/**
 * OndaViva — il suono in movimento, senza suono (26/8/2026, sera).
 *
 * Richiesta del founder sulla pagina di vendita: nella sezione «Il
 * suono non è una scatola nera» non finestre statiche ma L'ONDA — le
 * frequenze che si muovono. Un canvas che disegna le voci dello score
 * VERO (costruisci() del catalogo), animate a schermo ma MUTE: la
 * pagina di vendita non suona, mostra. Qui non c'è nessun contesto
 * audio, e la guardia lo pretende.
 *
 * Le regole del movimento vengono dallo score, non dal caso:
 *  - i cicli a schermo seguono il carrier (scala log, 55→880 Hz danno
 *    da 2 a 7 creste)
 *  - l'ampiezza segue il gain del livello
 *  - la pulsazione segue il battito (f0), col tetto anti-strobo del
 *    ciclo Danza: a schermo niente pulsa sopra 1 Hz
 *  - i livelli breath respirano davvero: inviluppo lento, non tremolio
 * Con prefers-reduced-motion l'onda resta, ferma su un fotogramma.
 */
import React, { useEffect, useRef } from 'react';

const COLORI = ['#c9b37e', '#8fd0c2', '#f6f2e8', '#6f9c8f'];
const TETTO_PULSAZIONE = 1; // Hz visivi — mai oltre (anti-strobo)

/** Da uno score alle voci visive: numeri del suono → numeri del segno. */
export function vociDaScore(score) {
  return (score?.layers || []).slice(0, 4).map((l) => {
    const carrier = l.carrier ?? 70;
    const cicli = 2 + 5 * Math.min(1, Math.max(0, Math.log2(carrier / 55) / 4));
    const battito = Math.abs(l.f0 ?? 0.15);
    return {
      cicli,
      amp: Math.min(1, (l.gain ?? 0.3) * 2.4),
      deriva: 0.3 + Math.min(TETTO_PULSAZIONE, battito) * 0.8,
      pulsa: Math.min(TETTO_PULSAZIONE, battito),
      respira: l.method === 'breath',
    };
  });
}

export default function OndaViva({ score, altezza = 220 }) {
  const tela = useRef(null);

  useEffect(() => {
    const c = tela.current;
    if (!c) return undefined;
    const voci = vociDaScore(score);
    const ctx = c.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    let W = 0;
    const misura = () => {
      W = c.clientWidth || 300;
      c.width = W * dpr;
      c.height = altezza * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    misura();

    const quadro = (t) => {
      ctx.clearRect(0, 0, W, altezza);
      voci.forEach((v, i) => {
        const inviluppo = v.respira
          ? 0.4 + 0.6 * (0.5 - 0.5 * Math.cos(2 * Math.PI * 0.1 * t))
          : 0.82 + 0.18 * Math.sin(2 * Math.PI * v.pulsa * t + i);
        const ampiezza = v.amp * inviluppo * (altezza * 0.3);
        const centro = altezza / 2 + (i - (voci.length - 1) / 2) * 7;
        ctx.beginPath();
        for (let x = 0; x <= W; x += 2) {
          const y = centro + ampiezza
            * Math.sin(2 * Math.PI * v.cicli * (x / W) + v.deriva * t + i * 1.7);
          if (x === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.strokeStyle = COLORI[i % COLORI.length];
        ctx.globalAlpha = Math.max(0.35, 0.9 - i * 0.18);
        ctx.lineWidth = i === 0 ? 2.2 : 1.5;
        ctx.stroke();
      });
      ctx.globalAlpha = 1;
    };

    const fermo = typeof window.matchMedia === 'function'
      && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    let vivo = true;
    let inizio = null;
    let raf = null;
    const passo = (ts) => {
      if (!vivo) return;
      if (inizio === null) inizio = ts;
      quadro((ts - inizio) / 1000);
      raf = window.requestAnimationFrame(passo);
    };
    // il primo fotogramma subito, in sincrono: se il rAF non parte
    // (scheda in secondo piano) l'onda c'e' comunque, ferma
    quadro(2.5);
    if (!fermo) raf = window.requestAnimationFrame(passo);
    window.addEventListener('resize', misura);
    return () => {
      vivo = false;
      if (raf) window.cancelAnimationFrame(raf);
      window.removeEventListener('resize', misura);
    };
  }, [score, altezza]);

  return (
    <canvas ref={tela} aria-hidden="true"
      style={{ width: '100%', height: altezza, display: 'block' }} />
  );
}
