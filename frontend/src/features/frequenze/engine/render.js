/**
 * Frequenze by Aurya — render offline (FQ0, 18/8/2026).
 *
 * Sintesi analitica esatta dello score in PCM 16-bit stereo, poi WAV o
 * MP3 320 (lamejs, import dinamico: l'encoder da 150KB entra in memoria
 * solo quando l'operatore esporta). Estratto fedelmente dal prototipo.
 * L'export e' una funzione per l'OPERATORE: il formato di pubblicazione
 * resta lo score (docs/FREQUENZE_PLAN_2026-08.md).
 */

import { neuroSample, neuroSampleInit, attackRelease } from './synth';
import {
  buildVoiceChain, connectVoiceSources, duckEnvelope, tailSeconds, makeImpulse,
} from './voicefx';
// CI-F2 — lo spazio e la Stanza: stessa matematica dell'anteprima
import { creaSpazio, creaStanza, mandata, spaceValido, stanzaValida, STANZE } from './spazio';

const sm = (x) => (x <= 0 ? 0 : x >= 1 ? 1 : x * x * (3 - 2 * x));

/* FV2 — pre-render di uno spezzone voce CON effetto: clip + coda di
   riverbero in un buffer "wet" unico, cosi' il mixer a chunk non tronca
   mai le code ai bordi. Il volume del layer e' gia' cotto dentro. */
async function renderWetVoice(l, d, sr) {
  const clipIn = Math.min(l.clip_in || 0, Math.max(0, l.buffer.duration - 0.2));
  const playLen = Math.min(Math.max(0.5, Math.min(l.end, d) - l.start),
                           l.buffer.duration - clipIn);
  const total = playLen + tailSeconds(l.fx);
  const off = new OfflineAudioContext(2, Math.ceil(total * sr), sr);
  const chain = buildVoiceChain(off, l.fx, l.fx_amount);
  const gv = off.createGain(); gv.gain.value = l.gain;
  chain.output.connect(gv);
  /* CI-F2 — la voce nello spazio SOLO se l'autore l'ha scelto: la
     traiettoria parte dal secondo 0 del clip, come dal vivo */
  if (spaceValido('voice', l.space?.preset)) {
    const sp = creaSpazio(off, l.space.preset, { tA: 0, uA: 0, uB: total });
    gv.connect(sp.input); sp.output.connect(off.destination);
  } else {
    gv.connect(off.destination);
  }
  /* lo stesso attacco netto del vivo (12ms): il master non puo'
     suonare diverso da cio' che si ascolta in Crea */
  const dk = Math.min(0.012, playLen / 4);
  chain.input.gain.setValueAtTime(0.0001, 0);
  chain.input.gain.linearRampToValueAtTime(1, dk);
  chain.input.gain.setValueAtTime(1, Math.max(dk, playLen - dk));
  chain.input.gain.linearRampToValueAtTime(0.0001, playLen);
  connectVoiceSources(off, l.buffer, chain).forEach((src) => {
    src.start(0, clipIn); src.stop(playLen);
  });
  const wet = await off.startRendering();
  return { start: l.start, buffer: wet };
}

/**
 * Renderizza lo score in PCM interleaved L/R.
 *
 * @param score  score v1
 * @param opts   { sampleRate, audioLayers, onProgress } — audioLayers come
 *               in startPreview (basi con AudioBuffer locale)
 * @returns Promise<Int16Array>
 */
export async function renderPcm(score, { sampleRate = 44100, audioLayers = [],
                                         voiceLayers = [], voiceDuck = false,
                                         onProgress, sink = null } = {}) {
  /* CI-F4 — `sink(Int16Array)`: se c'e', ogni blocco viene consegnato
     appena pronto e il PCM intero NON si alloca (90 minuti sarebbero
     ~950 MB). Senza sink, il comportamento di sempre. */
  const sr = sampleRate, d = score.duration_sec, dt = 1 / sr;
  const total = Math.floor(d * sr);
  const audio = audioLayers.filter((l) => !l.mute && l.gain > 0 && l.buffer);
  const voice = voiceLayers.filter((l) => !l.mute && l.gain > 0 && l.buffer);
  const neuro = (score.layers || []).filter(
    (l) => (l.kind || 'neuro') === 'neuro' && !l.mute && l.gain > 0);
  if (!audio.length && !neuro.length && !voice.length) {
    throw new Error('Nessun livello udibile');
  }
  // spezzoni voce: pre-render con effetto (coda inclusa, volume cotto)
  const wetClips = [];
  for (const l of voice) wetClips.push(await renderWetVoice(l, d, sr));
  const denv = (voiceDuck && voice.length) ? duckEnvelope(voice) : null;
  const duckPts = denv ? voice.flatMap(
    (l) => [l.start - 1, l.start, l.end, l.end + 1]) : [];
  const fi = score.fade_in_sec || 0, fo = score.fade_out_sec || 0;
  const pcm = sink ? null : new Int16Array(total * 2);
  const CHUNK = 20;
  const cl = (v) => (v > 32767 ? 32767 : v < -32768 ? -32768 : v);
  neuro.forEach(neuroSampleInit);

  /* CI-F2 — LO SPAZIO NEL MASTER A BLOCCHI. Panner e Stanza hanno una
     coda (HRTF pochi ms, la Stanza fino a 5,5 s): un blocco reso da
     solo la perderebbe al bordo. Convoluzione e panner sono lineari,
     quindi la coda del blocco n si SOMMA all'inizio del blocco n+1: ogni
     blocco si rende piu' lungo di `tailFrames` e l'eccedenza si
     riporta. Senza spazio ne' Stanza `tailFrames` e' 0 e il percorso e'
     quello di ieri, campione per campione. */
  const stanzaNome = stanzaValida(score.stanza) ? score.stanza : null;
  const conSpazio = !!stanzaNome || audio.some((l) => spaceValido('audio', l.space?.preset));
  const tailSec = conSpazio ? Math.max(0.05, stanzaNome ? STANZE[stanzaNome].sec + 0.3 : 0) : 0;
  const tailFrames = Math.ceil(tailSec * sr);
  let carryL = new Float32Array(tailFrames), carryR = new Float32Array(tailFrames);

  for (let cs = 0; cs < d; cs += CHUNK) {
    const len = Math.min(CHUNK, d - cs), frames = Math.floor(len * sr);
    let L = null, R = null;
    if (audio.length || wetClips.length) {
      const off = new OfflineAudioContext(2, frames + tailFrames, sr);
      const stanza = stanzaNome ? creaStanza(off, stanzaNome, makeImpulse) : null;
      if (stanza) stanza.output.connect(off.destination);
      audio.forEach((l) => {
        const span = Math.max(1, Math.min(l.end, d) - l.start);
        /* TG (24/8) — il taglio della base: `clip_in` sono i secondi
           saltati dentro il file. Il render deve dire ESATTAMENTE
           quello che si sente in Crea (e' il master di domani). */
        const tagl = Math.min(l.clip_in || 0, Math.max(0, l.buffer.duration - 0.2));
        const utile = Math.max(0.2, l.buffer.duration - tagl);
        const segEnd = l.loop ? l.start + span
                              : Math.min(l.start + span, l.start + utile);
        if (segEnd <= cs || l.start >= cs + len) return;
        const t0 = Math.max(l.start, cs), tE = Math.min(segEnd, cs + len);
        const src = off.createBufferSource();
        src.buffer = l.buffer; src.loop = l.loop;
        if (l.loop && tagl > 0) { src.loopStart = tagl; src.loopEnd = l.buffer.duration; }
        const g = off.createGain(); src.connect(g);
        if (spaceValido('audio', l.space?.preset)) {
          /* la traiettoria e' funzione del tempo dello STRATO: il
             blocco 37 calcola lo stesso punto dell'anteprima */
          const sp = creaSpazio(off, l.space.preset,
            { tA: t0 - cs, uA: t0 - l.start, uB: tE - l.start });
          g.connect(sp.input); sp.output.connect(off.destination);
          const send = stanza ? mandata(l.space.preset) : 0;
          if (send > 0) {
            const sg = off.createGain(); sg.gain.value = send;
            sp.output.connect(sg); sg.connect(stanza.input);
          }
        } else {
          g.connect(off.destination);
        }
        const { a, r } = attackRelease(span);   // TS1a: stessi numeri ovunque
        const ev = (t) => {
          const u = t - l.start;
          if (u <= 0 || u >= span) return 0;
          let e = l.gain;
          if (u < a) e *= sm(u / a);
          if (span - u < r) e *= sm((span - u) / r);
          return e * (denv ? denv(t) : 1);   // FV2: le basi sotto la voce
        };
        g.gain.setValueAtTime(ev(t0), t0 - cs);
        [l.start + a, l.start + span - r, ...duckPts].sort((x, y) => x - y)
          .forEach((pt) => {
            if (pt > t0 && pt < tE) g.gain.linearRampToValueAtTime(ev(pt), pt - cs);
          });
        g.gain.linearRampToValueAtTime(ev(tE), tE - cs);
        const offst = l.loop ? tagl + ((t0 - l.start) % utile) : tagl + (t0 - l.start);
        src.start(t0 - cs, Math.min(offst, Math.max(0, l.buffer.duration - 0.001)));
        src.stop(tE - cs);
      });
      // FV2 — voce: il buffer wet e' gia' pronto (effetto, coda, volume):
      // qui si piazza e basta, il chunking non tronca niente
      wetClips.forEach((w) => {
        const wEnd = w.start + w.buffer.duration;
        if (wEnd <= cs || w.start >= cs + len) return;
        const src = off.createBufferSource();
        src.buffer = w.buffer;
        src.connect(off.destination);
        const when = Math.max(0, w.start - cs);
        const offst = Math.max(0, cs - w.start);
        src.start(when, Math.min(offst, Math.max(0, w.buffer.duration - 0.001)));
        src.stop(Math.min(len, wEnd - cs));
      });
      const rb = await off.startRendering();
      L = rb.getChannelData(0);
      R = rb.numberOfChannels > 1 ? rb.getChannelData(1) : L;
      if (tailFrames > 0) {
        /* riporto della coda: quella del blocco precedente si somma qui,
           quella di questo blocco viaggia al prossimo */
        const nL = new Float32Array(tailFrames), nR = new Float32Array(tailFrames);
        for (let n = 0; n < frames; n++) {
          if (n < carryL.length) { L[n] += carryL[n]; R[n] += carryR[n]; }
        }
        for (let k = 0; k < tailFrames; k++) {
          const j = frames + k;
          nL[k] = L[j] + (j < carryL.length ? carryL[j] : 0);
          nR[k] = R[j] + (j < carryR.length ? carryR[j] : 0);
        }
        carryL = nL; carryR = nR;
      }
    }
    const base = Math.floor(cs * sr);
    const dest = sink ? new Int16Array(frames * 2) : pcm;
    const offsetIdx = sink ? 0 : base * 2;
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
      const idx = offsetIdx + n * 2;
      if (idx + 1 >= dest.length) break;
      dest[idx] = cl(sL * m * 32767);
      dest[idx + 1] = cl(sR * m * 32767);
    }
    if (sink) sink(dest);
    if (onProgress) onProgress(Math.min(1, (cs + len) / d));
    await new Promise((r) => setTimeout(r, 0));
  }
  return sink ? null : pcm;
}

/**
 * CI-F4 — render e codifica MP3 A BLOCCHI: ogni blocco di PCM entra
 * nell'encoder appena pronto, e si tiene in memoria solo l'MP3 (per 90
 * minuti a 192 kbps ~125 MB, contro ~950 MB di PCM). Stessa pipeline di
 * renderPcm + mp3Blob: stesso suono, stessi numeri.
 */
export async function renderMp3Streaming(score, opts = {}, kbps = 192) {
  const sr = opts.sampleRate || 44100;
  const { default: lamejs } = await import('./lamejs.vendor');
  const enc = new lamejs.Mp3Encoder(2, sr, kbps);
  const parts = [];
  const BLK = 1152 * 64;
  const Lb = new Int16Array(BLK), Rb = new Int16Array(BLK);
  const sink = (chunk) => {
    const frames = chunk.length / 2;
    for (let i = 0; i < frames; i += BLK) {
      const n = Math.min(BLK, frames - i);
      for (let j = 0; j < n; j++) {
        Lb[j] = chunk[(i + j) * 2];
        Rb[j] = chunk[(i + j) * 2 + 1];
      }
      const sub = enc.encodeBuffer(n === BLK ? Lb : Lb.subarray(0, n),
                                   n === BLK ? Rb : Rb.subarray(0, n));
      if (sub.length) parts.push(new Uint8Array(sub));
    }
  };
  await renderPcm(score, { ...opts, sampleRate: sr, sink });
  const end = enc.flush();
  if (end.length) parts.push(new Uint8Array(end));
  return new Blob(parts, { type: 'audio/mpeg' });
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

// MP3 CBR. 320 kbps (default) per l'export dell'operatore: il massimo
// del formato, separazione dei canali intatta (battiti binaurali).
// IL MASTER di pubblicazione usa 192: per un ascolto in streaming e'
// trasparente e il file di 27 minuti pesa ~37 MB invece di ~62.
export async function mp3Blob(pcm, sr, onProgress, kbps = 320) {
  const { default: lamejs } = await import('./lamejs.vendor');
  const enc = new lamejs.Mp3Encoder(2, sr, kbps);
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
