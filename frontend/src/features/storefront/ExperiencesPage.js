/**
 * ExperiencesPage — /esperienze (+ /esperienze/:categoria) (S2b).
 *
 * L'hub dei prodotti NON-evento degli operatori pubblici: servizi
 * (/p), prenotazioni (/r) e corsi (/co). I fisici/digitali restano
 * fuori per scelta (niente aggregatore retail cross-store — vedi
 * SEO_MASTER_PLAN §Cosa NON facciamo).
 */

import React, { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import api from '../../api/client';
import MarketplaceShell from './components/MarketplaceShell';
import useSeoMeta from './lib/useSeoMeta';

import { TypeIcon } from './lib/categoryIcons';

export default function ExperiencesPage() {
  const { t } = useTranslation('landings');
  const { categoria } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    api.get('/public/experiences', { params: categoria ? { category: categoria } : {} })
      .then(res => { if (mounted) setData(res.data); })
      .catch(() => { if (mounted) setData({ items: [], total: 0, categories: {} }); })
      .finally(() => { if (mounted) setLoading(false); });
    return () => { mounted = false; };
  }, [categoria]);

  const items = data?.items || [];
  const categories = useMemo(
    () => Object.entries(data?.categories || {}).sort((a, b) => b[1] - a[1]),
    [data],
  );
  const catLabel = categoria
    ? t(`landings:categories.${categoria}`, { defaultValue: categoria }) : '';

  useSeoMeta({
    title: categoria
      ? t('landings:experiences.seoTitleCat', {
          cat: catLabel, defaultValue: 'Esperienze di {{cat}} | Aurya' })
      : t('landings:experiences.seoTitle', {
          defaultValue: 'Esperienze olistiche: massaggi, corsi e soggiorni | Aurya' }),
    description: t('landings:experiences.seoDesc', {
      defaultValue: 'Massaggi, trattamenti, corsi e soggiorni olistici dagli organizzatori di Aurya. Prenoti online, paghi in sicurezza.',
    }),
    canonicalPath: categoria ? `/esperienze/${categoria}` : '/esperienze',
    noindex: !loading && items.length === 0,
    jsonLd: items.length > 0 ? {
      '@context': 'https://schema.org',
      '@type': 'ItemList',
      itemListElement: items.slice(0, 20).map((it, i) => ({
        '@type': 'ListItem', position: i + 1,
        url: window.location.origin + it.url,
      })),
    } : undefined,
  });

  return (
    <MarketplaceShell>
      <header className="aura-corner bg-gradient-to-b from-[#376254]/12 via-[#f6f3ec]/70 to-transparent">
        <div className="max-w-6xl mx-auto px-4 pt-10 pb-6">
          <nav className="text-xs text-muted-foreground mb-3">
            <Link to="/" className="hover:text-primary hover:underline">Aurya</Link>
            <span className="mx-1.5">›</span>
            {categoria ? (
              <>
                <Link to="/esperienze" className="hover:text-primary hover:underline">
                  {t('landings:experiences.heading', { defaultValue: 'Esperienze' })}
                </Link>
                <span className="mx-1.5">›</span>
                <span className="text-foreground">{catLabel}</span>
              </>
            ) : (
              <span className="text-foreground">
                {t('landings:experiences.heading', { defaultValue: 'Esperienze' })}
              </span>
            )}
          </nav>
          <p aria-hidden className="eyebrow mb-2">Connect · Heal · Grow</p>
          <h1 className="font-display text-3xl md:text-4xl font-bold text-foreground">
            {categoria
              ? t('landings:experiences.headingCat', {
                  cat: catLabel, defaultValue: 'Esperienze di {{cat}}' })
              : t('landings:experiences.heading', { defaultValue: 'Esperienze' })}
          </h1>
          <p className="mt-2 text-muted-foreground max-w-2xl">
            {t('landings:experiences.subtitle', {
              defaultValue: 'Massaggi, trattamenti, corsi e soggiorni: il benessere anche fuori dai ritiri.',
            })}
          </p>
          {categories.length > 0 && (
            <div className="mt-5 flex flex-wrap gap-2">
              <Link to="/esperienze"
                    className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
                      !categoria ? 'bg-primary text-white' : 'bg-white border border-border text-foreground hover:border-primary'}`}>
                {t('landings:calendar.allCategories', { defaultValue: 'Tutte' })}
              </Link>
              {categories.map(([key, count]) => (
                <Link key={key} to={`/esperienze/${key}`}
                      className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
                        categoria === key ? 'bg-primary text-white' : 'bg-white border border-border text-foreground hover:border-primary'}`}>
                  {t(`landings:categories.${key}`, { defaultValue: key })}
                  <span className="ml-1 text-xs opacity-70">({count})</span>
                </Link>
              ))}
            </div>
          )}
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8">
        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {[1, 2, 3].map(i => <div key={i} className="rounded-2xl border border-border bg-card h-56 animate-pulse" />)}
          </div>
        ) : items.length === 0 ? (
          <div className="text-center py-20 max-w-md mx-auto">
            <img src="/logo-aurya-128.png" alt="" aria-hidden className="mx-auto h-14 w-14 opacity-80" />
            <p className="mt-3 text-lg font-semibold text-foreground">
              {t('landings:experiences.emptyTitle', { defaultValue: 'Nessuna esperienza qui, per ora' })}
            </p>
            <Link to="/" className="mt-4 inline-block rounded-full bg-primary text-white px-5 py-2 text-sm font-semibold">
              {t('landings:experiences.backHome', { defaultValue: 'Vai ai ritiri' })}
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {items.map(item => (
              <Link key={item.url} to={item.url}
                    className="group rounded-2xl border border-border bg-card overflow-hidden hover:shadow-lg transition-shadow">
                <div className="h-40 bg-secondary overflow-hidden">
                  {item.image ? (
                    <img src={item.image} alt={item.title} loading="lazy"
                         className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-3xl" aria-hidden>
                      <TypeIcon type={item.item_type} className="h-12 w-12 text-[#376254]/40" />
                    </div>
                  )}
                </div>
                <div className="p-4">
                  <p className="text-[11px] uppercase tracking-wide text-muted-foreground">
                    {t(`catalog:item_type.${item.item_type}`, { defaultValue: item.item_type })}
                    {item.operator ? ` · ${item.operator}` : ''}
                  </p>
                  <h3 className="font-semibold text-foreground mt-0.5 line-clamp-2">{item.title}</h3>
                  {item.description && (
                    <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{item.description}</p>
                  )}
                  {item.price_from != null && (
                    <p className="text-sm font-semibold text-foreground mt-1.5">
                      {t('landings:calendar.priceFrom', { price: `${item.price_from} €`, defaultValue: 'da {{price}}' })}
                    </p>
                  )}
                </div>
              </Link>
            ))}
          </div>
        )}
      </main>
    </MarketplaceShell>
  );
}
