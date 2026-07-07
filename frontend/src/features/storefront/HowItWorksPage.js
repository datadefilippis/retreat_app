/**
 * HowItWorksPage — /come-funziona (AN1).
 *
 * I 4 passi (riuso del copy brandHome.how*) + le FAQ di fiducia
 * (caparra, recensioni, Passaporto, costi per organizzatori) con
 * JSON-LD FAQPage per la SERP. Copy in landings.json (howPage.*) ×4.
 */
import React from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { ArrowRight, Compass, Wallet, Ticket, MessageSquareHeart } from 'lucide-react';
import MarketplaceShell from './components/MarketplaceShell';
import useSeoMeta from './lib/useSeoMeta';

const STEPS = [
  { icon: Compass, t: 'brandHome.how1t', b: 'brandHome.how1b' },
  { icon: Wallet, t: 'brandHome.how2t', b: 'brandHome.how2b' },
  { icon: Ticket, t: 'brandHome.how3t', b: 'brandHome.how3b' },
  { icon: MessageSquareHeart, t: 'brandHome.how4t', b: 'brandHome.how4b' },
];
const FAQS = ['faq1', 'faq2', 'faq3', 'faq4'];

export default function HowItWorksPage() {
  const { t } = useTranslation('landings');

  useSeoMeta({
    title: t('howPage.seoTitle'),
    description: t('howPage.seoDesc'),
    canonicalPath: '/come-funziona',
    jsonLd: {
      '@context': 'https://schema.org',
      '@type': 'FAQPage',
      mainEntity: FAQS.map((f) => ({
        '@type': 'Question',
        name: t(`howPage.${f}q`),
        acceptedAnswer: { '@type': 'Answer', text: t(`howPage.${f}a`) },
      })),
    },
  });

  return (
    <MarketplaceShell noSearch>
      <div className="bg-background">
        <header className="relative bg-gradient-sidebar text-white overflow-hidden">
        <div aria-hidden className="absolute inset-0 pointer-events-none" style={{
          background: 'radial-gradient(ellipse 60% 80% at 15% 10%, rgba(255,255,255,0.08), transparent 60%), radial-gradient(ellipse 50% 70% at 85% 90%, rgba(193,102,61,0.22), transparent 55%)',
        }} />
          <div className="relative max-w-3xl mx-auto px-4 py-14 text-center">
            <p aria-hidden className="font-brand uppercase tracking-[0.35em] text-[11px] text-[#d6c49a] mb-3 select-none">Connect · Heal · Grow</p>
            <h1 className="font-display text-3xl md:text-4xl font-bold">{t('howPage.title')}</h1>
            <p className="text-white/85 mt-4 text-lg leading-relaxed">{t('howPage.intro')}</p>
          </div>
        </header>

        <main className="max-w-3xl mx-auto px-4 py-12 space-y-12">
          <section aria-label={t('howPage.title')}>
            {/* il cammino: un filo d'oro verticale lega i quattro passi */}
            <ol className="relative space-y-12 before:absolute before:left-[35px] before:top-4 before:bottom-4 before:w-px before:bg-gradient-to-b before:from-[#c9b37e] before:via-[#8a7440] before:to-transparent">
              {STEPS.map((s, i) => (
                <li key={s.t} className="relative flex items-start gap-6">
                  <span className="relative z-10 shrink-0 h-[72px] w-[72px] rounded-full bg-white ring-1 ring-[#8a7440]/40 shadow-[0_10px_28px_-10px_rgba(138,116,64,0.45)] flex items-center justify-center">
                    <s.icon className="h-8 w-8 text-[#376254]" aria-hidden />
                  </span>
                  <div className="pt-1.5">
                    <p aria-hidden className="font-brand text-[11px] tracking-[0.3em] uppercase text-[#8a7440] select-none">
                      {t('howPage.stepLabel', { n: i + 1, defaultValue: 'Passo {{n}}' })}
                    </p>
                    <h2 className="font-display text-xl md:text-2xl font-semibold text-foreground mt-1">{t(s.t)}</h2>
                    <p className="text-muted-foreground mt-2 leading-relaxed">{t(s.b)}</p>
                  </div>
                </li>
              ))}
            </ol>
          </section>

          <div aria-hidden className="gold-rule max-w-sm mx-auto" />

          <section aria-labelledby="faq-title">
            <h2 id="faq-title" className="font-heading text-xl font-semibold text-foreground mb-4">
              {t('howPage.faqTitle')}
            </h2>
            <div className="space-y-3">
              {FAQS.map((f) => (
                <details key={f} className="rounded-xl border border-border bg-card p-4 group">
                  <summary className="cursor-pointer font-medium text-foreground list-none flex items-center justify-between">
                    {t(`howPage.${f}q`)}
                    <span aria-hidden className="text-[#8a7440] group-open:rotate-45 transition-transform text-lg leading-none">+</span>
                  </summary>
                  <p className="text-sm text-muted-foreground mt-3 leading-relaxed">{t(`howPage.${f}a`)}</p>
                </details>
              ))}
            </div>
          </section>

          <p className="text-center">
            <Link to="/" className="inline-flex items-center gap-1.5 rounded-full bg-[#376254] text-white px-6 py-2.5 text-sm font-semibold hover:bg-[#2c4f43]">
              {t('howPage.cta')} <ArrowRight className="h-4 w-4" aria-hidden />
            </Link>
          </p>
        </main>
      </div>
    </MarketplaceShell>
  );
}
