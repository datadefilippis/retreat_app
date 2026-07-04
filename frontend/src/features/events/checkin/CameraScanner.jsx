/**
 * CameraScanner — html5-qrcode wrapper for the door check-in flow.
 *
 * Used by features/events/CheckInPage.js. Lives in a dedicated file
 * so the camera-permission and error-mapping concerns stay isolated
 * from the page-level layout, and so future surfaces (e.g. an admin
 * inline scanner on the event dashboard) can mount the same component.
 *
 * Why this lives next to CheckInPage and not in src/components/
 * --------------------------------------------------------------------
 * The component is meaningfully event-flavoured (debounce window,
 * QR box size, the contract with the parent's `onCode` handler are
 * all tuned for ticket scanning). Promoting it to a generic UI
 * primitive would be premature: today there's exactly one consumer.
 *
 * Error handling
 * --------------------------------------------------------------------
 * The single most common production failure on this surface is the
 * camera failing to start, and the user not understanding why. We
 * map the underlying browser/library exceptions to a small set of
 * user-actionable messages so the UI can guide the operator to
 * either fix the permission, switch device, or switch to the manual
 * input fallback that the parent always renders alongside.
 *
 * Mapping table:
 *   NotAllowedError        permission denied (user clicked "Block")
 *   NotFoundError          no camera device at all (desktop, locked-down kiosk)
 *   NotReadableError       camera busy (other tab, OS lock, hardware fault)
 *   OverconstrainedError   `facingMode: environment` not satisfiable
 *                          (front-only device); we retry without the
 *                          constraint inside the library, but if it
 *                          surfaces here it's terminal
 *   SecurityError          insecure context (http:// in non-localhost)
 *   AbortError             user navigated away while warming up
 *   default                anything we did not catalog
 *
 * The component reports the categorised reason back to the parent via
 * `onError(reason, message)` so the parent can do something smart with
 * the manual-input field (e.g. autofocus, surface a localised toast).
 */

import React, { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Html5Qrcode } from 'html5-qrcode';


// One stable random suffix per mount — html5-qrcode requires a unique
// container id, and re-using a counter risks collision when the user
// mounts/unmounts the scanner several times in the same session.
function useStableContainerId() {
  return useRef('qr-scanner-' + Math.random().toString(36).slice(2)).current;
}


// Categorise the various ways camera startup can fail. The first
// match wins; fallthrough lands on the generic "unknown" bucket.
// The translator function `t` is passed in so categoriseError stays
// pure (testable + memoisable). Falls back to Italian defaults when
// `t` is null (e.g. unit tests).
function categoriseError(err, t = null) {
  const tx = (key, fallback) => (t ? t(`dashboards.event.checkIn.scanner.errors.${key}`) : fallback);
  if (!err) return ['unknown', tx('unknown', 'Errore sconosciuto.')];

  const name = err.name || '';
  const msg = (err.message || '').toLowerCase();

  // Insecure-context check — easier to read from window.isSecureContext
  // than from the underlying error message, which varies by browser.
  if (typeof window !== 'undefined' && window.isSecureContext === false) {
    return ['insecure_context', tx('insecure_context', "La fotocamera richiede una connessione sicura (HTTPS). Apri questa pagina via https:// oppure usa l'input manuale qui sotto.")];
  }
  if (typeof navigator !== 'undefined' && !navigator.mediaDevices) {
    return ['no_media_api', tx('no_media_api', "Il browser non supporta l'accesso alla fotocamera. Usa l'input manuale qui sotto.")];
  }

  switch (name) {
    case 'NotAllowedError':
    case 'PermissionDeniedError':
      return ['permission_denied', tx('permission_denied', "Permesso fotocamera negato. Tocca il lucchetto nella barra dell'indirizzo, abilita la fotocamera, poi ricarica.")];
    case 'NotFoundError':
    case 'DevicesNotFoundError':
      return ['no_camera', tx('no_camera', "Nessuna fotocamera disponibile su questo dispositivo. Usa l'input manuale.")];
    case 'NotReadableError':
    case 'TrackStartError':
      return ['camera_busy', tx('camera_busy', "La fotocamera è in uso da un'altra app o tab. Chiudi le altre app e riprova.")];
    case 'OverconstrainedError':
    case 'ConstraintNotSatisfiedError':
      return ['constraints_unmet', tx('constraints_unmet', "Non riesco a usare la fotocamera posteriore. Riprova o usa l'input manuale.")];
    case 'SecurityError':
      return ['security', tx('security', "Accesso fotocamera bloccato dalle policy del browser. Verifica le impostazioni del sito.")];
    case 'AbortError':
      return ['aborted', tx('aborted', "Avvio fotocamera interrotto.")];
    default:
      // Some errors don't have a `.name` we recognise but include a
      // hint in the message — try a coarse keyword pass before giving up.
      if (msg.includes('permission')) return ['permission_denied', tx('permission_denied_short', "Permesso fotocamera negato.")];
      if (msg.includes('not found') || msg.includes('no camera')) return ['no_camera', tx('no_camera_short', "Nessuna fotocamera disponibile.")];
      return ['unknown', err.message || tx('fallback', "Errore avvio fotocamera. Usa l'input manuale qui sotto.")];
  }
}


export default function CameraScanner({ onCode, onClose, onError }) {
  const { t } = useTranslation('products');
  const containerId = useStableContainerId();
  const scannerRef = useRef(null);
  const [error, setError] = useState(null);
  const [errorReason, setErrorReason] = useState(null);

  // Same-code debounce window: a single QR in the camera frame fires
  // the decode callback ~10 times per second; we don't want one card
  // resolving to 10 check-in API calls.
  const lastScanRef = useRef({ code: null, at: 0 });

  // Stable-ref pattern for the callbacks. CheckInPage passes inline
  // arrow functions for onCode and onError, which means their identity
  // changes on every render of the parent. Listing them as `useEffect`
  // deps would re-run start/stop on the html5-qrcode scanner every
  // time the parent re-renders (counters poll every 10s, so the parent
  // re-renders frequently) — that produces a mount/unmount loop where
  // `stop()` is called before `start()` finishes, the lib bubbles a
  // sync error up the React tree, and the global ErrorBoundary catches
  // it as "Qualcosa è andato storto". The refs stay current via the
  // tiny effect below; the main effect only depends on containerId so
  // it runs exactly once per mount.
  const onCodeRef = useRef(onCode);
  const onErrorRef = useRef(onError);
  useEffect(() => { onCodeRef.current = onCode; }, [onCode]);
  useEffect(() => { onErrorRef.current = onError; }, [onError]);

  useEffect(() => {
    let mounted = true;

    const reportError = (errLike) => {
      if (!mounted) return;
      const [reason, msg] = categoriseError(errLike, t);
      setErrorReason(reason);
      setError(msg);
      const cb = onErrorRef.current;
      if (cb) {
        try { cb(reason, msg); } catch { /* parent crash must not bubble back */ }
      }
    };

    const start = async () => {
      // Pre-flight: bail before constructing Html5Qrcode if the
      // platform obviously can't honour the request. Cleaner UX than
      // letting the lib throw deep inside its own warmup.
      if (typeof window !== 'undefined' && window.isSecureContext === false) {
        reportError({ name: 'SecurityError', message: 'insecure context' });
        return;
      }
      if (typeof navigator === 'undefined' || !navigator.mediaDevices) {
        reportError({ message: 'no media api' });
        return;
      }

      // Constructor is its own try block — some browsers throw
      // synchronously here (e.g. when the container element isn't yet
      // in the DOM, in test envs, or on hot-reload races) and we want
      // that error to surface as a friendly banner rather than crash
      // the whole CheckInPage tree.
      let scanner;
      try {
        scanner = new Html5Qrcode(containerId, { verbose: false });
      } catch (e) {
        reportError(e);
        return;
      }
      scannerRef.current = scanner;

      try {
        await scanner.start(
          { facingMode: 'environment' },
          { fps: 10, qrbox: { width: 240, height: 240 } },
          (decoded) => {
            if (!mounted) return;
            const now = Date.now();
            if (lastScanRef.current.code === decoded &&
                now - lastScanRef.current.at < 2000) return;
            lastScanRef.current = { code: decoded, at: now };
            const cb = onCodeRef.current;
            if (cb) {
              try { cb(decoded); } catch { /* parent crash must not bubble back */ }
            }
          },
          () => { /* per-frame decode errors are noisy — ignore */ },
        );
      } catch (e) {
        reportError(e);
      }
    };

    start();
    return () => {
      mounted = false;
      const sc = scannerRef.current;
      if (sc) {
        // Best-effort cleanup. The lib raises if `stop()` is called
        // before the camera fully started — swallow that, the next
        // `clear()` either succeeds or no-ops, and we never want
        // teardown to break navigation.
        sc.stop().catch(() => {}).finally(() => {
          try { sc.clear(); } catch {}
        });
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [containerId]);

  return (
    <div className="rounded-xl border border-gray-300 bg-white p-3" data-testid="camera-scanner">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold text-gray-900">{t('dashboards.event.checkIn.scanner.title')}</h3>
        <button
          type="button"
          onClick={onClose}
          className="text-xs text-gray-500 hover:text-gray-900 underline"
        >{t('dashboards.event.checkIn.scanner.closeBtn')}</button>
      </div>
      <div
        id={containerId}
        className="rounded-lg overflow-hidden bg-black aspect-square max-w-xs mx-auto"
      />
      {error && (
        <div
          className="mt-2 rounded-lg border border-red-200 bg-red-50 p-3"
          role="alert"
          data-error-reason={errorReason}
        >
          <p className="text-xs font-semibold text-red-900 mb-1">{t('dashboards.event.checkIn.scanner.errorTitle')}</p>
          <p className="text-xs text-red-800 leading-snug">{error}</p>
        </div>
      )}
    </div>
  );
}
