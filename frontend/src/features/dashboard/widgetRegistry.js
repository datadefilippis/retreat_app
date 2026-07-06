/**
 * widgetRegistry — maps widget keys to their React components, data extractors
 * and layout hints. Used by DashboardPage to render pinned widgets dynamically.
 *
 * Convention:  "<module_key>:<widget_name>"
 *
 * Each entry:
 *   name           — human-readable label (shown in dashboard card header)
 *   moduleKey      — which module owns this widget (determines API call)
 *   component      — the React component to render
 *   dataSources    — array of source keys needed (default: ['overview'])
 *   dataExtractor  — fn(sources) → props to spread into component
 *                     sources = { overview: ..., charts: ..., alerts: ... }
 *   size           — 'full' (col-span-2) or 'half' (col-span-1)
 *
 * Multi-source support:
 *   Widgets declare which data sources they need via `dataSources`.
 *   The dashboard fetches each source via DATA_FETCHERS and passes the
 *   combined { [source]: data } object to dataExtractor.
 *   Existing widgets without dataSources default to ['overview'] and their
 *   dataExtractor receives { overview: overviewData } (backward compatible
 *   because we wrap the old extractors below).
 */
import { modulesAPI } from '../../api';
// Migrated from features/customers-light/DashboardWidgets.js during the
// Phase-3 single-brain consolidation. Same exported names so the
// widget registry keys (customers_light:kpi_strip, etc.) keep matching
// what's persisted in user dashboard preferences.
import { CustomerKPIStripWidget, TopCustomersWidget, SegmentChartWidget } from '../customer-insights/DashboardWidgets';


// ── Data Fetchers ──────────────────────────────────────────────────────────────
// Each key maps to a function (moduleKey, period, startDate, endDate) → Promise<data>.
// The dashboard calls the relevant fetchers based on pinned widgets' dataSources.

export const DATA_FETCHERS = {
  overview: (moduleKey, period, startDate, endDate) =>
    modulesAPI.getOverview(moduleKey, period, startDate, endDate)
      .then((res) => res.data),
};


// ── Widget registry (R4: restano i widget Customer Insights;
// i widget cashflow del vecchio BI sono stati rimossi) ──────────

export const WIDGET_REGISTRY = {
  // ── Customers Light widgets ─────────────────────────────────────────────────

  'customers_light:kpi_strip': {
    name: 'KPI Clienti',
    nameKey: 'widgets.header_kpi',
    nameNS: 'customers_light',
    moduleKey: 'customers_light',
    component: CustomerKPIStripWidget,
    dataSources: ['overview'],
    dataExtractor: (sources) => ({
      kpis: sources.overview?.has_data ? sources.overview?.kpis : null,
      loading: false,
    }),
    size: 'full',
  },

  'customers_light:top_customers': {
    name: 'Top Clienti',
    nameKey: 'widgets.header_top_customers',
    nameNS: 'customers_light',
    moduleKey: 'customers_light',
    component: TopCustomersWidget,
    dataSources: ['overview'],
    dataExtractor: (sources) => ({
      customers: sources.overview?.has_data ? sources.overview?.top_customers : [],
      loading: false,
    }),
    size: 'full',
  },

  'customers_light:segment_chart': {
    name: 'Segmenti Clienti',
    nameKey: 'widgets.header_segments',
    nameNS: 'customers_light',
    moduleKey: 'customers_light',
    component: SegmentChartWidget,
    dataSources: ['overview'],
    dataExtractor: (sources) => ({
      segments: sources.overview?.has_data ? sources.overview?.segments : [],
      loading: false,
    }),
    size: 'half',
  },

};

/**
 * Get unique module keys from a list of pinned widget keys.
 * Used by DashboardPage to know which modules need data fetching.
 */
export function getRequiredModules(widgetKeys) {
  const modules = new Set();
  for (const key of widgetKeys) {
    const entry = WIDGET_REGISTRY[key];
    if (entry) modules.add(entry.moduleKey);
  }
  return [...modules];
}

/**
 * Collect all unique (moduleKey, source) pairs needed by pinned widgets.
 * Returns a Map<moduleKey, Set<source>>.
 */
export function getRequiredSources(widgetKeys) {
  const required = new Map();
  for (const key of widgetKeys) {
    const entry = WIDGET_REGISTRY[key];
    if (!entry) continue;
    const sources = entry.dataSources || ['overview'];
    if (!required.has(entry.moduleKey)) required.set(entry.moduleKey, new Set());
    sources.forEach((s) => required.get(entry.moduleKey).add(s));
  }
  return required;
}

/**
 * Return all widget keys available for a given module.
 * Used to list available widgets in the module page.
 */
export function getWidgetKeysForModule(moduleKey) {
  return Object.entries(WIDGET_REGISTRY)
    .filter(([, v]) => v.moduleKey === moduleKey)
    .map(([k]) => k);
}
