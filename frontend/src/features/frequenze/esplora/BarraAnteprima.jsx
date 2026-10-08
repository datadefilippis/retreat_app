/**
 * BarraAnteprima — ES1: la barra in basso mentre una scheda suona (la stessa
 * grammatica della barra della casa): nome, Hz, i secondi, ferma, la scheda.
 */
import React from 'react';
import { Link } from 'react-router-dom';
import { sluggifica } from '../content/slugScheda';
import { ANTEPRIMA_SEC } from './anteprima';

export default function BarraAnteprima({ anteprima, famigliaSlug = '' }) {
  const { scheda, secondi, ferma } = anteprima;
  if (!scheda) return null;
  const resta = Math.max(0, Math.ceil(ANTEPRIMA_SEC - secondi));
  return (
    <div className="lettore barra-anteprima" data-testid="barra-anteprima" role="region" aria-label="In ascolto">
      <div className="lettore-cover anteprima-onda" aria-hidden="true"><span /><span /><span /></div>
      <div className="lettore-testo">
        <Link to={`/sound/esplora/${sluggifica(scheda.t)}${famigliaSlug ? `?famiglia=${famigliaSlug}` : ''}`} className="lettore-titolo">{scheda.t}</Link>
        <span className="lettore-meta">{scheda.hz} · {scheda.uso} · ancora {resta} s</span>
        <div className="anteprima-barra"><span style={{ width: `${Math.min(100, (secondi / ANTEPRIMA_SEC) * 100)}%` }} /></div>
      </div>
      <div className="lettore-gesti">
        <button type="button" className="lettore-g lettore-play" onClick={ferma} aria-label="Ferma" data-testid="barra-anteprima-ferma">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 7h10v10H7z" /></svg>
        </button>
      </div>
    </div>
  );
}
