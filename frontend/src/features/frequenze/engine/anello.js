/**
 * Frequenze by Aurya — l'anello: una scheda che gira all'infinito
 * senza scatti (AT4, 21/8/2026).
 *
 * Il perche': i SUONI della libreria sopravvivono al blocco schermo
 * (sono file dentro un <audio loop>), le FREQUENZE no (sono sintesi
 * WebAudio, che i browser mobili sospendono). Per uniformarle serve
 * dare anche a loro un file da mettere in un <audio loop>.
 *
 * Il problema di un file che gira: il punto di giunzione. Se alla fine
 * del file le fasi non sono quelle dell'inizio, si sente un CLIC a ogni
 * giro — su uno strumento da meditazione, inaccettabile.
 *
 * La soluzione e' aritmetica, non un trucco: si sceglie una durata D
 * che chiude TUTTE le componenti periodiche della scheda insieme —
 * la portante, il battito, e il respiro lento del motore (l'ondulazione
 * ±8% con periodo 26 s che envAt aggiunge a ogni livello). Misurato
 * sul catalogo: 28 schede su 36 chiudono in 26 secondi esatti, quasi
 * tutte le altre in 130.
 *
 * Due accortezze che il calcolo da solo non copre:
 *
 * 1. envAt apre ogni livello con un attacco fino a 12 s e lo chiude con
 *    un rilascio fino a 16 s. Renderizzati dentro l'anello, farebbero
 *    PULSARE il giro. Quindi si renderizza una finestra piu' larga e si
 *    ritaglia il centro, dove il livello e' in tenuta piena.
 * 2. rumore e discesa Shepard non hanno fase che torna (il rumore e'
 *    casuale, le voci Shepard accumulano fase per sempre). Per loro
 *    l'aritmetica non basta: interviene la dissolvenza incrociata, che
 *    dove il calcolo E' esatto non cambia nulla (mescola il segnale con
 *    se stesso) e dove non lo e' nasconde la giunzione.
 */

/* Il respiro lento del motore: envAt, `0.08 * Math.sin(TAU*tAbs/26)`.
   Se cambia li', cambia qui — la guardia di parita' lo verifica. */
export const RESPIRO_MOTORE_SEC = 26;
/* L'attacco piu' lungo che envAt possa applicare e' 12 s, il rilascio
   16 s: 30 s di margine per lato tengono il ritaglio in tenuta piena
   con abbondanza. */
export const MARGINE_SEC = 30;
/* La dissolvenza incrociata sulla giunzione. Corta abbastanza da non
   mangiare musica, lunga abbastanza da coprire una discontinuita'. */
export const INCROCIO_SEC = 1.5;
const CAP_CON_RESPIRO = 600;   // oltre, il file diventa scomodo sul telefono

const intero = (x) => Math.abs(x - Math.round(x)) < 1e-6;

/**
 * Le frequenze che devono chiudere il giro, per metodo.
 * Solo quelle con una fase che TORNA: rumore e Shepard non ci sono,
 * ed e' esattamente il motivo per cui esiste la dissolvenza.
 */
function componenti(cfg, battito) {
  const m = cfg.method || 'bin';
  const c = cfg.carrier ?? (m === 'bin' ? 400 : 180);
  if (m === 'tone') return [c];
  if (m === 'drone') return [c / 4];          // 1×, 5/4, 3/2 → tutte multiple di c/4
  if (m === 'bin') return [c, c + battito];   // due orecchie, due portanti
  if (m === 'noise' || m === 'shepard') return [];
  return [c, battito];                        // iso, mono, bil, breath
}

/**
 * La durata dell'anello per questa scheda.
 * @returns {{sec:number, esatto:boolean}} — `esatto` dice se il calcolo
 *          ha chiuso tutto (e quindi la dissolvenza e' solo una rete).
 */
export function durataAnello(cfg, battito) {
  const fs = componenti(cfg, battito).filter((f) => f > 0);
  if (!fs.length) return { sec: 120, esatto: false };   // rumore, Shepard
  // 1º tentativo: multipli del respiro del motore → chiude anche quello
  for (let k = 1; RESPIRO_MOTORE_SEC * k <= CAP_CON_RESPIRO; k++) {
    const D = RESPIRO_MOTORE_SEC * k;
    if (fs.every((f) => intero(D * f))) return { sec: D, esatto: true };
  }
  // 2º: chiudono portante e battito; il respiro resta scoperto, ma e'
  // uno scalino di livello ≤1,4 dB che la dissolvenza copre.
  for (let D = 1; D <= 100; D++) {
    if (fs.every((f) => intero(D * f))) return { sec: D, esatto: false };
  }
  return { sec: 120, esatto: false };
}

/**
 * Lo score da renderizzare: la scheda TENUTA FERMA alla sua frequenza,
 * dentro una finestra con margine da ritagliare.
 *
 * Ferma e non in movimento perche' un tragitto (Delta 4 → 2,5 Hz in tre
 * minuti) non e' una cosa che si puo' ripetere all'infinito: il giro e'
 * il punto d'arrivo, cioe' dove si sta quando si ascolta a lungo.
 * Chi ha preso il comando col campo della frequenza si porta dietro il
 * SUO numero: e' quello che gli passa il chiamante.
 */
export function scoreAnello(cfg, battito, portante, durataSec) {
  const m = cfg.method || 'bin';
  const totale = MARGINE_SEC * 2 + durataSec + INCROCIO_SEC;
  const layer = {
    id: 1, kind: 'neuro', name: cfg.name || 'Frequenza',
    method: m, timbre: cfg.timbre || 'warm',
    carrier: portante,
    // Shepard legge f0 come «ottave al minuto»: non e' un battito e non
    // va sostituito col numero dell'utente.
    f0: m === 'shepard' ? (cfg.f0 ?? 1.5) : battito,
    f1: m === 'shepard' ? (cfg.f0 ?? 1.5) : battito,
    curve: 'lin', start: 0, end: totale,
    gain: cfg.gain ?? 0.25, breath: cfg.breath !== false, mute: false,
    ...(cfg.color ? { color: cfg.color } : {}),
  };
  return {
    score_version: 1, duration_sec: totale,
    fade_in_sec: 0, fade_out_sec: 0,      // le dissolvenze le mette il ritaglio
    layers: [layer], phases: [],
  };
}

/**
 * Ritaglia dal render la finestra centrale e chiude il giro.
 *
 * Prende [M, M+D] e ci dissolve sopra [M+D, M+D+x]: la coda entra
 * mentre la testa esce, quindi l'ultimo campione si congiunge col
 * primo. Dove il calcolo e' esatto le due parti sono IDENTICHE e la
 * dissolvenza non cambia un campione — e' per questo che si puo'
 * applicare sempre senza rischiare artefatti sui toni puri.
 */
export function ritagliaAnello(pcm, sr, durataSec) {
  const off = Math.round(MARGINE_SEC * sr);
  const n = Math.round(durataSec * sr);
  const x = Math.round(INCROCIO_SEC * sr);
  const out = new Int16Array(n * 2);
  out.set(pcm.subarray(off * 2, (off + n) * 2));
  for (let i = 0; i < x; i++) {
    // coseno rialzato: somma dei pesi = 1 a ogni istante, quindi il
    // livello non cala nel mezzo dell'incrocio
    const a = 0.5 * (1 + Math.cos((Math.PI * i) / x));   // 1 → 0
    const src = (off + n + i) * 2;
    if (src + 1 >= pcm.length) break;
    out[i * 2] = Math.round(out[i * 2] * a + pcm[src] * (1 - a));
    out[i * 2 + 1] = Math.round(out[i * 2 + 1] * a + pcm[src + 1] * (1 - a));
  }
  return out;
}
