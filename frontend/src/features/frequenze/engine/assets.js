/**
 * Frequenze by Aurya — risoluzione basi sonore (FQ2, 18/8/2026).
 *
 * Le basi della libreria arrivano come URL (uploads/audio): qui si
 * scaricano e si decodificano in AudioBuffer, con cache per URL — una
 * base usata in tre tracce si scarica una volta sola. JS puro come il
 * resto dell'engine: la pagina non tocca mai decodeAudioData.
 */

import { cleanVoiceBuffer } from './voicefx';

const bufferCache = new Map(); // url → { p: Promise<AudioBuffer>, bytes }

/* TS4 — il tetto. Un AudioBuffer decodificato pesa ~0,4 MB al secondo
   (48 kHz stereo float32): tre basi lunghe superano i 200 MB, e su un
   telefono e' un crash che arriva dopo, lontano dalla causa. Oltre il
   tetto si liberano le entrate piu' vecchie NON in uso adesso: chi
   ascolta non perde niente, chi ha solo ascoltato in passato ricarica. */
const CACHE_MAX_BYTES = 60 * 1024 * 1024;

function sfoltisci(inUso) {
  let totale = 0;
  bufferCache.forEach((v) => { totale += v.bytes || 0; });
  if (totale <= CACHE_MAX_BYTES) return;
  for (const [url, v] of bufferCache) {           // ordine d'inserimento
    if (inUso.has(url) || !v.bytes) continue;
    bufferCache.delete(url);
    totale -= v.bytes;
    if (totale <= CACHE_MAX_BYTES) break;
  }
}

export function loadAssetBuffer(ctx, url, inUso = new Set([url])) {
  if (!bufferCache.has(url)) {
    const entry = { bytes: 0 };
    entry.p = fetch(url)
      .then((r) => {
        if (!r.ok) throw new Error(`base non raggiungibile (${r.status})`);
        return r.arrayBuffer();
      })
      .then((ab) => ctx.decodeAudioData(ab))
      .then((buf) => {
        entry.bytes = buf.length * buf.numberOfChannels * 4;
        sfoltisci(inUso);
        return buf;
      })
      .catch((e) => { bufferCache.delete(url); throw e; });
    bufferCache.set(url, entry);
  }
  return bufferCache.get(url).p;
}

/**
 * Risolve i layer audio di uno score in audioLayers per il motore
 * (startPreview / renderPcm): [{id, buffer, start, end, gain, loop,
 * mute}]. `soundsById` mappa asset_id → {stream_url}. I layer con base
 * irrisolvibile vengono saltati (la sessione suona senza).
 */
export async function resolveAudioLayers(ctx, score, soundsById) {
  const out = [];
  const inUso = new Set((score.layers || [])
    .map((l) => soundsById[l.asset_id]?.stream_url).filter(Boolean));
  for (const l of (score.layers || [])) {
    if (l.kind !== 'audio' || l.mute || !l.gain) continue;
    const asset = soundsById[l.asset_id];
    if (!asset || !asset.stream_url) continue;
    try {
      const buffer = await loadAssetBuffer(ctx, asset.stream_url, inUso);
      out.push({ id: l.id, buffer, start: l.start, end: l.end,
                 gain: l.gain, loop: l.loop !== false, mute: false });
    } catch (e) { /* base saltata: meglio una sessione parziale che muta */ }
  }
  return out;
}

/**
 * FV2 — risolve i layer VOCE di uno score: [{...layer, buffer}].
 * `voiceById` mappa asset_id → {stream_url} (gli spezzoni dell'org nel
 * compositore, o quelli della traccia nel player pubblico). Il buffer e'
 * il clip DRY: la catena effetti si costruisce all'ascolto (voicefx.js).
 */
export async function resolveVoiceLayers(ctx, score, voiceById) {
  const out = [];
  for (const l of (score.layers || [])) {
    if (l.kind !== 'voice' || l.mute || !l.gain) continue;
    const asset = voiceById[l.asset_id];
    if (!asset || !asset.stream_url) continue;
    try {
      const raw = await loadAssetBuffer(ctx, asset.stream_url,
        new Set((score.layers || [])
          .map((l2) => voiceById[l2.asset_id]?.stream_url).filter(Boolean)));
      // FV5 — pulizia deterministica (trim, gate, declick, normalize):
      // il file resta intatto, il buffer suona pulito ovunque uguale
      const buffer = cleanVoiceBuffer(ctx, raw);
      out.push({ id: l.id, buffer, start: l.start, end: l.end,
                 gain: l.gain, fx: l.fx || 'dream',
                 fx_amount: l.fx_amount ?? 0.6,
                 clip_in: l.clip_in || 0, mute: false });
    } catch (e) { /* spezzone saltato: sessione parziale, mai muta */ }
  }
  return out;
}

/** Durata in secondi di un File audio locale (upload admin). */
export async function fileDuration(ctx, file) {
  try {
    const buf = await ctx.decodeAudioData(await file.arrayBuffer());
    return Math.round(buf.duration * 10) / 10;
  } catch { return 0; }
}
