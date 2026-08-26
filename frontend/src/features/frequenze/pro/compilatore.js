/**
 * IL COMPILATORE — steps → score (Sound Professional P1, 26/8/2026).
 *
 * L'unico ponte fra il modello professionale («passi») e il contratto
 * audio esistente (score v1). Il principio, alla lettera:
 *
 *   il professionista progetta protocolli;
 *   il compilatore li traduce;
 *   il motore li suona;
 *   il motore NON sa nulla del professionista.
 *
 * PURO E SENZA IMPORT: nessun motore qui dentro, nessun accesso al
 * DOM, nessuno stato. Stesso input → stesso output, byte per byte.
 * Gira identico nel browser (l'anteprima del Builder) e in Node (i
 * test lo eseguono davvero e passano il risultato a clean_score, il
 * validatore DEL SERVER).
 *
 * LA PROPRIETA' CHE GOVERNA TUTTO: lo score prodotto deve essere
 * accettato da clean_score SENZA CORREZIONI — compila(steps) deve
 * essere identico a clean_score(compila(steps)). Per questo:
 *   - i fade sono emessi ESPLICITI (omessi, il contratto scriverebbe
 *     i suoi default 5/10);
 *   - start/end sono gia' arrotondati a 3 decimali, la durata a 1;
 *   - ogni layer porta ESATTAMENTE le 13 chiavi del layer pulito, con
 *     gli stessi default (timbre warm, breath true, mute false,
 *     f0/f1=10 dove il metodo non li usa);
 *   - le fasi sono [] (con 24 passi sforerebbero PHASES_MAX, e non
 *     hanno consumatori).
 *
 * IL TEMPO E' UN CURSORE: start = t, end = t + durata, poi
 * t += durata + pausa. Le pause sono BUCHI fra le finestre: le
 * sovrapposizioni sono impossibili per costruzione. La pausa dopo
 * l'ultimo passo si ignora (coda di silenzio senza senso).
 *
 * LE TRANSIZIONI: il DSL dice solo «fisso o transizione»
 * (battito_fine_hz presente o no); la curva la decide QUI il
 * compilatore, sempre esponenziale — percettivamente uniforme
 * (rapporti uguali in tempi uguali), la stessa scelta di CALM e
 * GROUND, e sempre valida perche' i battiti sono > 0 per contratto.
 *
 * LE COSTANTI sono il gemello di models/frequency_track.py: una
 * guardia di parita' nel backend le confronta coi valori veri — se il
 * contratto cambia, il test rompe qui prima che il compilatore menta.
 */

/* — gemelli di frequency_track.py (guardia di parita' nel backend) — */
export const PASSI_MAX = 24;              // LAYERS_MAX
export const DURATA_MIN = 60;             // DURATION_MIN
export const DURATA_MAX = 1800;           // DURATION_MAX
export const PORTANTE_MIN = 20;           // CARRIER_MIN
export const PORTANTE_MAX = 2000;         // CARRIER_MAX
export const BATTITO_MIN = 0.05;          // BEAT_MIN
export const BATTITO_MAX = 60;            // BEAT_MAX
/* i default che clean_layer scrive dove il metodo non usa i campi */
const BATTITO_NEUTRO = 10.0;              // min(10.0, beat_hi)

export const METODI_PASSO = Object.freeze(['tone', 'drone', 'bin', 'iso']);
const CON_BATTITO = Object.freeze(['bin', 'iso']);

export const PASSO_DURATA_MIN = 1;        // il contratto vuole >= 0.5: teniamo 1
export const GAIN_MIN = 0.05;             // lo zero e' muto: fuori dall'editor
export const GAIN_MAX = 1;

/** Errore di compilazione: porta l'indice del passo colpevole. */
export class ErrorePasso extends Error {
  constructor(indice, messaggio) {
    super(indice === null ? messaggio : `passo ${indice + 1}: ${messaggio}`);
    this.indice = indice;
  }
}

const r3 = (x) => Math.round(x * 1000) / 1000;
const r1 = (x) => Math.round(x * 10) / 10;
const numero = (v) => typeof v === 'number' && Number.isFinite(v);

/** Valida UN passo (struttura e range). Lancia ErrorePasso. */
function validaPasso(p, i) {
  if (!p || typeof p !== 'object') throw new ErrorePasso(i, 'non è un passo');
  if (!METODI_PASSO.includes(p.metodo)) {
    throw new ErrorePasso(i, `metodo «${p.metodo}» non previsto dal sequencer`);
  }
  if (!numero(p.hz) || p.hz < PORTANTE_MIN || p.hz > PORTANTE_MAX) {
    throw new ErrorePasso(i, `frequenza ${p.hz} fuori da ${PORTANTE_MIN}–${PORTANTE_MAX} Hz`);
  }
  if (!numero(p.durata_sec) || p.durata_sec < PASSO_DURATA_MIN) {
    throw new ErrorePasso(i, `durata ${p.durata_sec}s: il minimo è ${PASSO_DURATA_MIN}s`);
  }
  const pausa = p.pausa_dopo_sec ?? 0;
  if (!numero(pausa) || pausa < 0) throw new ErrorePasso(i, 'pausa negativa');
  if (!numero(p.gain) || p.gain < GAIN_MIN || p.gain > GAIN_MAX) {
    throw new ErrorePasso(i, `volume ${p.gain} fuori da ${GAIN_MIN}–${GAIN_MAX}`);
  }
  const conBattito = CON_BATTITO.includes(p.metodo);
  if (conBattito) {
    if (!numero(p.battito_hz) || p.battito_hz < BATTITO_MIN || p.battito_hz > BATTITO_MAX) {
      throw new ErrorePasso(i, `battito ${p.battito_hz} fuori da ${BATTITO_MIN}–${BATTITO_MAX} Hz`);
    }
    if (p.battito_fine_hz != null
        && (!numero(p.battito_fine_hz)
            || p.battito_fine_hz < BATTITO_MIN || p.battito_fine_hz > BATTITO_MAX)) {
      throw new ErrorePasso(i, `battito finale ${p.battito_fine_hz} fuori range`);
    }
  } else if (p.battito_hz != null || p.battito_fine_hz != null) {
    /* un campo che il motore ignorerebbe e' una promessa falsa */
    throw new ErrorePasso(i, `il metodo «${p.metodo}» non ha un battito`);
  }
}

/** Il nome del layer: deterministico e leggibile (≤ 60 char). */
function nomePasso(p, i) {
  const eticchette = { tone: 'tono', drone: 'accordo', bin: 'battito', iso: 'ritmo' };
  const base = `Passo ${i + 1} · ${eticchette[p.metodo]} ${p.hz} Hz`;
  return base.slice(0, 60);
}

/**
 * steps → score v1. Puro e deterministico.
 * Lancia ErrorePasso su input invalido: MAI uno score «quasi giusto».
 */
export function compila(steps) {
  if (!Array.isArray(steps) || steps.length === 0) {
    throw new ErrorePasso(null, 'serve almeno un passo');
  }
  if (steps.length > PASSI_MAX) {
    throw new ErrorePasso(null, `${steps.length} passi: il massimo è ${PASSI_MAX}`);
  }
  steps.forEach(validaPasso);

  let t = 0;
  const layers = steps.map((p, i) => {
    const inizio = r3(t);
    const fine = r3(t + p.durata_sec);
    const ultimo = i === steps.length - 1;
    t = fine + (ultimo ? 0 : (p.pausa_dopo_sec ?? 0));   // la coda di silenzio si ignora
    const conBattito = CON_BATTITO.includes(p.metodo);
    const f0 = conBattito ? p.battito_hz : BATTITO_NEUTRO;
    const f1 = conBattito ? (p.battito_fine_hz ?? p.battito_hz) : BATTITO_NEUTRO;
    return {
      /* ESATTAMENTE le 13 chiavi di clean_layer, stessi default */
      kind: 'neuro',
      name: nomePasso(p, i),
      method: p.metodo,
      timbre: 'warm',
      carrier: p.hz,
      f0,
      f1,
      /* la transizione e' sempre esponenziale: vedi testata */
      curve: (conBattito && f0 !== f1) ? 'exp' : 'lin',
      start: inizio,
      end: fine,
      gain: p.gain,
      breath: true,
      mute: false,
    };
  });

  const durata = r1(t);
  if (durata < DURATA_MIN) {
    throw new ErrorePasso(null,
      `il protocollo dura ${durata}s: il minimo è ${DURATA_MIN}s (un minuto)`);
  }
  if (durata > DURATA_MAX) {
    throw new ErrorePasso(null,
      `il protocollo dura ${durata}s: il massimo è ${DURATA_MAX}s (trenta minuti)`);
  }

  return {
    score_version: 1,
    duration_sec: durata,
    /* espliciti: omessi, il contratto scriverebbe i SUOI default */
    fade_in_sec: 0,
    fade_out_sec: 0,
    layers,
    phases: [],
  };
}

/** La durata totale (senza compilare): per l'editor. */
export function durataTotale(steps) {
  if (!Array.isArray(steps)) return 0;
  return r1(steps.reduce((t, p, i) => t + (p.durata_sec || 0)
    + (i === steps.length - 1 ? 0 : (p.pausa_dopo_sec || 0)), 0));
}
