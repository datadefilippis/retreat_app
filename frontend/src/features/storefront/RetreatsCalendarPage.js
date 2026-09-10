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
import { trackEvent } from '../../lib/analytics';   // RB13
import { useTranslation } from 'react-i18next';
import api from '../../api/client';
import GeoSearchBar from './components/GeoSearchBar';
import MarketplaceShell from './components/MarketplaceShell';
import Redacted from '../prelaunch/Redacted';
// G3 — vista mappa lazy (Leaflet caricato solo quando serve)
const RetreatsMapView = React.lazy(() => import('./components/RetreatsMapView'));

// G3 — il filtro regioni e' stato sostituito dalla ricerca geografica
// (GeoSearchBar); il param backend `region` resta per i vecchi link SEO.

// DS2 — icone categoria professionali (lucide), mappa unica condivisa.
import { Globe2, CalendarDays } from 'lucide-react';
import { CategoryIcon } from './lib/categoryIcons';
import BrandPayoff from '../../components/BrandPayoff';

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
  // PN (richiesta founder 29/7) — la stessa pagina risponde anche su
  // /esplora-ritiri: anteprima marketplace NON linkata (pattern basePath
  // di OperatorsIndexPage). Li' i dati sono VERI (?preview=1, bypass
  // PL8 lato backend) e la pagina si comporta come in fase marketplace:
  // ricerca, filtri e card piene, niente modalita' PL22.
  // RE (10/9/2026 sera, founder: «riaccendiamo»): il calendario E' la
  // pagina «Ritiri ed esperienze» su /esperienze, in ogni fase. /ritiri
  // ed /esplora-ritiri (l'anteprima non linkata del 29/7) rimandano qui.
  // Le pagine categoria/regione vivono sotto /esperienze e restano fuori
  // dagli indici finche' hanno meno di dieci ritiri (decide il dato).
  const basePath = '/esperienze';
  // PL22 — anteprima ONESTA in pre-lancio (feedback analista): niente
  // ricerca/filtri non funzionanti su dati d'esempio — solo poche card
  // sfocate che raccontano il concept, e le CTA verso le landing lead.
  // RE (10/9/2026): la modalita' «anteprima onesta» del pre-lancio (PL22:
  // banner, sei schede, niente filtri) non vale qui: /esperienze e' la
  // pagina vera, con i ritiri veri, in ogni fase.
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
    q.preview = 1;   // dati veri, sempre (l'anteprima era la regola, ora e' la pagina)
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
  // RE-ter: data.categories = {chiave: {label, count}} SOLO con ritiri
  const catLabel = category ? (data?.categories?.[category]?.label || t(`landings:categories.${category}`, { defaultValue: category })) : '';
  const seoHeading = (() => {
    const bits = ['Ritiri'];
    if (catLabel) bits.push('di ' + catLabel);
    if (region) bits.push('in ' + region);
    return bits.join(' ');
  })();
  const paginaCategoria = Boolean(routeParams.categoria || routeParams.regione);
  useSeoMeta({
    title: paginaCategoria
      ? `${seoHeading} | Aurya`
      : 'Ritiri ed esperienze in programma | Aurya',
    description: paginaCategoria
      ? `Ritiri${catLabel ? ' di ' + catLabel.toLowerCase() : ''}${region ? ' in ' + region : ''} dei professionisti della rete Aurya: date, luoghi, chi li conduce e come si prenota.`
      : 'I ritiri e le esperienze olistiche dei professionisti della rete Aurya, per data: yoga, meditazione, respiro, suono, cammini. Ogni scheda dice chi conduce, dove, quando, il prezzo e come si prenota.',
    canonicalPath: paginaCategoria ? window.location.pathname : '/esperienze',
    // ES (25/8) — la pagina resta fuori dagli indici finche' e' vuota e si
    // accende DA SOLA al primo ritiro (decide il dato). RE (10/9): le pagine
    // categoria/regione si accendono con almeno dieci ritiri, altrimenti
    // sono le pagine sottili chiuse a inizio settembre (IX1).
    noindex: !loading && (data?.items || []).length === 0,
    ...(paginaCategoria ? { noindex: !loading && (data?.items || []).length < 10 } : {}),
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

  return (
    <MarketplaceShell noSearch>
    <div className="bg-background">
      {/* RE-bis (10/9/2026 sera, founder: «lo stesso stile di
          esplora-operatori»): testata compatta con foto ferma e velatura
          a sinistra, briciole, payoff piccolo, titolo, una frase, un link
          discreto; niente video, niente chip nel cielo: i filtri stanno
          nella barra sotto, come nella directory dei professionisti. */}
      <header className="relative text-white overflow-hidden" data-testid="esp-hero">
        {/* founder 10/9 sera: una copertina DIVERSA da quella della home
            (il tramonto sul mare del video), o le due pagine sembrano la
            stessa. Il sole nelle mani: gia' in repo, non usata come hero. */}
        <img aria-hidden src="/media/hero-blog.webp" alt="" fetchpriority="high"
             className="absolute inset-0 w-full h-full object-cover object-[70%_50%]" />
        <div aria-hidden className="absolute inset-0 pointer-events-none bg-gradient-to-r from-[#14231d]/90 via-[#14231d]/65 to-[#14231d]/35" />
        <div className="relative max-w-6xl mx-auto px-4 pt-12 pb-8 md:pt-16 md:pb-12">
          <nav aria-label="breadcrumb" className="text-xs text-white/70 mb-3">
            <Link to="/" className="hover:text-white hover:underline">Aurya</Link>
            <span className="mx-1.5" aria-hidden>›</span>
            {category ? (
              <>
                <Link to={basePath} className="hover:text-white hover:underline">Ritiri ed esperienze</Link>
                <span className="mx-1.5" aria-hidden>›</span>
                {region ? (
                  <>
                    <Link to={`${basePath}/${category}`} className="hover:text-white hover:underline">{catLabel || category}</Link>
                    <span className="mx-1.5" aria-hidden>›</span>
                    <span className="text-white">{region}</span>
                  </>
                ) : <span className="text-white">{catLabel || category}</span>}
              </>
            ) : (
              <span className="text-white">Ritiri ed esperienze</span>
            )}
          </nav>
          <BrandPayoff tone="hero" size="sm" className="mb-2" />
          <h1 className="font-display text-3xl md:text-5xl font-semibold text-hero-shadow" data-testid="esp-title">
            {catLabel || region ? seoHeading : t('landings:calendar.title', { defaultValue: 'I prossimi ritiri ed esperienze.' })}
          </h1>
          <p className="mt-2.5 text-white/90 max-w-2xl text-hero-shadow">
            {t('landings:calendar.subtitle', { defaultValue: 'I ritiri e le esperienze dei professionisti della rete, per data. Ogni scheda dice chi conduce, dove, quando, il prezzo e come si prenota.' })}
          </p>
          <Link to="/entra-nella-rete?porta=esperienze" data-testid="esp-join"
                onClick={() => trackEvent('porta', { porta: 'operatore', da: 'esperienze' })}
                className="mt-3 inline-flex items-center gap-1 text-sm text-white/80 hover:text-white underline-offset-4 hover:underline">
            Organizzi ritiri? Apri il tuo spazio →
          </Link>
        </div>
      </header>

      {/* SEO3 — sulle pagine categoria, le regioni con ritiri come LINK
          crawlabili: i motori raggiungono /esperienze/{cat}/{regione}
          dai link interni, non solo dalla sitemap. */}
      {category && !region && regionsForCategory.length > 0 && (
        <div className="border-b border-border bg-background">
          <div className="max-w-6xl mx-auto px-4 py-2.5 flex flex-wrap items-center gap-2">
            <span className="text-xs font-semibold text-muted-foreground">
              {t('landings:calendar.byRegion', { defaultValue: 'Per regione:' })}
            </span>
            {regionsForCategory.map(rg => (
              <Link key={rg} to={`${basePath}/${category}/${rg}`}
                    className="rounded-full border border-border bg-card px-3 py-1 text-xs font-medium text-foreground hover:border-primary hover:text-primary transition-colors">
                {rg}
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* La barra dei filtri: la stessa della directory dei professionisti
          (Dove a tutta larghezza su mobile, il resto in una riga
          scrollabile; da lg una riga sola). L'URL resta la verita'. */}
      {<div data-testid="esp-search-bar" className="sticky top-14 z-30 border-b border-gray-200 bg-white/95 backdrop-blur shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-2.5 flex flex-col lg:flex-row lg:items-center gap-2 lg:gap-2.5">
          <div className="w-full lg:w-auto lg:flex-1 lg:min-w-[280px]">
            <GeoSearchBar value={geoValue} onChange={setGeo} fluid />
          </div>
          <div className="flex w-full lg:w-auto items-center gap-2 lg:gap-2.5 overflow-x-auto scrollbar-hide -mx-4 px-4 lg:mx-0 lg:px-0 lg:overflow-visible">
            <select
              value={category}
              onChange={e => (routeParams.categoria
                ? navigate(e.target.value ? `${basePath}/${e.target.value}` : basePath)
                : setFilter('categoria', e.target.value))}
              aria-label={t('landings:calendar.allCategories')}
              data-testid="esp-f-categoria"
              className="flex-none w-44 lg:w-52 rounded-full border border-gray-300 bg-white px-3.5 py-1.5 text-sm text-gray-700 focus:border-primary focus:outline-none"
            >
              <option value="">{t('landings:calendar.allCategories')}</option>
              {categories.map(([key, info]) => (
                <option key={key} value={key}>
                  {t(`landings:categories.${key}`, { defaultValue: info?.label || key })}{info?.count ? ` (${info.count})` : ''}
                </option>
              ))}
              {category && !categories.some(([k]) => k === category) && (
                <option value={category}>{catLabel}</option>
              )}
            </select>
            <input
              type="month"
              value={month}
              onChange={e => setFilter('mese', e.target.value)}
              aria-label={t('landings:calendar.monthLabel', { defaultValue: 'Mese' })}
              data-testid="esp-f-mese"
              className="flex-none w-40 rounded-full border border-gray-300 bg-white px-3.5 py-1.5 text-sm text-gray-700 focus:border-primary focus:outline-none"
            />
            <input
              type="search"
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder={t('landings:calendar.searchShort', { defaultValue: 'Cerca…' })}
              aria-label={t('landings:calendar.searchPlaceholder', { defaultValue: 'Cerca un ritiro, un luogo, un professionista…' })}
              data-testid="esp-f-cerca"
              className="flex-none w-36 lg:w-44 rounded-full border border-gray-300 bg-white px-3.5 py-1.5 text-sm text-gray-700 focus:border-primary focus:outline-none"
            />
            <button
              type="button"
              onClick={() => setFilter('vista', view === 'mappa' ? '' : 'mappa')}
              aria-pressed={view === 'mappa'}
              className={`flex-none rounded-full px-4 py-1.5 text-sm font-medium border transition-colors ${
                view === 'mappa'
                  ? 'bg-[#376254] border-[#376254] text-white shadow'
                  : 'bg-white border-gray-300 text-gray-700 hover:border-primary hover:text-primary'
              }`}
            >
              {t('landings:calendar.viewMap', { defaultValue: 'Mappa' })}
            </button>
            {anyFilter && (
              <button
                type="button"
                onClick={() => { navigate(basePath, { replace: true }); setQuery(''); }}
                className="flex-none text-sm text-muted-foreground underline px-1 whitespace-nowrap"
              >
                {t('landings:calendar.clearFilters')}
              </button>
            )}
            {!loading && (
              <span className="flex-none lg:ml-auto text-xs text-muted-foreground whitespace-nowrap" data-testid="esp-conteggio">
                {t('landings:calendar.resultsCount', { count: items.length, defaultValue: '{{count}} ritiri' })}
              </span>
            )}
          </div>
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
      </div>}

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
          anyFilter ? (
            <div className="text-center py-20 max-w-md mx-auto">
              <img src="/logo-aurya-128.png" alt="" aria-hidden className="mx-auto h-14 w-14 select-none opacity-80" draggable={false} />
              <p className="mt-3 text-lg font-semibold text-foreground">
                {t('landings:calendar.emptyFilteredTitle', { defaultValue: 'Nessun ritiro con questi filtri' })}
              </p>
              <p className="text-muted-foreground mt-1">
                {t('landings:calendar.emptyFiltered', { defaultValue: 'Prova ad allargare la ricerca: togli un filtro o guarda un altro mese.' })}
              </p>
              <button
                onClick={() => { setParams({}, { replace: true }); setQuery(''); }}
                className="mt-4 rounded-full bg-primary text-primary-foreground px-5 py-2 text-sm font-semibold"
              >
                {t('landings:calendar.showAll', { defaultValue: 'Mostra tutti i ritiri' })}
              </button>
            </div>
          ) : (
            /* P3 → RE (10/9/2026): lo stato vuoto onesto, con le parole del
               founder e le due porte. Niente «torna presto». */
            <div data-testid="esp-vuoto" className="text-center py-16 max-w-md mx-auto">
              <div className="mx-auto h-16 w-16 rounded-full bg-secondary flex items-center justify-center">
                <CalendarDays className="h-7 w-7 text-[#376254]" aria-hidden />
              </div>
              <p className="mt-4 font-display text-2xl text-foreground">
                {t('landings:calendar.emptyTitle', { defaultValue: 'I primi ritiri stanno arrivando.' })}
              </p>
              <p className="mt-3 text-base text-muted-foreground">
                {t('landings:calendar.emptyBody', { defaultValue: 'I professionisti della rete li stanno pubblicando. Dicci cosa cerchi e dove: ti avvisiamo appena c’è un ritiro vicino a te.' })}
              </p>
              <div className="mt-5 flex flex-wrap items-center justify-center gap-2">
                <Link to="/cerca-ritiro?porta=esperienze" data-testid="esp-cta-cerca"
                      onClick={() => trackEvent('porta', { porta: 'cerca', da: 'esperienze' })}
                      className="rounded-full bg-primary text-white px-5 py-1.5 text-sm font-semibold hover:opacity-90 transition-opacity">
                  Trovami il mio ritiro
                </Link>
                <Link to="/entra-nella-rete?porta=esperienze" data-testid="esp-cta-op"
                      onClick={() => trackEvent('porta', { porta: 'operatore', da: 'esperienze' })}
                      className="rounded-full border border-[#376254] text-[#376254] bg-white px-4 py-1.5 text-sm font-semibold hover:bg-[#376254]/5 transition-colors">
                  Organizzi ritiri? Apri il tuo spazio
                </Link>
              </div>
            </div>
          )
        ) : view === 'mappa' ? (
          /* G3 — la directory sulla mappa */
          <React.Suspense fallback={<div className="h-[520px] rounded-2xl bg-gray-100 animate-pulse" />}>
            <RetreatsMapView items={items} />
          </React.Suspense>
        ) : (
          <>
          {!anyFilter && items.some((it) => it.prima_fila) && (
            <p data-testid="esp-fascia-prima-fila" className="mb-4 text-xs uppercase tracking-wide text-muted-foreground">
              In prima fila: i ritiri promossi stanno in cima
            </p>
          )}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {items.map(item => {
              const badge = dateBadge(item.start_at, i18n.language);
              return (
                <Link
                  key={`${item.org_slug}/${item.slug}`}
                  to={item.sample ? '#' : item.url}
                  onClick={item.sample ? (e) => e.preventDefault() : undefined}
                  className={`group rounded-2xl border border-border bg-card overflow-hidden shadow-sm hover:shadow-lg transition-shadow duration-300 flex flex-col ${item.sample ? 'pointer-events-none select-none' : ''}`}
                >
                  <div className="relative aspect-[16/9] bg-muted overflow-hidden">
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
                    {item.prima_fila && (
                      <span className="absolute bottom-3 left-3 rounded-full bg-[#2f5749] px-2.5 py-1 text-[11px] font-semibold text-white shadow"
                            data-testid="esp-prima-fila">In prima fila</span>
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
                    {/* PL14 — il titolo evocativo resta VISIBILE anche sui
                        campioni: comunica il concept; l'identità (organizzatore,
                        rating) resta redatta qui sotto */}
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
                        {/* PL9 — organizzatore campione: segnaposto sfocato e
                            NIENTE rating (una recensione finta è fuorviante) */}
                        {item.sample ? <Redacted kind="name" /> : item.org_name}
                        {/* AN7 — recensioni verificate visibili dove si sceglie */}
                        {!item.sample && item.org_rating?.count > 0 && (
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
                        <span className="block text-[11px] text-muted-foreground">
                          {item.booking === 'request' ? 'su richiesta' : 'prenotazione online'}
                        </span>
                      </span>
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
          </>
        )}

        {/* P3 → RE — la chiusura: chi non trova il suo, e chi organizza */}
        {!loading && items.length > 0 && !anyFilter && (
          <p className="mt-10 text-sm text-muted-foreground">
            Non trovi il tuo? <Link to="/cerca-ritiro?porta=esperienze" className="underline">Dicci cosa cerchi</Link> e ti avvisiamo.
            {' '}Organizzi ritiri? <Link to="/entra-nella-rete?porta=esperienze" className="underline">Apri il tuo spazio</Link>: pubblicare è gratis, senza commissioni.
          </p>
        )}

      </main>

      {/* AN1 — l'anima di Aurya: come funziona / perché / organizzatori.
          Solo sulla home "pulita": chi sta filtrando non va interrotto. */}
    </div>
    </MarketplaceShell>
  );
}
