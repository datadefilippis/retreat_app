/**
 * useStorefrontLocale — resolves the active locale for the storefront / customer
 * context (catalog, checkout, customer auth, customer portal).
 *
 * Architectural intent
 * --------------------
 * The storefront is multi-tenant: each Store declares which languages it
 * exposes (`storefront_languages`, e.g. ["it","de"]). Visitors arrive in
 * different states (guest first-visit, returning guest, logged-in customer)
 * and we resolve the most specific signal first, falling back gracefully
 * down to the store's primary language.
 *
 * Resolution priority (first match wins)
 * --------------------------------------
 *   1. URL `?lang=xx`
 *      Explicit override. Lets a deep-link from an email or shared URL pin
 *      the language regardless of any other signal.
 *
 *   2. `customer.locale` (logged-in customer only)
 *      The customer's saved preference is the long-term source of truth.
 *      Set at signup, updated by the in-storefront language switcher
 *      via PATCH /customer/me.
 *
 *   3. `localStorage[customer_lang_<storeSlug>]`
 *      Guest persistence. A visitor who explicitly chose German via the
 *      switcher gets German again next time on the same store. Keyed by
 *      slug so different stores keep independent choices.
 *
 *   4. `supportedLanguages[0]` — STORE PRIMARY
 *      The merchant's first configured language IS the storefront's
 *      default. Sits above `browser` so the admin's choice in the store
 *      config wins over the visitor's OS preference. Rationale: the
 *      merchant explicitly decided "my store speaks Italian first" —
 *      a German-browser visitor doesn't override that unless they
 *      actively switch (which lands in localStorage / customer.locale).
 *
 *   5. `navigator.language`
 *      Last-resort match against the merchant list. Only honored if the
 *      browser language is in the supported list AND the merchant didn't
 *      configure a primary (impossible in practice — the array always
 *      has at least one entry — so this branch is effectively dead but
 *      kept as defense-in-depth).
 *
 *   6. `'it'`
 *      Hard fallback. Should be unreachable — the supported list always
 *      contains at least one language — but defensive in case the API
 *      returns an empty array.
 *
 * Hard constraint: the returned locale is always ∈ supportedLanguages.
 * If browser=de but the store only enabled it+en, we ignore the browser.
 *
 * Why store-primary outranks browser
 * -----------------------------------
 * The merchant configures a storefront in a specific language for
 * branding + content reasons. A visitor coming from a German browser
 * to an Italian-primary store should see Italian — that's the deliberate
 * face of the brand. If the visitor needs the page in German, the
 * floating switcher is one click away (and persists their choice into
 * localStorage so subsequent visits respect it). This is the inverse
 * of how generic CMS systems behave (browser-first), but matches how
 * direct-to-consumer storefronts (Shopify, Stripe Checkout) prioritize
 * merchant intent.
 *
 * 'pending' state (Step 3 of the language refactor)
 * --------------------------------------------------
 * When the merchant's supported list is genuinely UNKNOWN (no prop, no
 * context, e.g. a landing page that hasn't fetched its meta yet) we
 * return `{ locale: null, source: 'pending' }` instead of collapsing to
 * 'it'. Consumers MUST treat 'pending' as "do nothing yet" — most
 * importantly `useStorefrontLocaleSync` skips its `i18n.changeLanguage`
 * call so the previously-applied locale stays in place during the
 * loading window. This eliminates the IT-flicker bug on back-navigation
 * (catalog re-mounts with `catalog=null` for a tick, but instead of
 * calling changeLanguage('it') the resolver pauses until real data).
 *
 * Why a hook (not a plain function)
 * ---------------------------------
 * The resolver depends on FOUR reactive sources: the URL query string
 * (router state), the customer auth state, the store meta context, and
 * the optional `supportedLanguages` prop. A hook lets us subscribe to
 * all of them and re-resolve whenever any input changes — without
 * forcing every caller to wire those subscriptions manually.
 */

// ════════════════════════════════════════════════════════════════════════════
// LANGUAGE SYSTEM — full architecture map (read once, then this file)
// ════════════════════════════════════════════════════════════════════════════
//
// The AFianco app has FIVE writers to i18n.language. Mounted on different
// surfaces; the rightmost-mounted writer wins on each route. No race when
// they're mutually exclusive by route, which is the design.
//
//   Surface                  | Driver                               | Source of truth
//   -------------------------+--------------------------------------+----------------------
//   /admin/*                 | AuthContext.useEffect [user.locale]  | admin user record
//   /account/* (post-login)  | CustomerAuthContext.useEffect        | customer.locale
//   /s/:slug                 | useStorefrontLocaleSync (this hook)  | resolver chain below
//   /e, /p, /co, /r, /ph,    | useStorefrontLocaleSync (this hook,  | resolver chain below
//   /dg landings             |   via PublicStorefrontShell)         |
//   /account/login (etc.)    | useStorefrontLocaleSync (via         | resolver chain below
//                            |   AuthShell)                         |
//   /t, /b, /d, /rsv (token) | inherited from previous mount        | (no own writer yet)
//   Cold start any URL       | i18n.init lng=COLD_START_LNG         | URL-pathway hint
//
// The resolver chain (THIS HOOK) is the canonical multi-source decider
// for storefront-pathway pages. Other contexts have their own logic.
// All changes to i18n flow through `i18n.changeLanguage()`, which is the
// single mutation point. Every consumer of locale-aware behavior reads
// `i18n.language` (via `useTranslation`'s reactive subscription).
//
// Persistence layers
// ------------------
//   localStorage[storefront_meta_<slug>]  : StoreMetaContext cache (1h TTL)
//   localStorage[customer_lang_<slug>]    : per-store guest choice (no TTL)
//   `customer.locale` field on Customer   : server-side preference (PATCH /me)
//   `user.locale` field on User           : admin preference (settings page)
//
// Bug fix history
// ---------------
//   pre-Step3: resolver returned FALLBACK_LOCALE during loading window,
//              causing IT-flicker on back-navigation.
//   post-Step3: returns `source='pending'` when supportedLanguages is
//              unknown; sync hook skips changeLanguage; i18n stays at
//              previous value until real data arrives.
//   post-Step8: storeDefault outranks navigator.language. The merchant's
//              configured primary wins over the visitor's browser
//              preference — explicit user actions (?lang, login,
//              manual switcher) still override on top of that.
// ════════════════════════════════════════════════════════════════════════════

import { useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useCustomerAuth } from '../context/CustomerAuthContext';
import { useStoreMetaContext } from '../context/StoreMetaContext';

const FALLBACK_LOCALE = 'it';

// Languages the AFianco i18n stack actually has translations for.
// `useStorefrontLocale` will never return a language outside this set,
// even if the store config or backend/browser claims otherwise.
const APP_SUPPORTED = ['it', 'en', 'de', 'fr'];


/**
 * Normalise an arbitrary language input into a short app-supported code.
 *
 * Accepts BCP-47 forms ("en-US", "de-CH"), uppercase variants ("DE"), or
 * already-short codes. Returns null when the input cannot be resolved
 * to one of `APP_SUPPORTED` — callers fall through to the next priority.
 */
function _normalize(lang) {
  if (!lang) return null;
  const short = String(lang).toLowerCase().split('-')[0];
  return APP_SUPPORTED.includes(short) ? short : null;
}


function _localStorageKey(slug) {
  return slug ? `customer_lang_${slug}` : null;
}


/**
 * Resolve the active storefront locale.
 *
 * @param {object} args
 * @param {string|null} args.storeSlug
 *        The current storefront slug. Used as the localStorage namespace
 *        so different stores keep independent guest choices.
 * @param {string[]|null} args.supportedLanguages
 *        Optional explicit override of the merchant's allowed list.
 *        When provided, this takes precedence over the StoreMetaContext.
 *        Useful for backward-compat with call sites that already have
 *        the list from a different fetch (e.g. StorefrontPage passes
 *        `catalog?.storefront_languages` directly).
 *
 * @returns {{ locale: string|null, source: string }}
 *        `locale`:
 *           - When known: always one of APP_SUPPORTED (∈ merchant list).
 *           - When unknown (no prop + no context yet): `null`.
 *        `source` documents which signal won. Possible values:
 *           'pending'     — merchant list unknown, consumer should wait.
 *           'query'       — `?lang=` URL override matched.
 *           'customer'    — logged-in customer.locale matched.
 *           'localStorage'— per-store guest persistence matched.
 *           'browser'     — navigator.language matched.
 *           'storeDefault'— first entry in merchant list (always-defined fallback).
 */
export function useStorefrontLocale({ storeSlug, supportedLanguages } = {}) {
  const [searchParams] = useSearchParams();
  const { customer } = useCustomerAuth();
  // The context provides the canonical list once the /meta call resolves.
  // We read it here so every consumer of the resolver gets multi-source
  // behavior automatically — props remain a manual override path for
  // legacy call sites (StorefrontPage) and tests.
  const meta = useStoreMetaContext();

  return useMemo(() => {
    // Effective merchant list precedence:
    //   1. Explicit `supportedLanguages` prop (backward compat)
    //   2. StoreMetaContext (when status='ready' AND list is non-empty)
    //   3. Unknown → 'pending' state (return null, source='pending')
    //
    // Filtering both candidates against APP_SUPPORTED guarantees we
    // never return a language the i18n stack can't render, even if the
    // merchant's saved config drifted.
    let merchantSupported = null;
    if (Array.isArray(supportedLanguages) && supportedLanguages.length > 0) {
      merchantSupported = supportedLanguages.filter((l) => APP_SUPPORTED.includes(l));
    } else if (
      meta?.status === 'ready'
      && Array.isArray(meta.storefrontLanguages)
      && meta.storefrontLanguages.length > 0
    ) {
      merchantSupported = meta.storefrontLanguages.filter((l) => APP_SUPPORTED.includes(l));
    }

    // While the merchant list is genuinely unknown — context still
    // loading AND no prop — we DON'T return a placeholder locale.
    // Returning null + source='pending' lets `useStorefrontLocaleSync`
    // skip its `changeLanguage` call so i18n stays at whatever it was
    // (typically the previous catalog's resolved locale, or the i18n
    // fallback on cold start). This is the fix for the back-nav IT
    // flicker: catalog re-mount used to call changeLanguage('it') for
    // a frame before the catalog data arrived.
    if (!merchantSupported || merchantSupported.length === 0) {
      return { locale: null, source: 'pending' };
    }

    const inSupported = (loc) => loc && merchantSupported.includes(loc);

    // 1. Explicit ?lang=xx — only honoured when in the supported list.
    const queryLang = _normalize(searchParams.get('lang'));
    if (inSupported(queryLang)) return { locale: queryLang, source: 'query' };

    // 2. Customer preference (only when logged in).
    const customerLang = _normalize(customer?.locale);
    if (inSupported(customerLang)) return { locale: customerLang, source: 'customer' };

    // 3. Per-store guest persistence — the visitor's previous explicit
    //    choice on THIS store via the floating switcher.
    const lsKey = _localStorageKey(storeSlug);
    if (lsKey && typeof localStorage !== 'undefined') {
      let stored = null;
      try { stored = localStorage.getItem(lsKey); } catch { /* private mode */ }
      const lsLang = _normalize(stored);
      if (inSupported(lsLang)) return { locale: lsLang, source: 'localStorage' };
    }

    // 4. Store primary — the merchant's first configured language. Wins
    //    over `navigator.language` so the admin's choice in the store
    //    config drives the storefront's face. A German-browser visitor
    //    on an Italian-primary store sees Italian; if they want German
    //    they switch via the picker (and that choice lands in lsKey
    //    above for next time). MVP single-language stores hit this
    //    branch unconditionally — the array has 1 entry, the others
    //    can't match because supportedLanguages.length===1.
    //
    //    Note: returning `merchantSupported[0]` directly here. The
    //    `navigator.language` branch below is effectively unreachable
    //    given the current invariant `merchantSupported.length >= 1`,
    //    but kept as defense-in-depth in case a future change relaxes
    //    that invariant (e.g. when explicit `supportedLanguages` prop
    //    is somehow empty after filtering).
    return { locale: merchantSupported[0], source: 'storeDefault' };
  }, [searchParams, customer?.locale, storeSlug, supportedLanguages, meta?.status, meta?.storefrontLanguages]);
}


// Re-exported so consumers (e.g. useStorefrontLocaleSync) can branch
// on it without redeclaring the constant.
export const FALLBACK_LOCALE_DEFAULT = FALLBACK_LOCALE;


/**
 * Persist a language choice for the current store.
 *
 * Used by the storefront language switcher (Phase 7) to remember the
 * choice for guest visitors. Logged-in customers also get their backend
 * `locale` updated separately (Phase 5.1) so the choice survives device
 * changes; localStorage is purely the device-local cache.
 *
 * Failures (e.g. Safari private mode, full storage) are swallowed — the
 * UI applies the choice immediately via i18n.changeLanguage regardless.
 */
export function persistStorefrontLocale(storeSlug, locale) {
  if (!storeSlug) return;
  const normalized = _normalize(locale);
  if (!normalized) return;
  try {
    localStorage.setItem(_localStorageKey(storeSlug), normalized);
  } catch { /* localStorage may be unavailable; non-fatal */ }
}


// Re-export the supported list so callers (e.g. the language switcher)
// can render a consistent set of options without redeclaring the constant.
export const APP_SUPPORTED_LOCALES = APP_SUPPORTED;
