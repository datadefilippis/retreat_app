/**
 * StanzeSound — LA BARRA UNICA delle stanze (NV3, 27/8/2026).
 *
 * Il difetto che ripara (analisi BUSSOLA): le stanze del mondo Sound
 * vivevano su TRE barre — passerella (Lab), viewswitch (Esplora/Crea/
 * Impara), topbar (Le mie tracce) — e i pulsanti piu' critici per
 * l'operatore stavano in barre diverse. Da oggi la barra e' UNA,
 * condivisa da FrequenzePage e dal Lab: Esplora · Lab · Impara per
 * tutti, piu' Crea (col conteggio dei livelli) e Le mie tracce per
 * chi ha le chiavi. L'utente sa sempre dov'e' e dove puo' andare.
 *
 * Naviga per URL, mai per stato interno: FrequenzePage deriva gia' la
 * vista dall'URL (LN), e il Lab e' una pagina propria — un solo
 * meccanismo per entrambi. La chiave d'accesso e' la stessa cache
 * ottimista di FrequenzePage (aurya_sound_crea, riscritta a ogni
 * /auth/me): chi l'aveva ieri non vede la barra lampeggiare.
 */
import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

const STANZE = [
  ['esplora', 'Esplora', '/sound/esplora'],
  ['lab', 'Lab', '/sound/lab'],
  ['impara', 'Impara', '/sound/impara'],
];

export default function StanzeSound({ attiva, creaBadge = 0 }) {
  const navigate = useNavigate();
  const { user, loading: authLoading } = useAuth();
  const chiavi = user
    ? !!user.sound_crea
    : (!!authLoading && !!localStorage.getItem('token')
       && localStorage.getItem('aurya_sound_crea') === '1');

  const voci = chiavi
    ? [...STANZE,
       ['crea', 'Crea', '/sound/crea'],
       ['tracce', 'Le mie tracce', '/sound/tracce']]
    : STANZE;

  return (
    <div className="viewswitch" data-testid="stanze-sound">
      {voci.map(([id, label, to]) => (
        <button key={id} type="button"
          className={`vbtn${attiva === id ? ' on' : ''}`}
          data-testid={id === 'tracce' ? 'fqz-mine' : `stanza-${id}`}
          onClick={() => { if (attiva !== id) navigate(to); }}>
          {label}
          {id === 'crea' && creaBadge > 0 && (
            <span className="vcount">{creaBadge}</span>
          )}
        </button>
      ))}
    </div>
  );
}
