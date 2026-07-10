/**
 * TravelerLandingPage — /cerca-ritiro (PL10, copy v2).
 *
 * Landing di pre-lancio per chi cerca un ritiro. Tono: empatico ed
 * evocativo — parla al bisogno (fermarsi, respirare, ritrovarsi), non
 * alla feature. Il form profilato (città, interessi, budget) promette
 * una cosa concreta: al lancio proposte scelte per te, non una
 * newsletter qualsiasi. Accent salvia.
 */
import React from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Leaf, ShieldCheck, MapPin, ArrowLeft, ArrowRight, Quote } from 'lucide-react';
import useSeoMeta from '../storefront/lib/useSeoMeta';
import LeadForm from './LeadForm';

const ACCENT = '#376254';

export default function TravelerLandingPage() {
  const { t } = useTranslation('prelaunch');
  useSeoMeta({
    title: t('tr.seoTitle', { defaultValue: 'Aurya — c’è un ritiro che ti sta aspettando' }),
    description: t('tr.seoDesc', { defaultValue: 'Aurya sta per aprire: ritiri olistici veri, da operatori verificati, con caparra protetta. Raccontaci cosa cerchi e al lancio ti proponiamo ritiri scelti per te.' }),
  });

  const benefits = [
    { icon: Leaf, title: t('tr.b1t', { defaultValue: 'Scelti, non elencati' }),
      body: t('tr.b1b', { defaultValue: 'Dietro ogni ritiro c’è un operatore con un volto, un luogo vero e recensioni di chi c’è stato davvero. Nessun annuncio anonimo.' }) },
    { icon: ShieldCheck, title: t('tr.b2t', { defaultValue: 'Il posto è tuo, senza ansia' }),
      body: t('tr.b2b', { defaultValue: 'Blocchi con una caparra protetta da Stripe, il saldo arriva dopo. Regole chiare fin dall’inizio, nessun bonifico al buio.' }) },
    { icon: MapPin, title: t('tr.b3t', { defaultValue: 'Vicino a dove sei' }),
      body: t('tr.b3b', { defaultValue: 'Ci dici dove vivi e ti proponiamo esperienze raggiungibili. A volte il viaggio che serve è a un’ora da casa.' }) },
  ];

  return (
    <div className="min-h-screen bg-[#f7f9f6]">
      <header className="flex items-center justify-between px-5 py-4 md:px-10">
        <Link to="/" className="font-brand text-xl tracking-[0.3em] text-[#8a7440]">AURYA</Link>
        <Link to="/per-operatori" className="text-sm text-muted-foreground hover:text-foreground">
          {t('tr.switch', { defaultValue: 'Sei un operatore?' })}
        </Link>
      </header>

      {/* hero foto + scrim */}
      <section className="relative">
        <div className="relative mx-auto max-w-6xl overflow-hidden px-5 md:px-10">
          <div className="relative overflow-hidden rounded-3xl">
            <img src="/media/hero-destination.webp" alt=""
                 className="h-[440px] w-full object-cover md:h-[520px]" />
            <div className="absolute inset-0 bg-gradient-to-r from-[#1e2b26]/85 via-[#1e2b26]/55 to-transparent" aria-hidden />
            <div className="absolute inset-0 flex flex-col justify-center px-6 md:px-12">
              <p className="eyebrow text-[#d6c49a]">
                {t('tr.eyebrow', { defaultValue: 'Per chi sente il bisogno di fermarsi' })}
              </p>
              <h1 className="mt-3 max-w-xl font-heading text-3xl font-semibold leading-tight text-white text-hero-shadow md:text-5xl">
                {t('tr.title', { defaultValue: 'C’è un ritiro che ti sta aspettando' })}
              </h1>
              <p className="mt-4 max-w-md text-base text-white/90 md:text-lg">
                {t('tr.subtitle', { defaultValue: 'Il silenzio di un uliveto, un cerchio di persone vere, il respiro che torna lento. Aurya sta per aprire: raccontaci cosa cerchi e ti aiutiamo a trovarlo.' }) }
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* lead form + benefici */}
      <section className="mx-auto max-w-6xl px-5 py-14 md:px-10">
        <div className="grid gap-10 lg:grid-cols-2">
          <div>
            <h2 className="font-heading text-2xl font-semibold text-foreground">
              {t('tr.formTitle', { defaultValue: 'Raccontaci cosa cerchi' }) }
            </h2>
            <p className="mt-2 text-sm text-muted-foreground">
              {t('tr.formBody', { defaultValue: 'Bastano trenta secondi. Ci dici dove vivi e cosa ti chiama, e al lancio ricevi una selezione di ritiri pensata per te. Niente valanghe di email: solo quello che conta.' }) }
            </p>
            <div className="mt-5 max-w-md">
              <LeadForm type="traveler" accent={ACCENT} />
            </div>
            <Link to="/ritiri" className="mt-5 inline-flex items-center gap-1 text-sm font-medium" style={{ color: ACCENT }}>
              {t('tr.peek', { defaultValue: 'Sbircia l’anteprima dei ritiri' })} <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
          <div className="grid gap-4">
            {benefits.map((b, i) => (
              <div key={i} className="flex gap-4 rounded-2xl border border-border bg-white p-5">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl"
                     style={{ background: `${ACCENT}18`, color: ACCENT }}>
                  <b.icon className="h-5 w-5" />
                </div>
                <div>
                  <p className="font-heading text-base font-semibold text-foreground">{b.title}</p>
                  <p className="mt-1 text-sm text-muted-foreground">{b.body}</p>
                </div>
              </div>
            ))}
            {/* nota umana: perché nasce Aurya */}
            <div className="rounded-2xl border border-dashed p-5"
                 style={{ borderColor: `${ACCENT}55`, background: `${ACCENT}08` }}>
              <Quote className="h-5 w-5" style={{ color: ACCENT }} />
              <p className="mt-2 text-sm italic text-muted-foreground">
                {t('tr.why', { defaultValue: 'Aurya nasce da una convinzione semplice: prendersi cura di sé non dovrebbe richiedere ore di ricerche tra pagine social e passaparola. Un posto solo, curato, dove trovare chi fa questo lavoro con il cuore.' })}
              </p>
            </div>
          </div>
        </div>
        <Link to="/" className="mt-10 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-4 w-4" /> {t('tr.back', { defaultValue: 'Torna alla home' })}
        </Link>
      </section>
    </div>
  );
}
