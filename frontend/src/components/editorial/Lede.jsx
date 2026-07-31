/**
 * Lede — il testo sotto il titolo. Corpo max ~65 caratteri per riga
 * (BRAND_HOME §6), colore piu' morbido del titolo ma sopra il minimo
 * AA (foreground/75 su crema ≈ 5.6:1, non muted-foreground che sta a
 * 4.6:1 e sui corpi grandi si sfarina).
 *
 * size lead  → sottotitolo dell'hero e delle sezioni
 *      body  → paragrafo di corpo
 *      aside → la riga sottovoce (piu' piccola, mai un'altra tesi)
 */
import React from 'react';

const SIZES = {
  lead: 'text-lg sm:text-xl lg:text-2xl leading-relaxed',
  body: 'text-base sm:text-lg lg:text-xl leading-relaxed',
  aside: 'text-sm sm:text-base leading-relaxed',
};

// Il tono passa da QUI, non da classi opacity aggiunte a mano dal
// chiamante: due utility `opacity-*` sullo stesso nodo si contendono
// la cascata e vince quella che capita, non quella che intendevi.
// HP2 — `quiet` era opacity-60: misurato sul crema e sul bianco dava
// 4.03:1, sotto il minimo AA (4.5:1) per il testo normale. Al 70% sale
// a ~5.6:1 e resta comunque un gradino sotto `soft`: la gerarchia si
// legge, e il testo pure.
const TONES = {
  soft: 'opacity-80',
  quiet: 'opacity-70',
  inherit: '',
};

export default function Lede({
  size = 'lead',
  tone = 'soft',
  className = '',
  children,
}) {
  const color = TONES[tone] ?? TONES.soft;
  return (
    <p className={`max-w-[62ch] text-current ${SIZES[size] || SIZES.body} ${color} ${className}`}>
      {children}
    </p>
  );
}
