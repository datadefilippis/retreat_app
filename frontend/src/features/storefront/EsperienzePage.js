/**
 * EsperienzePage — /esperienze: «I prossimi ritiri ed esperienze» (P3,
 * 10/9/2026, piano di business).
 *
 * Fino a oggi /esperienze rimandava alla home (DS3, 7/7) e il calendario
 * pubblico elencava SOLO i ritiri prenotabili online con Stripe (GT1b):
 * il marketplace restava vuoto e la porta «Trovami il mio ritiro» non
 * aveva niente da mostrare. Decisione del founder (10/9): il marketplace
 * e' GRATIS per tutti i ritiri pubblicati, con o senza Stripe; si paga
 * la PROMOZIONE (la prima fila), non la presenza.
 *
 * La pagina e' semplice apposta: la fascia «In prima fila» (Spinta, Club:
 * oggi vuota, e quando e' vuota non si vede), poi tutti i ritiri per data.
 * Lo stato vuoto e' onesto e porta alle due porte. Niente ricerca, niente
 * mappa: quelle stanno nel calendario della fase marketplace.
 */
import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import api from '../../api/client';
import { trackEvent } from '../../lib/analytics';   // RB13
import MarketplaceShell from './components/MarketplaceShell';
import useSeoMeta from './lib/useSeoMeta';
import { Section, DisplayTitle, Lede, EditorialCta, PhotoOpener } from '../../components/editorial';

// founder 10/9 sera: una copertina che chiami, dalle foto gia' in repo
const COVER = '/media/aurya-hero-poster.jpg';

function fmtDates(start, end, lang = 'it-IT') {
  if (!start) return '';
  const s = new Date(start);
  const e = end ? new Date(end) : null;
  const d = (x) => x.toLocaleDateString(lang, { day: 'numeric', month: 'short' });
  if (e && e.toDateString() !== s.toDateString()) return `${d(s)} – ${d(e)}`;
  return d(s);
}

function Scheda({ item, lang }) {
  return (
    <Link to={item.url}
          className="group flex h-full flex-col overflow-hidden rounded-[1.5rem] border border-border bg-card transition-shadow hover:shadow-lg"
          data-testid="esp-scheda">
      <div className="relative h-44 overflow-hidden bg-secondary">
        {item.cover_image_url ? (
          <img src={item.cover_image_url} alt={item.title} loading="lazy"
               className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105" />
        ) : (
          <div className="flex h-full w-full items-center justify-center">
            <img src="/logo-aurya-128.png" alt="" aria-hidden className="h-10 w-10 opacity-60" />
          </div>
        )}
        {item.prima_fila && (
          <span className="absolute left-3 top-3 rounded-full bg-[#2f5749] px-2.5 py-1 text-[11px] font-semibold text-white shadow"
                data-testid="esp-prima-fila">In prima fila</span>
        )}
      </div>
      <div className="flex flex-1 flex-col p-4">
        {item.category && (
          <p className="text-[11px] uppercase tracking-wide text-muted-foreground">{item.category}</p>
        )}
        <h3 className="mt-0.5 line-clamp-2 font-semibold text-foreground">{item.title}</h3>
        <p className="mt-1 text-sm text-muted-foreground">
          {fmtDates(item.start_at, item.end_at, lang)}{item.city ? ` · ${item.city}` : ''}{item.region ? `, ${item.region}` : ''}
        </p>
        {item.org_name && <p className="mt-1 text-sm text-foreground/80">con {item.org_name}</p>}
        <div className="mt-auto flex items-end justify-between pt-3">
          {item.price_from != null
            ? <p className="text-sm font-semibold text-foreground">da {item.price_from} €</p>
            : <span />}
          <span className="text-[11px] text-muted-foreground">
            {item.booking === 'request' ? 'su richiesta' : 'prenotazione online'}
          </span>
        </div>
      </div>
    </Link>
  );
}

export default function EsperienzePage() {
  const { i18n } = useTranslation();
  const lang = i18n.language || 'it';
  const [dati, setDati] = useState(null);

  useSeoMeta({
    title: 'Ritiri ed esperienze in programma | Aurya',
    description: 'I ritiri e le esperienze olistiche dei professionisti della rete Aurya, per data: yoga, meditazione, respiro, suono, cammini. Con la caparra, online o con bonifico.',
    canonicalPath: '/esperienze',
  });

  useEffect(() => {
    let vivo = true;
    api.get('/public/retreats', { params: { limit: 120 } })
      .then((r) => { if (vivo) setDati(r.data); })
      .catch(() => { if (vivo) setDati({ items: [], total: 0 }); });
    return () => { vivo = false; };
  }, []);

  const items = dati?.items || [];
  const primaFila = items.filter((i) => i.prima_fila);
  const tutti = items.filter((i) => !i.prima_fila);

  return (
    <MarketplaceShell noSearch>
      <div className="bg-background">
        <PhotoOpener data-testid="esp-cover" image={COVER} focus="50% 40%" height="standard"
                     align="left" width="max-w-6xl" labelledBy="esp-title">
          <DisplayTitle as="h1" id="esp-title" size="hero" measure="title" className="text-hero-shadow">
            I prossimi ritiri ed esperienze.
          </DisplayTitle>
          <p className="mt-6 max-w-[46ch] text-balance text-lg leading-relaxed text-hero-shadow opacity-95 sm:text-xl">
            I ritiri e le esperienze dei professionisti della rete, per data. Ogni scheda dice chi conduce, dove, quando, il prezzo e come si prenota.
          </p>
        </PhotoOpener>

        {dati === null && (
          <Section tone="paper" rhythm="flow" width="max-w-6xl"><p className="text-sm text-muted-foreground">Carico…</p></Section>
        )}

        {dati !== null && items.length === 0 && (
          <Section tone="paper" rhythm="screen" width="max-w-3xl">
            <div data-testid="esp-vuoto" className="rounded-[1.75rem] border border-dashed border-border p-8 text-center">
              <p className="font-display text-2xl text-foreground">I primi ritiri stanno arrivando.</p>
              <p className="mt-3 text-base text-muted-foreground">
                I professionisti della rete li stanno pubblicando. Dicci cosa cerchi e dove: ti avvisiamo appena c’è un ritiro vicino a te.
              </p>
              <div className="mt-6 flex flex-col items-center gap-3 sm:flex-row sm:justify-center sm:gap-6">
                <EditorialCta to="/cerca-ritiro?porta=esperienze" variant="solid" data-testid="esp-cta-cerca"
                              onClick={() => trackEvent('porta', { porta: 'cerca', da: 'esperienze' })}>Trovami il mio ritiro</EditorialCta>
                <EditorialCta to="/entra-nella-rete?porta=esperienze" variant="quiet" data-testid="esp-cta-op"
                              onClick={() => trackEvent('porta', { porta: 'operatore', da: 'esperienze' })}>Organizzi ritiri? Apri il tuo spazio</EditorialCta>
              </div>
            </div>
          </Section>
        )}

        {primaFila.length > 0 && (
          <Section tone="sand" rhythm="flow" width="max-w-6xl">
            <div data-testid="esp-fascia-prima-fila">
              <DisplayTitle as="h2" size="section" measure="title">In prima fila.</DisplayTitle>
              <div className="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
                {primaFila.map((it) => <Scheda key={it.url} item={it} lang={lang} />)}
              </div>
            </div>
          </Section>
        )}

        {tutti.length > 0 && (
          <Section tone="paper" rhythm="flow" width="max-w-6xl">
            <div data-testid="esp-tutti">
              {primaFila.length > 0 && <DisplayTitle as="h2" size="section" measure="title">Tutti i ritiri, per data.</DisplayTitle>}
              <div className={`grid gap-6 sm:grid-cols-2 lg:grid-cols-3 ${primaFila.length > 0 ? 'mt-8' : ''}`}>
                {tutti.map((it) => <Scheda key={it.url} item={it} lang={lang} />)}
              </div>
            </div>
          </Section>
        )}

        {dati !== null && items.length > 0 && (
          <Section tone="cream" rhythm="flow" width="max-w-4xl">
            <p className="text-sm text-muted-foreground">
              Non trovi il tuo? <Link to="/cerca-ritiro?porta=esperienze" className="underline">Dicci cosa cerchi</Link> e ti avvisiamo.
              {' '}Organizzi ritiri? <Link to="/entra-nella-rete?porta=esperienze" className="underline">Apri il tuo spazio</Link>: pubblicare è gratis, senza commissioni.
            </p>
          </Section>
        )}
      </div>
    </MarketplaceShell>
  );
}
