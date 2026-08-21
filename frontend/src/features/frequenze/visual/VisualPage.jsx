/**
 * Aurya Mode — la pagina strumento (AV2-bis, 22/8/2026).
 *
 * Il founder ha consegnato un prototipo HTML e ha chiesto QUELLO,
 * integrale: pannelli, 11 slider, 6 palette, 7 preset, mandala a
 * petali, scorciatoie, drag&drop, impostazioni che si ricordano.
 * Questa pagina lo monta: markup e script sono ESTRATTI dal suo file
 * (prototipoMarkup / prototipo), non trascritti — la fedelta' e'
 * garantita dall'estrazione, gli adattamenti sono patch con assert.
 *
 * La prima stesura di questa pagina (sorgenti + tela semplice) e'
 * stata sostituita: era una mia interpretazione, e il founder ha
 * detto chiaro che l'originale era quello giusto.
 */
import React, { useEffect, useRef } from 'react';
import MARKUP from './prototipoMarkup';
import './prototipo.css';

export default function VisualPage() {
  const rootRef = useRef(null);

  useEffect(() => {
    document.title = 'Aurya Mode — Immersive Visualizer';
    const root = rootRef.current;
    if (!root) return undefined;
    root.innerHTML = MARKUP;
    let pulisci = null;
    let smontato = false;
    // lo script del prototipo (con Three) entra SOLO qui, lazy
    import('./prototipo').then(({ avviaPrototipo }) => {
      if (smontato) return;
      pulisci = avviaPrototipo(root);
    });
    return () => {
      smontato = true;
      pulisci?.();
      root.innerHTML = '';
    };
  }, []);

  return <div className="avz" data-testid="fqz-visual" ref={rootRef} />;
}
