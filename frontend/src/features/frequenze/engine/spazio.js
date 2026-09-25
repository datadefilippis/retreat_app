/**
 * LO SPAZIO — Crea immersivo (CI-F2, 22/9/2026, decisioni del founder).
 *
 * In cuffia il «3D» e' la spazializzazione HRTF: un PannerNode con la
 * posizione della sorgente rispetto alla testa. Una sorgente che ORBITA
 * e' un panner mosso nel tempo. Il «9D» del marketing e' questo piu' una
 * stanza (riverbero). Non c'e' altro dietro, e qui lo diciamo con
 * cinque parole per strato e quattro per la stanza: chi vuole i numeri
 * li trova nel Lab (Orbita).
 *
 * UNICA VERITA' per tre consumatori: l'anteprima dal vivo (synth.js),
 * il master e l'export (render.js, a blocchi) e l'ascolto continuo
 * (continuo.js passa da render). Per questo la posizione NON e' un
 * LFO che gira per conto suo (come nel Lab): e' una FUNZIONE del tempo
 * dello strato, `posizione(preset, u)`, cosi' il blocco 37 del master
 * calcola lo stesso punto dell'anteprima al secondo 740.
 *
 * LE REGOLE (founder, 22/9):
 *  - la VOCE guida NON ruota di default (`fermo`): e' il punto fermo
 *    di chi medita a occhi chiusi. Puo' farlo per scelta (orbita
 *    lenta / respira), e ha due preset suoi: «vicina» (si avvicina
 *    nei primi secondi) e «a lato» (fissa a 30°, per una seconda voce).
 *  - i BINAURALI non passano MAI da qui: il battimento vive nella
 *    differenza fra i due orecchi e l'HRTF li mescola. Gli strati
 *    `neuro` restano fuori da questo modulo per costruzione (nel
 *    master sono sintesi analitica, non nodi).
 *  - `space` ASSENTE = nessun nodo creato = grafo identico a ieri: le
 *    tracce pubblicate suonano byte per byte com'erano.
 *  - orbite LENTE per meditare (un giro ogni 12-30 s); lo 0,2 Hz dei
 *    video «8D» e' una giostra.
 */

/* Il preset per strato: raggio (m), velocita' (giri al secondo), quota
   (m), ampiezza dell'oscillazione (gradi) per «respira», e quanto manda
   alla Stanza. `kinds` dice a quali strati si offre. */
export const SPACE_PRESETS = Object.freeze({
  fermo: { label: 'fermo', kinds: ['audio', 'voice', 'guida'], hint: 'Davanti, al centro. Com’e’ sempre stato.' },
  respira: { label: 'respira', kinds: ['audio', 'voice', 'guida'], r: 1.5, sway: 35, swayHz: 0.06, send: 0.15,
    mono: true, rinforzo: 0.5, comp: 1.41,
    hint: 'Oscilla piano a destra e a sinistra, come un respiro.' },
  orbita_lenta: { label: 'orbita lenta', kinds: ['audio', 'voice', 'guida'], r: 1.6, rate: 1 / 24, send: 0.2,
    mono: true, rinforzo: 0.6, comp: 1.6,
    hint: 'Un giro intorno alla testa ogni 24 secondi.' },
  orbita: { label: 'orbita', kinds: ['audio'], r: 1.8, rate: 1 / 8, send: 0.2,
    mono: true, rinforzo: 0.7, comp: 1.7,
    hint: 'Un giro ogni 8 secondi: per la danza, non per dormire.' },
  avvolge: { label: 'avvolge', kinds: ['audio'], r: 2.4, rate: 1 / 20, riseY: 1.2, riseSec: 60, send: 0.45,
    mono: true, rinforzo: 0.55, comp: 1.7,
    hint: 'Largo, sale sopra la testa e riempie la stanza.' },
  vicina: { label: 'vicina', kinds: ['voice', 'guida'], r0: 2.2, r1: 0.6, approachSec: 6, send: 0, comp: 1.15,
    hint: 'Parte lontana e in sei secondi arriva vicino: presenza.' },
  a_lato: { label: 'a lato', kinds: ['voice', 'guida'], r: 1.0, angle: 30, send: 0, rinforzo: 0.4, comp: 1.05,
    hint: 'Fissa a 30 gradi sulla destra: per una seconda voce.' },
});

/* LA COMPENSAZIONE (22/9 sera, founder: «nei suoni spaziali il volume
   diventa molto piu' basso rispetto a fermo, e' corretto?»). E' fisica
   — una sorgente a 1,6 m e' piu' piana di una «nella testa»: l'HRTF
   toglie in media 2-3 dB, il modello di distanza 3-5, il downmix mono
   di uno stereo largo altri 2-3 — ma per chi compone e' sbagliato:
   scegliere un preset non deve cambiare il volume, il volume ha il suo
   cursore. `comp` riporta la POTENZA MEDIA su un giro intero a quella
   di «fermo», misurata su due basi vere (un pad stereo e una melodia):
   respira −2,3/−3,8 dB, orbita lenta −4,0/−4,9, orbita −6,3/−6,4,
   avvolge −3,5/−7,3, vicina −1,1/−2,2 (solo la partenza lontana),
   a lato −0,4. Un guadagno fisso: identico dal vivo e nel master.
   Tetto a 1,7 (+4,6 dB): con la compensazione piena, un file gia' a
   fondo scala spinto su un orecchio solo passava 1,0 di picco (pad:
   1,67 su «avvolge»); cosi' orbita e avvolge restano ~1 dB sotto
   «fermo», che non si sente, e i picchi restano nel margine del
   volume di strato (0,7 di default). */

/* IL RINFORZO (22/9 sera, founder: «ho ascoltato cambiando lo spazio e
   non ho notato differenze, anche con le cuffie»). Misurato col banco
   qui sotto: l'HRTF da solo sposta un tono di 660 Hz di ~6 dB fra i
   due orecchi, ma su un tappeto GRAVE e LARGO (le basi di Crea: pad,
   droni, natura in stereo) quasi niente — sotto i 700 Hz la testa non
   fa ombra, e un file stereo entra nel panner gia' spalmato su
   entrambi i lati. Due rimedi, entrambi deterministici (funzione dello
   stesso tempo dello strato, quindi identici nel master):
   - `mono`: lo strato che si muove entra nel panner come UN punto
     (downmix), non come due;
   - `rinforzo`: uno StereoPanner a valle dell'HRTF che segue lo stesso
     angolo (sin) con profondita' 0..1. E' il «trucco 8D» dei video,
     ma dosato e sotto l'HRTF, che mantiene davanti/dietro e quota. */

/* La Stanza della sessione: secondi di coda, tono (Hz del filtro che
   scurisce la coda) e livello del ritorno. `asciutta` = nessun nodo. */
export const STANZE = Object.freeze({
  asciutta: { label: 'asciutta', sec: 0, tone: 0, wet: 0, hint: 'Nessuna stanza: il mix com’e’.' },
  sala: { label: 'sala', sec: 1.6, tone: 3200, wet: 0.14, hint: 'Una sala di legno: poca coda, calda.' },
  tempio: { label: 'tempio', sec: 3.2, tone: 2400, wet: 0.24, hint: 'Pietra e volte: la coda si allunga.' },
  cattedrale: { label: 'cattedrale', sec: 5.5, tone: 1800, wet: 0.34, hint: 'Grande e lontana: per l’ascesa.' },
});

export const MAX_PANNER_VIVI = 6;    // oltre, equalpower: costa un decimo

export function presetPerTipo(kind) {
  return Object.entries(SPACE_PRESETS).filter(([, p]) => p.kinds.includes(kind)).map(([k]) => k);
}

export function spaceValido(kind, preset) {
  return !!preset && preset !== 'fermo' && !!SPACE_PRESETS[preset]
    && SPACE_PRESETS[preset].kinds.includes(kind);
}

export function stanzaValida(nome) {
  return !!nome && nome !== 'asciutta' && !!STANZE[nome];
}

const sm = (x) => (x <= 0 ? 0 : x >= 1 ? 1 : x * x * (3 - 2 * x));
const RAD = Math.PI / 180;

/**
 * La posizione della sorgente al secondo `u` dello strato (0 = quando
 * entra). Ascoltatore all'origine, guarda verso -Z, alto = +Y (default
 * Web Audio). Angolo 0 = davanti, cresce verso destra.
 * @returns {[x, y, z]}
 */
export function posizione(preset, u) {
  const p = SPACE_PRESETS[preset];
  if (!p || preset === 'fermo') return [0, 0, -1];
  let angle = 0, r = p.r || 1, y = 0;
  if (preset === 'respira') {
    angle = p.sway * Math.sin(2 * Math.PI * p.swayHz * u);
  } else if (preset === 'orbita_lenta' || preset === 'orbita') {
    angle = 360 * p.rate * u;
  } else if (preset === 'avvolge') {
    angle = 360 * p.rate * u;
    y = p.riseY * sm(u / p.riseSec) * (0.8 + 0.2 * Math.sin(2 * Math.PI * u / 45));
  } else if (preset === 'vicina') {
    r = p.r0 + (p.r1 - p.r0) * sm(u / p.approachSec);
  } else if (preset === 'a_lato') {
    angle = p.angle;
  }
  const a = angle * RAD;
  return [r * Math.sin(a), y, -r * Math.cos(a)];
}

/** Passo di campionamento della traiettoria: 24 punti per giro, mai
    piu' grosso di 0,5 s, mai piu' fine di 0,1 s. */
export function passoTraiettoria(preset) {
  const p = SPACE_PRESETS[preset] || {};
  const periodo = p.rate ? 1 / p.rate : p.swayHz ? 1 / p.swayHz : 6;
  return Math.max(0.1, Math.min(0.5, periodo / 24));
}

/**
 * Il panner di uno strato, con la traiettoria gia' scritta sui
 * parametri fra `tA` e `tB` (tempi del contesto) per la finestra
 * [uA, uB] dello strato. Deterministico: stessi punti dal vivo e nel
 * master. `economico` = equalpower invece di HRTF (oltre i sei vivi).
 * @returns {PannerNode}
 */
export function creaPanner(ctx, preset, { tA, uA, uB, economico = false }) {
  const pan = ctx.createPanner();
  pan.panningModel = economico ? 'equalpower' : 'HRTF';
  pan.distanceModel = 'inverse';
  pan.refDistance = 1;
  pan.rolloffFactor = 0.6;
  pan.maxDistance = 20;
  const set = (param, v, t) => {
    if (param && typeof param.setValueAtTime === 'function') {
      try { param.setValueAtTime(v, Math.max(0, t)); } catch { /* fuori dal contesto */ }
    }
  };
  const ramp = (param, v, t) => {
    if (param && typeof param.linearRampToValueAtTime === 'function') {
      try { param.linearRampToValueAtTime(v, Math.max(0, t)); } catch { /* fuori dal contesto */ }
    }
  };
  const [x0, y0, z0] = posizione(preset, uA);
  if (pan.positionX) {
    set(pan.positionX, x0, tA); set(pan.positionY, y0, tA); set(pan.positionZ, z0, tA);
    const passo = passoTraiettoria(preset);
    for (let u = uA + passo; u <= uB + 1e-6; u += passo) {
      const [x, y, z] = posizione(preset, Math.min(u, uB));
      const t = tA + (u - uA);
      ramp(pan.positionX, x, t); ramp(pan.positionY, y, t); ramp(pan.positionZ, z, t);
    }
  } else if (typeof pan.setPosition === 'function') {
    pan.setPosition(x0, y0, z0);          // browser vecchi: posizione fissa
  }
  return pan;
}

/** Il lato della sorgente al secondo `u`: -1 tutta a sinistra, +1
    tutta a destra, 0 davanti o dietro. E' il seno dell'angolo. */
export function lato(preset, u) {
  const [x, , z] = posizione(preset, u);
  const r = Math.hypot(x, z);
  return r > 1e-6 ? x / r : 0;
}

/**
 * LO SPAZIO di uno strato, completo: panner HRTF (+ downmix mono e
 * rinforzo stereo dove il preset li chiede). E' l'unica porta per i tre
 * consumatori (vivo, master, continuo): chi collega `input` e `output`
 * non deve sapere quanti nodi ci sono in mezzo.
 * @returns {{input: AudioNode, output: AudioNode, nodi: AudioNode[]}}
 */
export function creaSpazio(ctx, preset, { tA, uA, uB, economico = false }) {
  const p = SPACE_PRESETS[preset] || {};
  const pan = creaPanner(ctx, preset, { tA, uA, uB, economico });
  if (p.mono) {
    try { pan.channelCount = 1; pan.channelCountMode = 'explicit'; } catch { /* browser vecchio */ }
  }
  const nodi = [pan];
  let output = pan;
  if (p.rinforzo > 0 && typeof ctx.createStereoPanner === 'function') {
    const st = ctx.createStereoPanner();
    const a0 = lato(preset, uA) * p.rinforzo;
    try { st.pan.setValueAtTime(a0, Math.max(0, tA)); } catch { st.pan.value = a0; }
    const passo = passoTraiettoria(preset);
    for (let u = uA + passo; u <= uB + 1e-6; u += passo) {
      const v = lato(preset, Math.min(u, uB)) * p.rinforzo;
      try { st.pan.linearRampToValueAtTime(v, Math.max(0, tA + (u - uA))); } catch { /* fuori dal contesto */ }
    }
    pan.connect(st);
    output = st;
    nodi.push(st);
  }
  if (p.comp && Math.abs(p.comp - 1) > 0.01) {
    const comp = ctx.createGain();
    comp.gain.value = p.comp;
    output.connect(comp);
    output = comp;
    nodi.push(comp);
  }
  return { input: pan, output, nodi };
}

/**
 * La Stanza: un ConvolverNode con impulso sintetico (lo stesso metodo
 * della «voce da sogno»), un filtro che scurisce la coda e il ritorno.
 * @returns {{input: AudioNode, output: AudioNode, tailSec: number}}
 */
export function creaStanza(ctx, nome, makeImpulse) {
  const s = STANZE[nome];
  const input = ctx.createGain();
  if (!s || !s.sec) {
    return { input, output: input, tailSec: 0 };
  }
  const conv = ctx.createConvolver();
  conv.buffer = makeImpulse(ctx, s.sec, s.tone);
  const dark = ctx.createBiquadFilter();
  dark.type = 'lowpass'; dark.frequency.value = Math.max(1200, s.tone * 1.6);
  const wet = ctx.createGain(); wet.gain.value = s.wet;
  input.connect(conv); conv.connect(dark); dark.connect(wet);
  return { input, output: wet, tailSec: s.sec + 0.3 };
}

/** Quanto di questo strato va alla Stanza (0..1). */
export function mandata(preset) {
  const p = SPACE_PRESETS[preset];
  return p && typeof p.send === 'number' ? p.send : 0;
}

/* Banco di prova (solo in sviluppo): dalla console del browser si
   misura che un preset sposti davvero il suono fra i due orecchi —
   `window.__auryaSpazio.misura('orbita', 8)` → RMS sinistra/destra
   per mezzo secondo. E' come si e' verificato che l'HRTF lavora. */
if (typeof window !== 'undefined' && process.env.NODE_ENV === 'development') {
  window.__auryaSpazio = {
    posizione, creaPanner, creaSpazio, SPACE_PRESETS,
    /* `soloHrtf` = il panner nudo, per confrontare col rinforzo;
       `hz` basso (110) mostra perche' il rinforzo serve sui gravi */
    async misura(preset = 'orbita', secondi = 8, hz = 660, soloHrtf = false) {
      const sr = 44100;
      const off = new OfflineAudioContext(2, Math.ceil(secondi * sr), sr);
      const o = off.createOscillator(); o.type = 'sawtooth'; o.frequency.value = hz;
      const g = off.createGain(); g.gain.value = 0.3;
      o.connect(g);
      if (soloHrtf) {
        const pan = creaPanner(off, preset, { tA: 0, uA: 0, uB: secondi });
        g.connect(pan); pan.connect(off.destination);
      } else {
        const sp = creaSpazio(off, preset, { tA: 0, uA: 0, uB: secondi });
        g.connect(sp.input); sp.output.connect(off.destination);
      }
      o.start(0); o.stop(secondi);
      const b = await off.startRendering();
      const L = b.getChannelData(0), R = b.getChannelData(1), out = [];
      const win = Math.floor(sr / 2);
      for (let i = 0; i + win <= L.length; i += win) {
        let l = 0, r = 0;
        for (let k = i; k < i + win; k++) { l += L[k] * L[k]; r += R[k] * R[k]; }
        out.push({ t: (i / sr).toFixed(1), L: Math.sqrt(l / win).toFixed(3), R: Math.sqrt(r / win).toFixed(3) });
      }
      return out;
    },
  };
}
