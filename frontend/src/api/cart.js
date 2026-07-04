/**
 * cart.js — API client per il persistent server-side cart (Phase 0 Step 4).
 *
 * Wraps the 5 ``/api/public/cart/*`` endpoint exposed by the backend.
 * Used by ``usePersistentCartSync`` hook (sidecar dual-write — Step 4b)
 * and by future Stream A embed SDK + AI site renderer.
 *
 * Cookie ``afianco_cart_id`` is set/read automatically by the browser
 * when axios uses ``withCredentials: true`` — already configured globally
 * in api/client.js.
 *
 * Failure model
 * -------------
 * Every method ritorna una Promise<{data}> in success, ma il sidecar
 * caller usa try/catch e tolera failure (sessionStorage rimane source
 * of truth in Step 4b). Quando passeremo source of truth al server in
 * Step 4c, gli error path verranno alzati a UI-visible toast.
 */

import api from './client';


export const cartAPI = {
  /**
   * Create empty cart bound to store.
   *
   * Backend sets the ``afianco_cart_id`` cookie on the response (HttpOnly,
   * SameSite=Lax, 60gg TTL). The cookie is then automatically sent on
   * subsequent requests by the browser.
   *
   * @param {string} slug      Store slug
   * @param {string} [source]  Origin attribution: "storefront_classic" (default),
   *                           future: "embed_widget", "ai_site"
   * @returns {Promise<CartResponse>}
   */
  create: ({ slug, source = 'storefront_classic' } = {}) =>
    api.post('/public/cart', { slug, source }),

  /**
   * Read cart by id within a store's org context.
   *
   * @param {string} cartId
   * @param {string} slug    Store slug (used for org resolution + INV-CART-2)
   */
  get: ({ cartId, slug }) =>
    api.get(`/public/cart/${cartId}`, { params: { slug } }),

  /**
   * Update cart items + optionally bind customer_email.
   *
   * Items list semantica:
   *   - quantity=0 → rimuove product line
   *   - REPLACE total: items omessi vengono RIMOSSI dal cart
   *
   * Per add/remove parziale, caller deve fare prima un GET + merge.
   * (Pattern PUT-replace, non PATCH-merge — più predicibile per Stream A.)
   *
   * @param {string} cartId
   * @param {string} slug
   * @param {Object} body
   * @param {Array<CartItemInput>} [body.items]
   * @param {string} [body.customer_email]
   */
  update: ({ cartId, slug, body }) =>
    api.patch(`/public/cart/${cartId}`, body, { params: { slug } }),

  /**
   * Bind anonymous cart to logged-in customer account.
   *
   * Requires customer Bearer token in Authorization header (set by
   * CustomerAuthContext via axios interceptor when user is logged-in).
   * Server verifies org_id + sub match per prevenire hijack.
   *
   * @param {string} cartId
   * @param {string} slug
   * @param {string} customerAccountId
   */
  merge: ({ cartId, slug, customerAccountId }) =>
    api.post(
      `/public/cart/${cartId}/merge`,
      { customer_account_id: customerAccountId },
      { params: { slug } },
    ),

  /**
   * Clear cart items (soft, default) or hard-delete the cart entirely.
   *
   * Soft clear:  items wiped, cart_id rimane valido, cookie preservato.
   * Hard delete: cart doc removed + cookie cleared by response.
   *
   * @param {string} cartId
   * @param {string} slug
   * @param {boolean} [hard]  False = clear items only (default), True = hard delete
   */
  remove: ({ cartId, slug, hard = false }) =>
    api.delete(`/public/cart/${cartId}`, { params: { slug, hard } }),
};


export default cartAPI;
