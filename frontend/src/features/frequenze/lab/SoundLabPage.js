/**
 * /sound/lab — IL LABORATORIO (STEP 0, 25/8/2026).
 *
 * Il banco: la biblioteca spiega il suono, qui il suono si genera, si
 * osserva, si misura. Una sorgente (col suo sweep) e tre letture —
 * tempo, frequenze, frequenze nel tempo — tutte sullo stesso motore.
 *
 * La pagina POSSIEDE il ciclo di vita del motore: `ottieniLab()` crea
 * AudioContext + laboratorio al primo gesto (mai prima: iOS vuole il
 * tocco) e lo presta ai pannelli. I pannelli non creano nodi audio.
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import SoundTopbar from '../SoundTopbar';
import { SafetyCurtain, SafetyLine } from '../SafetyCurtain';
import Generatore from './Generatore';
import Oscilloscopio from './Oscilloscopio';
import Spettro from './Spettro';
import Spettrogramma from './Spettrogramma';
import { creaLaboratorio } from './motore';
import { ascoltaFermo, congela, eFermo } from './quadro';
import '../frequenze.css';
import './lab.css';

export default function SoundLabPage() {
  useEffect(() => { document.title = 'Aurya Sound Lab — Il laboratorio del suono'; }, []);
  const [safety, setSafety] = useState(false);
  const labRef = useRef(null);

  const ottieniLab = () => {
    if (!labRef.current) {
      const Ctx = window.AudioContext || window.webkitAudioContext;
      labRef.current = creaLaboratorio(new Ctx());
    }
    return labRef.current;
  };

  /* LA PRESA, una sola e STABILE. Era un'arrow scritta nel JSX: ne
     nasceva una nuova a ogni render della pagina, e i tre pittori si
     disiscrivevano e riscrivevano per nulla. Con uno stato di pagina
     (il congelamento, qui sotto) sarebbe successo a ogni clic. */
  const ottieniAnalisi = useCallback(() => labRef.current?.analisi || null, []);

  /* IL TEMPO VISIVO E' DEL BANCO, e vive nel quadro: qui non se ne
     tiene una copia, ci si iscrive. Congelare non tocca il suono. */
  const [fermo, setFermo] = useState(eFermo());
  useEffect(() => ascoltaFermo(setFermo), []);

  /* la striscia deve poter distinguere «ferme mentre suona» da
     «ferme e basta»: il generatore avvisa quando si accende o si
     spegne, cosi' il testo non promette un suono che non c'e'. */
  const [suona, setSuona] = useState(false);
  /* l'avviso serve a FAR ridisegnare la striscia; la verita', quando
     si ridisegna, si chiede al motore — cosi' resta onesta anche se un
     giorno qualcuno spegnesse il suono senza passare dal pulsante. */
  const suonaDavvero = labRef.current
    ? labRef.current.generatore.stato().attivo
    : suona;

  /* lasciare la pagina spegne il banco — e scongela, altrimenti il
     tempo fermo resterebbe fermo anche al ritorno */
  useEffect(() => () => { labRef.current?.spegni(); congela(false); }, []);

  return (
    <div className="fqz lab" data-testid="lab-page">
      <SoundTopbar firma="Lab" qui="/sound/lab" />
      <header>
        <div>
          <h1>Il <em>Laboratorio</em></h1>
          <div className="sub">Genera un segnale. Osservalo. Misuralo.</div>
          <p className="sld-parentela">
            La biblioteca spiega il suono: qui il suono si tocca. Un vero
            generatore di segnali nel tuo dispositivo — niente registrazioni,
            niente trucchi: l'onda che senti è calcolata mentre la ascolti.
          </p>
        </div>
      </header>
      <main>
        <Generatore ottieniLab={ottieniLab} onSuono={setSuona} />

        {/* IL COMANDO DEL BANCO: uno solo, fra la sorgente e le sue
            letture — perche' e' li' che passa il confine fra il tempo
            del suono e il tempo dell'immagine. */}
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
                ? 'le tre letture sono ferme — il suono continua'
                : 'le tre letture sono ferme')
              : 'un segnale, un tempo, tre letture'}
          </span>
        </div>

        {/* l'oscilloscopio riceve SOLO l'analisi: non sa chi genera il
            segnale — domani sara' il microfono e non cambiera' riga */}
        <Oscilloscopio ottieniAnalisi={ottieniAnalisi} fermo={fermo} />

        {/* stessa presa, altro dominio: il tempo sopra, le frequenze
            qui. Nemmeno lo spettro sa chi genera il segnale. */}
        <Spettro ottieniAnalisi={ottieniAnalisi} fermo={fermo} />

        {/* e il tempo dello spettro: stessa presa, terza lettura */}
        <Spettrogramma ottieniAnalisi={ottieniAnalisi} fermo={fermo} />

        {/* le controindicazioni valgono anche qui, stessa porta */}
        <SafetyLine onOpen={() => setSafety(true)} />

        <p className="lab-arrivo" data-testid="lab-arrivo">
          Un segnale, un tempo, tre letture: quello che senti è quello
          che vedi, misurato mentre accade.
        </p>
      </main>
      {safety && <SafetyCurtain mode="review" onClose={() => setSafety(false)} />}
      <footer className="fqzfoot">
        <a href="/sound">← Aurya Sound</a>
        <a href="/sound/esplora">La biblioteca</a>
        <a href="/sound/impara">Le fondamenta</a>
      </footer>
    </div>
  );
}
