/**
 * Frequenze by Aurya — risoluzione basi sonore (FQ2, 18/8/2026).
 *
 * Le basi della libreria arrivano come URL (uploads/audio): qui si
 * scaricano e si decodificano in AudioBuffer, con cache per URL — una
 * base usata in tre tracce si scarica una volta sola. JS puro come il
 * resto dell'engine: la pagina non tocca mai decodeAudioData.
 */

import { cleanVoiceBuffer } from './voicefx';
import { notaDiagnosi } from './diagnosi';
import { anelloDaBuffer } from './anello';

/* ── ES3 (21/8) — lo spezzone ──────────────────────────────────────
 * Misurato: una base ambient da 30 minuti decodificata occupa 611 MB
 * di RAM (×11 rispetto al file). Due basi lunghe = 1,2 GB = il
 * telefono chiude la scheda. E in libreria 9 basi ambient su 18 sono
 * lunghe: non e' un caso limite, e' la strada normale di chi compone.
 *
 * Rimedio: di una base usata come TAPPETO (loop) si chiede solo il
 * primo spezzone — i Range HTTP ci sono da oggi — e lo si chiude in
 * anello con la dissolvenza incrociata. Provato su entrambi i formati
 * della libreria: 3,8 MB scaricati e ~65 MB di RAM al posto di 908.
 *
 * Il criterio NON e' inventato: e' il flag `loop` del livello. Un
 * brano che evolve (loop:false) si scarica intero, com'e' giusto.
 */
export const SPEZZONE_SEC = 180;        // ~3 min di tappeto in anello
const MARGINE_SPEZZONE = 1.25;          // bitrate variabile: si chiede un po' di piu'

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
  for (const [chiave, v] of bufferCache) {        // ordine d'inserimento
    // la chiave puo' portare il suffisso #tappeto (ES3): la protezione
    // «non buttare cio' che sta suonando» ragiona sull'URL nudo, o
    // sfratterebbe proprio le basi in ascolto
    const url = chiave.split('#')[0];
    if (inUso.has(url) || !v.bytes) continue;
    bufferCache.delete(chiave);
    totale -= v.bytes;
    if (totale <= CACHE_MAX_BYTES) break;
  }
}

/**
 * Quanti byte servono per `sec` secondi di questa base.
 * Dai metadati dell'asset (size/durata = bitrate medio reale): niente
 * indovinelli; se i metadati mancano, o se il pezzo coprirebbe quasi
 * tutto il file comunque, si torna al file intero.
 */
function bytesParziale(asset, sec) {
  const dur = asset?.duration_sec, size = asset?.size_bytes;
  if (!dur || !size || !sec) return null;
  if (sec >= dur * 0.9) return null;      // tanto vale prenderlo intero
  return Math.ceil((size / dur) * sec * MARGINE_SPEZZONE);
}

/**
 * @param parziale  se valorizzato ({asset, sec, anello}), della base
 *                  servono solo `sec` secondi: un TAPPETO (anello:true)
 *                  prende lo spezzone e lo chiude in giro; un BRANO
 *                  INTERO usato per una finestra (anello:false) prende
 *                  solo la finestra — la coda la sfuma gia' l'inviluppo
 *                  del livello, niente da ricucire. Domanda esplicita
 *                  del founder: «se una traccia da 30 minuti e' usata
 *                  per 3, si scaricano 3 minuti?» — ora si'.
 */
export function loadAssetBuffer(ctx, url, inUso = new Set([url]), parziale = null) {
  const limite = parziale ? bytesParziale(parziale.asset, parziale.sec) : null;
  // chiave distinta per taglio: la stessa base puo' servire intera in
  // una sessione e parziale in un'altra — buffer diversi
  const chiave = limite ? `${url}#p${limite}` : url;
  if (!bufferCache.has(chiave)) {
    const entry = { bytes: 0 };
    entry.p = fetch(url, limite ? { headers: { Range: `bytes=0-${limite - 1}` } } : {})
      .then((r) => {
        if (!r.ok && r.status !== 206) {
          throw new Error(`base non raggiungibile (${r.status})`);
        }
        // 200 su una richiesta con Range = il server non li conosce
        // (dev vecchio, proxy di mezzo): e' arrivato il file intero,
        // e va trattato come tale — mai tagliarlo.
        const ottenuto = limite != null && r.status === 206;
        return r.arrayBuffer().then((ab) => ({ ab, parziale: ottenuto }));
      })
      .then(({ ab, parziale: ottenuto }) => ctx.decodeAudioData(ab)
        .then((buf) => (ottenuto && parziale?.anello
          ? anelloDaBuffer(ctx, buf) : buf))
        /* SE LO SPEZZONE NON SI DECODIFICA, SI PRENDE IL FILE INTERO.
           Un m4a tagliato a meta' e' un file incompleto: i decoder
           permissivi (desktop) lo accettano, quelli severi no —
           Safari iOS lo RIFIUTA. E il rifiuto finiva in un catch
           silenzioso piu' a valle: la base spariva dal mix e la
           sessione restava muta senza dire nulla (founder, 22/8: da
           telefono niente suono, con `livelloGrafo: 0` nel pannello).
           Qui si perde il risparmio di banda per QUESTA base, mai il
           suono. L'ArrayBuffer e' stato consumato dal decoder: si
           rifa' la richiesta, intera. */
        .catch((e) => {
          if (!ottenuto) throw e;          // era gia' intero: nulla da riprendere
          notaDiagnosi('spezzone non decodificabile → riprendo il file intero: '
            + url.split('/').pop());
          return fetch(url)
            .then((r) => r.arrayBuffer())
            .then((ab2) => ctx.decodeAudioData(ab2));
        }))
      .then((buf) => {
        entry.bytes = buf.length * buf.numberOfChannels * 4;
        sfoltisci(inUso);
        return buf;
      })
      .catch((e) => { bufferCache.delete(chiave); throw e; });
    bufferCache.set(chiave, entry);
  }
  return bufferCache.get(chiave).p;
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
      // tappeto in loop → spezzone in anello; brano intero → solo la
      // finestra che il mix usa davvero (la coda la sfuma l'inviluppo)
      const finestra = Math.max(0, (l.end ?? 0) - (l.start ?? 0));
      const parziale = l.loop !== false
        ? { asset, sec: SPEZZONE_SEC, anello: true }
        : (finestra > 0 ? { asset, sec: finestra + 10, anello: false } : null);
      const buffer = await loadAssetBuffer(ctx, asset.stream_url, inUso, parziale);
      out.push({ id: l.id, buffer, start: l.start, end: l.end,
                 gain: l.gain, loop: l.loop !== false, mute: false });
    } catch (e) {
      /* base saltata: meglio una sessione parziale che muta. Ma se le
         basi sono tutte qui, «parziale» vuol dire MUTA: il silenzio
         non deve piu' essere invisibile. */
      notaDiagnosi('BASE SALTATA (' + (asset.stream_url || '').split('/').pop()
        + '): ' + (e && e.message ? e.message : e));
    }
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


/**
 * ES3 — quanta memoria chiedera' questa sessione al dispositivo.
 *
 * Non un numero da nascondere in un log: e' l'informazione che decide
 * se la sessione partira' su un telefono. Un AudioBuffer costa
 * sampleRate x canali x 4 byte al secondo (~0,35 MB/s a 44,1 kHz
 * stereo); i livelli in loop pagano solo lo spezzone (SPEZZONE_SEC),
 * quelli interi pagano tutta la loro durata.
 *
 * @returns {{mb:number, colpevoli:string[]}} — i colpevoli sono le
 *          basi intere che pesano davvero: e' con loro che si tratta.
 */
export function memoriaStimataMB(score, assetsById, sampleRate = 44100) {
  const alSecondo = (sampleRate * 2 * 4) / 1048576;
  let mb = 0;
  const colpevoli = [];
  for (const l of (score?.layers || [])) {
    if (l.kind !== 'audio' || l.mute) continue;
    const a = assetsById?.[l.asset_id];
    const dur = a?.duration_sec;
    if (!dur) continue;
    const finestra = Math.max(0, (l.end ?? dur) - (l.start ?? 0));
    const usati = l.loop !== false
      ? Math.min(SPEZZONE_SEC, dur)
      : Math.min(finestra || dur, dur);
    const peso = usati * alSecondo;
    mb += peso;
    if (peso > 150) colpevoli.push(a.title || 'una base');
  }
  return { mb: Math.round(mb), colpevoli };
}
