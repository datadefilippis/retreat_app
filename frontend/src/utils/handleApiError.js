/**
 * handleApiError — central helper for showing API error toasts that respects
 * the global paywall/banner system.
 *
 * v5.8 / Onda 9.O — Background:
 *   The Axios interceptor (api/client.js) dispatches global events for
 *   billing-related errors (QUOTA_EXCEEDED, MODULE_NOT_AVAILABLE,
 *   FEATURE_NOT_AVAILABLE, READ_ONLY_GRACE, BILLING_TRIAL_EXPIRED,
 *   BILLING_PAST_DUE) and tags the error as `__handled_by_paywall = true`.
 *   Global components (<QuotaExceededPaywall>, <ModuleAccessPaywall>,
 *   <BillingStatusBanner>, <ReadOnlyGraceBanner>) listen for these events
 *   and show explanatory modals/banners with localized copy + upgrade CTAs.
 *
 *   WITHOUT this helper, every per-component catch was doing
 *   `toast.error(detail.message)` which:
 *     1. Showed the backend's Italian-only message (no i18n)
 *     2. Covered the global paywall visually
 *     3. Felt like a generic "error" instead of a "here's what to do"
 *
 *   WITH this helper, per-component catch blocks SKIP the toast entirely
 *   when the error has been picked up by a global paywall — letting the
 *   modal do its job. For non-billing errors, the toast still fires.
 *
 * USAGE:
 *
 *   import { handleApiError } from '../utils/handleApiError';
 *
 *   try {
 *     await api.post('/something');
 *   } catch (err) {
 *     handleApiError(err, t('something.error', 'Errore'), t);
 *   }
 *
 * The third argument `t` is optional — if omitted, falls back to the
 * raw backend message or the literal `fallback` string. Pass `t` whenever
 * you want fallback localization for non-billing errors too.
 */
import { toast } from 'sonner';

// 2026-05-20 — Pydantic v2 / FastAPI 422 ValidationError support.
// Mirrors the logic in lib/smartToastInit.js so callers that use this
// helper (instead of raw toast.error) get the same protection.
import {
  isPydanticErrorArray,
  formatPydanticErrors,
} from '../lib/apiErrorFormatting';


/**
 * Show an error toast unless a global paywall has already handled the error.
 *
 * @param {Error} err - The error caught from an axios call.
 * @param {string} fallback - Default message to show if backend message
 *                            is missing or not localized (e.g. "Errore nella creazione del prodotto").
 * @param {function} [t] - Optional i18n t() function for further localization.
 *                         Currently used only to know if the caller cares about locale.
 */
export function handleApiError(err, fallback = 'Errore', /* eslint-disable-next-line no-unused-vars */ t = null) {
  // v5.8 / Onda 9.P — Defensive: skip toast if isPaywallHandled detects
  // a billing code (covers both interceptor-tagged and shape-matched cases).
  // Without this, a cache mismatch where new helper loaded but old
  // interceptor was running caused the user to see a generic toast
  // covering the paywall again.
  if (isPaywallHandled(err)) {
    return;
  }

  // Extract a user-facing message from the response, with sensible fallbacks.
  const detail = err?.response?.data?.detail;
  let message = '';
  if (typeof detail === 'string') {
    message = detail;
  } else if (isPydanticErrorArray(detail)) {
    // 2026-05-20 — FastAPI 422 ValidationError list. Format the
    // first 3 field errors into a readable single-line toast instead
    // of letting the array escape into React children.
    message = formatPydanticErrors(detail);
  } else if (detail && typeof detail === 'object') {
    message = detail.message || '';
  } else {
    message = err?.message || '';
  }

  toast.error(message || fallback);
}


/**
 * Test helper — returns true if the global paywall is going to handle this
 * error (so the caller can decide to skip ALL its local UI updates, not
 * just the toast).
 *
 * v5.8 / Onda 9.P — DEFENSIVE: checks both the interceptor-set flag AND
 * the response shape directly. This is belt-and-suspenders against:
 *   · stale browser cache where the new helper loaded but the new
 *     interceptor didn't (or vice versa)
 *   · any other axios setup where the interceptor doesn't run
 *
 * If status+code match a known billing pattern, the global paywall
 * components (QuotaExceededPaywall, ModuleAccessPaywall, BillingStatusBanner,
 * ReadOnlyGraceBanner) WILL open via their own event listeners. The local
 * catch can safely skip its toast.
 */
const PAYWALL_403_CODES = new Set([
  'MODULE_NOT_AVAILABLE',
  'FEATURE_NOT_AVAILABLE',
  'READ_ONLY_GRACE',
  'BILLING_TRIAL_EXPIRED',
  'BILLING_PAST_DUE',
]);

export function isPaywallHandled(err) {
  if (!err) return false;
  if (err.__handled_by_paywall === true) return true;
  // Fallback: inspect response shape directly
  const status = err?.response?.status;
  const code = err?.response?.data?.detail?.code;
  if (status === 429 && code === 'QUOTA_EXCEEDED') return true;
  if (status === 403 && code && PAYWALL_403_CODES.has(code)) return true;
  return false;
}


export default handleApiError;
