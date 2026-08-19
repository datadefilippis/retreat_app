/**
 * Frequenze by Aurya — risoluzione basi sonore (FQ2, 18/8/2026).
 *
 * Le basi della libreria arrivano come URL (uploads/audio): qui si
 * scaricano e si decodificano in AudioBuffer, con cache per URL — una
 * base usata in tre tracce si scarica una volta sola. JS puro come il
 * resto dell'engine: la pagina non tocca mai decodeAudioData.
 */

const bufferCache = new Map(); // url → Promise<AudioBuffer>

export function loadAssetBuffer(ctx, url) {
  if (!bufferCache.has(url)) {
    const p = fetch(url)
      .then((r) => {
        if (!r.ok) throw new Error(`base non raggiungibile (${r.status})`);
        return r.arrayBuffer();
      })
      .then((ab) => ctx.decodeAudioData(ab))
      .catch((e) => { bufferCache.delete(url); throw e; });
    bufferCache.set(url, p);
  }
  return bufferCache.get(url);
}

/**
 * Risolve i layer audio di uno score in audioLayers per il motore
 * (startPreview / renderPcm): [{id, buffer, start, end, gain, loop,
 * mute}]. `soundsById` mappa asset_id → {stream_url}. I layer con base
 * irrisolvibile vengono saltati (la sessione suona senza).
 */
export async function resolveAudioLayers(ctx, score, soundsById) {
  const out = [];
  for (const l of (score.layers || [])) {
    if (l.kind !== 'audio' || l.mute || !l.gain) continue;
    const asset = soundsById[l.asset_id];
    if (!asset || !asset.stream_url) continue;
    try {
      const buffer = await loadAssetBuffer(ctx, asset.stream_url);
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
      const buffer = await loadAssetBuffer(ctx, asset.stream_url);
      out.push({ id: l.id, buffer, start: l.start, end: l.end,
                 gain: l.gain, fx: l.fx || 'dream',
                 fx_amount: l.fx_amount ?? 0.6, mute: false });
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
