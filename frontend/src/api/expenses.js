import api from './client';

function _csvOrUndef(arr) {
  return Array.isArray(arr) && arr.length > 0 ? arr.join(',') : undefined;
}


export const expensesAPI = {
  // 2026-05-20 — Default limit raised to 5000 (backend cap on
  // GET /api/expenses is le=5000). Reason and migration path
  // identical to salesAPI.list — see that file's header comment.
  list: ({ limit = 5000 } = {}) =>
    api.get('/expenses', { params: { limit } }),

  // Phase 2 (2026-05-20) — paginated + server-side filtered list.
  // See salesAPI.search for envelope shape + design notes.
  search: ({
    dateFrom,
    dateTo,
    categories,
    suppliers,
    supplierIds,
    source,
    amountMin,
    amountMax,
    q,
    page = 1,
    pageSize = 50,
  } = {}) =>
    api.get('/expenses/search', {
      params: {
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        categories: _csvOrUndef(categories),
        suppliers: _csvOrUndef(suppliers),
        supplier_ids: _csvOrUndef(supplierIds),
        source: source || undefined,
        amount_min: amountMin ?? undefined,
        amount_max: amountMax ?? undefined,
        q: q || undefined,
        page,
        page_size: pageSize,
      },
    }),

  create: (records) => api.post('/expenses', records),
  update: (id, updates) => api.patch(`/expenses/${id}`, updates),
  delete: (id) => api.delete(`/expenses/${id}`),
  getCategories: () => api.get('/expenses/categories'),
  getSuppliers: () => api.get('/expenses/suppliers'),
};
