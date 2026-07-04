import api from './client';

export const productCatalogAPI = {
  getOverview: (period = '30d', startDate, endDate) =>
    api.get('/modules/product_catalog/overview', {
      params: { period, start_date: startDate, end_date: endDate },
    }),
  getMetrics: (category, abcClass) =>
    api.get('/modules/product-catalog/metrics', {
      params: { category, abc_class: abcClass },
    }),
  getProductMetric: (productId) =>
    api.get(`/modules/product-catalog/metrics/${productId}`),
  getAbcDistribution: () =>
    api.get('/modules/product-catalog/abc'),
  refresh: () =>
    api.post('/modules/product-catalog/refresh'),

  // ── Wave 1 (W1.S3) — Cost configuration support ────────────────────────
  /**
   * List purchase categories actually used by the org's purchase records.
   * Powers the dropdown in CostSourceEditor so the merchant never types
   * (and never mistypes) a category name.
   *
   * @returns {Promise<{data: {categories: Array<{name, units, purchase_count, last_seen}>}}>}
   */
  getCostCategories: () =>
    api.get('/modules/product-catalog/cost-categories'),

  /**
   * Resolve a hypothetical cost_source WITHOUT saving. Used by the live
   * preview in CostSourceEditor: while the merchant tweaks components,
   * the UI calls this endpoint and renders the resolver's output.
   *
   * @param {Object} payload
   * @param {Object} payload.cost_source     CostSource shape (method + components)
   * @param {string} [payload.product_id]    needed for auto-share computation
   * @param {string} [payload.product_category]   needed for org_average scope=same_category
   * @param {string} [payload.product_item_type]  needed for org_average scope=same_item_type
   */
  previewCost: (payload) =>
    api.post('/modules/product-catalog/cost-preview', payload),

  /**
   * Resolve the CURRENT saved cost_source of an existing product.
   */
  previewSavedCost: (productId) =>
    api.get(`/modules/product-catalog/cost-preview/${productId}`),

  /**
   * IntelligenceBanner (IB.*) — run every health check on the org's
   * product catalog and return the issues found.
   *
   * @param {string} period — '7d' | '30d' | '90d' | '12m' | 'all'
   */
  healthCheck: (period = '30d') =>
    api.get('/modules/product-catalog/health-check', { params: { period } }),
};
