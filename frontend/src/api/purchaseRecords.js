import api from './client';

export const purchaseRecordsAPI = {
  list: ({ startDate, endDate, supplierId, limit = 200 } = {}) => {
    const params = {};
    if (startDate) params.start_date = startDate;
    if (endDate)   params.end_date   = endDate;
    if (supplierId) params.supplier_id = supplierId;
    params.limit = limit;
    return api.get('/purchase-records', { params });
  },

  get: (recordId) =>
    api.get(`/purchase-records/${recordId}`),

  create: (data) =>
    api.post('/purchase-records', data),

  delete: (recordId) =>
    api.delete(`/purchase-records/${recordId}`),
};
