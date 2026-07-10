/**
 * i18n configuration — AFianco internationalization foundation.
 *
 * Uses i18next + react-i18next with bundled JSON translations.
 * Language is resolved from: user preference → browser → Italian fallback.
 *
 * Namespaces:
 *   common            — navigation, buttons, generic labels, period selector
 *   auth              — login, signup, password reset
 *   settings          — settings page
 *   dashboard         — dashboard page chrome and empty states
 *   customers_light   — customers light module
 *   cashflow_monitor  — cashflow monitor module
 *   team              — team management page
 *   modules_page      — module library page
 *   alerts            — standalone alerts page
 *   ai_analysis       — AI analysis chat and digest
 */
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

// ── Translation imports ─────────────────────────────────────────────────────
import commonIt from './locales/it/common.json';
import authIt from './locales/it/auth.json';
import prelaunchIt from './locales/it/prelaunch.json';
// PL17 — restano sincroni: usati dai banner billing/paywall EAGER
import settingsIt from './locales/it/settings.json';
import modulesPageIt from './locales/it/modules_page.json';


import catalogIt from './locales/it/catalog.json';
// Fase 2 Track F Step 9 — legacy `setup` namespace removed (was used by
// the deprecated SetupPage.js). The new wizard uses `setup_wizard`.
import storefrontIt from './locales/it/storefront.json';
import landingsIt from './locales/it/landings.json';
import customerAuthIt from './locales/it/customer_auth.json';
import customerPortalIt from './locales/it/customer_portal.json';
// Fase 2 Track F — Setup Wizard dynamic onboarding widget
// Wave GDPR-Admin Phase E — re-consent modal, cookie banner, sub-processors page
import legalIt from './locales/it/legal.json';

import commonEn from './locales/en/common.json';
import authEn from './locales/en/auth.json';
import prelaunchEn from './locales/en/prelaunch.json';
// PL17 — restano sincroni: usati dai banner billing/paywall EAGER
import settingsEn from './locales/en/settings.json';
import modulesPageEn from './locales/en/modules_page.json';


import catalogEn from './locales/en/catalog.json';
import storefrontEn from './locales/en/storefront.json';
import landingsEn from './locales/en/landings.json';
import customerAuthEn from './locales/en/customer_auth.json';
import customerPortalEn from './locales/en/customer_portal.json';
import legalEn from './locales/en/legal.json';

import commonDe from './locales/de/common.json';
import authDe from './locales/de/auth.json';
import prelaunchDe from './locales/de/prelaunch.json';
// PL17 — restano sincroni: usati dai banner billing/paywall EAGER
import settingsDe from './locales/de/settings.json';
import modulesPageDe from './locales/de/modules_page.json';


import catalogDe from './locales/de/catalog.json';
import storefrontDe from './locales/de/storefront.json';
import landingsDe from './locales/de/landings.json';
import customerAuthDe from './locales/de/customer_auth.json';
import customerPortalDe from './locales/de/customer_portal.json';
import legalDe from './locales/de/legal.json';

import commonFr from './locales/fr/common.json';
import authFr from './locales/fr/auth.json';
import prelaunchFr from './locales/fr/prelaunch.json';
// PL17 — restano sincroni: usati dai banner billing/paywall EAGER
import settingsFr from './locales/fr/settings.json';
import modulesPageFr from './locales/fr/modules_page.json';


import catalogFr from './locales/fr/catalog.json';
import storefrontFr from './locales/fr/storefront.json';
import landingsFr from './locales/fr/landings.json';
import customerAuthFr from './locales/fr/customer_auth.json';
import customerPortalFr from './locales/fr/customer_portal.json';
import legalFr from './locales/fr/legal.json';

// ── Supported languages ─────────────────────────────────────────────────────
export const SUPPORTED_LANGUAGES = [
  { code: 'it', label: 'Italiano', flag: '🇮🇹' },
  { code: 'en', label: 'English', flag: '🇬🇧' },
  { code: 'de', label: 'Deutsch', flag: '🇩🇪' },
  { code: 'fr', label: 'Français', flag: '🇫🇷' },
];

const SUPPORTED_CODES = ['it', 'en', 'de', 'fr'];

/**
 * Cold-start language detection — runs once before i18n.init().
 *
 * Architectural intent
 * --------------------
 * The full resolver chain (`useStorefrontLocale`) only runs once React
 * has mounted, the `StoreMetaContext` has resolved, and the relevant
 * effects fire. That's typically <100ms but produces a visible
 * "wrong-language" flash on the very first paint of any storefront
 * page until the resolver corrects to the merchant's configured value.
 *
 * This detector gives i18n a SMART INITIAL LANGUAGE before React even
 * boots, so the first paint already speaks the right language for
 * returning visitors. Detection is cheap and pure (no async, no
 * network) — anything more sophisticated is owned by the resolver
 * chain at runtime.
 *
 * Priority on STOREFRONT routes (URL has a slug):
 *   1. `localStorage[customer_lang_<slug>]`
 *      The visitor's previous explicit choice on this store. The
 *      resolver respects this at runtime (priority 3 in its chain)
 *      so applying it at boot causes zero flash.
 *   2. `localStorage[storefront_meta_<slug>]` → `storefront_languages[0]`
 *      The merchant's primary language, read from the warm meta
 *      cache. Matches the resolver's `storeDefault` priority (its
 *      level 4) so a returning visitor with no explicit choice still
 *      sees the correct language on first paint.
 *   3. null — i18next applies fallbackLng='it'. First-ever visitors
 *      to a non-Italian store will see a brief flash before the
 *      resolver corrects. Acceptable: the meta cache is populated
 *      after the first visit and step 2 covers all returners.
 *
 * Priority on NON-STOREFRONT routes (admin, customer portal, etc.):
 *   1. `navigator.language` — generic browser preference. Used here
 *      because admin/customer contexts override at runtime anyway,
 *      and a German admin visiting `/admin` on cold start is happier
 *      starting in DE than IT.
 *   2. null — fallbackLng='it'.
 *
 * Browser preference on storefront routes
 * ----------------------------------------
 * Intentionally NOT used as a cold-start hint for storefront URLs.
 * With the post-Step8 priority (storeDefault > browser), using
 * `navigator.language` here would mismatch the resolver in the common
 * case (German browser on Italian-primary store), producing a needless
 * DE→IT flash. The meta cache (step 2) carries the merchant's primary
 * for returners; first-ever visitors accept the brief fallback flash.
 *
 * Runtime contract
 * ----------------
 * Whatever this detector returns is JUST the BOOT value. The full
 * resolver (in `useStorefrontLocaleSync`) runs after mount and will
 * call `i18n.changeLanguage` with the authoritative value if it
 * differs. So a "wrong" initial value here at worst produces a
 * one-render correction, not a permanent error.
 */
function _detectColdStartLanguage() {
  if (typeof window === 'undefined') return null;

  // Match the public storefront routes that carry a slug in the URL:
  //   /s/:slug, /e/:slug/..., /p/:slug/..., /co/:slug/...,
  //   /r/:slug/..., /ph/:slug/..., /dg/:slug/...
  // Token routes (/t, /b, /d, /rsv) don't have the slug in the URL.
  let pathSlug = null;
  let inStoreCtx = false;
  let isMarketplaceRoute = false;
  try {
    const m = window.location.pathname.match(/^\/(?:s|e|p|co|r|ph|dg)\/([^/]+)/);
    if (m) pathSlug = m[1];
    // ?store=1 = guscio negozio (merchant-first); /s/ diretto idem.
    inStoreCtx = new URLSearchParams(window.location.search).get('store') === '1'
      || window.location.pathname.startsWith('/s/');
    // Superfici del marketplace senza slug nel path. Include la HOME
    // (splash/directory), le landing di pre-lancio e le pagine pubbliche:
    // sono la faccia della piattaforma → partono in ITALIANO (fallback),
    // mai nella lingua del browser; lo switcher è a un click e la scelta
    // viene ricordata (aurya_lang). Admin e portali restano browser-first.
    isMarketplaceRoute = /^\/(?:$|ritiri|o\/|account|operatori|destinazioni|esperienze|blog|chi-siamo|come-funziona|cerca-ritiro|per-operatori|privacy|termini)/.test(window.location.pathname);
  } catch {
    // pathname unavailable — fall through.
  }

  // ── L1 — preferenza lingua di marketplace (aurya_lang) ──────────
  // In contesto MARKETPLACE (directory, profili operatore, Passaporto,
  // landing raggiunte senza ?store=1) la scelta del viaggiatore vince
  // al boot, coerente con la priorità 2.5 del resolver runtime. In
  // contesto store resta la catena merchant-first qui sotto.
  if (!inStoreCtx && (isMarketplaceRoute || pathSlug) && typeof localStorage !== 'undefined') {
    try {
      const mktp = localStorage.getItem('aurya_lang');
      if (mktp) {
        const norm = String(mktp).toLowerCase().split('-')[0];
        if (SUPPORTED_CODES.includes(norm)) return norm;
      }
    } catch { /* ignore */ }
  }

  // Le superfici marketplace SENZA una scelta salvata partono in
  // italiano (fallbackLng), NON nella lingua del browser: è la faccia
  // della piattaforma, e lo switcher è a un click — la scelta viene
  // poi ricordata per sempre (aurya_lang).
  if (isMarketplaceRoute) return null;

  if (pathSlug && typeof localStorage !== 'undefined') {
    // 1. The visitor's most-recent explicit choice for THIS store.
    try {
      const stored = localStorage.getItem('customer_lang_' + pathSlug);
      if (stored) {
        const norm = String(stored).toLowerCase().split('-')[0];
        if (SUPPORTED_CODES.includes(norm)) return norm;
      }
    } catch { /* ignore */ }

    // 2. The merchant's primary language, from the warm meta cache.
    //    Mirrors StoreMetaContext's `readCachedMeta` shape on purpose:
    //    `{ version: 1, fetched_at: <ms>, data: { storefront_languages: [...] } }`.
    //    The 5-minute TTL matches StoreMetaContext.CACHE_TTL_MS — kept
    //    short so admin changes propagate fast even on cold start. The
    //    runtime SWR refresh corrects any further drift after mount.
    try {
      const raw = localStorage.getItem('storefront_meta_' + pathSlug);
      if (raw) {
        const parsed = JSON.parse(raw);
        if (
          parsed
          && parsed.version === 1
          && typeof parsed.fetched_at === 'number'
          && Date.now() - parsed.fetched_at <= 5 * 60 * 1000
          && parsed.data
          && Array.isArray(parsed.data.storefront_languages)
          && parsed.data.storefront_languages.length > 0
        ) {
          const primary = String(parsed.data.storefront_languages[0]).toLowerCase().split('-')[0];
          if (SUPPORTED_CODES.includes(primary)) return primary;
        }
      }
    } catch { /* corrupted JSON or storage unavailable — fall through */ }

    // No further fallbacks for storefront routes — let fallbackLng
    // apply, the resolver corrects after mount.
    return null;
  }

  // Non-storefront route: generic browser preference is fine because
  // admin/customer contexts will overwrite based on user.locale.
  try {
    const browser = String(navigator.language || '').toLowerCase().split('-')[0];
    if (SUPPORTED_CODES.includes(browser)) return browser;
  } catch { /* navigator unavailable */ }

  return null;
}

const COLD_START_LNG = _detectColdStartLanguage();

// ── Resources ───────────────────────────────────────────────────────────────
const resources = {

  it: { common: commonIt, auth: authIt, catalog: catalogIt, storefront: storefrontIt, landings: landingsIt, customer_auth: customerAuthIt, customer_portal: customerPortalIt, legal: legalIt, prelaunch: prelaunchIt, settings: settingsIt, modules_page: modulesPageIt },
  en: { common: commonEn, auth: authEn, catalog: catalogEn, storefront: storefrontEn, landings: landingsEn, customer_auth: customerAuthEn, customer_portal: customerPortalEn, legal: legalEn, prelaunch: prelaunchEn, settings: settingsEn, modules_page: modulesPageEn },
  de: { common: commonDe, auth: authDe, catalog: catalogDe, storefront: storefrontDe, landings: landingsDe, customer_auth: customerAuthDe, customer_portal: customerPortalDe, legal: legalDe, prelaunch: prelaunchDe, settings: settingsDe, modules_page: modulesPageDe },
  fr: { common: commonFr, auth: authFr, catalog: catalogFr, storefront: storefrontFr, landings: landingsFr, customer_auth: customerAuthFr, customer_portal: customerPortalFr, legal: legalFr, prelaunch: prelaunchFr, settings: settingsFr, modules_page: modulesPageFr },

};

// PL17 — qui vive SOLO il pubblico (landing, marketplace, portale
// cliente, legal, prelaunch). I 20 namespace del back-office sono in
// i18n-admin.js, caricato dal guscio Layout dentro i chunk lazy admin:
// ~307KB gzip fuori dal percorso del visitatore.
// ── Initialize ──────────────────────────────────────────────────────────────
i18n.use(initReactI18next).init({
  resources,
  // Smart initial language for storefront URLs (see _detectColdStartLanguage).
  // null/undefined → i18next falls back to fallbackLng. This is purely a
  // first-paint optimization; the resolver chain still owns the
  // authoritative locale at runtime.
  lng: COLD_START_LNG || undefined,
  fallbackLng: 'it',
  defaultNS: 'common',

  ns: ['common', 'auth', 'settings', 'dashboard', 'customers_light', 'customerInsights', 'team', 'modules_page', 'product_catalog', 'product_cost', 'products', 'entities', 'orders', 'catalog', 'calendar', 'data_integrity', 'store_settings', 'setup_wizard', 'stores', 'pos', 'reservations', 'storefront', 'landings', 'customer_auth', 'customer_portal', 'legal', 'newsletter', 'cashflow_monitor', 'prelaunch'],

  interpolation: {
    escapeValue: false, // React already escapes
  },
  react: {
    useSuspense: false, // Avoid Suspense boundary requirement
  },
});

// SEO3 — <html lang> sempre allineato alla lingua attiva: index.html parte
// da "it" (default), poi ogni cambio lingua aggiorna documentElement.lang
// così il crawler capisce in che lingua è la pagina (era hardcoded "en").
const _syncHtmlLang = (lng) => {
  try {
    document.documentElement.lang = (lng || 'it').slice(0, 2);
  } catch { /* no-DOM: no-op */ }
};
_syncHtmlLang(i18n.language);
i18n.on('languageChanged', _syncHtmlLang);

export default i18n;
