import api from './client';

export const exportAPI = {
  /**
   * Download cashflow data as CSV.
   * @param {'sales'|'expenses'|'purchases'|'fixed_costs'} type
   * @param {'30d'|'90d'|'12m'|'all'} period
   */
  downloadCashflow: async (type, period = 'all') => {
    const response = await api.get('/export/cashflow', {
      params: { type, period },
      responseType: 'blob',
    });

    // Extract filename from Content-Disposition header or build a default
    const disposition = response.headers['content-disposition'] || '';
    const match = disposition.match(/filename="?([^"]+)"?/);
    const filename = match ? match[1] : `${type}_export.csv`;

    // Trigger browser download
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },
};
