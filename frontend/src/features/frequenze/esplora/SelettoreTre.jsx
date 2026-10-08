/**
 * SelettoreTre — ES0: le tre porte del suono in UN selettore, lo stesso in
 * ogni pagina (Frequenze · Fondamenta · Lab). Sostituisce le «stanze» per
 * il pubblico; chi compone ha «Crea» in passerella.
 */
import React from 'react';
import { Link } from 'react-router-dom';

export const PORTE = [
  ['frequenze', 'Frequenze', '/sound/esplora'],
  ['fondamenta', 'Fondamenta', '/sound/impara'],
  ['lab', 'Lab', '/sound/lab'],
];

export default function SelettoreTre({ attiva }) {
  return (
    <nav className="sel-tre" aria-label="Il suono" data-testid="sel-tre">
      {PORTE.map(([id, label, to]) => (
        <Link key={id} to={to} className={`sel-tre-voce${attiva === id ? ' on' : ''}`} aria-current={attiva === id ? 'page' : undefined} data-testid={`sel-tre-${id}`}>{label}</Link>
      ))}
    </nav>
  );
}
