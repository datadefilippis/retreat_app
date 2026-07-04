import React, { useState } from 'react';
import { Card, CardContent } from '../../../components/ui/card';
import { Skeleton } from '../../../components/ui/skeleton';
import { ArrowUpRight, ArrowDownRight, Info, RotateCcw, Minus } from 'lucide-react';
import { formatCurrency, formatPercent } from '../../../lib/utils';
import { PinToDashboardButton } from '../../dashboard/PinToDashboardButton';
import { useTranslation } from 'react-i18next';

/* ── KPI semantic rules ─────────────────────────────────────────────────── */

/**
 * Centralized variant rules for KPI cards (absolute card color).
 *
 * Each rule: (value, kpis) → 'success' | 'danger' | undefined (neutral).
 * KPIs NOT listed default to neutral — factual amounts with no inherent
 * good/bad meaning (revenue, expenses, purchases, burn rate, fixed costs).
 */
const KPI_VARIANT_RULES = {
  net_result:           (v) => v >= 0 ? 'success' : 'danger',
  break_even:           (v, k) => k?.total_sales < v ? 'danger' : 'success',
  operational_coverage: (v) => v < 30 ? 'danger' : v >= 60 ? 'success' : undefined,
  fixed_costs_pct:      (v) => v > 30 ? 'danger' : 'success',
  operating_margin_pct: (v) => v < 10 ? 'danger' : 'success',
  outflow_ratio:        (v) => v > 80 ? 'danger' : 'success',
};

/** Resolve card variant. Returns undefined for null/missing values. */
const kpiVariant = (key, val, kpis) => {
  if (val == null) return undefined;
  const rule = KPI_VARIANT_RULES[key];
  return rule ? rule(val, kpis) : undefined;
};

/**
 * KPI trend direction (comparison/delta coloring).
 *
 * KPIs in this set have INVERSE semantics: a decrease is favorable (green),
 * an increase is unfavorable (red). This controls the TrendBadge color.
 *
 * KPIs NOT listed: higher is better (default) or neutral.
 *   - total_sales: higher = growth (green ↑)
 *   - net_result: higher = more profit (green ↑)
 *   - operating_margin_pct: higher = better margin (green ↑)
 *   - operational_coverage: higher = more runway (green ↑)
 */
const KPI_TREND_INVERSE = new Set([
  'total_expenses',       // lower expenses = favorable
  'supplier_purchases',   // lower purchases = favorable
  'fixed_costs',          // lower fixed costs = favorable
  'burn_rate',            // lower burn = favorable
  'outflow_ratio',        // lower ratio = favorable
  'fixed_costs_pct',      // lower % = favorable
]);

/* ── Trend indicator ─────────────────────────────────────────────────────── */
function TrendBadge({ value, inverse, label }) {
  if (value == null) return null;
  const isGood = inverse ? value <= 0 : value >= 0;
  const isNeutral = Math.abs(value) < 0.5;

  if (isNeutral) {
    return (
      <span className="inline-flex items-center gap-0.5 text-xs text-muted-foreground">
        <Minus className="h-3 w-3" /> 0% {label}
      </span>
    );
  }

  // Cap extreme percentages at ±999% to avoid confusing numbers
  // (e.g., -249% on net result when previous year was near zero)
  const absVal = Math.abs(value);
  const displayPct = absVal > 999 ? (value > 0 ? '>999%' : '<-999%') : formatPercent(value);

  return (
    <span className={`inline-flex items-center gap-0.5 text-xs font-medium ${isGood ? 'text-emerald-600' : 'text-red-600'}`}>
      {value > 0 ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}
      {displayPct} {label}
    </span>
  );
}

/**
 * KPICard — metric card with single comparison + card-flip help.
 *
 * Design rule: each card shows at most ONE comparison line on the front side
 * to keep readability high. The comparison prop is generic — the caller
 * decides whether to pass period-over-period or YoY.
 */
export const KPICard = ({
  title,
  value,
  comparison,         // { value: number|null, inverse: boolean, label: string }
  tooltip,
  loading,
  variant,
  diagnostic,         // boolean — muted styling for supplementary metrics
  currency = 'EUR',
}) => {
  const { t } = useTranslation('cashflow_monitor');
  const [flipped, setFlipped] = useState(false);

  // Diagnostic cards use softer variant coloring (reduced opacity handles visual hierarchy)
  const bgClass =
    variant === 'success' ? 'bg-emerald-50/40 dark:bg-emerald-950/10 border-emerald-200/70' :
    variant === 'danger'  ? 'bg-red-50/40 dark:bg-red-950/10 border-red-200/70' :
    diagnostic ? 'border-border/50 bg-muted/20' :
    'border-border';

  if (loading) {
    return (
      <Card className="border border-border">
        <CardContent className="p-4 md:p-5">
          <Skeleton className="h-4 w-24 mb-2" />
          <Skeleton className="h-8 w-32 mb-2" />
          <Skeleton className="h-3.5 w-20" />
        </CardContent>
      </Card>
    );
  }

  // ── BACK SIDE ──────────────────────────────────────────────────────────
  if (flipped && tooltip) {
    const structured = typeof tooltip === 'object' && tooltip.def;
    return (
      <Card className="border border-primary/20 bg-primary/[0.02]">
        <CardContent className="p-4 md:p-5 flex flex-col justify-between min-h-[130px]">
          <div>
            <p className="text-sm font-semibold text-primary/80 mb-1.5">{title}</p>
            {structured ? (
              <div className="space-y-1.5 text-xs text-muted-foreground leading-relaxed">
                <p>{tooltip.def}</p>
                <p className="text-muted-foreground/70 italic">{tooltip.calc}</p>
                <p className="font-medium text-foreground/70">{tooltip.read}</p>
              </div>
            ) : (
              <p className="text-xs text-muted-foreground leading-relaxed">{tooltip}</p>
            )}
          </div>
          <button
            onClick={() => setFlipped(false)}
            className="mt-3 flex items-center gap-1 text-xs font-medium text-primary hover:text-primary/80 transition-colors self-start"
          >
            <RotateCcw className="h-3 w-3" />
            {t('kpis.back_button')}
          </button>
        </CardContent>
      </Card>
    );
  }

  // ── FRONT SIDE ─────────────────────────────────────────────────────────
  return (
    <Card className={`border transition-colors hover:border-primary/30 ${bgClass} ${diagnostic ? 'opacity-75' : ''}`}>
      <CardContent className="p-4 md:p-5">
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-sm font-medium text-muted-foreground flex items-center gap-1 truncate">
            {title}
            {tooltip && (
              <button onClick={(e) => { e.stopPropagation(); setFlipped(true); }} className="text-muted-foreground/40 hover:text-primary transition-colors flex-shrink-0" aria-label="Info">
                <Info className="h-3 w-3" />
              </button>
            )}
          </span>
        </div>

        <p className={`font-heading text-2xl font-bold tracking-tight ${diagnostic ? 'text-muted-foreground' : ''}`}>
          {typeof value === 'number' ? formatCurrency(value, currency) : (value ?? '\u2014')}
        </p>

        {comparison?.value != null && (
          <div className="mt-2">
            <TrendBadge value={comparison.value} inverse={comparison.inverse} label={comparison.label} />
          </div>
        )}
      </CardContent>
    </Card>
  );
};


/**
 * KPIStrip — card grid for the Detail tab.
 *
 * Row 1 (6): core operational KPIs with YoY comparison.
 * Row 2 (5): structural KPIs + 2 diagnostic-styled supplementary metrics.
 *
 * Canonical comparison baseline: same period previous year (YoY).
 * When YoY data is unavailable, comparison is hidden (no silent fallback).
 */
export const KPIStrip = ({ kpis, yoy, loading, widgetKey, isPinned, onTogglePin, currency = 'EUR' }) => {
  const { t } = useTranslation('cashflow_monitor');

  const outflowRatio    = kpis?.total_outflow_ratio;
  const outflowRatioStr = outflowRatio != null ? `${outflowRatio}%` : undefined;
  const yp = yoy?.pct || {};

  /** Build YoY comparison object. Returns undefined when no YoY data (no fallback). */
  const comp = (key, yoyKey) => {
    const val = yp[yoyKey || key];
    return val != null ? { value: val, inverse: KPI_TREND_INVERSE.has(key), label: t('kpis.vs_last_year') } : undefined;
  };

  // Data-driven structured tooltip: returns { def, calc, read } from i18n
  const explain = (key) => ({
    def: t(`kpis.explain.${key}.def`),
    calc: t(`kpis.explain.${key}.calc`),
    read: t(`kpis.explain.${key}.read`),
  });

  // Break-even uses context-aware explanation (3 variants)
  const breakEvenExplain = () => {
    if (kpis?.break_even != null) return explain('break_even');
    if (!kpis?.fixed_costs_total || kpis.fixed_costs_total === 0) return explain('break_even_no_fixed');
    return explain('break_even_na'); // VCR >= 1.0
  };

  return (
    <div className="relative">
      {widgetKey && onTogglePin && (
        <div className="absolute -top-1 right-0 z-10">
          <PinToDashboardButton widgetKey={widgetKey} isPinned={isPinned} onToggle={onTogglePin} />
        </div>
      )}
    {/* Row 1: core operational — YoY comparison */}
    <div className="grid gap-3 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
      <KPICard title={t('kpis.total_sales')} value={kpis?.total_sales} comparison={comp('total_sales')} tooltip={explain('total_sales')} loading={loading} currency={currency} />
      <KPICard title={t('kpis.total_expenses')} value={kpis?.total_expenses} comparison={comp('total_expenses')} tooltip={explain('total_expenses')} loading={loading} currency={currency} />
      <KPICard title={t('kpis.supplier_purchases')} value={kpis?.supplier_purchases} comparison={comp('supplier_purchases')} tooltip={explain('supplier_purchases')} loading={loading} currency={currency} />
      <KPICard title={t('kpis.fixed_costs')} value={kpis?.fixed_costs_total} tooltip={explain('fixed_costs')} loading={loading} currency={currency} />
      <KPICard title={t('kpis.net_result')} value={kpis?.net_after_fixed} comparison={comp('net_result', 'net_after_fixed')} tooltip={explain('net_result')} loading={loading} variant={kpiVariant('net_result', kpis?.net_after_fixed)} currency={currency} />
      <KPICard title={t('kpis.burn_rate')} value={kpis?.burn_rate_total} tooltip={explain('burn_rate')} loading={loading} currency={currency} />
    </div>

    {/* Row 2: structural + diagnostic supplementary metrics */}
    <div className="grid gap-3 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 mt-3">
      <KPICard
        title={t('kpis.break_even')}
        value={kpis?.break_even != null ? kpis.break_even : t('kpis.not_available')}
        tooltip={breakEvenExplain()}
        loading={loading}
        variant={kpiVariant('break_even', kpis?.break_even, kpis)}
        currency={currency}
      />
      <KPICard title={`${t('kpis.operational_coverage')} ${t('kpis.estimated_badge')}`} value={kpis?.giorni_autonomia != null ? `${Math.round(kpis.giorni_autonomia)}gg` : undefined} tooltip={explain('operational_coverage')} loading={loading} variant={kpiVariant('operational_coverage', kpis?.giorni_autonomia)} />
      <KPICard title={t('kpis.fixed_costs_pct')} value={kpis?.fixed_costs_pct != null ? `${kpis.fixed_costs_pct}%` : undefined} tooltip={explain('fixed_costs_pct')} loading={loading} variant={kpiVariant('fixed_costs_pct', kpis?.fixed_costs_pct)} />
      <KPICard title={t('kpis.operating_margin_pct')} value={kpis?.operating_margin_pct != null ? `${kpis.operating_margin_pct}%` : undefined} tooltip={explain('operating_margin_pct')} loading={loading} variant={kpiVariant('operating_margin_pct', kpis?.operating_margin_pct)} diagnostic />
      <KPICard title={t('kpis.outflow_ratio')} value={outflowRatioStr} tooltip={explain('outflow_ratio')} loading={loading} variant={kpiVariant('outflow_ratio', outflowRatio)} diagnostic />
    </div>
    </div>
  );
};

/**
 * CompactKPI — dense card for Summary tab.
 *
 * Canonical comparison: same period previous year (YoY only).
 * When YoY is unavailable, no comparison is shown (no silent PoP fallback).
 */
const CompactKPI = ({ label, value, yoy, yoyInverse, variant, tooltip, currency = 'EUR' }) => {
  const { t } = useTranslation('cashflow_monitor');
  const [flipped, setFlipped] = useState(false);

  // YoY only — no fallback to period-over-period
  const compValue = yoy != null ? yoy : null;
  const compLabel = yoy != null ? t('kpis.vs_last_year') : null;

  const bgClass =
    variant === 'success' ? 'bg-emerald-50/40 dark:bg-emerald-950/10 border-emerald-200/60' :
    variant === 'danger'  ? 'bg-red-50/40 dark:bg-red-950/10 border-red-200/60' :
    'border-border';

  // ── BACK SIDE ──────────────────────────────────────────────────────────
  const structured = typeof tooltip === 'object' && tooltip?.def;
  if (flipped && tooltip) {
    return (
      <div className="rounded-lg border border-primary/20 bg-primary/[0.02] px-3 py-3 flex flex-col justify-between min-h-[100px]">
        <div>
          <p className="text-sm font-semibold text-primary/80 mb-1">{label}</p>
          {structured ? (
            <div className="space-y-1 text-xs text-muted-foreground leading-relaxed">
              <p>{tooltip.def}</p>
              <p className="text-muted-foreground/70 italic">{tooltip.calc}</p>
              <p className="font-medium text-foreground/70">{tooltip.read}</p>
            </div>
          ) : (
            <p className="text-xs text-muted-foreground leading-relaxed">{tooltip}</p>
          )}
        </div>
        <button
          onClick={() => setFlipped(false)}
          className="mt-2 flex items-center gap-1 text-xs font-medium text-primary hover:text-primary/80 transition-colors self-start"
        >
          <RotateCcw className="h-3 w-3" />
          {t('kpis.back_button')}
        </button>
      </div>
    );
  }

  // ── FRONT SIDE ─────────────────────────────────────────────────────────
  return (
    <div className={`rounded-lg border px-3 py-3 transition-colors hover:border-primary/30 ${bgClass}`}>
      <div className="flex items-center gap-1">
        <span className="text-sm font-medium text-muted-foreground truncate">{label}</span>
        {tooltip && (
          <button onClick={() => setFlipped(true)} className="text-muted-foreground/40 hover:text-primary transition-colors flex-shrink-0" aria-label="Info">
            <Info className="h-3 w-3" />
          </button>
        )}
      </div>
      <p className="text-xl font-bold tracking-tight mt-0.5">
        {typeof value === 'number' ? formatCurrency(value, currency) : (value ?? '\u2014')}
      </p>
      {compValue != null && compLabel && (
        <div className="mt-1">
          <TrendBadge value={compValue} inverse={yoyInverse || false} label={compLabel} />
        </div>
      )}
    </div>
  );
};

/**
 * SummaryKPIStrip — compact 5-card set for the Summary tab.
 *
 * Canonical comparison: same period previous year (YoY only).
 * When YoY is unavailable, comparison is hidden (no silent PoP fallback).
 * Order: Sales, Net Result, Outflow Ratio, Op.Margin %, Operational Coverage.
 */
export const SummaryKPIStrip = ({ kpis, yoy, loading, currency = 'EUR' }) => {
  const { t } = useTranslation('cashflow_monitor');
  const outflowRatio = kpis?.total_outflow_ratio;
  const yp = yoy?.pct || {};

  const explain = (key) => ({
    def: t(`kpis.explain.${key}.def`),
    calc: t(`kpis.explain.${key}.calc`),
    read: t(`kpis.explain.${key}.read`),
  });

  if (loading) {
    return (
      <div className="grid gap-2 grid-cols-1 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
        {[1,2,3,4,5].map(i => <Skeleton key={i} className="h-[80px] w-full rounded-lg" />)}
      </div>
    );
  }

  return (
    <div className="grid gap-2 grid-cols-1 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
      <CompactKPI label={t('kpis.total_sales')} value={kpis?.total_sales} yoy={yp.total_sales} tooltip={explain('total_sales')} currency={currency} />
      <CompactKPI label={t('kpis.net_result')} value={kpis?.net_after_fixed} yoy={yp.net_after_fixed} variant={kpiVariant('net_result', kpis?.net_after_fixed)} tooltip={explain('net_result')} currency={currency} />
      <CompactKPI label={t('kpis.outflow_ratio')} value={outflowRatio != null ? `${outflowRatio}%` : undefined} yoy={yp.total_outflow_ratio} yoyInverse={KPI_TREND_INVERSE.has('outflow_ratio')} variant={kpiVariant('outflow_ratio', outflowRatio)} tooltip={explain('outflow_ratio')} />
      <CompactKPI label={t('kpis.operating_margin_pct')} value={kpis?.operating_margin_pct != null ? `${kpis.operating_margin_pct}%` : undefined} yoy={yp.operating_margin_pct} yoyInverse={KPI_TREND_INVERSE.has('operating_margin_pct')} variant={kpiVariant('operating_margin_pct', kpis?.operating_margin_pct)} tooltip={explain('operating_margin_pct')} />
      <CompactKPI label={`${t('kpis.operational_coverage')} ${t('kpis.estimated_badge')}`} value={kpis?.giorni_autonomia != null ? `${Math.round(kpis.giorni_autonomia)}gg` : undefined} variant={kpiVariant('operational_coverage', kpis?.giorni_autonomia)} tooltip={explain('operational_coverage')} />
    </div>
  );
};

export default KPIStrip;
