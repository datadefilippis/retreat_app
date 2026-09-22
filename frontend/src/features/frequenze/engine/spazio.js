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
  fermo: { label: 'fermo', kinds: ['audio', 'voice'], hint: 'Davanti, al centro. Com’e’ sempre stato.' },
  respira: { label: 'respira', kinds: ['audio', 'voice'], r: 1.5, sway: 20, swayHz: 0.06, send: 0.15,
    hint: 'Oscilla piano a destra e a sinistra, come un respiro.' },
  orbita_lenta: { label: 'orbita lenta', kinds: ['audio', 'voice'], r: 1.6, rate: 1 / 24, send: 0.2,
    hint: 'Un giro intorno alla testa ogni 24 secondi.' },
  orbita: { label: 'orbita', kinds: ['audio'], r: 1.8, rate: 1 / 8, send: 0.2,
    hint: 'Un giro ogni 8 secondi: per la danza, non per dormire.' },
  avvolge: { label: 'avvolge', kinds: ['audio'], r: 2.4, rate: 1 / 20, riseY: 1.2, riseSec: 60, send: 0.45,
    hint: 'Largo, sale sopra la testa e riempie la stanza.' },
  vicina: { label: 'vicina', kinds: ['voice'], r0: 2.2, r1: 0.6, approachSec: 6, send: 0,
    hint: 'Parte lontana e in sei secondi arriva vicino: presenza.' },
  a_lato: { label: 'a lato', kinds: ['voice'], r: 1.0, angle: 30, send: 0,
    hint: 'Fissa a 30 gradi sulla destra: per una seconda voce.' },
});

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
