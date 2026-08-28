/**
 * I FENOMENI — il catalogo onesto delle meraviglie (LB5, 28/8/2026).
 * (Si chiama fenomeni.js e non meraviglie.js perche' il pannello e'
 * Meraviglie.jsx: la trappola del filesystem case-insensitive del
 * Mac — pagata col Ritratto — non si paga due volte.)
 *
 * Il principio, deciso col founder: la geometria non si aggiunge al
 * suono, EMERGE dal suono. Ogni meraviglia e' un fenomeno vero
 * mostrato dal lato giusto — mai un effetto dipinto sopra — e porta
 * il suo CARTELLINO (le etichette della casa):
 *   A = fisica/psicoacustica documentata
 *   C = il valore e' simbolico/tradizionale (il fenomeno resta vero)
 *
 * React-free: ogni meraviglia riceve il lab e restituisce {ferma}.
 * Il suono entra dal lab.ingresso (→ master → ponte): la regola del
 * ponte resta intatta e l'analyser vede tutto. Le meraviglie dei
 * RAPPORTI pilotano invece le due voci del banco: cosi' il modo XY
 * dell'oscilloscopio disegna la figura — il telaio LB1 al lavoro.
 *
 * I moti (l'orbita del vortice) sono LFO agganciati agli AudioParam:
 * niente timer JavaScript, il moto continua a schermo spento. Le due
 * eccezioni dichiarate (Shepard) usano un orologio e lo dicono.
 */

/* un oscillatore COSENO fase-precisa: real[1]=1 (serie del coseno) —
   e' cosi' che due LFO partono in quadratura esatta, senza timer */
function lfoQuadratura(ctx, hz) {
  const sin = ctx.createOscillator();
  sin.frequency.value = hz;
  const cos = ctx.createOscillator();
  cos.frequency.value = hz;
  const re = new Float32Array(2), im = new Float32Array(2);
  re[1] = 1;                                   // coseno
  cos.setPeriodicWave(ctx.createPeriodicWave(re, im));
  return { sin, cos };
}

function tono(ctx, hz, amp, uscita) {
  const o = ctx.createOscillator();
  o.frequency.value = hz;
  const g = ctx.createGain();
  g.gain.value = 0;
  const t = ctx.currentTime;
  g.gain.setValueAtTime(0, t);
  g.gain.linearRampToValueAtTime(amp, t + 0.06);
  o.connect(g); g.connect(uscita);
  o.start();
  return { o, g };
}

function spegniToni(ctx, toni, extra = []) {
  const t = ctx.currentTime;
  toni.forEach(({ o, g }) => {
    try {
      g.gain.cancelScheduledValues(t);
      g.gain.setValueAtTime(g.gain.value, t);
      g.gain.linearRampToValueAtTime(0, t + 0.12);
      o.stop(t + 0.2);
    } catch { /* gia' */ }
  });
  extra.forEach((n) => { try { n.stop ? n.stop(t + 0.2) : n.disconnect(); } catch { /* via */ } });
}

/* ── LO SPAZIO ─────────────────────────────────────────────────── */

function vortice(lab) {
  const ctx = lab.ctx;
  const pan = ctx.createPanner();
  pan.panningModel = 'HRTF';
  pan.distanceModel = 'inverse';
  pan.refDistance = 1;
  pan.connect(lab.ingresso);
  const voce = tono(ctx, 240, 0.35, pan);
  /* l'orbita: due LFO in quadratura sui positionX/Z — il moto vive
     nel motore audio, continua anche a schermo spento */
  const { sin, cos } = lfoQuadratura(ctx, 0.22);
  const rX = ctx.createGain(), rZ = ctx.createGain();
  rX.gain.value = 2.2; rZ.gain.value = 2.2;
  cos.connect(rX); rX.connect(pan.positionX);
  sin.connect(rZ); rZ.connect(pan.positionZ);
  sin.start(); cos.start();
  /* la spirale: il raggio si stringe in 25 s mentre il tono sale —
     il suono AVVITA; poi resta in orbita stretta */
  const t = ctx.currentTime;
  rX.gain.setValueAtTime(2.2, t); rZ.gain.setValueAtTime(2.2, t);
  rX.gain.exponentialRampToValueAtTime(0.7, t + 25);
  rZ.gain.exponentialRampToValueAtTime(0.7, t + 25);
  voce.o.frequency.setValueAtTime(240, t);
  voce.o.frequency.exponentialRampToValueAtTime(320, t + 25);
  return { ferma: () => spegniToni(ctx, [voce], [sin, cos, pan]) };
}

function rotazioneTesta(lab) {
  /* due sinusoidi quasi identiche, UNA PER ORECCHIO: 0,2 Hz di
     differenza = la fase interaurale ruota ogni 5 secondi — la
     sorgente sembra girare DENTRO la testa (e' il meccanismo del
     battimento binaurale, letto dal lato spaziale) */
  const ctx = lab.ctx;
  const unione = ctx.createChannelMerger(2);
  unione.connect(lab.ingresso);
  const gL = ctx.createGain(), gR = ctx.createGain();
  gL.connect(unione, 0, 0); gR.connect(unione, 0, 1);
  const a = tono(ctx, 200, 0.3, gL);
  const b = tono(ctx, 200.2, 0.3, gR);
  return { ferma: () => spegniToni(ctx, [a, b], [unione, gL, gR]) };
}

/* ── LA GEOMETRIA (pilota le voci del banco: XY le disegna) ────── */

function rapporto(lab, num, den) {
  const base = 220;
  lab.generatore.imposta({ forma: 'sine', freq: base, amp: 0.25,
    orecchio: 'entrambe', fase: 1e-7 });
  lab.generatore2.imposta({ forma: 'sine', freq: base * (num / den),
    amp: 0.25, orecchio: 'entrambe', fase: 1e-7 });
  const via = (async () => {
    await lab.generatore.avvia();
    await lab.generatore2.avvia();
  })();
  return {
    ferma: () => via.then(() => {
      lab.generatore.ferma(); lab.generatore2.ferma();
    }),
  };
}

/* ── L'ILLUSIONE (psicoacustica vera) ──────────────────────────── */

function tartini(lab) {
  const ctx = lab.ctx;
  const a = tono(ctx, 1200, 0.28, lab.ingresso);
  const b = tono(ctx, 1500, 0.28, lab.ingresso);
  return { ferma: () => spegniToni(ctx, [a, b]) };
}

function fantasma(lab) {
  const ctx = lab.ctx;
  const toni = [400, 600, 800].map((hz) => tono(ctx, hz, 0.18, lab.ingresso));
  return { ferma: () => spegniToni(ctx, toni) };
}

function shepard(lab) {
  /* la scala che scende per sempre: sei voci a distanza d'ottava,
     tutte in glissando verso il basso; quando una esce dal fondo
     rientra dall'alto, e l'inviluppo a campana (sul log della
     frequenza) nasconde la giuntura. QUI c'e' un orologio JS, e lo
     dichiariamo: a schermo spento la discesa si ferma. */
  const ctx = lab.ctx;
  const N = 6, F0 = 55, T_OTTAVA = 8;
  const centro = Math.log2(440), sigma = 1.25;
  const voci = Array.from({ length: N }, () => {
    const o = ctx.createOscillator();
    const g = ctx.createGain();
    g.gain.value = 0;
    o.connect(g); g.connect(lab.ingresso);
    o.start();
    return { o, g };
  });
  const t0 = ctx.currentTime;
  const passo = () => {
    const u = (ctx.currentTime - t0) / T_OTTAVA;
    for (let k = 0; k < N; k++) {
      const pos = ((k - u) % N + N) % N;            // 0..N, scende
      const hz = F0 * Math.pow(2, pos);
      const lg = Math.log2(hz);
      const amp = 0.5 * Math.exp(-((lg - centro) ** 2) / (2 * sigma * sigma)) / N * 4;
      voci[k].o.frequency.setTargetAtTime(hz, ctx.currentTime, 0.05);
      voci[k].g.gain.setTargetAtTime(amp, ctx.currentTime, 0.05);
    }
  };
  passo();
  const orologio = setInterval(passo, 60);
  return { ferma: () => { clearInterval(orologio); spegniToni(ctx, voci); } };
}

/* ── IL BANCO CLASSICO ─────────────────────────────────────────── */

function rumore(lab, colore) {
  const ctx = lab.ctx;
  const sr = ctx.sampleRate, sec = 2;
  const buf = ctx.createBuffer(1, sr * sec, sr);
  const d = buf.getChannelData(0);
  if (colore === 'bianco') {
    for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
  } else if (colore === 'rosa') {
    /* Voss-McCartney: somma di generatori che cambiano a meta' */
    let b0 = 0, b1 = 0, b2 = 0;
    for (let i = 0; i < d.length; i++) {
      const w = Math.random() * 2 - 1;
      b0 = 0.997 * b0 + 0.029 * w;
      b1 = 0.985 * b1 + 0.032 * w;
      b2 = 0.95 * b2 + 0.048 * w;
      d[i] = (b0 + b1 + b2 + w * 0.05) * 2.8;
    }
  } else {                                          // marrone: il cammino casuale
    let v = 0;
    for (let i = 0; i < d.length; i++) {
      v = Math.max(-1, Math.min(1, v + (Math.random() * 2 - 1) * 0.02));
      d[i] = v * 3;
    }
  }
  /* si normalizza al picco: i tre colori escono allo stesso volume */
  let p = 0;
  for (let i = 0; i < d.length; i++) p = Math.max(p, Math.abs(d[i]));
  for (let i = 0; i < d.length; i++) d[i] = (d[i] / (p || 1)) * 0.9;
  const src = ctx.createBufferSource();
  src.buffer = buf; src.loop = true;
  const g = ctx.createGain();
  g.gain.value = 0;
  src.connect(g); g.connect(lab.ingresso);
  src.start();
  const t = ctx.currentTime;
  g.gain.linearRampToValueAtTime(0.22, t + 0.08);
  return { ferma: () => spegniToni(ctx, [{ o: src, g }]) };
}

function fmCampana(lab) {
  /* la campana di Chowning (1973): UNA portante e UNA modulante in
     rapporto inarmonico (1:1,4), l'indice che decade piu' in fretta
     dell'ampiezza — due oscillatori, un timbro di campana */
  const ctx = lab.ctx;
  const portante = ctx.createOscillator();
  portante.frequency.value = 200;
  const mod = ctx.createOscillator();
  mod.frequency.value = 280;
  const indice = ctx.createGain();
  indice.gain.value = 0;
  mod.connect(indice); indice.connect(portante.frequency);
  const g = ctx.createGain();
  g.gain.value = 0;
  portante.connect(g); g.connect(lab.ingresso);
  const t = ctx.currentTime;
  indice.gain.setValueAtTime(600, t);
  indice.gain.exponentialRampToValueAtTime(1, t + 6);
  g.gain.setValueAtTime(0.4, t);
  g.gain.exponentialRampToValueAtTime(0.001, t + 9);
  portante.start(); mod.start();
  portante.stop(t + 9.5); mod.stop(t + 9.5);
  return { ferma: () => spegniToni(ctx, [{ o: portante, g }], [mod]) };
}

function cordaPizzicata(lab) {
  /* Karplus-Strong (1983): un soffio di rumore in un anello di
     ritardo con un filtro — la fisica di una corda in venti righe.
     Il ritardo E' la lunghezza della corda: 1/220 s = La3. */
  const ctx = lab.ctx;
  const anello = ctx.createDelay(0.1);
  anello.delayTime.value = 1 / 220;
  const filtro = ctx.createBiquadFilter();
  filtro.type = 'lowpass'; filtro.frequency.value = 4200;
  /* TRAPPOLA PAGATA DUE VOLTE AL COLLAUDO: nel lowpass di WebAudio
     il Q e' IN DECIBEL — il default (1) e' un picco di +1 dB sopra
     l'unita' vicino al taglio, e perfino «Q=0,5» e' ancora +0,5 dB:
     l'anello si autoalimentava ed esplodeva (RMS 2e28). A −10 dB la
     risonanza e' sepolta e il giro dell'anello resta sotto 1. */
  filtro.Q.value = -10;
  const ritorno = ctx.createGain();
  ritorno.gain.value = 0.995;   // ~6 s di vita: una corda vera
  anello.connect(filtro); filtro.connect(ritorno); ritorno.connect(anello);
  const g = ctx.createGain();
  g.gain.value = 0.5;
  anello.connect(g); g.connect(lab.ingresso);
  /* il pizzico: 8 ms di rumore dentro l'anello */
  const sr = ctx.sampleRate;
  const soffio = ctx.createBuffer(1, Math.floor(sr * 0.008), sr);
  const d = soffio.getChannelData(0);
  for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
  const src = ctx.createBufferSource();
  src.buffer = soffio;
  src.connect(anello);
  src.start();
  return { ferma: () => spegniToni(ctx, [{ o: src, g }], [anello, filtro, ritorno]) };
}

/* ═══ IL REGISTRO ═══ */
export const MERAVIGLIE = [
  {
    id: 'vortice', nome: 'Il Vortice', cartellino: 'A', famiglia: 'spazio',
    riga: 'Il suono orbita attorno alla testa e si avvita salendo — in cuffia.',
    didascalia: 'È la spazializzazione HRTF: la stessa matematica con cui il cervello localizza i suoni nel mondo. L’orbita vive nel motore audio (due LFO in quadratura), non in un’animazione: continua anche a schermo spento. Chiudi gli occhi e seguilo.',
    avvia: vortice,
  },
  {
    id: 'rotazione', nome: 'La rotazione nella testa', cartellino: 'A', famiglia: 'spazio',
    riga: 'Due toni quasi identici, uno per orecchio: la sorgente gira DENTRO il cranio.',
    didascalia: 'A 200 e 200,2 Hz la fase tra le orecchie ruota ogni 5 secondi: il cervello la legge come posizione, e la posizione gira. È il meccanismo del battimento binaurale, visto dal lato spaziale. Solo in cuffia.',
    avvia: rotazioneTesta,
  },
  {
    id: 'ottava', nome: 'I Rapporti — 2:1, l’ottava', cartellino: 'A', famiglia: 'geometria',
    riga: 'L’intervallo più consonante — e in XY disegna un otto.',
    didascalia: 'Un intervallo è un rapporto tra numeri: 2:1 è l’ottava. Passa l’oscilloscopio in XY e guarda: la figura di Lissajous È quel rapporto disegnato. Quando lo senti consonante, stai sentendo la geometria.',
    avvia: (lab) => rapporto(lab, 2, 1),
  },
  {
    id: 'quinta', nome: 'I Rapporti — 3:2, la quinta', cartellino: 'A', famiglia: 'geometria',
    riga: 'La quinta giusta: un nodo in più nella figura.',
    didascalia: 'Il rapporto 3:2 è la quinta — il mattone delle scale di mezzo mondo. In XY la figura ha un intreccio in più dell’ottava: più il rapporto è semplice, più il disegno è quieto. Stona il rapporto di poco (muovi la frequenza della B) e la figura si mette a ruotare: è la fase che scorre.',
    avvia: (lab) => rapporto(lab, 3, 2),
  },
  {
    id: 'phi', nome: 'Phi — il rapporto aureo', cartellino: 'C', famiglia: 'geometria',
    riga: '1 : 1,618… — il battimento che non si ripete mai.',
    didascalia: 'Il rapporto aureo è il numero «più irrazionale» che esista: due voci in 1:φ non si allineano MAI — il battimento non si ripete, la figura XY non si chiude. Il valore simbolico è della tradizione (per questo il cartellino C); la matematica dell’irrazionalità è vera al cento per cento.',
    avvia: (lab) => rapporto(lab, 1.6180339887, 1),
  },
  {
    id: 'tartini', nome: 'Il terzo suono (Tartini)', cartellino: 'A', famiglia: 'illusione',
    riga: 'Suoniamo 1200 e 1500 Hz — e senti un 300 Hz che nell’aria non c’è.',
    didascalia: 'Il 300 Hz che senti lo genera il TUO orecchio (la coclea non è lineare: crea la differenza tra i due toni). Guarda lo spettro: il picco a 300 non esiste. Giuseppe Tartini lo descrisse nel 1714. Serve un volume discreto e un ambiente quieto.',
    avvia: tartini,
  },
  {
    id: 'fantasma', nome: 'La fondamentale fantasma', cartellino: 'A', famiglia: 'illusione',
    riga: '400+600+800 Hz senza il 200 — e il cervello sente il 200.',
    didascalia: 'Le tre armoniche condividono un periodo comune: 200 Hz. Il cervello ricostruisce l’altezza dal PERIODO, non dallo spettro — così senti un tono grave che nell’aria non c’è (lo spettro lo dimostra). È il motivo per cui la voce al telefono conserva l’altezza anche senza i bassi.',
    avvia: fantasma,
  },
  {
    id: 'shepard', nome: 'La discesa infinita (Shepard-Risset)', cartellino: 'A', famiglia: 'illusione',
    riga: 'Una scala che scende per sempre — e non arriva mai in fondo.',
    didascalia: 'Sei voci a distanza d’ottava scendono insieme; quando una esce dal fondo rientra dall’alto, e l’inviluppo a campana nasconde la giuntura. Guarda lo spettrogramma: le diagonali parallele SONO il trucco, svelato. (Il moto usa un orologio: a schermo spento la discesa si ferma.)',
    avvia: shepard,
  },
  {
    id: 'bianco', nome: 'Rumore bianco', cartellino: 'A', famiglia: 'banco',
    riga: 'Tutte le frequenze, stessa energia: lo spettro piatto.',
    didascalia: 'Ogni frequenza ha la stessa energia media: nello spettro è una linea piatta che frigge. È il metro di paragone di tutti i rumori — e il segnale di prova per misurare una stanza o un filtro.',
    avvia: (lab) => rumore(lab, 'bianco'),
  },
  {
    id: 'rosa', nome: 'Rumore rosa', cartellino: 'A', famiglia: 'banco',
    riga: 'Energia uguale per OTTAVA: il rumore che suona naturale.',
    didascalia: 'Il rosa perde 3 dB a ogni ottava: energia uguale per banda percettiva, non per Hertz. Per questo suona «giusto» all’orecchio — pioggia, cascate e mari gli somigliano. Nello spettro log è una discesa costante: guardala.',
    avvia: (lab) => rumore(lab, 'rosa'),
  },
  {
    id: 'marrone', nome: 'Rumore marrone', cartellino: 'A', famiglia: 'banco',
    riga: 'Il cammino casuale: gravi profondi, come un oceano dietro un muro.',
    didascalia: 'Ogni campione è il precedente più un passetto a caso (il moto browniano, da cui il nome): −6 dB per ottava, l’energia crolla verso l’acuto. È il più scuro dei tre colori.',
    avvia: (lab) => rumore(lab, 'marrone'),
  },
  {
    id: 'fm', nome: 'La campana di Chowning (FM)', cartellino: 'A', famiglia: 'banco',
    riga: 'Due soli oscillatori in FM — e suona una campana.',
    didascalia: 'John Chowning (1973): una portante e una modulante in rapporto inarmonico (qui 1:1,4), con l’indice di modulazione che decade più in fretta del volume. Confrontala col Ritratto di una campana vera: la FM inventa i parziali, il ritratto li misura.',
    avvia: fmCampana,
  },
  {
    id: 'corda', nome: 'La corda pizzicata (Karplus-Strong)', cartellino: 'A', famiglia: 'banco',
    riga: 'Un soffio di rumore in un anello di ritardo: nasce una corda.',
    didascalia: 'Il ritardo è la lunghezza della corda (1/220 s = La), il filtro è l’attrito che spegne prima gli acuti. Otto millisecondi di rumore, e la fisica fa il resto: riascolta il decadere nello spettrogramma — gli acuti muoiono prima, come nel Ritratto.',
    avvia: cordaPizzicata,
  },
];

/* banco di prova per i collaudi dalla console */
try { window.__fqzMeraviglie = { MERAVIGLIE }; } catch { /* SSR */ }
