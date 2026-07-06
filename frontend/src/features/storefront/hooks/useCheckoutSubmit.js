/**
 * useCheckoutSubmit — unified entry point for the public /order-request flow.
 *
 * Before this hook each caller had its own copy of the "submit order,
 * handle Stripe redirect, show errors" logic:
 *   - StorefrontPage had the full cart flow with window.location.href
 *     redirect when `payment_checkout_url` came back from the backend.
 *   - EventLandingPage had its own truncated flow that IGNORED the
 *     checkout URL entirely, silently breaking direct-mode events
 *     (customer saw "Prenotazione ricevuta!" without actually paying).
 *
 * The hook centralizes exactly that slice — backend call + Stripe
 * redirect decision + structured error surfacing. Callers keep their
 * own form UI and cart shape; they only stop re-implementing the
 * tricky part.
 *
 * Contract:
 *   submit(payload, overrides?) -> Promise<{
 *     ok: boolean,
 *     redirected?: boolean,     // true when we sent the browser to Stripe
 *     data?: object,            // backend response body on success
 *     error?: string,           // detail string on failure
 *   }>
 *
 * Options (can be passed to the hook OR to each submit() call):
 *   onSuccess(data)             called when backend returned 200 and NO
 *                               payment_checkout_url (request / approval
 *                               mode, or direct with gateway offline).
 *   onDirectCheckoutUrl(url)    called when backend returned a Stripe
 *                               checkout URL. Default: window.location.href
 *                               = url (same as StorefrontPage legacy flow).
 *   onError(message, exception) called on any backend / network failure
 *                               with the server detail string (or a
 *                               generic fallback).
 *
 * The overrides object passed to submit() wins over hook-level options,
 * which lets a caller tweak behavior per-submit (e.g. swap out the
 * success toast when the same page has multiple entry points).
 */

import { useState, useCallback } from 'react';
import i18n from '../../../i18n';
import { storefrontAPI } from '../../../api/storefront';


// R2a — lingua UI al momento del checkout, timbrata sull'ordine
// (order.locale) lato backend: guida la lingua di TUTTE le email verso
// il compratore, compresi i promemoria caparra che partono settimane
// dopo. Il hook è l'imbuto unico di ogni submit (store, landing,
// marketplace): timbrando qui la ereditano tutte le superfici.
const EMAIL_LOCALES = ['it', 'en', 'de', 'fr'];

function currentEmailLocale() {
  const lang = (i18n.language || '').slice(0, 2).toLowerCase();
  return EMAIL_LOCALES.includes(lang) ? lang : undefined;
}


const DEFAULT_ERROR = 'Errore durante la prenotazione. Riprova.';


/**
 * Normalize an arbitrary FastAPI error `detail` into a plain string.
 *
 * FastAPI increasingly returns structured errors like
 *   { detail: { error: "course_requires_account", message: "..." } }
 * while legacy endpoints still return plain strings. Passing a
 * structured detail directly to React (as toast text or JSX) throws
 * "Objects are not valid as a React child" and bubbles up to the
 * ErrorBoundary — which is exactly the kind of crash we want to
 * prevent at the hook layer so every caller is safe.
 */
function normalizeErrorDetail(detail) {
  if (typeof detail === 'string' && detail) return detail;
  if (Array.isArray(detail)) {
    // Pydantic validation errors shape: [{loc, msg, type}, ...]
    const first = detail[0];
    if (first && typeof first === 'object' && first.msg) return String(first.msg);
  }
  if (detail && typeof detail === 'object') {
    // Structured errors: prefer `message`, fall back to `error` code.
    if (typeof detail.message === 'string' && detail.message) return detail.message;
    if (typeof detail.error === 'string' && detail.error) return detail.error;
  }
  return DEFAULT_ERROR;
}


export function useCheckoutSubmit(defaults = {}) {
  const [submitting, setSubmitting] = useState(false);

  const submit = useCallback(async (payload, overrides = {}) => {
    if (submitting) return { ok: false, error: 'submitting' };
    const onSuccess = overrides.onSuccess || defaults.onSuccess;
    const onError = overrides.onError || defaults.onError;
    const onDirectCheckoutUrl = overrides.onDirectCheckoutUrl
      || defaults.onDirectCheckoutUrl
      || ((url) => { window.location.href = url; });

    setSubmitting(true);
    try {
      const locale = payload.locale || currentEmailLocale();
      const res = await storefrontAPI.submitOrder(
        locale ? { ...payload, locale } : payload
      );
      const data = res?.data || {};

      // Stripe / gateway redirect path. The backend returns
      // `payment_checkout_url` only in direct mode when the org has a
      // live payment provider and the cart passes availability checks.
      if (data.payment_checkout_url) {
        try { onDirectCheckoutUrl(data.payment_checkout_url, data); }
        catch (e) { /* user-provided handler threw — fall through to success */ }
        return { ok: true, redirected: true, data };
      }

      if (onSuccess) {
        try { onSuccess(data); } catch (e) { /* isolate handler errors */ }
      }
      return { ok: true, redirected: false, data };
    } catch (err) {
      // Always pass a plain string to consumers — `err.response.data.detail`
      // may be a FastAPI structured object, a Pydantic validation array,
      // or missing entirely.
      const detail = normalizeErrorDetail(err?.response?.data?.detail);
      if (onError) {
        try { onError(detail, err); } catch (e) { /* isolate */ }
      }
      return { ok: false, error: detail, exception: err };
    } finally {
      setSubmitting(false);
    }
  }, [submitting, defaults]);

  return { submit, submitting };
}
