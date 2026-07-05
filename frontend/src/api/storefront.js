/**
 * Public Storefront API — dedicated client for the public catalog and order flow.
 *
 * Uses customerClient as transport so that:
 * - customer_token is included automatically when present (registered customer)
 * - customer_token is absent gracefully when not present (guest)
 * - 401 on stale token is handled silently (no redirect, cleaned up by interceptor)
 * - BACKEND_URL is resolved consistently
 *
 * StorefrontPage should use ONLY this module for backend calls.
 */

import customerApi from './customerClient';

export const storefrontAPI = {
  getCatalog: (slug, lang) =>
    customerApi.get(`/api/public/catalog/${slug}`,
      lang && lang !== 'it' ? { params: { lang } } : undefined),

  // i18n + branding bootstrap. Lightweight payload (~250 bytes) consumed
  // by `StoreMetaContext` to drive the language resolver across every
  // public surface (catalog + 12 landings) before its own resource-heavy
  // endpoint resolves. Cached server-side 5min, client persists in
  // localStorage with 1h TTL — see StoreMetaContext for the full lifecycle.
  //
  // Accepts an axios config (e.g. `{ signal: abortController.signal }`)
  // so the StoreMetaContext can cancel in-flight requests on rapid slug
  // changes — strict-mode-safe and prevents race conditions between
  // overlapping fetches.
  getStorefrontMeta: (slug, config) =>
    customerApi.get(`/api/public/storefront/${slug}/meta`, config),

  submitOrder: (payload) =>
    customerApi.post('/api/public/order-request', payload),

  getAvailability: (slug, dateFrom, dateTo, duration, productId) =>
    customerApi.get(`/api/public/availability/${slug}`, { params: {
      date_from: dateFrom, date_to: dateTo,
      ...(duration ? { duration } : {}),
      ...(productId ? { product_id: productId } : {}),
    } }),

  // Fase 2: public-safe order status for the Stripe checkout redirect pages.
  // Used both for first render and for polling while webhook processes payment.
  getOrderStatus: (orderId) =>
    customerApi.get(`/api/public/orders/${orderId}/status`),

  // E3: full landing page payload for a single event occurrence.
  getEventLanding: (orgSlug, slug, lang) =>
    customerApi.get(`/api/public/events/${orgSlug}/${slug}`,
      lang && lang !== 'it' ? { params: { lang } } : undefined),

  // Onda 13: full landing page payload for a generic product (primarily services).
  getProductLanding: (orgSlug, productSlug, lang) =>
    customerApi.get(`/api/public/products/${orgSlug}/${productSlug}`,
      lang && lang !== 'it' ? { params: { lang } } : undefined),

  // F5 Onda 12: available service slots for a given product (used by landing).
  getServiceSlots: (productId, days = 30) =>
    customerApi.get(`/api/public/services/${productId}/slots?days=${days}`),

  // Advisory availability for rental range products: returns the list of
  // YYYY-MM-DD dates that are already booked/manually blocked so the date
  // picker can surface them before submit. The atomic guard at order confirm
  // time remains the source of truth — this is purely UX.
  getRentalBlockedDates: (productId, dateFromIso, dateToIso) =>
    customerApi.get(
      `/api/public/reservations/blocked-dates/${encodeURIComponent(productId)}`,
      { params: { from: dateFromIso, to: dateToIso } },
    ),

  // Available slots for a rental product with reservation_flavor=slot
  // (e.g. meeting rooms, courts). Mirrors getServiceSlots but filters
  // for rentals server-side.
  getRentalSlots: (productId, days = 30) =>
    customerApi.get(
      `/api/public/reservations/${encodeURIComponent(productId)}/slots`,
      { params: { days } },
    ),

  // Onda 17 — continuous availability windows for rental+flavor=slot
  // products with variable duration + cross-day support. Returns config
  // (min_duration, step, max_duration) and per-day free windows.
  getRentalAvailabilityWindows: (productId, days = 30) =>
    customerApi.get(
      `/api/public/reservations/${encodeURIComponent(productId)}/availability-windows`,
      { params: { days } },
    ),

  // Release 3 (Digital) — token-gated landing payload for /d/:access_token.
  // Always returns 200 with a status field; the landing UI renders the right
  // copy per status. A 404 only fires when the token is unknown.
  getPublicDownload: (accessToken) =>
    customerApi.get(
      `/api/public/downloads/${encodeURIComponent(accessToken)}`,
    ),

  // ── Sprint 2 W2.1 — coupon dry-run validation (parity widget E4.1) ──
  //
  // POST /api/public/embed/coupons/validate/{slug}
  // Body: { code: string, cart_subtotal: number }
  // Validates a coupon WITHOUT incrementing usage counter. Anti-race
  // condition pattern: customer preview vs real checkout.
  // The real checkout (POST /checkout/start) calls validate_coupon
  // (atomic increment) so dry-run can pass + checkout fail with
  // coupon_exhausted if the last slot was consumed mid-flight.
  //
  // Response: {
  //   valid: bool,
  //   reason?: "expired" | "max_uses_reached" | "min_order_amount" |
  //            "scope_mismatch" | "inactive" | "not_found",
  //   message?: string,
  //   discount_amount?: number,
  //   coupon?: { code, kind, value }
  // }
  validateCoupon: (slug, code, cartSubtotal) =>
    customerApi.post(
      `/api/public/embed/coupons/validate/${encodeURIComponent(slug)}`,
      {
        code: String(code || '').trim().toUpperCase(),
        cart_subtotal: Number(cartSubtotal) || 0,
      },
    ),
};
