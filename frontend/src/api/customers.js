import api from './client';

export const customersAPI = {
  list: (activeOnly = true, limit = 200) =>
    api.get('/customers', { params: { active_only: activeOnly, limit } }),

  get: (customerId) =>
    api.get(`/customers/${customerId}`),

  create: (data) =>
    api.post('/customers', data),

  update: (customerId, updates) =>
    api.patch(`/customers/${customerId}`, updates),

  deactivate: (customerId) =>
    api.delete(`/customers/${customerId}`),
};
