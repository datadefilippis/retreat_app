/**
 * Wave GDPR-Admin Phase E — cookie / tracking disclosure banner.
 *
 * afianco does NOT use third-party tracking, analytics, or advertising
 * cookies. We use ONLY technical first-party cookies (auth JWT in
 * localStorage + locale preference) which are exempt from prior
 * consent under ePrivacy / GDPR. But TRANSPARENCY is still required
 * (GDPR Art. 13.1.c and the ePrivacy Directive recital 25): the user
 * must be informed which cookies are used and why.
 *
 * Implementation choice:
 *   - One-time bottom banner shown on PUBLIC pages until the user
 *     clicks "Got it" or visits a page that already shows the banner
 *     wisdom (e.g. ReconsentModal — but those are auth-only surfaces).
 *   - Persistence: localStorage key ``afianco_cookie_disclosure_v1``.
 *     We bump the suffix (``_v2``, …) only if the disclosure text
 *     changes materially — small wording fixes don't re-prompt.
 *   - No blocking: the banner is non-modal, the page is fully usable
 *     beneath it. Because we only run essential cookies, no
 *     opt-in/opt-out toggles are needed.
 *
 * Mount in App.js OUTSIDE AuthProvider so the banner shows on the
 * public landing too. SSR-safe (guards `window`/`localStorage`).
 */
import React, { useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Cookie, X } from 'lucide-react';

const STORAGE_KEY = 'aurya_cookie_disclosure_v1';

export default function CookieConsentBanner() {
  const { t, i18n } = useTranslation('legal');
  const [visible, setVisible] = useState(false);

  // Decide visibility AFTER mount — avoids SSR mismatch and the
  // "banner flash on every reload before the localStorage read" UX bug.
  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      const seen = window.localStorage.getItem(STORAGE_KEY);
      if (!seen) setVisible(true);
    } catch {
      // localStorage unavailable (private mode / disabled). Show the
      // banner once per session in that case — better safe.
      setVisible(true);
    }
  }, []);

  const dismiss = useCallback(() => {
    try {
      window.localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          accepted_at: new Date().toISOString(),
          locale: (i18n.language || 'it').slice(0, 2),
        }),
      );
    } catch {
      // ignore — banner will reappear next session, no functional break.
    }
    setVisible(false);
  }, [i18n.language]);

  if (!visible) return null;

  // Privacy link respects current UI locale.
  const locale = ['it', 'en', 'de', 'fr'].includes(i18n.language)
    ? i18n.language
    : 'it';

  return (
    <div
      role="region"
      aria-label={t('cookie_banner.title')}
      className="fixed bottom-3 left-3 right-3 z-[90] sm:left-auto sm:right-4 sm:max-w-md"
    >
      <div className="rounded-lg border bg-background p-4 shadow-xl ring-1 ring-black/5 dark:ring-white/5">
        <div className="flex items-start gap-3">
          <div className="rounded-full bg-[#8a7440]/10 p-1.5 text-[#8a7440] dark:bg-[#d6c49a]/15 dark:text-[#d6c49a]">
            <Cookie className="h-4 w-4" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold leading-tight">
              {t('cookie_banner.title')}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              {t('cookie_banner.body')}
            </p>
            <a
              href={`/privacy?lang=${locale}`}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-1 inline-block text-xs font-medium text-[#8a7440] hover:underline dark:text-[#d6c49a]"
            >
              {t('cookie_banner.details_link')}
            </a>
          </div>
          <button
            type="button"
            onClick={dismiss}
            aria-label={t('cookie_banner.accept_button')}
            className="rounded p-1 text-muted-foreground hover:bg-accent"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="mt-3 flex justify-end">
          <button
            type="button"
            onClick={dismiss}
            className="rounded-full bg-[#8a7440] px-4 py-1.5 text-xs font-semibold text-white hover:bg-[#75622f]"
          >
            {t('cookie_banner.accept_button')}
          </button>
        </div>
      </div>
    </div>
  );
}
