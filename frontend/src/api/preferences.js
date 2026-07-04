import api from './client';

export const preferencesAPI = {
  getDashboard: () => api.get('/preferences/dashboard'),
  updateDashboard: (widgets) => api.patch('/preferences/dashboard', { widgets }),
};
