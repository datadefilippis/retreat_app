/**
 * useSeoMeta — imposta title + meta description + OG + canonical (Fase 5).
 *
 * Le pagine pubbliche (calendario, landing ritiro, profilo operatore) sono
 * il lato-domanda della piattaforma: il SEO qui è il prodotto, non un
 * accessorio. Hook leggero senza dipendenze (react-helmet non è nel
 * bundle); pulisce nulla — le pagine pubbliche montano una alla volta.
 *
 * Nota SEO reale: CRA serve una SPA, quindi il crawler vede questi tag
 * dopo il render JS. Google li indicizza; per il pre-render completo
 * (Bing/social scraper) serve SSR/prerender — annotato nel master plan
 * come step di infrastruttura (Fase 6), non blocca il lancio.
 */

import { useEffect } from 'react';

function setMeta(attr, key, content) {
  if (!content) return;
  let el = document.head.querySelector(`meta[${attr}="${key}"]`);
  if (!el) {
    el = document.createElement('meta');
    el.setAttribute(attr, key);
    document.head.appendChild(el);
  }
  el.setAttribute('content', content);
}

export default function useSeoMeta({ title, description, image, canonicalPath, jsonLd }) {
  useEffect(() => {
    if (title) document.title = title;
    setMeta('name', 'description', description);
    setMeta('property', 'og:title', title);
    setMeta('property', 'og:description', description);
    setMeta('property', 'og:type', 'website');
    if (image) setMeta('property', 'og:image', image);
    setMeta('name', 'twitter:card', image ? 'summary_large_image' : 'summary');

    if (canonicalPath) {
      let link = document.head.querySelector('link[rel="canonical"]');
      if (!link) {
        link = document.createElement('link');
        link.setAttribute('rel', 'canonical');
        document.head.appendChild(link);
      }
      link.setAttribute('href', window.location.origin + canonicalPath);
    }
  }, [title, description, image, canonicalPath]);

  // F3 (5/7/2026) — JSON-LD schema.org generato dai DATI (Event,
  // Organization, ItemList, BreadcrumbList): il "SEO automatico" del
  // piano. Un solo <script> gestito da questo hook, sostituito a ogni
  // cambio pagina e rimosso all'unmount (le pagine pubbliche montano
  // una alla volta, ma il cleanup evita residui tra SPA-navigations).
  useEffect(() => {
    const ID = 'seo-jsonld';
    document.getElementById(ID)?.remove();
    if (!jsonLd) return undefined;
    const script = document.createElement('script');
    script.type = 'application/ld+json';
    script.id = ID;
    script.textContent = JSON.stringify(jsonLd);
    document.head.appendChild(script);
    return () => { document.getElementById(ID)?.remove(); };
    // Nota: jsonLd viene serializzato per il confronto — gli oggetti
    // inline cambierebbero identita' a ogni render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(jsonLd || null)]);
}
