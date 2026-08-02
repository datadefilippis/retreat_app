/**
 * PhotoBand — la fascia fotografica a tutta larghezza (DS1).
 *
 * IL PERCHE'. E' il respiro di meta' pagina. Una pagina editoriale
 * lunga ha bisogno di un punto in cui si smette di leggere: senza,
 * anche il testo migliore diventa una colonna che scorre. La regola
 * della grammatica DS e' «almeno una foto a tutta larghezza per
 * pagina», e a tutta larghezza vuol dire davvero da bordo a bordo: e'
 * l'unico momento in cui la pagina esce dalla sua colonna, ed e' li'
 * che si sente il cambio di passo.
 *
 * DUE MODI, UNO SOLO DEI QUALI HA IL VELO.
 *   senza figli → la fotografia nuda, alla sua piena luce. Nessun velo:
 *                 velare una foto che non deve reggere testo vuol dire
 *                 solo sporcarla.
 *   con figli   → la frase grande dentro l'immagine, e allora il velo
 *                 c'e' e si calcola. Due strati: uno verticale e una
 *                 ellisse al centro, dove sta la frase.
 *
 * IL VELO, MISURATO sui pixel di r01, la foto peggiore del magazzino
 * per questo uso — verde in controluce,
 * con le foglie che arrivano a 246,252,187. Composti i due strati sul
 * riquadro che la frase occupa davvero: oro #ecd9a8 5,44:1 a 1440 e
 * 4,89:1 a 390; crema #f6f2e8 6,78:1 e 6,10:1. Minimo AA 4,5:1 per il
 * corpo, 3:1 per il display. Con un'altra fotografia si rimisura.
 *
 * ALTEZZA DICHIARATA, quindi nessun salto: la fascia ha la sua altezza
 * in `min-h`/`h` e l'immagine ci sta dentro in copertura. `loading`
 * resta lazy perche' la fascia sta sempre sotto la piega; l'apertura,
 * che sta sopra, ha il suo componente (PhotoOpener) e la sua priorita'.
 */
import React from 'react';

const HEIGHTS = {
  /* con la frase: deve esserci spazio attorno alle parole, altrimenti
     e' una didascalia sopra una foto e non un respiro */
  voice: 'min-h-[26rem] sm:min-h-[28rem] lg:min-h-[32.5rem]',
  /* muta: una striscia, non una schermata */
  quiet: 'h-[15rem] sm:h-[19rem] lg:h-[24rem]',
};

const VEIL_V = 'bg-[linear-gradient(to_bottom,rgba(14,26,21,0.54)_0%,rgba(14,26,21,0.70)_50%,rgba(14,26,21,0.54)_100%)]';
const VEIL_CENTER = 'bg-[radial-gradient(ellipse_68%_68%_at_50%_50%,rgba(14,26,21,0.52)_0%,rgba(14,26,21,0)_100%)]';

export default function PhotoBand({
  image,
  imageAlt = '',
  focus = '50% 40%',
  height,
  width = 'max-w-3xl',
  as: Tag = 'section',
  labelledBy,
  className = '',
  children,
  ...rest
}) {
  const voiced = Boolean(children);
  const box = HEIGHTS[height] || (voiced ? HEIGHTS.voice : HEIGHTS.quiet);

  return (
    <Tag
      aria-labelledby={labelledBy}
      className={`relative isolate w-full overflow-hidden bg-[#0e1a15] text-[#f6f2e8] ${box} ${className}`}
      {...rest}
    >
      {image && (
        <img
          src={image}
          alt={imageAlt}
          aria-hidden={imageAlt ? undefined : true}
          width="1600"
          height="1067"
          loading="lazy"
          decoding="async"
          className="absolute inset-0 h-full w-full object-cover"
          style={{ objectPosition: focus }}
        />
      )}
      {voiced && image && (
        <>
          <div aria-hidden className={`absolute inset-0 ${VEIL_V}`} />
          <div aria-hidden className={`absolute inset-0 ${VEIL_CENTER}`} />
        </>
      )}
      {voiced && (
        <div className={`relative mx-auto flex h-full w-full ${width} flex-col
                         items-center justify-center px-6 py-20 text-center sm:px-8 ${box}`}>
          {children}
        </div>
      )}
    </Tag>
  );
}
