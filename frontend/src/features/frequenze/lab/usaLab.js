/**
 * USA-LAB — il ciclo di vita del banco per pagina (LU2, 28/8/2026).
 *
 * Con le stanze (ciclo LU) ogni pagina del Lab possiede il SUO
 * motore: nasce al primo gesto (AudioContext e ponte vogliono un
 * tocco — iOS docet), si presta ai pannelli, e si spegne quando la
 * pagina si smonta (senza aspettare il GC, e scongelando il tempo
 * visivo). Prima questa disciplina viveva in SoundLabPage: ora e'
 * UNA e le stanze non possono divergere.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { creaLaboratorio } from './motore';
import { ascoltaFermo, congela, eFermo } from './quadro';

export function usaLab() {
  const labRef = useRef(null);

  const ottieniLab = useCallback(() => {
    if (!labRef.current) {
      const Ctx = window.AudioContext || window.webkitAudioContext;
      labRef.current = creaLaboratorio(new Ctx());
    }
    return labRef.current;
  }, []);

  /* le prese, STABILI: un'arrow nel JSX ri-iscriverebbe i pittori a
     ogni render (trappola pagata allo STEP 5) */
  const ottieniAnalisi = useCallback(() => labRef.current?.analisi || null, []);
  const ottieniXY = useCallback(() => {
    const lab = labRef.current;
    if (!lab) return null;
    return { a: (buf) => lab.generatore.tempo(buf),
             b: (buf) => lab.generatore2.tempo(buf) };
  }, []);

  /* il tempo visivo e' del banco e vive nel quadro: ci si iscrive */
  const [fermo, setFermo] = useState(eFermo());
  useEffect(() => ascoltaFermo(setFermo), []);

  /* l'avviso serve a FAR ridisegnare; la verita' si chiede al motore */
  const [suona, setSuona] = useState(false);
  const suonaDavvero = labRef.current
    ? (labRef.current.generatore.stato().attivo
       || labRef.current.generatore2.stato().attivo)
    : suona;

  /* lasciare la stanza spegne il banco — e scongela */
  useEffect(() => () => { labRef.current?.spegni(); congela(false); }, []);

  return { ottieniLab, ottieniAnalisi, ottieniXY,
           fermo, suona, setSuona, suonaDavvero };
}
