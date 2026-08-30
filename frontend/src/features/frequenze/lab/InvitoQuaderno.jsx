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
  return (
    <p className="lab-invito-quaderno" data-testid="lab-invito-quaderno">
      Salvato su questo dispositivo. Con un account Aurya (gratis) il
      tuo quaderno ti segue ovunque —{' '}
      <a href={creaAccount('', dove)}>crea l&rsquo;account</a>
      {' '}·{' '}
      <a href={entraInAurya('', dove)}>accedi</a>
    </p>
  );
}
