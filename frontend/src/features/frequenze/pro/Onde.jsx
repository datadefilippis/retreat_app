/**
 * LE ONDE — il suono che si vede, davvero (M4, 26/8/2026).
 *
 * La richiesta del founder: «onde reali in movimento, che
 * rappresentano realmente quello che si sta ascoltando». Quindi
 * NIENTE animazioni finte: si legge la forma d'onda VERA dal
 * rubinetto del player (getByteTimeDomainData sull'AnalyserNode) e
 * la si disegna — tre voci della stessa onda, sfalsate nel tempo,
 * perché il movimento lento dei battiti si veda come una scia.
 *
 * Questo componente DISEGNA e basta: non crea audio, non conosce il
 * motore — riceve una funzione che gli presta l'analyser, e finché
 * l'analyser non c'è disegna la quiete (una linea ferma). Il suo
 * requestAnimationFrame è suo e muore con lui (cancel su unmount):
 * il Lab ha il quadro, il rito ha questo — due mondi, nessun
 * orologio condiviso.
 */
import React, { useEffect, useRef } from 'react';

const CAMPIONI = 2048;

export default function Onde({ sorgente, altezza = 180 }) {
  const tela = useRef(null);

  useEffect(() => {
    const el = tela.current;
    if (!el) return undefined;
    const pennello = el.getContext('2d');
    const dati = new Uint8Array(CAMPIONI);
    /* le scie: due fotografie precedenti dell'onda */
    const scia1 = new Float32Array(CAMPIONI);
    const scia2 = new Float32Array(CAMPIONI);
    let vivo = true;
    let quadro = 0;

    const misura = () => {
      const dpr = Math.min(2, window.devicePixelRatio || 1);
      const w = el.clientWidth || 600;
      if (el.width !== Math.round(w * dpr)) {
        el.width = Math.round(w * dpr);
        el.height = Math.round(altezza * dpr);
      }
      return { w: el.width, h: el.height };
    };

    const linea = (serie, colore, spessore, alfa) => {
      const { w, h } = { w: el.width, h: el.height };
      pennello.beginPath();
      const passo = Math.max(1, Math.floor(CAMPIONI / w));
      for (let i = 0, x = 0; i < CAMPIONI; i += passo, x += passo) {
        const y = h / 2 + serie[i] * (h * 0.42);
        if (i === 0) pennello.moveTo((x / CAMPIONI) * w, y);
        else pennello.lineTo((x / CAMPIONI) * w, y);
      }
      pennello.strokeStyle = colore;
      pennello.globalAlpha = alfa;
      pennello.lineWidth = spessore;
      pennello.lineJoin = 'round';
      pennello.stroke();
      pennello.globalAlpha = 1;
    };

    const dipingi = () => {
      if (!vivo) return;
      quadro = requestAnimationFrame(dipingi);
      const { w, h } = misura();
      pennello.fillStyle = '#0D1A1E';
      pennello.fillRect(0, 0, w, h);

      const analyser = sorgente?.();
      const ora = new Float32Array(CAMPIONI);
      if (analyser) {
        analyser.getByteTimeDomainData(dati);
        for (let i = 0; i < CAMPIONI; i++) ora[i] = (dati[i] - 128) / 128;
      }
      /* le scie inseguono l'onda: il ritmo lento si vede come spessore */
      for (let i = 0; i < CAMPIONI; i++) {
        scia2[i] += (scia1[i] - scia2[i]) * 0.08;
        scia1[i] += (ora[i] - scia1[i]) * 0.22;
      }
      linea(scia2, '#3E5A60', 3, 0.5);
      linea(scia1, '#7EC1BA', 2, 0.65);
      linea(ora, '#E0A85F', 1.6, 0.95);
    };
    dipingi();

    return () => { vivo = false; cancelAnimationFrame(quadro); };
  }, [sorgente, altezza]);

  return (
    <canvas ref={tela} className="onde" style={{ height: altezza }}
      aria-hidden="true" data-testid="rito-onde" />
  );
}
