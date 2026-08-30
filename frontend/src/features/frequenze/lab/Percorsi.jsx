/**
 * I PERCORSI — gli esperimenti guidati (LB8, cross-stanza dal ciclo
 * LU, 28/8/2026).
 *
 * Il Lab e' una casa con le stanze; un percorso le attraversa in una
 * storia da fare con le mani. Ogni passo porta alla STANZA giusta
 * con un link vero (non piu' ancore di pagina: le stanze sono
 * pagine). Il percorso aperto si ricorda con sessionStorage — chi
 * torna alla Sala ritrova il suo filo, senza account e senza server.
 * Contenuto puro: nessun nodo audio, nessuno stato condiviso.
 */
import React, { useState } from 'react';
import { Link } from 'react-router-dom';

const CHIAVE_APERTO = 'fqz_lab_percorso';

const PERCORSI = [
  {
    id: 'bottiglia',
    nome: 'Misura la tua bottiglia',
    riga: 'La carta d’identità acustica di un oggetto qualsiasi, in cinque minuti.',
    passi: [
      ['L’Orecchio', '/sound/lab/orecchio', 'Apri il microfono: le letture guardano il mondo. Colpisci la bottiglia e osserva lo spettro, i picchi che appaiono sono i SUOI modi. Il «ping» del vetro è in alto; se soffi sul collo, il tono grave è la risonanza dell’aria.'],
      ['Il Ritratto', '/sound/lab/ritratto', 'Registra e analizza: colpisci appena parte il conto. La tabella ti dà le frequenze al decimo, le vite, i doppietti.'],
      ['La campana rifatta', '/sound/lab/ritratto', 'A/B con l’originale: la rifusione è la somma dei modi in tabella. Spegni un parziale e risenti la differenza.'],
      ['Le Risonanze', '/sound/lab/risonanze', 'Interroga l’oggetto con lo sweep: dove la curva fa un picco, l’oggetto canta. Con l’acqua dentro, rifai la misura: la risonanza dell’aria sale, il ping del vetro scende.'],
    ],
  },
  {
    id: 'geometria',
    nome: 'La geometria degli intervalli',
    riga: 'Vedere la consonanza: i rapporti semplici disegnano figure quiete.',
    passi: [
      ['Le Meraviglie', '/sound/lab/meraviglie', 'Avvia «2:1, l’ottava»: due voci del banco in rapporto perfetto. Poi porta l’oscilloscopio (qui sotto) in XY: l’otto che vedi È l’ottava.'],
      ['La quinta', '/sound/lab/meraviglie', 'Ora «3:2, la quinta»: un nodo in più nella figura. Più il rapporto è semplice, più il disegno è quieto.'],
      ['Stona il rapporto', '/sound/lab/banco', 'Al Banco, accendi le due voci a mano e muovi la B di +0,5 Hz: la figura si mette a ruotare, è la fase che scorre.'],
      ['Phi', '/sound/lab/meraviglie', 'Il rapporto aureo: il numero «più irrazionale» non chiude mai la figura, e il battimento non si ripete mai.'],
    ],
  },
  {
    id: 'orecchio',
    nome: 'L’orecchio che inventa',
    riga: 'Due suoni che senti e che nell’aria non esistono, con la prova.',
    passi: [
      ['Il terzo suono', '/sound/lab/meraviglie', 'Avvia «Tartini»: 1200 e 1500 Hz a volume discreto. Ascolta in basso: c’è un 300 Hz. Poi guarda lo spettro qui sotto: a 300 Hz NON c’è nessun picco, lo genera la tua coclea.'],
      ['La fondamentale fantasma', '/sound/lab/meraviglie', 'Avvia «la fondamentale fantasma»: 400+600+800 senza il 200, e il cervello sente il 200. È il motivo per cui la voce al telefono conserva l’altezza senza i bassi.'],
      ['L’accordatore', '/sound/lab/orecchio', 'Apri il microfono e canta la nota che «senti»: l’accordatore ti dice quanto l’orecchio ci ha preso.'],
    ],
  },
];

export default function Percorsi() {
  const [aperto, setAperto] = useState(() => {
    try { return sessionStorage.getItem(CHIAVE_APERTO) || null; }
    catch { return null; }
  });
  const alterna = (id) => {
    const nuovo = aperto === id ? null : id;
    setAperto(nuovo);
    try {
      if (nuovo) sessionStorage.setItem(CHIAVE_APERTO, nuovo);
      else sessionStorage.removeItem(CHIAVE_APERTO);
    } catch { /* senza memoria di sessione si vive lo stesso */ }
  };
  return (
    <section className="lab-card lab-percorsi" data-testid="lab-percorsi">
      <div className="lab-chead">
        <h2>I Percorsi</h2>
        <span className="lab-cnote">esperimenti guidati che attraversano le stanze, parti da qui se è la prima volta</span>
      </div>
      {PERCORSI.map((p) => (
        <div key={p.id} className={'lab-mer' + (aperto === p.id ? ' viva' : '')}
          data-testid={`lab-percorso-${p.id}`}>
          <div className="lab-mer-riga">
            <button type="button"
              className={'lab-freeze' + (aperto === p.id ? ' fermo' : '')}
              data-testid={`lab-percorso-${p.id}-apri`}
              aria-expanded={aperto === p.id}
              onClick={() => alterna(p.id)}>
              {aperto === p.id ? '▾' : '▸'}
            </button>
            <div className="lab-mer-testo">
              <b>{p.nome}</b>
              <span>{p.riga}</span>
            </div>
          </div>
          {aperto === p.id && (
            <ol className="lab-percorso-passi">
              {p.passi.map(([dove, via, testo], i) => (
                <li key={i}>
                  <Link to={via}>{dove}</Link>, {testo}
                </li>
              ))}
            </ol>
          )}
        </div>
      ))}
    </section>
  );
}
