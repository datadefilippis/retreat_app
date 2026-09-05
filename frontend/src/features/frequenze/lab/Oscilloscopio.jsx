/**
 * OSCILLOSCOPIO — il dominio del tempo (STEP 2, 26/8/2026).
 *
 * Disegna i campioni VERI dell'analyser (getFloatTimeDomainData via
 * analisi.tempo): se il DAC riproduce X, questa tela mostra X. Nessuna
 * onda decorativa.
 *
 * Il pannello riceve `ottieniAnalisi` e NON conosce il generatore:
 * quando il motore osservera' un microfono (analisi.sorgente(mic)),
 * questa tela lo disegnera' senza cambiare una riga — e' il contratto
 * architetturale del Lab, ed e' sotto guardia.
 *
 * IL TRIGGER e' cio' che lo rende uno strumento: senza, la traccia
 * parte da un campione arbitrario e l'onda «scorre». Qui si cerca un
 * attraversamento dello zero IN SALITA con isteresi (ci si arma sotto
 * −h, si scatta al ritorno sopra lo zero): la sinusoide sta ferma
 * come su un oscilloscopio vero. L'isteresi e' adattiva (frazione del
 * picco) cosi' il rumore di fondo non fa scattare a vuoto.
 *
 * FREEZE ferma il DISEGNO, mai il suono: da congelato si smette di
 * acquisire ma si continua a ridipingere l'ultimo buffer — cosi' un
 * ridimensionamento non cancella la traccia ferma.
 *
 * Un solo ciclo per tutto il banco: il pittore si iscrive al quadro.
 */
import React, { useEffect, useRef, useState } from 'react';
import { iscrivi, dprTela, economia } from './quadro';

const FINESTRA = 2048;          // campioni a schermo: a 44.1k ≈ 46 ms
const MARGINE_Y = 0.88;         // ±1 non tocca i bordi

/* zero-crossing in salita con isteresi adattiva.
   Ritorna l'indice di partenza e se l'aggancio e' riuscito. */
/* Esportato per OndaViva (Ritratto): l'aggancio e' UNA verita',
   non due copie che derivano. */
export function trigger(buf) {
  const fine = buf.length - FINESTRA;
  let picco = 0;
  for (let i = 0; i < fine; i++) {
    const a = Math.abs(buf[i]);
    if (a > picco) picco = a;
  }
  const h = Math.max(0.004, picco * 0.08);
  let armato = false;
  for (let i = 0; i < fine; i++) {
    if (buf[i] < -h) armato = true;
    else if (armato && buf[i] >= 0) return { da: i, ok: true };
  }
  return { da: 0, ok: false };            // corsa libera: silenzio o DC
}

export default function Oscilloscopio({ ottieniAnalisi, fermo, ottieniXY = null }) {
  const telaRef = useRef(null);
  const acqRef = useRef(null);            // l'ultimo buffer acquisito
  const daRef = useRef(0);                // indice del trigger nel buffer
  const srRef = useRef(0);
  const [aggancio, setAggancio] = useState(false);
  const [vivo, setVivo] = useState(false);
  /* LB1 — il MODO: 'tempo' e' l'oscilloscopio di sempre; 'xy' mette
     la sorgente A sull'asse X e la B sulla Y — le figure di
     Lissajous. Il modo vive in un ref per il pittore (che non deve
     ri-iscriversi) e in uno stato per i bottoni. */
  const [modo, setModo] = useState('tempo');
  const modoRef = useRef('tempo');
  const xyARef = useRef(null);
  const xyBRef = useRef(null);

  useEffect(() => {
    const tela = telaRef.current;
    const c2d = tela.getContext('2d');
    let tinte = null;                     // i colori della palette, letti una volta
    /* LB7 — LA SCIA AL FOSFORO: le tracce vecchie non spariscono di
       colpo, sbiadiscono — come sui tubi a fosfori veri. Non e'
       decorazione: la scia E' informazione (un segnale stabile lascia
       una scia sottile, uno che cambia la allarga). Vive su un livello
       fuori schermo: si sbiadisce con un velo di destination-out, ci
       si disegna la traccia col bagliore, e il quadro compone griglia
       nitida + scia + traccia viva. */
    const scia = document.createElement('canvas');
    const sciaC2d = scia.getContext('2d');

    const dipingi = (fermo) => {
      /* la tela segue la card (responsive), in pixel veri */
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
        };
      }

      /* ── modo XY (LB1): A sull'asse X, B sulla Y ── */
      if (modoRef.current === 'xy') {
        const xy = ottieniXY && ottieniXY();
        if (!tinte) return;
        if (xy && !fermo) {
          const N = 2048;
          if (!xyARef.current) { xyARef.current = new Float32Array(N); xyBRef.current = new Float32Array(N); }
          xy.a(xyARef.current); xy.b(xyBRef.current);
        }
        c2d.clearRect(0, 0, W, H);
        c2d.lineWidth = 1;
        c2d.strokeStyle = tinte.griglia;
        c2d.beginPath();                       // la croce degli assi
        c2d.moveTo(W / 2, 0); c2d.lineTo(W / 2, H);
        c2d.moveTo(0, H / 2); c2d.lineTo(W, H / 2);
        c2d.stroke();
        const A = xyARef.current, B = xyBRef.current;
        if (A && B) {
          const lato = Math.min(W, H) / 2 * MARGINE_Y;
          c2d.lineWidth = Math.max(1.25, 1.25 * dpr);
          c2d.strokeStyle = fermo ? tinte.fermo : tinte.traccia;
          c2d.beginPath();
          for (let i = 0; i < A.length; i++) {
            const x = W / 2 + A[i] * lato;
            const y = H / 2 - B[i] * lato;
            if (i === 0) c2d.moveTo(x, y); else c2d.lineTo(x, y);
          }
          c2d.stroke();
        }
        return;
      }

      /* acquisizione, salvo che da congelati */
      const analisi = ottieniAnalisi();
      if (analisi && !fermo) {
        const N = analisi.analyser.fftSize;
        if (!acqRef.current || acqRef.current.length !== N) {
          acqRef.current = new Float32Array(N);
        }
        analisi.tempo(acqRef.current);
        const t = trigger(acqRef.current);
        daRef.current = t.da;
        setAggancio(t.ok);                // React salta i re-render uguali
        srRef.current = analisi.analyser.context.sampleRate;
        setVivo(true);
      }

      /* griglia: molto discreta, l'asse dello zero, ±½, otto tempi */
      c2d.clearRect(0, 0, W, H);
      c2d.lineWidth = 1;
      c2d.strokeStyle = tinte.griglia;
      c2d.beginPath();
      [0.25, 0.75].forEach((q) => {       // ±0.5 di ampiezza
        const y = H / 2 + (q * 2 - 1) * (H / 2) * MARGINE_Y;
        c2d.moveTo(0, y); c2d.lineTo(W, y);
      });
      for (let k = 1; k < 8; k++) {
        const x = (W * k) / 8;
        c2d.moveTo(x, 0); c2d.lineTo(x, H);
      }
      c2d.stroke();
      c2d.strokeStyle = tinte.asse;       // lo zero, appena piu' presente
      c2d.beginPath(); c2d.moveTo(0, H / 2); c2d.lineTo(W, H / 2); c2d.stroke();

      /* la traccia, prima sulla scia (che sbiadisce), poi viva */
      if (scia.width !== W || scia.height !== H) {
        scia.width = W; scia.height = H;
      }
      const buf = acqRef.current;
      const traccia = (ctx2, spessore, colore, bagliore) => {
        ctx2.lineWidth = spessore;
        ctx2.strokeStyle = colore;
        ctx2.lineJoin = 'round'; ctx2.lineCap = 'round';
        if (bagliore && !economia()) { ctx2.shadowBlur = 6 * dpr; ctx2.shadowColor = colore; }
        ctx2.beginPath();
        if (buf) {
          const da = daRef.current;
          for (let i = 0; i < FINESTRA; i++) {
            const v = buf[da + i] || 0;
            const x = (i / (FINESTRA - 1)) * W;
            const y = H / 2 - v * (H / 2) * MARGINE_Y;
            if (i === 0) ctx2.moveTo(x, y); else ctx2.lineTo(x, y);
          }
        } else {
          ctx2.moveTo(0, H / 2); ctx2.lineTo(W, H / 2);   // banco spento
        }
        ctx2.stroke();
        ctx2.shadowBlur = 0;
      };
      if (!fermo) {
        /* la scia sbiadisce di un velo a ogni giro, poi accoglie la
           traccia nuova gia' col suo bagliore */
        sciaC2d.globalCompositeOperation = 'destination-out';
        sciaC2d.globalAlpha = 0.22;
        sciaC2d.fillRect(0, 0, W, H);
        sciaC2d.globalAlpha = 1;
        sciaC2d.globalCompositeOperation = 'source-over';
        if (buf) traccia(sciaC2d, Math.max(1, 1 * dpr), tinte.traccia, true);
      }
      c2d.globalAlpha = 0.55;
      c2d.drawImage(scia, 0, 0);
      c2d.globalAlpha = 1;
      traccia(c2d, Math.max(1.25, 1.25 * dpr),
        fermo ? tinte.fermo : tinte.traccia, !fermo);
    };

    return iscrivi(dipingi);
  }, [ottieniAnalisi, ottieniXY]);

  const ms = srRef.current ? ((FINESTRA / srRef.current) * 1000).toFixed(1).replace('.', ',') : null;

  return (
    <section className="lab-card lab-scope" data-testid="lab-oscilloscopio">
      <div className="lab-chead">
        <h2>Oscilloscopio</h2>
        <span className="lab-cnote">
          {modo === 'xy'
            ? 'sorgente A sull\u2019asse X, sorgente B sulla Y'
            : 'il segnale nel tempo, campione per campione'}
        </span>
        {ottieniXY && (
          <div className="lab-modi" role="radiogroup" aria-label="Modo di lettura">
            {['tempo', 'xy'].map((m) => (
              <button key={m} type="button" role="radio" aria-checked={modo === m}
                className={'lab-modo' + (modo === m ? ' vivo' : '')}
                data-testid={`lab-scope-${m}`}
                onClick={() => { modoRef.current = m; setModo(m); }}>
                {m === 'xy' ? 'XY' : 'Tempo'}
              </button>
            ))}
          </div>
        )}
      </div>
      <canvas ref={telaRef} className="lab-tela" role="img"
        aria-label="Oscilloscopio: la forma d'onda del segnale nel tempo" />
      {modo === 'xy' ? (
        <p className="lab-didascalia" data-testid="lab-xy-didascalia">
          <b>Figure di Lissajous.</b> Un intervallo musicale è un
          rapporto tra numeri: A e B a 2:1 (l&rsquo;ottava) disegnano un
          otto, 3:2 (la quinta) un nodo in più. Se il rapporto è
          leggermente stonato, la figura ruota, stai vedendo la fase
          che scorre.
        </p>
      ) : (
        <div className="lab-scope-info">
          <span>{ms ? `finestra ${ms} ms · ${FINESTRA} campioni` : 'in attesa di un segnale'}</span>
          <span data-testid="lab-aggancio">
            {fermo ? 'immagine ferma, il suono continua'
              : vivo ? (aggancio ? 'trigger agganciato' : 'corsa libera') : ''}
          </span>
          <span>asse ±1 · zero al centro</span>
        </div>
      )}
    </section>
  );
}
