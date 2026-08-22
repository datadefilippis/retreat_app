/* Il markup del prototipo del founder, INTEGRALE — estratto
   dall'HTML consegnato, non trascritto a mano (fedelta' garantita).
   Statico e nostro: l'iniezione via innerHTML e' sicura. Unica
   aggiunta: la riga privacy nel gate (promessa all'utente) e il
   marchio che riporta a /sound. */
const MARKUP = `
<div id="stage"><canvas id="gl"></canvas></div>
<div id="vig"></div>

<!-- ============ TOP BAR ============ -->
<div id="topbar">
  <div class="pill">
    <svg viewBox="0 0 24 24"><path d="M12 3v10M9 6v4M15 6v4M5 19h14M12 16v3"/><circle cx="12" cy="8" r="4"/></svg>
    <span id="micdot"></span><span id="srcLabel">Sorgente inattiva</span>
    <canvas id="topSpec" class="mini" width="220" height="18" style="width:110px;height:9px"></canvas>
  </div>
</div>
<button id="infoBtn" class="pill" style="cursor:pointer;font-family:inherit">Info</button>

<!-- ============ LEFT PANEL ============ -->
<aside id="left" class="panel">
  <div class="brand">
    <svg viewBox="0 0 24 24"><path d="M12 2C8 7 6 12 6 16c0 3.3 2.7 6 6 6"/><path d="M12 22c3.3 0 6-2.7 6-6 0-4-2-9-6-14"/><path d="M12 22V6"/></svg>
    <a href="/sound" style="text-decoration:none;color:inherit"><h1>AURYA</h1></a>
  </div>
  <div>
    <div class="title" id="presetTitle">COSMOS</div>
    <div class="sub">Immersive Mode</div>
  </div>

  <div class="sect" id="srcSect">
    <div class="lbl">Audio source</div>
    <button class="src on" id="btnMic">
      <svg viewBox="0 0 24 24"><path d="M3 12h2l2-5 2 9 2-12 2 15 2-9 2 4h4"/></svg>Microphone
    </button>
    <button class="src" id="btnFile">
      <svg viewBox="0 0 24 24"><circle cx="7" cy="18" r="2.6"/><path d="M9.6 18V5l10-2v12"/><circle cx="17.2" cy="15" r="2.6"/></svg>Upload Track
    </button>
    <input type="file" id="fileIn" accept="audio/*" hidden>
    <audio id="player" crossorigin="anonymous"></audio>
  </div>

  <div class="rule"></div>

  <div class="sect">
    <div class="lbl">Analysis</div>
    <div>
      <div class="lbl">Frequency range</div>
      <div class="mono" id="freqRange">20 Hz – 20 kHz</div>
    </div>
    <div>
      <div class="lbl">Dominant frequency</div>
      <div class="big" id="domFreq">0 Hz</div>
      <canvas id="wave" class="mini" width="400" height="80" style="width:100%;height:34px"></canvas>
    </div>
  </div>

  <div class="sect" id="meters">
    <div class="ctl"><div class="row"><span class="lbl">Intensity</span><span class="val" id="vInt">0%</span></div>
      <div class="meter m-int"><i id="mInt"></i></div></div>
    <div class="ctl"><div class="row"><span class="lbl">Bass</span><span class="val" id="vBass">0%</span></div>
      <div class="meter m-bass"><i id="mBass"></i></div></div>
    <div class="ctl"><div class="row"><span class="lbl">Mids</span><span class="val" id="vMid">0%</span></div>
      <div class="meter m-mid"><i id="mMid"></i></div></div>
    <div class="ctl"><div class="row"><span class="lbl">Highs</span><span class="val" id="vHigh">0%</span></div>
      <div class="meter m-high"><i id="mHigh"></i></div></div>
    <div class="ctl"><div class="row"><span class="lbl">Breath</span><span class="val" id="vDyn">0%</span></div>
      <div class="meter m-dyn"><i id="mDyn"></i></div></div>
  </div>

  <div class="rule"></div>

  <div class="sect">
    <div class="lbl">Visual preset</div>
    <div class="stepper"><button id="prevPreset">‹</button><span id="presetName">Cosmos</span><button id="nextPreset">›</button></div>
    <div class="lbl">Camera</div>
    <div class="stepper"><span id="camName">Orbit</span><button id="nextCam">›</button></div>
    <div class="lbl">Quality</div>
    <div class="seg" id="quality"><button data-q="0.65">Low</button><button data-q="1">Medium</button><button data-q="1.6" class="on">High</button></div>
  </div>

  <div class="footicons">
    <button id="resetBtn" title="Reset"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M12 3v3M12 18v3M3 12h3M18 12h3M6 6l2 2M16 16l2 2M18 6l-2 2M8 16l-2 2"/></svg></button>
    <button id="fsBtn" title="Fullscreen"><svg viewBox="0 0 24 24"><path d="M4 9V4h5M20 15v5h-5M20 9V4h-5M4 15v5h5"/></svg></button>
  </div>
</aside>

<!-- ============ RIGHT PANEL ============ -->
<aside id="right" class="panel">
  <div class="lbl">Visual controls</div>
  <div id="sliders" class="sect" style="gap:15px"></div>

  <div class="sect">
    <div class="lbl">Color palette</div>
    <div class="swatches" id="palette"></div>
  </div>

  <div class="sect">
    <div class="lbl">Reactivity</div>
    <div class="seg" id="react">
      <button data-r="0.4">Calm</button><button data-r="0.7">Soft</button>
      <button data-r="1.05">Deep</button><button data-r="1.5">Full</button>
    </div>
  </div>

  <div class="sect">
    <div class="lbl">Audio reactivity</div>
    <canvas id="radial" width="330" height="330" style="width:100%;height:auto"></canvas>
  </div>
</aside>

<!-- ============ MODE BAR ============ -->
<div id="modebar">
  <button class="shuffle" id="shuffle" title="Random"><svg viewBox="0 0 24 24" style="width:17px;height:17px;stroke:currentColor;fill:none;stroke-width:1.3"><path d="M12 4a8 8 0 1 1-8 8"/><path d="M4 4v5h5"/></svg></button>
</div>

<button id="hide"><span id="hideTxt">Hide interface</span>
  <svg viewBox="0 0 24 24"><path d="M6 9l6 6 6-6"/></svg></button>

<!-- ============ CHIPS (studio) ============ -->
<div id="chips">
  <button id="chipPreset" type="button">◈ Preset</button>
  <button id="chipRegola" type="button">☼ Regola</button>
  <button id="chipFatto" type="button" class="fatto">✓ Fatto</button>
</div>

<!-- ============ GATE / INFO ============ -->
<div id="gate"><div class="box">
  <h2>AURYA</h2>
  <p>Visualizer immersivo audio-reattivo per la meditazione. Attiva il microfono per far respirare l'immagine con la stanza, oppure carica la tua traccia. <b>Tutto accade sul tuo dispositivo: il tuo audio non viene caricato da nessuna parte.</b></p>
  <button class="cta" id="gateMic">Attiva microfono</button>
  <button class="cta ghost" id="gateFile">Carica traccia</button>
</div></div>

<div id="info"><div class="card">
  <h3>Info</h3>
  <p>L'immagine è un campo di luce generato in tempo reale. Il movimento nasce da tre sorgenti sovrapposte: un respiro lento continuo, una deriva organica basata su rumore simplex, e l'analisi FFT dell'audio (bassi → dilatazione, medi → deriva, alti → scintillio).</p>
  <p>Trascina per orbitare, rotella per avvicinarti. <kbd>H</kbd> nasconde l'interfaccia, <kbd>F</kbd> fullscreen, <kbd>1–7</kbd> forma, <kbd>Spazio</kbd> play/pausa.</p>
  <p style="margin-bottom:0"><button class="cta ghost" id="infoClose" style="margin:8px 0 0">Chiudi</button></p>
</div></div>

`;
export default MARKUP;
