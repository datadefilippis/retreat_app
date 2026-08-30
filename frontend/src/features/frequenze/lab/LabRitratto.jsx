/**
 * /sound/lab/ritratto — IL RITRATTO (LU3, 28/8/2026).
 * La stanza che risponde a: «Di cosa e' fatto il suono del MIO oggetto?»
 */
import React from 'react';
import Stanza from './Stanza';
import Orecchio from './Orecchio';
import Ritratto from './Ritratto';
import { useLab } from './usaLab';

export default function LabRitratto() {
  const { ottieniLab, ottieniAnalisi, ottieniVivo } = useLab();
  return (
    <Stanza slug="ritratto" titolo="Il Ritratto"
      domanda="Di cosa è fatto il suono del mio oggetto?"
      perche={<>Una campana, un bicchiere, una corda: ogni oggetto
        vibra solo sui <b>suoi</b> modi, come un&rsquo;impronta digitale.
        Qui registri sei secondi del suo suono e ne esce la carta
        d&rsquo;identità: quali frequenze lo compongono, quanto vive
        ciascuna, dove batte lo «shimmer». E poi la magia onesta: il
        banco lo <b>rifonde</b>, riascolti l&rsquo;originale e la copia
        sintetica, fianco a fianco, e capisci il timbro smontandolo.</>}
      azioni={[
        'Apri il microfono, registra il colpo di una campana o di un bicchiere',
        'Leggi la tabella dei suoi modi: frequenze, vite, doppietti',
        'Riascolta in A/B: originale contro rifusione, poi spegni un parziale e risenti',
      ]}>
      <Orecchio ottieniLab={ottieniLab} ottieniAnalisi={ottieniAnalisi}
        ottieniVivo={ottieniVivo} />
      <Ritratto ottieniLab={ottieniLab} ottieniAnalisi={ottieniAnalisi} />
    </Stanza>
  );
}
