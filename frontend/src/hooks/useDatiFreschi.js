import { useEffect, useRef } from 'react';

/**
 * DF1 (16/9/2026, segnalazione founder) — «l'operatore non deve uscire e
 * rientrare per vedere cosa gli e' entrato». Le pagine del gestionale
 * caricano i dati UNA volta, al montaggio: una scheda lasciata aperta sul
 * telefono e riaperta due giorni dopo mostra la schermata di due giorni
 * prima finche' non si naviga. Questo hook rilancia il caricamento
 * quando la scheda torna visibile (o riprende il fuoco) dopo essere stata
 * nascosta per almeno `minNascostaMs` — l'operatore era via, una ricarica
 * e' quello che si aspetta — e, solo se richiesto, ogni `ogniMs` finche' la
 * scheda e' visibile (per i contatori leggeri, mai per liste con moduli).
 *
 * Non tocca la logica di caricamento delle pagine: chiama la loro `load`
 * cosi' com'e'. Niente ricariche mentre l'operatore sta lavorando: il
 * ritorno scatta solo dopo un'assenza vera, l'intervallo si ferma quando la
 * scheda e' nascosta.
 */
export default function useDatiFreschi(load, { minNascostaMs = 60000, ogniMs = 0, attivo = true } = {}) {
  const loadRef = useRef(load);
  loadRef.current = load;
  const nascostaDaRef = useRef(null);

  useEffect(() => {
    if (!attivo || typeof document === 'undefined') return undefined;

    const ricarica = () => {
      try { const r = loadRef.current?.(); if (r && typeof r.catch === 'function') r.catch(() => {}); } catch { /* la pagina gestisce i suoi errori */ }
    };
    const alRitorno = () => {
      const da = nascostaDaRef.current;
      nascostaDaRef.current = null;
      if (da && Date.now() - da >= minNascostaMs) ricarica();
    };
    const onVisibility = () => {
      if (document.visibilityState === 'hidden') {
        if (!nascostaDaRef.current) nascostaDaRef.current = Date.now();
      } else {
        alRitorno();
      }
    };
    // `focus` copre i browser che non emettono visibilitychange al
    // rientro da un'altra finestra: conta solo se prima c'era stato un blur
    const onBlur = () => { if (!nascostaDaRef.current) nascostaDaRef.current = Date.now(); };
    const onFocus = () => { if (document.visibilityState !== 'hidden') alRitorno(); };

    document.addEventListener('visibilitychange', onVisibility);
    window.addEventListener('blur', onBlur);
    window.addEventListener('focus', onFocus);

    let timer = null;
    if (ogniMs > 0) {
      timer = setInterval(() => {
        if (document.visibilityState === 'visible') ricarica();
      }, ogniMs);
    }
    return () => {
      document.removeEventListener('visibilitychange', onVisibility);
      window.removeEventListener('blur', onBlur);
      window.removeEventListener('focus', onFocus);
      if (timer) clearInterval(timer);
    };
  }, [attivo, minNascostaMs, ogniMs]);
}
