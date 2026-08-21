/**
 * Aurya Mode — la tela (AV1, 21/8/2026).
 *
 * Fa girare un tema sul suono che gia' esiste. NON crea audio, non lo
 * ferma, non lo tocca: riceve un lettore (analisi.js) innestato nel
 * grafo e disegna. Se la tela sparisce, il suono continua — sono due
 * vite separate, e devono restarlo.
 *
 * I freni, perche' una scena bella che scalda il telefono e' una
 * scena sbagliata:
 * - risoluzione limitata (il DPR pieno su un telefono retina significa
 *   4 volte i pixel per zero guadagno percepito su una scena diffusa);
 * - il disegno si FERMA quando la pagina non e' visibile: nessuno
 *   guarda, e la batteria non si consuma;
 * - rispetta `prefers-reduced-motion`: chi ha chiesto meno movimento
 *   vede una scena ferma e composta, non un rifiuto.
 */
import React, { useEffect, useRef } from 'react';
import * as mandala from './temi/mandala';

const TEMI = { mandala };

export default function AuryaMode({ lettore, tema = 'mandala', attivo = true,
                                    className = '', altezza = 320 }) {
  const canvasRef = useRef(null);
  const rafRef = useRef(0);

  useEffect(() => {
    const cv = canvasRef.current;
    if (!cv || !lettore || !attivo) return undefined;
    const g = cv.getContext('2d', { alpha: false });
    const t = TEMI[tema] || mandala;
    const quieto = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

    /* Tetto al DPR: su un telefono a 3x una tela da 1000px larga
       diventerebbe 3000 — nove volte i pixel da riempire a ogni
       fotogramma, per una scena sfocata dove nessuno conta i pixel. */
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    let w = 0, h = 0;
    const misura = () => {
      const r = cv.getBoundingClientRect();
      w = Math.max(1, Math.round(r.width * dpr));
      h = Math.max(1, Math.round(r.height * dpr));
      if (cv.width !== w || cv.height !== h) { cv.width = w; cv.height = h; }
    };
    misura();
    const ro = new ResizeObserver(misura);
    ro.observe(cv);

    // il fondo pieno una volta sola: da qui in poi ogni fotogramma
    // vela il precedente, ed e' quello che crea la scia
    g.fillStyle = mandala.COLORI.fondo;
    g.fillRect(0, 0, w, h);

    const t0 = performance.now();
    let vivo = true;
    const giro = () => {
      if (!vivo) return;
      const L = lettore.leggi();
      t.disegna(g, L, (performance.now() - t0) / 1000, { w, h });
      // in quiete si disegna comunque (la scena resta viva col suono)
      // ma a un terzo del ritmo: meno movimento, meno batteria
      rafRef.current = quieto
        ? window.setTimeout(() => requestAnimationFrame(giro), 66)
        : requestAnimationFrame(giro);
    };
    /* Se la pagina non e' visibile non si disegna: rAF si ferma da
       solo, ma il setTimeout della modalita' quieta no — e resterebbe
       a bruciare cicli in una scheda che nessuno guarda. */
    const visibilita = () => {
      if (document.visibilityState === 'visible' && vivo) giro();
    };
    document.addEventListener('visibilitychange', visibilita);
    giro();

    return () => {
      vivo = false;
      cancelAnimationFrame(rafRef.current);
      clearTimeout(rafRef.current);
      document.removeEventListener('visibilitychange', visibilita);
      ro.disconnect();
    };
  }, [lettore, tema, attivo]);

  if (!attivo) return null;
  return (
    <canvas ref={canvasRef} className={`aurya-mode ${className}`}
      data-testid="aurya-mode"
      style={{ width: '100%', height: altezza, display: 'block',
               borderRadius: 12, background: mandala.COLORI.fondo }} />
  );
}
