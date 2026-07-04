import api from './client';

export const insightsAPI = {
  list: (moduleKey, limit = 20) => {
    const params = new URLSearchParams();
    if (moduleKey) params.append('module_key', moduleKey);
    params.append('limit', limit.toString());
    return api.get(`/insights?${params}`);
  },
  
  getLatest: (moduleKey = 'cashflow_monitor') => 
    api.get(`/insights/latest?module_key=${moduleKey}`),
  
  generate: (period = '30d', startDate, endDate) => {
    const params = new URLSearchParams({ period });
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    return api.post(`/insights/generate?${params}`);
  },
  
  get: (id) => api.get(`/insights/${id}`)
};
