/**
 * Il sipario delle controindicazioni (SF, 20/8/2026) — e il pulsante
 * che lo riapre quando si vuole.
 *
 * Due modi, stesso testo (content/safety.js):
 *   gate    — si apre prima del primo suono. Per proseguire bisogna
 *             dire «ho letto»: accettando, il suono che l'utente aveva
 *             chiesto parte subito (il clic sul bottone è anche il
 *             gesto che l'audio del browser richiede, quindi non serve
 *             premere due volte).
 *   review  — aperto dal pulsante «Controindicazioni»: si legge e si
 *             chiude, e NON sposta in avanti la scadenza dei 90 giorni.
 *             Rileggere non è accettare di nuovo.
 *
 * useSafetyGate() dà alle pagine un solo modo di proteggere un ascolto:
 *   const { guard, curtain, openReview } = useSafetyGate();
 *   <button onClick={guard(play)}>Ascolta</button>
 *   {curtain}
 */
import React, { useCallback, useState } from 'react';
import {
  SAFETY_INTRO, SAFETY_LINE, SAFETY_POINTS, SAFETY_TITLE, SAFETY_WARN,
  acceptSafety, safetyAccepted,
} from './content/safety';

export function SafetyCurtain({ mode, onAccept, onClose }) {
  const review = mode === 'review';
  return (
    <div className="gate" data-testid="fqz-safety" data-mode={mode}
      onClick={review ? onClose : undefined}>
      <div className="gatebox" onClick={(e) => e.stopPropagation()}>
        <h2>{SAFETY_TITLE}</h2>
        <p>{SAFETY_INTRO}</p>
        <div className="warnbox">{SAFETY_WARN}</div>
        <ul>
          {SAFETY_POINTS.map(([t, p]) => (
            <li key={t}><strong>{t}</strong> {p}</li>
          ))}
        </ul>
        <div className="gatefoot">
          {review ? (
            <button type="button" className="primary" onClick={onClose}>Chiudi</button>
          ) : (
            <button type="button" className="primary" data-testid="fqz-safety-ok"
              onClick={onAccept}>Ho letto e compreso</button>
          )}
        </div>
      </div>
    </div>
  );
}

/** Il pulsante sempre a vista: apre le controindicazioni in lettura. */
export function SafetyButton({ onClick, className = 'safetybtn' }) {
  return (
    <button type="button" className={className} data-testid="fqz-safety-btn"
      title="Leggi le controindicazioni di Aurya Sound"
      onClick={onClick}>⚠ Controindicazioni</button>
  );
}

/** La riga corta che sta accanto a chi sta per ascoltare. */
export function SafetyLine({ onOpen }) {
  return (
    <div className="safetyline" data-testid="fqz-safety-line">
      <span>{SAFETY_LINE}</span>
      {/* Solo su telefono: 27 schede su 32 suonano sotto i 500 Hz, e
          l'altoparlante di un telefono non scende li'. Chi prova senza
          cuffie sente silenzio e pensa a un guasto. Una riga, dove
          serve. */}
      <span className="solo-telefono" data-testid="fqz-nota-altoparlante">
        Senza cuffie i toni gravi non escono dall’altoparlante del telefono.
      </span>
      <button type="button" onClick={onOpen}>Cosa devo sapere</button>
    </div>
  );
}

export function useSafetyGate() {
  const [pending, setPending] = useState(null);   // azione in attesa
  const [review, setReview] = useState(false);

  /* Avvolge un'azione che produce suono: se l'avviso è già stato
     accettato (versione corrente, meno di 90 giorni) parte subito;
     altrimenti si apre il sipario e l'azione aspetta lì. */
  const guard = useCallback((fn) => (...args) => {
    if (safetyAccepted()) return fn(...args);
    setPending(() => () => fn(...args));
    return undefined;
  }, []);

  const accept = useCallback(() => {
    acceptSafety();
    const run = pending;
    setPending(null);
    if (run) run();
  }, [pending]);

  const curtain = pending ? (
    <SafetyCurtain mode="gate" onAccept={accept} />
  ) : review ? (
    <SafetyCurtain mode="review" onClose={() => setReview(false)} />
  ) : null;

  return {
    guard,
    curtain,
    openReview: () => setReview(true),
  };
}
