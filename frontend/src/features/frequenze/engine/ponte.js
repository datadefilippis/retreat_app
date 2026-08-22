/**
 * Il PONTE — l'unico sbocco del suono del motore (22/8/2026).
 *
 * Trovato in produzione dal founder, su iPhone: i suoni singoli si
 * sentivano (sono un <audio>), la sessione e la meditazione no (erano
 * WebAudio collegato all'altoparlante). Su iOS — dove OGNI browser e'
 * WebKit per obbligo, Brave incluso — i due canali vivono in regimi
 * diversi: un <audio> e' «musica» e suona sempre; il grafo WebAudio a
 * ctx.destination e' suono di CONTORNO, azzerabile dal silenziatore e
 * sottoposto a regole piu' severe. La meditazione muta era puramente
 * sintetica: non erano i file, era il canale.
 *
 * La cura e' UN canale solo, su ogni piattaforma: il motore sfocia in
 * un MediaStreamDestination, e quello alimenta un <audio playsinline>.
 * Stesso percorso per iPhone, Android e desktop — cio' che si verifica
 * su una piattaforma vale per le altre. L'analizzatore di Aurya Mode
 * resta un osservatore in parallelo: guarda, non trasporta.
 *
 * Regole d'uso:
 * - UN ponte per contesto (qui dentro c'e' il registro);
 * - `avvia()` va chiamata DENTRO il gesto dell'utente (il tocco su
 *   Ascolta): e' cio' che soddisfa ogni politica di autoplay;
 * - il nodo del ponte e' lo `sbocco` da passare al motore.
 */

/* iOS 16.4+: dichiara al sistema che questo sito suona MUSICA, non
   effetti. Innocuo dove l'API non esiste. */
function dichiaraMusica() {
  try {
    if (typeof navigator !== 'undefined' && navigator.audioSession) {
      navigator.audioSession.type = 'playback';
    }
  } catch { /* nessun browser deve rompersi per questo */ }
}

export function creaPonte(ctx) {
  if (ctx._fqzPonte) return ctx._fqzPonte;
  dichiaraMusica();
  const nodo = ctx.createMediaStreamDestination();
  const el = new Audio();
  el.srcObject = nodo.stream;
  el.playsInline = true;
  /* ancorato al documento: un elemento orfano suona, ma su iOS e' piu'
     fragile (e non e' ispezionabile). Nessuna UI: e' solo un condotto. */
  el.dataset.fqzPonte = '1';
  try { document.body.appendChild(el); } catch { /* SSR/test */ }
  const ponte = {
    /* lo sbocco del motore: startPreview ci si collega */
    nodo,
    el,
    /* da chiamare nel GESTO: se il play dell'elemento fallisse (non
       dovrebbe: siamo dentro un tocco), non deve rompere la sessione */
    async avvia() {
      try { await el.play(); } catch { /* il grafo suona comunque dove puo' */ }
    },
    ferma() {
      try { el.pause(); } catch { /* niente */ }
    },
  };
  ctx._fqzPonte = ponte;
  return ponte;
}
