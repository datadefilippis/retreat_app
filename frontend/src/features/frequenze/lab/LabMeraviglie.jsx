/**
 * /sound/lab/meraviglie — LE MERAVIGLIE (LU3, 28/8/2026).
 * La stanza che risponde a: «Cosa sa fare davvero il suono (senza trucchi)?»
 */
import React from 'react';
import Stanza from './Stanza';
import Meraviglie from './Meraviglie';
import LettureBanco from './LettureBanco';
import { useLab } from './usaLab';

export default function LabMeraviglie() {
  const { ottieniLab, ottieniAnalisi, ottieniXY,
          fermo, suonaDavvero } = useLab();
  return (
    <Stanza slug="meraviglie" titolo="Le Meraviglie"
      domanda="Cosa sa fare davvero il suono — senza trucchi?"
      perche={<>Vortici che ti girano attorno alla testa, suoni che il
        tuo orecchio <b>inventa</b>, scale che scendono per sempre,
        geometrie che emergono dai numeri. Sono tutti fenomeni veri —
        fisica e psicoacustica documentate — e ognuno porta il suo
        cartellino: qui la meraviglia non ha bisogno di mentire.
        Le letture qui sotto sono la prova: quello che senti si
        misura.</>}
      azioni={[
        'Avvia il Vortice in cuffia e chiudi gli occhi',
        'Ascolta il terzo suono di Tartini — poi guarda lo spettro: nell’aria non c’è',
        'Avvia un Rapporto e passa l’oscilloscopio in XY: l’intervallo si disegna',
      ]}>
      <Meraviglie ottieniLab={ottieniLab} />
      <LettureBanco ottieniAnalisi={ottieniAnalisi} ottieniXY={ottieniXY}
        fermo={fermo} suonaDavvero={suonaDavvero} />
    </Stanza>
  );
}
