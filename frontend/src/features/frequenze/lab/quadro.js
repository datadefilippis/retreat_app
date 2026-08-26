/**
 * IL QUADRO (26/8/2026) — l'unico ciclo di disegno del Lab.
 *
 * Regola dello STEP 2, che varra' per tutti gli strumenti a venire
 * (spettro compreso): UN solo requestAnimationFrame per tutto il
 * banco. Ogni pannello iscrive il suo pittore; il ciclo gira solo se
 * c'e' almeno un pittore E la pagina e' visibile — su
 * visibilitychange si ferma da solo e riparte da solo (il pattern di
 * AuryaMode: il suono continua, il disegno riposa).
 *
 * React-free come il motore: i pannelli si iscrivono in useEffect e
 * restituiscono il congedo.
 */

const pittori = new Set();
let giroId = null;

function giro() {
  giroId = null;
  if (!pittori.size || document.hidden) return;   // il ciclo MUORE, non gira a vuoto
  pittori.forEach((p) => {
    try { p(); } catch { /* un pittore rotto non ferma il banco */ }
  });
  giroId = requestAnimationFrame(giro);
}

function sveglia() {
  if (giroId === null && pittori.size && !document.hidden) {
    giroId = requestAnimationFrame(giro);
  }
}

try {
  document.addEventListener('visibilitychange', sveglia);
} catch { /* SSR/test: niente document */ }

/** Iscrive un pittore (chiamato una volta per frame). Ritorna il congedo. */
export function iscrivi(pittore) {
  pittori.add(pittore);
  sveglia();
  return () => { pittori.delete(pittore); };
}

/** Banco di prova: un frame a mano, anche a pagina nascosta. Serve ai
 *  collaudi automatici (dove il pannello non composita e il rAF tace)
 *  — l'app non lo chiama mai. */
export function unGiro() {
  pittori.forEach((p) => { try { p(); } catch { /* come nel giro vero */ } });
}

try { window.__fqzQuadro = { unGiro }; } catch { /* SSR/test */ }
