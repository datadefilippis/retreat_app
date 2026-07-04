import api from './client';

export const suppliersAPI = {
  list: (activeOnly = true, limit = 200) =>
    api.get('/suppliers', { params: { active_only: activeOnly, limit } }),

  get: (supplierId) =>
    api.get(`/suppliers/${supplierId}`),

  create: (data) =>
    api.post('/suppliers', data),

  update: (supplierId, updates) =>
    api.patch(`/suppliers/${supplierId}`, updates),

  deactivate: (supplierId) =>
    api.delete(`/suppliers/${supplierId}`),

  getMetrics: () =>
    api.get('/suppliers/metrics'),
};
