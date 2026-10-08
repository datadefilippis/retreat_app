/**
 * CorsoLandingPage — LA PAGINA DI UN CORSO (AC3, 7/10/2026).
 * Rotta: /corso/:org_slug/:slug — come /prodotto e /e: un link da condividere.
 *
 * In alto il VIDEO DI PRESENTAZIONE (se l'operatore l'ha caricato) o la
 * copertina; poi chi insegna, descrizione, prezzo, durata dell'accesso,
 * «Compra» in pagina (stesso checkout del profilo: account Aurya + Stripe),
 * «Condividi». Sotto: il PROGRAMMA con moduli e lezioni — le lezioni
 * segnate come anteprima si guardano gratis, qui, senza comprare — poi il
 * racconto, chi insegna, altri corsi dell'operatore. Su telefono la barra
 * con prezzo e «Compra» resta in basso.
 *
 * Dati: GET /public/corso/{org}/{slug} (dal public_slug); anteprime:
 * POST /public/corso/{org}/{slug}/anteprima/{lezione|trailer}/play-url.
 */
import React, { useEffect, useRef, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { ArrowLeft, Check, Share2, ShieldCheck, Play, FileText, Film, Music, Waves, Paperclip, Clock, Infinity as InfinityIcon, SearchX, GraduationCap } from 'lucide-react';
import AudioPlayer from '../accademia/player/AudioPlayer';
import SuonoPlayer from '../accademia/player/SuonoPlayer';
import { toast } from 'sonner';
import { storefrontAPI } from '../../api/storefront';
import { corsiAPI } from '../../api/corsi';
import { PLATFORM_TOKEN_KEY } from '../../api/platformClient';
import { fmtEuro } from '../../api/prodotti';
import { fmtDurata } from '../../api/accademia';
import { famiglieVive } from '../../lib/disciplines';
import useSeoMeta from './lib/useSeoMeta';

const InlineProdottoCheckout = React.lazy(() => import('./components/checkout/InlineProdottoCheckout'));

function testoStelle(stats) {
  const avg = Number(stats?.avg || stats?.average || 0);
  const n = Number(stats?.count || stats?.total || 0);
  if (!n || !avg) return null;
  return `★ ${avg.toFixed(1)} · ${n} recension${n === 1 ? 'e' : 'i'}`;
}

/** il riquadro video: miniatura con il play, poi l'iframe firmato (anteprima gratuita) */
function Anteprima({ orgSlug, slug, lessonId, thumbnail, titolo, etichetta }) {
  const [url, setUrl] = useState(null);
  const [media, setMedia] = useState(null);     // AU: {tipo:'audio', play_url} | {tipo:'suono', traccia}
  const [errore, setErrore] = useState(null);
  useEffect(() => {
    let vivo = true;
    setUrl(null); setMedia(null); setErrore(null);
    storefrontAPI.anteprimaCorsoPlayUrl(orgSlug, slug, lessonId)
      .then(res => {
        if (!vivo) return;
        const d = res.data || {};
        if (d.tipo === 'audio' || d.tipo === 'suono') setMedia(d); else setUrl(d.play_url || null);
      })
      .catch(() => { if (vivo) setErrore('Questa anteprima non è disponibile al momento.'); });
    return () => { vivo = false; };
  }, [orgSlug, slug, lessonId]);
  if (media?.tipo === 'audio') {
    return <div className="relative" data-testid="corso-anteprima"><AudioPlayer compatto src={`${process.env.REACT_APP_BACKEND_URL || ''}${media.play_url}`} titolo={titolo} copertina={thumbnail} />
      {etichetta && <span className="pointer-events-none absolute left-3 top-3 rounded-full bg-black/60 px-3 py-1 text-xs font-medium text-white" data-testid="corso-anteprima-etichetta">{etichetta}</span>}</div>;
  }
  if (media?.tipo === 'suono') {
    return <div className="relative" data-testid="corso-anteprima"><SuonoPlayer compatto traccia={media.traccia} />
      {etichetta && <span className="pointer-events-none absolute left-3 top-3 rounded-full bg-black/40 px-3 py-1 text-xs font-medium text-white" data-testid="corso-anteprima-etichetta">{etichetta}</span>}</div>;
  }
  return (
    <div className="relative aspect-video w-full overflow-hidden rounded-3xl bg-black" data-testid="corso-anteprima">
      {url ? (
        <iframe src={url} title={titolo} className="h-full w-full" allow="autoplay; encrypted-media; picture-in-picture" allowFullScreen loading="eager" />
      ) : (
        <div className="flex h-full w-full items-center justify-center text-sm text-white/80">
          {errore || 'Carico l’anteprima…'}
        </div>
      )}
      {etichetta && (
        <span className="pointer-events-none absolute left-3 top-3 rounded-full bg-black/60 px-3 py-1 text-xs font-medium text-white" data-testid="corso-anteprima-etichetta">{etichetta}</span>
      )}
      {thumbnail && !url && !errore && <img src={thumbnail} alt="" className="absolute inset-0 h-full w-full object-cover opacity-40" />}
    </div>
  );
}

export default function CorsoLandingPage() {
  const { org_slug: orgSlug, slug } = useParams();
  const [cercaParams] = useSearchParams();
  const daMeditazioni = cercaParams.get('da') === 'meditazioni';   // MR7
  const [data, setData] = useState(null);
  const [stato, setStato] = useState('loading');
  const [compra, setCompra] = useState(false);
  const [anteprima, setAnteprima] = useState(null);     // 'trailer' | lessonId | null
  const [iscrizione, setIscrizione] = useState(null);   // AC4: lo segui gia'? → «Vai al corso»
  const acquistaRef = useRef(null);
  const heroRef = useRef(null);

  useEffect(() => {
    let vivo = true;
    setStato('loading'); setCompra(false); setAnteprima(null);
    storefrontAPI.getCorsoLanding(orgSlug, slug)
      .then(res => {
        if (!vivo) return;
        setData(res.data); setStato('ready');
        // RF (8/10/2026, founder): l'anteprima vive SEMPRE nella copertina,
        // senza clic: il video di presentazione se c'e', altrimenti la prima
        // lezione gratuita. «Guarda gratis» cambia solo quale.
        const cc = res.data?.corso;
        const prima = (cc?.moduli || []).flatMap(m => m.lezioni).find(l => l.is_preview && l.tipo !== 'testo');
        setAnteprima(cc?.trailer ? 'trailer' : (prima ? prima.id : null));
      })
      .catch(err => { if (vivo) setStato(err?.response?.status === 404 ? 'notfound' : 'error'); });
    return () => { vivo = false; };
  }, [orgSlug, slug]);

  const c = data?.corso;
  const org = data?.org;
  // AC4 (7/10/2026): con l'account Aurya riconosciuto, se il corso e' gia' tuo
  // (attivo o completato) la pagina non ti fa ricomprare: ti porta al player.
  useEffect(() => {
    let tk = null;
    try { tk = localStorage.getItem(PLATFORM_TOKEN_KEY); } catch { /* private mode */ }
    if (!tk || !c?.course_id) { setIscrizione(null); return undefined; }
    let vivo = true;
    corsiAPI.getMyCourses().then(res => {
      if (!vivo) return;
      const mia = (res.data?.corsi || []).find(r => r.corso?.id === c.course_id && ['attivo', 'completato'].includes(r.iscrizione?.stato));
      setIscrizione(mia ? mia.iscrizione : null);
    }).catch(() => { if (vivo) setIscrizione(null); });
    return () => { vivo = false; };
  }, [c?.course_id]);
  useSeoMeta({
    title: c ? `${c.name} · ${org?.name || ''} | Aurya` : 'Corso | Aurya',
    description: c?.description || c?.long_description?.slice(0, 160) || undefined,
    image: c?.image_url || undefined,
    canonicalPath: `/corso/${orgSlug}/${slug}`,
  });

  const apriAcquisto = () => { setCompra(true); setTimeout(() => acquistaRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 50); };
  const guarda = (id) => { setAnteprima(id); setTimeout(() => heroRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 50); };
  const condividi = async () => {
    const url = window.location.href;
    try {
      if (navigator.share) { await navigator.share({ title: c?.name, url }); return; }
      await navigator.clipboard.writeText(url); toast.success('Link copiato.');
    } catch { /* annullato */ }
  };

  if (stato === 'loading') return <div className="mx-auto max-w-5xl px-4 py-16 text-sm text-gray-500 sm:px-6">Caricamento…</div>;
  if (stato !== 'ready' || !c) {
    return (
      <div className="mx-auto max-w-md px-4 py-20 text-center" data-testid="corso-landing-404">
        <SearchX className="mx-auto h-10 w-10 text-gray-300" aria-hidden />
        <h1 className="mt-4 font-display text-2xl text-gray-900">Questo corso non c'è più.</h1>
        <p className="mt-2 text-sm text-gray-600">Forse è stato tolto dal profilo, o il link non è completo.</p>
        <Link to={`/o/${orgSlug}`} className="mt-6 inline-flex rounded-full bg-[#2f5749] px-5 py-2.5 text-sm font-semibold text-white">Vai al profilo</Link>
      </div>
    );
  }

  const lezioniTot = c.lezioni_count || 0;
  const anteprime = (c.moduli || []).flatMap(m => m.lezioni.filter(l => l.is_preview));
  const categoriaLabel = c.categoria ? (famiglieVive().find(f => f.slug === c.categoria)?.label || c.categoria) : null;
  const accesso = c.access_policy === 'expiring' && c.access_expiry_days ? `Accesso per ${c.access_expiry_days} giorni` : 'Accesso per sempre';

  return (
    <div className="bg-[#faf8f3]" data-testid="corso-landing">
      <div className="mx-auto max-w-5xl px-4 pb-28 pt-5 sm:px-6 sm:pb-16 sm:pt-8">
        {/* MR7 (8/10/2026): «torna» a dove si era — dalle meditazioni (?da=meditazioni)
            si torna alle meditazioni, non al profilo: l'utente non si perde */}
        <Link to={daMeditazioni ? '/meditazioni' : `/o/${orgSlug}`} className="inline-flex items-center gap-1.5 text-sm text-gray-600 hover:text-gray-900" data-testid="corso-landing-back">
          <ArrowLeft className="h-4 w-4" aria-hidden /> {daMeditazioni ? 'Le meditazioni' : (org?.name || 'Il profilo')}
        </Link>

        <div className="mt-5 grid gap-6 lg:grid-cols-[1.15fr_1fr] lg:gap-10">
          {/* ── il video di presentazione, o la copertina ── */}
          <div ref={heroRef} className="scroll-mt-24">
            {anteprima ? (
              <Anteprima orgSlug={orgSlug} slug={slug} lessonId={anteprima} thumbnail={c.image_url}
                         titolo={anteprima === 'trailer' ? `Presentazione · ${c.name}` : 'Anteprima gratuita'}
                         etichetta={anteprima === 'trailer' ? 'Presentazione' : `Anteprima gratuita · ${anteprime.find(l => l.id === anteprima)?.title || ''}`} />
            ) : (
              <div className="relative aspect-video w-full overflow-hidden rounded-3xl bg-gradient-to-br from-[#eef3ef] to-[#dfe8e2] shadow-[0_24px_48px_-32px_rgba(30,47,40,0.35)]">
                {(c.trailer?.thumbnail_url || c.image_url)
                  ? <img src={c.trailer?.thumbnail_url || c.image_url} alt={c.name} className="h-full w-full object-cover" />
                  : <div className="flex h-full w-full items-center justify-center text-[#2f5749]/30"><GraduationCap className="h-16 w-16" aria-hidden /></div>}
                {c.trailer && (
                  <button type="button" onClick={() => guarda('trailer')} data-testid="corso-trailer-play"
                          className="absolute inset-0 flex items-center justify-center bg-black/10 transition hover:bg-black/20">
                    <span className="inline-flex items-center gap-2 rounded-full bg-white/95 px-5 py-2.5 text-sm font-semibold text-gray-900 shadow-lg">
                      <Play className="h-4 w-4 fill-current" aria-hidden /> Guarda la presentazione{c.trailer.duration_seconds ? ` · ${fmtDurata(c.trailer.duration_seconds)}` : ''}
                    </span>
                  </button>
                )}
              </div>
            )}
          </div>

          {/* ── la scheda ── */}
          <div className="lg:py-2">
            {categoriaLabel && (
              <Link to={`/corsi/${c.categoria}`} className="mb-2 inline-flex rounded-full bg-[#2f5749]/10 px-3 py-1 text-xs font-semibold text-[#2f5749] hover:bg-[#2f5749]/15" data-testid="corso-landing-categoria">{categoriaLabel}</Link>
            )}
            <h1 className="font-display text-3xl leading-tight text-gray-900 sm:text-4xl">{c.name}</h1>
            <Link to={`/o/${orgSlug}`} className="mt-4 inline-flex items-center gap-3 rounded-full bg-white/80 py-1.5 pl-1.5 pr-4 ring-1 ring-gray-200 hover:bg-white" data-testid="corso-landing-org">
              <span className="h-9 w-9 overflow-hidden rounded-full bg-gray-200">{org?.portrait_url && <img src={org.portrait_url} alt="" className="h-full w-full object-cover" />}</span>
              <span className="min-w-0 text-left">
                <span className="flex items-center gap-1 text-sm font-semibold text-gray-900">{c.instructor_name || org?.name}{org?.verified && <ShieldCheck className="h-4 w-4 text-[#2f5749]" aria-label="Verificato Aurya" />}</span>
                <span className="block text-xs text-gray-500">{[[org?.city, org?.region].filter(Boolean).join(', '), testoStelle(org?.reviews_stats)].filter(Boolean).join(' · ')}</span>
              </span>
            </Link>
            {c.description && <p className="mt-5 text-lg leading-relaxed text-gray-700">{c.description}</p>}
            <ul className="mt-4 flex flex-wrap gap-x-4 gap-y-1 text-sm text-gray-600" data-testid="corso-landing-fatti">
              <li className="inline-flex items-center gap-1.5"><Film className="h-4 w-4 text-[#2f5749]" aria-hidden /> {lezioniTot} lezion{lezioniTot === 1 ? 'e' : 'i'}</li>
              {c.durata_totale_seconds > 0 && <li className="inline-flex items-center gap-1.5"><Clock className="h-4 w-4 text-[#2f5749]" aria-hidden /> {fmtDurata(c.durata_totale_seconds)} di video</li>}
              <li className="inline-flex items-center gap-1.5"><InfinityIcon className="h-4 w-4 text-[#2f5749]" aria-hidden /> {accesso}</li>
            </ul>
            <div className="mt-6 flex flex-wrap items-center gap-3">
              <span className="text-3xl font-bold text-[#2f5749]" data-testid="corso-landing-prezzo">{fmtEuro(c.price)}</span>
            </div>
            <div className="mt-5 hidden gap-2 sm:flex">
              {iscrizione ? (
                <Link to={`/account/corsi/${iscrizione.id}`} data-testid="corso-landing-vai"
                  className="inline-flex min-h-[46px] items-center justify-center rounded-full bg-[#2f5749] px-7 text-sm font-semibold text-white shadow-[0_8px_20px_-10px_rgba(47,87,73,0.7)] transition hover:bg-[#27493d]">
                  <Play className="mr-1.5 h-4 w-4 fill-current" aria-hidden /> {iscrizione.stato === 'completato' ? 'Rivedi il corso' : 'Vai al corso'}
                </Link>
              ) : (
              <button type="button" onClick={apriAcquisto} disabled={compra} data-testid="corso-landing-compra"
                className="inline-flex min-h-[46px] items-center justify-center rounded-full bg-[#2f5749] px-7 text-sm font-semibold text-white shadow-[0_8px_20px_-10px_rgba(47,87,73,0.7)] transition hover:bg-[#27493d] disabled:opacity-50">
                {compra ? <><Check className="mr-1.5 h-4 w-4" aria-hidden /> Qui sotto</> : 'Compra il corso'}
              </button>
              )}
              <button type="button" onClick={condividi} className="inline-flex min-h-[46px] items-center gap-2 rounded-full border border-gray-200 bg-white px-5 text-sm font-medium text-gray-800 hover:bg-gray-50" data-testid="corso-landing-condividi">
                <Share2 className="h-4 w-4" aria-hidden /> Condividi
              </button>
            </div>
            {iscrizione && (
              <p className="mt-4 rounded-xl bg-emerald-50 px-4 py-2.5 text-sm text-emerald-900" data-testid="corso-landing-gia-tuo">
                Questo corso è già tuo: lo trovi in «I miei corsi», nel tuo account Aurya.
              </p>
            )}
            <ul className="mt-6 space-y-2.5 rounded-2xl border border-gray-200 bg-white p-4 text-sm text-gray-700" data-testid="corso-landing-come">
              <li className="flex gap-2.5"><Check className="mt-0.5 h-4 w-4 flex-none text-[#2f5749]" aria-hidden /><span>Lo segui dal tuo account Aurya, da qualunque telefono: riprendi da dove eri, lezione dopo lezione.</span></li>
              {anteprime.length > 0 && <li className="flex gap-2.5"><Play className="mt-0.5 h-4 w-4 flex-none text-[#2f5749]" aria-hidden /><span>{anteprime.length === 1 ? 'Una lezione' : `${anteprime.length} lezioni`} si guard{anteprime.length === 1 ? 'a' : 'ano'} gratis, qui sotto, prima di decidere.</span></li>}
              <li className="flex gap-2.5"><ShieldCheck className="mt-0.5 h-4 w-4 flex-none text-[#2f5749]" aria-hidden /><span>Pagamento sicuro con carta. Serve un account Aurya: ci trovi corsi, acquisti e file, per sempre.</span></li>
            </ul>
          </div>
        </div>

        {compra && (
          <section ref={acquistaRef} id="acquista" className="mt-8 scroll-mt-24 rounded-3xl border border-gray-200 bg-white p-4 sm:p-6" data-testid="corso-landing-acquisto">
            <h2 className="font-display text-xl text-gray-900">Compra «{c.name}»</h2>
            <div className="mt-4">
              <React.Suspense fallback={<p className="text-sm text-gray-500">Caricamento…</p>}>
                <InlineProdottoCheckout orgSlug={orgSlug} row={{ product_id: c.product_id, item_type: 'course', slug: c.slug }} onClose={() => setCompra(false)} />
              </React.Suspense>
            </div>
          </section>
        )}

        {/* ── il programma ── */}
        <section className="mt-10" data-testid="corso-landing-programma">
          <h2 className="font-display text-2xl text-gray-900">Il programma</h2>
          <div className="mt-4 space-y-4">
            {(c.moduli || []).map((m, mi) => (
              <div key={m.id} className="overflow-hidden rounded-2xl border border-gray-200 bg-white">
                {(c.moduli.length > 1 || m.title !== 'Lezioni') && (
                  <div className="border-b border-gray-100 bg-gray-50/70 px-4 py-2.5 text-sm font-semibold text-gray-800">{c.moduli.length > 1 ? `Modulo ${mi + 1} · ` : ''}{m.title}</div>
                )}
                <ol className="divide-y divide-gray-100">
                  {m.lezioni.map((l, li) => (
                    <li key={l.id} className="flex items-center gap-3 px-4 py-3" data-testid={`programma-lezione-${l.id}`}>
                      <span className="flex h-7 w-7 flex-none items-center justify-center rounded-full bg-[#2f5749]/10 text-[#2f5749]">
                        {l.tipo === 'testo' ? <FileText className="h-3.5 w-3.5" aria-hidden /> : l.tipo === 'audio' ? <Music className="h-3.5 w-3.5" aria-hidden /> : l.tipo === 'suono' ? <Waves className="h-3.5 w-3.5" aria-hidden /> : <Film className="h-3.5 w-3.5" aria-hidden />}
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium text-gray-900">{l.title}</p>
                        <p className="text-xs text-gray-500">
                          {l.tipo === 'testo' ? 'Lettura' : l.tipo === 'suono' ? `Traccia Aurya Sound${l.duration_seconds ? ` · ${fmtDurata(l.duration_seconds)}` : ''}` : l.tipo === 'audio' ? `Audio${l.duration_seconds ? ` · ${fmtDurata(l.duration_seconds)}` : ''}` : (l.duration_seconds ? fmtDurata(l.duration_seconds) : 'Video')}
                          {l.allegati > 0 && <span className="ml-2 inline-flex items-center gap-0.5"><Paperclip className="h-3 w-3" aria-hidden /> {l.allegati}</span>}
                        </p>
                      </div>
                      {l.is_preview && l.tipo !== 'testo' && (
                        <button type="button" onClick={() => guarda(l.id)} data-testid={`anteprima-${l.id}`} aria-pressed={anteprima === l.id}
                          className={`inline-flex min-h-[34px] items-center gap-1.5 rounded-full border px-3 text-xs font-semibold ${anteprima === l.id ? 'border-[#2f5749] bg-[#2f5749] text-white' : 'border-[#2f5749]/30 bg-[#2f5749]/[0.06] text-[#2f5749] hover:bg-[#2f5749]/10'}`}>
                          <Play className="h-3.5 w-3.5 fill-current" aria-hidden /> {anteprima === l.id ? 'In riproduzione' : (l.tipo === 'video' ? 'Guarda gratis' : 'Ascolta gratis')}
                        </button>
                      )}
                    </li>
                  ))}
                </ol>
              </div>
            ))}
          </div>
        </section>

        {c.long_description && (
          <section className="mt-10 max-w-3xl" data-testid="corso-landing-racconto">
            <h2 className="font-display text-2xl text-gray-900">Il racconto</h2>
            <div className="mt-4 whitespace-pre-line text-[17px] leading-relaxed text-gray-700">{c.long_description}</div>
          </section>
        )}

        {(c.instructor_name || c.instructor_bio) && (
          <section className="mt-10 max-w-3xl rounded-2xl border border-gray-200 bg-white p-5" data-testid="corso-landing-insegna">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-gray-500">Chi insegna</p>
            <h3 className="mt-1 font-display text-xl text-gray-900">{c.instructor_name || org?.name}</h3>
            {c.instructor_bio && <p className="mt-2 whitespace-pre-line text-sm leading-relaxed text-gray-700">{c.instructor_bio}</p>}
          </section>
        )}

        {(data.altri || []).length > 0 && (
          <section className="mt-12" data-testid="corso-landing-altri">
            <h2 className="font-display text-xl text-gray-900">Altri corsi di {org?.name}</h2>
            <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
              {data.altri.map(a => (
                <Link key={a.product_id} to={`/corso/${orgSlug}/${a.slug}`} className="group overflow-hidden rounded-2xl border border-gray-200 bg-white transition hover:shadow-md">
                  <div className="aspect-[4/3] bg-gradient-to-br from-[#eef3ef] to-[#dfe8e2]">{a.image_url && <img src={a.image_url} alt="" loading="lazy" className="h-full w-full object-cover transition group-hover:scale-[1.03]" />}</div>
                  <div className="p-3">
                    <p className="text-sm font-semibold leading-snug text-gray-900 line-clamp-2">{a.name}</p>
                    <p className="mt-1 text-sm font-bold text-[#2f5749]">{fmtEuro(a.price)}</p>
                  </div>
                </Link>
              ))}
            </div>
          </section>
        )}
      </div>

      {!compra && (
        <div className="fixed inset-x-0 bottom-0 z-30 border-t border-gray-200 bg-white/95 px-4 py-3 backdrop-blur sm:hidden" data-testid="corso-landing-barra">
          <div className="flex items-center justify-between gap-3">
            <div className="min-w-0"><p className="truncate text-xs text-gray-500">{c.name}</p><p className="text-lg font-bold text-[#2f5749]">{fmtEuro(c.price)}</p></div>
            <div className="flex gap-2">
              <button type="button" onClick={condividi} aria-label="Condividi" className="flex h-11 w-11 items-center justify-center rounded-full border border-gray-200 bg-white text-gray-700"><Share2 className="h-4 w-4" aria-hidden /></button>
              {iscrizione
                ? <Link to={`/account/corsi/${iscrizione.id}`} className="inline-flex min-h-[44px] items-center rounded-full bg-[#2f5749] px-6 text-sm font-semibold text-white">{iscrizione.stato === 'completato' ? 'Rivedi' : 'Vai al corso'}</Link>
                : <button type="button" onClick={apriAcquisto} className="min-h-[44px] rounded-full bg-[#2f5749] px-6 text-sm font-semibold text-white">Compra</button>}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
