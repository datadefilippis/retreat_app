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
import { Lock } from 'lucide-react';
import api from '../../api/client';
import MarketplaceShell from './components/MarketplaceShell';
import BlogNewsletterCTA from './components/BlogNewsletterCTA';
import useSeoMeta from './lib/useSeoMeta';
import BrandPayoff from '../../components/BrandPayoff';
import {
  Section, DisplayTitle, TitleLine, Lede, ArticleCard, EditorialCta, PhotoOpener,
} from '../../components/editorial';

/* La pastiglia: sobria per definizione. Stesso verde e stesso tracking
   dell'occhiello di ArticleCard, cosi' il filtro e la scheda si
   leggono come la stessa classificazione detta due volte.
   DS3 — piu' grande (min-h 2,5rem: un bersaglio da pollice, prima erano
   28px), e a riposo un contorno invece di un fondo tinto: cosi' la
   pastiglia ATTIVA e' l'unica piena della riga e si vede da lontano
   dove si e'. */
const CHIP = `inline-flex min-h-[2.5rem] items-center rounded-full border px-4 py-2
              text-[11px] font-medium uppercase tracking-[0.12em] transition-colors
              focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2f5749]
              focus-visible:ring-offset-2 focus-visible:ring-offset-background`;
const CHIP_ON = 'border-[#2f5749] bg-[#2f5749] text-[#f6f2e8]';
const CHIP_OFF = 'border-[#2f5749]/25 text-[#2f5749] hover:border-[#2f5749]/60 hover:bg-[#2f5749]/[0.06]';

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
        setItems(category ? all.filter(a => a.category === category) : all);
      })
      .catch(() => { if (mounted) { setAllItems([]); setItems([]); } })
      .finally(() => { if (mounted) setLoading(false); });
    return () => { mounted = false; };
  }, [lang, category]);

  const categoriesWithArticles = useMemo(() => {
    const seen = new Set(allItems.map(a => a.category).filter(Boolean));
    return [...seen];
  }, [allItems]);

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
            {category ? catLabel(category) : (
              <>
                <TitleLine>
                  {t('blog.lead1', { defaultValue: 'Le cose serie vanno spiegate.' })}
                </TitleLine>
                <TitleLine>
                  {t('blog.lead2', { defaultValue: 'Scriviamo.' })}
                </TitleLine>
              </>
            )}
          </DisplayTitle>
        </PhotoOpener>

        {/* ── LA SOGLIA — cosa ci trovi, e come ci si muove ────────
            Il crema subito sotto la foto: una riga che dice di che si
            tratta, il payoff, e la barra delle categorie. E' anche il
            posto in cui si capisce dove si e': la pastiglia piena e'
            una sola. */}
        <Section tone="cream" rhythm="flow" width="max-w-3xl">
          <div data-testid="mag-soglia">
            <Lede size="lead">
              {category
                ? t('blog.catSubtitle', { defaultValue: "Quello che abbiamo scritto su questo tema." })
                : t('blog.subtitle', { defaultValue: "Pratiche, luoghi e persone, raccontati per quello che sono. Senza scorciatoie." })}
            </Lede>
            <BrandPayoff tone="cream" size="sm" className="mt-8" />

            {/* i filtri: pastiglie, non bottoni pesanti, e link veri.
                Compaiono anche con una categoria sola quando si e'
                DENTRO una categoria: senza, da li' non si tornerebbe
                indietro se non col tasto del browser. */}
            {(categoriesWithArticles.length > 1 || category) && (
              <nav className="mt-10 border-t border-[#8a7440]/25 pt-8"
                   data-testid="blog-category-chips"
                   aria-label={t('blog.eyebrow', { defaultValue: 'Il Magazine' })}>
                <ul className="flex list-none flex-wrap gap-2.5 p-0">
                  <li>
                    <Link to="/blog"
                          className={`${CHIP} ${!category ? CHIP_ON : CHIP_OFF}`}
                          aria-current={!category ? 'page' : undefined}>
                      {t('blog.allArticles', { defaultValue: 'Tutti' })}
                    </Link>
                  </li>
                  {categoriesWithArticles.map(slug => (
                    <li key={slug}>
                      <Link to={`/blog/categoria/${slug}`}
                            className={`${CHIP} ${category === slug ? CHIP_ON : CHIP_OFF}`}
                            aria-current={category === slug ? 'page' : undefined}>
                        {catLabel(slug)}
                      </Link>
                    </li>
                  ))}
                </ul>
              </nav>
            )}
          </div>
        </Section>

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
                    {altri.map(a => card(a, 'compact'))}
                  </div>
                </div>
              )}
            </div>
          )}
        </Section>

        {/* ── 3. LA LETTERA — il Magazine converte (BN1) ───────── */}
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
