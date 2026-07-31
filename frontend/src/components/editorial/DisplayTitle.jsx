/**
 * DisplayTitle — il titolo display serif delle superfici editoriali.
 *
 * Due vincoli di brand, qui e non sparsi nelle pagine:
 *   1. serif display (.font-display), peso medio, interlinea stretta;
 *   2. RIGHE CORTE. La misura e' in `ch`, non in pixel: cambiando
 *      corpo il numero di caratteri per riga resta quello. Il tetto
 *      dichiarato e' ~45 caratteri (BRAND_HOME §6), le misure sotto
 *      stanno tutte sotto quel tetto perche' righe piu' corte reggono
 *      meglio il corpo grande.
 */
import React from 'react';

const SIZES = {
  // hero: la frase piu' grande della pagina
  hero: 'text-[2.6rem] leading-[1.06] sm:text-6xl lg:text-7xl lg:leading-[1.04]',
  // HP2 — hero a DUE FRASI, una per riga (<TitleLine>). Corpo piu'
  // contenuto del `hero`: con 38 caratteri sulla prima riga il 7xl la
  // spezzerebbe in tre, e la struttura "non X. Ma Y." si perderebbe.
  heroLines: 'text-[2.3rem] leading-[1.09] sm:text-5xl sm:leading-[1.07] lg:text-[3.4rem] lg:leading-[1.06]',
  // titolo di sezione
  section: 'text-[2rem] leading-[1.1] sm:text-5xl lg:text-[3.25rem] lg:leading-[1.08]',
  // il manifesto: una frase sola, molto vuoto attorno
  manifesto: 'text-[2.1rem] leading-[1.12] sm:text-5xl lg:text-[3.5rem] lg:leading-[1.1]',
};

const MEASURES = {
  tight: 'max-w-[17ch]',
  title: 'max-w-[22ch]',
  wide: 'max-w-[30ch]',
  // HP2 — quando le righe le decide il testo (due <TitleLine>), la
  // misura non deve rispezzarle: fa solo da tetto di sicurezza.
  lines: 'max-w-[40ch]',
};

/**
 * TitleLine — una riga voluta del titolo. Le due righe della
 * specifica sono due FRASI, non un a-capo estetico: restano due
 * elementi di blocco, cosi' ogni lingua le tiene separate senza <br>
 * e senza dipendere dalla larghezza del viewport. Su mobile ciascuna
 * puo' andare a capo da sola, ma la seconda frase non risalira' mai
 * accanto alla prima.
 */
export function TitleLine({ className = '', children }) {
  return <span className={`block ${className}`}>{children}</span>;
}

export default function DisplayTitle({
  as: Tag = 'h2',
  size = 'section',
  measure = 'title',
  id,
  className = '',
  children,
}) {
  return (
    <Tag
      id={id}
      className={`font-display font-medium tracking-[-0.015em] ${SIZES[size] || SIZES.section} ${MEASURES[measure] || MEASURES.title} ${className}`}
    >
      {children}
    </Tag>
  );
}
