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

import { fondamentale } from './accordatore';

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
export function goertzel(buf, da, quanti, sr, hz) {
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

  /* LA SATURAZIONE (LM1, 5/9/2026 — la campana forte del founder al
     telefono): un microfono che satura non lo diceva nessuno, e la
     tabella usciva sbagliata (prodotti di intermodulazione: 120 e
     152 Hz al posto di 214, misurato al banco). Si contano i campioni
     al tetto: sopra lo 0,05% il ritratto porta l'asterisco, e la UI
     dice la cura (allontanare il telefono). Mai bloccare: una misura
     con l'asterisco vale piu' di nessuna. */
  let saturi = 0;
  for (let i = 0; i < N0; i++) if (Math.abs(campioni[i]) >= 0.985) saturi++;
  const clipping = saturi > N0 * 0.0005;
  const piccoDb = +db(picco).toFixed(1);

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

  /* il pavimento spettrale: la mediana, robusta ai picchi */
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

  /* IL SOFFIO SI RICONOSCE DALLA STABILITA' (terzo giro, i primi
     due misurati e bocciati: «nessun picco» non basta perche' le
     fluttuazioni della FFT di un rumore superano la soglia locale;
     la prominenza globale nemmeno, perche' un rumore PENDENTE — il
     rosa, il respiro — svetta comunque sulla mediana. Il
     discriminante vero e' il TEMPO: un modo sta FERMO alla stessa
     frequenza tra l'inizio e la fine della registrazione, la
     fluttuazione di un rumore cambia posto. Si confrontano i picchi
     forti di due finestre lontane: nessuno stabile = soffio. */
  const verdettoSoffio = () => ({
    versione: 1,
    natura: 'soffio',
    sampleRate,
    durataSec: +(N0 / sampleRate).toFixed(2),
    piccoDb: +db(picco).toFixed(1),
  });
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
  let scelti = grezzi.slice(0, PARZIALI_MAX * 2).sort((x, y) => x.hz - y.hz);
  /* IL SOFFIO (consolidamento del Ritratto, 28/8): vento, respiro,
     fruscio, mare — c'e' energia ma NON ci sono modi: lo spettro e'
     liscio, nessun picco emerge dal pavimento. Prima si rispondeva
     «troppo piano» (falso: era forte); ora si dice la natura vera —
     e' rumore, non note, e la rifusione additiva non puo' replicarlo.
     E' un verdetto che INSEGNA, non un fallimento. */
  if (!scelti.length) {
    return picco >= 0.01 ? {
      versione: 1,
      natura: 'soffio',
      sampleRate,
      durataSec: +(N0 / sampleRate).toFixed(2),
      piccoDb: +db(picco).toFixed(1),
    } : null;
  }

  /* LE BANDE LATERALI (caso «aummm» del founder, 28/8): una voce con
     vibrato mette nello spettro picchi VERI a ±(4-10) Hz dal
     parziale — sono la firma della modulazione, non modi
     dell'oggetto, e sporcavano la tabella (146 con satelliti a 136,
     151, 156). Un picco molto piu' debole (≥6 dB) e vicino (fra la
     finestra dei doppietti e 15 Hz) a uno forte e' una banda
     laterale: si lascia fuori dal ritratto. I doppietti veri (<5 Hz)
     e i modi distinti (>15 Hz) non si toccano. */
  scelti = scelti.filter((p) => !scelti.some((q) => q !== p
    && q.db > p.db + 6
    && Math.abs(q.hz - p.hz) >= DOPPIETTO_HZ
    && Math.abs(q.hz - p.hz) < 15));

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

  /* ═══ LA VIA ARMONICA (caso «aummm» del founder, 28/8) ═══
     Un suono TENUTO e INTONATO (una voce, una corda tenuta, una
     campana strofinata) ha il vibrato: la fondamentale oscilla, e
     la FFT lunga spezza ogni armonica nelle sue bande di
     modulazione — misurato: con ±1,2% di vibrato la 3ª armonica
     diventava 432,8/438/443,2 e la rifusione suonava stonata.
     La cura e' cambiare STRUMENTO, non stringere il filtro: per i
     suoni tenuti la fondamentale si INSEGUE nel tempo (la stessa
     autocorrelazione dell'accordatore, fotogramma per fotogramma),
     le armoniche si misurano col Goertzel a k·f0, e il vibrato
     smette di essere rumore: diventa un DATO del ritratto
     (profondita' e velocita'), che la fonderia potra' risuonare.
     La via si TENTA SEMPRE (primo giro sbagliato: era agganciata al
     ramo «continuo», ma quello dipende da DOVE cade il picco — una
     voce tenuta col picco a meta' passava dalla via del colpo).
     Sono i suoi tre cancelli a decidere: 60% dei fotogrammi con una
     fondamentale, i picchi FFT forti che cadono sulla serie
     armonica, almeno due armoniche — un bordone inarmonico o una
     campana che sfuma non passano e restano sulla via dei modi. */
  /* IL DECADERE (LM1, 5/9): un oggetto colpito perde energia lungo la
     coda, una voce tenuta no. Oggi e' un DATO del verdetto (la
     melodia di un suono che decade non dice piu' «voce»: dice campana
     forte); la taratura dei cancelli si fa sui WAV veri del founder,
     non su un segnale sintetico (banco del 5/9: riproduce il bug,
     non tara la cura). */
  const percussivo = _decade(campioni, da, L);
  {
    const armonico = _viaArmonica(campioni, da, L, sampleRate, tenuti);
    if (armonico && armonico.mutevole) {
      return {
        versione: 1,
        natura: 'melodia',
        sampleRate,
        durataSec: +(N0 / sampleRate).toFixed(2),
        f0minHz: armonico.f0minHz,
        f0maxHz: armonico.f0maxHz,
        percussivo,
        clipping,
        piccoDb,
      };
    }
    if (armonico && !armonico.mutevole) {
      return {
        versione: 1,
        natura: 'intonato',
        armonico: true,
        continuo,
        sampleRate,
        durataSec: +(N0 / sampleRate).toFixed(2),
        codaSec: +(L / sampleRate).toFixed(2),
        rumoreFondoDb: null,
        clipping,
        piccoDb,
        ...armonico,
      };
    }
  }

  /* il giudice del soffio parla DOPO la via armonica: chi e'
     intonato e' gia' uscito, e qui si puo' essere severi */
  if (picco >= 0.01 && !_qualcosaDiFermo(campioni, da, L, sampleRate)) {
    return verdettoSoffio();
  }

  /* rapporto e scarto in cents dall'armonico teorico piu' vicino */
  for (const p of tenuti) {
    p.rapporto = p.hz / fondo.hz;
    const arm = Math.max(1, Math.round(p.rapporto));
    p.cents = Math.round(1200 * Math.log2(p.rapporto / arm));
  }

  return {
    versione: 1,
    natura: 'modi',
    sampleRate,
    durataSec: +(N0 / sampleRate).toFixed(2),
    codaSec: +(L / sampleRate).toFixed(2),
    continuo,
    clipping,
    piccoDb,
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

/* due FFT corte, agli estremi del segmento: i 3 picchi piu' forti
   della prima devono ritrovarsi (entro 3 Hz o lo 0,5%) fra i 6 piu'
   forti della seconda — ne basta UNO fermo per dire «non e' un
   soffio». Le finestre sono ADIACENTI, non agli estremi (quarto
   giro, misurato: una lattina ha modi che vivono mezzo secondo — a
   fine registrazione erano gia' morti e passava per soffio; il
   periodogramma di un rumore e' indipendente anche fra finestre
   attaccate, quindi l'adiacenza non regala stabilita' al vento). */
function _qualcosaDiFermo(campioni, da, L, sampleRate) {
  const W = 1 << 15;                              // ~0,74 s
  if (L < W * 2) return true;                     // troppo corto per giudicare
  const cime = (inizio) => {
    const re = new Float64Array(W), im = new Float64Array(W);
    for (let i = 0; i < W; i++) {
      const h = 0.5 - 0.5 * Math.cos((2 * Math.PI * i) / (W - 1));
      re[i] = campioni[inizio + i] * h;
    }
    fft(re, im);
    const hzB = sampleRate / W;
    const b0 = Math.max(2, Math.floor(FIN_MIN / hzB));
    const b1 = Math.min(W / 2 - 2, Math.ceil(FIN_MAX / hzB));
    const m = new Float64Array(b1 + 2);
    for (let b = b0 - 1; b <= b1 + 1; b++) m[b] = db(Math.hypot(re[b], im[b]));
    const trovate = [];
    for (let b = b0 + 8; b <= b1 - 8; b++) {
      const v = m[b];
      let cima = true;
      for (let k = 1; k <= 8; k++) {
        if (m[b - k] > v || m[b + k] > v) { cima = false; break; }
      }
      if (cima) trovate.push({ hz: b * hzB, db: v });
    }
    trovate.sort((x, y) => y.db - x.db);
    return trovate;
  };
  const prime = cime(da).slice(0, 3);
  const seconde = cime(da + W).slice(0, 6);

  /* QUINTO GIRO (respiro sintetico, misurato): un rumore a BANDA
     STRETTA concentra le cime in pochi bin e per caso «combacia»
     fra le due finestre. L'ultima parola ce l'ha la COERENZA: un
     modo vero decade LISCIO (i dB seguono una retta), l'ampiezza di
     un rumore filtrato sfarfalla di ±5 dB anche in un terzo di
     secondo. Dieci Goertzel corti sul candidato, fit lineare,
     residuo: sopra i 4 dB di scarto non e' un modo. La finestra
     corta (0,18 s → lobo ~5 Hz) perdona il vibrato di una voce. */
  const coerente = (hz) => {
    const Wg = 8192, quante = 12;
    if (L < Wg * 5) return true;         // troppo breve per giudicare
    const dbs = [];
    for (let k = 0; k < quante && da + (k + 1) * Wg <= da + L; k++) {
      dbs.push(db(goertzel(campioni, da + k * Wg, Wg, sampleRate, hz)));
    }
    /* SESTO GIRO (lattina, misurato): quando il modo muore nel
       rumore la serie fa un GINOCCHIO — retta ripida poi plateau —
       e il fit lineare esplodeva. Si giudica solo il tratto VIVO:
       la serie si tronca appena scende 40 dB sotto il suo massimo. */
    const massimo = Math.max(...dbs);
    let vivi = dbs.length;
    for (let k = 0; k < dbs.length; k++) {
      if (dbs[k] < massimo - 40) { vivi = k; break; }
    }
    const serie = dbs.slice(0, vivi);
    if (serie.length < 4) return true;   // vissuto troppo poco: gia' provato dal match
    const n = serie.length;
    let sx = 0, sy = 0, sxx = 0, sxy = 0;
    for (let k = 0; k < n; k++) {
      sx += k; sy += serie[k]; sxx += k * k; sxy += k * serie[k];
    }
    const m = (n * sxy - sx * sy) / (n * sxx - sx * sx || 1);
    const q = (sy - m * sx) / n;
    let res = 0;
    for (let k = 0; k < n; k++) {
      const e = serie[k] - (m * k + q);
      res += e * e;
    }
    /* 3,2 dB: i modi veri (vibrato perdonato dal lobo largo, e il
       battimento di un doppietto assorbito in parte dalla retta)
       stanno sotto; il rumore filtrato sfarfalla a 4-6. La soglia
       puo' essere severa perche' i suoni INTONATI escono dalla via
       armonica PRIMA di arrivare da questo giudice. */
    return Math.sqrt(res / n) <= 2.6;
  };

  return prime.some((p) => seconde.some((q) =>
    Math.abs(q.hz - p.hz) <= Math.max(3, p.hz * 0.005)) && coerente(p.hz));
}

/* Una nota che VIAGGIA cambia con continuita'; i modi di un oggetto
   fanno saltare il tracker. Rapporto fra fotogrammi contigui,
   ripiegato nell'ottava (2:1 e 1:2 sono errori del tracker, non
   salti); fuori da [0,8 · 1,25] e' un salto. */
function _notaCheViaggia(traccia) {
  let salti = 0, coppie = 0;
  for (let f = 1; f < traccia.length; f++) {
    const a = traccia[f - 1], b = traccia[f];
    if (a === null || b === null) continue;
    coppie++;
    let r = b / a;
    while (r > 1.4142) r /= 2;
    while (r < 0.7071) r *= 2;
    if (r > 1.25 || r < 0.8) salti++;
  }
  return coppie === 0 || salti / coppie <= 0.25;
}

/* I due gradini piu' frequentati del tracker (gruppi entro ±6%) e
   la loro SIMULTANEITA': Goertzel per fotogramma a entrambe le
   frequenze, «presente» = entro 25 dB dal proprio massimo. Se in
   almeno il 60% dei fotogrammi ci sono TUTTI E DUE, suonano insieme:
   e' un oggetto con due modi, non una nota che cambia. Un solo
   gradino (un glissando, un parlato che scorre) non e' giudicabile
   qui e resta una nota che viaggia. */
function _gradiniSimultanei(campioni, da, L, sampleRate, intonati) {
  const ordinati = [...intonati].sort((a, b) => a - b);
  const gruppi = [];
  for (const v of ordinati) {
    const u = gruppi[gruppi.length - 1];
    if (u && v <= u.centro * 1.06) { u.n++; u.somma += v; u.centro = u.somma / u.n; }
    else gruppi.push({ n: 1, somma: v, centro: v });
  }
  gruppi.sort((a, b) => b.n - a.n);
  if (gruppi.length < 2) return false;
  const gA = gruppi[0].centro;
  /* il secondo gradino e' il piu' frequentato fra quelli LONTANI dal
     primo: i passi contigui di una nota che scorre (meno di 1,25, un
     terzo maggiore) e le letture d'ottava del tracker (2:1, 4:1) non
     sono un secondo modo — i modi di una campana stanno a 2,7 e
     oltre l'uno dall'altro. Le letture sparse del fondamentale di
     una campana forte (97-114 Hz) restano cosi' un gradino solo. */
  let gB = null;
  for (const g of gruppi.slice(1)) {
    const r = Math.max(gA, g.centro) / Math.min(gA, g.centro);
    if (r < 1.25 || Math.abs(r - 2) < 0.06 || Math.abs(r - 4) < 0.12) continue;
    gB = g; break;
  }
  if (!gB || gB.n < intonati.length * 0.15) return false;
  gB = gB.centro;
  /* un GLISSANDO passa per tutte le altezze fra i due gradini (e la
     dispersione spettrale di un tono che scivola fa sembrare
     «presenti» due frequenze vicine): se il tracker ha visitato la
     zona in mezzo, non sono gradini, e' una nota che scorre */
  const lo = Math.min(gA, gB) * 1.25, hi = Math.max(gA, gB) / 1.25;
  if (hi > lo) {
    const fra = intonati.filter((v) => v > lo && v < hi).length;
    if (fra > intonati.length * 0.1) return false;
  }
  const finestra = 4096, passo = 2048;
  const quanti = Math.floor((L - finestra) / passo);
  if (quanti < 8) return false;
  const serie = (hz) => {
    const out = [];
    for (let f = 0; f < quanti; f++) {
      out.push(db(goertzel(campioni, da + f * passo, finestra, sampleRate, hz)));
    }
    const max = Math.max(...out);
    return out.map((v) => v > max - 25);
  };
  const pA = serie(gA), pB = serie(gB);
  let insieme = 0;
  for (let f = 0; f < quanti; f++) if (pA[f] && pB[f]) insieme++;
  return insieme / quanti >= 0.6;
}

/* Picchi entro `hz` l'uno dall'altro diventano UNO (resta il piu'
   forte): e' cosi' che le bande laterali del vibrato tornano a essere
   la loro armonica. */
function _raggruppa(picchi, hz) {
  const gruppi = [];
  for (const p of [...picchi].sort((a, b) => a.hz - b.hz)) {
    const u = gruppi[gruppi.length - 1];
    if (u && p.hz - u.hz < hz) {
      if (p.db > u.db) { u.hz = p.hz; u.db = p.db; }
    } else gruppi.push({ hz: p.hz, db: p.db });
  }
  return gruppi;
}

/* Il decadere della coda: energia del primo terzo contro l'ultimo
   terzo, in dB. Sopra i 12 dB di caduta il suono e' stato COLPITO. */
function _decade(campioni, da, L) {
  const terzo = Math.floor(L / 3);
  if (terzo < 2048) return false;
  const rms = (inizio) => {
    let s = 0;
    for (let i = 0; i < terzo; i++) s += campioni[inizio + i] * campioni[inizio + i];
    return Math.sqrt(s / terzo);
  };
  return db(rms(da)) - db(rms(da + 2 * terzo)) > 12;
}

function _viaArmonica(campioni, da, L, sampleRate, picchiFft) {
  const finestra = 4096, passo = 2048;
  const quanti = Math.floor((L - finestra) / passo);
  if (quanti < 8) return null;

  /* la fondamentale, fotogramma per fotogramma */
  const traccia = [];
  for (let f = 0; f < quanti; f++) {
    const fetta = campioni.subarray(da + f * passo, da + f * passo + finestra);
    const r = fondamentale(fetta, sampleRate);
    traccia.push(r ? r.hz : null);
  }
  const intonati = traccia.filter((x) => x !== null);
  if (intonati.length < quanti * 0.6) return null;   // non e' un suono intonato

  const ordinati = [...intonati].sort((a, b) => a - b);
  const f0 = ordinati[Math.floor(ordinati.length / 2)];
  if (!f0 || f0 < 40) return null;

  /* LA MELODIA: se la fondamentale VIAGGIA (piu' del 12%: ben oltre
     ogni vibrato) non e' una nota tenuta — e' una melodia o un
     parlato. Il ritratto fotografa UN istante: si dice cosa si e'
     sentito (da nota a nota) e si insegna il gesto giusto. */
  const e5 = ordinati[Math.floor(ordinati.length * 0.05)];
  const e95 = ordinati[Math.floor(ordinati.length * 0.95)];
  if ((e95 - e5) / f0 > 0.12) {
    /* LA CAMPANA FORTE (LM1, 5/9/2026 — referto del founder dal
       telefono: «suonata forte dice che sembra una voce»). Riprodotto
       al banco: con un colpo forte gli acuti valgono quanto il
       fondamentale e i doppietti li fanno pulsare, cosi'
       l'autocorrelazione SALTA fra i modi e i loro sottoperiodi (73,
       214, 575 Hz) da un fotogramma all'altro — e lo spread passava
       per «la nota si muove». Una voce o una melodia si muovono con
       CONTINUITA': fotogrammi di 43 ms vicini l'uno all'altro (anche
       un salto di quinta cantato e' UN salto ogni tanti fotogrammi).
       Gli errori d'ottava del tracker si ripiegano prima di contare.
       Se piu' di un quarto dei passi contigui e' un salto, non e' una
       nota che viaggia: e' un oggetto con piu' modi, e si torna alla
       via dei modi. */
    if (!_notaCheViaggia(traccia)) return null;
    /* LA CAMPANA GRAVE (stesso referto, misurato al banco su una
       campana a 110 Hz): il tracker non salta a ogni fotogramma, si
       FERMA a turno su un modo e sull'altro (110 per un po', poi 298,
       poi 110) — otto salti in sessanta passi, e la continuita' non
       basta. La fisica che decide e' la SIMULTANEITA': in una
       campana i due modi suonano INSIEME in ogni istante (il 298
       vibra mentre il 110 vibra); in una melodia le note vengono UNA
       DOPO L'ALTRA. Si prendono i due gradini piu' frequentati del
       tracker e si misura, fotogramma per fotogramma, se l'energia
       c'e' a entrambe le frequenze nello stesso momento. */
    if (_gradiniSimultanei(campioni, da, L, sampleRate, intonati)) return null;
    return { mutevole: true, f0minHz: +e5.toFixed(1), f0maxHz: +e95.toFixed(1) };
  }

  /* il suono deve DAVVERO stare sulla serie armonica: i picchi FFT
     forti devono cadere vicino a un multiplo di f0 (un bordone di
     due toni scorrelati non passa di qui).
     LM1 (5/9): le bande laterali del vibrato (±4-10 Hz attorno a ogni
     armonica, forti quanto l'armonica su una FFT lunga) NON sono
     picchi a se' — contate una per una bocciavano una voce tenuta con
     vibrato (9 su 16 «sul posto», misurato al banco). Entro 15 Hz si
     raggruppano e resta il piu' forte del gruppo. */
  const forti = _raggruppa(picchiFft.filter((p) => p.db >= -30), 15);
  if (forti.length) {
    /* LM1: il vibrato allarga la k-esima armonica di k volte la sua
       profondita' (misurata dal tracker: (e95−e5)/2). Su una FFT
       lunga il picco dell'armonica cade su una banda laterale, fino
       a k·profondita' dal multiplo esatto: la tolleranza lo sa. Una
       campana ferma ha spread quasi nullo e non ne guadagna. */
    const larghezzaVib = (e95 - e5) / 2;
    const sopra = forti.filter((p) => {
      const k = Math.max(1, Math.round(p.hz / f0));
      return Math.abs(p.hz - k * f0) <= Math.max(4, f0 * 0.04) + k * larghezzaVib;
    });
    if (sopra.length / forti.length < 0.7) return null;
  }

  /* il VIBRATO: quanto oscilla la fondamentale, e quanto in fretta */
  const profonditaHz = +((e95 - e5) / 2).toFixed(2);
  let giri = 0;
  let sopraMedia = null;
  for (const hz of intonati) {
    const ora = hz > f0;
    if (sopraMedia !== null && ora !== sopraMedia) giri++;
    sopraMedia = ora;
  }
  const secondi = (quanti * passo) / sampleRate;
  const rateHz = +((giri / 2) / secondi).toFixed(1);
  const vibrato = profonditaHz >= 0.3
    ? { profonditaHz, rateHz } : null;

  /* le armoniche: Goertzel a k·f0 INSEGUENDO la fondamentale del
     fotogramma (cosi' il vibrato non diluisce la misura), mediana
     sui fotogrammi intonati */
  const parziali = [];
  let piuForte = -Infinity;
  for (let k = 1; k <= PARZIALI_MAX && k * f0 < FIN_MAX; k++) {
    const ampiezze = [];
    for (let f = 0; f < quanti; f++) {
      if (traccia[f] === null) continue;
      ampiezze.push(goertzel(campioni, da + f * passo, finestra,
        sampleRate, k * traccia[f]));
    }
    if (!ampiezze.length) continue;
    ampiezze.sort((a, b) => a - b);
    const dbK = db(ampiezze[Math.floor(ampiezze.length / 2)]);
    if (dbK > piuForte) piuForte = dbK;
    parziali.push({ hz: +(k * f0).toFixed(2), grezzo: dbK, rapporto: k });
  }
  const tenute = parziali
    .map((p) => ({ hz: p.hz, db: +(p.grezzo - piuForte).toFixed(1),
                   rapporto: p.rapporto, cents: 0, t60: null,
                   doppietto: null }))
    .filter((p) => p.db >= -50);
  if (tenute.length < 2) return null;

  return {
    fondamentaleHz: +f0.toFixed(2),
    vibrato,
    parziali: tenute,
  };
}

/* banco di prova: l'analisi si collauda dalla console con una campana
   sintetica, senza microfono ne' permessi */
try { window.__fqzRitratto = { analizza, fft }; } catch { /* SSR/test */ }
