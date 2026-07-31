/**
 * HeroVideo — il tramonto di Aurya come sfondo, senza farlo pagare al
 * primo rendering (HP4, 31/7/2026).
 *
 * Nasce estraendo il pattern che viveva COPIATO in tre punti
 * (RetreatsCalendarPage, PrelaunchSplash e ora la home di rete):
 * poster sotto, video sopra, velo di leggibilita' a carico del
 * chiamante. Un posto solo per la strategia di caricamento, che e'
 * la parte delicata.
 *
 * ── SEQUENZA DI CARICAMENTO (il motivo per cui questo componente
 *    esiste; il founder ha chiesto esplicitamente che l'hero si
 *    dipinga subito) ─────────────────────────────────────────────
 *   1. Il POSTER e' un <img> vero, 47 KB, con fetchPriority="high" e
 *      NIENTE lazy: e' l'unica cosa che serve per vedere l'hero, ed e'
 *      anche il candidato LCP. Parte insieme all'HTML.
 *   2. Il <video> NON e' nel DOM al primo rendering. Viene montato
 *      dopo, quando la pagina ha finito di caricare (evento `load`,
 *      oppure subito se e' gia' avvenuto) e il browser ha un momento
 *      libero (requestIdleCallback, con un setTimeout di riserva dove
 *      non esiste). Cosi' 1,6 MB non contendono mai la banda a HTML,
 *      CSS, font e poster: nella scheda rete il video NON compare fra
 *      le richieste del primo rendering.
 *   3. Quando entra, entra con preload="auto" (a quel punto la banda
 *      e' libera) ma resta TRASPARENTE finche' non sta davvero
 *      giocando: la dissolvenza parte su `playing`, quindi non si vede
 *      mai un rettangolo nero al posto del poster.
 *
 * ── QUANDO IL VIDEO NON PARTE AFFATTO (resta il poster, fermo) ────
 *   - prefers-reduced-motion: reduce  → doppia guardia: qui non
 *     montiamo proprio l'elemento, e in index.css `.hero-video` resta
 *     display:none anche se qualcuno lo montasse comunque;
 *   - Save-Data attivo, oppure connessione dichiarata 2g/slow-2g:
 *     a chi paga il traffico non regaliamo 1,6 MB di decorazione.
 *     Il 3g passa (scelta founder): in Italia e' ancora comune su
 *     mobile, e il video arriva comunque ultimo senza bloccare nulla,
 *     quindi al massimo compare qualche secondo dopo;
 *   - autoplay rifiutato dal browser: il video resta a opacita' 0 e
 *     sotto c'e' gia' il poster, quindi non si nota nulla.
 *
 * ── ACCESSIBILITA' ───────────────────────────────────────────────
 * Il video e' DECORATIVO: aria-hidden, nessun controllo, nessun
 * audio, fuori dall'ordine di tabulazione. Il poster ha alt="" per
 * la stessa ragione. Il velo di contrasto NON sta qui: lo mette la
 * pagina, perche' dipende da dove cade il testo.
 */
import React, { useEffect, useRef, useState } from 'react';

/* Il tetto d'attesa dopo `load`. requestIdleCallback fa entrare il
   video appena il thread e' libero, ma NON e' garantito che scatti:
   dove non esiste (Safari) e nelle schede in secondo piano puo' non
   arrivare mai, e l'opzione `timeout` non basta perche' Chrome non
   apre periodi di inattivita' su una pagina che non sta disegnando.
   Misurato qui: in scheda nascosta il callback non e' arrivato dopo
   100 secondi. Quindi i due si CORRONO: vince chi arriva prima. */
const FALLBACK_DELAY = 600;

/** Il video si puo' caricare? Deciso una volta sola, al montaggio. */
function videoAllowed() {
  if (typeof window === 'undefined') return false;
  try {
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return false;
  } catch { /* matchMedia assente: si prosegue */ }
  const conn = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
  if (conn) {
    if (conn.saveData) return false;
    if (['slow-2g', '2g'].includes(conn.effectiveType)) return false;
  }
  return true;
}

export default function HeroVideo({
  src,
  poster,
  /** classi aggiuntive sui DUE strati (es. object-position) */
  className = '',
}) {
  const [mounted, setMounted] = useState(false);
  const [playing, setPlaying] = useState(false);
  const videoRef = useRef(null);

  useEffect(() => {
    if (!videoAllowed()) return undefined;

    let cancelled = false;
    let idleId = null;
    let timerId = null;

    const go = () => { if (!cancelled) setMounted(true); };

    const arm = () => {
      if (cancelled) return;
      if (typeof window.requestIdleCallback === 'function') {
        idleId = window.requestIdleCallback(go, { timeout: 2000 });
      }
      timerId = setTimeout(go, FALLBACK_DELAY);
    };

    if (document.readyState === 'complete') arm();
    else window.addEventListener('load', arm, { once: true });

    return () => {
      cancelled = true;
      window.removeEventListener('load', arm);
      if (idleId != null && typeof window.cancelIdleCallback === 'function') {
        window.cancelIdleCallback(idleId);
      }
      if (timerId != null) clearTimeout(timerId);
    };
  }, []);

  /* autoPlay basta quasi sempre (muted + playsInline), ma su alcuni
     browser un elemento montato DOPO il caricamento non riparte da
     solo: la spinta esplicita costa nulla e l'errore si ignora. */
  useEffect(() => {
    if (!mounted) return;
    const v = videoRef.current;
    if (v?.play) { const p = v.play(); if (p?.catch) p.catch(() => {}); }
  }, [mounted]);

  return (
    <>
      {/* il primo dipinto: nessun lazy, priorita' alta, sempre sotto */}
      <img
        src={poster}
        alt=""
        aria-hidden="true"
        fetchPriority="high"
        decoding="async"
        className={`absolute inset-0 h-full w-full object-cover ${className}`}
      />
      {mounted && (
        <video
          ref={videoRef}
          aria-hidden="true"
          tabIndex={-1}
          src={src}
          poster={poster}
          autoPlay
          muted
          loop
          playsInline
          preload="auto"
          onPlaying={() => setPlaying(true)}
          className={`hero-video absolute inset-0 h-full w-full object-cover
                      transition-opacity duration-700 ease-out
                      ${playing ? 'opacity-100' : 'opacity-0'} ${className}`}
        />
      )}
    </>
  );
}
