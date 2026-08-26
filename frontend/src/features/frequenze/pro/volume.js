/**
 * IL VOLUME — la conversione fra ciò che si legge e ciò che si manda.
 *
 * Il DSL parla di `gain`, un numero fra 0.05 e 1. All'operatore non si
 * mostra `0.17`: si mostra `17%`. La conversione è una divisione per
 * cento — esatta, reversibile, senza scale psicologiche («rilassante»,
 * «intenso»): quelle prometterebbero un effetto, e Aurya Sound non
 * promette effetti.
 *
 * Vive in un file suo, e non dentro la pagina, per due ragioni: si può
 * nominare (quindi discutere) e si può eseguire in Node (quindi
 * provare, come i compilatori). Il round-trip è sotto guardia.
 */

/* i limiti sono quelli del DSL (pro/compilatore.js): lo zero è muto e
   sta fuori dall'editor, l'uno è il tetto del contratto */
export const PERCENTO_MIN = 5;
export const PERCENTO_MAX = 100;
export const PERCENTO_DEFAULT = 25;

/** percentuale → gain del DSL. 17 → 0.17 */
export function aGain(percento) {
  const p = Math.min(PERCENTO_MAX, Math.max(PERCENTO_MIN, Math.round(percento)));
  /* due decimali: 17/100 in virgola mobile è 0.17000000000000001 */
  return Math.round(p) / 100;
}

/** gain del DSL → percentuale. 0.17 → 17 */
export function aPercento(gain) {
  if (!Number.isFinite(gain)) return PERCENTO_DEFAULT;
  return Math.min(PERCENTO_MAX, Math.max(PERCENTO_MIN, Math.round(gain * 100)));
}
