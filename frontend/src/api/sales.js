import api from './client';

// ─── helpers ─────────────────────────────────────────────────────────
// CSV-or-undefined: arrays become "A,B,C", anything empty becomes
// undefined (so axios omits the param). Mirrors the backend
// ``_csv_to_list`` helper — empty CSV → None → "no filter".
function _csvOrUndef(arr) {
  return Array.isArray(arr) && arr.length > 0 ? arr.join(',') : undefined;
}


export const salesAPI = {
  // 2026-05-20 — Default limit raised to 5000 (backend cap on
  // GET /api/sales is le=5000) so the cashflow Entrate table can
  // show every record an SME may realistically have, not just the
  // first 500 the previous implicit default returned. The argument
  // is an optional opts object — existing call sites passing nothing
  // keep working unchanged but now fetch up to 5000 records.
  //
  // This LEGACY list endpoint is still used by dashboard widgets +
  // analytics callers that expect the bare-array response shape.
  // For paginated + filtered table queries the Section components
  // call ``.search()`` instead (Phase 2, see below).
  list: ({ limit = 5000 } = {}) =>
    api.get('/sales', { params: { limit } }),

  // Phase 2 (2026-05-20) — paginated + server-side filtered list.
  //
  // Response envelope: ``{items, total, page, page_size, has_more}``.
  // All filter args are optional; multi-value ones are arrays that
  // serialize to CSV (mirrors the backend ``_csv_to_list`` parser).
  // ``source`` is "manual" | "file" only (backend Pydantic enum).
  //
  // Caps enforced by the backend: page_size ≤ 200, page ≤ 10000,
  // q ≤ 100 chars. Client should respect them but the server is
  // the source of truth.
  search: ({
    dateFrom,
    dateTo,
    dueDateFrom,
    dueDateTo,
    categories,
    channels,
    customerIds,
    paymentStatus,
    source,
    amountMin,
    amountMax,
    q,
    page = 1,
    pageSize = 50,
  } = {}) =>
    api.get('/sales/search', {
      params: {
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        due_date_from: dueDateFrom || undefined,
        due_date_to: dueDateTo || undefined,
        categories: _csvOrUndef(categories),
        channels: _csvOrUndef(channels),
        customer_ids: _csvOrUndef(customerIds),
        payment_status: _csvOrUndef(paymentStatus),
        source: source || undefined,
        amount_min: amountMin ?? undefined,
        amount_max: amountMax ?? undefined,
        q: q || undefined,
        page,
        page_size: pageSize,
      },
    }),

  create: (records) => api.post('/sales', records),
  update: (id, updates) => api.patch(`/sales/${id}`, updates),
  delete: (id) => api.delete(`/sales/${id}`),
  getCategories: () => api.get('/sales/categories'),
  getChannels: () => api.get('/sales/channels'),
};
