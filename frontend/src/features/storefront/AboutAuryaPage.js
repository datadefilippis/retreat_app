/**
 * AboutAuryaPage — /chi-siamo (AN1).
 *
 * La pagina istituzionale che mancava: chi è Aurya, missione, visione,
 * cosa promette a chi cerca e a chi organizza. Copy da
 * docs/BRAND_AURYA.md via landings.json (aboutPage.*) ×4 lingue.
 * SEO servita anche ai crawler dalla SEO shell (backend).
 */
import React from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { ArrowRight, Compass, HeartHandshake } from 'lucide-react';
import MarketplaceShell from './components/MarketplaceShell';
import useSeoMeta from './lib/useSeoMeta';
import { BRAND_NAME } from '../../config/brand';

export default function AboutAuryaPage() {
  const { t } = useTranslation('landings');

  useSeoMeta({
    title: t('aboutPage.seoTitle'),
    description: t('aboutPage.seoDesc'),
    canonicalPath: '/chi-siamo',
  });

  return (
    <MarketplaceShell noSearch>
      <div className="bg-background">
        <header className="bg-gradient-sidebar text-white">
          <div className="max-w-3xl mx-auto px-4 py-14 text-center">
            <h1 className="font-display text-3xl md:text-4xl font-bold">{t('aboutPage.title')}</h1>
            <p className="text-white/85 mt-4 text-lg leading-relaxed">{t('aboutPage.intro')}</p>
          </div>
        </header>

        <main className="max-w-3xl mx-auto px-4 py-12 space-y-10">
          <section>
            <h2 className="font-heading text-xl font-semibold text-foreground">{t('aboutPage.missionTitle')}</h2>
            <p className="text-muted-foreground mt-2 leading-relaxed">{t('aboutPage.missionBody')}</p>
          </section>
          <section>
            <h2 className="font-heading text-xl font-semibold text-foreground">{t('aboutPage.visionTitle')}</h2>
            <p className="text-muted-foreground mt-2 leading-relaxed">{t('aboutPage.visionBody')}</p>
          </section>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <section className="rounded-2xl border border-border bg-card p-6">
              <Compass className="h-6 w-6 text-[#376254]" aria-hidden />
              <h2 className="font-heading text-lg font-semibold text-foreground mt-3">{t('aboutPage.forSeekersTitle')}</h2>
              <p className="text-sm text-muted-foreground mt-2 leading-relaxed">{t('aboutPage.forSeekersBody')}</p>
            </section>
            <section className="rounded-2xl border border-border bg-card p-6">
              <HeartHandshake className="h-6 w-6 text-[#C97B5D]" aria-hidden />
              <h2 className="font-heading text-lg font-semibold text-foreground mt-3">{t('aboutPage.forOrganizersTitle')}</h2>
              <p className="text-sm text-muted-foreground mt-2 leading-relaxed">{t('aboutPage.forOrganizersBody')}</p>
            </section>
          </div>

          <p className="text-center pt-2">
            <Link to="/" className="inline-flex items-center gap-1.5 rounded-full bg-[#376254] text-white px-6 py-2.5 text-sm font-semibold hover:bg-[#2c4f43]">
              {t('aboutPage.cta')} <ArrowRight className="h-4 w-4" aria-hidden />
            </Link>
          </p>
          <p className="text-center text-xs text-muted-foreground">{BRAND_NAME} — Connect. Heal. Grow.</p>
        </main>
      </div>
    </MarketplaceShell>
  );
}
