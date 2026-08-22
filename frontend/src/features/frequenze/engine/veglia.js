/**
 * Frequenze by Aurya — lo schermo resta acceso mentre si ascolta
 * (AT2, 21/8/2026).
 *
 * Il problema: la sintesi e' WebAudio dal vivo, e i browser mobili la
 * sospendono appena la pagina va in background — schermo che si
 * oscura da solo compreso. La soluzione VERA per il blocco schermo e'
 * l'ascolto continuo (engine/continuo.js: file + <audio>); questa e'
 * la rete sotto: finche' si ascolta dal vivo, chiediamo al sistema di
 * NON spegnere lo schermo da solo (Screen Wake Lock API).
 *
 * Contratto con le pagine: un solo interruttore derivato dallo stato
 * («qualcosa sta suonando si'/no»), via useEffect — niente conteggi
 * sparsi per i punti di stop, che perdono il conto al primo percorso
 * dimenticato. Il lock:
 * - si rilascia da solo quando la pagina va in background (e' il
 *   comportamento dell'API): al ritorno visibile lo riprendiamo;
 * - non esiste ovunque (Safari < 16.4, browser vecchi): dove manca,
 *   questo modulo tace — nessun errore, semplicemente niente rete.
 */

let lock = null;
let voluto = false;      // «qualcosa sta suonando»: l'intenzione delle pagine
let agganciato = false;  // il listener di visibilita' si monta una volta sola

async function acquisisci() {
  if (!('wakeLock' in navigator)) return;
  try {
    lock = await navigator.wakeLock.request('screen');
    // il sistema puo' rilasciarlo quando vuole: non restare col fantasma
    lock.addEventListener('release', () => { lock = null; });
  } catch {
    lock = null;   // negato (risparmio energetico, permessi): pazienza
  }
}

function alRitorno() {
  if (document.visibilityState === 'visible' && voluto && !lock) acquisisci();
}

export function schermoAcceso() {
  voluto = true;
  if (!agganciato) {
    document.addEventListener('visibilitychange', alRitorno);
    agganciato = true;
  }
  if (!lock) acquisisci();
}

export function schermoLibero() {
  voluto = false;
  if (lock) { lock.release().catch(() => {}); lock = null; }
}

/* TS4 — la sorveglianza del contesto audio. iOS sospende il contesto
   quando si riprende l'audio (chiamata in arrivo, Siri, cambio app):
   senza questo aggancio la UI resta su «suona» mentre il suono non
   c'e' piu' — una bugia identica alla scheda muta del resume mancato.
   Un listener solo per contesto; al passaggio fuori da 'running' si
   avvisa la pagina, che ferma la SUA UI (mai il contesto: riprenderlo
   e' un gesto dell'utente). */
export function sorvegliaContesto(ctx, onPerso) {
  if (ctx._fqzSorvegliato) return;
  ctx._fqzSorvegliato = true;
  ctx.addEventListener('statechange', () => {
    if (ctx.state !== 'running') onPerso();
  });
}

