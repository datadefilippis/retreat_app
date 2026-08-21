/**
 * Frequenze by Aurya — la barra di scorrimento che segue il dito
 * (TS2, 21/8/2026).
 *
 * Prima era un div con onClick: il tap funzionava, il TRASCINAMENTO —
 * il gesto naturale su un telefono — non faceva niente. E ogni tocco
 * riavviava il motore, quindi un drag «vivo» sarebbe stato comunque
 * impossibile.
 *
 * Il contratto ora e':
 * - durante il gesto il cursore e il tempo seguono il dito SUBITO
 *   (stato locale, il motore non viene toccato);
 * - al rilascio si fa UN solo commit (onCommit), cioe' un solo riavvio
 *   del motore sul punto scelto. Il tap secco e' lo stesso gesto con
 *   zero movimento: stessa strada, niente doppio percorso click/drag;
 * - setPointerCapture tiene il gesto anche quando il dito esce dalla
 *   barra (su una barra alta 6px succede SEMPRE), e pointercancel
 *   (il sistema che si riprende il gesto: scroll, chiamata) lascia lo
 *   stato pulito invece del cursore congelato a meta'.
 *
 * Un solo componente per il compositore e per la pagina pubblica: il
 * gate dell'anteprima o altri vincoli stanno nel chiamante (onCommit),
 * non qui.
 */
import React, { useState } from 'react';

const fr = (e) => {
  const r = e.currentTarget.getBoundingClientRect();
  return Math.max(0, Math.min(1, (e.clientX - r.left) / r.width));
};

export default function SeekBar({ cur, tot, onCommit, fmt, testid, titolo }) {
  const [scrub, setScrub] = useState(null);          // frazione sotto il dito
  const frac = scrub != null ? scrub : Math.min(1, tot > 0 ? cur / tot : 0);
  return (
    <div className="seekwrap" style={{ display: 'flex' }}>
      <span className="seek-cur">{fmt(scrub != null ? scrub * tot : cur)}</span>
      <div className="seekbar" data-testid={testid}
        title={titolo} style={{ cursor: 'pointer' }}
        onPointerDown={(e) => {
          e.currentTarget.setPointerCapture(e.pointerId);
          setScrub(fr(e));
        }}
        onPointerMove={(e) => {
          if (e.currentTarget.hasPointerCapture(e.pointerId)) setScrub(fr(e));
        }}
        onPointerUp={(e) => {
          if (!e.currentTarget.hasPointerCapture(e.pointerId)) return;
          setScrub(null);
          onCommit(fr(e) * tot);
        }}
        onPointerCancel={() => setScrub(null)}
        /* il sistema puo' togliere la capture SENZA up ne' cancel
           (successo in verifica, con un gesto troncato a meta'): senza
           questo, il cursore resta congelato dov'era il dito */
        onLostPointerCapture={() => setScrub(null)}>
        <div className="seek-fill" style={{ width: `${frac * 100}%` }} />
        <div className="seek-knob" style={{ left: `${frac * 100}%` }} />
      </div>
      <span className="seek-tot">{fmt(tot)}</span>
    </div>
  );
}
