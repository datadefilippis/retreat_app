/**
 * BlogArticlePage — /blog/:slug (AN5).
 *
 * Dettaglio articolo nel guscio marketplace: markdown renderizzato col
 * renderer sicuro delle pagine legal (zero dipendenze, zero HTML).
 * Se la lingua attiva non ha traduzione il backend serve l'italiano e
 * lo dichiara (served_lang): la pagina lo dice con una nota onesta.
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

// Le categorie con una pagina /ritiri/{cat} prenotabile (tassonomia
// ritiri): SOLO queste hanno la CTA "Vivi un ritiro", e solo in fase
// marketplace. Le categorie editoriali (ritiri/energia/operatori) no.
const BOOKABLE_CATS = new Set(['yoga', 'meditazione', 'detox', 'suono',
  'massaggio', 'breathwork', 'cammini', 'femminile', 'aziendale']);

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

  // BN1 — "Continua a leggere": stesso cluster prima (categoria),
  // poi i piu' recenti. Sessioni piu' lunghe = fiducia + SEO interna.
  useEffect(() => {
    if (!article) { setRelated([]); return; }
    let mounted = true;
    api.get('/public/articles', { params: { lang, page_size: 50 } })
      .then(res => {
        if (!mounted) return;
        const all = (res.data?.items || []).filter(a => a.slug !== slug);
        const same = all.filter(a => article.category && a.category === article.category);
        const rest = all.filter(a => !same.includes(a));
        setRelated([...same, ...rest].slice(0, 3));
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

  if (error) {
    return (
      <MarketplaceShell noSearch>
        <div className="max-w-2xl mx-auto px-4 py-24 text-center">
          <p className="text-lg font-semibold text-gray-900 mb-2">
            {t('blog.notFound', { defaultValue: 'Articolo non trovato' })}
          </p>
          <Link to="/blog" className="text-primary underline text-sm">
            {t('blog.backToBlog', { defaultValue: 'Torna al Magazine' })}
          </Link>
        </div>
      </MarketplaceShell>
    );
  }

  return (
    <MarketplaceShell noSearch>
      <div className="bg-background">
        {article && (
          <article className="max-w-2xl mx-auto px-4 py-10" data-testid="blog-article">
            <nav className="text-xs text-gray-500 mb-6">
              <Link to="/blog" className="hover:text-primary hover:underline">
                {t('blog.title', { defaultValue: 'Il blog di Aurya' })}
              </Link>
              {article.category && (<>
                <span className="mx-1.5" aria-hidden>›</span>
                <Link to={`/blog/categoria/${article.category}`} className="hover:text-primary hover:underline">
                  {t(`categories.${article.category}`, { defaultValue: article.category })}
                </Link>
              </>)}
            </nav>

            <header className="mb-8">
              <h1 className="font-display text-3xl md:text-4xl font-bold text-gray-900 leading-tight">
                {article.title}
              </h1>
              <p className="text-sm text-gray-500 mt-3">
                {article.author_name} · {fmtDate(article.published_at)}
              </p>
              {lang !== 'it' && article.served_lang === 'it' && (
                <p className="mt-3 rounded-lg bg-amber-50 border border-amber-200 text-amber-800 text-xs px-3 py-2">
                  {t('blog.italianOnly', { defaultValue: 'Questo articolo è disponibile solo in italiano, per ora.' })}
                </p>
              )}
            </header>

            {article.featured_image_url && (
              <img src={article.featured_image_url} alt={article.title} fetchPriority="high"
                   className="w-full rounded-2xl mb-8 object-cover max-h-96" />
            )}

            <div className={article.gated ? 'blog-content gated-content' : 'blog-content'}>
              <LegalMarkdownRenderer content={article.content} />
            </div>

            {/* BN3 — guida riservata: anteprima onesta + indice + gate.
                Il gate E' il double opt-in: iscriviti, conferma dalla
                email, torni qui sbloccato. */}
            {article.gated && !article.unlocked && (
              <aside className="mt-8 rounded-2xl border-2 border-[#8a7440]/30 bg-gradient-to-b from-[#8a7440]/5 to-white p-6"
                     data-testid="blog-gate">
                {Array.isArray(article.toc) && article.toc.length > 0 && (
                  <div className="mb-5">
                    <p className="font-heading text-sm font-semibold text-gray-900">
                      {t('blog.gateToc', { defaultValue: 'Cosa trovi nella guida completa' })}
                    </p>
                    <ul className="mt-2 space-y-1.5">
                      {article.toc.map(h => (
                        <li key={h} className="flex items-start gap-2 text-sm text-gray-600">
                          <Lock className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#8a7440]" aria-hidden />
                          {h}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                <p className="font-heading font-semibold text-foreground">
                  {t('blog.gateTitle', { defaultValue: 'Questa guida è riservata agli iscritti alla lettera' })}
                </p>
                <p className="mt-1 text-sm text-muted-foreground">
                  {t('blog.gateBody', { defaultValue: 'Gratis: ti iscrivi, confermi dalla tua email e il link ti riporta qui, alla guida completa. Insieme ricevi la lettera di Aurya ogni due settimane, con disiscrizione a un click.' })}
                </p>
                <div className="mt-4 max-w-md">
                  <LeadForm
                    type="traveler" compact subscribe accent="#8a7440"
                    context={`gate_${article.category || slug}`}
                    returnTo={`/blog/${slug}`}
                    consentText={t('blogCta.consent', { defaultValue: 'Acconsento a ricevere la lettera di Aurya via email.' })}
                    ctaLabel={t('blog.gateCta', { defaultValue: 'Sblocca la guida completa' })}
                    thanksBody={t('blog.gateThanks', { defaultValue: 'Controlla la tua casella: il link di conferma sblocca la guida.' })}
                  />
                </div>
                <p className="mt-3 text-xs text-gray-400">
                  {t('blog.gateAlready', { defaultValue: 'Già iscritto? Inserisci la stessa email: ti arriva il link che riapre il tuo accesso, anche da un nuovo dispositivo.' })}
                </p>
              </aside>
            )}

            {/* SEO3→BN1 — la CTA ritiri vive SOLO in fase marketplace
                (in fase rete /ritiri redirige alla home: sarebbe una
                porta finta). In rete converte la newsletter qui sotto. */}
            {sitePhase === 'marketplace' && BOOKABLE_CATS.has(article.category) && (
              <aside className="mt-10 rounded-2xl border border-[#8a7440]/25 bg-[#376254]/5 p-6 flex flex-col sm:flex-row sm:items-center gap-4">
                <div className="flex-1">
                  <p className="font-heading font-semibold text-foreground">
                    {t('blog.exploreRetreatsTitle', {
                      cat: t(`categories.${article.category}`, { defaultValue: article.category }),
                      defaultValue: 'Vivi un ritiro di {{cat}}' })}
                  </p>
                  <p className="text-sm text-muted-foreground mt-1">
                    {t('blog.exploreRetreatsBody', {
                      defaultValue: 'Le date in programma, con prenotazione online e caparra protetta.' })}
                  </p>
                </div>
                <Link to={`/ritiri/${article.category}`}
                      className="shrink-0 inline-flex items-center justify-center gap-1.5 rounded-full bg-[#376254] text-white px-5 py-2.5 text-sm font-semibold hover:bg-[#2c4f43]">
                  {t('blog.exploreRetreatsCta', {
                    cat: t(`categories.${article.category}`, { defaultValue: article.category }),
                    defaultValue: 'Scopri i ritiri di {{cat}}' })} →
                </Link>
              </aside>
            )}

            {/* BN1 — il primo punto di conversione: CTA di cluster.
                BN3: sulle guide riservate il gate qui sopra E' la CTA
                (due form nella stessa pagina si cannibalizzano). */}
            {!article.gated && <BlogNewsletterCTA category={article.category} />}

            {/* BN1 — Continua a leggere: correlati per categoria */}
            {related.length > 0 && (
              <section className="mt-12" data-testid="blog-related">
                <h2 className="font-heading text-lg font-semibold text-gray-900">
                  {t('blog.related', { defaultValue: 'Continua a leggere' })}
                </h2>
                <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
                  {related.map(a => (
                    <Link key={a.slug} to={`/blog/${a.slug}`}
                          className="group rounded-xl border border-gray-200 bg-white p-4 hover:border-[#376254]/40 hover:shadow-sm transition-all">
                      {a.category && (
                        <p className="text-[11px] font-medium uppercase tracking-wide text-[#8a7440]">
                          {t(`categories.${a.category}`, { defaultValue: a.category })}
                        </p>
                      )}
                      <p className="mt-1 text-sm font-semibold text-gray-900 leading-snug group-hover:text-[#376254]">
                        {a.title}
                      </p>
                    </Link>
                  ))}
                </div>
              </section>
            )}

            <footer className="mt-12 pt-6 border-t border-gray-200">
              <Link to="/blog" className="text-sm font-medium text-primary hover:underline">
                ← {t('blog.backToBlog', { defaultValue: 'Torna al Magazine' })}
              </Link>
            </footer>
          </article>
        )}
      </div>
    </MarketplaceShell>
  );
}
