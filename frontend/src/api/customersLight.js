/**
 * Customers Light API client.
 *
 * Module-specific endpoints for customer intelligence analytics.
 * Customer profile CRUD stays on customersAPI (/api/customers/*).
 */
import api from './client';

export const customersLightAPI = {
  // Overview is served by the platform dispatcher: modulesAPI.getOverview('customers_light')
  // Module-specific endpoints only below.

  getMetrics: (segment, limit = 200) => {
    const params = new URLSearchParams({ limit: String(limit) });
    if (segment) params.append('segment', segment);
    return api.get(`/modules/customers_light/metrics?${params}`);
  },

  getSegments: () =>
    api.get('/modules/customers_light/segments'),

  getConcentration: (topN = 10) =>
    api.get(`/modules/customers_light/concentration?top_n=${topN}`),

  refresh: () =>
    api.post('/modules/customers_light/refresh'),
};
