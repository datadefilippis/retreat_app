/**
 * Currency formatting for the in-browser UI.
 *
 * Mirrors `backend/core/currency_format.py` so that an amount displayed
 * on a checkout button matches the same amount printed on the PDF
 * receipt — the merchant or the customer should never see CHF 49.50 on
 * one screen and "49,50 CHF" on another.
 *
 * Implementation note: we use `Intl.NumberFormat` for locale-aware
 * grouping/decimals, then post-process so the layout matches the
 * server: ISO code prefix for CHF (`CHF 49.50`), euro glyph + space
 * for EUR (`€ 49,50`).
 *
 * @module utils/currency
 */

import { SUPPORTED_CURRENCIES, DEFAULT_CURRENCY } from '../constants/currencies';

/**
 * Format a numeric amount for display.
 *
 * @param {number|string} amount - The numeric value (already in major units, eg. 49.50 not 4950).
 * @param {string} [currency="EUR"] - ISO 4217 code (case-insensitive).
 * @param {string} [locale="it"] - Short language code; region suffixes tolerated.
 * @returns {string} Display-ready string, eg. "CHF 49.50" or "€ 49,50".
 */
export function formatAmount(amount, currency = DEFAULT_CURRENCY, locale = 'it') {
  const num = typeof amount === 'number' ? amount : Number(amount);
  if (!Number.isFinite(num)) {
    // Defensive: never render NaN. Show a plain zero so the UI stays usable.
    return formatAmount(0, currency, locale);
  }

  const code = String(currency || '').toUpperCase();
  const isNegative = num < 0;
  const absNum = Math.abs(num);

  if (code === 'CHF') {
    // Apostrophe thousands, dot decimals, two decimals always.
    // The /g flag is essential — without it, only the *first* group of
    // three digits gets a separator, so 1234567.89 would render as
    // "1'234567.89" (silently wrong above 999'999). Verified against
    // the backend snapshot: format_amount(1234567.89, "CHF") →
    // "CHF 1'234'567.89".
    const [intPart, decPart] = absNum.toFixed(2).split('.');
    const grouped = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, "'");
    return `${isNegative ? '-' : ''}CHF ${grouped}.${decPart}`;
  }

  if (code === 'EUR') {
    // it / de / fr: dot thousands, comma decimal. en: comma thousands, dot decimal.
    const useEuropean = !String(locale).startsWith('en');
    if (useEuropean) {
      const [intPart, decPart] = absNum.toFixed(2).split('.');
      const grouped = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
      return `${isNegative ? '-' : ''}\u20ac ${grouped},${decPart}`;
    }
    const [intPart, decPart] = absNum.toFixed(2).split('.');
    const grouped = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    return `${isNegative ? '-' : ''}\u20ac ${grouped}.${decPart}`;
  }

  // Defensive fallback for unexpected codes: ISO + European style.
  const [intPart, decPart] = absNum.toFixed(2).split('.');
  const grouped = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  return `${isNegative ? '-' : ''}${code} ${grouped},${decPart}`;
}

/**
 * Short symbol for inline use (eg. inside a placeholder).
 *
 * @param {string} currency
 * @returns {string} "€" for EUR, "CHF" for everything else (including unknowns).
 */
export function currencySymbol(currency) {
  return String(currency || '').toUpperCase() === 'EUR' ? '\u20ac' : 'CHF';
}

/**
 * Whether the given ISO code is one we currently ship.
 *
 * @param {string} currency
 * @returns {boolean}
 */
export function isSupportedCurrency(currency) {
  return SUPPORTED_CURRENCIES.includes(String(currency || '').toUpperCase());
}
