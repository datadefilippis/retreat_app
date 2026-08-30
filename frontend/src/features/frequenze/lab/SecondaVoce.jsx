/**
 * SECONDA VOCE — la sorgente B del banco (LB1, 27/8/2026).
 *
 * Il pannello e' la meta' compatta del Generatore: stessa fabbrica
 * nel motore (generatore2), stessi gesti — forma, frequenza, fase,
 * ampiezza, «dove suona» — perche' con DUE voci il Lab mantiene
 * quello che finora prometteva soltanto:
 *
 *   - stessa frequenza + fase a 180° → interferenza distruttiva
 *     (il suono cala, e nell'oscilloscopio si vede perche');
 *   - frequenze vicine (440 e 444) nello stesso orecchio →
 *     battimenti monaurali: il battito a 4 Hz E' la differenza;
 *   - una voce per orecchio → il binaurale da banco, quello che il
 *     prodotto usa nelle sessioni, qui smontato e misurabile.
 *
 * React e' solo la mano sui comandi: il suono vive in motore.js.
 */
import React, { useEffect, useRef, useState } from 'react';
import { FORME, ORECCHIE } from './motore';

const MIN_UI = 20, MAX_UI = 20000;
const posAHz = (p) => MIN_UI * Math.pow(MAX_UI / MIN_UI, p);
const hzAPos = (hz) => Math.log(hz / MIN_UI) / Math.log(MAX_UI / MIN_UI);

const ETICHETTE = {
  sine: 'Sinusoide', square: 'Quadra',
  triangle: 'Triangolare', sawtooth: 'Dente di sega',
};
const ORECCHIO_LBL = {
  entrambe: 'Entrambe le orecchie', sinistra: 'Solo sinistra', destra: 'Solo destra',
};

export default function SecondaVoce({ ottieniLab, onSuono }) {
  const [forma, setForma] = useState('sine');
  const [freq, setFreq] = useState(444);          // a 4 Hz dalla A: i battimenti
  const [campo, setCampo] = useState('444');
  const [amp, setAmp] = useState(0.25);
  const [fase, setFase] = useState(0);
  const [orecchio, setOrecchio] = useState('entrambe');
  const [attivo, setAttivo] = useState(false);
  const labRef = useRef(null);

  const comanda = (patch) => { labRef.current?.generatore2.imposta(patch); };

  const confermaCampo = () => {
    const v = parseFloat(String(campo).replace(',', '.'));
    if (!Number.isFinite(v)) { setCampo(String(freq)); return; }
    const f = Math.min(Math.max(v, MIN_UI), MAX_UI);
    setFreq(f); setCampo(String(f));
    comanda({ freq: f });
  };

  const scegliFreq = (f) => {
    const v = Math.round(f * 100) / 100;
    setFreq(v); setCampo(String(v));
    comanda({ freq: v });
  };

  const alterna = async () => {
    const lab = ottieniLab();                     // nasce QUI, nel gesto
    labRef.current = lab;
    if (attivo) { lab.generatore2.ferma(); setAttivo(false); onSuono?.(); return; }
    lab.generatore2.imposta({ forma, freq, amp, orecchio,
      fase: (fase * Math.PI) / 180 });
    await lab.generatore2.avvia();
    setAttivo(true); onSuono?.();
  };

  useEffect(() => () => { labRef.current?.generatore2.ferma(); }, []);

  return (
    <section className="lab-card lab-voce2" data-testid="lab-voce2">
      <div className="lab-chead">
        <h2>Sorgente B</h2>
        <span className="lab-cnote">la seconda voce: da qui nascono interferenza e battimenti</span>
      </div>

      <div className="lab-voce2-riga">
        {/* la forma, compatta */}
        <label className="lab-par lab-voce2-forma">
          <span>Forma</span>
          <select value={forma} aria-label="Forma d'onda della sorgente B"
            data-testid="lab-voce2-forma"
            onChange={(e) => { setForma(e.target.value); comanda({ forma: e.target.value }); }}>
            {FORME.map((f) => <option key={f} value={f}>{ETICHETTE[f]}</option>)}
          </select>
        </label>
        {/* dove suona */}
        <label className="lab-par lab-voce2-orecchio">
          <span>Dove suona</span>
          <select value={orecchio} aria-label="Canale della sorgente B"
            data-testid="lab-voce2-orecchio"
            onChange={(e) => { setOrecchio(e.target.value); comanda({ orecchio: e.target.value }); }}>
            {ORECCHIE.map((o) => <option key={o} value={o}>{ORECCHIO_LBL[o]}</option>)}
          </select>
        </label>
      </div>

      {/* la frequenza */}
      <div className="lab-freq lab-voce2-freq">
        <div className="lab-freq-num">
          <input value={campo} inputMode="decimal"
            aria-label="Frequenza della sorgente B in Hertz"
            data-testid="lab-voce2-campo"
            onChange={(e) => setCampo(e.target.value)}
            onBlur={confermaCampo}
            onKeyDown={(e) => { if (e.key === 'Enter') { confermaCampo(); e.target.blur(); } }} />
          <b>Hz</b>
        </div>
        <input type="range" className="lab-slider" min="0" max="1" step="0.0005"
          aria-label="Frequenza della sorgente B (scala logaritmica)"
          value={hzAPos(freq)}
          onChange={(e) => scegliFreq(posAHz(+e.target.value))} />
      </div>

      <div className="lab-parametri">
        <label className="lab-par">
          <span>Ampiezza <b>{Math.round(amp * 100)}%</b></span>
          <input type="range" className="lab-slider" min="0" max="1" step="0.01"
            value={amp}
            onChange={(e) => { const a = +e.target.value; setAmp(a); comanda({ amp: a }); }} />
        </label>
        <label className="lab-par">
          <span>Fase <b>{fase}°</b></span>
          <input type="range" className="lab-slider" min="0" max="360" step="1"
            value={fase}
            onChange={(e) => {
              const g = +e.target.value; setFase(g);
              comanda({ fase: (g * Math.PI) / 180 });
            }} />
        </label>
      </div>

      <div className="lab-azione">
        <button type="button" className={'lab-play' + (attivo ? ' fermo' : '')}
          data-testid="lab-voce2-play" onClick={alterna}>
          {attivo ? '■ Ferma B' : '▶ Genera B'}
        </button>
        <p className="lab-volume">
          Due voci si sommano: con entrambe accese tieni le ampiezze
          più basse del solito.
        </p>
      </div>

      {/* la didascalia, ogni modulo si racconta (regola LB) */}
      <p className="lab-didascalia" data-testid="lab-voce2-didascalia">
        <b>Cosa provare.</b> Stessa frequenza della A e fase a 180°: le
        onde si cancellano (interferenza). 440 e 444 Hz nello stesso
        orecchio: senti un battito a 4 Hz, è la differenza tra le due.
        Una voce per orecchio (in cuffia): è il principio binaurale
        delle sessioni, qui sul banco.
      </p>
    </section>
  );
}
