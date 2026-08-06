import api from './client';

export const calendarAPI = {
  getItems: (year, month, productId) =>
    api.get('/calendar/items', { params: { year, month, ...(productId ? { product_id: productId } : {}) } }),
  // TA2 — chiusura appuntamento dal calendario (svolta / non presentato)
  completeBooking: (codeOrId) => api.post(`/issued-bookings/${codeOrId}/complete`),
  noShowBooking: (codeOrId) => api.post(`/issued-bookings/${codeOrId}/no-show`),
};
