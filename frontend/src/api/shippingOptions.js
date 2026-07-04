/**
 * Shipping Options — admin + public CRUD helpers.
 *
 * Admin endpoints live under `/api/shipping-options` and are scoped
 * per-org by the backend via the authenticated JWT. Creating an option
 * with `store_id === null` makes it org-global (visible at checkout in
 * every store of the org); passing a `store_id` limits it to one store.
 */

import api from './client';
import customerApi from './customerClient';


export const shippingOptionsAPI = {
  /**
   * List shipping options for the current org.
   * @param {object} [opts]
   * @param {string|null} [opts.storeId]  — filter by store_id
   * @param {'store'|'global'|'all'|null} [opts.scope]
   *   - 'store' requires storeId → only that store's options
   *   - 'global' → only org-global options (store_id=null)
   *   - 'all' requires storeId → both store + globals
   *   - null (default) → legacy: if storeId given filter by it, else all
   */
  list: ({ storeId = null, scope = null } = {}) => {
    const params = {};
    if (storeId) params.store_id = storeId;
    if (scope) params.scope = scope;
    return api.get('/shipping-options', { params });
  },

  create: (data) => api.post('/shipping-options', data),

  update: (optionId, updates) =>
    api.patch(`/shipping-options/${optionId}`, updates),

  delete: (optionId) => api.delete(`/shipping-options/${optionId}`),
};


/**
 * Public storefront helper — used by the checkout picker to surface the
 * resolved options for a given store slug. Returns
 * `{ options: [{id, label, description, base_price, free_shipping_threshold, sort_order}] }`.
 */
export const publicShippingOptions = {
  get: (storeSlug) =>
    customerApi.get(`/api/public/shipping-options/${encodeURIComponent(storeSlug)}`),
};
