/**
 * useProductSeo — SEO parity per le landing prodotto NON-evento (S1,
 * docs/SEO_MASTER_PLAN.md).
 *
 * Prima solo i ritiri avevano meta/JSON-LD: servizi, fisici, digitali,
 * corsi e prenotazioni erano invisibili ai motori. Questo hook dà a
 * tutte le landing lo stesso trattamento con UNA riga:
 *
 *   useProductSeo({ kind: 'ph', orgSlug, productSlug, product });
 *
 * kind → tipo schema.org:
 *   p  → Service          co → Course
 *   ph → Product           dg → Product
 *   r  → Product (prenotabile)
 *
 * Il canonical è la landing SENZA query (?store=1 e ?lang= puntano
 * alla versione pulita — regola S1). Il server-side speculare vive in
 * backend/routers/seo_shell.py: stessa logica, stessi tipi.
 */

import useSeoMeta from './useSeoMeta';

const SCHEMA_TYPE = { p: 'Service', co: 'Course', ph: 'Product', dg: 'Product', r: 'Product' };

export default function useProductSeo({ kind, orgSlug, productSlug, product, storeName, currency }) {
  const name = product?.name;
  const description = (product?.description || '').slice(0, 300);
  const image = (product?.images || [])[0] || null;
  const price = product?.unit_price ?? product?.price ?? null;
  const canonicalPath = `/${kind}/${orgSlug}/${productSlug}`;

  const jsonLd = name ? {
    '@context': 'https://schema.org',
    '@type': SCHEMA_TYPE[kind] || 'Product',
    name,
    description,
    ...(image ? { image: [image] } : {}),
    url: window.location.origin + canonicalPath,
    ...(storeName ? {
      [SCHEMA_TYPE[kind] === 'Service' ? 'provider' : 'brand']: {
        '@type': 'Organization', name: storeName,
      },
    } : {}),
    ...(price != null ? {
      offers: {
        '@type': 'Offer',
        price,
        priceCurrency: currency || product?.currency || 'EUR',
        availability: 'https://schema.org/InStock',
      },
    } : {}),
  } : null;

  useSeoMeta({
    title: name ? `${name}${storeName ? ' — ' + storeName : ''} | Aurya` : undefined,
    description: description || name,
    image,
    canonicalPath,
    jsonLd,
  });
}
