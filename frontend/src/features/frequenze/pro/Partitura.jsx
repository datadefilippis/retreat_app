/**
 * LA VESTE DELLA PARTITURA (M-D/1, 26/8/2026).
 *
 * La geometria la fa pro/spartito.js — pura, testata in Node; si
 * chiama spartito perché il file È il foglio, e perché sul
 * filesystem del Mac due nomi che differiscono solo per la maiuscola
 * collidono. Qui la
 * si veste e basta: SVG inline, colori dalle variabili del tema —
 * niente canvas, niente requestAnimationFrame, niente librerie. È un
 * DISEGNO, non un visualizzatore: il visual vivo, in sessione, è
 * un'altra cosa (Aurya Mode) e arriva con M4.
 */
import React, { useMemo } from 'react';
import { famiglie, partitura } from './spartito';

/* i colori delle famiglie: variabili del mondo Sound (.fqz) */
const COLORE = {
  continuo: 'var(--lamp)',
  ritmo: 'var(--water)',
  soffio: '#8FA6AD',
  respiro: 'var(--violet, #9B8BC4)',
  materia: '#C9B08A',
};
const NOME = {
  continuo: 'tono continuo',
  ritmo: 'battito',
  soffio: 'soffio',
  respiro: 'respiro',
  materia: 'basi e voce',
};

const mmss = (s) => {
  const t = Math.max(0, Math.round(s || 0));
  return `${Math.floor(t / 60)}:${String(t % 60).padStart(2, '0')}`;
};

/* la banda: una foglia, entra morbida, sta, esce morbida */
function foglia({ x0, x1, yc, alto, punta }) {
  const a = alto / 2;
  return [
    `M ${x0} ${yc}`,
    `Q ${x0 + punta * 0.5} ${yc - a} ${x0 + punta} ${yc - a}`,
    `L ${x1 - punta} ${yc - a}`,
    `Q ${x1 - punta * 0.5} ${yc - a} ${x1} ${yc}`,
    `Q ${x1 - punta * 0.5} ${yc + a} ${x1 - punta} ${yc + a}`,
    `L ${x0 + punta} ${yc + a}`,
    `Q ${x0 + punta * 0.5} ${yc + a} ${x0} ${yc}`,
    'Z',
  ].join(' ');
}

/**
 * @param score     lo score v1 (dati, mai toccati)
 * @param dettaglio true = scheda grande: fasi, asse del tempo, legenda
 */
export default function Partitura({ score, dettaglio = false, altezza }) {
  const h = altezza || (dettaglio ? 132 : 44);
  const geo = useMemo(() => partitura(score, { w: 600, h }), [score, h]);
  const fam = useMemo(() => famiglie(score), [score]);
  if (!geo.bande.length) return null;

  return (
    <figure className={`partitura${dettaglio ? ' grande' : ''}`}
      data-testid="partitura">
      <svg viewBox={`0 0 600 ${h + (dettaglio ? 22 : 0)}`}
        preserveAspectRatio="none" role="img"
        aria-label={`L'arco del protocollo: ${geo.bande.length} suoni su ${mmss(geo.durata)}`}>
        {dettaglio && geo.fasi.map((f) => (
          <line key={`${f.x}-${f.nome}`} x1={f.x} y1={0} x2={f.x} y2={h}
            stroke="var(--line)" strokeWidth="1" />
        ))}
        {geo.bande.map((b, i) => (
          <path key={i} d={foglia(b)} fill={COLORE[b.famiglia]}
            opacity={b.opacita} />
        ))}
        {geo.curve.map((c, i) => (
          <polyline key={i}
            points={c.punti.map(([x, y]) => `${x},${y}`).join(' ')}
            fill="none" stroke="#0D1A1E" strokeWidth="1.5"
            opacity="0.55" />
        ))}
        {dettaglio && geo.fasi.map((f) => (
          <text key={`t-${f.x}-${f.nome}`} x={f.x + 4} y={h + 15}
            className="partitura-fase">{f.nome}</text>
        ))}
      </svg>
      {dettaglio && (
        <figcaption className="partitura-piede">
          <span className="partitura-tempo">0:00</span>
          <span className="partitura-legenda">
            {fam.map((f) => (
              <span key={f} className="partitura-voce">
                <i style={{ background: COLORE[f] }} />{NOME[f]}
              </span>
            ))}
          </span>
          <span className="partitura-tempo">{mmss(geo.durata)}</span>
        </figcaption>
      )}
    </figure>
  );
}
