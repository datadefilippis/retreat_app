/**
 * PurchaseDistributionChart — Pareto chart for purchase distribution
 * by Prodotto (product) or Categoria (category).
 *
 * Renders descending bars with a cumulative percentage line.
 * Toggle between "Per Prodotto" and "Per Categoria".
 * Uses data from overview.purchase_distribution.
 */
import React, { useState, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../../components/ui/card';
import { Skeleton } from '../../../components/ui/skeleton';
import { Button } from '../../../components/ui/button';
import { formatCurrency, chartTickFormatter } from '../../../lib/utils';
import {
  Bar, ComposedChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts';
import { useTranslation } from 'react-i18next';
import { PinToDashboardButton } from '../../dashboard/PinToDashboardButton';

const MAX_ITEMS = 10;

function buildParetoData(items, otherLabel) {
  if (!items?.length) return [];

  // Take top N, group rest as "Altro"
  const top = items.slice(0, MAX_ITEMS);
  const rest = items.slice(MAX_ITEMS);
  const restTotal = rest.reduce((sum, r) => sum + (r.total || 0), 0);
  const restCount = rest.reduce((sum, r) => sum + (r.count || 0), 0);

  const display = [...top];
  if (restTotal > 0) {
    display.push({ name: otherLabel, total: restTotal, count: restCount });
  }

  const grandTotal = display.reduce((sum, d) => sum + (d.total || 0), 0);
  let cumulative = 0;

  return display.map((d) => {
    cumulative += d.total || 0;
    return {
      name: d.name || '—',
      total: d.total || 0,
      count: d.count || 0,
      cumulativePct: grandTotal > 0 ? Math.round((cumulative / grandTotal) * 100) : 0,
    };
  });
}

export const PurchaseDistributionChart = ({ distribution, loading, widgetKey, isPinned, onTogglePin, currency = 'EUR' }) => {
  const { t } = useTranslation('cashflow_monitor');
  const [view, setView] = useState('product'); // 'product' | 'category'

  const byProduct = distribution?.by_product ?? [];
  const byCategory = distribution?.by_category ?? [];

  const otherLabel = t('forms.chart_other', 'Altro');

  const data = useMemo(() => {
    const items = view === 'product' ? byProduct : byCategory;
    return buildParetoData(items, otherLabel);
  }, [view, byProduct, byCategory, otherLabel]);

  const hasData = data.length > 0;
  const isEmpty = view === 'category' ? byCategory.length === 0 : byProduct.length === 0;

  return (
    <Card className="border border-border">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="font-heading text-lg">
              {t('forms.purchase_distribution', 'Distribuzione Acquisti')}
            </CardTitle>
            <CardDescription>
              {view === 'product'
                ? t('forms.product_tooltip')
                : t('forms.purchase_category_tooltip')
              }
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            {widgetKey && onTogglePin && (
              <PinToDashboardButton widgetKey={widgetKey} isPinned={isPinned} onToggle={onTogglePin} />
            )}
            <div className="flex gap-1">
            <Button
              variant={view === 'product' ? 'default' : 'outline'}
              size="sm"
              className="h-7 text-xs"
              onClick={() => setView('product')}
            >
              {t('forms.by_product', 'Per Prodotto')}
            </Button>
            <Button
              variant={view === 'category' ? 'default' : 'outline'}
              size="sm"
              className="h-7 text-xs"
              onClick={() => setView('category')}
            >
              {t('forms.by_category', 'Per Categoria')}
            </Button>
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <Skeleton className="h-56 md:h-72 w-full" />
        ) : !hasData || isEmpty ? (
          <div className="h-56 md:h-72 flex items-center justify-center text-muted-foreground text-sm">
            {view === 'category'
              ? t('forms.purchase_category_tooltip', 'Nessun dato per categoria')
              : t('forms.product_tooltip', 'Nessun dato per prodotto')
            }
          </div>
        ) : (
          <div className="h-56 md:h-72" data-testid="purchase-distribution-chart">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={data}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                <XAxis
                  dataKey="name"
                  stroke="#94A3B8"
                  fontSize={11}
                  angle={-20}
                  textAnchor="end"
                  height={50}
                  interval={0}
                />
                <YAxis
                  yAxisId="left"
                  stroke="#94A3B8"
                  fontSize={12}
                  tickFormatter={(v) => chartTickFormatter(v, currency)}
                />
                <YAxis
                  yAxisId="right"
                  orientation="right"
                  stroke="#94A3B8"
                  fontSize={12}
                  domain={[0, 100]}
                  tickFormatter={(v) => `${v}%`}
                />
                <Tooltip
                  formatter={(value, name) =>
                    name === 'cumulativePct'
                      ? [`${value}%`, t('forms.cumulative_pct', 'Cumulativo %')]
                      : [formatCurrency(value, currency), view === 'product' ? t('forms.product') : t('forms.purchase_category')]
                  }
                />
                <Legend />
                <Bar
                  yAxisId="left"
                  dataKey="total"
                  fill={view === 'product' ? '#F97316' : '#8B5CF6'}
                  name={view === 'product' ? t('forms.product') : t('forms.purchase_category')}
                  radius={[4, 4, 0, 0]}
                />
                <Line
                  yAxisId="right"
                  dataKey="cumulativePct"
                  stroke="#1E40AF"
                  strokeWidth={2}
                  dot={false}
                  name={t('forms.cumulative_pct', 'Cumulativo %')}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default PurchaseDistributionChart;
