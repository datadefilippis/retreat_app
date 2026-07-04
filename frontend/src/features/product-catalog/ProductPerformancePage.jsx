/**
 * ProductPerformancePage — the new home of the /modules/product-catalog
 * route, mirroring the Customer Insights pattern.
 *
 * Layout
 * ──────
 *   ┌─ Header (title + period selector + refresh) ──────────────────┐
 *   ├─ Cost-data banner (when partial / missing) ────────────────────┤
 *   ├─ Tier 1 — Headline KPIs (revenue, cost, margins, products) ──┤
 *   ├─ Tier 2 — Operational insights (top seller, profitability …) ┤
 *   ├─ Distribution row (ABC + categories) ──────────────────────────┤
 *   └─ Products table (filters + click-to-drill) ────────────────────┘
 *
 *   + ProductProfileSlide on the right when the merchant clicks a row.
 *
 * Data flow
 * ─────────
 *   - ``useProductOverview(period)`` owns the /overview fetch
 *   - Period changes refire the hook; loading state cascades to every
 *     section via InsightCard's skeleton.
 *   - Refresh button calls ``productCatalogAPI.refresh()`` (recomputes
 *     materialised metrics) and then re-fetches the overview.
 *
 * History
 * ───────
 * Replaces the legacy ``ProductCatalogPage.js`` (removed in PP.9).
 * The legacy page lives in git history if a behavioural diff is ever
 * needed; the new page is the only mount of ``/modules/product-catalog``.
 */

import React, { useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { Button } from '../../components/ui/button';
import { AppLayout, Header } from '../../components/Layout';
import { RefreshCw, Loader2, Package, AlertCircle } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { productCatalogAPI } from '../../api/productCatalog';
import { PeriodSelector } from '../../components/insights/PeriodSelector';
import useProductOverview from './hooks/useProductOverview';
import useProductHealthChecks from './hooks/useProductHealthChecks';
import ProductKpiSection from './components/ProductKpiSection';
import AbcDistributionCard from './components/AbcDistributionCard';
import CategoryBreakdownCard from './components/CategoryBreakdownCard';
import ProductsPerformanceTable from './components/ProductsPerformanceTable';
import ProductProfileSlide from './components/ProductProfileSlide';
import IntelligenceBanner from './components/IntelligenceBanner';


export default function ProductPerformancePage() {
  const { t } = useTranslation('product_catalog');
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin' || user?.role === 'system_admin';

  // ── State ──────────────────────────────────────────────────────────────
  const [period, setPeriod] = useState('30d');
  const [refreshing, setRefreshing] = useState(false);

  // Drill-down state: which product is in the slide and is it open.
  const [drillProductId, setDrillProductId] = useState(null);
  const [drillSummary, setDrillSummary] = useState(null);
  const [drillOpen, setDrillOpen] = useState(false);

  const { overview, loading, error, refetch } = useProductOverview(period);
  // Intelligence Banner — separate fetch so it can refresh independently
  // and so a slow overview never delays issue visibility.
  const {
    data: healthData,
    loading: healthLoading,
    refetch: refetchHealth,
    isDismissed,
    dismissCheck,
  } = useProductHealthChecks(period);

  // ── Handlers ───────────────────────────────────────────────────────────

  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    try {
      await productCatalogAPI.refresh();
      toast.success(t('actions.refresh_success'));
      refetch();
      refetchHealth();
    } catch {
      toast.error(t('actions.refresh_error'));
    } finally {
      setRefreshing(false);
    }
  }, [t, refetch, refetchHealth]);

  const openProductDrill = useCallback((productId, summary = null) => {
    if (!productId) return;
    setDrillProductId(productId);
    setDrillSummary(summary);
    setDrillOpen(true);
  }, []);

  // Resolve a summary row (for the slide header) from the table data
  // when the drill is triggered from a KPI card (no row data nearby).
  const productDrillFromTable = useCallback((productId) => {
    const row = overview?.top_products?.find(p => p.product_id === productId);
    openProductDrill(productId, row || null);
  }, [overview, openProductDrill]);

  // ── Derived flags ──────────────────────────────────────────────────────

  const kpi = overview?.kpi || {};
  const hasData = !!overview && overview.has_data !== false;
  const totalRevenue = kpi.totalRevenue?.value ?? 0;
  // Cost-banner flags previously derived here moved into IntelligenceBanner
  // (see useProductHealthChecks). The banner aggregates ALL data-quality
  // issues, not just cost coverage.

  // ── Render ─────────────────────────────────────────────────────────────

  return (
    <AppLayout>
      <div className="min-h-screen flex flex-col">
        <Header title={t('page.title')} subtitle={t('page.subtitle')}>
          {isAdmin && hasData && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              disabled={refreshing}
              className="gap-2"
            >
              {refreshing
                ? <Loader2 className="h-4 w-4 animate-spin" />
                : <RefreshCw className="h-4 w-4" />}
              {refreshing ? t('actions.refreshing') : t('actions.refresh')}
            </Button>
          )}
        </Header>

        <div className="flex-1 p-4 md:p-8 space-y-6 animate-fade-in">
          {/* Period selector strip — always visible at the top */}
          <div className="flex items-center justify-between flex-wrap gap-2">
            <PeriodSelector value={period} onChange={setPeriod} />
            {overview?.period && (
              <span className="text-[11px] text-muted-foreground">
                {overview.period.start} → {overview.period.end}
              </span>
            )}
          </div>

          {/* Top-level error band — kept inline so the rest of the page
              still tries to render if it can. */}
          {error && !loading && (
            <div className="rounded-lg border border-red-200 bg-red-50/60 p-3 text-sm text-red-800 flex items-start gap-2">
              <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Empty state — no metrics yet at all */}
          {!loading && !hasData ? (
            <EmptyState
              isAdmin={isAdmin}
              onRefresh={handleRefresh}
              refreshing={refreshing}
              t={t}
            />
          ) : (
            <>
              {/* IB.6 — Intelligence Banner: replaces the two legacy
                  CostBanner notices. Aggregates every health check
                  (cost coverage, suspicious margins, cashflow
                  coherence, …) into a single expandable surface so
                  the merchant sees ALL data-quality issues at once
                  rather than two static notices. */}
              <IntelligenceBanner
                data={healthData}
                loading={healthLoading}
                isDismissed={isDismissed}
                onDismissCheck={dismissCheck}
                onRefreshMetrics={handleRefresh}
              />

              {/* Tier 1 + Tier 2 KPIs */}
              <ProductKpiSection
                kpi={kpi}
                loading={loading}
                onProductDrill={productDrillFromTable}
              />

              {/* Distribution row */}
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
                  {t('sections.distribution')}
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <AbcDistributionCard
                    abc={overview?.abc_distribution}
                    loading={loading}
                  />
                  <CategoryBreakdownCard
                    categories={overview?.categories}
                    totalRevenue={totalRevenue}
                    loading={loading}
                  />
                </div>
              </div>

              {/* Products table */}
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
                  {t('sections.products_table')}
                </h3>
                <ProductsPerformanceTable
                  products={overview?.top_products}
                  loading={loading}
                  onProductDrill={productDrillFromTable}
                />
              </div>
            </>
          )}
        </div>
      </div>

      {/* Drill-down slide-over */}
      <ProductProfileSlide
        productId={drillProductId}
        summary={drillSummary}
        open={drillOpen}
        onOpenChange={setDrillOpen}
      />
    </AppLayout>
  );
}


// ── Subcomponents ────────────────────────────────────────────────────────────

// CostBanner removed in IB.6 — its job (showing cost-coverage warnings)
// is now part of IntelligenceBanner together with 9 other checks.

function EmptyState({ isAdmin, onRefresh, refreshing, t }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted mb-4">
        <Package className="h-8 w-8 text-muted-foreground" />
      </div>
      <h3 className="text-lg font-semibold">{t('empty.title')}</h3>
      <p className="mt-2 max-w-md text-sm text-muted-foreground">
        {t('empty.description')}
      </p>
      <div className="mt-6 flex gap-3">
        <Button variant="outline" onClick={() => { window.location.href = '/products'; }}>
          {t('empty.cta_manage')}
        </Button>
        {isAdmin && (
          <Button onClick={onRefresh} disabled={refreshing}>
            {refreshing ? t('actions.refreshing') : t('empty.cta_refresh')}
          </Button>
        )}
      </div>
    </div>
  );
}
