/**
 * LinkPage — /@{slug} e /l/{slug} (LK2, piano pagina link, 14/8/2026).
 *
 * La pagina per la bio di Instagram: UNA colonna, pollice-friendly,
 * niente header ne' menu — chi arriva qui deve solo scegliere dove
 * andare. E' Linktree, ma coi blocchi VIVI di Aurya: il prossimo
 * ritiro con data e prezzo che finisce nel checkout, il listino, il
 * profilo, WhatsApp, i social. Tutto arriva dal profilo gia'
 * configurato: zero passi extra per l'operatore.
 *
 * Il footer e' il loop di crescita («Sei un professionista del
 * benessere?»): ogni operatore che mette la pagina in bio presenta
 * Aurya alla sua audience — che contiene altri operatori.
 *
 * SEO: noindex (l'asset indicizzato resta /o/), ma OG completi dal
 * guscio server-side: questa pagina vive nelle chat e l'anteprima
 * su WhatsApp deve mostrare foto e nome.
 */
import React, { useEffect, useState } from 'react';
import { useParams, Link, Navigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Instagram, Facebook, Globe, ArrowRight, MessageCircle, CalendarDays } from 'lucide-react';
import api from '../../api/client';
import useSeoMeta from './lib/useSeoMeta';
import useTrackView from './lib/useTrackView';
import useItalianOnly from '../../lib/useItalianOnly';
import { useSiteConfig } from '../../context/SiteConfigContext';
import { BrandLogo } from '../../components/BrandLogo';
import VerifiedAuryaBadge from '../../components/VerifiedAuryaBadge';

/* I 4 temi — parole del mondo Aurya, non nomi tecnici. Ogni tema e'
   un set chiuso di classi: la scelta cambia atmosfera, mai struttura.
   `carta` e' l'unico col linguaggio editoriale (bordo netto + ombra
   dura che si schiaccia al click): le sue card non portano l'ombra
   morbida delle altre. */
export const LINK_THEMES = {
  salvia: {
    page: 'bg-gradient-to-b from-[#f2f5ee] via-[#edf1e8] to-[#e5ebdd]',
    text: 'text-stone-800', sub: 'text-stone-500',
    card: 'bg-white/95 border border-stone-200/90 text-stone-800 shadow-[0_1px_2px_rgba(28,25,23,0.04),0_10px_28px_-16px_rgba(55,98,84,0.35)] hover:border-[#8a9979] hover:-translate-y-0.5 hover:shadow-[0_2px_4px_rgba(28,25,23,0.05),0_16px_36px_-16px_rgba(55,98,84,0.45)]',
    hero: 'text-stone-900',
    ring: 'ring-white',
    halo: 'shadow-[0_10px_36px_-10px_rgba(55,98,84,0.5)]',
    social: 'bg-white/80 border border-stone-200/90 text-stone-500 hover:text-[#376254] hover:border-[#8a9979]',
    footer: 'text-stone-500',
    cta: 'bg-white/70 border border-stone-200/90 backdrop-blur',
    ctaBtn: 'bg-[#376254] text-white hover:bg-[#2c5044]',
  },
  terra: {
    page: 'bg-gradient-to-b from-[#f8ecdf] via-[#f2ddc9] to-[#eaceb2]',
    text: 'text-stone-800', sub: 'text-stone-500',
    card: 'bg-white/90 backdrop-blur border border-orange-900/10 text-stone-800 shadow-[0_1px_2px_rgba(67,20,7,0.05),0_10px_28px_-16px_rgba(124,45,18,0.35)] hover:border-orange-900/30 hover:-translate-y-0.5 hover:shadow-[0_2px_4px_rgba(67,20,7,0.06),0_16px_36px_-16px_rgba(124,45,18,0.45)]',
    hero: 'text-stone-900',
    ring: 'ring-white/90',
    halo: 'shadow-[0_10px_36px_-10px_rgba(124,45,18,0.4)]',
    social: 'bg-white/70 border border-orange-900/10 text-stone-500 hover:text-orange-950 hover:border-orange-900/30',
    footer: 'text-stone-500',
    cta: 'bg-white/60 border border-orange-900/10 backdrop-blur',
    ctaBtn: 'bg-[#9a5b2e] text-white hover:bg-[#84491f]',
  },
  notte: {
    page: 'bg-gradient-to-b from-[#1b201c] via-[#181c19] to-[#121613]',
    text: 'text-stone-100', sub: 'text-stone-400',
    card: 'bg-white/[0.06] backdrop-blur border border-white/10 text-stone-100 hover:bg-white/[0.12] hover:border-white/25 hover:-translate-y-0.5',
    hero: 'text-white',
    ring: 'ring-white/25',
    halo: 'shadow-[0_10px_40px_-10px_rgba(216,226,207,0.25)]',
    social: 'bg-white/[0.06] border border-white/10 text-stone-300 hover:text-white hover:border-white/30',
    footer: 'text-stone-400',
    cta: 'bg-white/[0.05] border border-white/10',
    ctaBtn: 'bg-[#d8e2cf] text-stone-900 hover:bg-white',
  },
  carta: {
    page: 'bg-[#faf8f2]',
    text: 'text-stone-900', sub: 'text-stone-500',
    card: 'bg-white border-2 border-stone-900 text-stone-900 shadow-[3px_3px_0_#1c1917] hover:bg-stone-900 hover:text-white active:translate-x-[2px] active:translate-y-[2px] active:shadow-[1px_1px_0_#1c1917]',
    hero: 'text-stone-900',
    ring: 'ring-stone-900',
    halo: '',
    social: 'bg-white border-2 border-stone-900 text-stone-900 hover:bg-stone-900 hover:text-white',
    footer: 'text-stone-500',
    cta: 'bg-white border-2 border-stone-900 shadow-[4px_4px_0_#1c1917]',
    ctaBtn: 'bg-stone-900 text-white hover:bg-stone-700',
  },
};

const httpsify = (u) => (/^https?:\/\//i.test(u || '') ? u : `https://${u}`);

/* LK4 — beacon del click: fire-and-forget con keepalive, cosi' parte
   anche se la pagina sta gia' navigando via. Stesse garanzie del
   motore VT: mai bloccare, mai rompere. */
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';
function trackClick(slug, linkId) {
  try {
    fetch(`${BACKEND_URL}/api/public/track`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ surface: 'link_click', slug,
                             channel: 'direct', link_id: linkId }),
      keepalive: true,
    }).catch(() => {});
  } catch { /* mai rompere la navigazione */ }
}

/* LK6 — dentro l'anteprima dell'editor (iframe) i link interni
   aprirebbero il profilo DENTRO la cornice, senza modo di tornare:
   in iframe TUTTO apre in una scheda nuova. */
const IN_FRAME = typeof window !== 'undefined' && window.self !== window.top;

/* Una riga cliccabile della colonna: stessa forma per blocchi vivi e
   link personalizzati — la pagina resta UNA cosa, non due liste. */
function Row({ theme, children, onNavigate, to, ...linkProps }) {
  const cls = 'block w-full rounded-2xl px-5 py-4 text-center text-[15px] '
    + `font-semibold transition-all duration-200 active:scale-[0.98] ${theme.card}`;
  if (to && !IN_FRAME) {
    return <Link to={to} {...linkProps} onClick={onNavigate} className={cls}>{children}</Link>;
  }
  return <a href={to || linkProps.href} {...(({ href, ...rest }) => rest)(linkProps)}
            onClick={onNavigate} className={cls}
            target="_blank" rel="noopener noreferrer">{children}</a>;
}

/* Ingresso morbido: ogni elemento sale di qualche pixel, in sequenza.
   La keyframe vive in index.css dietro prefers-reduced-motion. */
const rise = (i) => ({ animationDelay: `${Math.min(i, 8) * 55}ms` });

export default function LinkPage({ handle }) {
  const { t } = useTranslation('landings');
  useItalianOnly();   // founder 27/7 — sito pubblico solo italiano
  const params = useParams();
  const { sitePhase } = useSiteConfig();
  const org_slug = (handle || params.org_slug || '').replace(/^@/, '');

  const [data, setData] = useState(null);
  const [status, setStatus] = useState('loading');

  useEffect(() => {
    let alive = true;
    api.get(`/public/operator/${org_slug}`)
      .then((r) => { if (alive) { setData(r.data); setStatus('ok'); } })
      .catch(() => { if (alive) setStatus('missing'); });
    return () => { alive = false; };
  }, [org_slug]);

  useSeoMeta({
    title: data?.name ? `${data.name} | Aurya` : 'Aurya',
    description: data?.tagline || data?.bio || '',
  });
  // LK4 — la visita conta nello specchietto Visibilita' (superficie
  // "links", stessa pipeline privacy-first delle altre pagine)
  useTrackView('links', org_slug);

  if (status === 'missing') return <Navigate to="/" replace />;
  // pagina non attivata → la casa vera dell'operatore e' il profilo
  if (status === 'ok' && !data?.link_page) {
    return <Navigate to={`/o/${org_slug}`} replace />;
  }
  if (status === 'loading' || !data) {
    return <div className="min-h-screen bg-[#edf1e8]" />;
  }

  const lp = data.link_page;
  const theme = LINK_THEMES[lp.theme] || LINK_THEMES.salvia;
  const blocks = lp.blocks || {};
  const next = (data.upcoming || [])[0];
  const socials = data.socials || {};
  const hasListino = (data.listino || []).length > 0;
  // RT2 — stessa destinazione phase-aware della CTA operatori nel guscio
  const joinTo = sitePhase === 'network' ? '/entra-nella-rete' : '/inizia';

  const dateLabel = (iso) => {
    try {
      return new Date(iso).toLocaleDateString('it-IT',
        { day: 'numeric', month: 'long' });
    } catch { return ''; }
  };

  /* indice progressivo per lo stagger: header=0, social=1, poi le righe */
  let seq = 1;

  return (
    <div className={`min-h-screen ${theme.page} ${theme.text}`} data-testid="link-page">
      <main className="mx-auto flex min-h-screen w-full max-w-md flex-col px-5 pb-8 pt-14 sm:pt-16">

        {/* ── Identita' ─────────────────────────────────────────── */}
        <header className="lk-rise text-center" style={rise(0)}>
          {data.portrait_url && (
            <img src={data.portrait_url} alt={data.name}
                 className={`mx-auto h-28 w-28 rounded-full object-cover ring-4 ${theme.ring} ${theme.halo}`} />
          )}
          <h1 className={`mt-5 font-display text-[26px] font-bold tracking-tight ${theme.hero}`}>
            {data.name}
          </h1>
          {data.interview_verified_at && (
            <div className="mt-2 flex justify-center">
              <VerifiedAuryaBadge size="sm"
                variant={lp.theme === 'notte' ? 'on-photo' : 'on-light'} />
            </div>
          )}
          {data.tagline && (
            <p className={`mx-auto mt-2.5 max-w-[34ch] text-[15px] leading-relaxed ${theme.sub}`}>
              {data.tagline}
            </p>
          )}
        </header>

        {/* ── Social ────────────────────────────────────────────── */}
        {blocks.socials !== false && (socials.instagram || socials.facebook || socials.website) && (
          <div className="lk-rise mt-6 flex justify-center gap-3" style={rise(1)}>
            {socials.instagram && (
              <a href={httpsify(socials.instagram)} target="_blank" rel="noopener noreferrer"
                 aria-label="Instagram"
                 className={`flex h-11 w-11 items-center justify-center rounded-full transition-all duration-200 active:scale-95 ${theme.social}`}>
                <Instagram className="h-5 w-5" />
              </a>
            )}
            {socials.facebook && (
              <a href={httpsify(socials.facebook)} target="_blank" rel="noopener noreferrer"
                 aria-label="Facebook"
                 className={`flex h-11 w-11 items-center justify-center rounded-full transition-all duration-200 active:scale-95 ${theme.social}`}>
                <Facebook className="h-5 w-5" />
              </a>
            )}
            {socials.website && (
              <a href={httpsify(socials.website)} target="_blank" rel="noopener noreferrer"
                 aria-label="Sito web"
                 className={`flex h-11 w-11 items-center justify-center rounded-full transition-all duration-200 active:scale-95 ${theme.social}`}>
                <Globe className="h-5 w-5" />
              </a>
            )}
          </div>
        )}

        {/* ── La colonna, nell'ordine scelto dall'operatore (LK6):
            lp.order = ["block:<nome>" | "link:<id>"], gia' completo e
            validato dal backend. Le voci senza contenuto (nessun
            ritiro, blocco spento, link disattivato) spariscono. */}
        <div className="mt-8 space-y-3.5">
          {(lp.order || []).map((key) => {
            if (key === 'block:upcoming') {
              if (blocks.upcoming === false || !next) return null;
              const Cmp = IN_FRAME ? 'a' : Link;
              const nav = IN_FRAME
                ? { href: next.url, target: '_blank', rel: 'noopener noreferrer' }
                : { to: next.url };
              seq += 1;
              return (
                <Cmp key={key} {...nav} data-testid="link-block-upcoming"
                     onClick={() => trackClick(org_slug, 'block:upcoming')}
                     style={rise(seq)}
                     className={`lk-rise block overflow-hidden rounded-2xl text-left transition-all duration-200 active:scale-[0.98] ${theme.card}`}>
                  <div className="flex items-stretch">
                    {next.cover_image_url && (
                      <img src={next.cover_image_url} alt=""
                           className="h-auto w-[88px] shrink-0 object-cover" />
                    )}
                    <div className="min-w-0 flex-1 px-4 py-3.5">
                      <p className={`text-[10px] font-bold uppercase tracking-[0.12em] ${theme.sub}`}>
                        <CalendarDays className="mr-1 inline h-3 w-3 align-[-1px]" />
                        {t('linkPage.next', { defaultValue: 'Prossimo ritiro' })}
                      </p>
                      <p className="mt-1 truncate text-[15px] font-bold leading-snug">{next.title}</p>
                      <p className={`mt-0.5 text-xs ${theme.sub}`}>
                        {dateLabel(next.start_at)}
                        {next.city ? ` · ${next.city}` : ''}
                        {next.price_from ? ` · da ${next.price_from} €` : ''}
                      </p>
                    </div>
                    <div className="flex items-center pr-4">
                      <ArrowRight className="h-4 w-4 opacity-50 transition-transform duration-200 group-hover:translate-x-0.5" />
                    </div>
                  </div>
                </Cmp>
              );
            }
            if (key === 'block:listino') {
              if (blocks.listino === false || !hasListino) return null;
              seq += 1;
              return (
                <div key={key} className="lk-rise" style={rise(seq)}>
                  <Row theme={theme} to={`/o/${org_slug}#listino`}
                       data-testid="link-block-listino"
                       onNavigate={() => trackClick(org_slug, 'block:listino')}>
                    {t('linkPage.book', { defaultValue: 'Prenota una seduta' })}
                  </Row>
                </div>
              );
            }
            if (key === 'block:whatsapp') {
              if (blocks.whatsapp === false || !lp.whatsapp) return null;
              seq += 1;
              return (
                <div key={key} className="lk-rise" style={rise(seq)}>
                  <Row theme={theme} href={`https://wa.me/${lp.whatsapp}`}
                       data-testid="link-block-whatsapp"
                       onNavigate={() => trackClick(org_slug, 'block:whatsapp')}>
                    <MessageCircle className="mr-1.5 inline h-4 w-4 align-[-2px]" />
                    {t('linkPage.whatsapp', { defaultValue: 'Scrivimi su WhatsApp' })}
                  </Row>
                </div>
              );
            }
            if (key === 'block:profile') {
              if (blocks.profile === false) return null;
              seq += 1;
              return (
                <div key={key} className="lk-rise" style={rise(seq)}>
                  <Row theme={theme} to={`/o/${org_slug}`}
                       data-testid="link-block-profile"
                       onNavigate={() => trackClick(org_slug, 'block:profile')}>
                    {t('linkPage.profile', { defaultValue: 'Scopri chi sono' })}
                  </Row>
                </div>
              );
            }
            if (key.startsWith('link:')) {
              const l = (lp.links || []).find((x) => `link:${x.id}` === key);
              if (!l) return null;
              seq += 1;
              return (
                <div key={key} className="lk-rise" style={rise(seq)}>
                  <Row theme={theme} href={l.url} data-linkid={l.id}
                       onNavigate={() => trackClick(org_slug, l.id)}>
                    {l.label}
                  </Row>
                </div>
              );
            }
            return null;
          })}
        </div>

        {/* ── Footer Aurya: il loop ─────────────────────────────────
            Non piu' una riga di testo con un link sottolineato: una
            card intera, tutta cliccabile, col gesto chiaro («Crea la
            tua pagina»). Chi non e' operatore la ignora; chi lo e'
            ha un bottone vero sotto il pollice. */}
        <footer className="lk-rise mt-auto pt-12" style={rise(9)}>
          <Link to={joinTo} data-testid="link-page-join"
                className={`group block rounded-3xl px-6 py-6 text-center transition-all duration-200 active:scale-[0.98] ${theme.cta}`}>
            {/* size xs = solo glifo + wordmark: il payoff vive gia'
                sotto la card, due taglines nella stessa vista stonano */}
            <span className="inline-flex justify-center opacity-90 transition-opacity group-hover:opacity-100">
              <BrandLogo size="xs" variant={lp.theme === 'notte' ? 'light' : 'dark'} />
            </span>
            <p className="mt-3 text-sm font-medium">
              {t('linkPage.footerAsk', { defaultValue: 'Sei un professionista del benessere?' })}
            </p>
            <span className={`mt-4 inline-flex items-center gap-2 rounded-full px-6 py-2.5 text-sm font-semibold transition-all duration-200 ${theme.ctaBtn}`}>
              {t('linkPage.footerCta', { defaultValue: 'Crea la tua pagina' })}
              <ArrowRight className="h-4 w-4 transition-transform duration-200 group-hover:translate-x-0.5" />
            </span>
          </Link>
          <p className={`mt-4 text-center text-[11px] ${theme.footer}`}>
            {t('linkPage.footerNote', { defaultValue: 'Ci si fida di qualcuno, non di qualcosa.' })}
          </p>
        </footer>
      </main>
    </div>
  );
}
