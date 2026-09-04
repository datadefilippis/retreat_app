/**
 * NetworkHomePage — la home della fase rete.
 *
 * HP5 (2/8/2026) — IL COPY E' NUOVO, SCRITTO DAL FOUNDER, e con lui
 * cambia la scaletta: sei battute invece di sette. Sparisce la sezione
 * "Stiamo costruendo una rete, non una directory" (quello che diceva ora
 * sta dentro la seconda battuta e dentro la colonna Professionisti), e
 * la sezione degli operatori si prende il posto e la fotografia che
 * erano suoi.
 *
 *   1. HERO          la convinzione      video del tramonto, due CTA
 *   2. CAPIRE        la mappa            tre colonne (Magazine / Professionisti / Esperienze)
 *   3. PERCHE'       la ragione          ancora verde, CTA manifesto
 *   4. DAL MAGAZINE  la prova            gated sui dati
 *   5. OPERATORI     l'invito            foto/testo, due CTA
 *   6. LA LETTERA    restare             fascia fotografica, newsletter
 *
 * IL TESTO E' PIU' LUNGO DI PRIMA e arriva quasi tutto in frasi corte
 * elencate una sotto l'altra. Messo cosi' com'e' in colonna sarebbe un
 * muro; il lavoro di questa onda e' dargli RITMO, cioe' decidere quali
 * frasi vanno insieme, quali si affiancano e quali prendono corpo
 * display. Nessuna parola e' cambiata: solo la tipografia e la forma.
 *   HERO      tre capoversi in gerarchia calante: la constatazione in
 *             corpo lead, poi cosa e' Aurya e come lo fa affiancati su
 *             desktop (in colonna resterebbero nove righe di testo
 *             sopra un video, cioe' un muro luminoso).
 *   CAPIRE    quattro righe in due coppie: le prime due dicono cos'e' il
 *             benessere (corpo lead), le altre due cos'e' Aurya (corpo).
 *             Stanno accanto al titolo, non sotto: e' una masthead.
 *   PERCHE'   sei righe in tre movimenti. Le due centrali ("Trovare un
 *             professionista e' semplice" / "Scegliere quello giusto e'
 *             cio' che conta") sono un'ANTITESI: prendono il corpo display,
 *             una per riga, separate da un filo. E' il perno della
 *             pagina. Le ultime tre si affiancano: la convinzione da una
 *             parte, la decisione dall'altra.
 *   OPERATORI le prime tre righe sono frammenti di una stessa frase
 *             ("Ogni professionista ha una storia. Un modo di lavorare.
 *             Un motivo...") e vanno lette come un crescendo: display
 *             serif, una per riga, interlinea stretta. Poi il capoverso
 *             lungo in corpo di lettura e la riga d'invito.
 *   LETTERA   la stessa cosa in verticale: apertura, i tre "una..."
 *             incolonnati al centro, la chiusa in due righe piu' quiete.
 *
 * L'HERO IN MOVIMENTO NON SI TOCCA (decisione del founder, HP4): resta
 * il video del tramonto con poster immediato e video montato dopo il
 * `load` (HeroVideo), restano i due veli misurati. Cambiano solo le
 * parole dentro, che ora sono una frase-titolo e tre capoversi.
 *
 * ALTERNANZA DEI FONDI: VIDEO scuro → sabbia → VERDE → bianco → crema
 * +foto → FOTO a tutta larghezza. Due sezioni adiacenti non hanno mai
 * lo stesso fondo, e l'unica ancora verde piena sta a meta' esatta
 * della lettura (grammatica DS: massimo due, mai adiacenti).
 *
 * CONTRASTI MISURATI (minimo AA: 4,5:1 corpo, 3:1 display ≥24px). Le
 * misure sono LETTE sui pixel che Chrome ha davvero disegnato: si
 * nasconde il testo (visibility, quindi il layout non si muove), si
 * cattura la finestra, si rilegge il riquadro che il testo occupava e
 * si tiene il pixel PIU' CHIARO, cioe' il caso peggiore. I due numeri
 * sono 1440px e 390px.
 *   hero, titolo crema #f6f2e8 sul video velato ....... 7,79 / 7,01
 *   hero, capoverso lead crema ........................ 7,67 / 7,00
 *   hero, capoversi 2-3 crema al 90% .................. 7,94 / 5,79
 *   hero, superficie crema del bottone sul fondo ..... 10,13 / 11,22
 *   hero, CTA secondaria crema ....................... 15,72 / 15,77
 *   lettera, titolo crema su hero-destination ......... 5,67 / 5,20
 *   lettera, apertura lead crema ...................... 8,07 / 7,06
 *   lettera, le tre righe display crema .............. 10,06 / 7,76
 *   lettera, chiusa crema al 90% ...................... 8,15 / 6,10
 *   lettera, superficie crema del bottone sul fondo ... 7,44 / 5,88
 *   lettera, etichetta #1c2e27 dentro il bottone crema  12,78 (fisso)
 * (i numeri dell'hero dipendono dal fotogramma su cui cade la cattura:
 * il velo pero' e' tarato in HP4 sul fotogramma PIU' CHIARO, il sole
 * bruciato, dove il caso peggiore misurato resta 5,80:1 sull'occhiello
 * e 6,64:1 sul corpo. Quello e' il pavimento, non questi.)
 * Sui fondi pieni valgono le misure gia' note del kit: crema su salvia
 * 7,28:1, crema al 90% su salvia 6,26:1, occhiello oro #7d6a3a su
 * crema 4,97:1, corpo foreground/80 su sabbia 8,12:1.
 *
 * MOVIMENTO. Solo la dissolvenza d'ingresso del kit, il sollevamento
 * delle schede e il segno "scendi" sotto l'hero: tutti spenti da
 * prefers-reduced-motion. Nessuna parallasse.
 *
 * In fase marketplace questa home cede il posto alla directory
 * (HomeGate → RetreatsCalendarPage): quella e' un'altra pagina e non
 * viene toccata qui.
 */
import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ChevronDown } from 'lucide-react';
import api from '../../api/client';
import MarketplaceShell from '../storefront/components/MarketplaceShell';
import useSeoMeta from '../storefront/lib/useSeoMeta';
import BrandPayoff from '../../components/BrandPayoff';
import HeroVideo from '../../components/HeroVideo';
import LeadForm from '../prelaunch/LeadForm';
import {
  Section, DisplayTitle, TitleLine, Lede, ArticleCard, PillarCard, EditorialCta,
  PhotoBand, PhotoSplit,
} from '../../components/editorial';

/* NOTA TECNICA — la rotta del Magazine.
   Il testo del founder scrive /magazine. Quella rotta esiste ma e' un
   rimando a /blog (App.js), e /blog e' la canonica: sta in sitemap ed
   e' gia' stata spinta con IndexNow. Da qui linkiamo la canonica,
   perche' passare dal redirect costa un rimbalzo all'utente e diluisce
   il segnale interno verso l'URL che i motori conoscono. L'etichetta
   che il visitatore legge resta "Magazine". */
const MAGAZINE_PATH = '/blog';

/* NOTA TECNICA — i due indirizzi della rete.
   Il founder scrive "Scopri la rete → /rete" e "Entra nella rete →
   /operatori": da noi i due nomi sono invertiti. /operatori e' la
   pagina dei MEMBRI (li' si scopre la rete), /entra-nella-rete e' la
   landing per candidarsi. Qui si segue l'intenzione, non la lettera. */
const NETWORK_PATH = '/operatori';        // scopri la rete (i membri)
const JOIN_PATH = '/entra-nella-rete';    // entra nella rete (candidarsi)

/* il verde di brand del kit editoriale: accento del form della Lettera */
const SAGE = '#2f5749';

/* Il segno in testa alle tre colonne. 'plain' = nessun segno: la
   fotografia in testa alla scheda fa gia' quel mestiere. Le emoji che
   il founder ha messo accanto ai tre titoli (libro, persone, foglia)
   NON si stampano: sarebbero un secondo segno a tre centimetri dal
   primo, e per giunta l'unico elemento della pagina disegnato dal
   sistema operativo invece che da noi. Se un giorno servisse un segno,
   l'alternativa dentro la grammatica del sito e' 'numeral' (01/02/03 in
   display serif). Le motivazioni stanno per esteso nella NOTA DIREZIONE
   CREATIVA di editorial/PillarCard.jsx. */
const PILLAR_VARIANT = 'plain';

/** quanti articoli in vetrina: uno grande, due piccoli */
const MAX_ARTICLES = 3;

/* ── L'APERTURA IN MOVIMENTO (HP4, confermata in HP5) ──────────────
   Il tramonto di Aurya: lo stesso asset dello splash di prelancio,
   cioe' la firma visiva del brand. Sul primo rendering pesa solo il
   poster (47 KB); il video lo monta HeroVideo dopo il `load`. */
const HERO_VIDEO = '/media/aurya-hero.mp4';
const HERO_POSTER = '/media/aurya-hero-poster.jpg';

/* ── LE FOTOGRAFIE ────────────────────────────────────────────────
   Cinque, piu' il video e le copertine degli articoli. Nessun asset
   nuovo. Accanto a ciascuna, il perche' sta li' e non altrove.

   MAG    hero-blog — la copertina di /blog, cioe' della pagina che la
          scheda apre: chi clicca ritrova la stessa immagine e capisce
          di essere arrivato.
   PRO    r06 — qualcuno seduto sul proprio cuscino, mala, candela,
          pavimento di casa: un professionista nel suo spazio, non uno
          scatto di categoria. E' esattamente quello che dice la
          colonna ("raccontati attraverso le loro storie").
   EXP    r07 — meditazione seduta sull'acqua, luce alta: una scena che
          si VIVE, ed e' il verbo della colonna Esperienze. Rimpiazza
          r02, che dall'onda della landing operatori e' impegnata li'
          (stessa foto a un clic di distanza si nota subito).
   OPS    hero-organizer — l'immagine con cui il sito racconta il lato
          di chi lavora (e' la copertina storica del mondo
          organizzatori/operatori). Mani in gesto di pratica, in luce
          naturale: e' una persona al lavoro, non un servizio. Nessuna
          r0* poteva stare qui senza ripetere una pagina a un clic di
          distanza.
   LETTERA hero-destination — il campo in controluce, la sera. La
          Lettera parla anche di "un luogo da scoprire", e la sua luce
          fa rima con il tramonto dell'hero: la pagina comincia e
          finisce sulla stessa ora del giorno.

   Fuori uso perche' impegnate su pagine vicine: r04 e r01 (Manifesto),
   r03, r08, r09, r05, r02 (landing operatori), chisiamo-aurya (la
   firma dei fondatori: giusta sul Manifesto e su Chi siamo, fuori tono
   in home). */
/* HS (21/8) — la fotografia della striscia Sound. Vuota finche' il
   file non c'e': un `src` che punta al nulla e' una richiesta a vuoto a
   ogni caricamento della home. Appena l'immagine e' in
   `public/media/hp-sound.jpg`, si accende scrivendo qui il percorso.

   TRATTAMENTO (e il perche'): l'immagine scelta dal founder e' una
   luce dipinta blu-ciano su nero. Il ciano puro e' l'unico colore
   lontano dalla tavolozza di Aurya, quindi non si posa MAI a piena
   forza: entra in `mix-blend-screen` sull'inchiostro, cosi' il nero
   della foto sparisce e restano solo i filamenti; un velo in gradiente
   tiene scuro il lato del testo; e una rotazione di tinta appena
   accennata porta il ciano verso l'acqua di Sound (--water). Il
   risultato e' una texture, non un secondo colore di marca. */
const SOUND_PHOTO = '/media/hp-sound.jpg';

const PHOTO = {
  magazine: '/media/hero-blog.webp',
  pros: '/media/prelaunch/r06.jpg',
  experiences: '/media/prelaunch/r07.jpg',
  operators: '/media/hero-organizer.webp',
  letter: '/media/hero-destination.webp',
};

export default function NetworkHomePage() {
  const { t, i18n } = useTranslation('landings');
  const lang = (i18n.language || 'it').slice(0, 2);
  const [articles, setArticles] = useState([]);

  useSeoMeta({
    title: t('nwHome.seoTitle', { defaultValue: "Aurya | Il benessere inizia dalle persone" }),
    // 148 caratteri: cosa e' Aurya e con che cosa, tagliato dove
    // finisce la frase e non dove finisce lo spazio.
    description: t('nwHome.seoDesc', { defaultValue: "Aurya è uno spazio per orientarsi nel mondo del benessere: contenuti autorevoli, professionisti raccontati con cura ed esperienze selezionate." }),
    canonicalPath: '/',
  });

  useEffect(() => {
    let mounted = true;
    api.get('/public/articles', { params: { lang, page_size: MAX_ARTICLES } })
      .then(res => { if (mounted) setArticles(res.data?.items || []); })
      .catch(() => { /* niente articoli: la sezione non compare */ });
    return () => { mounted = false; };
  }, [lang]);

  const fmtDate = (iso) => {
    if (!iso) return '';
    try { return new Date(iso).toLocaleDateString(lang, { day: 'numeric', month: 'long', year: 'numeric' }); }
    catch { return ''; }
  };
  const catLabel = (slug) => (slug ? t(`categories.${slug}`, { defaultValue: slug }) : '');

  const [lead, ...secondary] = articles;

  /* Le tre colonne in un dato solo: l'ordine e' quello del founder e la
     terza NON ha `to`, quindi PillarCard le da' l'etichetta di stato
     ("Prossimamente") al posto del link — si accendera' al lancio del
     marketplace.
     Le immagini sono DECORATIVE (alt=""): titolo e testo della scheda
     dicono gia' tutto, e un alt che ripete "una persona che medita"
     aggiungerebbe rumore a chi ascolta la pagina invece di leggerla. */
  const pillars = [
    {
      id: 'magazine',
      numeral: '01',
      image: PHOTO.magazine,
      title: t('nwHome.pillarMagTitle', { defaultValue: "Magazine" }),
      text: t('nwHome.pillarMagText', { defaultValue: "Guide, approfondimenti e storie per capire il mondo del benessere senza semplificazioni e senza promesse facili." }),
      to: MAGAZINE_PATH,
      ctaLabel: t('nwHome.pillarMagCta', { defaultValue: "Leggi gli articoli" }),
    },
    {
      id: 'professionisti',
      numeral: '02',
      image: PHOTO.pros,
      title: t('nwHome.pillarProTitle', { defaultValue: "Professionisti" }),
      // SR2 — niente promesse di cantiere: quelle vivono nel Manifesto.
      // Qui si dice cosa trovi, e la porta si chiama come nel menu.
      text: t('nwHome.pillarProText', { defaultValue: "Persone che conosciamo una per una: la loro storia, il modo in cui lavorano, i loro servizi e i loro ritiri." }),
      to: NETWORK_PATH,
      ctaLabel: t('nwHome.pillarProCta', { defaultValue: "Scopri i professionisti" }),
    },
    {
      id: 'esperienze',
      numeral: '03',
      image: PHOTO.experiences,
      title: t('nwHome.pillarExpTitle', { defaultValue: "Esperienze" }),
      text: t('nwHome.pillarExpText', { defaultValue: "Workshop, ritiri ed eventi per trasformare ciò che hai scoperto in qualcosa da vivere." }),
      // niente `to`: la terza colonna e' una promessa, non una porta
      badge: t('nwHome.pillarExpBadge', { defaultValue: "Prossimamente" }),
    },
  ];

  return (
    <MarketplaceShell noSearch>
      <div className="bg-background">

        {/* ── 1. HERO — la convinzione ─────────────────────────────
            La meccanica e' quella di HP4 e non si tocca: video montato
            dopo il `load`, poster subito, due veli tarati sul
            fotogramma PIU' CHIARO del tramonto (il sole bruciato,
            255-255-151). Il velo verticale scurisce sopra e molto
            sotto, cosi' il taglio verso la sabbia si legge come una
            scelta; l'ellisse centrale aggiunge buio SOLO dietro il
            blocco di testo e lascia respirare gli angoli.

            Quello che cambia in HP5 e' il testo, che da due frasi-
            titolo diventa una frase sola piu' tre capoversi. Tre
            capoversi centrati uno sotto l'altro, su desktop, sono nove
            righe sopra un video: si legge come una pagina di libro
            appoggiata su una fotografia. Per questo il secondo e il
            terzo si AFFIANCANO da `lg` in su — sono paralleli (cosa e'
            Aurya / come lo fa), e affiancati si leggono in un colpo
            d'occhio solo. Sotto `lg` tornano in colonna, dove due
            colonne di testo centrato non starebbero in piedi. */}
        {/* <section> e non <header>: il landmark banner e' gia' quello
            della shell, due banner confondono lo screen reader.
            `isolate` tiene il velo e il testo nel loro contesto di
            impilamento, senza contendere lo z-index all'header. */}
        <section aria-labelledby="hp-hero-title"
                 className="relative isolate overflow-hidden bg-[#0e1a15] text-[#f6f2e8]">
          <HeroVideo src={HERO_VIDEO} poster={HERO_POSTER} className="object-[50%_42%]" />
          <div aria-hidden
               className="absolute inset-0 bg-gradient-to-b from-[#0e1a15]/[0.72] via-[#0e1a15]/[0.58] to-[#0e1a15]/[0.88]" />
          <div aria-hidden
               className="absolute inset-0 bg-[radial-gradient(ellipse_88%_66%_at_50%_50%,rgba(14,26,21,0.50)_0%,rgba(14,26,21,0.32)_55%,rgba(14,26,21,0)_100%)]" />
          {/* pb-24 su telefono e non py-16: con tre capoversi il blocco
              di testo e' cresciuto, e il segno "scendi" che vive nel
              padding inferiore arrivava a sfiorare la CTA secondaria. Da
              `sm` in su il padding torna simmetrico: li' lo spazio c'e'. */}
          <div data-testid="hp-hero"
               className="relative mx-auto flex min-h-[32rem] w-full max-w-5xl flex-col items-center
                          justify-center px-6 pb-24 pt-16 text-center sm:min-h-[70svh] sm:px-8 sm:py-20
                          lg:min-h-[82svh] lg:py-24">
            <BrandPayoff tone="hero" size="xs" className="mb-5 sm:mb-7" />
            <DisplayTitle as="h1" id="hp-hero-title" size="hero" measure="wide"
                          className="mx-auto text-hero-shadow">
              {t('nwHome.heroTitle', { defaultValue: "Il benessere inizia dalle persone." })}
            </DisplayTitle>
            {/* tone inherit: sul video l'opacita' di default toglierebbe
                contrasto proprio dove serve tutto quello che c'e' */}
            <Lede size="lead" tone="inherit"
                  className="mx-auto mt-6 max-w-[46ch] text-hero-shadow sm:mt-8">
              {t('nwHome.heroP1', { defaultValue: "Trovare il professionista giusto, comprendere una pratica o scegliere un’esperienza non dovrebbe essere una questione di fortuna." })}
            </Lede>
            {/* i due capoversi paralleli. Il filo d'oro sopra non e'
                decorazione: dice che quello che segue e' un secondo
                movimento e non la coda del primo. */}
            <div aria-hidden className="gold-rule mt-8 w-24 sm:mt-10" />
            <div className="mt-8 grid gap-6 text-center sm:mt-9 lg:grid-cols-2 lg:gap-12">
              <Lede size="body" tone="inherit" className="mx-auto max-w-[44ch] text-hero-shadow opacity-90">
                {t('nwHome.heroP2', { defaultValue: "Aurya è uno spazio dedicato a chi vuole orientarsi nel mondo del benessere con maggiore consapevolezza." })}
              </Lede>
              <Lede size="body" tone="inherit" className="mx-auto max-w-[44ch] text-hero-shadow opacity-90">
                {t('nwHome.heroP3', { defaultValue: "Attraverso contenuti, professionisti raccontati con cura ed esperienze selezionate, aiutiamo le persone a trovare ciò che fa davvero per loro." })}
              </Lede>
            </div>
            {/* due azioni, ma di peso diverso: la prima e' la porta di
                casa, la seconda smista l'altro pubblico senza
                contendersela. SR2 (3/9/2026, SITO IMMEDIATO): la porta
                di casa e' la DIRECTORY dei professionisti — quando la
                rete era vuota era il Magazine «l'unica cosa gia' viva»;
                ora chi cerca qualcuno lo trova dal primo schermo.
                In colonna su mobile: affiancate, la secondaria
                finirebbe schiacciata sotto i 375px. */}
            <div className="mt-9 flex flex-col items-center gap-5 sm:mt-10 sm:flex-row sm:justify-center sm:gap-8">
              <EditorialCta to={NETWORK_PATH} variant="solid" tone="dark" data-testid="hp-hero-cta">
                {t('nwHome.heroCta', { defaultValue: "Scopri i professionisti" })}
              </EditorialCta>
              {/* LC6 — stessa parola dell'header: "professionisti".
                  La stessa destinazione aveva due nomi (header "Per i
                  professionisti", hero "Per gli operatori") e due nomi
                  per una porta sola fanno sembrare due porte. */}
              <EditorialCta to={JOIN_PATH} variant="quiet" tone="dark" data-testid="hp-hero-cta-alt">
                {t('nwHome.heroCtaAlt', { defaultValue: "Per i professionisti" })}
              </EditorialCta>
            </div>
          </div>
          {/* l'invito a scendere. La prima schermata e' un video a
              tutto campo: bella, ma muta sul fatto che sotto continui.
              E' un SEGNO, non un comando: decorativo (aria-hidden), non
              focalizzabile, non cliccabile, nessuna parola nuova in
              nessuna delle quattro lingue. Sta dentro il padding
              inferiore dell'hero, quindi non tocca mai le due CTA, e il
              movimento e' spento da prefers-reduced-motion. */}
          <div aria-hidden
               className="pointer-events-none absolute inset-x-0 bottom-5 flex justify-center sm:bottom-7">
            <span className="flex h-10 w-10 items-center justify-center rounded-full
                             border border-[#f6f2e8]/45 text-[#f6f2e8]/90
                             motion-safe:animate-bounce [animation-duration:2.6s]">
              <ChevronDown className="h-5 w-5" />
            </span>
          </div>
        </section>

        {/* ── 2. UN LUOGO DOVE CAPIRE — la mappa ───────────────────
            Fondo sabbia e non bianco: le tre schede sono bianche, e
            schede bianche su fondo bianco non esistono. E' il fondo
            piu' caldo a farle galleggiare e a dare alla mappa del sito
            un peso diverso dal racconto che la circonda.

            La testa e' una MASTHEAD: il titolo tiene la colonna di
            sinistra, le quattro righe del founder stanno a destra
            divise nelle due coppie che sono davvero — "il benessere e'
            fatto di X" (corpo lead) e "per questo Aurya e' Y" (corpo).
            Allineate in basso, cosi' la sezione ha un bordo superiore
            riconoscibile invece di cominciare in mezzo al colore.
            Le schede hanno la stessa altezza e il piede alla stessa
            quota: "Prossimamente" si legge come una differenza voluta e
            non come una scheda rotta. */}
        <Section tone="sand" rhythm="screen" labelledBy="hp-find-title"
                 width="max-w-6xl">
          <div data-testid="hp-pillars">
            <div className="grid gap-8 lg:grid-cols-12 lg:items-end lg:gap-14">
              <div className="lg:col-span-5">
                <DisplayTitle as="h2" id="hp-find-title" size="section" measure="title">
                  {t('nwHome.findTitle', { defaultValue: "Un luogo dove conoscere, confrontare e scegliere con consapevolezza" })}
                </DisplayTitle>
                <div aria-hidden className="gold-rule mt-8 max-w-[10rem]" />
              </div>
              <div className="lg:col-span-7">
                <Lede size="lead">
                  <TitleLine>
                    {t('nwHome.findP1', { defaultValue: "Il benessere non è fatto solo di discipline." })}
                  </TitleLine>
                  <TitleLine>
                    {t('nwHome.findP2', { defaultValue: "È fatto di persone, approcci, esperienze e percorsi diversi." })}
                  </TitleLine>
                </Lede>
                <Lede size="body" className="mt-6">
                  <TitleLine>
                    {t('nwHome.findP3', { defaultValue: "Per questo Aurya non nasce come una semplice directory." })}
                  </TitleLine>
                  <TitleLine>
                    {t('nwHome.findP4', { defaultValue: "Nasce per aiutarti a orientarti, conoscere chi hai davanti e scegliere con maggiore consapevolezza." })}
                  </TitleLine>
                </Lede>
              </div>
            </div>
            {/* con la scheda-oggetto il gap puo' stringersi: a separarle
                ci pensano il bordo e l'ombra, non piu' il vuoto */}
            <ul className="mt-12 sm:mt-14 grid gap-7 sm:gap-8 lg:grid-cols-3 list-none p-0">
              {/* `id` esce dallo spread: e' la chiave della lista e il
                  nostro appiglio nei test, non un attributo da versare
                  sul DOM della scheda */}
              {pillars.map(({ id, ...card }) => (
                <li key={id} data-testid={`hp-pillar-${id}`} className="h-full">
                  <PillarCard variant={PILLAR_VARIANT} {...card} />
                </li>
              ))}
            </ul>

            {/* ── la striscia: Aurya Sound ────────────────────────────
                HS (21/8/2026, founder) — Sound era in DUE voci di menu e
                in nessun punto della home: chi ci cliccava attraversava
                il confine visivo scuro senza sapere cosa fosse. Qui la
                mappa smette di essere incompleta.

                PERCHE' UNA FASCIA E NON UNA QUARTA COLONNA. Le tre
                schede sono tre modi di incontrare QUALCUNO: leggere chi
                scrive, conoscere chi pratica, vivere cio' che propone.
                Sound non e' un quarto contenuto, e' uno STRUMENTO:
                messo in fila sembrerebbe la stessa cosa degli altri.
                E in pratica: la fila e' larga 1088 px, tre schede da
                341; a quattro diventerebbero 248 l'una — un quarto in
                meno su una scheda alta 472 con foto, titolo, testo e
                invito. La griglia non si tocca.

                IL FONDO E' L'INCHIOSTRO DI SOUND (--stone #122125), non
                il salvia della battuta 3: due verdi adiacenti
                romperebbero l'alternanza dei fondi (grammatica DS: mai
                due ancore verdi vicine). Ed e' un'anteprima onesta —
                chi la vede ha gia' visto il mondo in cui sta per
                entrare. Resta un OGGETTO sulla sabbia, come le tre
                schede bianche: il padding della sezione lascia sotto
                un respiro di sabbia prima del verde.

                IL TITOLO CHIUDE LA FRASE che le tre schede aprono —
                leggere, conoscere, vivere — e non ha bisogno di
                spiegare il collegamento: sta appena sotto di loro. */}
            <div data-testid="hp-sound"
                 className="relative mt-10 sm:mt-12 overflow-hidden rounded-3xl bg-[#122125]
                            text-[#f6f2e8] shadow-[0_18px_44px_rgba(18,33,37,0.22)]">
              {SOUND_PHOTO && (
                <div aria-hidden className="pointer-events-none absolute inset-0">
                  <img src={SOUND_PHOTO} alt="" loading="lazy" decoding="async"
                       className="h-full w-full object-cover opacity-[0.45] mix-blend-screen
                                  [filter:hue-rotate(-22deg)_saturate(0.78)]" />
                  {/* VELO UNIFORME, non a gradiente. Il primo tentativo
                      apriva il velo verso destra pensando che li' non ci
                      fosse testo — ma il testo occupa TUTTA la larghezza
                      (titolo a sinistra, corpo e invito a destra), e la
                      misura sui pixel veri dell'immagine dava 4,69:1 nel
                      punto piu' chiaro: appena sopra il minimo, su una
                      pagina che sta fra 7 e 15 dappertutto.
                      Con velo 0,66 e immagine 0,45 il caso peggiore
                      (lo 0,1% di pixel piu' luminosi) e' 6,41 e il tipico
                      10,09 — e la texture visibile e' persino maggiore,
                      perche' il velo piu' fitto lascia alzare l'opacita'. */}
                  <div className="absolute inset-0 bg-[#122125]/[0.66]" />
                </div>
              )}
              <div aria-hidden className="gold-rule relative" />
              <div className="relative grid gap-8 p-8 sm:p-10 lg:grid-cols-12 lg:gap-12 lg:p-12">
                {/* Il titolo E' il nome (testo del founder, 21/8): via
                    l'occhiello, che diceva «AURYA SOUND» tre centimetri
                    sopra un titolo «Aurya Sound». L'oro resta nel filo
                    in testa alla striscia. */}
                {/* ORO su titolo e sottotitolo (founder, 21/8). Non e'
                    l'oro editoriale #c9b37e ma #d6c49a: e' quello che il
                    sito usa GIA' sui fondi scuri (i titoletti del
                    footer). La differenza non e' estetica ma misurata —
                    col velo e la texture sotto, l'oro editoriale scende
                    a 3,49:1 nel punto piu' chiaro, questo tiene 4,17
                    (tipico 6,56). Entrambi i testi sono «grandi» per
                    WCAG (52 px e 24 px), quindi la soglia e' 3:1: qui
                    ci stiamo sopra con margine, non per un pelo.
                    Il corpo resta crema, che sotto la texture regge
                    6,41 nel peggiore e 10,09 nel tipico. */}
                <div className="lg:col-span-5">
                  <DisplayTitle as="h3" size="section" measure="tight"
                                className="text-[#d6c49a]">
                    {t('nwHome.soundTitle', { defaultValue: 'Aurya Sound' })}
                  </DisplayTitle>
                  <div aria-hidden className="gold-rule mt-7 max-w-[8rem]" />
                </div>
                <div className="lg:col-span-7">
                  {/* Lede porta `text-current`: e' fatto per EREDITARE
                      il colore, non per riceverlo da className (le due
                      utility si contendono la cascata e vince quella che
                      capita). Quindi l'oro si mette sul contenitore. */}
                  <div className="text-[#d6c49a]">
                    <Lede size="lead" tone="inherit">
                      {t('nwHome.soundP1', { defaultValue: 'Lo spazio di Aurya dedicato al suono.' })}
                    </Lede>
                  </div>
                  <Lede size="body" tone="inherit" className="mt-5 opacity-90">
                    {t('nwHome.soundP2', { defaultValue: 'Frequenze, suoni, meditazioni e sessioni da ascoltare, esplorare e sperimentare. Aurya Sound offre strumenti per creare e personalizzare sessioni sonore, sia per chi pratica sia per chi conduce esperienze.' })}
                  </Lede>
                  <p className="mt-8">
                    <EditorialCta to="/sound" variant="solid" tone="dark"
                                  data-testid="hp-sound-cta">
                      {t('nwHome.soundCta', { defaultValue: 'Esplora Aurya Sound' })}
                    </EditorialCta>
                  </p>
                </div>
              </div>
            </div>
          </div>
        </Section>

        {/* ── 3. PERCHE' ESISTE AURYA — la ragione ─────────────────
            L'ANCORA TONALE della pagina, a meta' esatta della lettura:
            e' il cuore concettuale ed e' l'unica sezione fatta di solo
            ragionamento. Il verde pieno le da' il peso che il testo da
            solo non riusciva a prendersi e spezza la sequenza dei fondi
            chiari. Verde pieno e non fotografia: qui il testo e' lungo,
            e un'immagine sotto un testo lungo si paga sempre in
            leggibilita'.

            LA FORMA. Il titolo tiene la colonna di sinistra col filo
            d'oro sotto (lo schema del Manifesto). A destra i sei
            capoversi del founder diventano tre movimenti:
              · la constatazione, in corpo lead;
              · l'ANTITESI — "trovare un nome" contro "capire a chi
                affidarsi" — in corpo display, una riga ciascuna,
                separate da un filo. E' la frase su cui gira tutta la
                pagina, e in corpo di lettura passava inosservata;
              · la convinzione e la decisione, affiancate: sono
                paralleli, e in colonna sembravano una spiegazione
                lunga il doppio di quello che e'. */}
        <Section tone="sage" rhythm="screen" labelledBy="hp-why-title"
                 width="max-w-6xl">
          <div data-testid="hp-why" className="grid gap-9 lg:grid-cols-12 lg:gap-14">
            <div className="lg:col-span-4">
              <DisplayTitle as="h2" id="hp-why-title" size="section" measure="tight">
                {t('nwHome.whyTitle', { defaultValue: "Perché esiste Aurya?" })}
              </DisplayTitle>
              <div aria-hidden className="gold-rule mt-8 max-w-[10rem]" />
            </div>
            <div className="lg:col-span-8">
              {/* SR2 (3/9/2026, SITO IMMEDIATO — founder: «troppe
                  informazioni, uno si stanca»): il perche' per esteso
                  (fiducia, tempo, trasparenza, «abbiamo deciso di
                  costruire Aurya») vive nel Manifesto, che e' casa sua.
                  Qui resta l'antitesi in due righe display — la frase
                  che definisce il progetto — e la porta per leggere il
                  resto. Da sei capoversi a due righe.
                  I fili sono decorativi (sono bordi, non testo), le
                  righe stanno a piena opacita' — 7,28:1 sul salvia. */}
              <div className="border-t border-[#f6f2e8]/20">
                <p className="border-b border-[#f6f2e8]/20 py-6 font-display text-[1.4rem]
                              leading-[1.24] tracking-[-0.015em] sm:py-7 sm:text-[1.75rem] lg:text-[1.95rem]">
                  {t('nwHome.whyP2', { defaultValue: "Trovare un professionista è semplice." })}
                </p>
                <p className="border-b border-[#f6f2e8]/20 py-6 font-display text-[1.4rem]
                              leading-[1.24] tracking-[-0.015em] sm:py-7 sm:text-[1.75rem] lg:text-[1.95rem]">
                  {t('nwHome.whyP3', { defaultValue: "Scegliere quello giusto è ciò che conta." })}
                </p>
              </div>
              <div className="mt-9">
                <EditorialCta to="/manifesto" variant="light" data-testid="hp-why-cta">
                  {t('nwHome.whyCta', { defaultValue: "Leggi il Manifesto" })}
                </EditorialCta>
              </div>
            </div>
          </div>
        </Section>

        {/* ── 4. DAL MAGAZINE — la prova ───────────────────────────
            Fondo bianco pieno, il punto piu' luminoso della pagina,
            subito dopo l'ancora verde. Serve anche alle copertine:
            quelle autogenerate del Magazine sono verdi scure, e sul
            bianco si staccano come oggetti.
            La testa e' una MASTHEAD da rivista: nome della rubrica a
            sinistra col capoverso che la spiega, "Tutti gli articoli" a
            destra sulla stessa riga, un filo che chiude la testata e
            apre la vetrina. Il link e' UNO SOLO e sta dove si vede
            prima di leggere, non in fondo.
            Uno grande, due piccoli; con un articolo solo il grande
            prende tutta la larghezza invece di lasciare mezza griglia
            vuota. Zero articoli, zero sezione: una griglia vuota direbbe
            "non abbiamo ancora niente" molto piu' forte del silenzio.
            (E' l'unico punto in cui una battuta del founder puo' non
            comparire: sta scritto nel report.) */}
        {articles.length > 0 && (
          <Section tone="paper" rhythm="screen" labelledBy="hp-mag-title"
                   width="max-w-6xl">
            <div data-testid="hp-magazine">
              <div className="flex flex-col gap-6 border-b border-[#1e2f28]/[0.12] pb-7
                              sm:flex-row sm:items-end sm:justify-between sm:gap-12">
                <div>
                  <DisplayTitle as="h2" id="hp-mag-title" size="section" measure="title">
                    {t('nwHome.magTitle', { defaultValue: "Dal Magazine" })}
                  </DisplayTitle>
                  <Lede size="body" className="mt-5 max-w-[54ch]">
                    {t('nwHome.magBody', { defaultValue: "Il Magazine è il cuore di Aurya. Qui raccontiamo pratiche, persone e idee che aiutano a comprendere il benessere con uno sguardo aperto, concreto e curioso." })}
                  </Lede>
                </div>
                <div className="shrink-0 sm:pb-1.5">
                  <EditorialCta to={MAGAZINE_PATH} variant="quiet" data-testid="hp-mag-cta">
                    {t('nwHome.magCta', { defaultValue: "Tutti gli articoli" })}
                  </EditorialCta>
                </div>
              </div>
              <div className="mt-10 sm:mt-12 grid gap-10 lg:grid-cols-12 lg:gap-14">
                <div className={secondary.length > 0 ? 'lg:col-span-7' : 'lg:col-span-8'}>
                  <ArticleCard article={lead} variant="lead"
                               category={catLabel(lead.category)}
                               date={fmtDate(lead.published_at)} />
                </div>
                {/* la spalla resta di fianco (variant "aside"): qui i due
                    secondari stanno accanto a un articolo grande, e
                    impilarli con la copertina piena metterebbe tre
                    copertine a competere nella stessa sezione. */}
                {secondary.length > 0 && (
                  <div className="lg:col-span-5 grid gap-7 sm:grid-cols-2 lg:grid-cols-1 lg:content-start lg:gap-9 lg:pt-2">
                    {secondary.map(a => (
                      <ArticleCard key={a.slug} article={a} variant="aside"
                                   category={catLabel(a.category)}
                                   date={fmtDate(a.published_at)} />
                    ))}
                  </div>
                )}
              </div>
            </div>
          </Section>
        )}

        {/* ── 5. PER GLI OPERATORI — l'invito ──────────────────────
            La battuta piu' lunga della pagina, e l'unica rivolta a un
            altro pubblico: per questo cambia FORMA e non solo fondo.
            Mezza pagina di fotografia (le mani di chi pratica, in luce
            naturale: una persona al lavoro) e mezza di testo sul crema
            pieno. Il testo NON sta sopra la foto: cosi' il
            contrasto e' quello dichiarato dal tono e non dipende da
            come e' esposto quello scatto.
            La foto sta a destra: i titoli di tutta la pagina partono
            dal filo verticale di sinistra, e tenerlo anche qui evita
            che l'occhio ricominci da capo alla penultima battuta.
            Le prime tre righe del founder sono frammenti della stessa
            frase e vanno lette d'un fiato: display serif, una per riga,
            interlinea stretta, nessun filo in mezzo (i fili sono gia'
            il segno dell'antitesi verde: due volte lo stesso segno
            sarebbe un tic). Poi il capoverso lungo in corpo di lettura,
            e l'invito che chiude, in tono pieno perche' e' la riga che
            porta al bottone.
            Due CTA e non una: i due gesti sono davvero diversi
            (candidarsi / farsi un'idea prima). */}
        <PhotoSplit
          image={PHOTO.operators}
          focus="50% 45%"
          side="right"
          tone="cream"
          imageWidth="1920"
          imageHeight="1280"
          labelledBy="hp-pros-title"
        >
          <div data-testid="hp-pros">
            <DisplayTitle as="h2" id="hp-pros-title" size="section" measure="title">
              {t('nwHome.prosTitle', { defaultValue: "Per chi dedica la propria vita al benessere degli altri." })}
            </DisplayTitle>
            <div aria-hidden className="gold-rule mt-8 max-w-[10rem]" />
            {/* il crescendo: tre frammenti, una riga ciascuno */}
            <div className="mt-8 font-display text-[1.35rem] leading-[1.35] tracking-[-0.015em]
                            text-foreground/90 sm:text-[1.6rem] sm:leading-[1.32]">
              <p>{t('nwHome.prosP1', { defaultValue: "Ogni professionista ha una storia." })}</p>
              <p>{t('nwHome.prosP2', { defaultValue: "Un modo di lavorare." })}</p>
              <p>{t('nwHome.prosP3', { defaultValue: "Un motivo per cui ha scelto questo percorso." })}</p>
            </div>
            {/* SR2 (3/9/2026): il capoverso lungo («presenza digitale
                autorevole, strumenti per crescere») e' il discorso della
                landing /entra-nella-rete, non della home: qui resta il
                crescendo del founder, l'invito in una riga e UNA porta
                (il Manifesto ha gia' la sua, due sezioni sopra). */}
            <Lede size="body" tone="inherit" className="mt-8">
              {t('nwHome.prosP5', { defaultValue: "Se sei un professionista del benessere, ci piacerebbe conoscerti." })}
            </Lede>
            <div className="mt-9">
              <EditorialCta to={JOIN_PATH} variant="solid" data-testid="hp-pros-cta">
                {t('nwHome.prosCta', { defaultValue: "Entra nella rete" })}
              </EditorialCta>
            </div>
          </div>
        </PhotoSplit>

        {/* ── 6. LA LETTERA — restare ──────────────────────────────
            LA PAGINA SI CHIUDE SU UNA FOTOGRAFIA, non su un testo: e'
            la fascia a tutta larghezza che la grammatica DS chiede a
            ogni pagina, ed e' l'unica volta in cui la home esce dalla
            sua colonna dopo l'hero. Fa rima con l'apertura: si comincia
            e si finisce sulla luce di sera.
            Il testo del founder e' fatto di sei frasi cortissime, e la
            forma le rispetta: l'apertura, i tre "una..." incolonnati al
            centro in display serif (e' un elenco vero, quindi e' una
            <ul>: chi ascolta la pagina sente "elenco di tre voci"), la
            chiusa in due righe piu' quiete. La misura di riga e'
            stretta apposta, cosi' ogni frase cade su una riga sola e il
            ritmo si vede invece di doverlo immaginare.
            Il bottone e' `solid` in tono scuro (crema su verde
            profondo): sul fondo fotografico il verde pieno non si
            staccherebbe, ed e' l'ultima azione della pagina. */}
        <PhotoBand
          image={PHOTO.letter}
          focus="50% 58%"
          width="max-w-3xl"
          labelledBy="hp-letter-title"
        >
          <div data-testid="hp-letter" className="flex flex-col items-center">
            <DisplayTitle as="h2" id="hp-letter-title" size="section" measure="title"
                          className="text-hero-shadow">
              {t('nwHome.letterTitle', { defaultValue: "Entra nel Cerchio di Aurya." })}
            </DisplayTitle>
            {/* CN3 (3/9/2026, piano IL CERCHIO): la sezione vende
                l'appartenenza, non «una lettera ogni tanto»: le tre
                cose vere che ricevi, il form, una riga di fiducia. */}
            <Lede size="lead" tone="inherit" className="mt-6 max-w-[40ch] text-hero-shadow">
              {t('nwHome.letterP1', { defaultValue: "Meditazioni riservate, ritiri in anteprima e una lettera quando vale la pena. Gratis." })}
            </Lede>
            <ul className="mt-7 list-none space-y-2 p-0 font-display text-[1.3rem] leading-[1.35]
                           tracking-[-0.015em] text-hero-shadow sm:text-[1.55rem]">
              <li>{t('nwHome.letterP2', { defaultValue: "Meditazioni riservate." })}</li>
              <li>{t('nwHome.letterP3', { defaultValue: "Ritiri ed esperienze in anteprima." })}</li>
              <li>{t('nwHome.letterP4', { defaultValue: "La Lettera, quando vale la pena." })}</li>
            </ul>
            <div aria-hidden className="gold-rule mt-8 w-24" />
            <Lede size="body" tone="inherit" className="mt-7 max-w-[46ch] text-hero-shadow opacity-90">
              <TitleLine>
                {t('nwHome.letterP6', { defaultValue: "Una conferma via email, poi sei dentro. Ti cancelli con un clic." })}
              </TitleLine>
            </Lede>
            {/* LC5 — il form al posto del link: un passo in meno per
                l'azione a minor attrito del sito. Pannello crema pieno:
                gli input bianchi e il consenso grigio sono disegnati per
                fondo chiaro, non per la fotografia. CN3: preferenza
                ritiri accesa, con la citta' (variante leggera). */}
            <div className="mt-9 w-full max-w-md rounded-2xl bg-[#f6f2e8]/95 p-5 text-left
                            shadow-[0_18px_48px_-28px_rgba(14,26,21,0.6)] sm:p-6"
                 data-testid="hp-letter-form">
              <LeadForm
                type="traveler" compact subscribe showName={false} accent={SAGE}
                experiencesOptIn experiencesDefault experiencesLight
                context="home_letter"
                consentText={t('blogCta.consent', { defaultValue: 'Acconsento a ricevere le email del Cerchio di Aurya.' })}
                ctaLabel={t('nwHome.letterCta', { defaultValue: 'Entra nel Cerchio' })}
                thanksBody={t('blogCta.thanksDoi', { defaultValue: 'Quasi dentro: apri la tua casella e clicca «Entro nel Cerchio» nell’email che ti abbiamo appena mandato.' })}
              />
            </div>
            <p className="mt-5">
              <EditorialCta to="/newsletter" variant="light" data-testid="hp-letter-cta">
                {t('nwHome.letterMore', { defaultValue: "Scopri cos'è il Cerchio" })}
              </EditorialCta>
            </p>
          </div>
        </PhotoBand>

      </div>
    </MarketplaceShell>
  );
}
