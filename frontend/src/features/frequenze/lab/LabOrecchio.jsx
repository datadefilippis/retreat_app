/**
 * /sound/lab/orecchio — L'ORECCHIO (LU3, 28/8/2026).
 * La stanza che risponde a: «Che nota e'? Che suono fa il mondo?»
 */
import React from 'react';
import Stanza from './Stanza';
import Orecchio from './Orecchio';
import LettureBanco from './LettureBanco';
import { useLab } from './usaLab';

export default function LabOrecchio() {
  const { ottieniLab, ottieniAnalisi, ottieniVivo, fermo, suonaDavvero } = useLab();
  return (
    <Stanza slug="orecchio" titolo="L’Orecchio"
      domanda="Che nota è? Che suono fa il mondo?"
      perche={<>Il banco può ascoltare, oltre che generare: apri il
        microfono e le letture ti mostrano il suono <b>vero</b> — la tua
        voce, un bicchiere colpito, la stanza in cui sei.
        L&rsquo;accordatore ti dice la nota con la precisione di uno
        strumento. E il suono non lascia mai il tuo dispositivo: il
        microfono si collega solo all&rsquo;analisi.</>}
      azioni={[
        'Canta o fischia una nota tenuta: l’accordatore la nomina, coi cents di scarto',
        'Colpisci un bicchiere davanti allo spettro e guarda i SUOI modi apparire',
        'Osserva la tua voce nello spettrogramma: le armoniche sono righe parallele',
      ]}>
      <Orecchio ottieniLab={ottieniLab} ottieniAnalisi={ottieniAnalisi}
        ottieniVivo={ottieniVivo} />
      <LettureBanco ottieniAnalisi={ottieniAnalisi}
        fermo={fermo} suonaDavvero={suonaDavvero} />
    </Stanza>
  );
}
