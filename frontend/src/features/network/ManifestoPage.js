/**
 * ManifestoPage — /manifesto (RT2, piano sito-rete).
 *
 * LA pagina piu' importante del sito della rete: e' il filtro di
 * credibilita' che un operatore legge prima di candidarsi. Assorbe
 * /chi-siamo (redirect permanente in App.js) riusando le chiavi i18n
 * aboutPage.* gia' tradotte x4, e aggiunge le sezioni del manifesto:
 * da dove nasce Aurya, cosa non ci convince del settore, cosa vogliamo
 * costruire. I testi nuovi sono una BOZZA nella voce del brand: la
 * parola definitiva e' del founder (RT0).
 */
import React from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { ArrowRight, Sprout, Eye, Hammer } from 'lucide-react';
import MarketplaceShell from '../storefront/components/MarketplaceShell';
import useSeoMeta from '../storefront/lib/useSeoMeta';
import { BRAND_NAME } from '../../config/brand';

export default function ManifestoPage() {
  const { t } = useTranslation('landings');

  useSeoMeta({
    title: t('manifesto.seoTitle', { defaultValue: 'Il manifesto di Aurya | La rete del benessere olistico in Italia' }),
    description: t('manifesto.seoDesc', { defaultValue: 'Da dove nasce Aurya, cosa vogliamo costruire e chi siamo. La rete degli operatori olistici in Italia, raccontata con onesta.' }),
    canonicalPath: '/manifesto',
  });

  const pillars = [
    {
      icon: Sprout,
      title: t('manifesto.p1t', { defaultValue: 'Da dove nasce Aurya' }),
      body: t('manifesto.p1b', { defaultValue: 'Nasce da un incontro: una operatrice olistica e un costruttore di piattaforme digitali. Abbiamo visto da vicino quanto lavoro invisibile c’è dietro una pratica fatta bene, e quanto poco il web sappia raccontarlo.' }),
    },
    {
      icon: Eye,
      title: t('manifesto.p2t', { defaultValue: 'Cosa non ci convince del settore' }),
      body: t('manifesto.p2b', { defaultValue: 'Vetrine piene di promesse e vuote di persone. Elenchi infiniti dove chi lavora con serietà sparisce in mezzo a chi improvvisa. Il benessere meritava di meglio: volti, percorsi veri, parole dette in prima persona.' }),
    },
    {
      icon: Hammer,
      title: t('manifesto.p3t', { defaultValue: 'Cosa vogliamo costruire' }),
      body: t('manifesto.p3b', { defaultValue: 'Una rete di operatori scelti uno a uno, presentati attraverso interviste vere. Ogni profilo racconta chi sei, come lavori e perché. Prima le persone, poi gli strumenti: il resto arriva quando la rete è viva.' }),
    },
  ];

  return (
    <MarketplaceShell noSearch>
      <div className="bg-background">
        <header className="relative bg-gradient-sidebar text-white overflow-hidden">
          <div aria-hidden className="absolute inset-0 pointer-events-none" style={{
            background: 'radial-gradient(ellipse 60% 80% at 15% 10%, rgba(255,255,255,0.08), transparent 60%), radial-gradient(ellipse 50% 70% at 85% 90%, rgba(193,102,61,0.22), transparent 55%)',
          }} />
          <div className="relative max-w-3xl mx-auto px-4 py-14 text-center">
            <p aria-hidden className="font-brand uppercase tracking-[0.35em] text-[11px] text-[#d6c49a] mb-3 select-none">Connect · Heal · Grow</p>
            <h1 className="font-display text-3xl md:text-4xl font-bold">
              {t('manifesto.title', { defaultValue: 'Il nostro manifesto' })}
            </h1>
            <p className="text-white/85 mt-4 text-lg leading-relaxed">
              {t('manifesto.intro', { defaultValue: 'Aurya è la rete degli operatori olistici in Italia. Persone vere, pratiche serie, raccontate una alla volta.' })}
            </p>
          </div>
        </header>

        <main className="max-w-3xl mx-auto px-4 py-12 space-y-10">
          {/* Le tre sezioni del manifesto */}
          <div className="space-y-6">
            {pillars.map(({ icon: Icon, title, body }) => (
              <section key={title} className="rounded-2xl border border-border bg-card p-6 md:p-8">
                <Icon className="h-6 w-6 text-[#376254]" aria-hidden />
                <h2 className="font-heading text-xl font-semibold text-foreground mt-3">{title}</h2>
                <p className="text-muted-foreground mt-2 leading-relaxed">{body}</p>
              </section>
            ))}
          </div>

          {/* Missione e visione (contenuto gia' tradotto x4 da /chi-siamo) */}
          <section>
            <h2 className="font-heading text-xl font-semibold text-foreground">{t('aboutPage.missionTitle')}</h2>
            <p className="text-muted-foreground mt-2 leading-relaxed">{t('aboutPage.missionBody')}</p>
          </section>
          <section>
            <h2 className="font-heading text-xl font-semibold text-foreground">{t('aboutPage.visionTitle')}</h2>
            <p className="text-muted-foreground mt-2 leading-relaxed">{t('aboutPage.visionBody')}</p>
          </section>

          {/* Chi c'e' dietro: i volti veri (migrato da /chi-siamo) */}
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
                {t('aboutPage.facesBody1', { defaultValue: 'Dietro ad Aurya ci siamo noi: una coppia unita dalla passione per la crescita personale e l’evoluzione interiore. Abbiamo fuso le nostre competenze per creare qualcosa di unico. Valentina è l’anima olistica del progetto: operatrice Reiki di terzo livello, guida le persone attraverso letture evolutive di tarocchi, oracoli e lo studio delle mappe natali. Davide porta la sua esperienza nel mondo digitale, costruendo piattaforme capaci di connettere le persone.' })}
              </p>
              <p className="text-muted-foreground mt-3 leading-relaxed">
                {t('aboutPage.facesBody2', { defaultValue: 'L’approccio olistico e la ricerca della consapevolezza ci hanno uniti come coppia e come professionisti. Crediamo fermamente nell’evoluzione personale e nel valore di ciò che facciamo ogni giorno. Aurya nasce proprio da questa sinergia: l’incontro tra la profondità del benessere autentico e la cura di uno spazio digitale solido, pensato per supportare operatori e anime in cammino.' })}
              </p>
              {/* Una riga sugli strumenti digitali: una riga, non una sezione */}
              <p className="text-xs text-muted-foreground mt-4 italic">
                {t('manifesto.toolsLine', { defaultValue: 'Per la rete stiamo costruendo anche strumenti digitali dedicati: arriveranno quando sarà il momento giusto.' })}
              </p>
            </div>
          </section>

          {/* CTA: entra nella rete */}
          <section className="rounded-3xl bg-gradient-sidebar text-white p-8 text-center overflow-hidden relative">
            <div aria-hidden className="absolute inset-0 pointer-events-none" style={{
              background: 'radial-gradient(ellipse 50% 70% at 85% 90%, rgba(193,102,61,0.22), transparent 55%)',
            }} />
            <div className="relative">
              <h2 className="font-heading text-2xl font-semibold">
                {t('manifesto.ctaTitle', { defaultValue: 'Sei un operatore olistico?' })}
              </h2>
              <p className="text-white/85 mt-2 max-w-xl mx-auto leading-relaxed">
                {t('manifesto.ctaBody', { defaultValue: 'La rete cresce una persona alla volta. Ti intervistiamo, raccontiamo il tuo lavoro e ti diamo un profilo pubblico curato. Gratuitamente.' })}
              </p>
              <Link to="/entra-nella-rete" className="mt-5 inline-flex items-center gap-1.5 rounded-full bg-white text-[#376254] px-6 py-2.5 text-sm font-semibold hover:bg-gray-100">
                {t('manifesto.ctaButton', { defaultValue: 'Entra nella rete' })} <ArrowRight className="h-4 w-4" aria-hidden />
              </Link>
            </div>
          </section>

          <p className="text-center text-xs text-muted-foreground">{BRAND_NAME} — Connect. Heal. Grow.</p>
        </main>
      </div>
    </MarketplaceShell>
  );
}
