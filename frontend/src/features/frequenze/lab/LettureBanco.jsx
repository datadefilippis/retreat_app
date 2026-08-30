/**
 * LE LETTURE DEL BANCO — il blocco riusabile (LU2, 28/8/2026).
 *
 * Oscilloscopio, Spettro, Spettrogramma e il comando Congela erano
 * figli sciolti della pagina unica: con le stanze diventano UN
 * blocco che ogni stanza monta se le serve — il Banco tutte e tre,
 * l'Orecchio tutte e tre (guardano il microfono), le Meraviglie pure
 * (le prove di Tartini e Shepard si vedono qui). Il contratto dei
 * pannelli non cambia di una virgola: ricevono le prese, non
 * conoscono la sorgente.
 */
import React from 'react';
import Oscilloscopio from './Oscilloscopio';
import Spettro from './Spettro';
import Spettrogramma from './Spettrogramma';
import { congela } from './quadro';

export default function LettureBanco({
  ottieniAnalisi, ottieniXY = null, fermo, suonaDavvero,
  quali = ['oscilloscopio', 'spettro', 'spettrogramma'],
}) {
  return (
    <>
      {/* IL COMANDO DEL BANCO: uno solo, fra la sorgente e le sue
          letture, e' li' che passa il confine fra il tempo del
          suono e il tempo dell'immagine. */}
      <div className="lab-banco" data-testid="lab-banco">
        <button type="button" data-testid="lab-congela"
          className={'lab-freeze' + (fermo ? ' fermo' : '')}
          aria-pressed={fermo}
          onClick={() => congela(!fermo)}>
          {fermo ? '● Riprendi' : '❄ Congela'}
        </button>
        <span>
          {fermo
            ? (suonaDavvero
              ? 'le letture sono ferme, il suono continua'
              : 'le letture sono ferme')
            : 'quello che senti è quello che vedi, misurato mentre accade'}
        </span>
      </div>

      {quali.includes('oscilloscopio') && (
        <Oscilloscopio ottieniAnalisi={ottieniAnalisi} fermo={fermo}
          ottieniXY={ottieniXY} />
      )}
      {quali.includes('spettro') && (
        <Spettro ottieniAnalisi={ottieniAnalisi} fermo={fermo} />
      )}
      {quali.includes('spettrogramma') && (
        <Spettrogramma ottieniAnalisi={ottieniAnalisi} fermo={fermo} />
      )}
    </>
  );
}
