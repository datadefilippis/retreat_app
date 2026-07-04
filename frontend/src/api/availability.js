/**
 * Availability API — scheduling rules, blocked slots, and free slot computation.
 */

import api from './client';

export const availabilityAPI = {
  // Rules
  listRules: (storeId, productId) => api.get('/availability/rules', {
    params: {
      ...(storeId ? { store_id: storeId } : {}),
      ...(productId ? { product_id: productId } : {}),
    },
  }),
  createRule: (data) => api.post('/availability/rules', data),
  deleteRule: (ruleId) => api.delete(`/availability/rules/${ruleId}`),

  // Blocked slots
  listBlocked: (dateFrom, dateTo, storeId, productId) =>
    api.get('/availability/blocked', { params: { date_from: dateFrom, date_to: dateTo, store_id: storeId, ...(productId ? { product_id: productId } : {}) } }),
  createBlocked: (data) => api.post('/availability/blocked', data),
  createBatchBlocked: (data) => api.post('/availability/blocked/batch', data),
  deleteBlocked: (slotId) => api.delete(`/availability/blocked/${slotId}`),
  deleteBlockedGroup: (groupId) => api.delete(`/availability/blocked/group/${groupId}`),

  // Computed free slots
  getSlots: (dateFrom, dateTo, storeId) =>
    api.get('/availability/slots', { params: { date_from: dateFrom, date_to: dateTo, store_id: storeId } }),
};
