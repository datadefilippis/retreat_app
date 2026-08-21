/**
 * Frequenze by Aurya — motore di sintesi (FQ0, 18/8/2026).
 *
 * Estratto FEDELMENTE dal prototipo del founder (aurya-frequenze.html):
 * stessa matematica delle curve, stesso grafo WebAudio dell'anteprima,
 * stessa sintesi analitica campione-per-campione del render. JS puro,
 * zero dipendenze React/DOM: lo riusano compositore (FQ0) e player
 * pubblico (FQ1).
 *
 * Il contratto dei dati e' lo "score" v1 (models/frequency_track.py):
 * { duration_sec, fade_in_sec, fade_out_sec, layers[], phases[] }.
 * Un layer neuro: { method: bin|iso|mono|bil|noise|tone, timbre, carrier,
 * f0, f1, curve: lin|exp|steps, start, end, gain, breath, mute }.
 * I layer audio (base musicale) viaggiano a parte con un AudioBuffer
 * locale: in FQ0 non si persistono (arrivano con FQ2 via audio_assets).
 */

import { buildVoiceChain, connectVoiceSources, duckEnvelope } from './voicefx';

const TAU = Math.PI * 2;
const sm = (x) => (x <= 0 ? 0 : x >= 1 ? 1 : x * x * (3 - 2 * x));

export const METHOD_LABELS = Object.freeze({
  bin: 'binaurale', iso: 'isocronico', mono: 'monoaurale',
  bil: 'bilaterale', noise: 'soffio', tone: 'tono puro',
  drone: 'bordone armonico',
});

/* ONDA 4 (21/8) — il colore del soffio. Il rosa c'era gia' (meno
   energia sugli acuti del bianco); il marrone scende ancora, il bianco
   e' il riferimento crudo. NON serve a imitare la natura — per mare,
   pioggia e vento ci sono le basi VERE in libreria (decisione founder
   21/8): qui e' il colore del veicolo su cui viaggia il RITMO. */
export const NOISE_COLORS = Object.freeze({
  pink: 'rosa', brown: 'marrone', white: 'bianco',
});
/* Pareggio dei livelli: misurati sul render, rosa 0,486 · marrone
   0,171 · bianco 0,141 di RMS. Senza questi fattori cambiare colore
   cambierebbe il VOLUME, e chi prova i tre soffi sentirebbe la
   differenza sbagliata. Il rosa resta 1: e' il riferimento storico,
   e ogni ricetta gia' salvata deve suonare identica. */
export const NOISE_GAIN = Object.freeze({ pink: 1, brown: 2.84, white: 3.45 });
export const CURVE_LABELS = Object.freeze({
  lin: 'costante', exp: 'naturale', steps: 'a gradini', wave: 'a onda',
});

/** ONDA 2 (21/8) — periodo di default della marea, in secondi: lungo
 *  abbastanza da essere un movimento e non un vibrato. */
export const WAVE_PERIOD_SEC = 40;

/** Frequenza del battito al tempo u dentro una barra lunga span.
 *
 *  ONDA 2 — la curva `wave` non e' un tragitto ma una MAREA: il
 *  battito va da f0 a f1 e TORNA, all'infinito, con periodo `period`.
 *  Le altre tre curve vanno da un valore all'altro una volta sola.
 *  Formula: f0 + (f1-f0) * (1 - cos(2π u / period)) / 2 — parte da f0,
 *  tocca f1 a meta' periodo, e' derivabile ovunque (nessuno scatto).
 *  E' l'unico posto dove questa forma vive: render analitico e
 *  anteprima WebAudio la leggono entrambi da qui. */
export function freqAt(l, u, span) {
  if (l.f0 === l.f1) return l.f0;
  if (l.curve === 'wave') {
    const T = Math.max(2, l.period || WAVE_PERIOD_SEC);
    return l.f0 + (l.f1 - l.f0) * (1 - Math.cos((TAU * u) / T)) / 2;
  }
  const x = Math.min(1, Math.max(0, u / span));
  if (l.curve === 'exp' && l.f0 > 0 && l.f1 > 0) {
    return l.f0 * Math.pow(l.f1 / l.f0, x);
  }
  if (l.curve === 'steps') {
    const lv = [l.f0, l.f0 + (l.f1 - l.f0) / 3, l.f0 + 2 * (l.f1 - l.f0) / 3, l.f1];
    const seg = span / 4, k = Math.min(3, Math.floor(u / seg));
    if (k === 0) return lv[0];
    const local = u - k * seg, r = seg * 0.25;
    return local < r ? lv[k - 1] + (lv[k] - lv[k - 1]) * (local / r) : lv[k];
  }
  return l.f0 + (l.f1 - l.f0) * x;
}

/** Inviluppo del livello (attack/release + respiro) al tempo assoluto. */
export function envAt(l, u, span, tAbs) {
  if (u < 0 || u > span) return 0;
  const a = Math.min(12, span * 0.3), r = Math.min(16, span * 0.3);
  let e = 1;
  if (u < a) e *= sm(u / a);
  if (span - u < r) e *= sm((span - u) / r);
  if (l.breath !== false) e *= 1 + 0.08 * Math.sin((TAU * tAbs) / 26 + (l.id || 0));
  return e * l.gain;
}

const warm = (th) =>
  (Math.sin(th) + 0.28 * Math.sin(2 * th + 0.3) + 0.12 * Math.sin(3 * th)) / 1.4;
const voice = (l, th) => (l.timbre === 'warm' ? warm(th) : Math.sin(th));

/* ── sintesi analitica campione-per-campione (render esatto) ─────────────
   Fase accumulata → continuita' garantita, zero clic sulle transizioni. */
export function neuroSampleInit(l) {
  l._ph = 0; l._pk = { b0: 0, b1: 0, b2: 0 }; l._br = 0;
}

/* Il bordone: fondamentale + quinta e terza in intonazione NATURALE
   (3/2 e 5/4, i rapporti semplici che non battono tra loro). Il tono
   puro dava fondamentale + 2ª e 3ª armonica: una nota sola, piu'
   calda. Questo e' un accordo — la differenza tra un diapason e un
   armonium. */
const DRONE_PARTS = [[1, 1], [1.5, 0.55], [1.25, 0.4]];
const DRONE_NORM = DRONE_PARTS.reduce((a, [, w]) => a + w, 0);
export function neuroSample(l, tAbs, dt) {
  const span = Math.max(1, l.end - l.start), u = tAbs - l.start;
  if (u < 0 || u > span) return [0, 0];
  const e = envAt(l, u, span, tAbs);
  if (e <= 0) return [0, 0];
  if (l.method === 'tone') {
    const v = voice(l, TAU * l.carrier * tAbs) * e;
    return [v, v];
  }
  if (l.method === 'drone') {
    const th = TAU * l.carrier * tAbs;
    let v = 0;
    DRONE_PARTS.forEach(([mu, w]) => { v += w * voice(l, th * mu); });
    v = (v / DRONE_NORM) * e;
    return [v, v];
  }
  const f = freqAt(l, u, span);
  l._ph += TAU * f * dt;
  const pb = l._ph, cp = TAU * l.carrier * tAbs;
  if (l.method === 'bin') return [voice(l, cp) * e, voice(l, cp + pb) * e];
  if (l.method === 'mono') {
    const v = (voice(l, cp) + voice(l, cp + pb)) * 0.5 * e;
    return [v, v];
  }
  if (l.method === 'iso') {
    const gate = Math.pow(Math.max(0, Math.sin(pb)), 0.8);
    const v = voice(l, cp) * gate * e;
    return [v, v];
  }
  if (l.method === 'bil') {
    const p = Math.sin(pb);
    const gl = Math.sqrt((1 - p) / 2), gr = Math.sqrt((1 + p) / 2);
    const v = voice(l, cp) * e;
    return [v * gl, v * gr];
  }
  if (l.method === 'noise') {
    const w = Math.random() * 2 - 1, k = l._pk;
    let n;
    if (l.color === 'white') n = w * 0.25 * NOISE_GAIN.white;
    else if (l.color === 'brown') {
      // integratore con perdita: -6 dB/ottava, piu' cupo del rosa
      l._br = (l._br + 0.02 * w) / 1.02;
      n = l._br * 3.0 * NOISE_GAIN.brown;
    } else {
      k.b0 = 0.99765 * k.b0 + w * 0.099046;
      k.b1 = 0.963 * k.b1 + w * 0.2965164;
      k.b2 = 0.57 * k.b2 + w * 1.0526913;
      n = (k.b0 + k.b1 + k.b2 + w * 0.1848) * 0.25;
    }
    const gate = (1 + Math.sin(pb)) / 2;
    const v = n * gate * e * 1.6;
    return [v, v];
  }
  return [0, 0];
}

/* ── anteprima: grafo WebAudio ──────────────────────────────────────────── */

const noiseBufCache = {};
/** Buffer di rumore per colore. La matematica e' la stessa di
 *  neuroSample: se qui e li' divergessero, anteprima ed export
 *  suonerebbero due soffi diversi. */
export function pinkBuf(actx, color = 'pink') {
  const key = `${color}:${actx.sampleRate}`;
  if (noiseBufCache[key]) return noiseBufCache[key];
  const n = actx.sampleRate * 4, b = actx.createBuffer(2, n, actx.sampleRate);
  for (let c = 0; c < 2; c++) {
    const d = b.getChannelData(c);
    let b0 = 0, b1 = 0, b2 = 0, br = 0;
    for (let i = 0; i < n; i++) {
      const w = Math.random() * 2 - 1;
      if (color === 'white') d[i] = w * 0.25 * NOISE_GAIN.white;
      else if (color === 'brown') { br = (br + 0.02 * w) / 1.02; d[i] = br * 3.0 * NOISE_GAIN.brown; }
      else {
        b0 = 0.99765 * b0 + w * 0.099046;
        b1 = 0.963 * b1 + w * 0.2965164;
        b2 = 0.57 * b2 + w * 1.0526913;
        d[i] = (b0 + b1 + b2 + w * 0.1848) * 0.25;
      }
    }
  }
  noiseBufCache[key] = b;
  return b;
}

/** Durata del tragitto di una scheda (f0 → f1), in secondi. Lungo
 *  abbastanza da non sembrare un effetto: e' una discesa, non uno swoosh. */
export const CARD_SWEEP_SEC = 180;

/**
 * Ascolto live di una SINGOLA frequenza (le schede di Esplora): parte
 * subito, resta accesa finche' non la fermi, si combina con le altre.
 *
 * ONDA 1 (21/8/2026, founder) — la scheda percorre il TRAGITTO che ha
 * scritto nei dati. Prima qui arrivava un solo numero (`f0`) e restava
 * fisso: la scheda Delta dichiarava «da 4 a 2,5 Hz» e suonava 4 Hz per
 * sempre. Curva e respiro esistevano nel motore ma vivevano solo dentro
 * una sessione composta. Ora la scheda scende (o sale) con la sua curva
 * in CARD_SWEEP_SEC secondi e poi TIENE il valore d'arrivo — un ascolto
 * di scheda non ha una fine, quindi non puo' avere un ritorno.
 * Il tragitto si annulla appena l'utente tocca il battito: da quel
 * momento comanda lui.
 *
 * @param ctx   AudioContext attivo
 * @param cfg   { method, carrier, timbre, f0, f1, curve } della scheda
 * @param gain  volume iniziale 0..1
 * @param fval  battito iniziale in Hz (o frequenza del tono se method=tone)
 * @returns {{setGain, setBeat, setCarrier, stop, sweepTo}}
 */
export function startCardLive(ctx, cfg, gain, fval) {
  const method = cfg.method || 'bin';
  const timbre = cfg.timbre || 'warm';
  const carrier = method === 'tone' ? fval : (cfg.carrier ?? (method === 'bin' ? 400 : 180));
  let beat = method === 'tone' ? 0 : fval;
  // il tragitto: solo se la scheda ne dichiara uno e non e' un tono puro
  const sweepTo = (method !== 'tone' && cfg.f1 != null && cfg.f1 !== beat)
    ? cfg.f1 : null;
  const curve = cfg.curve || 'lin';
  const t0 = ctx.currentTime;
  const beatAt = (u) => freqAt(
    { f0: beat, f1: sweepTo, curve, period: cfg.period }, u, CARD_SWEEP_SEC);
  const nodesBreath = [];
  // Il respiro vive su un nodo IN SERIE, non sommato al volume: un
  // LFO agganciato a g.gain aggiungerebbe ±0,08 in assoluto (cioe'
  // ±32% su un volume di 0,25), mentre envAt lo definisce ±8%
  // RELATIVO. Qui out oscilla intorno a 1 e moltiplica: la proporzione
  // resta giusta a qualunque volume, anche dopo setGain.
  const out = ctx.createGain();
  out.gain.value = 1;
  out.connect(ctx.destination);
  const g = ctx.createGain();
  g.gain.setValueAtTime(0.0001, t0);
  g.gain.linearRampToValueAtTime(Math.max(0.0001, gain), t0 + 1.5);
  g.connect(out);
  if (cfg.breath !== false) {
    const bl = ctx.createOscillator(), ba = ctx.createGain();
    bl.frequency.value = 1 / 26;   // stesso periodo di envAt
    ba.gain.value = 0.08;          // stessa ampiezza di envAt
    bl.connect(ba); ba.connect(out.gain); bl.start();
    nodesBreath.push(bl);
  }
  const nodes = [];
  const mkV = (f, dest) => {
    const parts = timbre === 'warm'
      ? [[1, 1 / 1.4], [2, 0.28 / 1.4], [3, 0.12 / 1.4]] : [[1, 1]];
    const vs = [];
    parts.forEach(([mu, w]) => {
      const o = ctx.createOscillator(), og = ctx.createGain();
      og.gain.value = w;
      o.frequency.value = Math.max(1, f * mu);
      o.connect(og); og.connect(dest); o.start();
      nodes.push(o); vs.push([o, mu]);
    });
    return {
      set(f2) {
        vs.forEach(([o, mu]) =>
          o.frequency.setTargetAtTime(Math.max(1, f2 * mu), ctx.currentTime, 0.05));
      },
      // ogni parziale segue il tragitto sul suo multiplo
      sweep(draw, fn) {
        vs.forEach(([o, mu]) => draw(o.frequency, (u) => Math.max(1, fn(u) * mu)));
      },
      // idem per la marea: valore centrale e ampiezza scalano insieme
      tide(modula, center) {
        vs.forEach(([o, mu]) => { o.frequency.value = Math.max(1, center * mu); modula(o.frequency, mu); });
      },
    };
  };
  let vL = null, vR = null, lfo = null, curCarrier = carrier;
  if (method === 'tone') vL = mkV(carrier, g);
  else if (method === 'drone') {
    // stessi rapporti di DRONE_PARTS: quinta e terza naturali
    DRONE_PARTS.forEach(([mu, w]) => {
      const h = ctx.createGain(); h.gain.value = w / DRONE_NORM; h.connect(g);
      const v = mkV(carrier * mu, h);
      if (mu === 1) vL = v;
    });
  }
  else if (method === 'bin') {
    const mg = ctx.createChannelMerger(2), gl = ctx.createGain(), gr = ctx.createGain();
    gl.connect(mg, 0, 0); gr.connect(mg, 0, 1); mg.connect(g);
    vL = mkV(carrier, gl); vR = mkV(carrier + beat, gr);
  } else if (method === 'mono') {
    const h = ctx.createGain(); h.gain.value = 0.5; h.connect(g);
    vL = mkV(carrier, h); vR = mkV(carrier + beat, h);
  } else if (method === 'iso') {
    const gate = ctx.createGain(); gate.gain.value = 0.5; gate.connect(g);
    lfo = ctx.createOscillator();
    const la = ctx.createGain(); la.gain.value = 0.5;
    lfo.frequency.value = Math.max(0.05, beat);
    lfo.connect(la); la.connect(gate.gain); lfo.start();
    nodes.push(lfo);
    vL = mkV(carrier, gate);
  } else if (method === 'bil') {
    let dst = g;
    if (ctx.createStereoPanner) {
      const pan = ctx.createStereoPanner(); pan.connect(g);
      lfo = ctx.createOscillator();
      lfo.frequency.value = Math.max(0.05, beat);
      lfo.connect(pan.pan); lfo.start();
      nodes.push(lfo); dst = pan;
    }
    vL = mkV(carrier, dst);
  } else if (method === 'noise') {
    const src = ctx.createBufferSource();
    src.buffer = pinkBuf(ctx, cfg.color); src.loop = true;
    const gate = ctx.createGain(); gate.gain.value = 0.5;
    lfo = ctx.createOscillator();
    const la = ctx.createGain(); la.gain.value = 0.5;
    lfo.frequency.value = Math.max(0.05, beat);
    lfo.connect(la); la.connect(gate.gain);
    src.connect(gate); gate.connect(g);
    src.start(); lfo.start();
    nodes.push(src, lfo);
  }
  /* Il tragitto: si disegna UNA volta sui parametri che portano il
     battito — l'oscillatore destro (binaurale/monoaurale) e l'LFO
     (isocronico, bilaterale, soffio). Campionato come rampCurve, con la
     curva dichiarata dalla scheda; all'arrivo il valore resta. */
  const sweepParams = [];
  /* ONDA 2 — la MAREA in una scheda e' infinita, quindi non si puo'
     disegnare: si GENERA. Un oscillatore a 1/periodo Hz, con forma
     -cos (periodic wave: real=[0,-1]), sommato al valore centrale
     riproduce ESATTAMENTE la formula di freqAt —
       f0 + (f1-f0)(1-cos(2πu/T))/2  =  mid - amp·cos(2πu/T)
     — per sempre e con due nodi, invece che con migliaia di rampe
     schedulate. La stessa marea che il render calcola punto per punto. */
  const isMarea = curve === 'wave' && sweepTo != null;
  if (isMarea) {
    const T = Math.max(2, cfg.period || WAVE_PERIOD_SEC);
    const mid = (beat + sweepTo) / 2, amp = (sweepTo - beat) / 2;
    const pw = ctx.createPeriodicWave(
      new Float32Array([0, -1]), new Float32Array([0, 0]));
    const modula = (param, mu = 1) => {
      const osc = ctx.createOscillator(), amt = ctx.createGain();
      osc.setPeriodicWave(pw);
      osc.frequency.value = 1 / T;
      amt.gain.value = amp * mu;
      osc.connect(amt); amt.connect(param);
      osc.start();
      nodes.push(osc);
      sweepParams.push(param);
    };
    if (lfo) { lfo.frequency.value = Math.max(0.05, mid); modula(lfo.frequency); }
    if (vR) vR.tide(modula, carrier + mid);
  } else if (sweepTo != null) {
    const steps = 240;
    const draw = (param, fn) => {
      param.cancelScheduledValues(t0);
      param.setValueAtTime(fn(0), t0);
      for (let i = 1; i <= steps; i++) {
        const u = (i / steps) * CARD_SWEEP_SEC;
        param.linearRampToValueAtTime(fn(u), t0 + u);
      }
      sweepParams.push(param);
    };
    if (lfo) draw(lfo.frequency, (u) => Math.max(0.05, beatAt(u)));
    if (vR) vR.sweep(draw, (u) => carrier + beatAt(u));
  }
  const fermaIlTragitto = () => {
    sweepParams.forEach((param) => {
      const v = param.value;
      param.cancelScheduledValues(ctx.currentTime);
      param.setValueAtTime(v, ctx.currentTime);
    });
    sweepParams.length = 0;
  };

  return {
    method, carrier, beat, gain,
    // che movimento sta facendo: la scheda lo racconta mentre suona
    sweepTo, marea: isMarea,
    sweepSec: sweepTo != null ? CARD_SWEEP_SEC : 0,
    periodo: isMarea ? Math.max(2, cfg.period || WAVE_PERIOD_SEC) : 0,
    da: beat,
    beatNow() {
      if (sweepTo == null) return beat;
      const u = ctx.currentTime - t0;
      // la marea non si ferma all'arrivo: continua a girare
      return isMarea ? beatAt(u) : beatAt(Math.min(CARD_SWEEP_SEC, u));
    },
    setGain(v) {
      g.gain.setTargetAtTime(Math.max(0.0001, v), ctx.currentTime, 0.08);
      this.gain = v;
    },
    setCarrier(v) {
      curCarrier = v; this.carrier = v;
      vL && vL.set(v); vR && vR.set(v + beat);
    },
    setBeat(v) {
      // da qui comanda l'utente: il tragitto si ferma dov'e' arrivato
      fermaIlTragitto();
      beat = v; this.beat = v; this.sweepTo = null;
      if (lfo) lfo.frequency.setTargetAtTime(Math.max(0.05, v), ctx.currentTime, 0.05);
      vR && vR.set(curCarrier + v);
    },
    stop() {
      g.gain.setTargetAtTime(0.0001, ctx.currentTime, 0.25);
      setTimeout(() => {
        nodes.concat(nodesBreath).forEach((n) => {
          try { n.stop(); } catch (e) { /* gia' fermo */ }
        });
        try { g.disconnect(); } catch (e) { /* idem */ }
        try { out.disconnect(); } catch (e) { /* idem */ }
      }, 900);
    },
  };
}

/* Disegna una curva su un AudioParam campionandola a passi.
 *
 * `now` e' il presente del contesto: al seek in avanti un livello puo'
 * essere gia' cominciato, e la sua curva parte a un istante passato —
 * che al limite e' NEGATIVO (t0 = adesso - punto di seek), e Web Audio
 * rifiuta i tempi negativi. Qui la curva riprende dal punto in cui si
 * trova adesso e schedula solo il futuro: nessun tempo illegale, e il
 * livello riparte al valore giusto invece che dall'inizio. */
const rampCurve = (param, t0, span, fn, steps = 160, now = 0) => {
  const from = Math.max(t0, now);
  param.setValueAtTime(fn(Math.max(0, from - t0)), from);
  for (let i = 1; i <= steps; i++) {
    const u = (i / steps) * span;
    if (t0 + u > from) param.linearRampToValueAtTime(fn(u), t0 + u);
  }
};

/**
 * Avvia l'anteprima di uno score dentro un AudioContext.
 *
 * @param ctx      AudioContext gia' creato (e resumed) dal chiamante
 * @param score    score v1 (duration_sec, fade_*, layers neuro)
 * @param opts     { fromT, audioLayers, voiceLayers, voiceDuck } —
 *                 audioLayers: basi con buffer; voiceLayers: spezzoni
 *                 voce con buffer DRY + fx (resolveVoiceLayers, la
 *                 catena effetti si costruisce qui); voiceDuck: le basi
 *                 respirano piano sotto la voce
 * @returns {{stop: fn, elapsed: fn, setLayerGain: fn(id, gain)}}
 */
export function startPreview(ctx, score,
  { fromT = 0, audioLayers = [], voiceLayers = [], voiceDuck = false } = {}) {
  const d = score.duration_sec;
  const off = Math.max(0, Math.min(fromT || 0, d - 1));
  const t0 = ctx.currentTime + 0.15 - off;
  const nodes = [], liveG = {};
  const sess = ctx.createGain();
  sess.connect(ctx.destination);
  const fi = score.fade_in_sec || 0, fo = score.fade_out_sec || 0;
  const now = ctx.currentTime;
  const startAt = now + 0.15;
  // Col seek in avanti t0 finisce nel passato (anche sotto zero): ogni
  // istante assoluto va ancorato ad `at`, o Web Audio solleva
  // «Time must be a finite non-negative number» e l'ascolto muore.
  const at = (t) => Math.max(now, t);
  sess.gain.setValueAtTime(off < fi && fi > 0 ? Math.max(0.0001, off / fi) : 1, startAt);
  if (fi > 0 && off < fi) sess.gain.linearRampToValueAtTime(1, at(t0 + fi));
  if (fo > 0) {
    sess.gain.setValueAtTime(1, at(t0 + d - fo));
    sess.gain.linearRampToValueAtTime(0.0001, at(t0 + d));
  }

  // FV2 — ducking: dove parla la voce, le basi respirano piano.
  // Deterministico (le finestre sono nello score): identico ovunque.
  let duckBus = sess;
  if (voiceDuck && voiceLayers.length) {
    const duck = ctx.createGain(); duck.connect(sess);
    const env = duckEnvelope(voiceLayers);
    rampCurve(duck.gain, t0, d, (u) => env(u), Math.min(600, Math.ceil(d * 2)), now);
    duckBus = duck;
  }

  audioLayers.filter((l) => !l.mute && l.gain > 0 && l.buffer).forEach((l) => {
    const span = Math.max(1, Math.min(l.end, d) - l.start), s0 = t0 + l.start;
    if (s0 + span <= ctx.currentTime) return;
    const uG = ctx.createGain(); uG.gain.value = 1; uG.connect(duckBus);
    liveG[l.id] = { node: uG, base: l.gain };
    const src = ctx.createBufferSource();
    src.buffer = l.buffer; src.loop = l.loop;
    const g = ctx.createGain(); src.connect(g); g.connect(uG);
    const a = Math.min(6, span * 0.2), r = Math.min(8, span * 0.25);
    g.gain.setValueAtTime(0.0001, at(s0));
    g.gain.linearRampToValueAtTime(l.gain, at(s0 + a));
    g.gain.setValueAtTime(l.gain, at(s0 + span - r));
    g.gain.linearRampToValueAtTime(0.0001, at(s0 + span));
    const startOffset = off > l.start ? off - l.start : 0;
    const when = at(s0);
    src.start(when, l.loop ? startOffset % l.buffer.duration
                           : Math.min(startOffset, l.buffer.duration - 0.001));
    src.stop(at(s0 + span));
    nodes.push(src);
  });

  // FV2 — spezzoni voce: clip DRY → catena effetti del preset → sessione.
  // La sorgente si ferma a fine clip ma la coda (riverbero/eco) continua
  // a decadere attraverso la catena: e' il comportamento giusto.
  voiceLayers.filter((l) => !l.mute && l.gain > 0 && l.buffer).forEach((l) => {
    const span = Math.max(0.5, Math.min(l.end, d) - l.start);
    const s0 = t0 + l.start;
    const clipIn = Math.min(l.clip_in || 0, Math.max(0, l.buffer.duration - 0.2));
    const playLen = Math.min(span, l.buffer.duration - clipIn);
    if (playLen <= 0 || s0 + playLen <= ctx.currentTime) return;
    const chain = buildVoiceChain(ctx, l.fx, l.fx_amount);
    const uG = ctx.createGain(); uG.gain.value = 1; uG.connect(sess);
    liveG[l.id] = { node: uG, base: l.gain };
    const vg = ctx.createGain(); vg.connect(uG); vg.gain.value = l.gain;
    chain.output.connect(vg);
    // declick corto sul segnale DRY in ingresso: la coda non si tronca
    const dk = 0.12;
    chain.input.gain.setValueAtTime(0.0001, at(s0));
    chain.input.gain.linearRampToValueAtTime(1, at(s0 + dk));
    chain.input.gain.setValueAtTime(1, at(s0 + playLen - dk));
    chain.input.gain.linearRampToValueAtTime(0.0001, at(s0 + playLen));
    const startOffset = clipIn + (off > l.start ? off - l.start : 0);
    if (startOffset >= l.buffer.duration) return;
    connectVoiceSources(ctx, l.buffer, chain).forEach((src) => {
      src.start(at(s0), Math.min(startOffset, l.buffer.duration - 0.001));
      src.stop(at(s0 + playLen));
      nodes.push(src);
    });
  });

  (score.layers || []).filter((l) => (l.kind || 'neuro') === 'neuro' && !l.mute && l.gain > 0).forEach((l) => {
    const span = Math.max(1, Math.min(l.end, d) - l.start), s0 = t0 + l.start;
    if (s0 + span <= ctx.currentTime) return;
    const uG = ctx.createGain(); uG.gain.value = 1; uG.connect(sess);
    liveG[l.id] = { node: uG, base: l.gain };
    const g = ctx.createGain(); g.connect(uG);
    rampCurve(g.gain, s0, span,
      (u) => Math.max(0.0001, envAt(l, u, span, l.start + u)), 200, now);
    const mkVoice = (fFn, dest) => {
      const parts = l.timbre === 'warm'
        ? [[1, 1 / 1.4], [2, 0.28 / 1.4], [3, 0.12 / 1.4]] : [[1, 1]];
      parts.forEach(([m, w]) => {
        const o = ctx.createOscillator(), og = ctx.createGain();
        og.gain.value = w;
        rampCurve(o.frequency, s0, span, (u) => Math.max(1, fFn(u) * m), passi, now);
        o.connect(og); og.connect(dest);
        o.start(at(s0)); o.stop(at(s0 + span));
        nodes.push(o);
      });
    };
    const beat = (u) => freqAt(l, u, span);
    /* ONDA 2 — quanti campioni servono per disegnare questa curva.
       Le curve monotone si accontentano di 120 punti su tutta la
       barra; una MAREA no: con periodo 40 s su un livello di 20
       minuti, 120 punti sono un campione ogni 10 s e la curva
       ricostruita e' un'altra onda (aliasing puro). Qui si chiedono
       ~24 campioni per periodo, con un tetto perche' ogni punto e' un
       evento schedulato. */
    const passi = l.curve === 'wave'
      ? Math.min(3000, Math.max(120, Math.ceil((span / Math.max(2, l.period || WAVE_PERIOD_SEC)) * 24)))
      : 120;
    if (l.method === 'tone') mkVoice(() => l.carrier, g);
    else if (l.method === 'drone') {
      DRONE_PARTS.forEach(([mu, w]) => {
        const h = ctx.createGain(); h.gain.value = w / DRONE_NORM; h.connect(g);
        mkVoice(() => l.carrier * mu, h);
      });
    }
    else if (l.method === 'bin') {
      const m = ctx.createChannelMerger(2), gl = ctx.createGain(), gr = ctx.createGain();
      gl.connect(m, 0, 0); gr.connect(m, 0, 1); m.connect(g);
      mkVoice(() => l.carrier, gl); mkVoice((u) => l.carrier + beat(u), gr);
    } else if (l.method === 'mono') {
      const half = ctx.createGain(); half.gain.value = 0.5; half.connect(g);
      mkVoice(() => l.carrier, half); mkVoice((u) => l.carrier + beat(u), half);
    } else if (l.method === 'iso') {
      const gate = ctx.createGain(); gate.gain.value = 0.5; gate.connect(g);
      const lfo = ctx.createOscillator(), la = ctx.createGain(); la.gain.value = 0.5;
      rampCurve(lfo.frequency, s0, span, (u) => beat(u), passi, now);
      lfo.connect(la); la.connect(gate.gain);
      lfo.start(at(s0)); lfo.stop(at(s0 + span));
      nodes.push(lfo);
      mkVoice(() => l.carrier, gate);
    } else if (l.method === 'bil') {
      const pan = ctx.createStereoPanner ? ctx.createStereoPanner() : null;
      const dst = pan || g;
      if (pan) {
        pan.connect(g);
        const lfo = ctx.createOscillator(), la = ctx.createGain(); la.gain.value = 1;
        rampCurve(lfo.frequency, s0, span, (u) => beat(u), passi, now);
        lfo.connect(la); la.connect(pan.pan);
        lfo.start(at(s0)); lfo.stop(at(s0 + span));
        nodes.push(lfo);
      }
      mkVoice(() => l.carrier, dst);
    } else if (l.method === 'noise') {
      const src = ctx.createBufferSource();
      src.buffer = pinkBuf(ctx, l.color); src.loop = true;
      const gate = ctx.createGain(); gate.gain.value = 0.8;
      const lfo = ctx.createOscillator(), la = ctx.createGain(); la.gain.value = 0.8;
      rampCurve(lfo.frequency, s0, span, (u) => beat(u), passi, now);
      lfo.connect(la); la.connect(gate.gain);
      src.connect(gate); gate.connect(g);
      src.start(at(s0)); src.stop(at(s0 + span));
      lfo.start(at(s0)); lfo.stop(at(s0 + span));
      nodes.push(src, lfo);
    }
  });

  return {
    elapsed: () => ctx.currentTime - t0,
    setLayerGain(id, gain) {
      const h = liveG[id];
      if (h) h.node.gain.setTargetAtTime(
        Math.max(0.0001, gain / (h.base || 1)), ctx.currentTime, 0.06);
    },
    stop() {
      nodes.forEach((n) => { try { n.stop(); } catch (e) { /* gia' fermo */ } });
      try { sess.gain.setTargetAtTime(0.0001, ctx.currentTime, 0.15); } catch (e) { /* ctx chiuso */ }
      setTimeout(() => { try { sess.disconnect(); } catch (e) { /* idem */ } }, 600);
    },
  };
}
