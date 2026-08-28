/**
 * I PERCORSI — gli esperimenti guidati (LB8, 28/8/2026).
 *
 * Il Lab e' pieno di strumenti; un percorso li lega in una storia da
 * fare con le mani. Tre esperimenti passo-passo, ognuno attraversa
 * piu' moduli — e' qui che «utile e interessante» diventa concreto.
 * Contenuto puro: nessun nodo audio, nessuno stato condiviso.
 */
import React, { useState } from 'react';

const PERCORSI = [
  {
    id: 'bottiglia',
    nome: 'Misura la tua bottiglia',
    riga: 'La carta d’identità acustica di un oggetto qualsiasi, in cinque minuti.',
    passi: [
      ['L’Orecchio', '#lab-sezione-orecchio', 'Apri il microfono: le tre letture ora guardano il mondo.'],
      ['Il colpo', '#lab-sezione-orecchio', 'Colpisci la bottiglia (o un bicchiere) e guarda lo spettro: i picchi che appaiono sono i SUOI modi. Il «ping» del vetro è in alto; se soffi sul collo, il tono grave è la risonanza dell’aria (Helmholtz).'],
      ['Il Ritratto', '#lab-sezione-ritratto', 'Registra e analizza: colpisci appena parte il conto. La tabella ti dà le frequenze al decimo, le vite, i doppietti.'],
      ['La campana rifatta', '#lab-sezione-ritratto', 'A/B con l’originale: la rifusione è la somma dei modi in tabella. Spegni un parziale e risenti.'],
      ['Le Risonanze', '#lab-sezione-risonanze', 'Ora interroga l’oggetto con lo sweep: dove la curva fa un picco, l’oggetto canta. Con l’acqua dentro, rifai la misura: la risonanza dell’aria sale, il ping del vetro scende.'],
    ],
  },
  {
    id: 'geometria',
    nome: 'La geometria degli intervalli',
    riga: 'Vedere la consonanza: i rapporti semplici disegnano figure quiete.',
    passi: [
      ['I Rapporti', '#lab-sezione-meraviglie', 'Nelle Meraviglie, avvia «2:1, l’ottava»: due voci del banco in rapporto perfetto.'],
      ['Il modo XY', '#lab-sezione-letture', 'Porta l’oscilloscopio in XY: l’otto che vedi È l’ottava. Poi prova la quinta (3:2): un nodo in più.'],
      ['Stona il rapporto', '#lab-sezione-voce2', 'Muovi di poco la frequenza della Sorgente B (+0,5 Hz): la figura si mette a ruotare — è la fase che scorre tra le due voci.'],
      ['Phi', '#lab-sezione-meraviglie', 'Ora il rapporto aureo: il numero «più irrazionale» non chiude mai la figura, e il battimento non si ripete mai.'],
    ],
  },
  {
    id: 'orecchio',
    nome: 'L’orecchio che inventa',
    riga: 'Due suoni che senti e che nell’aria non esistono — con la prova.',
    passi: [
      ['Il terzo suono', '#lab-sezione-meraviglie', 'Avvia «Tartini»: 1200 e 1500 Hz a volume discreto. Ascolta in basso: c’è un 300 Hz.'],
      ['La prova', '#lab-sezione-letture', 'Guarda lo spettro: a 300 Hz NON c’è nessun picco. Quel suono lo sta generando la tua coclea.'],
      ['La fondamentale fantasma', '#lab-sezione-meraviglie', 'Avvia «la fondamentale fantasma»: 400+600+800 senza il 200 — e il cervello sente il 200. È il motivo per cui la voce al telefono conserva l’altezza senza i bassi.'],
      ['L’accordatore', '#lab-sezione-orecchio', 'Riapri il microfono e canta la nota che «senti»: l’accordatore ti dice quanto l’orecchio ci ha preso.'],
    ],
  },
];

export default function Percorsi() {
  const [aperto, setAperto] = useState(null);
  return (
    <section className="lab-card lab-percorsi" data-testid="lab-percorsi"
      id="lab-sezione-percorsi">
      <div className="lab-chead">
        <h2>I Percorsi</h2>
        <span className="lab-cnote">tre esperimenti guidati che legano gli strumenti del banco</span>
      </div>
      {PERCORSI.map((p) => (
        <div key={p.id} className={'lab-mer' + (aperto === p.id ? ' viva' : '')}
          data-testid={`lab-percorso-${p.id}`}>
          <div className="lab-mer-riga">
            <button type="button"
              className={'lab-freeze' + (aperto === p.id ? ' fermo' : '')}
              data-testid={`lab-percorso-${p.id}-apri`}
              aria-expanded={aperto === p.id}
              onClick={() => setAperto(aperto === p.id ? null : p.id)}>
              {aperto === p.id ? '▾' : '▸'}
            </button>
            <div className="lab-mer-testo">
              <b>{p.nome}</b>
              <span>{p.riga}</span>
            </div>
          </div>
          {aperto === p.id && (
            <ol className="lab-percorso-passi">
              {p.passi.map(([dove, ancora, testo], i) => (
                <li key={i}>
                  <a href={ancora}>{dove}</a> — {testo}
                </li>
              ))}
            </ol>
          )}
        </div>
      ))}
    </section>
  );
}
