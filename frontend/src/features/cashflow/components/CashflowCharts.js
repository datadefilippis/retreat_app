import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../../components/ui/card';
import { Skeleton } from '../../../components/ui/skeleton';
import { Info } from 'lucide-react';
import { formatCurrency, chartTickFormatter } from '../../../lib/utils';
import {
  ComposedChart, Bar, LineChart, Line, AreaChart, Area,
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


/**
 * SalesExpensesChart — daily Sales vs Expenses bar chart.
 */
export const SalesExpensesChart = ({ data, loading, widgetKey, isPinned, onTogglePin, currency = 'EUR' }) => {
  const { t } = useTranslation('cashflow_monitor');
  return (
  <Card className="border border-border">
    <CardHeader className="pb-2">
      <div className="flex items-center justify-between">
        <div>
          <CardTitle className="font-heading text-lg">{t('charts.sales_expenses_title')}</CardTitle>
          <CardDescription>{t('charts.sales_expenses_desc')}</CardDescription>
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
        <div className="h-56 md:h-72" data-testid="sales-expenses-chart">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
              <XAxis dataKey="date" tickFormatter={formatChartDate} stroke="#94A3B8" fontSize={12} />
              <YAxis stroke="#94A3B8" fontSize={12} tickFormatter={(v) => chartTickFormatter(v, currency)} />
              <Tooltip formatter={(v) => [formatCurrency(v, currency), '']} labelFormatter={formatChartDate} />
              <Legend />
              <Bar dataKey="sales" fill="#4361EE" name={t('charts.legend_sales')} radius={[2, 2, 0, 0]} />
              <Bar dataKey="expenses" fill="#EF4444" name={t('charts.legend_expenses')} radius={[2, 2, 0, 0]} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}
    </CardContent>
  </Card>
  );
};


/**
 * NetCashflowChart — area chart for daily net cashflow.
 */
export const NetCashflowChart = ({ data, loading, widgetKey, isPinned, onTogglePin, currency = 'EUR' }) => {
  const { t } = useTranslation('cashflow_monitor');
  return (
  <Card className="border border-border">
    <CardHeader className="pb-2">
      <div className="flex items-center justify-between">
        <div>
          <CardTitle className="font-heading text-lg">{t('charts.net_cashflow_title')}</CardTitle>
          <CardDescription>{t('charts.net_cashflow_desc')}</CardDescription>
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
        <div className="h-56 md:h-72" data-testid="cashflow-trend-chart">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data}>
              <defs>
                <linearGradient id="netGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#14B8A6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#14B8A6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
              <XAxis dataKey="date" tickFormatter={formatChartDate} stroke="#94A3B8" fontSize={12} />
              <YAxis stroke="#94A3B8" fontSize={12} tickFormatter={(v) => chartTickFormatter(v, currency)} />
              <Tooltip formatter={(v) => [formatCurrency(v, currency), '']} labelFormatter={formatChartDate} />
              <Legend />
              <Area
                type="monotone"
                dataKey="net_cashflow"
                stroke="#14B8A6"
                fill="url(#netGradient)"
                strokeWidth={2}
                name={t('charts.legend_net_cashflow')}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </CardContent>
  </Card>
  );
};


/**
 * CumulativeCashflowChart — area chart showing running cumulative cashflow.
 */
export const CumulativeCashflowChart = ({ data, loading, widgetKey, isPinned, onTogglePin, currency = 'EUR' }) => {
  const { t } = useTranslation('cashflow_monitor');
  const [showInfo, setShowInfo] = useState(false);
  return (
  <Card className="border border-border">
    <CardHeader className="pb-2">
      <div className="flex items-center justify-between">
        <div>
          <CardTitle className="font-heading text-lg flex items-center gap-1.5">
            {t('charts.cumulative_title')}
            <button onClick={() => setShowInfo(v => !v)} className="text-muted-foreground/40 hover:text-primary transition-colors" aria-label="Info">
              <Info className="h-3.5 w-3.5" />
            </button>
          </CardTitle>
          <CardDescription>{t('charts.cumulative_desc')}</CardDescription>
        </div>
        {widgetKey && onTogglePin && (
          <PinToDashboardButton widgetKey={widgetKey} isPinned={isPinned} onToggle={onTogglePin} />
        )}
      </div>
      {showInfo && (
        <p className="mt-2 text-xs text-amber-700 bg-amber-50 rounded-md px-3 py-2 leading-relaxed border border-amber-200">
          {t('charts.cumulative_info')}
        </p>
      )}
    </CardHeader>
    <CardContent>
      {loading ? (
        <Skeleton className="h-56 md:h-72 w-full" />
      ) : (
        <div className="h-56 md:h-72" data-testid="cumulative-cashflow-chart">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data}>
              <defs>
                <linearGradient id="cumulGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#3B82F6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
              <XAxis dataKey="date" tickFormatter={formatChartDate} stroke="#94A3B8" fontSize={12} />
              <YAxis stroke="#94A3B8" fontSize={12} tickFormatter={(v) => chartTickFormatter(v, currency)} />
              <Tooltip formatter={(v) => [formatCurrency(v, currency), '']} labelFormatter={formatChartDate} />
              <Legend />
              <Area
                type="monotone"
                dataKey="cumulative"
                stroke="#3B82F6"
                fill="url(#cumulGradient)"
                strokeWidth={2}
                name={t('charts.legend_cumulative')}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </CardContent>
  </Card>
  );
};


/**
 * DetailedTrendsCharts — Sales and Expenses line charts with 7-day MA.
 */
export const DetailedTrendsCharts = ({ data, loading, widgetKey, isPinned, onTogglePin, currency = 'EUR' }) => {
  const { t } = useTranslation('cashflow_monitor');
  return (
  <div className="grid gap-6 lg:grid-cols-2">
    <Card className="border border-border">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="font-heading text-lg">{t('charts.trend_sales_title')}</CardTitle>
            <CardDescription>{t('charts.trend_sales_desc')}</CardDescription>
          </div>
          {widgetKey && onTogglePin && (
            <PinToDashboardButton widgetKey={widgetKey} isPinned={isPinned} onToggle={onTogglePin} />
          )}
        </div>
      </CardHeader>
      <CardContent>
        {loading ? <Skeleton className="h-56 md:h-72 w-full" /> : (
          <div className="h-56 md:h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                <XAxis dataKey="date" tickFormatter={formatChartDate} stroke="#94A3B8" fontSize={12} />
                <YAxis stroke="#94A3B8" fontSize={12} tickFormatter={(v) => chartTickFormatter(v, currency)} />
                <Tooltip formatter={(v) => [formatCurrency(v, currency), '']} labelFormatter={formatChartDate} />
                <Legend />
                <Line type="monotone" dataKey="sales" stroke="#4361EE" strokeWidth={2} dot={false} name={t('charts.legend_daily_sales')} />
                <Line type="monotone" dataKey="sales_ma7" stroke="#94A3B8" strokeWidth={2} strokeDasharray="5 5" dot={false} name={t('charts.legend_ma7')} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>

    <Card className="border border-border">
      <CardHeader className="pb-2">
        <CardTitle className="font-heading text-lg">{t('charts.trend_expenses_title')}</CardTitle>
        <CardDescription>{t('charts.trend_expenses_desc')}</CardDescription>
      </CardHeader>
      <CardContent>
        {loading ? <Skeleton className="h-56 md:h-72 w-full" /> : (
          <div className="h-56 md:h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                <XAxis dataKey="date" tickFormatter={formatChartDate} stroke="#94A3B8" fontSize={12} />
                <YAxis stroke="#94A3B8" fontSize={12} tickFormatter={(v) => chartTickFormatter(v, currency)} />
                <Tooltip formatter={(v) => [formatCurrency(v, currency), '']} labelFormatter={formatChartDate} />
                <Legend />
                <Line type="monotone" dataKey="expenses" stroke="#EF4444" strokeWidth={2} dot={false} name={t('charts.legend_daily_expenses')} />
                <Line type="monotone" dataKey="expenses_ma7" stroke="#94A3B8" strokeWidth={2} strokeDasharray="5 5" dot={false} name={t('charts.legend_ma7')} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  </div>
  );
};
