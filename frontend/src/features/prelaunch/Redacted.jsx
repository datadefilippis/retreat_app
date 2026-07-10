/**
 * Redacted — segnaposto sfocato per i contenuti campione (PL9).
 *
 * Sui sample non basta sfocare il dato finto: un nome inventato leggibile
 * (o ispezionabile nel DOM) tradisce che la piattaforma non è ancora
 * popolata. Questo componente SOSTITUISCE il testo con un segnaposto
 * neutro e lo sfoca: l'effetto è "contenuto riservato fino al lancio",
 * non "dato finto". select-none + aria-hidden: né copiabile né letto
 * dagli screen reader.
 */
import React from 'react';

const PLACEHOLDER = {
  title: 'Un ritiro in arrivo su Aurya al lancio',
  name: 'Organizzatore verificato',
  text: 'Profilo completo disponibile al lancio, con recensioni verificate e contatti diretti',
};

export default function Redacted({ kind = 'text', className = '' }) {
  return (
    <span
      aria-hidden
      className={`select-none blur-[5px] opacity-70 ${className}`}
    >
      {PLACEHOLDER[kind] || PLACEHOLDER.text}
    </span>
  );
}
