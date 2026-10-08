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
 *
 * LOTTO LA (8/10/2026 sera, founder: «rendi il Lab usabile, moderno,
 * immediato, multipiattaforma, anche con popup»): dietro LAB_VESTITO_NUOVO
 * il telaio veste il nuovo. Lo strumento in primo piano: «Perché ti
 * interessa» e «Cosa puoi fare qui» stanno in un FOGLIO «?» che si apre da
 * solo alla prima visita della stanza (poi resta a un tocco); il selettore
 * a tre e la RIGA DELLE STANZE al posto della barra vecchia; le letture
 * ACCANTO ai comandi (`letture`: due colonne su desktop, striscia sticky
 * sul telefono); le didascalie si ripiegano con un tocco. Gli strumenti
 * non cambiano: stesso markup, stessi handler, stessi testid.
 * ?vestito=vecchio mostra il telaio di prima.
 */
import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import SoundTopbar from '../SoundTopbar';
import InvitoSound from '../InvitoSound';
import StanzeSound from '../StanzeSound';
import SelettoreTre from '../esplora/SelettoreTre';
import { SafetyCurtain, SafetyLine } from '../SafetyCurtain';
import { LAB_VESTITO_NUOVO, SOUND_ESPLORA_NUOVA } from '../stato';
import '../frequenze.css';
import '../esplora/esplora.css';
import './lab.css';
import './lab-vestito.css';

export const STANZE_RIGA = [
  ['banco', 'Banco'],
  ['orecchio', 'Orecchio'],
  ['ritratto', 'Ritratto'],
  ['meraviglie', 'Meraviglie'],
  ['risonanze', 'Risonanze'],
];

export function vestitoNuovo() {
  let vecchio = false;
  try { vecchio = new URLSearchParams(window.location.search).get('vestito') === 'vecchio'; } catch { /* ssr */ }
  return LAB_VESTITO_NUOVO && !vecchio;
}

/* la riga delle stanze: cinque pastiglie, la corrente accesa, e il «?» */
export function RigaStanze({ slug, onSpiega }) {
  return (
    <nav className="lab-riga-stanze" data-testid="lab-riga-stanze" aria-label="Le stanze del Lab">
      <div className="lab-riga-scroll">
        {STANZE_RIGA.map(([id, nome]) => (
          <Link key={id} to={`/sound/lab/${id}`} className={`lab-stanza-pill${slug === id ? ' on' : ''}`}
            aria-current={slug === id ? 'page' : undefined} data-testid={`lab-riga-${id}`}>{nome}</Link>
        ))}
      </div>
      {onSpiega && (
        <button type="button" className="lab-spiega-apri" data-testid="lab-spiega-apri"
          title="Perché ti interessa e cosa puoi fare qui" onClick={onSpiega}>?</button>
      )}
    </nav>
  );
}

export default function Stanza({
  slug,                 // 'banco' | 'orecchio' | ...
  titolo,               // «Il Banco»
  domanda,              // la domanda a cui la stanza risponde
  perche,               // il perche' per il neofita (stringa o nodo)
  azioni = [],          // 3 azioni concrete
  senzaSuono = false,   // la Sala non suona: niente riga di sicurezza
  lettureUltime = false, // LA2: l'ULTIMO figlio sono le letture, da mettere accanto ai comandi
  children,
}) {
  const nuovo = vestitoNuovo();
  /* i figli restano nell'ordine di sempre (SORGENTI poi LETTURE); il telaio
     separa l'ultimo e lo affianca */
  const figli = React.Children.toArray(children);
  const letture = lettureUltime && figli.length > 1 ? figli[figli.length - 1] : null;
  const comandi = letture ? figli.slice(0, -1) : figli;
  const [safety, setSafety] = useState(false);
  const [spiega, setSpiega] = useState(false);
  useEffect(() => {
    document.title = `${titolo} | Aurya Sound Lab`;
  }, [titolo]);
  /* LA1 — alla PRIMA visita di ogni stanza il foglio si apre da solo; poi
     resta a un tocco. Storage in try/catch: mai bloccare il banco. */
  useEffect(() => {
    if (!nuovo) return;
    try {
      const k = `fqz_lab_spiega_${slug}`;
      if (!localStorage.getItem(k)) { setSpiega(true); localStorage.setItem(k, '1'); }
    } catch { /* privato: il foglio resta a un tocco */ }
  }, [slug, nuovo]);
  /* LA1 — le didascalie degli strumenti si ripiegano con un tocco: la
     delega vive qui, i componenti non cambiano. */
  const toccoDidascalia = (e) => {
    if (!nuovo) return;
    const d = e.target.closest('.lab-didascalia');
    if (d && !e.target.closest('a, button, input, select')) d.classList.toggle('aperta');
  };

  const testata = (
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
  );

  return (
    <div className={`fqz lab${nuovo ? ' vestito' : ''}`} data-testid={`lab-stanza-${slug}`}>
      <SoundTopbar firma="Lab" qui="/sound/lab" />
      <header>
        <div>
          <p className="lab-ritorno">
            <Link to="/sound/lab" data-testid="lab-ritorno-sala">← Sala del Lab</Link>
          </p>
          <h1>{titolo}</h1>
          <div className="sub" data-testid="lab-domanda">{domanda}</div>
        </div>
        {!nuovo && <StanzeSound attiva="lab" />}
      </header>
      <main onClick={toccoDidascalia}>
        {nuovo && (
          <>
            {SOUND_ESPLORA_NUOVA ? <SelettoreTre attiva="lab" /> : <StanzeSound attiva="lab" />}
            <RigaStanze slug={slug} onSpiega={() => setSpiega(true)} />
          </>
        )}
        {!nuovo && testata}

        {nuovo && letture ? (
          <div className="lab-due-colonne" data-testid="lab-due-colonne">
            <div className="lab-col-comandi">{comandi}</div>
            <div className="lab-col-letture" data-testid="lab-col-letture">{letture}</div>
          </div>
        ) : children}

        <div className="lab-coda">
          {!senzaSuono && <SafetyLine onOpen={() => setSafety(true)} />}
          <p className="lab-glossario-ponte" data-testid="lab-glossario-ponte">
            Hertz, spettro, parziale… parole nuove?{' '}
            <Link to="/sound/impara/glossario">Il glossario le spiega tutte →</Link>
          </p>
        </div>
      </main>
      {safety && <SafetyCurtain mode="review" onClose={() => setSafety(false)} />}
      {nuovo && spiega && (
        <div className="gate lab-foglio" onClick={() => setSpiega(false)} data-testid="lab-spiega-foglio">
          <div className="gatebox" onClick={(e) => e.stopPropagation()}>
            <div className="lab-foglio-testa">
              <div>
                <h2>{titolo}</h2>
                <p className="lab-foglio-domanda">{domanda}</p>
              </div>
              <button type="button" className="lab-x" aria-label="Chiudi" onClick={() => setSpiega(false)}>×</button>
            </div>
            {testata}
            <div className="gatefoot">
              <button type="button" className="primary" data-testid="lab-spiega-vai" onClick={() => setSpiega(false)}>Allo strumento →</button>
            </div>
          </div>
        </div>
      )}
      {/* FA8, l'invito del mondo Sound, con la fonte della stanza
          (regola del silenzio nel componente) */}
      <div className="lab-invito-fondo">
        <InvitoSound fonte={`sound:lab:${slug}`} dove={`/sound/lab/${slug}`} />
      </div>
      <footer className="fqzfoot">
        <Link to="/sound/lab">← La Sala del Lab</Link>
        <a href="/sound/esplora">La biblioteca</a>
        <a href="/sound/impara">Le fondamenta</a>
      </footer>
    </div>
  );
}
