/**
 * useStripeReadiness — single-source-of-truth React hook that reflects
 * whether the current admin's organization can accept direct Stripe
 * checkout payments.
 *
 * Used by:
 *   - StripeRequiredAlert component (next to transaction_mode selector)
 *   - any future surface that needs to gate a direct-pay-only feature
 *
 * Design notes
 * ============
 *
 * Caching across components. Two product-form pages mounted in the
 * same session would otherwise issue two identical /payments/readiness
 * requests. We promote the first response to a module-scope promise
 * so subsequent hook mounts await the same call. A consumer can call
 * `refresh()` to invalidate (used after the admin completes Stripe
 * onboarding and returns to the form).
 *
 * Fail-open default. If the network call fails (offline, server 500,
 * timeout) we DON'T block the admin from selecting "direct" — we just
 * skip the warning. A false negative ("Stripe is configured" when in
 * fact it isn't) only causes the storefront fallback that already
 * exists today; the worst case here is identical to the bug we're
 * trying to surface, which is preferable to blocking workflow on a
 * transient network blip.
 *
 * No suspense / no react-query. The codebase doesn't use either, and
 * a custom hook keeps the implementation surface tiny and matches
 * the existing `useBilling` / `useAiAccess` style.
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import { paymentsAPI } from '../api/payments';

// Module-scope cache: shared by every consumer of the hook within a
// session. Cleared by `refresh()` so admins returning from onboarding
// see the new state without a hard reload.
let _cachedPromise = null;

function fetchOnce() {
  if (_cachedPromise) return _cachedPromise;
  _cachedPromise = paymentsAPI.getReadiness();
  return _cachedPromise;
}

function clearCache() {
  _cachedPromise = null;
}

/**
 * Returns
 * -------
 * {
 *   loading:       boolean — true while the first response is in flight
 *   ready:         boolean — true when stripe_configured === true
 *   reasonCode:    string  — backend reason_code (or '' before load /
 *                            'fetch_error' on failure)
 *   message:       string  — Italian human-readable status
 *   provider:      string  — 'stripe' (today) or null
 *   actionUrl:     string  — where to send the admin to fix things
 *   refresh():     () => Promise<void> — force re-fetch
 * }
 */
export function useStripeReadiness() {
  const [state, setState] = useState({
    loading: true,
    ready: false,
    reasonCode: '',
    message: '',
    provider: null,
    actionUrl: null,
  });

  // `mounted` guard so we don't setState on a component that has gone
  // away while the request was in flight (typical with rapid form
  // re-mounts during route changes).
  const mounted = useRef(true);

  const load = useCallback(async () => {
    try {
      const data = await fetchOnce();
      if (!mounted.current) return;
      setState({
        loading: false,
        ready: !!data?.stripe_configured,
        reasonCode: data?.reason_code || '',
        message: data?.message_it || '',
        provider: data?.provider || null,
        actionUrl: data?.action_url || null,
      });
    } catch (err) {
      // Fail-open: don't block the admin. See file header.
      if (!mounted.current) return;
      setState({
        loading: false,
        ready: true,                 // ← fail-open
        reasonCode: 'fetch_error',
        message: '',
        provider: null,
        actionUrl: null,
      });
    }
  }, []);

  const refresh = useCallback(async () => {
    clearCache();
    setState((s) => ({ ...s, loading: true }));
    await load();
  }, [load]);

  useEffect(() => {
    mounted.current = true;
    load();
    return () => { mounted.current = false; };
  }, [load]);

  return { ...state, refresh };
}
