/**
 * OperatorLandingPage — /entra-nella-rete (OL3, riscrittura integrale del
 * copy da parte del founder, 2/8/2026).
 *
 * IL NOME DELLA PAGINA CAMBIA. Non e' piu' la pagina "per gli operatori":
 * e' la pagina PER I PROFESSIONISTI DEL BENESSERE. La parola d'ordine
 * entra nell'occhiello dell'apertura, nel titolo SEO e nel microcopy.
 * Le etichette fuori da questa pagina (header, login, banner) le cambia
 * il founder: qui dentro non si esce dal file.
 *
 * L'IMPIANTO VISIVO NON SI SMONTA. Questa e' la pagina che il founder ha
 * approvato e che e' diventata il modello di tutto il sito
 * (docs/DESIGN_PASS_DS_2026-08.md): ancora scura in apertura, foto vere e
 * grandi, alternanza dei fondi, blocchi a schede, ancore multiple verso
 * l'azione. Il copy e' nuovo da capo a fondo, la grammatica e' la stessa
 * e in due punti si rafforza (la fascia fotografica a tutta larghezza e
 * il registro delle cinque voci sul verde).
 *
 * NOVE SEZIONI, copy CHIUSO parola per parola (le chiavi vivono in
 * `opPro`, namespace prelaunch, SOLO in italiano: il founder ha chiesto
 * niente en/de/fr, e con fallbackLng='it' le altre lingue leggono queste):
 *   1. HERO       la rete da costruire       foto + due CTA
 *   2. OGGI       perche' entrare adesso     due colonne, foto r02
 *   3. RETE       cosa significa entrare     tre schede con foto
 *   4. GIA' QUI   quello che puoi gia' fare  fascia foto + registro verde
 *   5. PER CHI    la selezione gentile       il no e il si', affiancati
 *   6. FAQ        cinque domande             elenco leggibile, sempre aperto
 *   7. CHI SIAMO  i volti veri               Valentina e Davide
 *   8. FORM       la conversazione           #presentati, LeadForm
 *   9. CHIUSURA   l'invito                   ancora verde
 *
 * FONDI, nell'ordine: dark(foto) → sabbia → crema → sabbia → FOTO A TUTTA
 * LARGHEZZA → VERDE → crema → bianco → sabbia → crema → VERDE. Due sezioni
 * adiacenti non hanno mai lo stesso fondo, e le due ancore verdi (4 e 9)
 * non si toccano.
 *
 * LE FOTOGRAFIE, una per ragione:
 *   HERO   hero-organizer (mani in gyan mudra) — la copertina storica.
 *          Su desktop il velo uniforme non c'e': colonna scura piena a
 *          sinistra per il testo (contrasto FISSO 15,96:1) e fotografia
 *          NUDA a destra. Su mobile resta il fondo fotografico velato,
 *          misurato sui pixel reali (7,95:1 nel caso peggiore).
 *   r02    "perche' entrare oggi": l'unica foto al plurale del magazzino,
 *          nella sezione che parla di costruire INSIEME.
 *   r03    una persona sola nel suo elemento → "una presenza che parla di te".
 *   r08    le mani di chi cura → la fiducia che nasce prima della chiamata.
 *   r09    la pratica nello spazio di tutti → la presenza che continua a crescere.
 *   r05    il cairn, una pietra alla volta → "quello che puoi gia' fare".
 *          E' la sezione che dice di piu' e si prende il trattamento piu'
 *          forte della pagina: la fascia a tutta larghezza col titolo
 *          DENTRO l'immagine, poi il verde pieno col registro delle voci.
 *          Il velo di PhotoBand e' stato RIMISURATO su r05 (e' un'altra
 *          fotografia, quindi non ci si fida della misura di r01):
 *          composti i due strati sui pixel veri, il pixel piu' chiaro
 *          sotto il testo da' 5,58:1 col crema a 1440 e 5,72:1 a 390
 *          (minimo AA: 4,5:1 corpo, 3:1 display).
 *   chisiamo-aurya  i fondatori, taglio ritratto 4:5.
 * Il video del tramonto resta la firma della home e non si duplica qui.
 *
 * IL FORM (OL3b, richiesta del founder arrivata a lavoro in corso): sette
 * campi e non piu' quello che c'era. L'ultimo, "qual e' la cosa che
 * vorresti far capire alle persone del tuo lavoro", non e' una riga fra
 * le altre: e' la domanda che vale l'intera candidatura, quindi ha una
 * sua etichetta visibile e un campo alto. La meccanica del POST e il
 * blocco del consenso privacy NON si toccano (vedi LeadForm.jsx).
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { Mail } from 'lucide-react';
import MarketplaceShell from '../storefront/components/MarketplaceShell';
import useSeoMeta from '../storefront/lib/useSeoMeta';
import LeadForm from './LeadForm';
import {
  Section, DisplayTitle, TitleLine, Lede, EditorialCta, PhotoBand, PhotoSplit,
} from '../../components/editorial';

/** l'ancora del form: destinazione delle CTA interne e dei link che
    arrivano da fuori (/entra-nella-rete#presentati dalla home) */
const FORM_ANCHOR = '#presentati';

/** il verde di brand del kit editoriale: la pagina non ha un accento
    proprio, parla la lingua della home */
const SAGE = '#2f5749';

const HERO_PHOTO = '/media/hero-organizer.webp';
const FOUNDERS_PHOTO = '/media/chisiamo-aurya.jpg';
const TOGETHER_PHOTO = '/media/prelaunch/r02.jpg';   // costruire insieme
const HORIZON_PHOTO = '/media/prelaunch/r05.jpg';    // il cairn: una pietra alla volta

/* Le tre schede della sezione 3. DECORATIVE (alt=""): ogni scheda dice
   gia' tutto con titolo e testo, descriverle a voce sarebbe rumore. */
const CARD_PHOTOS = {
  '01': '/media/prelaunch/r03.jpg',  // una persona nel suo elemento
  '02': '/media/prelaunch/r08.jpg',  // le mani di chi cura, da vicino
  '03': '/media/prelaunch/r09.jpg',  // la pratica nello spazio di tutti
};

/**
 * OfferCard — una delle tre promesse della sezione 3.
 *
 * NON e' PillarCard: quella scheda ha un piede sempre presente (link o
 * etichetta di stato), qui nessuna delle tre porta da qualche parte,
 * quindi il piede non esiste e la scheda resta un argomento.
 * Fotografia in testa 3:2 come nel kit, rapporto dichiarato per prenotare
 * lo spazio prima che il file arrivi (zero salti di layout). Niente zoom
 * al passaggio del mouse: la scheda non si apre, e muoversi sotto il
 * cursore prometterebbe un clic che non esiste.
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
  // l'unica cosa che resta al namespace landings e' l'alt VERIFICATO
  // della fotografia dei fondatori, lo stesso di /chi-siamo e del
  // Manifesto: la descrizione di una foto vera non si riscrive due volte.
  const { t: tl } = useTranslation('landings');

  useSeoMeta({
    title: t('opPro.seoTitle', { defaultValue: 'Per i professionisti del benessere | Aurya' }),
    description: t('opPro.seoDesc', { defaultValue: 'Stiamo costruendo la rete dei professionisti del benessere: profili raccontati con cura, interviste e uno spazio che nel tempo diventerà il punto di riferimento della tua presenza digitale.' }),
    canonicalPath: '/entra-nella-rete',
  });

  /** chi ha chiesto meno movimento non si fa mezza pagina di viaggio */
  const prefersReducedMotion = () => typeof window.matchMedia === 'function'
    && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* Le CTA interne (hero e chiusura) portano tutte QUI. preventDefault:
     l'hash non finisce nell'URL, quindi il gesto si puo' ripetere
     all'infinito. Un <Link to="#presentati"> del router avrebbe
     funzionato solo al primo clic. */
  const scrollToForm = (e) => {
    e.preventDefault();
    document.getElementById('presentati')?.scrollIntoView({
      behavior: prefersReducedMotion() ? 'auto' : 'smooth',
      block: 'start',
    });
  };

  /* HP2 — l'ancora #presentati e' una destinazione anche da FUORI: la
     home linka /entra-nella-rete#presentati. Chi arriva da li' viene
     portato all'ancora da ScrollToTop in App.js, che e' hash-aware per
     tutte le ancore del sito e sa aspettare le pagine lazy. Qui resta
     solo l'id sulla sezione del form. */

  const cards = [
    {
      numeral: '01',
      title: t('opPro.j1t', { defaultValue: 'Una presenza che parla di te.' }),
      body: t('opPro.j1b', { defaultValue: 'Realizziamo insieme un profilo pubblico che racconta il tuo approccio, la tua storia e il valore del tuo lavoro. Un luogo che potrai condividere ovunque e che crescerà insieme alla tua attività.' }),
    },
    {
      numeral: '02',
      title: t('opPro.j2t', { defaultValue: 'Più fiducia, prima ancora della prima chiamata.' }),
      body: t('opPro.j2b', { defaultValue: 'Attraverso un’intervista e i contenuti del Magazine aiutiamo le persone a conoscerti prima ancora di contattarti. Perché chi comprende il tuo approccio ti sceglie con maggiore consapevolezza.' }),
    },
    {
      numeral: '03',
      title: t('opPro.j3t', { defaultValue: 'Una presenza che continua a crescere.' }),
      body: t('opPro.j3b', { defaultValue: 'Il tuo profilo sarà valorizzato attraverso il Magazine, la newsletter, i nostri contenuti e, nel tempo, da tutto l’ecosistema Aurya. Ogni nuovo contenuto contribuirà a dare maggiore visibilità anche al tuo lavoro.' }),
    },
  ];

  /* Le cinque voci della sezione 4. Il founder le aveva accompagnate con
     delle emoji: qui parlano la grammatica grafica del sito (registro a
     righe con filo sottile sul verde), che e' identica su ogni sistema
     operativo, mentre un'emoji la disegna il telefono di chi legge. */
  const voices = [
    {
      title: t('opPro.v1t', { defaultValue: 'Pubblichi i tuoi servizi.' }),
      body: t('opPro.v1b', { defaultValue: 'Con il tuo listino prezzi sempre aggiornato.' }),
    },
    {
      title: t('opPro.v2t', { defaultValue: 'Ricevi richieste di appuntamento.' }),
      body: t('opPro.v2b', { defaultValue: 'Direttamente dal tuo profilo.' }),
    },
    {
      title: t('opPro.v3t', { defaultValue: 'Organizzi workshop ed eventi.' }),
      body: t('opPro.v3b', { defaultValue: 'In pochi minuti. Con iscrizioni online.' }),
    },
    {
      title: t('opPro.v4t', { defaultValue: 'Pubblichi ritiri.' }),
      body: t('opPro.v4b', { defaultValue: 'Con tutte le informazioni e la gestione delle prenotazioni.' }),
    },
    {
      // SP3 — Aurya Sound e' uno strumento gia' vero: la CTA della
      // biblioteca pubblica (#sound) atterra su questo registro
      title: t('opPro.v6t', { defaultValue: 'Componi esperienze sonore.' }),
      body: t('opPro.v6b', { defaultValue: 'Con Aurya Sound ascolti frequenze e metodi, li combini con la tua voce e pubblichi la sessione con un link.' }),
    },
    {
      title: t('opPro.v5t', { defaultValue: 'Condividi un unico link.' }),
      body: t('opPro.v5b', { defaultValue: 'Il tuo sito. I tuoi servizi. I tuoi eventi. Le recensioni. La tua storia. Tutto nello stesso posto.' }),
    },
  ];

  /* Cinque domande, cinque risposte SEMPRE VISIBILI. Niente accordion:
     le risposte sono di due o tre righe, un accordion le nasconderebbe
     dietro un gesto per risparmiare trecento pixel su mobile,
     toglierebbe il testo ai motori di ricerca e costringerebbe a cinque
     clic chi vuole solo capire come funziona. Il <dl> e' la semantica
     giusta: domanda e risposta, in coppia.
     Le prime tre risposte sono quelle GIA' APPROVATE e non si riscrivono
     (la prima e' anche l'unico punto della pagina in cui si parla di
     quanto costa: e' una risposta onesta a una domanda legittima, non un
     argomento da vetrina). Le ultime due sono nuove e aspettano l'ok del
     founder: dicono solo cose che il prodotto fa davvero oggi. */
  const faq = [
    {
      q: t('opPro.faq1q', { defaultValue: 'Quanto costa?' }),
      // AB2 (founder, 13/8) — la risposta diventa concreta: tre punti
      // e il rimando alla pagina /costi con i due piani spiegati.
      a: (
        <ul className="list-disc space-y-2 pl-5">
          <li>{t('opPro.faq1b1', { defaultValue: 'L’utilizzo della piattaforma è sempre gratuito.' })}</li>
          <li>{t('opPro.faq1b2', { defaultValue: 'Fino al 31 dicembre 2026 Aurya non ha alcun costo, nemmeno quando le prenotazioni arrivano tramite Aurya.' })}</li>
          <li>
            {t('opPro.faq1b3', { defaultValue: 'Dopo quella data potrai scegliere tra due soluzioni, in base alle tue esigenze. ' })}
            <Link to="/costi" className="font-semibold text-primary underline underline-offset-2">
              {t('opPro.faq1b3cta', { defaultValue: 'Guarda i piani e i costi' })}
            </Link>
          </li>
        </ul>
      ),
    },
    {
      q: t('opPro.faq2q', { defaultValue: 'Come funziona?' }),
      a: t('opPro.faq2a', { defaultValue: 'Ci scrivi due righe su di te. Se c’è sintonia ci sentiamo e ti facciamo qualche domanda. Poi scriviamo il tuo profilo con le tue parole e lo pubblichiamo insieme alla tua storia.' }),
    },
    {
      q: t('opPro.faq3q', { defaultValue: 'Quando arriveranno le nuove funzionalità?' }),
      a: t('opPro.faq3a', { defaultValue: 'Le stiamo costruendo insieme ai primi professionisti che entrano. Le priorità le decidiamo ascoltando loro, e chi c’è dall’inizio le prova per primo.' }),
    },
    {
      q: t('opPro.faq4q', { defaultValue: 'Posso usare Aurya anche se ho già un sito?' }),
      a: t('opPro.faq4a', { defaultValue: 'Sì, e non devi scegliere. Il profilo Aurya non sostituisce il tuo sito: dal profilo puoi linkare il sito e i tuoi canali, così chi ti trova qui arriva anche lì. Molti lo usano come pagina da condividere nei messaggi e sui social, dove serve un link solo.' }),
    },
    {
      q: t('opPro.faq5q', { defaultValue: 'Posso gestire prenotazioni esterne?' }),
      a: t('opPro.faq5a', { defaultValue: 'Non ancora del tutto. Oggi puoi bloccare gli orari in cui sei già occupato, così da Aurya nessuno te li chiede, e vedi in un unico calendario gli appuntamenti nati qui. Quello che ancora non c’è è il collegamento con un’agenda esterna: se prendi prenotazioni fuori da Aurya, per ora restano fuori. È tra le cose che stiamo costruendo, e te lo diremo quando sarà pronto, non prima.' }),
    },
  ];

  const ctaJoin = t('opPro.ctaJoin', { defaultValue: 'Entra nella rete Aurya' });
  const ctaContact = t('opPro.ctaContact', { defaultValue: 'Entriamo in contatto' });

  return (
    <MarketplaceShell noSearch>
      <div className="bg-background">

        {/* ── 1. HERO — la rete da costruire ───────────────────────
            Due tempi dentro una sola sezione.

            a) LA FOTO E LA FRASE. hero-organizer (mani in gyan mudra):
               fondo fotografico velato fino a tablet, colonna scura +
               foto nuda da lg. Il testo e' allineato a SINISTRA e non
               centrato come nella home: e' una constatazione rivolta a
               una persona sola, e centrarla la farebbe sembrare uno
               slogan. Dentro l'apertura sta anche la cadenza staccata
               del founder (tempo / studio / esperienza / presenza):
               quattro righe di una riga sola, il ritmo si VEDE.
            b) LA SOGLIA. La promessa lunga e le due azioni stanno sotto
               la foto, sul sabbia: si leggono sul chiaro, le CTA hanno
               il contrasto pieno del kit e chi scorre arriva ai bottoni
               DOPO aver letto l'argomento.

            IL VELO, MISURATO (solo sotto il breakpoint lg). Su mobile e
            tablet la foto sta DIETRO il testo e sopra passano due
            strati: uno verticale e uno radiale che aggiunge buio solo
            dietro la colonna di testo. Misurato componendo i veli sui
            pixel reali: il pixel piu' chiaro sotto il testo da' 7,95:1
            col crema #f6f2e8. L'ombra (.text-hero-shadow) e' la cintura
            di sicurezza, non il motore. DA lg IN SU la fotografia
            smette di fare da tappezzeria e diventa una colonna nuda
            nella meta' destra: il testo sta su #0e1a15 pieno, contrasto
            FISSO 15,96:1. Fra colonna e foto una cerniera in gradiente:
            il buio dietro il testo non dipende mai dall'immagine. */}
        <section data-testid="ol-hero" aria-labelledby="ol-hero-title">
          <div className="relative isolate overflow-hidden bg-[#0e1a15] text-[#f6f2e8]">
            {/* decorativa: il titolo dice gia' quello che la foto
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
              <div className="lg:max-w-[30rem]">
                {/* OL3 — il nome della pagina, detto in chiaro prima del
                    titolo: questa e' la pagina PER I PROFESSIONISTI DEL
                    BENESSERE, non "per gli operatori" */}
                <p className="eyebrow eyebrow-light mb-6 text-hero-shadow">
                  {t('opPro.heroEyebrow', { defaultValue: 'Per i professionisti del benessere' })}
                </p>
                <DisplayTitle as="h1" id="ol-hero-title" size="heroLines" measure="lines"
                              className="text-hero-shadow">
                  {t('opPro.heroTitle', { defaultValue: 'Costruiamo la rete dei professionisti del benessere.' })}
                </DisplayTitle>
                <div className="mt-7 space-y-4 sm:mt-9 sm:space-y-5">
                  <Lede size="body" tone="inherit" className="text-hero-shadow">
                    {t('opPro.heroP1', { defaultValue: 'Ogni giorno accompagni persone nel loro percorso di crescita, equilibrio e benessere.' })}
                  </Lede>
                  {/* la cadenza: quattro frasi di una parola, una per
                      riga. Sono un solo respiro, quindi un solo
                      paragrafo con quattro righe volute */}
                  <Lede size="body" tone="inherit" className="text-hero-shadow">
                    <span className="block">{t('opPro.heroBeat1', { defaultValue: 'Ci metti tempo.' })}</span>
                    <span className="block">{t('opPro.heroBeat2', { defaultValue: 'Studio.' })}</span>
                    <span className="block">{t('opPro.heroBeat3', { defaultValue: 'Esperienza.' })}</span>
                    <span className="block">{t('opPro.heroBeat4', { defaultValue: 'Presenza.' })}</span>
                  </Lede>
                  <Lede size="body" tone="inherit" className="text-hero-shadow">
                    {t('opPro.heroP2', { defaultValue: 'Eppure, online, tutto questo spesso si riduce a una scheda, qualche recensione e un elenco di servizi.' })}
                  </Lede>
                  <Lede size="body" tone="inherit" className="text-hero-shadow">
                    {t('opPro.heroP3', { defaultValue: 'Noi crediamo che il tuo lavoro meriti molto di più.' })}
                  </Lede>
                </div>
                {/* LC4 — l'azione nel primo campo visivo. La revisione
                    pre-lancio ha misurato la prima CTA a 3,4 schermate
                    (desktop) e il form a 26: chi arriva gia' convinto —
                    un passaparola, un'intervista — doveva comunque farsi
                    tutta la pagina. Stessa ancora della soglia, che
                    resta: quella parla a chi legge la promessa, questa
                    a chi l'ha gia' sentita altrove. */}
                <div className="mt-9 sm:mt-10">
                  <EditorialCta href={FORM_ANCHOR} onClick={scrollToForm}
                                tone="dark" variant="solid"
                                data-testid="ol-hero-cta-top">
                    {ctaContact}
                  </EditorialCta>
                </div>
              </div>
            </div>
          </div>

          {/* la soglia: la promessa e le due porte, sul chiaro */}
          <Section tone="sand" rhythm="flow" width="max-w-5xl">
            <DisplayTitle as="p" size="section" measure="lines"
                          className="text-[1.6rem] leading-[1.18] sm:text-[2rem] lg:text-[2.3rem]">
              {t('opPro.heroP4', { defaultValue: 'Per questo stiamo costruendo Aurya.' })}
            </DisplayTitle>
            <Lede size="lead" className="mt-6">
              {t('opPro.heroP5', { defaultValue: 'Una rete di professionisti raccontati con cura e uno spazio che, nel tempo, diventerà il punto di riferimento della tua presenza digitale.' })}
            </Lede>
            <div className="mt-9 flex flex-col items-start gap-5 sm:flex-row sm:items-center sm:gap-8">
              <EditorialCta href={FORM_ANCHOR} onClick={scrollToForm}
                            variant="solid" data-testid="ol-hero-cta">
                {ctaContact}
              </EditorialCta>
              <EditorialCta to="/manifesto" variant="quiet" data-testid="ol-hero-cta-alt">
                {t('opPro.ctaWhy', { defaultValue: 'Perché stiamo costruendo Aurya' })}
              </EditorialCta>
            </div>
          </Section>
        </section>

        {/* ── 2. PERCHE' ENTRARE OGGI — la finestra aperta ─────────
            Il ragionamento sta accanto a una figura, non dentro una
            colonna: r02 e' l'unica fotografia al plurale del magazzino
            (due persone che meditano insieme) ed e' esattamente la
            sezione che dice "ci aiuteranno a costruirla".
            Il testo NON sta mai sopra l'immagine: sta sul crema pieno
            accanto, quindi il contrasto e' quello dichiarato dal tono e
            non dipende da come e' esposto quello scatto.
            La chiusura non e' un altro paragrafo: e' la voce della
            pagina che alza il tono, quindi torna al display serif. */}
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
            {t('opPro.nowTitle', { defaultValue: 'Perché entrare oggi.' })}
          </DisplayTitle>
          <Lede size="lead" className="mt-7">
            {t('opPro.nowP1', { defaultValue: 'Aurya è ancora all’inizio. Ed è proprio questo il momento in cui puoi contribuire a darle forma.' })}
          </Lede>
          <Lede size="body" className="mt-5">
            {t('opPro.nowP2', { defaultValue: 'I primi professionisti non saranno semplicemente presenti sulla piattaforma. Ci aiuteranno a costruirla.' })}
          </Lede>
          <Lede size="body" className="mt-5">
            {t('opPro.nowP3', { defaultValue: 'Ascolteremo i vostri bisogni, raccoglieremo i vostri suggerimenti e svilupperemo strumenti che nascono dal lavoro reale di chi accompagna ogni giorno le persone.' })}
          </Lede>
          <DisplayTitle as="p" size="section" measure="lines"
                        className="mt-10 text-[1.5rem] leading-[1.2] sm:text-[1.8rem] lg:text-[2.05rem]">
            <TitleLine>
              {t('opPro.nowCloseA', { defaultValue: 'Non stiamo cercando iscritti.' })}
            </TitleLine>
            <TitleLine>
              {t('opPro.nowCloseB', { defaultValue: 'Stiamo cercando le persone con cui costruire Aurya.' })}
            </TitleLine>
          </DisplayTitle>
        </PhotoSplit>

        {/* ── 3. COSA SIGNIFICA ENTRARE NELLA RETE — le tre promesse
            Fondo sabbia: le schede sono bianche, e schede bianche su
            fondo bianco non esistono. Tre colonne su desktop, una sola
            su telefono: i testi sono di tre righe, a un terzo di
            larghezza restano righe vere e non parole spezzate. */}
        <Section tone="sand" rhythm="screen" labelledBy="ol-join-title" width="max-w-6xl">
          <div data-testid="ol-join">
            <DisplayTitle as="h2" id="ol-join-title" size="section" measure="title">
              {t('opPro.joinTitle', { defaultValue: 'Cosa significa entrare nella rete.' })}
            </DisplayTitle>
            <ul className="mt-10 grid list-none gap-7 p-0 sm:mt-12 sm:gap-8 lg:grid-cols-3">
              {cards.map((c) => (
                <li key={c.numeral} data-testid={`ol-card-${c.numeral}`} className="h-full">
                  <OfferCard image={CARD_PHOTOS[c.numeral]} title={c.title} body={c.body} />
                </li>
              ))}
            </ul>
          </div>
        </Section>

        {/* ── 4. QUELLO CHE PUOI GIA' FARE — il trattamento piu' forte
            OF2 (decisione del founder, 2/8/2026): questa sezione era
            scritta al futuro e prometteva cinque cose che il prodotto fa
            GIA' oggi — listino sul profilo pubblico, richiesta di
            appuntamento per riga di listino, eventi e ritiri con
            iscrizioni, il profilo /o/:slug che raccoglie tutto. La fase
            "rete" spegne la vetrina di scoperta, non gli strumenti del
            professionista: quindi si scrive al presente. L'unica cosa
            davvero futura (la parte pubblica) si dice da sola, in coda.
            E' la sezione che dice di piu', e si prende due battute
            invece di una:
              a) la FASCIA a tutta larghezza, con il titolo e l'orizzonte
                 DENTRO la fotografia (r05, il cairn: una pietra alla
                 volta). E' l'unico momento in cui la pagina esce dalla
                 sua colonna, ed e' li' che si sente il cambio di passo.
              b) l'ANCORA VERDE con il registro delle cinque voci: righe
                 separate da un filo sottile, titolo a sinistra e riga di
                 dettaglio a destra. E' la grammatica grafica del sito al
                 posto delle emoji della specifica: identica su ogni
                 telefono, e allineata come un indice di cose che ci sono.
            Sul verde il crema sta a 7,28:1, al 90% a 6,26:1 (AA: 4,5:1).
            Le due battute sono una sezione sola per chi ascolta la
            pagina: l'h2 e' uno, e sta nella fascia. */}
        <section id="sound" data-testid="ol-go" aria-labelledby="ol-go-title">
          <PhotoBand as="div" image={HORIZON_PHOTO} focus="50% 40%" width="max-w-3xl">
            <DisplayTitle as="h2" id="ol-go-title" size="section" measure="title"
                          className="text-hero-shadow">
              {t('opPro.goTitle', { defaultValue: 'Quello che puoi già fare.' })}
            </DisplayTitle>
            <Lede size="lead" tone="inherit" className="mt-7 text-hero-shadow">
              {t('opPro.goP1', { defaultValue: 'Aurya è il luogo dove raccontiamo professionisti e contenuti.' })}
            </Lede>
            <Lede size="lead" tone="inherit" className="mt-4 text-hero-shadow">
              {t('opPro.goP2', { defaultValue: 'Ed è anche il luogo da cui gestisci la tua presenza professionale. Già adesso.' })}
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
                  {/* opacita' 90 e non il tono `soft` del kit: sul verde
                      l'80% scenderebbe verso il minimo, il 90% resta a
                      6,26:1 e la gerarchia col titolo si legge lo stesso */}
                  <p className="max-w-[52ch] text-base leading-relaxed opacity-90 sm:text-lg lg:col-span-7 lg:pt-1">
                    {v.body}
                  </p>
                </li>
              ))}
            </ul>
            {/* OF2 — la sola cosa futura di questa sezione, e sta DOPO le
                cinque voci, non in mezzo: cosi' nessuno la puo' scambiare
                per una di loro. Il tono e' quello della FAQ sulle agende
                esterne ("quello che ancora non c'e' e'..."): i limiti si
                dicono con le stesse parole ovunque. */}
            <Lede size="body" tone="inherit" className="mt-12 opacity-90 sm:mt-14">
              {t('opPro.goSoon', { defaultValue: 'Quello che ancora non c’è è la parte pubblica: quella in cui sono le persone a cercare un ritiro e ad arrivare a te. L’apriamo quando la rete sarà abbastanza viva da reggerla.' })}
            </Lede>
          </Section>
        </section>

        {/* ── 5. PER CHI E' AURYA — il no e il si', affiancati ─────
            La selezione detta gentilmente. Le due frasi "se..." non sono
            due paragrafi in fila: sono un bivio, quindi stanno una
            accanto all'altra separate da un filo verticale. La prima e'
            piu' bassa di tono (foreground/70 ≈ 5,6:1 sul crema, sopra il
            minimo AA), la seconda ha il colore pieno: la pagina dice
            senza urlare quale delle due strade ci interessa. */}
        <Section tone="cream" rhythm="screen" labelledBy="ol-for-title" width="max-w-5xl">
          <div data-testid="ol-for">
            <DisplayTitle as="h2" id="ol-for-title" size="section" measure="title">
              {t('opPro.forTitle', { defaultValue: 'Per chi è Aurya.' })}
            </DisplayTitle>
            <Lede size="lead" className="mt-7">
              {t('opPro.forP1', { defaultValue: 'Aurya è pensata per professionisti che desiderano costruire relazioni prima ancora che clienti.' })}
            </Lede>
            <Lede size="body" className="mt-5">
              {t('opPro.forP2', { defaultValue: 'Persone che credono nel valore dell’ascolto, della trasparenza e della crescita continua.' })}
            </Lede>
            <div className="mt-11 grid gap-8 sm:mt-14 lg:grid-cols-2 lg:gap-14">
              <p className="font-display text-[1.3rem] leading-snug text-foreground/70 sm:text-[1.5rem]">
                {t('opPro.forNo', { defaultValue: 'Se il tuo obiettivo è semplicemente comparire in un elenco, probabilmente Aurya non fa per te.' })}
              </p>
              <p className="font-display text-[1.3rem] leading-snug text-foreground sm:text-[1.5rem]
                            lg:border-l lg:border-[#1e2f28]/15 lg:pl-14">
                {t('opPro.forYes', { defaultValue: 'Se invece vuoi costruire una presenza professionale autorevole nel tempo, ci piacerebbe conoscerti.' })}
              </p>
            </div>
          </div>
        </Section>

        {/* ── 6. DOMANDE FREQUENTI — l'elenco leggibile ────────────
            Fondo bianco pieno: e' la sezione di servizio della pagina, e
            la luce piena e' quella che si legge meglio. Le coppie stanno
            in colonna singola con un filo sottile a separarle: due
            colonne avrebbero costretto l'occhio a saltare. */}
        <Section tone="paper" rhythm="screen" labelledBy="ol-faq-title" width="max-w-3xl">
          <div data-testid="ol-faq">
            <DisplayTitle as="h2" id="ol-faq-title" size="section" measure="title">
              {t('opPro.faqTitle', { defaultValue: 'Domande frequenti.' })}
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

        {/* ── 7. CHI C'E' DIETRO AURYA — i volti veri ──────────────
            LC4 — qui c'erano tre negazioni secche ("Non siamo
            un'agenzia. Non siamo un software. Non siamo una
            directory."): definirsi per sottrazione a una schermata dal
            form era il punto peggiore dove farlo. Al loro posto il
            payoff del brand, che e' un contrasto voluto e non una
            negazione: e' la sezione dove la frase si dimostra, perche'
            subito sotto arrivano i due qualcuno con nome e faccia.
            Il titolo resta fatto di frasi, ogni riga una <TitleLine>.
            La fotografia dei fondatori e' l'unica foto vera nostra e
            sta in taglio ritratto (4:5): l'originale e' quasi quadrato
            e un 4:3 taglierebbe la fronte e il mare. */}
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

        {/* ── 8. IL FORM — la conversazione ────────────────────────
            UN solo form in tutta la pagina, con l'ancora #presentati.
            Due colonne da lg: a sinistra l'invito (che spiega cos'e' e
            cosa succede dopo), a destra il modulo. Il form OL3b ha sette
            campi: in colonna singola sarebbe diventato un muro alto
            quanto una schermata, e l'invito sarebbe finito fuori vista
            proprio mentre si compila.
            LeadForm: la meccanica del POST e il blocco del consenso
            privacy non si toccano. */}
        <Section tone="cream" rhythm="screen" labelledBy="ol-form-title" width="max-w-6xl"
                 id="presentati" className="scroll-mt-20">
          <div data-testid="ol-form"
               className="grid gap-10 lg:grid-cols-12 lg:items-start lg:gap-16">
            <div className="lg:col-span-5">
              <DisplayTitle as="h2" id="ol-form-title" size="section" measure="title"
                            className="text-[1.9rem] leading-[1.12] sm:text-[2.4rem] lg:text-[2.6rem]">
                {t('opPro.formTitle', { defaultValue: 'Iniziamo a conoscerci.' })}
              </DisplayTitle>
              <Lede size="lead" className="mt-7">
                <span className="block">
                  {t('opPro.formA', { defaultValue: 'Non è una selezione.' })}
                </span>
                <span className="block">
                  {t('opPro.formB', { defaultValue: 'Non è un’iscrizione automatica.' })}
                </span>
                <span className="block">
                  {t('opPro.formC', { defaultValue: 'È una conversazione.' })}
                </span>
              </Lede>
              <Lede size="body" className="mt-6">
                <span className="block">
                  {t('opPro.formD', { defaultValue: 'Compila il modulo.' })}
                </span>
                <span className="block">
                  {t('opPro.formE', { defaultValue: 'Leggeremo personalmente ogni candidatura.' })}
                </span>
                <span className="block">
                  {t('opPro.formF', { defaultValue: 'Se penseremo che ci sia sintonia fisseremo una chiamata.' })}
                </span>
                <span className="block">
                  {t('opPro.formG', { defaultValue: 'Il resto inizierà da lì.' })}
                </span>
              </Lede>
              {/* PL22 — il canale diretto resta: c'e' chi i form non li
                  ama, e un'email vera vale piu' di un contatto perso. */}
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
                <LeadForm
                  type="operator"
                  accent={SAGE}
                  ctaLabel={ctaContact}
                />
              </div>
            </div>
          </div>
        </Section>

        {/* ── 9. CHIUSURA — seconda ancora verde ───────────────────
            Due frasi, una per riga, e un invito solo. Sul verde il
            bottone pieno di brand sparirebbe (verde su verde), quindi la
            primaria prende il trattamento `tone="dark"`: crema con testo
            verde scuro, lo stesso della home sopra il tramonto. */}
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
                {t('opPro.endC', { defaultValue: 'Stiamo iniziando con calma.' })}
              </span>
              <span className="block">
                {t('opPro.endD', { defaultValue: 'Una conversazione alla volta.' })}
              </span>
            </Lede>
            <Lede size="body" tone="inherit" className="mt-5 opacity-90">
              {t('opPro.endBody', { defaultValue: 'Se senti che Aurya rappresenta anche il tuo modo di vedere il benessere, ci piacerebbe costruirla insieme a te.' })}
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
