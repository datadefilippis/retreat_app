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
import React, { useRef, useState } from 'react';

const fr = (e) => {
  const r = e.currentTarget.getBoundingClientRect();
  return Math.max(0, Math.min(1, (e.clientX - r.left) / r.width));
};

/* setPointerCapture PUO' lanciare (NotFoundError se il pointer non e'
   piu' attivo — visto succedere): senza il try, l'eccezione ucciderebbe
   l'intero gesto. Se la capture fallisce, il tap semplice resta vivo. */
const cattura = (e) => {
  try { e.currentTarget.setPointerCapture(e.pointerId); } catch { /* tap senza capture */ }
};
const haCattura = (e) => {
  try { return e.currentTarget.hasPointerCapture(e.pointerId); } catch { return false; }
};

export default function SeekBar({ cur, tot, onCommit, fmt, testid, titolo }) {
  const [scrub, setScrubState] = useState(null);     // frazione sotto il dito
  /* il ref e' la verita' per la LOGICA del gesto: un tap velocissimo fa
     arrivare down e up prima che React ri-renderizzi, e la closure di
     up leggerebbe lo scrub del render precedente (null) — gesto perso.
     Lo stato serve solo a disegnare. */
  const scrubRef = useRef(null);
  const setScrub = (v) => { scrubRef.current = v; setScrubState(v); };
  const frac = scrub != null ? scrub : Math.min(1, tot > 0 ? cur / tot : 0);
  return (
    <div className="seekwrap" style={{ display: 'flex' }}>
      <span className="seek-cur">{fmt(scrub != null ? scrub * tot : cur)}</span>
      <div className="seekbar" data-testid={testid}
        title={titolo} style={{ cursor: 'pointer' }}
        onPointerDown={(e) => {
          cattura(e);
          setScrub(fr(e));
        }}
        onPointerMove={(e) => {
          if (haCattura(e)) setScrub(fr(e));
        }}
        onPointerUp={(e) => {
          /* commit se il gesto era NOSTRO (capture) o se e' un tap
             secco su cui la capture non era riuscita: scrub != null
             dice che il down e' passato di qui */
          if (!haCattura(e) && scrubRef.current == null) return;
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
