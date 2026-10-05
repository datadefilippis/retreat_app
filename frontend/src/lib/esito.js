/**
 * FL1 (5/10/2026 sera, founder: «dopo l'iscrizione la pagina si sposta e
 * la persona non vede la conferma») — UN solo modo di mostrare il risultato
 * di un gesto: il box di successo si porta al centro dello schermo e
 * prende il focus (lo legge anche chi usa uno screen reader: role=status).
 *
 * `<Esito>` sostituisce il contenitore del box di successo: al montaggio
 * (cioè nell'istante in cui il form diventa «fatto») chiama mostraEsito.
 * Non tocca nessuna logica: solo dove si guarda.
 *
 * Regole: rispetta prefers-reduced-motion (scorrimento secco), non scorre
 * se il box è già tutto visibile, il focus non riscorre (preventScroll).
 */
import React, { useEffect, useRef } from 'react';

export function mostraEsito(el) {
  if (!el || typeof window === 'undefined') return false;
  let riduci = false;
  try { riduci = !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches); } catch { /* */ }
  let visibile = false;
  try {
    const r = el.getBoundingClientRect();
    const h = window.innerHeight || document.documentElement.clientHeight || 0;
    visibile = r.top >= 0 && r.bottom <= h;
  } catch { /* */ }
  if (!visibile) {
    try { el.scrollIntoView({ block: 'center', behavior: riduci ? 'auto' : 'smooth' }); }
    catch { try { el.scrollIntoView(); } catch { /* */ } }
  }
  try { el.focus({ preventScroll: true }); } catch { /* */ }
  return true;
}

/** Il box di successo: stesso markup di prima, in più ref + focus + ruolo. */
export function Esito({ as: Tag = 'div', children, className = '', ritardo = 60, ...resto }) {
  const ref = useRef(null);
  // una volta sola, al montaggio: e' l'istante in cui il form diventa «fatto»
  useEffect(() => {
    const t = setTimeout(() => mostraEsito(ref.current), ritardo);
    return () => clearTimeout(t);
  }, [ritardo]);
  return (
    <Tag ref={ref} tabIndex={-1} role="status" className={`outline-none ${className}`.trim()} {...resto}>
      {children}
    </Tag>
  );
}

export default Esito;
