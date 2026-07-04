import api from './client';

export const ordersAPI = {
  // Fase 2 S2 (retreat) — segna una scadenza pagata fuori piattaforma
  markSchedulePaidManual: (orderId, rowSeq, note) =>
    api.post(`/orders/${orderId}/schedule/${rowSeq}/mark-paid-manual`, { note }),
  list: (status, limit = 200) =>
    api.get('/orders', { params: { status, limit } }),
  get: (orderId) =>
    api.get(`/orders/${orderId}`),
  create: (data) =>
    api.post('/orders', data),
  update: (orderId, data) =>
    api.patch(`/orders/${orderId}`, data),
  confirm: (orderId) =>
    api.post(`/orders/${orderId}/confirm`),
  // Fase 6a: admin-triggered pull of current payment state from Stripe.
  // Used when a webhook was lost / late and the order appears stuck in draft.
  verifyPayment: (orderId) =>
    api.post(`/orders/${orderId}/verify-payment`),
  cancel: (orderId) =>
    api.post(`/orders/${orderId}/cancel`),
  complete: (orderId) =>
    api.post(`/orders/${orderId}/complete`),
  getUnseenCount: () =>
    api.get('/orders/unseen-count'),
  markSeen: () =>
    api.post('/orders/mark-seen'),
  getSummary: () =>
    api.get('/orders/summary'),
  getDashboard: (storeId) =>
    api.get('/orders/dashboard', { params: storeId ? { store_id: storeId } : {} }),
  updateFulfillment: (orderId, status, extras = {}) =>
    api.post(`/orders/${orderId}/fulfillment`, { status, ...extras }),
  markPaid: (orderId) =>
    api.post(`/orders/${orderId}/mark-paid`),
  markUnpaid: (orderId) =>
    api.post(`/orders/${orderId}/mark-unpaid`),
  downloadReceipt: (orderId) =>
    api.get(`/orders/${orderId}/receipt`, { responseType: 'blob' }),
  // Admin order management consolidation: aggregator for IssuedTicket/Booking/Reservation
  getIssued: (orderId) =>
    api.get(`/orders/${orderId}/issued`),
  // kind: 'ticket' | 'booking' | 'reservation'
  // tickets use code, bookings/reservations accept id (bookings also accept code)
  resendIssued: (kind, idOrCode) => {
    if (kind === 'ticket') return api.post(`/tickets/${idOrCode}/resend-email`);
    if (kind === 'booking') return api.post(`/issued-bookings/${idOrCode}/resend`);
    if (kind === 'reservation') return api.post(`/issued-reservations/${idOrCode}/resend`);
    return Promise.reject(new Error(`Unknown issued kind: ${kind}`));
  },
  pos: (data) =>
    api.post('/orders/pos', data),
  importOrders: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/orders/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  importOrdersWithMapping: (tempUploadId, columnMapping) => {
    const formData = new FormData();
    formData.append('temp_upload_id', tempUploadId);
    formData.append('column_mapping', JSON.stringify(columnMapping));
    return api.post('/orders/import-with-mapping', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
};
