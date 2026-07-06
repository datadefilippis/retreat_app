/**
 * StoreContextNav — il menu dello store SULLE landing prodotto (7/7/2026).
 *
 * "Dentro lo store non si esce mai": quando il visitatore apre un
 * ritiro/prodotto DAL negozio (?store=1 sui link delle card), la landing
 * mantiene la barra del negozio: nome store (→ home/bio) + la stessa
 * CategoryNav (categorie + Chi siamo). Chi arriva dalla directory o da
 * un link condiviso senza param non la vede: il funnel resta pulito.
 *
 * Il catalogo viene fetchato qui (serve per le categorie con conteggi):
 * un solo round-trip extra, solo in contesto store.
 */
import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { storefrontAPI } from '../../../api/storefront';
import useAvailableCategories from '../hooks/useAvailableCategories';
import CategoryNav from './CategoryNav';

export default function StoreContextNav({ slug }) {
  const { i18n } = useTranslation();
  const [catalog, setCatalog] = useState(null);
  const categories = useAvailableCategories(catalog);

  useEffect(() => {
    let mounted = true;
    storefrontAPI.getCatalog(slug, (i18n.language || 'it').slice(0, 2))
      .then(res => { if (mounted) setCatalog(res.data); })
      .catch(() => {});   // barra best-effort: senza catalogo non si rende
    return () => { mounted = false; };
  }, [slug, i18n.language]);

  if (!catalog) return null;

  const si = catalog.store_info || {};
  const brandBg = si.brand_color || null;
  const brandFg = si.brand_color_text || (brandBg ? '#ffffff' : null);

  return (
    <div className="sticky top-0 z-20">
      <div
        className="px-4 py-2.5"
        style={brandBg
          ? { backgroundColor: brandBg, color: brandFg }
          : { backgroundColor: '#111827', color: '#ffffff' }}
      >
        <div className="max-w-6xl mx-auto flex items-center gap-2">
          <Link to={`/s/${slug}`} className="font-semibold text-sm hover:opacity-80 truncate">
            {si.display_name || catalog.org_name}
          </Link>
        </div>
      </div>
      <CategoryNav
        orgSlug={slug}
        categories={categories}
        storeInfo={si}
        customLinks={catalog.custom_nav_links}
      />
    </div>
  );
}
