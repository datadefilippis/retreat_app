import api from './client';

export const fixedCostsAPI = {
  list: ({ activeOnly = true, category, limit = 200 } = {}) => {
    const params = { active_only: activeOnly, limit };
    if (category) params.category = category;
    return api.get('/fixed-costs', { params });
  },

  get: (costId) =>
    api.get(`/fixed-costs/${costId}`),

  create: (data) =>
    api.post('/fixed-costs', data),

  createBulk: (records) =>
    api.post('/fixed-costs/bulk', records),

  update: (costId, updates) =>
    api.patch(`/fixed-costs/${costId}`, updates),

  delete: (costId) =>
    api.delete(`/fixed-costs/${costId}`),
};
