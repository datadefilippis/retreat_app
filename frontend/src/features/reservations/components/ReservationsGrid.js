/**
 * ReservationsGrid — admin grid of rental/reservation products.
 *
 * Mounts inside ProductsPage when typeFilter === 'rental'. Mirrors
 * ServicesGrid / EventsGrid design language via ProductCardBase, so the
 * catalog looks uniform regardless of the product type.
 *
 * Covers both flavors of the unified "Prenotazione" umbrella (Onda 16):
 *   - range: multi-day rentals (B&B, car rental, equipment)
 *   - slot:  single-shot time windows (meeting rooms, courts)
 *
 * Data source: productsAPI.list(false) filtered client-side to
 * item_type === 'rental'. Small dataset — no server-side pre-filter needed.
 *
 * Contract:
 *   <ReservationsGrid
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


// Presentational classes only — labels resolved at render time via t().
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


function ReservationCard({ product, orgSlug, onStatusChange }) {
  const { t } = useTranslation('products');
  const orgCurrency = useCurrency();
  const meta = product.metadata || {};
  const hero = meta.cover_image_url || product.image_url;
  const flavor = meta.reservation_flavor
    || (meta.rental_unit === 'ora' ? 'slot' : 'range');

  // Overline copy differs by flavor so the admin can scan at a glance.
  const overlineParts = [];
  if (flavor === 'range') {
    overlineParts.push(t('grids.reservation.flavorRange'));
    if (meta.rental_unit) overlineParts.push(t('grids.reservation.perRentalUnit', { unit: meta.rental_unit }));
  } else {
    overlineParts.push(t('grids.reservation.flavorSlot'));
    if (meta.slot_duration_minutes) overlineParts.push(t('grids.reservation.slotMinutes', { minutes: meta.slot_duration_minutes }));
    else if (meta.duration_label) overlineParts.push(meta.duration_label);
  }

  const secondaryCta = product.slug && orgSlug
    ? {
        href: `/r/${encodeURIComponent(orgSlug)}/${product.slug}`,
        title: t('grids.common.previewLanding'),
        label: '🔗',
      }
    : null;

  return (
    <ProductCardBase
      hero={{
        src: hero,
        gradientFrom: flavor === 'range' ? 'from-orange-700' : 'from-purple-700',
        gradientTo: flavor === 'range' ? 'to-orange-500' : 'to-purple-500',
        fallbackEmoji: flavor === 'range' ? '🔑' : '📅',
        typeBadge: flavor === 'range' ? t('grids.reservation.typeBadgeRange') : t('grids.reservation.typeBadgeSlot'),
      }}
      href={`/reservations/${product.id}`}
      title={product.name || t('grids.common.noName')}
      overline={overlineParts.join(' · ')}
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


export default function ReservationsGrid({ embedded = false, onCreateClick = null }) {
  const { t } = useTranslation('products');
  const [q, setQ] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
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
      // Fetch products + stores in parallel. Stores give us the org_slug used
      // to build the public landing URL for the preview link on the card.
      const { storesAPI } = await import('../../../api/stores');
      const [prodRes, storesRes] = await Promise.all([
        productsAPI.list(false),
        storesAPI.list().catch(() => ({ data: { stores: [] } })),
      ]);
      const all = prodRes.data || [];
      // Include both item_type=rental AND legacy item_type=booking so admins
      // can see un-migrated products alongside new ones (Onda 16 Fase 6).
      const rentals = all.filter(
        p => (p.item_type === 'rental' || p.item_type === 'booking') && p.is_active !== false,
      );
      setProducts(rentals);
      const publishedStore = (storesRes.data?.stores || []).find(s => s.is_published);
      setOrgSlug(publishedStore?.slug || null);
      setError(null);
    } catch (err) {
      setError(err?.response?.data?.detail || t('grids.reservation.errorLoad'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const filtered = useMemo(() => {
    let list = products;
    if (statusFilter === 'published') list = list.filter(p => p.is_published);
    else if (statusFilter === 'draft') list = list.filter(p => !p.is_published);
    if (q.trim()) {
      const needle = q.trim().toLowerCase();
      list = list.filter(p =>
        p.name?.toLowerCase().includes(needle) ||
        p.description?.toLowerCase().includes(needle)
      );
    }
    return list;
  }, [products, statusFilter, q]);

  const wrapperClass = embedded ? '' : 'min-h-screen bg-gray-50';

  return (
    <div className={wrapperClass}>
      {!embedded && (
        <div className="bg-white border-b sticky top-0 z-10">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 py-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div className="min-w-0">
              <h1 className="text-xl sm:text-2xl font-bold text-gray-900">{t('grids.reservation.title')}</h1>
              <p className="text-xs text-gray-500">
                {t('grids.reservation.subtitle')}
              </p>
            </div>
            {onCreateClick && (
              <button
                type="button"
                onClick={onCreateClick}
                className="rounded-md bg-gray-900 text-white px-4 py-2 text-sm font-semibold hover:bg-gray-800 whitespace-nowrap"
              >
                {t('grids.reservation.newCta')}
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
          <div className="flex-1" />
          <input
            type="search"
            value={q}
            onChange={e => setQ(e.target.value)}
            placeholder={t('grids.reservation.searchPlaceholder')}
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
            <div className="text-4xl mb-2">🔑</div>
            <h2 className="text-lg font-semibold text-gray-900">{t('grids.reservation.emptyTitle')}</h2>
            <p className="text-sm text-gray-600 mt-1 mb-4">
              {q || statusFilter
                ? t('grids.common.tryRemoveFilters')
                : t('grids.reservation.emptyDescFirst')}
            </p>
            {!q && !statusFilter && onCreateClick && (
              <button
                type="button"
                onClick={onCreateClick}
                className="rounded-md bg-gray-900 text-white px-4 py-2 text-sm font-semibold hover:bg-gray-800"
              >
                {t('grids.reservation.firstCreateCta')}
              </button>
            )}
          </div>
        )}

        {!loading && filtered.length > 0 && (
          <>
            <p className="text-xs text-gray-500 mb-3">
              {t('grids.reservation.count', { count: filtered.length })}
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {filtered.map(p => (
                <ReservationCard
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
