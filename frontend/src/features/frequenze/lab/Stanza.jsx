/**
 * LA STANZA — il telaio delle pagine del Lab (LU3, 28/8/2026).
 *
 * Ogni stanza del laboratorio risponde a UNA domanda, e la risposta
 * inizia PRIMA degli strumenti: la testata dice la domanda, il
 * blocco «Perché ti interessa» parla al neofita (2-3 righe umane),
 * «Cosa puoi fare qui» sono tre azioni concrete. Poi, solo poi, gli
 * strumenti — con le loro didascalie di sempre.
 *
 * Il telaio porta anche cio' che ogni stanza deve avere uguale:
 * la testata del mondo Sound, la via del ritorno alla Sala, la barra
 * delle stanze, la riga di sicurezza, il ponte col glossario
 * (/sound/impara/glossario — le parole nuove si spiegano li'),
 * il piede. Una stanza non puo' dimenticarsi un pezzo di casa.
 */
import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import SoundTopbar from '../SoundTopbar';
import StanzeSound from '../StanzeSound';
import { SafetyCurtain, SafetyLine } from '../SafetyCurtain';
import '../frequenze.css';
import './lab.css';

export default function Stanza({
  slug,                 // 'banco' | 'orecchio' | ...
  titolo,               // «Il Banco»
  domanda,              // la domanda a cui la stanza risponde
  perche,               // il perche' per il neofita (stringa o nodo)
  azioni = [],          // 3 azioni concrete
  senzaSuono = false,   // la Sala non suona: niente riga di sicurezza
  children,
}) {
  const [safety, setSafety] = useState(false);
  useEffect(() => {
    document.title = `${titolo} — Aurya Sound Lab`;
  }, [titolo]);

  return (
    <div className="fqz lab" data-testid={`lab-stanza-${slug}`}>
      <SoundTopbar firma="Lab" qui="/sound/lab" />
      <header>
        <div>
          <p className="lab-ritorno">
            <Link to="/sound/lab" data-testid="lab-ritorno-sala">← La Sala del Lab</Link>
          </p>
          <h1>{titolo}</h1>
          <div className="sub" data-testid="lab-domanda">{domanda}</div>
        </div>
        <StanzeSound attiva="lab" />
      </header>
      <main>
        <div className="lab-testata" data-testid="lab-testata">
          <div className="lab-testata-perche">
            <h3>Perché ti interessa</h3>
            <p>{perche}</p>
          </div>
          {azioni.length > 0 && (
            <div className="lab-testata-azioni">
              <h3>Cosa puoi fare qui</h3>
              <ul>
                {azioni.map((a) => <li key={a}>{a}</li>)}
              </ul>
            </div>
          )}
        </div>

        {children}

        {!senzaSuono && <SafetyLine onOpen={() => setSafety(true)} />}
        <p className="lab-glossario-ponte" data-testid="lab-glossario-ponte">
          Hertz, spettro, parziale… parole nuove?{' '}
          <Link to="/sound/impara/glossario">Il glossario le spiega tutte →</Link>
        </p>
      </main>
      {safety && <SafetyCurtain mode="review" onClose={() => setSafety(false)} />}
      <footer className="fqzfoot">
        <Link to="/sound/lab">← La Sala del Lab</Link>
        <a href="/sound/esplora">La biblioteca</a>
        <a href="/sound/impara">Le fondamenta</a>
      </footer>
    </div>
  );
}
