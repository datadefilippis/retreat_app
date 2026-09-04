/**
 * OperatorInterviewPage — /o/:org_slug/intervista (PV3,
 * docs/PROFILO_VERIFICATO_PIANO_2026-07.md).
 *
 * L'intervista del team Aurya su pagina propria, in CONTINUITÀ col
 * profilo (richiesta founder): stessa testata identitaria
 * (OperatorIdentityHeader, lo stesso componente dell'hero /o/), barra
 * sticky con breadcrumb e "Torna al profilo" sempre visibile, video
 * YouTube (solo youtube-nocookie, facade con poster: l'iframe nasce al
 * click), Q&A editoriali che si leggono come un articolo, e in fondo
 * la fascia "Continua a scoprire" con le CTA verso le sezioni del
 * profilo. Se l'intervista non è pubblicata (payload PV2: interview
 * vuota) si REDIRIGE al profilo: nessun 404 crudo.
 */

import React, { useEffect, useState } from 'react';
import { useParams, Link, Navigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { ArrowLeft, ArrowRight, Flower2, Play, Star, Tags } from 'lucide-react';
import api from '../../api/client';
import useSeoMeta from './lib/useSeoMeta';
import MarketplaceShell from './components/MarketplaceShell';
import OperatorIdentityHeader from './components/OperatorIdentityHeader';
import BrandPayoff from '../../components/BrandPayoff';

function fmtDay(iso, lang = 'it-IT') {
  try {
    return new Date(iso).toLocaleDateString(lang, { day: 'numeric', month: 'long', year: 'numeric' });
  } catch { return (iso || '').slice(0, 10); }
}

// Stesso riconoscimento dell'admin (InterviewsTab): il backend salva
// l'URL canonico youtube.com/watch?v=ID, qui serve solo l'ID.
const ytVideoId = (url) => {
  const m = String(url || '').match(
    /^https?:\/\/(?:(?:www\.|m\.)?youtube\.com\/watch\?(?:[^#]*&)?v=|youtu\.be\/|(?:www\.|m\.)?youtube\.com\/shorts\/)([A-Za-z0-9_-]{11})(?:[?&#/]|$)/
  );
  return m ? m[1] : null;
};

// Facade: poster + play finché l'utente non clicca, poi SOLO
// youtube-nocookie (privacy) con autoplay. Niente youtube.com/embed.
function InterviewVideo({ videoId, name, t }) {
  const [playing, setPlaying] = useState(false);
  return (
    <div className="relative aspect-video rounded-2xl overflow-hidden bg-black shadow-lg"
         data-testid="interview-video">
      {playing ? (
        <iframe
          src={`https://www.youtube-nocookie.com/embed/${videoId}?autoplay=1&rel=0`}
          title={t('landings:operator.interviewVideoTitle', { defaultValue: 'Video intervista a {{name}}', name })}
          loading="lazy"
          className="absolute inset-0 w-full h-full"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen
        />
      ) : (
        <button type="button" onClick={() => setPlaying(true)}
                aria-label={t('landings:operator.interviewPlay', { defaultValue: 'Guarda il video dell\'intervista' })}
                className="group absolute inset-0 w-full h-full">
          <img src={`https://i.ytimg.com/vi/${videoId}/hqdefault.jpg`} alt="" loading="lazy"
               className="absolute inset-0 w-full h-full object-cover" />
          <span aria-hidden className="absolute inset-0 bg-black/30 group-hover:bg-black/20 transition-colors" />
          <span aria-hidden className="absolute inset-0 flex items-center justify-center">
            <span className="flex h-16 w-16 items-center justify-center rounded-full bg-white/90 shadow-lg group-hover:scale-105 transition-transform">
              <Play className="h-7 w-7 text-[#376254] ml-1" fill="currentColor" />
            </span>
          </span>
        </button>
      )}
    </div>
  );
}

export default function OperatorInterviewPage() {
  const { org_slug } = useParams();
  const { t, i18n } = useTranslation('landings');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  // OP2 — stessa risoluzione lingua del profilo: fetch con lang e
  // refetch al cambio (contenuti tradotti dove compilati).
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

  // PV2 — l'intervista è nel payload SOLO se pubblicata: lista vuota
  // significa niente da mostrare qui.
  const published = Array.isArray(data?.interview) && data.interview.length > 0;
  const firstAnswer = published ? String(data.interview[0].answer || '') : '';

  useSeoMeta({
    title: data?.name
      ? t('landings:operator.interviewSeoTitle', { defaultValue: '{{name}}, l\'intervista | Aurya', name: data.name })
      : undefined,
    description: firstAnswer ? firstAnswer.slice(0, 155) : undefined,
    image: data?.cover_url || data?.logo_url || undefined,
    canonicalPath: `/o/${org_slug}/intervista`,
    // SEO2a — breadcrumb JSON-LD: il minimo coerente con la scala del
    // sito (il profilo porta il LocalBusiness, qui la briciola).
    jsonLd: (data?.name && published) ? {
      '@context': 'https://schema.org',
      '@type': 'BreadcrumbList',
      itemListElement: [
        { '@type': 'ListItem', position: 1,
          name: t('landings:operators.heading', { defaultValue: 'Professionisti' }),
          item: `${window.location.origin}/operatori` },
        { '@type': 'ListItem', position: 2, name: data.name,
          item: `${window.location.origin}/o/${org_slug}` },
        { '@type': 'ListItem', position: 3,
          name: t('landings:operator.interviewBreadcrumb', { defaultValue: 'Intervista' }) },
      ],
    } : undefined,
  });

  if (loading) return <div className="min-h-screen flex items-center justify-center text-gray-400">…</div>;

  // Niente 404 crudo: org sconosciuta o intervista non pubblicata →
  // si atterra sul profilo (che sa gestire anche il suo not-found).
  if (notFound || !data || !published) {
    return <Navigate to={`/o/${org_slug}`} replace />;
  }

  const videoId = ytVideoId(data.interview_video_url);
  const hasListino = Array.isArray(data.listino) && data.listino.length > 0;

  // Fascia finale — le sezioni del profilo come prosecuzione naturale
  // della lettura: ancore reali di /o/ (il profilo scorre fin lì).
  const continueCards = [
    {
      to: `/o/${org_slug}#ritiri`,
      icon: Flower2,
      title: t('landings:operator.interviewCtaRetreats', { defaultValue: 'I suoi ritiri' }),
      sub: t('landings:operator.interviewCtaRetreatsSub', { defaultValue: 'Le prossime date in calendario' }),
    },
    hasListino && {
      to: `/o/${org_slug}#listino`,
      icon: Tags,
      title: t('landings:operator.interviewCtaListino', { defaultValue: 'Servizi e prezzi' }),
      sub: t('landings:operator.interviewCtaListinoSub', { defaultValue: 'Il listino completo' }),
    },
    {
      to: `/o/${org_slug}#recensioni`,
      icon: Star,
      title: t('landings:operator.interviewCtaReviews', { defaultValue: 'Le recensioni' }),
      sub: t('landings:operator.interviewCtaReviewsSub', { defaultValue: 'Cosa raccontano le persone' }),
    },
  ].filter(Boolean);

  return (
    <MarketplaceShell>
    <div className="bg-gray-50">
      {/* Barra sticky sotto l'header dello shell (h-14): breadcrumb +
          "Torna al profilo" SEMPRE visibile mentre si legge. */}
      <div className="sticky top-14 z-30 border-b border-gray-200 bg-white/95 backdrop-blur">
        <div className="max-w-6xl mx-auto px-4 h-11 flex items-center justify-between gap-3">
          <nav className="text-xs text-gray-500 truncate" aria-label="breadcrumb">
            <Link to="/operatori" className="hover:text-primary hover:underline">
              {t('landings:operators.heading', { defaultValue: 'Professionisti' })}
            </Link>
            <span className="mx-1.5" aria-hidden>›</span>
            <Link to={`/o/${org_slug}`} className="hover:text-primary hover:underline">
              {data.name}
            </Link>
            <span className="mx-1.5" aria-hidden>›</span>
            <span className="text-gray-700">
              {t('landings:operator.interviewBreadcrumb', { defaultValue: 'Intervista' })}
            </span>
          </nav>
          <Link to={`/o/${org_slug}`} data-testid="back-to-profile"
                className="shrink-0 inline-flex items-center gap-1.5 rounded-full border border-[#376254] text-[#376254] px-3.5 py-1.5 text-xs font-semibold hover:bg-[#376254] hover:text-white transition-colors">
            <ArrowLeft className="h-3.5 w-3.5" aria-hidden />
            {t('landings:operator.interviewBackToProfile', { defaultValue: 'Torna al profilo' })}
          </Link>
        </div>
      </div>

      {/* La STESSA testata del profilo: continuità garantita dal
          componente condiviso, non da uno stile somigliante. */}
      <OperatorIdentityHeader data={data} t={t} />

      <main className="max-w-3xl mx-auto px-4 py-10">
        {videoId && (
          <div className="mb-10">
            <InterviewVideo videoId={videoId} name={data.name} t={t} />
          </div>
        )}

        <div className="mb-8">
          <BrandPayoff tone="cream" size="xs" className="mb-2" />
          <h2 className="font-heading text-2xl sm:text-3xl font-bold text-foreground">
            {t('landings:operator.interviewTitle', { defaultValue: 'L\'intervista' })}
          </h2>
          {/* Riga discreta: chi l'ha realizzata e quando (verified_at) */}
          <p className="text-xs text-gray-500 mt-2">
            {t('landings:operator.interviewByAurya', { defaultValue: 'Intervista realizzata dal team Aurya' })}
            {data.interview_verified_at && <> · {fmtDay(data.interview_verified_at, i18n.language)}</>}
          </p>
        </div>

        {/* Q&A editoriali: si leggono come un articolo, niente accordion */}
        <article className="space-y-10">
          {data.interview.map((qa, i) => (
            <div key={i}>
              <p aria-hidden className="font-brand text-[#8a7440] text-xs tracking-[0.25em] select-none mb-1.5">
                {String(i + 1).padStart(2, '0')}
              </p>
              <h3 className="font-heading text-xl sm:text-2xl font-bold text-[#376254] leading-snug">
                {qa.question}
              </h3>
              <p className="text-gray-700 leading-relaxed whitespace-pre-line mt-3">
                {qa.answer}
              </p>
            </div>
          ))}
        </article>

        {/* Fascia "Continua a scoprire": la lettura prosegue sulla
            stessa scheda, verso le sezioni del profilo. */}
        <section className="mt-14 border-t border-gray-200 pt-8" data-testid="continue-band">
          <h2 className="font-heading text-xl font-bold text-foreground mb-4">
            {t('landings:operator.interviewContinueTitle', { defaultValue: 'Continua a scoprire {{name}}', name: data.name })}
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {continueCards.map(card => (
              <Link key={card.to} to={card.to}
                    className="group rounded-2xl border border-border bg-card p-4 hover:shadow-md hover:border-[#376254]/40 transition-all">
                <card.icon className="h-5 w-5 text-[#376254]" aria-hidden />
                <p className="font-heading font-semibold text-foreground mt-2 group-hover:text-[#376254]">
                  {card.title}
                </p>
                <p className="text-xs text-muted-foreground mt-0.5">{card.sub}</p>
                <span className="inline-flex items-center gap-1 text-xs font-semibold text-[#8a7440] mt-2.5">
                  {t('landings:operator.interviewContinueGo', { defaultValue: 'Vai alla sezione' })}
                  <ArrowRight className="h-3.5 w-3.5 group-hover:translate-x-0.5 transition-transform" aria-hidden />
                </span>
              </Link>
            ))}
          </div>
        </section>
      </main>
    </div>
    </MarketplaceShell>
  );
}
