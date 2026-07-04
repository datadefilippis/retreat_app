/**
 * PhysicalsGrid — admin grid of physical products.
 *
 * Release 2 (Physical pattern parity, A4). Mirrors ReservationsGrid /
 * ServicesGrid / EventsGrid so the catalog looks uniform regardless of type.
 *
 * Mounts inside ProductsPage when typeFilter === 'physical'. Data source:
 * productsAPI.list(false) filtered client-side to item_type === 'physical'.
 *
 * Contract:
 *   <PhysicalsGrid
 *     embedded={boolean}      // true when mounted inside ProductsPage
 *     onCreateClick={fn?}     // hide CTA when undefined
 *   />
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { productsAPI } from '../../../api';
import { toast } from 'sonner';
import ProductCardBase from '../../products/components/ProductCardBase';
import { useCurrency } from '../../../context/AuthContext';


// Status configuration: only presentational classes here. Labels are
// resolved at render time via t('grids.common.statusOnline/Offline')
// so the chip text changes with the active locale.
const STATUS_CFG = {
  published: { cls: 'bg-green-100 text-green-900' },
  draft:     { cls: 'bg-gray-100 text-gray-700' },
};


function StatusChip({ isPublished, productId, onStatusChange }) {
  const { t } = useTranslation('products');
  const cfg = isPublished ? STATUS_CFG.published : STATUS_CFG.draft;
  const [saving, setSaving] = useState(false);

  const toggle = async (e) => {
    e.stopPropagation();
    e.preventDefault();
    const next = !isPublished;
    setSaving(true);
    try {
      await productsAPI.update(productId, { is_published: next });
      onStatusChange(productId, next);
    } catch {
      toast.error(t('grids.common.statusChangeError'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <button
      type="button"
      onClick={toggle}
      disabled={saving}
      title={isPublished ? t('grids.common.toggleToOffline') : t('grids.common.toggleToOnline')}
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold ${cfg.cls} hover:opacity-90 ${saving ? 'opacity-60' : ''}`}
    >
      {isPublished ? t('grids.common.statusOnline') : t('grids.common.statusOffline')}
    </button>
  );
}


/**
 * Compact stock indicator for the card overline. Untracked products render
 * nothing (`null`), so the overline falls back to the SKU / category.
 * Returns the i18n key + interpolation count so the caller can resolve
 * with its own `t` instance (works in any locale).
 */
function stockOverline(product, t) {
  const q = product.stock_quantity;
  if (q == null) return null;
  const n = Number(q);
  if (n <= 0) return t('grids.physical.stockOverline.depleted');
  if (n <= 5) return t('grids.physical.stockOverline.lastN', { count: n });
  return t('grids.physical.stockOverline.inStock', { count: n });
}


function PhysicalCard({ product, orgSlug, onStatusChange }) {
  const orgCurrency = useCurrency();
  const { t } = useTranslation('products');
  const meta = product.metadata || {};
  const hero = meta.cover_image_url || product.image_url;

  // Overline: stock status (when tracked) + SKU/category fallback. Kept under
  // ~40 chars so it fits the card ProductCardBase renders.
  const parts = [];
  const stock = stockOverline(product, t);
  if (stock) parts.push(stock);
  if (product.sku) parts.push(`SKU ${product.sku}`);
  if (!product.sku && product.category) parts.push(product.category);

  const secondaryCta = product.slug && orgSlug
    ? {
        href: `/ph/${encodeURIComponent(orgSlug)}/${product.slug}`,
        title: t('grids.common.previewLanding'),
        label: '🔗',
      }
    : null;

  return (
    <ProductCardBase
      hero={{
        src: hero,
        gradientFrom: 'from-gray-700',
        gradientTo: 'to-gray-500',
        fallbackEmoji: '📦',
        typeBadge: t('grids.physical.typeBadge'),
      }}
      href={`/physicals/${product.id}`}
      title={product.name || t('grids.common.noName')}
      overline={parts.join(' · ')}
      description={product.description}
      price={product.unit_price}
      currency={product.currency || orgCurrency}
      statusChip={
        <StatusChip
          isPublished={!!product.is_published}
          productId={product.id}
          onStatusChange={onStatusChange}
        />
      }
      secondaryCta={secondaryCta}
    />
  );
}


export default function PhysicalsGrid({ embedded = false, onCreateClick = null }) {
  const { t } = useTranslation('products');
  const [q, setQ] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [stockFilter, setStockFilter] = useState('');   // '' | 'tracked' | 'untracked' | 'out_of_stock' | 'low_stock'
  const [products, setProducts] = useState([]);
  const [orgSlug, setOrgSlug] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const handleStatusChange = useCallback((productId, isPublished) => {
    setProducts(prev => prev.map(p => p.id === productId ? { ...p, is_published: isPublished } : p));
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { storesAPI } = await import('../../../api/stores');
      const [prodRes, storesRes] = await Promise.all([
        productsAPI.list(false),
        storesAPI.list().catch(() => ({ data: { stores: [] } })),
      ]);
      const all = prodRes.data || [];
      const physicals = all.filter(
        p => p.item_type === 'physical' && p.is_active !== false,
      );
      setProducts(physicals);
      const publishedStore = (storesRes.data?.stores || []).find(s => s.is_published);
      setOrgSlug(publishedStore?.slug || null);
      setError(null);
    } catch (err) {
      setError(err?.response?.data?.detail || t('grids.physical.errorLoad'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const filtered = useMemo(() => {
    let list = products;
    if (statusFilter === 'published') list = list.filter(p => p.is_published);
    else if (statusFilter === 'draft') list = list.filter(p => !p.is_published);

    if (stockFilter === 'tracked') {
      list = list.filter(p => p.stock_quantity != null);
    } else if (stockFilter === 'untracked') {
      list = list.filter(p => p.stock_quantity == null);
    } else if (stockFilter === 'out_of_stock') {
      list = list.filter(p => p.stock_quantity != null && Number(p.stock_quantity) <= 0);
    } else if (stockFilter === 'low_stock') {
      list = list.filter(p => {
        const q = Number(p.stock_quantity);
        return p.stock_quantity != null && q > 0 && q <= 5;
      });
    }

    if (q.trim()) {
      const needle = q.trim().toLowerCase();
      list = list.filter(p =>
        p.name?.toLowerCase().includes(needle) ||
        p.description?.toLowerCase().includes(needle) ||
        p.sku?.toLowerCase().includes(needle) ||
        p.category?.toLowerCase().includes(needle)
      );
    }
    return list;
  }, [products, statusFilter, stockFilter, q]);

  const wrapperClass = embedded ? '' : 'min-h-screen bg-gray-50';

  return (
    <div className={wrapperClass}>
      {!embedded && (
        <div className="bg-white border-b sticky top-0 z-10">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 py-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div className="min-w-0">
              <h1 className="text-xl sm:text-2xl font-bold text-gray-900">{t('grids.physical.title')}</h1>
              <p className="text-xs text-gray-500">
                {t('grids.physical.subtitle')}
              </p>
            </div>
            {onCreateClick && (
              <button
                type="button"
                onClick={onCreateClick}
                className="rounded-md bg-gray-900 text-white px-4 py-2 text-sm font-semibold hover:bg-gray-800 whitespace-nowrap"
              >
                {t('grids.common.newCta')}
              </button>
            )}
          </div>
        </div>
      )}

      {/* Filter row */}
      <div className={`${embedded ? '' : 'bg-white border-b sticky'} top-0 z-[5]`}>
        <div className={`${embedded ? '' : 'max-w-6xl mx-auto'} px-0 sm:px-0 py-2 flex flex-wrap items-center gap-2`}>
          {[
            { k: '',          labelKey: 'grids.common.statusFilterAll' },
            { k: 'published', labelKey: 'grids.common.statusOnline' },
            { k: 'draft',     labelKey: 'grids.common.statusOffline' },
          ].map(tab => (
            <button
              key={tab.k || 'all'}
              type="button"
              onClick={() => setStatusFilter(tab.k)}
              className={`rounded-full px-3 py-1 text-xs font-semibold ${
                statusFilter === tab.k
                  ? 'bg-gray-900 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >{t(tab.labelKey)}</button>
          ))}
          <div className="w-px h-5 bg-gray-200 mx-1" aria-hidden />
          {[
            { k: '',             labelKey: 'grids.physical.stockFilter.any' },
            { k: 'tracked',      labelKey: 'grids.physical.stockFilter.tracked' },
            { k: 'untracked',    labelKey: 'grids.physical.stockFilter.untracked' },
            { k: 'low_stock',    labelKey: 'grids.physical.stockFilter.lowStock' },
            { k: 'out_of_stock', labelKey: 'grids.physical.stockFilter.outOfStock' },
          ].map(tab => (
            <button
              key={tab.k || 'stock-all'}
              type="button"
              onClick={() => setStockFilter(tab.k)}
              className={`rounded-full px-3 py-1 text-xs font-semibold ${
                stockFilter === tab.k
                  ? 'bg-gray-900 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >{t(tab.labelKey)}</button>
          ))}
          <div className="flex-1" />
          <input
            type="search"
            value={q}
            onChange={e => setQ(e.target.value)}
            placeholder={t('grids.physical.searchPlaceholder')}
            className="rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-gray-900 focus:outline-none min-w-[180px]"
          />
        </div>
      </div>

      <div className={`${embedded ? '' : 'max-w-6xl mx-auto px-4 sm:px-6'} py-4 sm:py-6`}>
        {loading && (
          <div className="text-center text-sm text-gray-500 py-12">{t('grids.common.loading')}</div>
        )}

        {error && !loading && (
          <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-800">
            {error}
          </div>
        )}

        {!loading && !error && filtered.length === 0 && (
          <div className="rounded-xl border-2 border-dashed border-gray-300 bg-white p-10 text-center">
            <div className="text-4xl mb-2">📦</div>
            <h2 className="text-lg font-semibold text-gray-900">{t('grids.physical.emptyTitle')}</h2>
            <p className="text-sm text-gray-600 mt-1 mb-4">
              {q || statusFilter || stockFilter
                ? t('grids.common.tryRemoveFilters')
                : t('grids.physical.emptyDescFirst')}
            </p>
            {!q && !statusFilter && !stockFilter && onCreateClick && (
              <button
                type="button"
                onClick={onCreateClick}
                className="rounded-md bg-gray-900 text-white px-4 py-2 text-sm font-semibold hover:bg-gray-800"
              >
                {t('grids.common.firstCreateCta')}
              </button>
            )}
          </div>
        )}

        {!loading && filtered.length > 0 && (
          <>
            <p className="text-xs text-gray-500 mb-3">
              {t('grids.physical.count', { count: filtered.length })}
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {filtered.map(p => (
                <PhysicalCard
                  key={p.id}
                  product={p}
                  orgSlug={orgSlug}
                  onStatusChange={handleStatusChange}
                />
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
