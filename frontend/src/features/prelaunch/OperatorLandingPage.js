/**
 * OperatorLandingPage — /entra-nella-rete (OL1, riscrittura sulla
 * specifica del founder del 31/7/2026).
 *
 * POSIZIONAMENTO. "Non stiamo chiedendo agli operatori di iscriversi a
 * una piattaforma. Li stiamo invitando a entrare nel progetto che punta
 * a diventare il punto di riferimento per il benessere consapevole."
 * Ogni scelta di questa pagina risponde a quella frase: si parla di
 * lavoro riconosciuto, non di funzionalita'; di rete, non di iscrizioni.
 *
 * LA REGOLA CHE CAMBIA TUTTO. Il "profilo gratuito" NON e' piu' un
 * argomento di vendita: la parola gratuito/gratis abbassava il valore
 * percepito e ora vive in UN SOLO posto, la risposta della FAQ "Perche'
 * e' gratuito?", dove e' una risposta onesta a una domanda legittima e
 * non una promessa da vetrina. Titolo e description SEO sono stati
 * ripuliti (dicevano "Gratuitamente"). La guardia sta in
 * backend/tests/test_listino_tw.py::TestLandingOperatoriOl1.
 *
 * Otto sezioni, copy CHIUSO parola per parola:
 *   1. HERO        il riconoscimento     foto + due CTA
 *   2. PERCHE'     la tesi               molto piu' di una vetrina
 *   3. COSA TROVI  le quattro promesse   profilo, storia, visibilita', crescita
 *   4. INSIEME     il ruolo speciale     ancora verde
 *   5. FAQ         le quattro domande    elenco leggibile, sempre aperto
 *   6. CHI SIAMO   i volti veri          Davide e Valentina, testo esistente
 *   7. FORM        la conversazione      #presentati, LeadForm invariato
 *   8. CHIUSURA    l'invito              ancora verde
 *
 * VINCOLO DI LESSICO. L'evoluzione del prodotto si racconta com'e'
 * scritta nella scheda 4: mai "Aurya Connect", mai "gestionale".
 *
 * FONDI. crema/sabbia/carta con DUE sole ancore verdi, non adiacenti
 * (sezioni 4 e 8): dark(foto) → sabbia → crema → sabbia → VERDE+foto →
 * bianco → crema → sabbia → VERDE. Stessa grammatica della home di
 * rete, kit editoriale condiviso.
 *
 * SW2 — IL PASSAGGIO VISIVO (richiesta founder: "manca di visual e
 * design"). Copy, ordine e CTA restano congelati; cambia solo il
 * vestito. Le fotografie passano da due a sette, ciascuna con un
 * perche':
 *   HERO   hero-organizer (mani in gyan mudra) — resta la copertina
 *          storica, ma su desktop il velo uniforme sparisce: colonna
 *          scura piena a sinistra per il testo (contrasto FISSO,
 *          15,9:1, non sperato) e fotografia NUDA a destra, alla sua
 *          piena luce. Su mobile resta il fondo fotografico velato,
 *          misurato sui pixel reali (7,95:1 nel caso peggiore).
 *   CARDS  le quattro promesse prendono una fotografia in testa, come
 *          le PillarCard della home: r03 (una persona sola, raccontata
 *          nel suo elemento) per il profilo; r08 (le mani di chi cura,
 *          la fiducia che passa dal gesto) per la storia; r09 (la
 *          pratica visibile nello spazio di tutti) per la visibilita';
 *          r05 (il cairn, una pietra alla volta) per la crescita.
 *          r06 e r02 in card restano alla home: le due pagine sono
 *          sorelle, non fotocopie.
 *   VERDE  la prima ancora (sezione 4) diventa la fascia a tutta
 *          larghezza col testo sul verde pieno e r02 accanto (due
 *          persone che meditano INSIEME: e' la sezione del
 *          "costruiamo insieme"), speculare alla fascia "La rete"
 *          della home: foto a sinistra, testo a destra.
 *   CHI SIAMO  chisiamo-aurya in taglio ritratto (4:5): il quadrato
 *          originale si vede quasi intero e i volti restano grandi.
 * Il video del tramonto resta la firma della home e non si duplica qui.
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import { Mail } from 'lucide-react';
import MarketplaceShell from '../storefront/components/MarketplaceShell';
import useSeoMeta from '../storefront/lib/useSeoMeta';
import LeadForm from './LeadForm';
import {
  Section, DisplayTitle, TitleLine, Lede, EditorialCta,
} from '../../components/editorial';

/** l'ancora del form: destinazione delle tre CTA interne e dei link
    che arrivano da fuori (/entra-nella-rete#presentati dalla home) */
const FORM_ANCHOR = '#presentati';

/** il verde di brand del kit editoriale: la pagina non ha piu' un
    accento proprio (la terracotta di PL16), parla la lingua della home */
const SAGE = '#2f5749';

/* La copertina storica della pagina. Su mobile sotto il testo passa
   un velo in due strati tarato sui pixel piu' chiari della foto; su
   desktop la foto sta nuda nella meta' destra: le misure di contrasto
   stanno nel commento della sezione 1. */
const HERO_PHOTO = '/media/hero-organizer.webp';
const FOUNDERS_PHOTO = '/media/chisiamo-aurya.jpg';

/* SW2 — le fotografie delle quattro promesse e della fascia verde.
   Tutte gia' in /public/media/prelaunch, aperte e scelte una a una;
   il perche' di ciascuna sta nel commento di testa del file. Sono
   DECORATIVE (alt=""): ogni scheda dice gia' tutto con titolo e
   testo, e descriverle a voce sarebbe rumore per chi ascolta. */
const CARD_PHOTOS = {
  '01': '/media/prelaunch/r03.jpg',  // una persona nel suo elemento
  '02': '/media/prelaunch/r08.jpg',  // le mani di chi cura, da vicino
  '03': '/media/prelaunch/r09.jpg',  // la pratica nello spazio di tutti
  '04': '/media/prelaunch/r05.jpg',  // il cairn: una pietra alla volta
};
const TOGETHER_PHOTO = '/media/prelaunch/r02.jpg'; // meditare insieme

/**
 * OfferCard — una delle quattro promesse della sezione 3.
 *
 * NON e' PillarCard: quella scheda ha un piede sempre presente (link o
 * etichetta di stato), qui nessuna delle quattro porta da qualche
 * parte, quindi il piede non esiste e la scheda resta un argomento.
 *
 * SW2 — la fotografia in testa (3:2, come PillarCard: e' il kit che
 * comanda). OL1 aveva scelto quattro schede di solo testo col numerale
 * serif per non fare "catalogo"; la richiesta del founder ("aggiungi
 * delle foto, rendi il design piu' ad impatto visivo") ribalta quella
 * scelta e la regola del kit torna a valere: con la fotografia in
 * testa il segno c'e' gia', e il numerale sarebbe il secondo segno
 * sopra lo stesso titolo (NOTA DIREZIONE CREATIVA di PillarCard).
 * Il rapporto dichiarato (aspect-[3/2]) prenota lo spazio prima che il
 * file arrivi: zero salti di layout. Niente zoom al passaggio: la
 * scheda non si apre, e muoversi sotto il mouse prometterebbe un clic
 * che non esiste.
 */
function OfferCard({ image, title, body }) {
  return (
    <article className="flex h-full flex-col overflow-hidden rounded-[1.75rem] bg-white
                        ring-1 ring-[#1e2f28]/[0.07]
                        shadow-[0_1px_2px_rgba(30,47,40,0.04),0_18px_40px_-24px_rgba(30,47,40,0.28)]">
      <div className="aspect-[3/2] w-full overflow-hidden bg-[#e8e2d4]">
        <img
          src={image}
          alt=""
          width="900"
          height="600"
          loading="lazy"
          decoding="async"
          className="h-full w-full object-cover"
        />
      </div>
      <div className="flex flex-1 flex-col p-7 sm:p-8">
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
  // la sezione "Chi siamo" riusa il racconto GIA' VERIFICATO dei
  // fondatori (aboutPage.*, namespace landings): stesso testo del
  // Manifesto e di /chi-siamo, tradotto x4. Qui non si inventa nulla.
  const { t: tl } = useTranslation('landings');

  useSeoMeta({
    title: t('opNw.seoTitle', { defaultValue: 'Il tuo lavoro merita di essere conosciuto | Aurya' }),
    description: t('opNw.seoDesc', { defaultValue: 'Aurya racconta i professionisti del benessere con interviste e profili curati. Entra nella rete che sta nascendo: il tuo lavoro merita di essere conosciuto.' }),
    canonicalPath: '/entra-nella-rete',
  });

  /** chi ha chiesto meno movimento non si fa mezza pagina di viaggio */
  const prefersReducedMotion = () => typeof window.matchMedia === 'function'
    && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* Le tre CTA interne (hero, "Parliamone", chiusura) portano tutte
     QUI. preventDefault: l'hash non finisce nell'URL, quindi il gesto
     si puo' ripetere all'infinito. Un <Link to="#presentati"> del
     router avrebbe funzionato solo al primo clic. */
  const scrollToForm = (e) => {
    e.preventDefault();
    document.getElementById('presentati')?.scrollIntoView({
      behavior: prefersReducedMotion() ? 'auto' : 'smooth',
      block: 'start',
    });
  };

  /* HP2 — l'ancora #presentati e' una destinazione anche da FUORI: la
     home linka /entra-nella-rete#presentati ("Parliamone"). Chi arriva
     da li' viene portato all'ancora da ScrollToTop in App.js, che e'
     hash-aware per tutte le ancore del sito e sa aspettare le pagine
     lazy. Qui resta solo l'id sulla sezione del form. */

  const cards = [
    {
      numeral: '01',
      title: t('opNw.c1t', { defaultValue: 'Un profilo che racconta chi sei' }),
      body: t('opNw.c1b', { defaultValue: 'Non una scheda. Una pagina costruita insieme a noi che racconta il tuo approccio, il tuo percorso e il valore del tuo lavoro.' }),
    },
    {
      numeral: '02',
      title: t('opNw.c2t', { defaultValue: 'Una storia che crea fiducia' }),
      body: t('opNw.c2b', { defaultValue: 'Ti intervistiamo e trasformiamo la tua esperienza in un contenuto pubblicato sul Magazine di Aurya. Perché le persone scelgono più facilmente chi hanno avuto modo di conoscere.' }),
    },
    {
      numeral: '03',
      title: t('opNw.c3t', { defaultValue: 'Più occasioni per essere scoperto' }),
      body: t('opNw.c3b', { defaultValue: 'Il tuo profilo sarà valorizzato attraverso il Magazine, la newsletter, i nostri canali e i motori di ricerca. Ogni contenuto contribuisce a rendere più visibile anche il tuo lavoro.' }),
    },
    {
      numeral: '04',
      title: t('opNw.c4t', { defaultValue: 'Uno spazio che crescerà con te' }),
      body: t('opNw.c4b', { defaultValue: 'Nei prossimi mesi il tuo profilo diventerà sempre più completo. Potrai pubblicare i tuoi servizi, ricevere richieste di prenotazione, organizzare workshop, eventi e ritiri, condividere un unico link con tutto ciò che fai e gestire la tua presenza in un unico luogo.' }),
    },
  ];

  /* Quattro domande, quattro risposte SEMPRE VISIBILI. Niente
     accordion: le risposte sono di due o tre righe, un accordion le
     nasconderebbe dietro un gesto per risparmiare trecento pixel su
     mobile, toglierebbe il testo ai motori di ricerca e costringerebbe
     a quattro clic chi vuole solo capire come funziona. Il <dl> e' la
     semantica giusta: domanda e risposta, in coppia. */
  const faq = [
    {
      q: t('opNw.faq1q', { defaultValue: 'Quanto costa?' }),
      a: t('opNw.faq1a', { defaultValue: 'Oggi entrare nella rete non ha un costo. Quello che ti chiediamo è il tempo di una conversazione e la voglia di raccontare il tuo lavoro sul serio.' }),
    },
    {
      q: t('opNw.faq2q', { defaultValue: 'Come funziona?' }),
      a: t('opNw.faq2a', { defaultValue: 'Ci scrivi due righe su di te. Se c’è sintonia ci sentiamo e ti facciamo qualche domanda. Poi scriviamo il tuo profilo con le tue parole e lo pubblichiamo insieme alla tua storia.' }),
    },
    {
      // L'UNICO punto della pagina in cui la parola compare: qui e'
      // una risposta onesta, non un argomento di vendita.
      q: t('opNw.faq3q', { defaultValue: 'Perché è gratuito?' }),
      a: t('opNw.faq3a', { defaultValue: 'Perché in questa fase il valore lo costruiamo insieme: tu porti il tuo lavoro e la tua esperienza, noi il tempo per raccontarlo e i canali per farlo leggere. Quando arriveranno gli strumenti per gestire servizi e prenotazioni ne parleremo con chiarezza, senza sorprese.' }),
    },
    {
      q: t('opNw.faq4q', { defaultValue: 'Quando arriveranno le nuove funzionalità?' }),
      a: t('opNw.faq4a', { defaultValue: 'Le stiamo costruendo insieme ai primi professionisti che entrano. Le priorità le decidiamo ascoltando loro, e chi c’è dall’inizio le prova per primo.' }),
    },
  ];

  const ctaJoin = t('opNw.ctaJoin', { defaultValue: 'Entra nella rete Aurya' });

  return (
    <MarketplaceShell noSearch>
      <div className="bg-background">

        {/* ── 1. HERO — il riconoscimento ──────────────────────────
            Due tempi dentro una sola sezione.

            a) LA FOTO E LA FRASE. hero-organizer (mani in gyan mudra):
               fondo fotografico velato fino a tablet, colonna scura +
               foto nuda da lg (vedi sotto). Il testo e' allineato a
               SINISTRA e non centrato come nella home: quattro frasi
               corte una sotto l'altra sono una constatazione rivolta a
               una persona sola, e centrarle le avrebbe fatte sembrare
               uno slogan.
            b) LA SOGLIA. Il quinto capoverso (quello lungo, la
               promessa) e le due azioni stanno sotto la foto, sul
               sabbia. Sopra la fotografia sarebbero stati altri sette
               righe di testo velato: qui invece si leggono sul chiaro,
               le CTA hanno il contrasto pieno del kit e chi scorre
               arriva ai bottoni DOPO aver letto l'argomento.

            IL VELO, MISURATO (SW2: solo sotto il breakpoint lg).
            Su mobile e tablet la foto sta DIETRO il testo e sopra
            passano due strati: uno verticale (piu' scuro in alto e in
            fondo, dove raccorda con il sabbia) e uno radiale che
            aggiunge buio solo dietro la colonna di testo. Misurato
            componendo i veli sui pixel reali della fotografia
            (script SW2): il pixel piu' chiaro sotto il testo da'
            7,95:1 col crema #f6f2e8 (minimo AA: 4,5:1 corpo, 3:1
            display). L'ombra (.text-hero-shadow) e' la cintura di
            sicurezza, non il motore.

            SW2 — DA lg IN SU la foto smette di fare da tappezzeria
            velata (il founder la vedeva "senza visual": sotto il velo
            uniforme la fotografia moriva) e diventa una COLONNA nuda
            nella meta' destra, alla sua piena luce. Il testo sta su
            #0e1a15 pieno: contrasto FISSO 15,96:1 (crema su verde
            quasi nero), misurato sui valori e non sperato sui pixel.
            Fra colonna e foto una cerniera in gradiente (da #0e1a15 a
            trasparente) sopra il bordo sinistro della foto: il buio
            dietro il testo non dipende mai dall'immagine. */}
        <section data-testid="ol-hero" aria-labelledby="ol-hero-title">
          <div className="relative isolate overflow-hidden bg-[#0e1a15] text-[#f6f2e8]">
            {/* decorativa: il titolo dice gia' tutto quello che la foto
                suggerisce, e un alt che descrive due mani in mudra
                aggiungerebbe rumore a chi ascolta la pagina */}
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
            {/* i due veli mobile: da lg spariscono con la tappezzeria */}
            <div aria-hidden
                 className="absolute inset-0 bg-gradient-to-b from-[#0e1a15]/[0.78] via-[#0e1a15]/[0.62] to-[#0e1a15]/[0.90] lg:hidden" />
            <div aria-hidden
                 className="absolute inset-0 bg-[radial-gradient(ellipse_92%_74%_at_36%_50%,rgba(14,26,21,0.52)_0%,rgba(14,26,21,0.34)_58%,rgba(14,26,21,0)_100%)] lg:hidden" />
            {/* la cerniera desktop: parte esattamente sul bordo sinistro
                della foto (54% = 100% - 46%) e sfuma in 11rem, a ogni
                larghezza di schermo. Il testo (max-w-[30rem] dentro il
                contenitore 5xl) finisce sempre PRIMA del 54%: non
                incontra mai un pixel di fotografia. */}
            <div aria-hidden
                 className="hidden lg:block absolute inset-y-0 left-[54%] w-44 bg-gradient-to-r from-[#0e1a15] to-transparent" />
            <div className="relative mx-auto w-full max-w-5xl px-6 py-16 sm:px-8 sm:py-24
                            lg:flex lg:min-h-[38rem] lg:flex-col lg:justify-center lg:py-24">
              {/* su desktop il testo resta nella colonna scura: il tetto
                  in rem tiene titolo e capoversi a sinistra della foto */}
              <div className="lg:max-w-[30rem]">
                <DisplayTitle as="h1" id="ol-hero-title" size="heroLines" measure="lines"
                              className="text-hero-shadow">
                  {t('opNw.heroTitle', { defaultValue: 'Il tuo lavoro merita di essere conosciuto.' })}
                </DisplayTitle>
                {/* i quattro capoversi brevi: uno per blocco, cosi' il
                    ritmo si vede invece di doverlo immaginare */}
                <div className="mt-7 space-y-3 sm:mt-9 sm:space-y-4">
                  <Lede size="body" tone="inherit" className="text-hero-shadow">
                    {t('opNw.heroP1', { defaultValue: 'Ogni giorno accompagni persone nel loro percorso di benessere.' })}
                  </Lede>
                  <Lede size="body" tone="inherit" className="text-hero-shadow">
                    {t('opNw.heroP2', { defaultValue: 'Ci metti studio, esperienza, ascolto e presenza.' })}
                  </Lede>
                  <Lede size="body" tone="inherit" className="text-hero-shadow">
                    {t('opNw.heroP3', { defaultValue: 'Eppure, online, tutto questo spesso si riduce a poche righe e a un elenco di servizi.' })}
                  </Lede>
                  <Lede size="body" tone="inherit" className="text-hero-shadow">
                    {t('opNw.heroP4', { defaultValue: 'Aurya nasce per cambiare questo.' })}
                  </Lede>
                </div>
              </div>
            </div>
          </div>

          {/* la soglia: la promessa lunga e le due porte, sul chiaro */}
          <Section tone="sand" rhythm="flow" width="max-w-5xl">
            <Lede size="lead">
              {t('opNw.heroP5', { defaultValue: 'Stiamo costruendo una rete di professionisti raccontati con cura, uno spazio dove le persone possano conoscerti prima ancora di sceglierti e dove la tua presenza digitale possa crescere insieme alla tua attività.' })}
            </Lede>
            <div className="mt-9 flex flex-col items-start gap-5 sm:flex-row sm:items-center sm:gap-8">
              <EditorialCta href={FORM_ANCHOR} onClick={scrollToForm}
                            variant="solid" data-testid="ol-hero-cta">
                {ctaJoin}
              </EditorialCta>
              <EditorialCta to="/manifesto" variant="quiet" data-testid="ol-hero-cta-alt">
                {t('opNw.ctaManifesto', { defaultValue: 'Leggi il Manifesto' })}
              </EditorialCta>
            </div>
          </Section>
        </section>

        {/* ── 2. PERCHE' AURYA — la tesi ───────────────────────────
            Solo ragionamento, tre paragrafi in scala discendente: il
            primo e' la tesi e sta al corpo del lede, gli altri due
            argomentano. Nessuna immagine: sotto un testo lungo si paga
            sempre in leggibilita', e la fotografia in questa pagina ha
            gia' i suoi due posti (hero e Chi siamo). */}
        <Section tone="cream" rhythm="screen" labelledBy="ol-why-title" width="max-w-5xl">
          <div data-testid="ol-why">
            <DisplayTitle as="h2" id="ol-why-title" size="section" measure="tight">
              {t('opNw.whyTitle', { defaultValue: 'Molto più di una vetrina.' })}
            </DisplayTitle>
            <Lede size="lead" className="mt-7">
              {t('opNw.whyP1', { defaultValue: 'Internet offre tantissimi modi per essere visibili. Ma essere visibili non significa essere compresi.' })}
            </Lede>
            <Lede size="body" className="mt-5">
              {t('opNw.whyP2', { defaultValue: 'Noi crediamo che le persone scelgano un professionista soprattutto per come lavora, per ciò che trasmette e per la fiducia che riesce a creare.' })}
            </Lede>
            <Lede size="body" className="mt-5">
              {t('opNw.whyP3', { defaultValue: 'Per questo Aurya non nasce come una directory. Nasce per raccontare le persone, valorizzarne il percorso e costruire una rete in cui contenuti, professionisti ed esperienze si rafforzano a vicenda.' })}
            </Lede>
            <div className="mt-9">
              <EditorialCta to="/manifesto" variant="quiet" data-testid="ol-why-cta">
                {t('opNw.whyCta', { defaultValue: 'Scopri la nostra visione' })}
              </EditorialCta>
            </div>
          </div>
        </Section>

        {/* ── 3. COSA TROVI IN AURYA — le quattro promesse ─────────
            Fondo sabbia: le schede sono bianche, e schede bianche su
            fondo bianco non esistono. Griglia 2x2 e non quattro
            colonne: i testi sono lunghi, e a un quarto di larghezza
            diventerebbero quattro colonne di parole spezzate.
            La chiusura della sezione non e' una quinta scheda: e' la
            voce della pagina che alza il tono, quindi torna al display
            serif e sta al centro, sotto la griglia. */}
        <Section tone="sand" rhythm="screen" labelledBy="ol-find-title" width="max-w-6xl">
          <div data-testid="ol-find">
            <DisplayTitle as="h2" id="ol-find-title" size="section" measure="title">
              {t('opNw.findTitle', { defaultValue: 'Uno spazio che cresce insieme al tuo lavoro.' })}
            </DisplayTitle>
            <Lede size="body" className="mt-6">
              {t('opNw.findIntro', { defaultValue: 'Entrando nella rete inizierai a costruire una presenza digitale pensata per accompagnare la tua attività nel tempo.' })}
            </Lede>
            <ul className="mt-10 grid list-none gap-7 p-0 sm:mt-12 sm:gap-8 lg:grid-cols-2">
              {cards.map((c) => (
                <li key={c.numeral} data-testid={`ol-card-${c.numeral}`} className="h-full">
                  <OfferCard image={CARD_PHOTOS[c.numeral]} {...c} />
                </li>
              ))}
            </ul>
            <div className="mt-12 sm:mt-14">
              <DisplayTitle as="p" size="section" measure="lines"
                            className="text-[1.6rem] leading-[1.18] sm:text-[2rem] lg:text-[2.4rem]">
                <TitleLine>
                  {t('opNw.findCloseA', { defaultValue: 'Non stiamo costruendo semplicemente una piattaforma.' })}
                </TitleLine>
                <TitleLine>
                  {t('opNw.findCloseB', { defaultValue: 'Stiamo costruendo lo spazio digitale che molti professionisti del benessere hanno sempre desiderato.' })}
                </TitleLine>
              </DisplayTitle>
            </div>
          </div>
        </Section>

        {/* ── 4. COSTRUIAMO AURYA INSIEME — prima ancora verde ─────
            Il cuore della proposta: non "iscriviti", ma "decidi con
            noi". Il verde pieno le da' il peso che il testo da solo
            non riusciva a prendersi e spezza la sequenza di fondi
            chiari esattamente a meta' della lettura.

            SW2 — la fascia a tutta larghezza, come "La rete" della
            home ma SPECULARE (foto a sinistra, testo a destra): le due
            pagine sono sorelle, non fotocopie. La fotografia e' r02,
            due persone che meditano insieme nel bosco al tramonto:
            l'unica foto al plurale della cartella, nella sola sezione
            che parla di fare le cose INSIEME. Il testo sta sul verde
            PIENO e mai sopra l'immagine: crema su salvia 7,28:1, al
            90% 6,26:1 (minimo AA 4,5:1). La geometria della mezza
            griglia e' quella della home: mezzo contenitore (36rem =
            meta' di max-w-6xl) agganciato al centro con mr-auto, cosi'
            il filo verticale della pagina resta uno solo. */}
        <Section tone="sage" rhythm="none" labelledBy="ol-build-title"
                 width="max-w-none" gutter={false}>
          <div data-testid="ol-build" className="grid lg:grid-cols-2 lg:items-stretch">
            {/* decorativa: la sezione si capisce tutta a parole */}
            <img
              src={TOGETHER_PHOTO}
              alt=""
              width="900"
              height="599"
              loading="lazy"
              decoding="async"
              className="h-56 w-full object-cover sm:h-80 lg:h-full lg:min-h-[30rem]"
            />
            <div className="flex items-center px-6 py-16 sm:px-8 sm:py-24 lg:py-28 lg:px-0">
              <div className="w-full lg:mr-auto lg:max-w-[36rem] lg:pl-14 lg:pr-8">
                <DisplayTitle as="h2" id="ol-build-title" size="section" measure="title">
                  {t('opNw.buildTitle', { defaultValue: 'I primi professionisti avranno un ruolo speciale.' })}
                </DisplayTitle>
                {/* tone inherit: sul verde l'opacita' di default mangia
                    contrasto, e il crema all'80% scenderebbe sotto AA */}
                <Lede size="lead" tone="inherit" className="mt-7">
                  {t('opNw.buildP1', { defaultValue: 'Aurya è ancora all’inizio. Per questo vogliamo costruirla insieme alle persone che ogni giorno lavorano nel mondo del benessere.' })}
                </Lede>
                <Lede size="body" tone="inherit" className="mt-5 opacity-90">
                  {t('opNw.buildP2', { defaultValue: 'Le vostre idee, i vostri bisogni e la vostra esperienza guideranno l’evoluzione del progetto.' })}
                </Lede>
                <Lede size="body" tone="inherit" className="mt-5 opacity-90">
                  {t('opNw.buildP3', { defaultValue: 'Entrare oggi significa contribuire alla nascita di una rete che continuerà a crescere negli anni.' })}
                </Lede>
                <div className="mt-9">
                  <EditorialCta href={FORM_ANCHOR} onClick={scrollToForm}
                                variant="light" data-testid="ol-build-cta">
                    {t('opNw.buildCta', { defaultValue: 'Parliamone' })}
                  </EditorialCta>
                </div>
              </div>
            </div>
          </div>
        </Section>

        {/* ── 5. DOMANDE FREQUENTI — l'elenco leggibile ────────────
            Fondo bianco pieno: e' la sezione di servizio della pagina,
            e la luce piena e' quella che si legge meglio. Le coppie
            stanno in colonna singola con un filo sottile a separarle:
            due colonne avrebbero costretto l'occhio a saltare, e con
            quattro domande non c'e' nulla da comprimere. */}
        <Section tone="paper" rhythm="screen" labelledBy="ol-faq-title" width="max-w-3xl">
          <div data-testid="ol-faq">
            <DisplayTitle as="h2" id="ol-faq-title" size="section" measure="title">
              {t('opNw.faqTitle', { defaultValue: 'Domande frequenti.' })}
            </DisplayTitle>
            <dl className="mt-10 sm:mt-12">
              {faq.map((f, i) => (
                <div key={f.q}
                     className={`py-7 ${i > 0 ? 'border-t border-[#1e2f28]/[0.10]' : 'pt-0'}`}>
                  <dt className="font-display text-[1.3rem] leading-snug text-foreground sm:text-[1.5rem]">
                    {f.q}
                  </dt>
                  <dd className="mt-3 max-w-[62ch] text-base leading-relaxed text-foreground/75 sm:text-lg">
                    {f.a}
                  </dd>
                </div>
              ))}
            </dl>
          </div>
        </Section>

        {/* ── 6. CHI SIAMO — i volti veri ──────────────────────────
            Tre negazioni secche e poi la frase: il titolo e' fatto di
            frasi, quindi ogni riga e' una <TitleLine> e non un a-capo
            estetico (in ogni lingua restano tre righe distinte).
            Il racconto dei fondatori NON e' riscritto: e' lo stesso
            testo verificato di /manifesto e /chi-siamo (aboutPage.*),
            con la stessa fotografia e lo stesso alt. */}
        <Section tone="cream" rhythm="screen" labelledBy="ol-who-title" width="max-w-6xl">
          <div data-testid="ol-who">
            <p className="eyebrow mb-5">
              {t('opNw.whoEyebrow', { defaultValue: 'Chi siamo' })}
            </p>
            <DisplayTitle as="h2" id="ol-who-title" size="section" measure="lines"
                          className="text-[1.9rem] leading-[1.14] sm:text-[2.4rem] lg:text-[2.9rem]">
              <TitleLine>
                {t('opNw.whoLine1', { defaultValue: 'Non siamo un’agenzia di marketing.' })}
              </TitleLine>
              <TitleLine>
                {t('opNw.whoLine2', { defaultValue: 'Non siamo un software.' })}
              </TitleLine>
              <TitleLine>
                {t('opNw.whoLine3', { defaultValue: 'Non siamo una directory.' })}
              </TitleLine>
            </DisplayTitle>
            <Lede size="lead" className="mt-7">
              {t('opNw.whoLead', { defaultValue: 'Siamo persone che credono che il benessere meriti uno spazio diverso sul web.' })}
            </Lede>

            <div className="mt-12 grid gap-9 sm:mt-14 lg:grid-cols-12 lg:items-center lg:gap-14">
              <div className="lg:col-span-5">
                {/* SW2 — taglio ritratto (4:5): l'originale e' quasi
                    quadrato (900x886) e il vecchio 4:3 gli tagliava la
                    fronte e il mare; cosi' si vede quasi intero e i
                    volti restano grandi anche nella colonna stretta */}
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
                <h3 className="font-display text-[1.6rem] leading-tight text-foreground sm:text-[2rem]">
                  {tl('aboutPage.facesTitle', { defaultValue: 'Siamo Davide e Valentina' })}
                </h3>
                <Lede size="body" className="mt-5">
                  {tl('aboutPage.facesBody1', { defaultValue: 'Dietro ad Aurya ci siamo noi: una coppia unita dalla passione per la crescita personale e l’evoluzione interiore. Abbiamo fuso le nostre competenze per creare qualcosa di unico. Valentina è l’anima olistica del progetto: operatrice Reiki di terzo livello, guida le persone attraverso letture evolutive di tarocchi, oracoli e lo studio delle mappe natali. Davide porta la sua esperienza nel mondo digitale, costruendo piattaforme capaci di connettere le persone.' })}
                </Lede>
                <div className="mt-8">
                  <EditorialCta to="/manifesto" variant="quiet" data-testid="ol-who-cta">
                    {t('opNw.whoCta', { defaultValue: 'Conosci la nostra storia' })}
                  </EditorialCta>
                </div>
              </div>
            </div>
          </div>
        </Section>

        {/* ── 7. IL FORM — la conversazione ────────────────────────
            UN solo form in tutta la pagina, con l'ancora #presentati.
            LeadForm non si tocca: stessi campi, stesso POST
            /public/leads. Cambia solo l'etichetta del bottone, che era
            gia' un prop (`ctaLabel`): la landing viaggiatori non lo
            passa e continua a leggere il suo default.
            Colonna singola e centrata: qui non c'e' piu' niente da
            leggere, c'e' solo da rispondere. */}
        <Section tone="sand" rhythm="screen" labelledBy="ol-form-title" width="max-w-2xl"
                 id="presentati" className="scroll-mt-20">
          <div data-testid="ol-form">
            <DisplayTitle as="h2" id="ol-form-title" size="section" measure="title"
                          className="text-[1.9rem] leading-[1.12] sm:text-[2.4rem] lg:text-[2.75rem]">
              {t('opNw.formTitle', { defaultValue: 'Raccontaci qualcosa di te.' })}
            </DisplayTitle>
            <Lede size="body" className="mt-6">
              <TitleLine>
                {t('opNw.formSubA', { defaultValue: 'Non è una candidatura.' })}
              </TitleLine>
              <TitleLine>
                {t('opNw.formSubB', { defaultValue: 'È l’inizio di una conversazione.' })}
              </TitleLine>
            </Lede>
            <div className="mt-9 rounded-[1.75rem] bg-white p-6 ring-1 ring-[#1e2f28]/[0.07] shadow-[0_1px_2px_rgba(30,47,40,0.04),0_18px_40px_-24px_rgba(30,47,40,0.28)] sm:p-8">
              <LeadForm
                type="operator"
                accent={SAGE}
                ctaLabel={t('opNw.formCta', { defaultValue: 'Entriamo in contatto' })}
              />
            </div>
            {/* PL22 — il canale diretto resta: c'e' chi i form non li
                ama, e un'email vera vale piu' di un contatto perso. */}
            <p className="mt-5 flex flex-wrap items-center gap-1.5 text-sm text-foreground/70">
              <Mail className="h-4 w-4 shrink-0 text-[#2f5749]" aria-hidden />
              {t('op.directT', { defaultValue: 'Preferisci parlarne senza form?' })}{' '}
              <a href="mailto:info@aurya.life"
                 className="font-medium text-[#2f5749] underline underline-offset-[4px] decoration-[#2f5749]/40 hover:decoration-[#2f5749]">
                info@aurya.life
              </a>
            </p>
          </div>
        </Section>

        {/* ── 8. CHIUSURA — seconda ancora verde ───────────────────
            Due frasi, una per riga, e un invito solo. Sul verde il
            bottone pieno di brand sparirebbe (verde su verde), quindi
            la primaria prende il trattamento `tone="dark"`: crema con
            testo verde scuro, lo stesso della home sopra il tramonto. */}
        <Section tone="sage" rhythm="screen" labelledBy="ol-end-title" width="max-w-5xl">
          <div data-testid="ol-end">
            <DisplayTitle as="h2" id="ol-end-title" size="section" measure="lines">
              <TitleLine>
                {t('opNw.endTitleA', { defaultValue: 'Le reti non si costruiscono in un giorno.' })}
              </TitleLine>
              <TitleLine>
                {t('opNw.endTitleB', { defaultValue: 'Si costruiscono una persona alla volta.' })}
              </TitleLine>
            </DisplayTitle>
            <Lede size="lead" tone="inherit" className="mt-7">
              {t('opNw.endBody', { defaultValue: 'Se senti che Aurya rappresenta anche il tuo modo di vedere il benessere, ci piacerebbe conoscerti.' })}
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
