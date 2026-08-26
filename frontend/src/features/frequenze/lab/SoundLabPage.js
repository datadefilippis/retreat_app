/**
 * /sound/lab — IL LABORATORIO (STEP 0, 25/8/2026).
 *
 * Il banco: la biblioteca spiega il suono, qui il suono si genera, si
 * osserva, si misura. V1 = il Generatore; oscilloscopio, spettro e
 * sweep arrivano a passi, sullo stesso motore.
 *
 * La pagina POSSIEDE il ciclo di vita del motore: `ottieniLab()` crea
 * AudioContext + laboratorio al primo gesto (mai prima: iOS vuole il
 * tocco) e lo presta ai pannelli. I pannelli non creano nodi audio.
 */
import React, { useEffect, useRef, useState } from 'react';
import SoundTopbar from '../SoundTopbar';
import { SafetyCurtain, SafetyLine } from '../SafetyCurtain';
import Generatore from './Generatore';
import Oscilloscopio from './Oscilloscopio';
import { creaLaboratorio } from './motore';
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

  /* lasciare la pagina spegne il banco */
  useEffect(() => () => { labRef.current?.spegni(); }, []);

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
        <Generatore ottieniLab={ottieniLab} />

        {/* l'oscilloscopio riceve SOLO l'analisi: non sa chi genera il
            segnale — domani sara' il microfono e non cambiera' riga */}
        <Oscilloscopio ottieniAnalisi={() => labRef.current?.analisi || null} />

        {/* le controindicazioni valgono anche qui, stessa porta */}
        <SafetyLine onOpen={() => setSafety(true)} />

        <p className="lab-arrivo" data-testid="lab-arrivo">
          Il banco crescerà: analizzatore di spettro e sweep di frequenza
          si costruiscono qui, sullo stesso motore.
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
