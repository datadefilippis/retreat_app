/**
 * LA GUIDA DEL RESPIRO — CI-F1 (22/9/2026, registrazioni del founder).
 *
 * Il founder ha registrato i clip (memo del telefono, preparati con
 * scripts/prepara_respiro.py e importati in libreria con categoria
 * `respiro`): cicli interi («inspira 1 2 3 4, espira 1 2 3 4», «dentro
 * … fuori …», il conteggio nudo, il respiro vero), le parole sole
 * («inspira», «espira») e i soffi. Il tempo di ogni ciclo e' quello
 * della registrazione (`ciclo_sec`, misurato sulla forma d'onda): non
 * si stira la voce, si ripete il clip ogni `ciclo_sec` secondi.
 *
 * Lo strato `kind:'guida'` della ricetta (score v5) descrive una
 * DRAMMATURGIA a round, come nel file SOMA che il founder ha allegato:
 *
 *   round = `respiri` cicli
 *         → ritenzione a VUOTO  (`vuoto_sec`: voce muta, campana all'inizio)
 *         → ritenzione a PIENO  (`pieno_sec`: la parola «inspira», poi
 *                               campana; alla fine la parola «espira»)
 *         → RECUPERO            (`recupero_sec`: campana, respiro libero)
 *   ripetuto `round` volte. Con vuoto/pieno/recupero a 0 e' un respiro
 *   guidato continuo.
 *
 * UNICA VERITA' per vivo (synth.js), master/export (render.js, a
 * blocchi) e ascolto continuo: `partituraGuida()` e' una funzione pura
 * dello strato → lista di eventi al secondo u dello strato; `montaGuida()`
 * li appoggia su un grafo (online o offline) dentro una finestra
 * [da, a): il blocco 37 del master piazza lo stesso clip dell'anteprima.
 *
 * La campana di svolta e' sintetica (528 Hz, due parziali, coda 2,2 s),
 * generata come buffer deterministico: identica ovunque, nessun file.
 *
 * Gemello del backend: models/frequency_track.py (GUIDA_*), guardia di
 * parita' nei test.
 */

export const GUIDA_TIPI = ['ciclo', 'inspira', 'espira', 'conta', 'soffio_in', 'soffio_out'];

export const GUIDA_LIMITI = Object.freeze({
  respiri: [1, 200, 20],
  round: [1, 10, 1],
  vuoto_sec: [0, 300, 0],
  pieno_sec: [0, 120, 0],
  recupero_sec: [0, 180, 0],
});

/* Gli schemi offerti in Crea, in due parole: quello continuo e quello
   a round (la struttura del file SOMA: 2 round, ritenzione a vuoto
   di un minuto, a pieno 15 s, recupero 20 s). */
export const GUIDA_SCHEMI = Object.freeze({
  continuo: { label: 'respiro continuo', round: 1, vuoto_sec: 0, pieno_sec: 0, recupero_sec: 0,
    hint: 'Il ciclo si ripete per tutti i respiri, senza pause.' },
  round: { label: '2 round con ritenzioni', round: 2, vuoto_sec: 60, pieno_sec: 15, recupero_sec: 20,
    hint: 'Respiri, poi trattieni a vuoto, inspira e trattieni, recupero. Due volte.' },
});

const CAMPANA_SEC = 2.2;
const PAROLA_SEC_DEFAULT = 1.6;    // se la parola non c'e', la campana arriva comunque

const dentro = (v, [lo, hi, d]) => {
  const n = Number(v);
  if (!Number.isFinite(n)) return d;
  return Math.max(lo, Math.min(hi, Math.round(n)));
};

/** I numeri dello strato, riportati nei limiti (stessi del backend). */
export function normalizzaGuida(l) {
  const out = {};
  Object.entries(GUIDA_LIMITI).forEach(([k, lim]) => { out[k] = dentro(l[k], lim); });
  return out;
}

/**
 * La partitura: eventi e fasi al secondo u dello strato (0 = quando
 * entra). `ciclo` = secondi fra un ciclo e il successivo; `parolaSec`
 * = durata della parola «inspira» (per piazzare la campana dopo).
 * @returns {{eventi: {t:number, tipo:string}[], fasi: {t:number, nome:string}[], totale: number}}
 */
export function partituraGuida(l, ciclo, parolaSec = PAROLA_SEC_DEFAULT) {
  const g = normalizzaGuida(l);
  const c = Math.max(0.5, Number(ciclo) || 8);
  const campana = l.campana !== false;
  const eventi = [], fasi = [];
  let t = 0;
  for (let r = 1; r <= g.round; r++) {
    fasi.push({ t, nome: g.round > 1 ? `Round ${r}` : 'Respiro guidato' });
    for (let i = 0; i < g.respiri; i++) eventi.push({ t: t + i * c, tipo: 'ciclo' });
    t += g.respiri * c;
    if (g.vuoto_sec > 0) {
      fasi.push({ t, nome: 'Trattieni a vuoto' });
      if (campana) eventi.push({ t, tipo: 'campana' });
      t += g.vuoto_sec;
    }
    if (g.pieno_sec > 0) {
      fasi.push({ t, nome: 'Inspira e trattieni' });
      eventi.push({ t, tipo: 'inspira' });
      if (campana) eventi.push({ t: t + Math.max(0.6, parolaSec) + 0.3, tipo: 'campana' });
      t += g.pieno_sec;
      eventi.push({ t, tipo: 'espira' });
    }
    if (g.recupero_sec > 0) {
      fasi.push({ t, nome: 'Recupero' });
      if (campana) eventi.push({ t: t + 0.4, tipo: 'campana' });
      t += g.recupero_sec;
    }
  }
  return { eventi, fasi, totale: t };
}

/** Quanto dura lo strato per costruzione. */
export function durataGuida(l, ciclo, parolaSec) {
  return partituraGuida(l, ciclo, parolaSec).totale;
}

/** Un riassunto in una riga per chi compone: «20 respiri × 8,4 s = 2:48 · …». */
export function riassuntoGuida(l, ciclo) {
  const g = normalizzaGuida(l);
  const fmt = (s) => `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, '0')}`;
  const c = Math.max(0.5, Number(ciclo) || 8);
  const parti = [`${g.respiri} respiri × ${String(c.toFixed(1)).replace('.', ',')} s = ${fmt(g.respiri * c)}`];
  if (g.vuoto_sec) parti.push(`vuoto ${fmt(g.vuoto_sec)}`);
  if (g.pieno_sec) parti.push(`pieno ${fmt(g.pieno_sec)}`);
  if (g.recupero_sec) parti.push(`recupero ${fmt(g.recupero_sec)}`);
  if (g.round > 1) parti.push(`× ${g.round} round`);
  return `${parti.join(' · ')} → ${fmt(durataGuida(l, c))}`;
}

/* La campana di svolta, sintetica e deterministica: un buffer per
   contesto (WeakMap), cosi' vivo e master la calcolano una volta. */
const campane = new WeakMap();
export function campanaBuffer(ctx) {
  if (campane.has(ctx)) return campane.get(ctx);
  const sr = ctx.sampleRate, n = Math.ceil(CAMPANA_SEC * sr);
  const buf = ctx.createBuffer(1, n, sr);
  const d = buf.getChannelData(0);
  const parziali = [[528, 1, 0.9], [1056 * 1.005, 0.35, 0.45], [2112 * 1.01, 0.12, 0.25]];
  for (let i = 0; i < n; i++) {
    const t = i / sr;
    let v = 0;
    parziali.forEach(([f, a, tau]) => { v += a * Math.sin(2 * Math.PI * f * t) * Math.exp(-t / tau); });
    const att = Math.min(1, t / 0.004);
    d[i] = v * att * 0.32;
  }
  campane.set(ctx, buf);
  return buf;
}

/**
 * Appoggia la guida sul grafo dentro la finestra [da, a) del tempo
 * dello strato. `quando(u)` traduce il secondo u dello strato nel tempo
 * del contesto (dal vivo: at(s0 + u); nel blocco: u + start - cs).
 * `g` e' lo strato RISOLTO (assets.js): buffer del ciclo, `ciclo`,
 * `parole` {inspira, espira} con buffer. Restituisce i nodi creati.
 */
export function montaGuida(ctx, dest, g, { da, a, quando }) {
  const nodi = [];
  const bufferDi = (tipo) => {
    if (tipo === 'ciclo') return g.buffer;
    if (tipo === 'campana') return g.campana === false ? null : campanaBuffer(ctx);
    return g.parole && g.parole[tipo] ? g.parole[tipo] : null;
  };
  const parolaSec = g.parole && g.parole.inspira ? g.parole.inspira.duration : PAROLA_SEC_DEFAULT;
  const { eventi } = partituraGuida(g, g.ciclo, parolaSec);
  const inizioFinestra = Math.max(0, da);
  eventi.forEach((ev) => {
    const buf = bufferDi(ev.tipo);
    if (!buf) return;
    const D = buf.duration;
    const inizio = Math.max(ev.t, inizioFinestra);
    const fine = Math.min(ev.t + D, a);
    if (fine - inizio <= 0.01) return;
    const src = ctx.createBufferSource();
    src.buffer = buf;
    src.connect(dest);
    src.start(quando(inizio), Math.min(inizio - ev.t, Math.max(0, D - 0.001)));
    src.stop(quando(fine));
    nodi.push(src);
  });
  return nodi;
}
