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

/* IL TEMPO VISIVO DEL BANCO (STEP 5, 26/8/2026).
 *
 * Congelare non e' mettere in pausa il suono: e' fermare l'IMMAGINE
 * mentre il suono continua. E siccome il quadro e' l'unico padrone
 * del tempo di rendering, il tempo fermo abita qui — non tre volte
 * nei tre pannelli. I pittori lo ricevono a ogni giro e decidono
 * cosa significa per loro: chi disegna una traccia ridipinge
 * l'ultimo campione (cosi' un ridimensionamento non la cancella),
 * chi scorre una storia semplicemente non avanza.
 *
 * Il ciclo continua a girare da fermi, ed e' voluto: costa due
 * ridisegni per fotogramma e in cambio l'immagine ferma sopravvive
 * a un cambio di misura della finestra. */
let tempoFermo = false;
const testimoni = new Set();

function giro() {
  giroId = null;
  if (!pittori.size || document.hidden) return;   // il ciclo MUORE, non gira a vuoto
  pittori.forEach((p) => {
    try { p(tempoFermo); } catch { /* un pittore rotto non ferma il banco */ }
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

/** Ferma o riavvia il tempo VISIVO del banco. Il suono non c'entra:
 *  continua a suonare e l'analisi continua a misurare. */
export function congela(valore) {
  const nuovo = !!valore;
  if (nuovo === tempoFermo) return;
  tempoFermo = nuovo;
  testimoni.forEach((f) => { try { f(tempoFermo); } catch { /* nessuno cade */ } });
  sveglia();
}

/** Lo stato del tempo visivo, per chi deve mostrarlo. */
export function eFermo() { return tempoFermo; }

/** Si iscrive ai cambi del tempo visivo (per l'interfaccia). Ritorna
 *  il congedo. Chi ascolta non tiene una COPIA dello stato: legge
 *  questa, che e' l'unica. */
export function ascoltaFermo(fn) {
  testimoni.add(fn);
  return () => { testimoni.delete(fn); };
}

/** Banco di prova: un frame a mano, anche a pagina nascosta. Serve ai
 *  collaudi automatici (dove il pannello non composita e il rAF tace)
 *  — l'app non lo chiama mai. */
export function unGiro() {
  pittori.forEach((p) => { try { p(tempoFermo); } catch { /* come nel giro vero */ } });
}

try { window.__fqzQuadro = { unGiro, congela, eFermo }; } catch { /* SSR/test */ }
