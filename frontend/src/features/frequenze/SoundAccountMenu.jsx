/**
 * SoundAccountMenu — l'omino nel buio (DN2, 21/8/2026, founder).
 *
 * Le VOCI sono quelle del menu del sito, prese da lib/cappelli: stesso
 * modello, stessa logica dei due cappelli. Cambia solo la pelle —
 * .fqz invece di Tailwind/Radix — perche' portare qui i componenti del
 * mondo chiaro significherebbe portarci dentro il suo tema.
 *
 * Prima di questo, chi era loggato entrava in Sound e smetteva di
 * vedersi: nessun «chi sono», nessun account, nessun «Esci».
 */
import React from 'react';
import { cappelliAddosso, vociAccount, indossaCappelloCliente, esci } from '../../lib/cappelli';

export default function SoundAccountMenu({ tornaA = '/' }) {
  const [aperto, setAperto] = React.useState(false);
  const [errore, setErrore] = React.useState('');
  const box = React.useRef(null);
  const cappelli = cappelliAddosso();
  const { tue, professionisti } = vociAccount(cappelli);

  // clic fuori ed Esc chiudono, come nel menu del sito
  React.useEffect(() => {
    if (!aperto) return undefined;
    const fuori = (e) => { if (box.current && !box.current.contains(e.target)) setAperto(false); };
    const esc = (e) => { if (e.key === 'Escape') setAperto(false); };
    document.addEventListener('mousedown', fuori);
    document.addEventListener('keydown', esc);
    return () => {
      document.removeEventListener('mousedown', fuori);
      document.removeEventListener('keydown', esc);
    };
  }, [aperto]);

  const voce = (v) => (v.action === 'addClientHat' ? (
    <button type="button" key={v.testid} className="sam-voce" data-testid={v.testid}
      onClick={() => indossaCappelloCliente(setErrore)}>
      {v.label}
    </button>
  ) : (
    <a key={v.testid} className="sam-voce" href={v.to} data-testid={v.testid}>{v.label}</a>
  ));

  return (
    <div className="sam" ref={box}>
      <button type="button" className="sam-trigger" data-testid="sound-account-trigger"
        aria-label="Il tuo account" title="Il tuo account"
        aria-expanded={aperto} onClick={() => setAperto((v) => !v)}>
        <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor"
          strokeWidth="1.6" aria-hidden>
          <circle cx="12" cy="12" r="9.5" />
          <circle cx="12" cy="10" r="3.2" />
          <path d="M5.6 19a7 7 0 0 1 12.8 0" />
        </svg>
        {cappelli.dentro && <span className="sam-dot" aria-hidden />}
      </button>

      {aperto && (
        <div className="sam-menu" role="menu" data-testid="sound-account-menu">
          <div className="sam-tit">Il tuo account Aurya</div>
          {tue.map(voce)}
          <div className="sam-sep" />
          <div className="sam-tit">Per i professionisti del benessere</div>
          {professionisti.map(voce)}
          {cappelli.dentro && (
            <>
              <div className="sam-sep" />
              <button type="button" className="sam-voce" data-testid="sound-account-logout"
                onClick={() => esci(tornaA)}>
                Esci
              </button>
            </>
          )}
          {errore && <div className="sam-err">{errore}</div>}
        </div>
      )}
    </div>
  );
}
