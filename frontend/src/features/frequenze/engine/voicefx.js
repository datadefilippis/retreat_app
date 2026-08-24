/**
 * Frequenze by Aurya — effetti voce (FV2, 19/8/2026).
 *
 * La «voce da sogno» delle sessioni guidate non e' un effetto solo:
 * e' un CONTRASTO costruito (docs/FREQUENZE_VOCE_PLAN_2026-08.md) —
 * voce intimissima davanti (compressione + EQ), coda enorme e scura
 * dietro (riverbero lungo con pre-delay e taglio delle alte), eco
 * filtrata che "allontana" la parola, doubling leggero.
 *
 * Tutto WebAudio nativo: il riverbero usa una risposta all'impulso
 * SINTETICA (rumore stereo a decadimento esponenziale, scurito), zero
 * file esterni. JS puro: niente React, niente DOM.
 *
 * I preset sono il gemello di VOICE_FX nel backend
 * (models/frequency_track.py): tenerli allineati.
 */

export const VOICE_PRESETS = Object.freeze({
  natural: {
    label: 'Naturale',
    hint: 'Solo pulizia: per istruzioni e passaggi pratici.',
    reverbSec: 0.9, reverbTone: 4500, preDelay: 0.02, wet: 0.12,
    echoTime: 0, echoFeedback: 0, echoTone: 0, echoWet: 0,
    double: false,
  },
  dream: {
    label: 'Sogno',
    hint: 'La voce delle sessioni guidate: vicina e immensa insieme.',
    reverbSec: 4.5, reverbTone: 2600, preDelay: 0.09, wet: 0.45,
    echoTime: 0.42, echoFeedback: 0.32, echoTone: 2800, echoWet: 0.22,
    double: true,
  },
  temple: {
    label: 'Tempio',
    hint: 'Riverbero grande senza eco: mantra, spazi sacri.',
    reverbSec: 6.0, reverbTone: 2200, preDelay: 0.06, wet: 0.5,
    echoTime: 0, echoFeedback: 0, echoTone: 0, echoWet: 0,
    double: false,
  },
  whisper: {
    label: 'Sussurro',
    hint: 'Intimità pura, appena un alone.',
    reverbSec: 1.6, reverbTone: 3200, preDelay: 0.03, wet: 0.2,
    echoTime: 0, echoFeedback: 0, echoTone: 0, echoWet: 0,
    double: false,
  },
});

export const VOICE_FX_KEYS = Object.keys(VOICE_PRESETS);

/* Cache delle IR per (sampleRate, secondi, tono): generarle costa. */
const irCache = new Map();

/**
 * Risposta all'impulso sintetica: rumore stereo decorrelato con
 * decadimento esponenziale, scurito da un one-pole lowpass — la "stanza"
 * del riverbero, generata in pochi ms.
 */
export function makeImpulse(ctx, seconds, tone) {
  const key = `${ctx.sampleRate}:${seconds}:${tone}`;
  if (irCache.has(key)) return irCache.get(key);
  const sr = ctx.sampleRate;
  const len = Math.max(1, Math.floor(sr * seconds));
  const buf = ctx.createBuffer(2, len, sr);
  // coefficiente del one-pole per il tono richiesto
  const k = Math.exp(-2 * Math.PI * (tone / sr));
  for (let c = 0; c < 2; c++) {
    const d = buf.getChannelData(c);
    let lp = 0;
    for (let i = 0; i < len; i++) {
      const env = Math.pow(1 - i / len, 2.4);          // decadimento
      const w = (Math.random() * 2 - 1) * env;
      lp = lp * k + w * (1 - k);                        // scurisce
      d[i] = lp;
    }
  }
  irCache.set(key, buf);
  return buf;
}

/**
 * Costruisce la catena effetti per un preset.
 *
 * @param ctx     AudioContext o OfflineAudioContext
 * @param fx      chiave preset ('natural'|'dream'|'temple'|'whisper')
 * @param amount  0..1 — quanto effetto (scala wet ed eco, mai il dry)
 * @returns {{input: AudioNode, output: AudioNode}}
 */
export function buildVoiceChain(ctx, fx, amount = 0.6) {
  const p = VOICE_PRESETS[fx] || VOICE_PRESETS.natural;
  const amt = Math.max(0, Math.min(1, amount));

  const input = ctx.createGain();
  const output = ctx.createGain();

  // — pulizia comune: la voce «intimissima davanti» —
  const comp = ctx.createDynamicsCompressor();
  comp.threshold.value = -24; comp.ratio.value = 5;
  comp.attack.value = 0.003; comp.release.value = 0.25;
  const hp = ctx.createBiquadFilter();
  hp.type = 'highpass'; hp.frequency.value = 90;
  input.connect(comp); comp.connect(hp);

  // dry sempre pieno: l'effetto si AGGIUNGE, non sostituisce
  const dry = ctx.createGain(); dry.gain.value = 1;
  hp.connect(dry); dry.connect(output);

  // — riverbero: pre-delay → convolver → scurito —
  if (p.wet > 0) {
    const pre = ctx.createDelay(1); pre.delayTime.value = p.preDelay;
    const conv = ctx.createConvolver();
    conv.buffer = makeImpulse(ctx, p.reverbSec, p.reverbTone);
    const dark = ctx.createBiquadFilter();
    dark.type = 'lowpass'; dark.frequency.value = Math.max(1200, p.reverbTone * 1.6);
    const wet = ctx.createGain(); wet.gain.value = p.wet * amt;
    hp.connect(pre); pre.connect(conv); conv.connect(dark); dark.connect(wet);
    wet.connect(output);
  }

  // — eco filtrata: ogni ripetizione piu' scura e lontana —
  if (p.echoTime > 0) {
    const del = ctx.createDelay(2); del.delayTime.value = p.echoTime;
    const fb = ctx.createGain(); fb.gain.value = p.echoFeedback;
    const lp = ctx.createBiquadFilter();
    lp.type = 'lowpass'; lp.frequency.value = p.echoTone;
    const ewet = ctx.createGain(); ewet.gain.value = p.echoWet * amt;
    hp.connect(del); del.connect(lp); lp.connect(fb); fb.connect(del);
    lp.connect(ewet); ewet.connect(output);
  }

  return { input, output, preset: p };
}

/** Coda del preset in secondi: quanto lasciar suonare dopo la parola. */
export function tailSeconds(fx) {
  const p = VOICE_PRESETS[fx] || VOICE_PRESETS.natural;
  let echoTail = 0;
  if (p.echoTime > 0 && p.echoFeedback > 0) {
    // tempo perche' il feedback scenda sotto -60 dB
    echoTail = p.echoTime * Math.ceil(-3 / Math.log10(p.echoFeedback));
  }
  return Math.min(10, Math.max(p.reverbSec, echoTail) + 0.5);
}

/**
 * Collega un clip voce (buffer) alla catena: sorgente principale + il
 * doubling «angelico» se il preset lo chiede. Ritorna le sorgenti da
 * avviare/fermare (start/stop restano al chiamante, che conosce i tempi).
 */
export function connectVoiceSources(ctx, buffer, chain) {
  const sources = [];
  const main = ctx.createBufferSource();
  main.buffer = buffer;
  main.connect(chain.input);
  sources.push(main);
  if (chain.preset.double) {
    const dup = ctx.createBufferSource();
    dup.buffer = buffer;
    if (dup.detune) dup.detune.value = 8;             // +8 cents
    const lag = ctx.createDelay(0.1); lag.delayTime.value = 0.015;
    const g = ctx.createGain(); g.gain.value = 0.35;
    dup.connect(lag); lag.connect(g);
    if (ctx.createStereoPanner) {
      const pan = ctx.createStereoPanner(); pan.pan.value = 0.35;
      g.connect(pan); pan.connect(chain.input);
    } else {
      g.connect(chain.input);
    }
    sources.push(dup);
  }
  return sources;
}

/* FV5 — pulizia della registrazione. Il FILE resta l'originale: questa
 * e' matematica deterministica applicata al buffer decodificato, quindi
 * suona identica in anteprima, export e player — e si puo' migliorare
 * domani senza riprocessare nulla.
 *
 * Catena: trim dei silenzi in testa/coda (+150ms di respiro) → gate
 * leggero anti-fruscio nelle pause (soglia RELATIVA al fondo della
 * registrazione: il respiro voluto, piu' forte del fondo, sopravvive)
 * → declick 20ms ai bordi → normalizzazione di picco a -1 dB. */
/* VP (24/8) — I TRE MODI DELLA PULIZIA (founder: «ogni registrazione
   inizia bassa e poi il volume si alza — si puo' regolare?»).
   Era il GATE: una voce che attacca dolcemente sta sotto soglia per
   qualche decina di ms, usciva a -18 dB e risaliva a scalini. Ora:
     naturale — volume pareggiato + silenzi ai bordi. NIENTE gate:
                 l'attacco resta com'e' (default dei take nuovi);
     pulita    — anche il gate sulle pause, per stanze rumorose
                 (comportamento storico, addolcito);
     grezza    — la registrazione cosi' com'e'.
   La cache tiene conto del modo: lo stesso buffer con due modi sono
   due suoni diversi. */
/* DUE MODI, non tre (24/8 — founder: «grezza, pulita e naturale
   hanno ancora ragione di esistere?»). Misurato: su una
   registrazione gia' pulita «naturale» e «pulita» davano lo STESSO
   identico risultato (-19,1 dB entrambe) — una scelta che non
   cambia niente e' una scelta che confonde. Ora il rumore lo
   riconosce il sistema: la sottrazione si accende SOLO se c'e'
   davvero qualcosa da togliere. All'autore resta la sola domanda
   che sa rispondere: «sistemala tu» oppure «non toccarla». */
export const CLEAN_MODES = Object.freeze({
  auto: { label: 'Sistemata', hint: 'Bordi, volume e — se serve — il rumore di fondo. Il resto non si tocca.' },
  grezza: { label: 'Grezza', hint: 'Nessun ritocco: la registrazione com\u2019e\u2019.' },
});
/* i nomi di ieri restano leggibili: chi ha gia' scelto non si vede
   cambiare il suono sotto i piedi (naturale/pulita → auto) */
export const CLEAN_ALIAS = Object.freeze({
  naturale: 'auto', pulita: 'auto', auto: 'auto', grezza: 'grezza',
});

/* ══ LA SOTTRAZIONE SPETTRALE (24/8/2026) ═══════════════════════════
 * Founder: «perche' non si puo' togliere il rumore di fondo senza
 * abbassare i decibel all'inizio?». Perche' il GATE guarda solo il
 * VOLUME: sotto soglia abbassa, e per lui «fruscio» e «voce che
 * attacca piano» sono la stessa cosa. Questo invece guarda il COLORE:
 * impara l'impronta in frequenza del rumore dai frame piu' quieti e
 * la sottrae da TUTTI i frame. Cosi' il fruscio sparisce anche
 * mentre parli, e l'attacco resta intero — non si abbassa niente, si
 * toglie solo cio' che e' rumore.
 *
 * STFT con finestra di Hann, salto 1/4 (overlap-add che ricostruisce
 * esatto), sottrazione con pavimento: si toglie `forza` volte il
 * rumore stimato, ma non si scende mai sotto `pavimento` volte il
 * segnale — il pavimento e' cio' che evita il «gorgoglio» metallico
 * dei riduttori troppo aggressivi.
 */
const FFT_N = 1024;                     // ~21ms a 48k: la voce ci sta
const HOP = FFT_N / 4;

/* FFT radix-2 in loco (Cooley-Tukey): niente librerie, ~40 righe.
   re/im sono Float32Array di lunghezza n (potenza di 2). */
function fft(re, im, inversa) {
  const n = re.length;
  for (let i = 1, j = 0; i < n; i++) {          // bit reversal
    let bit = n >> 1;
    for (; j & bit; bit >>= 1) j ^= bit;
    j ^= bit;
    if (i < j) {
      let t = re[i]; re[i] = re[j]; re[j] = t;
      t = im[i]; im[i] = im[j]; im[j] = t;
    }
  }
  for (let len = 2; len <= n; len <<= 1) {
    const ang = (inversa ? 2 : -2) * Math.PI / len;
    const wr = Math.cos(ang), wi = Math.sin(ang);
    for (let i = 0; i < n; i += len) {
      let cr = 1, ci = 0;
      for (let k = 0; k < len / 2; k++) {
        const ur = re[i + k], ui = im[i + k];
        const vr = re[i + k + len / 2] * cr - im[i + k + len / 2] * ci;
        const vi = re[i + k + len / 2] * ci + im[i + k + len / 2] * cr;
        re[i + k] = ur + vr; im[i + k] = ui + vi;
        re[i + k + len / 2] = ur - vr; im[i + k + len / 2] = ui - vi;
        const nr = cr * wr - ci * wi;
        ci = cr * wi + ci * wr; cr = nr;
      }
    }
  }
  if (inversa) for (let i = 0; i < n; i++) { re[i] /= n; im[i] /= n; }
}

/**
 * Toglie il rumore di fondo di un canale senza toccare le dinamiche.
 * @param canale Float32Array
 * @param forza  quante volte il rumore stimato si sottrae (1.5 = deciso)
 * @param pavimento quanto del segnale resta comunque (0.1 = -20dB)
 */
function sottraiRumoreCanale(canale, forza = 1.5, pavimento = 0.1) {
  const n = canale.length;
  if (n < FFT_N * 4) return canale;             // troppo corto: si lascia stare
  const finestra = new Float32Array(FFT_N);
  for (let i = 0; i < FFT_N; i++) {
    finestra[i] = 0.5 - 0.5 * Math.cos((2 * Math.PI * i) / FFT_N);
  }
  const nFrame = Math.floor((n - FFT_N) / HOP) + 1;
  const bins = FFT_N / 2 + 1;
  const modulo = new Float32Array(nFrame * bins);
  const fase = new Float32Array(nFrame * bins);
  const energia = new Float32Array(nFrame);
  const re = new Float32Array(FFT_N), im = new Float32Array(FFT_N);

  for (let f = 0; f < nFrame; f++) {            // ANALISI
    const off = f * HOP;
    for (let i = 0; i < FFT_N; i++) { re[i] = canale[off + i] * finestra[i]; im[i] = 0; }
    fft(re, im, false);
    let en = 0;
    for (let k = 0; k < bins; k++) {
      const m = Math.hypot(re[k], im[k]);
      modulo[f * bins + k] = m;
      fase[f * bins + k] = Math.atan2(im[k], re[k]);
      en += m;
    }
    energia[f] = en;
  }

  /* IL PROFILO DEL RUMORE: la mediana dei frame piu' quieti (il 15%
     inferiore). La mediana, non la media: un colpo secco in mezzo al
     silenzio non deve insegnare al filtro che quello e' rumore. */
  const ordine = Array.from(energia.keys()).sort((a, b) => energia[a] - energia[b]);
  const quanti = Math.max(3, Math.floor(nFrame * 0.15));
  const quieti = ordine.slice(0, quanti);
  const profilo = new Float32Array(bins);
  const colonna = new Float32Array(quanti);
  for (let k = 0; k < bins; k++) {
    for (let i = 0; i < quanti; i++) colonna[i] = modulo[quieti[i] * bins + k];
    const ord = Array.prototype.slice.call(colonna).sort((a, b) => a - b);
    profilo[k] = ord[Math.floor(quanti / 2)];
  }

  const out = new Float32Array(n);
  const pesi = new Float32Array(n);
  for (let f = 0; f < nFrame; f++) {            // SINTESI
    const off = f * HOP;
    for (let k = 0; k < bins; k++) {
      const m = modulo[f * bins + k];
      const pulito = Math.max(m - forza * profilo[k], pavimento * m);
      const p = fase[f * bins + k];
      re[k] = pulito * Math.cos(p);
      im[k] = pulito * Math.sin(p);
      if (k > 0 && k < FFT_N / 2) {             // simmetria hermitiana
        re[FFT_N - k] = re[k];
        im[FFT_N - k] = -im[k];
      }
    }
    fft(re, im, true);
    for (let i = 0; i < FFT_N; i++) {
      out[off + i] += re[i] * finestra[i];
      pesi[off + i] += finestra[i] * finestra[i];
    }
  }
  for (let i = 0; i < n; i++) if (pesi[i] > 1e-6) out[i] /= pesi[i];
  // le code fuori dalle finestre restano com'erano
  for (let i = 0; i < FFT_N; i++) out[i] = out[i] || canale[i];
  for (let i = n - FFT_N; i < n; i++) out[i] = out[i] || canale[i];
  return out;
}

/* l'ultima pulizia, per poterla RACCONTARE nella UI: «rumore tolto»
   oppure «era gia' pulita». Chi registra deve sapere cosa e'
   successo, non fidarsi. */
export let ultimaPulizia = { rumoreTolto: false, rapporto: 0 };

const cleanCache = new WeakMap();
export function cleanVoiceBuffer(ctx, buffer, modoChiesto = 'auto') {
  const mode = CLEAN_ALIAS[modoChiesto] || 'auto';
  if (mode === 'grezza') return buffer;
  const perBuffer = cleanCache.get(buffer);
  if (perBuffer && perBuffer[mode]) return perBuffer[mode];
  const sr = buffer.sampleRate, ch = buffer.numberOfChannels, n = buffer.length;
  const data = [];
  for (let c = 0; c < ch; c++) data.push(buffer.getChannelData(c));
  const win = Math.max(1, Math.round(sr * 0.01));          // finestre da 10ms
  const nw = Math.ceil(n / win);
  const rms = new Float32Array(nw);
  for (let w = 0; w < nw; w++) {
    let s = 0; const a = w * win, b = Math.min(n, a + win);
    for (let i = a; i < b; i++) { const v = data[0][i]; s += v * v; }
    rms[w] = Math.sqrt(s / Math.max(1, b - a));
  }
  const sorted = Array.from(rms).sort((x, y) => x - y);
  const floor = sorted[Math.floor(nw * 0.1)] || 0;         // fondo: 10° percentile
  const speechThr = Math.max(floor * 3.16, 0.004);         // +10dB, mai sotto -48dBFS
  let first = -1, last = -1;
  for (let w = 0; w < nw; w++) {
    if (rms[w] >= speechThr) { if (first < 0) first = w; last = w; }
  }
  if (first < 0) { ricorda(buffer, mode, buffer); return buffer; } // solo silenzio
  /* il respiro prima della prima parola: 60ms invece di 150. Il pad
     lungo lasciava mezzo secondo di rampa in testa anche quando la
     voce partiva subito (misurato su «Spezzone 3»: -41 dB nei primi
     0,5s contro -19 di regime). 60ms bastano a non tagliare l'attacco
     della consonante, e la voce entra quando entra davvero. */
  const pad = Math.round(0.06 * sr);
  const start = Math.max(0, first * win - pad);
  const end = Math.min(n, (last + 1) * win + pad);
  /* NIENTE PIU' GATE (24/8, founder: «perche' per togliere il rumore
     bisogna abbassare l'inizio?»). Il gate guardava il VOLUME e non
     sapeva distinguere il fruscio da una voce che attacca piano: per
     questo mangiava gli attacchi. In «pulita» ora lavora la
     SOTTRAZIONE SPETTRALE, piu' sotto: guarda il COLORE del rumore e
     lo toglie da tutto, anche mentre parli, senza toccare le
     dinamiche. I gains restano a 1: la struttura resta (trim,
     declick, normalizzazione), cambia CHI pulisce. */
  const gains = new Float32Array(nw).fill(1);
  const len = end - start;
  const out = ctx.createBuffer(ch, len, sr);
  let peak = 0;
  for (let c = 0; c < ch; c++) {
    const src = data[c], dst = out.getChannelData(c);
    for (let i = 0; i < len; i++) {
      dst[i] = src[start + i] * gains[Math.floor((start + i) / win)];
      const av = Math.abs(dst[i]); if (av > peak) peak = av;
    }
    const f = Math.min(Math.round(0.02 * sr), Math.floor(len / 4)); // declick
    for (let i = 0; i < f; i++) { const k = i / f; dst[i] *= k; dst[len - 1 - i] *= k; }
  }
  /* LA SOTTRAZIONE SI ACCENDE DA SOLA. Il rumore si misura: fondo
     (10° percentile) contro voce (mediana dei frame parlati). Se il
     fondo sta piu' di 40 dB sotto la voce, la stanza era gia' quieta
     e togliere «rumore» significherebbe solo togliere aria. Sopra
     quella soglia si pulisce: e' una misura, non un'opinione da
     chiedere a chi registra.
     La sottrazione lavora sul TAGLIATO (dopo trim e declick) e prima
     della normalizzazione: cosi' il livello finale tiene conto del
     rumore gia' tolto, invece di alzarlo insieme alla voce. */
  const parlati = Array.from(rms).filter((v) => v >= speechThr).sort((a, b) => a - b);
  const voceTipica = parlati.length ? parlati[Math.floor(parlati.length / 2)] : 0;
  const rapporto = voceTipica > 0 ? floor / voceTipica : 0;
  const serveRipulire = rapporto > 0.01;     // fondo entro 40 dB dalla voce
  if (serveRipulire) {
    for (let c = 0; c < ch; c++) {
      const dst = out.getChannelData(c);
      const pulito = sottraiRumoreCanale(dst, 1.5, 0.1);
      if (pulito !== dst) dst.set(pulito);
    }
    peak = 0;
    for (let c = 0; c < ch; c++) {
      const dst = out.getChannelData(c);
      for (let i = 0; i < len; i++) { const av = Math.abs(dst[i]); if (av > peak) peak = av; }
    }
  }
  ultimaPulizia = { rumoreTolto: serveRipulire, rapporto };
  if (peak > 0.001) {
    const k = Math.min(0.9 / peak, 8);                     // alza al massimo x8
    if (k < 0.999 || k > 1.05) {
      for (let c = 0; c < ch; c++) {
        const dst = out.getChannelData(c);
        for (let i = 0; i < len; i++) dst[i] *= k;
      }
    }
  }
  ricorda(buffer, mode, out);
  return out;
}

/* la cache e' per (buffer, modo): cambiare modo nel leggio deve
   ricalcolare, non riesumare il suono di prima */
function ricorda(buffer, mode, out) {
  const per = cleanCache.get(buffer) || {};
  per[mode] = out;
  cleanCache.set(buffer, per);
}

/**
 * Finestre di ducking: dove c'e' voce, le basi respirano piano.
 * Ritorna un moltiplicatore di volume in funzione del tempo assoluto.
 */
export function duckEnvelope(voiceLayers, depth = 0.4, ramp = 1.0) {
  const wins = (voiceLayers || [])
    .filter((l) => !l.mute)
    .map((l) => [l.start, l.end])
    .sort((a, b) => a[0] - b[0]);
  return (t) => {
    let m = 1;
    for (const [s, e] of wins) {
      if (t < s - ramp || t > e + ramp) continue;
      let f = 1;
      if (t < s) f = (t - (s - ramp)) / ramp;           // scende
      else if (t > e) f = 1 - (t - e) / ramp;           // risale
      m = Math.min(m, 1 - depth * Math.max(0, Math.min(1, f)));
    }
    return m;
  };
}
