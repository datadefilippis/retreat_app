/**
 * IL MOTORE DEL LAB (25/8/2026) — React-free, come prototipo.js.
 *
 * Un solo grafo per tutto il Laboratorio:
 *
 *   generatore → master ─┬→ analyser (osservatore)
 *                        └→ ponte.nodo → <audio> → altoparlante
 *
 * Tre regole ereditate dal resto del motore, pagate in produzione:
 *
 * 1. Il suono esce SOLO dal ponte (engine/ponte.js): su iOS il grafo
 *    collegato a ctx.destination e' suono «di contorno», azzerabile
 *    dal silenziatore. MAI connect(ctx.destination) in questo file.
 * 2. L'analisi e' un ospite: guarda, non trasporta (visual/analisi.js).
 *    `analisi.sorgente(nodo)` accetta QUALSIASI nodo — oggi il
 *    generatore, domani un MediaStreamSource dal microfono: e' la
 *    presa per tutto il futuro del Lab, e i moduli che leggono
 *    l'analyser non sapranno mai da dove viene il segnale.
 * 3. Nessun parametro salta: ampiezza e frequenza si muovono con
 *    rampe (DK = 12 ms, la costante di casa), il cambio di forma o di
 *    fase e' un CROSSFADE fra due oscillatori — cambiare `type` a
 *    caldo produce un click.
 *
 * LA FASE. L'OscillatorNode nativo non ce l'ha: si ottiene con
 * setPeriodicWave. La serie di Fourier della forma, con ogni armonica
 * ruotata di k·fase, da' esattamente sin(k(ωt+φ)) — e siccome la
 * PeriodicWave e' band-limitata dal browser, e' pure anti-aliasata.
 * A fase 0 si usano i tipi nativi (purezza massima, zero calcoli).
 */
import { creaPonte } from '../engine/ponte';

const DK = 0.012;           // declick: nessun salto piu' rapido di 12 ms
const XFADE = 0.024;        // crossfade cambio forma/fase
const ARMONICHE = 512;      // fino a ~20 kHz gia' da un fondamentale di 40 Hz

export const FORME = ['sine', 'square', 'triangle', 'sawtooth'];

/* Coefficiente b_k della serie di Fourier (seno) della forma.
   Le stesse serie delle forme native — la normalizzazione del
   browser riporta il picco a 1, quindi il volume non cambia
   passando da nativa a PeriodicWave. */
function coeff(forma, k) {
  switch (forma) {
    case 'sine': return k === 1 ? 1 : 0;
    case 'square': return k % 2 ? 4 / (k * Math.PI) : 0;
    case 'sawtooth': return (2 / (k * Math.PI)) * (k % 2 ? 1 : -1);
    case 'triangle':
      return k % 2 ? (8 / (Math.PI * Math.PI * k * k)) * ((k % 4 === 1) ? 1 : -1) : 0;
    default: return 0;
  }
}

/* PeriodicWave della forma ruotata di `fase` radianti (sul
   fondamentale): real[k] = b_k·sin(k·fase), imag[k] = b_k·cos(k·fase). */
function ondaConFase(ctx, forma, fase) {
  const real = new Float32Array(ARMONICHE + 1);
  const imag = new Float32Array(ARMONICHE + 1);
  for (let k = 1; k <= ARMONICHE; k++) {
    const b = coeff(forma, k);
    if (!b) continue;
    real[k] = b * Math.sin(k * fase);
    imag[k] = b * Math.cos(k * fase);
  }
  return ctx.createPeriodicWave(real, imag);
}

export function creaLaboratorio(ctx) {
  if (ctx._fqzLab) return ctx._fqzLab;
  const ponte = creaPonte(ctx);
  const nyquist = ctx.sampleRate / 2;          // il limite VERO, non 20 kHz
  const clampF = (f) => Math.min(Math.max(+f || 1, 1), nyquist * 0.995);

  /* ── il rubinetto d'analisi ─────────────────────────────────── */
  const analyser = ctx.createAnalyser();
  analyser.fftSize = 8192;                     // ~5.4 Hz/bin a 44.1k
  analyser.smoothingTimeConstant = 0.55;

  /* ── l'uscita del generatore ────────────────────────────────── */
  const master = ctx.createGain();
  master.gain.value = 0;
  master.connect(analyser);                    // osserva
  master.connect(ponte.nodo);                  // trasporta — MAI ctx.destination

  let osservato = master;                      // cio' che l'analyser guarda ora

  const stato = { forma: 'sine', freq: 440, amp: 0.25, fase: 0, attivo: false };
  let voce = null;                             // { osc, gain } vivo

  /* LA CORSA (STEP 6, 26/8/2026) — lo sweep di frequenza.
   *
   * Non e' un timer che ritocca la frequenza sessanta volte al
   * secondo: e' UNA rampa esponenziale sull'AudioParam, calcolata dal
   * motore audio campione per campione. Continua a scheda nascosta e
   * a schermo spento (dove ogni orologio JavaScript dorme), la durata
   * e' esatta e la curva e' esponenziale per natura — cioe' diritta
   * all'orecchio, che le frequenze le sente in ottave.
   *
   * Qui si tiene solo il PROMEMORIA della rampa (da, a, quando, per
   * quanto): serve a dire che frequenza suona ADESSO senza inventare
   * una seconda verita'. La formula sotto e' la stessa che il browser
   * usa per la rampa — v(t) = da · (a/da)^u — quindi il numero
   * scritto e il suono non possono divergere: sono la stessa cosa
   * letta due volte. */
  let corsa = null;

  const freqOra = () => {
    if (!corsa) return stato.freq;
    const u = (ctx.currentTime - corsa.t0) / corsa.durata;
    if (u >= 1) { const fine = corsa.a; corsa = null; return fine; }
    if (u <= 0) return corsa.da;
    return corsa.da * Math.pow(corsa.a / corsa.da, u);
  };

  /* onde con fase gia' calcolate: (forma, fase arrotondata) → wave */
  const cache = new Map();
  const onda = (forma, fase) => {
    const chiave = forma + '@' + Math.round(fase * 1000);
    if (!cache.has(chiave)) cache.set(chiave, ondaConFase(ctx, forma, fase));
    return cache.get(chiave);
  };

  const vesti = (osc) => {
    if (stato.fase === 0) osc.type = stato.forma;
    else osc.setPeriodicWave(onda(stato.forma, stato.fase));
  };

  const nuovaVoce = (guadagno) => {
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    vesti(osc);
    /* la voce nuova nasce DOVE SIAMO, non alla meta: se una corsa e'
       in atto (cambio di forma a meta' sweep) eredita il pezzo di
       rampa che resta, altrimenti si perderebbe lo sweep. */
    const ora = freqOra();
    osc.frequency.value = ora;
    if (corsa) {
      const t0 = ctx.currentTime;
      const resta = corsa.t0 + corsa.durata - t0;
      if (resta > 0) {
        osc.frequency.setValueAtTime(ora, t0);
        osc.frequency.exponentialRampToValueAtTime(corsa.a, t0 + resta);
      }
    }
    gain.gain.value = guadagno;
    osc.connect(gain); gain.connect(master);
    osc.start();
    return { osc, gain };
  };

  /* cambio forma o fase a caldo: la voce vecchia scende, la nuova
     sale, si incrociano in XFADE — l'orecchio sente una sola nota */
  const rimpiazza = () => {
    if (!voce) return;
    const via = voce, t = ctx.currentTime;
    voce = nuovaVoce(0);
    voce.gain.gain.linearRampToValueAtTime(1, t + XFADE);
    via.gain.gain.setValueAtTime(1, t);
    via.gain.gain.linearRampToValueAtTime(0, t + XFADE);
    via.osc.stop(t + XFADE + 0.05);
    via.osc.onended = () => { try { via.gain.disconnect(); } catch { /* gia' */ } };
  };

  const lab = {
    ctx,
    ponte,
    limiti: { min: 1, max: nyquist },

    generatore: {
      /* `freq` e' la frequenza che suona ADESSO (durante una corsa si
         muove); `meta` e' dove sta andando; `corsa` e' il promemoria
         della rampa, o null se non c'e'. */
      stato: () => ({ ...stato, freq: freqOra(), meta: stato.freq,
                      corsa: corsa ? { ...corsa } : null }),

      imposta(patch = {}) {
        const t = ctx.currentTime;
        if (patch.freq !== undefined) {
          /* CON `secondi` e' una corsa, SENZA e' il gesto di sempre —
             il comportamento vecchio non cambia di una virgola. */
          const secondi = Math.max(0, +patch.secondi || 0);
          const partenza = freqOra();          // dove siamo davvero ora
          stato.freq = clampF(patch.freq);
          if (voce) {
            const p = voce.osc.frequency;
            /* cancellare basta a interrompere: non ci sono timer da
               spegnere ne' animazioni da rincorrere, perche' non ce
               n'e' mai stato uno */
            p.cancelScheduledValues(t);
            if (secondi > 0) {
              p.setValueAtTime(partenza, t);
              p.exponentialRampToValueAtTime(stato.freq, t + secondi);
              corsa = { da: partenza, a: stato.freq, t0: t, durata: secondi };
            } else {
              /* setTargetAtTime: scivola senza zipper, qualunque sia
                 il passo del controllo */
              p.setTargetAtTime(stato.freq, t, DK / 3);
              corsa = null;
            }
          } else corsa = null;                 // a motore spento non si corre
        }
        if (patch.amp !== undefined) {
          stato.amp = Math.min(Math.max(+patch.amp || 0, 0), 1);
          if (stato.attivo) {
            master.gain.cancelScheduledValues(t);
            master.gain.setTargetAtTime(stato.amp, t, DK / 3);
          }
        }
        let rifare = false;
        if (patch.forma !== undefined && FORME.includes(patch.forma)
            && patch.forma !== stato.forma) { stato.forma = patch.forma; rifare = true; }
        if (patch.fase !== undefined) {
          const f = +patch.fase || 0;
          if (f !== stato.fase) { stato.fase = f; rifare = true; }
        }
        if (rifare && voce) rimpiazza();
      },

      /* da chiamare DENTRO il gesto (clic/tocco): il ponte e il
         resume del contesto vogliono l'attivazione dell'utente */
      async avvia() {
        if (stato.attivo) return;
        try { await ctx.resume(); } catch { /* gia' attivo */ }
        await ponte.avvia();
        voce = nuovaVoce(1);
        const t = ctx.currentTime;
        master.gain.cancelScheduledValues(t);
        master.gain.setValueAtTime(0, t);
        master.gain.linearRampToValueAtTime(stato.amp, t + DK);
        stato.attivo = true;
      },

      ferma() {
        if (!stato.attivo) return;
        corsa = null;                          // spegnere ferma anche la corsa
        const t = ctx.currentTime;
        master.gain.cancelScheduledValues(t);
        master.gain.setValueAtTime(master.gain.value, t);
        master.gain.linearRampToValueAtTime(0, t + DK);
        if (voce) {
          voce.osc.stop(t + DK + 0.05);
          const via = voce;
          via.osc.onended = () => { try { via.gain.disconnect(); } catch { /* gia' */ } };
          voce = null;
        }
        stato.attivo = false;
        /* il rilascio del ponte: su iOS un <audio> lasciato in play su
           uno stream muto ripete l'ultimo buffer in loop (22/8) */
        ponte.rilascia();
      },
    },

    analisi: {
      analyser,
      tempo(buf) { analyser.getFloatTimeDomainData(buf); return buf; },
      spettro(buf) { analyser.getFloatFrequencyData(buf); return buf; },
      /* la presa del futuro: cambia CIO' CHE si osserva, non chi
         disegna. Il microfono sara' `sorgente(ctx.createMediaStreamSource(...))`
         e oscilloscopio/spettro non se ne accorgeranno. */
      sorgente(nodo) {
        try { osservato.disconnect(analyser); } catch { /* mai collegato */ }
        (nodo || master).connect(analyser);
        osservato = nodo || master;
      },
      hzPerBin: ctx.sampleRate / analyser.fftSize,
    },

    spegni() {
      lab.generatore.ferma();
      try { master.disconnect(); } catch { /* niente */ }
      delete ctx._fqzLab;
    },
  };

  ctx._fqzLab = lab;
  /* banco di prova: diagnosi dalla console (e dai collaudi) senza
     toccare React. Sola lettura, nessun segreto. */
  try { window.__fqzLab = lab; } catch { /* SSR/test */ }
  return lab;
}
