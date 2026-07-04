/**
 * ServicesGrid — admin grid of service products (Onda 13).
 *
 * Mirrors EventsGrid design language: rich cards with image + quick
 * status pill, filter row (search + status), dashboard CTA. Mounted
 * inside ProductsPage when typeFilter === 'service'.
 *
 * Contract:
 *   <ServicesGrid
 *     embedded={boolean}      // true when mounted inside ProductsPage
 *     onCreateClick={fn?}     // hide CTA when undefined
 *   />
 *
 * Data source: productsAPI.list(false) filtered client-side to
 * item_type === 'service'. A future endpoint `/api/products/services/admin`
 * could pre-filter server-side but for now the dataset is small.
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { productsAPI } from '../../../api';
import { toast } from 'sonner';
import { useCurrency } from '../../../context/AuthContext';
import { formatCurrency as fmtCurrency } from '../../../lib/utils';


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


function ServiceCard({ service, onStatusChange }) {
  const orgCurrency = useCurrency();
  const { t } = useTranslation('products');
  const hero = (service.metadata?.cover_image_url) || service.image_url;
  const price = service.unit_price;
  const optionsCount = service.metadata?.service_options_count; // may be undefined
  const duration = service.metadata?.duration_minutes;

  return (
    <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden flex flex-col">
      <Link
        to={`/services/${service.id}`}
        className="relative aspect-[16/9] bg-gradient-to-br from-blue-700 to-blue-500 overflow-hidden block"
      >
        {hero && (
          <img
            src={hero}
            alt=""
            className="w-full h-full object-cover hover:scale-[1.02] transition-transform duration-200"
          />
        )}
        <div className="absolute top-2 left-2 flex gap-1">
          <span className="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold bg-white/90 text-gray-900">
            {t('grids.service.typeBadge')}
          </span>
        </div>
        {!hero && (
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-5xl opacity-60">🛠</span>
          </div>
        )}
      </Link>

      <div className="p-4 flex-1 flex flex-col gap-2">
        <div>
          <Link to={`/services/${service.id}`} className="block hover:underline">
            <h3 className="font-bold text-gray-900 line-clamp-2">
              {service.name || t('grids.service.fallbackName')}
            </h3>
          </Link>
          <p className="text-[11px] uppercase tracking-wide text-gray-500 font-semibold mt-1">
            {service.transaction_mode === 'direct' ? t('grids.service.modeDirect') : t('grids.service.modeRequest')}
            {duration ? ` · ${t('grids.service.durationSuffix', { minutes: duration })}` : ''}
          </p>
          {service.description && (
            <p className="text-xs text-gray-600 mt-1 line-clamp-2">{service.description}</p>
          )}
        </div>

        {price != null && (
          <p className="text-sm text-gray-700">{t('grids.service.fromPrice')} <strong>{fmtCurrency(Number(price), service.currency || orgCurrency)}</strong></p>
        )}

        <div className="mt-auto pt-2 space-y-2">
          <div className="flex items-center justify-between gap-2">
            <span className="text-[10px] uppercase tracking-wide text-gray-500 font-semibold">{t('grids.service.stateLabel')}</span>
            <StatusChip
              isPublished={!!service.is_published}
              productId={service.id}
              onStatusChange={onStatusChange}
            />
          </div>
          <div className="flex gap-2">
            <Link
              to={`/services/${service.id}`}
              className="flex-1 text-center text-xs font-semibold rounded-md bg-gray-900 text-white px-2 py-1.5 hover:bg-gray-800"
            >{t('grids.service.dashboardCta')}</Link>
            {service.slug && (
              <Link
                to={`/p/${encodeURIComponent(service._orgSlug || '')}/${service.slug}`}
                target="_blank"
                rel="noopener noreferrer"
                title={t('grids.common.previewLanding')}
                className="text-center text-xs font-semibold rounded-md border border-gray-300 text-gray-900 px-2 py-1.5 hover:border-gray-900"
              >🔗</Link>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}


export default function ServicesGrid({ embedded = false, onCreateClick = null }) {
  const { t } = useTranslation('products');
  const [q, setQ] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [services, setServices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const handleStatusChange = useCallback((productId, isPublished) => {
    setServices(prev => prev.map(s => s.id === productId ? { ...s, is_published: isPublished } : s));
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await productsAPI.list(false);
      const all = res.data || [];
      const services = all.filter(p => p.item_type === 'service' && p.is_active !== false);
      setServices(services);
      setError(null);
    } catch (err) {
      setError(err?.response?.data?.detail || t('grids.service.errorLoad'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const filtered = useMemo(() => {
    let list = services;
    if (statusFilter === 'published') list = list.filter(s => s.is_published);
    else if (statusFilter === 'draft') list = list.filter(s => !s.is_published);
    if (q.trim()) {
      const needle = q.trim().toLowerCase();
      list = list.filter(s =>
        s.name?.toLowerCase().includes(needle) ||
        s.description?.toLowerCase().includes(needle)
      );
    }
    return list;
  }, [services, statusFilter, q]);

  const wrapperClass = embedded ? '' : 'min-h-screen bg-gray-50';

  return (
    <div className={wrapperClass}>
      {!embedded && (
        <div className="bg-white border-b sticky top-0 z-10">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 py-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div className="min-w-0">
              <h1 className="text-xl sm:text-2xl font-bold text-gray-900">{t('grids.service.title')}</h1>
              <p className="text-xs text-gray-500">
                {t('grids.service.subtitle')}
              </p>
            </div>
            {onCreateClick && (
              <button
                type="button"
                onClick={onCreateClick}
                className="rounded-md bg-gray-900 text-white px-4 py-2 text-sm font-semibold hover:bg-gray-800 whitespace-nowrap"
              >
                {t('grids.service.newCta')}
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
            placeholder={t('grids.service.searchPlaceholder')}
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
            <div className="text-4xl mb-2">🛠</div>
            <h2 className="text-lg font-semibold text-gray-900">{t('grids.service.emptyTitle')}</h2>
            <p className="text-sm text-gray-600 mt-1 mb-4">
              {q || statusFilter
                ? t('grids.common.tryRemoveFilters')
                : t('grids.service.emptyDescFirst')}
            </p>
            {!q && !statusFilter && onCreateClick && (
              <button
                type="button"
                onClick={onCreateClick}
                className="rounded-md bg-gray-900 text-white px-4 py-2 text-sm font-semibold hover:bg-gray-800"
              >
                {t('grids.service.firstCreateCta')}
              </button>
            )}
          </div>
        )}

        {!loading && filtered.length > 0 && (
          <>
            <p className="text-xs text-gray-500 mb-3">
              {t('grids.service.count', { count: filtered.length })}
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {filtered.map(s => (
                <ServiceCard key={s.id} service={s} onStatusChange={handleStatusChange} />
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
