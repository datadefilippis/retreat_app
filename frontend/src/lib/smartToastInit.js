/**
 * smartToastInit — global monkey-patch of `toast.error` from sonner.
 *
 * v5.8 / Onda 9.X — Holistic UX fix for billing blocks.
 *
 * THE PROBLEM:
 *   Many existing pages do `toast.error(error.response?.data?.detail || ...)`
 *   directly without using handleApiError. When the backend returns a 429
 *   QUOTA_EXCEEDED or 403 paywall code, the `detail` field is a DICT
 *   ({code, message, used, limit, ...}) — not a string. Two bad outcomes:
 *
 *   1. Toast renders the dict as "[object Object]" → user sees garbage
 *   2. Even when we coerce to dict.message, the toast COMPETES with the
 *      <QuotaExceededPaywall> / <ModuleAccessPaywall> global modals (which
 *      already opened via the axios interceptor's event dispatch). User
 *      sees both, gets confused, dismisses the wrong one.
 *
 *   We fixed this in some pages (StoresPage, ProductsPage, OrdersPage,
 *   ChatPage, SalesEntryForm, ExpensesEntryForm) but ~40+ other catch
 *   blocks across the codebase still use raw `toast.error(detail)`.
 *
 * THE SOLUTION:
 *   Monkey-patch `toast.error` ONCE at app startup so EVERY existing
 *   toast.error call benefits automatically:
 *
 *   1. If the message is a dict with a known billing code → swallow toast
 *      (paywall will show)
 *   2. If the message is a dict without billing code → coerce to dict.message
 *      or JSON.stringify (avoids "[object Object]")
 *   3. If the message is a string → pass through unchanged
 *
 *   Zero changes needed in calling code. Single point of control.
 *
 * SCOPE:
 *   Only `toast.error` is patched. `toast.success`, `toast.info`, etc.
 *   are not affected (they don't carry billing payloads).
 */
import { toast } from 'sonner';

// 2026-05-20 — Pydantic v2 / FastAPI 422 ValidationError support.
// See lib/apiErrorFormatting.js header for the bug postmortem. The
// import is small enough that bundle impact is negligible.
import {
  isPydanticErrorArray,
  formatPydanticErrors,
  coerceToToastString,
} from './apiErrorFormatting';


// Codes that indicate a global paywall/banner is handling the error.
// When toast.error is called with a dict containing one of these, suppress
// the toast entirely — the paywall already explains the situation with
// localized copy and an upgrade CTA.
const PAYWALL_CODES = new Set([
  'QUOTA_EXCEEDED',           // 429 — chat, products, orders, stores, team_members, etc.
  'MODULE_NOT_AVAILABLE',     // 403 — module disabled in plan
  'FEATURE_NOT_AVAILABLE',    // 403 — feature limit is 0 in plan
  'READ_ONLY_GRACE',          // 403 — 7d grace after downgrade
  'BILLING_TRIAL_EXPIRED',    // 403 — v6.0 billing gate
  'BILLING_PAST_DUE',         // 403 — v6.0 billing gate
]);


let _originalError = null;
let _installed = false;


/**
 * Install the smart toast.error wrapper. Idempotent — safe to call multiple
 * times (subsequent calls are no-ops).
 *
 * Call this ONCE at app startup, ideally in src/index.js or App.js before
 * any component renders.
 */
export function installSmartToast() {
  if (_installed) return;
  _installed = true;
  _originalError = toast.error;

  toast.error = function smartToastError(message, options) {
    // Case 1: message is null/undefined → use a generic fallback
    if (message == null) {
      return _originalError.call(toast, 'Errore', options);
    }

    // Case 1.5 (2026-05-20): Pydantic v2 ValidationError array.
    //
    // FastAPI returns ``detail: [{type, loc, msg, input, ctx, url}, ...]``
    // for HTTP 422 (request body failed Pydantic validation). Roughly
    // 66 call sites in the codebase do ``toast.error(err.response.data
    // .detail || fallback)`` — without this branch the array lands in
    // sonner → eventually React tries to render objects as children
    // and throws "Objects are not valid as a React child".
    //
    // We format the list as a single readable string before passing
    // it to sonner. The fix is centralised here so the 66 call sites
    // don't need to be touched individually.
    if (isPydanticErrorArray(message)) {
      const formatted = formatPydanticErrors(message);
      return _originalError.call(
        toast,
        formatted || 'Errore di validazione',
        options,
      );
    }

    // Case 2: message is a backend detail dict
    if (typeof message === 'object' && !Array.isArray(message)) {
      const code = message.code;

      // 2a. Billing code → paywall handles it, swallow toast silently.
      // Returns a dummy id-like value so callers expecting a toast id
      // don't crash if they try to dismiss.
      if (code && PAYWALL_CODES.has(code)) {
        return -1;  // sentinel: nothing to dismiss
      }

      // 2b. Dict with a `message` field → use that as the toast text
      const text = message.message
        || message.error
        || message.detail
        || 'Errore';
      return _originalError.call(toast, String(text), options);
    }

    // Case 3: string / number → pass through unchanged
    if (typeof message === 'string' || typeof message === 'number') {
      return _originalError.call(toast, message, options);
    }

    // Case 4 (2026-05-20 safety net): anything else (raw arrays of
    // strings, exotic dicts, etc.) — coerce to a safe string so React
    // never receives a non-primitive in its children tree. Without
    // this, a future backend change to detail shape could re-trigger
    // the "Objects are not valid as a React child" crash.
    const safe = coerceToToastString(message);
    return _originalError.call(toast, safe || 'Errore', options);
  };
}


/**
 * Test helper: returns true if the wrapper has been installed.
 */
export function isSmartToastInstalled() {
  return _installed;
}
