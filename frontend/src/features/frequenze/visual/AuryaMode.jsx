/**
 * Aurya Mode — la tela dentro una meditazione (AV1 → AV5, 22/8/2026).
 *
 * Regola che non cambia: la tela NON crea audio, non lo ferma, non lo
 * tocca. Riceve il lettore (analisi.js) e disegna.
 *
 * Cosa cambia con AV5: il motore non e' piu' una mia interpretazione
 * del concept, e' IL PROTOTIPO DEL FOUNDER — lo stesso file che regge
 * /sound/visual, montato «incorporato»: senza pannelli, con
 * l'analizzatore prestato dal grafo che sta suonando, e le forme
 * fissate sul preset Aurya con la palette multicolore. Due motori
 * diversi per la stessa cosa erano il motivo per cui la meditazione
 * non somigliava allo strumento; ora non possono divergere.
 *
 * - IMMERSIVO (prototipo + Three): lazy, entra in memoria solo quando
 *   qualcuno preme «Guarda»;
 * - SORGENTE (canvas 2D): la rete, dove WebGL manca o fallisce.
 *
 * Un tocco apre la scena a tutto schermo. Il fullscreen nativo su
 * iPhone non esiste per un elemento qualsiasi: la verita' e' una
 * classe CSS che funziona ovunque, e dove il nativo c'e' si aggiunge
 * sopra per far sparire anche le barre del browser.
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import * as sorgente from './temi/sorgente';
import { MARKUP_INCORPORATO } from './markupIncorporato';
import './incorporato.css';

export default function AuryaMode({ lettore, attivo = true,
                                    className = '', altezza = 380,
                                    visual = null, suMotore = null,
                                    alTocco = null }) {
  const boxRef = useRef(null);      // la cornice: e' lei che va a tutto schermo
  const telaRef = useRef(null);     // dove il prototipo (o il 2D) vive
  const rafRef = useRef(0);
  const [pieno, setPieno] = useState(false);
  const [quieta, setQuieta] = useState(false);

  /* ── il motore ────────────────────────────────────────────────── */
  useEffect(() => {
    const tela = telaRef.current;
    if (!tela || !lettore || !attivo) return undefined;
    let smontato = false;
    let manico = null;
    const quieto = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    const webgl2 = !quieto && !!document.createElement('canvas').getContext('webgl2');

    /* ── via immersiva: il prototipo, lazy (Three arriva solo qui) ── */
    if (webgl2) {
      tela.innerHTML = MARKUP_INCORPORATO;
      import('./prototipo').then(({ avviaPrototipo }) => {
        if (smontato) return;
        try {
          manico = avviaPrototipo(tela, {
            incorporato: true,
            analizzatore: lettore.analyser,
            sampleRate: lettore.analyser?.context?.sampleRate,
            /* VC1 — la scena dell'autore, risolta dallo score; senza,
               l'ambiente di default (AV5) */
            impostazioni: visual || undefined,
          });
          /* VC3 — Crea suona questo strumento con la sua tastiera */
          suMotore?.(manico);
        } catch {
          tela.innerHTML = '';       // WebGL c'e' ma non parte: si resta al buio
        }
      }).catch(() => {});
      return () => {
        smontato = true;
        suMotore?.(null);
        manico?.pulisci?.();
        tela.innerHTML = '';
      };
    }

    /* ── la rete: Sorgente 2D ── */
    const cv = document.createElement('canvas');
    cv.className = 'avze-2d';
    tela.appendChild(cv);
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const g = cv.getContext('2d', { alpha: false });
    let w = 0, h = 0;
    const misura = () => {
      const r = cv.getBoundingClientRect();
      w = Math.max(1, Math.round(r.width * dpr));
      h = Math.max(1, Math.round(r.height * dpr));
      if (cv.width !== w || cv.height !== h) { cv.width = w; cv.height = h; }
    };
    misura();
    const ro = new ResizeObserver(misura);
    ro.observe(cv);
    g.fillStyle = sorgente.COLORI.fondo;
    g.fillRect(0, 0, w, h);
    const t0 = performance.now();
    let vivo = true;
    const giro = () => {
      if (!vivo) return;
      const L = lettore.leggi();
      sorgente.disegna(g, L, (performance.now() - t0) / 1000, { w, h });
      rafRef.current = quieto
        ? window.setTimeout(() => requestAnimationFrame(giro), 66)
        : requestAnimationFrame(giro);
    };
    const visibilita = () => {
      if (document.visibilityState === 'visible' && vivo) giro();
    };
    document.addEventListener('visibilitychange', visibilita);
    giro();
    return () => {
      vivo = false;
      smontato = true;
      cancelAnimationFrame(rafRef.current);
      clearTimeout(rafRef.current);
      document.removeEventListener('visibilitychange', visibilita);
      ro.disconnect();
      tela.innerHTML = '';
    };
  }, [lettore, attivo]);

  /* ── a tutto schermo ──────────────────────────────────────────── */
  const commuta = useCallback(() => {
    /* VC6 — in Crea il tocco sulla forma apre lo studio (l'autore
       sceglie); per chi ascolta resta il tutto schermo, perche' la
       scena e' gia' stata scelta da chi l'ha composta */
    if (alTocco) { alTocco(); return; }
    const ora = !pieno;
    setPieno(ora);
    /* Il fullscreen nativo e' un di piu': la classe basta da sola. E
       fallisce piu' spesso di quanto sembri — dentro un iframe senza
       permesso, o quando il gesto non lo convince. Restituisce una
       PROMESSA: senza catch il rifiuto diventa un errore non gestito
       (visto dal vivo: «Permissions check failed»), e un try/catch
       intorno alla chiamata non lo prende. */
    const box = boxRef.current;
    try {
      if (ora) box?.requestFullscreen?.()?.catch(() => {});
      else if (document.fullscreenElement) document.exitFullscreen?.()?.catch(() => {});
    } catch { /* browser senza fullscreen: resta la classe */ }
  }, [pieno, alTocco]);

  /* Se l'utente esce dal fullscreen nativo (ESC, gesto del sistema) la
     cornice deve tornare nella pagina da sola, o resterebbe una tela
     fissa sopra tutto. L'evento arriva solo dove il nativo esiste —
     dove non esiste (iPhone) non c'e' niente da sincronizzare. */
  useEffect(() => {
    const sincro = () => { if (!document.fullscreenElement) setPieno(false); };
    document.addEventListener('fullscreenchange', sincro);
    return () => document.removeEventListener('fullscreenchange', sincro);
  }, []);

  useEffect(() => {
    if (!pieno) return undefined;
    const prima = document.body.style.overflow;
    document.body.style.overflow = 'hidden';   // niente pagina che scorre dietro
    const esci = (e) => { if (e.key === 'Escape') setPieno(false); };
    document.addEventListener('keydown', esci);
    return () => {
      document.body.style.overflow = prima;
      document.removeEventListener('keydown', esci);
    };
  }, [pieno]);

  /* l'invito si fa da parte dopo qualche secondo */
  useEffect(() => {
    setQuieta(false);
    const t = setTimeout(() => setQuieta(true), 4200);
    return () => clearTimeout(t);
  }, [pieno]);

  if (!attivo) return null;
  return (
    <div ref={boxRef}
      className={`avze${pieno ? ' pieno' : ''}${quieta ? ' quieta' : ''} ${className}`}
      data-testid="aurya-mode"
      style={pieno ? undefined : { height: altezza }}
      onClick={commuta}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); commuta(); } }}
      aria-label={alTocco ? 'Apri lo studio della scena'
        : pieno ? 'Chiudi lo schermo intero' : 'Guarda a tutto schermo'}>
      <div className="avze-tela" ref={telaRef} />
      <span className="avze-hint" data-testid="aurya-mode-pieno">
        {alTocco ? 'Tocca per scegliere forma e colori'
          : pieno ? 'Tocca per uscire' : 'Tocca per lo schermo intero'}
      </span>
    </div>
  );
}
