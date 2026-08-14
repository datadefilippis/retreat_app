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
   un set chiuso di classi: la scelta cambia atmosfera, mai struttura. */
export const LINK_THEMES = {
  salvia: {
    page: 'bg-[#edf1e8]',
    text: 'text-stone-800', sub: 'text-stone-500',
    card: 'bg-white border border-stone-200 text-stone-800 shadow-sm hover:shadow-md hover:border-[#8a9979]',
    hero: 'text-stone-900',
    ring: 'ring-[#8a9979]/40',
    footer: 'text-stone-500',
  },
  terra: {
    page: 'bg-gradient-to-b from-[#f7ebdf] via-[#f2ddc9] to-[#ecd0b6]',
    text: 'text-stone-800', sub: 'text-stone-500',
    card: 'bg-white/90 backdrop-blur border border-orange-900/10 text-stone-800 shadow-sm hover:shadow-md hover:border-orange-900/30',
    hero: 'text-stone-900',
    ring: 'ring-orange-900/25',
    footer: 'text-stone-500',
  },
  notte: {
    page: 'bg-[#181c19]',
    text: 'text-stone-100', sub: 'text-stone-400',
    card: 'bg-white/[0.07] border border-white/15 text-stone-100 hover:bg-white/[0.14]',
    hero: 'text-white',
    ring: 'ring-white/30',
    footer: 'text-stone-400',
  },
  carta: {
    page: 'bg-[#fdfcf9]',
    text: 'text-stone-900', sub: 'text-stone-500',
    card: 'bg-white border-2 border-stone-900 text-stone-900 hover:bg-stone-900 hover:text-white',
    hero: 'text-stone-900',
    ring: 'ring-stone-900/30',
    footer: 'text-stone-500',
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

/* Una riga cliccabile della colonna: stessa forma per blocchi vivi e
   link personalizzati — la pagina resta UNA cosa, non due liste. */
function Row({ theme, children, onNavigate, ...linkProps }) {
  const cls = `block w-full rounded-2xl px-5 py-4 text-center text-[15px] font-semibold transition-all ${theme.card}`;
  return linkProps.to
    ? <Link {...linkProps} onClick={onNavigate} className={cls}>{children}</Link>
    : <a {...linkProps} onClick={onNavigate} className={cls} target="_blank" rel="noopener noreferrer">{children}</a>;
}

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

  return (
    <div className={`min-h-screen ${theme.page} ${theme.text}`} data-testid="link-page">
      <main className="mx-auto flex min-h-screen w-full max-w-md flex-col px-5 pb-10 pt-12">

        {/* ── Identita' ─────────────────────────────────────────── */}
        <header className="text-center">
          {data.portrait_url && (
            <img src={data.portrait_url} alt={data.name}
                 className={`mx-auto h-24 w-24 rounded-full object-cover ring-4 ${theme.ring}`} />
          )}
          <h1 className={`mt-4 font-display text-2xl font-bold ${theme.hero}`}>
            {data.name}
          </h1>
          {data.interview_verified_at && (
            <div className="mt-2 flex justify-center">
              <VerifiedAuryaBadge size="sm"
                variant={lp.theme === 'notte' ? 'on-photo' : 'on-light'} />
            </div>
          )}
          {data.tagline && (
            <p className={`mt-2 text-sm leading-relaxed ${theme.sub}`}>{data.tagline}</p>
          )}
        </header>

        {/* ── Social ────────────────────────────────────────────── */}
        {blocks.socials !== false && (socials.instagram || socials.facebook || socials.website) && (
          <div className="mt-5 flex justify-center gap-5">
            {socials.instagram && (
              <a href={httpsify(socials.instagram)} target="_blank" rel="noopener noreferrer"
                 aria-label="Instagram" className="opacity-80 hover:opacity-100">
                <Instagram className="h-5 w-5" />
              </a>
            )}
            {socials.facebook && (
              <a href={httpsify(socials.facebook)} target="_blank" rel="noopener noreferrer"
                 aria-label="Facebook" className="opacity-80 hover:opacity-100">
                <Facebook className="h-5 w-5" />
              </a>
            )}
            {socials.website && (
              <a href={httpsify(socials.website)} target="_blank" rel="noopener noreferrer"
                 aria-label="Sito web" className="opacity-80 hover:opacity-100">
                <Globe className="h-5 w-5" />
              </a>
            )}
          </div>
        )}

        {/* ── Blocchi vivi + link personalizzati ───────────────── */}
        <div className="mt-7 space-y-3">

          {/* Il prossimo ritiro: l'unico blocco "ricco" — e' la cosa
              piu' preziosa che l'operatore ha da mostrare */}
          {blocks.upcoming !== false && next && (
            <Link to={next.url} data-testid="link-block-upcoming"
                  onClick={() => trackClick(org_slug, 'block:upcoming')}
                  className={`block overflow-hidden rounded-2xl text-left transition-all ${theme.card}`}>
              <div className="flex items-stretch">
                {next.cover_image_url && (
                  <img src={next.cover_image_url} alt=""
                       className="h-auto w-24 shrink-0 object-cover" />
                )}
                <div className="min-w-0 flex-1 px-4 py-3">
                  <p className={`text-[11px] font-semibold uppercase tracking-wide ${theme.sub}`}>
                    <CalendarDays className="mr-1 inline h-3 w-3 align-[-1px]" />
                    {t('linkPage.next', { defaultValue: 'Prossimo ritiro' })}
                  </p>
                  <p className="mt-0.5 truncate text-[15px] font-bold">{next.title}</p>
                  <p className={`mt-0.5 text-xs ${theme.sub}`}>
                    {dateLabel(next.start_at)}
                    {next.city ? ` · ${next.city}` : ''}
                    {next.price_from ? ` · da ${next.price_from} €` : ''}
                  </p>
                </div>
                <div className="flex items-center pr-4">
                  <ArrowRight className="h-4 w-4 opacity-60" />
                </div>
              </div>
            </Link>
          )}

          {blocks.listino !== false && hasListino && (
            <Row theme={theme} to={`/o/${org_slug}#listino`} data-testid="link-block-listino"
                 onNavigate={() => trackClick(org_slug, 'block:listino')}>
              {t('linkPage.book', { defaultValue: 'Prenota una seduta' })}
            </Row>
          )}

          {blocks.whatsapp !== false && lp.whatsapp && (
            <Row theme={theme} href={`https://wa.me/${lp.whatsapp}`} data-testid="link-block-whatsapp"
                 onNavigate={() => trackClick(org_slug, 'block:whatsapp')}>
              <MessageCircle className="mr-1.5 inline h-4 w-4 align-[-2px]" />
              {t('linkPage.whatsapp', { defaultValue: 'Scrivimi su WhatsApp' })}
            </Row>
          )}

          {/* i link personalizzati dell'operatore, nel suo ordine */}
          {(lp.links || []).map((l) => (
            <Row key={l.id} theme={theme} href={l.url} data-linkid={l.id}
                 onNavigate={() => trackClick(org_slug, l.id)}>
              {l.label}
            </Row>
          ))}

          {blocks.profile !== false && (
            <Row theme={theme} to={`/o/${org_slug}`} data-testid="link-block-profile"
                 onNavigate={() => trackClick(org_slug, 'block:profile')}>
              {t('linkPage.profile', { defaultValue: 'Scopri chi sono' })}
            </Row>
          )}
        </div>

        {/* ── Footer Aurya: il loop ─────────────────────────────── */}
        <footer className="mt-auto pt-12 text-center">
          <Link to="/" aria-label="Aurya" className="inline-block opacity-90 hover:opacity-100">
            <BrandLogo size="sm" variant={lp.theme === 'notte' ? 'light' : 'dark'} />
          </Link>
          <p className={`mt-3 text-xs ${theme.footer}`}>
            {t('linkPage.footerAsk', { defaultValue: 'Sei un professionista del benessere?' })}
            {' '}
            <Link to={joinTo} className="font-semibold underline underline-offset-2"
                  data-testid="link-page-join">
              {t('linkPage.footerCta', { defaultValue: 'Iscriviti' })}
            </Link>
          </p>
        </footer>
      </main>
    </div>
  );
}
