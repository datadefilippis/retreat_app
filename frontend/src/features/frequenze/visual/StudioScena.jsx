/**
 * Lo studio della scena (VC6, 22/8/2026).
 *
 * Il founder: «tutte le regolazioni in un pannello a tutto schermo,
 * esattamente come /sound/visual; cliccando sulla forma si apre».
 * Ed e' letteralmente quello: stesso markup, stesso script, stesse
 * manopole — in modalita' `studio`, cioe' con le sorgenti spente (il
 * suono e' la sessione che sta gia' suonando in Crea) e la memoria
 * nella ricetta invece che nel browser.
 *
 * L'audio NON si interrompe: questo e' un velo sopra la pagina, non
 * una navigazione. Si chiude con «Fatto», col marchio o con ESC, e
 * cio' che l'autore ha scelto torna indietro in un colpo solo.
 *
 * Vive in un PORTALE su <body>, non dentro Crea. Non e' un dettaglio:
 * montato nella pagina, lo studio eredita il CSS del sito — e succede
 * davvero (`.fqz .row` sotto i 900px impala le righe in colonna, e i
 * valori dei cursori finivano sotto le etichette). Il prototipo l'ho
 * chiuso perche' non uscisse; il portale impedisce al sito di
 * entrare. In piu' evita che un antenato con `transform` diventi il
 * riferimento dei nostri `position:fixed`.
 */
import React, { useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import MARKUP from './prototipoMarkup';
import './prototipo.css';

export default function StudioScena({ lettore, visual, titolo, onChiudi }) {
  const rootRef = useRef(null);
  /* la chiusura cambia a ogni render (chiude sopra `visual`), ma il
     motore si monta UNA volta sola: il riferimento evita di
     rimontarlo — rimontarlo significherebbe ricostruire 24.000
     particelle a ogni battito di stato */
  const chiudiRef = useRef(onChiudi);
  chiudiRef.current = onChiudi;

  useEffect(() => {
    const root = rootRef.current;
    if (!root) return undefined;
    root.innerHTML = MARKUP;
    let manico = null;
    let smontato = false;
    const primaOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';   // la pagina sotto non scorre

    import('./prototipo').then(({ avviaPrototipo }) => {
      if (smontato) return;
      try {
        manico = avviaPrototipo(root, {
          studio: true,
          /* se la sessione non sta suonando l'analizzatore non c'e':
             il prototipo ha il suo respiro di riposo, e si scelgono
             forma e colori su una scena che si muove piano */
          analizzatore: lettore?.analyser,
          sampleRate: lettore?.analyser?.context?.sampleRate,
          impostazioni: visual || undefined,
          /* in cima si legge il titolo che l'autore ha dato alla
             sessione — «La tua sessione» solo finche' non ce n'e' uno */
          titolo,
          alFatto: (scelta) => chiudiRef.current?.(scelta),
        });
      } catch {
        chiudiRef.current?.(null);   // niente WebGL: si torna indietro
      }
    }).catch(() => chiudiRef.current?.(null));

    return () => {
      smontato = true;
      document.body.style.overflow = primaOverflow;
      manico?.pulisci?.();
      root.innerHTML = '';
    };
    // il montaggio e' uno solo: `visual` e' lo stato INIZIALE, e da
    // qui in poi la verita' e' dentro il motore
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lettore]);

  return createPortal(
    <div className="avz" data-testid="fqc-studio" ref={rootRef} />,
    document.body,
  );
}
