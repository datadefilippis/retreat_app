/**
 * TravelerLandingPage — /cerca-ritiro (PL5).
 *
 * Landing di pre-lancio per chi cerca un ritiro: presenta il progetto
 * (operatori curati, caparra protetta, recensioni verificate) e raccoglie
 * il lead. Accent salvia.
 */
import React from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Leaf, ShieldCheck, Star, ArrowLeft, ArrowRight } from 'lucide-react';
import useSeoMeta from '../storefront/lib/useSeoMeta';
import LeadForm from './LeadForm';

const ACCENT = '#376254';

export default function TravelerLandingPage() {
  const { t } = useTranslation('prelaunch');
  useSeoMeta({
    title: t('tr.seoTitle', { defaultValue: 'Aurya — ritiri olistici scelti con cura, presto online' }),
    description: t('tr.seoDesc', { defaultValue: 'Aurya sta per aprire: ritiri olistici da operatori curati, con caparra protetta e recensioni verificate. Lascia la tua email e sii tra i primi a prenotare.' }),
  });

  const benefits = [
    { icon: Leaf, title: t('tr.b1t', { defaultValue: 'Operatori curati' }),
      body: t('tr.b1b', { defaultValue: 'Ogni operatore ha un profilo verificato: sai chi organizza, dove e cosa propone, prima di partire.' }) },
    { icon: ShieldCheck, title: t('tr.b2t', { defaultValue: 'Caparra protetta' }),
      body: t('tr.b2b', { defaultValue: 'Blocchi il posto con una caparra protetta da Stripe. Nessuna sorpresa, nessun bonifico al buio.' }) },
    { icon: Star, title: t('tr.b3t', { defaultValue: 'Recensioni vere' }),
      body: t('tr.b3b', { defaultValue: 'Solo chi ha davvero partecipato può recensire. Scegli con la fiducia di voci autentiche.' }) },
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
                 className="h-[420px] w-full object-cover md:h-[500px]" />
            <div className="absolute inset-0 bg-gradient-to-r from-[#1e2b26]/85 via-[#1e2b26]/55 to-transparent" aria-hidden />
            <div className="absolute inset-0 flex flex-col justify-center px-6 md:px-12">
              <p className="eyebrow text-[#d6c49a]">
                {t('tr.eyebrow', { defaultValue: 'Per chi cerca benessere autentico' })}
              </p>
              <h1 className="mt-3 max-w-xl font-heading text-3xl font-semibold leading-tight text-white text-hero-shadow md:text-5xl">
                {t('tr.title', { defaultValue: 'Ritiri olistici, scelti con cura' })}
              </h1>
              <p className="mt-4 max-w-md text-base text-white/90 md:text-lg">
                {t('tr.subtitle', { defaultValue: 'Aurya sta per aprire. Yoga, meditazione, cammini e molto altro, da operatori curati in tutta Italia. Sii tra i primi a prenotare.' }) }
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
              {t('tr.formTitle', { defaultValue: 'Ti avvisiamo appena apriamo' }) }
            </h2>
            <p className="mt-2 text-sm text-muted-foreground">
              {t('tr.formBody', { defaultValue: 'Lascia la tua email: sarai tra i primi a scoprire i ritiri e a prenotare, con un occhio di riguardo per chi c’è dall’inizio.' }) }
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
          </div>
        </div>
        <Link to="/" className="mt-10 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-4 w-4" /> {t('tr.back', { defaultValue: 'Torna alla home' })}
        </Link>
      </section>
    </div>
  );
}
