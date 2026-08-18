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

const TAU = Math.PI * 2;
const sm = (x) => (x <= 0 ? 0 : x >= 1 ? 1 : x * x * (3 - 2 * x));

export const METHOD_LABELS = Object.freeze({
  bin: 'binaurale', iso: 'isocronico', mono: 'monoaurale',
  bil: 'bilaterale', noise: 'soffio', tone: 'tono puro',
});
export const CURVE_LABELS = Object.freeze({
  lin: 'costante', exp: 'naturale', steps: 'a gradini',
});

/** Frequenza del battito al tempo u dentro una barra lunga span. */
export function freqAt(l, u, span) {
  if (l.f0 === l.f1) return l.f0;
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
  l._ph = 0; l._pk = { b0: 0, b1: 0, b2: 0 };
}
export function neuroSample(l, tAbs, dt) {
  const span = Math.max(1, l.end - l.start), u = tAbs - l.start;
  if (u < 0 || u > span) return [0, 0];
  const e = envAt(l, u, span, tAbs);
  if (e <= 0) return [0, 0];
  if (l.method === 'tone') {
    const v = voice(l, TAU * l.carrier * tAbs) * e;
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
    k.b0 = 0.99765 * k.b0 + w * 0.099046;
    k.b1 = 0.963 * k.b1 + w * 0.2965164;
    k.b2 = 0.57 * k.b2 + w * 1.0526913;
    const pink = (k.b0 + k.b1 + k.b2 + w * 0.1848) * 0.25;
    const gate = (1 + Math.sin(pb)) / 2;
    const v = pink * gate * e * 1.6;
    return [v, v];
  }
  return [0, 0];
}

/* ── anteprima: grafo WebAudio ──────────────────────────────────────────── */

let pinkBufCache = null;
export function pinkBuf(actx) {
  if (pinkBufCache && pinkBufCache.sampleRate === actx.sampleRate) return pinkBufCache;
  const n = actx.sampleRate * 4, b = actx.createBuffer(2, n, actx.sampleRate);
  for (let c = 0; c < 2; c++) {
    const d = b.getChannelData(c);
    let b0 = 0, b1 = 0, b2 = 0;
    for (let i = 0; i < n; i++) {
      const w = Math.random() * 2 - 1;
      b0 = 0.99765 * b0 + w * 0.099046;
      b1 = 0.963 * b1 + w * 0.2965164;
      b2 = 0.57 * b2 + w * 1.0526913;
      d[i] = (b0 + b1 + b2 + w * 0.1848) * 0.25;
    }
  }
  pinkBufCache = b;
  return b;
}

const rampCurve = (param, t0, span, fn, steps = 160) => {
  param.setValueAtTime(fn(0), t0);
  for (let i = 1; i <= steps; i++) {
    const u = (i / steps) * span;
    param.linearRampToValueAtTime(fn(u), t0 + u);
  }
};

/**
 * Avvia l'anteprima di uno score dentro un AudioContext.
 *
 * @param ctx      AudioContext gia' creato (e resumed) dal chiamante
 * @param score    score v1 (duration_sec, fade_*, layers neuro)
 * @param opts     { fromT, audioLayers } — audioLayers: [{buffer, start,
 *                 end, gain, loop, mute}] basi musicali locali (FQ0)
 * @returns {{stop: fn, elapsed: fn, setLayerGain: fn(id, gain)}}
 */
export function startPreview(ctx, score, { fromT = 0, audioLayers = [] } = {}) {
  const d = score.duration_sec;
  const off = Math.max(0, Math.min(fromT || 0, d - 1));
  const t0 = ctx.currentTime + 0.15 - off;
  const nodes = [], liveG = {};
  const sess = ctx.createGain();
  sess.connect(ctx.destination);
  const fi = score.fade_in_sec || 0, fo = score.fade_out_sec || 0;
  const startAt = ctx.currentTime + 0.15;
  sess.gain.setValueAtTime(off < fi && fi > 0 ? Math.max(0.0001, off / fi) : 1, startAt);
  if (fi > 0 && off < fi) sess.gain.linearRampToValueAtTime(1, t0 + fi);
  if (fo > 0) {
    sess.gain.setValueAtTime(1, t0 + d - fo);
    sess.gain.linearRampToValueAtTime(0.0001, t0 + d);
  }

  audioLayers.filter((l) => !l.mute && l.gain > 0 && l.buffer).forEach((l) => {
    const span = Math.max(1, Math.min(l.end, d) - l.start), s0 = t0 + l.start;
    if (s0 + span <= ctx.currentTime) return;
    const uG = ctx.createGain(); uG.gain.value = 1; uG.connect(sess);
    liveG[l.id] = { node: uG, base: l.gain };
    const src = ctx.createBufferSource();
    src.buffer = l.buffer; src.loop = l.loop;
    const g = ctx.createGain(); src.connect(g); g.connect(uG);
    const a = Math.min(6, span * 0.2), r = Math.min(8, span * 0.25);
    g.gain.setValueAtTime(0.0001, s0);
    g.gain.linearRampToValueAtTime(l.gain, s0 + a);
    g.gain.setValueAtTime(l.gain, s0 + span - r);
    g.gain.linearRampToValueAtTime(0.0001, s0 + span);
    const startOffset = off > l.start ? off - l.start : 0;
    const when = Math.max(ctx.currentTime, s0);
    src.start(when, l.loop ? startOffset % l.buffer.duration
                           : Math.min(startOffset, l.buffer.duration - 0.001));
    src.stop(s0 + span);
    nodes.push(src);
  });

  (score.layers || []).filter((l) => !l.mute && l.gain > 0).forEach((l) => {
    const span = Math.max(1, Math.min(l.end, d) - l.start), s0 = t0 + l.start;
    if (s0 + span <= ctx.currentTime) return;
    const uG = ctx.createGain(); uG.gain.value = 1; uG.connect(sess);
    liveG[l.id] = { node: uG, base: l.gain };
    const g = ctx.createGain(); g.connect(uG);
    rampCurve(g.gain, s0, span,
      (u) => Math.max(0.0001, envAt(l, u, span, l.start + u)), 200);
    const mkVoice = (fFn, dest) => {
      const parts = l.timbre === 'warm'
        ? [[1, 1 / 1.4], [2, 0.28 / 1.4], [3, 0.12 / 1.4]] : [[1, 1]];
      parts.forEach(([m, w]) => {
        const o = ctx.createOscillator(), og = ctx.createGain();
        og.gain.value = w;
        rampCurve(o.frequency, s0, span, (u) => Math.max(1, fFn(u) * m), 120);
        o.connect(og); og.connect(dest);
        o.start(Math.max(ctx.currentTime, s0)); o.stop(s0 + span);
        nodes.push(o);
      });
    };
    const beat = (u) => freqAt(l, u, span);
    if (l.method === 'tone') mkVoice(() => l.carrier, g);
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
      rampCurve(lfo.frequency, s0, span, (u) => beat(u), 120);
      lfo.connect(la); la.connect(gate.gain);
      lfo.start(Math.max(ctx.currentTime, s0)); lfo.stop(s0 + span);
      nodes.push(lfo);
      mkVoice(() => l.carrier, gate);
    } else if (l.method === 'bil') {
      const pan = ctx.createStereoPanner ? ctx.createStereoPanner() : null;
      const dst = pan || g;
      if (pan) {
        pan.connect(g);
        const lfo = ctx.createOscillator(), la = ctx.createGain(); la.gain.value = 1;
        rampCurve(lfo.frequency, s0, span, (u) => beat(u), 120);
        lfo.connect(la); la.connect(pan.pan);
        lfo.start(Math.max(ctx.currentTime, s0)); lfo.stop(s0 + span);
        nodes.push(lfo);
      }
      mkVoice(() => l.carrier, dst);
    } else if (l.method === 'noise') {
      const src = ctx.createBufferSource();
      src.buffer = pinkBuf(ctx); src.loop = true;
      const gate = ctx.createGain(); gate.gain.value = 0.8;
      const lfo = ctx.createOscillator(), la = ctx.createGain(); la.gain.value = 0.8;
      rampCurve(lfo.frequency, s0, span, (u) => beat(u), 120);
      lfo.connect(la); la.connect(gate.gain);
      src.connect(gate); gate.connect(g);
      src.start(Math.max(ctx.currentTime, s0)); src.stop(s0 + span);
      lfo.start(Math.max(ctx.currentTime, s0)); lfo.stop(s0 + span);
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
