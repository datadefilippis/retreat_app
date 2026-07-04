/**
 * Dedicated axios instance for customer-facing API calls.
 *
 * Completely separate from the admin client (api/client.js):
 * - Reads `customer_token` from localStorage (NOT `token`)
 * - On 401 → cleans up token silently (NO redirect)
 * - Redirect to /account/login is CustomerProtectedRoute's job
 * - NO billing event dispatching (customers have no billing)
 * - NO admin side-effects
 *
 * Sprint 3 W3.4 — Per-slug token scoping (parity widget defense-in-depth)
 * ===========================================================================
 * Pre-W3.4: token key was global `customer_token`. If a customer browsed
 * 2 different merchant stores in the same browser, the JWT issued for
 * store A would leak to API calls for store B. Backend org_id validation
 * mitigated multi-tenant leak, but the client-side surface was still
 * unsafe (e.g. customer thought they were "logged into store A" but the
 * UI reflected store B's customer profile if they navigated quickly).
 *
 * Post-W3.4: token key is `customer_token_{slug}` when a store_slug is
 * known (resolved from URL or localStorage `customer_store_slug`).
 * Legacy `customer_token` key is read as fallback for backward compat
 * and migrated to the scoped key on first successful read.
 */

import axios from 'axios';

const customerApi = axios.create({
  headers: { 'Content-Type': 'application/json' },
});

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';

// Sprint 3 W3.4 — resolve slug for token scoping
function _resolveCurrentSlug() {
  try {
    // 1. URL path /s/:slug/* or /account?slug=...
    const match = window.location.pathname.match(/\/s\/([^/]+)/);
    if (match && match[1]) return match[1];
    // 2. localStorage cache (set by CustomerAuthContext on login)
    const cached = localStorage.getItem('customer_store_slug');
    if (cached) return cached;
  } catch {
    // SSR safety (no window)
  }
  return null;
}

function _tokenKeyForSlug(slug) {
  return slug ? `customer_token_${slug}` : 'customer_token';
}

// Read token with backward-compat fallback to legacy global key
export function readCustomerToken() {
  const slug = _resolveCurrentSlug();
  const scopedKey = _tokenKeyForSlug(slug);
  try {
    // Prefer slug-scoped
    const scoped = localStorage.getItem(scopedKey);
    if (scoped) return scoped;
    // Fallback legacy global key
    if (scopedKey !== 'customer_token') {
      const legacy = localStorage.getItem('customer_token');
      if (legacy) {
        // Migration: copy to scoped key (next read is direct)
        localStorage.setItem(scopedKey, legacy);
        return legacy;
      }
    }
  } catch {
    // localStorage unavailable
  }
  return null;
}

// Clear token (current slug + legacy global)
export function clearCustomerToken() {
  const slug = _resolveCurrentSlug();
  const scopedKey = _tokenKeyForSlug(slug);
  try {
    localStorage.removeItem(scopedKey);
    localStorage.removeItem('customer_token'); // also clear legacy
  } catch {
    // ignore
  }
}

customerApi.interceptors.request.use((config) => {
  if (config.url && !config.url.startsWith('http')) {
    const path = config.url.startsWith('/api')
      ? config.url
      : `/api${config.url.startsWith('/') ? '' : '/'}${config.url}`;
    config.url = `${BACKEND_URL}${path}`;
  }
  delete config.baseURL;

  const token = readCustomerToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// On 401: clean up stale token silently — never redirect.
// Public routes (storefront) must degrade to guest, not break.
// Protected routes use CustomerProtectedRoute for redirect logic.
customerApi.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      clearCustomerToken();
    }
    return Promise.reject(error);
  },
);

export default customerApi;
