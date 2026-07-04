/**
 * RetreatsCalendarPage — /ritiri (Fase 5).
 *
 * IL calendario pubblico: tutti i ritiri pubblicati e futuri, di tutti
 * gli organizzatori, filtrabili per categoria / regione / mese / prezzo.
 * Ogni card porta alla landing prenotabile (/e/:org/:slug) — la
 * differenza competitiva rispetto ai portali-vetrina: qui si prenota.
 */

import React, { useEffect, useMemo, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import useSeoMeta from './lib/useSeoMeta';
import { useTranslation } from 'react-i18next';
import api from '../../api/client';

const REGIONS = [
  'Abruzzo', 'Basilicata', 'Calabria', 'Campania', 'Emilia-Romagna',
  'Friuli-Venezia Giulia', 'Lazio', 'Liguria', 'Lombardia', 'Marche',
  'Molise', 'Piemonte', 'Puglia', 'Sardegna', 'Sicilia', 'Toscana',
  'Trentino-Alto Adige', 'Umbria', "Valle d'Aosta", 'Veneto',
];

function fmtPrice(n) {
  if (n === null || n === undefined) return null;
  try {
    return new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }).format(n);
  } catch { return `${n} €`; }
}

function fmtDates(start, end, lang = 'it-IT') {
  try {
    const s = new Date(start);
    const opts = { day: 'numeric', month: 'short' };
    if (!end) return s.toLocaleDateString(lang, { ...opts, year: 'numeric' });
    const e = new Date(end);
    return `${s.toLocaleDateString(lang, opts)} – ${e.toLocaleDateString(lang, { ...opts, year: 'numeric' })}`;
  } catch { return start; }
}

export default function RetreatsCalendarPage() {
  const { t, i18n } = useTranslation('landings');
  const [params, setParams] = useSearchParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  // Path params (pagine SEO /ritiri/:cat/:reg) hanno priorità sui query
  // param (filtri interattivi): un URL indicizzabile è un URL stabile.
  const routeParams = useParams();
  const category = routeParams.categoria || params.get('categoria') || '';
  const region = routeParams.regione || params.get('regione') || '';
  const month = params.get('mese') || '';

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    const q = {};
    if (category) q.category = category;
    if (region) q.region = region;
    if (month) q.month = month;
    api.get('/public/retreats', { params: q })
      .then(res => { if (mounted) setData(res.data); })
      .catch(() => { if (mounted) setData({ items: [], total: 0, categories: {} }); })
      .finally(() => { if (mounted) setLoading(false); });
    return () => { mounted = false; };
  }, [category, region, month]);

  const setFilter = (key, value) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value); else next.delete(key);
    setParams(next, { replace: true });
  };

  const categories = useMemo(() => Object.entries(data?.categories || {}), [data]);

  // SEO — title/description dinamici per categoria×regione. È il motore
  // di domanda: "ritiri yoga in Puglia" deve essere un URL indicizzabile.
  const catLabel = category ? (data?.categories?.[category] || category) : '';
  const seoTitle = (() => {
    const bits = ['Ritiri'];
    if (catLabel) bits.push(catLabel.toLowerCase());
    if (region) bits.push('in ' + region);
    return bits.join(' ') + ' — prenota online';
  })();
  useSeoMeta({
    title: seoTitle,
    description: `Trova e prenota ${catLabel ? catLabel.toLowerCase() + ' ' : ''}ritiri${region ? ' in ' + region : ' in Italia'}: date, prezzi e disponibilità in tempo reale, con prenotazione e caparra online.`,
    canonicalPath: (routeParams.categoria || routeParams.regione)
      ? window.location.pathname : '/ritiri',
  });
  const selCls = 'rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-gray-900';

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-gray-900 text-white">
        <div className="max-w-6xl mx-auto px-4 py-10">
          <h1 className="text-3xl font-bold">{t('landings:calendar.title')}</h1>
          <p className="text-gray-300 mt-2 max-w-xl">{t('landings:calendar.subtitle')}</p>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-6">
        {/* Filtri */}
        <div className="flex flex-wrap gap-2 mb-6">
          <select value={category} onChange={e => setFilter('categoria', e.target.value)} className={selCls}>
            <option value="">{t('landings:calendar.allCategories')}</option>
            {categories.map(([key, label]) => (
              <option key={key} value={key}>{label}</option>
            ))}
          </select>
          <select value={region} onChange={e => setFilter('regione', e.target.value)} className={selCls}>
            <option value="">{t('landings:calendar.allRegions')}</option>
            {REGIONS.map(r => <option key={r} value={r}>{r}</option>)}
          </select>
          <input
            type="month"
            value={month}
            onChange={e => setFilter('mese', e.target.value)}
            className={selCls}
          />
          {(category || region || month) && (
            <button
              type="button"
              onClick={() => setParams({}, { replace: true })}
              className="text-sm text-gray-500 underline px-2"
            >
              {t('landings:calendar.clearFilters')}
            </button>
          )}
        </div>

        {/* Griglia */}
        {loading ? (
          <p className="text-gray-500 py-12 text-center">{t('landings:calendar.loading')}</p>
        ) : (data?.items || []).length === 0 ? (
          <div className="text-center py-16">
            <p className="text-lg font-semibold text-gray-900">{t('landings:calendar.emptyTitle')}</p>
            <p className="text-gray-500 mt-1">{t('landings:calendar.emptyBody')}</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {data.items.map(item => (
              <Link
                key={`${item.org_slug}/${item.slug}`}
                to={item.url}
                className="group rounded-xl border border-gray-200 bg-white overflow-hidden hover:shadow-md transition-shadow"
              >
                <div className="h-40 bg-gray-100 overflow-hidden">
                  {item.cover_image_url ? (
                    <img
                      src={item.cover_image_url}
                      alt=""
                      loading="lazy"
                      className="w-full h-full object-cover group-hover:scale-[1.02] transition-transform"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-4xl">🧘</div>
                  )}
                </div>
                <div className="p-4">
                  <p className="text-[11px] font-semibold text-emerald-700 uppercase tracking-wide">
                    {(data.categories || {})[item.category] || item.category || ''}
                  </p>
                  <h2 className="font-semibold text-gray-900 mt-0.5 line-clamp-2">{item.title}</h2>
                  <p className="text-sm text-gray-600 mt-1">
                    {fmtDates(item.start_at, item.end_at, i18n.language)}
                    {(item.city || item.region) && (
                      <> · {[item.city, item.region].filter(Boolean).join(', ')}</>
                    )}
                  </p>
                  <div className="flex items-center justify-between mt-3">
                    <span className="text-sm text-gray-500">{item.org_name}</span>
                    <span className="text-right">
                      {item.price_from != null && (
                        <span className="font-bold text-gray-900">
                          {t('landings:calendar.priceFrom', { price: fmtPrice(item.price_from) })}
                        </span>
                      )}
                      {item.deposit_mode && (
                        <span className="block text-[11px] text-emerald-700">
                          {t('landings:calendar.depositBadge')}
                        </span>
                      )}
                    </span>
                  </div>
                  {item.remaining != null && item.remaining <= 5 && item.remaining > 0 && (
                    <p className="text-[11px] font-semibold text-amber-700 mt-2">
                      {t('landings:calendar.fewLeft', { count: item.remaining })}
                    </p>
                  )}
                </div>
              </Link>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
