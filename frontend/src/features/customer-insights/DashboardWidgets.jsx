/**
 * Customers Light — dashboard widget components.
 * Localized via customers_light namespace.
 */
import React from 'react';
import { Card, CardContent } from '../../components/ui/card';
import { Badge } from '../../components/ui/badge';
import { Skeleton } from '../../components/ui/skeleton';
import { Users, UserCheck, UserX, Target } from 'lucide-react';
import { formatCurrency } from '../../lib/utils';
import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip, Legend } from 'recharts';
import { useTranslation } from 'react-i18next';
import { useCurrency } from '../../context/AuthContext';

const SEGMENT_COLORS = {
  top: '#3B82F6',
  active: '#22C55E',
  new: '#8B5CF6',
  occasional: '#F59E0B',
  inactive: '#EF4444',
};


// ── KPI Strip Widget ─────────────────────────────────────────────────────────

export function CustomerKPIStripWidget({ kpis, loading }) {
  const { t } = useTranslation('customers_light');

  if (!kpis && !loading) return null;

  const cards = [
    { title: t('widgets.customers_label'), value: kpis?.total_customers, icon: Users, format: 'int' },
    { title: t('widgets.active_label'), value: kpis?.active_customers, icon: UserCheck, format: 'int' },
    { title: t('widgets.inactive_pct_label'), value: kpis?.inactive_rate_pct, icon: UserX, format: 'pct' },
    { title: t('widgets.top10_pct_label'), value: kpis?.top_10_share_pct, icon: Target, format: 'pct' },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      {cards.map((c) => {
        if (loading) {
          return (
            <Card key={c.title} className="border border-border border-l-4 border-l-primary">
              <CardContent className="p-3">
                <Skeleton className="h-3 w-16 mb-2" />
                <Skeleton className="h-6 w-12" />
              </CardContent>
            </Card>
          );
        }

        let displayValue;
        if (c.format === 'pct') displayValue = `${(c.value || 0).toFixed(1)}%`;
        else displayValue = c.value ?? 0;

        const Icon = c.icon;

        return (
          <Card key={c.title} className="border border-border border-l-4 border-l-primary">
            <CardContent className="p-3">
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">{c.title}</span>
                <Icon className="h-3.5 w-3.5 text-muted-foreground" />
              </div>
              <div className="mt-1">
                <span className="font-heading text-lg font-bold">{displayValue}</span>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}


// ── Top Customers Widget ─────────────────────────────────────────────────────

export function TopCustomersWidget({ customers, loading }) {
  const { t } = useTranslation('customers_light');
  const orgCurrency = useCurrency();

  if (loading) {
    return <div className="space-y-2">{[1,2,3,4,5].map(i => <Skeleton key={i} className="h-8" />)}</div>;
  }

  if (!customers || customers.length === 0) {
    return <p className="text-sm text-muted-foreground text-center py-4">{t('widgets.no_data')}</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b">
            <th className="text-left p-2 text-xs text-muted-foreground">{t('widgets.col_customer')}</th>
            <th className="text-right p-2 text-xs text-muted-foreground">{t('widgets.col_revenue')}</th>
            <th className="text-right p-2 text-xs text-muted-foreground">{t('widgets.col_share')}</th>
          </tr>
        </thead>
        <tbody>
          {customers.slice(0, 5).map((c, i) => (
            <tr key={i} className="border-b last:border-0">
              <td className="p-2 font-medium text-xs">{c.customer_name || '—'}</td>
              <td className="p-2 text-right text-xs font-mono">{formatCurrency(c.total_revenue, orgCurrency)}</td>
              <td className="p-2 text-right text-xs">{c.revenue_share_pct?.toFixed(1)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}


// ── Segment Chart Widget ─────────────────────────────────────────────────────

export function SegmentChartWidget({ segments, loading }) {
  const { t } = useTranslation('customers_light');

  if (loading) return <Skeleton className="h-40" />;

  if (!segments || segments.length === 0) {
    return <p className="text-sm text-muted-foreground text-center py-4">{t('widgets.no_data_short')}</p>;
  }

  const data = segments.map((s) => ({
    name: t(`segments.${s.segment}`, { defaultValue: s.segment }),
    value: s.count,
    fill: SEGMENT_COLORS[s.segment] || '#94A3B8',
  }));

  return (
    <ResponsiveContainer width="100%" height={180}>
      <PieChart>
        <Pie
          data={data}
          dataKey="value"
          nameKey="name"
          cx="50%"
          cy="50%"
          outerRadius={60}
          label={({ name, value }) => `${name}: ${value}`}
        >
          {data.map((entry, i) => (
            <Cell key={i} fill={entry.fill} />
          ))}
        </Pie>
        <Tooltip />
        <Legend wrapperStyle={{ fontSize: '12px' }} />
      </PieChart>
    </ResponsiveContainer>
  );
}
