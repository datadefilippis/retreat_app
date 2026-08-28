/**
 * /sound/lab/banco — IL BANCO (LU3, 28/8/2026).
 * La stanza che risponde a: «Com'e' fatto un suono?»
 */
import React from 'react';
import Stanza from './Stanza';
import Generatore from './Generatore';
import SecondaVoce from './SecondaVoce';
import LettureBanco from './LettureBanco';
import { usaLab } from './usaLab';

export default function LabBanco() {
  const { ottieniLab, ottieniAnalisi, ottieniXY,
          fermo, setSuona, suonaDavvero } = usaLab();
  return (
    <Stanza slug="banco" titolo="Il Banco"
      domanda="Com’è fatto un suono?"
      perche={<>Ogni suono che senti — una voce, una campana, il mare —
        è fatto di onde. Qui ne generi una <b>tu</b>, e la guardi mentre
        suona: è il modo più veloce per capire cosa significano parole
        come frequenza, volume, timbro. Niente registrazioni, niente
        trucchi: l&rsquo;onda che senti è calcolata mentre la ascolti.</>}
      azioni={[
        'Genera un tono e guardalo muoversi nelle tre letture',
        'Accendi la Sorgente B alla stessa frequenza, porta la fase a 180° e senti le onde cancellarsi',
        'Passa l’oscilloscopio in XY e guarda la geometria di un intervallo',
      ]}>
      <Generatore ottieniLab={ottieniLab} onSuono={setSuona} />
      <SecondaVoce ottieniLab={ottieniLab}
        onSuono={() => setSuona((v) => !v)} />
      <LettureBanco ottieniAnalisi={ottieniAnalisi} ottieniXY={ottieniXY}
        fermo={fermo} suonaDavvero={suonaDavvero} />
    </Stanza>
  );
}
