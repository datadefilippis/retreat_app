/**
 * CashflowModulePage — Cashflow Monitor v2
 *
 * Orchestratore: gestisce stato, fetch dei dati e routing tra tab.
 * Tutta la logica di rendering è delegata ai sotto-componenti in ./components/.
 *
 * Strategia di fetch (post-overview migration):
 *   Chiamata primaria (1 round-trip):
 *     GET /modules/cashflow_monitor/overview  → kpis, daily_series, categorie,
 *                                               last_insight, data_availability
 *   Chiamate supplementari (dati non coperti dall'overview):
 *     GET /alerts                            → lista completa con campo summary
 *     GET /fixed-costs                       → tabella costi fissi individuali
 *     GET /modules/cashflow_monitor/status   → stato attivazione modulo
 *
 * Totale chiamate: 4. MA7 calcolata client-side da daily_series.
 * AI features (Chat, Digest) spostati in /analisi-ai.
 */
import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { AppLayout, Header } from '../../components/Layout';
import { PageSubheader } from '../../components/PageSubheader';
import { Card, CardContent } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import { Input } from '../../components/ui/input';
import { PeriodSelector } from '../../components/PeriodSelector';
import { analyticsAPI, alertsAPI, modulesAPI, fixedCostsAPI, preferencesAPI } from '../../api';
import { computePeriodDates, periodNeedsCustomDates } from '../../lib/utils';
import { TrendingUp, RefreshCw, UploadCloud, ArrowRight } from 'lucide-react';
import { toast } from 'sonner';
import { useTranslation } from 'react-i18next';

// Sub-components
import { ModuleStatusBanner } from './components/ModuleStatusBanner';
import { KPIStrip, SummaryKPIStrip } from './components/KPIStrip';
import {
  SalesExpensesChart,
  NetCashflowChart,
  CumulativeCashflowChart,
  DetailedTrendsCharts,
} from './components/CashflowCharts';
import { CategoryPieCharts, CategoryBarCharts } from './components/CategoryCharts';
import { PurchaseDistributionChart } from './components/PurchaseDistributionChart';
import { FixedCostsTab } from './components/FixedCostsTab';
import { AlertsTab } from './components/AlertsTab';
import { AnalisiTab } from './components/AnalisiTab';
import { ScadenzarioTab } from './components/ScadenzarioTab';
import { HealthScoreGauge } from './components/HealthScoreGauge';
import { useCurrency } from '../../context/AuthContext';


// ── Client-side 7-day moving average ──────────────────────────────────────────
// Computes MA7 from overview daily_series, eliminating the /analytics/charts call.
function _computeMA7(dailySeries) {
  if (!dailySeries?.length) return [];
  return dailySeries.map((point, idx) => {
    const windowStart = Math.max(0, idx - 6);
    const window = dailySeries.slice(windowStart, idx + 1);
    const salesSum = window.reduce((sum, p) => sum + (p.sales || 0), 0);
    const expSum = window.reduce((sum, p) => sum + (p.expenses || 0), 0);
    return {
      ...point,
      sales_ma7: Math.round((salesSum / window.length) * 100) / 100,
      expenses_ma7: Math.round((expSum / window.length) * 100) / 100,
    };
  });
}

// ── Overview data adapters ─────────────────────────────────────────────────────
// These pure functions normalize the overview response into the shapes expected
// by existing sub-components.  Isolated here so fetchData stays readable.

/**
 * Build the KPI object expected by KPIStrip from the overview response.
 * Overview kpis already match the enriched-kpis shape except for the
 * top_expense_category field, which we derive from categories.top_expenses[0].
 */
function _adaptKPIsFromOverview(overview) {
  const topCat = overview.categories?.top_expenses?.[0] ?? null;
  return {
    ...overview.kpis,
    top_expense_category: topCat
      ? { category: topCat.category, total: topCat.total, percentage: topCat.percentage }
      : null,
  };
}

/**
 * Wrap a raw category array into the { categories: [...] } object shape
 * expected by CategoryPieCharts and CategoryBarCharts.
 * Overview already uses the { category, total, count, percentage } item shape.
 */
function _adaptCategoriesFromOverview(rawArray) {
  return { categories: rawArray ?? [] };
}


// ── No-data upload nudge ────────────────────────────────────────────────────────
// Shown when the module IS activated but no data has been uploaded yet.
// Sits between the ModuleStatusBanner and the KPI strip.

const NoDataUploadBanner = () => {
  const { t } = useTranslation('cashflow_monitor');
  return (
    <Card className="border-2 border-primary/20 bg-gradient-to-br from-primary/5 to-background">
      <CardContent className="flex flex-col sm:flex-row items-start sm:items-center gap-4 p-5">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10">
          <UploadCloud className="h-5 w-5 text-primary" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold leading-tight">
            {t('no_data_banner.title')}
          </p>
          <p className="text-xs text-muted-foreground mt-0.5">
            {t('no_data_banner.description')}
          </p>
        </div>
        <Link to="/upload" className="shrink-0">
          <Button size="sm" className="gap-2 whitespace-nowrap" data-testid="no-data-upload-btn">
            <UploadCloud className="h-3.5 w-3.5" />
            {t('no_data_banner.cta')}
            <ArrowRight className="h-3.5 w-3.5" />
          </Button>
        </Link>
      </CardContent>
    </Card>
  );
};


// ── Module activation gate ─────────────────────────────────────────────────────

const ActivationGate = ({ onActivate }) => {
  const { t } = useTranslation('cashflow_monitor');
  return (
    <div className="page-container">
      <Card className="max-w-2xl mx-auto">
        <CardContent className="py-12 text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted mx-auto">
            <TrendingUp className="h-8 w-8 text-muted-foreground" />
          </div>
          <h2 className="mt-6 font-heading text-2xl font-bold">{t('activation.title')}</h2>
          <p className="mt-2 text-muted-foreground max-w-md mx-auto">
            {t('activation.desc')}
          </p>
          <Button className="mt-6" onClick={onActivate} data-testid="activate-module-btn">
            {t('activation.cta')}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
};


// ── Main component ─────────────────────────────────────────────────────────────

export const CashflowModulePage = () => {
  const { t } = useTranslation('cashflow_monitor');
  const currency = useCurrency();

  // Period selection
  const [period, setPeriod] = useState('30d');
  const [customDateRange, setCustomDateRange] = useState(null);
  const [dataDateRange, setDataDateRange] = useState(null);

  // Tab
  const [activeTab, setActiveTab] = useState('summary');

  // Module state
  const [moduleStatus, setModuleStatus] = useState(null);
  // v2.3: synthetic health status (level/color/label/message/data_warnings)
  const [healthStatus, setHealthStatus] = useState(null);

  // Data state
  const [kpis, setKpis] = useState(null);
  const [chartData, setChartData] = useState([]);
  const [cumulativeData, setCumulativeData] = useState([]);
  const [salesCategories, setSalesCategories] = useState(null);
  const [expensesCategories, setExpensesCategories] = useState(null);
  const [fixedCosts, setFixedCosts] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [topSuppliers, setTopSuppliers] = useState([]);
  const [purchaseDistribution, setPurchaseDistribution] = useState(null);
  const [scadenzario, setScadenzario] = useState(null);
  const [yoyData, setYoyData] = useState(null);
  const [healthScoreData, setHealthScoreData] = useState(null);

  // Dashboard pin state
  const [pinnedWidgets, setPinnedWidgets] = useState(new Set());

  // Loading / action state
  const [loading, setLoading] = useState(true);
  // generatingInsight removed — insight generation deprecated in favour of Digest
  const [generatingAlerts, setGeneratingAlerts] = useState(false);

  // ── On mount: check available data range ────────────────────────────────────
  // Runs once to detect whether the org's data is older than 30 days and
  // auto-switch the period selector accordingly.  Stays as a separate call
  // because it must resolve BEFORE the first fetchData() to set the correct
  // period and avoid a double-fetch.
  useEffect(() => {
    const checkDateRange = async () => {
      try {
        const { data } = await analyticsAPI.getDateRange();
        setDataDateRange(data);

        // Auto-switch to data_range if latest data is older than 30 days
        if (data.has_data && data.max_date) {
          const maxDate = new Date(data.max_date);
          const thirtyDaysAgo = new Date();
          thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
          if (maxDate < thirtyDaysAgo) {
            setPeriod('data_range');
            setCustomDateRange({ start: data.min_date, end: data.max_date });
          }
        }
      } catch (err) {
        console.error('Date range check failed:', err);
      }
    };
    checkDateRange();
  }, []);

  // ── Fetch pinned dashboard widgets on mount ─────────────────────────────
  useEffect(() => {
    const fetchPinned = async () => {
      try {
        const { data } = await preferencesAPI.getDashboard();
        setPinnedWidgets(new Set(data?.widgets || []));
      } catch {
        setPinnedWidgets(new Set());
      }
    };
    fetchPinned();
  }, []);

  // ── Toggle pin handler (shared with all chart sub-components) ───────────
  const handleTogglePin = async (widgetKey) => {
    const newSet = new Set(pinnedWidgets);
    if (newSet.has(widgetKey)) {
      newSet.delete(widgetKey);
    } else {
      newSet.add(widgetKey);
    }
    setPinnedWidgets(newSet);
    try {
      await preferencesAPI.updateDashboard([...newSet]);
      toast.success(
        newSet.has(widgetKey) ? t('toast.pin_added') : t('toast.pin_removed')
      );
    } catch {
      toast.error(t('toast.pin_error'));
      // Revert
      setPinnedWidgets(pinnedWidgets);
    }
  };

  // ── Fetch all data when period changes ──────────────────────────────────────
  // Primary source: overview endpoint (1 call → KPIs, daily series, categories,
  // last insight, data availability, scadenzario, health score, status).
  // MA7 (7-day moving average) is computed client-side from daily_series.
  // Legacy calls retained only for:
  //   alertsRes     — AlertsTab needs full list with summary field
  //   fixedCostsRes — FixedCostsTab individual items table
  const fetchData = useCallback(async () => {
    setLoading(true);
    const needsCustom = periodNeedsCustomDates(period);
    const startDate = needsCustom ? customDateRange?.start : undefined;
    const endDate   = needsCustom ? customDateRange?.end   : undefined;
    const effectivePeriod = needsCustom ? 'custom' : period;

    try {
      const [
        statusRes,
        overviewRes,
        alertsRes,
        fixedCostsRes,
      ] = await Promise.all([
        modulesAPI.getStatus('cashflow_monitor'),
        modulesAPI.getOverview('cashflow_monitor', effectivePeriod, startDate, endDate)
          .catch(() => ({ data: null })),
        alertsAPI.list(null, null, 50),
        fixedCostsAPI.list({ activeOnly: true, limit: 100 }),
      ]);

      setModuleStatus(statusRes.data);

      const overview = overviewRes.data;
      if (overview) {
        setDataDateRange(overview.data_availability);
        setKpis(_adaptKPIsFromOverview(overview));
        const dailySeries = overview.charts.daily_series;
        setCumulativeData(dailySeries);
        setChartData(_computeMA7(dailySeries));  // client-side MA7 replaces /analytics/charts
        setSalesCategories(_adaptCategoriesFromOverview(overview.categories.top_sales));
        setExpensesCategories(_adaptCategoriesFromOverview(overview.categories.top_expenses));
        setTopSuppliers(overview.suppliers?.top_suppliers ?? []);
        setPurchaseDistribution(overview.purchase_distribution ?? null);
        setScadenzario(overview.scadenzario ?? null);
        setYoyData(overview.yoy ?? null);
        setHealthScoreData(overview.health_score ?? null);
        setHealthStatus(overview.status ?? null);
      }

      setAlerts((alertsRes.data ?? []).filter((a) => a.module_key === 'cashflow_monitor'));
      setFixedCosts(fixedCostsRes.data ?? []);

    } catch (err) {
      console.error('Fetch module data failed:', err);
      toast.error(t('toast.fetch_error'));
    } finally {
      setLoading(false);
    }
  }, [period, customDateRange]);

  useEffect(() => {
    const needsDates = periodNeedsCustomDates(period);
    if (!needsDates || customDateRange) {
      fetchData();
    }
  }, [period, customDateRange, fetchData]);

  // ── Actions ─────────────────────────────────────────────────────────────────
  const handleActivateModule = async () => {
    try {
      await modulesAPI.activate('cashflow_monitor');
      toast.success(t('toast.module_activated'));
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || t('toast.module_activate_error'));
    }
  };

  const handleGenerateAlerts = async () => {
    setGeneratingAlerts(true);
    try {
      const { data } = await alertsAPI.generate();
      toast.success(t('toast.alerts_generated', { count: data.alerts_generated }));
      fetchData();
    } catch {
      toast.error(t('toast.alerts_generate_error'));
    } finally {
      setGeneratingAlerts(false);
    }
  };

  // handleGenerateInsight removed — insight generation deprecated in favour of Digest

  // ── Period change handler ──────────────────────────────────────────────────
  const handlePeriodChange = (newPeriod) => {
    setPeriod(newPeriod);
    const computed = computePeriodDates(newPeriod);
    if (computed) {
      setCustomDateRange(computed);
    } else if (newPeriod === 'data_range' && dataDateRange?.has_data) {
      setCustomDateRange({ start: dataDateRange.min_date, end: dataDateRange.max_date });
    } else if (newPeriod !== 'custom') {
      setCustomDateRange(null);
    }
    // 'custom' — non resetta le date, l'utente le inserisce manualmente
  };

  // ── Sync active period to localStorage for AI chat context ────────────────
  useEffect(() => {
    const needsCustom = periodNeedsCustomDates(period);
    const ctx = {
      label: period,
      start: needsCustom ? customDateRange?.start : undefined,
      end: needsCustom ? customDateRange?.end : undefined,
    };
    try { localStorage.setItem('cashflow_active_period', JSON.stringify(ctx)); } catch {}
  }, [period, customDateRange]);

  // ── Module not activated ─────────────────────────────────────────────────────
  if (!loading && moduleStatus && !moduleStatus.is_activated) {
    return (
      <AppLayout>
        <Header title={t('page.title')} subtitle={t('page.subtitle')} />
        <ActivationGate onActivate={handleActivateModule} />
      </AppLayout>
    );
  }

  // ── Render ───────────────────────────────────────────────────────────────────
  return (
    <AppLayout>
      <Header title={t('page.title')} subtitle={t('page.subtitle')} />
      <PageSubheader
        actions={
          <>
            {/* Period selector — full-width on phones, compact from sm+ */}
            <PeriodSelector
              period={period}
              onPeriodChange={handlePeriodChange}
              dataDateRange={dataDateRange}
              className="w-full sm:w-44"
            />
            <Button
              variant="outline"
              size="sm"
              onClick={fetchData}
              data-testid="refresh-module-btn"
              className="shrink-0"
              aria-label={t('actions.refresh', { defaultValue: 'Refresh' })}
            >
              <RefreshCw className="h-4 w-4" />
            </Button>
          </>
        }
      />

      <div className="page-container section-gap animate-fade-in">
        {/* Custom date range inputs — shown when "Personalizzato" is selected */}
        {period === 'custom' && (
          <div className="flex flex-wrap items-center gap-2 p-3 bg-muted/50 rounded-lg">
            <span className="text-sm text-muted-foreground font-medium">{t('date_range.from')}</span>
            <Input
              type="date"
              value={customDateRange?.start || ''}
              onChange={(e) => setCustomDateRange(prev => ({ ...prev, start: e.target.value }))}
              className="h-8 w-auto"
            />
            <span className="text-sm text-muted-foreground font-medium">{t('date_range.to')}</span>
            <Input
              type="date"
              value={customDateRange?.end || ''}
              onChange={(e) => setCustomDateRange(prev => ({ ...prev, end: e.target.value }))}
              className="h-8 w-auto"
            />
          </div>
        )}

        {/* v2.3: synthetic health status banner */}
        <ModuleStatusBanner status={healthStatus} loading={loading} />

        {/* No-data nudge: module activated but no data uploaded yet */}
        {!loading && dataDateRange && !dataDateRange.has_data && <NoDataUploadBanner />}

        {/* Tabs — Wave C reorganization: Summary / Detail / Advanced / Alerts */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="w-full md:w-auto">
            <TabsTrigger value="summary"  data-testid="tab-summary"  className="px-2.5 md:px-4 text-xs md:text-sm">{t('tabs.summary')}</TabsTrigger>
            <TabsTrigger value="detail"   data-testid="tab-detail"   className="px-2.5 md:px-4 text-xs md:text-sm">{t('tabs.detail')}</TabsTrigger>
            <TabsTrigger value="advanced" data-testid="tab-advanced" className="px-2.5 md:px-4 text-xs md:text-sm">{t('tabs.advanced')}</TabsTrigger>
            <TabsTrigger value="alerts"   data-testid="tab-alerts"   className="px-2.5 md:px-4 text-xs md:text-sm">
              {t('tabs.alerts')} {alerts.length > 0 ? `(${alerts.length})` : ''}
            </TabsTrigger>
          </TabsList>

          {/* ═══════════════════════════════════════════════════════════════════
              SUMMARY — "How am I doing overall?"
              Health gauge, 5 core KPIs, primary charts.
              ═══════════════════════════════════════════════════════════════════ */}
          <TabsContent value="summary" className="mt-6 space-y-6">
            {/* Health Score Gauge + Summary KPI strip */}
            <div className="grid gap-4 lg:grid-cols-[280px_1fr]">
              <HealthScoreGauge
                healthScore={healthScoreData}
                loading={loading}
                widgetKey="cashflow_monitor:health_score"
                isPinned={pinnedWidgets.has('cashflow_monitor:health_score')}
                onTogglePin={handleTogglePin}
                period={{ label: periodNeedsCustomDates(period) ? 'custom' : period, start: customDateRange?.start, end: customDateRange?.end }}
                onRefresh={fetchData}
              />
              <SummaryKPIStrip kpis={kpis} yoy={yoyData} loading={loading} currency={currency} />
            </div>

            {/* Core charts: Revenue vs Expenses + Net Cashflow */}
            <div className="grid gap-6 lg:grid-cols-2">
              <SalesExpensesChart
                data={cumulativeData}
                loading={loading}
                widgetKey="cashflow_monitor:sales_expenses_chart"
                isPinned={pinnedWidgets.has('cashflow_monitor:sales_expenses_chart')}
                onTogglePin={handleTogglePin}
                currency={currency}
              />
              <NetCashflowChart
                data={cumulativeData}
                loading={loading}
                widgetKey="cashflow_monitor:net_cashflow_chart"
                isPinned={pinnedWidgets.has('cashflow_monitor:net_cashflow_chart')}
                onTogglePin={handleTogglePin}
                currency={currency}
              />
            </div>
          </TabsContent>

          {/* ═══════════════════════════════════════════════════════════════════
              DETAIL — "Where do the numbers come from?"
              Full KPI strip, cumulative, trend MA7, category charts.
              ═══════════════════════════════════════════════════════════════════ */}
          <TabsContent value="detail" className="mt-6 space-y-6">
            {/* Full 12-KPI strip */}
            <KPIStrip
              kpis={kpis}
              yoy={yoyData}
              loading={loading}
              widgetKey="cashflow_monitor:kpi_strip"
              isPinned={pinnedWidgets.has('cashflow_monitor:kpi_strip')}
              onTogglePin={handleTogglePin}
              currency={currency}
            />

            {/* Cumulative cashflow */}
            <CumulativeCashflowChart
              data={cumulativeData}
              loading={loading}
              widgetKey="cashflow_monitor:cumulative_chart"
              isPinned={pinnedWidgets.has('cashflow_monitor:cumulative_chart')}
              onTogglePin={handleTogglePin}
              currency={currency}
            />

            {/* Trend charts with 7-day moving average */}
            <DetailedTrendsCharts
              data={chartData}
              loading={loading}
              widgetKey="cashflow_monitor:detailed_trends"
              isPinned={pinnedWidgets.has('cashflow_monitor:detailed_trends')}
              onTogglePin={handleTogglePin}
              currency={currency}
            />

            {/* Category breakdowns */}
            <CategoryBarCharts
              salesCategories={salesCategories}
              expensesCategories={expensesCategories}
              loading={loading}
              widgetKey="cashflow_monitor:category_bar"
              isPinned={pinnedWidgets.has('cashflow_monitor:category_bar')}
              onTogglePin={handleTogglePin}
              currency={currency}
            />
            <CategoryPieCharts
              salesCategories={salesCategories}
              expensesCategories={expensesCategories}
              loading={loading}
              widgetKey="cashflow_monitor:category_pie"
              isPinned={pinnedWidgets.has('cashflow_monitor:category_pie')}
              onTogglePin={handleTogglePin}
              currency={currency}
            />
            <PurchaseDistributionChart
              distribution={purchaseDistribution}
              loading={loading}
              widgetKey="cashflow_monitor:purchase_distribution"
              isPinned={pinnedWidgets.has('cashflow_monitor:purchase_distribution')}
              onTogglePin={handleTogglePin}
              currency={currency}
            />
          </TabsContent>

          {/* ═══════════════════════════════════════════════════════════════════
              ADVANCED — "What deeper financial mechanics are happening?"
              Waterfall, Pareto, Composition, Fixed vs Variable,
              Scadenzario (DSO/DPO/CCC/Aging/Forecast).
              ═══════════════════════════════════════════════════════════════════ */}
          <TabsContent value="advanced" className="mt-6 space-y-8">
            {/* Waterfall + Pareto + Composition */}
            <AnalisiTab
              kpis={kpis}
              dailySeries={cumulativeData}
              topSuppliers={topSuppliers}
              loading={loading}
              waterfallWidgetKey="cashflow_monitor:waterfall_chart"
              isWaterfallPinned={pinnedWidgets.has('cashflow_monitor:waterfall_chart')}
              paretoWidgetKey="cashflow_monitor:pareto_fornitori"
              isParetoPinned={pinnedWidgets.has('cashflow_monitor:pareto_fornitori')}
              composizioneWidgetKey="cashflow_monitor:composizione_uscite"
              isComposizionePinned={pinnedWidgets.has('cashflow_monitor:composizione_uscite')}
              onTogglePin={handleTogglePin}
              currency={currency}
            />

            {/* Fixed vs Variable + Fixed Costs table */}
            <FixedCostsTab
              fixedCosts={fixedCosts}
              fixedCostsTotal={kpis?.fixed_costs_total}
              variableExpenses={kpis?.total_expenses}
              loading={loading}
              fixedVsVariableWidgetKey="cashflow_monitor:fixed_vs_variable"
              isFixedVsVariablePinned={pinnedWidgets.has('cashflow_monitor:fixed_vs_variable')}
              onTogglePin={handleTogglePin}
              currency={currency}
            />

            {/* Scadenzario (DSO/DPO/CCC/Aging/Timeline/Forecast) */}
            <ScadenzarioTab
              kpis={kpis}
              scadenzario={scadenzario}
              loading={loading}
              agingWidgetKey="cashflow_monitor:aging_chart"
              isAgingPinned={pinnedWidgets.has('cashflow_monitor:aging_chart')}
              timelineWidgetKey="cashflow_monitor:timeline_chart"
              isTimelinePinned={pinnedWidgets.has('cashflow_monitor:timeline_chart')}
              forecastWidgetKey="cashflow_monitor:cash_forecast_chart"
              isForecastPinned={pinnedWidgets.has('cashflow_monitor:cash_forecast_chart')}
              onTogglePin={handleTogglePin}
              currency={currency}
            />
          </TabsContent>

          {/* ═══════════════════════════════════════════════════════════════════
              ALERTS — anomalies and warnings
              ═══════════════════════════════════════════════════════════════════ */}
          <TabsContent value="alerts">
            <AlertsTab
              alerts={alerts}
              loading={loading}
              generatingAlerts={generatingAlerts}
              onGenerate={handleGenerateAlerts}
              alertsWidgetKey="cashflow_monitor:alerts_summary"
              isAlertsPinned={pinnedWidgets.has('cashflow_monitor:alerts_summary')}
              onTogglePin={handleTogglePin}
            />
          </TabsContent>

        </Tabs>
      </div>

    </AppLayout>
  );
};

export default CashflowModulePage;
