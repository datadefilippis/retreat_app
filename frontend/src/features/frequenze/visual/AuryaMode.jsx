/**
 * Aurya Mode — la tela (AV1→AV4, 22/8/2026).
 *
 * Due motori, una regola: la tela NON crea audio, non lo ferma, non
 * lo tocca — riceve il lettore (analisi.js) e disegna.
 *
 * - MOTORE IMMERSIVO (motore3d, dal concept del founder): WebGL,
 *   16.000 particelle, sette modi. Si carica LAZY — Three.js entra in
 *   memoria solo quando qualcuno preme «Guarda», mai prima;
 * - SORGENTE (canvas 2D): la rete — dove WebGL manca o fallisce, la
 *   scena di luce leggera c'e' comunque.
 *
 * I freni restano quelli di sempre: DPR limitato, disegno FERMO a
 * pagina nascosta, prefers-reduced-motion rispettato (nel motore 3D:
 * si resta sul 2D, che in quiete rallenta da solo — una galassia che
 * turbina non e' «movimento ridotto» per nessuna definizione).
 */
import React, { useEffect, useRef, useState } from 'react';
import * as sorgente from './temi/sorgente';

const MODI_NOMI = {
  respiro: 'Respiro', nebulosa: 'Nebulosa', spirale: 'Spirale',
  flusso: 'Flusso', alone: 'Alone', elica: 'Elica', onde: 'Onde',
};

export default function AuryaMode({ lettore, attivo = true,
                                    className = '', altezza = 380 }) {
  const canvasRef = useRef(null);
  const motoreRef = useRef(null);
  const rafRef = useRef(0);
  const [modo, setModo] = useState('spirale');
  const [immersivo, setImmersivo] = useState(null);   // null = da decidere

  useEffect(() => {
    const cv = canvasRef.current;
    if (!cv || !lettore || !attivo) return undefined;
    let smontato = false;
    const quieto = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);

    const webgl2 = !quieto && !!document.createElement('canvas').getContext('webgl2');

    /* ── via immersiva: Three arriva SOLO adesso, lazy ── */
    if (webgl2) {
      let ro;
      import('./motore3d').then(({ creaMotore }) => {
        if (smontato) return;
        try {
          const m = creaMotore(cv, lettore, { modo });
          motoreRef.current = m;
          const misura = () => {
            const r = cv.getBoundingClientRect();
            m.ridimensiona(Math.max(1, r.width), Math.max(1, r.height), dpr);
          };
          misura();
          ro = new ResizeObserver(misura);
          ro.observe(cv);
          const visibilita = () => {
            if (document.visibilityState === 'visible') m.avvia(); else m.ferma();
          };
          document.addEventListener('visibilitychange', visibilita);
          m._pulisci = () => {
            document.removeEventListener('visibilitychange', visibilita);
            ro?.disconnect();
          };
          m.avvia();
          setImmersivo(true);
        } catch {
          setImmersivo(false);   // WebGL c'e' ma non parte: rete 2D
        }
      }).catch(() => setImmersivo(false));
      return () => {
        smontato = true;
        if (motoreRef.current) {
          motoreRef.current._pulisci?.();
          motoreRef.current.dispose();
          motoreRef.current = null;
        }
      };
    }

    /* ── la rete: Sorgente 2D ── */
    setImmersivo(false);
    const g = cv.getContext('2d', { alpha: false });
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
    g.fillStyle = sorgente.COLORI.fondo;
    g.fillRect(0, 0, w, h);
    const t0 = performance.now();
    let vivo = true;
    const giro = () => {
      if (!vivo) return;
      const L = lettore.leggi();
      sorgente.disegna(g, L, (performance.now() - t0) / 1000, { w, h });
      rafRef.current = quieto
        ? window.setTimeout(() => requestAnimationFrame(giro), 66)
        : requestAnimationFrame(giro);
    };
    const visibilita = () => {
      if (document.visibilityState === 'visible' && vivo) giro();
    };
    document.addEventListener('visibilitychange', visibilita);
    giro();
    return () => {
      vivo = false;
      smontato = true;
      cancelAnimationFrame(rafRef.current);
      clearTimeout(rafRef.current);
      document.removeEventListener('visibilitychange', visibilita);
      ro.disconnect();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lettore, attivo]);

  // il cambio modo NON ricrea il motore: e' un uniform
  useEffect(() => { motoreRef.current?.impostaModo(modo); }, [modo]);

  if (!attivo) return null;
  return (
    <div style={{ position: 'relative' }}>
      <canvas ref={canvasRef} className={`aurya-mode ${className}`}
        data-testid="aurya-mode"
        style={{ width: '100%', height: altezza, display: 'block',
                 borderRadius: 12, background: sorgente.COLORI.fondo }} />
      {immersivo && (
        <button type="button" data-testid="aurya-mode-modo"
          onClick={() => {
            const tutti = Object.keys(MODI_NOMI);
            setModo(tutti[(tutti.indexOf(modo) + 1) % tutti.length]);
          }}
          style={{ position: 'absolute', top: 10, right: 10,
                   background: 'rgba(12,22,24,.55)', color: '#C9B37E',
                   border: '1px solid rgba(201,179,126,.35)', borderRadius: 999,
                   padding: '5px 12px', fontSize: 11, letterSpacing: '.08em',
                   cursor: 'pointer' }}>
          {MODI_NOMI[modo]} ›
        </button>
      )}
    </div>
  );
}
