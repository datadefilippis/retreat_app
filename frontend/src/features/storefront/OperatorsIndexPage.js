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
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import api from '../../api/client';
import MarketplaceShell from './components/MarketplaceShell';
import GeoSearchBar from './components/GeoSearchBar';
import useSeoMeta from './lib/useSeoMeta';

const OperatorsMapView = React.lazy(() => import('./components/OperatorsMapView'));

import { Leaf, MapPin } from 'lucide-react';
import { CategoryIcon } from './lib/categoryIcons';

function OperatorCard({ op, t }) {
  return (
    <Link
      to={`/o/${op.org_slug}`}
      className="group rounded-2xl border border-border bg-card overflow-hidden hover:shadow-lg transition-shadow"
    >
      <div className="h-24 bg-gradient-to-br from-primary/15 to-secondary relative">
        {op.cover_url && (
          <img src={op.cover_url} alt="" className="w-full h-full object-cover" loading="lazy" />
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
        <p className="font-semibold text-foreground group-hover:text-primary transition-colors">{op.name}</p>
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
        {op.bio && (
          <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{op.bio}</p>
        )}
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
      </div>
    </Link>
  );
}

export default function OperatorsIndexPage() {
  const { t, i18n } = useTranslation('landings');
  const { categoria } = useParams();
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
  const setGeo = (next) => {
    const q = new URLSearchParams(params);
    if (next) {
      q.set('lat', next.lat); q.set('lng', next.lng);
      q.set('r', next.radius || 100); q.set('luogo', next.label || '');
    } else {
      q.delete('lat'); q.delete('lng'); q.delete('r'); q.delete('luogo');
    }
    setParams(q, { replace: true });
  };

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    const q = categoria ? { category: categoria } : {};
    if (geoLat && geoLng) {
      q.lat = geoLat; q.lng = geoLng; q.radius_km = geoRadius;
    }
    if (uiLang !== 'it') q.lang = uiLang;
    api.get('/public/operators', { params: q })
      .then(res => { if (mounted) setData(res.data); })
      .catch(() => { if (mounted) setData({ items: [], total: 0, categories: {} }); })
      .finally(() => { if (mounted) setLoading(false); });
    return () => { mounted = false; };
  }, [categoria, geoLat, geoLng, geoRadius, uiLang]);

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

          {categories.length > 0 && (
            <div className="mt-5 flex flex-wrap gap-2">
              <Link
                to="/operatori"
                className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors backdrop-blur-sm ${
                  !categoria ? 'bg-white text-gray-900 shadow-lg' : 'bg-black/25 border border-white/25 text-white hover:bg-black/40'
                }`}
              >
                {t('landings:calendar.allCategories', { defaultValue: 'Tutte' })}
              </Link>
              {categories.map(([key, count]) => (
                <Link
                  key={key}
                  to={`/operatori/${key}`}
                  className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors backdrop-blur-sm ${
                    categoria === key ? 'bg-white text-gray-900 shadow-lg' : 'bg-black/25 border border-white/25 text-white hover:bg-black/40'
                  }`}
                >
                  <CategoryIcon category={key} className="h-3.5 w-3.5 mr-1 inline-block align-[-2px]" />
                  {t(`landings:categories.${key}`, { defaultValue: key })}
                  <span className="ml-1 text-xs opacity-70">({count})</span>
                </Link>
              ))}
            </div>
          )}

          {/* AN3 — Dove? + vicino a me + vista mappa */}
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <div className="w-full sm:w-80"><GeoSearchBar value={geoValue} onChange={setGeo} /></div>
            <button
              type="button"
              onClick={() => {
                const q = new URLSearchParams(params);
                if (view === 'mappa') q.delete('vista'); else q.set('vista', 'mappa');
                setParams(q, { replace: true });
              }}
              className={`rounded-full px-4 py-1.5 text-sm font-medium border transition-colors backdrop-blur-sm ${
                view === 'mappa' ? 'bg-white text-gray-900 border-white shadow-lg' : 'bg-black/25 border-white/25 text-white hover:bg-black/40'
              }`}
            >
              {t('landings:operators.mapToggle', { defaultValue: 'Mappa' })}
            </button>
          </div>
        </div>
      </header>

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
