import api from './client';

export const modulesAPI = {
  listAvailable: () => api.get('/modules/available'),
  listActive: () => api.get('/modules/active'),
  getStatus: (moduleKey) => api.get(`/modules/${moduleKey}/status`),
  activate: (moduleKey) => api.post(`/modules/${moduleKey}/activate`),
  deactivate: (moduleKey) => api.post(`/modules/${moduleKey}/deactivate`),

  /**
   * Returns the composite overview for a module: KPIs, daily chart series,
   * top categories (sales + expenses), open alerts summary, and the last
   * AI insight — all in a single round-trip.
   *
   * @param {string} moduleKey   e.g. "cashflow_monitor"
   * @param {string} period      "7d" | "30d" | "90d" | "custom"
   * @param {string} [startDate] ISO date, required when period="custom"
   * @param {string} [endDate]   ISO date, required when period="custom"
   */
  getOverview: (moduleKey, period = '30d', startDate, endDate) => {
    const params = new URLSearchParams({ period });
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    return api.get(`/modules/${moduleKey}/overview?${params}`);
  },
};
