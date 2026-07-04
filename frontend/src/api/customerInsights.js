/**
 * Customer Insights API client.
 *
 * Talks to the backend module landed in Phase 1
 * (modules.customer_insights.router). All endpoints under
 * /api/customer-insights/*.
 *
 * The legacy customers_light client (api/modules/customers_light)
 * stays in place for AI tools and the legacy /customers-legacy route.
 */
import api from './client';

export const customerInsightsAPI = {
  /**
   * Period-aware overview: KPIs with delta, segments, concentration,
   * suggested_actions.
   *
   * @param {object} opts
   * @param {string} [opts.period='30d']  7d / 30d / 90d / 180d / 12m / 24m / all / custom
   * @param {string} [opts.customStart]   ISO date — only when period=custom
   * @param {string} [opts.customEnd]     ISO date — only when period=custom
   */
  getOverview: ({ period = '30d', customStart, customEnd } = {}) => {
    const params = { period };
    if (period === 'custom') {
      if (customStart) params.custom_start = customStart;
      if (customEnd) params.custom_end = customEnd;
    }
    return api.get('/customer-insights/overview', { params });
  },

  /**
   * Paginated customer list with filter chain.
   * Filters apply to all-time materialised metrics — period selector
   * affects only the overview KPIs by design.
   */
  getCustomers: ({
    segment,
    customerStatus,
    minRevenue,
    hasEmail,
    hasPhone,
    // CI-admin-vis: two new optional filters — leave undefined / null
    // to skip filtering (legacy behaviour). The backend treats only
    // ``true`` / ``false`` as active filters.
    hasAccount,
    marketingOptedIn,
    search,
    page = 1,
    pageSize = 50,
  } = {}) => {
    const params = { page, page_size: pageSize };
    if (segment) params.segment = segment;
    if (customerStatus) params.customer_status = customerStatus;
    if (minRevenue && minRevenue > 0) params.min_revenue = minRevenue;
    if (hasEmail !== undefined && hasEmail !== null) params.has_email = hasEmail;
    if (hasPhone !== undefined && hasPhone !== null) params.has_phone = hasPhone;
    if (hasAccount !== undefined && hasAccount !== null) params.has_account = hasAccount;
    if (marketingOptedIn !== undefined && marketingOptedIn !== null) {
      params.marketing_opted_in = marketingOptedIn;
    }
    if (search) params.search = search;
    return api.get('/customer-insights/customers', { params });
  },

  /**
   * Cohort retention table.
   * @param {object} opts
   * @param {'month'|'quarter'|'week'} [opts.bucket='month']
   * @param {number} [opts.horizon=12]
   * @param {string} [opts.since]  ISO date floor
   */
  getCohorts: ({ bucket = 'month', horizon = 12, since } = {}) => {
    const params = { bucket, horizon };
    if (since) params.since = since;
    return api.get('/customer-insights/cohorts', { params });
  },

  /** Customer drill-down timeline (orders + sales records merged DESC). */
  getCustomerTimeline: (customerId, { limit = 50 } = {}) =>
    api.get(`/customer-insights/customer/${customerId}/timeline`, {
      params: { limit },
    }),

  /**
   * Download the filtered customer list as CSV.
   *
   * Goes through axios so the JWT Bearer token gets attached by the
   * client.js interceptor. ``window.open`` would have skipped the
   * Authorization header entirely and the backend would 403.
   *
   * Returns a Promise that resolves once the browser has triggered
   * the download. Errors propagate so the caller can surface them in
   * the UI.
   */
  exportCustomers: async ({
    segment,
    customerStatus,
    minRevenue,
    hasEmail,
    hasPhone,
    hasAccount,
    marketingOptedIn,
    search,
    filename = 'customers_export.csv',
  } = {}) => {
    const params = {};
    if (segment) params.segment = segment;
    if (customerStatus) params.customer_status = customerStatus;
    if (minRevenue && minRevenue > 0) params.min_revenue = minRevenue;
    if (hasEmail !== undefined && hasEmail !== null) params.has_email = hasEmail;
    if (hasPhone !== undefined && hasPhone !== null) params.has_phone = hasPhone;
    // CI-admin-vis: include the two new filters in the export so the
    // CSV is consistent with whatever the merchant sees in the table.
    if (hasAccount !== undefined && hasAccount !== null) params.has_account = hasAccount;
    if (marketingOptedIn !== undefined && marketingOptedIn !== null) {
      params.marketing_opted_in = marketingOptedIn;
    }
    if (search) params.search = search;

    const res = await api.get('/customer-insights/export', {
      params,
      responseType: 'blob',
    });

    // Trigger download via temporary <a href="blob:..." download>.
    // Must revoke the blob URL afterwards to release memory.
    const blob = new Blob([res.data], { type: 'text/csv;charset=utf-8' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  },

  /** Log a customer outreach action (email/whatsapp/task/tag). */
  logAction: ({ customerId, channel, template, status = 'opened' }) =>
    api.post('/customer-insights/actions/log', {
      customer_id: customerId,
      channel,
      template: template || null,
      status,
    }),

  /**
   * Phase 3 — build a deep-link URL (mailto / wa.me) for a customer +
   * template. Backend renders the localised subject/body, builds the
   * URL, and logs the click in audit_logs in the same call.
   *
   * Frontend usage:
   *   const res = await customerInsightsAPI.buildOutreach({...});
   *   window.open(res.data.url, '_blank');
   */
  buildOutreach: ({ customerId, channel, template, locale = 'it' }) =>
    api.post('/customer-insights/actions/outreach', {
      customer_id: customerId,
      channel,
      template,
      locale,
    }),

  /** List available outreach templates for the picker. */
  listOutreachTemplates: ({ locale = 'it' } = {}) =>
    api.get('/customer-insights/actions/templates', { params: { locale } }),
};
