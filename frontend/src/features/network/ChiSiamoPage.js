/**
 * ChiSiamoPage — /chi-siamo (CS2 → SR4, 3/9/2026).
 *
 * LA REGOLA DEL FOUNDER resta: «questa pagina non deve rispondere a
 * "chi sono Davide e Valentina?". Deve rispondere a "perche' dovrei
 * fidarmi di chi sta costruendo Aurya?"».
 *
 * SR4 (founder 3/9: «in chi siamo vedo cose ridondanti... integrare il
 * manifesto o teniamo separato? rimozione ridondanze e concetti che
 * creano sforzo cognitivo»). Decisione: due pagine, DUE RUOLI, zero
 * doppioni. Il Manifesto e' il PERCHE' (la domanda distesa, in cosa
 * crediamo, i cinque principi, cosa stiamo costruendo). Chi siamo e'
 * la FIDUCIA: chi c'e' dietro, con che ordine costruisce, dove
 * scrivergli. Sono uscite da qui le tre cose che il Manifesto diceva
 * gia' meglio: la domanda distesa (cs-distance), i quattro principi
 * («Come lavoriamo», due dei quali con lo stesso titolo dei principi
 * del Manifesto) e la scala delle quattro «persone che costruiranno»
 * (un elenco di funzioni travestito da persone). Da 417 a ~200 parole.
 *
 * I MOVIMENTI: apertura (la domanda, r08) con la porta al Manifesto
 * subito sotto → i due percorsi (la foto vera, PhotoSplit) → il lungo
 * periodo (i quattro tempi, verde) → la chiusura (una frase, tre
 * porte, l'indirizzo). Fondi: foto scura → bianco+foto → verde → sabbia.
 *
 * CONTRASTI: misurati in CS2 (git), invariati: crema sui veli di r08
 * ≥ 11:1, oro chiaro 7,2:1; crema su salvia 7,28:1; foreground su
 * bianco/sabbia > 12.
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import MarketplaceShell from '../storefront/components/MarketplaceShell';
import useSeoMeta from '../storefront/lib/useSeoMeta';
import { BRAND_EMAIL } from '../../config/brand';
import {
  Section, DisplayTitle, Lede, EditorialCta, PhotoOpener, PhotoSplit,
} from '../../components/editorial';

const OPENER_PHOTO = '/media/prelaunch/r08.jpg';   // le mani di chi cura
const FOUNDERS_PHOTO = '/media/chisiamo-aurya.jpg'; // l'unica foto nostra

/* Il filo che collega i quattro tempi si fa piu' netto a ogni passo:
   e' decorativo (aria-hidden), quindi il contrasto non lo riguarda. */
const STEP_LINE = [
  'bg-[#f6f2e8]/20',
  'bg-[#f6f2e8]/35',
  'bg-[#f6f2e8]/50',
  'bg-[#f6f2e8]/70',
];

export default function ChiSiamoPage() {
  const { t } = useTranslation('landings');

  useSeoMeta({
    title: t('aboutPage.seoTitle', { defaultValue: 'Chi siamo | Aurya' }),
    description: t('aboutPage.seoDesc', { defaultValue: 'Aurya nasce da una domanda: perché è così difficile orientarsi nel mondo del benessere? Chi siamo, come lavoriamo e cosa stiamo costruendo.' }),
    canonicalPath: '/chi-siamo',
  });

  /* I quattro tempi. L'ordine e' il contenuto. */
  const steps = [
    t('aboutPage.step1', { defaultValue: 'Prima i contenuti.' }),
    t('aboutPage.step2', { defaultValue: 'Poi le persone.' }),
    t('aboutPage.step3', { defaultValue: 'Poi le esperienze.' }),
    t('aboutPage.step4', { defaultValue: 'Infine gli strumenti.' }),
  ];

  return (
    <MarketplaceShell noSearch>
      <div className="bg-background">

        {/* ── APERTURA — la domanda, dentro la fotografia ──────────
            L'h1 e' la frase del founder; la domanda vera gli sta sotto,
            in corsivo e in oro. Subito sotto la porta al perche' per
            esteso: e' il Manifesto, non questa pagina. */}
        <PhotoOpener
          data-testid="cs-open"
          image={OPENER_PHOTO}
          focus="50% 45%"
          height="tall"
          align="left"
          width="max-w-3xl"
          labelledBy="cs-open-title"
          eyebrow={t('aboutPage.title', { defaultValue: 'Chi siamo' })}
        >
          <DisplayTitle as="h1" id="cs-open-title" size="manifesto" measure="wide"
                        className="text-hero-shadow">
            {t('aboutPage.heroTitle', { defaultValue: 'Tutto inizia da una domanda.' })}
          </DisplayTitle>
          <div aria-hidden className="gold-rule mt-8 max-w-[9rem]" />
          <p className="mt-8 max-w-[26ch] font-display text-balance text-[1.3rem] italic
                        leading-snug text-[#d6c49a] text-hero-shadow sm:text-[1.6rem] lg:text-[1.9rem]">
            {t('aboutPage.heroQuestion', { defaultValue: 'Di cosa ho davvero bisogno per stare meglio?' })}
          </p>
          <p className="mt-9">
            <EditorialCta to="/manifesto" variant="quiet" tone="dark" data-testid="cs-cta-manifesto">
              {t('aboutPage.ctaManifesto', { defaultValue: 'Perché esiste Aurya: il Manifesto' })}
            </EditorialCta>
          </p>
        </PhotoOpener>

        {/* ── 1. DUE PERCORSI — bianco, con la foto vera ───────────
            Le due persone, con le due competenze che il problema
            richiede. Il testo del founder (CS2b) e' tenuto alla lettera
            nelle biografie; e' uscita la coda generica («crediamo
            fermamente nell'evoluzione personale»): resta la sintesi. */}
        <PhotoSplit
          data-testid="cs-paths"
          image={FOUNDERS_PHOTO}
          imageAlt={t('aboutPage.facesAlt', { defaultValue: 'Davide e Valentina, i fondatori di Aurya, in riva al mare' })}
          focus="50% 34%"
          side="left"
          tone="paper"
          imageWidth="900"
          imageHeight="886"
          labelledBy="cs-paths-title"
        >
          <DisplayTitle as="h2" id="cs-paths-title" size="section" measure="title">
            {t('aboutPage.pathsTitle', { defaultValue: 'Siamo Davide e Valentina' })}
          </DisplayTitle>
          <Lede size="lead" className="mt-6">
            {t('aboutPage.pathsLead', { defaultValue: 'Dietro ad Aurya ci siamo noi: una coppia unita dalla passione per la crescita personale e l’evoluzione interiore. Abbiamo fuso le nostre competenze per creare qualcosa di unico.' })}
          </Lede>

          <div className="mt-10 space-y-9 sm:mt-12 sm:space-y-10">
            <div>
              <div aria-hidden className="gold-rule max-w-[5rem]" />
              <p className="mt-5 font-display text-balance text-[1.2rem] leading-[1.3]
                            tracking-[-0.01em] text-foreground sm:text-[1.35rem]">
                {t('aboutPage.pathsValentina1', { defaultValue: 'Valentina è l’anima olistica del progetto:' })}
              </p>
              <Lede size="body" className="mt-3">
                {t('aboutPage.pathsValentina2', { defaultValue: 'operatrice Reiki di terzo livello, guida le persone attraverso letture evolutive di tarocchi, oracoli e lo studio delle mappe natali.' })}
              </Lede>
            </div>
            <div>
              <div aria-hidden className="gold-rule max-w-[5rem]" />
              <p className="mt-5 font-display text-balance text-[1.2rem] leading-[1.3]
                            tracking-[-0.01em] text-foreground sm:text-[1.35rem]">
                {t('aboutPage.pathsDavide1', { defaultValue: 'Davide porta la sua esperienza nel mondo digitale,' })}
              </p>
              <Lede size="body" className="mt-3">
                {t('aboutPage.pathsDavide2', { defaultValue: 'costruendo piattaforme capaci di connettere le persone.' })}
              </Lede>
            </div>
          </div>

          <div className="mt-12 sm:mt-14">
            <div aria-hidden className="gold-rule" />
            <p className="mt-6 max-w-[42ch] font-display text-balance text-[1.4rem] font-medium
                          leading-[1.22] tracking-[-0.015em] sm:text-[1.75rem]">
              {t('aboutPage.pathsClose3', { defaultValue: 'Aurya nasce proprio da questa sinergia: l’incontro tra la profondità del benessere autentico e la cura di uno spazio digitale solido, pensato per supportare operatori e anime in cammino.' })}
            </p>
          </div>
        </PhotoSplit>

        {/* ── 2. LUNGO PERIODO — l'ancora verde ────────────────────
            Dichiarare in anticipo l'ordine dei passi e' l'unica
            promessa che si puo' verificare. La porta a meta' pagina fa
            vedere il gradino su cui siamo: le persone sono arrivate. */}
        <Section tone="sage" rhythm="none" width="max-w-4xl"
                 labelledBy="cs-long-title"
                 innerClassName="py-24 sm:py-32 lg:py-36">
          <div data-testid="cs-long">
            <DisplayTitle as="h2" id="cs-long-title" size="section" measure="title"
                          className="text-[2.1rem] sm:text-[2.9rem] lg:text-[3.4rem] lg:leading-[1.06]">
              {t('aboutPage.longTitle', { defaultValue: 'Più che una startup, un progetto di lungo periodo.' })}
            </DisplayTitle>
            <p className="mt-8 max-w-[24ch] font-display text-balance text-[1.5rem] font-medium
                          leading-[1.22] tracking-[-0.015em] sm:text-[1.9rem] lg:text-[2.05rem]">
              {t('aboutPage.longP3', { defaultValue: 'Per questo abbiamo deciso di partire lentamente.' })}
            </p>

            <ol className="mt-14 grid list-none gap-9 p-0 sm:mt-16 sm:grid-cols-2 sm:gap-10 lg:grid-cols-4 lg:gap-7">
              {steps.map((s, i) => (
                <li key={s}>
                  <div aria-hidden className="flex items-center gap-3">
                    <span className="h-1.5 w-1.5 shrink-0 rotate-45 bg-[#d6c49a]" />
                    <span className={`h-px w-full ${STEP_LINE[i]}`} />
                  </div>
                  <p className="eyebrow eyebrow-light mt-5">{`0${i + 1}`}</p>
                  <p className="mt-3 font-display text-balance text-[1.2rem] leading-[1.28]
                                tracking-[-0.01em] sm:text-[1.3rem]">
                    {s}
                  </p>
                </li>
              ))}
            </ol>

            <Lede size="body" tone="inherit" className="mt-12 opacity-90 sm:mt-14">
              {t('aboutPage.stepsClose', { defaultValue: 'Ogni passo serve a costruire il successivo.' })}
            </Lede>
            <p className="mt-10 sm:mt-12">
              <EditorialCta to="/operatori" variant="light" data-testid="cs-cta-mid">
                {t('aboutPage.midCta', { defaultValue: 'Scopri i professionisti' })}
              </EditorialCta>
            </p>
          </div>
        </Section>

        {/* ── 3. CHIUSURA — una frase, tre porte, l'indirizzo ──────
            "Sei un professionista?" porta a /entra-nella-rete e non a
            /operatori: chi legge questa domanda deve ancora candidarsi. */}
        <Section tone="sand" rhythm="screen" width="max-w-3xl"
                 labelledBy="cs-together-title">
          <div data-testid="cs-together">
            <DisplayTitle as="h2" id="cs-together-title" size="section" measure="title">
              {t('aboutPage.togetherTitle', { defaultValue: 'Stiamo costruendo questo insieme.' })}
            </DisplayTitle>
            <p className="mt-8 max-w-[28ch] font-display text-balance text-[1.4rem] font-medium
                          leading-[1.22] tracking-[-0.015em] sm:text-[1.8rem] lg:text-[1.95rem]">
              {t('aboutPage.togetherClose', { defaultValue: 'Questo progetto esiste perché crediamo che il benessere sia qualcosa che si costruisce insieme.' })}
            </p>

            <div className="mt-10 flex flex-col items-start gap-5 sm:mt-12 sm:flex-row sm:flex-wrap sm:items-center sm:gap-8">
              <EditorialCta to="/newsletter" variant="solid" data-testid="cs-cta-letter">
                {t('aboutPage.ctaLetter', { defaultValue: 'Entra nel Cerchio di Aurya' })}
              </EditorialCta>
              <EditorialCta to="/entra-nella-rete" variant="quiet" data-testid="cs-cta-pro">
                {t('aboutPage.ctaPro', { defaultValue: 'Sei un professionista?' })}
              </EditorialCta>
              <EditorialCta to="/blog" variant="quiet" data-testid="cs-cta-magazine">
                {t('aboutPage.ctaMagazine', { defaultValue: 'Esplora il Magazine' })}
              </EditorialCta>
            </div>

            {/* OF1 — la porta che mancava: chi arriva in fondo convinto
                e NON e' un professionista deve poterci scrivere.
                L'indirizzo e' scritto per esteso: `select-all` lo
                prende tutto con un clic. */}
            <p className="mt-12 text-base leading-relaxed text-foreground/75 sm:mt-14 sm:text-lg"
               data-testid="cs-contact">
              {t('aboutPage.contactLead', { defaultValue: 'Vuoi dirci qualcosa? Scrivici:' })}{' '}
              <a href={`mailto:${BRAND_EMAIL}`}
                 className="select-all font-medium text-[#2f5749] underline underline-offset-4">
                {BRAND_EMAIL}
              </a>
            </p>
          </div>
        </Section>

      </div>
    </MarketplaceShell>
  );
}
