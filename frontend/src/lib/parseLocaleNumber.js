/**
 * Locale-tolerant numeric parser for manual entry forms.
 *
 * Mirrors backend/core/numeric.parse_locale_number() exactly so that
 * frontend and backend always agree on how to interpret user input.
 *
 * Rules:
 *   1. null / undefined / empty  → NaN
 *   2. Already a number          → passthrough
 *   3. Strip currency symbols ($€£¥₹) and whitespace
 *   4. If both , and . present:
 *      - rightmost is the decimal separator
 *      - "1.234,56" → 1234.56   "1,234.56" → 1234.56
 *   5. If only comma present:
 *      - ≤2 digits after comma → decimal  ("12,5" → 12.5)
 *      - 3+ digits after comma → thousands ("1,000" → 1000)
 *   6. Strip remaining non-numeric chars (except dot and minus)
 *   7. parseFloat; return NaN on failure
 *
 * @param {string|number|null|undefined} value
 * @returns {number} Parsed float, or NaN if unparseable
 */
export function parseLocaleNumber(value) {
  if (value == null) return NaN;
  if (typeof value === 'number') return value;

  let s = String(value).trim();
  if (!s) return NaN;

  // Strip currency symbols and all whitespace (incl. non-breaking space \u00a0)
  s = s.replace(/[$€£¥₹\s\u00a0]/g, '');

  if (s.includes(',') && s.includes('.')) {
    // Both separators: rightmost is the decimal separator
    if (s.lastIndexOf(',') > s.lastIndexOf('.')) {
      // European: "1.234,56" → remove dots, comma → dot
      s = s.replace(/\./g, '').replace(',', '.');
    } else {
      // US: "1,234.56" → remove commas
      s = s.replace(/,/g, '');
    }
  } else if (s.includes(',')) {
    const parts = s.split(',');
    if (parts.length === 2 && parts[1].length <= 2) {
      // Single comma with ≤2 decimal digits → decimal separator
      s = s.replace(',', '.');
    } else {
      // Thousands comma: "1,000" or "1,000,000"
      s = s.replace(/,/g, '');
    }
  }

  // Strip Swiss apostrophe and any remaining junk
  s = s.replace(/[^\d.\-]/g, '');

  const result = parseFloat(s);
  return isNaN(result) ? NaN : result;
}
