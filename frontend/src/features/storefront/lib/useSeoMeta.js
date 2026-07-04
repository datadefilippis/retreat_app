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

export default function useSeoMeta({ title, description, image, canonicalPath }) {
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
}
