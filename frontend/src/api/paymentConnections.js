import api from './client';

export const paymentConnectionsAPI = {
  list: () => api.get('/payment-connections'),
  getStatus: () => api.get('/payment-connections/status'),
  create: (data) => api.post('/payment-connections', data),
  update: (id, data) => api.patch(`/payment-connections/${id}`, data),
  // Express Connect (Account Links) — the only flow as of Block 6.
  // Legacy Standard OAuth methods (getStripeConnectUrl, stripeCallback)
  // were removed together with their backend endpoints.
  // Lotto S (6/10/2026): il paese dell'account (IT default) si sceglie prima
  expressStart: (data) => api.post('/payment-connections/stripe/express/start', data || {}),
  expressPaesi: () => api.get('/payment-connections/stripe/express/paesi'),
  // «Ricomincia col paese giusto»: solo su account mai completati
  expressRicomincia: (data) => api.post('/payment-connections/stripe/express/ricomincia', data),
  expressRefresh: () => api.post('/payment-connections/stripe/express/refresh'),
  expressComplete: () => api.post('/payment-connections/stripe/express/complete'),
  // Short-lived login URL into the merchant's own Stripe Express dashboard.
  // URL expires within minutes — caller should open immediately, not cache.
  expressDashboardLink: () =>
    api.post('/payment-connections/stripe/express/dashboard-link'),
};
