/**
 * ChiSiamoPage — /chi-siamo (CS2: copy nuovo del founder + disegno).
 *
 * LA REGOLA CHE VIENE PRIMA DI TUTTE, e che il founder ha messo in cima
 * al brief: «questa pagina non deve rispondere a "chi sono Davide e
 * Valentina?". Deve rispondere a "perche' dovrei fidarmi di chi sta
 * costruendo Aurya?"». Le due biografie non sono il centro della
 * pagina: sono la prova di una tesi, e l'impaginazione lo dice prima
 * ancora che si legga una riga.
 *
 * COME LA DOMANDA DIVENTA UNA PAGINA. La risposta a "perche' fidarsi"
 * non e' un curriculum, e' una sequenza: (1) siamo partiti da un
 * problema vero, non da un'idea di business; (2) abbiamo le due
 * competenze che quel problema richiede, e sono due, non una; (3) non
 * abbiamo fretta, e questo si puo' verificare perche' l'ordine dei
 * passi e' dichiarato in anticipo; (4) i principi con cui lavoriamo
 * sono scritti, quindi contestabili; (5) l'esito non dipende solo da
 * noi. Ognuno di questi cinque e' un movimento della pagina, e in
 * quest'ordine e' un ragionamento. Per questo l'apertura NON e' la
 * fotografia dei fondatori ma la domanda da cui siamo partiti: aprire
 * sui nostri volti avrebbe risposto alla domanda sbagliata.
 *
 * DOVE STA LA FOTO VERA. `chisiamo-aurya` e' l'unica fotografia nostra
 * che esiste, e sta al MOVIMENTO 2, dove il testo parla dei due
 * percorsi: mezza pagina di immagine, fino al bordo dello schermo,
 * accanto alle parole e non sotto un velo (PhotoSplit). E' il punto in
 * cui la tesi ha bisogno di una prova, ed e' l'unico punto in cui due
 * facce sono una prova. Non e' un francobollo e non e' un'apertura.
 *
 * LE ALTRE DUE FOTOGRAFIE, e perche' non sono quelle assegnate.
 *   APERTURA r08 (le mani di chi cura, macro, fondo scuro). Il DS
 *     assegnava r07 a questa pagina, ma r07 e' appena andata sulla home
 *     nella sezione Esperienze: a una schermata di distanza nel menu si
 *     nota. Serviva comunque una foto SCURA per l'apertura — il velo
 *     dell'opener e' tarato su un caso peggiore chiaro — e r07 e' in
 *     piena luce. r08 e' scura, calda, e mostra il gesto di cui la
 *     pagina parla: qualcuno che si prende cura di qualcuno.
 *   FASCIA r05 (il cairn, una pietra alla volta). Non e' una scelta di
 *     ripiego: e' l'immagine letterale di «ogni passo serve a costruire
 *     il successivo», e sta subito dopo la sezione dei quattro tempi.
 *     Entrambe stanno sulla landing prelaunch degli operatori, che e'
 *     un altro imbuto: nessuna delle due e' su una pagina adiacente a
 *     questa (Manifesto r04+r01, home r06+r07, /operatori r10).
 *
 * I MOVIMENTI, E CHE FONDO HANNO.
 *   APERTURA  r08 col velo: occhiello, il titolo, e la domanda in
 *             corsivo oro sotto il filo. Nient'altro: la domanda deve
 *             restare sola.
 *   MOV. 1    sabbia — la distanza. I due capoversi "ogni giorno" sono
 *             paralleli e stanno affiancati: sono i due lati che non si
 *             toccano. Poi un filo d'oro che attraversa TUTTA la
 *             larghezza fra le due colonne, e sopra quel filo cadono le
 *             tre righe che chiudono ("Non come una piattaforma. / Come
 *             un ponte."). Il ponte e' disegnato, non solo detto.
 *   MOV. 2    bianco + la foto vera a mezza pagina. In fondo alla
 *             colonna le due righe "Da una parte… / Dall'altra…" sono
 *             allineate a bordi opposti, e quello che le ricuce e' la
 *             riga in corpo grande: "nel punto in cui questi due mondi
 *             si incontrano".
 *   MOV. 3    VERDE, l'ancora tonale — il lungo periodo. I quattro
 *             tempi sono una linea del tempo in quattro colonne, con il
 *             nodo in oro e il segmento che si fa piu' netto a ogni
 *             passo: si legge come una progressione e non come un
 *             elenco. Numerati 01-04 perche' qui l'ordine E' il
 *             contenuto.
 *   FASCIA    r05 a tutta larghezza e MUTA: il respiro. Senza testo
 *             sopra non serve nessun velo, e la fotografia resta alla
 *             sua luce.
 *   MOV. 4    crema — i principi, quattro schede bianche. NON numerate:
 *             "alcuni principi semplici" non sono una classifica, e
 *             numerarli avrebbe copiato i principi del Manifesto, che
 *             e' la pagina accanto.
 *   MOV. 5    sabbia — le quattro righe di chi costruira' Aurya, in
 *             scala: ogni riga entra dopo un segmento d'oro piu' lungo
 *             del precedente, cosi' la lista si accumula invece di
 *             elencare. In fondo le due porte.
 *
 * ALTERNANZA DEI FONDI: foto scura → sabbia → bianco+foto → VERDE →
 * foto a tutta larghezza → crema → sabbia. Due sezioni adiacenti non
 * hanno mai lo stesso fondo.
 *
 * NIENTE MovementIndex (divieto del founder): il percorso di lettura lo
 * fanno i fondi che si alternano e la fascia a meta' strada.
 *
 * CONTRASTI. L'unico testo sopra una fotografia e' quello
 * dell'apertura, e non e' stato sperato: composti i due strati di velo
 * del PhotoOpener sui pixel veri di r08, nel rettangolo che il testo
 * occupa davvero, il caso PEGGIORE e' 11,12:1 a 1440 e 11,20:1 a 390
 * per il crema #f6f2e8; 7,24:1 e 7,29:1 per l'oro chiaro #d6c49a della
 * domanda. Minimo AA: 4,5:1 corpo, 3:1 display ≥24px. Tutto il resto
 * della pagina sta su fondi pieni, quindi i rapporti sono fissi:
 *   crema #f6f2e8 su salvia #2f5749 ................ 7,28:1
 *   crema al 90% su salvia ......................... 6,26:1
 *   oro chiaro #d6c49a su salvia (numeri, nodi) .... 4,74:1
 *   foreground #212c28 su crema/bianco (titoli) .... 13,6:1 / 14,5:1
 *   foreground all'85% su sabbia (i perni display) . 7,9:1
 *   foreground al 70-80% (Lede) .................... 5,4:1 - 6,8:1
 *   occhiello oro #7d6a3a su bianco ................ 5,24:1
 *   verde #2f5749 della CTA piena sulla sabbia ..... 8,0:1
 *
 * MOVIMENTO: solo la dissolvenza d'ingresso del kit, spenta da
 * prefers-reduced-motion. Le fotografie sotto la piega sono `lazy` e
 * `decoding="async"`; l'apertura no, perche' e' il primo pixel utile.
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import MarketplaceShell from '../storefront/components/MarketplaceShell';
import useSeoMeta from '../storefront/lib/useSeoMeta';
import { BRAND_EMAIL } from '../../config/brand';
import {
  Section, DisplayTitle, Lede, EditorialCta,
  PhotoOpener, PhotoBand, PhotoSplit,
} from '../../components/editorial';

/* Le tre fotografie della pagina. Il perche' di ciascuna sta in testa. */
const OPENER_PHOTO = '/media/prelaunch/r08.jpg';   // le mani di chi cura
const FOUNDERS_PHOTO = '/media/chisiamo-aurya.jpg'; // l'unica foto nostra
const BAND_PHOTO = '/media/prelaunch/r05.jpg';      // il cairn

/* Il segmento che precede ogni riga del movimento 5 si allunga: e' la
   scala, e le classi devono restare letterali perche' Tailwind legge il
   sorgente, non le stringhe composte a runtime. */
const LADDER_RULE = [
  'w-5 sm:w-8',
  'w-9 sm:w-16',
  'w-14 sm:w-24',
  'w-[4.5rem] sm:w-32',
];

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
    // 139 caratteri: la domanda da cui parte la pagina, poi cosa ci si trova.
    description: t('aboutPage.seoDesc', { defaultValue: 'Aurya nasce da una domanda: perché è così difficile orientarsi nel mondo del benessere? Chi siamo, come lavoriamo e cosa stiamo costruendo.' }),
    canonicalPath: '/chi-siamo',
  });

  /* I quattro tempi del movimento 3. L'ordine e' il contenuto. */
  const steps = [
    t('aboutPage.step1', { defaultValue: 'Prima i contenuti.' }),
    t('aboutPage.step2', { defaultValue: 'Poi le persone.' }),
    t('aboutPage.step3', { defaultValue: 'Poi le esperienze.' }),
    t('aboutPage.step4', { defaultValue: 'Infine gli strumenti.' }),
  ];

  /* I quattro principi: titolo e riga che lo spiega. Nessun numero. */
  const principles = [
    {
      title: t('aboutPage.p1Title', { defaultValue: 'Ascoltiamo prima di costruire.' }),
      body: t('aboutPage.p1Body', { defaultValue: 'Preferiamo conoscere le persone prima di progettare strumenti per loro.' }),
    },
    {
      title: t('aboutPage.p2Title', { defaultValue: 'La qualità viene prima della velocità.' }),
      body: t('aboutPage.p2Body', { defaultValue: 'Ci interessa costruire qualcosa che duri, non crescere a tutti i costi.' }),
    },
    {
      title: t('aboutPage.p3Title', { defaultValue: 'Le relazioni vengono prima della tecnologia.' }),
      body: t('aboutPage.p3Body', { defaultValue: 'La tecnologia deve aiutare le persone a incontrarsi. Mai sostituire quell’incontro.' }),
    },
    {
      title: t('aboutPage.p4Title', { defaultValue: 'Continuiamo a imparare.' }),
      body: t('aboutPage.p4Body', { defaultValue: 'Aurya non nasce con tutte le risposte. Nasce con la curiosità di continuare a fare domande.' }),
    },
  ];

  /* Chi fara' crescere Aurya. Non e' un elenco di funzioni: e' un
     elenco di persone, e per questo si accumula invece di enumerare. */
  const who = [
    t('aboutPage.who1', { defaultValue: 'Chi leggerà il Magazine.' }),
    t('aboutPage.who2', { defaultValue: 'Chi entrerà nella rete.' }),
    t('aboutPage.who3', { defaultValue: 'Chi parteciperà a un’esperienza.' }),
    t('aboutPage.who4', { defaultValue: 'Chi ci aiuterà a migliorare ciò che ancora non funziona.' }),
  ];

  return (
    <MarketplaceShell noSearch>
      <div className="bg-background">

        {/* ── APERTURA — la domanda, dentro la fotografia ──────────
            L'h1 e' la frase del founder; la domanda vera gli sta sotto,
            in corsivo e in oro chiaro, separata da un filo. E' l'unica
            cosa che deve restare nella prima schermata: chi arriva qui
            deve capire subito che la pagina parte da un problema e non
            da una presentazione. I capoversi che spiegano la domanda
            NON stanno sulla foto — sopra un'immagine si regge un
            titolo, non un ragionamento — e aprono il movimento 1. */}
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
            {t('aboutPage.heroTitle', { defaultValue: 'Tutto è iniziato da una domanda.' })}
          </DisplayTitle>
          <div aria-hidden className="gold-rule mt-8 max-w-[9rem]" />
          <p className="mt-8 max-w-[26ch] font-display text-balance text-[1.3rem] italic
                        leading-snug text-[#d6c49a] text-hero-shadow sm:text-[1.6rem] lg:text-[1.9rem]">
            {t('aboutPage.heroQuestion', { defaultValue: 'Perché è così difficile orientarsi nel mondo del benessere?' })}
          </p>
        </PhotoOpener>

        {/* ── 1. LA DISTANZA — sabbia ──────────────────────────────
            I due capoversi sono la stessa scena vista da due lati (chi
            cerca / chi offre) e per questo stanno affiancati, non uno
            sotto l'altro: la distanza di cui parlano si vede nel vuoto
            che li separa. Il filo d'oro attraversa tutta la larghezza
            proprio sopra le tre righe finali, che sono la risposta:
            quello che unisce le due colonne e' letteralmente disegnato
            fra le due colonne. La sezione non ha un titolo perche' non
            e' un capitolo nuovo: e' il seguito dell'apertura. */}
        <Section tone="sand" rhythm="screen" width="max-w-3xl">
          <div data-testid="cs-distance">
            <div className="grid gap-7 sm:gap-10 lg:grid-cols-2">
              <Lede size="body">
                {t('aboutPage.heroP1', { defaultValue: 'Ogni giorno incontriamo persone che cercano un professionista, una pratica o un’esperienza che possa aiutarle a stare meglio.' })}
              </Lede>
              <Lede size="body">
                {t('aboutPage.heroP2', { defaultValue: 'E ogni giorno incontriamo professionisti che dedicano tempo, studio ed energia al proprio lavoro, ma fanno fatica a raccontarlo online in modo autentico.' })}
              </Lede>
            </div>
            <div aria-hidden className="gold-rule mt-12 sm:mt-14" />
            <Lede size="lead" className="mt-10">
              {t('aboutPage.bridge1', { defaultValue: 'Da questa distanza è nata Aurya.' })}
            </Lede>
            <p className="mt-7 max-w-[26ch] font-display text-balance text-[1.5rem] font-medium
                          leading-[1.22] tracking-[-0.015em] sm:text-[1.9rem] lg:text-[2.1rem]">
              <span className="block text-foreground/70">
                {t('aboutPage.bridge2', { defaultValue: 'Non come una piattaforma.' })}
              </span>
              <span className="block text-foreground">
                {t('aboutPage.bridge3', { defaultValue: 'Come un ponte.' })}
              </span>
            </p>
          </div>
        </Section>

        {/* ── 2. DUE PERCORSI — bianco, con la foto vera ───────────
            Qui, e solo qui, la pagina mostra le due persone: il titolo
            e' la tesi ("una stessa visione") e le due biografie stanno
            sotto come prova, ciascuna aperta dal suo filo d'oro. La
            fotografia occupa mezza pagina fino al bordo dello schermo e
            non e' velata: il testo le sta accanto, non sopra.
            Le due righe che chiudono sono allineate a bordi opposti —
            "Da una parte…" a sinistra, "Dall'altra…" a destra — e sotto
            il filo la riga in corpo grande le ricuce. E' il "punto in
            cui i due mondi si incontrano" fatto con l'impaginazione. */}
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
            {t('aboutPage.pathsTitle', { defaultValue: 'Due percorsi, una stessa visione.' })}
          </DisplayTitle>
          <Lede size="lead" className="mt-6">
            {t('aboutPage.pathsLead', { defaultValue: 'Aurya nasce dall’incontro tra due esperienze molto diverse.' })}
          </Lede>

          <div className="mt-10 space-y-9 sm:mt-12 sm:space-y-10">
            <div>
              <div aria-hidden className="gold-rule max-w-[5rem]" />
              <p className="mt-5 font-display text-balance text-[1.2rem] leading-[1.3]
                            tracking-[-0.01em] text-foreground sm:text-[1.35rem]">
                {t('aboutPage.pathsValentina1', { defaultValue: 'Valentina vive il mondo del benessere dall’interno.' })}
              </p>
              <Lede size="body" className="mt-3">
                {t('aboutPage.pathsValentina2', { defaultValue: 'Ogni giorno accompagna persone nel loro percorso di crescita attraverso Reiki, pratiche energetiche e strumenti di consapevolezza.' })}
              </Lede>
            </div>
            <div>
              <div aria-hidden className="gold-rule max-w-[5rem]" />
              <p className="mt-5 font-display text-balance text-[1.2rem] leading-[1.3]
                            tracking-[-0.01em] text-foreground sm:text-[1.35rem]">
                {t('aboutPage.pathsDavide1', { defaultValue: 'Davide progetta prodotti digitali e da anni osserva come la tecnologia possa semplificare il lavoro delle persone senza sostituire le relazioni.' })}
              </p>
            </div>
          </div>

          <div className="mt-12 sm:mt-14">
            <p className="font-display text-[1.15rem] leading-snug text-foreground/85 sm:text-[1.3rem]">
              {t('aboutPage.pathsClose1', { defaultValue: 'Da una parte il contatto umano.' })}
            </p>
            <p className="mt-2 text-right font-display text-[1.15rem] leading-snug text-foreground/85 sm:text-[1.3rem]">
              {t('aboutPage.pathsClose2', { defaultValue: 'Dall’altra la progettazione digitale.' })}
            </p>
            <div aria-hidden className="gold-rule mt-6" />
            <p className="mt-6 max-w-[26ch] font-display text-balance text-[1.4rem] font-medium
                          leading-[1.22] tracking-[-0.015em] sm:text-[1.75rem]">
              {t('aboutPage.pathsClose3', { defaultValue: 'Aurya nasce nel punto in cui questi due mondi si incontrano.' })}
            </p>
          </div>
        </PhotoSplit>

        {/* ── 3. LUNGO PERIODO — l'ancora verde ────────────────────
            E' il movimento che risponde meglio alla domanda del founder:
            dichiarare in anticipo l'ordine dei passi e' l'unica promessa
            che si puo' verificare. Per questo prende il fondo piu' forte
            della pagina e il titolo piu' grande.
            La coppia negazione/affermazione sta in due righe di corpo,
            poi "partire lentamente" passa al corpo display e fa da
            perno. I quattro tempi sono una linea del tempo: nodo in oro,
            numero, frase, e il segmento che li unisce si fa piu' netto a
            ogni passo — la progressione si vede prima di leggerla. Su
            telefono le quattro colonne diventano quattro gradini. */}
        <Section tone="sage" rhythm="none" width="max-w-4xl"
                 labelledBy="cs-long-title"
                 innerClassName="py-24 sm:py-32 lg:py-36">
          <div data-testid="cs-long">
            <DisplayTitle as="h2" id="cs-long-title" size="section" measure="title"
                          className="text-[2.1rem] sm:text-[2.9rem] lg:text-[3.4rem] lg:leading-[1.06]">
              {t('aboutPage.longTitle', { defaultValue: 'Più che una startup, un progetto di lungo periodo.' })}
            </DisplayTitle>
            <Lede size="body" tone="inherit" className="mt-8 opacity-90">
              {t('aboutPage.longP1', { defaultValue: 'Non abbiamo creato Aurya per lanciare una piattaforma.' })}
            </Lede>
            <Lede size="body" tone="inherit" className="mt-4 opacity-90">
              {t('aboutPage.longP2', { defaultValue: 'L’abbiamo creata per costruire un luogo che continui ad avere valore anche tra dieci anni.' })}
            </Lede>
            <div aria-hidden className="gold-rule mt-10 max-w-[10rem]" />
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

            {/* OF1 — l'azione a meta' strada. Prima di questa, la prima
                cosa che un lettore poteva FARE cadeva al 91% della
                pagina: chi si convinceva qui doveva scorrere altri tre
                schermi per trovare una porta, e in mezzo non c'era
                niente da fare. Sta esattamente dopo la scala dei
                quattro tempi perche' il primo gradino e' "prima i
                contenuti": il modo piu' onesto di provare che la scala
                e' vera e' far vedere il gradino su cui siamo adesso. */}
            <p className="mt-10 sm:mt-12">
              <EditorialCta to="/blog" variant="light" data-testid="cs-cta-mid">
                {t('aboutPage.midCta', { defaultValue: 'Guarda il primo passo' })}
              </EditorialCta>
            </p>
          </div>
        </Section>

        {/* ── LA FASCIA — il respiro, e il commento alla scala ─────
            Il cairn a tutta larghezza e senza una parola sopra. Sta
            subito dopo "ogni passo serve a costruire il successivo"
            perche' e' la stessa frase detta con una fotografia, ed e'
            l'unico punto della pagina in cui non c'e' niente da
            leggere. Il ritaglio e' basso (57%) perche' la fascia e'
            molto piu' larga che alta: preso a meta' altezza il cairn
            perderebbe la base, e una pila di pietre senza la pietra di
            sotto e' esattamente il contrario di quello che dice. */}
        <PhotoBand image={BAND_PHOTO} focus="50% 57%" />

        {/* ── 4. COME LAVORIAMO — crema, quattro schede ────────────
            I principi sono la parte contestabile della pagina: scritti,
            quindi verificabili. Quattro schede bianche invece di quattro
            capoversi, perche' un principio deve poter essere guardato
            uno alla volta.
            NON sono numerati, per due motivi: il testo dice "alcuni
            principi semplici" e non una classifica, e i principi
            numerati sono gia' il blocco piu' riconoscibile del
            Manifesto, che e' la pagina accanto. Filo d'oro e basta. */}
        <Section tone="cream" rhythm="screen" width="max-w-5xl"
                 labelledBy="cs-how-title">
          <div data-testid="cs-how">
            <div className="max-w-2xl">
              <DisplayTitle as="h2" id="cs-how-title" size="section" measure="title">
                {t('aboutPage.howTitle', { defaultValue: 'Come lavoriamo.' })}
              </DisplayTitle>
              <Lede size="lead" className="mt-6">
                {t('aboutPage.howLead', { defaultValue: 'Ogni scelta che prendiamo parte da alcuni principi semplici.' })}
              </Lede>
            </div>
            <ul className="mt-12 grid list-none gap-6 p-0 sm:mt-14 sm:grid-cols-2 sm:gap-7">
              {principles.map((p) => (
                <li key={p.title}
                    className="rounded-[1.5rem] bg-white px-7 py-8 ring-1 ring-[#1e2f28]/[0.07]
                               shadow-[0_1px_2px_rgba(30,47,40,0.04),0_18px_40px_-24px_rgba(30,47,40,0.28)]
                               sm:px-8 sm:py-9">
                  <div aria-hidden className="gold-rule max-w-[4rem]" />
                  <p className="mt-6 font-display text-balance text-[1.25rem] font-medium
                                leading-[1.22] tracking-[-0.015em] text-foreground sm:text-[1.4rem]">
                    {p.title}
                  </p>
                  <Lede size="body" className="mt-4">
                    {p.body}
                  </Lede>
                </li>
              ))}
            </ul>
          </div>
        </Section>

        {/* ── 5. INSIEME — sabbia, la scala e le due porte ─────────
            Le quattro righe non sono un elenco di funzioni: sono le
            persone da cui dipende l'esito, ed e' l'ultima ragione per
            fidarsi (nessuno promette di farcela da solo). Per questo
            ognuna entra dopo un segmento d'oro piu' lungo del
            precedente: la riga si sposta a destra e la lista si accumula
            invece di enumerare. Sotto, la frase che chiude tutta la
            pagina e le due porte: il Magazine (che oggi e' la cosa che
            esiste davvero) prende l'unica azione piena della pagina,
            candidarsi resta un invito discreto.
            L'indirizzo del Magazine e' /blog: /magazine e' solo un
            rimando, e mandare l'unica azione forte su una redirezione e'
            il modo piu' rapido di perdere un clic. "Sei un
            professionista?" porta a /entra-nella-rete e non a
            /operatori: chi legge questa domanda deve ancora candidarsi,
            mentre /operatori e' la pagina di chi e' gia' stato
            raccontato. */}
        <Section tone="sand" rhythm="screen" width="max-w-3xl"
                 labelledBy="cs-together-title">
          <div data-testid="cs-together">
            <DisplayTitle as="h2" id="cs-together-title" size="section" measure="title">
              {t('aboutPage.togetherTitle', { defaultValue: 'Stiamo costruendo questo insieme.' })}
            </DisplayTitle>
            <Lede size="lead" className="mt-6">
              {t('aboutPage.togetherLead', { defaultValue: 'Aurya crescerà grazie alle persone che sceglieranno di farne parte.' })}
            </Lede>

            <ul className="mt-11 list-none space-y-4 p-0 sm:mt-12 sm:space-y-5">
              {who.map((w, i) => (
                <li key={w} className="flex items-center gap-4 sm:gap-5">
                  <span aria-hidden
                        className={`h-px shrink-0 bg-[#7d6a3a]/45 ${LADDER_RULE[i]}`} />
                  <p className="font-display text-balance text-[1.15rem] leading-[1.3]
                                tracking-[-0.01em] text-foreground/85 sm:text-[1.35rem]">
                    {w}
                  </p>
                </li>
              ))}
            </ul>

            <p className="mt-12 max-w-[28ch] font-display text-balance text-[1.4rem] font-medium
                          leading-[1.22] tracking-[-0.015em] sm:mt-14 sm:text-[1.8rem] lg:text-[1.95rem]">
              {t('aboutPage.togetherClose', { defaultValue: 'Questo progetto esiste perché crediamo che il benessere sia qualcosa che si costruisce insieme.' })}
            </p>

            <div className="mt-10 flex flex-col items-start gap-5 sm:mt-12 sm:flex-row sm:items-center sm:gap-8">
              <EditorialCta to="/blog" variant="solid" data-testid="cs-cta-magazine">
                {t('aboutPage.ctaMagazine', { defaultValue: 'Esplora il Magazine' })}
              </EditorialCta>
              <EditorialCta to="/entra-nella-rete" variant="quiet" data-testid="cs-cta-pro">
                {t('aboutPage.ctaPro', { defaultValue: 'Sei un professionista?' })}
              </EditorialCta>
              {/* LC6 — la terza porta: la Lettera. E' la pagina dove la
                  fiducia e' al massimo (si e' appena letta la storia
                  delle due persone) e chiudeva con Magazine e rete ma
                  senza il funnel dei lettori. */}
              <EditorialCta to="/newsletter" variant="quiet" data-testid="cs-cta-letter">
                {t('aboutPage.ctaLetter', { defaultValue: 'Ricevi la Lettera' })}
              </EditorialCta>
            </div>

            {/* OF1 — la porta che mancava. Questa pagina risponde a
                "perche' fidarsi di chi costruisce Aurya": chi arriva
                in fondo convinto e NON e' un professionista non aveva
                nessun modo di scriverci (il vecchio mailto era sparito
                nella riscrittura). L'indirizzo e' scritto per esteso,
                non nascosto dietro una parola: un mailto senza client
                di posta configurato non fa niente, e un indirizzo che
                non si vede non si puo' nemmeno copiare. `select-all`
                lo prende tutto con un clic. */}
            <p className="mt-12 max-w-[46ch] text-[0.95rem] leading-relaxed text-foreground/70 sm:mt-14">
              {t('aboutPage.writeUs', { defaultValue: 'Se vuoi dirci qualcosa, scriverci è la strada più corta:' })}{' '}
              <a
                href={`mailto:${BRAND_EMAIL}`}
                className="select-all break-all font-medium text-foreground underline decoration-[#8a7440]/40 underline-offset-4 transition-colors hover:decoration-[#8a7440]"
              >
                {BRAND_EMAIL}
              </a>
            </p>
          </div>
        </Section>

      </div>
    </MarketplaceShell>
  );
}
