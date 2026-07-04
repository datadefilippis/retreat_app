/**
 * useIsMarketingOptedIn — unified "is this checkout user already
 * iscritto alla newsletter?" probe.
 *
 * 2026-05-20 — Powers the symmetric UX where the marketing checkbox
 * at storefront checkout is HIDDEN for any user (guest or registered)
 * who is already opted-in. The previous logic gated the entire GDPR
 * block on ``!isAuthenticated`` which made the marketing checkbox
 * disappear ONLY for logged-in users, regardless of their actual
 * marketing state — confusing for both:
 *   · Logged-in but NOT opted-in: couldn't opt-in at checkout
 *   · Guest WHO IS opted-in (returning customer): saw the checkbox
 *     again and got confused
 *
 * The hook resolves the state from two independent sources without
 * blurring them together:
 *
 *   LOGGED-IN path (zero query): reads from the ``customer`` object
 *   that the CustomerAuthContext already fetched via /api/customer/me
 *   on login. The ``accepted_marketing_at`` and ``marketing_revoked_at``
 *   fields are exposed by CustomerAccountResponse on the backend.
 *
 *   GUEST path (1 query, debounced 400ms): hits the public endpoint
 *   GET /api/public/storefront/<slug>/marketing-status?email=<email>
 *   The backend rate-limits the endpoint at 10/min/IP and returns a
 *   uniformly-shaped {opted_in: bool} body (no PII, no distinction
 *   between known-not-opted and unknown-email — privacy guard).
 *
 * Returns:
 *   { isOptedIn: boolean, loading: boolean, source: string }
 *
 * source ∈ {"logged-in", "guest-lookup", "unknown"}:
 *   - "logged-in"     when the answer comes from customer object
 *   - "guest-lookup"  when the answer comes from the public endpoint
 *   - "unknown"       when neither side has resolved yet (email empty,
 *                      lookup in flight, etc.) — frontend should default
 *                      to showing the checkbox in this case
 *
 * Returning a separate ``source`` lets the UI distinguish "we don't
 * know yet → keep showing the checkbox optimistically" from
 * "we know the customer is opted-in → hide it confidently".
 */

import { useEffect, useState, useRef } from 'react';

// Public storefront API — same axios client the rest of the storefront
// uses, so it inherits the base URL and any future global interceptors
// (CORS, retry, etc.) without divergence.
import api from '../api/client';


const LOOKUP_DEBOUNCE_MS = 400;
const EMAIL_MIN_VALID_LENGTH = 5;  // "a@b.c" lower-bound


function _looksLikeEmail(s) {
  if (!s || typeof s !== 'string') return false;
  if (s.length < EMAIL_MIN_VALID_LENGTH) return false;
  return s.includes('@') && s.includes('.');
}


function _isLoggedInOptedIn(customer) {
  if (!customer) return false;
  const accepted = customer.accepted_marketing_at;
  if (!accepted) return false;
  const revoked = customer.marketing_revoked_at;
  // Most-recent-wins (same formula the backend uses everywhere).
  if (revoked && !(accepted > revoked)) return false;
  return true;
}


export default function useIsMarketingOptedIn({
  customer,             // from useCustomerAuth(), null when guest
  isAuthenticated,      // boolean
  email,                // guest's email as they type it
  slug,                 // storefront slug for the public lookup
  enabled = true,       // toggle off when the block isn't visible anyway
}) {
  // ── Hooks declared unconditionally (React rule of hooks). ─────────
  // The logged-in path derivation happens AFTER all hooks have been
  // called, never via early-return before them.
  const [state, setState] = useState({
    isOptedIn: false,
    loading: false,
    source: 'unknown',
  });
  const debounceRef = useRef(null);
  const lastEmailRef = useRef('');

  useEffect(() => {
    // Skip the guest lookup when the user is already logged-in or
    // the hook is explicitly disabled — the return value below uses
    // the logged-in synchronous derivation instead.
    if (!enabled || (isAuthenticated && customer)) {
      return undefined;
    }

    const cleanEmail = (email || '').trim().toLowerCase();
    if (!_looksLikeEmail(cleanEmail)) {
      // Email empty/incomplete — reset to unknown so the checkbox
      // stays visible optimistically.
      lastEmailRef.current = '';
      setState({ isOptedIn: false, loading: false, source: 'unknown' });
      if (debounceRef.current) clearTimeout(debounceRef.current);
      return undefined;
    }

    if (cleanEmail === lastEmailRef.current) {
      // Same email already probed — no-op.
      return undefined;
    }

    // Debounce: cancel any in-flight scheduled call.
    if (debounceRef.current) clearTimeout(debounceRef.current);
    setState((prev) => ({ ...prev, loading: true }));

    debounceRef.current = setTimeout(async () => {
      lastEmailRef.current = cleanEmail;
      try {
        const res = await api.get(
          `/public/storefront/${encodeURIComponent(slug)}/marketing-status`,
          { params: { email: cleanEmail } },
        );
        // Defensive: backend may not be deployed everywhere yet.
        // Treat missing field as false.
        const optedIn = !!res?.data?.opted_in;
        setState({
          isOptedIn: optedIn,
          loading: false,
          source: 'guest-lookup',
        });
      } catch (err) {
        // Rate-limited / network error / 4xx: fall back to "unknown"
        // so the UI keeps the checkbox visible. NEVER let this
        // lookup break the checkout flow.
        setState({ isOptedIn: false, loading: false, source: 'unknown' });
      }
    }, LOOKUP_DEBOUNCE_MS);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [email, slug, enabled, isAuthenticated, customer]);

  // Logged-in path — synchronously derived from the customer object
  // that CustomerAuthContext already fetched via /api/customer/me on
  // login. This branch ignores the guest-lookup state above.
  if (isAuthenticated && customer) {
    return {
      isOptedIn: _isLoggedInOptedIn(customer),
      loading: false,
      source: 'logged-in',
    };
  }

  return state;
}
