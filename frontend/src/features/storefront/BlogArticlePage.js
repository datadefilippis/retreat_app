/**
 * BlogArticlePage — /blog/:slug (AN5 per la sostanza, DS3 per il disegno).
 *
 * Dettaglio articolo nel guscio marketplace: markdown renderizzato col
 * renderer sicuro delle pagine legal (zero dipendenze, zero HTML).
 * Se la lingua attiva non ha traduzione il backend serve l'italiano e
 * lo dichiara (served_lang): la pagina lo dice con una nota onesta.
 *
 * IL COPY NON E' CAMBIATO DI UNA PAROLA (DS3 e' un passaggio di disegno):
 * stesse chiavi blog.*, stessi defaultValue, stesse quattro lingue.
 * Cambia dove stanno le cose, su che fondo e con che gerarchia.
 *
 * IL DIFETTO CHE SI CORREGGE (docs/DESIGN_PASS_DS_2026-08.md). Era
 * l'ultima pagina del Magazine ferma alla grammatica vecchia: una
 * colonna da 42rem con briciole grigie, il titolo in grassetto sans, la
 * copertina infilata a meta' come se fosse un allegato, il corpo del
 * pezzo con la tipografia dei documenti legali (prose-sm in
 * muted-foreground) e in fondo tre schede bordate senza copertina —
 * il debito segnalato dal founder.
 *
 * COSA FA ORA, IN ORDINE.
 *   APERTURA   ancora scura piena a tutta larghezza: briciole, titolo
 *              display, il sommario come sommario (era solo un meta tag)
 *              e la firma. Accanto, il SIGILLO: la copertina in 40:21.
 *   LETTURA    crema, colonna da 38rem: misura di lettura vera (~68
 *              caratteri), attacco piu' grande, capitoli in serif col
 *              filo d'oro. Le regole stanno in index.css (.blog-content),
 *              non nel renderer, che e' condiviso con /privacy.
 *   SOGLIA     sabbia: il gate delle guide riservate, che da riquadro
 *              dentro la colonna diventa una fascia intera — e' il muro,
 *              deve sembrarlo. Oppure la lettera, quando l'articolo e'
 *              aperto.
 *   RITIRI     verde, solo in fase marketplace: l'unica ancora tonale.
 *   CORRELATI  bianco: "Continua a leggere" con le COPERTINE (ArticleCard
 *              compact, le stesse dell'indice) al posto delle card
 *              bordate. Sotto, la porta di ritorno al Magazine.
 *
 * PERCHE' L'APERTURA NON E' UNA FOTO. Le copertine del Magazine sono
 * autogenerate: un sigillo verde scuro con dentro il nome della
 * categoria e il marchio. Stenderci sopra il titolo dell'articolo vuol
 * dire sovrapporre due testi grandi. E' un OGGETTO, non un'atmosfera:
 * sta accanto al titolo, in 40:21 (il suo rapporto esatto, nessun
 * ritaglio), e l'ancora scura fa da fondo. E' il terzo modo d'aprire
 * previsto dalla grammatica DS, l'accostamento foto/parola.
 *
 * ALTERNANZA DEI FONDI: scuro → crema → sabbia → [verde] → bianco.
 * Due sezioni adiacenti non hanno mai lo stesso fondo.
 *
 * CONTRASTI MISURATI (minimo AA: 4,5:1 corpo, 3:1 display).
 *   apertura, fondo pieno #0e1a15 (nessuna foto, nessun velo)
 *     crema #f6f2e8 .............................. 15,96:1
 *     crema al 90% (sommario, nota lingua) ....... 13,01:1
 *     crema al 75% (firma) ........................ 9,33:1
 *     briciole oro #d6c49a ....................... 10,38:1
 *   lettura, corpo #212C28 all'88% su crema ....... 9,48:1
 *   lettura, attacco al 95% ...................... 11,79:1
 *   soglia, corpo all'88% su sabbia ............... 8,70:1
 *   soglia, sottovoce al 70% su sabbia ............ 5,01:1
 *   ritiri, crema su salvia #2f5749 ............... 7,28:1
 *   correlati, titolo scheda su bianco ........... 14,43:1
 *
 * MOVIMENTO: solo la dissolvenza d'ingresso del kit e lo zoom lentissimo
 * delle copertine al passaggio del mouse, entrambi in motion-safe.
 */
import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import api from '../../api/client';
import MarketplaceShell from './components/MarketplaceShell';
import BlogNewsletterCTA from './components/BlogNewsletterCTA';
import LeadForm from '../prelaunch/LeadForm';
import { Lock } from 'lucide-react';
import useSeoMeta from './lib/useSeoMeta';
import { useSiteConfig } from '../../context/SiteConfigContext';
import LegalMarkdownRenderer from '../../components/legal/LegalMarkdownRenderer';
import {
  Section, DisplayTitle, Lede, EditorialCta, PhotoOpener, ArticleCard,
} from '../../components/editorial';

// Le categorie con una pagina /ritiri/{cat} prenotabile (tassonomia
// ritiri): SOLO queste hanno la CTA "Vivi un ritiro", e solo in fase
// marketplace. Le categorie editoriali (ritiri/energia/operatori) no.
const BOOKABLE_CATS = new Set(['yoga', 'meditazione', 'detox', 'suono',
  'massaggio', 'breathwork', 'cammini', 'femminile', 'aziendale']);

/* OF1 — l'unica categoria del Magazine scritta PER chi lavora nel
   benessere, non per chi lo cerca (fiscalita', prezzo di un ritiro,
   come riempirlo). Vive qui come costante perche' decide due cose
   diverse: quale porta compare in fondo all'articolo e, altrove,
   se l'articolo entra nell'indice del Magazine. */
export const PRO_CATEGORY = 'operatori';

/* Le briciole sull'ancora scura: oro chiaro, come l'occhiello delle
   aperture fotografiche (10,38:1 sul fondo #0e1a15). */
const CRUMB = `eyebrow eyebrow-light transition-colors hover:text-[#efe2bd]
               focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#f6f2e8]
               focus-visible:ring-offset-2 focus-visible:ring-offset-[#0e1a15] rounded-sm`;

export default function BlogArticlePage() {
  const { slug } = useParams();
  const { t, i18n } = useTranslation('landings');
  const { sitePhase } = useSiteConfig();
  const lang = (i18n.language || 'it').slice(0, 2);

  const [article, setArticle] = useState(null);
  const [related, setRelated] = useState([]);
  const [error, setError] = useState(false);

  useEffect(() => {
    let mounted = true;
    setArticle(null);
    setError(false);
    // BN3 — il token del subscriber confermato (salvato alla conferma)
    // sblocca le guide riservate; assente o invalido → anteprima
    let st = null;
    try { st = localStorage.getItem('aurya_nl_token') || null; } catch { /* private mode */ }
    api.get(`/public/articles/${slug}`, { params: { lang, st } })
      .then(res => { if (mounted) setArticle(res.data); })
      .catch(() => { if (mounted) setError(true); });
    return () => { mounted = false; };
  }, [slug, lang]);

  /* "Continua a leggere" (BN1, riscritto in PE7).
     Prima l'ordine era: stessa categoria, poi i piu' recenti. Con tre
     articoli in una categoria accosta pezzi che non c'entrano, e con
     le categorie piccole pesca a caso fra i recenti.
     Ora comanda il GRAFO CURATO (`related_slugs`, deciso a mano in
     scripts/pe7_link_interni.py): sono i correlati veri, nell'ordine
     in cui ha senso leggerli. L'automatismo resta sotto e riempie i
     posti che avanzano, cosi' nessun articolo resta senza coda anche
     se il grafo non lo copre. */
  useEffect(() => {
    if (!article) { setRelated([]); return; }
    let mounted = true;
    api.get('/public/articles', { params: { lang, page_size: 50 } })
      .then(res => {
        if (!mounted) return;
        const all = (res.data?.items || []).filter(a => a.slug !== slug);
        const perSlug = new Map(all.map(a => [a.slug, a]));
        const scelti = (article.related_slugs || [])
          .map(s => perSlug.get(s))
          .filter(Boolean);
        const presi = new Set(scelti.map(a => a.slug));
        const resto = all.filter(a => !presi.has(a.slug));
        const stessaCat = resto.filter(a => article.category && a.category === article.category);
        const altri = resto.filter(a => !stessaCat.includes(a));
        setRelated([...scelti, ...stessaCat, ...altri].slice(0, 3));
      })
      .catch(() => { if (mounted) setRelated([]); });
    return () => { mounted = false; };
  }, [article, slug, lang]);

  useSeoMeta({
    title: article ? `${article.title} | Aurya` : 'Blog | Aurya',
    description: article?.description || undefined,
    image: article?.featured_image_url || undefined,
    canonicalPath: `/blog/${slug}`,
  });

  const fmtDate = (iso) => {
    if (!iso) return '';
    try {
      return new Date(iso).toLocaleDateString(lang, { day: 'numeric', month: 'long', year: 'numeric' });
    } catch { return ''; }
  };
  const catLabel = (s) => (s ? t(`categories.${s}`, { defaultValue: s }) : '');

  if (error) {
    return (
      <MarketplaceShell noSearch>
        <div className="bg-background">
          {/* Anche il vicolo cieco e' una pagina: fondo, titolo display e
              una porta sola, invece di due righe grigie in mezzo al nulla. */}
          <Section tone="cream" rhythm="screen" width="max-w-2xl">
            <DisplayTitle as="h1" size="section" measure="title">
              {t('blog.notFound', { defaultValue: 'Articolo non trovato' })}
            </DisplayTitle>
            <div aria-hidden className="gold-rule mt-8 max-w-[10rem]" />
            <p className="mt-8">
              <EditorialCta to="/blog" variant="quiet">
                {t('blog.backToBlog', { defaultValue: 'Torna al Magazine' })}
              </EditorialCta>
            </p>
          </Section>
        </div>
      </MarketplaceShell>
    );
  }

  const cover = article?.featured_image_url;
  const gateOpen = article?.gated && !article?.unlocked;

  return (
    <MarketplaceShell noSearch>
      <div className="bg-background">
        {article && (
          <article data-testid="blog-article">

            {/* ── 1. APERTURA — l'ancora scura e il sigillo ─────────────
                PhotoOpener senza `image` e' il verde quasi nero pieno:
                nessun velo da sperare, contrasto fisso 15,96:1. La
                copertina sta accanto come oggetto, nel suo 40:21 esatto
                (nessun ritaglio: la cornice incisa resta intera). */}
            <PhotoOpener
              height="standard"
              align="left"
              width="max-w-6xl"
              labelledBy="art-title"
            >
              <div className="grid gap-10 lg:grid-cols-12 lg:items-center lg:gap-14">
                <div className={cover ? 'lg:col-span-7' : 'lg:col-span-9'}>
                  <nav aria-label={t('blog.title', { defaultValue: 'Il Magazine di Aurya' })}
                       className="mb-6 flex flex-wrap items-center gap-x-2.5 gap-y-1">
                    <Link to="/blog" className={CRUMB}>
                      {t('blog.title', { defaultValue: 'Il Magazine di Aurya' })}
                    </Link>
                    {article.category && (
                      <>
                        <span aria-hidden className="text-[#d6c49a]/70">›</span>
                        <Link to={`/blog/categoria/${article.category}`} className={CRUMB}>
                          {catLabel(article.category)}
                        </Link>
                      </>
                    )}
                  </nav>

                  <DisplayTitle as="h1" id="art-title" size="section" measure="wide"
                                className="text-hero-shadow">
                    {article.title}
                  </DisplayTitle>

                  {/* Il sommario esisteva gia' (article.description): era
                      solo un meta tag e una riga sotto le schede. Qui fa
                      il mestiere per cui e' stato scritto. */}
                  {article.description && (
                    <Lede size="lead" tone="inherit" className="mt-6 opacity-90">
                      {article.description}
                    </Lede>
                  )}

                  <p className="mt-7 text-sm text-[#f6f2e8]/75">
                    {article.author_name} · {fmtDate(article.published_at)}
                  </p>

                  {lang !== 'it' && article.served_lang === 'it' && (
                    <p className="mt-6 max-w-[46ch] border-l-2 border-[#d6c49a]/60 pl-4
                                  text-sm leading-relaxed text-[#f6f2e8]/90">
                      {t('blog.italianOnly', { defaultValue: 'Questo articolo è disponibile solo in italiano, per ora.' })}
                    </p>
                  )}
                </div>

                {cover && (
                  <div className="lg:col-span-5">
                    <img
                      src={cover}
                      alt=""
                      aria-hidden
                      width="1200"
                      height="630"
                      fetchPriority="high"
                      decoding="async"
                      className="aspect-[40/21] w-full rounded-2xl object-cover
                                 ring-1 ring-[#f6f2e8]/15
                                 shadow-[0_30px_60px_-30px_rgba(0,0,0,0.85)]"
                    />
                  </div>
                )}
              </div>
            </PhotoOpener>

            {/* ── 2. LETTURA — la colonna, alla sua misura ──────────────
                38rem ≈ 68 caratteri per riga col corpo da 1,125rem: la
                misura di lettura del kit (Lede sta a 62ch). Il vestito
                tipografico e' in index.css, .blog-content. */}
            <Section tone="cream" rhythm="flow" width="max-w-[38rem]">
              <div className={article.gated ? 'blog-content gated-content' : 'blog-content'}>
                <LegalMarkdownRenderer content={article.content} />
              </div>
            </Section>

            {/* ── 3. LA SOGLIA — il gate, o la lettera ─────────────────
                BN3 — guida riservata: anteprima onesta + indice + gate.
                Il gate E' il double opt-in: iscriviti, conferma dalla
                email, torni qui sbloccato.
                DS3 — da riquadro dentro la colonna a fascia intera su
                sabbia: e' il punto in cui la lettura si interrompe, e
                un muro dentro la colonna non sembrava un muro. L'ordine
                cambia (prima si dice cosa c'e' dietro, poi l'indice,
                poi la porta), le parole no. */}
            {gateOpen && (
              <Section tone="sand" rhythm="flow" width="max-w-2xl"
                       labelledBy="art-gate-title">
                <div data-testid="blog-gate">
                  <DisplayTitle as="h2" id="art-gate-title" size="section" measure="title"
                                className="text-[1.7rem] sm:text-[2rem] lg:text-[2.25rem]">
                    {t('blog.gateTitle', { defaultValue: 'Questa guida è riservata agli iscritti alla lettera' })}
                  </DisplayTitle>
                  <Lede size="body" className="mt-6">
                    {t('blog.gateBody', { defaultValue: 'Gratis: ti iscrivi, confermi dalla tua email e il link ti riporta qui, alla guida completa. Insieme ricevi la lettera di Aurya, con disiscrizione a un click.' })}
                  </Lede>

                  {Array.isArray(article.toc) && article.toc.length > 0 && (
                    <div className="mt-9 border-t border-[#8a7440]/30 pt-7">
                      <p className="font-heading text-sm font-semibold text-foreground">
                        {t('blog.gateToc', { defaultValue: 'Cosa trovi nella guida completa' })}
                      </p>
                      <ul className="mt-4 list-none space-y-2.5 p-0">
                        {article.toc.map(h => (
                          <li key={h} className="flex items-start gap-2.5 text-[0.95rem] text-foreground/80">
                            <Lock className="mt-1 h-3.5 w-3.5 shrink-0 text-[#7d6a3a]" aria-hidden />
                            <span>{h}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <div className="mt-8 max-w-md">
                    <LeadForm
                      type="traveler" compact subscribe accent="#8a7440"
                      context={`gate_${article.category || slug}`}
                      returnTo={`/blog/${slug}`}
                      consentText={t('blogCta.consent', { defaultValue: 'Acconsento a ricevere la lettera di Aurya via email.' })}
                      ctaLabel={t('blog.gateCta', { defaultValue: 'Sblocca la guida completa' })}
                      thanksBody={t('blog.gateThanks', { defaultValue: 'Controlla la tua casella: il link di conferma sblocca la guida.' })}
                    />
                  </div>
                  <Lede size="aside" tone="quiet" className="mt-5">
                    {t('blog.gateAlready', { defaultValue: 'Già iscritto? Inserisci la stessa email: ti arriva il link che riapre il tuo accesso, anche da un nuovo dispositivo.' })}
                  </Lede>
                </div>
              </Section>
            )}

            {/* BN1 — il primo punto di conversione: CTA di cluster.
                BN3: sulle guide riservate il gate qui sopra E' la CTA
                (due form nella stessa pagina si cannibalizzano).

                OF1 (2/8/2026) — la porta ora dipende da CHI sta
                leggendo. Gli articoli della categoria "operatori"
                (fiscalita', prezzo di un ritiro, come riempirlo) li
                legge un professionista: offrirgli la lettera per
                viaggiatori era l'invito sbagliato alla persona giusta,
                ed era l'unico posto del sito dove il contenuto e il
                pubblico coincidevano senza che ci fosse una porta.
                Per tutti gli altri resta la lettera. */}
            {!article.gated && (
              article.category === PRO_CATEGORY ? (
                <Section tone="sage" rhythm="flow" width="max-w-3xl"
                         labelledBy="art-pro-title">
                  <DisplayTitle as="h2" id="art-pro-title" size="section" measure="title"
                                className="text-[1.8rem] sm:text-[2.2rem] lg:text-[2.5rem]">
                    {t('blog.proBridgeTitle', {
                      defaultValue: 'Scriviamo anche di te.' })}
                  </DisplayTitle>
                  <Lede size="lead" tone="inherit" className="mt-6 opacity-90">
                    {t('blog.proBridgeBody', {
                      defaultValue: 'Guide come questa nascono parlando con chi fa questo lavoro. Se lo fai anche tu e ti va di raccontarti, il primo passo e\' una conversazione.' })}
                  </Lede>
                  <p className="mt-8">
                    <EditorialCta to="/entra-nella-rete" variant="light">
                      {t('blog.proBridgeCta', { defaultValue: 'Entra nella rete' })}
                    </EditorialCta>
                  </p>
                </Section>
              ) : (
                <Section tone="sand" rhythm="flow" width="max-w-2xl">
                  <BlogNewsletterCTA category={article.category} />
                </Section>
              )
            )}

            {/* ── 4. I RITIRI — l'unica ancora tonale ──────────────────
                SEO3→BN1 — la CTA ritiri vive SOLO in fase marketplace
                (in fase rete /ritiri redirige alla home: sarebbe una
                porta finta). In rete converte la lettera qui sopra. */}
            {sitePhase === 'marketplace' && BOOKABLE_CATS.has(article.category) && (
              <Section tone="sage" rhythm="flow" width="max-w-3xl"
                       labelledBy="art-retreats-title">
                <DisplayTitle as="h2" id="art-retreats-title" size="section" measure="title"
                              className="text-[1.8rem] sm:text-[2.2rem] lg:text-[2.5rem]">
                  {t('blog.exploreRetreatsTitle', {
                    cat: catLabel(article.category),
                    defaultValue: 'Vivi un ritiro di {{cat}}' })}
                </DisplayTitle>
                <Lede size="lead" tone="inherit" className="mt-6 opacity-90">
                  {t('blog.exploreRetreatsBody', {
                    defaultValue: 'Le date in programma, con prenotazione online e caparra protetta.' })}
                </Lede>
                <p className="mt-8">
                  <EditorialCta to={`/ritiri/${article.category}`} variant="light">
                    {t('blog.exploreRetreatsCta', {
                      cat: catLabel(article.category),
                      defaultValue: 'Scopri i ritiri di {{cat}}' })}
                  </EditorialCta>
                </p>
              </Section>
            )}

            {/* ── 5. CONTINUA A LEGGERE — con le copertine ─────────────
                Era il debito segnalato: tre card bordate col solo
                titolo, l'unico posto del Magazine dove una scheda non
                aveva la sua copertina. Ora e' la stessa ArticleCard
                dell'indice, sullo stesso bianco. Tre per riga: sono
                gia' un secondo piano, la colonna larga ce l'ha avuta
                l'articolo. Sotto, la porta di ritorno. */}
            <Section tone="paper" rhythm="flow" width="max-w-6xl"
                     labelledBy={related.length > 0 ? 'art-related-title' : undefined}>
              {related.length > 0 && (
                <div data-testid="blog-related" className="mb-14">
                  <DisplayTitle as="h2" id="art-related-title" size="section" measure="title"
                                className="text-[1.6rem] sm:text-[1.9rem] lg:text-[2.1rem]">
                    {t('blog.related', { defaultValue: 'Continua a leggere' })}
                  </DisplayTitle>
                  <div className="mt-10 grid gap-y-12 sm:grid-cols-2 sm:gap-x-9
                                  lg:grid-cols-3 lg:gap-x-10">
                    {related.map(a => (
                      <ArticleCard key={a.slug} article={a} variant="compact"
                                   category={catLabel(a.category)}
                                   date={fmtDate(a.published_at)} />
                    ))}
                  </div>
                </div>
              )}
              <div className="border-t border-foreground/10 pt-8">
                <EditorialCta to="/blog" variant="quiet">
                  {t('blog.backToBlog', { defaultValue: 'Torna al Magazine' })}
                </EditorialCta>
              </div>
            </Section>

          </article>
        )}
      </div>
    </MarketplaceShell>
  );
}
