/**
 * NewsletterLandingPage — /newsletter (RT4, piano sito-rete).
 *
 * La destinazione del link in bio Instagram e l'unico asset davvero di
 * proprieta'. Regole del piano: un NOME, una FREQUENZA dichiarata, una
 * PROMESSA specifica ("iscriviti agli aggiornamenti" converte al 2%,
 * una promessa concreta molto di piu'). Nome/frequenza/promessa sono
 * BOZZE nella voce del brand: la parola finale e' del founder (RT0).
 *
 * Lead magnet: se NEWSLETTER_LEAD_MAGNET_URL e' valorizzata sul
 * backend (env runtime, zero rebuild), dopo l'iscrizione compare il
 * bottone di download del materiale gratuito.
 */
import React from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Mail, ArrowLeft, Feather, Users, Compass } from 'lucide-react';
import useSeoMeta from '../storefront/lib/useSeoMeta';
import useItalianOnly from '../../lib/useItalianOnly';
import { useSiteConfig } from '../../context/SiteConfigContext';
import LeadForm from './LeadForm';

const GOLD = '#8a7440';

export default function NewsletterLandingPage() {
  useItalianOnly();
  const { t } = useTranslation('prelaunch');
  const { leadMagnetUrl } = useSiteConfig();

  useSeoMeta({
    title: t('nl.seoTitle', { defaultValue: 'La lettera di Aurya | Newsletter sul benessere olistico' }),
    description: t('nl.seoDesc', { defaultValue: 'Una lettera ogni due settimane su pratiche, storie e persone del benessere olistico in Italia. Curata, senza rumore.' }),
  });

  const pillars = [
    { icon: Feather,
      title: t('nl.w1t', { defaultValue: 'Una pratica, raccontata bene' }),
      body: t('nl.w1b', { defaultValue: 'Ogni lettera approfondisce un tema vero: respiro, meditazione, discipline olistiche. Con onestà, incluse le controindicazioni.' }) },
    { icon: Users,
      title: t('nl.w2t', { defaultValue: 'Una persona della rete' }),
      body: t('nl.w2b', { defaultValue: 'Il volto e la storia di un operatore intervistato da noi: chi è, come lavora, perché fidarsi.' }) },
    { icon: Compass,
      title: t('nl.w3t', { defaultValue: 'Una direzione' }),
      body: t('nl.w3b', { defaultValue: 'Cosa stiamo costruendo con Aurya, senza filtri: le scelte, i dubbi, i passi avanti.' }) },
  ];

  return (
    <div className="min-h-screen bg-[#f7f9f6]">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-5 py-4 md:px-10">
        <Link to="/" className="font-brand text-xl tracking-[0.3em] text-[#8a7440]">AURYA</Link>
        <div className="flex items-center gap-3">
          <Link to="/" className="inline-flex items-center gap-1.5 text-sm text-gray-600 hover:text-gray-900">
            <ArrowLeft className="h-4 w-4" />
            {t('nl.back', { defaultValue: 'Torna alla home' })}
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-2xl px-5 pb-20 pt-10 md:px-0 md:pt-16">
        <div className="text-center">
          <span className="inline-flex h-12 w-12 items-center justify-center rounded-full"
                style={{ backgroundColor: `${GOLD}22` }}>
            <Mail className="h-6 w-6" style={{ color: GOLD }} />
          </span>
          <h1 className="mt-5 font-brand text-3xl text-gray-900 md:text-4xl">
            {t('nl.title', { defaultValue: 'La lettera di Aurya' })}
          </h1>
          {/* la promessa: cosa, per chi, ogni quanto */}
          <p className="mx-auto mt-4 max-w-xl text-base leading-relaxed text-gray-600">
            {t('nl.body', { defaultValue: 'Una lettera ogni due settimane su pratiche, storie e persone del benessere olistico in Italia. La scriviamo noi, Davide e Valentina: niente rumore, niente fretta, mai spam.' })}
          </p>
        </div>

        {/* cosa trovi dentro */}
        <div className="mt-10 grid grid-cols-1 gap-4 sm:grid-cols-3">
          {pillars.map(({ icon: Icon, title, body }) => (
            <div key={title} className="rounded-2xl border border-gray-200 bg-white p-5 text-center">
              <Icon className="mx-auto h-5 w-5" style={{ color: GOLD }} aria-hidden />
              <h2 className="mt-2 font-heading text-sm font-semibold text-gray-900">{title}</h2>
              <p className="mt-1.5 text-xs leading-relaxed text-gray-500">{body}</p>
            </div>
          ))}
        </div>

        {/* lead magnet promesso PRIMA del form, se configurato. BN2:
            la consegna avviene sulla pagina di CONFERMA (double opt-in),
            e la promessa lo dice onestamente. */}
        {leadMagnetUrl && (
          <p className="mt-8 text-center text-sm text-gray-600">
            {t('nl.magnetPromiseDoi', { defaultValue: 'Confermando l’iscrizione ricevi subito il nostro materiale gratuito di benvenuto.' })}
          </p>
        )}

        <div className="mt-8">
          <LeadForm
            type="traveler"
            subscribe
            accent={GOLD}
            context="newsletter"
            consentText={t('blogCta.consent', { defaultValue: 'Acconsento a ricevere la lettera di Aurya via email.' })}
            thanksBody={t('blogCta.thanksDoi', { defaultValue: 'Quasi fatto: controlla la tua casella e clicca il link di conferma che ti abbiamo appena inviato.' })}
          />
        </div>

        <p className="mt-6 text-center text-xs text-gray-400">
          {t('nl.footer', { defaultValue: 'Puoi disiscriverti quando vuoi, con un click. I tuoi dati restano tuoi.' })}
        </p>
      </main>
    </div>
  );
}
