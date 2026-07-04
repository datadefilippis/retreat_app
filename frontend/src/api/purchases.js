import api from './client';

function _csvOrUndef(arr) {
  return Array.isArray(arr) && arr.length > 0 ? arr.join(',') : undefined;
}


export const purchasesAPI = {
  // 2026-05-20 — Default limit raised to 5000 (backend cap on
  // GET /api/purchases is le=5000). First positional arg
  // ``supplierId`` preserved for backward compat with the single
  // existing caller (PurchasesSection.js). The opts object adds
  // ``limit`` so future call sites can override without dropping
  // the supplier filter.
  list: (supplierId = null, { limit = 5000 } = {}) =>
    api.get('/purchases', {
      params: {
        limit,
        ...(supplierId ? { supplier_id: supplierId } : {}),
      },
    }),

  // Phase 2 (2026-05-20) — paginated + server-side filtered list.
  // See salesAPI.search. Note: ``q`` searches BOTH description AND
  // invoice_number on the backend (matches the single-search-box UX).
  search: ({
    dateFrom,
    dateTo,
    dueDateFrom,
    dueDateTo,
    supplierNames,
    supplierIds,
    productIds,
    categories,
    categoriesMacro,
    units,
    ivaValues,
    paymentStatus,
    source,
    quantityMin,
    quantityMax,
    unitPriceMin,
    unitPriceMax,
    q,
    page = 1,
    pageSize = 50,
  } = {}) =>
    api.get('/purchases/search', {
      params: {
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        due_date_from: dueDateFrom || undefined,
        due_date_to: dueDateTo || undefined,
        supplier_names: _csvOrUndef(supplierNames),
        supplier_ids: _csvOrUndef(supplierIds),
        product_ids: _csvOrUndef(productIds),
        categories: _csvOrUndef(categories),
        categories_macro: _csvOrUndef(categoriesMacro),
        units: _csvOrUndef(units),
        iva_values: _csvOrUndef(ivaValues),
        payment_status: _csvOrUndef(paymentStatus),
        source: source || undefined,
        quantity_min: quantityMin ?? undefined,
        quantity_max: quantityMax ?? undefined,
        unit_price_min: unitPriceMin ?? undefined,
        unit_price_max: unitPriceMax ?? undefined,
        q: q || undefined,
        page,
        page_size: pageSize,
      },
    }),

  create: (records) => api.post('/purchases', records),
  update: (id, updates) => api.patch(`/purchases/${id}`, updates),
  delete: (id) => api.delete(`/purchases/${id}`),
  getSuppliers: () => api.get('/purchases/suppliers'),
  getCategories: () => api.get('/purchases/categories'),
  getCategoriesMacro: () => api.get('/purchases/categories-macro'),
};
