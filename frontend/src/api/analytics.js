import api from './client';

export const analyticsAPI = {
  getDateRange: () => api.get('/analytics/date-range'),
  
  getKPIs: (period = '30d', startDate, endDate) => {
    const params = new URLSearchParams({ period });
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    return api.get(`/analytics/kpis?${params}`);
  },
  
  getChartData: (period = '30d', startDate, endDate) => {
    const params = new URLSearchParams({ period });
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    return api.get(`/analytics/charts?${params}`);
  },
  
  getSummary: (period = '30d', startDate, endDate) => {
    const params = new URLSearchParams({ period });
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    return api.get(`/analytics/summary?${params}`);
  },
  
  getSalesByCategory: (period = '30d', startDate, endDate) => {
    const params = new URLSearchParams({ period });
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    return api.get(`/analytics/categories/sales?${params}`);
  },
  
  getExpensesByCategory: (period = '30d', startDate, endDate) => {
    const params = new URLSearchParams({ period });
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    return api.get(`/analytics/categories/expenses?${params}`);
  },
  
  getCategoryTrends: (categoryType = 'sales', period = '30d', startDate, endDate) => {
    const params = new URLSearchParams({ category_type: categoryType, period });
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    return api.get(`/analytics/categories/trends?${params}`);
  },

  // ── v2.1: Cashflow Monitor enriched endpoints ──────────────────────────────

  /**
   * Returns all standard KPI fields PLUS: fixed_costs_total, combined_expenses,
   * expense_ratio, burn_rate, top_expense_category.
   * Use this instead of getKPIs() on the CashflowModulePage.
   */
  getEnrichedKPIs: (period = '30d', startDate, endDate) => {
    const params = new URLSearchParams({ period });
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    return api.get(`/analytics/cashflow/enriched-kpis?${params}`);
  },

  /**
   * Returns [{date, sales, expenses, daily_net, cumulative}] sorted by date.
   * Powers the cumulative cashflow area chart.
   */
  getCumulativeCashflow: (period = '30d', startDate, endDate) => {
    const params = new URLSearchParams({ period });
    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    return api.get(`/analytics/cashflow/cumulative?${params}`);
  },
};

// ── Phase-3: Pre-computed KPI snapshots ───────────────────────────────────────
export const analyticsSnapshotAPI = {
  /**
   * Returns pre-computed KPI snapshots (faster than live /analytics/kpis).
   * Falls back gracefully if no snapshots exist yet.
   */
  getKPIsSnapshot: (moduleKey = 'cashflow_monitor', granularity = 'monthly', limit = 12) =>
    api.get('/analytics/kpis/snapshot', {
      params: { module_key: moduleKey, granularity, limit },
    }),
};
