/**
 * OperatorLandingPage — /entra-nella-rete, la landing dell'OPERATORE OLISTICO.
 *
 * RB2 (10/9/2026, REBRANDING — docs/REBRANDING_STRATEGIA_2026-09.md).
 * Dal 4/8 questa pagina parlava di «rete», «presenza» e «conversazione»
 * e si contraddiceva sul come si entra (candidatura + «account in un
 * minuto»); diceva «con calma», «una conversazione alla volta» e «se
 * vuoi solo comparire in un elenco non fa per te». Gli operatori la
 * leggevano, dicevano «interessante» e rimandavano: stavano facendo
 * quello che la pagina chiedeva. L'offerta vera (profilo, listino,
 * prenotazioni, eventi e ritiri con caparra, un link solo) stava a meta'
 * pagina in un elenco senza prove.
 *
 * Ora la pagina segue il trittico della voce per chi opera: COSA HAI,
 * PERCHE' ORA, COME SI ENTRA. Concreto, veloce, verbi e numeri. La
 * fiducia resta nel tono, non nella lentezza. Lessico: «operatore
 * olistico» (e' come il target si chiama), mai «gestionale».
 *
 * L'IMPIANTO VISIVO NON SI SMONTA (docs/DESIGN_PASS_DS_2026-08.md):
 * ancora scura in apertura, foto vere, alternanza dei fondi, blocchi a
 * schede, ancore multiple verso l'azione. I testid restano gli stessi
 * (le guardie seguono il dispositivo): cambia l'ordine e il copy.
 *
 * OTTO SEZIONI, copy in `opPro` (namespace prelaunch, solo italiano):
 *   1. HERO       il tuo spazio, pronto oggi     foto + offerta + CTA
 *   2. COSA HAI   gli strumenti, al presente     fascia foto + registro verde   (ol-go)
 *   3. PERCHE' ORA il patto fondatori            due colonne + contatore vero   (ol-now)
 *   4. COME SI ENTRA tre passi                   tre schede con foto            (ol-join)
 *   5. FAQ        sei domande                    <details>, una alla volta
 *   6. CHI SIAMO  i volti veri                   Valentina e Davide
 *   7. REGISTRAZIONE si comincia da te           #presentati, InlineSignupForm
 *   8. CHIUSURA   il tuo spazio e' pronto        ancora verde
 * La sezione «Per chi e' Aurya» (il no e il si') e' USCITA: respingeva
 * proprio l'operatore che vuole visibilita', cioe' quello che si iscrive.
 *
 * FONDI: dark(foto) → sabbia → FOTO A TUTTA LARGHEZZA → VERDE → crema
 * → sabbia → bianco → sabbia → crema → VERDE. Due sezioni adiacenti non
 * hanno mai lo stesso fondo; le due ancore verdi (2 e 8) non si toccano.
 *
 * IL CONTATORE DEI FONDATORI e' VERO: GET /public/fondatori (tetto,
 * rimasti, scadenza). Se la rete non risponde, la frase resta senza
 * numero: mai un contatore inventato.
 */
import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { Mail } from 'lucide-react';
import api from '../../api/client';
import MarketplaceShell from '../storefront/components/MarketplaceShell';
import useSeoMeta from '../storefront/lib/useSeoMeta';
import InlineSignupForm from './InlineSignupForm';
import {
  Section, DisplayTitle, TitleLine, Lede, EditorialCta, PhotoBand, PhotoSplit,
} from '../../components/editorial';

/** l'ancora del form: destinazione delle CTA interne e dei link che
    arrivano da fuori (/entra-nella-rete#presentati dalla home) */
const FORM_ANCHOR = '#presentati';

/** un profilo VERO da mostrare come prova: listino, recensioni, un
    evento in programma. E' la prova che nessun elenco puo' dare. */
const PROOF_PROFILE = '/o/selva-viva-di-olisticamente-silvia';

const HERO_PHOTO = '/media/hero-organizer.webp';
const FOUNDERS_PHOTO = '/media/chisiamo-aurya.jpg';
const TOGETHER_PHOTO = '/media/prelaunch/r02.jpg';   // costruire insieme
const HORIZON_PHOTO = '/media/prelaunch/r05.jpg';    // il cairn: una pietra alla volta

/* Le tre schede della sezione «come si entra». DECORATIVE (alt=""). */
const CARD_PHOTOS = {
  '01': '/media/prelaunch/r03.jpg',  // una persona nel suo elemento
  '02': '/media/prelaunch/r08.jpg',  // le mani di chi cura, da vicino
  '03': '/media/prelaunch/r09.jpg',  // la pratica nello spazio di tutti
};

function OfferCard({ image, numeral, title, body }) {
  return (
    <article className="flex h-full flex-col overflow-hidden rounded-[1.75rem] bg-white
                        ring-1 ring-[#1e2f28]/[0.07]
                        shadow-[0_1px_2px_rgba(30,47,40,0.04),0_18px_40px_-24px_rgba(30,47,40,0.28)]">
      <div className="aspect-[3/2] w-full overflow-hidden bg-[#e8e2d4]">
        <img src={image} alt="" width="900" height="600" loading="lazy" decoding="async"
             className="h-full w-full object-cover" />
      </div>
      <div className="flex flex-1 flex-col p-7 sm:p-8">
        <p className="eyebrow mb-3">{numeral}</p>
        <h3 className="font-display text-[1.4rem] leading-tight text-foreground sm:text-2xl">
          {title}
        </h3>
        <p className="mt-3 max-w-[52ch] text-pretty text-[0.975rem] leading-relaxed text-foreground/75 sm:text-base">
          {body}
        </p>
      </div>
    </article>
  );
}

export default function OperatorLandingPage() {
  const { t } = useTranslation('prelaunch');
  const { t: tl } = useTranslation('landings');

  useSeoMeta({
    title: t('opPro.seoTitle', { defaultValue: 'Per operatori olistici: il tuo spazio professionale, pronto oggi | Aurya' }),
    description: t('opPro.seoDesc', { defaultValue: 'Profilo pubblico, prenotazioni, eventi e ritiri con caparra, un link solo. Gratis fino al 31 dicembre 2026. Poi il racconto del tuo lavoro lo scriviamo insieme.' }),
    canonicalPath: '/entra-nella-rete',
  });

  /* RB2 — il contatore vero dei fondatori. Senza risposta: nessun numero. */
  const [fondatori, setFondatori] = useState(null);
  useEffect(() => {
    api.get('/public/fondatori').then((r) => setFondatori(r.data)).catch(() => setFondatori(null));
  }, []);

  const prefersReducedMotion = () => typeof window.matchMedia === 'function'
    && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const scrollToForm = (e) => {
    e.preventDefault();
    document.getElementById('presentati')?.scrollIntoView({
      behavior: prefersReducedMotion() ? 'auto' : 'smooth',
      block: 'start',
    });
  };

  /* Come si entra: tre passi, tre schede. */
  const cards = [
    {
      numeral: '01',
      title: t('opPro.j1t', { defaultValue: 'Ti registri in un minuto.' }),
      body: t('opPro.j1b', { defaultValue: 'Nome, email, password. Nessuna carta, nessuna attesa: il tuo spazio si apre subito.' }),
    },
    {
      numeral: '02',
      title: t('opPro.j2t', { defaultValue: 'Pubblichi il profilo.' }),
      body: t('opPro.j2b', { defaultValue: 'Una foto, due righe, il primo servizio. Sei online, nella directory di Aurya, con un link da mettere nella bio.' }),
    },
    {
      numeral: '03',
      title: t('opPro.j3t', { defaultValue: 'Valentina ti scrive entro due giorni.' }),
      body: t('opPro.j3b', { defaultValue: 'Se vuoi, il racconto del tuo lavoro lo scriviamo insieme e lo pubblichiamo con la tua storia: è il badge Verificato Aurya.' }),
    },
  ];

  /* Cosa hai da subito: sei voci, al presente. Ogni voce e' una cosa
     che il prodotto fa OGGI (OF2: mai il futuro in questa sezione). */
  const voices = [
    {
      title: t('opPro.v1t', { defaultValue: 'Ti trovano.' }),
      body: t('opPro.v1b', { defaultValue: 'Un profilo pubblico indicizzato su Google, con la tua storia, le discipline, le foto e le recensioni verificate di chi c’è stato.' }),
    },
    {
      title: t('opPro.v2t', { defaultValue: 'Ti prenotano.' }),
      body: t('opPro.v2b', { defaultValue: 'Il listino con richiesta di appuntamento e un calendario che blocca gli orari occupati.' }),
    },
    {
      title: t('opPro.v3t', { defaultValue: 'Riempi eventi e ritiri.' }),
      body: t('opPro.v3b', { defaultValue: 'Iscrizioni online con caparra e saldo, promemoria automatici, partecipanti in un posto solo.' }),
    },
    {
      title: t('opPro.v4t', { defaultValue: 'Un link solo.' }),
      body: t('opPro.v4b', { defaultValue: 'La tua pagina per la bio di Instagram: servizi, eventi, ritiri, recensioni, la tua storia. Tutto nello stesso posto.' }),
    },
    {
      title: t('opPro.v5t', { defaultValue: 'Tutto il resto.' }),
      body: t('opPro.v5b', { defaultValue: 'Clienti, ordini, incassi, team. Il tempo dei messaggi e dei fogli di calcolo torna alle persone.' }),
    },
    {
      // SP3 — Aurya Sound e' uno strumento gia' vero
      title: t('opPro.v6t', { defaultValue: 'Componi meditazioni con la tua voce.' }),
      body: t('opPro.v6b', { defaultValue: 'Con Crea Studio, l’atelier di Aurya Sound, combini frequenze, metodi e la tua voce in una sessione e la pubblichi con un link.' }),
      to: '/sound/studio',
      toLabel: t('opPro.v6cta', { defaultValue: 'Scopri Crea Studio' }),
      testid: 'ol-voice-studio',
    },
  ];

  /* Sei domande, risposte brevi e oneste, una alla volta (SR5). */
  const faq = [
    {
      q: t('opPro.faq1q', { defaultValue: 'Quanto costa?' }),
      a: (
        <ul className="list-disc space-y-2 pl-5">
          <li>{t('opPro.faq1b1', { defaultValue: 'L’utilizzo della piattaforma è sempre gratuito, e Aurya non prende commissioni: quello che incassi è tuo.' })}</li>
          <li>{t('opPro.faq1b2', { defaultValue: 'Fino al 31 dicembre 2026 Aurya non ha alcun costo, di nessun tipo.' })}</li>
          <li>
            {t('opPro.faq1b3', { defaultValue: 'Dal 2027 si paga solo la prima fila: la Spinta per un ritiro (19 €) o il Club (49 € l’anno); il Pro (119 € l’anno) aggiunge la tua voce e noi accanto. I primi venti hanno il Club regalato per tutto il 2027. ' })}
            <Link to="/costi" className="font-semibold text-primary underline underline-offset-2">
              {t('opPro.faq1b3cta', { defaultValue: 'Guarda i piani e i costi' })}
            </Link>
          </li>
        </ul>
      ),
    },
    {
      q: t('opPro.faq2q', { defaultValue: 'Come funziona?' }),
      a: t('opPro.faq2a3', { defaultValue: 'Ti registri, confermi l’email e metti foto, due righe e il primo servizio: il profilo è online. Poi Valentina ti scrive: se vuoi, il racconto del tuo lavoro lo costruiamo insieme, con le tue parole.' }),
    },
    {
      q: t('opPro.faq3q', { defaultValue: 'Quando arriveranno le nuove funzionalità?' }),
      a: t('opPro.faq3a2', { defaultValue: 'Le costruiamo con i primi operatori che entrano: le priorità le decidono loro, e chi c’è dall’inizio le prova per primo.' }),
    },
    {
      q: t('opPro.faq4q', { defaultValue: 'Posso usare Aurya anche se ho già un sito?' }),
      a: t('opPro.faq4a', { defaultValue: 'Sì, e non devi scegliere. Il profilo Aurya non sostituisce il tuo sito: dal profilo puoi linkare il sito e i tuoi canali, così chi ti trova qui arriva anche lì. Molti lo usano come pagina da condividere nei messaggi e sui social, dove serve un link solo.' }),
    },
    {
      q: t('opPro.faq5q', { defaultValue: 'Posso gestire prenotazioni esterne?' }),
      a: t('opPro.faq5a2', { defaultValue: 'Oggi puoi bloccare gli orari in cui sei già occupato e vedere in un unico calendario gli appuntamenti nati qui. Il collegamento con un’agenda esterna è in lavorazione: te lo diciamo quando c’è.' }),
    },
    {
      q: t('opPro.faq6q', { defaultValue: 'Posso uscire quando voglio?' }),
      a: t('opPro.faq6a', { defaultValue: 'Sì. Puoi spegnere il profilo o cancellare l’account dalle impostazioni, quando vuoi. I tuoi clienti restano tuoi, sempre.' }),
    },
  ];

  const ctaOpen = t('opPro.ctaOpen', { defaultValue: 'Apri il tuo spazio' });
  const ctaJoin = t('opPro.ctaJoin', { defaultValue: 'Apri il tuo spazio' });
  const ctaContact = t('opPro.ctaContact2', { defaultValue: 'Crea il tuo account' });   // il bottone del form

  const rimasti = fondatori && Number.isFinite(fondatori.rimasti) ? fondatori.rimasti : null;

  return (
    <MarketplaceShell noSearch>
      <div className="bg-background">

        {/* ── 1. HERO — il tuo spazio, pronto oggi ─────────────────
            Stessa scena di prima (foto hero-organizer, colonna scura +
            foto nuda da lg, veli misurati sotto lg): cambia cio' che
            dice. Prima frase: l'offerta. Seconda: il prezzo, con la
            data. Poi il bottone. Chi arriva convinto ha l'azione nel
            primo campo visivo (LC4). */}
        <section data-testid="ol-hero" aria-labelledby="ol-hero-title">
          <div className="relative isolate overflow-hidden bg-[#0e1a15] text-[#f6f2e8]">
            <img
              src={HERO_PHOTO}
              alt=""
              width="1920"
              height="1280"
              fetchPriority="high"
              decoding="async"
              className="absolute inset-0 h-full w-full object-cover object-[50%_38%]
                         lg:left-auto lg:right-0 lg:w-[46%] lg:object-[38%_45%]"
            />
            <div aria-hidden
                 className="absolute inset-0 bg-gradient-to-b from-[#0e1a15]/[0.78] via-[#0e1a15]/[0.62] to-[#0e1a15]/[0.90] lg:hidden" />
            <div aria-hidden
                 className="absolute inset-0 bg-[radial-gradient(ellipse_92%_74%_at_36%_50%,rgba(14,26,21,0.52)_0%,rgba(14,26,21,0.34)_58%,rgba(14,26,21,0)_100%)] lg:hidden" />
            <div aria-hidden
                 className="hidden lg:block absolute inset-y-0 left-[54%] w-44 bg-gradient-to-r from-[#0e1a15] to-transparent" />
            <div className="relative mx-auto w-full max-w-5xl px-6 py-16 sm:px-8 sm:py-24
                            lg:flex lg:min-h-[38rem] lg:flex-col lg:justify-center lg:py-24">
              <div className="lg:max-w-[30rem]">
                <p className="eyebrow eyebrow-light mb-6 text-hero-shadow">
                  {t('opPro.heroEyebrow', { defaultValue: 'Per operatori e operatrici olistiche' })}
                </p>
                <DisplayTitle as="h1" id="ol-hero-title" size="heroLines" measure="lines"
                              className="text-hero-shadow">
                  {t('opPro.heroTitle', { defaultValue: 'Il tuo spazio professionale, pronto oggi.' })}
                </DisplayTitle>
                <div className="mt-7 space-y-4 sm:mt-9 sm:space-y-5">
                  <Lede size="body" tone="inherit" className="text-hero-shadow">
                    {t('opPro.heroP1', { defaultValue: 'Profilo pubblico, listino con prenotazione, eventi e ritiri con iscrizioni online e caparra, un link solo per Instagram.' })}
                  </Lede>
                  <Lede size="body" tone="inherit" className="text-hero-shadow">
                    {t('opPro.heroP2', { defaultValue: 'Ci metti tempo, studio, esperienza, presenza. Online, tutto questo merita più di una scheda.' })}
                  </Lede>
                  <Lede size="body" tone="inherit" className="text-hero-shadow">
                    {t('opPro.heroP3', { defaultValue: 'Gratis per sempre, senza commissioni. Fino al 31 dicembre 2026 non costa niente di niente.' })}
                  </Lede>
                </div>
                <div className="mt-9 sm:mt-10">
                  <EditorialCta href={FORM_ANCHOR} onClick={scrollToForm}
                                tone="dark" variant="solid"
                                data-testid="ol-hero-cta-top">
                    {ctaOpen}
                  </EditorialCta>
                  <p className="mt-3 text-sm opacity-80 text-hero-shadow">
                    {t('opPro.heroNote', { defaultValue: 'Un minuto per registrarti. Nessuna carta.' })}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* la soglia: la prova, sul chiaro. Un profilo VERO da vedere
              vale piu' di qualsiasi promessa: e' la differenza fra un
              elenco e una persona con recensioni ed eventi. */}
          <Section tone="sand" rhythm="flow" width="max-w-5xl">
            <DisplayTitle as="p" size="section" measure="lines"
                          className="text-[1.6rem] leading-[1.18] sm:text-[2rem] lg:text-[2.3rem]">
              {t('opPro.heroP4', { defaultValue: 'Non è una promessa: è già così per chi è dentro.' })}
            </DisplayTitle>
            <Lede size="lead" className="mt-6">
              {t('opPro.heroP5', { defaultValue: 'Guarda un profilo vero: listino, recensioni verificate e un evento in programma, sulla stessa pagina.' })}
            </Lede>
            <div className="mt-9 flex flex-col items-start gap-5 sm:flex-row sm:items-center sm:gap-8">
              <EditorialCta href={FORM_ANCHOR} onClick={scrollToForm}
                            variant="solid" data-testid="ol-hero-cta">
                {ctaOpen}
              </EditorialCta>
              <EditorialCta to={PROOF_PROFILE} variant="quiet" data-testid="ol-hero-cta-alt">
                {t('opPro.ctaProof', { defaultValue: 'Guarda un profilo vero' })}
              </EditorialCta>
            </div>
          </Section>
        </section>

        {/* ── 2. COSA HAI DA SUBITO — il trattamento piu' forte ────
            OF2: tutto al presente. La fascia a tutta larghezza col
            titolo dentro la foto (r05, il cairn), poi l'ancora verde col
            registro delle sei voci. Sul verde il crema sta a 7,28:1. */}
        <section id="sound" data-testid="ol-go" aria-labelledby="ol-go-title">
          <PhotoBand as="div" image={HORIZON_PHOTO} focus="50% 40%" width="max-w-3xl">
            <DisplayTitle as="h2" id="ol-go-title" size="section" measure="title"
                          className="text-hero-shadow">
              {t('opPro.goTitle', { defaultValue: 'Cosa hai da subito.' })}
            </DisplayTitle>
            <Lede size="lead" tone="inherit" className="mt-7 text-hero-shadow">
              {t('opPro.goP1', { defaultValue: 'Sono strumenti che esistono oggi, non un programma.' })}
            </Lede>
            <Lede size="lead" tone="inherit" className="mt-4 text-hero-shadow">
              {t('opPro.goP2', { defaultValue: 'Li usi dal primo giorno, dal telefono.' })}
            </Lede>
          </PhotoBand>

          <Section tone="sage" rhythm="screen" as="div" width="max-w-5xl">
            <DisplayTitle as="p" size="section" measure="lines"
                          className="text-[1.6rem] leading-[1.18] sm:text-[2rem] lg:text-[2.3rem]">
              <TitleLine>
                {t('opPro.goP3', { defaultValue: 'Senza cambiare piattaforma.' })}
              </TitleLine>
              <TitleLine>
                {t('opPro.goP4', { defaultValue: 'Senza ricominciare da zero.' })}
              </TitleLine>
            </DisplayTitle>
            <ul className="mt-11 list-none p-0 sm:mt-14">
              {voices.map((v, i) => (
                <li
                  key={v.title}
                  className={`grid gap-2 py-6 lg:grid-cols-12 lg:gap-10 ${
                    i > 0 ? 'border-t border-[#f6f2e8]/20' : 'pt-0'}`}
                >
                  <h3 className="font-display text-[1.3rem] leading-snug sm:text-[1.55rem] lg:col-span-5">
                    {v.title}
                  </h3>
                  <p className="max-w-[52ch] text-base leading-relaxed opacity-90 sm:text-lg lg:col-span-7 lg:pt-1">
                    {v.body}
                    {v.to && (
                      <>
                        {' '}
                        <Link to={v.to} data-testid={v.testid}
                              className="font-semibold underline underline-offset-4 hover:opacity-100">
                          {v.toLabel} →
                        </Link>
                      </>
                    )}
                  </p>
                </li>
              ))}
            </ul>
            <Lede size="body" tone="inherit" className="mt-12 opacity-90 sm:mt-14">
              {t('opPro.goSoon', { defaultValue: 'E la parte pubblica è aperta: chi cerca un professionista ti trova nella directory di Aurya, con i tuoi servizi, i tuoi eventi e i tuoi ritiri.' })}
            </Lede>
            <div className="mt-9">
              <EditorialCta href={FORM_ANCHOR} onClick={scrollToForm}
                            variant="solid" tone="dark" data-testid="ol-go-cta">
                {ctaOpen}
              </EditorialCta>
            </div>
          </Section>
        </section>

        {/* ── 3. PERCHE' ORA — il patto fondatori ─────────────────
            Urgenza onesta: un tetto, una data, un contatore vero. Sul
            crema accanto a r02, l'unica foto al plurale del magazzino:
            e' la sezione che parla dei primi venti, insieme. */}
        <PhotoSplit
          image={TOGETHER_PHOTO}
          side="left"
          tone="cream"
          focus="50% 45%"
          imageWidth="900"
          imageHeight="599"
          labelledBy="ol-now-title"
          data-testid="ol-now"
        >
          <DisplayTitle as="h2" id="ol-now-title" size="section" measure="title">
            {t('opPro.nowTitle', { defaultValue: 'Perché ora.' })}
          </DisplayTitle>
          <Lede size="lead" className="mt-7">
            {t('opPro.nowP1', { defaultValue: 'I primi venti operatori olistici che pubblicano il profilo entro il 31 ottobre 2026 entrano come fondatori.' })}
          </Lede>
          <Lede size="body" className="mt-5">
            {t('opPro.nowP2', { defaultValue: 'Il Club regalato per tutto il 2027 (la prima fila su ogni tuo ritiro, la Lettera alla tua zona, un post al mese), il badge permanente, il prezzo del Pro bloccato per sempre, la precedenza nella selezione dei ritiri di primavera 2027.' })}
          </Lede>
          <p className="mt-6 font-display text-[1.35rem] leading-snug text-foreground sm:text-[1.6rem]"
             data-testid="ol-fondatori-contatore">
            {rimasti !== null
              ? t('opPro.nowCount', { defaultValue: '{{rimasti}} posti su {{tetto}} ancora liberi.', rimasti, tetto: fondatori.tetto })
              : t('opPro.nowCountFallback', { defaultValue: 'Venti posti, poi la parola fondatori sparisce da questa pagina.' })}
          </p>
          <DisplayTitle as="p" size="section" measure="lines"
                        className="mt-10 text-[1.5rem] leading-[1.2] sm:text-[1.8rem] lg:text-[2.05rem]">
            <TitleLine>
              {t('opPro.nowCloseA2', { defaultValue: 'Non cerchiamo numeri.' })}
            </TitleLine>
            <TitleLine>
              {t('opPro.nowCloseB2', { defaultValue: 'Cerchiamo i primi venti con cui costruire Aurya.' })}
            </TitleLine>
          </DisplayTitle>
        </PhotoSplit>

        {/* ── 4. COME SI ENTRA — tre passi, tre schede ─────────────
            Fondo sabbia: le schede sono bianche. Tre colonne da lg. */}
        <Section tone="sand" rhythm="screen" labelledBy="ol-join-title" width="max-w-6xl">
          <div data-testid="ol-join">
            <DisplayTitle as="h2" id="ol-join-title" size="section" measure="title">
              {t('opPro.joinTitle', { defaultValue: 'Come si entra.' })}
            </DisplayTitle>
            <ul className="mt-10 grid list-none gap-7 p-0 sm:mt-12 sm:gap-8 lg:grid-cols-3">
              {cards.map((c) => (
                <li key={c.numeral} data-testid={`ol-card-${c.numeral}`} className="h-full">
                  <OfferCard image={CARD_PHOTOS[c.numeral]} numeral={c.numeral} title={c.title} body={c.body} />
                </li>
              ))}
            </ul>
          </div>
        </Section>

        {/* ── 5. DOMANDE — l'elenco leggibile, una alla volta (SR5) ── */}
        <Section tone="paper" rhythm="screen" labelledBy="ol-faq-title" width="max-w-3xl">
          <div data-testid="ol-faq">
            <DisplayTitle as="h2" id="ol-faq-title" size="section" measure="title">
              {t('opPro.faqTitle', { defaultValue: 'Domande frequenti.' })}
            </DisplayTitle>
            <div className="mt-10 sm:mt-12" data-testid="ol-faq-list">
              {faq.map((f, i) => (
                <details key={f.q}
                         className={`group py-5 ${i > 0 ? 'border-t border-[#1e2f28]/[0.10]' : 'pt-0'}`}>
                  <summary className="flex cursor-pointer list-none items-start justify-between gap-4
                                      font-display text-[1.2rem] leading-snug text-foreground sm:text-[1.4rem]
                                      [&::-webkit-details-marker]:hidden">
                    <span>{f.q}</span>
                    <span aria-hidden
                          className="mt-1 shrink-0 text-[#8a7440] transition-transform group-open:rotate-45">+</span>
                  </summary>
                  <div className="mt-3 max-w-[62ch] text-base leading-relaxed text-foreground/75 sm:text-lg">
                    {f.a}
                  </div>
                </details>
              ))}
            </div>
          </div>
        </Section>

        {/* ── 6. CHI C'E' DIETRO AURYA — i volti veri ──────────────
            LC4: il payoff del brand al posto delle negazioni; la foto
            vera dei fondatori in taglio ritratto. */}
        <Section tone="sand" rhythm="screen" labelledBy="ol-who-title" width="max-w-6xl">
          <div data-testid="ol-who">
            <p className="eyebrow mb-5">
              {t('opPro.whoEyebrow', { defaultValue: 'Chi c’è dietro Aurya' })}
            </p>
            <DisplayTitle as="h2" id="ol-who-title" size="section" measure="lines"
                          className="text-[1.9rem] leading-[1.14] sm:text-[2.4rem] lg:text-[2.9rem]">
              <TitleLine>
                {t('opPro.whoLine1', { defaultValue: 'Pratiche, eventi e ritiri' })}
              </TitleLine>
              <TitleLine>
                {t('opPro.whoLine2', { defaultValue: 'di benessere' })}
              </TitleLine>
            </DisplayTitle>
            <Lede size="lead" className="mt-7">
              {t('opPro.whoLead', { defaultValue: 'Siamo due persone che hanno deciso di costruire lo spazio che avrebbero voluto trovare.' })}
            </Lede>

            <div className="mt-12 grid gap-9 sm:mt-14 lg:grid-cols-12 lg:items-center lg:gap-14">
              <div className="lg:col-span-5">
                <img
                  src={FOUNDERS_PHOTO}
                  alt={tl('aboutPage.facesAlt', { defaultValue: 'Davide e Valentina, i fondatori di Aurya, in riva al mare' })}
                  width="900"
                  height="1125"
                  loading="lazy"
                  decoding="async"
                  className="aspect-[4/5] w-full rounded-[1.75rem] object-cover shadow-[0_18px_48px_-28px_rgba(30,47,40,0.45)]"
                />
              </div>
              <div className="lg:col-span-7">
                <p className="font-display text-[1.5rem] leading-snug text-foreground sm:text-[1.85rem]">
                  <span className="block">
                    {t('opPro.whoV', { defaultValue: 'Valentina vive il mondo del benessere ogni giorno.' })}
                  </span>
                  <span className="mt-3 block">
                    {t('opPro.whoD', { defaultValue: 'Davide costruisce prodotti digitali da anni.' })}
                  </span>
                </p>
                <Lede size="body" className="mt-6">
                  {t('opPro.whoP', { defaultValue: 'Aurya nasce dall’incontro tra queste due esperienze.' })}
                </Lede>
                <div className="mt-8">
                  <EditorialCta to="/chi-siamo" variant="quiet" data-testid="ol-who-cta">
                    {t('opPro.whoCta', { defaultValue: 'Conosci la nostra storia' })}
                  </EditorialCta>
                </div>
              </div>
            </div>
          </div>
        </Section>

        {/* ── 7. LA REGISTRAZIONE — si comincia da te ──────────────
            UN solo form in tutta la pagina, con l'ancora #presentati.
            InlineSignupForm: la STESSA signup() di AuthContext. */}
        <Section tone="cream" rhythm="screen" labelledBy="ol-form-title" width="max-w-6xl"
                 id="presentati" className="scroll-mt-20">
          <div data-testid="ol-form"
               className="grid gap-10 lg:grid-cols-12 lg:items-start lg:gap-16">
            <div className="lg:col-span-5">
              <DisplayTitle as="h2" id="ol-form-title" size="section" measure="title"
                            className="text-[1.9rem] leading-[1.12] sm:text-[2.4rem] lg:text-[2.6rem]">
                {t('opPro.formTitle2', { defaultValue: 'Si comincia da te.' })}
              </DisplayTitle>
              <Lede size="lead" className="mt-7">
                {t('opPro.formA3', { defaultValue: 'Crei il tuo account in un minuto e pubblichi il tuo profilo.' })}
              </Lede>
              <Lede size="lead" className="mt-6">
                {t('opPro.formC3', { defaultValue: 'Poi Valentina ti scrive.' })}
              </Lede>
              <Lede size="body" className="mt-4">
                {t('opPro.formD3', { defaultValue: 'Entro due giorni, per una conversazione dedicata: il tuo percorso, cosa rende unico il tuo lavoro.' })}
              </Lede>
              <Lede size="body" className="mt-4">
                {t('opPro.formE3', { defaultValue: 'Da quella conversazione nasce il tuo racconto su Aurya. Con la tua voce.' })}
              </Lede>

              <p className="mt-8 flex flex-wrap items-center gap-1.5 text-sm text-foreground/70">
                <Mail className="h-4 w-4 shrink-0 text-[#2f5749]" aria-hidden />
                {t('op.directT', { defaultValue: 'Preferisci parlarne senza form?' })}{' '}
                <a href="mailto:info@aurya.life"
                   className="font-medium text-[#2f5749] underline underline-offset-[4px] decoration-[#2f5749]/40 hover:decoration-[#2f5749]">
                  info@aurya.life
                </a>
              </p>
            </div>
            <div className="lg:col-span-7">
              <div className="rounded-[1.75rem] bg-white p-6 ring-1 ring-[#1e2f28]/[0.07] shadow-[0_1px_2px_rgba(30,47,40,0.04),0_18px_40px_-24px_rgba(30,47,40,0.28)] sm:p-8">
                <InlineSignupForm />
              </div>
            </div>
          </div>
        </Section>

        {/* ── 8. CHIUSURA — seconda ancora verde ───────────────────
            Le due frasi del founder restano; la chiusa non dice piu'
            «con calma»: dice che lo spazio e' pronto. */}
        <Section tone="sage" rhythm="screen" labelledBy="ol-end-title" width="max-w-5xl">
          <div data-testid="ol-end">
            <DisplayTitle as="h2" id="ol-end-title" size="section" measure="lines">
              <TitleLine>
                {t('opPro.endA', { defaultValue: 'Le reti non nascono da una piattaforma.' })}
              </TitleLine>
              <TitleLine>
                {t('opPro.endB', { defaultValue: 'Nascono dalle persone.' })}
              </TitleLine>
            </DisplayTitle>
            <Lede size="lead" tone="inherit" className="mt-7">
              <span className="block">
                {t('opPro.endC2', { defaultValue: 'Il tuo spazio è pronto.' })}
              </span>
              <span className="block">
                {t('opPro.endD2', { defaultValue: 'Il resto lo costruiamo insieme.' })}
              </span>
            </Lede>
            <Lede size="body" tone="inherit" className="mt-5 opacity-90">
              {t('opPro.endBody2', { defaultValue: 'Se senti che Aurya rappresenta anche il tuo modo di vedere il benessere, apri il tuo spazio oggi.' })}
            </Lede>
            <div className="mt-9">
              <EditorialCta href={FORM_ANCHOR} onClick={scrollToForm}
                            variant="solid" tone="dark" data-testid="ol-end-cta">
                {ctaJoin}
              </EditorialCta>
            </div>
          </div>
        </Section>

      </div>
    </MarketplaceShell>
  );
}
