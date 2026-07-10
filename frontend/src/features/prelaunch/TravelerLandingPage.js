/**
 * TravelerLandingPage — /cerca-ritiro (PL16, refinement design+contenuto).
 *
 * Posizionamento: ad Aurya non si "cerca un annuncio", ci si affida a un
 * sistema che si prende cura del viaggio interiore dall'inizio alla fine.
 * Struttura: hero evocativo → come funziona (3 passi umani) → form (UNO)
 * + pilastri di fiducia → perché nasce Aurya. Niente gergo tecnico:
 * "pagamento diretto", mai il nome del provider. Accent salvia + oro.
 */
import React from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Leaf, ShieldCheck, MapPin, ArrowLeft, ArrowRight, Quote } from 'lucide-react';
import useSeoMeta from '../storefront/lib/useSeoMeta';
import { LangSwitcher } from '../storefront/components/MarketplaceShell';
import LeadForm from './LeadForm';

const ACCENT = '#376254';
const GOLD = '#8a7440';

export default function TravelerLandingPage() {
  const { t } = useTranslation('prelaunch');
  useSeoMeta({
    title: t('tr.seoTitle', { defaultValue: 'Aurya — c’è un ritiro che ti sta aspettando' }),
    description: t('tr.seoDesc', { defaultValue: 'Aurya sta per aprire: ritiri olistici veri, da operatori verificati, con caparra e pagamento diretto online. Raccontaci cosa cerchi e al lancio ti proponiamo ritiri scelti per te.' }),
  });

  const steps = [
    { n: '01', title: t('tr.s1t', { defaultValue: 'Raccontaci cosa cerchi' }),
      body: t('tr.s1b', { defaultValue: 'Dove vivi, cosa ti chiama, quanto vuoi allontanarti. Trenta secondi, senza impegno.' }) },
    { n: '02', title: t('tr.s2t', { defaultValue: 'Ricevi una selezione pensata per te' }),
      body: t('tr.s2b', { defaultValue: 'Al lancio non ti mandiamo un catalogo: ti proponiamo i ritiri giusti per te, scelti a mano.' }) },
    { n: '03', title: t('tr.s3t', { defaultValue: 'Prenota con serenità' }),
      body: t('tr.s3b', { defaultValue: 'Blocchi il posto con una piccola caparra e paghi direttamente online, con regole chiare. Il resto è cammino.' }) },
  ];

  const benefits = [
    { icon: Leaf, title: t('tr.b1t', { defaultValue: 'Persone, non annunci' }),
      body: t('tr.b1b', { defaultValue: 'Dietro ogni ritiro c’è un operatore con un volto, un luogo vero e recensioni di chi c’è stato davvero. Sai a chi ti affidi, prima di partire.' }) },
    { icon: ShieldCheck, title: t('tr.b2t', { defaultValue: 'Il posto è tuo, senza pensieri' }),
      body: t('tr.b2b', { defaultValue: 'Una piccola caparra per bloccare il posto, il pagamento diretto online, il saldo più avanti. Niente bonifici al buio, nessuna sorpresa.' }) },
    { icon: MapPin, title: t('tr.b3t', { defaultValue: 'Vicino a dove sei' }),
      body: t('tr.b3b', { defaultValue: 'Ci dici dove vivi e ti proponiamo esperienze raggiungibili. A volte il viaggio che serve è a un’ora da casa.' }) },
  ];

  return (
    <div className="min-h-screen bg-[#f7f9f6]">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-5 py-4 md:px-10">
        <Link to="/" className="font-brand text-xl tracking-[0.3em] text-[#8a7440]">AURYA</Link>
        <div className="flex items-center gap-3">
          <Link to="/per-operatori" className="text-sm text-muted-foreground hover:text-foreground">
            {t('tr.switch', { defaultValue: 'Sei un operatore?' })}
          </Link>
          <LangSwitcher />
        </div>
      </header>

      {/* ── Hero ──────────────────────────────────────────────────── */}
      <section className="relative">
        <div className="relative mx-auto max-w-6xl overflow-hidden px-5 md:px-10">
          <div className="rise-in relative overflow-hidden rounded-3xl">
            <img src="/media/hero-destination.webp" alt=""
                 className="h-[460px] w-full object-cover md:h-[540px]" />
            {/* PL18 — velatura rinforzata: il sottotitolo deve leggersi
                bene anche sui punti più chiari della foto */}
            <div className="absolute inset-0 bg-gradient-to-r from-[#1e2b26]/95 via-[#1e2b26]/75 to-[#1e2b26]/35" aria-hidden />
            <div className="absolute inset-0 flex flex-col justify-center px-6 md:px-14">
              <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-[#d6c49a]">
                {t('tr.eyebrow', { defaultValue: 'Per chi sente il bisogno di fermarsi' })}
              </p>
              <h1 className="mt-4 max-w-xl font-heading text-3xl font-semibold leading-tight text-white text-hero-shadow md:text-5xl">
                {t('tr.title', { defaultValue: 'C’è un ritiro che ti sta aspettando' })}
              </h1>
              <div className="mt-5 h-px w-16 bg-[#d6c49a]/70" aria-hidden />
              <p className="mt-5 max-w-md text-base leading-relaxed text-white/90 md:text-lg">
                {t('tr.subtitle', { defaultValue: 'Il silenzio di un uliveto, un cerchio di persone vere, il respiro che torna lento. Aurya sta per aprire: raccontaci cosa cerchi e ti aiutiamo a trovarlo.' }) }
              </p>
              <a href="#racconta"
                 onClick={(e) => { e.preventDefault(); document.getElementById('racconta')?.scrollIntoView({ behavior: 'smooth' }); }}
                 className="mt-7 inline-flex w-fit items-center gap-2 rounded-full px-6 py-3 text-sm font-semibold text-white shadow-lg transition-opacity hover:opacity-90"
                 style={{ background: ACCENT }}>
                {t('tr.heroCta', { defaultValue: 'Inizia da qui' })} <ArrowRight className="h-4 w-4" />
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* ── Come funziona: 3 passi umani ─────────────────────────── */}
      <section className="mx-auto max-w-6xl px-5 pt-14 md:px-10">
        <p className="text-center text-[11px] font-semibold uppercase tracking-[0.28em]" style={{ color: GOLD }}>
          {t('tr.stepsEyebrow', { defaultValue: 'Semplice, umano' })}
        </p>
        <h2 className="mt-2 text-center font-heading text-2xl font-semibold text-foreground md:text-3xl">
          {t('tr.stepsTitle', { defaultValue: 'Non un altro portale. Qualcuno che ti accompagna.' })}
        </h2>
        <div className="mt-8 grid gap-5 md:grid-cols-3">
          {steps.map((s) => (
            <div key={s.n} className="rounded-2xl border-t-2 bg-white p-6 shadow-sm transition-all duration-300 hover:-translate-y-1 hover:shadow-md"
                 style={{ borderTopColor: `${GOLD}88` }}>
              <span className="font-heading text-2xl font-semibold" style={{ color: `${GOLD}` }}>{s.n}</span>
              <p className="mt-2 font-heading text-lg font-semibold text-foreground">{s.title}</p>
              <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{s.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Form + pilastri di fiducia ───────────────────────────── */}
      <section id="racconta" className="mx-auto max-w-6xl scroll-mt-8 px-5 py-16 md:px-10">
        <div className="grid gap-10 lg:grid-cols-2">
          <div className="rise-in rise-d1 rounded-3xl border bg-white p-6 shadow-lg md:p-8"
               style={{ borderColor: `${ACCENT}22` }}>
            <h2 className="font-heading text-2xl font-semibold text-foreground">
              {t('tr.formTitle', { defaultValue: 'Raccontaci cosa cerchi' }) }
            </h2>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
              {t('tr.formBody', { defaultValue: 'Bastano trenta secondi. Ci dici dove vivi e cosa ti chiama, e al lancio ricevi una selezione di ritiri pensata per te. Niente valanghe di email: solo quello che conta.' }) }
            </p>
            <div className="mt-6">
              <LeadForm type="traveler" accent={ACCENT} />
            </div>
            <Link to="/ritiri" className="mt-5 inline-flex items-center gap-1 text-sm font-medium" style={{ color: ACCENT }}>
              {t('tr.peek', { defaultValue: 'Sbircia l’anteprima dei ritiri' })} <ArrowRight className="h-4 w-4" />
            </Link>
            {/* PL22 — canale diretto, discreto: non tutti amano i form */}
            <p className="mt-3 text-xs text-muted-foreground">
              {t('tr.directT', { defaultValue: 'Preferisci scriverci direttamente?' })}{' '}
              <a href="mailto:info@aurya.life" className="font-medium underline underline-offset-2" style={{ color: ACCENT }}>
                info@aurya.life
              </a>
            </p>
          </div>

          <div className="flex flex-col gap-4">
            {benefits.map((b, i) => (
              <div key={i} className="flex gap-4 rounded-2xl border border-border bg-white p-5">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl"
                     style={{ background: `${ACCENT}14`, color: ACCENT }}>
                  <b.icon className="h-5 w-5" />
                </div>
                <div>
                  <p className="font-heading text-base font-semibold text-foreground">{b.title}</p>
                  <p className="mt-1 text-sm leading-relaxed text-muted-foreground">{b.body}</p>
                </div>
              </div>
            ))}
            {/* perché nasce Aurya — la voce umana del progetto */}
            <div className="rounded-2xl p-6" style={{ background: `${ACCENT}0d` }}>
              <Quote className="h-5 w-5" style={{ color: ACCENT }} />
              <p className="mt-2 text-sm italic leading-relaxed text-[#2b3a34]">
                {t('tr.why', { defaultValue: 'Aurya nasce da una convinzione semplice: prendersi cura di sé non dovrebbe richiedere ore di ricerche tra pagine social e passaparola. Un posto solo, curato, dove trovare chi fa questo lavoro con il cuore.' })}
              </p>
              <p className="mt-3 text-xs font-semibold uppercase tracking-[0.2em]" style={{ color: GOLD }}>Aurya · Connect · Heal · Grow</p>
            </div>
          </div>
        </div>
        <Link to="/" className="mt-12 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-4 w-4" /> {t('tr.back', { defaultValue: 'Torna alla home' })}
        </Link>
      </section>
    </div>
  );
}
