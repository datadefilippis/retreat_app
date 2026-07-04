import api from './client';

export const digestsAPI = {
  generate: (period = 7, digestType = 'weekly', format = 'report', startDate = null, endDate = null) => {
    const params = new URLSearchParams();
    // When custom dates are provided, don't send period (backend calculates it)
    if (startDate && endDate) {
      params.append('start_date', startDate);
      params.append('end_date', endDate);
    } else {
      params.append('period', period);
    }
    params.append('digest_type', digestType);
    params.append('format', format);
    return api.post(`/digests/generate?${params.toString()}`);
  },

  list: (digestType = null, limit = 10) => {
    const params = new URLSearchParams();
    if (digestType) params.append('digest_type', digestType);
    params.append('limit', limit);
    return api.get(`/digests?${params.toString()}`);
  },

  latest: (digestType = 'weekly') =>
    api.get(`/digests/latest?digest_type=${digestType}`),

  getById: (id) => api.get(`/digests/${id}`),

  downloadPdf: (id) =>
    api.get(`/digests/${id}/pdf`, { responseType: 'blob' }),
};
