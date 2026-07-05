/**
 * RetreatsCalendarPage — /ritiri (Fase 5 → redesign F1, 5/7/2026).
 *
 * IL calendario pubblico: tutti i ritiri pubblicati e futuri, di tutti
 * gli organizzatori. Ogni card porta alla landing prenotabile — la
 * differenza competitiva rispetto ai portali-vetrina: qui si prenota.
 *
 * F1 (docs/DIRECTORY_DESIGN_PLAN.md): hero con ricerca, categorie
 * visuali, filtri sticky, card raffinate (operatore cliccabile → /o/),
 * skeleton, empty state caldo. Le logiche SEO restano INTATTE: path
 * param /ritiri/:cat/:reg prioritario sui query param, useSeoMeta.
 */

import React, { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import useSeoMeta from './lib/useSeoMeta';
import { useTranslation } from 'react-i18next';
import api from '../../api/client';

const REGIONS = [
  'Abruzzo', 'Basilicata', 'Calabria', 'Campania', 'Emilia-Romagna',
  'Friuli-Venezia Giulia', 'Lazio', 'Liguria', 'Lombardia', 'Marche',
  'Molise', 'Piemonte', 'Puglia', 'Sardegna', 'Sicilia', 'Toscana',
  'Trentino-Alto Adige', 'Umbria', "Valle d'Aosta", 'Veneto',
];

// Icone per le categorie note (chiavi backend) — fallback ✨ per le nuove.
const CATEGORY_ICONS = {
  yoga: '🧘', meditazione: '🌿', meditation: '🌿', detox: '🥗',
  sound: '🎶', sound_healing: '🎶', breathwork: '🌬️', fitness: '💪',
  benessere: '🌸', wellness: '🌸', escursioni: '🥾', hiking: '🥾',
};

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

function dateBadge(start, lang = 'it-IT') {
  try {
    const s = new Date(start);
    return {
      day: s.toLocaleDateString(lang, { day: 'numeric' }),
      month: s.toLocaleDateString(lang, { month: 'short' }).replace('.', ''),
    };
  } catch { return null; }
}

function SkeletonCard() {
  return (
    <div className="rounded-2xl border border-border bg-card overflow-hidden">
      <div className="h-48 bg-muted animate-pulse" />
      <div className="p-4 space-y-2">
        <div className="h-3 w-16 rounded bg-muted animate-pulse" />
        <div className="h-4 w-3/4 rounded bg-muted animate-pulse" />
        <div className="h-3 w-1/2 rounded bg-muted animate-pulse" />
      </div>
    </div>
  );
}

export default function RetreatsCalendarPage() {
  const { t, i18n } = useTranslation('landings');
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  // Path params (pagine SEO /ritiri/:cat/:reg) hanno priorità sui query
  // param (filtri interattivi): un URL indicizzabile è un URL stabile.
  const routeParams = useParams();
  const category = routeParams.categoria || params.get('categoria') || '';
  const region = routeParams.regione || params.get('regione') || '';
  const month = params.get('mese') || '';
  const [query, setQuery] = useState('');

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

  // Ricerca client-side sul dataset già caricato (titolo, luogo, operatore)
  const items = useMemo(() => {
    const list = data?.items || [];
    const q = query.trim().toLowerCase();
    if (!q) return list;
    return list.filter(it => (
      (it.title || '').toLowerCase().includes(q)
      || (it.city || '').toLowerCase().includes(q)
      || (it.region || '').toLowerCase().includes(q)
      || (it.org_name || '').toLowerCase().includes(q)
    ));
  }, [data, query]);

  // SEO — title/description dinamici per categoria×regione (INTATTO).
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
    // F3 — ItemList dei ritiri visibili (max 20: ai crawler serve il
    // segnale di lista, non l'inventario completo)
    jsonLd: (data?.items || []).length > 0 ? {
      '@context': 'https://schema.org',
      '@type': 'ItemList',
      itemListElement: (data.items || []).slice(0, 20).map((it, i) => ({
        '@type': 'ListItem',
        position: i + 1,
        name: it.title,
        url: `${window.location.origin}${it.url}`,
      })),
    } : undefined,
  });

  const anyFilter = category || region || month || query;
  const selCls = 'rounded-full border border-gray-300 bg-white px-3 py-1.5 text-sm focus:border-primary focus:outline-none';

  return (
    <div className="min-h-screen bg-background">
      {/* ── Hero ─────────────────────────────────────────────────────── */}
      <header className="bg-gradient-sidebar text-white">
        <div className="max-w-6xl mx-auto px-4 pt-12 pb-8">
          <h1 className="text-3xl md:text-4xl font-bold tracking-tight">
            {catLabel || region
              ? seoTitle.replace(' — prenota online', '')
              : t('landings:calendar.title')}
          </h1>
          <p className="text-white/75 mt-2 max-w-xl">{t('landings:calendar.subtitle')}</p>

          <div className="mt-6 max-w-lg">
            <input
              type="search"
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder={t('landings:calendar.searchPlaceholder', { defaultValue: 'Cerca un ritiro, un luogo, un organizzatore…' })}
              className="w-full rounded-full border-0 bg-white/95 px-5 py-3 text-sm text-gray-900 shadow-lg focus:outline-none focus:ring-2 focus:ring-white/60"
            />
          </div>

          {/* Categorie visuali — dalle categorie REALI del backend */}
          {categories.length > 0 && (
            <div className="mt-6 flex gap-2 overflow-x-auto pb-1 -mx-1 px-1">
              <button
                onClick={() => setFilter('categoria', '')}
                className={`shrink-0 rounded-full px-4 py-2 text-sm font-medium transition-colors ${
                  !category ? 'bg-white text-gray-900' : 'bg-white/10 text-white hover:bg-white/20'
                }`}
              >
                {t('landings:calendar.allCategories')}
              </button>
              {categories.map(([key, label]) => (
                <button
                  key={key}
                  onClick={() => setFilter('categoria', key)}
                  className={`shrink-0 rounded-full px-4 py-2 text-sm font-medium transition-colors ${
                    category === key ? 'bg-white text-gray-900' : 'bg-white/10 text-white hover:bg-white/20'
                  }`}
                >
                  <span aria-hidden className="mr-1.5">{CATEGORY_ICONS[key] || '✨'}</span>
                  {label}
                </button>
              ))}
            </div>
          )}
        </div>
      </header>

      {/* ── Barra filtri sticky ──────────────────────────────────────── */}
      <div className="sticky top-0 z-20 border-b border-border bg-background/95 backdrop-blur">
        <div className="max-w-6xl mx-auto px-4 py-2.5 flex flex-wrap items-center gap-2">
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
          {anyFilter && (
            <button
              type="button"
              onClick={() => { setParams({}, { replace: true }); setQuery(''); }}
              className="text-sm text-muted-foreground underline px-1"
            >
              {t('landings:calendar.clearFilters')}
            </button>
          )}
          {!loading && (
            <span className="ml-auto text-xs text-muted-foreground">
              {t('landings:calendar.resultsCount', { count: items.length, defaultValue: '{{count}} ritiri' })}
            </span>
          )}
        </div>
      </div>

      {/* ── Griglia ──────────────────────────────────────────────────── */}
      <main className="max-w-6xl mx-auto px-4 py-8">
        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {[1, 2, 3, 4, 5, 6].map(i => <SkeletonCard key={i} />)}
          </div>
        ) : items.length === 0 ? (
          <div className="text-center py-20 max-w-md mx-auto">
            <span aria-hidden className="text-4xl">🌿</span>
            <p className="mt-3 text-lg font-semibold text-foreground">
              {t('landings:calendar.emptyTitle')}
            </p>
            <p className="text-muted-foreground mt-1">
              {anyFilter
                ? t('landings:calendar.emptyFiltered', { defaultValue: 'Prova ad allargare la ricerca: togli un filtro o guarda un altro mese.' })
                : t('landings:calendar.emptyBody')}
            </p>
            {anyFilter && (
              <button
                onClick={() => { setParams({}, { replace: true }); setQuery(''); }}
                className="mt-4 rounded-full bg-primary text-primary-foreground px-5 py-2 text-sm font-semibold"
              >
                {t('landings:calendar.showAll', { defaultValue: 'Mostra tutti i ritiri' })}
              </button>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {items.map(item => {
              const badge = dateBadge(item.start_at, i18n.language);
              return (
                <Link
                  key={`${item.org_slug}/${item.slug}`}
                  to={item.url}
                  className="group rounded-2xl border border-border bg-card overflow-hidden hover-lift"
                >
                  <div className="relative h-48 bg-muted overflow-hidden">
                    {item.cover_image_url ? (
                      <img
                        src={item.cover_image_url}
                        alt=""
                        loading="lazy"
                        className="w-full h-full object-cover group-hover:scale-[1.03] transition-transform duration-300"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-5xl bg-gradient-to-br from-secondary to-muted" aria-hidden>
                        {CATEGORY_ICONS[item.category] || '🧘'}
                      </div>
                    )}
                    {badge && (
                      <div className="absolute top-3 left-3 rounded-xl bg-white/95 px-2.5 py-1.5 text-center shadow-md leading-none">
                        <span className="block text-lg font-bold text-gray-900">{badge.day}</span>
                        <span className="block text-[10px] font-semibold uppercase text-gray-500 mt-0.5">{badge.month}</span>
                      </div>
                    )}
                    {item.remaining != null && item.remaining <= 5 && item.remaining > 0 && (
                      <span className="absolute top-3 right-3 rounded-full bg-accent text-accent-foreground px-2.5 py-1 text-[11px] font-bold shadow">
                        {t('landings:calendar.fewLeft', { count: item.remaining })}
                      </span>
                    )}
                  </div>
                  <div className="p-4">
                    <p className="text-[11px] font-semibold text-primary uppercase tracking-wide">
                      {(data.categories || {})[item.category] || item.category || ''}
                    </p>
                    <h2 className="font-semibold text-foreground mt-0.5 line-clamp-2">{item.title}</h2>
                    <p className="text-sm text-muted-foreground mt-1">
                      {fmtDates(item.start_at, item.end_at, i18n.language)}
                      {(item.city || item.region) && (
                        <> · {[item.city, item.region].filter(Boolean).join(', ')}</>
                      )}
                    </p>
                    <div className="flex items-center justify-between mt-3">
                      {/* F2 — operatore cliccabile → profilo. Link annidato in
                          Link non è HTML valido: handler con stopPropagation
                          che naviga SPA (niente full reload). */}
                      <span
                        role="link"
                        tabIndex={0}
                        onClick={(e) => {
                          e.preventDefault(); e.stopPropagation();
                          navigate(`/o/${item.org_slug}`);
                        }}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            e.preventDefault(); e.stopPropagation();
                            navigate(`/o/${item.org_slug}`);
                          }
                        }}
                        className="text-sm text-muted-foreground hover:text-primary hover:underline truncate"
                      >
                        {item.org_name}
                      </span>
                      <span className="text-right shrink-0 ml-2">
                        {item.price_from != null && (
                          <span className="font-bold text-foreground">
                            {t('landings:calendar.priceFrom', { price: fmtPrice(item.price_from) })}
                          </span>
                        )}
                        {item.deposit_mode && (
                          <span className="block text-[11px] text-primary">
                            {t('landings:calendar.depositBadge')}
                          </span>
                        )}
                      </span>
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
}
