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
import GeoSearchBar from './components/GeoSearchBar';
import MarketplaceShell from './components/MarketplaceShell';
import PrelaunchBanner from '../prelaunch/PrelaunchBanner';
import MarketplaceValueSections from './components/MarketplaceValueSections';
// G3 — vista mappa lazy (Leaflet caricato solo quando serve)
const RetreatsMapView = React.lazy(() => import('./components/RetreatsMapView'));

// G3 — il filtro regioni e' stato sostituito dalla ricerca geografica
// (GeoSearchBar); il param backend `region` resta per i vecchi link SEO.

// DS2 — icone categoria professionali (lucide), mappa unica condivisa.
import { Globe2 } from 'lucide-react';
import { CategoryIcon } from './lib/categoryIcons';

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

  // G3 — posizione+raggio dall'URL (condivisibile): ?lat&lng&r&luogo
  const geoLat = params.get('lat');
  const geoLng = params.get('lng');
  const geoRadius = Number(params.get('r')) || 100;
  const geoLabel = params.get('luogo') || '';
  const geoValue = (geoLat && geoLng)
    ? { lat: Number(geoLat), lng: Number(geoLng), label: geoLabel, radius: geoRadius }
    : null;
  const setGeo = (next) => {
    const nx = new URLSearchParams(params);
    if (next) {
      nx.set('lat', String(next.lat)); nx.set('lng', String(next.lng));
      nx.set('r', String(next.radius || 100));
      if (next.label) nx.set('luogo', next.label); else nx.delete('luogo');
    } else {
      ['lat', 'lng', 'r', 'luogo'].forEach(k => nx.delete(k));
    }
    setParams(nx, { replace: true });
  };
  // vista lista/mappa
  const view = params.get('vista') === 'mappa' ? 'mappa' : 'lista';

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    const q = {};
    if (category) q.category = category;
    if (region) q.region = region;
    if (month) q.month = month;
    if (geoLat && geoLng) {
      q.lat = geoLat; q.lng = geoLng; q.radius_km = geoRadius;
    }
    // Multilingua manuale: la vista in lingua X mostra solo i ritiri
    // offerti in X (l'italiano mostra tutto)
    const uiLang = (i18n.language || 'it').slice(0, 2);
    if (uiLang !== 'it') q.lang = uiLang;
    api.get('/public/retreats', { params: q })
      .then(res => { if (mounted) setData(res.data); })
      .catch(() => { if (mounted) setData({ items: [], total: 0, categories: {} }); })
      .finally(() => { if (mounted) setLoading(false); });
    return () => { mounted = false; };
  }, [category, region, month, geoLat, geoLng, geoRadius, i18n.language]);

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

  // SEO3 — le pagine /ritiri/{cat}/{regione} vanno raggiunte da LINK
  // interni (non solo dal sitemap): su una pagina categoria elenchiamo
  // le regioni con ritiri come link crawlabili.
  const regionsForCategory = useMemo(() => {
    if (!category || region) return [];
    const seen = new Set();
    (data?.items || []).forEach(it => { if (it.region) seen.add(it.region); });
    return [...seen].sort().slice(0, 12);
  }, [data, category, region]);

  // SEO — title/description dinamici per categoria×regione. Allineati allo
  // shell (routers/seo_shell._meta_category): "Ritiri di {cat} in {regione}",
  // separatore | (mai em-dash), niente "in Italia" (regola brand no-geografia
  // imposta — la location arriva SOLO quando c'è davvero una regione).
  const catLabel = category ? (data?.categories?.[category] || category) : '';
  const seoHeading = (() => {
    const bits = ['Ritiri'];
    if (catLabel) bits.push('di ' + catLabel);
    if (region) bits.push('in ' + region);
    return bits.join(' ');
  })();
  useSeoMeta({
    title: `${seoHeading} | Aurya`,
    description: `Trova e prenota ${catLabel ? catLabel.toLowerCase() + ' ' : ''}ritiri${region ? ' a ' + region : ''}: date, prezzi e disponibilità in tempo reale, con prenotazione e caparra online.`,
    canonicalPath: (routeParams.categoria || routeParams.regione)
      ? window.location.pathname : '/',
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
    <MarketplaceShell noSearch>
    <div className="bg-background">
      {/* PL6 — avviso anteprima lancio (solo in pre-lancio) */}
      <PrelaunchBanner audience="traveler" />
      {/* ── Hero (DS: il tramonto di Aurya in sottofondo) ────────────── */}
      <header className="relative bg-gradient-sidebar text-white overflow-hidden">
        {/* poster sempre sotto: primo dipinto + fallback reduced-motion */}
        <img aria-hidden src="/media/aurya-hero-poster.jpg" alt=""
             className="absolute inset-0 w-full h-full object-cover" />
        <video aria-hidden className="hero-video absolute inset-0 w-full h-full object-cover"
               autoPlay muted loop playsInline preload="metadata"
               poster="/media/aurya-hero-poster.jpg" src="/media/aurya-hero.mp4" />
        {/* scrim salvia: il tramonto è oro acceso, i testi restano leggibili */}
        <div aria-hidden className="absolute inset-0 pointer-events-none bg-gradient-to-b from-[#14231d]/85 via-[#14231d]/55 to-[#0e1a15]/90" />
        <div className="relative max-w-6xl mx-auto px-4 pt-20 pb-16 md:pt-28 md:pb-24 text-center">
          {/* RB4 — il motto in font-brand, il filo d'oro del wordmark */}
          <p aria-hidden className="font-brand uppercase tracking-[0.35em] text-base md:text-2xl text-[#f2dfab] mb-4 select-none text-hero-shadow flex items-center justify-center gap-4">
            <span aria-hidden className="hidden sm:block h-px w-12 md:w-20 bg-gradient-to-r from-transparent to-[#d6c49a]/80" />
            Connect · Heal · Grow
            <span aria-hidden className="hidden sm:block h-px w-12 md:w-20 bg-gradient-to-l from-transparent to-[#d6c49a]/80" />
          </p>
          <h1 className="font-display text-4xl md:text-6xl font-medium tracking-tight leading-tight text-hero-shadow">
            {catLabel || region ? seoHeading : t('landings:calendar.title')}
          </h1>
          <p className="text-white/95 mt-4 max-w-xl mx-auto text-base md:text-lg text-hero-shadow">{t('landings:calendar.subtitle')}</p>

          <div className="mt-7 max-w-xl mx-auto">
            <input
              type="search"
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder={t('landings:calendar.searchPlaceholder', { defaultValue: 'Cerca un ritiro, un luogo, un organizzatore…' })}
              className="w-full rounded-full border-0 bg-white/95 backdrop-blur px-6 py-3.5 md:py-4 text-base text-gray-900 shadow-2xl focus:outline-none focus:ring-2 focus:ring-[#d6c49a]"
            />
          </div>

          {/* Categorie visuali — dalle categorie REALI del backend.
              L1: niente strip a scorrimento (era overflow-x-auto, con
              jank ai reload): riga statica che va a capo. */}
          {categories.length > 0 && (
            <div className="mt-7 flex flex-wrap gap-2 justify-center">
              <button
                onClick={() => setFilter('categoria', '')}
                className={`rounded-full px-4 py-2 text-sm font-medium transition-colors backdrop-blur-sm ${
                  !category ? 'bg-white text-gray-900 shadow-lg' : 'bg-black/25 border border-white/25 text-white hover:bg-black/40'
                }`}
              >
                {t('landings:calendar.allCategories')}
              </button>
              {categories.map(([key, label]) => (
                <button
                  key={key}
                  onClick={() => setFilter('categoria', key)}
                  className={`rounded-full px-4 py-2 text-sm font-medium transition-colors backdrop-blur-sm ${
                    category === key ? 'bg-white text-gray-900 shadow-lg' : 'bg-black/25 border border-white/25 text-white hover:bg-black/40'
                  }`}
                >
                  <CategoryIcon category={key} className="h-4 w-4 mr-1.5 inline-block align-[-2px]" />
                  {/* T3 — label categoria via i18n (fallback: label backend) */}
                  {t(`landings:categories.${key}`, { defaultValue: label })}
                </button>
              ))}
            </div>
          )}
        </div>
      </header>

      {/* SEO3 — breadcrumb navigabile + regioni come LINK crawlabili sulle
          pagine categoria: i motori raggiungono /ritiri/{cat}/{regione} dai
          link interni, non solo dal sitemap. */}
      {(category || region) && (
        <div className="border-b border-border bg-background">
          <div className="max-w-6xl mx-auto px-4 py-3">
            <nav aria-label="breadcrumb" className="text-xs text-muted-foreground">
              <Link to="/" className="hover:text-primary hover:underline">Aurya</Link>
              <span className="mx-1.5" aria-hidden>›</span>
              {category ? (
                <Link to={`/ritiri/${category}`} className="hover:text-primary hover:underline">
                  {catLabel || category}
                </Link>
              ) : (
                <span className="text-foreground">{t('landings:calendar.title', { defaultValue: 'Ritiri' })}</span>
              )}
              {region && (<>
                <span className="mx-1.5" aria-hidden>›</span>
                <span className="text-foreground">{region}</span>
              </>)}
            </nav>
            {regionsForCategory.length > 0 && (
              <div className="mt-2.5 flex flex-wrap items-center gap-2">
                <span className="text-xs font-semibold text-muted-foreground">
                  {t('landings:calendar.byRegion', { defaultValue: 'Per regione:' })}
                </span>
                {regionsForCategory.map(rg => (
                  <Link key={rg} to={`/ritiri/${category}/${rg}`}
                        className="rounded-full border border-border bg-card px-3 py-1 text-xs font-medium text-foreground hover:border-primary hover:text-primary transition-colors">
                    {rg}
                  </Link>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Barra filtri sticky ──────────────────────────────────────── */}
      <div className="sticky top-14 z-20 border-b border-border bg-background/95 backdrop-blur">
        <div className="max-w-6xl mx-auto px-4 py-2.5 flex flex-wrap items-center gap-2">
          {/* G3 — "Dove?" con autocomplete+raggio al posto delle regioni
              (gli eventi possono essere in tutto il mondo) */}
          <GeoSearchBar value={geoValue} onChange={setGeo} />
          <input
            type="month"
            value={month}
            onChange={e => setFilter('mese', e.target.value)}
            className={selCls}
          />
          {/* V3 — la ricerca segue lo scroll (era solo nell'hero) */}
          <input
            type="search"
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder={t('landings:calendar.searchShort', { defaultValue: 'Cerca…' })}
            className="rounded-full border border-gray-300 bg-white px-3 py-1.5 text-sm w-32 focus:w-48 transition-all focus:border-primary focus:outline-none"
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
          <button
            type="button"
            onClick={() => setFilter('vista', view === 'mappa' ? '' : 'mappa')}
            className={`rounded-full px-3 py-1.5 text-sm font-medium transition-colors ${
              view === 'mappa'
                ? 'bg-primary text-white'
                : 'border border-gray-300 bg-white text-gray-700 hover:border-primary'
            }`}
          >
            {view === 'mappa'
              ? t('landings:calendar.viewList', { defaultValue: '☰ Lista' })
              : t('landings:calendar.viewMap', { defaultValue: 'Mappa' })}
          </button>
          {!loading && (
            <span className="ml-auto text-xs text-muted-foreground">
              {t('landings:calendar.resultsCount', { count: items.length, defaultValue: '{{count}} ritiri' })}
            </span>
          )}
        </div>
        {/* L1 — nota filtro lingua: in lingua ≠ it la vista è filtrata
            ai ritiri TENUTI in quella lingua; va detto, o l'elenco
            ridotto sembra un bug. */}
        {(i18n.language || 'it').slice(0, 2) !== 'it' && (
          <div className="max-w-6xl mx-auto px-4 pb-2 -mt-0.5">
            <p className="text-xs text-muted-foreground">
              <Globe2 className="h-3.5 w-3.5 inline-block mr-1 align-[-2px]" aria-hidden />{t('marketplace.langFilterCaption', {
                lang: (i18n.language || '').slice(0, 2).toUpperCase(),
                defaultValue: 'Mostriamo i ritiri e le esperienze tenuti in {{lang}}. Cambia lingua in alto per vederne altri.',
              })}
            </p>
          </div>
        )}
      </div>

      {/* ── Griglia ──────────────────────────────────────────────────── */}
      {/* GT3 (rivisto, scelta founder): niente sezione In evidenza
          separata — i featured si riconoscono dal badge ✦ sulla card,
          il calendario resta un'unica lista cronologica senza doppioni. */}
      <main className="max-w-6xl mx-auto px-4 py-8">
        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {[1, 2, 3, 4, 5, 6].map(i => <SkeletonCard key={i} />)}
          </div>
        ) : items.length === 0 ? (
          <div className="text-center py-20 max-w-md mx-auto">
            <img src="/logo-aurya-128.png" alt="" aria-hidden className="mx-auto h-14 w-14 select-none opacity-80" draggable={false} />
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
        ) : view === 'mappa' ? (
          /* G3 — la directory sulla mappa */
          <React.Suspense fallback={<div className="h-[520px] rounded-2xl bg-gray-100 animate-pulse" />}>
            <RetreatsMapView items={items} />
          </React.Suspense>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {items.map(item => {
              const badge = dateBadge(item.start_at, i18n.language);
              return (
                <Link
                  key={`${item.org_slug}/${item.slug}`}
                  to={item.sample ? '#' : item.url}
                  onClick={item.sample ? (e) => e.preventDefault() : undefined}
                  className={`group card-lift rounded-2xl border border-border bg-card overflow-hidden shadow-sm ${item.sample ? 'pointer-events-none select-none' : ''}`}
                >
                  <div className="relative h-56 bg-muted overflow-hidden">
                    {/* PL6 — anteprima lancio: card campione sfocata e non cliccabile */}
                    {item.sample && (
                      <div className="absolute inset-0 z-10 flex items-center justify-center bg-[#1e2b26]/25 backdrop-blur-[1px]">
                        <span className="rounded-full bg-white/90 px-3 py-1.5 text-[11px] font-semibold text-[#376254] shadow">
                          {t('landings:calendar.comingSoon', { defaultValue: 'Presto disponibile' })}
                        </span>
                      </div>
                    )}
                    {item.cover_image_url ? (
                      <img
                        src={item.cover_image_url}
                        alt=""
                        loading="lazy"
                        className={`w-full h-full object-cover transition-transform duration-500 ${item.sample ? 'blur-[3px] scale-105' : 'group-hover:scale-[1.04]'}`}
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-secondary to-muted" aria-hidden>
                        <CategoryIcon category={item.category} className="h-14 w-14 opacity-70" />
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
                    {/* MD3 — badge dei piani "In evidenza" (promessa Pro resa vera) */}
                    {item.featured && !(item.remaining != null && item.remaining <= 5 && item.remaining > 0) && (
                      <span className="absolute top-3 right-3 rounded-full bg-gradient-to-r from-[#8a7440] to-[#a98f52] text-[#faf6ec] px-3 py-1 text-[11px] font-semibold shadow-lg">
                        ✦ {t('landings:calendar.featured', { defaultValue: 'In evidenza' })}
                      </span>
                    )}
                  </div>
                  <div className="p-4">
                    {/* V3 — tap sulla categoria → filtra la directory */}
                    <p
                      role="button"
                      tabIndex={0}
                      onClick={(e) => {
                        e.preventDefault(); e.stopPropagation();
                        setFilter('categoria', item.category);
                      }}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          e.preventDefault(); e.stopPropagation();
                          setFilter('categoria', item.category);
                        }
                      }}
                      className="text-[11px] font-semibold text-primary uppercase tracking-wide hover:underline w-fit"
                    >
                      {t(`landings:categories.${item.category}`, {
                        defaultValue: (data.categories || {})[item.category] || item.category || '',
                      })}
                    </p>
                    <h2 className="font-semibold text-foreground mt-0.5 line-clamp-2">{item.title}</h2>
                    <p className="text-sm text-muted-foreground mt-1">
                      {fmtDates(item.start_at, item.end_at, i18n.language)}
                      {(item.city || item.region) && (
                        <> · {[item.city, item.region].filter(Boolean).join(', ')}</>
                      )}
                      {item.distance_km != null && (
                        <span className="ml-1.5 inline-block rounded-full bg-primary/10 text-primary px-2 py-0.5 text-[11px] font-semibold align-middle">
                          {t('landings:calendar.distanceAway', {
                            defaultValue: 'a {{km}} km', km: item.distance_km })}
                        </span>
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
                        {/* AN7 — recensioni verificate visibili dove si sceglie */}
                        {item.org_rating?.count > 0 && (
                          <span className="ml-1.5 text-xs text-foreground whitespace-nowrap">
                            ★ {item.org_rating.avg}
                            <span className="text-muted-foreground"> ({item.org_rating.count})</span>
                          </span>
                        )}
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

      {/* AN1 — l'anima di Aurya: come funziona / perché / organizzatori.
          Solo sulla home "pulita": chi sta filtrando non va interrotto. */}
      {!anyFilter && view !== 'mappa' && <MarketplaceValueSections />}
    </div>
    </MarketplaceShell>
  );
}
