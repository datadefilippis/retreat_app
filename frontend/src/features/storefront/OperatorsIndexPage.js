/**
 * OperatorsIndexPage — /operatori (+ /operatori/:categoria)
 *
 * S2 del SEO_MASTER_PLAN: l'aggregatore pubblico degli organizzatori —
 * il secondo pilastro di pagine indicizzabili dopo i ritiri. Le card
 * portano al profilo /o/{slug}; i filtri categoria mostrano SOLO
 * categorie con operatori reali (anti thin-content) e hanno una URL
 * propria (/operatori/yoga) indicizzabile.
 */

import React, { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import api from '../../api/client';
import MarketplaceShell from './components/MarketplaceShell';
import PrelaunchBanner from '../prelaunch/PrelaunchBanner';
import Redacted from '../prelaunch/Redacted';
import GeoSearchBar from './components/GeoSearchBar';
import useSeoMeta from './lib/useSeoMeta';

const OperatorsMapView = React.lazy(() => import('./components/OperatorsMapView'));

import { Leaf, MapPin } from 'lucide-react';

// LM3 — l'URL parla italiano (?ordina=), l'API il gergo suo (sort=):
// la mappa e' l'unico punto di traduzione.
const SORT_PARAM = { distanza: 'distance', valutazione: 'rating', prezzo: 'price' };

// LM2 — stelle piene/vuote sul rating medio (stesso disegno del profilo)
function Stars({ value }) {
  const full = Math.round(value || 0);
  return (
    <span className="text-xs tracking-tight" aria-label={`${value} su 5`}>
      <span className="text-amber-500">{'★'.repeat(full)}</span>
      <span className="text-gray-300">{'★'.repeat(5 - full)}</span>
    </span>
  );
}

function OperatorCard({ op, t }) {
  // LM2 — vista rapida: anteprima listino IN CARD (pattern PN3,
  // aria-expanded); il click sulla card resta il link al profilo.
  const [quickOpen, setQuickOpen] = useState(false);
  const preview = op.listino_preview || [];
  return (
    <div className={`group rounded-2xl border border-border bg-card overflow-hidden hover:shadow-lg transition-shadow flex flex-col ${op.sample ? 'pointer-events-none select-none' : ''}`}>
    <Link
      to={op.sample ? '#' : `/o/${op.org_slug}`}
      onClick={op.sample ? (e) => e.preventDefault() : undefined}
      className="block"
    >
      <div className="h-24 bg-gradient-to-br from-primary/15 to-secondary relative">
        {/* PL6 — operatore campione: cover sfocata + chip anteprima */}
        {op.sample && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-[#1e2b26]/25 backdrop-blur-[1px]">
            <span className="rounded-full bg-white/90 px-3 py-1 text-[11px] font-semibold text-[#376254] shadow">
              {t('landings:calendar.comingSoon', { defaultValue: 'Presto disponibile' })}
            </span>
          </div>
        )}
        {op.cover_url && (
          <img src={op.cover_url} alt=""
               className={`w-full h-full object-cover ${op.sample ? 'blur-[3px] scale-105' : ''}`}
               loading="lazy" />
        )}
        {/* GT3 — badge dei piani "In evidenza" anche nell'aggregatore */}
        {op.featured && (
          <span className="absolute top-2 right-2 rounded-full bg-[#376254] text-white px-2.5 py-1 text-[11px] font-semibold shadow">
            ✦ {t('landings:calendar.featured', { defaultValue: 'In evidenza' })}
          </span>
        )}
        <div className="absolute -bottom-6 left-4 h-14 w-14 rounded-full border-2 border-white bg-white shadow overflow-hidden flex items-center justify-center">
          {op.logo_url
            ? <img src={op.logo_url} alt="" className="h-full w-full object-cover" loading="lazy" />
            : <Leaf className="h-6 w-6 text-[#376254]/50" aria-hidden />}
        </div>
      </div>
      <div className="pt-8 px-4 pb-4">
        {/* PL9 — nome campione: segnaposto sfocato, mai il nome finto */}
        <p className="font-semibold text-foreground group-hover:text-primary transition-colors">
          {op.sample ? <Redacted kind="name" /> : op.name}
        </p>
        {/* LM2 — fiducia subito: rating medio + numero recensioni */}
        {op.rating?.count > 0 && (
          <p className="mt-0.5 flex items-center gap-1.5">
            <Stars value={op.rating.avg} />
            <span className="text-[11px] text-muted-foreground">
              {Number(op.rating.avg).toFixed(1)} · {t('landings:operators.reviewCount', {
                count: op.rating.count,
                defaultValue: op.rating.count === 1 ? '1 recensione' : '{{count}} recensioni',
              })}
            </span>
          </p>
        )}
        {/* AN3 — posizione dal profilo + distanza quando c'è un punto */}
        {(op.city || op.region || op.distance_km != null) && (
          <p className="text-[11px] text-muted-foreground mt-0.5">
            <MapPin className="h-3 w-3 inline-block mr-0.5 align-[-1px]" aria-hidden />{[op.city, op.region].filter(Boolean).join(', ')}
            {op.distance_km != null && (
              <span className="ml-1.5 rounded-full bg-primary/10 text-primary px-2 py-0.5 font-semibold">
                {op.distance_km} km
              </span>
            )}
          </p>
        )}
        {op.sample ? (
          <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
            <Redacted kind="text" />
          </p>
        ) : op.bio ? (
          <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{op.bio}</p>
        ) : null}
        <div className="mt-2 flex flex-wrap gap-1.5">
          {(op.categories || []).slice(0, 3).map(c => (
            <span key={c} className="rounded-full bg-secondary px-2 py-0.5 text-[11px] text-secondary-foreground">
              {t(`landings:categories.${c}`, { defaultValue: c })}
            </span>
          ))}
        </div>
        <p className="mt-2 text-xs text-muted-foreground">
          {op.upcoming_retreats > 0 && (
            t('landings:operators.retreatCount', {
              count: op.upcoming_retreats,
              defaultValue: '{{count}} ritiri in programma',
            })
          )}
          {op.upcoming_retreats > 0 && op.other_products > 0 && ' · '}
          {op.other_products > 0 && (
            t('landings:operators.productCount', {
              count: op.other_products,
              defaultValue: '{{count}} esperienze e prodotti',
            })
          )}
        </p>
        {/* LM2 — 'da X euro · N servizi': il prezzo di partenza del listino */}
        {op.services_count > 0 && (
          <p className="mt-1 text-xs font-semibold text-[#376254]">
            {op.price_from != null && (
              <>{t('landings:operators.priceFrom', {
                price: Number(op.price_from).toFixed(0),
                defaultValue: 'da {{price}} euro',
              })} · </>
            )}
            {t('landings:operators.serviceCount', {
              count: op.services_count,
              defaultValue: op.services_count === 1 ? '1 servizio' : '{{count}} servizi',
            })}
          </p>
        )}
      </div>
    </Link>
    {/* LM2 — vista rapida: i primi servizi a listino senza cambiare
        pagina; l'acquisto vero resta sul profilo (PN3) */}
    {!op.sample && preview.length > 0 && (
      <div className="px-4 pb-4 mt-auto">
        <button
          type="button"
          aria-expanded={quickOpen}
          data-testid="operator-quick-view"
          onClick={() => setQuickOpen(v => !v)}
          className={`w-full rounded-full px-4 py-1.5 text-xs font-semibold transition-colors ${
            quickOpen
              ? 'border border-[#376254] text-[#376254] bg-white hover:bg-gray-50'
              : 'bg-secondary text-secondary-foreground hover:bg-[#376254]/15'
          }`}
        >
          {quickOpen
            ? t('landings:operators.quickViewClose', { defaultValue: 'Chiudi anteprima' })
            : t('landings:operators.quickView', { defaultValue: 'Vista rapida' })}
        </button>
        {quickOpen && (
          <div className="mt-2 rounded-xl border border-border bg-white divide-y divide-gray-100">
            {preview.map((row) => (
              <div key={row.name} className="flex items-center gap-2 px-3 py-2">
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-medium text-gray-900 truncate">{row.name}</p>
                  {row.duration_minutes ? (
                    <p className="text-[11px] text-gray-500">{row.duration_minutes} min</p>
                  ) : null}
                </div>
                <span className="text-xs font-semibold text-gray-900 whitespace-nowrap">
                  {row.on_request
                    ? t('landings:operator.priceOnRequest', { defaultValue: 'Su richiesta' })
                    : (row.price != null ? `${Number(row.price).toFixed(0)} €` : '')}
                </span>
              </div>
            ))}
            <Link
              to={`/o/${op.org_slug}`}
              className="block px-3 py-2 text-center text-xs font-semibold text-[#376254] hover:bg-gray-50"
            >
              {t('landings:operators.goToProfile', { defaultValue: 'Vai al profilo' })}
            </Link>
          </div>
        )}
      </div>
    )}
    </div>
  );
}

export default function OperatorsIndexPage() {
  const { t, i18n } = useTranslation('landings');
  const { categoria } = useParams();
  // PN/LM — anteprima pubblica non linkata: la stessa pagina risponde
  // anche su /esplora-operatori (il menu resta sulla pagina rete)
  const basePath = window.location.pathname.startsWith('/esplora-operatori')
    ? '/esplora-operatori' : '/operatori';
  const navigate = useNavigate();
  // OP4 — le bio degli operatori parlano la lingua attiva (refetch al cambio)
  const uiLang = (i18n.language || 'it').slice(0, 2);
  const [params, setParams] = useSearchParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  // AN3 — scoperta geografica: ?lat/lng/r/luogo condivisibili come
  // sulla directory ritiri, + toggle ?vista=mappa
  const geoLat = params.get('lat');
  const geoLng = params.get('lng');
  const geoRadius = Number(params.get('r')) || 100;
  const geoLabel = params.get('luogo') || '';
  const view = params.get('vista') || 'lista';
  const geoValue = (geoLat && geoLng)
    ? { lat: Number(geoLat), lng: Number(geoLng), label: geoLabel, radius: geoRadius }
    : null;
  // LM3 — ?ordina= in URL (condivisibile); default: distanza con geo
  // attivo, valutazione altrimenti (lo stesso default del backend)
  const ordina = params.get('ordina') || '';
  const defaultOrdina = geoValue ? 'distanza' : 'valutazione';
  const effectiveOrdina = SORT_PARAM[ordina] ? ordina : defaultOrdina;

  const setGeo = (next) => {
    const q = new URLSearchParams(params);
    if (next) {
      q.set('lat', next.lat); q.set('lng', next.lng);
      q.set('r', next.radius || 100); q.set('luogo', next.label || '');
    } else {
      q.delete('lat'); q.delete('lng'); q.delete('r'); q.delete('luogo');
      // senza geo l'ordinamento per distanza non ha più senso
      if (q.get('ordina') === 'distanza') q.delete('ordina');
    }
    setParams(q, { replace: true });
  };

  const setOrdina = (next) => {
    const q = new URLSearchParams(params);
    if (!next || next === defaultOrdina) q.delete('ordina');
    else q.set('ordina', next);
    setParams(q, { replace: true });
  };

  // LM3 — "Cosa": la categoria resta un segmento di path indicizzabile
  // (/operatori/yoga); i filtri in query string sopravvivono al cambio
  const setCosa = (next) => {
    navigate({
      pathname: next ? `${basePath}/${next}` : basePath,
      search: params.toString() ? `?${params.toString()}` : '',
    }, { replace: true });
  };

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    const q = categoria ? { category: categoria } : {};
    if (geoLat && geoLng) {
      q.lat = geoLat; q.lng = geoLng; q.radius_km = geoRadius;
    }
    // LM3 — ordinamento esplicito solo se l'utente l'ha scelto: il
    // default (distance con geo, rating senza) lo applica il backend
    if (SORT_PARAM[ordina]) q.sort = SORT_PARAM[ordina];
    if (uiLang !== 'it') q.lang = uiLang;
    api.get('/public/operators', { params: q })
      .then(res => { if (mounted) setData(res.data); })
      .catch(() => { if (mounted) setData({ items: [], total: 0, categories: {} }); })
      .finally(() => { if (mounted) setLoading(false); });
    return () => { mounted = false; };
  }, [categoria, geoLat, geoLng, geoRadius, ordina, uiLang]);

  const items = data?.items || [];
  const categories = useMemo(
    () => Object.entries(data?.categories || {}).sort((a, b) => b[1] - a[1]),
    [data],
  );

  const catLabel = categoria
    ? t(`landings:categories.${categoria}`, { defaultValue: categoria }) : '';

  useSeoMeta({
    title: categoria
      ? t('landings:operators.seoTitleCat', {
          cat: catLabel, defaultValue: 'Operatori di {{cat}} | Aurya' })
      : t('landings:operators.seoTitle', {
          defaultValue: 'Tutti gli organizzatori di ritiri ed esperienze | Aurya' }),
    description: t('landings:operators.seoDesc', {
      defaultValue: 'Scopri gli organizzatori di ritiri ed esperienze olistiche su Aurya: profili, prossime date e prenotazione online con caparra.',
    }),
    canonicalPath: categoria ? `/operatori/${categoria}` : '/operatori',
    // 0 risultati = pagina indice vuota: mai in SERP (regola S5)
    noindex: !loading && items.length === 0,
    jsonLd: items.length > 0 ? {
      '@context': 'https://schema.org',
      '@type': 'ItemList',
      itemListElement: items.slice(0, 20).map((op, i) => ({
        '@type': 'ListItem',
        position: i + 1,
        item: {
          '@type': 'Organization',
          name: op.name,
          url: `${window.location.origin}/o/${op.org_slug}`,
        },
      })),
    } : undefined,
  });

  return (
    <MarketplaceShell>
      <PrelaunchBanner audience="operator" />
      <header className="relative text-white overflow-hidden">
        {/* le mani in mudra del founder: chi organizza è il volto della pagina */}
        <img aria-hidden src="/media/hero-organizer.webp" alt="" fetchpriority="high"
             className="absolute inset-0 w-full h-full object-cover" />
        {/* velatura salvia più densa a sinistra, dove vive il testo */}
        <div aria-hidden className="absolute inset-0 pointer-events-none bg-gradient-to-r from-[#14231d]/90 via-[#14231d]/65 to-[#14231d]/35" />
        <div className="relative max-w-6xl mx-auto px-4 pt-12 pb-8 md:pt-16 md:pb-12">
          <nav className="text-xs text-white/70 mb-3">
            <Link to="/" className="hover:text-white hover:underline">Aurya</Link>
            <span className="mx-1.5">›</span>
            {categoria ? (
              <>
                <Link to="/operatori" className="hover:text-white hover:underline">
                  {t('landings:operators.heading', { defaultValue: 'Organizzatori' })}
                </Link>
                <span className="mx-1.5">›</span>
                <span className="text-white">{catLabel}</span>
              </>
            ) : (
              <span className="text-white">
                {t('landings:operators.heading', { defaultValue: 'Organizzatori' })}
              </span>
            )}
          </nav>
          <p aria-hidden className="font-brand uppercase tracking-[0.35em] text-xs md:text-sm text-[#ecd9a8] mb-2 select-none text-hero-shadow">Connect · Heal · Grow</p>
          <h1 className="font-display text-3xl md:text-5xl font-semibold text-hero-shadow">
            {categoria
              ? t('landings:operators.headingCat', {
                  cat: catLabel, defaultValue: 'Organizzatori di {{cat}}' })
              : t('landings:operators.heading', { defaultValue: 'Organizzatori' })}
          </h1>
          <p className="mt-2.5 text-white/90 max-w-2xl text-hero-shadow">
            {t('landings:operators.subtitle', {
              defaultValue: 'Le persone e i centri dietro i ritiri: scopri chi organizza, cosa propone e prenota direttamente online.',
            })}
          </p>

        </div>
      </header>

      {/* LM3 — barra di ricerca Treatwell: Dove / Cosa / Ordina in una
          barra unica sticky subito sotto l'header dello shell (h-14 →
          top-14). L'URL resta la fonte di verità: lat/lng/r/luogo,
          /operatori/{categoria} e ?ordina= sopravvivono a refresh e
          condivisione. Su mobile la barra va a capo: Dove a tutta
          larghezza, Cosa/Ordina/Mappa sulla riga sotto. */}
      <div
        data-testid="operators-search-bar"
        className="sticky top-14 z-30 border-b border-gray-200 bg-white/95 backdrop-blur shadow-sm"
      >
        <div className="max-w-6xl mx-auto px-4 py-2.5 flex flex-wrap items-center gap-2">
          {/* Dove — GeoSearchBar (autocomplete + vicino a me + raggio) */}
          <div className="w-full lg:w-auto lg:flex-1 lg:min-w-[280px]">
            <GeoSearchBar value={geoValue} onChange={setGeo} fluid />
          </div>
          {/* Cosa — categorie reali (listino + ritiri) da data.categories */}
          <select
            value={categoria || ''}
            onChange={(e) => setCosa(e.target.value)}
            aria-label={t('landings:operators.whatLabel', { defaultValue: 'Cosa cerchi?' })}
            className="flex-1 lg:flex-none min-w-0 lg:w-48 rounded-full border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 focus:border-primary focus:outline-none"
          >
            <option value="">
              {t('landings:operators.whatAll', { defaultValue: 'Tutti i servizi' })}
            </option>
            {categories.map(([key, count]) => (
              <option key={key} value={key}>
                {t(`landings:categories.${key}`, { defaultValue: key })} ({count})
              </option>
            ))}
          </select>
          {/* Ordina — Distanza solo con geo attivo (come il backend) */}
          <label className="flex-1 lg:flex-none flex items-center gap-1.5 min-w-0">
            <span className="hidden md:inline text-xs text-gray-500 whitespace-nowrap">
              {t('landings:operators.sortLabel', { defaultValue: 'Ordina per' })}
            </span>
            <select
              value={effectiveOrdina}
              onChange={(e) => setOrdina(e.target.value)}
              aria-label={t('landings:operators.sortLabel', { defaultValue: 'Ordina per' })}
              className="flex-1 lg:flex-none min-w-0 lg:w-36 rounded-full border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 focus:border-primary focus:outline-none"
            >
              {geoValue && (
                <option value="distanza">
                  {t('landings:operators.sortDistance', { defaultValue: 'Distanza' })}
                </option>
              )}
              <option value="valutazione">
                {t('landings:operators.sortRating', { defaultValue: 'Valutazione' })}
              </option>
              <option value="prezzo">
                {t('landings:operators.sortPrice', { defaultValue: 'Prezzo (da)' })}
              </option>
            </select>
          </label>
          {/* AN3 — vista mappa, invariata (?vista=mappa) */}
          <button
            type="button"
            onClick={() => {
              const q = new URLSearchParams(params);
              if (view === 'mappa') q.delete('vista'); else q.set('vista', 'mappa');
              setParams(q, { replace: true });
            }}
            aria-pressed={view === 'mappa'}
            className={`rounded-full px-4 py-1.5 text-sm font-medium border transition-colors ${
              view === 'mappa'
                ? 'bg-[#376254] border-[#376254] text-white shadow'
                : 'bg-white border-gray-300 text-gray-700 hover:border-primary hover:text-primary'
            }`}
          >
            {t('landings:operators.mapToggle', { defaultValue: 'Mappa' })}
          </button>
        </div>
      </div>

      <main className="max-w-6xl mx-auto px-4 py-8">
        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {[1, 2, 3].map(i => (
              <div key={i} className="rounded-2xl border border-border bg-card h-52 animate-pulse" />
            ))}
          </div>
        ) : items.length === 0 ? (
          <div className="text-center py-20 max-w-md mx-auto">
            <img src="/logo-aurya-128.png" alt="" aria-hidden className="mx-auto h-14 w-14 opacity-80" />
            <p className="mt-3 text-lg font-semibold text-foreground">
              {t('landings:operators.emptyTitle', { defaultValue: 'Nessun organizzatore qui, per ora' })}
            </p>
            <p className="text-muted-foreground mt-1">
              {t('landings:operators.emptyBody', { defaultValue: 'Prova un\'altra categoria o torna alla directory dei ritiri.' })}
            </p>
            <Link to="/" className="mt-4 inline-block rounded-full bg-primary text-white px-5 py-2 text-sm font-semibold">
              {t('landings:operators.backHome', { defaultValue: 'Vai ai ritiri' })}
            </Link>
          </div>
        ) : view === 'mappa' ? (
          <React.Suspense fallback={<div className="h-[520px] rounded-2xl bg-gray-100 animate-pulse" />}>
            <OperatorsMapView items={items} />
          </React.Suspense>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {items.map(op => <OperatorCard key={op.org_slug} op={op} t={t} />)}
          </div>
        )}
      </main>
    </MarketplaceShell>
  );
}
