/**
 * IL KIT DELLE LANDING DI SOUND (26/8/2026 sera).
 *
 * Pezzi condivisi dalle due pagine di presentazione (/sound e
 * /sound/professional), nati da tre richieste del founder: testi PIÙ
 * GRANDI (la scala del sito, non un corpo minuto), più CONTRASTO fra
 * le sezioni, e l'ORO di marca dove non sporca — occhielli, filetti,
 * numeri, e i richiami sulle bande scure.
 *
 * L'ORO È #c9b37e, quello editoriale del sito. Regola: mai su fondo
 * chiaro come testo di lettura (non tiene il contrasto), sempre come
 * ACCENTO — un occhiello, un numerale, un filo, un bordo.
 */
import React from 'react';
import { Link } from 'react-router-dom';

export const ORO = '#c9b37e';
export const VERDE = '#2f5749';

/** Il corpo del testo: la misura del sito, non un corpo minuto. */
export function Testo({ children, className = '', tono = 'scuro' }) {
  const colore = tono === 'chiaro' ? 'text-white/85' : 'text-muted-foreground';
  return (
    <p className={`text-base sm:text-lg leading-relaxed ${colore} ${className}`}>
      {children}
    </p>
  );
}

/** La frase che porta il peso: serif, grande, senza virgolette. */
export function Rilievo({ children, className = '', tono = 'scuro' }) {
  const colore = tono === 'chiaro' ? 'text-white' : '';
  return (
    <p className={`font-serif text-2xl sm:text-3xl leading-snug ${colore} ${className}`}>
      {children}
    </p>
  );
}

/** L'occhiello: piccolo, spaziato, ORO. */
export function Occhiello({ children, className = '', tono = 'scuro' }) {
  return (
    <p className={`text-[11px] sm:text-xs tracking-[0.24em] uppercase mb-5 ${className}`}
      style={{ color: tono === 'chiaro' ? '#e0cfa4' : ORO }}>
      {children}
    </p>
  );
}

/** Le righe che il testo del founder vuole staccate, una per volta. */
export function Righe({ voci, className = '', tono = 'scuro' }) {
  return (
    <div className={`space-y-4 ${className}`}>
      {voci.map((v) => <Testo key={v} tono={tono}>{v}</Testo>)}
    </div>
  );
}

/** Il richiamo pieno: oro su scuro, verde su chiaro. */
export function Bottone({ to, href, children, tono = 'scuro', testid }) {
  const oro = tono === 'chiaro';
  const stile = oro
    ? { background: ORO, color: '#14212b' }
    : { background: VERDE, color: '#f6f2e8' };
  const cls = 'inline-flex items-center gap-2 rounded-full px-7 py-3.5 '
    + 'text-sm sm:text-base font-medium transition hover:opacity-90';
  if (href) {
    return <a href={href} className={cls} style={stile} data-testid={testid}>{children}</a>;
  }
  return <Link to={to} className={cls} style={stile} data-testid={testid}>{children}</Link>;
}

/** Il richiamo leggero: solo testo e filo. */
export function Richiamo({ to, children, tono = 'scuro', testid }) {
  return (
    <Link to={to} data-testid={testid}
      className={`inline-flex items-center gap-2 text-sm sm:text-base border-b pb-1 transition
        ${tono === 'chiaro'
          ? 'text-white/90 border-white/40 hover:border-white'
          : 'text-foreground border-[#c9b37e] hover:border-foreground'}`}>
      {children}
    </Link>
  );
}

/** Una scheda con l'oro sul bordo alto: il contrasto che mancava. */
export function Scheda({ occhiello, titolo, children, footer, testid,
  accento = ORO }) {
  return (
    <article data-testid={testid}
      className="relative rounded-2xl bg-white p-8 flex flex-col
                 shadow-[0_1px_0_rgba(0,0,0,0.04)] border border-[#e8e0ce]">
      <span aria-hidden className="absolute left-8 right-8 top-0 h-[3px] rounded-b"
        style={{ background: accento }} />
      {occhiello && <Occhiello className="mt-2">{occhiello}</Occhiello>}
      <h3 className="font-serif text-2xl sm:text-3xl mb-4">{titolo}</h3>
      <div className="space-y-3 flex-1 text-base leading-relaxed text-muted-foreground">
        {children}
      </div>
      {footer && <div className="mt-7">{footer}</div>}
    </article>
  );
}
