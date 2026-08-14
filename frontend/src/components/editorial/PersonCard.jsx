/**
 * PersonCard — una persona della rete, formato ritratto.
 *
 * Ordine di lettura voluto: prima il volto, poi il nome, poi la voce.
 * La citazione dice piu' di qualsiasi elenco di dati, per questo sta
 * sotto al nome e non in fondo.
 *
 * SW5 (31/7/2026) — il gap segnalato qui e' chiuso:
 * /public/network/members espone ora `quote` (la frase scelta a mano
 * dal system admin nell'editor dell'intervista, in pubblico solo a
 * intervista pubblicata) e `category` (la pratica, derivata dai
 * prodotti pubblicati dell'org). Il ripiego resta, e resta voluto:
 * senza citazione parla la `tagline`, senza nessuna delle due restano
 * il volto e il nome. Una scheda non deve mai sembrare rotta perche'
 * manca un campo facoltativo.
 *
 * Lo spazio dell'immagine e' RISERVATO (aspect-[3/4]) anche senza
 * foto: nessun salto di layout al caricamento.
 */
import React from 'react';
import { Link } from 'react-router-dom';
import Quote from './Quote';
import VerifiedAuryaBadge from '../VerifiedAuryaBadge';

/** taglio gentile: si tronca su una parola intera, mai a meta' */
export function truncateWords(text, maxChars = 120) {
  if (!text) return '';
  const clean = String(text).trim();
  if (clean.length <= maxChars) return clean;
  const cut = clean.slice(0, maxChars);
  const lastSpace = cut.lastIndexOf(' ');
  return `${(lastSpace > maxChars * 0.5 ? cut.slice(0, lastSpace) : cut).replace(/[.,;:]$/, '')}…`;
}

export default function PersonCard({ person, quoteMaxChars = 120 }) {
  const { slug, name, city, region, portrait_url: portrait,
          cover_url: cover, tagline, category, quote, verified } = person || {};
  const photo = portrait || cover;
  const place = [city, region].filter(Boolean).join(', ');
  const voice = truncateWords(quote || tagline, quoteMaxChars);

  return (
    <article className="group">
      <Link
        to={`/o/${slug}`}
        className="block rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#2f5749] focus-visible:ring-offset-4 focus-visible:ring-offset-background"
      >
        <div className="aspect-[3/4] w-full overflow-hidden bg-[#e8e2d4]">
          {photo ? (
            <img
              src={photo}
              alt={name ? `Ritratto di ${name}` : ''}
              loading="lazy"
              decoding="async"
              /* founder 14/8 — il ritratto si mostra INTERO: object-cover
                 centrato tagliava le teste sulle foto verticali. Con
                 contain la foto appoggia sul fondo sabbia del riquadro
                 (effetto passe-partout), mai un volto tagliato. */
              className="h-full w-full object-contain transition-transform duration-700 group-hover:scale-[1.02]"
            />
          ) : (
            /* niente stock: un campo di colore col nome, e basta */
            <span className="flex h-full w-full items-end p-4 font-display text-2xl text-[#2f5749]/45">
              {name}
            </span>
          )}
        </div>
        <h3 className="font-display text-2xl sm:text-[1.65rem] mt-5 leading-tight text-foreground">
          {name}
        </h3>
      </Link>
      {(category || place) && (
        <p className="text-sm text-foreground/65 mt-1.5">
          {[category, place].filter(Boolean).join(' · ')}
        </p>
      )}
      {verified && (
        <p className="mt-2">
          <VerifiedAuryaBadge variant="on-light" size="sm" />
        </p>
      )}
      {voice && (
        <Quote className="mt-4 text-foreground/80">{voice}</Quote>
      )}
    </article>
  );
}
