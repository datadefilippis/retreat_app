/**
 * LessonPlayer — Bunny Stream iframe player for a single lesson.
 *
 * Owns:
 *   • Signed URL fetch from /play-url, with automatic refresh 5
 *     minutes before expiry (long sessions don't break mid-video).
 *   • 30s heartbeat to /progress while the tab is visible
 *     (cumulative watched_seconds, server enforces max() so
 *     rewinds never lower the counter).
 *   • Watermark overlay (customer email) when the org has
 *     `watermark_enabled` (HTML overlay, pointer-events: none, anchored
 *     top-right so it doesn't fight Bunny's bottom-right chrome).
 *   • Player.js subscription + `ended` event listener for auto-
 *     complete (Q3=a — fires immediately on natural video end).
 *   • Dedicated error states (no-video, bunny-missing, generic).
 *
 * Inputs:
 *   enrollmentId       — used to scope all backend calls
 *   lesson             — { id, title, duration_seconds, ... }
 *   customerEmail      — fallback watermark when server doesn't supply
 *   onProgressUpdate   — called on every successful heartbeat with
 *                        the fresh server progress object
 *   onAccessRevoked    — called when the server returns 403
 *                        enrollment_revoked / enrollment_expired
 *   onLessonEnded      — called when Bunny's iframe broadcasts the
 *                        Player.js `ended` event (auto-complete)
 *
 * Extracted from the 1392-line monolith during Fase 4 architectural
 * split. The previous overlay button "Segna come completata" lived
 * here; it was lifted to LessonActionBar to fix a UX bug (the overlay
 * covered the iframe's volume/fullscreen/settings chrome).
 */

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { customerPortalAPI } from '../../../../api/customerPortal';


// Must match backend services/bunny_service.py REFRESH_MARGIN_SECONDS.
const REFRESH_MARGIN_MS = 300 * 1000;             // 5 minutes
// Heartbeat cadence — conservative so we don't spam /progress when the
// customer leaves the tab open.
const HEARTBEAT_INTERVAL_MS = 30 * 1000;          // 30s

const BUNNY_IFRAME_ORIGIN = 'https://iframe.mediadelivery.net';


export default function LessonPlayer({
  enrollmentId,
  lesson,
  customerEmail,
  onProgressUpdate,
  onAccessRevoked,
  onLessonEnded,
}) {
  const { t } = useTranslation('customer_portal');
  const [playUrl, setPlayUrl] = useState(null);
  const [expiresAt, setExpiresAt] = useState(null);
  const [watermarkText, setWatermarkText] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const iframeRef = useRef(null);

  // Heartbeat bookkeeping:
  //   - startedAtRef captures when the current lesson started playing
  //     (changes on lesson switch)
  //   - baselineWatchedRef is the server-side baseline at mount; every
  //     heartbeat sends baseline + elapsed_local so we never regress.
  const startedAtRef = useRef(null);
  const baselineWatchedRef = useRef(0);
  const refreshTimerRef = useRef(null);
  const heartbeatTimerRef = useRef(null);

  /* Fetch a fresh signed URL */
  const fetchPlayUrl = useCallback(async () => {
    if (!lesson?.id) return;
    setLoading(true);
    setError(null);
    try {
      const { data } = await customerPortalAPI.getPlayUrl(enrollmentId, lesson.id);
      setPlayUrl(data.play_url);
      setExpiresAt(data.expires_at ? new Date(data.expires_at) : null);
      setWatermarkText(data.watermark_text || null);
    } catch (err) {
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail;
      const code = typeof detail === 'object' ? detail?.error : null;
      if (status === 403 && (code === 'enrollment_revoked' || code === 'enrollment_expired')) {
        onAccessRevoked?.(code);
        return;
      }
      if (code === 'lesson_no_video') {
        setError({ kind: 'no_video' });
      } else if (code === 'bunny_not_configured') {
        setError({ kind: 'bunny_missing' });
      } else {
        setError({ kind: 'generic' });
      }
      setPlayUrl(null);
    } finally {
      setLoading(false);
    }
  }, [enrollmentId, lesson?.id, onAccessRevoked]);

  /* On lesson change: reset baselines + fetch a fresh URL */
  useEffect(() => {
    startedAtRef.current = Date.now();
    baselineWatchedRef.current = 0;
    setPlayUrl(null);
    setError(null);
    fetchPlayUrl();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lesson?.id, enrollmentId]);

  /* Schedule auto-refresh 5 min before expiry */
  useEffect(() => {
    if (!expiresAt) return;
    if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
    const delay = Math.max(1000, expiresAt.getTime() - Date.now() - REFRESH_MARGIN_MS);
    refreshTimerRef.current = setTimeout(() => { fetchPlayUrl(); }, delay);
    return () => {
      if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current);
    };
  }, [expiresAt, fetchPlayUrl]);

  /* Listen for Bunny's `ended` postMessage event → auto-complete the
   * lesson (Q3=a decision: auto-mark immediately on natural video end).
   *
   * Bunny Stream embeds use the Player.js cross-frame protocol. Events
   * arrive as JSON-encoded messages from the iframe origin. After the
   * iframe loads we send an `addEventListener` subscription so the
   * player knows to broadcast `ended` (and other) events back to us
   * — this is the Player.js handshake that some embed configurations
   * require.
   *
   * Defensive parsing: messages can arrive as either JSON strings or
   * already-parsed objects depending on browser + iframe version. We
   * handle both. We also gate on origin so we don't trust arbitrary
   * messages from other iframes (storefront, ads, etc).
   *
   * Idempotency: the parent's onLessonEnded handler is responsible for
   * the "already-completed" guard — we just notify on every ended
   * event we observe.
   */
  useEffect(() => {
    if (!playUrl || !onLessonEnded) return;

    // Send subscription handshake once the iframe has had a chance to
    // initialize. ~500ms is enough for the player to set up its
    // message listener — earlier subscriptions get lost.
    const subscribeTimer = setTimeout(() => {
      try {
        const iframe = iframeRef.current;
        if (!iframe?.contentWindow) return;
        iframe.contentWindow.postMessage(
          JSON.stringify({
            context: 'player.js',
            version: '0.0.7',
            method: 'addEventListener',
            value: 'ended',
          }),
          BUNNY_IFRAME_ORIGIN,
        );
      } catch {
        // Cross-origin send can throw on some browsers if the iframe
        // hasn't fully loaded yet — ignored. The next lesson load
        // will retry; the auto-complete is best-effort, not critical
        // (the user always has the manual "Segna come completata"
        // button in the action bar as a fallback).
      }
    }, 500);

    const handleMessage = (event) => {
      // Strict origin check — only trust the Bunny iframe.
      if (event.origin !== BUNNY_IFRAME_ORIGIN) return;

      let data = event.data;
      if (typeof data === 'string') {
        try { data = JSON.parse(data); } catch { return; }
      }
      if (!data || typeof data !== 'object') return;

      // Player.js event format: `{ event: 'ended', ... }`. Some
      // embed builds wrap it as `{ value: 'ended' }` for response
      // handshakes — we accept both.
      const evt = data.event || data.value;
      if (evt === 'ended') {
        onLessonEnded();
      }
    };

    window.addEventListener('message', handleMessage);
    return () => {
      clearTimeout(subscribeTimer);
      window.removeEventListener('message', handleMessage);
    };
  }, [playUrl, onLessonEnded]);

  /* Heartbeat — only when the tab is visible. Sends cumulative
     watched_seconds = baseline + elapsed_local_seconds */
  useEffect(() => {
    if (!playUrl || !lesson?.id) return;

    const tick = async () => {
      if (document.visibilityState !== 'visible') return;
      const elapsed = Math.floor((Date.now() - (startedAtRef.current || Date.now())) / 1000);
      const total = baselineWatchedRef.current + elapsed;
      try {
        const { data } = await customerPortalAPI.sendProgress(enrollmentId, {
          lesson_id: lesson.id,
          watched_seconds: total,
          completed: false,
        });
        onProgressUpdate?.(data);
      } catch (err) {
        const code = err?.response?.data?.detail?.error;
        if (code === 'enrollment_revoked' || code === 'enrollment_expired') {
          onAccessRevoked?.(code);
        }
        // Silent on transient errors — the next heartbeat retries.
      }
    };

    heartbeatTimerRef.current = setInterval(tick, HEARTBEAT_INTERVAL_MS);
    return () => {
      if (heartbeatTimerRef.current) clearInterval(heartbeatTimerRef.current);
    };
  }, [playUrl, lesson?.id, enrollmentId, onProgressUpdate, onAccessRevoked]);

  /* ─── Render ────────────────────────────────────────────────────── */

  // Dedicated error states for the player surface
  if (error?.kind === 'no_video') {
    return (
      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm aspect-video flex flex-col items-center justify-center text-center p-6">
        <div className="text-4xl mb-2">🎬</div>
        <h3 className="text-sm font-semibold text-gray-900">{t('customer_portal:lessonPlayer.errors.noVideo.title')}</h3>
        <p className="text-xs text-gray-600 mt-1 max-w-md">
          {t('customer_portal:lessonPlayer.errors.noVideo.body')}
        </p>
      </div>
    );
  }
  if (error?.kind === 'bunny_missing') {
    return (
      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm aspect-video flex flex-col items-center justify-center text-center p-6">
        <div className="text-4xl mb-2">🛠️</div>
        <h3 className="text-sm font-semibold text-gray-900">{t('customer_portal:lessonPlayer.errors.bunnyMissing.title')}</h3>
        <p className="text-xs text-gray-600 mt-1 max-w-md">
          {t('customer_portal:lessonPlayer.errors.bunnyMissing.body')}
        </p>
      </div>
    );
  }
  if (error?.kind === 'generic') {
    return (
      <div className="bg-white rounded-2xl border border-red-200 shadow-sm aspect-video flex flex-col items-center justify-center text-center p-6">
        <div className="text-4xl mb-2">⚠️</div>
        <h3 className="text-sm font-semibold text-gray-900">{t('customer_portal:lessonPlayer.errors.generic.title')}</h3>
        <button
          type="button"
          onClick={fetchPlayUrl}
          className="mt-3 rounded-md bg-gray-900 text-white text-xs font-semibold px-3 py-1.5 hover:bg-gray-800"
        >
          {t('customer_portal:lessonPlayer.errors.generic.retry')}
        </button>
      </div>
    );
  }

  const displayWatermark = watermarkText || (customerEmail || null);

  return (
    <div className="bg-black rounded-2xl overflow-hidden relative aspect-video shadow-sm">
      {loading && !playUrl && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 text-white/80 text-sm">
          {/* Subtle gray pulsing dot replaces the old "Caricamento video…"
              text — less noisy, signals progress without a spinner. */}
          <div className="h-2 w-2 rounded-full bg-white/60 animate-pulse" aria-hidden />
          <span className="text-xs text-white/60">{t('customer_portal:lessonPlayer.preparing')}</span>
        </div>
      )}
      {playUrl && (
        <iframe
          ref={iframeRef}
          key={playUrl}
          src={playUrl}
          title={lesson?.title || t('customer_portal:lessonPlayer.iframeTitleFallback')}
          className="absolute inset-0 w-full h-full"
          loading="lazy"
          allow="accelerometer; gyroscope; autoplay; encrypted-media; picture-in-picture;"
          allowFullScreen
          /*
           * Referrer-Policy override
           * ------------------------
           * Bunny's iframe document does not set a Referrer-Policy of
           * its own, so the browser inherits whatever the embedding
           * page (afianco.app/account/courses/<id>) says. The default
           * strict-origin-when-cross-origin combined with cross-origin
           * sub-requests inside the iframe (player -> Pull Zone CDN)
           * produces a request with `Origin` set but no `Referer`,
           * which the Pull Zone's hotlink protection rejects with 403.
           * The visible symptom is "This content is blocked" with
           * the watermark still visible (player loaded, manifest didn't).
           *
           * "no-referrer-when-downgrade" mirrors the pre-2020 default
           * and ensures the Referer header is sent for every same-
           * scheme request — including the cross-origin fetch from
           * the iframe document to the Pull Zone CDN. This keeps the
           * pull zone happy without the merchant having to flip any
           * Bunny dashboard switch.
           *
           * Security trade-off: the Pull Zone host (vz-XXX.b-cdn.net)
           * sees a Referer pointing at iframe.mediadelivery.net, NOT
           * at afianco.app. The customer's specific URL never leaks
           * to the CDN. The downgrade clause means the policy degrades
           * safely when an HTTPS page would otherwise leak to HTTP.
           */
          referrerPolicy="no-referrer-when-downgrade"
        />
      )}
      {/* Watermark overlay — pointer-events: none so clicks pass to the
          iframe. Anchored top-right because the player chrome (volume/
          fullscreen/settings) lives BOTTOM-right and would be overlapped
          otherwise. The "Mark completed" button used to live bottom-right
          too — that was the bug fixed in Fase 1 (button moved to
          LessonActionBar). */}
      {playUrl && watermarkText && displayWatermark && (
        <div
          className="pointer-events-none absolute top-2 right-3 text-white/70 text-[11px] font-mono select-none"
          style={{ textShadow: '0 0 4px rgba(0,0,0,0.8)' }}
          aria-hidden
        >
          {displayWatermark}
        </div>
      )}
    </div>
  );
}
