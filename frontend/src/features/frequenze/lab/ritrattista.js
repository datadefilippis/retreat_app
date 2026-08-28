/**
 * IL RITRATTISTA — l'analisi solida di un suono catturato (LB3,
 * 27/8/2026). Si chiama cosi' (e non ritratto.js) perche' il pannello
 * e' Ritratto.jsx: sul filesystem case-insensitive del Mac i due nomi
 * COLLIDONO e il CaseSensitivePathsPlugin di CRA rifiuta l'import —
 * «Cannot find module», pagato al collaudo.
 *
 * React-free e senza nodi audio: riceve i campioni di una
 * registrazione (la campana colpita, il bicchiere, una voce) e ne
 * scrive la CARTA D'IDENTITA' ACUSTICA — dati, non audio, come lo
 * score e' la ricetta della sessione:
 *
 *   - la TABELLA DEI PARZIALI: per ogni modo, frequenza fine
 *     (vertice parabolico su FFT lunga con zero-padding), forza in
 *     dB relativi, rapporto col fondamentale e scarto in cents
 *     dall'armonico teorico — una campana NON e' armonica, e il
 *     ritratto lo mostra;
 *   - i DOPPIETTI: nelle campane i modi vivono in coppie quasi
 *     coincidenti, e il loro battimento e' lo «shimmer» che gira;
 *   - gli INVILUPPI: per ogni parziale il tempo di decadimento T60
 *     (Goertzel per fotogramma + regressione sul decadere in dB) —
 *     gli acuti muoiono prima, e' la firma temporale del timbro.
 *
 * La FFT e' nostra (radix-2 iterativa, ~40 righe): niente dipendenze,
 * e controlliamo noi finestra e risoluzione. Con 3 s di coda utile a
 * 44,1 kHz il bin vale 0,34 Hz e il vertice scende sotto il decimo.
 */

const MAX_CAMPIONI = 1 << 17;      // ~3 s a 44.1k: la coda che si analizza
const PARZIALI_MAX = 16;
const SOPRA_FONDO_DB = 18;         // un picco deve emergere dal pavimento
const FIN_MIN = 40, FIN_MAX = 16000;  // la finestra onesta di un mic consumer
const DOPPIETTO_HZ = 5;            // due modi entro 5 Hz = una coppia

/* ── FFT radix-2 iterativa, in-place, Float64 ─────────────────── */
export function fft(re, im) {
  const n = re.length;
  for (let i = 1, j = 0; i < n; i++) {
    let bit = n >> 1;
    for (; j & bit; bit >>= 1) j ^= bit;
    j |= bit;
    if (i < j) {
      let t = re[i]; re[i] = re[j]; re[j] = t;
      t = im[i]; im[i] = im[j]; im[j] = t;
    }
  }
  for (let len = 2; len <= n; len <<= 1) {
    const ang = -2 * Math.PI / len;
    const wr = Math.cos(ang), wi = Math.sin(ang);
    for (let i = 0; i < n; i += len) {
      let cr = 1, ci = 0;
      for (let k = 0; k < len / 2; k++) {
        const j2 = i + k + len / 2;
        const tr = re[j2] * cr - im[j2] * ci;
        const ti = re[j2] * ci + im[j2] * cr;
        re[j2] = re[i + k] - tr; im[j2] = im[i + k] - ti;
        re[i + k] += tr; im[i + k] += ti;
        const ncr = cr * wr - ci * wi;
        ci = cr * wi + ci * wr; cr = ncr;
      }
    }
  }
}

const db = (v) => 20 * Math.log10(Math.max(v, 1e-12));

/* Goertzel: l'ampiezza di UNA frequenza in una finestra — per gli
   inviluppi costa n·parziali, non una FFT per fotogramma */
function goertzel(buf, da, quanti, sr, hz) {
  const w = 2 * Math.PI * hz / sr;
  const c = 2 * Math.cos(w);
  let s0 = 0, s1 = 0, s2 = 0;
  for (let i = 0; i < quanti; i++) {
    s0 = buf[da + i] + c * s1 - s2;
    s2 = s1; s1 = s0;
  }
  const re = s1 - s2 * Math.cos(w), im = s2 * Math.sin(w);
  return Math.sqrt(re * re + im * im) * 2 / quanti;
}

export function analizza(campioni, sampleRate, opzioni = {}) {
  const N0 = campioni.length;
  if (!N0 || N0 < sampleRate * 0.4) return null;   // sotto 0,4 s non e' un ritratto

  /* il COLPO: il picco assoluto. L'analisi spettrale parte 50 ms
     dopo (l'attacco e' rumore a banda larga, non parziali). */
  let piccoIdx = 0, picco = 0;
  for (let i = 0; i < N0; i++) {
    const a = Math.abs(campioni[i]);
    if (a > picco) { picco = a; piccoIdx = i; }
  }
  if (picco < 0.003) return null;                  // silenzio

  /* il pavimento PRIMA del colpo: il rumore della stanza */
  const preN = Math.min(piccoIdx, Math.floor(sampleRate * 0.3));
  let pre = 0;
  for (let i = piccoIdx - preN; i < piccoIdx; i++) pre += campioni[i] * campioni[i];
  const rumoreFondo = preN > 400 ? db(Math.sqrt(pre / preN)) : null;

  let da = Math.min(N0 - 1, piccoIdx + Math.floor(sampleRate * 0.05));
  let L = Math.min(N0 - da, MAX_CAMPIONI);
  let continuo = false;
  /* IL SUONO TENUTO (collaudo LB3): in un suono continuo il «picco»
     cade dove capita — anche a fine registrazione — e la coda si
     accorcia fino a perdere i doppietti (0,3 s = bin da 3 Hz). Se
     dopo il picco resta meno di un secondo ma la registrazione e'
     lunga, non e' un colpo: e' un suono tenuto — si analizza la
     parte piu' lunga possibile e il "fondo della stanza" non ha
     senso (non c'e' un prima). */
  if (L < sampleRate && N0 > sampleRate * 1.2) {
    continuo = true;
    da = Math.max(0, N0 - MAX_CAMPIONI);
    L = N0 - da;
  }
  if (L < sampleRate * 0.3) return null;           // coda troppo corta

  /* Hann sulla coda + zero-padding ×4: il vertice della parabola
     scende sotto il decimo di Hz */
  let size = 1; while (size < L * 4) size <<= 1;
  const re = new Float64Array(size), im = new Float64Array(size);
  for (let i = 0; i < L; i++) {
    const h = 0.5 - 0.5 * Math.cos((2 * Math.PI * i) / (L - 1));
    re[i] = campioni[da + i] * h;
  }
  fft(re, im);

  const hzPerBin = sampleRate / size;
  const bMin = Math.max(2, Math.floor(FIN_MIN / hzPerBin));
  const bMax = Math.min(size / 2 - 2, Math.ceil(FIN_MAX / hzPerBin));
  const mag = new Float64Array(bMax + 2);
  for (let b = bMin - 1; b <= bMax + 1; b++) {
    mag[b] = db(Math.hypot(re[b], im[b]));
  }

  /* il pavimento spettrale: la mediana — robusta ai picchi */
  const copia = [];
  for (let b = bMin; b <= bMax; b += 7) copia.push(mag[b]);
  copia.sort((a, b2) => a - b2);
  const pavimento = copia[Math.floor(copia.length / 2)];

  /* i picchi: massimi locali su un intorno largo quanto il lobo
     della finestra (4 bin veri = 16 bin col padding), sopra il
     pavimento e non troppo sotto il campione piu' forte */
  const lobo = 16;
  let maxDb = -Infinity;
  for (let b = bMin; b <= bMax; b++) if (mag[b] > maxDb) maxDb = mag[b];
  const grezzi = [];
  for (let b = bMin + lobo; b <= bMax - lobo; b++) {
    const v = mag[b];
    if (v < pavimento + SOPRA_FONDO_DB || v < maxDb - 60) continue;
    let cima = true;
    for (let k = 1; k <= lobo; k++) {
      if (mag[b - k] > v || mag[b + k] > v) { cima = false; break; }
    }
    if (!cima) continue;
    /* vertice della parabola sui dB */
    const a = mag[b - 1], c = mag[b + 1];
    const denom = a - 2 * v + c;
    const delta = denom !== 0 ? 0.5 * (a - c) / denom : 0;
    grezzi.push({ hz: (b + delta) * hzPerBin, db: v - maxDb });
  }
  grezzi.sort((x, y) => y.db - x.db);
  const scelti = grezzi.slice(0, PARZIALI_MAX * 2).sort((x, y) => x.hz - y.hz);
  if (!scelti.length) return null;

  /* i DOPPIETTI: coppie entro DOPPIETTO_HZ — si tengono INSIEME
     (il battimento e' informazione, non rumore da fondere) */
  const parziali = [];
  for (let i = 0; i < scelti.length; i++) {
    const p = scelti[i];
    const prossimo = scelti[i + 1];
    if (prossimo && prossimo.hz - p.hz < DOPPIETTO_HZ) {
      const forte = p.db >= prossimo.db ? p : prossimo;
      const debole = p.db >= prossimo.db ? prossimo : p;
      parziali.push({ ...forte,
        doppietto: { hz: debole.hz, db: debole.db,
                     battito: Math.abs(prossimo.hz - p.hz) } });
      i++;                                        // la coppia consuma due picchi
    } else parziali.push({ ...p });
  }
  const tenuti = parziali.slice(0, PARZIALI_MAX);

  /* il FONDAMENTALE: il modo piu' grave fra quelli che contano */
  const fondo = tenuti.filter((p) => p.db >= -30)
    .sort((x, y) => x.hz - y.hz)[0] || tenuti[0];

  /* gli INVILUPPI: Goertzel per fotogramma sulla registrazione dal
     colpo in poi, poi regressione sul decadere in dB → T60 */
  const finestra = 4096, passo = 2048;
  const daInv = Math.max(0, piccoIdx - finestra);
  const fotogrammi = Math.floor((N0 - daInv - finestra) / passo);
  for (const p of tenuti) {
    if (fotogrammi < 6) { p.t60 = null; continue; }
    const inv = [];
    for (let f = 0; f < fotogrammi; f++) {
      inv.push(db(goertzel(campioni, daInv + f * passo, finestra, sampleRate, p.hz)));
    }
    let cima = 0;
    for (let f = 1; f < inv.length; f++) if (inv[f] > inv[cima]) cima = f;
    const soglia = inv[cima] - 50;
    const ts = [], vs = [];
    for (let f = cima; f < inv.length; f++) {
      if (inv[f] < soglia) break;
      ts.push((f * passo) / sampleRate); vs.push(inv[f]);
    }
    if (ts.length < 4) { p.t60 = null; continue; }
    const n = ts.length;
    let st = 0, sv = 0, stt = 0, stv = 0;
    for (let k = 0; k < n; k++) {
      st += ts[k]; sv += vs[k]; stt += ts[k] * ts[k]; stv += ts[k] * vs[k];
    }
    const pendenza = (n * stv - st * sv) / (n * stt - st * st || 1);
    p.t60 = pendenza < -0.5 ? Math.min(99, -60 / pendenza) : null;
  }

  /* rapporto e scarto in cents dall'armonico teorico piu' vicino */
  for (const p of tenuti) {
    p.rapporto = p.hz / fondo.hz;
    const arm = Math.max(1, Math.round(p.rapporto));
    p.cents = Math.round(1200 * Math.log2(p.rapporto / arm));
  }

  return {
    versione: 1,
    sampleRate,
    durataSec: +(N0 / sampleRate).toFixed(2),
    codaSec: +(L / sampleRate).toFixed(2),
    continuo,
    rumoreFondoDb: (continuo || rumoreFondo === null)
      ? null : +rumoreFondo.toFixed(1),
    fondamentaleHz: +fondo.hz.toFixed(2),
    parziali: tenuti.map((p) => ({
      hz: +p.hz.toFixed(2),
      db: +p.db.toFixed(1),
      rapporto: +p.rapporto.toFixed(3),
      cents: p.cents,
      t60: p.t60 === null ? null : +p.t60.toFixed(2),
      doppietto: p.doppietto ? {
        hz: +p.doppietto.hz.toFixed(2),
        db: +p.doppietto.db.toFixed(1),
        battito: +p.doppietto.battito.toFixed(2),
      } : null,
    })),
  };
}

/* banco di prova: l'analisi si collauda dalla console con una campana
   sintetica, senza microfono ne' permessi */
try { window.__fqzRitratto = { analizza, fft }; } catch { /* SSR/test */ }
