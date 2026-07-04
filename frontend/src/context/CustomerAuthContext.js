/**
 * Customer Authentication Context — completely separate from admin AuthContext.
 *
 * ORG-SCOPED: customer accounts belong to a specific organization.
 * The store slug is required for login/signup to identify the org.
 *
 * - Token stored as `customer_token` in localStorage (NOT `token`)
 * - Org slug stored as `customer_store_slug` in localStorage
 * - Independent login/logout lifecycle
 * - No billing events
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
// `i18n` is no longer imported here — Step 11 moved language application
// out of this context. See the deprecation note further down for the
// architectural rationale.
import { customerAuthAPI } from '../api/customerAuth';

const CustomerAuthContext = createContext(null);

export const useCustomerAuth = () => {
  const ctx = useContext(CustomerAuthContext);
  if (!ctx) throw new Error('useCustomerAuth must be inside CustomerAuthProvider');
  return ctx;
};

export const CustomerAuthProvider = ({ children }) => {
  const [customer, setCustomer] = useState(null);
  const [customerToken, setCustomerToken] = useState(localStorage.getItem('customer_token'));
  const [storeSlug, setStoreSlug] = useState(localStorage.getItem('customer_store_slug') || '');
  const [loading, setLoading] = useState(true);

  const isCustomerAuthenticated = !!customer;

  // Soft auth check on mount — degrade to guest silently on failure.
  useEffect(() => {
    let cancelled = false;
    const checkAuth = async () => {
      const token = localStorage.getItem('customer_token');
      if (!token) {
        setLoading(false);
        return;
      }
      try {
        const res = await customerAuthAPI.getMe();
        if (!cancelled) {
          setCustomer(res.data);
          // Restore slug from /me response if available
          if (res.data?.org_slug) {
            setStoreSlug(res.data.org_slug);
            localStorage.setItem('customer_store_slug', res.data.org_slug);
          }
        }
      } catch {
        localStorage.removeItem('customer_token');
        localStorage.removeItem('customer_store_slug');
        if (!cancelled) {
          setCustomerToken(null);
          setCustomer(null);
          setStoreSlug('');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    checkAuth();
    return () => { cancelled = true; };
  }, []);

  // Note (Step 11): this context NO LONGER writes to i18n.language directly.
  //
  // Architectural rationale
  // -----------------------
  // The storefront resolver chain (`useStorefrontLocale` →
  // `useStorefrontLocaleSync`) considers `customer?.locale` as priority 2
  // — but ONLY when it's in the merchant's `storefront_languages` list.
  // Writing it directly here would bypass that filter, leading to a
  // bug where a customer with locale='it' on a German-only store sees
  // Italian instead of the merchant's configured German storefront.
  //
  // The resolver is now mounted on every customer-bearing surface:
  //   • PublicStorefrontShell (storefront + 12 landings)
  //   • AuthShell (customer auth pages)
  //   • CustomerLayout (post-login customer area, since Step 11)
  //
  // Each of those reads the merchant's allowed list from
  // StoreMetaContext and applies `customer.locale` only when it's
  // compatible. The customer's preference is therefore honored where
  // possible and gracefully falls back to the store's primary
  // language otherwise.
  //
  // `customer.locale` itself is still kept on the context object — it's
  // read by ProfilePage's locale picker, by the resolver, and may be
  // used by future surfaces. The deprecation here is only the side
  // effect (i18n.changeLanguage), not the field.

  const login = useCallback(async (slug, email, password) => {
    const res = await customerAuthAPI.login(slug, email, password);
    const { access_token, customer: customerData } = res.data;
    // Sprint 3 W3.4 — per-slug token scoping (defense-in-depth multi-tenant)
    // Write BOTH legacy (backward compat) AND scoped key cosi' i 2 client
    // (storefront + protected routes) leggono il giusto token per slug.
    localStorage.setItem('customer_token', access_token);
    localStorage.setItem(`customer_token_${slug}`, access_token);
    localStorage.setItem('customer_store_slug', slug);
    setCustomerToken(access_token);
    setCustomer(customerData);
    setStoreSlug(slug);
    // Sprint 2 W2.6 — dispatch document event per cart merge hook
    // (mirror del widget afianco:customer-logged-in pattern).
    // useStorefrontCart listener invoca POST /cart/{guest_id}/merge.
    try {
      document.dispatchEvent(
        new CustomEvent('afianco:customer-logged-in', {
          detail: { customer: customerData, access_token, slug },
        }),
      );
    } catch {
      // CustomEvent unsupported in old browsers - non blocking
    }
    return customerData;
  }, []);

  const signup = useCallback(async (data) => {
    // data: { slug, email, name, password, locale, auto_login? }
    const res = await customerAuthAPI.signup(data);
    const payload = res.data || {};

    // Release 4 (Courses) — when `auto_login: true` is passed, the backend
    // also returns an `access_token` + `customer` so the caller can proceed
    // to a purchase immediately (the email-verification gate is bypassed
    // for this session; subsequent fresh logins still require it).
    if (payload.access_token && payload.customer) {
      localStorage.setItem('customer_token', payload.access_token);
      if (data.slug) {
        localStorage.setItem('customer_store_slug', data.slug);
      }
      setCustomerToken(payload.access_token);
      setCustomer(payload.customer);
      if (data.slug) setStoreSlug(data.slug);
      return {
        status: 'auto_logged_in',
        customer: payload.customer,
        access_token: payload.access_token,
      };
    }

    // Legacy flow: verification email sent, no token yet.
    if (res.status === 202 || payload.status === 'verification_required') {
      if (data.slug) {
        localStorage.setItem('customer_store_slug', data.slug);
        setStoreSlug(data.slug);
      }
      return 'verification_required';
    }
    return payload;
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('customer_token');
    localStorage.removeItem('customer_store_slug');
    setCustomerToken(null);
    setCustomer(null);
    setStoreSlug('');
  }, []);

  // Merge a partial update into the in-memory customer record. Used
  // after a successful `PATCH /customer/me` so the rest of the UI
  // (sidebar, profile read-only fields, the locale-driven i18n sync
  // effect above) reflects the new value without forcing a /me round-
  // trip. The caller is responsible for sending the same payload to
  // the backend; this function only propagates the change client-side.
  const updateCustomer = useCallback((partial) => {
    if (!partial || typeof partial !== 'object') return;
    setCustomer(prev => (prev ? { ...prev, ...partial } : prev));
  }, []);

  // Wave GDPR-Commerce CG-4 — round-trip /api/customer/me and update the
  // local customer state. Called by <CustomerReconsentModal/> after a
  // successful re-consent POST so consent_needs_refresh flips False and
  // the modal unmounts on the next render.
  const refreshCustomer = useCallback(async () => {
    if (!customerToken) return null;
    try {
      const r = await customerAuthAPI.getMe();
      if (r && r.data) {
        setCustomer(r.data);
        return r.data;
      }
    } catch (err) {
      // Don't surface — caller already handles UX (toast / inline error).
      console.warn('refreshCustomer failed:', err);
    }
    return null;
  }, [customerToken]);

  const value = {
    customer,
    customerToken,
    storeSlug,
    loading,
    isCustomerAuthenticated,
    login,
    signup,
    logout,
    updateCustomer,
    refreshCustomer,
  };

  return (
    <CustomerAuthContext.Provider value={value}>
      {children}
    </CustomerAuthContext.Provider>
  );
};
