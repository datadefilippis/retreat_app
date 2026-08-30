/**
 * /sound/lab/risonanze — LE RISONANZE (LU3, 28/8/2026).
 * La stanza che risponde a: «A quale frequenza canta il mio oggetto?»
 */
import React from 'react';
import Stanza from './Stanza';
import Risonanze from './Risonanze';
import { useLab } from './usaLab';

export default function LabRisonanze() {
  const { ottieniLab, ottieniAnalisi } = useLab();
  return (
    <Stanza slug="risonanze" titolo="Le Risonanze"
      domanda="A quale frequenza canta il mio oggetto?"
      perche={<>Ogni oggetto ha frequenze a cui <b>risuona</b>, dove
        basta pochissima energia per farlo vibrare forte. Qui il banco
        le trova da solo: uno sweep lento lo interroga, il microfono
        ascolta quando risponde, e la curva ti mostra i picchi. È il
        primo passo della cimatica: trovata la frequenza, tienila
        addosso all&rsquo;oggetto e <b>guarda</b>, riso sulla lattina,
        acqua nel bicchiere.</>}
      azioni={[
        'Metti una bottiglia vicino ad altoparlante e microfono, avvia la misura',
        'Leggi i picchi in oro: sono le frequenze dove il tuo oggetto canta',
        'Scarica il WAV di un tono trovato e usalo su un amplificatore vero',
      ]}>
      <Risonanze ottieniLab={ottieniLab} ottieniAnalisi={ottieniAnalisi} />
    </Stanza>
  );
}
