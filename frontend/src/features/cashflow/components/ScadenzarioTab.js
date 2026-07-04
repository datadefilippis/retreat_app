/**
 * ScadenzarioTab — Phase 2: DSO/DPO KPIs, Aging chart, Timeline chart, Cash Forecast.
 *
 * Charts follow the standard pattern: Card + ResponsiveContainer + pin support.
 * Empty state shown when no due_date data is available.
 */
import React, { useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../../components/ui/card';
import { Skeleton } from '../../../components/ui/skeleton';
import { formatCurrency, chartTickFormatter } from '../../../lib/utils';
import {
  BarChart, Bar, ComposedChart,
  AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts';
import { PinToDashboardButton } from '../../dashboard/PinToDashboardButton';
import { Info } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import i18n from '../../../i18n';

const LOCALE_MAP = { it: 'it-IT', en: 'en-GB', de: 'de-DE', fr: 'fr-FR' };
const formatChartDate = (dateStr) => {
  const d = new Date(dateStr);
  return d.toLocaleDateString(LOCALE_MAP[i18n.language] || 'it-IT', { month: 'short', day: 'numeric' });
};


// ── KPI Summary Cards ────────────────────────────────────────────────────────

function KpiCard({ label, value, unit, variant, estimated, tooltip }) {
  const colorMap = {
    success: 'text-emerald-600',
    danger:  'text-red-600',
    warning: 'text-amber-600',
    default: 'text-foreground',
  };
  const color = colorMap[variant] || colorMap.default;

  return (
    <div className="rounded-lg border bg-card p-4 text-center" title={tooltip || undefined}>
      <p className="text-xs text-muted-foreground mb-1">
        {label}
        {estimated && <span className="ml-1 text-[10px] text-primary/60">{estimated}</span>}
      </p>
      <p className={`text-xl font-bold ${color}`}>
        {value}{unit && <span className="text-sm font-normal ml-0.5">{unit}</span>}
      </p>
    </div>
  );
}

function ScadenzarioKPIs({ kpis, currency = 'EUR' }) {
  const { t } = useTranslation('cashflow_monitor');
  const dso = kpis?.dso ?? 0;
  const dpo = kpis?.dpo ?? 0;
  const ccc = kpis?.cash_conversion_cycle ?? 0;
  const openRecv = kpis?.open_receivables ?? 0;
  const openPay = kpis?.open_payables ?? 0;
  const estBadge = t('kpis.estimated_badge');

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
      <KpiCard
        label={t('scadenzario.dso_label')}
        value={dso.toFixed(0)}
        unit={t('scadenzario.unit_days')}
        variant={dso > 60 ? 'danger' : dso > 45 ? 'warning' : 'success'}
        estimated={estBadge}
        tooltip={t('kpis.estimated_tooltip_dso')}
      />
      <KpiCard
        label={t('scadenzario.dpo_label')}
        value={dpo.toFixed(0)}
        unit={t('scadenzario.unit_days')}
        variant={dpo > 90 ? 'warning' : 'default'}
        estimated={estBadge}
        tooltip={t('kpis.estimated_tooltip_dpo')}
      />
      <KpiCard
        label={t('scadenzario.ccc_label')}
        value={ccc.toFixed(0)}
        unit={t('scadenzario.unit_days')}
        variant={ccc > 90 ? 'danger' : ccc > 60 ? 'warning' : 'success'}
        estimated={estBadge}
        tooltip={t('kpis.estimated_tooltip_ccc')}
      />
      <KpiCard
        label={t('scadenzario.open_receivables_label')}
        value={formatCurrency(openRecv, currency)}
        variant={openRecv > 0 ? 'warning' : 'default'}
      />
      <KpiCard
        label={t('scadenzario.open_payables_label')}
        value={formatCurrency(openPay, currency)}
        variant={openPay > 0 ? 'danger' : 'default'}
      />
    </div>
  );
}


// ── Data Quality Warning Banner ─────────────────────────────────────────────

function DataQualityBanner() {
  const { t } = useTranslation('cashflow_monitor');
  return (
    <div className="flex items-start gap-2.5 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-300">
      <Info className="mt-0.5 h-4 w-4 flex-shrink-0" />
      <p>{t('scadenzario.data_quality_warning')}</p>
    </div>
  );
}


// ── Aging Chart ──────────────────────────────────────────────────────────────

const AGING_BUCKETS = ['0-30', '31-60', '61-90', '>90'];

function buildAgingData(receivablesAging, payablesAging) {
  const recvMap = {};
  for (const r of (receivablesAging || [])) recvMap[r.bucket] = r.total || 0;
  const payMap = {};
  for (const p of (payablesAging || [])) payMap[p.bucket] = p.total || 0;

  return AGING_BUCKETS.map((bucket) => ({
    bucket: `${bucket}gg`,
    crediti: recvMap[bucket] || 0,
    debiti: payMap[bucket] || 0,
  }));
}

export const AgingChart = ({
  receivablesAging, payablesAging, loading,
  widgetKey, isPinned, onTogglePin, currency = 'EUR',
}) => {
  const { t } = useTranslation('cashflow_monitor');
  const data = useMemo(
    () => buildAgingData(receivablesAging, payablesAging),
    [receivablesAging, payablesAging]
  );
  const hasData = data.some((d) => d.crediti > 0 || d.debiti > 0);

  return (
    <Card className="border border-border">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="font-heading text-lg">{t('scadenzario.aging_title')}</CardTitle>
            <CardDescription>{t('scadenzario.aging_desc')}</CardDescription>
          </div>
          {widgetKey && onTogglePin && (
            <PinToDashboardButton widgetKey={widgetKey} isPinned={isPinned} onToggle={onTogglePin} />
          )}
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <Skeleton className="h-56 md:h-72 w-full" />
        ) : !hasData ? (
          <div className="h-56 md:h-72 flex items-center justify-center text-muted-foreground text-sm">
            {t('scadenzario.empty_aging')}
          </div>
        ) : (
          <div className="h-56 md:h-72" data-testid="aging-chart">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data} barGap={4}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                <XAxis dataKey="bucket" stroke="#94A3B8" fontSize={12} />
                <YAxis stroke="#94A3B8" fontSize={12} tickFormatter={(v) => chartTickFormatter(v, currency)} />
                <Tooltip formatter={(v) => [formatCurrency(v, currency), '']} />
                <Legend />
                <Bar dataKey="crediti" fill="#22C55E" name={t('scadenzario.aging_receivables')} radius={[4, 4, 0, 0]} />
                <Bar dataKey="debiti" fill="#EF4444" name={t('scadenzario.aging_payables')} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  );
};


// ── Timeline Chart ───────────────────────────────────────────────────────────

function buildTimelineData(upcomingRecv, upcomingPay) {
  const dateMap = {};

  for (const r of (upcomingRecv || [])) {
    if (!dateMap[r.date]) dateMap[r.date] = { date: r.date, incassi: 0, pagamenti: 0 };
    dateMap[r.date].incassi += r.total || 0;
  }
  for (const p of (upcomingPay || [])) {
    if (!dateMap[p.date]) dateMap[p.date] = { date: p.date, incassi: 0, pagamenti: 0 };
    dateMap[p.date].pagamenti += p.total || 0;
  }

  return Object.values(dateMap).sort((a, b) => a.date.localeCompare(b.date));
}

export const TimelineChart = ({
  upcomingReceivables, upcomingPayables, loading,
  widgetKey, isPinned, onTogglePin, currency = 'EUR',
}) => {
  const { t } = useTranslation('cashflow_monitor');
  const data = useMemo(
    () => buildTimelineData(upcomingReceivables, upcomingPayables),
    [upcomingReceivables, upcomingPayables]
  );

  return (
    <Card className="border border-border">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="font-heading text-lg">{t('scadenzario.timeline_title')}</CardTitle>
            <CardDescription>{t('scadenzario.timeline_desc')}</CardDescription>
          </div>
          {widgetKey && onTogglePin && (
            <PinToDashboardButton widgetKey={widgetKey} isPinned={isPinned} onToggle={onTogglePin} />
          )}
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <Skeleton className="h-56 md:h-72 w-full" />
        ) : !data.length ? (
          <div className="h-56 md:h-72 flex items-center justify-center text-muted-foreground text-sm">
            {t('scadenzario.empty_timeline')}
          </div>
        ) : (
          <div className="h-56 md:h-72" data-testid="timeline-chart">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={data}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                <XAxis dataKey="date" tickFormatter={formatChartDate} stroke="#94A3B8" fontSize={11} />
                <YAxis stroke="#94A3B8" fontSize={12} tickFormatter={(v) => chartTickFormatter(v, currency)} />
                <Tooltip
                  formatter={(v, name) => [formatCurrency(v, currency), name === 'incassi' ? t('scadenzario.timeline_receivables') : t('scadenzario.timeline_payables')]}
                  labelFormatter={formatChartDate}
                />
                <Legend />
                <Bar dataKey="incassi" fill="#22C55E" name={t('scadenzario.timeline_receivables')} radius={[4, 4, 0, 0]} />
                <Bar dataKey="pagamenti" fill="#EF4444" name={t('scadenzario.timeline_payables')} radius={[4, 4, 0, 0]} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  );
};


// ── Cash Forecast Chart ──────────────────────────────────────────────────────

function buildForecastData(upcomingRecv, upcomingPay, currentCash) {
  const dateMap = {};

  for (const r of (upcomingRecv || [])) {
    if (!dateMap[r.date]) dateMap[r.date] = { date: r.date, recv: 0, pay: 0 };
    dateMap[r.date].recv += r.total || 0;
  }
  for (const p of (upcomingPay || [])) {
    if (!dateMap[p.date]) dateMap[p.date] = { date: p.date, recv: 0, pay: 0 };
    dateMap[p.date].pay += p.total || 0;
  }

  const sorted = Object.values(dateMap).sort((a, b) => a.date.localeCompare(b.date));
  let running = currentCash || 0;

  return sorted.map((d) => {
    running += d.recv - d.pay;
    return {
      date: d.date,
      proiezione: Math.round(running * 100) / 100,
    };
  });
}

export const CashForecastChart = ({
  upcomingReceivables, upcomingPayables, currentCash, loading,
  widgetKey, isPinned, onTogglePin, currency = 'EUR',
}) => {
  const { t } = useTranslation('cashflow_monitor');
  const data = useMemo(
    () => buildForecastData(upcomingReceivables, upcomingPayables, currentCash),
    [upcomingReceivables, upcomingPayables, currentCash]
  );

  return (
    <Card className="border border-border">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="font-heading text-lg">
              {t('scadenzario.forecast_title')} <span className="text-xs font-normal text-primary/60">{t('kpis.estimated_badge')}</span>
            </CardTitle>
            <CardDescription>{t('scadenzario.forecast_desc')}</CardDescription>
          </div>
          {widgetKey && onTogglePin && (
            <PinToDashboardButton widgetKey={widgetKey} isPinned={isPinned} onToggle={onTogglePin} />
          )}
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <Skeleton className="h-56 md:h-72 w-full" />
        ) : !data.length ? (
          <div className="h-56 md:h-72 flex items-center justify-center text-muted-foreground text-sm">
            {t('scadenzario.empty_forecast')}
          </div>
        ) : (
          <div className="h-56 md:h-72" data-testid="cash-forecast-chart">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                <XAxis dataKey="date" tickFormatter={formatChartDate} stroke="#94A3B8" fontSize={11} />
                <YAxis stroke="#94A3B8" fontSize={12} tickFormatter={(v) => chartTickFormatter(v, currency)} />
                <Tooltip
                  formatter={(v) => [formatCurrency(v, currency), t('scadenzario.forecast_tooltip_name')]}
                  labelFormatter={formatChartDate}
                />
                <defs>
                  <linearGradient id="forecastGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#3B82F6" stopOpacity={0.05} />
                  </linearGradient>
                </defs>
                <Area
                  type="monotone"
                  dataKey="proiezione"
                  stroke="#3B82F6"
                  strokeWidth={2}
                  fill="url(#forecastGradient)"
                  name={t('scadenzario.forecast_legend')}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  );
};


// ── ScadenzarioTab — container ───────────────────────────────────────────────

export const ScadenzarioTab = ({
  kpis,
  scadenzario,
  loading,
  agingWidgetKey,
  isAgingPinned,
  timelineWidgetKey,
  isTimelinePinned,
  forecastWidgetKey,
  isForecastPinned,
  onTogglePin,
  currency = 'EUR',
}) => {
  const { t } = useTranslation('cashflow_monitor');
  const hasScadenzarioData =
    (scadenzario?.receivables_aging?.length > 0) ||
    (scadenzario?.payables_aging?.length > 0) ||
    (scadenzario?.upcoming_receivables?.length > 0) ||
    (scadenzario?.upcoming_payables?.length > 0);

  if (!loading && !hasScadenzarioData) {
    return (
      <div className="mt-6">
        <Card className="border border-border">
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground text-sm">
              {t('scadenzario.no_data_message')}
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="mt-6 space-y-6">
      {/* Data quality warning */}
      <DataQualityBanner />

      {/* KPI Summary */}
      <ScadenzarioKPIs kpis={kpis} currency={currency} />

      {/* Aging Chart */}
      <AgingChart
        receivablesAging={scadenzario?.receivables_aging}
        payablesAging={scadenzario?.payables_aging}
        loading={loading}
        widgetKey={agingWidgetKey}
        isPinned={isAgingPinned}
        onTogglePin={onTogglePin}
        currency={currency}
      />

      {/* Timeline + Cash Forecast */}
      <div className="grid gap-6 lg:grid-cols-2">
        <TimelineChart
          upcomingReceivables={scadenzario?.upcoming_receivables}
          upcomingPayables={scadenzario?.upcoming_payables}
          loading={loading}
          widgetKey={timelineWidgetKey}
          isPinned={isTimelinePinned}
          onTogglePin={onTogglePin}
          currency={currency}
        />
        <CashForecastChart
          upcomingReceivables={scadenzario?.upcoming_receivables}
          upcomingPayables={scadenzario?.upcoming_payables}
          currentCash={kpis?.net_after_fixed ?? 0}
          loading={loading}
          widgetKey={forecastWidgetKey}
          isPinned={isForecastPinned}
          onTogglePin={onTogglePin}
          currency={currency}
        />
      </div>
    </div>
  );
};

export default ScadenzarioTab;
