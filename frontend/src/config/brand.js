/**
 * Brand del marketplace — AURYA (deciso 11/7/2026, dominio aurya.life).
 *
 * Questo file è la FONTE UNICA del brand lato frontend; il gemello
 * backend è backend/core/brand.py. Ogni superficie pubblica (header,
 * footer, title, copy) legge da qui.
 */
export const BRAND_NAME = 'Aurya';
export const BRAND_DOMAIN = 'aurya.life';
export const BRAND_TAGLINE_KEY = 'marketplace.tagline';   // i18n landings
export const BRAND_GLYPH = '🌿';   // emoji di riserva (contesti solo-testo)
// Logo ufficiale (loto + sole, deciso 13/7/2026) — asset statici in /public
// HP1 (31/7/2026) — il payoff sostituisce il vecchio motto in tre
// parole su header, footer, meta, email, social. E' una legge del mondo,
// non una descrizione di Aurya (docs/BRAND_HOME_AURYA_2026-07.md §2). A
// differenza del vecchio motto SI TRADUCE: la chiave i18n e' quella
// qui sotto, questa costante e' il default italiano.
export const BRAND_PAYOFF = 'Pratiche, eventi e ritiri di benessere';
export const BRAND_PAYOFF_KEY = 'marketplace.payoff';   // i18n landings
export const BRAND_LOGO = '/logo-aurya.png';        // full-res (og:image, condivisioni)
export const BRAND_LOGO_128 = '/logo-aurya-128.png'; // header, favicon
// Canale email pubblico: e' quello che riceve i lead e le risposte.
export const BRAND_EMAIL = 'info@aurya.life';
// Instagram: il founder lo ha chiesto nel footer (2/8/2026) ma il
// profilo non e' ancora nel codice, e un indirizzo social inventato
// porta a casa di qualcun altro. Finche' questa costante e' vuota la
// voce NON compare: appena arriva l'indirizzo vero, si accende da sola.
//
// SOC (21/8/2026): l'icona ora vive nella barra di chiusura del footer
// (© · Privacy · Termini), non tra le «Risorse» — Instagram non e' un
// contenuto di Aurya, e' il canale dove Aurya sta. Qui va l'URL
// COMPLETO del profilo, es. 'https://www.instagram.com/nomeprofilo/'.
export const BRAND_INSTAGRAM = '';
