import api from './client';

export const couponsAPI = {
  list: (storeId) => api.get('/coupons', { params: storeId ? { store_id: storeId } : {} }),
  create: (data) => api.post('/coupons', data),
  update: (couponId, data) => api.patch(`/coupons/${couponId}`, data),
  delete: (couponId) => api.delete(`/coupons/${couponId}`),
};
