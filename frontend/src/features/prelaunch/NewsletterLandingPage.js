/**
 * NewsletterLandingPage — /newsletter (RT1, piano sito-rete).
 *
 * STUB funzionale: l'URL nasce ora e non cambiera' mai; la landing
 * definitiva arriva in RT4 (nome della newsletter, promessa, frequenza,
 * lead magnet — decisioni founder). Nel frattempo la pagina e' onesta e
 * raccoglie iscrizioni col LeadForm viaggiatore esistente (dedup e
 * notifica gia' cablate), cosi' il link in bio Instagram puo' gia'
 * puntare qui senza perdere nessuno.
 */
import React from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Mail, ArrowLeft } from 'lucide-react';
import useSeoMeta from '../storefront/lib/useSeoMeta';
import { LangSwitcher } from '../storefront/components/MarketplaceShell';
import LeadForm from './LeadForm';

const GOLD = '#8a7440';

export default function NewsletterLandingPage() {
  const { t } = useTranslation('prelaunch');
  useSeoMeta({
    title: t('nl.seoTitle', { defaultValue: 'Newsletter | Aurya' }),
    description: t('nl.seoDesc', { defaultValue: 'Ricevi da Aurya pratiche, storie e persone del benessere olistico in Italia. Una lettera curata, niente rumore.' }),
  });

  return (
    <div className="min-h-screen bg-[#f7f9f6]">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-5 py-4 md:px-10">
        <Link to="/" className="font-brand text-xl tracking-[0.3em] text-[#8a7440]">AURYA</Link>
        <div className="flex items-center gap-3">
          <LangSwitcher />
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
          <p className="mx-auto mt-4 max-w-xl text-base leading-relaxed text-gray-600">
            {t('nl.body', { defaultValue: 'Pratiche, storie e persone del benessere olistico in Italia, raccontate con cura. Lascia il tuo contatto: ti scriviamo noi, senza rumore e senza fretta.' })}
          </p>
        </div>

        <div className="mt-10">
          <LeadForm type="traveler" accent={GOLD} />
        </div>
      </main>
    </div>
  );
}
