/**
 * EventsGrid — shared component that renders the admin events list.
 *
 * Extracted from EventsListPage so the same UI can mount inside
 * ProductsPage when the user filters by type=event_ticket (Onda 7
 * "Products hub unico"). EventsListPage is now a thin wrapper around
 * this component for backward-compat with the /events route.
 *
 * Contract:
 *   <EventsGrid
 *     embedded={boolean}       // true when mounted inside another
 *                              // page — hides the page header, only
 *                              // the filter row + grid render
 *     onCreateClick={fn?}      // wire the "+ Nuovo evento" behaviour;
 *                              // when omitted the CTA is hidden
 *   />
 *
 * Everything else is fully self-contained: data fetching, filter
 * state, loading / empty / error states, card layout, quick-action
 * links. Navigation destinations (dashboard E6, check-in E5, landing
 * E3) are unchanged.
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { eventOccurrencesAPI } from '../../../api/eventOccurrences';


// Presentational classes only — labels resolved at render time via t().
const STATUS_CFG = {
  draft:     { cls: 'bg-gray-100 text-gray-700' },
  published: { cls: 'bg-green-100 text-green-900' },
  closed:    { cls: 'bg-amber-100 text-amber-900' },
  cancelled: { cls: 'bg-red-100 text-red-900' },
};


function StatusChip({ status, eventId, onStatusChange }) {
  const { t } = useTranslation('products');
  const cfg = STATUS_CFG[status] || { cls: 'bg-gray-100 text-gray-700' };
  const [saving, setSaving] = useState(false);

  const handleChange = async (e) => {
    e.stopPropagation();
    const next = e.target.value;
    if (next === status) return;
    setSaving(true);
    try {
      await eventOccurrencesAPI.update(eventId, { status: next });
      onStatusChange(eventId, next);
    } catch { /* ignore */ }
    finally { setSaving(false); }
  };

  return (
    <div className="relative" onClick={e => e.stopPropagation()}>
      <select
        value={status}
        onChange={handleChange}
        disabled={saving}
        className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold border-0 cursor-pointer appearance-none focus:outline-none pr-4 ${cfg.cls} ${saving ? 'opacity-60' : ''}`}
      >
        <option value="draft">{t('grids.event.statusBadge.draft')}</option>
        <option value="published">{t('grids.event.statusBadge.published')}</option>
        <option value="closed">{t('grids.event.statusBadge.closed')}</option>
        <option value="cancelled">{t('grids.event.statusBadge.cancelled')}</option>
      </select>
      <span className="pointer-events-none absolute right-1 top-1/2 -translate-y-1/2 text-[8px] opacity-60">▾</span>
    </div>
  );
}


function formatDateLine(iso, locale = 'it-IT') {
  if (!iso) return { date: '', time: '' };
  try {
    const d = new Date(iso);
    return {
      date: d.toLocaleDateString(locale, { weekday: 'short', day: 'numeric', month: 'short' }),
      time: d.toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit' }),
      year: d.getFullYear(),
    };
  } catch { return { date: iso, time: '' }; }
}


function EventCard({ event, onStatusChange }) {
  const { t, i18n } = useTranslation('products');
  const hero = event.cover_image_url || event.product_image_url;
  const dt = useMemo(() => formatDateLine(event.start_at, i18n.language), [event.start_at, i18n.language]);
  const cap = event.capacity;
  const reserved = event.reserved_seats || 0;
  const capacityPct = cap ? Math.min(100, Math.round((reserved / cap) * 100)) : null;
  const venueLine = [event.venue_name, event.city].filter(Boolean).join(' · ') || event.location || '—';

  return (
    <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden flex flex-col">
      <Link to={`/events/${event.id}`} className="relative aspect-[16/9] bg-gradient-to-br from-gray-800 to-gray-600 overflow-hidden block">
        {hero && (
          <img src={hero} alt="" className="w-full h-full object-cover hover:scale-[1.02] transition-transform duration-200" />
        )}
        {event.is_archived && (
          <div className="absolute top-2 left-2 flex gap-1">
            <span className="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold bg-gray-200 text-gray-700">
              {t('grids.event.archivedBadge')}
            </span>
          </div>
        )}
      </Link>

      <div className="p-4 flex-1 flex flex-col gap-2">
        <div>
          <p className="text-[11px] uppercase tracking-wide text-gray-500 font-semibold">
            {dt.date}{dt.time ? ` · ${dt.time}` : ''} · {dt.year}
          </p>
          <Link to={`/events/${event.id}`} className="block mt-0.5 hover:underline">
            <h3 className="font-bold text-gray-900 line-clamp-2">
              {event.product_name || t('grids.event.fallbackName')}
            </h3>
          </Link>
          <p className="text-xs text-gray-600 mt-1 line-clamp-1">📍 {venueLine}</p>
        </div>

        {cap ? (
          <div className="space-y-1">
            <div className="flex justify-between text-[11px] text-gray-600">
              <span>{t('grids.event.soldCount', { reserved, cap })}</span>
              <span className="tabular-nums">{capacityPct}%</span>
            </div>
            <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
              <div
                className={`h-full ${capacityPct >= 90 ? 'bg-red-500' : capacityPct >= 70 ? 'bg-amber-500' : 'bg-green-500'}`}
                style={{ width: `${capacityPct}%` }}
              />
            </div>
          </div>
        ) : (
          <p className="text-[11px] text-gray-500">{t('grids.event.unlimitedCapacity')}</p>
        )}

        {event.tier_count > 0 && (
          <p className="text-[11px] text-gray-500">{t('grids.event.tierCount', { count: event.tier_count })}</p>
        )}

        <div className="mt-auto pt-2 space-y-2">
          <div className="flex items-center justify-between gap-2">
            <span className="text-[10px] uppercase tracking-wide text-gray-500 font-semibold">{t('grids.event.stateLabel')}</span>
            <StatusChip status={event.status} eventId={event.id} onStatusChange={onStatusChange} />
          </div>
          <div className="flex gap-2">
            <Link
              to={`/events/${event.id}`}
              className="flex-1 text-center text-xs font-semibold rounded-md bg-gray-900 text-white px-2 py-1.5 hover:bg-gray-800"
            >{t('grids.event.dashboardCta')}</Link>
            <Link
              to={`/events/${event.id}/check-in`}
              className="text-center text-xs font-semibold rounded-md border border-gray-300 text-gray-900 px-2 py-1.5 hover:border-gray-900"
            >{t('grids.event.checkInCta')}</Link>
            {/* F5: direct link to product edit section in dashboard */}
            <Link
              to={`/events/${event.id}?edit=product`}
              title={t('grids.event.editProductTitle')}
              className="flex items-center justify-center text-xs font-semibold rounded-md border border-gray-300 text-gray-900 px-2 py-1.5 hover:border-gray-900"
            >✏️</Link>
          </div>
        </div>
      </div>
    </div>
  );
}


export default function EventsGrid({ embedded = false, onCreateClick = null }) {
  const { t } = useTranslation('products');
  const [when, setWhen] = useState('upcoming');
  const [statusFilter, setStatusFilter] = useState('');
  const [q, setQ] = useState('');
  const [archivedFilter, setArchivedFilter] = useState('hide');
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const handleStatusChange = useCallback((eventId, newStatus) => {
    setEvents(prev => prev.map(ev => ev.id === eventId ? { ...ev, status: newStatus } : ev));
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = { when, limit: 100, archived: archivedFilter };
      if (statusFilter) params.status = statusFilter;
      if (q.trim()) params.q = q.trim();
      const res = await eventOccurrencesAPI.listAdmin(params);
      setEvents(res.data?.events || []);
      setError(null);
    } catch (err) {
      setError(err?.response?.data?.detail || t('grids.event.errorLoad'));
    } finally {
      setLoading(false);
    }
  }, [when, statusFilter, q, archivedFilter]);

  useEffect(() => {
    const t = setTimeout(load, 150);
    return () => clearTimeout(t);
  }, [load]);

  const wrapperClass = embedded ? '' : 'min-h-screen bg-gray-50';

  return (
    <div className={wrapperClass}>
      {/* Page header — rendered only when not embedded */}
      {!embedded && (
        <div className="bg-white border-b sticky top-0 z-10">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 py-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div className="min-w-0">
              <h1 className="text-xl sm:text-2xl font-bold text-gray-900">{t('grids.event.title')}</h1>
              <p className="text-xs text-gray-500">
                {t('grids.event.subtitle')}
              </p>
            </div>
            {onCreateClick && (
              <button
                type="button"
                onClick={onCreateClick}
                className="rounded-md bg-gray-900 text-white px-4 py-2 text-sm font-semibold hover:bg-gray-800 whitespace-nowrap"
              >
                {t('grids.event.newCta')}
              </button>
            )}
          </div>
        </div>
      )}

      {/* Filter row */}
      <div className={`${embedded ? '' : 'bg-white border-b sticky'} top-0 z-[5]`}>
        <div className={`${embedded ? '' : 'max-w-6xl mx-auto'} px-0 sm:px-0 py-2 flex flex-wrap items-center gap-2`}>
          {[
            { k: 'upcoming', labelKey: 'grids.event.whenFilter.upcoming' },
            { k: 'past',     labelKey: 'grids.event.whenFilter.past' },
            { k: 'all',      labelKey: 'grids.event.whenFilter.all' },
          ].map(tab => (
            <button
              key={tab.k}
              type="button"
              onClick={() => { setWhen(tab.k); setArchivedFilter('hide'); }}
              className={`rounded-full px-3 py-1 text-xs font-semibold ${
                when === tab.k && archivedFilter !== 'only'
                  ? 'bg-gray-900 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >{t(tab.labelKey)}</button>
          ))}
          <button
            type="button"
            onClick={() => { setArchivedFilter('only'); setWhen('all'); }}
            className={`rounded-full px-3 py-1 text-xs font-semibold ${
              archivedFilter === 'only'
                ? 'bg-gray-900 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >{t('grids.event.archiveFilter')}</button>

          <div className="flex-1" />

          <input
            type="search"
            value={q}
            onChange={e => setQ(e.target.value)}
            placeholder={t('grids.event.searchPlaceholder')}
            className="rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-gray-900 focus:outline-none min-w-[180px]"
          />
          <select
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
            className="rounded-md border border-gray-300 px-3 py-1.5 text-sm bg-white"
          >
            <option value="">{t('grids.event.statusFilter.all')}</option>
            <option value="draft">{t('grids.event.statusFilter.draft')}</option>
            <option value="published">{t('grids.event.statusFilter.published')}</option>
            <option value="closed">{t('grids.event.statusFilter.closed')}</option>
            <option value="cancelled">{t('grids.event.statusFilter.cancelled')}</option>
          </select>
        </div>
      </div>

      {/* Body */}
      <div className={`${embedded ? '' : 'max-w-6xl mx-auto px-4 sm:px-6'} py-4 sm:py-6`}>
        {loading && (
          <div className="text-center text-sm text-gray-500 py-12">{t('grids.common.loading')}</div>
        )}

        {error && !loading && (
          <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-800">
            {error}
          </div>
        )}

        {!loading && !error && events.length === 0 && (
          <div className="rounded-xl border-2 border-dashed border-gray-300 bg-white p-10 text-center">
            <div className="text-4xl mb-2">📅</div>
            <h2 className="text-lg font-semibold text-gray-900">{t('grids.event.emptyTitle')}</h2>
            <p className="text-sm text-gray-600 mt-1 mb-4">
              {when === 'past'
                ? t('grids.event.emptyDescPast')
                : q || statusFilter
                  ? t('grids.common.tryRemoveFilters')
                  : t('grids.event.emptyDescFirst')}
            </p>
            {!q && !statusFilter && when !== 'past' && onCreateClick && (
              <button
                type="button"
                onClick={onCreateClick}
                className="rounded-md bg-gray-900 text-white px-4 py-2 text-sm font-semibold hover:bg-gray-800"
              >
                {t('grids.event.firstCreateCta')}
              </button>
            )}
          </div>
        )}

        {!loading && events.length > 0 && (
          <>
            <p className="text-xs text-gray-500 mb-3">
              {t('grids.event.count', { count: events.length })}
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {events.map(ev => <EventCard key={ev.id} event={ev} onStatusChange={handleStatusChange} />)}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
