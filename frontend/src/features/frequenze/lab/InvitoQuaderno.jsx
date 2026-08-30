/**
 * L'INVITO DEL QUADERNO (FA4, piano FARO 30/8/2026) — il trigger
 * account, al momento giusto: il PRIMO salvataggio.
 *
 * LA REGOLA DEL SILENZIO (contratto FARO): chi ha gia' l'account non
 * vede nulla — il controllo sta PRIMA del render. Mai un popup, mai
 * un blocco: una riga sotto la conferma di salvataggio, coi link di
 * ritorno (?next=) alla stanza. La fonte e' tracciata nel next per
 * il funnel (sound:quaderno:{stanza}).
 */
import React from 'react';
import { haAccount } from './quadernoRemoto';
import { creaAccount, entraInAurya } from '../../../utils/authLinks';

export default function InvitoQuaderno({ stanza }) {
  if (haAccount()) return null;
  const dove = `/sound/lab/${stanza}?da=quaderno`;
  /* Founder (30/8): il testo si confondeva coi bianchi intorno —
     l'invito diventa una CARD bordata d'oro con bottone pieno:
     l'utente va incentivato, non sussurrato. */
  return (
    <div className="lab-invito-quaderno" data-testid="lab-invito-quaderno">
      <p className="lab-invito-titolo">Salvato su questo dispositivo.</p>
      <p>Con un account Aurya, gratis, il tuo quaderno ti segue
        ovunque: lo ritrovi da telefono e computer, per sempre.</p>
      <p className="lab-invito-gesti">
        <a className="lab-invito-crea" href={creaAccount('', dove)}>
          Crea l&rsquo;account gratis</a>
        <a className="lab-invito-accedi" href={entraInAurya('', dove)}>
          Ho già un account</a>
      </p>
    </div>
  );
}
