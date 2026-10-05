/**
 * Cookie banner — FL0 (5/10/2026 sera, founder: «il banner deve incentivare
 * "Accetta tutto": con tre opzioni uguali vince il rifiuto»).
 *
 * Primo livello: UN pulsante pieno «Accetta tutto»; sotto, in testo,
 * «Personalizza» e «Continua senza accettare». La X vale «continua senza
 * accettare» (etichetta propria). Secondo livello (Personalizza): due
 * interruttori, Statistiche (GA4) e Misurazione delle inserzioni (Meta
 * Pixel + Conversions API), con «Salva la scelta» e di nuovo «Accetta tutto».
 *
 * Garante (linee guida 10/6/2021): proseguire senza consenso resta a UN
 * gesto dal primo livello (link + X), personalizzare e' a portata, nessun
 * consenso implicito (chiudere = solo essenziali). Cambia solo la gerarchia
 * visiva e le parole: la verita' della scelta resta in lib/consenso.js
 * (chiave `aurya_consent_v3`), identica a MP1.
 * SSR-safe (guards `window`/`localStorage`).
 */
import React, { useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Cookie, X } from 'lucide-react';
import { grantAnalyticsConsent, denyAnalyticsConsent } from '../../lib/analytics';
import { bannerDaMostrare, salvaConsenso, EVENTO_APRI } from '../../lib/consenso';

const ORO = '#8a7440';

export default function CookieConsentBanner() {
  const { t, i18n } = useTranslation('legal');
  const [visible, setVisible] = useState(false);
  const [personalizza, setPersonalizza] = useState(false);
  const [stats, setStats] = useState(true);        // nel secondo livello gli interruttori partono accesi:
  const [marketing, setMarketing] = useState(true); // chi li apre sceglie cosa TOGLIERE; si salva solo al clic

  // Decide visibility AFTER mount — avoids SSR mismatch and the
  // "banner flash on every reload before the localStorage read" UX bug.
  useEffect(() => {
    if (typeof window === 'undefined') return undefined;
    try {
      if (bannerDaMostrare()) setVisible(true);
    } catch {
      setVisible(true);   // storage inaccessibile: meglio chiedere
    }
    const riapri = () => { setPersonalizza(false); setVisible(true); };
    window.addEventListener(EVENTO_APRI, riapri);
    return () => window.removeEventListener(EVENTO_APRI, riapri);
  }, []);

  const scegli = useCallback((analytics, marketingScelto) => {
    // GA come prima (consent mode update); Meta ascolta lib/consenso.onCambio
    if (analytics) grantAnalyticsConsent();
    else denyAnalyticsConsent();
    salvaConsenso({ analytics, marketing: marketingScelto });
    setVisible(false);
    setPersonalizza(false);
  }, []);

  if (!visible) return null;

  // Privacy link respects current UI locale.
  const locale = ['it', 'en', 'de', 'fr'].includes(i18n.language)
    ? i18n.language
    : 'it';

  const testoBtn = 'text-xs font-medium text-muted-foreground underline-offset-2 hover:underline';

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
          {/* AC5 — la X dice cosa fa (= continua senza accettare, solo essenziali) */}
          <button
            type="button"
            onClick={() => scegli(false, false)}
            aria-label={t('cookie_banner.close_button', { defaultValue: 'Chiudi e continua con i soli cookie essenziali' })}
            className="rounded p-1 text-muted-foreground hover:bg-accent"
            data-testid="cookie-chiudi"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {personalizza ? (
          /* ── secondo livello: due interruttori, chiari ── */
          <div className="mt-3 space-y-2" data-testid="cookie-personalizza-pannello">
            <label className="flex items-start gap-2 text-xs">
              <input type="checkbox" checked={stats} onChange={(e) => setStats(e.target.checked)}
                     className="mt-0.5 h-4 w-4" style={{ accentColor: ORO }} data-testid="cookie-toggle-statistiche" />
              <span><strong>{t('cookie_banner.stats_label', { defaultValue: 'Statistiche' })}</strong>
                {' · '}<span className="text-muted-foreground">{t('cookie_banner.stats_desc', { defaultValue: 'capire quali pagine servono davvero (Google Analytics)' })}</span></span>
            </label>
            <label className="flex items-start gap-2 text-xs">
              <input type="checkbox" checked={marketing} onChange={(e) => setMarketing(e.target.checked)}
                     className="mt-0.5 h-4 w-4" style={{ accentColor: ORO }} data-testid="cookie-toggle-marketing" />
              <span><strong>{t('cookie_banner.marketing_label', { defaultValue: 'Misurazione delle inserzioni' })}</strong>
                {' · '}<span className="text-muted-foreground">{t('cookie_banner.marketing_desc', { defaultValue: 'sapere quali inserzioni portano persone vere (Meta). Nessun profilo venduto a nessuno.' })}</span></span>
            </label>
            <div className="flex flex-wrap items-center justify-end gap-2 pt-1">
              <button type="button" onClick={() => scegli(stats, marketing)} data-testid="cookie-salva"
                      className="rounded-full border border-[#8a7440]/40 px-4 py-1.5 text-xs font-semibold text-[#8a7440] hover:bg-[#8a7440]/10 dark:text-[#d6c49a]">
                {t('cookie_banner.save_button', { defaultValue: 'Salva la scelta' })}
              </button>
              <button type="button" onClick={() => scegli(true, true)} data-testid="cookie-accetta-tutto"
                      className="rounded-full bg-[#8a7440] px-4 py-1.5 text-xs font-semibold text-white hover:bg-[#75622f]">
                {t('cookie_banner.all_button', { defaultValue: 'Accetta tutto' })}
              </button>
            </div>
          </div>
        ) : (
          /* ── primo livello: un pulsante pieno, due vie in testo ── */
          <div className="mt-3">
            <button type="button" onClick={() => scegli(true, true)} data-testid="cookie-accetta-tutto"
                    className="w-full rounded-full bg-[#8a7440] px-4 py-2 text-sm font-semibold text-white hover:bg-[#75622f]">
              {t('cookie_banner.all_button', { defaultValue: 'Accetta tutto' })}
            </button>
            <div className="mt-2 flex items-center justify-between">
              <button type="button" onClick={() => setPersonalizza(true)} data-testid="cookie-personalizza" className={testoBtn}>
                {t('cookie_banner.personalize_button', { defaultValue: 'Personalizza' })}
              </button>
              <button type="button" onClick={() => scegli(false, false)} data-testid="cookie-continua-senza" className={testoBtn}>
                {t('cookie_banner.continue_without_button', { defaultValue: 'Continua senza accettare' })}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
