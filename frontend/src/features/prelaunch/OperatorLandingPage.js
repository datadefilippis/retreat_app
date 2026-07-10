/**
 * OperatorLandingPage — /per-operatori (PL10, copy v2).
 *
 * Landing di pre-lancio per operatori olistici. Tono: riconoscimento
 * del loro lavoro ("hai costruito qualcosa di prezioso") prima della
 * promessa ("noi lo facciamo trovare"). Il form profilato (telefono,
 * località, attività, descrizione) prepara un follow-up personale —
 * e lo diciamo: niente call center, niente spam. Accent terracotta.
 */
import React from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Eye, ShieldCheck, HeartHandshake, ArrowLeft, Sparkles } from 'lucide-react';
import useSeoMeta from '../storefront/lib/useSeoMeta';
import LeadForm from './LeadForm';

const ACCENT = '#C97B5D';

export default function OperatorLandingPage() {
  const { t } = useTranslation('prelaunch');
  useSeoMeta({
    title: t('op.seoTitle', { defaultValue: 'Aurya per operatori — tu crei l’esperienza, noi la facciamo trovare' }),
    description: t('op.seoDesc', { defaultValue: 'Aurya sta per aprire: il marketplace italiano dei ritiri olistici. Visibilità vera, prenotazioni con caparra protetta, gestione semplice. Presentati: i primi operatori partono da fondatori.' }),
  });

  const benefits = [
    { icon: Eye, title: t('op.b1t', { defaultValue: 'Ti trovano davvero' }),
      body: t('op.b1b', { defaultValue: 'Il tuo profilo e i tuoi ritiri ottimizzati per chi cerca su Google "ritiro yoga vicino a me". Appari dove le persone scelgono, non dove urli più forte.' }) },
    { icon: ShieldCheck, title: t('op.b2t', { defaultValue: 'Meno posti vuoti' }),
      body: t('op.b2b', { defaultValue: 'Prenotazione online con caparra protetta da Stripe e promemoria automatici: chi si iscrive arriva. I no-show smettono di essere il costo nascosto del tuo lavoro.' }) },
    { icon: HeartHandshake, title: t('op.b3t', { defaultValue: 'Tu pensi alle persone' }),
      body: t('op.b3b', { defaultValue: 'Calendario, partecipanti, recensioni verificate e incassi in un posto solo. Il tempo che perdevi in messaggi e fogli di calcolo torna alle persone che accompagni.' }) },
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
              {t('op.eyebrow', { defaultValue: 'Per chi crea esperienze di benessere' })}
            </p>
            <h1 className="mt-3 font-heading text-3xl font-semibold leading-tight text-foreground md:text-5xl">
              {t('op.title', { defaultValue: 'Tu crei l’esperienza. Noi la facciamo trovare.' })}
            </h1>
            <p className="mt-4 text-base text-muted-foreground md:text-lg">
              {t('op.subtitle', { defaultValue: 'Hai costruito qualcosa di prezioso: un luogo, una pratica, una comunità. Meriti di essere trovato da chi lo sta cercando, senza rincorrere gli algoritmi. Aurya sta per aprire: il marketplace italiano dei ritiri olistici.' })}
            </p>
            {/* vantaggio fondatori: la ragione per iscriversi ORA */}
            <div className="mt-5 inline-flex items-start gap-2 rounded-2xl border px-4 py-3"
                 style={{ borderColor: `${ACCENT}55`, background: `${ACCENT}0d` }}>
              <Sparkles className="mt-0.5 h-4 w-4 shrink-0" style={{ color: ACCENT }} />
              <p className="text-sm text-muted-foreground">
                <span className="font-semibold text-foreground">
                  {t('op.foundersT', { defaultValue: 'I primi partono da fondatori.' })}
                </span>{' '}
                {t('op.foundersB', { defaultValue: 'Chi sale a bordo ora avrà visibilità in prima fila al lancio e condizioni riservate. Ti ricontattiamo personalmente.' })}
              </p>
            </div>
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
          {t('op.ctaTitle', { defaultValue: 'Presentati: ci conosciamo' })}
        </h2>
        <p className="mt-2 text-sm text-muted-foreground">
          {t('op.ctaBody', { defaultValue: 'Due righe su di te e sulla tua attività. Ti scriviamo noi, personalmente, prima del lancio. Niente call center, niente spam.' })}
        </p>
        <div className="mx-auto mt-5 max-w-md text-left">
          <LeadForm type="operator" accent={ACCENT} />
        </div>
        <Link to="/" className="mt-8 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-4 w-4" /> {t('op.back', { defaultValue: 'Torna alla home' })}
        </Link>
      </section>
    </div>
  );
}
