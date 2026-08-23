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

import { Leaf, MapPin, SearchX } from 'lucide-react';
import { Skeleton } from '../../components/ui/skeleton';
import VerifiedAuryaBadge from '../../components/VerifiedAuryaBadge';
// DI — tassonomia discipline (specchio backend)
import { disciplineLabel, DISCIPLINE_FAMILIES } from '../../lib/disciplines';
import BrandPayoff from '../../components/BrandPayoff';

// LM3 — l'URL parla italiano (?ordina=), l'API il gergo suo (sort=):
// la mappa e' l'unico punto di traduzione.
const SORT_PARAM = { distanza: 'distance', valutazione: 'rating', prezzo: 'price' };

// LM4 — "Quando": ?quando=YYYY-MM-DD (+ ?fascia=) in URL; l'API riceve
// date/time_from/time_to. Le fasce sono un vocabolario umano fisso.
const FASCIA_PARAM = {
  mattina: ['06:00', '12:00'],
  pomeriggio: ['12:00', '18:00'],
  sera: ['18:00', '23:59'],
};

// LM4 — "Primo posto: gio 30 lug, 14:00" dal next_available dell'indice
function formatNextAvailable(na, lang) {
  try {
    const day = new Date(`${na.date}T00:00:00`).toLocaleDateString(
      lang || 'it', { weekday: 'short', day: 'numeric', month: 'short' });
    return `${day}, ${na.first_slot}`;
  } catch {
    return `${na.date} ${na.first_slot}`;
  }
}

// LM2 — stelle piene/vuote sul rating medio (stesso disegno del profilo)
function Stars({ value }) {
  const full = Math.round(value || 0);
  return (
    <span className="text-sm tracking-tight" aria-label={`${value} su 5`}>
      <span className="text-amber-500">{'★'.repeat(full)}</span>
      <span className="text-gray-300">{'★'.repeat(5 - full)}</span>
    </span>
  );
}

// LM5 — scheletro della card: stessa geometria (cover 16/9, avatar,
// righe di testo) al posto del flash vuoto durante il fetch
function OperatorCardSkeleton() {
  return (
    <div
      data-testid="operator-card-skeleton"
      className="rounded-2xl border border-border bg-card overflow-hidden"
    >
      <Skeleton className="aspect-[16/9] w-full rounded-none" />
      <div className="relative px-4 pb-4 pt-9">
        <div className="absolute -top-7 left-4 h-14 w-14 rounded-full border-2 border-white bg-white shadow overflow-hidden">
          <Skeleton className="h-full w-full rounded-full" />
        </div>
        <Skeleton className="h-4 w-2/3" />
        <Skeleton className="mt-2 h-3 w-2/5" />
        <Skeleton className="mt-3 h-3 w-full" />
        <Skeleton className="mt-1.5 h-3 w-5/6" />
        <div className="mt-3 flex gap-1.5">
          <Skeleton className="h-5 w-16 rounded-full" />
          <Skeleton className="h-5 w-14 rounded-full" />
        </div>
        <Skeleton className="mt-4 h-3.5 w-1/2" />
      </div>
    </div>
  );
}

function OperatorCard({ op, t, lang }) {
  // LM2 — vista rapida: anteprima listino IN CARD (pattern PN3,
  // aria-expanded); il click sulla card resta il link al profilo.
  const [quickOpen, setQuickOpen] = useState(false);
  const preview = op.listino_preview || [];
  return (
    <div className={`group rounded-2xl border border-border bg-card overflow-hidden shadow-sm hover:shadow-lg transition-shadow duration-300 flex flex-col ${op.sample ? 'pointer-events-none select-none' : ''}`}>
    <Link
      to={op.sample ? '#' : `/o/${op.org_slug}`}
      onClick={op.sample ? (e) => e.preventDefault() : undefined}
      className="block"
    >
      {/* LM5 — la foto è la protagonista: cover 16/9 con zoom morbido */}
      <div className="aspect-[16/9] bg-gradient-to-br from-primary/15 to-secondary relative overflow-hidden">
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
               className={`w-full h-full object-cover transition-transform duration-500 group-hover:scale-[1.04] ${op.sample ? 'blur-[3px] scale-105' : ''}`}
               loading="lazy" />
        )}
        {/* PV4+GT3 — pillole di fiducia sulla cover: Verificato Aurya
            PRIMA di In evidenza (ordine fisso ovunque); sm = glifo +
            "Verificato" corto, la card mobile non si affolla */}
        {(op.verified || op.featured) && (
          <div className="absolute top-2.5 right-2.5 flex items-center gap-1.5">
            {op.verified && (
              <VerifiedAuryaBadge variant="on-light" size="sm" className="shadow" />
            )}
            {op.featured && (
              <span className="rounded-full bg-[#376254] text-white px-2.5 py-1 text-[11px] font-semibold shadow">
                ✦ {t('landings:calendar.featured', { defaultValue: 'In evidenza' })}
              </span>
            )}
          </div>
        )}
        <div className="absolute bottom-2.5 left-3 h-14 w-14 rounded-full border-2 border-white bg-white shadow-md overflow-hidden flex items-center justify-center">
          {op.logo_url
            ? <img src={op.logo_url} alt="" className="h-full w-full object-cover" loading="lazy" />
            : <Leaf className="h-6 w-6 text-[#376254]/50" aria-hidden />}
        </div>
      </div>
      <div className="pt-3.5 px-4 pb-4">
        {/* LM5 — gerarchia: nome grande, fiducia subito sotto, poi il resto */}
        {/* PL9 — nome campione: segnaposto sfocato, mai il nome finto */}
        <p className="text-base leading-snug font-semibold text-foreground group-hover:text-primary transition-colors line-clamp-1">
          {op.sample ? <Redacted kind="name" /> : op.name}
        </p>
        {/* LM2 — fiducia subito: rating medio + numero recensioni */}
        {op.rating?.count > 0 && (
          <p className="mt-1 flex items-center gap-1.5">
            <span className="text-sm font-bold text-foreground">
              {Number(op.rating.avg).toFixed(1)}
            </span>
            <Stars value={op.rating.avg} />
            <span className="text-xs text-muted-foreground">
              {t('landings:operators.reviewCount', {
                count: op.rating.count,
                defaultValue: op.rating.count === 1 ? '1 recensione' : '{{count}} recensioni',
              })}
            </span>
          </p>
        )}
        {/* AN3 — posizione dal profilo + distanza quando c'è un punto */}
        {(op.city || op.region || op.distance_km != null) && (
          <p className="text-xs text-muted-foreground mt-1">
            <MapPin className="h-3 w-3 inline-block mr-0.5 align-[-1px]" aria-hidden />{[op.city, op.region].filter(Boolean).join(', ')}
            {op.distance_km != null && (
              <span className="ml-1.5 rounded-full bg-primary/10 text-primary px-2 py-0.5 text-[11px] font-semibold">
                {op.distance_km} km
              </span>
            )}
          </p>
        )}
        {op.sample ? (
          <p className="text-xs text-muted-foreground mt-1.5 line-clamp-2">
            <Redacted kind="text" />
          </p>
        ) : op.bio ? (
          <p className="text-xs leading-relaxed text-muted-foreground mt-1.5 line-clamp-2">{op.bio}</p>
        ) : null}
        {/* LM5 — chip categorie discrete: piccole, tono su tono */}
        <div className="mt-2.5 flex flex-wrap gap-1.5">
          {(op.categories || []).slice(0, 3).map(c => (
            <span key={c} className="rounded-full bg-secondary/70 px-2 py-0.5 text-[11px] text-secondary-foreground/90">
              {t(`landings:categories.${c}`, { defaultValue: c })}
            </span>
          ))}
          {/* DI — discipline dichiarate: chip nel verde del brand */}
          {(op.disciplines || []).slice(0, 3).map(d => (
            <span key={d} className="rounded-full bg-[#376254]/10 px-2 py-0.5 text-[11px] text-[#376254]">
              {disciplineLabel(d)}
            </span>
          ))}
        </div>
        {(op.upcoming_retreats > 0 || op.other_products > 0) && (
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
        )}
        {/* LM2+LM5 — riga prezzo/servizi ben separata e leggibile */}
        {op.services_count > 0 && (
          <p className="mt-2.5 pt-2.5 border-t border-border/70 text-sm font-semibold text-[#376254]">
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
        {/* LM4 — primo posto libero dall'indice disponibilita': pill verde */}
        {!op.sample && op.next_available && (
          <p className="mt-2">
            <span
              data-testid="operator-next-available"
              className="inline-block rounded-full bg-[#376254]/10 text-[#376254] px-2.5 py-1 text-[11px] font-semibold"
            >
              {t('landings:operators.nextAvailable', {
                when: formatNextAvailable(op.next_available, lang),
                defaultValue: 'Primo posto: {{when}}',
              })}
            </span>
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
        {/* LM5 — apertura morbida: griglia 0fr→1fr, niente scatti */}
        <div
          className={`grid transition-all duration-300 ease-in-out ${
            quickOpen ? 'grid-rows-[1fr] opacity-100 mt-2' : 'grid-rows-[0fr] opacity-0 mt-0'
          }`}
          aria-hidden={!quickOpen}
        >
          <div className="overflow-hidden">
            <div className="rounded-xl border border-border bg-white divide-y divide-gray-100">
              {/* PV4 — il sigillo anche nella vista rapida (on-light) */}
              {op.verified && (
                <div className="px-3 py-2">
                  <VerifiedAuryaBadge variant="on-light" size="sm" />
                </div>
              )}
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
                tabIndex={quickOpen ? 0 : -1}
                className="block px-3 py-2 text-center text-xs font-semibold text-[#376254] hover:bg-gray-50"
              >
                {t('landings:operators.goToProfile', { defaultValue: 'Vai al profilo' })}
              </Link>
            </div>
          </div>
        </div>
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
  // PN — su /esplora-operatori l'anteprima e' VERA: preview=1 al
  // backend (bypass PL8, operatori reali come al lancio) e noindex
  // (rotta non linkata, mai in SERP prima del lancio).
  const isPreview = basePath === '/esplora-operatori';
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
  // LM4 — "Quando" in URL (?quando=YYYY-MM-DD, ?fascia=mattina|...)
  const quando = params.get('quando') || '';
  // DI — filtro per disciplina dichiarata (query string, no path)
  const disciplina = params.get('disciplina') || '';
  const fascia = params.get('fascia') || '';

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

  // LM4 — Quando: la data guida, la fascia e' un raffinamento che non
  // vive da sola (senza data si spegne anche lei)
  const setQuando = (next) => {
    const q = new URLSearchParams(params);
    if (next) q.set('quando', next);
    else { q.delete('quando'); q.delete('fascia'); }
    setParams(q, { replace: true });
  };
  const setFascia = (next) => {
    const q = new URLSearchParams(params);
    if (next && FASCIA_PARAM[next]) q.set('fascia', next);
    else q.delete('fascia');
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
    // LM4 — Quando: data + fascia mappata su time_from/time_to
    if (quando) {
      q.date = quando;
      const banda = FASCIA_PARAM[fascia];
      if (banda) { q.time_from = banda[0]; q.time_to = banda[1]; }
    }
    if (disciplina) q.discipline = disciplina;   // DI
    if (uiLang !== 'it') q.lang = uiLang;
    if (isPreview) q.preview = 1;   // PN — dati veri sulla rotta esplora
    api.get('/public/operators', { params: q })
      .then(res => { if (mounted) setData(res.data); })
      .catch(() => { if (mounted) setData({ items: [], total: 0, categories: {} }); })
      .finally(() => { if (mounted) setLoading(false); });
    return () => { mounted = false; };
  }, [categoria, geoLat, geoLng, geoRadius, ordina, quando, fascia, disciplina, uiLang, isPreview]);

  const items = data?.items || [];
  const categories = useMemo(
    () => Object.entries(data?.categories || {}).sort((a, b) => b[1] - a[1]),
    [data],
  );
  // DI — discipline presenti tra gli operatori (slug -> conteggio):
  // il select mostra solo voci con contenuto, come le categorie
  const disciplines = useMemo(
    () => Object.entries(data?.disciplines || {}).sort((a, b) => b[1] - a[1]),
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
    // 0 risultati = pagina indice vuota: mai in SERP (regola S5).
    // PN — la rotta /esplora-operatori e' un'anteprima non linkata:
    // noindex sempre, qualunque sia il contenuto.
    noindex: isPreview || (!loading && items.length === 0),
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
    /* noSearch (23/8, founder): questa E' una directory, coi suoi
       filtri sotto. La scorciatoia "Dove? · Quando? · Che ritiro?"
       nella barra del menu rimandava altrove (la home dei ritiri) e
       si confondeva coi filtri veri della pagina. Stessa scelta gia'
       fatta sul calendario ritiri. */
    <MarketplaceShell noSearch>
      {/* PN — sulla rotta anteprima i dati sono VERI: niente banner
          "d'esempio" (su /operatori marketplace si spegne da solo) */}
      {!isPreview && <PrelaunchBanner audience="operator" />}
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
          <BrandPayoff tone="hero" size="sm" className="mb-2" />
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
        {/* LM5 — su mobile (375px) la barra collassa ordinata: Dove a
            tutta larghezza sopra, il resto in UNA riga scrollabile
            (scrollbar-hide); da lg tutto su una riga sola. */}
        <div className="max-w-6xl mx-auto px-4 py-2.5 flex flex-col lg:flex-row lg:items-center gap-2 lg:gap-2.5">
          {/* Dove — GeoSearchBar (autocomplete + vicino a me + raggio) */}
          <div className="w-full lg:w-auto lg:flex-1 lg:min-w-[280px]">
            <GeoSearchBar value={geoValue} onChange={setGeo} fluid />
          </div>
          <div className="flex w-full lg:w-auto items-center gap-2 lg:gap-2.5 overflow-x-auto scrollbar-hide -mx-4 px-4 lg:mx-0 lg:px-0 lg:overflow-visible">
            {/* DI5 (founder 14/8) — Disciplina user-friendly: SOLO le
                voci con almeno un operatore (conteggio accanto),
                raggruppate per famiglia. Niente catalogo intero che
                "non filtra nulla"; senza discipline dichiarate il
                select non compare. */}
            {(disciplines.length > 0 || disciplina) && (
              <select
                value={disciplina}
                onChange={(e) => {
                  const q = new URLSearchParams(params);
                  if (e.target.value) q.set('disciplina', e.target.value);
                  else q.delete('disciplina');
                  setParams(q, { replace: true });
                }}
                aria-label={t('landings:operators.disciplineLabel', { defaultValue: 'Disciplina' })}
                data-testid="operators-discipline-filter"
                className="flex-none w-44 lg:w-52 rounded-full border border-gray-300 bg-white px-3.5 py-1.5 text-sm text-gray-700 focus:border-primary focus:outline-none"
              >
                <option value="">
                  {t('landings:operators.disciplineAll', { defaultValue: 'Tutte le discipline' })}
                </option>
                {DISCIPLINE_FAMILIES.map(fam => {
                  const presenti = fam.items.filter(
                    d => data?.disciplines?.[d.slug] || d.slug === disciplina);
                  if (presenti.length === 0) return null;
                  return (
                    <optgroup key={fam.slug} label={fam.label}>
                      {presenti.map(d => {
                        const n = data?.disciplines?.[d.slug];
                        return (
                          <option key={d.slug} value={d.slug}>
                            {d.label}{n ? ` (${n})` : ''}
                          </option>
                        );
                      })}
                    </optgroup>
                  );
                })}
              </select>
            )}
            {/* Formato — asse complementare alla Disciplina: la
                disciplina dice COSA pratichi, il formato in che modo
                lo compri (tassonomia service). Opzioni reali da
                data.categories. */}
            <select
              value={categoria || ''}
              onChange={(e) => setCosa(e.target.value)}
              aria-label={t('landings:operators.whatLabel', { defaultValue: 'Formato' })}
              className="flex-none w-40 lg:w-48 rounded-full border border-gray-300 bg-white px-3.5 py-1.5 text-sm text-gray-700 focus:border-primary focus:outline-none"
            >
              <option value="">
                {t('landings:operators.whatAll', { defaultValue: 'Ogni formato' })}
              </option>
              {categories.map(([key, count]) => (
                <option key={key} value={key}>
                  {t(`landings:categories.${key}`, { defaultValue: key })} ({count})
                </option>
              ))}
            </select>
            {/* LM4 — Quando: visibile SOLO se l'indice di disponibilita'
                esiste (date_filter_ready); data nativa + fascia opzionale */}
            {data?.date_filter_ready && (
              <div className="flex flex-none items-center gap-1.5" data-testid="operators-when-filter">
                <span className="hidden xl:inline text-xs text-gray-500 whitespace-nowrap">
                  {t('landings:operators.whenLabel', { defaultValue: 'Quando?' })}
                </span>
                <input
                  type="date"
                  value={quando}
                  min={new Date().toISOString().slice(0, 10)}
                  onChange={(e) => setQuando(e.target.value)}
                  aria-label={t('landings:operators.whenLabel', { defaultValue: 'Quando?' })}
                  className="flex-none w-36 lg:w-40 rounded-full border border-gray-300 bg-white px-3.5 py-1.5 text-sm text-gray-700 focus:border-primary focus:outline-none"
                />
                {quando && (
                  <select
                    value={fascia}
                    onChange={(e) => setFascia(e.target.value)}
                    aria-label={t('landings:operators.whenBandLabel', { defaultValue: 'Fascia oraria' })}
                    className="flex-none w-32 rounded-full border border-gray-300 bg-white px-3.5 py-1.5 text-sm text-gray-700 focus:border-primary focus:outline-none"
                  >
                    <option value="">
                      {t('landings:operators.whenAllDay', { defaultValue: 'Tutto il giorno' })}
                    </option>
                    <option value="mattina">
                      {t('landings:operators.whenMorning', { defaultValue: 'Mattina' })}
                    </option>
                    <option value="pomeriggio">
                      {t('landings:operators.whenAfternoon', { defaultValue: 'Pomeriggio' })}
                    </option>
                    <option value="sera">
                      {t('landings:operators.whenEvening', { defaultValue: 'Sera' })}
                    </option>
                  </select>
                )}
              </div>
            )}
            {/* Ordina — Distanza solo con geo attivo (come il backend) */}
            <label className="flex-none flex items-center gap-1.5">
              <span className="hidden md:inline text-xs text-gray-500 whitespace-nowrap">
                {t('landings:operators.sortLabel', { defaultValue: 'Ordina per' })}
              </span>
              <select
                value={effectiveOrdina}
                onChange={(e) => setOrdina(e.target.value)}
                aria-label={t('landings:operators.sortLabel', { defaultValue: 'Ordina per' })}
                className="flex-none w-36 rounded-full border border-gray-300 bg-white px-3.5 py-1.5 text-sm text-gray-700 focus:border-primary focus:outline-none"
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
              className={`flex-none rounded-full px-4 py-1.5 text-sm font-medium border transition-colors ${
                view === 'mappa'
                  ? 'bg-[#376254] border-[#376254] text-white shadow'
                  : 'bg-white border-gray-300 text-gray-700 hover:border-primary hover:text-primary'
              }`}
            >
              {t('landings:operators.mapToggle', { defaultValue: 'Mappa' })}
            </button>
          </div>
        </div>
      </div>

      <main className="max-w-6xl mx-auto px-4 py-8">
        {loading ? (
          /* LM5 — scheletri con la stessa geometria delle card: niente
             flash vuoto, il layout non salta al termine del fetch */
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {[1, 2, 3, 4, 5, 6].map(i => <OperatorCardSkeleton key={i} />)}
          </div>
        ) : items.length === 0 ? (
          /* LM5 — empty state onesto: dice PERCHE' e suggerisce il
             gesto giusto per il filtro attivo (data, raggio, categoria) */
          <div data-testid="operators-empty" className="text-center py-16 max-w-md mx-auto">
            <div className="mx-auto h-16 w-16 rounded-full bg-secondary flex items-center justify-center">
              <SearchX className="h-7 w-7 text-[#376254]" aria-hidden />
            </div>
            <p className="mt-4 text-lg font-semibold text-foreground">
              {t('landings:operators.emptyTitle', { defaultValue: 'Nessun organizzatore qui, per ora' })}
            </p>
            <p className="text-muted-foreground mt-1.5 text-sm">
              {quando
                ? t('landings:operators.emptySuggestDate', {
                    defaultValue: 'Per quella data non risulta posto libero: prova un altro giorno o togli la data.',
                  })
                : geoValue
                  ? t('landings:operators.emptySuggestRadius', {
                      defaultValue: 'In questa zona non abbiamo ancora organizzatori: allarga il raggio o cambia località.',
                    })
                  : categoria
                    ? t('landings:operators.emptySuggestCategory', {
                        defaultValue: 'Per questa categoria non abbiamo ancora nessuno: prova con tutti i servizi.',
                      })
                    : t('landings:operators.emptyBody', { defaultValue: 'Prova un\'altra categoria o torna alla directory dei ritiri.' })}
            </p>
            <div className="mt-5 flex flex-wrap items-center justify-center gap-2">
              {quando && (
                <button
                  type="button"
                  onClick={() => setQuando('')}
                  className="rounded-full border border-[#376254] text-[#376254] bg-white px-4 py-1.5 text-sm font-semibold hover:bg-[#376254]/5 transition-colors"
                >
                  {t('landings:operators.emptyClearDate', { defaultValue: 'Togli la data' })}
                </button>
              )}
              {geoValue && geoRadius < 250 && (
                <button
                  type="button"
                  onClick={() => setGeo({ ...geoValue, radius: 250 })}
                  className="rounded-full border border-[#376254] text-[#376254] bg-white px-4 py-1.5 text-sm font-semibold hover:bg-[#376254]/5 transition-colors"
                >
                  {t('landings:operators.emptyWidenRadius', { defaultValue: 'Allarga il raggio' })}
                </button>
              )}
              {categoria && (
                <button
                  type="button"
                  onClick={() => setCosa('')}
                  className="rounded-full border border-[#376254] text-[#376254] bg-white px-4 py-1.5 text-sm font-semibold hover:bg-[#376254]/5 transition-colors"
                >
                  {t('landings:operators.emptyAllServices', { defaultValue: 'Ogni formato' })}
                </button>
              )}
              <Link to="/" className="rounded-full bg-primary text-white px-5 py-1.5 text-sm font-semibold hover:opacity-90 transition-opacity">
                {t('landings:operators.backHome', { defaultValue: 'Vai ai ritiri' })}
              </Link>
            </div>
          </div>
        ) : view === 'mappa' ? (
          <React.Suspense fallback={<div className="h-[520px] rounded-2xl bg-gray-100 animate-pulse" />}>
            <OperatorsMapView items={items} />
          </React.Suspense>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {items.map(op => <OperatorCard key={op.org_slug} op={op} t={t} lang={uiLang} />)}
          </div>
        )}
      </main>
    </MarketplaceShell>
  );
}
