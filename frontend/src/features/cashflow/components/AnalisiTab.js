/**
 * AnalisiTab — Revenue Flow, Pareto Fornitori, Composizione Uscite.
 *
 * Revenue Flow uses pure HTML/CSS horizontal bars (no chart library).
 * Pareto and Composizione use Recharts.
 */
import React from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../../components/ui/card';
import { Skeleton } from '../../../components/ui/skeleton';
import { formatCurrency, chartTickFormatter } from '../../../lib/utils';
import {
  Bar, ComposedChart, Line,
  AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts';
import { PinToDashboardButton } from '../../dashboard/PinToDashboardButton';
import { useTranslation } from 'react-i18next';
import i18n from '../../../i18n';

const LOCALE_MAP = { it: 'it-IT', en: 'en-GB', de: 'de-DE', fr: 'fr-FR' };
const formatChartDate = (dateStr) => {
  const d = new Date(dateStr);
  return d.toLocaleDateString(LOCALE_MAP[i18n.language] || 'it-IT', { month: 'short', day: 'numeric' });
};


// ── Revenue Flow ────────────────────────────────────────────────────────────
// Pure HTML/CSS "revenue consumption" visual.
// Shows: Revenue → cost rows with proportional bars → Net Result.
// Far more intuitive than a chart-based waterfall for non-financial users.

function FlowRow({ label, value, pct, pctDisplay, barColor, barBg, sign, currency, negative }) {
  const pctText = pctDisplay !== undefined ? pctDisplay : `${pct}%`;
  return (
    <div className="flex items-center gap-3">
      <div className="w-28 sm:w-36 shrink-0 text-right">
        <p className="text-sm font-medium truncate">{label}</p>
      </div>
      <div className="flex-1 min-w-0">
        <div className={`h-7 rounded-md ${barBg} overflow-hidden`}>
          <div
            className={`h-full rounded-md ${barColor} transition-all duration-700 ease-out`}
            style={{ width: `${Math.max(pct, 1)}%` }}
          />
        </div>
      </div>
      <div className="w-24 sm:w-32 shrink-0 text-right">
        <p className={`text-sm font-bold ${negative ? 'text-red-600' : ''}`}>{sign}{formatCurrency(value, currency)}</p>
        <p className={`text-xs ${negative ? 'text-red-500 font-medium' : 'text-muted-foreground'}`}>{pctText}</p>
      </div>
    </div>
  );
}

export const RevenueFlowChart = ({ kpis, loading, widgetKey, isPinned, onTogglePin, currency = 'EUR' }) => {
  const { t } = useTranslation('cashflow_monitor');

  if (loading) {
    return (
      <Card className="border border-border">
        <CardContent className="p-5"><Skeleton className="h-64 w-full" /></CardContent>
      </Card>
    );
  }

  const sales     = kpis?.total_sales || 0;
  const expenses  = kpis?.total_expenses || 0;
  const purchases = kpis?.supplier_purchases || 0;
  const fixed     = kpis?.fixed_costs_total || 0;
  const net       = kpis?.net_after_fixed ?? (sales - expenses - purchases - fixed);
  const pct = (v) => sales > 0 ? Math.round(v / sales * 100) : 0;
  const isPositive = net >= 0;

  if (!sales) return null;

  return (
    <Card className="border border-border">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="font-heading text-lg">{t('analysis.flow_title')}</CardTitle>
            <CardDescription>{t('analysis.flow_desc')}</CardDescription>
          </div>
          {widgetKey && onTogglePin && (
            <PinToDashboardButton widgetKey={widgetKey} isPinned={isPinned} onToggle={onTogglePin} />
          )}
        </div>
      </CardHeader>
      <CardContent data-testid="revenue-flow">
        <div className="space-y-3">
          {/* Revenue — the starting base */}
          <FlowRow
            label={t('analysis.flow_revenue')}
            value={sales}
            pct={100}
            barColor="bg-emerald-500"
            barBg="bg-emerald-100 dark:bg-emerald-950/30"
            sign=""
            currency={currency}
          />

          {/* Divider */}
          <div className="border-t border-dashed border-border my-1" />

          {/* Cost buckets — sorted largest to smallest (Pareto order) */}
          {[
            { label: t('analysis.flow_expenses'),  value: expenses,  barColor: 'bg-red-500',    barBg: 'bg-red-100 dark:bg-red-950/30' },
            { label: t('analysis.flow_purchases'), value: purchases, barColor: 'bg-orange-500', barBg: 'bg-orange-100 dark:bg-orange-950/30' },
            { label: t('analysis.flow_fixed'),     value: fixed,     barColor: 'bg-violet-500', barBg: 'bg-violet-100 dark:bg-violet-950/30' },
          ]
            .filter(row => row.value > 0)
            .sort((a, b) => b.value - a.value)
            .map((row) => (
              <FlowRow
                key={row.label}
                label={row.label}
                value={row.value}
                pct={pct(row.value)}
                barColor={row.barColor}
                barBg={row.barBg}
                sign={'\u2212'}
                currency={currency}
              />
            ))
          }

          {/* Divider */}
          <div className="border-t-2 border-border my-1" />

          {/* Net Result — green if positive, red with minus % if negative */}
          <FlowRow
            label={t('analysis.flow_result')}
            value={Math.abs(net)}
            pct={pct(Math.abs(net))}
            pctDisplay={isPositive ? `${pct(net)}%` : `\u2212${pct(Math.abs(net))}%`}
            barColor={isPositive ? 'bg-emerald-500' : 'bg-red-500'}
            barBg={isPositive ? 'bg-emerald-100 dark:bg-emerald-950/30' : 'bg-red-100 dark:bg-red-950/30'}
            sign={isPositive ? '+' : '\u2212'}
            negative={!isPositive}
            currency={currency}
          />
        </div>
      </CardContent>
    </Card>
  );
};


// ── Pareto Fornitori ────────────────────────────────────────────────────────
// Bar: totale per fornitore (desc)  |  Line: % cumulativa (asse Y destro 0-100%)

function buildParetoData(topSuppliers) {
  if (!topSuppliers?.length) return [];

  const total = topSuppliers.reduce((sum, s) => sum + (s.total || 0), 0);
  let cumulative = 0;

  return topSuppliers.map((s) => {
    cumulative += s.total || 0;
    return {
      name: s.supplier || 'N/D',
      total: s.total || 0,
      cumulativePct: total > 0 ? Math.round((cumulative / total) * 100) : 0,
    };
  });
}

export const ParetoFornitori = ({ topSuppliers, loading, widgetKey, isPinned, onTogglePin, currency = 'EUR' }) => {
  const { t } = useTranslation('cashflow_monitor');
  const data = buildParetoData(topSuppliers);

  return (
    <Card className="border border-border">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="font-heading text-lg">{t('analysis.pareto_title')}</CardTitle>
            <CardDescription>{t('analysis.pareto_desc')}</CardDescription>
          </div>
          {widgetKey && onTogglePin && (
            <PinToDashboardButton widgetKey={widgetKey} isPinned={isPinned} onToggle={onTogglePin} />
          )}
        </div>
      </CardHeader>
      <CardContent>
        {loading || !data.length ? (
          loading ? <Skeleton className="h-56 md:h-72 w-full" /> : (
            <div className="h-56 md:h-72 flex items-center justify-center text-muted-foreground text-sm">
              {t('analysis.pareto_no_data')}
            </div>
          )
        ) : (
          <div className="h-56 md:h-72" data-testid="pareto-chart">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={data}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                <XAxis dataKey="name" stroke="#94A3B8" fontSize={11} angle={-20} textAnchor="end" height={50} />
                <YAxis yAxisId="left" stroke="#94A3B8" fontSize={12} tickFormatter={(v) => chartTickFormatter(v, currency)} />
                <YAxis yAxisId="right" orientation="right" stroke="#94A3B8" fontSize={12} domain={[0, 100]} tickFormatter={(v) => `${v}%`} />
                <Tooltip
                  formatter={(value, name) =>
                    name === 'cumulativePct' ? [`${value}%`, t('analysis.pareto_cumulative_pct')] : [formatCurrency(value, currency), t('analysis.pareto_amount')]
                  }
                />
                <Legend />
                <Bar yAxisId="left" dataKey="total" fill="#F97316" name={t('analysis.pareto_amount')} radius={[4, 4, 0, 0]} />
                <Line yAxisId="right" dataKey="cumulativePct" stroke="#1E40AF" strokeWidth={2} dot={false} name={t('analysis.pareto_cumulative_pct')} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  );
};


// ── Composizione Uscite (Stacked Area) ──────────────────────────────────────
// Shows Bucket A (red), Bucket B (orange), Bucket C (purple) stacked over time.

export const ComposizioneUscite = ({ data, loading, widgetKey, isPinned, onTogglePin, currency = 'EUR' }) => {
  const { t } = useTranslation('cashflow_monitor');
  return (
  <Card className="border border-border">
    <CardHeader className="pb-2">
      <div className="flex items-center justify-between">
        <div>
          <CardTitle className="font-heading text-lg">{t('analysis.composition_title')}</CardTitle>
          <CardDescription>{t('analysis.composition_desc')}</CardDescription>
        </div>
        {widgetKey && onTogglePin && (
          <PinToDashboardButton widgetKey={widgetKey} isPinned={isPinned} onToggle={onTogglePin} />
        )}
      </div>
    </CardHeader>
    <CardContent>
      {loading ? (
        <Skeleton className="h-56 md:h-72 w-full" />
      ) : (
        <div className="h-56 md:h-72" data-testid="composizione-uscite-chart">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
              <XAxis dataKey="date" tickFormatter={formatChartDate} stroke="#94A3B8" fontSize={12} />
              <YAxis stroke="#94A3B8" fontSize={12} tickFormatter={(v) => chartTickFormatter(v, currency)} />
              <Tooltip formatter={(v) => [formatCurrency(v, currency), '']} labelFormatter={formatChartDate} />
              <Legend />
              <Area type="monotone" dataKey="expenses" stackId="outflows" fill="#EF4444" stroke="#EF4444" fillOpacity={0.6} name={t('analysis.composition_expenses')} />
              <Area type="monotone" dataKey="purchases" stackId="outflows" fill="#F97316" stroke="#F97316" fillOpacity={0.6} name={t('analysis.composition_purchases')} />
              <Area type="monotone" dataKey="fixed_costs_daily" stackId="outflows" fill="#8B5CF6" stroke="#8B5CF6" fillOpacity={0.6} name={t('analysis.composition_fixed')} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </CardContent>
  </Card>
  );
};


// ── AnalisiTab — container ──────────────────────────────────────────────────

export const AnalisiTab = ({
  kpis,
  dailySeries,
  topSuppliers,
  loading,
  waterfallWidgetKey,
  isWaterfallPinned,
  paretoWidgetKey,
  isParetoPinned,
  composizioneWidgetKey,
  isComposizionePinned,
  onTogglePin,
  currency = 'EUR',
}) => (
  <div className="mt-6 space-y-6">
    <RevenueFlowChart
      kpis={kpis}
      loading={loading}
      widgetKey={waterfallWidgetKey}
      isPinned={isWaterfallPinned}
      onTogglePin={onTogglePin}
      currency={currency}
    />
    <div className="grid gap-6 lg:grid-cols-2">
      <ParetoFornitori
        topSuppliers={topSuppliers}
        loading={loading}
        widgetKey={paretoWidgetKey}
        isPinned={isParetoPinned}
        onTogglePin={onTogglePin}
        currency={currency}
      />
      <ComposizioneUscite
        data={dailySeries}
        loading={loading}
        widgetKey={composizioneWidgetKey}
        isPinned={isComposizionePinned}
        onTogglePin={onTogglePin}
        currency={currency}
      />
    </div>
  </div>
);

export default AnalisiTab;
