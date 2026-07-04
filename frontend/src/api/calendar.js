import api from './client';

export const calendarAPI = {
  getItems: (year, month, productId) =>
    api.get('/calendar/items', { params: { year, month, ...(productId ? { product_id: productId } : {}) } }),
};
