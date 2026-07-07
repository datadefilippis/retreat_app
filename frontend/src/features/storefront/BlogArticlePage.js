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
import useSeoMeta from './lib/useSeoMeta';
import LegalMarkdownRenderer from '../../components/legal/LegalMarkdownRenderer';

export default function BlogArticlePage() {
  const { slug } = useParams();
  const { t, i18n } = useTranslation('landings');
  const lang = (i18n.language || 'it').slice(0, 2);

  const [article, setArticle] = useState(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let mounted = true;
    setArticle(null);
    setError(false);
    api.get(`/public/articles/${slug}`, { params: { lang } })
      .then(res => { if (mounted) setArticle(res.data); })
      .catch(() => { if (mounted) setError(true); });
    return () => { mounted = false; };
  }, [slug, lang]);

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
            {t('blog.backToBlog', { defaultValue: 'Torna al blog' })}
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
                <Link to={`/blog?categoria=${article.category}`} className="hover:text-primary hover:underline">
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
              <img src={article.featured_image_url} alt="" fetchpriority="high"
                   className="w-full rounded-2xl mb-8 object-cover max-h-96" />
            )}

            <div className="blog-content">
              <LegalMarkdownRenderer content={article.content} />
            </div>

            <footer className="mt-12 pt-6 border-t border-gray-200">
              <Link to="/blog" className="text-sm font-medium text-primary hover:underline">
                ← {t('blog.backToBlog', { defaultValue: 'Torna al blog' })}
              </Link>
            </footer>
          </article>
        )}
      </div>
    </MarketplaceShell>
  );
}
