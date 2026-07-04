/**
 * @afianco/embed-sdk i18n — Track E Step 4.5.
 *
 * Lightweight i18n system custom (no dipendenze esterne) per minimizzare
 * bundle bloat. ~3KB overhead, lazy-load locale resources on demand.
 *
 * Pattern: dictionary key → string lookup con fallback chain:
 *   resolved_locale → 'it' (base) → key string itself (last resort)
 *
 * API:
 *   import { t, setLocale, getLocale } from './i18n';
 *   t('checkout.submit')              → "Procedi al pagamento"
 *   t('cart.item_count', { count: 3 }) → "3 articoli"
 *   setLocale('en')                    → switch + persist to localStorage
 *
 * I componenti Lit chiamano `t(key)` nei template — re-render automatico
 * via reactive event "afianco:locale-changed" che il `<afianco-storefront-init>`
 * intercetta + requestUpdate sui children.
 *
 * Persistence: localStorage[`afianco_lang_{slug}`] — per-slug per supportare
 * merchant multipli sulla stessa origin (esempio testing diversi store).
 *
 * Fallback resolution:
 *   1. User scelto via setLocale() o ?lang=xx URL param o <init lang="xx">
 *   2. localStorage[`afianco_lang_{slug}`]
 *   3. navigator.language matchato vs supported list
 *   4. 'it' (default baseline)
 */

import { it } from './locales/it.js';
import { en } from './locales/en.js';
// Sprint 4 W4.1+W4.2 — Lingue DE + FR (parity React storefront 4 lingue)
import { de } from './locales/de.js';
import { fr } from './locales/fr.js';

// Tutti i locale dictionaries supportati (extendable: aggiungi import + entry)
const LOCALES: Record<string, Record<string, string>> = {
  it,
  en,
  de,
  fr,
};

let currentLocale = 'it';

/**
 * Get currently active locale code (es. 'it', 'en').
 */
export function getLocale(): string {
  return currentLocale;
}

/**
 * Set active locale. Triggers document-level event for components to
 * re-render. Persist on localStorage scoped per slug.
 *
 * Returns true if locale supported, false otherwise (no-op).
 */
export function setLocale(locale: string, opts: { slug?: string; silent?: boolean } = {}): boolean {
  if (!LOCALES[locale]) return false;
  if (locale === currentLocale && !opts.silent) return true;
  currentLocale = locale;
  // Persist (best-effort)
  if (opts.slug && typeof localStorage !== 'undefined') {
    try {
      localStorage.setItem(`afianco_lang_${opts.slug}`, locale);
    } catch {
      // ignore quota / private mode
    }
  }
  // Notify components for re-render
  if (typeof document !== 'undefined' && !opts.silent) {
    document.dispatchEvent(
      new CustomEvent('afianco:locale-changed', {
        detail: { locale },
        bubbles: true,
        composed: true,
      }),
    );
  }
  return true;
}

/**
 * Translate a key. Supports nested paths via dot notation.
 *
 * Optional `params` for interpolation: t('cart.item_count', { count: 3 })
 * replaces {{count}} with 3 in the resolved string.
 *
 * Fallback chain: current locale → 'it' (base) → key (visible debug).
 */
export function t(key: string, params?: Record<string, string | number>): string {
  const dict = LOCALES[currentLocale] ?? LOCALES.it;
  const fallback = LOCALES.it;
  // Nested lookup not supported per snippet; tutte le key sono flat (es. "checkout.submit")
  let val = dict?.[key] ?? fallback?.[key] ?? key;
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      val = val.replace(new RegExp(`{{\\s*${k}\\s*}}`, 'g'), String(v));
    }
  }
  return val;
}

/**
 * Initialize locale from URL param / localStorage / browser / store config.
 *
 * Called by <afianco-storefront-init> al mount con la lista delle lingue
 * supportate dal merchant (init.storefront_languages).
 */
export function initLocale(opts: {
  slug: string;
  supportedLanguages: string[];
  explicitLang?: string | null;
}): string {
  const supported = opts.supportedLanguages ?? ['it'];

  // W4.4 — Soft cleanup localStorage stale.
  //
  // Bug fix: pre-W4.4 il localStorage era "sticky" anche per lingue
  // RIMOSSE dal merchant. Scenario:
  //   1. Merchant supporta ['it', 'de']
  //   2. Customer sceglie 'de' -> localStorage[afianco_lang_acme] = 'de'
  //   3. Merchant rimuove 'de' (ora supporta solo ['it'])
  //   4. Pre-W4.4: customer continuava a vedere 'de' (cached) ma key
  //      i18n caderebbero in fallback rendering misto.
  //   5. W4.4 fix: cleanup localStorage SE la lingua cached non e' piu'
  //      supportata. Prossimo init() applica il default merchant.
  //
  // Anche W4.4 ne approfitta per supportare il caso opposto (merchant
  // CAMBIA storefront_languages[0] da 'it' a 'de'): customer senza
  // explicit choice vede automaticamente la nuova lingua default.
  if (typeof localStorage !== 'undefined') {
    try {
      const stored = localStorage.getItem(`afianco_lang_${opts.slug}`);
      if (stored && (!supported.includes(stored) || !LOCALES[stored])) {
        // Lingua cached NON piu' supportata -> cleanup
        localStorage.removeItem(`afianco_lang_${opts.slug}`);
      }
    } catch {
      // ignore
    }
  }

  // W4.4 — Force re-apply current locale se cambiato esternamente.
  // Quando il widget re-fetcha init() (visibilitychange) e il merchant
  // ha rimosso la lingua corrente, dobbiamo forzare un cambio + dispatch
  // event cosi' tutti i componenti re-render con i18n aggiornato.
  const currentNoLongerSupported =
    currentLocale && !supported.includes(currentLocale);

  // 1. Explicit prop / URL param
  if (opts.explicitLang && supported.includes(opts.explicitLang) && LOCALES[opts.explicitLang]) {
    // Force=true se la lingua corrente non e' piu' supportata
    setLocale(opts.explicitLang, {
      slug: opts.slug,
      silent: !currentNoLongerSupported,
    });
    return opts.explicitLang;
  }
  // 2. URL ?lang query
  if (typeof window !== 'undefined') {
    const urlLang = new URLSearchParams(window.location.search).get('lang');
    if (urlLang && supported.includes(urlLang) && LOCALES[urlLang]) {
      setLocale(urlLang, { slug: opts.slug, silent: !currentNoLongerSupported });
      return urlLang;
    }
  }
  // 3. localStorage persisted (post-cleanup)
  if (typeof localStorage !== 'undefined') {
    try {
      const stored = localStorage.getItem(`afianco_lang_${opts.slug}`);
      if (stored && supported.includes(stored) && LOCALES[stored]) {
        setLocale(stored, { slug: opts.slug, silent: !currentNoLongerSupported });
        return stored;
      }
    } catch {
      // ignore
    }
  }
  // 4. Browser language
  if (typeof navigator !== 'undefined') {
    const browserLang = (navigator.language || '').slice(0, 2).toLowerCase();
    if (browserLang && supported.includes(browserLang) && LOCALES[browserLang]) {
      setLocale(browserLang, { slug: opts.slug, silent: !currentNoLongerSupported });
      return browserLang;
    }
  }
  // 5. Fallback to first supported (tipicamente 'it' o lingua merchant default)
  // W4.4 — dispatch event (silent=false) se lingua corrente cambia per
  // forzare re-render dei componenti consumer.
  const fallback = supported[0] ?? 'it';
  setLocale(LOCALES[fallback] ? fallback : 'it', {
    slug: opts.slug,
    silent: !currentNoLongerSupported,
  });
  return currentLocale;
}

/**
 * Get list of all supported locale codes (for language switcher rendering).
 */
export function getSupportedLocales(): string[] {
  return Object.keys(LOCALES);
}
