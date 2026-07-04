import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import { formatAmount } from "../utils/currency";

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

/**
 * Format a numeric amount as currency for display.
 *
 * CH compliance v1: CHF always uses the Swiss convention
 * ("CHF 1'234.50") regardless of the UI locale, matching the backend
 * formatter and the PDF receipt. EUR preserves the previous behaviour
 * (it-IT, no decimals) so the 21 existing callers across the dashboard
 * remain visually identical — change the third argument explicitly to
 * opt into a different locale.
 *
 * @param {number} amount
 * @param {string} [currency="EUR"]
 * @param {string} [locale="it-IT"] - BCP-47 tag. Only used for EUR.
 */
export function formatCurrency(amount, currency = 'EUR', locale = 'it-IT') {
  if (String(currency || '').toUpperCase() === 'CHF') {
    // Swiss formatting (apostrophe thousands, dot decimals, two decimals).
    // Delegated to the shared formatter so the storefront, the email and
    // the PDF all read the same.
    return formatAmount(amount, 'CHF');
  }
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(amount);
}

/** Get the narrow symbol for a currency code (e.g. "EUR" → "€", "USD" → "$"). */
export function getCurrencySymbol(currency = 'EUR') {
  if (String(currency || '').toUpperCase() === 'CHF') {
    // Swiss convention prefers the ISO code as the symbol.
    return 'CHF';
  }
  try {
    return new Intl.NumberFormat('it-IT', {
      style: 'currency',
      currency,
      currencyDisplay: 'narrowSymbol',
    }).formatToParts(0)
      .find(p => p.type === 'currency')?.value || currency;
  } catch {
    return currency;
  }
}

/** Chart axis tick formatter: "€12k" / "CHF 12k" / "$12k". */
export function chartTickFormatter(value, currency = 'EUR') {
  const sym = getCurrencySymbol(currency);
  // Insert a space between the ISO code and the digits when the symbol
  // is the code itself (CHF, USD when narrowSymbol is unavailable) to
  // avoid the cramped "CHF12k" look.
  const sep = sym.length > 1 ? ' ' : '';
  return `${sym}${sep}${(value / 1000).toFixed(0)}k`;
}

export function formatNumber(num) {
  return new Intl.NumberFormat('it-IT').format(num);
}

export function formatPercent(num) {
  const sign = num >= 0 ? '+' : '';
  return `${sign}${num.toFixed(1)}%`;
}

export function formatDate(dateString) {
  return new Date(dateString).toLocaleDateString('it-IT', {
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  });
}

export function formatShortDate(dateString) {
  return new Date(dateString).toLocaleDateString('it-IT', {
    month: 'short',
    day: 'numeric'
  });
}

export function getDateRange(period) {
  const today = new Date();
  const end = today.toISOString().split('T')[0];

  let days;
  switch (period) {
    case '7d':
      days = 7;
      break;
    case '30d':
      days = 30;
      break;
    case '90d':
      days = 90;
      break;
    default:
      days = 30;
  }

  const start = new Date(today);
  start.setDate(start.getDate() - days + 1);

  return {
    start: start.toISOString().split('T')[0],
    end
  };
}

/**
 * Compute start/end dates for semantic period values (YTD, MTD).
 * Returns { start, end } in ISO format or null for preset periods.
 */
export function computePeriodDates(period) {
  const today = new Date();
  // Use local-timezone date formatting to avoid UTC shift
  // (toISOString() converts to UTC, which shifts dates back 1 day in UTC+N timezones)
  const pad = (n) => String(n).padStart(2, '0');
  const toLocal = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  switch (period) {
    case 'ytd':
      return { start: `${today.getFullYear()}-01-01`, end: toLocal(today) };
    case 'mtd':
      return { start: `${today.getFullYear()}-${pad(today.getMonth() + 1)}-01`, end: toLocal(today) };
    default:
      return null;
  }
}

/** Check if a period value requires custom date range */
export function periodNeedsCustomDates(period) {
  return ['data_range', 'ytd', 'mtd', 'custom'].includes(period);
}
