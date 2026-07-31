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
 *                 home ma piu' ricca: articolo di apertura grande,
 *                 due di spalla, poi tutti gli altri in griglia.
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
 * Fondi: crema, bianco, sabbia. Nessuna ancora verde piena: il verde
 * qui e' gia' nelle copertine, che da SW4 sono un medaglione salvia su
 * ogni scheda. Una fascia verde in piu' le avrebbe spente.
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
  Section, DisplayTitle, TitleLine, Lede, ArticleCard,
} from '../../components/editorial';

/* Il chip: sobrio per definizione. Stesso verde e stesso tracking
   dell'occhiello di ArticleCard, cosi' il filtro e la scheda si
   leggono come la stessa classificazione detta due volte. */
const CHIP = 'inline-flex items-center rounded-full px-3 py-1.5 text-[11px] font-medium uppercase tracking-[0.12em] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2f5749] focus-visible:ring-offset-2';
const CHIP_ON = 'bg-[#2f5749] text-[#f6f2e8]';
const CHIP_OFF = 'bg-[#2f5749]/10 text-[#2f5749] hover:bg-[#2f5749]/20';

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

  const [lead, ...rest] = items;
  const spalla = rest.slice(0, 2);     // i due accanto all'apertura
  const altri = rest.slice(2);         // la griglia sotto la riga

  return (
    <MarketplaceShell noSearch>
      <div className="bg-background">

        {/* ── 1. APERTURA ──────────────────────────────────────────
            Il dispositivo a coppia sta in due <TitleLine>: sono due
            frasi, non un a-capo estetico, e in ogni lingua restano
            due righe. Sulla pagina di categoria la coppia lascia il
            posto al nome della categoria: li' il titolo deve dire
            dove sei, non ripetere la tesi del Magazine. */}
        <Section tone="cream" rhythm="hero" labelledBy="mag-title">
          <div data-testid="mag-open">
            <p className="eyebrow mb-5">
              {t('blog.eyebrow', { defaultValue: 'Il Magazine' })}
            </p>
            <DisplayTitle as="h1" id="mag-title" size="heroLines" measure="lines">
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
            <Lede size="lead" className="mt-8">
              {category
                ? t('blog.catSubtitle', { defaultValue: "Quello che abbiamo scritto su questo tema." })
                : t('blog.subtitle', { defaultValue: "Pratiche, luoghi e persone, raccontati per quello che sono. Senza scorciatoie." })}
            </Lede>
            <BrandPayoff tone="cream" size="sm" className="mt-9" />

            {/* i filtri: chip, non bottoni pesanti, e link veri */}
            {categoriesWithArticles.length > 1 && (
              <nav className="mt-10 flex flex-wrap gap-2" data-testid="blog-category-chips"
                   aria-label={t('blog.eyebrow', { defaultValue: 'Il Magazine' })}>
                <Link to="/blog"
                      className={`${CHIP} ${!category ? CHIP_ON : CHIP_OFF}`}
                      aria-current={!category ? 'page' : undefined}>
                  {t('blog.allArticles', { defaultValue: 'Tutti' })}
                </Link>
                {categoriesWithArticles.map(slug => (
                  <Link key={slug} to={`/blog/categoria/${slug}`}
                        className={`${CHIP} ${category === slug ? CHIP_ON : CHIP_OFF}`}
                        aria-current={category === slug ? 'page' : undefined}>
                    {catLabel(slug)}
                  </Link>
                ))}
              </nav>
            )}
          </div>
        </Section>

        {/* ── 2. LA VETRINA ────────────────────────────────────────
            Bianco pieno, come la sezione "Dal Magazine" della home:
            le copertine sono medaglioni scuri e sul bianco si staccano
            come oggetti. L'apertura grande prende sette colonne e i
            due di spalla cinque; il resto scende in griglia sotto una
            riga sottile, l'unico separatore della pagina. Con un
            articolo solo l'apertura prende tutta la larghezza, invece
            di lasciare mezza griglia vuota. */}
        <Section tone="paper" rhythm="flow" width="max-w-6xl">
          {loading ? (
            <p className="text-foreground/50 py-10" aria-live="polite">…</p>
          ) : items.length === 0 ? (
            <div data-testid="blog-empty">
              <Lede size="body" tone="quiet">
                {category
                  ? t('blog.emptyCat', { defaultValue: "Su questo tema non abbiamo ancora scritto." })
                  : t('blog.empty', { defaultValue: "Non c'è ancora niente da leggere in questa lingua." })}
              </Lede>
            </div>
          ) : (
            <div data-testid="blog-list">
              <div className="grid gap-10 lg:grid-cols-12 lg:gap-14">
                <div className={spalla.length > 0 ? 'lg:col-span-7' : 'lg:col-span-8'}>
                  {card(lead, 'lead', true)}
                </div>
                {spalla.length > 0 && (
                  <div className="lg:col-span-5 grid gap-7 sm:grid-cols-2 lg:grid-cols-1 lg:content-start lg:gap-9 lg:pt-2">
                    {spalla.map(a => card(a, 'compact'))}
                  </div>
                )}
              </div>

              {altri.length > 0 && (
                <div className="mt-14 border-t border-foreground/10 pt-12">
                  <p className="eyebrow mb-8">
                    {t('blog.moreTitle', { defaultValue: 'Altri articoli' })}
                  </p>
                  <div className="grid gap-9 sm:grid-cols-2 sm:gap-x-10 lg:grid-cols-3">
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
      </div>
    </MarketplaceShell>
  );
}
