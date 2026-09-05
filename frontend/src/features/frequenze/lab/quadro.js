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
  const t0 = performance.now();
  pittori.forEach((p) => {
    try { p(tempoFermo); } catch { /* un pittore rotto non ferma il banco */ }
  });
  misuraCosto(performance.now() - t0);
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

/* ═══ LM3 (5/9/2026) — IL BUDGET DEL DISEGNO SUL TELEFONO ═══
 *
 * Il founder, dal telefono: «riascoltando il ritratto scattava e
 * tremava tutto». Misurato sul banco: l'Onda viva costava il 95% del
 * fotogramma (tre tracciati da 2048 punti, scia a piena risoluzione,
 * shadowBlur a 8·dpr); su un telefono a dpr 3 col blur software di
 * WebKit sono decine di millisecondi, e il ponte <audio> alimentato
 * da un MediaStream su iOS scatta proprio quando il thread principale
 * e' saturo.
 *
 * La regola vive QUI, non tre volte nei pittori: l'ECONOMIA si accende
 * su un dispositivo a tocco (pointer: coarse) o quando il giro medio
 * dei pittori supera i 10 ms — e resta accesa (mai un'oscillazione
 * fra bello e leggero). In economia le tele si disegnano al massimo a
 * dpr 1,5 (un quarto dei pixel a dpr 3) e i pittori saltano il
 * bagliore (shadowBlur). Su desktop non cambia nulla. */
let costoMedio = null;
let economiaAccesa = false;
let economiaForzata = null;               // solo collaudo: true/false/null
function misuraCosto(ms) {
  costoMedio = costoMedio === null ? ms : costoMedio * 0.9 + ms * 0.1;
  if (costoMedio > 10) economiaAccesa = true;
}
function toccoGrosso() {
  try { return !!(window.matchMedia && window.matchMedia('(pointer: coarse)').matches); }
  catch { return false; }
}
/** Vero quando il disegno deve stare leggero (telefono, o giro lento). */
export function economia() {
  if (economiaForzata !== null) return economiaForzata;
  return economiaAccesa || toccoGrosso();
}
/** La densita' di pixel con cui disegnare le tele: piena su desktop,
 *  al massimo 1,5 in economia. */
export function dprTela() {
  const dpr = (typeof window !== 'undefined' && window.devicePixelRatio) || 1;
  return economia() ? Math.min(dpr, 1.5) : dpr;
}
/** Collaudo: forza l'economia (true/false) o torna all'automatico (null). */
export function forzaEconomia(v) { economiaForzata = v; }
/** Il costo medio del giro, in ms (null finche' non gira). */
export function costoGiro() { return costoMedio; }

try {
  window.__fqzQuadro = { unGiro, congela, eFermo, economia, forzaEconomia, costoGiro };
} catch { /* SSR/test */ }
