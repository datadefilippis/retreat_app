import api from './client';

/**
 * Service Options admin client (F5 Onda 12).
 *
 * CRUD for a service product's radio-select options.
 * Pairs with backend/routers/service_options.py.
 */
export const serviceOptionsAPI = {
  // GET /api/products/{product_id}/service-options
  list: (productId) =>
    api.get(`/products/${productId}/service-options`),

  // POST /api/products/{product_id}/service-options
  create: (productId, body) =>
    api.post(`/products/${productId}/service-options`, body),

  // PATCH /api/products/{product_id}/service-options/{option_id}
  update: (productId, optionId, body) =>
    api.patch(`/products/${productId}/service-options/${optionId}`, body),

  // DELETE /api/products/{product_id}/service-options/{option_id}
  delete: (productId, optionId) =>
    api.delete(`/products/${productId}/service-options/${optionId}`),
};
