/**
 * DashboardPage — personalizable dashboard with pinned widgets.
 *
 * Empty-state cascade:
 *   1. No active modules   → invite to activate a module
 *   2. Modules but no data → invite to upload data
 *   3. Data but no widgets → invite to add widgets from modules
 *   4. Widgets pinned      → render dynamic widget grid
 *
 * Data flow:
 *   - Fetch pinned widget keys from GET /api/preferences/dashboard
 *   - Group widgets by moduleKey (from WIDGET_REGISTRY)
 *   - Fetch modulesAPI.getOverview() once per unique module
 *   - Distribute data to each widget via its dataExtractor
 */
import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { AppLayout, Header } from '../../components/Layout';
import { PageSubheader } from '../../components/PageSubheader';
import { Card, CardContent } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Skeleton } from '../../components/ui/skeleton';
import { PeriodSelector } from '../../components/PeriodSelector';
import { preferencesAPI, modulesAPI, analyticsAPI } from '../../api';
import { useAuth } from '../../context/AuthContext';
import { computePeriodDates, periodNeedsCustomDates } from '../../lib/utils';
import { WIDGET_REGISTRY, getRequiredSources, DATA_FETCHERS } from './widgetRegistry';
import { DashboardWidgetCard } from './DashboardWidgetCard';
import {
  Blocks,
  UploadCloud,
  LayoutGrid,
  ArrowRight,
  RefreshCw,
  TrendingUp,
} from 'lucide-react';
import { toast } from 'sonner';
import { useTranslation } from 'react-i18next';
import OperatorHome from './OperatorHome';

// Map module_key → { dataHref, moduleHref }
const MODULE_META = {
  cashflow_monitor: {
    dataHref: '/modules/cashflow/data',
    moduleHref: '/modules/cashflow',
  },
  customers_light: {
    dataHref: '/modules/cashflow/data',  // uploads via cashflow data page
    moduleHref: '/modules/customers-light',
  },
};


// ── Empty States ──────────────────────────────────────────────────────────────

const EmptyStateShell = ({ icon: Icon, title, description, children }) => (
  <div className="flex flex-col items-center justify-center py-16 px-4 text-center animate-fade-in">
    <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted">
      <Icon className="h-8 w-8 text-muted-foreground" />
    </div>
    <h2 className="mt-6 font-heading text-xl font-bold tracking-tight">{title}</h2>
    <p className="mt-2 max-w-md text-sm text-muted-foreground">{description}</p>
    {children && <div className="mt-6 flex flex-col sm:flex-row gap-3">{children}</div>}
  </div>
);

/** State 1 — no active modules */
const NoModulesEmpty = () => {
  const { t } = useTranslation('dashboard');
  return (
    <EmptyStateShell
      icon={Blocks}
      title={t('empty.no_modules_title')}
      description={t('empty.no_modules_desc')}
    >
      <Link to="/modules">
        <Button className="gap-2">
          <Blocks className="h-4 w-4" />
          {t('empty.go_to_modules')}
          <ArrowRight className="h-4 w-4" />
        </Button>
      </Link>
    </EmptyStateShell>
  );
};

/** State 2 — modules active but no data uploaded */
const NoDataEmpty = ({ activeModules }) => {
  const { t } = useTranslation('dashboard');
  const { t: tc } = useTranslation('common');
  return (
    <EmptyStateShell
      icon={UploadCloud}
      title={t('empty.no_data_title')}
      description={t('empty.no_data_desc', { count: activeModules.length })}
    >
      {activeModules.map((mod) => {
        const meta = MODULE_META[mod.module_key];
        if (!meta) return null;
        const label = tc(`modules.${mod.module_key}`, { defaultValue: mod.name });
        return (
          <Link key={mod.module_key} to={meta.dataHref}>
            <Button variant="outline" className="gap-2">
              <UploadCloud className="h-4 w-4" />
              {t('empty.upload_data', { label })}
            </Button>
          </Link>
        );
      })}
    </EmptyStateShell>
  );
};

/** State 3 — data available but no widgets pinned */
const NoWidgetsEmpty = ({ activeModules }) => {
  const { t } = useTranslation('dashboard');
  const { t: tc } = useTranslation('common');
  return (
    <EmptyStateShell
      icon={LayoutGrid}
      title={t('empty.no_widgets_title')}
      description={t('empty.no_widgets_desc')}
    >
      {activeModules.map((mod) => {
        const meta = MODULE_META[mod.module_key];
        if (!meta) return null;
        const label = tc(`modules.${mod.module_key}`, { defaultValue: mod.name });
        return (
          <Link key={mod.module_key} to={meta.moduleHref}>
            <Button variant="outline" className="gap-2">
              <TrendingUp className="h-4 w-4" />
              {t('empty.go_to_module', { label })}
              <ArrowRight className="h-4 w-4" />
            </Button>
          </Link>
        );
      })}
    </EmptyStateShell>
  );
};


// ── Main Component ───────────────────────────────────────────────────────────

export const DashboardPage = () => {
  const { t } = useTranslation('dashboard');
  // Period
  const [period, setPeriod] = useState('30d');
  const [customDateRange, setCustomDateRange] = useState(null);
  const [dataDateRange, setDataDateRange] = useState(null);

  // State detection
  const [activeModules, setActiveModules] = useState(null); // null = loading
  const [hasData, setHasData] = useState(null);             // null = loading

  // Pinned widgets
  const [pinnedKeys, setPinnedKeys] = useState(null);       // null = loading

  // Module data cache: { [moduleKey]: overviewData }
  const [moduleData, setModuleData] = useState({});
  const [loadingData, setLoadingData] = useState(false);

  // ── Initial load: modules + date range + pinned widgets ───────────────────
  useEffect(() => {
    const init = async () => {
      try {
        const [modulesRes, dateRangeRes, prefsRes] = await Promise.all([
          modulesAPI.listActive(),
          analyticsAPI.getDateRange().catch(() => ({ data: { has_data: false } })),
          preferencesAPI.getDashboard(),
        ]);

        setActiveModules(modulesRes.data || []);

        const dr = dateRangeRes.data;
        setDataDateRange(dr);
        setHasData(dr?.has_data ?? false);

        // Auto-switch period if data is older than 30 days
        if (dr?.has_data && dr.max_date) {
          const maxDate = new Date(dr.max_date);
          const thirtyDaysAgo = new Date();
          thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
          if (maxDate < thirtyDaysAgo) {
            setPeriod('data_range');
            setCustomDateRange({ start: dr.min_date, end: dr.max_date });
          }
        }

        setPinnedKeys(prefsRes.data?.widgets || []);
      } catch (err) {
        console.error('Dashboard init failed:', err);
        setActiveModules([]);
        setHasData(false);
        setPinnedKeys([]);
      }
    };
    init();
  }, []);

  // ── Fetch widget data when pinnedKeys or period changes ─────────────────
  const fetchModuleData = useCallback(async () => {
    if (!pinnedKeys || pinnedKeys.length === 0) return;

    const requiredSources = getRequiredSources(pinnedKeys);
    if (requiredSources.size === 0) return;

    setLoadingData(true);
    const needsCustom = periodNeedsCustomDates(period);
    const startDate = needsCustom ? customDateRange?.start : undefined;
    const endDate = needsCustom ? customDateRange?.end : undefined;
    const effectivePeriod = needsCustom ? 'custom' : period;

    try {
      const fetches = [];
      requiredSources.forEach((sources, modKey) => {
        sources.forEach((source) => {
          const fetcher = DATA_FETCHERS[source];
          if (!fetcher) return;
          fetches.push(
            fetcher(modKey, effectivePeriod, startDate, endDate)
              .then((data) => ({ modKey, source, data }))
              .catch(() => ({ modKey, source, data: null }))
          );
        });
      });

      const results = await Promise.all(fetches);

      const cache = {};
      results.forEach(({ modKey, source, data }) => {
        if (!cache[modKey]) cache[modKey] = {};
        if (data != null) cache[modKey][source] = data;
      });
      setModuleData(cache);
    } catch (err) {
      console.error('Failed to fetch module data:', err);
    } finally {
      setLoadingData(false);
    }
  }, [pinnedKeys, period, customDateRange]);

  useEffect(() => {
    const needsDates = periodNeedsCustomDates(period);
    if (pinnedKeys && pinnedKeys.length > 0 && (!needsDates || customDateRange)) {
      fetchModuleData();
    }
  }, [fetchModuleData, period, customDateRange]);

  // ── Widget actions ────────────────────────────────────────────────────────
  const updatePinnedWidgets = async (newKeys) => {
    setPinnedKeys(newKeys);
    try {
      await preferencesAPI.updateDashboard(newKeys);
    } catch {
      toast.error(t('toast.save_error'));
    }
  };

  const handleRemoveWidget = (widgetKey) => {
    const newKeys = pinnedKeys.filter((k) => k !== widgetKey);
    updatePinnedWidgets(newKeys);
    toast.success(t('toast.widget_removed'));
  };

  const handleMoveUp = (idx) => {
    if (idx === 0) return;
    const newKeys = [...pinnedKeys];
    [newKeys[idx - 1], newKeys[idx]] = [newKeys[idx], newKeys[idx - 1]];
    updatePinnedWidgets(newKeys);
  };

  const handleMoveDown = (idx) => {
    if (idx >= pinnedKeys.length - 1) return;
    const newKeys = [...pinnedKeys];
    [newKeys[idx], newKeys[idx + 1]] = [newKeys[idx + 1], newKeys[idx]];
    updatePinnedWidgets(newKeys);
  };

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
  };

  // ── Determine current state ──────────────────────────────────────────────
  const isInitializing = activeModules === null || hasData === null || pinnedKeys === null;
  const hasActiveModules = activeModules && activeModules.length > 0;
  const hasPinnedWidgets = pinnedKeys && pinnedKeys.length > 0;

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <AppLayout>
      <Header title={t('title')} subtitle={t('subtitle')} />
      {hasPinnedWidgets && (
        <PageSubheader
          actions={
            <>
              {/* Period selector takes the available row on mobile
                  (full width via w-full in the subheader's actions slot)
                  and reverts to compact width from sm+. */}
              <PeriodSelector
                period={period}
                onPeriodChange={handlePeriodChange}
                dataDateRange={dataDateRange}
                className="w-full sm:w-44"
              />
              <Button
                variant="outline"
                size="sm"
                onClick={fetchModuleData}
                data-testid="refresh-btn"
                className="shrink-0"
                aria-label={t('refresh', { defaultValue: 'Refresh' })}
              >
                <RefreshCw className="h-4 w-4" />
              </Button>
            </>
          }
        />
      )}

      <div className="p-4 md:p-8 animate-fade-in space-y-6">
        {/* D3 — home operatore: sempre in testa, zero configurazione.
            I widget pinnati / empty states dei moduli restano sotto come
            personalizzazione avanzata. */}
        <OperatorHome />

        {/* Custom date range inputs */}
        {period === 'custom' && hasPinnedWidgets && (
          <div className="flex flex-wrap items-center gap-2 p-3 mb-6 bg-muted/50 rounded-lg">
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

        {/* Loading skeleton */}
        {isInitializing && (
          <div className="space-y-6">
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
              {[1, 2, 3, 4].map((i) => (
                <Card key={i} className="border border-border">
                  <CardContent className="p-6">
                    <Skeleton className="h-4 w-24 mb-2" />
                    <Skeleton className="h-8 w-32 mb-2" />
                    <Skeleton className="h-4 w-20" />
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        )}

        {/* Empty State 1 — No active modules */}
        {!isInitializing && !hasActiveModules && <NoModulesEmpty />}

        {/* Empty State 2 — Modules active, no data */}
        {!isInitializing && hasActiveModules && !hasData && (
          <NoDataEmpty activeModules={activeModules} />
        )}

        {/* Empty State 3 — Data present, no widgets pinned */}
        {!isInitializing && hasActiveModules && hasData && !hasPinnedWidgets && (
          <NoWidgetsEmpty activeModules={activeModules} />
        )}

        {/* Widget Grid */}
        {!isInitializing && hasPinnedWidgets && (
          <div className="grid gap-6 grid-cols-1 lg:grid-cols-2">
            {pinnedKeys.map((widgetKey, idx) => {
              const entry = WIDGET_REGISTRY[widgetKey];
              if (!entry) return null;

              const { name, nameKey, nameNS, moduleKey, component: WidgetComponent, dataExtractor, size } = entry;
              const sources = moduleData[moduleKey];
              const hasData = sources && Object.keys(sources).length > 0;
              const widgetProps = hasData
                ? dataExtractor(sources)
                : { loading: true };

              if (loadingData && !hasData) {
                widgetProps.loading = true;
              }

              return (
                <DashboardWidgetCard
                  key={widgetKey}
                  title={name}
                  nameKey={nameKey}
                  nameNS={nameNS}
                  size={size}
                  isFirst={idx === 0}
                  isLast={idx === pinnedKeys.length - 1}
                  onMoveUp={() => handleMoveUp(idx)}
                  onMoveDown={() => handleMoveDown(idx)}
                  onRemove={() => handleRemoveWidget(widgetKey)}
                >
                  <WidgetComponent {...widgetProps} />
                </DashboardWidgetCard>
              );
            })}
          </div>
        )}
      </div>
    </AppLayout>
  );
};

export default DashboardPage;
