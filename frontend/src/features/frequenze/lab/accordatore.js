/**
 * L'ACCORDATORE — la matematica del pitch (LB2, 27/8/2026).
 *
 * React-free e senza nodi audio: riceve un buffer di campioni e
 * risponde «che nota e'». La stessa famiglia di matematica del polso
 * della Danza (autocorrelazione), ma sul SEGNALE, non sull'inviluppo:
 *
 *   1. si toglie la media (il DC di un mic economico sposterebbe
 *      tutti i prodotti);
 *   2. autocorrelazione normalizzata r(lag) = Σx·x_lag / r(0) sui lag
 *      del range udibile-utile (50 Hz–2 kHz: voce e strumenti);
 *   3. anti-ottava: non il massimo globale, ma il PRIMO picco che
 *      vale almeno il 90% del massimo — l'autocorrelazione di un
 *      timbro armonico ripete i picchi a 2·lag, 3·lag… e il massimo
 *      puo' cadere un'ottava SOTTO la nota vera;
 *   4. interpolazione parabolica sul vertice: la risoluzione scende
 *      sotto il campione (a 44,1 kHz e 440 Hz un lag intero vale
 *      ~4 Hz: senza vertice l'accordatore sarebbe una pietra).
 *
 * `chiarezza` e' l'altezza del picco scelto (0..1): sotto ~0,5 il
 * suono non e' abbastanza periodico per dichiarare una nota (rumore,
 * silenzio, parlato sordo) e si risponde null — un accordatore che
 * inventa numeri non e' uno strumento.
 */

const SOGLIA_RMS = 0.003;      // sotto: silenzio, niente da accordare
const SOGLIA_CHIAREZZA = 0.5;  // sotto: non e' una nota, e' rumore
const QUASI_MASSIMO = 0.9;     // anti-ottava: primo picco ≥ 90% del max

export function fondamentale(buf, sampleRate,
  { minHz = 50, maxHz = 2000, finestra = 4096 } = {}) {
  const N = Math.min(finestra, buf.length);

  let media = 0;
  for (let i = 0; i < N; i++) media += buf[i];
  media /= N;

  let energia = 0;
  for (let i = 0; i < N; i++) {
    const v = buf[i] - media;
    energia += v * v;
  }
  const rms = Math.sqrt(energia / N);
  if (rms < SOGLIA_RMS) return null;

  const lagMin = Math.max(2, Math.floor(sampleRate / maxHz));
  const lagMax = Math.min(N - 2, Math.ceil(sampleRate / minHz));
  if (lagMax <= lagMin) return null;

  /* Normalizzazione PER SOVRAPPOSIZIONE: a lag crescente la somma ha
     meno termini (N−lag), e senza questo conto i lag lunghi partono
     svantaggiati — la parabola si storce e l'accordatore sbaglia di
     qualche decimo (misurato: 137,42 → 137,72). Media dei prodotti
     diviso energia media: r e' un coseno pulito, il vertice e' vero. */
  const energiaMedia = energia / N;
  const r = new Float32Array(lagMax + 1);
  for (let lag = lagMin; lag <= lagMax; lag++) {
    let acc = 0;
    const conta = N - lag;
    for (let i = 0; i < conta; i++) {
      acc += (buf[i] - media) * (buf[i + lag] - media);
    }
    r[lag] = (acc / conta) / energiaMedia;
  }

  let massimo = 0;
  for (let lag = lagMin; lag <= lagMax; lag++) {
    if (r[lag] > massimo) massimo = r[lag];
  }
  if (massimo < SOGLIA_CHIAREZZA) return null;

  /* il PRIMO picco locale che vale quasi quanto il massimo */
  let scelto = -1;
  for (let lag = lagMin + 1; lag < lagMax; lag++) {
    if (r[lag] >= QUASI_MASSIMO * massimo
        && r[lag] >= r[lag - 1] && r[lag] >= r[lag + 1]) { scelto = lag; break; }
  }
  if (scelto < 0) return null;

  /* vertice della parabola per i tre punti attorno al picco */
  const a = r[scelto - 1], b = r[scelto], c = r[scelto + 1];
  const denom = a - 2 * b + c;
  const delta = denom !== 0 ? 0.5 * (a - c) / denom : 0;
  let lagFine = scelto + Math.max(-0.5, Math.min(0.5, delta));

  /* IL SOTTOPERIODO (caso del founder, 28/8: rifusione a 4884 Hz e
     l'accordatore diceva «1628» — 4884/3 esatto). Un tono SOPRA
     maxHz ha il periodo vero FUORI dal campo di ricerca, e
     l'autocorrelazione aggancia il primo multiplo che vi cade
     dentro. Prima di rispondere si prova lag/2..lag/8, anche sotto
     il campo: se la correlazione regge (>=85% del picco), il
     periodo vero e' il piu' corto che regge — e la risposta e'
     quella, anche oltre maxHz. Uno strumento risponde giusto o
     tace: mai un numero sbagliato con la faccia sicura. */
  const rA = (lag) => {
    const l = Math.round(lag);
    if (l < 2 || l >= N - 2) return 0;
    let acc = 0;
    const conta = N - l;
    for (let i = 0; i < conta; i++) {
      acc += (buf[i] - media) * (buf[i + l] - media);
    }
    return (acc / conta) / energiaMedia;
  };
  for (let k = 8; k >= 2; k--) {
    const cand = lagFine / k;
    if (cand < 2) continue;
    if (rA(cand) >= 0.85 * b) {
      /* vertice locale attorno al sottoperiodo trovato */
      const l0 = Math.round(cand);
      const ra = rA(l0 - 1), rb = rA(l0), rc = rA(l0 + 1);
      const den2 = ra - 2 * rb + rc;
      const d2 = den2 !== 0 ? 0.5 * (ra - rc) / den2 : 0;
      lagFine = l0 + Math.max(-0.5, Math.min(0.5, d2));
      break;
    }
  }

  return { hz: sampleRate / lagFine, chiarezza: b };
}

/* banco di prova: la matematica si collauda dalla console con un
   buffer sintetico, senza microfono ne' permessi */
try { window.__fqzAccordatore = { fondamentale }; } catch { /* SSR/test */ }
