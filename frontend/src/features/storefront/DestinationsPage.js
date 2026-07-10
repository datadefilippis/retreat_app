/**
 * DestinationsPage — /destinazioni e /destinazioni/{luogo} (S2b).
 *
 * Le pagine programmatiche per le query "ritiri + luogo" — la domanda
 * organica n°1 del settore. Esistono SOLO per luoghi con ritiri reali
 * (l'indice viene da /public/destinations); il dettaglio riusa la
 * ricerca directory (region=label) e aggancia gli operatori della zona.
 */

import React, { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import api from '../../api/client';
import MarketplaceShell from './components/MarketplaceShell';
import PrelaunchBanner from '../prelaunch/PrelaunchBanner';
import useSeoMeta from './lib/useSeoMeta';

function fmtDates(start, end, lang = 'it-IT') {
  try {
    const s = new Date(start);
    const opts = { day: 'numeric', month: 'short' };
    if (!end) return s.toLocaleDateString(lang, { ...opts, year: 'numeric' });
    const e = new Date(end);
    return `${s.toLocaleDateString(lang, opts)} – ${e.toLocaleDateString(lang, { ...opts, year: 'numeric' })}`;
  } catch { return ''; }
}

function RetreatCard({ item, i18nLang, t }) {
  return (
    <Link
      to={item.sample ? '#' : item.url}
      onClick={item.sample ? (e) => e.preventDefault() : undefined}
      className={`group rounded-2xl border border-border bg-card overflow-hidden hover:shadow-lg transition-shadow ${item.sample ? 'pointer-events-none select-none' : ''}`}
    >
      <div className="relative h-40 bg-secondary overflow-hidden">
        {/* PL13 — stesso oscuramento della directory: i campioni sono
            sfocati, non cliccabili e senza identita' anche qui */}
        {item.sample && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-[#1e2b26]/25 backdrop-blur-[1px]">
            <span className="rounded-full bg-white/90 px-3 py-1 text-[11px] font-semibold text-[#376254] shadow">
              {t('landings:calendar.comingSoon', { defaultValue: 'Presto disponibile' })}
            </span>
          </div>
        )}
        {item.cover_image_url ? (
          <img src={item.cover_image_url} alt={item.sample ? '' : item.title} loading="lazy"
               className={`w-full h-full object-cover transition-transform duration-300 ${item.sample ? 'blur-[3px] scale-105' : 'group-hover:scale-105'}`} />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <img src="/logo-aurya-128.png" alt="" aria-hidden className="h-10 w-10 opacity-60" />
          </div>
        )}
      </div>
      <div className="p-4">
        {item.category && (
          <p className="text-[11px] uppercase tracking-wide text-muted-foreground">
            {t(`landings:categories.${item.category}`, { defaultValue: item.category })}
          </p>
        )}
        {/* PL14 — titolo evocativo visibile anche sui campioni */}
        <h3 className="font-semibold text-foreground mt-0.5 line-clamp-2">{item.title}</h3>
        <p className="text-sm text-muted-foreground mt-1">
          {fmtDates(item.start_at, item.end_at, i18nLang)}
          {item.city ? ` · ${item.city}` : ''}
        </p>
        {item.price_from != null && (
          <p className="text-sm font-semibold text-foreground mt-1.5">
            {t('landings:calendar.priceFrom', { price: `${item.price_from} €`, defaultValue: 'da {{price}}' })}
          </p>
        )}
      </div>
    </Link>
  );
}

export default function DestinationsPage() {
  const { t, i18n } = useTranslation('landings');
  const { luogo } = useParams();
  const [index, setIndex] = useState(null);
  const [retreats, setRetreats] = useState(null);
  const [operators, setOperators] = useState([]);
  const [loading, setLoading] = useState(true);

  // Indice destinazioni: serve sia alla pagina indice sia al dettaglio
  // (slug → label per interrogare la directory).
  useEffect(() => {
    let mounted = true;
    api.get('/public/destinations')
      .then(res => { if (mounted) setIndex(res.data); })
      .catch(() => { if (mounted) setIndex({ items: [], total: 0 }); });
    return () => { mounted = false; };
  }, []);

  const place = useMemo(
    () => luogo && index ? (index.items || []).find(p => p.slug === luogo) : null,
    [luogo, index],
  );

  useEffect(() => {
    if (!luogo) { setLoading(!index); setRetreats(null); return; }
    if (!index) return;
    if (!place) { setLoading(false); setRetreats({ items: [] }); return; }
    let mounted = true;
    setLoading(true);
    Promise.all([
      // PL18 — la lingua viaggia anche qui: i campioni (e i ritiri veri)
      // arrivano tradotti come nella directory
      api.get('/public/retreats', { params: { region: place.label,
        ...(i18n.language && i18n.language.slice(0, 2) !== 'it'
          ? { lang: i18n.language.slice(0, 2) } : {}) } }),
      api.get('/public/operators').catch(() => ({ data: { items: [] } })),
    ]).then(([r, o]) => {
      if (!mounted) return;
      // la region della directory matcha la regione; per le città il
      // filtro lato client sulle card (city) tiene la pagina onesta
      const items = (r.data?.items || []).filter(it =>
        (it.region || '').toLowerCase() === place.label.toLowerCase()
        || (it.city || '').toLowerCase() === place.label.toLowerCase());
      setRetreats({ items: items.length > 0 ? items : (r.data?.items || []) });
      setOperators((o.data?.items || []).filter(op =>
        (op.regions || []).includes(place.label)));
    }).catch(() => { if (mounted) setRetreats({ items: [] }); })
      .finally(() => { if (mounted) setLoading(false); });
    return () => { mounted = false; };
  }, [luogo, index, place, i18n.language]);

  const label = place?.label || (luogo || '').replace(/-/g, ' ');
  const items = retreats?.items || [];
  const indexItems = index?.items || [];

  useSeoMeta({
    title: luogo
      ? t('landings:destinations.seoTitle', {
          place: label, defaultValue: 'Ritiri ed esperienze a {{place}} | Aurya' })
      : t('landings:destinations.seoTitleIndex', {
          defaultValue: 'Destinazioni — dove vuoi ritrovarti? | Aurya' }),
    description: luogo
      ? t('landings:destinations.seoDesc', {
          place: label,
          defaultValue: 'Ritiri di yoga, meditazione ed esperienze olistiche a {{place}}: date, prezzi e disponibilità reali. Prenota online con la caparra.' })
      : t('landings:destinations.seoDescIndex', {
          defaultValue: 'Scegli la destinazione del tuo prossimo ritiro: i luoghi con ritiri ed esperienze in programma su Aurya.' }),
    canonicalPath: luogo ? `/destinazioni/${luogo}` : '/destinazioni',
    noindex: !loading && (luogo ? items.length === 0 : indexItems.length === 0),
    jsonLd: (luogo && items.length > 0) ? {
      '@context': 'https://schema.org',
      '@type': 'ItemList',
      itemListElement: items.slice(0, 20).map((it, i) => ({
        '@type': 'ListItem', position: i + 1,
        url: window.location.origin + it.url,
      })),
    } : undefined,
  });

  return (
    <MarketplaceShell>
      {/* PL12 — anche da qui si torna sempre alle landing lead */}
      <PrelaunchBanner audience="traveler" />
      <header className="relative text-white overflow-hidden">
        {/* la verticale sul mare del founder: la promessa del viaggio */}
        <img aria-hidden src="/media/hero-destination.webp" alt="" fetchpriority="high"
             className="absolute inset-0 w-full h-full object-cover" />
        {/* velatura salvia più densa a sinistra, dove vive il testo */}
        <div aria-hidden className="absolute inset-0 pointer-events-none bg-gradient-to-r from-[#14231d]/90 via-[#14231d]/60 to-[#14231d]/30" />
        <div className="relative max-w-6xl mx-auto px-4 pt-12 pb-10 md:pt-16 md:pb-14">
          <nav className="text-xs text-white/70 mb-3">
            <Link to="/" className="hover:text-white hover:underline">Aurya</Link>
            <span className="mx-1.5">›</span>
            {luogo ? (
              <>
                <Link to="/destinazioni" className="hover:text-white hover:underline">
                  {t('landings:destinations.heading', { defaultValue: 'Destinazioni' })}
                </Link>
                <span className="mx-1.5">›</span>
                <span className="text-white">{label}</span>
              </>
            ) : (
              <span className="text-white">
                {t('landings:destinations.heading', { defaultValue: 'Destinazioni' })}
              </span>
            )}
          </nav>
          <p aria-hidden className="font-brand uppercase tracking-[0.35em] text-xs md:text-sm text-[#ecd9a8] mb-2 select-none text-hero-shadow">Connect · Heal · Grow</p>
          <h1 className="font-display text-3xl md:text-5xl font-semibold text-hero-shadow">
            {luogo
              ? t('landings:destinations.headingPlace', {
                  place: label, defaultValue: 'Ritiri ed esperienze a {{place}}' })
              : t('landings:destinations.heading', { defaultValue: 'Destinazioni' })}
          </h1>
          <p className="mt-2.5 text-white/90 max-w-2xl text-hero-shadow">
            {luogo
              ? t('landings:destinations.subtitlePlace', {
                  place: label,
                  defaultValue: 'Le date in programma a {{place}}: prenoti online con la caparra, il saldo più avanti.' })
              : t('landings:destinations.subtitle', {
                  defaultValue: 'I luoghi dove i nostri organizzatori tengono ritiri ed esperienze, aggiornati in tempo reale.' })}
          </p>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8">
        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {[1, 2, 3].map(i => <div key={i} className="rounded-2xl border border-border bg-card h-56 animate-pulse" />)}
          </div>
        ) : !luogo ? (
          indexItems.length === 0 ? (
            <p className="text-center text-muted-foreground py-16">
              {t('landings:destinations.empty', { defaultValue: 'Nessuna destinazione con ritiri in programma, per ora.' })}
            </p>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
              {indexItems.map(p => (
                <Link key={p.slug} to={`/destinazioni/${p.slug}`}
                      className="rounded-2xl border border-border bg-card p-5 hover:shadow-lg hover:border-primary/40 transition-all">
                  <p className="font-semibold text-foreground">{p.label}</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    {t('landings:destinations.count', { count: p.retreats, defaultValue: '{{count}} ritiri in programma' })}
                  </p>
                </Link>
              ))}
            </div>
          )
        ) : items.length === 0 ? (
          <div className="text-center py-20 max-w-md mx-auto">
            <img src="/logo-aurya-128.png" alt="" aria-hidden className="mx-auto h-14 w-14 opacity-80" />
            <p className="mt-3 text-lg font-semibold text-foreground">
              {t('landings:destinations.emptyPlace', { defaultValue: 'Nessun ritiro qui, per ora' })}
            </p>
            <Link to="/destinazioni" className="mt-4 inline-block rounded-full bg-primary text-white px-5 py-2 text-sm font-semibold">
              {t('landings:destinations.backIndex', { defaultValue: 'Tutte le destinazioni' })}
            </Link>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
              {items.map(item => (
                <RetreatCard key={item.url} item={item} i18nLang={i18n.language} t={t} />
              ))}
            </div>
            {operators.some(op => !op.sample) && (
              <section className="mt-12">
                <h2 className="font-heading text-xl font-bold text-foreground mb-4">
                  {t('landings:destinations.operatorsHere', {
                    place: label, defaultValue: 'Organizzatori a {{place}}' })}
                </h2>
                <div className="flex flex-wrap gap-3">
                  {/* PL13 — niente chip per i campioni: nome redatto e
                      profilo 404, sarebbe una pillola vuota */}
                  {operators.filter(op => !op.sample).map(op => (
                    <Link key={op.org_slug} to={`/o/${op.org_slug}`}
                          className="rounded-full border border-border bg-card px-4 py-2 text-sm font-medium hover:border-primary hover:text-primary transition-colors">
                      {op.name}
                    </Link>
                  ))}
                </div>
              </section>
            )}
          </>
        )}
      </main>
    </MarketplaceShell>
  );
}
