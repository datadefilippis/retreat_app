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
        <header className="bg-gradient-sidebar text-white">
          <div className="max-w-3xl mx-auto px-4 py-14 text-center">
            <p aria-hidden className="font-brand uppercase tracking-[0.35em] text-[11px] text-[#d6c49a] mb-3 select-none">Connect · Heal · Grow</p>
            <h1 className="font-display text-3xl md:text-4xl font-bold">{t('howPage.title')}</h1>
            <p className="text-white/85 mt-4 text-lg leading-relaxed">{t('howPage.intro')}</p>
          </div>
        </header>

        <main className="max-w-3xl mx-auto px-4 py-12 space-y-12">
          <section aria-label={t('howPage.title')}>
            <ol className="space-y-4">
              {STEPS.map((s, i) => (
                <li key={s.t} className="rounded-2xl border border-border bg-card p-5 flex items-start gap-4">
                  <span aria-hidden className="shrink-0 h-9 w-9 rounded-full bg-[#376254] text-white font-bold flex items-center justify-center">
                    {i + 1}
                  </span>
                  <div>
                    <h2 className="font-semibold text-foreground flex items-center gap-2">
                      <s.icon className="h-4 w-4 text-[#376254]" aria-hidden /> {t(s.t)}
                    </h2>
                    <p className="text-sm text-muted-foreground mt-1 leading-relaxed">{t(s.b)}</p>
                  </div>
                </li>
              ))}
            </ol>
          </section>

          <section aria-labelledby="faq-title">
            <h2 id="faq-title" className="font-heading text-xl font-semibold text-foreground mb-4">
              {t('howPage.faqTitle')}
            </h2>
            <div className="space-y-3">
              {FAQS.map((f) => (
                <details key={f} className="rounded-xl border border-border bg-card p-4 group">
                  <summary className="cursor-pointer font-medium text-foreground list-none flex items-center justify-between">
                    {t(`howPage.${f}q`)}
                    <span aria-hidden className="text-muted-foreground group-open:rotate-45 transition-transform text-lg leading-none">+</span>
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
