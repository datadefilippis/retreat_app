/**
 * L'ONDA VIVA — la forma d'onda della fonderia, dal vivo (29/8/2026).
 *
 * Il desiderio del founder: «dopo che si e' sintetizzato un suono e
 * lo si ascolta, mostrare l'onda di quel suono in movimento in
 * maniera professionale e stilosa». Professionale qui ha un
 * significato preciso: sono i campioni VERI dell'analyser sul master
 * (analisi.tempo), agganciati col TRIGGER dell'Oscilloscopio — la
 * stessa unica verita' del Banco, importata, non ricopiata. Senza
 * trigger l'onda scorrerebbe; con l'aggancio sta ferma come su uno
 * strumento vero, e per un suono che muore (il colpo) la vedi
 * spegnersi in ampiezza senza bugie di auto-gain.
 *
 * Stiloso e' il vestito, non il dato: scia al fosforo (il pattern
 * LB7 — le tracce vecchie sbiadiscono con un velo di
 * 'destination-out' su un livello fuori schermo), traccia con
 * bagliore e gradiente acqua→oro, un velo d'area sotto la curva.
 * La tela appare solo mentre qualcosa suona (il contenitore si apre
 * e si chiude in CSS) e si iscrive al quadro solo da viva: da spenta
 * non costa un fotogramma.
 */
import React, { useEffect, useRef, useState } from 'react';
import { iscrivi } from './quadro';
import { trigger } from './Oscilloscopio';

const FINESTRA = 2048;          // ≈46 ms a 44.1k — come l'Oscilloscopio
const MARGINE_Y = 0.86;

const NOMI = {
  orig: 'l’originale registrato',
  colpo: 'la rifusione — colpo',
  tenuto: 'la rifusione — tenuta',
};

/* `nome` (opzionale) sovrascrive il nome di battesimo: il quaderno
   dei ritratti lo usa per dire l'etichetta della voce che suona. */
export default function OndaViva({ ottieniAnalisi, attivo, nome = null }) {
  const telaRef = useRef(null);
  const acqRef = useRef(null);
  const daRef = useRef(0);
  const [aggancio, setAggancio] = useState(false);

  useEffect(() => {
    if (!attivo || !ottieniAnalisi) return undefined;
    const tela = telaRef.current;
    if (!tela) return undefined;
    const c2d = tela.getContext('2d');
    let tinte = null;
    const scia = document.createElement('canvas');
    const sciaC2d = scia.getContext('2d');

    const dipingi = (fermo) => {
      const dpr = window.devicePixelRatio || 1;
      const W = Math.round(tela.clientWidth * dpr);
      const H = Math.round(tela.clientHeight * dpr);
      if (!W || !H) return;
      if (tela.width !== W || tela.height !== H) {
        tela.width = W; tela.height = H;
        scia.width = W; scia.height = H;
        tinte = null;
      }
      if (!tinte) {
        const s = getComputedStyle(tela);
        tinte = {
          asse: s.getPropertyValue('--line-soft').trim() || '#1B2E32',
          acqua: s.getPropertyValue('--water').trim() || '#66B79C',
          oro: s.getPropertyValue('--lamp').trim() || '#C9B37E',
        };
      }

      /* acquisizione dal master — salvo che a tempo fermo */
      const analisi = ottieniAnalisi();
      if (analisi && !fermo) {
        const N = analisi.analyser.fftSize;
        if (!acqRef.current || acqRef.current.length !== N) {
          acqRef.current = new Float32Array(N);
        }
        analisi.tempo(acqRef.current);
        const t = trigger(acqRef.current);
        daRef.current = t.da;
        setAggancio(t.ok);
      }
      const buf = acqRef.current;
      if (!buf) return;

      const mezzo = H / 2;
      const ampiezza = mezzo * MARGINE_Y;
      const da = daRef.current;
      const passo = W / (FINESTRA - 1);

      /* la scia sbiadisce, poi accoglie la traccia di questo giro */
      sciaC2d.globalCompositeOperation = 'destination-out';
      sciaC2d.fillStyle = 'rgba(0,0,0,0.20)';
      sciaC2d.fillRect(0, 0, W, H);
      sciaC2d.globalCompositeOperation = 'source-over';
      sciaC2d.lineWidth = Math.max(1, dpr);
      sciaC2d.strokeStyle = tinte.acqua;
      sciaC2d.globalAlpha = 0.35;
      sciaC2d.beginPath();
      for (let i = 0; i < FINESTRA; i++) {
        const y = mezzo - (buf[da + i] || 0) * ampiezza;
        if (i === 0) sciaC2d.moveTo(0, y); else sciaC2d.lineTo(i * passo, y);
      }
      sciaC2d.stroke();
      sciaC2d.globalAlpha = 1;

      /* composizione: asse, scia, velo d'area, traccia col bagliore */
      c2d.clearRect(0, 0, W, H);
      c2d.lineWidth = 1;
      c2d.strokeStyle = tinte.asse;
      c2d.beginPath();
      c2d.moveTo(0, mezzo); c2d.lineTo(W, mezzo);
      c2d.stroke();
      c2d.drawImage(scia, 0, 0);

      const gradiente = c2d.createLinearGradient(0, 0, W, 0);
      gradiente.addColorStop(0, tinte.acqua);
      gradiente.addColorStop(1, tinte.oro);

      c2d.beginPath();
      for (let i = 0; i < FINESTRA; i++) {
        const y = mezzo - (buf[da + i] || 0) * ampiezza;
        if (i === 0) c2d.moveTo(0, y); else c2d.lineTo(i * passo, y);
      }
      /* il velo d'area: la stessa curva chiusa sull'asse */
      c2d.save();
      c2d.lineTo(W, mezzo); c2d.lineTo(0, mezzo); c2d.closePath();
      c2d.globalAlpha = 0.10;
      c2d.fillStyle = gradiente;
      c2d.fill();
      c2d.restore();

      c2d.beginPath();
      for (let i = 0; i < FINESTRA; i++) {
        const y = mezzo - (buf[da + i] || 0) * ampiezza;
        if (i === 0) c2d.moveTo(0, y); else c2d.lineTo(i * passo, y);
      }
      c2d.lineWidth = Math.max(1.5, 1.5 * dpr);
      c2d.strokeStyle = gradiente;
      c2d.shadowColor = tinte.acqua;
      c2d.shadowBlur = 8 * dpr;
      c2d.stroke();
      c2d.shadowBlur = 0;
    };

    return iscrivi(dipingi);
  }, [attivo, ottieniAnalisi]);

  return (
    <div className={`lab-ondaviva${attivo ? ' viva' : ''}`}
      data-testid="lab-ondaviva" aria-hidden={!attivo}>
      <div className="lab-ondaviva-testa">
        <span>L’onda, dal vivo{attivo ? ` — ${nome || NOMI[attivo] || ''}` : ''}</span>
        <span className={`lab-ondaviva-stato${aggancio ? ' ok' : ''}`}>
          {aggancio ? 'agganciata' : 'in corsa'}
        </span>
      </div>
      <canvas ref={telaRef} className="lab-ondaviva-tela" />
    </div>
  );
}
