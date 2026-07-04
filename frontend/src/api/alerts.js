import api from './client';

export const alertsAPI = {
  list: (status, severity, limit = 50, category = null) => {
    const params = new URLSearchParams();
    if (status) params.append('status_filter', status);
    if (severity) params.append('severity_filter', severity);
    if (category) params.append('category_filter', category);
    params.append('limit', limit.toString());
    return api.get(`/alerts?${params}`);
  },

  getCounts: () => api.get('/alerts/count'),

  get: (id) => api.get(`/alerts/${id}`),

  updateStatus: (id, status) => api.put(`/alerts/${id}/status`, { status }),

  generate: () => api.post('/alerts/generate'),

  getPreferences: () => api.get('/alerts/preferences'),

  updatePreferences: (data) => api.put('/alerts/preferences', data)
};
