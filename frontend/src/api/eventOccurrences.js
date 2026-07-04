import api from './client';

export const eventOccurrencesAPI = {
  list: (productId) =>
    api.get('/event-occurrences', { params: { product_id: productId } }),
  get: (occurrenceId) =>
    api.get(`/event-occurrences/${occurrenceId}`),
  create: (data) =>
    api.post('/event-occurrences', data),
  update: (occurrenceId, updates) =>
    api.patch(`/event-occurrences/${occurrenceId}`, updates),
  // G1 admin Eventi home — returns occurrences with product + tier_count.
  // Supported query params: { when, status, q, limit }.
  listAdmin: (params = {}) =>
    api.get('/event-occurrences/admin/list', { params }),
  // G3 — revenue + per-tier breakdown + last-30d sales timeline.
  analytics: (occurrenceId) =>
    api.get(`/event-occurrences/${occurrenceId}/analytics`),
  // G3 — CSV attendance export URL; caller opens it as a download
  // (can't use axios blob easily due to auth header interception;
  // using window.open with a signed path is also avoided). The
  // Dashboard uses a tiny fetch+blob helper below.
  ticketsCsvUrl: (occurrenceId) =>
    `/event-occurrences/${occurrenceId}/tickets-csv`,
  // Fase 2 S2 (retreat) — dashboard incassi: aggregato + dettaglio per ordine
  payments: (occurrenceId) =>
    api.get(`/event-occurrences/${occurrenceId}/payments`),
  // Fase 2 S3 — annullo ritiro con cascata rimborsi (conferma esplicita)
  cancelCascade: (occurrenceId) =>
    api.post(`/event-occurrences/${occurrenceId}/cancel-cascade`, { confirm: true }),
  paymentsCsvUrl: (occurrenceId) =>
    `/event-occurrences/${occurrenceId}/payments/export.csv`,
  // G2 — atomic create: product + occurrence + tiers in one call.
  // Body: { product:{...}, occurrence:{...}, tiers:[...] }
  // Returns: { product_id, occurrence_id, tier_ids, slug }
  wizardCreate: (payload) =>
    api.post('/event-occurrences/wizard', payload),
  // G6 — get a wizard-ready payload derived from an existing event.
  // Used to pre-fill the EventWizard in "Duplica" mode.
  duplicateData: (occurrenceId) =>
    api.post(`/event-occurrences/${occurrenceId}/duplicate`),
  // Upload (or replace) the cover image for an occurrence.
  // 2026-05-20 — Accepts an optional ``config`` so callers can pass
  // ``{ signal: abortController.signal }`` and cancel the upload on
  // unmount / navigation (paired with useAbortableUpload).
  uploadCoverImage: (occurrenceId, file, config = {}) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post(`/event-occurrences/${occurrenceId}/cover-image`, formData, {
      ...config,
      headers: {
        'Content-Type': 'multipart/form-data',
        ...(config.headers || {}),
      },
    });
  },
};

export const eventTicketTiersAPI = {
  list: (occurrenceId) =>
    api.get(`/event-occurrences/${occurrenceId}/tiers`),
  create: (occurrenceId, data) =>
    api.post(`/event-occurrences/${occurrenceId}/tiers`, data),
  update: (occurrenceId, tierId, updates) =>
    api.patch(`/event-occurrences/${occurrenceId}/tiers/${tierId}`, updates),
  remove: (occurrenceId, tierId) =>
    api.delete(`/event-occurrences/${occurrenceId}/tiers/${tierId}`),
};
