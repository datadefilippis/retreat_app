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
import { modulesAPI, analyticsAPI, alertsAPI } from '../../api';
import { KPIStrip } from '../cashflow/components/KPIStrip';
// Migrated from features/customers-light/DashboardWidgets.js during the
// Phase-3 single-brain consolidation. Same exported names so the
// widget registry keys (customers_light:kpi_strip, etc.) keep matching
// what's persisted in user dashboard preferences.
import { CustomerKPIStripWidget, TopCustomersWidget, SegmentChartWidget } from '../customer-insights/DashboardWidgets';
import {
  SalesExpensesChart,
  NetCashflowChart,
  CumulativeCashflowChart,
  DetailedTrendsCharts,
} from '../cashflow/components/CashflowCharts';
import { CategoryPieCharts, CategoryBarCharts } from '../cashflow/components/CategoryCharts';
import { FixedVsVariableChart } from '../cashflow/components/FixedCostsTab';
import { LatestInsightWidget, AlertsSummaryWidget } from '../cashflow/components/DashboardWidgets';
import { RevenueFlowChart, ParetoFornitori, ComposizioneUscite } from '../cashflow/components/AnalisiTab';
import { AgingChart, TimelineChart, CashForecastChart } from '../cashflow/components/ScadenzarioTab';
import { HealthScoreGauge } from '../cashflow/components/HealthScoreGauge';
import { PurchaseDistributionChart } from '../cashflow/components/PurchaseDistributionChart';


// ── Data Fetchers ──────────────────────────────────────────────────────────────
// Each key maps to a function (moduleKey, period, startDate, endDate) → Promise<data>.
// The dashboard calls the relevant fetchers based on pinned widgets' dataSources.

export const DATA_FETCHERS = {
  overview: (moduleKey, period, startDate, endDate) =>
    modulesAPI.getOverview(moduleKey, period, startDate, endDate)
      .then((res) => res.data),
  charts: (_moduleKey, period, startDate, endDate) =>
    analyticsAPI.getChartData(period, startDate, endDate)
      .then((res) => res.data),
  alerts: (moduleKey) =>
    alertsAPI.list(null, null, 50)
      .then((res) => (res.data || []).filter((a) => a.module_key === moduleKey)),
};


// ── Cashflow Monitor widgets ────────────────────────────────────────────────────

export const WIDGET_REGISTRY = {
  // KPI strip (full width)
  'cashflow_monitor:kpi_strip': {
    name: 'KPI Cashflow',
    nameKey: 'widgets.header_kpi',
    nameNS: 'cashflow_monitor',
    moduleKey: 'cashflow_monitor',
    component: KPIStrip,
    dataSources: ['overview'],
    dataExtractor: (sources) => ({
      kpis: sources.overview?.kpis || {},
      loading: false,
    }),
    size: 'full',
  },

  // Charts (half width each)
  'cashflow_monitor:sales_expenses_chart': {
    name: 'Ricavi vs Spese',
    nameKey: 'widgets.header_sales_expenses',
    nameNS: 'cashflow_monitor',
    moduleKey: 'cashflow_monitor',
    component: SalesExpensesChart,
    dataSources: ['overview'],
    dataExtractor: (sources) => ({
      data: sources.overview?.charts?.daily_series || [],
      loading: false,
    }),
    size: 'half',
  },

  'cashflow_monitor:net_cashflow_chart': {
    name: 'Risultato Giornaliero',
    nameKey: 'widgets.header_net_cashflow',
    nameNS: 'cashflow_monitor',
    moduleKey: 'cashflow_monitor',
    component: NetCashflowChart,
    dataSources: ['overview'],
    dataExtractor: (sources) => ({
      data: sources.overview?.charts?.daily_series || [],
      loading: false,
    }),
    size: 'half',
  },

  'cashflow_monitor:cumulative_chart': {
    name: 'Cashflow Cumulativo',
    nameKey: 'widgets.header_cumulative',
    nameNS: 'cashflow_monitor',
    moduleKey: 'cashflow_monitor',
    component: CumulativeCashflowChart,
    dataSources: ['overview'],
    dataExtractor: (sources) => ({
      data: sources.overview?.charts?.daily_series || [],
      loading: false,
    }),
    size: 'half',
  },

  // Category charts (full width — contain 2 sub-charts side by side)
  'cashflow_monitor:category_pie': {
    name: 'Categorie (Torta)',
    nameKey: 'widgets.header_category_pie',
    nameNS: 'cashflow_monitor',
    moduleKey: 'cashflow_monitor',
    component: CategoryPieCharts,
    dataSources: ['overview'],
    dataExtractor: (sources) => ({
      salesCategories: { categories: sources.overview?.categories?.top_sales || [] },
      expensesCategories: { categories: sources.overview?.categories?.top_expenses || [] },
      loading: false,
    }),
    size: 'full',
  },

  'cashflow_monitor:category_bar': {
    name: 'Categorie (Classifica)',
    nameKey: 'widgets.header_category_bar',
    nameNS: 'cashflow_monitor',
    moduleKey: 'cashflow_monitor',
    component: CategoryBarCharts,
    dataSources: ['overview'],
    dataExtractor: (sources) => ({
      salesCategories: { categories: sources.overview?.categories?.top_sales || [] },
      expensesCategories: { categories: sources.overview?.categories?.top_expenses || [] },
      loading: false,
    }),
    size: 'full',
  },

  // ── NEW: previously missing widgets ─────────────────────────────────────────

  // Detailed Trends with 7-day MA (full width — 2 charts side by side)
  'cashflow_monitor:detailed_trends': {
    name: 'Trend con Media Mobile',
    nameKey: 'widgets.header_detailed_trends',
    nameNS: 'cashflow_monitor',
    moduleKey: 'cashflow_monitor',
    component: DetailedTrendsCharts,
    dataSources: ['charts'],
    dataExtractor: (sources) => ({
      data: sources.charts || [],
      loading: false,
    }),
    size: 'full',
  },

  // Fixed vs Variable costs comparison (half width)
  'cashflow_monitor:fixed_vs_variable': {
    name: 'Fisso vs Variabile',
    nameKey: 'widgets.header_fixed_variable',
    nameNS: 'cashflow_monitor',
    moduleKey: 'cashflow_monitor',
    component: FixedVsVariableChart,
    dataSources: ['overview'],
    dataExtractor: (sources) => ({
      fixedCostsTotal: sources.overview?.kpis?.fixed_costs_total,
      variableExpenses: sources.overview?.kpis?.total_expenses,
      loading: false,
    }),
    size: 'half',
  },

  // Latest AI Insight (half width — read-only)
  'cashflow_monitor:latest_insight': {
    name: 'Ultima Analisi AI',
    nameKey: 'widgets.header_latest_insight',
    nameNS: 'cashflow_monitor',
    moduleKey: 'cashflow_monitor',
    component: LatestInsightWidget,
    dataSources: ['overview'],
    dataExtractor: (sources) => ({
      insight: sources.overview?.last_insight || null,
      loading: false,
    }),
    size: 'half',
  },

  // ── v2.4: Phase 1 Analysis Charts ────────────────────────────────────────

  // Waterfall — where does the money go (full width)
  'cashflow_monitor:waterfall_chart': {
    name: 'Waterfall Risultato',
    nameKey: 'widgets.header_waterfall',
    nameNS: 'cashflow_monitor',
    moduleKey: 'cashflow_monitor',
    component: RevenueFlowChart,
    dataSources: ['overview'],
    dataExtractor: (sources) => ({
      kpis: sources.overview?.kpis || {},
      loading: false,
    }),
    size: 'full',
  },

  // Pareto Fornitori (half width)
  'cashflow_monitor:pareto_fornitori': {
    name: 'Pareto Fornitori',
    nameKey: 'widgets.header_pareto',
    nameNS: 'cashflow_monitor',
    moduleKey: 'cashflow_monitor',
    component: ParetoFornitori,
    dataSources: ['overview'],
    dataExtractor: (sources) => ({
      topSuppliers: sources.overview?.suppliers?.top_suppliers || [],
      loading: false,
    }),
    size: 'half',
  },

  // Composizione Uscite stacked (half width)
  'cashflow_monitor:composizione_uscite': {
    name: 'Composizione Uscite',
    nameKey: 'widgets.header_composition',
    nameNS: 'cashflow_monitor',
    moduleKey: 'cashflow_monitor',
    component: ComposizioneUscite,
    dataSources: ['overview'],
    dataExtractor: (sources) => ({
      data: sources.overview?.charts?.daily_series || [],
      loading: false,
    }),
    size: 'half',
  },

  // ── v2.4: Phase 2 Scadenzario Charts ─────────────────────────────────────

  // Aging Crediti vs Debiti (full width)
  'cashflow_monitor:aging_chart': {
    name: 'Aging Crediti/Debiti',
    nameKey: 'widgets.header_aging',
    nameNS: 'cashflow_monitor',
    moduleKey: 'cashflow_monitor',
    component: AgingChart,
    dataSources: ['overview'],
    dataExtractor: (sources) => ({
      receivablesAging: sources.overview?.scadenzario?.receivables_aging || [],
      payablesAging: sources.overview?.scadenzario?.payables_aging || [],
      loading: false,
    }),
    size: 'full',
  },

  // Timeline scadenze prossimi 60gg (half width)
  'cashflow_monitor:timeline_chart': {
    name: 'Scadenze 60gg',
    nameKey: 'widgets.header_timeline',
    nameNS: 'cashflow_monitor',
    moduleKey: 'cashflow_monitor',
    component: TimelineChart,
    dataSources: ['overview'],
    dataExtractor: (sources) => ({
      upcomingReceivables: sources.overview?.scadenzario?.upcoming_receivables || [],
      upcomingPayables: sources.overview?.scadenzario?.upcoming_payables || [],
      loading: false,
    }),
    size: 'half',
  },

  // Cash forecast projection (half width)
  'cashflow_monitor:cash_forecast_chart': {
    name: 'Proiezione Liquidità',
    nameKey: 'widgets.header_forecast',
    nameNS: 'cashflow_monitor',
    moduleKey: 'cashflow_monitor',
    component: CashForecastChart,
    dataSources: ['overview'],
    dataExtractor: (sources) => ({
      upcomingReceivables: sources.overview?.scadenzario?.upcoming_receivables || [],
      upcomingPayables: sources.overview?.scadenzario?.upcoming_payables || [],
      currentCash: sources.overview?.kpis?.net_after_fixed ?? 0,
      loading: false,
    }),
    size: 'half',
  },

  // ── v2.4: Phase 3 Health Score ───────────────────────────────────────────

  // Health Score Gauge (half width)
  'cashflow_monitor:health_score': {
    name: 'Salute Finanziaria',
    nameKey: 'widgets.header_health_score',
    nameNS: 'cashflow_monitor',
    moduleKey: 'cashflow_monitor',
    component: HealthScoreGauge,
    dataSources: ['overview'],
    dataExtractor: (sources) => ({
      healthScore: sources.overview?.health_score || null,
      loading: false,
    }),
    size: 'half',
  },

  // Alerts Summary (half width — compact counts)
  'cashflow_monitor:alerts_summary': {
    name: 'Riepilogo Anomalie',
    nameKey: 'widgets.header_alerts_summary',
    nameNS: 'cashflow_monitor',
    moduleKey: 'cashflow_monitor',
    component: AlertsSummaryWidget,
    dataSources: ['alerts'],
    dataExtractor: (sources) => ({
      alerts: sources.alerts || [],
      loading: false,
    }),
    size: 'half',
  },

  // Purchase Distribution (Pareto by product/category)
  'cashflow_monitor:purchase_distribution': {
    name: 'Distribuzione Acquisti',
    nameKey: 'widgets.header_purchase_distribution',
    nameNS: 'cashflow_monitor',
    moduleKey: 'cashflow_monitor',
    component: PurchaseDistributionChart,
    dataSources: ['overview'],
    dataExtractor: (sources) => ({
      distribution: sources.overview?.purchase_distribution || { by_product: [], by_category: [] },
      loading: false,
    }),
    size: 'full',
  },


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
