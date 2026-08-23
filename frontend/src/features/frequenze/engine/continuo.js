/**
 * Frequenze by Aurya — ascolto continuo a schermo bloccato
 * (AT3, 21/8/2026).
 *
 * Il fatto: la sintesi dal vivo e' WebAudio, e i browser mobili la
 * SOSPENDONO quando lo schermo si blocca — regola loro, non si
 * aggira. Quello che invece sopravvive al blocco e' un media element
 * che riproduce un file, come un lettore musicale. Quindi: si
 * renderizza la sessione in un file (renderPcm gia' esisteva per
 * l'export dell'operatore) e la si riproduce con <audio> + Media
 * Session — che in piu' mette titolo, copertina e play/pausa sulla
 * schermata di blocco.
 *
 * Le scelte, e il loro perche':
 * - WAV, non MP3: l'encoder c'e' (lamejs) ma su un telefono comprime
 *   a pochi multipli del tempo reale — minuti di attesa in piu'. Il
 *   WAV e' pronto appena renderizzato;
 * - 22050 Hz: meta' tempo di render e meta' memoria di 44100. Il
 *   contenuto ci sta tutto: la portante piu' alta del catalogo e' 963
 *   Hz (con le armoniche del timbro caldo ~2,9 kHz) e la voce parlata
 *   vive sotto gli 8 kHz; il limite di banda a 11 kHz toglie solo un
 *   po' d'aria alle basi naturali — prezzo dichiarato, non nascosto;
 * - tetto a 30 minuti: a 22050 Hz stereo sono ~158 MB di file, il
 *   massimo che un telefono regge senza rischiare. Oltre, il pulsante
 *   non compare: meglio un limite onesto di un crash a meta' notte;
 * - il render NON parte da solo: e' un'attesa (secondi o minuti, con
 *   il progresso visibile) che l'utente sceglie con un tocco.
 *
 * Il cancello dei 90 secondi resta sovrano: la pagina offre il
 * continuo solo a sblocco avvenuto — un file intero in mano a chi ha
 * l'anteprima sarebbe il cancello demolito da un'altra porta.
 */

import { renderPcm, wavBlob } from './render';
import { durataAnello, scoreAnello, ritagliaAnello } from './anello';

export const CONTINUO_SR = 22050;
export const CONTINUO_MAX_SEC = 1800;   // 30 min: ~158 MB di WAV, il tetto del telefono

export function continuoDisponibile(score) {
  return (score?.duration_sec || 0) <= CONTINUO_MAX_SEC;
}

/* C'e' un motivo per offrirlo? Solo dove l'API esiste e serve: la
   Media Session e' il segnale che il browser sa fare il lettore
   musicale. Dove manca (browser d'epoca) il pulsante non compare. */
export function continuoSupportato() {
  return typeof Audio !== 'undefined' && 'mediaSession' in navigator;
}

/**
 * Renderizza lo score e prepara il lettore.
 *
 * @param opts { score, audioLayers, voiceLayers, voiceDuck,
 *               titolo, autore, onProgress }
 * @param eventi { onPlay, onPause, onTime, onEnd } — arrivano ANCHE
 *        dai comandi della schermata di blocco, non solo dalla UI:
 *        la pagina si tiene sincronizzata ascoltando questi, mai
 *        supponendo di essere l'unica a comandare.
 * @returns handle { play, pause, seek, currentTime, dispose }
 */
export async function preparaContinuo(
  { score, audioLayers = [], voiceLayers = [], voiceDuck = false,
    titolo, autore, onProgress },
  eventi = {},
) {
  const pcm = await renderPcm(score, {
    sampleRate: CONTINUO_SR, audioLayers, voiceLayers, voiceDuck, onProgress,
  });
  return lettore(pcm, score.duration_sec, { titolo, autore }, eventi, false);
}

/**
 * L'ANELLO di una scheda: la stessa frequenza, ma in un file che gira
 * all'infinito — come gia' fanno i suoni della libreria, che sono file
 * dentro un <audio loop> ed e' il motivo per cui LORO sopravvivono al
 * blocco schermo e le frequenze no.
 *
 * @param cfg       il cfg della scheda
 * @param battito   il ritmo da tenere (l'arrivo del tragitto, o il
 *                  numero che l'utente ha imposto col campo)
 * @param portante  la portante da tenere (idem)
 */
export async function preparaAnello(
  { cfg, battito, portante, titolo, onProgress }, eventi = {},
) {
  const { sec, esatto } = durataAnello(cfg, battito);
  const score = scoreAnello(cfg, battito, portante, sec);
  const pcm = await renderPcm(score, { sampleRate: CONTINUO_SR, onProgress });
  const anello = ritagliaAnello(pcm, CONTINUO_SR, sec);
  const h = lettore(anello, sec, { titolo, autore: null }, eventi, true);
  h.giroSec = sec;
  h.giroEsatto = esatto;
  return h;
}

/* Il lettore vero e proprio: <audio> + Media Session. Uno solo, per la
   sessione e per l'anello — due copie divergerebbero alla prima
   modifica (e i comandi della schermata di blocco sono proprio la
   cosa che non ci si accorge di aver rotto). */
function lettore(pcm, d, meta, eventi, ciclico) {
  const url = URL.createObjectURL(wavBlob(pcm, CONTINUO_SR));
  return lettoreDaSrc(url, d, meta, eventi, { ciclico, daRevocare: true });
}

/* IL MASTER (23/8) — lo stesso lettore, ma la sorgente e' un URL di
   rete: il file renderizzato ALLA PUBBLICAZIONE dal browser
   dell'operatore, servito in streaming. L'elemento resta un <audio>
   PURO (niente grafo in mezzo: un grafo si sospende a schermo
   bloccato — la lezione AT3); per il visual, `presaAnalisi(analyser)`
   aggancia una COPIA via captureStream dove il browser la offre —
   dove manca, la scena resta nel respiro di veglia. Il suono prima
   del visual. */
export function lettoreDaUrl(url, d, meta, eventi = {}) {
  return lettoreDaSrc(url, d, meta, eventi, { ciclico: false, daRevocare: false });
}

function lettoreDaSrc(url, d, { titolo, autore }, eventi, { ciclico, daRevocare }) {
  const el = new Audio(url);
  el.crossOrigin = 'anonymous';
  el.preload = 'auto';
  el.loop = !!ciclico;
  const posizione = () => {
    // un anello non ha una fine: dichiararne una farebbe disegnare al
    // telefono una barra che arriva in fondo e non finisce mai
    if (ciclico || !('setPositionState' in navigator.mediaSession)) return;
    try {
      navigator.mediaSession.setPositionState(
        { duration: d, playbackRate: 1, position: Math.min(d, el.currentTime) });
    } catch { /* posizione decorativa: mai un motivo per fermarsi */ }
  };
  el.addEventListener('play', () => { eventi.onPlay?.(); posizione(); });
  el.addEventListener('pause', () => eventi.onPause?.());
  el.addEventListener('ended', () => eventi.onEnd?.());
  el.addEventListener('timeupdate', () => {
    eventi.onTime?.(el.currentTime); posizione();
  });

  navigator.mediaSession.metadata = new window.MediaMetadata({
    title: titolo || 'Sessione',
    artist: autore ? `${autore} · Aurya Sound` : 'Aurya Sound',
    artwork: [{ src: '/logo-aurya-512.png', sizes: '512x512', type: 'image/png' }],
  });
  const az = (nome, fn) => {
    try { navigator.mediaSession.setActionHandler(nome, fn); } catch { /* azione non supportata */ }
  };
  az('play', () => el.play());
  az('pause', () => el.pause());
  az('stop', () => { el.pause(); el.currentTime = 0; });
  // spostarsi dentro un anello non vuol dire niente: sono tutti lo
  // stesso istante. Registrare i comandi disegnerebbe frecce inerti.
  if (!ciclico) {
    az('seekbackward', (e2) => { el.currentTime = Math.max(0, el.currentTime - (e2.seekOffset || 15)); });
    az('seekforward', (e2) => { el.currentTime = Math.min(d, el.currentTime + (e2.seekOffset || 15)); });
    az('seekto', (e2) => { if (e2.seekTime != null) el.currentTime = e2.seekTime; });
  }

  return {
    play: () => el.play().catch(() => { /* gesto mancante: la UI mostra ▶ */ }),
    pause: () => el.pause(),
    seek: (t) => { el.currentTime = Math.max(0, Math.min(d, t)); },
    currentTime: () => el.currentTime,
    /* la presa per il visual: una COPIA del flusso verso l'analyser,
       senza dirottare l'uscita dell'elemento (MediaElementSource la
       dirotterebbe: canale-contorno su iOS e silenzio a schermo
       bloccato). Se captureStream non c'e', si torna false e la scena
       resta in veglia. */
    presaAnalisi: (ctx, analyser) => {
      try {
        /* SOLO captureStream standard: il mozCaptureStream di
           Firefox DIROTTA l'uscita (elemento muto) — meglio niente
           visual che niente suono */
        const flusso = el.captureStream ? el.captureStream() : null;
        if (!flusso || !flusso.getAudioTracks().length) return false;
        const src = ctx.createMediaStreamSource(flusso);
        src.connect(analyser);
        return true;
      } catch { return false; }
    },
    dispose: () => {
      el.pause();
      el.removeAttribute('src');
      el.load();
      if (daRevocare) URL.revokeObjectURL(url);
      ['play', 'pause', 'stop', 'seekbackward', 'seekforward', 'seekto']
        .forEach((nome) => az(nome, null));
      navigator.mediaSession.metadata = null;
    },
  };
}
