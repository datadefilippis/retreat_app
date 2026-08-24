/**
 * VS3 (24/8/2026) — LO SPETTRO DIPINTO: la scena danza sulla RICETTA.
 *
 * Col MASTER il suono di una meditazione esce da un `<audio>` puro, e
 * deve restare puro: portarlo dentro WebAudio lo rimetterebbe sotto il
 * tasto silenzioso e lo ucciderebbe a schermo bloccato (la lezione
 * AT3). Per il visual si spilla una COPIA del flusso
 * (`presaAnalisi`) — ma `HTMLMediaElement.captureStream` **Safari non
 * ce l'ha**: sul telefono del founder, dov'è nato «Guarda il suono»,
 * quella strada non esiste.
 *
 * Qui si prende l'altra: non c'è un segnale da guardare, ma c'è **la
 * ricetta**, che della composizione è la verità. Sa quali livelli
 * suonano adesso, con che guadagno, a che portante, con che battito.
 * Si dipinge quindi uno spettro plausibile e lo si consegna al motore
 * visivo attraverso **la stessa superficie di un AnalyserNode**
 * (`fftSize`, `frequencyBinCount`, `getByteFrequencyData`,
 * `getByteTimeDomainData`): il prototipo non può accorgersi della
 * differenza, e nessuna riga del motore va toccata.
 *
 * Onestà su cosa è: la struttura è ESATTA (i livelli entrano ed escono
 * quando devono, le dissolvenze sono quelle, portante e battito dei
 * livelli neuro vengono dalla ricetta). I transienti veri di una base
 * registrata e le sillabe della voce no: quelli stanno nell'audio, e
 * l'audio qui non si apre — erano loro il gigabyte di RAM che abbiamo
 * tolto. Non si finge un ascolto: si suona la partitura per gli occhi.
 */

import { creaLettore } from './analisi';

const FFT = 2048;
/* la rampa ai bordi di un livello: il motore audio ha il suo declick
   da 12 ms, ma un occhio che vede comparire un livello di colpo legge
   uno scatto — un secondo e mezzo è il tempo in cui una cosa "entra" */
const RAMPA = 1.5;
/* la finestra in dB dell'analyser vero (analisi.js): dipingere fuori
   da questa scala darebbe una scena sempre accesa o sempre spenta */
const DB_MIN = -90, DB_MAX = -10;

const clamp = (x, a, b) => (x < a ? a : x > b ? b : x);

/* una fase stabile per livello: senza, tutti i respiri lenti
   partirebbero insieme e la scena pomperebbe invece di vivere */
function fase(seme) {
  let h = 2166136261;
  for (let i = 0; i < seme.length; i++) {
    h ^= seme.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return ((h >>> 0) % 1000) / 1000 * Math.PI * 2;
}

/* quanto pesa un livello adesso: 0 fuori dai suoi estremi */
function inviluppo(l, t) {
  if (t < l.start || t > l.end) return 0;
  const su = Math.min(1, (t - l.start) / RAMPA);
  const giu = Math.min(1, (l.end - t) / RAMPA);
  return Math.max(0, Math.min(su, giu)) * (l.gain != null ? l.gain : 0.5);
}

/* il battito adesso, con la stessa geometria del motore audio: le
   curve monotone corrono da f0 a f1, la marea va e TORNA */
function battito(l, t) {
  const f0 = l.f0 != null ? l.f0 : 8, f1 = l.f1 != null ? l.f1 : f0;
  const durata = Math.max(0.001, l.end - l.start);
  const p = clamp((t - l.start) / durata, 0, 1);
  if (l.curve === 'wave') {
    const per = Math.max(2, l.period || 40);
    const u = 0.5 - 0.5 * Math.cos((2 * Math.PI * (t - l.start)) / per);
    return f0 + (f1 - f0) * u;
  }
  if (l.curve === 'exp') return f0 * Math.pow(Math.max(0.01, f1 / f0), p);
  if (l.curve === 'steps') {
    const n = 6;
    return f0 + (f1 - f0) * (Math.floor(p * n) / (n - 1));
  }
  return f0 + (f1 - f0) * p;
}

/* una gobba attorno a una frequenza: è così che un tono si presenta a
   una FFT, non come una riga sola */
function gobba(amp, hzPerBin, hz, altezza, larghezzaHz) {
  if (!(hz > 0) || altezza <= 0) return;
  const c = hz / hzPerBin;
  const s = Math.max(1, larghezzaHz / hzPerBin);
  const da = Math.max(0, Math.floor(c - 3 * s));
  const a = Math.min(amp.length - 1, Math.ceil(c + 3 * s));
  for (let i = da; i <= a; i++) {
    const d = (i - c) / s;
    amp[i] += altezza * Math.exp(-0.5 * d * d);
  }
}

/* un letto largo che scende con la frequenza: il profilo di quasi
   tutto ciò che è registrato (più corpo in basso, aria in alto) */
function letto(amp, hzPerBin, altezza, pendenza, hzMax) {
  for (let i = 1; i < amp.length; i++) {
    const hz = i * hzPerBin;
    if (hz > hzMax) break;
    amp[i] += altezza / Math.pow(Math.max(0.3, hz / 100), pendenza);
  }
}

/* Il nome della base è l'unico indizio di timbro che la ricetta porta
   (la categoria vive in libreria, e qui la libreria non si apre). Se
   il nome parla, il colore lo segue; se tace, un letto onesto. */
const INDIZI = [
  [/(campan|bowl|bell|gong|chime|handpan|kalimba|koshi)/i, { pend: 0.35, hzMax: 12000, brillio: 0.55 }],
  [/(pioggia|rain|mare|ocean|wave|onde|acqua|water|river|vento|wind|forest|bosco|bird|uccell|fuoco|fire)/i,
    { pend: 0.25, hzMax: 16000, brillio: 0.40 }],
  [/(drone|bordone|hum|deep|sub|space)/i, { pend: 1.15, hzMax: 3000, brillio: 0.05 }],
  [/(drum|tamburo|percuss|tribal|beat|ritm|taiko|shaman)/i, { pend: 1.00, hzMax: 9000, brillio: 0.25 }],
  [/(chant|mantra|choir|coro|voce|vocal|om\b)/i, { pend: 0.70, hzMax: 6000, brillio: 0.18 }],
  [/(piano|guitar|chitarr|flute|flaut|harp|arpa|strings|archi)/i, { pend: 0.60, hzMax: 11000, brillio: 0.35 }],
];
const LETTO_MUTO = { pend: 0.80, hzMax: 8000, brillio: 0.20 };

function timbroDalNome(nome) {
  for (const [re, prof] of INDIZI) if (re.test(nome || '')) return prof;
  return LETTO_MUTO;
}

function dipingiNeuro(amp, l, t, hzPerBin, ph) {
  const g = inviluppo(l, t);
  if (g <= 0) return;
  const b = battito(l, t);
  const c = clamp(l.carrier || 180, 20, 2000);
  const largo = Math.max(8, c * 0.03);

  if (l.method === 'noise' || l.method === 'breath') {
    /* il soffio: un letto colorato che respira al ritmo del livello.
       Il respiro guidato è ASIMMETRICO (inspiro più corto), ed è
       proprio quello che lo distingue da un'onda del mare. */
    const pend = l.method === 'breath' ? 0.55
      : l.color === 'brown' ? 1.10 : l.color === 'white' ? 0.10 : 0.55;
    let ciclo;
    if (l.method === 'breath') {
      const inn = l.inhale || 0.35, exh = l.exhale || 0.50;
      const u = ((t - l.start) * b) % 1;
      ciclo = u < inn ? u / inn
        : u < inn + exh ? 1 - (u - inn) / exh
          : 0;
    } else {
      ciclo = 0.5 + 0.5 * Math.sin(2 * Math.PI * b * t + ph);
    }
    letto(amp, hzPerBin, 0.030 * g * (0.35 + 0.65 * ciclo), pend,
      l.method === 'breath' ? 6000 : 14000);
    return;
  }

  /* i toni: la portante pulsa al battito. L'isocrono stacca (è la sua
     natura: acceso/spento), gli altri ondeggiano. */
  const onda = Math.sin(2 * Math.PI * b * t + ph);
  const puls = l.method === 'iso' ? (onda > 0 ? 1 : 0.12)
    : l.method === 'bil' ? 0.55 + 0.45 * Math.abs(onda)
      : 0.72 + 0.28 * onda;
  const a0 = 0.50 * g * puls;

  if (l.method === 'drone') {
    /* l'accordo naturale: fondamentale, terza 5/4, quinta 3/2 */
    gobba(amp, hzPerBin, c, a0, largo);
    gobba(amp, hzPerBin, c * 1.25, a0 * 0.55, largo * 1.25);
    gobba(amp, hzPerBin, c * 1.5, a0 * 0.65, largo * 1.5);
    gobba(amp, hzPerBin, c * 2, a0 * 0.30, largo * 2);
    return;
  }
  if (l.method === 'shepard') {
    /* la discesa infinita: le ottave scivolano e si riaffacciano in
       alto mentre svaniscono in basso */
    const giro = (t * (l.f0 || 1)) / 60;
    for (let k = -2; k <= 2; k++) {
      const u = ((giro + k / 5) % 1 + 1) % 1;
      const hz = c * Math.pow(2, 2 - u * 4);
      const peso = Math.sin(Math.PI * u);
      gobba(amp, hzPerBin, hz, a0 * 0.5 * peso * peso, Math.max(8, hz * 0.03));
    }
    return;
  }
  gobba(amp, hzPerBin, c, a0, largo);
  if (l.timbre !== 'pure') {
    gobba(amp, hzPerBin, c * 2, a0 * 0.42, largo * 2);
    gobba(amp, hzPerBin, c * 3, a0 * 0.22, largo * 3);
    gobba(amp, hzPerBin, c * 4, a0 * 0.11, largo * 4);
  }
  /* il battito binaurale nasce dalla DIFFERENZA tra le due orecchie:
     due portanti vicinissime, non una sola */
  if (l.method === 'bin') gobba(amp, hzPerBin, c + b, a0 * 0.9, largo);
}

function dipingiBase(amp, l, t, hzPerBin, ph) {
  const g = inviluppo(l, t);
  if (g <= 0) return;
  const prof = timbroDalNome(l.name);
  /* due respiri lenti incommensurabili: una base viva non sta ferma,
     e due periodi che non tornano mai insieme non fanno mai schema */
  const vita = 1
    + 0.20 * Math.sin((2 * Math.PI * t) / 13.7 + ph)
    + 0.11 * Math.sin((2 * Math.PI * t) / 7.3 + ph * 1.7);
  letto(amp, hzPerBin, 0.026 * g * vita, prof.pend, prof.hzMax);
  if (prof.brillio > 0) {
    /* l'aria in alto: quella che fa scintillare campane e acqua */
    const scint = 0.5 + 0.5 * Math.sin((2 * Math.PI * t) / 3.1 + ph * 2.3);
    letto(amp, hzPerBin, 0.010 * g * prof.brillio * (0.4 + 0.6 * scint),
      0.15, prof.hzMax);
  }
}

function dipingiVoce(amp, l, t, hzPerBin, ph) {
  const g = inviluppo(l, t);
  if (g <= 0) return;
  /* Non si sa QUANDO parla (le sillabe stanno nel file, e il file non
     si apre): si dipinge il ritmo del parlato — frasi con pause,
     sillabe dentro le frasi. È una modulazione, non una trascrizione. */
  const frase = Math.sin((2 * Math.PI * t) / 6.4 + ph);
  const parla = frase > -0.35 ? 1 : 0.10;
  const sill = 0.60 + 0.40 * Math.abs(Math.sin(2 * Math.PI * 2.9 * t + ph * 3));
  const a = 0.34 * g * parla * sill;
  /* fondamentale + tre formanti: il disegno di una voce vista da una
     FFT, senza pretendere di sapere quale vocale */
  gobba(amp, hzPerBin, 170, a * 0.9, 60);
  gobba(amp, hzPerBin, 620, a, 200);
  gobba(amp, hzPerBin, 1400, a * 0.70, 350);
  gobba(amp, hzPerBin, 2700, a * 0.35, 600);
  letto(amp, hzPerBin, 0.006 * g * parla, 0.5, 7000);
}

/**
 * Un analizzatore che non ascolta niente e dipinge la ricetta.
 *
 * @param score   la ricetta della traccia (score.layers)
 * @param oraSec  funzione: a che secondo siamo ADESSO
 */
export function analizzatoreDaRicetta(score, oraSec, { sampleRate = 44100 } = {}) {
  const bins = FFT / 2;
  const hzPerBin = sampleRate / 2 / bins;
  const livelli = (score && Array.isArray(score.layers) ? score.layers : [])
    .filter((l) => l && !l.mute)
    .map((l, i) => ({ l, ph: fase(`${l.kind || l.method || 'x'}:${l.name || ''}:${i}`) }));
  const amp = new Float32Array(bins);

  /* dominante e energia servono anche alla forma d'onda: si tengono
     dall'ultimo disegno invece di ricalcolarli */
  let ultimaHz = 220, ultimaEn = 0;

  const disegna = () => {
    amp.fill(0);
    const t = oraSec();
    for (const { l, ph } of livelli) {
      if (l.kind === 'audio') dipingiBase(amp, l, t, hzPerBin, ph);
      else if (l.kind === 'voice') dipingiVoce(amp, l, t, hzPerBin, ph);
      else dipingiNeuro(amp, l, t, hzPerBin, ph);
    }
    let somma = 0, max = 0, iMax = 1;
    for (let i = 1; i < bins; i++) {
      somma += amp[i];
      if (amp[i] > max) { max = amp[i]; iMax = i; }
    }
    ultimaHz = iMax * hzPerBin;
    ultimaEn = Math.min(1, somma / 40);
    return t;
  };

  return {
    fftSize: FFT,
    frequencyBinCount: bins,
    minDecibels: DB_MIN,
    maxDecibels: DB_MAX,
    smoothingTimeConstant: 0,
    /* il prototipo chiede `analyser.context.sampleRate` */
    context: { sampleRate },
    /* la firma che dice a chi guarda da dove viene la scena (?ascolto=1) */
    daRicetta: true,

    getByteFrequencyData(out) {
      disegna();
      const n = Math.min(out.length, bins);
      for (let i = 0; i < n; i++) {
        const a = amp[i];
        const db = a > 1e-6 ? 20 * Math.log10(a) : DB_MIN;
        out[i] = clamp(Math.round((255 * (db - DB_MIN)) / (DB_MAX - DB_MIN)), 0, 255);
      }
    },

    /* Una forma d'onda coerente con ciò che si è appena dipinto: il
       motore ne ricava l'altezza del suono, e un rumore casuale gli
       farebbe leggere un'altezza che non esiste. */
    getByteTimeDomainData(out) {
      const t = oraSec();
      const w = (2 * Math.PI * ultimaHz) / sampleRate;
      const a = 100 * Math.min(1, ultimaEn * 2.2);
      for (let i = 0; i < out.length; i++) {
        const v = Math.sin(w * i + t * 6.283) * a
          + Math.sin(w * 2 * i + t) * a * 0.25;
        out[i] = clamp(Math.round(128 + v), 0, 255);
      }
    },
  };
}

/** Il lettore completo (bande, energia, battito) alimentato dalla ricetta. */
export function creaLettoreDaRicetta(ctx, score, oraSec) {
  return creaLettore(ctx, {
    analyser: analizzatoreDaRicetta(score, oraSec, { sampleRate: ctx.sampleRate }),
  });
}
