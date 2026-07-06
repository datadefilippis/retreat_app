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

  // Solo la CategoryNav: il NOME dello store sta gia' nella barra del
  // titolo della landing (feedback founder 7/7 — via il doppione blu;
  // il menu si posiziona SOTTO la barra del titolo).
  return (
    <CategoryNav
      orgSlug={slug}
      categories={categories}
      storeInfo={si}
      customLinks={catalog.custom_nav_links}
    />
  );
}
