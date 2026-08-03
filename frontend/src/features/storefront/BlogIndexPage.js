/**
 * BlogIndexPage — /blog e /blog/categoria/:slug (SW4).
 *
 * Il Magazine e' il primo anello del flywheel (Blueprint cap. 10): e'
 * la superficie che oggi porta le persone qui. Fino a SW4 l'indice era
 * l'unica pagina di racconto rimasta alla grammatica vecchia (hero
 * fotografico generico, card con bordo, ombra e bottone "Leggi"),
 * mentre home, Manifesto e Chi siamo parlavano gia' il kit editoriale.
 * Adesso sono sorelle.
 *
 * Tre battute, nessuno stile nuovo:
 *   1. APERTURA   il dispositivo a coppia del Blueprint, cap. 9:
 *                 "Le cose serie vanno spiegate." (una verita' sul
 *                 mondo) e "Scriviamo." (il nostro gesto). Sotto,
 *                 cosa ci trovi; poi i filtri come chip sobri.
 *   2. LA VETRINA fondo bianco, come la sezione "Dal Magazine" della
 *                 home ma piu' ampia: l'articolo di apertura con la
 *                 copertina larga, poi tutti gli altri due per riga,
 *                 copertina grande e testo sotto (SW4b).
 *   3. LA LETTERA la fascia newsletter, invariata (BN1).
 *
 * La pagina di CATEGORIA e' la stessa, con l'apertura che cambia
 * titolo: il nome della categoria al posto della coppia, e una riga
 * che non promette niente che non ci sia.
 *
 * Regola lingua ereditata dal marketplace: in lingua X si vedono solo
 * gli articoli tradotti in X (mai fallback in lista). I chip mostrano
 * solo le categorie che hanno articoli, e sono <Link>: la categoria e'
 * una rotta vera e indicizzabile, non un bottone che naviga.
 *
 * DS3 (2/8/2026) — il disegno, non le parole. La struttura della
 * vetrina resta quella approvata dal founder (copertina larga in
 * apertura, poi due per riga con la copertina grande e il testo sotto):
 * quello che mancava era il CARATTERE attorno. Tre interventi:
 *   1. APERTURA FOTOGRAFICA. La coppia "Le cose serie vanno spiegate. /
 *      Scriviamo." stava sopra il crema vuoto. Ora sta DENTRO
 *      `hero-blog` (l'assegnazione del ciclo DS per il Magazine), che e'
 *      la foto piu' scura del magazzino dopo r04: velo calcolato, non
 *      sperato (misure sotto). Sulla pagina di categoria cambia il
 *      titolo, non il dispositivo.
 *   2. LA SOGLIA. Sotto l'apertura, sul crema, restano il sottotitolo,
 *      il payoff e i filtri — che diventano una vera barra di
 *      navigazione: pastiglie piu' grandi, cliccabili col pollice
 *      (40px di altezza), separate dal testo da un filo d'oro, e
 *      presenti anche quando c'e' una categoria sola, perche' da una
 *      pagina di categoria si deve poter tornare a "Tutti".
 *   3. GLI STATI VUOTI. Erano una riga grigia in mezzo al bianco. Ora
 *      hanno un titolo, un filo e una porta d'uscita (torna a Tutti):
 *      un vuoto raccontato e' una pagina, un vuoto muto e' un errore.
 *
 * Fondi: FOTO scura → crema → bianco → sabbia. Nessuna ancora verde
 * piena: il verde qui e' gia' nelle copertine, che da SW4 sono un
 * medaglione salvia su ogni scheda. Una fascia verde in piu' le
 * avrebbe spente.
 *
 * CONTRASTI MISURATI (minimo AA 4,5:1 corpo, 3:1 display). Non
 * stimati: presi NEL BROWSER, rendendo invisibile il testo (che
 * continua a occupare il suo posto), catturando la schermata e
 * leggendo il pixel piu' chiaro dentro il rettangolo che quel testo
 * occupa davvero — a 1440 e a 390:
 *   titolo, crema #f6f2e8 ..................... 8,07:1 / 7,22:1
 *   occhiello oro #d6c49a ..................... 6,13:1 / 6,13:1
 *   pastiglia attiva, crema su salvia #2f5749 ...... 7,28:1
 *   pastiglia a riposo, #2f5749 su crema ........... 7,68:1
 *   testo degli stati vuoti, #212C28 al 70% ........ 5,46:1 (bianco)
 * Il ritaglio scelto (65% 20%) e' quello che tiene il sole — il solo
 * punto luminoso della foto — fuori dalla colonna delle parole.
 */
import React, { useEffect, useMemo, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { ArrowLeft, Lock } from 'lucide-react';
import api from '../../api/client';
import MarketplaceShell from './components/MarketplaceShell';
import BlogNewsletterCTA from './components/BlogNewsletterCTA';
import MagazineCategoryNav, { coloreCategoria } from './components/MagazineCategoryNav';
import CategorySigil from './components/CategorySigil';
import { PRO_CATEGORY } from './BlogArticlePage';
import introPerCategoria from './blogCategoryIntros';
import useSeoMeta from './lib/useSeoMeta';
import BrandPayoff from '../../components/BrandPayoff';
import {
  Section, DisplayTitle, TitleLine, Lede, ArticleCard, EditorialCta, PhotoOpener,
} from '../../components/editorial';

/* MG1 — quanti articoli per pagina prima di "Mostra altri".
   Dodici: sei righe da due sul desktop, che e' quanto una persona
   scorre prima di decidere se questo posto le interessa. Sotto i 12
   la lista sembrerebbe povera, sopra i 12 torna il muro. */
const PER_PAGINA = 12;
/* Dopo quante schede si infila la proposta della lettera. Sei: dopo
   l'apertura e due righe, cioe' quando chi legge ha visto abbastanza
   da sapere se gli interessa. */
const LETTERA_DOPO = 6;

/* MG1 — le pastiglie testuali sono state sostituite da
   MagazineCategoryNav: con dodici categorie una fila di parole
   costringeva a leggerle tutte per trovarne una, e non diceva niente
   su cosa ci fosse dentro. Le costanti CHIP sono uscite con loro. */

/* L'apertura del Magazine (DS §Il magazzino foto): `hero-blog` e' la
   sua foto assegnata, e non compare su nessuna pagina vicina. */
const OPENER_PHOTO = '/media/hero-blog.webp';

export default function BlogIndexPage() {
  const { t, i18n } = useTranslation('landings');
  const { categoria: routeCategory } = useParams();
  const [searchParams] = useSearchParams();
  // BN5 — la categoria vive nell'URL come rotta vera (/blog/categoria/x,
  // indicizzabile); il query param resta solo come fallback dei vecchi
  // link condivisi
  const category = routeCategory || searchParams.get('categoria') || '';
  const lang = (i18n.language || 'it').slice(0, 2);

  const [items, setItems] = useState([]);
  const [allItems, setAllItems] = useState([]);   // per i chip categoria
  const [loading, setLoading] = useState(true);

  const catLabel = (slug) => (slug ? t(`categories.${slug}`, { defaultValue: slug }) : '');
  /* PC1 — l'introduzione della categoria, se ne ha una. */
  const intro = introPerCategoria(category);
  useSeoMeta({
    title: category
      ? t('blog.seoCatTitle', { cat: catLabel(category), defaultValue: '{{cat}}: articoli e guide | Il Magazine di Aurya' })
      : t('blog.seoTitle', { defaultValue: 'Ritiri, discipline olistiche e benessere | Il Magazine di Aurya' }),
    description: t('blog.seoDesc', { defaultValue: 'Storie, pratiche e sapere olistico da chi organizza e vive i ritiri.' }),
    canonicalPath: category ? `/blog/categoria/${category}` : '/blog',
  });

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    const params = { lang, page_size: 50 };
    api.get('/public/articles', { params })
      .then(res => {
        if (!mounted) return;
        const all = res.data?.items || [];
        setAllItems(all);
        /* OF4 (decisione founder 2/8) — il Magazine e' per chi CERCA il
           benessere. Gli articoli scritti per chi lo pratica di mestiere
           (fiscalita', prezzo di un ritiro, come riempirlo) uscivano
           nello stesso elenco, e chi arrivava cercando "cos'e' il reiki"
           capiva che questo posto non era per lui.
           NON si cancellano e NON cambiano indirizzo: restano su
           /blog/:slug (le pagine indicizzate valgono), e il loro elenco
           resta su /blog/categoria/operatori, che diventa la sezione
           dedicata raggiungibile dal mondo dei professionisti. Sparisce
           solo dall'indice generale e dalle pillole delle categorie. */
        setItems(category
          ? all.filter(a => a.category === category)
          : all.filter(a => a.category !== PRO_CATEGORY));
      })
      .catch(() => { if (mounted) { setAllItems([]); setItems([]); } })
      .finally(() => { if (mounted) setLoading(false); });
    return () => { mounted = false; };
  }, [lang, category]);

  /* MG1 — le categorie ordinate per ricchezza, non per ordine di
     comparsa nel database: chi guarda la navigazione deve trovare per
     prime le stanze piene. Con il conteggio a fianco, che dice se
     dietro una porta c'e' una stanza o un ripostiglio. */
  const { categoriesWithArticles, conteggi, totalePubblico } = useMemo(() => {
    /* OF4 — la pillola "Per gli operatori" esce dal filtro: e' la sezione
       dei professionisti, non una lettura del Magazine. La sua pagina
       (/blog/categoria/operatori) resta viva e raggiungibile da li'. */
    const conte = {};
    allItems.forEach(a => {
      if (a.category && a.category !== PRO_CATEGORY) {
        conte[a.category] = (conte[a.category] || 0) + 1;
      }
    });
    const slugs = Object.keys(conte).sort(
      (a, b) => conte[b] - conte[a] || a.localeCompare(b));
    return {
      categoriesWithArticles: slugs,
      conteggi: conte,
      totalePubblico: slugs.reduce((n, s) => n + conte[s], 0),
    };
  }, [allItems]);

  /* MG1 — la paginazione. Si azzera quando cambia categoria o lingua,
     altrimenti si entra in una categoria da cinque articoli con la
     lista gia' "espansa" da quella precedente. */
  const [quanti, setQuanti] = useState(PER_PAGINA);
  useEffect(() => { setQuanti(PER_PAGINA); }, [category, lang]);

  const fmtDate = (iso) => {
    if (!iso) return '';
    try {
      return new Date(iso).toLocaleDateString(lang, { day: 'numeric', month: 'long', year: 'numeric' });
    } catch { return ''; }
  };

  /* BN3 — la promessa si vede gia' in lista: la guida riservata lo
     dice qui, non dopo il clic. */
  const gatedBadge = (a) => (a.gated ? (
    <span className="inline-flex items-center gap-1 rounded-full bg-[#8a7440]/12 px-2 py-0.5 text-[11px] font-medium text-[#7a6636]"
          data-testid="blog-card-gated">
      <Lock className="h-3 w-3" aria-hidden />
      {t('blog.gatedBadge', { defaultValue: 'Per gli iscritti' })}
    </span>
  ) : null);

  const card = (a, variant, eager = false) => (
    <ArticleCard key={a.slug} article={a} variant={variant} eager={eager}
                 category={catLabel(a.category)}
                 date={fmtDate(a.published_at)}
                 badge={gatedBadge(a)} />
  );

  const [lead, ...altri] = items;      // l'apertura, poi la griglia
  /* MG1 — quanti ne mostriamo adesso: l'apertura non si conta, e'
     sempre visibile. `restanti` alimenta sia il bottone sia la riga
     "x di y", che e' l'unica cosa che dice a chi legge quanto manca. */
  const visibili = altri.slice(0, quanti);
  const restanti = altri.length - visibili.length;

  return (
    <MarketplaceShell noSearch>
      <div className="bg-background">

        {/* ── 1. APERTURA — dentro la fotografia ───────────────────
            Il dispositivo a coppia sta in due <TitleLine>: sono due
            frasi, non un a-capo estetico, e in ogni lingua restano
            due righe. Sulla pagina di categoria la coppia lascia il
            posto al nome della categoria: li' il titolo deve dire
            dove sei, non ripetere la tesi del Magazine.
            DS3 — la coppia ha smesso di galleggiare sul crema: sta
            dentro `hero-blog`, col velo calcolato di PhotoOpener. Il
            sottotitolo scende alla soglia chiara qui sotto, come sulla
            landing operatori (che e' la pagina approvata): il titolo
            sta sulla foto, l'argomento si legge sul chiaro. */}
        {category ? (
          /* MG1 — LA TESTATA DI CATEGORIA, compatta.
             Prima anche qui c'era la fotografia alta, ed era il primo
             dei tre motivi per cui gli articoli cominciavano a 6,5
             schermate dall'alto (misurato su /blog/categoria/yoga).
             Il ragionamento e' semplice: la fotografia grande e' la
             DICHIARAZIONE del Magazine, e si fa una volta sola,
             all'ingresso. Chi e' dentro una categoria ci e' arrivato
             apposta e vuole gli articoli, non un secondo benvenuto.
             Il colore della categoria resta, ed e' lo stesso delle
             sue copertine: dice dove sei prima che tu legga il titolo.
             Non come filo sottile in alto pero' — sotto la riga verde
             dell'header del sito sarebbe invisibile, e per la categoria
             yoga, che e' verde, si confonderebbe proprio con quella.
             Tinge invece tutto il fondo della testata, appena
             percettibile: abbastanza da riconoscere la stanza a colpo
             d'occhio, abbastanza poco da non litigare col crema del
             resto della pagina. */
          <header data-testid="mag-open-cat"
                  className="relative overflow-hidden pb-10 pt-12 lg:pb-12 lg:pt-14"
                  style={{ backgroundColor: `${coloreCategoria(category)}1c` }}>
            {/* MG2 — il segno della categoria in grande, come filigrana
                sulla destra. E' lo stesso disegno che sta sulle
                copertine di tutti gli articoli qui sotto: chi scende lo
                ritrova dodici volte in piccolo, e la testata smette di
                essere un titolo su un fondo colorato.
                Sta al 9% e sborda a destra, dove non c'e' testo — la
                colonna delle parole arriva al massimo a meta' pagina.
                Su telefono sparisce: li' lo spazio a destra non c'e', e
                una filigrana sotto il titolo sarebbe solo rumore. */}
            <CategorySigil
              categoria={category}
              spessore={1.6}
              style={{ color: coloreCategoria(category) }}
              className="pointer-events-none absolute -right-16 -top-12 hidden h-[26rem]
                         w-[26rem] opacity-[0.10] sm:block"
            />
            {/* Il padding orizzontale sta sul contenitore INTERNO, non
                sull'header: e' cosi' che lo mette Section, e con la
                struttura opposta il titolo partiva 32 px piu' a
                sinistra della griglia e dell'introduzione. Due colonne
                che dovrebbero allinearsi e non lo fanno si notano anche
                senza righello. */}
            <div className="relative mx-auto max-w-6xl px-6 sm:px-8">
              <Link to="/blog"
                    className="inline-flex items-center gap-1.5 text-[13px] text-[#2f5749]
                               underline-offset-4 hover:underline focus-visible:outline-none
                               focus-visible:ring-2 focus-visible:ring-[#2f5749]
                               focus-visible:ring-offset-2 focus-visible:ring-offset-[#f6f2e8]"
                    data-testid="mag-back">
                <ArrowLeft className="h-3.5 w-3.5" aria-hidden />
                {t('blog.backToBlogShort', { defaultValue: 'Magazine' })}
              </Link>
              <DisplayTitle as="h1" id="mag-title" size="section" measure="title"
                            className="mt-4 text-[2rem] sm:text-[2.6rem] lg:text-[3rem]">
                {catLabel(category)}
              </DisplayTitle>
              {/* La misura la impone il CONTENITORE, non una classe
                  sul componente: Lede porta gia' un suo max-w-[62ch] e
                  fra due utility della stessa famiglia non vince quella
                  scritta dopo nella stringa, vince quella che sta dopo
                  nel foglio di stile. Risultato misurato: il testo
                  arrivava 81 px dentro la filigrana. */}
              <div className="mt-4 max-w-2xl">
                <Lede size="lead">
                  {intro?.lede
                   || t('blog.catSubtitle', { defaultValue: 'Quello che abbiamo scritto su questo tema.' })}
                </Lede>
              </div>
            </div>
          </header>
        ) : (
          <PhotoOpener
            data-testid="mag-open"
            image={OPENER_PHOTO}
            focus="65% 20%"
            height="tall"
            align="left"
            width="max-w-3xl"
            labelledBy="mag-title"
            eyebrow={t('blog.eyebrow', { defaultValue: 'Il Magazine' })}
          >
            <DisplayTitle as="h1" id="mag-title" size="heroLines" measure="lines"
                          className="text-hero-shadow">
              <TitleLine>
                {t('blog.lead1', { defaultValue: 'Le cose serie vanno spiegate.' })}
              </TitleLine>
              <TitleLine>
                {t('blog.lead2', { defaultValue: 'Scriviamo.' })}
              </TitleLine>
            </DisplayTitle>
          </PhotoOpener>
        )}

        {/* ── LA SOGLIA — cosa ci trovi, e come ci si muove ────────
            Il crema subito sotto la foto: una riga che dice di che si
            tratta, il payoff, e la barra delle categorie. E' anche il
            posto in cui si capisce dove si e': la pastiglia piena e'
            una sola. */}
        {/* MG1 — LA SOGLIA esiste solo sull'indice. Sulla pagina di
            categoria il suo contenuto (dove sei, di che si tratta) e'
            gia' nella testata compatta qui sopra, e ripeterlo era il
            secondo motivo per cui gli articoli finivano lontani. */}
        {!category && (
          <Section tone="cream" rhythm="flow" width="max-w-6xl">
            <div data-testid="mag-soglia">
              <div className="max-w-3xl">
                <Lede size="lead">
                  {t('blog.subtitle', { defaultValue: 'Pratiche, luoghi e persone, raccontati per quello che sono. Senza scorciatoie.' })}
                </Lede>
                <BrandPayoff tone="cream" size="sm" className="mt-8" />
              </div>

              {/* MG1 — le categorie diventano una navigazione che si
                  guarda. Ogni scheda porta il colore che quella
                  categoria ha gia' sulle sue copertine, e il numero di
                  articoli: dice se dietro la porta c'e' una stanza o un
                  ripostiglio, che e' l'informazione che manca di piu'
                  quando si sceglie dove entrare. */}
              {categoriesWithArticles.length > 1 && (
                <div className="mt-12 border-t border-[#8a7440]/25 pt-10">
                  <p className="eyebrow mb-5">
                    {t('blog.catNavTitle', { defaultValue: 'Scegli un tema' })}
                  </p>
                  <MagazineCategoryNav
                    categorie={categoriesWithArticles}
                    conteggi={conteggi}
                    attiva=""
                    totale={totalePubblico}
                  />
                </div>
              )}
            </div>
          </Section>
        )}

        {/* ── L'INTRODUZIONE DELLA CATEGORIA (PC1) ─────────────────
            Una pagina di categoria che elenca e basta non e' un hub,
            e' un indice: non dice di che si tratta e non passa
            autorita' a nessuno. Qui l'argomento viene presentato e
            le porte portano ai figli con un'ancora vera, che e' il
            tipo di link che conta.
            Sta DOPO le pastiglie (da una categoria si deve poter
            tornare subito indietro) e PRIMA della griglia, perche'
            e' l'inquadramento di quello che si sta per vedere.
            Le categorie senza introduzione restano come prima. */}
        {/* MG1 — L'INTRODUZIONE SI SPEZZA IN DUE, ed era il terzo motivo
            per cui gli articoli cominciavano lontani: da sola misurava
            2875 px, cioe' quasi quattro schermate di premessa prima di
            vedere un titolo.
            Sopra la griglia resta il PRIMO paragrafo, che inquadra
            l'argomento. Il resto e le porte scendono sotto gli
            articoli, dove servono di piu': chi ha appena scorso le
            copertine e non ha trovato la sua strada e' esattamente chi
            ha bisogno di "da dove partire". */}
        {/* La fascia e' larga come la griglia e il testo dentro sta a
              sinistra nella sua misura di lettura. Con width max-w-3xl
              la Section centrava il paragrafo, che partiva rientrato
              rispetto al titolo sopra e alle copertine sotto: una
              colonna sola disallineata si legge come un errore di
              impaginazione, non come una scelta. */}
        {intro && (
          <Section tone="sand" rhythm="tight" width="max-w-6xl"
                   labelledBy="mag-cat-intro">
            <h2 id="mag-cat-intro" className="sr-only">
              {catLabel(category)}
            </h2>
            <Lede size="body" className="max-w-3xl">{intro.paragrafi[0]}</Lede>
          </Section>
        )}

        {/* ── 2. LA VETRINA ────────────────────────────────────────
            Bianco pieno, come la sezione "Dal Magazine" della home:
            le copertine sono medaglioni scuri e sul bianco si staccano
            come oggetti.
            SW4b — il ritmo cambia: le miniature di fianco erano
            francobolli ("copertine piu' grandi e testo sotto",
            founder 31/7). Adesso l'apertura ha la sua copertina larga
            e gli altri scendono DUE per riga, immagine sopra e testo
            sotto, sotto una riga sottile: l'unico separatore della
            pagina. Con un articolo solo resta solo l'apertura. */}
        <Section tone="paper" rhythm="flow" width="max-w-6xl">
          {loading ? (
            /* L'attesa non deve muovere la pagina: il posto della prima
               copertina e' gia' prenotato, nel suo 40:21, col fondo
               sabbia delle copertine che arrivano. */
            <div className="max-w-3xl" aria-live="polite" aria-busy="true">
              <div aria-hidden className="aspect-[40/21] w-full rounded-2xl bg-[#e8e2d4]" />
              <span className="sr-only">…</span>
            </div>
          ) : items.length === 0 ? (
            /* Lo stato vuoto: un titolo, un filo e una porta. Prima era
               una riga grigia sospesa nel bianco, che si legge come un
               guasto invece che come una notizia. */
            <div data-testid="blog-empty" className="max-w-[46ch] py-4">
              <DisplayTitle as="p" size="section" measure="title"
                            className="text-[1.5rem] sm:text-[1.8rem] lg:text-[2rem]">
                {category
                  ? t('blog.emptyCat', { defaultValue: "Su questo tema non abbiamo ancora scritto." })
                  : t('blog.empty', { defaultValue: "Non c'è ancora niente da leggere in questa lingua." })}
              </DisplayTitle>
              <div aria-hidden className="gold-rule mt-8 max-w-[8rem]" />
              {category && (
                <p className="mt-8">
                  <EditorialCta to="/blog" variant="quiet">
                    {t('blog.backToBlog', { defaultValue: 'Torna al Magazine' })}
                  </EditorialCta>
                </p>
              )}
            </div>
          ) : (
            <div data-testid="blog-list">
              {/* l'apertura: una copertina sola, larga, e il testo
                  sotto. Sta in max-w-3xl e non a tutta la fascia
                  perche' a 1152 px un 40:21 diventa alto 600 px e
                  mangia lo schermo intero. */}
              <div className="max-w-3xl">
                {card(lead, 'lead', true)}
              </div>

              {altri.length > 0 && (
                <div className="mt-16 border-t border-foreground/10 pt-14">
                  <p className="eyebrow mb-10">
                    {t('blog.moreTitle', { defaultValue: 'Altri articoli' })}
                  </p>
                  {/* due per riga, non tre: le copertine restano grandi
                      e il testo sotto ha la sua misura. Sul telefono
                      una sola, con l'aria in mezzo. */}
                  <div className="grid gap-y-14 sm:grid-cols-2 sm:gap-x-10 lg:gap-x-14 lg:gap-y-16">
                    {visibili.map((a, i) => (
                      /* MG1 — LA LETTERA DENTRO LA GRIGLIA. In fondo alla
                         pagina nessuno la vedeva: su una categoria da
                         cinque articoli arrivava a 12,5 schermate
                         dall'alto. Qui occupa una cella come una scheda
                         qualsiasi, alla settima posizione, e non
                         interrompe niente — chi sta scorrendo la trova
                         mentre guarda, non dopo aver finito.
                         Sta nella griglia e non in una fascia a tutta
                         larghezza proprio per questo: una fascia
                         spezza, una cella si affianca. */
                      i === LETTERA_DOPO ? (
                        <React.Fragment key="lettera-inline">
                          <aside data-testid="mag-lettera-inline"
                                 className="rounded-2xl bg-[#f2ece0] p-6 sm:p-7">
                            <BlogNewsletterCTA category={category || null} />
                          </aside>
                          {card(a, 'compact')}
                        </React.Fragment>
                      ) : card(a, 'compact')
                    ))}
                  </div>

                  {/* MG1 — la paginazione. Con trentatre' articoli la
                      pagina era un muro di sedici schermate: si mostra
                      una manciata e si chiede se si vuole il resto.
                      E' un bottone e non una rotta ?pagina=2 perche'
                      gli articoli restano tutti nella stessa pagina
                      indicizzata: la porzione nascosta e' un fatto di
                      lettura, non di indicizzazione. */}
                  {restanti > 0 && (
                    <div className="mt-16 flex flex-col items-center gap-3">
                      <button
                        type="button"
                        data-testid="mag-mostra-altri"
                        onClick={() => setQuanti(q => q + PER_PAGINA)}
                        className="inline-flex min-h-[2.75rem] items-center rounded-full
                                   border border-[#2f5749] px-7 py-2.5 text-[13px]
                                   font-medium uppercase tracking-[0.12em] text-[#2f5749]
                                   transition-colors hover:bg-[#2f5749] hover:text-[#f6f2e8]
                                   focus-visible:outline-none focus-visible:ring-2
                                   focus-visible:ring-[#2f5749] focus-visible:ring-offset-2">
                        {t('blog.showMore', { defaultValue: 'Mostra altri articoli' })}
                      </button>
                      <p className="text-[13px] text-foreground/55" aria-live="polite">
                        {t('blog.showMoreCount', {
                          shown: items.length - restanti, total: items.length,
                          defaultValue: '{{shown}} di {{total}}',
                        })}
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </Section>

        {/* MG1 — LA SECONDA META' DELL'INTRODUZIONE, e le porte.
            Sotto gli articoli e non sopra: chi ha appena scorso le
            copertine senza trovare la sua strada e' esattamente chi ha
            bisogno di sentirsi dire da dove partire. Sopra la griglia
            era una premessa da superare, qui e' una risposta. */}
        {intro && (intro.paragrafi.length > 1 || intro.porte?.length > 0) && (
          <Section tone="sand" rhythm="flow" width="max-w-3xl"
                   labelledBy="mag-cat-piu">
            <h2 id="mag-cat-piu" className="eyebrow mb-6">
              {t('blog.catMore', { defaultValue: 'Su questo tema' })}
            </h2>
            {intro.paragrafi.slice(1).map((p, i) => (
              <Lede key={i} size="body" className={i ? 'mt-5' : undefined}>{p}</Lede>
            ))}
            {intro.porte?.length > 0 && (
              <div className="mt-10 border-t border-[#8a7440]/25 pt-8">
                <p className="eyebrow mb-5">
                  {t('blog.catStartHere', { defaultValue: 'Da dove partire' })}
                </p>
                <ul className="list-none space-y-3 p-0">
                  {intro.porte.map(porta => (
                    <li key={porta.to}>
                      <EditorialCta to={porta.to} variant="quiet">
                        {porta.label}
                      </EditorialCta>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </Section>
        )}

        {/* MG1 — IL CAMBIO DI TEMA, in fondo alla categoria.
            Prima, arrivati in fondo a una categoria, l'unica strada era
            il tasto indietro del browser: le pastiglie erano rimaste
            dodici schermate piu' su. Qui la navigazione visiva torna
            dov'e' utile, cioe' nel punto in cui uno ha finito di
            leggere e si chiede cos'altro c'e'. */}
        {category && categoriesWithArticles.length > 1 && (
          <Section tone="cream" rhythm="flow" width="max-w-6xl"
                   labelledBy="mag-altri-temi">
            <h2 id="mag-altri-temi" className="eyebrow mb-6">
              {t('blog.catNavOther', { defaultValue: 'Cambia tema' })}
            </h2>
            <MagazineCategoryNav
              categorie={categoriesWithArticles}
              conteggi={conteggi}
              attiva={category}
              totale={totalePubblico}
            />
          </Section>
        )}

        {/* ── 3. LA LETTERA — il Magazine converte (BN1) ─────────
            Resta anche in fondo: chi arriva qui ha letto tutto e non ha
            cliccato la versione dentro la griglia, ed e' il momento in
            cui la proposta costa meno. La versione inline non la
            sostituisce, la anticipa. */}
        <Section tone="sand" rhythm="flow" width="max-w-2xl">
          <BlogNewsletterCTA category={category || null} />
        </Section>

        {/* ── 4. IL PONTE VERSO LE PERSONE (OF1) ───────────────────
            Il Magazine e' la porta d'ingresso principale del sito (i
            venti articoli sono oggi l'unico canale che porta traffico)
            ed era un vicolo cieco: dal corpo di questa pagina non
            partiva un solo link verso la rete, il manifesto o la
            candidatura. Chi non si iscriveva alla lettera usciva.
            Sta DOPO il modulo e non prima per una ragione precisa: la
            lettera resta la conversione principale dell'indice, e un
            secondo invito messo sopra le avrebbe rubato l'attenzione.
            Qui invece raccoglie chi ha gia' detto di no. */}
        <Section tone="paper" rhythm="flow" width="max-w-3xl"
                 labelledBy="blog-people-title">
          <DisplayTitle as="h2" id="blog-people-title" size="section" measure="title"
                        className="text-[1.7rem] sm:text-[2.1rem] lg:text-[2.4rem]">
            {t('blog.peopleBridgeTitle', { defaultValue: 'Dietro ogni articolo ci sono delle persone.' })}
          </DisplayTitle>
          <Lede size="body" className="mt-6">
            {t('blog.peopleBridgeBody', { defaultValue: 'Quello che scriviamo nasce parlando con chi fa questo lavoro tutti i giorni. Sono loro la parte che conta.' })}
          </Lede>
          <p className="mt-8">
            <EditorialCta to="/operatori" variant="quiet">
              {t('blog.peopleBridgeCta', { defaultValue: 'Conosci la rete' })}
            </EditorialCta>
          </p>
        </Section>
      </div>
    </MarketplaceShell>
  );
}
