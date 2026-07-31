/**
 * NetworkHomePage — la home della fase rete.
 *
 * HP2 (31/7/2026) — riscritta sulla SPECIFICA DEFINITIVA del founder,
 * che supera la v3 di HP1. Sette sezioni, copy CHIUSO parola per
 * parola (si tocca solo il vestito: gerarchia, ritmo, componenti):
 *   1. HERO         la convinzione        due CTA (esplora / operatori)
 *   2. COSA TROVERAI le tre colonne       Magazine, Professionisti, Esperienze
 *   3. PERCHE'      la ragione            tre paragrafi, CTA manifesto
 *   4. DAL MAGAZINE la prova              gated sui dati
 *   5. LA RETE      il picco (salvia)     rete, non directory
 *   6. OPERATORI    l'invito              due CTA
 *   7. LA LETTERA   restare               newsletter
 *
 * HP3 (31/7/2026) — REFINEMENT SOLO VISIVO. Copy, ordine delle
 * sezioni e CTA restano congelati: cambiano fotografie, fondi, ritmo
 * e micro-interazioni. Le tre decisioni portanti:
 *
 *   a) FOTOGRAFIA DOVE ARGOMENTA, NON DOVE RIEMPIE. Ogni immagine e'
 *      scelta per quello che dice la sezione in cui sta, e due delle
 *      cinque sono la copertina della pagina verso cui porta il link
 *      (Magazine → la cover di /blog; La rete → la cover di
 *      /entra-nella-rete): chi clicca ritrova la stessa immagine e
 *      capisce di essere arrivato.
 *   b) ALTERNANZA DEI FONDI. crema → sabbia → VERDE → bianco →
 *      VERDE+foto → crema → sabbia. Due ancore verdi non adiacenti,
 *      separate dalla vetrina bianca del Magazine, che e' anche il
 *      punto piu' luminoso della pagina.
 *   c) RESPIRO FRA, NON DENTRO. Il ritmo `screen` non stira piu' le
 *      sezioni a 82vh: era quello a produrre i vuoti bianchi.
 *
 * HP4 (31/7/2026) — SOLO L'HERO, su decisione del founder: la prima
 * schermata torna al video del tramonto a tutta larghezza con il testo
 * centrato sopra, come sullo splash di prelancio. Cambia il vestito
 * dell'apertura (fondo scuro, testo centrato, due veli misurati) e
 * NIENTE altro: copy invariato parola per parola, sezioni 2-7 intatte.
 * La sequenza di caricamento e le soglie di contrasto stanno nel
 * commento della sezione 1 e in components/HeroVideo.jsx.
 *
 * Cosa e' USCITO rispetto a HP1: la sezione "Le persone" coi volti dei
 * membri. La sostituiscono la colonna "Professionisti" (sezione 2) e
 * la sezione 5, che raccontano la rete come promessa in costruzione
 * invece di mostrarla come griglia. Effetto collaterale positivo: il
 * gap segnalato su /public/network/members (nessun campo `quote` ne'
 * `category` nel payload, PersonCard costretta a ripiegare sulla
 * tagline) non e' piu' bloccante per la home. PersonCard resta nel kit
 * per /operatori e per il giorno in cui i volti torneranno.
 *
 * Il payoff di brand ("Ci si fida di qualcuno, non di qualcosa") resta
 * occhiello sopra l'H1: non si tocca.
 *
 * In fase marketplace questa home cede il posto alla directory
 * (HomeGate → RetreatsCalendarPage): quella e' un'altra pagina e non
 * viene toccata qui.
 */
import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import api from '../../api/client';
import MarketplaceShell from '../storefront/components/MarketplaceShell';
import useSeoMeta from '../storefront/lib/useSeoMeta';
import BrandPayoff from '../../components/BrandPayoff';
import HeroVideo from '../../components/HeroVideo';
import {
  Section, DisplayTitle, TitleLine, Lede, ArticleCard, PillarCard, EditorialCta,
} from '../../components/editorial';

/* NOTA TECNICA — la rotta del Magazine.
   La specifica scrive /magazine, ma la rotta canonica e indicizzata e'
   /blog (sta in sitemap ed e' gia' stata spinta con IndexNow). /magazine
   ORA ESISTE come redirect (App.js), cosi' i link della specifica non
   cadono nel vuoto; da qui pero' linkiamo la canonica, perche' passare
   dal redirect costa un rimbalzo di rendering all'utente e diluisce il
   segnale interno verso l'URL che i motori conoscono.
   Il cambio di canonical /blog → /magazine e' una decisione SEO a se':
   richiede sitemap, 301 lato server e un nuovo giro di IndexNow. */
const MAGAZINE_PATH = '/blog';

/* La landing operatori ha UN solo form, con ancora #presentati.
   "Parliamone" ci porta dritto li' invece che in cima alla pagina. */
const OPERATOR_FORM_PATH = '/entra-nella-rete#presentati';

/* Il segno in testa alle tre colonne: da HP3 il default e' 'plain'
   (la fotografia in testa fa gia' da segno). 'emoji' resta la
   specifica originale del founder, 'numeral' l'alternativa
   editoriale. Si prova cambiando questa sola parola; le motivazioni
   stanno nella NOTA DIREZIONE CREATIVA di editorial/PillarCard.jsx. */
const PILLAR_VARIANT = 'plain';

/** quanti articoli in vetrina: uno grande, due piccoli */
const MAX_ARTICLES = 3;

/* ── L'APERTURA IN MOVIMENTO (HP4) ────────────────────────────────
   Il tramonto di Aurya: lo stesso asset dello splash di prelancio e
   dell'hero marketplace, cioe' la firma visiva del brand. HP3 lo
   aveva scartato temendo 1,6 MB sul primo rendering; HeroVideo toglie
   quella obiezione, perche' sul primo rendering pesa solo il poster
   (47 KB) e il video arriva dopo, a pagina caricata. */
const HERO_VIDEO = '/media/aurya-hero.mp4';
const HERO_POSTER = '/media/aurya-hero-poster.jpg';

/* ── LE FOTOGRAFIE ────────────────────────────────────────────────
   Tutte gia' presenti in /public/media: nessun asset nuovo, nessuna
   stock. Accanto a ciascuna, il perche' sta li' e non altrove.

   MAG    hero-blog — la copertina di /blog, cioe' della pagina che la
          scheda apre. Chi clicca ritrova la stessa immagine.
   PRO    r06 — qualcuno seduto sul proprio cuscino, mala, candela,
          pavimento di casa: un professionista nel suo spazio, non uno
          scatto di categoria. "Raccontati con cura, uno alla volta."
   EXP    r02 — due persone che meditano insieme in un bosco al
          tramonto: e' un ritiro, ed e' al plurale. Desaturata, perche'
          la colonna e' una promessa e non un'offerta.
   RETE   hero-organizer — la copertina di /entra-nella-rete, la pagina
          della CTA di quella sezione. Stesso patto della colonna
          Magazine: l'immagine e' la porta.

   Scartate e perche': chisiamo-aurya (selfie dei fondatori: giusto sul
   Manifesto, fuori tono in home), hero-destination (girasoli:
   bellissimi, ma non parlano di persone), r08/r10 (trattamenti in
   primissimo piano: fortissimi, ma spostano il discorso dalla persona
   alla prestazione). r03 (la donna che medita sul muschio) era l'hero
   di HP3: con il video in apertura non ha piu' un posto dove stare
   senza ripetere quello che gia' dicono le tre colonne. */
const PHOTO = {
  magazine: '/media/hero-blog.webp',
  pros: '/media/prelaunch/r06.jpg',
  experiences: '/media/prelaunch/r02.jpg',
  network: '/media/hero-organizer.webp',
};

export default function NetworkHomePage() {
  const { t, i18n } = useTranslation('landings');
  const lang = (i18n.language || 'it').slice(0, 2);
  const [articles, setArticles] = useState([]);

  useSeoMeta({
    title: t('nwHome.seoTitle', { defaultValue: "Aurya | Il benessere inizia dalle persone" }),
    // 155 caratteri: la promessa dell'hero, tagliata dove finisce la
    // frase e non dove finisce lo spazio.
    description: t('nwHome.seoDesc', { defaultValue: "Scegliere un professionista del benessere significa affidargli qualcosa di personale. Aurya ti fa conoscere le persone dietro le pratiche." }),
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

  /* Le tre colonne in un dato solo: l'ordine e' quello della specifica
     e la terza NON ha `to`, quindi PillarCard le da' l'etichetta di
     stato al posto del link.
     Le immagini sono DECORATIVE (alt=""): titolo e testo della scheda
     dicono gia' tutto, e un alt che ripete "una persona che medita"
     aggiungerebbe rumore a chi ascolta la pagina invece di leggerla. */
  const pillars = [
    {
      id: 'magazine',
      icon: '📖',
      numeral: '01',
      image: PHOTO.magazine,
      title: t('nwHome.pillarMagTitle', { defaultValue: "Magazine" }),
      text: t('nwHome.pillarMagText', { defaultValue: "Guide, approfondimenti e storie per orientarti nel mondo del benessere senza promesse facili." }),
      to: MAGAZINE_PATH,
      ctaLabel: t('nwHome.pillarMagCta', { defaultValue: "Leggi gli articoli" }),
    },
    {
      id: 'professionisti',
      icon: '🌿',
      numeral: '02',
      image: PHOTO.pros,
      title: t('nwHome.pillarProTitle', { defaultValue: "Professionisti" }),
      text: t('nwHome.pillarProText', { defaultValue: "Stiamo costruendo una rete di professionisti raccontati con cura, uno alla volta. Ogni profilo nascerà da una conversazione, non da un semplice modulo." }),
      to: '/operatori',
      ctaLabel: t('nwHome.pillarProCta', { defaultValue: "Scopri il progetto" }),
    },
    {
      id: 'esperienze',
      icon: '✨',
      numeral: '03',
      image: PHOTO.experiences,
      title: t('nwHome.pillarExpTitle', { defaultValue: "Esperienze" }),
      text: t('nwHome.pillarExpText', { defaultValue: "Ritiri, workshop ed eventi selezionati per chi desidera vivere ciò che ha scoperto." }),
      // niente `to`: la terza colonna e' una promessa, non una porta
      badge: t('nwHome.pillarExpBadge', { defaultValue: "In arrivo" }),
    },
  ];

  return (
    <MarketplaceShell noSearch>
      <div className="bg-background">

        {/* ── 1. HERO — la convinzione ─────────────────────────────
            HP4 (decisione del founder): l'apertura torna a essere il
            TRAMONTO in movimento, come sullo splash di prelancio e
            sulla home marketplace, con il testo centrato sopra. HP3
            aveva provato la fotografia a due colonne e la teneva su un
            fondo crema: si leggeva benissimo, ma la prima schermata
            del sito non aveva impatto. Qui l'impatto lo fa il video e
            la leggibilita' la fa il velo, misurata e non sperata.

            Le quattro decisioni di questo blocco:
            a) CARICAMENTO. Il video non e' nel primo rendering: lo
               monta HeroVideo dopo `load`, in un momento di quiete
               (vedi il commento nel componente). Quello che si vede
               subito e' il poster da 47 KB.
            b) VELO IN DUE STRATI. Uno verticale, che scurisce sopra e
               molto sotto per raccordare il taglio con la sezione
               sabbia; uno radiale centrato, che aggiunge buio SOLO
               dietro il blocco di testo e lascia respirare gli angoli
               del tramonto. Le opacita' non sono a occhio: campionati
               i pixel del video sotto OGNI blocco di testo su 24
               fotogrammi, il velo e' tarato sul fotogramma PIU'
               CHIARO (il sole e' bruciato: 255-255-151, luminanza
               0,95). Rapporti nel caso peggiore, a 375 px: occhiello
               5,80:1, titolo 7,08:1, paragrafo 6,64:1, "Sei un
               operatore?" 10,59:1, e il bottone crema si stacca dal
               fondo a 9,39:1. A 1280 px: 6,47 / 7,23 / 7,49 / 9,60 /
               9,88. I minimi AA sono 4,5:1 per il corpo e 3:1 per il
               display grande. L'ombra del testo (.text-hero-shadow)
               c'e' ma e' la cintura di sicurezza, non il motore.
            c) ALTEZZA. Cinematografica ma mai 100vh: su mobile le
               barre del browser mangerebbero le CTA. Su schermo largo
               82svh, su telefono un'altezza in rem che il contenuto
               riempie senza obbligare a scorrere per vedere i bottoni.
            d) AZIONI. Le stesse due di sempre, ma in `tone="dark"`:
               sul tramonto scurito il verde pieno del bottone non si
               staccherebbe dal fondo, quindi la primaria diventa
               crema. Vedi EditorialCta. */}
        {/* <section> e non <header>: il landmark banner e' gia' quello
            della shell, due banner confondono lo screen reader.
            `isolate` tiene il velo e il testo nel loro contesto di
            impilamento, senza contendere lo z-index all'header. */}
        <section aria-labelledby="hp-hero-title"
                 className="relative isolate overflow-hidden bg-[#0e1a15] text-[#f6f2e8]">
          <HeroVideo src={HERO_VIDEO} poster={HERO_POSTER} className="object-[50%_42%]" />
          {/* velo 1: la verticale. Piu' buio in alto (dove il cielo del
              tramonto e' acceso) e in basso: e' il RACCORDO con la
              sezione sabbia che segue. Il punto piu' scuro della
              pagina sta sul bordo inferiore dell'hero, cosi' il
              passaggio a #f2ece0 si legge come un taglio voluto e non
              come una foto che finisce. Per questo la sezione 2 non
              cambia di una virgola: il raccordo lo fa l'hero, e il
              filo `border-b` che c'era in HP3 e' uscito perche' su un
              fondo scuro non lo vedrebbe nessuno. */}
          <div aria-hidden
               className="absolute inset-0 bg-gradient-to-b from-[#0e1a15]/[0.72] via-[#0e1a15]/[0.58] to-[#0e1a15]/[0.88]" />
          {/* velo 2: il buio dietro le parole. Ellisse morbida centrata
              sul blocco di testo: al centro somma ~0,80 di opacita'
              totale, ai bordi si annulla e il tramonto resta visibile.
              Senza questo secondo strato, sul sole bruciato il corpo
              del testo scendeva a 4,9:1: dentro AA per un soffio, e
              un soffio non e' un margine. */}
          <div aria-hidden
               className="absolute inset-0 bg-[radial-gradient(ellipse_88%_66%_at_50%_50%,rgba(14,26,21,0.50)_0%,rgba(14,26,21,0.32)_55%,rgba(14,26,21,0)_100%)]" />
          <div data-testid="hp-hero"
               className="relative mx-auto flex min-h-[32rem] w-full max-w-6xl flex-col items-center
                          justify-center px-6 py-16 text-center sm:min-h-[70svh] sm:px-8 sm:py-20
                          lg:min-h-[82svh] lg:py-24">
            <BrandPayoff tone="hero" size="xs" className="mb-5 sm:mb-7" />
            <DisplayTitle as="h1" id="hp-hero-title" size="heroLines" measure="lines"
                          className="mx-auto text-hero-shadow">
              <TitleLine>
                {t('nwHome.heroTitleA', { defaultValue: "Il benessere non inizia da una pratica." })}
              </TitleLine>
              <TitleLine>
                {t('nwHome.heroTitleB', { defaultValue: "Inizia dalle persone." })}
              </TitleLine>
            </DisplayTitle>
            {/* tone inherit: sul video l'opacita' di default toglierebbe
                contrasto proprio dove serve tutto quello che c'e' */}
            <Lede size="lead" tone="inherit" className="mx-auto mt-6 text-hero-shadow sm:mt-8">
              {t('nwHome.heroBody', { defaultValue: "Scegliere un professionista del benessere significa affidargli qualcosa di personale. Per questo Aurya nasce per aiutarti a conoscere le persone dietro le pratiche, comprendere i diversi approcci e orientarti con maggiore consapevolezza." })}
            </Lede>
            {/* due azioni, ma di peso diverso: la prima e' la porta di
                casa (il Magazine e' l'unica cosa gia' viva), la
                seconda smista l'altro pubblico senza contendersela.
                In colonna su mobile: affiancate, "Sei un operatore?"
                finirebbe schiacciata sotto i 375px. */}
            <div className="mt-8 flex flex-col items-center gap-5 sm:mt-10 sm:flex-row sm:justify-center sm:gap-8">
              <EditorialCta to={MAGAZINE_PATH} variant="solid" tone="dark" data-testid="hp-hero-cta">
                {t('nwHome.heroCta', { defaultValue: "Esplora il Magazine" })}
              </EditorialCta>
              <EditorialCta to="/entra-nella-rete" variant="quiet" tone="dark" data-testid="hp-hero-cta-alt">
                {t('nwHome.heroCtaAlt', { defaultValue: "Sei un operatore?" })}
              </EditorialCta>
            </div>
          </div>
        </section>

        {/* ── 2. COSA TROVERAI — le tre colonne ────────────────────
            HP3: fondo sabbia e non bianco. Le tre schede sono bianche,
            e schede bianche su fondo bianco non esistono: e' il fondo
            piu' caldo a farle galleggiare e a dare alla mappa del sito
            un peso diverso dal racconto che la circonda.
            Le schede hanno la stessa altezza e il piede alla stessa
            quota, cosi' "In arrivo" si legge come una differenza
            voluta e non come una card rotta. */}
        <Section tone="sand" rhythm="screen" labelledBy="hp-pillars-title"
                 width="max-w-6xl">
          <div data-testid="hp-pillars">
            <DisplayTitle as="h2" id="hp-pillars-title" size="section" measure="title">
              {t('nwHome.findTitle', { defaultValue: "Cosa troverai su Aurya." })}
            </DisplayTitle>
            <Lede size="body" className="mt-5">
              <TitleLine>
                {t('nwHome.findSubA', { defaultValue: "Non un catalogo." })}
              </TitleLine>
              <TitleLine>
                {t('nwHome.findSubB', { defaultValue: "Uno spazio per capire, prima ancora di scegliere." })}
              </TitleLine>
            </Lede>
            {/* con la scheda-oggetto il gap puo' stringersi: a separarle
                ci pensano il bordo e l'ombra, non piu' il vuoto */}
            <ul className="mt-10 sm:mt-12 grid gap-7 sm:gap-8 lg:grid-cols-3 list-none p-0">
              {/* `id` esce dallo spread: e' la chiave della lista e il
                  nostro appiglio nei test, non un attributo da versare
                  sul DOM della scheda */}
              {pillars.map(({ id, ...card }) => (
                <li key={id} data-testid={`hp-pillar-${id}`} className="h-full">
                  <PillarCard variant={PILLAR_VARIANT} {...card} />
                </li>
              ))}
            </ul>
          </div>
        </Section>

        {/* ── 3. PERCHE' ESISTE AURYA — la ragione ─────────────────
            HP3: PRIMA ANCORA TONALE. E' il cuore concettuale della
            pagina, ed e' l'unica sezione fatta di solo ragionamento:
            il verde pieno le da' il peso che il testo da solo non
            riusciva a prendersi, e spezza la sequenza di fondi chiari
            proprio a meta' della lettura.
            Verde pieno e non fotografia: qui i paragrafi sono tre, e
            un'immagine sotto un testo lungo si paga sempre in
            leggibilita'. La foto va dove il testo e' corto (sezione 5).
            Tre paragrafi in scala discendente di peso: il primo e'
            la tesi e sta al corpo del lede, gli altri due argomentano. */}
        <Section tone="sage" rhythm="screen" labelledBy="hp-why-title"
                 width="max-w-6xl">
          <div data-testid="hp-why">
            <DisplayTitle as="h2" id="hp-why-title" size="section" measure="tight">
              {t('nwHome.whyTitle', { defaultValue: "Perché esiste Aurya?" })}
            </DisplayTitle>
            {/* tone inherit: sul verde l'opacita' di default mangia
                contrasto, e il crema all'80% scenderebbe sotto AA */}
            <Lede size="lead" tone="inherit" className="mt-7">
              {t('nwHome.whyP1', { defaultValue: "Internet rende facile trovare informazioni. Molto più difficile è capire di chi fidarsi." })}
            </Lede>
            <Lede size="body" tone="inherit" className="mt-5 opacity-90">
              {t('nwHome.whyP2', { defaultValue: "Ogni giorno migliaia di persone cercano un professionista, leggono recensioni sparse, visitano decine di siti e finiscono per scegliere quasi alla cieca." })}
            </Lede>
            <Lede size="body" tone="inherit" className="mt-5 opacity-90">
              {t('nwHome.whyP3', { defaultValue: "Aurya nasce per cambiare questo. Vogliamo costruire uno spazio dove contenuti, persone ed esperienze possano essere conosciuti con il tempo e l'attenzione che meritano." })}
            </Lede>
            <div className="mt-9">
              <EditorialCta to="/manifesto" variant="light" data-testid="hp-why-cta">
                {t('nwHome.whyCta', { defaultValue: "Leggi il Manifesto" })}
              </EditorialCta>
            </div>
          </div>
        </Section>

        {/* ── 4. DAL MAGAZINE — la prova ───────────────────────────
            HP3: fondo bianco pieno, il punto piu' luminoso della
            pagina, incastrato fra le due ancore verdi. Serve anche alle
            copertine: quelle autogenerate del Magazine sono verdi
            scure, e sul bianco si staccano come oggetti.
            Uno grande, due piccoli; con un articolo solo il grande
            prende tutta la larghezza invece di lasciare mezza griglia
            vuota. Zero articoli, zero sezione: una griglia vuota direbbe
            "non abbiamo ancora niente" molto piu' forte del silenzio. */}
        {articles.length > 0 && (
          <Section tone="paper" rhythm="screen" labelledBy="hp-mag-title"
                   width="max-w-6xl">
            <div data-testid="hp-magazine">
              <DisplayTitle as="h2" id="hp-mag-title" size="section" measure="title">
                {t('nwHome.magTitle', { defaultValue: "Dal Magazine" })}
              </DisplayTitle>
              <Lede size="body" className="mt-5">
                {t('nwHome.magSub', { defaultValue: "Capire è il primo passo per scegliere bene." })}
              </Lede>
              <div className="mt-10 sm:mt-12 grid gap-10 lg:grid-cols-12 lg:gap-14">
                <div className={secondary.length > 0 ? 'lg:col-span-7' : 'lg:col-span-8'}>
                  <ArticleCard article={lead} variant="lead"
                               category={catLabel(lead.category)}
                               date={fmtDate(lead.published_at)} />
                </div>
                {secondary.length > 0 && (
                  <div className="lg:col-span-5 grid gap-7 sm:grid-cols-2 lg:grid-cols-1 lg:content-start lg:gap-9 lg:pt-2">
                    {secondary.map(a => (
                      <ArticleCard key={a.slug} article={a} variant="compact"
                                   category={catLabel(a.category)}
                                   date={fmtDate(a.published_at)} />
                    ))}
                  </div>
                )}
              </div>
              <div className="mt-12">
                <EditorialCta to={MAGAZINE_PATH} variant="quiet" data-testid="hp-mag-cta">
                  {t('nwHome.magCta', { defaultValue: "Tutti gli articoli" })}
                </EditorialCta>
              </div>
            </div>
          </Section>
        )}

        {/* ── 5. LA RETE — il picco ────────────────────────────────
            HP3: SECONDA ANCORA TONALE, ma di natura diversa dalla
            terza sezione, cosi' le due non si ripetono: qui il verde
            e' una fascia a tutta larghezza affiancata da una
            fotografia. Il testo sta sul verde PIENO e non sopra
            l'immagine: e' l'unico modo di avere insieme una foto vera e
            un contrasto misurabile che non dipenda da quanto e'
            luminoso quel pixel.
            La foto e' la copertina di /entra-nella-rete, cioe' della
            pagina dove porta la CTA di questa sezione.
            Qui NON si nomina niente di commerciale: solo presenza. */}
        <Section tone="sage" rhythm="none" labelledBy="hp-network-title"
                 width="max-w-none" gutter={false}>
          <div data-testid="hp-network" className="grid lg:grid-cols-2 lg:items-stretch">
            {/* la fascia esce dai margini, il TESTO no: mezza griglia
                larga quanto mezzo contenitore di pagina (36rem = metà
                di max-w-6xl) spinta a destra da ml-auto, piu' lo stesso
                gutter delle altre sezioni. Cosi' il filo verticale
                sinistro della pagina resta uno solo a ogni larghezza,
                senza calcoli su 100vw che la barra di scorrimento
                falserebbe. */}
            <div className="order-2 lg:order-1 flex items-center px-6 py-16 sm:px-8 sm:py-24 lg:py-28 lg:px-0">
              <div className="w-full lg:ml-auto lg:max-w-[36rem] lg:pl-8 lg:pr-14">
                <DisplayTitle as="h2" id="hp-network-title" size="section" measure="lines">
                  <TitleLine>
                    {t('nwHome.netTitleA', { defaultValue: "Stiamo costruendo una rete." })}
                  </TitleLine>
                  <TitleLine>
                    {t('nwHome.netTitleB', { defaultValue: "Non una directory." })}
                  </TitleLine>
                </DisplayTitle>
                <Lede size="body" tone="inherit" className="mt-7 opacity-90">
                  {t('nwHome.netBody', { defaultValue: "Ogni professionista entrerà in Aurya attraverso un percorso di conoscenza reciproca. Prima ascoltiamo la sua storia. Poi la raccontiamo. Infine costruiamo insieme un profilo che nel tempo diventerà il punto di riferimento della sua presenza su Aurya." })}
                </Lede>
                <div className="mt-9">
                  <EditorialCta to="/entra-nella-rete" variant="light" data-testid="hp-network-cta">
                    {t('nwHome.netCta', { defaultValue: "Scopri come entrare nella rete" })}
                  </EditorialCta>
                </div>
              </div>
            </div>
            {/* decorativa: la sezione si capisce tutta a parole */}
            <img
              src={PHOTO.network}
              alt=""
              width="1920"
              height="1280"
              loading="lazy"
              decoding="async"
              className="order-1 lg:order-2 h-56 w-full object-cover sm:h-80 lg:h-full lg:min-h-[30rem]"
            />
          </div>
        </Section>

        {/* ── 6. PER GLI OPERATORI — l'invito ──────────────────────
            Torna il crema e torna il silenzio: dopo la fascia verde e
            le copertine, questa sezione e quella della Lettera sono la
            discesa. Metterci una sesta fotografia avrebbe reso la
            pagina un catalogo di immagini; qui serve che si legga.
            L'unica sezione con due CTA oltre all'hero: la doppia porta
            ha senso, perche' i due gesti sono davvero diversi
            (candidarsi / farsi due domande prima). */}
        <Section tone="cream" rhythm="screen" labelledBy="hp-pros-title"
                 width="max-w-6xl" className="border-b border-[#1e2f28]/[0.07]">
          <div data-testid="hp-pros">
            <p className="eyebrow mb-5">
              {t('nwHome.prosEyebrow', { defaultValue: "Per gli operatori" })}
            </p>
            <DisplayTitle as="h2" id="hp-pros-title" size="section" measure="tight">
              {t('nwHome.prosTitle', { defaultValue: "Il tuo lavoro merita più di un profilo." })}
            </DisplayTitle>
            <Lede size="lead" className="mt-7">
              {t('nwHome.prosP1', { defaultValue: "Aurya nasce per dare ai professionisti del benessere uno spazio che cresca insieme alla loro attività." })}
            </Lede>
            <Lede size="body" className="mt-5">
              {t('nwHome.prosP2', { defaultValue: "Oggi significa raccontare il tuo percorso. Domani significherà anche ricevere richieste, pubblicare servizi, organizzare esperienze, raccogliere recensioni e gestire tutto da un unico luogo." })}
            </Lede>
            <Lede size="body" className="mt-5">
              {t('nwHome.prosP3', { defaultValue: "Stiamo costruendo tutto questo insieme ai primi professionisti che scelgono di far parte della rete." })}
            </Lede>
            <div className="mt-9 flex flex-col items-start gap-5 sm:flex-row sm:items-center sm:gap-8">
              <EditorialCta to="/entra-nella-rete" variant="solid" data-testid="hp-pros-cta">
                {t('nwHome.prosCta', { defaultValue: "Entra tra i primi operatori" })}
              </EditorialCta>
              <EditorialCta to={OPERATOR_FORM_PATH} variant="quiet" data-testid="hp-pros-cta-alt">
                {t('nwHome.prosCtaAlt', { defaultValue: "Parliamone" })}
              </EditorialCta>
            </div>
          </div>
        </Section>

        {/* ── 7. LA LETTERA — restare ──────────────────────────────
            Il testo e' fatto di frasi cortissime: la misura di riga qui
            e' stretta apposta (max-w-[30ch]), cosi' le frasi cadono
            una per riga e il ritmo si vede invece di doverlo
            immaginare. La chiusa scende di tono: e' il commento, non
            l'elenco. Fondo sabbia: la pagina si chiude un gradino piu'
            caldo di dove e' cominciata. */}
        <Section tone="sand" rhythm="screen" labelledBy="hp-letter-title"
                 width="max-w-6xl">
          <div data-testid="hp-letter">
            <DisplayTitle as="h2" id="hp-letter-title" size="section" measure="tight">
              {t('nwHome.letterTitle', { defaultValue: "Ricevi la Lettera di Aurya." })}
            </DisplayTitle>
            <Lede size="lead" className="mt-7 max-w-[30ch]">
              {t('nwHome.letterBody', { defaultValue: "Una volta ogni tanto. Una persona da conoscere. Una pratica da capire. Un luogo da scoprire." })}
            </Lede>
            <Lede size="body" tone="quiet" className="mt-4 max-w-[30ch]">
              {t('nwHome.letterClose', { defaultValue: "Niente rumore. Solo ciò che vale il tuo tempo." })}
            </Lede>
            <div className="mt-9">
              <EditorialCta to="/newsletter" variant="quiet" data-testid="hp-letter-cta">
                {t('nwHome.letterCta', { defaultValue: "Iscriviti" })}
              </EditorialCta>
            </div>
          </div>
        </Section>

      </div>
    </MarketplaceShell>
  );
}
