/**
 * SPETTRO — il dominio delle frequenze (STEP 3, 26/8/2026).
 *
 * Stesso contratto dell'Oscilloscopio, alla lettera: importa React e
 * il quadro, riceve `ottieniAnalisi`, non conosce il generatore, non
 * possiede nodi audio, non ha un ciclo suo. Il motore non e' stato
 * toccato: `analisi.spettro()` (getFloatFrequencyData) e
 * `analisi.hzPerBin` esistevano gia' dallo STEP 1.
 *
 * DUE SCELTE che separano uno strumento da un grafico:
 *
 * 1. SI DISEGNA PER PIXEL, NON PER BIN. Su scala logaritmica i bin
 *    sono distribuiti male: sotto i 200 Hz una colonna di schermo
 *    contiene MENO di un bin (e a disegnare per bin restano buchi),
 *    sopra i 5 kHz ne contiene decine (e disegnandone uno solo si
 *    perdono i picchi). Per ogni colonna si prende il MASSIMO dei bin
 *    che le competono — un picco stretto non puo' sparire per
 *    arrotondamento.
 *
 * 2. IL PICCO SI LEGGE PER DAVVERO. La FFT ha passo ~5,4 Hz: il bin
 *    piu' alto da solo direbbe «137,9» per un tono a 137,42. Con
 *    l'interpolazione parabolica sui tre bin attorno al massimo si
 *    ricostruisce il vertice vero e l'etichetta dice «137,4». E'
 *    questa cifra che rende il Lab credibile.
 *
 * La verticale usa la finestra dell'analyser stesso (min/maxDecibels):
 * niente normalizzazione inventata, la scala e' quella dichiarata dal
 * nodo che misura.
 */
import React, { useEffect, useRef, useState } from 'react';
import { iscrivi, dprTela, economia } from './quadro';

const F_MIN = 20;               // sotto non c'e' udito, e la log esplode
const MARGINE_BASSO = 18;       // spazio per le etichette dell'asse

/* LA FINESTRA VERTICALE, in dBFS (0 = fondo scala del segnale).
 *
 * Primo tentativo sbagliato, corretto dalla misura: avevo usato
 * `analyser.min/maxDecibels`. Quelle due proprieta' governano SOLO la
 * conversione a byte (getByteFrequencyData); i dati float arrivano in
 * dBFS a prescindere. Col tetto di fabbrica a −30 dB ogni livello
 * sopra un quarto d'ampiezza finiva schiacciato in cima e cambiare
 * l'ampiezza non muoveva NULLA sullo schermo. Qui la scala e' quella
 * vera del segnale: −96 (silenzio a 16 bit) → 0 (fondo scala). */
const DB_MIN = -96, DB_MAX = 0;

/* vertice del picco con interpolazione parabolica sui tre bin:
   restituisce l'indice frazionario, non quello intero */
function vertice(db, k) {
  const a = db[k - 1], b = db[k], c = db[k + 1];
  if (!isFinite(a) || !isFinite(c)) return k;
  const den = a - 2 * b + c;
  if (!den) return k;
  const d = (0.5 * (a - c)) / den;
  return k + (Math.abs(d) < 1 ? d : 0);
}

const scriviHz = (hz) => (hz >= 1000
  ? `${(hz / 1000).toFixed(hz >= 10000 ? 1 : 2).replace('.', ',')} kHz`
  : `${hz.toFixed(hz < 100 ? 2 : 1).replace('.', ',')} Hz`);

export default function Spettro({ ottieniAnalisi, fermo }) {
  const telaRef = useRef(null);
  const dbRef = useRef(null);          // ultimo spettro acquisito
  const hzBinRef = useRef(0);
  const fMaxRef = useRef(0);
  /* il picco vive in un ref per il DISEGNO (che gira a ogni frame) e
     in uno stato solo per l'ETICHETTA: se finisse nelle dipendenze
     dell'effetto, il pittore si re-iscriverebbe sessanta volte al
     secondo. L'etichetta si aggiorna a scatti di un decimo di Hz,
     cosi' React lavora quando serve e la cifra non tremola. */
  const piccoRef = useRef(null);
  const [picco, setPicco] = useState(null);

  useEffect(() => {
    const tela = telaRef.current;
    const c2d = tela.getContext('2d');
    let tinte = null;

    const dipingi = (fermo) => {
      const dpr = dprTela();
      const W = Math.round(tela.clientWidth * dpr);
      const H = Math.round(tela.clientHeight * dpr);
      if (tela.width !== W || tela.height !== H) {
        tela.width = W; tela.height = H; tinte = null;
      }
      if (!W || !H) return;
      if (!tinte) {
        const s = getComputedStyle(tela);
        tinte = {
          griglia: s.getPropertyValue('--line-soft').trim() || '#1B2E32',
          asse: s.getPropertyValue('--line').trim() || '#23393D',
          traccia: s.getPropertyValue('--water').trim() || '#66B79C',
          fermo: s.getPropertyValue('--lamp').trim() || '#C9B37E',
          nota: s.getPropertyValue('--dimmer').trim() || '#86A0A4',
        };
      }

      const analisi = ottieniAnalisi();
      const dbMin = DB_MIN, dbMax = DB_MAX;
      if (analisi) {
        if (!fermo) {
          const N = analisi.analyser.frequencyBinCount;
          if (!dbRef.current || dbRef.current.length !== N) {
            dbRef.current = new Float32Array(N);
          }
          analisi.spettro(dbRef.current);
          hzBinRef.current = analisi.hzPerBin;
          fMaxRef.current = analisi.analyser.context.sampleRate / 2;

          /* il picco, letto col vertice della parabola */
          const db = dbRef.current;
          let k = 1;
          for (let i = 2; i < db.length - 1; i++) if (db[i] > db[k]) k = i;
          const trovato = db[k] > dbMin + 3
            ? { hz: vertice(db, k) * analisi.hzPerBin, db: db[k] }
            : null;                       // silenzio: nessuna bugia
          const prima = piccoRef.current;
          piccoRef.current = trovato;
          if (!trovato !== !prima
              || (trovato && Math.abs(trovato.hz - prima.hz) > 0.1)) {
            setPicco(trovato);
          }
        }
      }

      const db = dbRef.current;
      const hzBin = hzBinRef.current;
      const fMax = fMaxRef.current || 22050;
      const HG = H - MARGINE_BASSO * dpr;                 // altezza del grafico
      const lo = Math.log10(F_MIN), hi = Math.log10(fMax);
      const xDaHz = (hz) => ((Math.log10(hz) - lo) / (hi - lo)) * W;
      const hzDaX = (x) => Math.pow(10, lo + (x / W) * (hi - lo));
      const yDaDb = (v) => HG - ((v - dbMin) / (dbMax - dbMin)) * HG;

      c2d.clearRect(0, 0, W, H);

      /* griglia: le decadi (100, 1k, 10k) piu' i loro passi, sottilissima */
      c2d.lineWidth = 1;
      c2d.strokeStyle = tinte.griglia;
      c2d.beginPath();
      const tacche = [];
      for (let dec = 1; dec <= 5; dec++) {
        for (let m = 1; m <= 9; m++) {
          const hz = m * Math.pow(10, dec);
          if (hz < F_MIN || hz > fMax) continue;
          tacche.push({ hz, forte: m === 1 });
          const x = Math.round(xDaHz(hz)) + 0.5;
          c2d.moveTo(x, 0); c2d.lineTo(x, HG);
        }
      }
      for (let q = 1; q < 4; q++) {                        // quattro fasce in dB
        const y = Math.round((HG * q) / 4) + 0.5;
        c2d.moveTo(0, y); c2d.lineTo(W, y);
      }
      c2d.stroke();
      c2d.strokeStyle = tinte.asse;                        // la linea di fondo
      c2d.beginPath();
      c2d.moveTo(0, HG + 0.5); c2d.lineTo(W, HG + 0.5);
      c2d.stroke();

      /* la traccia: una colonna per pixel, col MASSIMO dei suoi bin.
         LB7 — la cresta ha un filo di bagliore e l'area sotto si
         spegne in gradiente verso il fondo: presenza, non neon. */
      c2d.lineWidth = Math.max(1.25, 1.25 * dpr);
      /* giunture tonde: sulle creste piu' acute lo spigolo di fabbrica
         allunga la punta oltre il vertice. Qui la differenza e' di
         frazioni di pixel — si tiene per prudenza, non per rimediare
         a un difetto misurato. */
      c2d.lineJoin = 'round';
      c2d.lineCap = 'round';
      c2d.strokeStyle = fermo ? tinte.fermo : tinte.traccia;
      c2d.beginPath();
      if (db && hzBin) {
        let primo = true;
        for (let x = 0; x <= W; x++) {
          const f0 = hzDaX(x - 0.5), f1 = hzDaX(x + 0.5);
          let k0 = Math.floor(f0 / hzBin), k1 = Math.ceil(f1 / hzBin);
          if (k1 <= k0) k1 = k0 + 1;                       // sotto: almeno un bin
          k0 = Math.max(0, Math.min(k0, db.length - 1));
          k1 = Math.max(k0 + 1, Math.min(k1, db.length));
          let v = -Infinity;
          for (let k = k0; k < k1; k++) if (db[k] > v) v = db[k];
          const y = yDaDb(Math.max(dbMin, Math.min(dbMax, v)));
          if (primo) { c2d.moveTo(x, y); primo = false; } else c2d.lineTo(x, y);
        }
      } else {
        c2d.moveTo(0, HG); c2d.lineTo(W, HG);              // banco spento
      }
      if (!economia()) {                     // LM3: niente bagliore sul telefono
        c2d.shadowBlur = 5 * dpr;
        c2d.shadowColor = fermo ? tinte.fermo : tinte.traccia;
      }
      c2d.stroke();
      c2d.shadowBlur = 0;
      /* l'area sotto la traccia: gradiente che si spegne verso il fondo */
      if (db && hzBin) {
        c2d.lineTo(W, HG); c2d.lineTo(0, HG); c2d.closePath();
        const velo = c2d.createLinearGradient(0, 0, 0, HG);
        const base = fermo ? tinte.fermo : tinte.traccia;
        velo.addColorStop(0, base + '59');      // ~35% in cima
        velo.addColorStop(1, base + '00');      // nulla sul fondo
        c2d.fillStyle = velo;
        c2d.fill();
      }

      /* le etichette dell'asse: solo le decadi, mono e discrete */
      c2d.fillStyle = tinte.nota;
      c2d.font = `${Math.round(9 * dpr)}px ui-monospace, Menlo, monospace`;
      c2d.textBaseline = 'top';
      tacche.filter((t) => t.forte).forEach((t) => {
        const testo = t.hz >= 1000 ? `${t.hz / 1000}k` : `${t.hz}`;
        const x = xDaHz(t.hz);
        c2d.textAlign = x < 12 * dpr ? 'left' : (x > W - 12 * dpr ? 'right' : 'center');
        c2d.fillText(testo, Math.min(Math.max(x, 1), W - 1), HG + 5 * dpr);
      });

      /* il picco: una tacca CORTA sopra la cresta, in oro. Prima era
         una linea per tutta l'altezza: troppo inchiostro per un'unica
         informazione, e per giunta attraversava la traccia. La cifra
         esatta sta gia' sotto, nella riga dei numeri. */
      if (piccoRef.current && db) {
        const x = xDaHz(Math.max(F_MIN, piccoRef.current.hz));
        const yPicco = yDaDb(Math.max(dbMin, Math.min(dbMax, piccoRef.current.db)));
        c2d.strokeStyle = tinte.fermo;
        c2d.beginPath();
        c2d.moveTo(x, yPicco - 4 * dpr);
        c2d.lineTo(x, yPicco - 11 * dpr);
        c2d.stroke();
        /* LB7 — la quota accanto alla tacca: lo strumento risponde
           dove guardi, senza cercare la riga dei numeri */
        const testo = piccoRef.current.hz >= 1000
          ? `${(piccoRef.current.hz / 1000).toFixed(2).replace('.', ',')}k`
          : piccoRef.current.hz.toFixed(1).replace('.', ',');
        c2d.fillStyle = tinte.fermo;
        c2d.font = `${Math.round(10 * dpr)}px ui-monospace, Menlo, monospace`;
        c2d.textBaseline = 'bottom';
        c2d.textAlign = x > W - 60 * dpr ? 'right' : 'left';
        c2d.fillText(testo, x + (x > W - 60 * dpr ? -5 : 5) * dpr,
          Math.max(12 * dpr, yPicco - 13 * dpr));
      }
    };

    return iscrivi(dipingi);
  }, [ottieniAnalisi]);

  return (
    <section className="lab-card lab-scope" data-testid="lab-spettro">
      <div className="lab-chead">
        <h2>Spettro</h2>
        <span className="lab-cnote">le frequenze che compongono il segnale</span>
      </div>
      <canvas ref={telaRef} className="lab-tela" role="img"
        aria-label="Spettro: le frequenze presenti nel segnale" />
      <div className="lab-scope-info">
        <span>scala logaritmica · {F_MIN} Hz → Nyquist</span>
        <span data-testid="lab-picco" className="lab-picco">
          {fermo ? 'immagine ferma, il suono continua'
            : picco ? `picco ${scriviHz(picco.hz)}` : 'nessun picco'}
        </span>
        <span>ampiezza in dB</span>
      </div>
    </section>
  );
}
