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
        <header className="relative bg-gradient-sidebar text-white overflow-hidden">
        <div aria-hidden className="absolute inset-0 pointer-events-none" style={{
          background: 'radial-gradient(ellipse 60% 80% at 15% 10%, rgba(255,255,255,0.08), transparent 60%), radial-gradient(ellipse 50% 70% at 85% 90%, rgba(193,102,61,0.22), transparent 55%)',
        }} />
          <div className="relative max-w-3xl mx-auto px-4 py-14 text-center">
            <p aria-hidden className="font-brand uppercase tracking-[0.35em] text-[11px] text-[#d6c49a] mb-3 select-none">Connect · Heal · Grow</p>
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

          {/* Chi c'è dietro (11/7, scelta founder): i volti veri di chi
              costruisce Aurya. La fiducia si dà a persone, non a loghi. */}
          <section className="rounded-3xl border border-border bg-card overflow-hidden md:grid md:grid-cols-5">
            <div className="md:col-span-2">
              <img
                src="/media/chisiamo-aurya.jpg"
                alt={t('aboutPage.facesAlt', { defaultValue: 'Davide e Valentina, i fondatori di Aurya, in riva al mare' })}
                loading="lazy"
                className="h-64 w-full object-cover md:h-full"
              />
            </div>
            <div className="p-6 md:col-span-3 md:p-8">
              <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-[#8a7440]">
                {t('aboutPage.facesEyebrow', { defaultValue: 'Ci presentiamo' })}
              </p>
              <h2 className="font-heading text-xl font-semibold text-foreground mt-2">
                {t('aboutPage.facesTitle', { defaultValue: 'Siamo Davide e Valentina' })}
              </h2>
              <p className="text-muted-foreground mt-3 leading-relaxed">
                {t('aboutPage.facesBody1', { defaultValue: 'Dietro ad Aurya ci siamo noi: una coppia unita dalla passione per la crescita personale e l’evoluzione interiore. Abbiamo fuso le nostre competenze per creare qualcosa di unico. Valentina è l’anima olistica del progetto: operatrice Reiki di terzo livello, guida le persone attraverso letture evolutive di tarocchi, oracoli e lo studio delle mappe natali. Davide porta la sua esperienza nel mondo digitale, costruendo piattaforme capaci di connettere le persone.' })}
              </p>
              <p className="text-muted-foreground mt-3 leading-relaxed">
                {t('aboutPage.facesBody2', { defaultValue: 'L’approccio olistico e la ricerca della consapevolezza ci hanno uniti come coppia e come professionisti. Crediamo fermamente nell’evoluzione personale e nel valore di ciò che facciamo ogni giorno. Aurya nasce proprio da questa sinergia: l’incontro tra la profondità del benessere autentico e la cura di uno spazio digitale solido, pensato per supportare operatori e anime in cammino.' })}
              </p>
            </div>
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
