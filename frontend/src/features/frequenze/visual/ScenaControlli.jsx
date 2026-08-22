/**
 * La scena, scelta dall'autore (VC3/VC4, 22/8/2026).
 *
 * Questa NON e' una seconda versione dei pannelli: e' una tastiera
 * diversa sullo stesso strumento. Preset, palette, forme e cursori
 * arrivano da visual/tabelle.js — LO STANDARD e' /sound/visual
 * (decisione founder: «se aggiungeremo nuovi preset o nuove variabili,
 * compariranno anche in Crea») — e ogni gesto chiama applica() sul
 * motore montato, che e' lo stesso file della pagina strumento.
 *
 * Tre piani di sforzo: chi non apre niente ha il default; un tocco su
 * un preset cambia la scena dal vivo; «Regola fine» apre gli 11
 * cursori per chi esplora. Le etichette sono italiane dove le
 * conosciamo; una variabile nuova nello standard compare comunque,
 * con la sua etichetta originale, finche' qualcuno non la traduce.
 */
import React, { useState } from 'react';
import { SLIDERS, PALETTES, PRESETS, CAMS } from './tabelle';
import './incorporato.css';

const ETICHETTE = {
  intensity: 'Intensità', scale: 'Scala', speed: 'Velocità',
  breath: 'Ciclo respiro', drift: 'Deriva', particles: 'Particelle',
  glow: 'Bagliore', trails: 'Scie', depth: 'Profondità',
  brightness: 'Luce', contrast: 'Contrasto',
};
const CAM_IT = { Orbit: 'Orbita', Still: 'Ferma', Breathe: 'Respiro', Drift: 'Deriva' };

export default function ScenaControlli({ motore, visual, onCambia }) {
  const [fine, setFine] = useState(false);
  const [presetSu, setPresetSu] = useState(null);   // solo evidenza, non verita'

  /* la verita' dei valori: cio' che il motore sta suonando adesso;
     prima che monti, cio' che la bozza ricorda */
  const stato = motore ? motore.leggi() : (visual || {});

  const gesto = (patch, preset = null) => {
    if (!motore) return;
    motore.applica(patch);
    setPresetSu(preset);
    onCambia(motore.leggi());     // nella bozza vanno valori RISOLTI
  };

  return (
    <div className="scnc" data-testid="fqc-scena">
      {/* piano 1 — un tocco: i preset dello standard, a occhio */}
      <div className="scnc-riga" role="group" aria-label="Preset della scena">
        {PRESETS.map((p, k) => (
          <button key={p.name} type="button"
            className={`scnc-preset${presetSu === k ? ' su' : ''}`}
            data-testid={`fqc-scena-preset-${k}`}
            disabled={!motore}
            onClick={() => gesto({ mode: p.mode, pal: p.pal, ...p.over }, k)}>
            <span className="scnc-punti" aria-hidden>
              {(PALETTES[p.pal]?.c || []).map((c, i) => (
                <i key={i} style={{ background: c }} />
              ))}
            </span>
            {p.name}
          </button>
        ))}
      </div>

      {/* il colore da solo, tenendo la forma */}
      <div className="scnc-riga" role="group" aria-label="Palette dei colori">
        {PALETTES.map((p, k) => (
          <button key={p.name} type="button" title={p.name}
            className={`scnc-pal${stato.pal === k ? ' su' : ''}`}
            data-testid={`fqc-scena-pal-${k}`}
            disabled={!motore}
            style={{ background: p.sw }}
            onClick={() => gesto({ pal: k })} />
        ))}
        <button type="button" className="scnc-cam" disabled={!motore}
          data-testid="fqc-scena-cam"
          onClick={() => gesto({ cam: ((stato.cam ?? 0) + 1) % CAMS.length })}>
          Camera: {CAM_IT[CAMS[stato.cam ?? 0]] || CAMS[stato.cam ?? 0]}
        </button>
      </div>

      {/* piano 2 — per chi esplora */}
      <button type="button" className="scnc-fine" disabled={!motore}
        data-testid="fqc-scena-fine"
        onClick={() => setFine((v) => !v)}>
        {fine ? 'Chiudi le regolazioni' : 'Regola fine'} {fine ? '▴' : '▾'}
      </button>
      {fine && motore && (
        <div className="scnc-cursori">
          {SLIDERS.map(([k, label, min, max, , unit]) => (
            <label key={k} className="scnc-ctl">
              <span>
                {ETICHETTE[k] || label}
                <b>{stato[k]}{unit}</b>
              </span>
              <input type="range" min={min} max={max} step="1"
                value={stato[k] ?? min}
                data-testid={`fqc-scena-${k}`}
                onChange={(e) => gesto({ [k]: +e.target.value })} />
            </label>
          ))}
        </div>
      )}
    </div>
  );
}
