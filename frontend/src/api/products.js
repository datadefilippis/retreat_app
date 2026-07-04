import api from './client';

export const productsAPI = {
  list: (activeOnly = true, limit = 500, storeId = null) =>
    api.get('/products', { params: { active_only: activeOnly, limit, ...(storeId ? { store_id: storeId } : {}) } }),

  get: (productId) =>
    api.get(`/products/${productId}`),

  create: (data) =>
    api.post('/products', data),

  update: (productId, updates) =>
    api.patch(`/products/${productId}`, updates),

  deactivate: (productId) =>
    api.delete(`/products/${productId}`),

  // Onda 13 — server-side clone of a product (name + "(copia)",
  // metadata copied, service_options + availability_rules cloned
  // when item_type=service, is_published=false on the clone).
  duplicate: (productId) =>
    api.post(`/products/${productId}/duplicate`),

  // Onda 14 Parte C — bookings attached to a service product, used by
  // the ServiceDashboardPage "Prossimi appuntamenti" card.
  listBookings: (productId, { upcoming = 1, limit = 10 } = {}) =>
    api.get(`/products/${productId}/bookings`, { params: { upcoming, limit } }),

  // Admin-side resolution of the public landing URL for a product.
  // Returns { has_landing, landing_url_path, landing_url_absolute, store_slug,
  //           store_name, product_slug, item_type, blockers: string[] }.
  // Single source of truth consumed by the "Preview landing" + "Copy link"
  // actions across Reservation / Service / Physical / Digital dashboards.
  getLandingInfo: (productId) =>
    api.get(`/products/${productId}/landing-info`),

  // 2026-05-20 — Added the optional ``config`` param so callers (typically
  // useAbortableUpload) can pass ``{ signal: abortController.signal }`` and
  // cancel a slow upload on unmount / navigation.
  uploadImage: (productId, file, config = {}) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post(`/products/${productId}/image`, formData, {
      ...config,
      headers: {
        'Content-Type': 'multipart/form-data',
        ...(config.headers || {}),
      },
    });
  },

  // Release 3 (Digital) — upload the payload of an item_type=digital product
  // into the private storage root. Updates product.metadata with filename /
  // size / mime snapshot so the storefront can surface "download ready".
  uploadDigitalFile: (productId, file, config = {}) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post(`/products/${productId}/digital-file`, formData, {
      ...config,
      headers: {
        'Content-Type': 'multipart/form-data',
        ...(config.headers || {}),
      },
    });
  },

  // 2026-05-20 — Lightweight SKU uniqueness probe used by the live-check
  // hook in the wizard form fields. Backend: GET /api/products/check-sku.
  // Returns { available: bool, conflicting_product_id?: str, degraded?: bool }.
  // ``excludeProductId`` is set in edit-mode so the product keeps its own SKU.
  checkSkuAvailability: (sku, { excludeProductId, signal } = {}) =>
    api.get('/products/check-sku', {
      params: {
        sku,
        ...(excludeProductId ? { exclude_product_id: excludeProductId } : {}),
      },
      signal,
    }),
};
