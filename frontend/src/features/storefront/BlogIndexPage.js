/**
 * BlogIndexPage — /blog (AN5).
 *
 * La voce di Aurya: articoli olistici nella stessa tassonomia dei
 * ritiri. Regola lingua ereditata dal marketplace: in lingua X si
 * vedono solo gli articoli tradotti in X (mai fallback in lista).
 * I chip categoria mostrano solo le categorie che hanno articoli.
 */
import React, { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import api from '../../api/client';
import MarketplaceShell from './components/MarketplaceShell';
import useSeoMeta from './lib/useSeoMeta';

const CATEGORY_TONES = {
  yoga: 'from-[#376254]/80', meditazione: 'from-[#4a7a68]/80',
  detox: 'from-[#5a8a5a]/80', suono: 'from-[#7a6a8a]/80',
  massaggio: 'from-[#a8765a]/80', breathwork: 'from-[#5a7a8a]/80',
  cammini: 'from-[#6a7a4a]/80', femminile: 'from-[#a85a6a]/80',
  aziendale: 'from-[#4a5a6a]/80',
};

export default function BlogIndexPage() {
  const { t, i18n } = useTranslation('landings');
  const [searchParams, setSearchParams] = useSearchParams();
  const category = searchParams.get('categoria') || '';
  const lang = (i18n.language || 'it').slice(0, 2);

  const [items, setItems] = useState([]);
  const [allItems, setAllItems] = useState([]);   // per i chip categoria
  const [loading, setLoading] = useState(true);

  useSeoMeta({
    title: t('blog.seoTitle', { defaultValue: 'Blog | Aurya' }),
    description: t('blog.seoDesc', { defaultValue: 'Storie, pratiche e sapere olistico da chi organizza e vive i ritiri.' }),
    canonicalPath: '/blog',
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

  return (
    <MarketplaceShell noSearch>
      <div className="bg-background min-h-[60vh]">
        <header className="relative bg-gradient-sidebar text-white overflow-hidden">
        <div aria-hidden className="absolute inset-0 pointer-events-none" style={{
          background: 'radial-gradient(ellipse 60% 80% at 15% 10%, rgba(255,255,255,0.08), transparent 60%), radial-gradient(ellipse 50% 70% at 85% 90%, rgba(193,102,61,0.22), transparent 55%)',
        }} />
          <div className="relative max-w-4xl mx-auto px-4 py-12 text-center">
            <p aria-hidden className="font-brand uppercase tracking-[0.35em] text-[11px] text-[#d6c49a] mb-3 select-none">Connect · Heal · Grow</p>
            <h1 className="font-display text-3xl md:text-4xl font-bold">
              {t('blog.title', { defaultValue: 'Il blog di Aurya' })}
            </h1>
            <p className="text-white/85 mt-3 text-lg leading-relaxed max-w-2xl mx-auto">
              {t('blog.subtitle', { defaultValue: 'Storie, pratiche e sapere olistico da chi i ritiri li organizza e li vive.' })}
            </p>
          </div>
        </header>

        <main className="max-w-4xl mx-auto px-4 py-10">
          {categoriesWithArticles.length > 1 && (
            <div className="flex flex-wrap gap-2 mb-8" data-testid="blog-category-chips">
              <button type="button"
                      onClick={() => setSearchParams({})}
                      className={`rounded-full px-3 py-1 text-xs font-medium border transition-colors ${!category ? 'bg-primary text-white border-primary' : 'border-gray-300 text-gray-600 hover:border-primary'}`}>
                {t('blog.allArticles', { defaultValue: 'Tutti' })}
              </button>
              {categoriesWithArticles.map(slug => (
                <button key={slug} type="button"
                        onClick={() => setSearchParams({ categoria: slug })}
                        className={`rounded-full px-3 py-1 text-xs font-medium border transition-colors ${category === slug ? 'bg-primary text-white border-primary' : 'border-gray-300 text-gray-600 hover:border-primary'}`}>
                  {t(`categories.${slug}`, { defaultValue: slug })}
                </button>
              ))}
            </div>
          )}

          {loading ? (
            <p className="text-sm text-muted-foreground py-16 text-center">…</p>
          ) : items.length === 0 ? (
            <p className="text-sm text-muted-foreground py-16 text-center">
              {t('blog.empty', { defaultValue: 'Nessun articolo in questa lingua, per ora. Le storie stanno arrivando.' })}
            </p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6" data-testid="blog-list">
              {items.map(a => (
                <Link key={a.slug} to={`/blog/${a.slug}`}
                      className="group rounded-2xl border border-gray-200 bg-white overflow-hidden hover:shadow-md transition-shadow flex flex-col">
                  {a.featured_image_url ? (
                    <img src={a.featured_image_url} alt="" loading="lazy"
                         className="h-44 w-full object-cover group-hover:brightness-95 transition" />
                  ) : (
                    <div aria-hidden
                         className={`h-44 w-full bg-gradient-to-br ${CATEGORY_TONES[a.category] || 'from-[#376254]/80'} to-[#F6F3EC] flex items-center justify-center`}>
                      <span className="font-brand uppercase tracking-[0.3em] text-white/90 text-xs px-4 text-center">
                        {a.category ? t(`categories.${a.category}`, { defaultValue: a.category }) : 'Aurya'}
                      </span>
                    </div>
                  )}
                  <div className="p-5 flex flex-col flex-1">
                    <div className="flex items-center gap-2 text-[11px] text-gray-400 mb-2">
                      {a.category && (
                        <span className="uppercase tracking-wide font-semibold text-primary">
                          {t(`categories.${a.category}`, { defaultValue: a.category })}
                        </span>
                      )}
                      <span>{fmtDate(a.published_at)}</span>
                    </div>
                    <h2 className="font-heading text-lg font-bold text-gray-900 group-hover:text-primary transition-colors">
                      {a.title}
                    </h2>
                    {a.description && (
                      <p className="text-sm text-gray-600 mt-2 line-clamp-3 flex-1">{a.description}</p>
                    )}
                    <span className="mt-3 text-sm font-medium text-primary">
                      {t('blog.readMore', { defaultValue: 'Leggi' })} →
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </main>
      </div>
    </MarketplaceShell>
  );
}
