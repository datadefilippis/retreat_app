/**
 * ProductsPerformanceTable — period-filtered product list with filters
 * and click-to-drill.
 *
 * Renders the top-products payload from /overview as a responsive
 * table. Filters and search are client-side (the backend already
 * limits to top-20 in the period, so we don't paginate further).
 *
 * Drill-down: clicking a row calls ``onProductDrill(productId)`` so the
 * parent page can open the detail slide.
 *
 * Props:
 *   products  — array from overview.top_products
 *   loading   — optional skeleton state
 *   onProductDrill — (productId) => void
 */

import React, { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Card, CardContent } from '../../../components/ui/card';
import { Badge } from '../../../components/ui/badge';
import { Input } from '../../../components/ui/input';
import { Skeleton } from '../../../components/ui/skeleton';
import { TrendingUp, TrendingDown, Search } from 'lucide-react';
import { useCurrency } from '../../../context/AuthContext';
import { formatCurrency } from '../../../lib/utils';


const _abcClass = (cls) => {
  if (cls === 'A') return 'bg-emerald-100 text-emerald-800';
  if (cls === 'B') return 'bg-amber-100 text-amber-800';
  return 'bg-gray-100 text-gray-600';
};

const _trendIcon = (pct) => {
  if (pct > 0) return <TrendingUp className="h-3.5 w-3.5 text-emerald-600" />;
  if (pct < 0) return <TrendingDown className="h-3.5 w-3.5 text-red-500" />;
  return null;
};


export default function ProductsPerformanceTable({ products, loading, onProductDrill }) {
  const { t } = useTranslation('product_catalog');
  const currency = useCurrency();

  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [abcFilter, setAbcFilter] = useState('');

  // Build filter dropdown options from the data itself.
  const categories = useMemo(() => {
    const set = new Set();
    for (const p of (products || [])) if (p.category) set.add(p.category);
    return Array.from(set).sort();
  }, [products]);

  const filtered = useMemo(() => {
    let list = products || [];
    if (search) {
      const q = search.toLowerCase();
      list = list.filter(p =>
        (p.product_name || '').toLowerCase().includes(q) ||
        (p.sku || '').toLowerCase().includes(q)
      );
    }
    if (categoryFilter) {
      list = list.filter(p => p.category === categoryFilter);
    }
    if (abcFilter) {
      list = list.filter(p => p.abc_class === abcFilter);
    }
    return list;
  }, [products, search, categoryFilter, abcFilter]);

  if (loading) {
    return (
      <Card>
        <CardContent className="p-4 space-y-3">
          <Skeleton className="h-8 w-full" />
          {[1,2,3,4,5].map(i => <Skeleton key={i} className="h-10 w-full" />)}
        </CardContent>
      </Card>
    );
  }

  const empty = !products || products.length === 0;

  return (
    <Card>
      <CardContent className="p-0">
        {/* Filters bar */}
        <div className="p-3 border-b flex flex-wrap items-center gap-2">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
            <Input
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder={t('actions.search_placeholder')}
              className="text-xs h-8 pl-7"
            />
          </div>
          <select
            value={categoryFilter}
            onChange={e => setCategoryFilter(e.target.value)}
            className="rounded-md border border-input bg-background px-2 h-8 text-xs"
          >
            <option value="">{t('filters.all_categories')}</option>
            {categories.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
          <select
            value={abcFilter}
            onChange={e => setAbcFilter(e.target.value)}
            className="rounded-md border border-input bg-background px-2 h-8 text-xs"
          >
            <option value="">{t('filters.all_classes')}</option>
            <option value="A">A</option>
            <option value="B">B</option>
            <option value="C">C</option>
          </select>
        </div>

        {/* Table */}
        {empty ? (
          <div className="p-8 text-center text-muted-foreground text-sm">
            {t('table.no_data')}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-muted/30">
                  <th className="text-left px-4 py-2 font-medium text-xs">{t('table.name')}</th>
                  <th className="text-left px-4 py-2 font-medium text-xs hidden md:table-cell">{t('table.category')}</th>
                  <th className="text-right px-4 py-2 font-medium text-xs">{t('table.revenue')}</th>
                  <th className="text-right px-4 py-2 font-medium text-xs hidden sm:table-cell">{t('table.cost')}</th>
                  <th className="text-right px-4 py-2 font-medium text-xs">{t('table.margin')}</th>
                  <th className="text-right px-4 py-2 font-medium text-xs hidden lg:table-cell">{t('table.units')}</th>
                  <th className="text-right px-4 py-2 font-medium text-xs hidden md:table-cell">{t('table.trend')}</th>
                  <th className="text-center px-4 py-2 font-medium text-xs">{t('table.abc')}</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((p) => (
                  <tr
                    key={p.product_id}
                    className="border-b last:border-0 hover:bg-muted/20 cursor-pointer transition-colors"
                    onClick={() => onProductDrill?.(p.product_id)}
                  >
                    <td className="px-4 py-2.5">
                      <div className="font-medium text-sm">{p.product_name}</div>
                      {p.sku && <div className="text-[11px] text-muted-foreground">{p.sku}</div>}
                    </td>
                    <td className="px-4 py-2.5 text-muted-foreground text-xs hidden md:table-cell">
                      {p.category || '—'}
                    </td>
                    <td className="px-4 py-2.5 text-right text-sm font-medium tabular-nums">
                      {formatCurrency(p.total_revenue, currency)}
                    </td>
                    <td className="px-4 py-2.5 text-right text-xs text-muted-foreground hidden sm:table-cell tabular-nums">
                      {p.total_cost > 0 ? formatCurrency(p.total_cost, currency) : '—'}
                    </td>
                    <td className={`px-4 py-2.5 text-right text-sm font-medium tabular-nums ${
                      p.margin_pct == null ? 'text-muted-foreground'
                      : p.margin_pct < 5 ? 'text-red-600'
                      : p.margin_pct > 30 ? 'text-emerald-600' : ''
                    }`}>
                      {p.margin_pct != null ? `${p.margin_pct.toFixed(1)}%` : 'N/D'}
                    </td>
                    <td className="px-4 py-2.5 text-right text-xs text-muted-foreground hidden lg:table-cell tabular-nums">
                      {p.total_units_sold}
                    </td>
                    <td className="px-4 py-2.5 text-right hidden md:table-cell">
                      <div className="flex items-center justify-end gap-1">
                        {_trendIcon(p.trend_30d_pct)}
                        <span className={`text-xs tabular-nums ${
                          p.trend_30d_pct > 0 ? 'text-emerald-600'
                          : p.trend_30d_pct < 0 ? 'text-red-500'
                          : 'text-muted-foreground'
                        }`}>
                          {p.trend_30d_pct >= 0 ? '+' : ''}{(p.trend_30d_pct || 0).toFixed(1)}%
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-2.5 text-center">
                      <Badge className={`${_abcClass(p.abc_class)} text-xs`}>
                        {p.abc_class}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
