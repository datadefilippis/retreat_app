/**
 * PhotoSplit — la sezione a due colonne, fotografia e testo (DS1).
 *
 * IL PERCHE'. E' il modo piu' economico che una pagina ha di cambiare
 * ritmo senza cambiare argomento: la stessa battuta, ma letta accanto a
 * una figura invece che dentro una colonna. La grammatica DS chiede che
 * il lato si alterni («mai tre split di fila dallo stesso lato»), e per
 * poterlo alternare serve che il lato sia un prop e non una riscrittura
 * del markup: da qui `side`.
 *
 * COSA FA E COSA NON FA.
 *   - La fotografia arriva al bordo dello schermo (nessuna gutter, il
 *     fondo della sezione va da bordo a bordo): mezza pagina di
 *     immagine e' il punto, un'immagine dentro un contenitore centrato
 *     sarebbe di nuovo un francobollo grande.
 *   - Il testo NON sta mai sopra la fotografia: sta sul fondo pieno
 *     accanto. Cosi' il contrasto e' quello dichiarato dal tono
 *     (crema/sabbia/bianco/salvia) e non dipende da come e' esposto
 *     quel particolare scatto. E' la stessa scelta della fascia verde
 *     della landing operatori, che e' la pagina approvata.
 *   - La colonna di testo resta agganciata all'asse centrale della
 *     pagina (`max-w-[36rem]` + auto dal lato giusto), cosi' il filo
 *     verticale del sito resta uno solo anche quando la sezione esce
 *     dalla sua colonna.
 *
 * ORDINE NEL DOM. L'immagine sta scritta per prima e su desktop si
 * sposta con `order`. E' la stessa scelta della landing operatori:
 * l'immagine e' decorativa (`alt=""`), quindi l'ordine di lettura per
 * chi ascolta non cambia, e su telefono la figura apre la sezione, che
 * e' il verso giusto per una sezione che si apre con una figura.
 *
 * Nessun salto di layout: l'immagine ha altezze dichiarate a ogni
 * gradino (18rem → sm:22rem → lg: tutta la riga, con un minimo di
 * 32rem), quindi lo spazio e' prenotato prima che il file arrivi.
 */
import React from 'react';
import Section from './Section';

export default function PhotoSplit({
  image,
  imageAlt = '',
  focus = '50% 50%',
  /** da che lato sta la FOTOGRAFIA su desktop */
  side = 'left',
  tone = 'cream',
  labelledBy,
  imageWidth = '900',
  imageHeight = '900',
  className = '',
  children,
  ...rest
}) {
  const photoRight = side === 'right';
  return (
    <Section
      tone={tone}
      rhythm="none"
      width="max-w-none"
      gutter={false}
      labelledBy={labelledBy}
      className={className}
      {...rest}
    >
      <div className="grid lg:grid-cols-2 lg:items-stretch">
        <img
          src={image}
          alt={imageAlt}
          aria-hidden={imageAlt ? undefined : true}
          width={imageWidth}
          height={imageHeight}
          loading="lazy"
          decoding="async"
          className={`h-72 w-full object-cover sm:h-[22rem] lg:h-full lg:min-h-[32rem]
                      ${photoRight ? 'lg:order-last' : ''}`}
          style={{ objectPosition: focus }}
        />
        <div className="flex items-center px-6 py-14 sm:px-8 sm:py-20 lg:py-24 lg:px-0">
          <div
            className={`w-full lg:max-w-[36rem] ${
              photoRight
                ? 'lg:ml-auto lg:pr-14 lg:pl-8'
                : 'lg:mr-auto lg:pl-14 lg:pr-8'
            }`}
          >
            {children}
          </div>
        </div>
      </div>
    </Section>
  );
}
