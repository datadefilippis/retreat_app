/**
 * OperatorLandingPage — /per-operatori (PL16, refinement design+contenuto).
 *
 * Posizionamento: riconoscimento ("hai costruito qualcosa di prezioso")
 * → visione (non una vetrina: un ecosistema che lavora per te) → valore
 * umano (essere trovati, prenotazioni senza attrito, tempo che torna
 * alle persone) → programma fondatori → UN SOLO form (hero); la CTA
 * finale scorre al form, niente duplicati. Niente gergo tecnico:
 * "pagamento diretto", mai il nome del provider. Accent terracotta + oro.
 */
import React from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Eye, ShieldCheck, HeartHandshake, ArrowLeft, ArrowRight, Sparkles, Check } from 'lucide-react';
import useSeoMeta from '../storefront/lib/useSeoMeta';
import { LangSwitcher } from '../storefront/components/MarketplaceShell';
import LeadForm from './LeadForm';

const ACCENT = '#C97B5D';
const GOLD = '#8a7440';

export default function OperatorLandingPage() {
  const { t } = useTranslation('prelaunch');
  useSeoMeta({
    title: t('op.seoTitle', { defaultValue: 'Aurya per operatori — tu crei l’esperienza, noi la facciamo trovare' }),
    description: t('op.seoDesc', { defaultValue: 'Aurya sta per aprire: il punto d\u2019incontro italiano del benessere autentico. Ti trovano le persone giuste, prenotano con caparra e pagamento diretto, e tu torni a occuparti di loro. I primi operatori partono da fondatori.' }),
  });

  const benefits = [
    { icon: Eye, title: t('op.b1t', { defaultValue: 'Ti trovano le persone giuste' }),
      body: t('op.b1b', { defaultValue: 'Il tuo profilo racconta chi sei, il tuo luogo e la tua pratica — e appare a chi sta cercando esattamente questo, nella tua zona. Senza rincorrere gli algoritmi.' }) },
    { icon: ShieldCheck, title: t('op.b2t', { defaultValue: 'Prenotazioni senza attrito' }),
      body: t('op.b2b', { defaultValue: 'Chi si iscrive versa una caparra e paga direttamente online; i promemoria arrivano da soli. Chi prenota, arriva: i posti vuoti smettono di essere il costo nascosto del tuo lavoro.' }) },
    { icon: HeartHandshake, title: t('op.b3t', { defaultValue: 'Il tuo tempo torna alle persone' }),
      body: t('op.b3b', { defaultValue: 'Calendario, partecipanti, recensioni verificate e incassi vivono in un posto solo, in armonia. Le ore perse tra messaggi e fogli di calcolo tornano a chi accompagni.' }) },
  ];

  const founders = [
    t('op.f1', { defaultValue: 'Visibilità in prima fila al lancio, quando tutti guarderanno' }),
    t('op.f2', { defaultValue: 'Accompagnamento personale nella costruzione del tuo profilo' }),
    t('op.f3', { defaultValue: 'Condizioni riservate a chi c’è dall’inizio, per sempre' }),
  ];

  const scrollToForm = (e) => {
    e.preventDefault();
    document.getElementById('presentati')?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <div className="min-h-screen bg-[#faf8f4]">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-5 py-4 md:px-10">
        <Link to="/" className="font-brand text-xl tracking-[0.3em] text-[#8a7440]">AURYA</Link>
        <div className="flex items-center gap-3">
          <Link to="/cerca-ritiro" className="text-sm text-muted-foreground hover:text-foreground">
            {t('op.switch', { defaultValue: 'Cerchi un ritiro?' })}
          </Link>
          <LangSwitcher />
        </div>
      </header>

      {/* ── Hero: racconto + UNICO form ──────────────────────────── */}
      <section className="relative mx-auto max-w-6xl px-5 pt-6 md:px-10">
        <div className="grid items-start gap-10 lg:grid-cols-2">
          <div className="rise-in">
            <p className="text-[11px] font-semibold uppercase tracking-[0.28em]" style={{ color: ACCENT }}>
              {t('op.eyebrow', { defaultValue: 'Per chi crea esperienze di benessere' })}
            </p>
            <h1 className="mt-4 font-heading text-3xl font-semibold leading-tight text-foreground md:text-5xl">
              {t('op.title', { defaultValue: 'Tu crei l’esperienza. Noi la facciamo trovare.' })}
            </h1>
            <div className="mt-5 h-px w-16" style={{ background: `${GOLD}88` }} aria-hidden />
            <p className="mt-5 max-w-lg text-base leading-relaxed text-muted-foreground md:text-lg">
              {t('op.subtitle', { defaultValue: 'Hai costruito qualcosa di prezioso: un luogo, una pratica, una comunità. Meriti di essere trovato da chi lo sta cercando, senza rincorrere gli algoritmi. Aurya sta per aprire: il punto d’incontro italiano del benessere autentico.' })}
            </p>
            <div className="relative mt-7 overflow-hidden rounded-3xl">
              <img src="/media/hero-organizer.webp" alt=""
                   className="aspect-[16/10] w-full object-cover" />
              <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-[#2b1e18]/75 to-transparent p-5">
                <p className="text-sm font-medium italic text-white/95">
                  {t('op.photoCaption', { defaultValue: '«Il lavoro più bello del mondo merita di essere visto.»' })}
                </p>
              </div>
            </div>
          </div>

          <div id="presentati" className="scroll-mt-8">
            <div className="rise-in rise-d2 rounded-3xl border bg-white p-6 shadow-lg md:p-8"
                 style={{ borderColor: `${ACCENT}33` }}>
              {/* vantaggio fondatori: la ragione per farlo ORA */}
              <div className="mb-5 flex items-start gap-2 rounded-2xl px-4 py-3"
                   style={{ background: `${ACCENT}0d` }}>
                <Sparkles className="mt-0.5 h-4 w-4 shrink-0" style={{ color: ACCENT }} />
                <p className="text-sm text-muted-foreground">
                  <span className="font-semibold text-foreground">
                    {t('op.foundersT', { defaultValue: 'I primi partono da fondatori.' })}
                  </span>{' '}
                  {t('op.foundersB', { defaultValue: 'Ti ricontattiamo personalmente prima del lancio. Niente call center, niente spam.' })}
                </p>
              </div>
              <h2 className="font-heading text-xl font-semibold text-foreground">
                {t('op.formTitle', { defaultValue: 'Presentati: ci conosciamo' })}
              </h2>
              <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">
                {t('op.formBody', { defaultValue: 'Due righe su di te e sulla tua attività. È l’inizio di una conversazione, non un modulo.' })}
              </p>
              <div className="mt-5">
                <LeadForm type="operator" accent={ACCENT} />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Visione: non una vetrina, un ecosistema ──────────────── */}
      <section className="mt-16 py-14" style={{ background: 'linear-gradient(135deg, #2b3a34 0%, #376254 100%)' }}>
        <div className="mx-auto max-w-3xl px-5 text-center md:px-10">
          <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-[#d6c49a]">
            {t('op.visionEyebrow', { defaultValue: 'La visione' })}
          </p>
          <h2 className="mt-3 font-heading text-2xl font-semibold leading-snug text-white md:text-3xl">
            {t('op.visionT', { defaultValue: 'Non una vetrina in più. Un ecosistema che lavora per te.' })}
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-base leading-relaxed text-white/85">
            {t('op.visionB', { defaultValue: 'Un profilo che racconta la tua storia, ritiri che si fanno trovare, prenotazioni che arrivano confermate, recensioni vere che costruiscono la tua reputazione. Ogni parte sostiene le altre — come in ogni pratica olistica che si rispetti.' })}
          </p>
        </div>
      </section>

      {/* ── I tre valori ─────────────────────────────────────────── */}
      <section className="mx-auto max-w-6xl px-5 py-16 md:px-10">
        <div className="grid gap-6 md:grid-cols-3">
          {benefits.map((b, i) => (
            <div key={i} className="rounded-2xl border-t-2 border border-border bg-white p-6 shadow-sm transition-all duration-300 hover:-translate-y-1 hover:shadow-md"
                 style={{ borderTopColor: `${ACCENT}99` }}>
              <div className="flex h-11 w-11 items-center justify-center rounded-xl"
                   style={{ background: `${ACCENT}14`, color: ACCENT }}>
                <b.icon className="h-5 w-5" />
              </div>
              <p className="mt-4 font-heading text-lg font-semibold text-foreground">{b.title}</p>
              <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{b.body}</p>
            </div>
          ))}
        </div>

        {/* programma fondatori, esplicito */}
        <div className="mt-10 rounded-3xl border p-7 md:p-9"
             style={{ borderColor: `${GOLD}55`, background: `${GOLD}0a` }}>
          <div className="flex flex-col items-start gap-6 md:flex-row md:items-center md:justify-between">
            <div className="max-w-xl">
              <p className="text-[11px] font-semibold uppercase tracking-[0.28em]" style={{ color: GOLD }}>
                {t('op.foundersEyebrow', { defaultValue: 'Programma fondatori' })}
              </p>
              <h3 className="mt-2 font-heading text-xl font-semibold text-foreground md:text-2xl">
                {t('op.foundersTitle', { defaultValue: 'Chi semina per primo, raccoglie per primo' })}
              </h3>
              <ul className="mt-4 space-y-2.5">
                {founders.map((f, i) => (
                  <li key={i} className="flex items-start gap-2.5 text-sm text-muted-foreground">
                    <Check className="mt-0.5 h-4 w-4 shrink-0" style={{ color: ACCENT }} />
                    {f}
                  </li>
                ))}
              </ul>
            </div>
            <a href="#presentati" onClick={scrollToForm}
               className="inline-flex shrink-0 items-center gap-2 rounded-full px-7 py-3.5 text-sm font-semibold text-white shadow-lg transition-opacity hover:opacity-90"
               style={{ background: ACCENT }}>
              {t('op.ctaBtn', { defaultValue: 'Presentati ora' })} <ArrowRight className="h-4 w-4" />
            </a>
          </div>
        </div>

        <Link to="/" className="mt-10 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-4 w-4" /> {t('op.back', { defaultValue: 'Torna alla home' })}
        </Link>
      </section>
    </div>
  );
}
