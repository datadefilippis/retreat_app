/**
 * Cuore — MR2: il bottone del cuore, uno solo per tutte le viste.
 * `variante`: 'card' (tondo sulla copertina), 'inline' (accanto a un titolo),
 * 'riga' (in una lista). Il colore acceso e' l'oro di casa.
 */
import React from 'react';
import { emailDellaProva } from '../../../lib/cerchio';
import PortaAurya from '../../account/PortaAurya';   // 8/10 sera: la porta unica, qui dentro

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

/**
 * L'invito all'account, lo stesso ovunque il cuore lo chieda.
 * 8/10 sera (founder): senza uscire dalla pagina. Dentro c'e' la porta unica
 * dell'account (nome, email gia' scritta se sei nel Cerchio, password, la
 * casella legale obbligatoria = l'accettazione): quando sei dentro,
 * `onDentro` chiude e il cuore in attesa si salva da solo. La prova del
 * Cerchio da sola NON basta ad aprire un account: chiunque dichiari un'email
 * iscritta la riceve (unlock), e l'account custodisce ordini e corsi.
 */
export function InvitoAccount({ aperto, onChiudi, onDentro }) {
  if (!aperto) return null;
  return (
    <div className="gate" onClick={onChiudi}>
      <div className="gatebox" style={{ maxWidth: 460 }} onClick={(e) => e.stopPropagation()} data-testid="invito-account">
        <h2>Il tuo spazio vive nel tuo account</h2>
        <p>Preferite, ascolti recenti e «riprendi da dove eri» si ritrovano su ogni telefono con un account Aurya, gratuito: lo stesso di corsi e prenotazioni. Lo crei qui, e il cuore che hai toccato si salva da solo.</p>
        <div className="invito-porta">
          <PortaAurya vista="crea" emailIniziale={emailDellaProva() || ''} contesto="preferite"
            onDentro={(me) => { onDentro?.(me); onChiudi?.(); }} />
        </div>
        <div className="gatefoot" style={{ gap: 8 }}>
          <button type="button" onClick={onChiudi}>Non ora</button>
        </div>
      </div>
    </div>
  );
}
