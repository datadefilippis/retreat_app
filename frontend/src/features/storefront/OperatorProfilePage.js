/**
 * OperatorProfilePage — /o/:org_slug (PR1+PR4, OPERATOR_PROFILE_REVIEWS_PLAN).
 *
 * La CARTA D'IDENTITÀ dell'operatore: hero con cover + badge fiducia
 * (anzianità, ritiri, ★rating), colonna contenuti (bio, galleria con
 * lightbox, prossimi ritiri, recensioni) + sidebar sticky (ritratto,
 * tagline, luogo→destinazione, lingue, social, contatti opt-in, store,
 * CTA recensione). Recensioni: flusso email→OTP→form (stesso pattern
 * UX del Passaporto), badge "Cliente verificato".
 */

import React, { useEffect, useState } from 'react';
import { useParams, useLocation, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { ArrowRight, Flower2, Play } from 'lucide-react';
import api from '../../api/client';
import { useSiteConfig } from '../../context/SiteConfigContext';
import useSeoMeta from './lib/useSeoMeta';
import useTrackView from './lib/useTrackView';
import MarketplaceShell from './components/MarketplaceShell';
// PV3 — la testata identitaria è condivisa con la pagina intervista
// (/o/:slug/intervista): stesso componente, continuità garantita.
import OperatorIdentityHeader from './components/OperatorIdentityHeader';
// PN3 — l'acquisto del servizio avviene TUTTO sul profilo: la riga di
// listino si espande su un harness che riusa il checkout dello storefront
// (CheckoutForm/OrderSummary/useCheckoutForm, zero fork di logica).
import InlineServiceCheckout from './components/checkout/InlineServiceCheckout';

function fmtPrice(n) {
  if (n == null) return null;
  try {
    return new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }).format(n);
  } catch { return `${n} €`; }
}
function fmtDates(s, e, lang = 'it-IT') {
  try {
    const d = new Date(s);
    const o = { day: 'numeric', month: 'short' };
    if (!e) return d.toLocaleDateString(lang, { ...o, year: 'numeric' });
    return `${d.toLocaleDateString(lang, o)} – ${new Date(e).toLocaleDateString(lang, { ...o, year: 'numeric' })}`;
  } catch { return s; }
}
function fmtDay(iso, lang = 'it-IT') {
  try {
    return new Date(iso).toLocaleDateString(lang, { day: 'numeric', month: 'long', year: 'numeric' });
  } catch { return (iso || '').slice(0, 10); }
}

const LANG_FLAGS = { it: '🇮🇹', en: '🇬🇧', de: '🇩🇪', fr: '🇫🇷', es: '🇪🇸', pt: '🇵🇹' };

function Stars({ value, size = 'text-sm' }) {
  const full = Math.round(value || 0);
  return (
    <span className={`${size} tracking-tight`} aria-label={`${value} su 5`}>
      <span className="text-amber-500">{'★'.repeat(full)}</span>
      <span className="text-gray-300">{'★'.repeat(5 - full)}</span>
    </span>
  );
}

// ── Galleria + lightbox (pattern M2) ─────────────────────────────────────────

function Gallery({ photos, name, t }) {
  const [open, setOpen] = useState(null);
  if (!photos?.length) return null;
  return (
    <section id="foto" className="mt-8">
      <h2 className="font-heading text-xl font-bold text-foreground mb-3">
        {t('landings:operator.gallery', { defaultValue: 'Foto' })}
      </h2>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
        {photos.map((url, i) => (
          <button key={url} type="button" onClick={() => setOpen(i)}
                  className="h-36 rounded-xl overflow-hidden bg-secondary group">
            <img src={url} alt={`${name} — foto ${i + 1}`} loading="lazy"
                 className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" />
          </button>
        ))}
      </div>
      {open != null && (
        <div className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center p-4"
             onClick={() => setOpen(null)} role="dialog" aria-modal="true">
          <img src={photos[open]} alt={`${name} — foto ${open + 1}`} className="max-h-[85vh] max-w-full rounded-lg" />
          <button type="button" aria-label="Chiudi"
                  className="absolute top-4 right-5 text-white text-3xl">×</button>
          {photos.length > 1 && (
            <button type="button" aria-label="Prossima"
                    onClick={(e) => { e.stopPropagation(); setOpen((open + 1) % photos.length); }}
                    className="absolute right-5 top-1/2 text-white text-4xl">›</button>
          )}
        </div>
      )}
    </section>
  );
}

// ── Recensioni (PR4) ─────────────────────────────────────────────────────────

function WriteReviewModal({ orgSlug, onClose, onDone, t, i18n }) {
  const [step, setStep] = useState('email');   // email → code → form → done
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [rating, setRating] = useState(5);
  const [body, setBody] = useState('');
  const [name, setName] = useState('');
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const lang = (i18n.language || 'it').slice(0, 2);

  const requestOtp = async (e) => {
    e.preventDefault();
    setBusy(true); setError(null);
    try {
      await api.post('/public/reviews/request-otp', { org_slug: orgSlug, email, language: lang });
      setStep('code');
    } catch {
      setError(t('landings:reviews.genericError', { defaultValue: 'Qualcosa non ha funzionato, riprova.' }));
    } finally { setBusy(false); }
  };

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true); setError(null);
    try {
      await api.post('/public/reviews/submit', {
        org_slug: orgSlug, email, code, rating, body,
        author_name: name, language: lang, website: '',
      });
      setStep('done');
      onDone?.();
    } catch (err) {
      const d = err?.response?.data?.detail;
      setError(d?.message || t('landings:reviews.genericError', { defaultValue: 'Qualcosa non ha funzionato, riprova.' }));
    } finally { setBusy(false); }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4"
         role="dialog" aria-modal="true">
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
        <div className="flex items-start justify-between mb-4">
          <h3 className="font-heading text-lg font-bold text-foreground">
            {t('landings:reviews.writeTitle', { defaultValue: 'Scrivi una recensione' })}
          </h3>
          <button type="button" onClick={onClose} aria-label="Chiudi"
                  className="text-gray-400 hover:text-gray-600 text-xl leading-none">×</button>
        </div>

        {step === 'email' && (
          <form onSubmit={requestOtp} className="space-y-3">
            <p className="text-sm text-muted-foreground">
              {t('landings:reviews.emailIntro', { defaultValue: 'Usa l\'email con cui hai prenotato: ti mandiamo un codice per verificare che sia tu.' })}
            </p>
            <input type="email" required value={email} onChange={e => setEmail(e.target.value)}
                   placeholder="la-tua@email.com"
                   className="w-full rounded-lg border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40" />
            <button type="submit" disabled={busy}
                    className="w-full rounded-full bg-primary text-white py-2.5 text-sm font-semibold disabled:opacity-60">
              {t('landings:reviews.sendCode', { defaultValue: 'Inviami il codice' })}
            </button>
          </form>
        )}

        {step === 'code' && (
          <form onSubmit={(e) => { e.preventDefault(); setStep('form'); }} className="space-y-3">
            <p className="text-sm text-muted-foreground">
              {t('landings:reviews.codeIntro', { defaultValue: 'Ti abbiamo inviato un codice a 6 cifre. Inseriscilo qui:' })}
            </p>
            <input inputMode="numeric" autoComplete="one-time-code" required
                   minLength={6} maxLength={6} value={code}
                   onChange={e => setCode(e.target.value.replace(/\D/g, ''))}
                   className="w-full rounded-lg border border-border px-3 py-2 text-center text-2xl tracking-[0.4em] focus:outline-none focus:ring-2 focus:ring-primary/40" />
            <button type="submit" disabled={busy || code.length !== 6}
                    className="w-full rounded-full bg-primary text-white py-2.5 text-sm font-semibold disabled:opacity-60">
              {t('landings:reviews.continue', { defaultValue: 'Continua' })}
            </button>
          </form>
        )}

        {step === 'form' && (
          <form onSubmit={submit} className="space-y-3">
            <div className="flex items-center gap-1" role="radiogroup" aria-label="Valutazione">
              {[1, 2, 3, 4, 5].map(v => (
                <button key={v} type="button" onClick={() => setRating(v)}
                        aria-label={`${v} stelle`}
                        className={`text-3xl ${v <= rating ? 'text-amber-500' : 'text-gray-300'}`}>★</button>
              ))}
            </div>
            <input required value={name} onChange={e => setName(e.target.value)}
                   maxLength={60}
                   placeholder={t('landings:reviews.namePlaceholder', { defaultValue: 'Il tuo nome (visibile)' })}
                   className="w-full rounded-lg border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40" />
            <textarea required minLength={20} maxLength={1500} rows={5}
                      value={body} onChange={e => setBody(e.target.value)}
                      placeholder={t('landings:reviews.bodyPlaceholder', { defaultValue: 'Com\'è andata? Racconta la tua esperienza (min 20 caratteri)…' })}
                      className="w-full rounded-lg border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40" />
            {/* honeypot: invisibile agli umani */}
            <input type="text" name="website" tabIndex={-1} autoComplete="off"
                   className="hidden" aria-hidden="true" />
            <button type="submit" disabled={busy || body.length < 20}
                    className="w-full rounded-full bg-accent text-accent-foreground py-2.5 text-sm font-bold disabled:opacity-60">
              {t('landings:reviews.publish', { defaultValue: 'Pubblica la recensione' })}
            </button>
          </form>
        )}

        {step === 'done' && (
          <div className="text-center py-4">
            <p className="text-3xl mb-2" aria-hidden>🙏</p>
            <p className="font-semibold text-foreground">
              {t('landings:reviews.thanks', { defaultValue: 'Grazie della tua recensione!' })}
            </p>
            <button type="button" onClick={onClose}
                    className="mt-4 rounded-full bg-primary text-white px-6 py-2 text-sm font-semibold">
              {t('landings:reviews.close', { defaultValue: 'Chiudi' })}
            </button>
          </div>
        )}

        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
      </div>
    </div>
  );
}

function ReviewsSection({ orgSlug, stats, onWrite, refreshKey, t, i18n }) {
  const [data, setData] = useState(null);
  const [page, setPage] = useState(1);

  useEffect(() => {
    let mounted = true;
    api.get(`/public/reviews/${orgSlug}`, { params: { page } })
      .then(res => {
        if (!mounted) return;
        setData(prev => page === 1 ? res.data
          : { ...res.data, items: [...(prev?.items || []), ...res.data.items] });
      })
      .catch(() => { if (mounted) setData({ items: [], total: 0 }); });
    return () => { mounted = false; };
  }, [orgSlug, page, refreshKey]);

  const items = data?.items || [];
  const total = data?.total || 0;
  const dist = stats?.distribution || {};
  const maxDist = Math.max(1, ...Object.values(dist));

  return (
    <section id="recensioni" className="mt-10 scroll-mt-20">
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-heading text-xl font-bold text-foreground">
          {t('landings:reviews.heading', { defaultValue: 'Recensioni' })}
          {total > 0 && <span className="text-muted-foreground font-normal text-base"> ({total})</span>}
        </h2>
        <button type="button" onClick={onWrite}
                className="rounded-full border border-primary text-primary px-4 py-1.5 text-sm font-semibold hover:bg-primary hover:text-white transition-colors">
          {t('landings:reviews.writeCta', { defaultValue: 'Scrivi una recensione' })}
        </button>
      </div>

      {stats?.count > 0 && (
        <div className="mb-6 flex flex-col sm:flex-row gap-6 rounded-2xl border border-border bg-card p-5">
          <div className="text-center sm:text-left">
            <p className="text-4xl font-bold text-foreground">{stats.avg}</p>
            <Stars value={stats.avg} size="text-lg" />
            <p className="text-xs text-muted-foreground mt-1">
              {t('landings:reviews.basedOn', { count: stats.count, defaultValue: 'su {{count}} recensioni' })}
            </p>
          </div>
          <div className="flex-1 space-y-1">
            {[5, 4, 3, 2, 1].map(v => (
              <div key={v} className="flex items-center gap-2 text-xs">
                <span className="w-3 text-muted-foreground">{v}</span>
                <div className="flex-1 h-2 rounded-full bg-secondary overflow-hidden">
                  <div className="h-full bg-amber-400"
                       style={{ width: `${((dist[String(v)] || 0) / maxDist) * 100}%` }} />
                </div>
                <span className="w-6 text-right text-muted-foreground">{dist[String(v)] || 0}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {items.length === 0 ? (
        <p className="text-muted-foreground text-sm">
          {t('landings:reviews.empty', { defaultValue: 'Ancora nessuna recensione. Hai prenotato con questo operatore? Racconta com\'è andata.' })}
        </p>
      ) : (
        <div className="space-y-4">
          {items.map(r => (
            <article key={r.id} className="rounded-2xl border border-border bg-card p-4">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-semibold text-foreground">{r.author_name}</span>
                {r.verified && (
                  <span className="rounded-full bg-primary/10 text-primary px-2 py-0.5 text-[11px] font-medium">
                    ✓ {t('landings:reviews.verified', { defaultValue: 'Cliente verificato' })}
                  </span>
                )}
                <span className="ml-auto text-xs text-muted-foreground">
                  {fmtDay(r.created_at, i18n.language)}
                  {r.edited && <> · {t('landings:reviews.edited', { defaultValue: 'aggiornata' })}</>}
                </span>
              </div>
              <Stars value={r.rating} />
              {r.title && <p className="font-medium text-foreground mt-1">{r.title}</p>}
              <p className="text-sm text-gray-700 mt-1 whitespace-pre-line">{r.body}</p>
              {r.reply?.body && (
                <div className="mt-3 rounded-xl bg-secondary/60 p-3 border-l-2 border-primary">
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-primary mb-1">
                    {t('landings:reviews.operatorReply', { defaultValue: 'Risposta dell\'organizzatore' })}
                  </p>
                  <p className="text-sm text-gray-700 whitespace-pre-line">{r.reply.body}</p>
                </div>
              )}
            </article>
          ))}
          {items.length < total && (
            <button type="button" onClick={() => setPage(p => p + 1)}
                    className="w-full rounded-full border border-border py-2 text-sm font-medium text-foreground hover:border-primary">
              {t('landings:reviews.showMore', { defaultValue: 'Mostra altre' })}
            </button>
          )}
        </div>
      )}
    </section>
  );
}

// ── Pagina ───────────────────────────────────────────────────────────────────

export default function OperatorProfilePage() {
  const { org_slug } = useParams();
  // VT2 — visita al profilo per lo specchietto Visibilità (ping 3s)
  useTrackView('profile', org_slug);
  const { t, i18n } = useTranslation('landings');
  // RT3 — la fase decide se mostrare i ritiri prenotabili
  const { sitePhase } = useSiteConfig();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [writeOpen, setWriteOpen] = useState(false);
  const [reviewsKey, setReviewsKey] = useState(0);
  // PN3 — riga di listino espansa (una alla volta): l'acquisto avviene
  // in pagina, niente navigazione verso /p/ come CTA primaria.
  const [expandedService, setExpandedService] = useState(null);

  // OP2 — il profilo parla la lingua del viaggiatore: fetch con lang e
  // refetch al cambio lingua (bio/tagline tradotte dove l'operatore le
  // ha compilate, italiano altrimenti).
  const uiLang = (i18n.language || 'it').slice(0, 2);
  useEffect(() => {
    let mounted = true;
    api.get(`/public/operator/${org_slug}`,
            { params: uiLang !== 'it' ? { lang: uiLang } : {} })
      .then(res => { if (mounted) setData(res.data); })
      .catch(err => { if (mounted) setNotFound(err?.response?.status === 404); })
      .finally(() => { if (mounted) setLoading(false); });
    return () => { mounted = false; };
  }, [org_slug, uiLang]);

  // PV3 — arrivo dalle CTA della pagina intervista (#ritiri, #listino,
  // #recensioni): a dati pronti si scorre all'ancora, così le due
  // pagine si comportano come un'unica scheda. (ScrollToTop in App.js
  // riparte dall'alto al cambio pathname: qui si corregge dopo.)
  const { hash } = useLocation();
  useEffect(() => {
    if (!data || !hash) return;
    const el = document.getElementById(hash.slice(1));
    if (el) {
      // behavior auto (salto secco): lo smooth viene cancellato dai
      // reflow delle immagini che arrivano subito dopo il fetch.
      const id = setTimeout(() => el.scrollIntoView({ block: 'start' }), 120);
      return () => clearTimeout(id);
    }
    return undefined;
  }, [data, hash]);

  const rs = data?.reviews_stats;
  useSeoMeta({
    title: data?.name
      ? `${data.name}${data.city ? ` · ritiri a ${data.city}` : ''} · profilo organizzatore`
      : undefined,
    description: (data?.tagline || data?.bio)
      ? String(data.tagline || data.bio).slice(0, 155) : undefined,
    image: data?.cover_url || data?.logo_url || undefined,
    canonicalPath: `/o/${org_slug}`,
    // SEO1 — LocalBusiness geo-taggato allineato allo shell: address + geo
    // + rating + sameAs (evita che l'hydration sovrascriva con schema povero).
    jsonLd: data?.name ? {
      '@context': 'https://schema.org',
      '@type': 'LocalBusiness',
      name: data.name,
      url: `${window.location.origin}/o/${org_slug}`,
      ...(data.logo_url ? { image: data.logo_url } : {}),
      ...(data.bio ? { description: String(data.bio).slice(0, 300) } : {}),
      ...(data.founded_year ? { foundingDate: String(data.founded_year) } : {}),
      ...((data.city || data.region) ? {
        address: {
          '@type': 'PostalAddress',
          ...(data.city ? { addressLocality: data.city } : {}),
          ...(data.region ? { addressRegion: data.region } : {}),
        },
      } : {}),
      ...(data.latitude != null && data.longitude != null ? {
        geo: {
          '@type': 'GeoCoordinates',
          latitude: data.latitude,
          longitude: data.longitude,
        },
      } : {}),
      ...(Object.keys(data.socials || {}).length > 0
        ? { sameAs: Object.values(data.socials).map(u =>
            String(u).startsWith('http') ? u : `https://${u}`) } : {}),
      ...(rs?.count > 0 ? {
        aggregateRating: {
          '@type': 'AggregateRating',
          ratingValue: rs.avg, reviewCount: rs.count,
          bestRating: 5, worstRating: 1,
        },
      } : {}),
    } : undefined,
  });

  if (loading) return <div className="min-h-screen flex items-center justify-center text-gray-400">…</div>;
  if (notFound || !data) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-2">
        <p className="text-lg font-semibold text-gray-900">{t('landings:operator.notFound')}</p>
        <Link to="/" className="text-emerald-700 underline">{t('landings:operator.backToCalendar')}</Link>
      </div>
    );
  }

  const socials = data.socials || {};
  const extUrl = (u) => (u && !u.startsWith('http') ? `https://${u}` : u);
  const placeSlug = (data.region || data.city)
    ? String(data.region || data.city).toLowerCase().normalize('NFKD')
        .replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '')
    : null;

  return (
    <MarketplaceShell>
    <div className="bg-gray-50">
      <div className="max-w-6xl mx-auto px-4 pt-3">
        <nav className="text-xs text-gray-500">
          <Link to="/operatori" className="hover:text-primary hover:underline">
            {t('landings:operators.heading', { defaultValue: 'Organizzatori' })}
          </Link>
          <span className="mx-1.5" aria-hidden>›</span>
          <span className="text-gray-700">{data.name}</span>
        </nav>
      </div>

      {/* ── Hero — testata identitaria condivisa con /o/:slug/intervista (PV3) ── */}
      <OperatorIdentityHeader data={data} t={t} />

      {/* ── Due colonne ── */}
      <main className="max-w-6xl mx-auto px-4 py-8 grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-8">
        {/* mobile: la carta d'identità (foto profilo) sale sotto la
            copertina, prima della descrizione (order); desktop: torna
            colonna destra */}
        <div className="min-w-0 order-2 lg:order-1">
          {data.bio && (
            <section id="chi-siamo">
              <h2 className="font-heading text-xl font-bold text-foreground mb-3">
                {t('landings:operator.about', { defaultValue: 'Chi siamo' })}
              </h2>
              <p className="text-gray-700 leading-relaxed whitespace-pre-line">{data.bio}</p>
            </section>
          )}

          {/* PV3 — l'intervista integrale vive su pagina propria
              (/o/:slug/intervista): qui resta un blocco compatto con
              la prima domanda come anteprima e il bottone di lettura.
              L'ancora #intervista continua a rispondere. */}
          {Array.isArray(data.interview) && data.interview.length > 0 && (
            <section id="intervista" className="mt-8 scroll-mt-20" data-testid="interview-teaser">
              <h2 className="font-heading text-xl font-bold text-foreground mb-1">
                {t('landings:operator.interviewTitle', { defaultValue: 'L’intervista' })}
              </h2>
              <p className="text-sm text-gray-500 mb-4">
                {t('landings:operator.interviewSub', { defaultValue: 'Le parole di chi c’è dietro, raccolte da Aurya.' })}
              </p>
              <div className="rounded-2xl border border-gray-200 bg-white p-5">
                <h3 className="font-heading font-semibold text-[#376254] leading-snug">
                  {data.interview[0].question}
                </h3>
                <p className="text-gray-700 leading-relaxed mt-1.5 line-clamp-3">
                  {data.interview[0].answer}
                </p>
                <div className="mt-4 flex flex-wrap items-center gap-3">
                  <Link to={`/o/${org_slug}/intervista`} data-testid="read-interview-cta"
                        className="inline-flex items-center gap-1.5 rounded-full bg-[#376254] px-5 py-2 text-sm font-semibold text-white hover:bg-[#2c4f43] transition-colors">
                    {t('landings:operator.interviewReadCta', { defaultValue: 'Leggi l’intervista' })}
                    <ArrowRight className="h-4 w-4" aria-hidden />
                  </Link>
                  {data.interview_video_url && (
                    <span className="inline-flex items-center gap-1 text-xs font-medium text-gray-500">
                      <Play className="h-3.5 w-3.5 text-[#8a7440]" aria-hidden />
                      {t('landings:operator.interviewHasVideo', { defaultValue: 'Con video' })}
                    </span>
                  )}
                </div>
              </div>
            </section>
          )}

          {/* TW2+PN3 (piano Profilo=Negozio) — il profilo E' il negozio:
              i servizi a listino con la porta d'azione per riga. Il
              bottone ESPANDE la riga e l'acquisto avviene in pagina
              (InlineServiceCheckout riusa il checkout dello storefront).
              La landing /p/ resta come link secondario "Vedi dettagli". */}
          {Array.isArray(data.listino) && data.listino.length > 0 && (
            <section id="listino" className="mt-8 scroll-mt-20" data-testid="profile-listino">
              <h2 className="font-heading text-xl font-bold text-foreground mb-3">
                {t('landings:operator.listino', { defaultValue: 'Servizi e prezzi' })}
              </h2>
              <div className="overflow-hidden rounded-2xl border border-gray-200 bg-white divide-y divide-gray-100">
                {data.listino.map((row) => {
                  const rowKey = row.product_id || row.slug || row.name;
                  const expanded = expandedService === rowKey;
                  return (
                  <div key={rowKey}>
                    <div className="flex flex-wrap items-center gap-3 px-4 py-3">
                      <div className="min-w-0 flex-1">
                        <p className="font-medium text-gray-900">{row.name}</p>
                        <p className="text-xs text-gray-500">
                          {[row.duration_minutes ? `${row.duration_minutes} min` : null,
                            row.service_mode === 'online'
                              ? t('landings:operator.svcOnline', { defaultValue: 'Online' })
                              : row.service_mode === 'both'
                                ? t('landings:operator.svcBoth', { defaultValue: 'In presenza oppure online' })
                                : t('landings:operator.svcInPerson', { defaultValue: 'In presenza' }),
                          ].filter(Boolean).join(' · ')}
                        </p>
                        {row.note && (
                          <p className="mt-0.5 text-xs text-gray-400">{row.note}</p>
                        )}
                        {/* PN3 — la landing /p/ resta viva come approfondimento */}
                        {row.slug && (
                          <Link to={`/p/${org_slug}/${row.slug}`}
                                className="mt-0.5 inline-block text-xs text-gray-500 underline hover:text-gray-800">
                            {t('landings:operator.viewDetails', { defaultValue: 'Vedi dettagli' })}
                          </Link>
                        )}
                      </div>
                      <span className="text-sm font-semibold text-gray-900 whitespace-nowrap">
                        {row.on_request
                          ? t('landings:operator.priceOnRequest', { defaultValue: 'Su richiesta' })
                          : (row.price != null ? `${Number(row.price).toFixed(0)} €` : '')}
                      </span>
                      {row.product_id ? (
                        <button type="button"
                                data-testid="listino-cta"
                                aria-expanded={expanded}
                                onClick={() => setExpandedService(expanded ? null : rowKey)}
                                className={`shrink-0 rounded-full px-4 py-1.5 text-xs font-semibold transition-colors ${
                                  expanded
                                    ? 'border border-[#376254] text-[#376254] bg-white hover:bg-gray-50'
                                    : 'bg-[#376254] text-white hover:bg-[#2c4f43]'
                                }`}>
                          {expanded
                            ? t('landings:operator.inlineClose', { defaultValue: 'Chiudi' })
                            : row.transaction_mode === 'direct'
                              ? t('landings:operator.book', { defaultValue: 'Prenota' })
                              : t('landings:operator.requestAppt', { defaultValue: 'Richiedi appuntamento' })}
                        </button>
                      ) : row.slug ? (
                        <Link to={`/p/${org_slug}/${row.slug}`}
                              className="shrink-0 rounded-full bg-[#376254] px-4 py-1.5 text-xs font-semibold text-white hover:bg-[#2c4f43]">
                          {row.transaction_mode === 'direct'
                            ? t('landings:operator.book', { defaultValue: 'Prenota' })
                            : t('landings:operator.requestAppt', { defaultValue: 'Richiedi appuntamento' })}
                        </Link>
                      ) : null}
                    </div>
                    {expanded && row.product_id && (
                      <div className="border-t border-gray-100 bg-gray-50/70 px-3 py-4 sm:px-4"
                           data-testid="inline-checkout-panel">
                        <InlineServiceCheckout
                          orgSlug={org_slug}
                          row={row}
                          onClose={() => setExpandedService(null)}
                        />
                      </div>
                    )}
                  </div>
                  );
                })}
              </div>
              {/* RS3 Patti chiari — le condizioni dell'operatore a un
                  click dal listino (la pagina risponde sempre) */}
              <a href={`/s/${org_slug}/terms`} target="_blank" rel="noreferrer"
                 data-testid="profile-conditions"
                 className="mt-2 inline-block text-xs text-gray-500 underline hover:text-gray-800">
                {t('landings:operator.conditions', { defaultValue: 'Condizioni di vendita di {{name}}', name: data.name })}
              </a>
            </section>
          )}

          <Gallery photos={data.photos} name={data.name} t={t} />

          {/* PN0 — il profilo e' la vetrina dell'operatore: i suoi
              ritiri pubblicati si vedono SEMPRE, anche in fase network
              e anche senza Stripe (il gate GT1b vale solo per la
              directory, non per la pagina personale) */}
          {true && (
          <section id="ritiri" className="mt-8 scroll-mt-20">
            <h2 className="font-heading text-xl font-bold text-foreground mb-3">
              {t('landings:operator.upcoming', { count: data.upcoming_count })}
            </h2>
            {data.upcoming.length === 0 ? (
              <p className="text-gray-500">{t('landings:operator.noUpcoming')}</p>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {data.upcoming.map(item => (
                  <Link key={item.url} to={item.url}
                    className="rounded-2xl border border-gray-200 bg-white overflow-hidden hover:shadow-md transition-shadow">
                    <div className="h-36 bg-gray-100">
                      {item.cover_image_url
                        ? <img src={item.cover_image_url} alt={item.title} loading="lazy" className="w-full h-full object-cover" />
                        : <div className="w-full h-full flex items-center justify-center" aria-hidden><Flower2 className="h-8 w-8 text-[#376254]/40" /></div>}
                    </div>
                    <div className="p-3">
                      <h3 className="font-semibold text-gray-900 line-clamp-2">{item.title}</h3>
                      <p className="text-sm text-gray-600 mt-0.5">
                        {fmtDates(item.start_at, item.end_at, i18n.language)}
                        {(item.city || item.region) && <> · {[item.city, item.region].filter(Boolean).join(', ')}</>}
                      </p>
                      {item.price_from != null && (
                        <p className="font-bold text-gray-900 mt-1">
                          {t('landings:calendar.priceFrom', { price: fmtPrice(item.price_from) })}
                        </p>
                      )}
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </section>
          )}

          <ReviewsSection orgSlug={org_slug} stats={rs}
                          onWrite={() => setWriteOpen(true)}
                          refreshKey={reviewsKey} t={t} i18n={i18n} />
        </div>

        {/* ── Sidebar carta d'identità ── */}
        <aside className="order-1 lg:order-2 lg:sticky lg:top-20 self-start space-y-4">
          <div className="rounded-2xl border border-border bg-card p-5">
            {data.portrait_url && (
              <img src={data.portrait_url} alt={data.name}
                   className="w-full h-52 rounded-xl object-cover mb-4" />
            )}
            {data.tagline && (
              <p className="text-sm text-gray-700 italic mb-3">"{data.tagline}"</p>
            )}
            <dl className="space-y-2 text-sm">
              {(data.city || data.region) && (
                <div className="flex items-start gap-2">
                  <span aria-hidden>📍</span>
                  {placeSlug ? (
                    <Link to={`/destinazioni/${placeSlug}`} className="text-primary hover:underline">
                      {[data.city, data.region].filter(Boolean).join(', ')}
                    </Link>
                  ) : (
                    <span className="text-gray-700">{[data.city, data.region].filter(Boolean).join(', ')}</span>
                  )}
                </div>
              )}
              {data.languages?.length > 0 && (
                <div className="flex items-start gap-2">
                  <span aria-hidden>💬</span>
                  <span className="text-gray-700">
                    {data.languages.map(l => `${LANG_FLAGS[l] || ''} ${l.toUpperCase()}`).join(' · ')}
                  </span>
                </div>
              )}
              {data.contacts?.public_email && (
                <div className="flex items-start gap-2">
                  <span aria-hidden>✉️</span>
                  <a href={`mailto:${data.contacts.public_email}`}
                     className="text-primary hover:underline break-all">{data.contacts.public_email}</a>
                </div>
              )}
              {data.contacts?.public_phone && (
                <div className="flex items-start gap-2">
                  <span aria-hidden>📞</span>
                  <span className="text-gray-700">{data.contacts.public_phone}</span>
                </div>
              )}
            </dl>
            {(socials.instagram || socials.website || socials.facebook) && (
              <div className="mt-4 pt-3 border-t border-border flex flex-wrap gap-3 text-sm">
                {socials.instagram && (
                  <a href={extUrl(socials.instagram)} target="_blank" rel="noreferrer"
                     className="text-primary hover:underline">Instagram</a>
                )}
                {socials.website && (
                  <a href={extUrl(socials.website)} target="_blank" rel="noreferrer"
                     className="text-primary hover:underline">
                    {t('landings:operator.website', { defaultValue: 'Sito web' })}
                  </a>
                )}
                {socials.facebook && (
                  <a href={extUrl(socials.facebook)} target="_blank" rel="noreferrer"
                     className="text-primary hover:underline">Facebook</a>
                )}
              </div>
            )}
          </div>

          {/* PN0 — via "Visita il negozio": il profilo E' il negozio
              (il listino e i ritiri si comprano da qui) */}
          <button type="button" onClick={() => setWriteOpen(true)}
                  className="block w-full rounded-2xl border border-primary text-primary text-center px-4 py-3 text-sm font-semibold hover:bg-primary hover:text-white transition-colors">
            ★ {t('landings:reviews.writeCta', { defaultValue: 'Scrivi una recensione' })}
          </button>
        </aside>
      </main>

      {writeOpen && (
        <WriteReviewModal orgSlug={org_slug} t={t} i18n={i18n}
                          onClose={() => setWriteOpen(false)}
                          onDone={() => setReviewsKey(k => k + 1)} />
      )}
    </div>
    </MarketplaceShell>
  );
}
