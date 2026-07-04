import api from './client';
import customerApi from './customerClient';

/**
 * Product Extras admin client (Onda 16 — Prenotazione consolidation).
 *
 * Generalizes service_options with:
 *   - kind: "mandatory" | "optional" | "radio_variant"
 *   - group_key: required for radio_variant, forms picker groups
 *   - price_modifier_type: "flat" | "per_day" | "per_unit"
 *
 * Pairs with backend/routers/product_extras.py.
 * Also provides pricePreview() — a stateless dry-run total computation
 * used by the storefront landing pages for live price display.
 */
export const productExtrasAPI = {
  list: (productId) => api.get(`/products/${productId}/extras`),
  create: (productId, body) => api.post(`/products/${productId}/extras`, body),
  update: (productId, extraId, body) =>
    api.patch(`/products/${productId}/extras/${extraId}`, body),
  // Soft-delete (is_active → false); order snapshots stay intact.
  delete: (productId, extraId) =>
    api.delete(`/products/${productId}/extras/${extraId}`),
};

/**
 * Stateless price preview with extras resolution.
 *
 * body = {
 *   product_id: string,
 *   quantity?: number,
 *   discount_pct?: number,
 *   date_from?: string,        // range flavor
 *   date_to?: string,          // range flavor
 *   extra_selections?: {
 *     mandatory_confirmed?: boolean,
 *     optional_ids?: string[],
 *     radio_picks?: { [group_key]: extra_id },
 *   }
 * }
 *
 * Returns { base, extras_total, total, day_count, extras[], extras_breakdown[] }.
 *
 * Admin variant — requires authentication. Kept for internal use (e.g. admin
 * checkout composer). Public storefront landings should use publicPricePreview
 * below so anonymous visitors still get a live total.
 */
export const pricePreview = (body) => api.post('/orders/price-preview', body);

/**
 * Public variant of pricePreview — same contract, but does not require
 * authentication and resolves the product via its id alone. Enforced to
 * active+published products server-side.
 */
export const publicPricePreview = (body) =>
  customerApi.post('/api/public/price-preview', body);

export const issuedReservationsAPI = {
  list: (params = {}) => api.get('/issued-reservations', { params }),
  resend: (reservationId) =>
    api.post(`/issued-reservations/${reservationId}/resend`),
};
