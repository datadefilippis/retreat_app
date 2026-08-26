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
import { iscrivi } from './quadro';

const FINESTRA = 2048;          // campioni a schermo: a 44.1k ≈ 46 ms
const MARGINE_Y = 0.88;         // ±1 non tocca i bordi

/* zero-crossing in salita con isteresi adattiva.
   Ritorna l'indice di partenza e se l'aggancio e' riuscito. */
function trigger(buf) {
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

export default function Oscilloscopio({ ottieniAnalisi, fermo }) {
  const telaRef = useRef(null);
  const acqRef = useRef(null);            // l'ultimo buffer acquisito
  const daRef = useRef(0);                // indice del trigger nel buffer
  const srRef = useRef(0);
  const [aggancio, setAggancio] = useState(false);
  const [vivo, setVivo] = useState(false);

  useEffect(() => {
    const tela = telaRef.current;
    const c2d = tela.getContext('2d');
    let tinte = null;                     // i colori della palette, letti una volta

    const dipingi = (fermo) => {
      /* la tela segue la card (responsive), in pixel veri */
      const dpr = window.devicePixelRatio || 1;
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

      /* acquisizione — salvo che da congelati */
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

      /* griglia: molto discreta — l'asse dello zero, ±½, otto tempi */
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

      /* la traccia */
      const buf = acqRef.current;
      c2d.lineWidth = Math.max(1.25, 1.25 * dpr);
      c2d.strokeStyle = fermo ? tinte.fermo : tinte.traccia;
      c2d.beginPath();
      if (buf) {
        const da = daRef.current;
        for (let i = 0; i < FINESTRA; i++) {
          const v = buf[da + i] || 0;
          const x = (i / (FINESTRA - 1)) * W;
          const y = H / 2 - v * (H / 2) * MARGINE_Y;
          if (i === 0) c2d.moveTo(x, y); else c2d.lineTo(x, y);
        }
      } else {
        c2d.moveTo(0, H / 2); c2d.lineTo(W, H / 2);   // banco spento: linea di riposo
      }
      c2d.stroke();
    };

    return iscrivi(dipingi);
  }, [ottieniAnalisi]);

  const ms = srRef.current ? ((FINESTRA / srRef.current) * 1000).toFixed(1).replace('.', ',') : null;

  return (
    <section className="lab-card lab-scope" data-testid="lab-oscilloscopio">
      <div className="lab-chead">
        <h2>Oscilloscopio</h2>
        <span className="lab-cnote">il segnale nel tempo, campione per campione</span>
      </div>
      <canvas ref={telaRef} className="lab-tela" role="img"
        aria-label="Oscilloscopio: la forma d'onda del segnale nel tempo" />
      <div className="lab-scope-info">
        <span>{ms ? `finestra ${ms} ms · ${FINESTRA} campioni` : 'in attesa di un segnale'}</span>
        <span data-testid="lab-aggancio">
          {fermo ? 'immagine ferma — il suono continua'
            : vivo ? (aggancio ? 'trigger agganciato' : 'corsa libera') : ''}
        </span>
        <span>asse ±1 · zero al centro</span>
      </div>
    </section>
  );
}
