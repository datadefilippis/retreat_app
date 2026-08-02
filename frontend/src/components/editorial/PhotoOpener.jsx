/**
 * PhotoOpener — l'apertura fotografica delle pagine editoriali (DS1).
 *
 * IL PERCHE'. Il founder ha una sola pagina che gli piace, e la prima
 * ragione (docs/DESIGN_PASS_DS_2026-08.md) e' che apre su un'ancora
 * scura invece che sul crema: «la crema da' aria ma non da' identita'».
 * Le altre pagine aprivano con una frase sopra il vuoto, che e' elegante
 * in un PDF e muta in un browser. Questo componente e' la regola resa
 * eseguibile: il titolo entra DENTRO l'immagine, non sopra il niente.
 *
 * TRE COSE CHE NON SI POSSONO SBAGLIARE, E QUINDI STANNO QUI DENTRO.
 *
 * 1. IL VELO SI CALCOLA, NON SI SPERA. Sotto il testo passano due
 *    strati: uno verticale (piu' scuro in cima e in fondo, dove
 *    l'apertura raccorda con l'header e con la sezione seguente) e uno
 *    orientato come il testo — a sinistra se il testo e' a sinistra,
 *    radiale se e' al centro. Le fermate dei gradienti sono le stesse
 *    che sono state MISURATE sui pixel della fotografia: si compongono
 *    i gradienti sul ritaglio vero (quello che fa object-fit:cover) e
 *    si prende il pixel piu' chiaro del riquadro che il testo occupa.
 *    Chi usa il componente con una foto nuova rimisura: il velo e'
 *    tarato sul caso peggiore di r04 (la mano
 *    in gyan mudra, con la pelle in piena luce a 254,237,208) e regge
 *    8,84:1 a 1440 e 7,96:1 a 390 sul crema #f6f2e8. Il minimo AA e'
 *    4,5:1 per il corpo e 3:1 per il display.
 *
 * 2. REGGE ANCHE SENZA FOTO. Il fondo non e' l'immagine: e' il verde
 *    quasi nero #0e1a15, che c'e' sempre. Se `image` manca (o se il
 *    file non arriva mai) resta un'ancora scura piena, con lo stesso
 *    contrasto FISSO di 15,96:1. Un'apertura non deve mai dipendere da
 *    un byte che potrebbe non arrivare.
 *
 * 3. ZERO SALTO DI LAYOUT. L'altezza la decide il contenitore
 *    (`min-h-*`), non l'immagine: la fotografia sta in `absolute
 *    inset-0` e non partecipa al flusso. Quando il file arriva, non si
 *    muove un pixel. L'immagine e' `fetchPriority="high"` perche' e'
 *    il primo pixel significativo della pagina: metterla in lazy
 *    ritarderebbe il Largest Contentful Paint di proposito.
 *
 * L'immagine e' DECORATIVA per default (`imageAlt=""`): il titolo dice
 * gia' quello che la foto suggerisce, e descrivere una foto d'atmosfera
 * a chi ascolta la pagina e' rumore. Se una foto porta informazione che
 * il testo non ha, si passa un alt vero.
 */
import React from 'react';

const GROUND = 'bg-[#0e1a15] text-[#f6f2e8]';

const HEIGHTS = {
  /* l'apertura di una pagina lunga: deve occupare la prima schermata
     senza mangiarla tutta, cosi' si vede che sotto continua */
  tall: 'min-h-[27rem] sm:min-h-[32rem] lg:min-h-[38.5rem]',
  standard: 'min-h-[22rem] sm:min-h-[26rem] lg:min-h-[31rem]',
};

/* Strato 1 — verticale, uguale per tutte le aperture. */
const VEIL_V = 'bg-[linear-gradient(to_bottom,rgba(14,26,21,0.74)_0%,rgba(14,26,21,0.58)_42%,rgba(14,26,21,0.90)_100%)]';

/* Strato 2 — segue il testo. A sinistra il buio sta dove stanno le
   parole e la fotografia resta leggibile dalla meta' in la'; al centro
   il buio e' un'ellisse, cosi' i quattro angoli restano fotografia. */
const VEIL_BY_ALIGN = {
  left: 'bg-[linear-gradient(to_right,rgba(14,26,21,0.72)_0%,rgba(14,26,21,0.46)_52%,rgba(14,26,21,0.10)_100%)]',
  center: 'bg-[radial-gradient(ellipse_78%_78%_at_50%_50%,rgba(14,26,21,0.56)_0%,rgba(14,26,21,0)_100%)]',
};

export default function PhotoOpener({
  image,
  imageAlt = '',
  /** object-position: dove sta il soggetto quando il ritaglio stringe */
  focus = '50% 45%',
  height = 'tall',
  align = 'left',
  width = 'max-w-3xl',
  eyebrow,
  labelledBy,
  as: Tag = 'section',
  className = '',
  children,
  ...rest
}) {
  const centered = align === 'center';
  return (
    <Tag
      aria-labelledby={labelledBy}
      className={`relative isolate overflow-hidden ${GROUND} ${className}`}
      {...rest}
    >
      {image && (
        <img
          src={image}
          alt={imageAlt}
          aria-hidden={imageAlt ? undefined : true}
          width="1600"
          height="1067"
          fetchPriority="high"
          decoding="async"
          className="absolute inset-0 h-full w-full object-cover"
          style={{ objectPosition: focus }}
        />
      )}
      {image && <div aria-hidden className={`absolute inset-0 ${VEIL_V}`} />}
      {image && (
        <div aria-hidden
             className={`absolute inset-0 ${VEIL_BY_ALIGN[align] || VEIL_BY_ALIGN.left}`} />
      )}

      <div
        className={`relative mx-auto flex w-full ${width} flex-col justify-center
                    px-6 py-16 sm:px-8 sm:py-20 lg:py-24 ${HEIGHTS[height] || HEIGHTS.tall}
                    ${centered ? 'items-center text-center' : ''}`}
      >
        {eyebrow && (
          <p className={`eyebrow eyebrow-light mb-6 text-hero-shadow ${centered ? 'text-center' : ''}`}>
            {eyebrow}
          </p>
        )}
        {children}
      </div>
    </Tag>
  );
}
