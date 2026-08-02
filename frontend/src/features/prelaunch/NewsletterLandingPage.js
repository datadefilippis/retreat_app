/**
 * NewsletterLandingPage — /newsletter: «La Lettera di Aurya» (LT1).
 *
 * IL NOME. Il founder: «Io non la chiamerei quasi mai "newsletter". La
 * chiamerei sempre La Lettera di Aurya, perche' e' molto piu' coerente
 * col brand.» Dentro questa pagina la parola "newsletter" non compare
 * piu' in nessun testo che si legge, titolo SEO compreso. Restano
 * tecniche le cose che non si vedono e che non sono un vestito: la
 * rotta /newsletter (canonica, indicizzata), l'endpoint
 * /public/newsletter/subscribe, i nomi delle chiavi i18n. Quelle non si
 * rinominano per una questione di lessico. Le etichette FUORI da questa
 * pagina (menu, footer, altre pagine) le cambia il founder.
 *
 * IL COPY e' del founder, parola per parola (LT1): sistemata solo la
 * punteggiatura tipografica (apostrofi curvi). Chiavi nel namespace
 * `prelaunch`, blocco `nl`, con defaultValue italiano.
 *
 * LA PAGINA IN CINQUE BATTUTE, coi fondi che si alternano sempre
 * (grammatica DS, docs/DESIGN_PASS_DS_2026-08.md):
 *   1. apertura fotografica scura — «Una lettera, ogni tanto.»
 *   2. crema — «Cosa troverai.», tre schede bianche
 *   3. fascia fotografica a tutta larghezza — «Per chi e' questa
 *      lettera?»: il respiro di meta' percorso, subito prima del form
 *   4. sabbia — IL FORM, in una scheda bianca che galleggia
 *   5. salvia — «Prima di salutarci.» e il rimando al Magazine
 *
 * IL FORM E' IL CENTRO, non un modulo in fondo: e' la sezione 4 di 5,
 * ci portano DUE ancore sopra di lui (l'apertura e la fascia) e il
 * bianco della scheda e' l'unico bianco pieno della pagina.
 *
 * LE FOTOGRAFIE. Il magazzino e' esaurito: tutte e dieci le r0* sono
 * impegnate su pagine a un clic da qui (Manifesto, landing
 * professionisti, pagina della rete, home). Restano le due che il sito
 * usa altrove in ruoli diversi, e sono le due giuste per la Lettera:
 *   apertura  hero-destination — il campo in controluce, la sera. E'
 *             GIA' il volto della Lettera sulla home (la scheda che
 *             porta qui usa questa foto): chi clicca ritrova la stessa
 *             immagine e capisce di essere arrivato.
 *   fascia    aurya-hero-poster — il tramonto, cioe' il primo
 *             fotogramma del video della home. In home si vede un
 *             istante e poi parte il video; qui e' una fotografia
 *             ferma, in un altro punto della pagina e a un'altra
 *             misura. Limite dichiarato al founder: con foto
 *             d'archivio si arriva a "curato", non a "inconfondibile".
 *
 * CONTRASTO, MISURATO e non sperato (script LT1: i veli dei componenti
 * composti sui pixel veri del ritaglio, pixel peggiore del riquadro che
 * il testo occupa davvero; 1440 e 390):
 *   apertura, crema #f6f2e8 sul velo di hero-destination . 7,40 / 5,75
 *   apertura, occhiello oro #d6c49a sul velo ............. 4,82
 *   fascia, crema #f6f2e8 sul velo del tramonto .......... 5,56 / 4,52
 *   crema pieno su salvia #2f5749 ........................ 7,28
 *   foreground #1e2f28 su sabbia/bianco .................. > 12
 * Minimo AA: 4,5:1 per il corpo, 3:1 per il display. Sulla fascia il
 * testo e' SOLO crema pieno: l'oro chiaro li' sta a 3,59:1 e non entra.
 *
 * IL FORM (founder, LT1): «Io toglierei tutto. Rimarrebbero solo: Nome,
 * Email, Checkbox Privacy, Pulsante Ricevi la Lettera.» Qui non si
 * tocca ne' la meccanica di invio ne' il doppio opt-in: resta LeadForm
 * con `subscribe`, resta il POST /public/newsletter/subscribe, resta il
 * consenso obbligatorio col SUO testo. Cambiano solo i campi mostrati
 * (`compact` + `showName`) e l'etichetta del bottone.
 *
 * MOVIMENTO. Solo la dissolvenza d'ingresso del kit, spenta da
 * prefers-reduced-motion, e lo scorrimento verso il form che diventa
 * istantaneo per chi ha chiesto meno movimento. Nessuna libreria nuova.
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import MarketplaceShell from '../storefront/components/MarketplaceShell';
import useSeoMeta from '../storefront/lib/useSeoMeta';
import { useSiteConfig } from '../../context/SiteConfigContext';
import LeadForm from './LeadForm';
import {
  Section, DisplayTitle, Lede, EditorialCta, PhotoOpener, PhotoBand,
} from '../../components/editorial';

/* Le due fotografie: il perche' di ciascuna sta nel commento di testa.
   Sono DECORATIVE (alt=""): il titolo dice gia' quello che la foto
   suggerisce, e descrivere uno scatto d'atmosfera a chi ascolta la
   pagina e' rumore. */
const OPENER_PHOTO = '/media/hero-destination.webp';
const BAND_PHOTO = '/media/aurya-hero-poster.jpg';

/** il verde di brand del kit editoriale: la pagina non ha piu' un
    accento proprio (l'oro #8a7440 di RT4), parla la lingua della home */
const SAGE = '#2f5749';

/** l'ancora del form: destinazione delle due CTA interne e dei link che
    dovessero arrivare da fuori (/newsletter#iscriviti) */
const FORM_ANCHOR = '#iscriviti';

/**
 * LetterCard — una delle tre promesse di «Cosa troverai».
 *
 * Stessa superficie delle schede del kit (bianco, angoli generosi,
 * anello tenue, ombra bassa): qui non c'e' una fotografia da mettere in
 * testa — il magazzino e' finito — quindi il segno torna a essere il
 * NUMERALE serif nel verde salvia, che e' la variante `numeral` di
 * PillarCard. E' anche la risposta alla specifica del founder, che
 * chiedeva un'emoji per scheda (libro, foglia, fumetto): l'emoji la
 * disegna il sistema operativo, cambia forma su iOS, Android e Windows
 * ed e' l'unico elemento della pagina che non controlliamo. Il numerale
 * e' identico ovunque e da' alla fila un ordine di lettura esplicito.
 * Nessun piede: nessuna delle tre porta da qualche parte.
 */
function LetterCard({ numeral, title, body }) {
  return (
    <article className="flex h-full flex-col overflow-hidden rounded-[1.75rem] bg-white
                        p-7 ring-1 ring-[#1e2f28]/[0.07] sm:p-8
                        shadow-[0_1px_2px_rgba(30,47,40,0.04),0_18px_40px_-24px_rgba(30,47,40,0.28)]">
      <p aria-hidden className="font-display text-2xl leading-none tracking-[0.02em] text-[#2f5749]/70">
        {numeral}
      </p>
      <h3 className="mt-5 font-display text-[1.4rem] leading-tight text-foreground sm:text-2xl">
        {title}
      </h3>
      <p className="mt-3 max-w-[46ch] text-pretty text-[0.975rem] leading-relaxed text-foreground/75 sm:text-base">
        {body}
      </p>
    </article>
  );
}

export default function NewsletterLandingPage() {
  const { t } = useTranslation('prelaunch');
  const { leadMagnetUrl } = useSiteConfig();

  useSeoMeta({
    title: t('nl.seoTitle', { defaultValue: 'La Lettera di Aurya | Una lettera, ogni tanto' }),
    // 152 caratteri, taglio a 158.
    description: t('nl.seoDesc', { defaultValue: 'Un approfondimento, una persona da conoscere, uno sguardo sul progetto. La Lettera di Aurya raccoglie ciò che pubblichiamo di più prezioso. Niente rumore.' }),
    canonicalPath: '/newsletter',
  });

  /** chi ha chiesto meno movimento non si fa mezza pagina di viaggio */
  const prefersReducedMotion = () => typeof window.matchMedia === 'function'
    && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* Le due CTA interne portano al form. preventDefault: l'hash non
     finisce nell'URL, quindi il gesto si puo' ripetere all'infinito.
     Un <Link to="#iscriviti"> del router avrebbe funzionato solo al
     primo clic. */
  const scrollToForm = (e) => {
    e.preventDefault();
    document.getElementById('iscriviti')?.scrollIntoView({
      behavior: prefersReducedMotion() ? 'auto' : 'smooth',
      block: 'start',
    });
  };

  /* Le tre righe dell'apertura: sono un elenco a voce, non un elenco
     puntato. Restano tre frasi separate perche' il founder le ha
     scritte cosi', una per riga. */
  const heroLines = [
    t('nl.hl1', { defaultValue: 'Una pratica da comprendere.' }),
    t('nl.hl2', { defaultValue: 'Una persona da conoscere.' }),
    t('nl.hl3', { defaultValue: 'Un’idea su cui riflettere.' }),
  ];

  const cards = [
    {
      numeral: '01',
      title: t('nl.c1t', { defaultValue: 'Un approfondimento.' }),
      body: t('nl.c1b', { defaultValue: 'Ogni lettera parte da una domanda. Esploriamo pratiche, discipline e temi legati al benessere con uno sguardo aperto, curioso e concreto.' }),
    },
    {
      numeral: '02',
      title: t('nl.c2t', { defaultValue: 'Una persona.' }),
      body: t('nl.c2b', { defaultValue: 'Ti presenteremo i professionisti che entreranno nella rete Aurya e le loro storie. Perché dietro ogni percorso c’è sempre una persona.' }),
    },
    {
      numeral: '03',
      title: t('nl.c3t', { defaultValue: 'Uno sguardo sul progetto.' }),
      body: t('nl.c3b', { defaultValue: 'Condivideremo anche ciò che stiamo costruendo. Le idee. I dubbi. Le scelte. Perché Aurya crescerà insieme alla sua comunità.' }),
    },
  ];

  const whoLines = [
    t('nl.who1', { defaultValue: 'Per chi ama approfondire.' }),
    t('nl.who2', { defaultValue: 'Per chi preferisce capire prima di scegliere.' }),
    t('nl.who3', { defaultValue: 'Per chi crede che il benessere non sia fatto di risposte facili, ma di domande interessanti.' }),
  ];

  const ctaLetter = t('nl.cta', { defaultValue: 'Ricevi la Lettera' });

  return (
    <MarketplaceShell noSearch>
      <div className="bg-background">

        {/* ── 1. APERTURA — «Una lettera, ogni tanto.» ─────────────
            Il titolo entra DENTRO l'immagine (mai una frase sopra il
            vuoto): hero-destination sotto i due veli calcolati di
            PhotoOpener, testo a sinistra. Le tre righe della promessa
            stanno sopra la foto in corpo display, staccate dal filo
            d'oro; la prima azione della pagina e' qui, non in fondo. */}
        <PhotoOpener
          data-testid="nl-open"
          image={OPENER_PHOTO}
          focus="50% 50%"
          height="tall"
          align="left"
          width="max-w-3xl"
          labelledBy="nl-open-title"
          eyebrow={t('nl.eyebrow', { defaultValue: 'La Lettera di Aurya' })}
        >
          <DisplayTitle as="h1" id="nl-open-title" size="hero" measure="title"
                        className="text-hero-shadow">
            {t('nl.title', { defaultValue: 'Una lettera, ogni tanto.' })}
          </DisplayTitle>

          <div className="mt-8 max-w-[52ch] space-y-2.5 text-hero-shadow sm:space-y-3">
            <p className="text-balance text-lg leading-relaxed opacity-90 sm:text-xl">
              {t('nl.p1', { defaultValue: 'Viviamo in un mondo pieno di notifiche.' })}
            </p>
            <p className="text-balance text-lg leading-relaxed opacity-90 sm:text-xl">
              {t('nl.p2', { defaultValue: 'Noi preferiamo scrivere quando abbiamo davvero qualcosa da condividere.' })}
            </p>
            <p className="text-balance text-lg leading-relaxed opacity-90 sm:text-xl">
              {t('nl.p3', { defaultValue: 'La Lettera di Aurya raccoglie ciò che pubblichiamo di più prezioso.' })}
            </p>
          </div>

          <div aria-hidden className="gold-rule mt-8 max-w-[9rem]" />

          <div className="mt-8 space-y-1.5 text-hero-shadow">
            {heroLines.map((line) => (
              <p key={line}
                 className="font-display text-balance text-xl italic leading-snug sm:text-2xl lg:text-[1.75rem]">
                {line}
              </p>
            ))}
          </div>

          <div className="mt-8 space-y-1 text-hero-shadow">
            <p className="text-base leading-relaxed opacity-90 sm:text-lg">
              {t('nl.p4', { defaultValue: 'Niente rumore.' })}
            </p>
            <p className="text-base leading-relaxed opacity-90 sm:text-lg">
              {t('nl.p5', { defaultValue: 'Solo contenuti che meritano il tuo tempo.' })}
            </p>
          </div>

          <div className="mt-10">
            <EditorialCta href={FORM_ANCHOR} onClick={scrollToForm}
                          variant="solid" tone="dark" data-testid="nl-hero-cta">
              {ctaLetter}
            </EditorialCta>
          </div>
        </PhotoOpener>

        {/* ── 2. COSA TROVERAI — tre promesse sul crema ────────────
            Tre schede bianche affiancate: e' l'unico modo di dire tre
            cose senza fare un elenco puntato. Il numerale serif fa da
            segno al posto delle emoji (vedi LetterCard). */}
        <Section tone="cream" rhythm="screen" width="max-w-5xl"
                 labelledBy="nl-find-title">
          <div data-testid="nl-find">
            <DisplayTitle as="h2" id="nl-find-title" size="section" measure="title">
              {t('nl.findTitle', { defaultValue: 'Cosa troverai.' })}
            </DisplayTitle>
            <div className="mt-10 grid gap-6 sm:gap-7 lg:grid-cols-3">
              {cards.map((c) => (
                <LetterCard key={c.numeral} {...c} />
              ))}
            </div>
          </div>
        </Section>

        {/* ── 3. PER CHI E' — la fascia a tutta larghezza ──────────
            Il respiro di meta' percorso: la pagina esce dalla sua
            colonna e per una schermata si smette di leggere. E' anche
            il punto in cui la domanda diventa personale, quindi la
            seconda ancora verso il form sta qui e non piu' giu'.
            Testo solo crema pieno: le misure stanno in testa al file. */}
        <PhotoBand
          data-testid="nl-who"
          image={BAND_PHOTO}
          focus="50% 40%"
          width="max-w-3xl"
          labelledBy="nl-who-title"
        >
          <DisplayTitle as="h2" id="nl-who-title" size="section" measure="wide"
                        className="mx-auto text-balance text-center text-hero-shadow
                                   text-[1.9rem] leading-[1.12] sm:text-[2.4rem] lg:text-[3rem]">
            {t('nl.whoTitle', { defaultValue: 'Per chi è questa lettera?' })}
          </DisplayTitle>
          <div className="mt-8 max-w-[46ch] space-y-2 text-hero-shadow">
            {whoLines.map((line) => (
              <p key={line} className="text-balance text-lg leading-relaxed sm:text-xl">
                {line}
              </p>
            ))}
          </div>
          <p className="mt-7 max-w-[46ch] text-balance font-display text-xl italic leading-snug text-hero-shadow sm:text-2xl">
            {t('nl.who4', { defaultValue: 'Se ti riconosci in questo modo di guardare il mondo, probabilmente ti sentirai a casa.' })}
          </p>
          <div className="mt-9">
            <EditorialCta href={FORM_ANCHOR} onClick={scrollToForm}
                          variant="solid" tone="dark" data-testid="nl-who-cta">
              {ctaLetter}
            </EditorialCta>
          </div>
        </PhotoBand>

        {/* ── 4. ISCRIVITI — il centro della pagina ────────────────
            Il sabbia fa galleggiare la scheda bianca, che e' l'unico
            bianco pieno di tutta la pagina: l'occhio ci finisce dentro.
            Colonna singola: qui non c'e' piu' niente da leggere, c'e'
            solo da rispondere.

            IL FORM NON SI TOCCA nella meccanica: `subscribe` manda al
            doppio opt-in (POST /public/newsletter/subscribe), il
            consenso resta OBBLIGATORIO e col suo testo, il link alla
            privacy lo mette LeadForm. Cambiano solo i campi mostrati —
            Nome, Email, consenso, bottone: e' la richiesta del founder
            («io toglierei tutto») — e l'etichetta del bottone. */}
        <Section tone="sand" rhythm="screen" width="max-w-2xl"
                 id="iscriviti" className="scroll-mt-20" labelledBy="nl-form-title">
          <div data-testid="nl-form">
            <DisplayTitle as="h2" id="nl-form-title" size="section" measure="title"
                          className="text-[2rem] leading-[1.12] sm:text-[2.4rem] lg:text-[2.75rem]">
              {t('nl.formTitle', { defaultValue: 'Iscriviti.' })}
            </DisplayTitle>
            <div aria-hidden className="gold-rule mt-7 max-w-[9rem]" />

            {/* la promessa del materiale gratuito, se e' configurato:
                la consegna avviene sulla pagina di CONFERMA (doppio
                opt-in) e la riga lo dice onestamente. */}
            {leadMagnetUrl && (
              <p className="mt-7 max-w-[52ch] text-base leading-relaxed text-foreground/75">
                {t('nl.magnetPromiseDoi', { defaultValue: 'Confermando l’iscrizione ricevi subito il nostro materiale gratuito di benvenuto.' })}
              </p>
            )}

            <div className="mt-9 rounded-[1.75rem] bg-white p-6 ring-1 ring-[#1e2f28]/[0.07] shadow-[0_1px_2px_rgba(30,47,40,0.04),0_18px_40px_-24px_rgba(30,47,40,0.28)] sm:p-8">
              <LeadForm
                type="traveler"
                subscribe
                compact
                showName
                accent={SAGE}
                context="newsletter"
                ctaLabel={ctaLetter}
                consentText={t('blogCta.consent', { defaultValue: 'Acconsento a ricevere la lettera di Aurya via email.' })}
                thanksBody={t('blogCta.thanksDoi', { defaultValue: 'Quasi fatto: controlla la tua casella e clicca il link di conferma che ti abbiamo appena inviato.' })}
              />
            </div>
          </div>
        </Section>

        {/* ── 5. PRIMA DI SALUTARCI — l'ancora verde in chiusura ───
            Tre righe di promessa e un solo invito, che qui NON e' il
            form: chi e' arrivato in fondo senza iscriversi ha bisogno
            di leggere qualcosa, non di un altro bottone uguale. Sul
            verde il pieno di brand sparirebbe (verde su verde), quindi
            la primaria prende il trattamento `tone="dark"`.
            /magazine e' un alias: il link punta alla rotta canonica. */}
        <Section tone="sage" rhythm="screen" width="max-w-5xl"
                 labelledBy="nl-end-title">
          <div data-testid="nl-end">
            <DisplayTitle as="h2" id="nl-end-title" size="section" measure="title">
              {t('nl.endTitle', { defaultValue: 'Prima di salutarci.' })}
            </DisplayTitle>
            <div className="mt-8 space-y-3">
              <Lede size="lead" tone="inherit">
                {t('nl.end1', { defaultValue: 'Promettiamo una cosa semplice.' })}
              </Lede>
              <Lede size="lead" tone="inherit">
                {t('nl.end2', { defaultValue: 'Non useremo la tua email per riempire la tua casella di posta.' })}
              </Lede>
              <Lede size="lead" tone="inherit">
                {t('nl.end3', { defaultValue: 'Scriveremo solo quando avremo qualcosa che vale davvero il tempo che ci dedicherai.' })}
              </Lede>
            </div>
            <p className="mt-10 text-base leading-relaxed opacity-90 sm:text-lg">
              {t('nl.endCtaIntro', { defaultValue: 'Nel frattempo puoi iniziare da qui.' })}
            </p>
            <div className="mt-5">
              <EditorialCta to="/blog" variant="solid" tone="dark" data-testid="nl-end-cta">
                {t('nl.endCta', { defaultValue: 'Esplora il Magazine' })}
              </EditorialCta>
            </div>
          </div>
        </Section>

      </div>
    </MarketplaceShell>
  );
}
