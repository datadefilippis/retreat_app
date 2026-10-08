/**
 * Cuore — MR2: il bottone del cuore, uno solo per tutte le viste.
 * `variante`: 'card' (tondo sulla copertina), 'inline' (accanto a un titolo),
 * 'riga' (in una lista). Il colore acceso e' l'oro di casa.
 */
import React from 'react';
import { creaAccount } from '../../../utils/authLinks';
import { emailDellaProva } from '../../../lib/cerchio';

const Forma = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true">
    <path d="M12 20.2S5.6 16 3.2 12.4C1.1 9.3 2.7 5.4 6 5.4c2 0 3.1 1 4.2 2.5.7 1 .9 1 1.6 0C12.9 6.4 14 5.4 16 5.4c3.3 0 4.9 3.9 2.8 7C16.4 16 12 20.2 12 20.2z" />
  </svg>
);

export default function Cuore({ on = false, onClick, variante = 'card', titolo = '', testid = 'cuore' }) {
  return (
    <button type="button" className={`cuore cuore-${variante}${on ? ' on' : ''}`} aria-pressed={on}
      title={on ? `Togli dalle preferite${titolo ? `: ${titolo}` : ''}` : `Salva tra le preferite${titolo ? `: ${titolo}` : ''}`}
      data-testid={testid} onClick={(e) => { e.preventDefault(); e.stopPropagation(); onClick?.(); }}>
      <Forma />
    </button>
  );
}

/** l'invito all'account, lo stesso ovunque il cuore lo chieda */
export function InvitoAccount({ aperto, onChiudi, ritorno = '/meditazioni' }) {
  if (!aperto) return null;
  return (
    <div className="gate" onClick={onChiudi}>
      <div className="gatebox" style={{ maxWidth: 460 }} onClick={(e) => e.stopPropagation()}>
        <h2>Il tuo spazio vive nel tuo account</h2>
        <p>Preferite, ascolti recenti e «riprendi da dove eri» si ritrovano su ogni telefono con un account Aurya, gratuito: lo stesso di corsi e prenotazioni.</p>
        <div className="gatefoot" style={{ gap: 8 }}>
          <button type="button" className="primary" onClick={() => { window.location.href = creaAccount(emailDellaProva() || '', ritorno); }}>Crea il tuo account</button>
          <button type="button" onClick={onChiudi}>Non ora</button>
        </div>
      </div>
    </div>
  );
}
