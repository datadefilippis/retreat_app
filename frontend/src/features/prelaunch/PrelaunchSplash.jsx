/**
 * PrelaunchSplash — home in modalità pre-lancio (PL4).
 *
 * Sostituisce il marketplace quando PRELAUNCH_MODE è attivo (e non sei
 * admin loggato). Presenta Aurya e offre le DUE strade: operatore /
 * viaggiatore, ciascuna verso la propria landing di raccolta lead.
 * Hero video tramonto (asset DS), wordmark oro, motto ufficiale.
 */
import React from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Sparkles, Compass, ArrowRight } from 'lucide-react';
import useSeoMeta from '../storefront/lib/useSeoMeta';

export default function PrelaunchSplash() {
  const { t } = useTranslation('prelaunch');
  useSeoMeta({
    title: t('splash.seoTitle', { defaultValue: 'Aurya — il marketplace dei ritiri olistici sta per aprire' }),
    description: t('splash.seoDesc', { defaultValue: 'Aurya connette chi crea ritiri olistici con chi li cerca. Stiamo preparando il lancio: lascia la tua email e sarai tra i primi.' }),
  });

  return (
    <div className="relative min-h-screen w-full overflow-hidden bg-[#2b3a34]">
      {/* Hero video di sfondo (poster fallback + reduced-motion via .hero-video) */}
      <img src="/media/aurya-hero-poster.jpg" alt=""
           className="absolute inset-0 h-full w-full object-cover" aria-hidden />
      <video className="hero-video absolute inset-0 h-full w-full object-cover"
             autoPlay muted loop playsInline poster="/media/aurya-hero-poster.jpg">
        <source src="/media/aurya-hero.mp4" type="video/mp4" />
      </video>
      {/* Scrim salvia per leggibilità */}
      <div className="absolute inset-0 bg-gradient-to-b from-[#1e2b26]/80 via-[#243530]/70 to-[#1e2b26]/90" aria-hidden />

      <div className="relative z-10 mx-auto flex min-h-screen max-w-5xl flex-col items-center justify-center px-5 py-16 text-center">
        {/* Wordmark */}
        <p className="font-brand text-4xl tracking-[0.35em] text-[#d6c49a] md:text-5xl">AURYA</p>
        <p className="mt-2 text-xs uppercase tracking-[0.3em] text-white/70">Connect · Heal · Grow</p>

        {/* Badge "in preparazione" */}
        <div className="mt-8 inline-flex items-center gap-2 rounded-full border border-white/25 bg-black/25 px-4 py-1.5 text-xs font-medium text-white backdrop-blur">
          <Sparkles className="h-3.5 w-3.5 text-[#d6c49a]" />
          {t('splash.badge', { defaultValue: 'Stiamo preparando il lancio' })}
        </div>

        {/* Headline */}
        <h1 className="mt-6 max-w-3xl font-heading text-3xl font-medium leading-tight text-white text-hero-shadow md:text-5xl">
          {t('splash.title', { defaultValue: 'Il marketplace dei ritiri olistici sta per aprire' })}
        </h1>
        <p className="mt-4 max-w-xl text-base text-white/85 md:text-lg">
          {t('splash.subtitle', { defaultValue: 'Aurya connette chi crea esperienze di benessere autentico con chi le cerca. Scegli la tua strada.' })}
        </p>

        {/* Due strade */}
        <div className="mt-10 grid w-full max-w-2xl gap-4 sm:grid-cols-2">
          <Link to="/cerca-ritiro"
                className="group rounded-2xl border border-white/20 bg-white/10 p-6 text-left backdrop-blur transition-colors hover:bg-white/20">
            <Compass className="h-7 w-7 text-[#d6c49a]" />
            <p className="mt-3 font-heading text-lg font-semibold text-white">
              {t('splash.travelerTitle', { defaultValue: 'Cerchi un ritiro olistico?' })}
            </p>
            <p className="mt-1 text-sm text-white/75">
              {t('splash.travelerText', { defaultValue: 'Scopri il progetto e sii tra i primi a prenotare al lancio.' })}
            </p>
            <span className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-[#d6c49a]">
              {t('splash.discover', { defaultValue: 'Scopri di più' })}
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
            </span>
          </Link>

          <Link to="/per-operatori"
                className="group rounded-2xl border border-white/20 bg-white/10 p-6 text-left backdrop-blur transition-colors hover:bg-white/20">
            <Sparkles className="h-7 w-7 text-[#e0a672]" />
            <p className="mt-3 font-heading text-lg font-semibold text-white">
              {t('splash.operatorTitle', { defaultValue: 'Sei un operatore olistico?' })}
            </p>
            <p className="mt-1 text-sm text-white/75">
              {t('splash.operatorText', { defaultValue: 'Porta i tuoi ritiri su Aurya e fatti trovare da chi cerca proprio te.' })}
            </p>
            <span className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-[#e0a672]">
              {t('splash.discover', { defaultValue: 'Scopri di più' })}
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
            </span>
          </Link>
        </div>

        {/* Sbirciata alla vetrina in anteprima */}
        <Link to="/ritiri"
              className="mt-8 text-sm text-white/70 underline underline-offset-4 hover:text-white">
          {t('splash.peek', { defaultValue: 'Dai un’occhiata all’anteprima dei ritiri' })}
        </Link>
      </div>
    </div>
  );
}
