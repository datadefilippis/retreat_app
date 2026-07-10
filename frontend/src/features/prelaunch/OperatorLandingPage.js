/**
 * OperatorLandingPage — /per-operatori (PL5).
 *
 * Landing di pre-lancio per operatori olistici: presenta il valore
 * (visibilità, prenotazioni con caparra protetta, gestione semplice) e
 * raccoglie il lead. Accent terracotta.
 */
import React from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Eye, ShieldCheck, Sparkles, ArrowLeft } from 'lucide-react';
import useSeoMeta from '../storefront/lib/useSeoMeta';
import LeadForm from './LeadForm';

const ACCENT = '#C97B5D';

export default function OperatorLandingPage() {
  const { t } = useTranslation('prelaunch');
  useSeoMeta({
    title: t('op.seoTitle', { defaultValue: 'Aurya per operatori — porta i tuoi ritiri dove ti cercano' }),
    description: t('op.seoDesc', { defaultValue: 'Su Aurya i tuoi ritiri olistici si fanno trovare da chi li cerca: visibilità sui motori, prenotazioni con caparra protetta, gestione semplice. Iscriviti al lancio.' }),
  });

  const benefits = [
    { icon: Eye, title: t('op.b1t', { defaultValue: 'Ti trovano davvero' }),
      body: t('op.b1b', { defaultValue: 'Profilo e ritiri ottimizzati per i motori di ricerca e la tua zona: appari a chi cerca proprio quello che offri.' }) },
    { icon: ShieldCheck, title: t('op.b2t', { defaultValue: 'Prenotazioni con caparra protetta' }),
      body: t('op.b2b', { defaultValue: 'Incassi online con caparra e saldo, protetti da Stripe. Meno posti vuoti, meno no-show.' }) },
    { icon: Sparkles, title: t('op.b3t', { defaultValue: 'Gestione senza pensieri' }),
      body: t('op.b3b', { defaultValue: 'Calendario, partecipanti, promemoria automatici e recensioni verificate: tu pensi all’esperienza, al resto pensa Aurya.' }) },
  ];

  return (
    <div className="min-h-screen bg-[#faf8f4]">
      {/* header minimale */}
      <header className="flex items-center justify-between px-5 py-4 md:px-10">
        <Link to="/" className="font-brand text-xl tracking-[0.3em] text-[#8a7440]">AURYA</Link>
        <Link to="/cerca-ritiro" className="text-sm text-muted-foreground hover:text-foreground">
          {t('op.switch', { defaultValue: 'Cerchi un ritiro?' })}
        </Link>
      </header>

      {/* hero */}
      <section className="relative mx-auto max-w-6xl px-5 pt-6 md:px-10">
        <div className="grid items-center gap-8 lg:grid-cols-2">
          <div>
            <p className="eyebrow" style={{ color: ACCENT }}>
              {t('op.eyebrow', { defaultValue: 'Per operatori olistici' })}
            </p>
            <h1 className="mt-3 font-heading text-3xl font-semibold leading-tight text-foreground md:text-5xl">
              {t('op.title', { defaultValue: 'Porta i tuoi ritiri dove chi li cerca ti trova' })}
            </h1>
            <p className="mt-4 text-base text-muted-foreground md:text-lg">
              {t('op.subtitle', { defaultValue: 'Aurya sta per aprire: il marketplace italiano dei ritiri olistici, pensato per farti trovare e prenotare online. Lascia la tua email e sarai tra i primi operatori a bordo.' })}
            </p>
            <div className="mt-6 max-w-md">
              <LeadForm type="operator" accent={ACCENT} />
            </div>
          </div>
          <div className="relative">
            <img src="/media/hero-organizer.webp" alt=""
                 className="aspect-[4/3] w-full rounded-3xl object-cover shadow-xl" />
          </div>
        </div>
      </section>

      {/* benefici */}
      <section className="mx-auto max-w-6xl px-5 py-16 md:px-10">
        <div className="grid gap-6 md:grid-cols-3">
          {benefits.map((b, i) => (
            <div key={i} className="rounded-2xl border border-border bg-white p-6">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl"
                   style={{ background: `${ACCENT}18`, color: ACCENT }}>
                <b.icon className="h-5 w-5" />
              </div>
              <p className="mt-4 font-heading text-lg font-semibold text-foreground">{b.title}</p>
              <p className="mt-1 text-sm text-muted-foreground">{b.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA finale */}
      <section className="mx-auto max-w-xl px-5 pb-20 text-center md:px-10">
        <h2 className="font-heading text-2xl font-semibold text-foreground">
          {t('op.ctaTitle', { defaultValue: 'Vuoi essere tra i primi?' })}
        </h2>
        <p className="mt-2 text-sm text-muted-foreground">
          {t('op.ctaBody', { defaultValue: 'Ti scriviamo appena apriamo le iscrizioni operatori.' })}
        </p>
        <div className="mx-auto mt-5 max-w-md">
          <LeadForm type="operator" accent={ACCENT} />
        </div>
        <Link to="/" className="mt-8 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-4 w-4" /> {t('op.back', { defaultValue: 'Torna alla home' })}
        </Link>
      </section>
    </div>
  );
}
