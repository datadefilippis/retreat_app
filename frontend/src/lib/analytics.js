/**
 * GA1 — Google Analytics 4 con Consent Mode v2.
 *
 * Regole della casa:
 *  - L'ID di misurazione arriva da /public/site-config (env
 *    GA_MEASUREMENT_ID sul backend): runtime, non build-time. Al
 *    lancio ufficiale NON si riconfigura niente: stesso ID, stesse
 *    pagine, stesso storico in GA.
 *  - Consent Mode v2 con default TUTTO negato: finché l'utente non
 *    accetta dal cookie banner, GA non imposta cookie (manda solo i
 *    ping anonimi senza identificatori previsti dal Consent Mode).
 *  - La scelta dell'utente è persistita e riapplicata ai boot
 *    successivi; revocabile in qualsiasi momento.
 *  - Le page_view le mandiamo noi sui cambi rotta della SPA
 *    (send_page_view: false), così ogni navigazione conta una volta.
 */

const CONSENT_KEY = 'aurya_analytics_consent_v1';

let loaded = false;
let measurementId = null;

function gtag() {
  if (typeof window === 'undefined') return;
  window.dataLayer = window.dataLayer || [];
  window.dataLayer.push(arguments);
}

export function readStoredConsent() {
  try {
    const raw = window.localStorage.getItem(CONSENT_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch { return null; }
}

function storeConsent(analytics) {
  try {
    window.localStorage.setItem(CONSENT_KEY, JSON.stringify({
      analytics,
      at: new Date().toISOString(),
    }));
  } catch { /* storage negato: la scelta vale per la sessione */ }
}

export function initAnalytics(id) {
  if (!id || loaded || typeof window === 'undefined') return;
  measurementId = id;

  // Consent Mode v2 PRIMA di tutto: nessun cookie finché non c'è un sì
  gtag('consent', 'default', {
    ad_storage: 'denied',
    ad_user_data: 'denied',
    ad_personalization: 'denied',
    analytics_storage: 'denied',
  });
  gtag('js', new Date());
  gtag('config', id, { send_page_view: false });

  const s = document.createElement('script');
  s.async = true;
  s.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(id)}`;
  document.head.appendChild(s);
  loaded = true;

  // consenso già espresso in una visita precedente → riapplica in silenzio
  const stored = readStoredConsent();
  if (stored?.analytics === true) grantAnalyticsConsent(false);
}

export function grantAnalyticsConsent(persist = true) {
  gtag('consent', 'update', { analytics_storage: 'granted' });
  if (persist) storeConsent(true);
}

export function denyAnalyticsConsent(persist = true) {
  gtag('consent', 'update', { analytics_storage: 'denied' });
  if (persist) storeConsent(false);
}

export function trackEvent(name, params = {}) {
  if (!loaded || !measurementId) return;
  gtag('event', name, params);
}

export function trackPageView(path) {
  if (!loaded || !measurementId) return;
  gtag('event', 'page_view', {
    page_path: path,
    page_location: window.location.href,
    page_title: typeof document !== 'undefined' ? document.title : undefined,
  });
}
