/**
 * Frequenze by Aurya — render offline (FQ0, 18/8/2026).
 *
 * Sintesi analitica esatta dello score in PCM 16-bit stereo, poi WAV o
 * MP3 320 (lamejs, import dinamico: l'encoder da 150KB entra in memoria
 * solo quando l'operatore esporta). Estratto fedelmente dal prototipo.
 * L'export e' una funzione per l'OPERATORE: il formato di pubblicazione
 * resta lo score (docs/FREQUENZE_PLAN_2026-08.md).
 */

import { neuroSample, neuroSampleInit } from './synth';

const sm = (x) => (x <= 0 ? 0 : x >= 1 ? 1 : x * x * (3 - 2 * x));

/**
 * Renderizza lo score in PCM interleaved L/R.
 *
 * @param score  score v1
 * @param opts   { sampleRate, audioLayers, onProgress } — audioLayers come
 *               in startPreview (basi con AudioBuffer locale)
 * @returns Promise<Int16Array>
 */
export async function renderPcm(score, { sampleRate = 44100, audioLayers = [], onProgress } = {}) {
  const sr = sampleRate, d = score.duration_sec, dt = 1 / sr;
  const total = Math.floor(d * sr);
  const audio = audioLayers.filter((l) => !l.mute && l.gain > 0 && l.buffer);
  const neuro = (score.layers || []).filter((l) => l.kind !== 'audio' && !l.mute && l.gain > 0);
  if (!audio.length && !neuro.length) throw new Error('Nessun livello udibile');
  const fi = score.fade_in_sec || 0, fo = score.fade_out_sec || 0;
  const pcm = new Int16Array(total * 2);
  const CHUNK = 20;
  const cl = (v) => (v > 32767 ? 32767 : v < -32768 ? -32768 : v);
  neuro.forEach(neuroSampleInit);

  for (let cs = 0; cs < d; cs += CHUNK) {
    const len = Math.min(CHUNK, d - cs), frames = Math.floor(len * sr);
    let L = null, R = null;
    if (audio.length) {
      const off = new OfflineAudioContext(2, frames, sr);
      audio.forEach((l) => {
        const span = Math.max(1, Math.min(l.end, d) - l.start);
        const segEnd = l.loop ? l.start + span
                              : Math.min(l.start + span, l.start + l.buffer.duration);
        if (segEnd <= cs || l.start >= cs + len) return;
        const t0 = Math.max(l.start, cs), tE = Math.min(segEnd, cs + len);
        const src = off.createBufferSource();
        src.buffer = l.buffer; src.loop = l.loop;
        const g = off.createGain(); src.connect(g); g.connect(off.destination);
        const a = Math.min(6, span * 0.2), r = Math.min(8, span * 0.25);
        const ev = (t) => {
          const u = t - l.start;
          if (u <= 0 || u >= span) return 0;
          let e = l.gain;
          if (u < a) e *= sm(u / a);
          if (span - u < r) e *= sm((span - u) / r);
          return e;
        };
        g.gain.setValueAtTime(ev(t0), t0 - cs);
        [l.start + a, l.start + span - r].forEach((pt) => {
          if (pt > t0 && pt < tE) g.gain.linearRampToValueAtTime(ev(pt), pt - cs);
        });
        g.gain.linearRampToValueAtTime(ev(tE), tE - cs);
        const offst = l.loop ? (t0 - l.start) % l.buffer.duration : t0 - l.start;
        src.start(t0 - cs, Math.min(offst, Math.max(0, l.buffer.duration - 0.001)));
        src.stop(tE - cs);
      });
      const rb = await off.startRendering();
      L = rb.getChannelData(0);
      R = rb.numberOfChannels > 1 ? rb.getChannelData(1) : L;
    }
    const base = Math.floor(cs * sr);
    for (let n = 0; n < frames; n++) {
      const t = cs + n / sr;
      let m = 1;
      if (fi > 0 && t < fi) m = t / fi;
      if (fo > 0 && t > d - fo) m = Math.min(m, Math.max(0, (d - t) / fo));
      let sL = L ? L[n] : 0, sR = R ? R[n] : 0;
      for (const nl of neuro) {
        const [a2, b2] = neuroSample(nl, t, dt);
        sL += a2; sR += b2;
      }
      const idx = (base + n) * 2;
      if (idx + 1 >= pcm.length) break;
      pcm[idx] = cl(sL * m * 32767);
      pcm[idx + 1] = cl(sR * m * 32767);
    }
    if (onProgress) onProgress(Math.min(1, (cs + len) / d));
    await new Promise((r) => setTimeout(r, 0));
  }
  return pcm;
}

export function wavBlob(pcm, sr) {
  const bytes = pcm.length * 2, buf = new ArrayBuffer(44 + bytes), v = new DataView(buf);
  const s = (o, t) => { for (let i = 0; i < t.length; i++) v.setUint8(o + i, t.charCodeAt(i)); };
  s(0, 'RIFF'); v.setUint32(4, 36 + bytes, true); s(8, 'WAVE');
  s(12, 'fmt '); v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 2, true);
  v.setUint32(24, sr, true); v.setUint32(28, sr * 4, true); v.setUint16(32, 4, true);
  v.setUint16(34, 16, true);
  s(36, 'data'); v.setUint32(40, bytes, true);
  new Int16Array(buf, 44).set(pcm);
  return new Blob([buf], { type: 'audio/wav' });
}

// MP3 a 320 kbps CBR: il massimo del formato — preserva la separazione dei
// canali (essenziale per i battiti binaurali) con degradazione impercettibile.
export async function mp3Blob(pcm, sr, onProgress) {
  const { default: lamejs } = await import('./lamejs.vendor');
  const enc = new lamejs.Mp3Encoder(2, sr, 320);
  const frames = pcm.length / 2, BLK = 1152 * 64, parts = [];
  const L = new Int16Array(BLK), R = new Int16Array(BLK);
  for (let i = 0; i < frames; i += BLK) {
    const n = Math.min(BLK, frames - i);
    for (let j = 0; j < n; j++) {
      L[j] = pcm[(i + j) * 2];
      R[j] = pcm[(i + j) * 2 + 1];
    }
    const sub = enc.encodeBuffer(n === BLK ? L : L.subarray(0, n),
                                 n === BLK ? R : R.subarray(0, n));
    if (sub.length) parts.push(new Uint8Array(sub));
    if (onProgress) onProgress(i / frames);
    if ((i / BLK) % 8 === 0) await new Promise((r) => setTimeout(r, 0));
  }
  const end = enc.flush();
  if (end.length) parts.push(new Uint8Array(end));
  return new Blob(parts, { type: 'audio/mpeg' });
}
