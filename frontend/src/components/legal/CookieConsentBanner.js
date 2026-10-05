/**
 * Cookie banner — tre scelte (MP1, 5/10/2026).
 *
 *   Solo essenziali   → niente GA, niente Meta
 *   Statistiche       → Google Analytics 4 (Consent Mode)
 *   Accetta tutto     → statistiche + marketing (Meta Pixel e Conversions API)
 *
 * La verita' della scelta sta in lib/consenso.js (chiave `aurya_consent_v3`):
 * chi aveva scelto con il banner a una categoria lo rivede UNA volta.
 * La X e «Chiudi» valgono «Solo essenziali» (mai un consenso implicito).
 * Il pie' di pagina puo' riaprirlo con apriPreferenzeCookie().
 * SSR-safe (guards `window`/`localStorage`).
 */
import React, { useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Cookie, X } from 'lucide-react';
import { grantAnalyticsConsent, denyAnalyticsConsent } from '../../lib/analytics';
import { bannerDaMostrare, salvaConsenso, EVENTO_APRI } from '../../lib/consenso';

export default function CookieConsentBanner() {
  const { t, i18n } = useTranslation('legal');
  const [visible, setVisible] = useState(false);

  // Decide visibility AFTER mount — avoids SSR mismatch and the
  // "banner flash on every reload before the localStorage read" UX bug.
  useEffect(() => {
    if (typeof window === 'undefined') return undefined;
    try {
      if (bannerDaMostrare()) setVisible(true);
    } catch {
      setVisible(true);   // storage inaccessibile: meglio chiedere
    }
    const riapri = () => setVisible(true);
    window.addEventListener(EVENTO_APRI, riapri);
    return () => window.removeEventListener(EVENTO_APRI, riapri);
  }, []);

  const scegli = useCallback((analytics, marketing) => {
    // GA come prima (consent mode update); Meta ascolta lib/consenso.onCambio
    if (analytics) grantAnalyticsConsent();
    else denyAnalyticsConsent();
    salvaConsenso({ analytics, marketing });
    setVisible(false);
  }, []);

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
      data-testid="cookie-banner"
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
          {/* AC5 — etichetta dedicata per la X: dice cosa fa (= solo essenziali) */}
          <button
            type="button"
            onClick={() => scegli(false, false)}
            aria-label={t('cookie_banner.close_button', { defaultValue: 'Chiudi e continua con i soli cookie essenziali' })}
            className="rounded p-1 text-muted-foreground hover:bg-accent"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="mt-3 flex flex-wrap justify-end gap-2">
          <button
            type="button"
            onClick={() => scegli(false, false)}
            data-testid="cookie-solo-essenziali"
            className="rounded-full border border-[#8a7440]/40 px-4 py-1.5 text-xs font-semibold text-[#8a7440] hover:bg-[#8a7440]/10 dark:text-[#d6c49a]"
          >
            {t('cookie_banner.essential_button')}
          </button>
          <button
            type="button"
            onClick={() => scegli(true, false)}
            data-testid="cookie-statistiche"
            className="rounded-full border border-[#8a7440]/40 px-4 py-1.5 text-xs font-semibold text-[#8a7440] hover:bg-[#8a7440]/10 dark:text-[#d6c49a]"
          >
            {t('cookie_banner.stats_button', { defaultValue: 'Statistiche' })}
          </button>
          <button
            type="button"
            onClick={() => scegli(true, true)}
            data-testid="cookie-accetta-tutto"
            className="rounded-full bg-[#8a7440] px-4 py-1.5 text-xs font-semibold text-white hover:bg-[#75622f]"
          >
            {t('cookie_banner.all_button', { defaultValue: 'Accetta tutto' })}
          </button>
        </div>
      </div>
    </div>
  );
}
