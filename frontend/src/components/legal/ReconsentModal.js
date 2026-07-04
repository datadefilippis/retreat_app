/**
 * Wave GDPR-Admin Phase E — blocking re-consent modal.
 *
 * Renders when ``user.consent_needs_refresh === true`` (server-computed
 * by /api/auth/me when the user's accepted_terms_version is stale vs
 * core/legal_versions.CURRENT_VERSION_TAG).
 *
 * Behaviour:
 *   - Dialog is NOT dismissible: Escape and outside-click are no-ops.
 *     The user has exactly two paths forward: accept the new terms, or
 *     log out (the latter handled by AuthContext.logout).
 *   - Mounts global at App.js scope, AFTER AuthProvider so it can read
 *     ``useAuth()``. Renders nothing when there is no logged-in user or
 *     when consent is in order — so it costs nothing in the common case.
 *   - On Accept: calls POST /api/auth/re-consent with the user's current
 *     UI locale, then calls refreshUser() so AuthContext picks up the
 *     fresh accepted_terms_version and the modal disappears.
 *
 * Why the IT version is the binding reference is NOT advertised in the
 * modal copy — that disclosure already lives in the header of every
 * translated Privacy/Terms doc the user opens via the "Read" links.
 *
 * Why we skip a "what changed (diff)" view: we don't ship one. The
 * privacy_<locale>.md files are the source of truth and they're short
 * enough to re-read. Future enhancement: render a server-computed
 * structural diff between version_tag N-1 and N.
 */
import React, { useState, useCallback } from 'react';
import * as DialogPrimitive from '@radix-ui/react-dialog';
import { useTranslation } from 'react-i18next';
import { ShieldCheck, ExternalLink, LogOut, Loader2 } from 'lucide-react';

import { useAuth } from '../../context/AuthContext';
import { authAPI } from '../../api/auth';

/**
 * Encode the user's UI locale into the public legal-doc URL so the
 * markdown renderer fetches the right translation when they click
 * "Read the Privacy Policy" / "Read the Terms".
 */
function buildLegalLink(docType, locale) {
  const safeLocale = ['it', 'en', 'de', 'fr'].includes(locale) ? locale : 'it';
  return `/${docType === 'privacy' ? 'privacy' : 'terms'}?lang=${safeLocale}`;
}

export default function ReconsentModal() {
  const { t, i18n } = useTranslation('legal');
  const { user, refreshUser, logout } = useAuth();

  const [checked, setChecked] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  // Render gate — no user, no need to refresh: render nothing.
  const open = Boolean(user && user.consent_needs_refresh);

  // ``isFirstConsent``: legacy users with no accepted_terms_version at
  // all see slightly different copy ("To use afianco accept …") vs
  // post-bump users ("We updated the docs, accept again to continue").
  const isFirstConsent = open && !user.accepted_terms_version;

  const locale = (user?.locale && ['it', 'en', 'de', 'fr'].includes(user.locale))
    ? user.locale
    : (i18n.language || 'it').slice(0, 2);

  const handleAccept = useCallback(async () => {
    if (!checked || submitting) return;
    setSubmitting(true);
    setError(null);
    try {
      await authAPI.reConsent(locale);
      // refresh AuthContext: the next /auth/me roundtrip will return
      // consent_needs_refresh=false and unmount this modal.
      await refreshUser();
    } catch (err) {
      // Surface a generic message; the backend logs the real cause.
      console.error('re-consent failed:', err);
      setError(t('reconsent.error_generic'));
      setSubmitting(false);
    }
  }, [checked, submitting, locale, refreshUser, t]);

  const handleLogout = useCallback(() => {
    if (submitting) return;
    logout();
  }, [submitting, logout]);

  // Block Escape + outside-click dismissal by intercepting the events.
  // We deliberately do NOT pass onOpenChange — Radix won't try to close.
  return (
    <DialogPrimitive.Root open={open}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay
          className="fixed inset-0 z-[100] bg-black/70 backdrop-blur-sm data-[state=open]:animate-in data-[state=open]:fade-in-0"
        />
        <DialogPrimitive.Content
          className="fixed left-1/2 top-1/2 z-[101] w-[95vw] max-w-xl -translate-x-1/2 -translate-y-1/2 rounded-lg border bg-background p-6 shadow-2xl data-[state=open]:animate-in data-[state=open]:zoom-in-95 sm:rounded-xl"
          onEscapeKeyDown={(e) => e.preventDefault()}
          onPointerDownOutside={(e) => e.preventDefault()}
          onInteractOutside={(e) => e.preventDefault()}
        >
          <div className="flex items-start gap-3">
            <div className="rounded-full bg-blue-100 p-2 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <div className="flex-1">
              <DialogPrimitive.Title className="text-lg font-semibold leading-tight tracking-tight">
                {t('reconsent.title')}
              </DialogPrimitive.Title>
              <DialogPrimitive.Description className="mt-1 text-sm text-muted-foreground">
                {isFirstConsent
                  ? t('reconsent.intro_first')
                  : t('reconsent.intro_update')}
              </DialogPrimitive.Description>
            </div>
          </div>

          {!isFirstConsent && (
            <div className="mt-4 rounded-md border border-blue-200 bg-blue-50 p-3 text-sm text-blue-900 dark:border-blue-900/40 dark:bg-blue-900/20 dark:text-blue-100">
              <p className="font-medium">
                {t('reconsent.what_changed_title')}
              </p>
              <p className="mt-1 text-blue-800 dark:text-blue-200">
                {t('reconsent.what_changed_body')}
              </p>
            </div>
          )}

          <div className="mt-4 flex flex-col gap-2 text-sm">
            <a
              href={buildLegalLink('privacy', locale)}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-blue-600 underline-offset-2 hover:underline dark:text-blue-400"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              {t('reconsent.read_privacy')}
            </a>
            <a
              href={buildLegalLink('terms', locale)}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-blue-600 underline-offset-2 hover:underline dark:text-blue-400"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              {t('reconsent.read_terms')}
            </a>
            <a
              href={`/legal/sub-processors?lang=${locale}`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-blue-600 underline-offset-2 hover:underline dark:text-blue-400"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              {t('reconsent.read_sub_processors')}
            </a>
          </div>

          <label className="mt-5 flex cursor-pointer items-start gap-2 rounded-md border p-3 hover:bg-muted/40">
            <input
              type="checkbox"
              checked={checked}
              onChange={(e) => setChecked(e.target.checked)}
              disabled={submitting}
              className="mt-0.5 h-4 w-4 cursor-pointer accent-blue-600"
            />
            <span className="text-sm leading-snug">
              {t('reconsent.checkbox_label')}
            </span>
          </label>

          {error && (
            <div className="mt-3 rounded-md border border-red-200 bg-red-50 p-2 text-xs text-red-700 dark:border-red-900/40 dark:bg-red-900/20 dark:text-red-300">
              {error}
            </div>
          )}

          {user?.current_terms_version && (
            <p className="mt-3 text-[11px] text-muted-foreground">
              {t('reconsent.version_notice', { version: user.current_terms_version })}
            </p>
          )}

          <div className="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <button
              type="button"
              onClick={handleLogout}
              disabled={submitting}
              className="inline-flex items-center justify-center gap-1.5 rounded-md border border-input bg-background px-4 py-2 text-sm font-medium hover:bg-accent disabled:opacity-50"
            >
              <LogOut className="h-4 w-4" />
              {t('reconsent.logout_button')}
            </button>
            <button
              type="button"
              onClick={handleAccept}
              disabled={!checked || submitting}
              className="inline-flex items-center justify-center gap-1.5 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
              {submitting ? t('reconsent.accepting') : t('reconsent.accept_button')}
            </button>
          </div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
