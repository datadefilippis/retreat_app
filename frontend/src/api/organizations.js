import api from './client';

export const organizationsAPI = {
  getCurrent:       () => api.get('/organizations/current'),
  updateCurrent:    (data) => api.put('/organizations/current', data),
  // CH compliance v1: tells the UI whether the currency selector is
  // still mutable. Once the org has any orders, the backend forbids
  // changing currency to keep the audit trail consistent.
  getCurrencyInfo:  () => api.get('/organizations/current/currency-info'),
  // Sub-stream 2.4: which payment methods the connected provider has
  // enabled. The Settings page renders status (card / TWINT) plus a
  // deep-link to dashboard.stripe.com when TWINT is missing on a
  // CHF org. Backend is cached 5 min server-side already; pass
  // ``forceRefresh: true`` from the manual ↻ refresh button so the
  // merchant doesn't wait out the TTL after toggling a payment method
  // on their Stripe dashboard.
  getPaymentCapabilities: ({ forceRefresh = false } = {}) =>
    api.get('/organizations/current/payment-capabilities', {
      params: forceRefresh ? { force_refresh: true } : {},
    }),
  getTeam:          () => api.get('/organizations/team'),
  inviteUser:       (data) => api.post('/organizations/team/invite', data),
  updateUserRole:   (userId, role) => api.put(`/organizations/team/${userId}/role`, { role }),
  removeUser:       (userId) => api.delete(`/organizations/team/${userId}`),
  reactivateUser:   (userId) => api.post(`/organizations/team/${userId}/reactivate`),
};
