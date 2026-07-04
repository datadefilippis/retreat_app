import React from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../../components/ui/card';
import { Skeleton } from '../../../components/ui/skeleton';
import { formatCurrency, chartTickFormatter } from '../../../lib/utils';
import {
  PieChart, Pie, Cell, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts';
import { PinToDashboardButton } from '../../dashboard/PinToDashboardButton';
import { useTranslation } from 'react-i18next';

const CATEGORY_COLORS = [
  '#0F172A', '#3B82F6', '#10B981', '#F59E0B', '#EF4444',
  '#8B5CF6', '#EC4899', '#06B6D4', '#84CC16', '#F97316',
];

const EmptyState = ({ height = 'h-56 md:h-72' }) => (
  <div className={`${height} flex items-center justify-center text-muted-foreground`}>
    Nessun dato per categoria
  </div>
);


/**
 * CategoryPieCharts — two pie charts (sales + expenses) side by side.
 */
export const CategoryPieCharts = ({ salesCategories, expensesCategories, loading, widgetKey, isPinned, onTogglePin, currency = 'EUR' }) => {
  const { t } = useTranslation('cashflow_monitor');
  return (
  <div className="relative">
    {widgetKey && onTogglePin && (
      <div className="absolute -top-1 right-0 z-10">
        <PinToDashboardButton widgetKey={widgetKey} isPinned={isPinned} onToggle={onTogglePin} />
      </div>
    )}
  <div className="grid gap-6 lg:grid-cols-2">
    <Card className="border border-border">
      <CardHeader className="pb-2">
        <CardTitle className="font-heading text-lg">{t('categories.sales_pie_title')}</CardTitle>
        <CardDescription>{t('categories.sales_pie_desc')}</CardDescription>
      </CardHeader>
      <CardContent>
        {loading ? <Skeleton className="h-56 md:h-72 w-full" /> : salesCategories?.categories?.length > 0 ? (
          <div className="h-56 md:h-72" data-testid="sales-category-chart">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={salesCategories.categories}
                  dataKey="total"
                  nameKey="category"
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  label={({ category, percentage }) => `${category} (${percentage}%)`}
                  labelLine
                >
                  {salesCategories.categories.map((_, i) => (
                    <Cell key={i} fill={CATEGORY_COLORS[i % CATEGORY_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(v) => formatCurrency(v, currency)} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        ) : <EmptyState />}
      </CardContent>
    </Card>

    <Card className="border border-border">
      <CardHeader className="pb-2">
        <CardTitle className="font-heading text-lg">{t('categories.expenses_pie_title')}</CardTitle>
        <CardDescription>{t('categories.expenses_pie_desc')}</CardDescription>
      </CardHeader>
      <CardContent>
        {loading ? <Skeleton className="h-56 md:h-72 w-full" /> : expensesCategories?.categories?.length > 0 ? (
          <div className="h-56 md:h-72" data-testid="expenses-category-chart">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={expensesCategories.categories}
                  dataKey="total"
                  nameKey="category"
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  label={({ category, percentage }) => `${category} (${percentage}%)`}
                  labelLine
                >
                  {expensesCategories.categories.map((_, i) => (
                    <Cell key={i} fill={CATEGORY_COLORS[i % CATEGORY_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(v) => formatCurrency(v, currency)} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        ) : <EmptyState />}
      </CardContent>
    </Card>
  </div>
  </div>
  );
};


/**
 * CategoryBarCharts — horizontal bar charts ranking categories by total.
 */
export const CategoryBarCharts = ({ salesCategories, expensesCategories, loading, widgetKey, isPinned, onTogglePin, currency = 'EUR' }) => {
  const { t } = useTranslation('cashflow_monitor');
  return (
  <div className="relative">
    {widgetKey && onTogglePin && (
      <div className="absolute -top-1 right-0 z-10">
        <PinToDashboardButton widgetKey={widgetKey} isPinned={isPinned} onToggle={onTogglePin} />
      </div>
    )}
  <div className="grid gap-6 lg:grid-cols-2">
    <Card className="border border-border">
      <CardHeader className="pb-2">
        <CardTitle className="font-heading text-lg">{t('categories.sales_bar_title')}</CardTitle>
        <CardDescription>{t('categories.sales_bar_desc')}</CardDescription>
      </CardHeader>
      <CardContent>
        {loading ? <Skeleton className="h-48 md:h-64 w-full" /> : salesCategories?.categories?.length > 0 ? (
          <div className="h-48 md:h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={salesCategories.categories} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                <XAxis type="number" tickFormatter={(v) => chartTickFormatter(v, currency)} stroke="#94A3B8" fontSize={12} />
                <YAxis type="category" dataKey="category" stroke="#94A3B8" fontSize={12} width={100} />
                <Tooltip formatter={(v) => formatCurrency(v, currency)} />
                <Bar dataKey="total" fill="#0F172A" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : <EmptyState height="h-48 md:h-64" />}
      </CardContent>
    </Card>

    <Card className="border border-border">
      <CardHeader className="pb-2">
        <CardTitle className="font-heading text-lg">{t('categories.expenses_bar_title')}</CardTitle>
        <CardDescription>{t('categories.expenses_bar_desc')}</CardDescription>
      </CardHeader>
      <CardContent>
        {loading ? <Skeleton className="h-48 md:h-64 w-full" /> : expensesCategories?.categories?.length > 0 ? (
          <div className="h-48 md:h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={expensesCategories.categories} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                <XAxis type="number" tickFormatter={(v) => chartTickFormatter(v, currency)} stroke="#94A3B8" fontSize={12} />
                <YAxis type="category" dataKey="category" stroke="#94A3B8" fontSize={12} width={100} />
                <Tooltip formatter={(v) => formatCurrency(v, currency)} />
                <Bar dataKey="total" fill="#EF4444" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : <EmptyState height="h-48 md:h-64" />}
      </CardContent>
    </Card>
  </div>
  </div>
  );
};
