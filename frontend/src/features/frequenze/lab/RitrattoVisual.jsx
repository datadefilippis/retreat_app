/**
 * IL VISUAL DEL RITRATTO (consolidamento 28/8) — le corde del suono.
 *
 * Ogni parziale della tabella e' una CORDA verticale sull'asse delle
 * frequenze (logaritmico, come l'orecchio): l'altezza e' la forza,
 * l'oro e' la fondamentale, i doppietti sono coppie gemelle, e la
 * vita (T60) si legge nel bagliore — un modo che vive a lungo
 * brilla di piu' alla base.
 *
 * Quando qualcosa SUONA (l'originale o la rifusione), dietro le
 * corde appare la sagoma dello spettro vivo: e' l'A/B fatto
 * immagine — se la sagoma sposa le corde, la rifusione e' fedele;
 * cio' che la sagoma ha in piu' e' cio' che il ritratto non cattura.
 *
 * Contratto dei pannelli: riceve le prese, un solo rAF (il quadro),
 * niente nodi audio.
 */
import React, { useEffect, useRef } from 'react';
import { iscrivi } from './quadro';

const DB_GIU = -50;              // il fondo della scala delle corde

export default function RitrattoVisual({ esito, ottieniAnalisi, vivo }) {
  const telaRef = useRef(null);
  const vivoRef = useRef(vivo);
  vivoRef.current = vivo;
  const esitoRef = useRef(esito);
  esitoRef.current = esito;
  const spettroRef = useRef(null);

  useEffect(() => {
    const tela = telaRef.current;
    if (!tela) return undefined;
    const c2d = tela.getContext('2d');
    let tinte = null;

    const dipingi = () => {
      const r = esitoRef.current;
      if (!r || !r.parziali || !r.parziali.length) return;
      const dpr = window.devicePixelRatio || 1;
      const W = Math.round(tela.clientWidth * dpr);
      const H = Math.round(tela.clientHeight * dpr);
      if (!W || !H) return;
      if (tela.width !== W || tela.height !== H) {
        tela.width = W; tela.height = H; tinte = null;
      }
      if (!tinte) {
        const st = getComputedStyle(tela);
        tinte = {
          griglia: st.getPropertyValue('--line-soft').trim() || '#1B2E32',
          acqua: st.getPropertyValue('--water').trim() || '#66B79C',
          oro: st.getPropertyValue('--lamp').trim() || '#C9B37E',
          nota: st.getPropertyValue('--dimmer').trim() || '#86A0A4',
        };
      }

      /* la finestra: mezza ottava sotto la fondamentale, un terzo
         sopra l'ultimo parziale */
      const hzs = r.parziali.map((p) => p.hz);
      const fMin = Math.max(30, Math.min(...hzs) / 1.5);
      const fMax = Math.max(...hzs) * 1.3;
      const lo = Math.log10(fMin), hi = Math.log10(fMax);
      const xDaHz = (hz) => ((Math.log10(hz) - lo) / (hi - lo || 1)) * W;
      const yDaDb = (v) => {
        const u = Math.max(0, Math.min(1, (v - DB_GIU) / -DB_GIU));
        return H * 0.92 - u * H * 0.78;
      };
      const base = H * 0.92;

      c2d.clearRect(0, 0, W, H);

      /* la sagoma dello SPETTRO VIVO, dietro, solo mentre suona */
      const analisi = ottieniAnalisi && ottieniAnalisi();
      if (vivoRef.current && analisi) {
        const N = analisi.analyser.frequencyBinCount;
        if (!spettroRef.current || spettroRef.current.length !== N) {
          spettroRef.current = new Float32Array(N);
        }
        analisi.spettro(spettroRef.current);
        const hzBin = analisi.hzPerBin;
        c2d.beginPath();
        c2d.moveTo(0, base);
        for (let x = 0; x <= W; x += 2) {
          const f0 = Math.pow(10, lo + ((x - 1) / W) * (hi - lo));
          const f1 = Math.pow(10, lo + ((x + 1) / W) * (hi - lo));
          let k0 = Math.max(1, Math.floor(f0 / hzBin));
          let k1 = Math.min(N, Math.max(k0 + 1, Math.ceil(f1 / hzBin)));
          let v = -Infinity;
          for (let k = k0; k < k1; k++) {
            if (spettroRef.current[k] > v) v = spettroRef.current[k];
          }
          /* la scala dei dBFS (-96..0) portata su quella delle corde */
          c2d.lineTo(x, yDaDb(Math.max(DB_GIU, v + 20)));
        }
        c2d.lineTo(W, base); c2d.closePath();
        c2d.globalAlpha = 0.16;
        c2d.fillStyle = tinte.acqua;
        c2d.fill();
        c2d.globalAlpha = 1;
      }

      /* la linea di terra e due fasce discrete */
      c2d.strokeStyle = tinte.griglia;
      c2d.lineWidth = 1;
      c2d.beginPath();
      c2d.moveTo(0, base + 0.5); c2d.lineTo(W, base + 0.5);
      [0.25, 0.5].forEach((q) => {
        const y = Math.round(yDaDb(DB_GIU * q)) + 0.5;
        c2d.moveTo(0, y); c2d.lineTo(W, y);
      });
      c2d.stroke();

      /* LE CORDE: una per parziale (e la gemella del doppietto) */
      const maxT60 = Math.max(...r.parziali.map((p) => p.t60 || 0), 1);
      const corda = (hz, dbV, fondamentale, t60) => {
        const x = xDaHz(hz);
        const y = yDaDb(dbV);
        const colore = fondamentale ? tinte.oro : tinte.acqua;
        /* il bagliore alla base racconta la VITA del modo */
        const vita = t60 ? Math.min(1, t60 / maxT60) : 0.35;
        const alone = c2d.createRadialGradient(x, base, 0, x, base, 26 * dpr);
        alone.addColorStop(0, colore + Math.round(60 * vita)
          .toString(16).padStart(2, '0'));
        alone.addColorStop(1, colore + '00');
        c2d.fillStyle = alone;
        c2d.fillRect(x - 26 * dpr, base - 26 * dpr, 52 * dpr, 26 * dpr);
        c2d.strokeStyle = colore;
        c2d.lineWidth = Math.max(1.5, (fondamentale ? 2.2 : 1.5) * dpr);
        c2d.lineCap = 'round';
        c2d.shadowBlur = 7 * dpr; c2d.shadowColor = colore;
        c2d.beginPath();
        c2d.moveTo(x, base); c2d.lineTo(x, y);
        c2d.stroke();
        c2d.shadowBlur = 0;
      };
      for (const p of r.parziali) {
        corda(p.hz, p.db, p.hz === r.fondamentaleHz, p.t60);
        if (p.doppietto) corda(p.doppietto.hz, p.db - 3, false, p.t60);
      }

      /* le quote: la fondamentale sempre, le altre se c'e' spazio */
      c2d.fillStyle = tinte.nota;
      c2d.font = `${Math.round(9.5 * dpr)}px ui-monospace, Menlo, monospace`;
      c2d.textAlign = 'center'; c2d.textBaseline = 'top';
      let ultimaX = -Infinity;
      for (const p of r.parziali) {
        const x = xDaHz(p.hz);
        if (x - ultimaX < 34 * dpr) continue;
        ultimaX = x;
        c2d.fillStyle = p.hz === r.fondamentaleHz ? tinte.oro : tinte.nota;
        c2d.fillText(p.hz >= 1000
          ? `${(p.hz / 1000).toFixed(1).replace('.', ',')}k`
          : String(Math.round(p.hz)), x, base + 4 * dpr);
      }
    };

    return iscrivi(dipingi);
  }, [ottieniAnalisi]);

  if (!esito || !esito.parziali || !esito.parziali.length) return null;
  return (
    <div className="lab-ritratto-visual" data-testid="lab-ritratto-visual">
      <canvas ref={telaRef} className="lab-tela lab-ritratto-tela" role="img"
        aria-label="Le corde del ritratto: un tratto per ogni modo del suono" />
      <p className="lab-ritratto-visual-nota">
        Ogni corda è un modo: l&rsquo;<b>altezza</b> è la forza, l&rsquo;
        <b>oro</b> è la fondamentale, il <b>bagliore</b> alla base è
        quanto vive. Mentre ascolti, la sagoma chiara dietro è lo
        spettro vivo: se sposa le corde, la rifusione è fedele.
      </p>
    </div>
  );
}
