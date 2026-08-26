/**
 * NetworkOperatorsPage — /operatori, che da RT4 si chiama LA RETE.
 *
 * IL CAMBIO. Fino a ieri questa pagina si presentava come l'albo di chi
 * era gia' dentro ("Dietro ogni pratica c'e' una persona. Qui la puoi
 * conoscere.") e spiegava i criteri d'ingresso. Il founder l'ha
 * riscritta: la rete non e' ancora popolata, e fingere il contrario e'
 * il modo piu' veloce per bruciare la fiducia che la pagina chiede. Ora
 * dice tre cose in quest'ordine — cos'e' la rete, come crescera', cosa
 * ci troverai quando ci sara' — e chiude con due porte (candidarsi,
 * seguire il progetto). La parola d'ordine e' "la rete", non
 * "operatori": l'URL resta per non rompere i link, il titolo SEO no.
 *
 * COSA E' SPARITO, E PERCHE'. Il blocco "Come si entra" (i tre gesti:
 * andiamo a conoscere / facciamo domande scomode / firmiamo il
 * racconto) non c'e' piu' nel testo nuovo. Non e' un taglio nostro:
 * quel contenuto oggi vive sul manifesto e su /entra-nella-rete, e
 * ripeterlo qui trasformava una pagina di presentazione in un
 * regolamento. Le chiavi (nwOps.how*) sono state rimosse dal locale.
 *
 * IL MECCANISMO DELLE PERSONE RESTA. Le schede continuano ad arrivare
 * da /public/network/members: foto, nome, pratica, luogo, sigillo
 * Verificato Aurya e UNA citazione presa dall'intervista (campo
 * `quote`, esposto solo a intervista pubblicata, scelto a mano dal
 * system admin: quale frase valga la pena leggere sotto un nome lo sa
 * solo chi quella conversazione l'ha fatta). Senza citazione la scheda
 * ripiega sulla tagline; senza nessuna delle due restano il volto e il
 * nome, che sono comunque una persona.
 *
 * ── GLI STATI ─────────────────────────────────────────────────────
 *   CON PERSONE  founder 26/8, coi primi profili VERI in produzione:
 *                griglia UNICA e uniforme dal primo profilo in poi
 *                (2 → 3 → 4 colonne; schede 4/5 identiche, vedi
 *                PersonCard). Il vecchio layout a righe intere per i
 *                primi due e' morto sul campo: ritratti enormi e, con
 *                object-contain, ognuno del suo formato.
 *   SENZA        un OGGETTO: il pannello salvia dentro la sezione
 *                bianca, con il filo d'oro, l'occhiello "In arrivo",
 *                la riga del founder e la porta della Lettera. Occupa
 *                lo spazio delle schede e ne ha il peso: si legge come
 *                una scelta, non come un buco.
 * Non e' un tratteggio "placeholder" e non simula schede finte:
 * disegnare il fantasma di quello che non c'e' e' la versione
 * educata della bugia.
 *
 * ── IL DISEGNO ────────────────────────────────────────────────────
 * ALTERNANZA DEI FONDI, sempre diversa fra sezioni adiacenti:
 *   foto scura (r10) → crema → sabbia → bianco → crema → SALVIA →
 *   sabbia → fascia fotografica (r05).
 * L'apertura e' fotografica (il titolo sta DENTRO l'immagine, mai
 * sopra un fondo piatto) e il respiro a tutta larghezza e' la fascia
 * finale: e' l'unico punto in cui la pagina esce dalla sua colonna, ed
 * e' il posto giusto per la frase che il founder ha scelto come
 * chiusura.
 *
 * LE FOTO. r10 in apertura e' l'assegnazione del ciclo (DS §magazzino).
 * Per la fascia serviva una seconda immagine e il magazzino e' tutto
 * gia' impegnato altrove: r05 — il cairn, una pietra alla volta — e'
 * la scelta con la collisione piu' bassa (sulla landing vive dentro una
 * scheda piccola, qui e' una fascia da bordo a bordo: scala diversa,
 * lettura diversa) ed e' anche l'unica del magazzino che dice
 * letteralmente la tesi della pagina, cioe' costruire lentamente.
 *
 * LE EMOJI DELLA SPECIFICA (libro, foglia, busta) non sono state usate
 * come emoji: nelle quattro voci di "Cosa troverai nella rete" il segno
 * e' il filo d'oro del sito, che e' identico su ogni sistema operativo.
 *
 * CONTRASTI (minimo AA: 4,5:1 corpo, 3:1 display). NESSUNO E' STIMATO.
 * Le quattro misure sopra fotografia sono prese NEL BROWSER,
 * ricomponendo i due veli sul ritaglio vero (quello che fa
 * object-fit:cover, con la stessa object-position della pagina) e
 * leggendo il pixel piu' chiaro dentro il rettangolo che il testo
 * occupa davvero — a 1440 e a 390:
 *   apertura, crema #f6f2e8 sul velo di r10 ....... 9,21:1 / 9,35:1
 *   apertura, payoff oro #ecd9a8 sul velo di r10 .. 7,36:1 / 5,61:1
 *   fascia, display crema sul velo di r05 ......... 6,11:1 / 5,71:1
 *   fascia, corpo crema sul velo di r05 ........... 7,74:1 / 6,99:1
 * Le altre sono lette dai colori calcolati nel DOM (colore effettivo
 * dopo la catena di opacita', contro il fondo pieno che sta sotto):
 *   corpo all'80% su crema #faf8f5 ................ 7,27:1
 *   corpo all'80% su sabbia #f2ece0 ............... 6,83:1
 *   inciso al 70% su sabbia ....................... 5,01:1
 *   corpo all'80% su bianco ....................... 7,58:1
 *   invito, crema al 90% su salvia #2f5749 ........ 6,28:1
 *   pannello d'attesa, display crema su salvia .... 7,28:1
 *   pannello d'attesa, occhiello oro #d6c49a ...... 4,74:1
 * E le due delle schede, invariate dal ciclo precedente:
 *   nome pieno su bianco .......................... 14,43:1
 *   pratica e luogo al 70% su bianco .............. 5,46:1
 * L'occhiello del pannello e' il punto piu' stretto della pagina: 11px
 * in maiuscoletto spaziato, 4,74:1 contro un minimo di 4,5. E' il
 * motivo per cui il pannello e' salvia e non sabbia — sulla sabbia lo
 * stesso oro da lettura (#7d6a3a) scende a 4,47:1, cioe' sotto.
 *
 * MOVIMENTO: solo la dissolvenza d'ingresso del kit e lo zoom
 * lentissimo dei ritratti al passaggio del mouse. Entrambi spenti da
 * prefers-reduced-motion.
 */
import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import api from '../../api/client';
import MarketplaceShell from '../storefront/components/MarketplaceShell';
import useSeoMeta from '../storefront/lib/useSeoMeta';
import BrandPayoff from '../../components/BrandPayoff';
import {
  Section, DisplayTitle, Lede, PersonCard,
  EditorialCta, PhotoOpener, PhotoBand,
} from '../../components/editorial';

/* Le due fotografie della pagina. r10 e' l'assegnazione del ciclo;
   r05 e' la fascia finale (vedi testata). */
const OPENER_PHOTO = '/media/prelaunch/r10.jpg';  // mani sulla schiena, macro
const BAND_PHOTO = '/media/prelaunch/r05.jpg';    // il cairn, una pietra alla volta

/* 280 resta il tetto editoriale del system admin; in GRIGLIA pero' la
   voce si ferma prima (founder 26/8): su schede da quattro colonne una
   frase piena diventa una colonna di testo e i volti perdono il ritmo.
   Il taglio e' gentile (truncateWords, dentro PersonCard) e la frase
   intera vive sul profilo e nell'intervista. */
const QUOTE_GRID = 170;

/* La riga display che fa da perno dentro una sezione: non e' un altro
   capoverso, e' la frase su cui la sezione gira. Stesso trattamento su
   manifesto e chi siamo, per questo sta in una costante e non in tre
   copie di classi. */
const PIVOT = `font-display text-balance font-medium leading-[1.22] tracking-[-0.015em]
               text-[1.5rem] sm:text-[1.9rem] lg:text-[2.1rem]`;

export default function NetworkOperatorsPage() {
  const { t } = useTranslation('landings');
  const [members, setMembers] = useState(null);   // null = caricamento

  useSeoMeta({
    title: t('nwOps.seoTitle', { defaultValue: 'La rete Aurya | I professionisti che stiamo conoscendo' }),
    // 155 caratteri: cos'e' la rete, con che passo cresce, cosa ci
    // trovera' chi arriva. Taglio a 158.
    description: t('nwOps.seoDesc', { defaultValue: 'Stiamo costruendo una rete di professionisti del benessere, una persona alla volta. Ogni profilo racconta chi è, come lavora e perché ha scelto il benessere.' }),
    canonicalPath: '/operatori',
  });

  useEffect(() => {
    let mounted = true;
    api.get('/public/network/members')
      .then(res => { if (mounted) setMembers(res.data?.items || []); })
      .catch(() => { if (mounted) setMembers([]); });
    return () => { mounted = false; };
  }, []);

  /* La pratica arriva come slug stabile: la label la risolve l'i18n,
     come nell'aggregatore. */
  const catLabel = (slug) => (slug ? t(`categories.${slug}`, { defaultValue: slug }) : null);

  /* Le quattro voci di "Cosa troverai nella rete". Stanno in un array
     perche' sono una lista vera (<ul>) e perche' cosi' il markup della
     voce esiste UNA volta sola: quattro copie dello stesso blocco sono
     quattro posti dove sbagliare. */
  const perks = [
    {
      title: t('nwOps.what1Title', { defaultValue: 'Conoscere la sua storia' }),
      body: t('nwOps.what1Body', { defaultValue: 'Per capire il percorso che lo ha portato fin qui.' }),
    },
    {
      title: t('nwOps.what2Title', { defaultValue: 'Scoprire il suo approccio' }),
      body: t('nwOps.what2Body', { defaultValue: 'Per comprendere come lavora e a chi si rivolge.' }),
    },
    {
      title: t('nwOps.what3Title', { defaultValue: 'Leggere approfondimenti' }),
      body: t('nwOps.what3Body', { defaultValue: 'Articoli, interviste e contenuti che aiutano a conoscere meglio il suo modo di vedere il benessere.' }),
    },
    {
      title: t('nwOps.what4Title', { defaultValue: 'Trovare servizi, eventi e ritiri' }),
      body: t('nwOps.what4Body', { defaultValue: 'In un unico luogo. Senza dover cercare tra siti diversi.' }),
    },
  ];

  /* UN SOLO MODO DI MOSTRARE LE PERSONE (founder 26/8). Il layout a
     righe intere per i primi due profili e' morto in produzione: i
     ritratti a mezza colonna erano enormi, e con object-contain ogni
     foto portava il suo rapporto — la pagina sembrava fatta di formati
     diversi. Ora la griglia e' UNA, dal primo profilo in poi: schede
     uniformi (4/5, vedi PersonCard), piu' piccole e piu' fitte — 2
     colonne da tablet, 3 su schermi medi, 4 su desktop. Una persona
     sola occupa una casella della stessa griglia: e' una rete che
     cresce, non un'eccezione da impaginare. */
  const list = members || [];

  return (
    <MarketplaceShell noSearch>
      <div className="bg-background">

        {/* ── APERTURA — dentro la fotografia ──────────────────────
            Il titolo e' UNA riga sola, ed e' il nome della cosa: "La
            rete Aurya." Sopra sta il payoff di brand al posto di un
            occhiello, perche' un occhiello che dicesse "La rete" sopra
            un titolo che dice "La rete Aurya" sarebbe la stessa parola
            due volte a due centimetri di distanza.
            L'argomento (le quattro frasi del founder) non sta sulla
            foto: si legge sul chiaro, subito sotto. E' la scelta della
            landing operatori, che e' la pagina approvata, e ha una
            ragione tecnica oltre che estetica — il contrasto di un
            paragrafo lungo sopra una fotografia dipende da dove cade
            il ritaglio, quello di un titolo corto no. */}
        <PhotoOpener
          data-testid="nw-open"
          image={OPENER_PHOTO}
          focus="35% 80%"
          height="tall"
          align="left"
          width="max-w-3xl"
          labelledBy="nw-open-title"
        >
          <BrandPayoff tone="hero" size="xs" className="mb-5 sm:mb-7" />
          <DisplayTitle as="h1" id="nw-open-title" size="hero" measure="tight"
                        className="text-hero-shadow">
            {t('nwOps.title', { defaultValue: 'La rete Aurya.' })}
          </DisplayTitle>
        </PhotoOpener>

        {/* ── LA SOGLIA — che cos'e' questa rete ───────────────────
            Le quattro frasi del founder in tre gradini: la premessa,
            l'idea che si condivide, quello che ogni persona porta. La
            quarta ("Ed e' proprio da li' che vogliamo partire.") non e'
            un quarto capoverso, e' il perno: passa al corpo display,
            perche' e' la frase che gira la pagina dal dire al fare.
            La porta e' il manifesto: chi vuole sapere come la pensiamo
            prima di guardare chi c'e' dentro, esce di qui. */}
        <Section tone="cream" rhythm="flow" width="max-w-3xl">
          <div data-testid="nw-soglia">
            <Lede size="lead">
              {t('nwOps.leadP1', { defaultValue: 'Stiamo costruendo una rete di professionisti del benessere che condividono una stessa idea.' })}
            </Lede>
            <Lede size="body" className="mt-5">
              {t('nwOps.leadP2', { defaultValue: 'Che prendersi cura delle persone significhi prima di tutto ascoltarle, accompagnarle e continuare a crescere.' })}
            </Lede>
            <Lede size="body" className="mt-5">
              {t('nwOps.leadP3', { defaultValue: 'Ogni persona che entrerà nella rete porterà una storia, un percorso e un modo unico di lavorare.' })}
            </Lede>
            <div aria-hidden className="gold-rule mt-10 max-w-[10rem]" />
            <p className={`mt-9 max-w-[24ch] ${PIVOT}`}>
              {t('nwOps.leadPivot', { defaultValue: 'Ed è proprio da lì che vogliamo partire.' })}
            </p>
            <div className="mt-9">
              <EditorialCta to="/manifesto" variant="quiet" data-testid="nw-cta-vision">
                {t('nwOps.visionCta', { defaultValue: 'Conosci la nostra visione' })}
              </EditorialCta>
            </div>
          </div>
        </Section>

        {/* ── 2. UNA RETE CHE CRESCE UNA PERSONA ALLA VOLTA ────────
            Impaginato da rivista: il titolo tiene la sua colonna a
            sinistra e il ragionamento scorre a destra, cosi' la
            sezione si legge in due colpi d'occhio invece che come una
            colonna lunga il doppio. L'ultima frase si stacca
            nell'inciso col filo d'oro: non e' un altro passaggio del
            ragionamento, e' la ragione per cui il ragionamento vale. */}
        <Section tone="sand" rhythm="screen" width="max-w-5xl"
                 id="nw-cresce" labelledBy="nw-grow-title"
                 className="scroll-mt-20">
          <div data-testid="nw-grow" className="grid gap-8 lg:grid-cols-12 lg:gap-12">
            <div className="lg:col-span-5">
              <DisplayTitle as="h2" id="nw-grow-title" size="section" measure="tight"
                            className="text-[1.9rem] sm:text-[2.4rem] lg:text-[2.4rem]">
                {t('nwOps.growTitle', { defaultValue: 'Una rete che cresce una persona alla volta.' })}
              </DisplayTitle>
              <div aria-hidden className="gold-rule mt-7 max-w-[7rem]" />
            </div>
            <div className="lg:col-span-7">
              <Lede size="lead">
                {t('nwOps.growP1', { defaultValue: 'Non stiamo cercando di riempire un elenco. Preferiamo conoscere davvero ogni professionista che entra in Aurya.' })}
              </Lede>
              <Lede size="body" className="mt-5">
                {t('nwOps.growP2', { defaultValue: 'Per questo ogni persona della rete viene raccontata attraverso una conversazione vera, non un semplice modulo. Il racconto richiede tempo, e ce lo prendiamo.' })}
              </Lede>
              <div className="mt-9 border-l-2 border-[#7d6a3a]/50 pl-5 sm:pl-6">
                <Lede size="body" tone="quiet">
                  {t('nwOps.growClose', { defaultValue: 'Crediamo che sia il modo migliore per costruire qualcosa destinato a durare.' })}
                </Lede>
              </div>
            </div>
          </div>
        </Section>

        {/* ── 3. LE PRIME PERSONE ──────────────────────────────────
            Fondo bianco: e' il punto piu' luminoso della pagina, ed e'
            li' che i ritratti si staccano come oggetti. Il testo
            annuncia (la pagina cambiera', qui pubblicheremo, ogni
            profilo raccontera'), il perno lo chiude — "prima di
            scegliere una pratica, spesso scegliamo una persona" — e
            SOTTO succede quello che il testo ha appena promesso: le
            persone se ci sono, il pannello d'attesa se non ci sono.
            "Leggi l'intervista" e' un link VERO alla pagina dedicata
            (PV3), e compare solo dove l'intervista e' pubblicata. */}
        <Section tone="paper" rhythm="screen" width="max-w-6xl"
                 id="nw-persone" labelledBy="nw-people-title"
                 className="scroll-mt-20">
          <div data-testid="nw-people">
            <div className="max-w-3xl">
              <DisplayTitle as="h2" id="nw-people-title" size="section" measure="title">
                {t('nwOps.peopleTitle', { defaultValue: 'Presto potrai conoscere le prime persone della rete.' })}
              </DisplayTitle>
              <Lede size="lead" className="mt-7">
                {t('nwOps.peopleP1', { defaultValue: 'Questa pagina cambierà nel tempo. Qui pubblicheremo i primi professionisti che stanno contribuendo alla nascita di Aurya.' })}
              </Lede>
              <Lede size="body" className="mt-5">
                {t('nwOps.peopleP2', { defaultValue: 'Ogni profilo racconterà non solo cosa fa una persona, ma anche come lavora, quale percorso l’ha portata fin qui e perché ha scelto di dedicarsi al benessere.' })}
              </Lede>
              <p className={`mt-10 max-w-[26ch] ${PIVOT}`}>
                {t('nwOps.peoplePivot', { defaultValue: 'Perché prima di scegliere una pratica, spesso scegliamo una persona.' })}
              </p>
            </div>

            {members === null ? (
              /* /70 e non /60: al 60% il testo scende a 4,03:1, sotto
                 il minimo AA. Stessa soglia del tono `quiet` del kit.
                 Nessun riquadro fantasma: quanti profili arriveranno
                 non si sa, e prenotare il posto per uno che potrebbe
                 non esserci e' un salto di layout travestito. */
              <p className="mt-12 text-sm text-foreground/70" aria-live="polite">
                {t('nwOps.loading', { defaultValue: 'Un momento.' })}
              </p>
            ) : list.length === 0 ? (
              /* IL PANNELLO D'ATTESA. Occupa lo spazio delle schede e
                 ne ha il peso: superficie salvia sulla sezione bianca,
                 angoli generosi, l'aura del logo come texture. Dice
                 quello che sta succedendo e offre l'unica cosa utile
                 a chi e' arrivato fin qui per guardare le persone:
                 essere avvisato quando ci saranno. Il verde qui e'
                 legittimo anche se l'ancora tonale della pagina e' piu'
                 sotto — e' un OGGETTO dentro una sezione chiara, non
                 una seconda fascia piena. */
              <div data-testid="nw-people-soon" className="mt-14 sm:mt-16">
                <div className="aura-corner rounded-[1.75rem] bg-[#2f5749] px-7 py-14
                                text-[#f6f2e8] sm:px-12 sm:py-16 lg:px-16 lg:py-20">
                  <div aria-hidden className="gold-rule max-w-[7rem]" />
                  <p className="eyebrow eyebrow-light mt-7">
                    {t('nwOps.soonEyebrow', { defaultValue: 'In arrivo' })}
                  </p>
                  <p className={`mt-5 max-w-[22ch] ${PIVOT}`}>
                    {t('nwOps.soonTitle', { defaultValue: 'I primi profili saranno pubblicati prossimamente.' })}
                  </p>
                  <div className="mt-10">
                    <EditorialCta to="/newsletter" variant="light"
                                  data-testid="nw-soon-cta">
                      {t('nwOps.letterCta', { defaultValue: 'Ricevi la Lettera' })}
                    </EditorialCta>
                  </div>
                </div>
              </div>
            ) : (
              /* founder 26/8 — griglia unica e uniforme: 2 → 3 → 4
                 colonne. La voce in griglia si tronca prima (170) del
                 tetto editoriale (280): su una scheda da ~250px una
                 citazione lunga diventa una colonna di testo, e la
                 griglia perde il ritmo dei volti. */
              <ul className="mt-14 grid list-none gap-x-6 gap-y-12 p-0 sm:mt-16
                             sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
                {list.map(m => (
                  <li key={m.slug} data-testid="nw-person">
                    <PersonCard
                      person={{ ...m, category: catLabel(m.category) }}
                      quoteMaxChars={QUOTE_GRID}
                    />
                    {m.has_interview && (
                      <p className="mt-4">
                        <EditorialCta to={`/o/${m.slug}/intervista`} variant="quiet">
                          {t('nwOps.readInterview', { defaultValue: 'Leggi l’intervista' })}
                        </EditorialCta>
                      </p>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </Section>

        {/* ── 4. COSA TROVERAI NELLA RETE ──────────────────────────
            L'introduzione finisce con i due punti e le quattro voci la
            completano ("...dove potrai: conoscere, scoprire, leggere,
            trovare"): sono una lista vera, quindi <ul>, e restano
            infiniti come li ha scritti il founder.
            La specifica aveva tre emoji (libro, foglia, busta). Qui il
            segno e' il filo d'oro del sito: non cambia forma fra iOS,
            Android e Windows, e non compete col titolo che ha accanto. */}
        <Section tone="cream" rhythm="screen" width="max-w-5xl"
                 id="nw-cosa" labelledBy="nw-what-title"
                 className="scroll-mt-20">
          <div data-testid="nw-what">
            <div className="max-w-3xl">
              <DisplayTitle as="h2" id="nw-what-title" size="section" measure="title">
                {t('nwOps.whatTitle', { defaultValue: 'Cosa troverai nella rete.' })}
              </DisplayTitle>
              <Lede size="lead" className="mt-7">
                {t('nwOps.whatIntro', { defaultValue: 'Quando inizierà a crescere, ogni professionista avrà uno spazio dedicato dove potrai:' })}
              </Lede>
            </div>
            <ul className="mt-12 grid list-none gap-9 p-0 sm:mt-14 sm:gap-x-12 sm:gap-y-12 lg:grid-cols-2">
              {perks.map(p => (
                <li key={p.title}>
                  <div aria-hidden className="gold-rule" />
                  <p className="mt-5 font-display text-balance text-[1.35rem] font-medium
                                leading-[1.24] tracking-[-0.015em] sm:text-[1.6rem]">
                    {p.title}
                  </p>
                  <Lede size="body" className="mt-3">{p.body}</Lede>
                </li>
              ))}
            </ul>
          </div>
        </Section>

        {/* ── 5. SEI UN PROFESSIONISTA? — l'ancora verde ───────────
            L'unica sezione tonale piena della pagina, e l'unica in cui
            si chiede qualcosa a qualcuno. L'indirizzo e'
            /entra-nella-rete e non questa pagina: qui si guarda chi e'
            gia' stato raccontato, li' si comincia a raccontarsi. */}
        <Section tone="sage" rhythm="screen" width="max-w-3xl"
                 id="nw-invito" labelledBy="nw-pro-title"
                 className="scroll-mt-20">
          <div data-testid="nw-join">
            <DisplayTitle as="h2" id="nw-pro-title" size="section" measure="tight"
                          className="text-[2.2rem] sm:text-[3rem] lg:text-[3.5rem]">
              {t('nwOps.proTitle', { defaultValue: 'Sei un professionista?' })}
            </DisplayTitle>
            <Lede size="lead" tone="inherit" className="mt-7 opacity-90">
              {t('nwOps.proP1', { defaultValue: 'Stiamo iniziando a conoscere le prime persone che entreranno nella rete.' })}
            </Lede>
            <Lede size="body" tone="inherit" className="mt-5 opacity-90">
              {t('nwOps.proP2', { defaultValue: 'Se condividi il nostro modo di vedere il benessere e senti che il tuo lavoro merita di essere raccontato con cura, ci piacerebbe conoscerti.' })}
            </Lede>
            {/* OF1 — passa da discreta a PIENA. Era l'unica pagina del
                sito senza una sola azione piena: tutto invitava allo
                stesso modo, quindi niente invitava davvero. Questa e'
                l'obiettivo di conversione della pagina e ora si vede
                che lo e'. `solid` sul salvia usa il pieno crema, che e'
                il contrasto piu' alto disponibile su questo fondo. */}
            <div className="mt-10">
              <EditorialCta to="/entra-nella-rete" variant="solid" tone="dark"
                            data-testid="nw-join-cta">
                {t('nwOps.joinCta', { defaultValue: 'Entra nella rete' })}
              </EditorialCta>
            </div>
          </div>
        </Section>

        {/* ── 6. VUOI SEGUIRE IL PROGETTO? ─────────────────────────
            Due colonne come la sezione 2, cosi' la coda della pagina
            non diventa una fila di blocchi centrati tutti uguali. E'
            la porta di chi non e' un professionista e non ha ancora
            nessuno da guardare: l'unica cosa che possiamo offrirgli
            oggi e' di essere avvisato. */}
        <Section tone="sand" rhythm="screen" width="max-w-5xl"
                 id="nw-segui" labelledBy="nw-follow-title"
                 className="scroll-mt-20">
          <div data-testid="nw-follow" className="grid gap-8 lg:grid-cols-12 lg:gap-12">
            <div className="lg:col-span-5">
              <DisplayTitle as="h2" id="nw-follow-title" size="section" measure="tight"
                            className="text-[1.9rem] sm:text-[2.4rem] lg:text-[2.4rem]">
                {t('nwOps.followTitle', { defaultValue: 'Vuoi seguire il progetto?' })}
              </DisplayTitle>
              <div aria-hidden className="gold-rule mt-7 max-w-[7rem]" />
            </div>
            <div className="lg:col-span-7">
              <Lede size="lead">
                {t('nwOps.followP1', { defaultValue: 'La rete crescerà lentamente. Racconteremo ogni nuova persona attraverso il Magazine e la Lettera di Aurya.' })}
              </Lede>
              <Lede size="body" className="mt-5">
                {t('nwOps.followP2', { defaultValue: 'Se vuoi seguirne l’evoluzione puoi iscriverti gratuitamente.' })}
              </Lede>
              <div className="mt-9">
                <EditorialCta to="/newsletter" variant="quiet"
                              data-testid="nw-letter-cta">
                  {t('nwOps.letterCta', { defaultValue: 'Ricevi la Lettera' })}
                </EditorialCta>
              </div>
            </div>
          </div>
        </Section>

        {/* ── LA CHIUSURA — il respiro a tutta larghezza ───────────
            L'unico momento in cui la pagina esce dalla sua colonna, ed
            e' l'ultimo: r05 da bordo a bordo, il cairn che si costruisce
            una pietra alla volta, e sopra le due righe che il founder ha
            scelto come congedo. Le altre due frasi stanno sotto, in
            corpo di lettura: sono la promessa, non il titolo. */}
        <PhotoBand image={BAND_PHOTO} focus="50% 45%" width="max-w-3xl"
                   data-testid="nw-close">
          <p className="max-w-[24ch] font-display text-balance text-[1.75rem] font-medium
                        leading-[1.16] tracking-[-0.015em] text-hero-shadow
                        sm:text-[2.4rem] lg:text-[3rem]">
            <span className="block">
              {t('nwOps.closeLine1', { defaultValue: 'Le reti non nascono dai numeri.' })}
            </span>
            <span className="block">
              {t('nwOps.closeLine2', { defaultValue: 'Nascono dalle persone.' })}
            </span>
          </p>
          <p className="mt-8 max-w-[46ch] text-base leading-relaxed text-hero-shadow
                        sm:text-lg">
            {t('nwOps.closeBody', { defaultValue: 'Ogni nuovo ingresso sarà un passo in più verso il progetto che immaginiamo. E noi abbiamo intenzione di prenderci il tempo necessario per costruirlo bene.' })}
          </p>
        </PhotoBand>

      </div>
    </MarketplaceShell>
  );
}
