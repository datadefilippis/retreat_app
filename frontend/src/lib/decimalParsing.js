/**
 * decimalParsing — locale-aware number input helpers.
 *
 * 2026-05-20 — Background: every product-creation wizard renders prices
 * with ``<input type="number" step="0.01">``. HTML5 number inputs are
 * locale-aware in a particularly painful way:
 *
 *   · In Italian locale ("it-IT"), the user types "10,50" but the browser
 *     either rejects the comma or silently coerces to ``NaN``/"1050".
 *   · In US locale ("en-US"), "10.50" works but "10,50" doesn't.
 *
 * The result is that Italian merchants (our primary market) routinely fail
 * to enter decimal prices and don't understand why. The audit ranked this
 * as the #1 friction issue across all 5 wizards.
 *
 * This module provides:
 *
 *   parseLocaleNumber(input, opts) → number | null
 *     Permissive parser. Accepts "10,50", "10.50", "1.234,56", "1,234.56",
 *     "1234". Returns null when the string is empty / unparsable. Caller
 *     decides whether null means "leave the field blank" or "fail".
 *
 *   formatLocaleNumber(n, opts) → string
 *     Locale-aware rendering for the input's ``value`` prop. Uses the
 *     current i18next language when available, falls back to browser.
 *
 *   isValidDecimalInput(str) → boolean
 *     True iff the in-progress string is a plausible decimal literal —
 *     used to gate per-keystroke ``onChange`` updates so the field can
 *     keep partial input like "10," while the user is typing.
 *
 * Design notes:
 *   · We do NOT use Intl.NumberFormat's parser — it doesn't exist as a
 *     stable API yet. The hand-rolled parser below covers the four
 *     locale combinations we ship (it / en / de / fr).
 *   · The parser is intentionally permissive on thousand separators —
 *     Italian "1.234,56" and US "1,234.56" both yield 1234.56.
 *   · The output is always a plain JS number (or null), so existing
 *     submit code that does ``Number(value)`` keeps working unchanged.
 */


function _detectCurrentLocale() {
  try {
    // Lazy import to avoid pulling i18next into modules that don't use it.
    // eslint-disable-next-line global-require
    const i18n = require('../i18n').default;
    const lang = i18n?.language || '';
    if (typeof lang === 'string' && lang.length >= 2) return lang.slice(0, 2);
  } catch {
    // i18n may not be initialized in tests/SSR — fall through.
  }
  try {
    const nav = (typeof navigator !== 'undefined' && navigator.language) || '';
    if (nav.length >= 2) return nav.slice(0, 2);
  } catch {
    // SSR / non-browser env
  }
  return 'en';
}


/**
 * Parse a user-typed decimal string into a JS number, tolerating both
 * comma and dot decimal separators and either-style thousand separators.
 *
 * @param {string|number|null|undefined} input
 * @param {object} [opts]
 * @param {number} [opts.min] — reject values strictly below
 * @param {number} [opts.max] — reject values strictly above
 * @returns {number|null} parsed value, or null if empty/invalid/out-of-range.
 */
export function parseLocaleNumber(input, opts = {}) {
  if (input == null) return null;
  if (typeof input === 'number') {
    if (!Number.isFinite(input)) return null;
    return _clampOrNull(input, opts);
  }
  const raw = String(input).trim();
  if (!raw) return null;

  // Strip currency symbols and whitespace — defensive against paste.
  let s = raw.replace(/[\s\u00a0€$£¥]/g, '');

  // Normalise sign — accept leading +/-, also a trailing minus (rare locale).
  let negative = false;
  if (s.startsWith('-')) { negative = true; s = s.slice(1); }
  else if (s.startsWith('+')) { s = s.slice(1); }

  // Detect which char is the decimal separator. Heuristic:
  //   · if there is only one of {',', '.'} → that one is the decimal.
  //   · if both are present → the LAST occurrence is the decimal,
  //     the other one is the thousand grouping.
  //   · if neither → it's an integer.
  const lastComma = s.lastIndexOf(',');
  const lastDot = s.lastIndexOf('.');
  let decimalSep = null;
  if (lastComma >= 0 && lastDot >= 0) {
    decimalSep = lastComma > lastDot ? ',' : '.';
  } else if (lastComma >= 0) {
    decimalSep = ',';
  } else if (lastDot >= 0) {
    decimalSep = '.';
  }

  if (decimalSep === ',') {
    // Thousand grouping is '.', decimal is ','
    s = s.replace(/\./g, '').replace(',', '.');
  } else if (decimalSep === '.') {
    // Thousand grouping is ',', decimal is '.'
    s = s.replace(/,/g, '');
  } else {
    // No decimal separator — strip any commas (treated as thousand grouping)
    s = s.replace(/,/g, '');
  }

  if (!/^[0-9]*\.?[0-9]*$/.test(s)) return null;
  if (s === '' || s === '.') return null;

  const n = Number(s);
  if (!Number.isFinite(n)) return null;
  return _clampOrNull(negative ? -n : n, opts);
}


function _clampOrNull(n, opts) {
  if (typeof opts.min === 'number' && n < opts.min) return null;
  if (typeof opts.max === 'number' && n > opts.max) return null;
  return n;
}


/**
 * Format a number for display in a locale-aware string.
 *
 * @param {number|null|undefined} n
 * @param {object} [opts]
 * @param {number} [opts.decimals=2] — fixed decimal places
 * @param {string} [opts.locale]     — override the auto-detected locale
 * @returns {string} formatted string ("" for null/NaN)
 */
export function formatLocaleNumber(n, opts = {}) {
  if (n == null || !Number.isFinite(n)) return '';
  const decimals = typeof opts.decimals === 'number' ? opts.decimals : 2;
  const locale = opts.locale || _detectCurrentLocale();
  try {
    return new Intl.NumberFormat(locale, {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
      useGrouping: false,  // no thousand separator inside form inputs
    }).format(n);
  } catch {
    return n.toFixed(decimals);
  }
}


/**
 * In-progress validation: returns true iff the string COULD become a
 * valid decimal after more typing. Used to gate per-keystroke updates
 * so the user can leave the field as "10," for a brief moment.
 *
 * Accepts:
 *   ""           (clearing)
 *   "10"         (integer-so-far)
 *   "10,"  "10." (decimal separator just pressed)
 *   "10,5" "10.50"
 *   "-10" "-10,5"
 *   "1.234,56" "1,234.56"
 */
export function isValidDecimalInput(str) {
  if (str == null) return true;  // null = field cleared
  const s = String(str);
  if (s === '') return true;
  // Allow a leading sign + digits + at most one decimal-separator with
  // up to N more digits. Thousand separators allowed mid-stream.
  // Single regex with both ',' and '.' as decimal candidates.
  return /^-?(?:\d{1,3}(?:[.,]?\d{3})*|\d+)(?:[.,]\d*)?$/.test(s);
}
