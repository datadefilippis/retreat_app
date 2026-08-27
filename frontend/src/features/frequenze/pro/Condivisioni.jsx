/**
 * CondivisioniTraccia — il FOGLIO dei link riservati (TR4, 27/8;
 * rivisto dal founder il 27/8 sera: «il riquadro si allunga troppo»).
 *
 * Prima viveva DENTRO la scheda della traccia: ogni link creato la
 * allungava, e nella carta stretta i testi uscivano dal riquadro. Ora
 * e' un overlay (gate/gatebox, lo stesso vestito dei modali del
 * mondo): la scheda resta della sua misura e mostra solo il
 * conteggio; qui dentro la lista scorre, non cresce.
 *
 * Il processo che il foglio racconta: scegli un contatto dal CRM del
 * gestionale (ScegliPersona — la fonte e' UNA, la collezione
 * customers; NON serve un ordine, basta essere in rubrica) e se la
 * persona non c'e' la crei qui col nome e basta. Nasce IL SUO link,
 * lo copi o lo mandi su WhatsApp. La revoca e' chirurgica: quel
 * contatto smette subito, gli altri continuano. I contatori
 * (ascolti, ultimo accesso) sono il termometro: chi inoltra il link,
 * inoltra il proprio nome.
 */
import React, { useEffect, useState } from 'react';
import { frequenciesAPI } from '../../../api/frequencies';
import { messaggio } from './errori';
import ScegliPersona from './ScegliPersona';

const quando = (iso) => {
  if (!iso) return 'mai aperto';
  try {
    return new Date(iso).toLocaleDateString('it-IT',
      { day: 'numeric', month: 'short' });
  } catch { return ''; }
};

export default function CondivisioniTraccia({
  trackId, titolo = '', onCambio = null, onChiudi = null,
}) {
  const [items, setItems] = useState(null);   // null = caricamento
  const [persona, setPersona] = useState(null);
  const [msg, setMsg] = useState('');
  const [busy, setBusy] = useState(false);
  const [vediRevocati, setVediRevocati] = useState(false);

  const carica = () => {
    frequenciesAPI.listShares(trackId)
      .then((r) => setItems(r.data.items || []))
      .catch(() => setItems([]));
  };
  useEffect(carica, [trackId]);   // eslint-disable-line react-hooks/exhaustive-deps

  const linkDi = (token) => `${window.location.origin}/ascolta/${token}`;

  const copia = async (token) => {
    try {
      await navigator.clipboard.writeText(linkDi(token));
      setMsg('Link copiato: incollalo in un messaggio al tuo contatto.');
    } catch { setMsg(linkDi(token)); }
  };

  const crea = async () => {
    if (!persona || busy) return;
    setBusy(true); setMsg('');
    try {
      const r = await frequenciesAPI.createShare(trackId, persona.id);
      setPersona(null);
      carica();
      if (onCambio) onCambio();   // TM2: il conteggio in scheda resta vero
      await copia(r.data.token);
    } catch (e) {
      setMsg(messaggio(e, 'Non creato: riprova.'));
    } finally { setBusy(false); }
  };

  const revoca = async (share) => {
    try {
      await frequenciesAPI.revokeShare(share.id);
      carica();
      if (onCambio) onCambio();
      setMsg(`Link di ${share.contact_name || 'contatto'} revocato: non suona più.`);
    } catch { setMsg('Revoca non riuscita.'); }
  };

  const attivi = (items || []).filter((s) => s.stato === 'attivo');
  const revocati = (items || []).filter((s) => s.stato !== 'attivo');

  return (
    <div className="gate" onClick={onChiudi}>
      <div className="gatebox condivisioni-box"
        onClick={(e) => e.stopPropagation()}
        data-testid="fq-condivisioni">
        <button type="button" className="learnclose" title="Chiudi"
          onClick={onChiudi}>×</button>
        <h2>Link riservati{titolo ? <> — <em>{titolo}</em></> : null}</h2>
        <p className="cond-spiega">
          Un link personale per contatto, revocabile quando vuoi. I
          contatti sono quelli del tuo gestionale — non serve che
          abbiano ordini; se una persona non c’è ancora, creala qui
          col nome e basta.
        </p>
        <div className="cond-crea">
          <ScegliPersona valore={persona} onScegli={setPersona}
            placeholder="A chi vuoi mandarla?"
            testid="fq-share-persona" />
          <button type="button" className="add" disabled={!persona || busy}
            data-testid="fq-share-crea" onClick={crea}>
            {busy ? 'Creo…' : 'Crea link'}
          </button>
        </div>
        {msg && <p className="cond-msg" aria-live="polite">{msg}</p>}
        {items === null ? (
          <p className="vd-hint">Un momento…</p>
        ) : (
          <>
            {attivi.length === 0 && (
              <p className="vd-hint">
                Nessun link attivo: creane uno qui sopra.
              </p>
            )}
            <ul className="cond-lista">
              {attivi.map((sh) => (
                <li key={sh.id} data-testid="fq-share">
                  <div className="cond-chi">
                    <b>{sh.contact_name || 'Contatto'}</b>
                    <span>{`${sh.accessi || 0} ascolti · ${quando(sh.ultimo_accesso)}`}</span>
                  </div>
                  <div className="cond-gesti">
                    <button type="button" className="chip"
                      onClick={() => copia(sh.token)}>Copia</button>
                    <a className="chip" style={{ textDecoration: 'none' }}
                      href={`https://wa.me/?text=${encodeURIComponent(
                        'Un ascolto riservato per te: ' + linkDi(sh.token))}`}
                      target="_blank" rel="noreferrer">WhatsApp</a>
                    <button type="button" className="chip m"
                      data-testid="fq-share-revoca"
                      onClick={() => revoca(sh)}>Revoca</button>
                  </div>
                </li>
              ))}
            </ul>
            {revocati.length > 0 && (
              <>
                <button type="button" className="cond-revocati"
                  onClick={() => setVediRevocati((v) => !v)}>
                  {vediRevocati ? '▾' : '▸'} Revocati ({revocati.length})
                </button>
                {vediRevocati && (
                  <ul className="cond-lista spenti">
                    {revocati.map((sh) => (
                      <li key={sh.id}>
                        <div className="cond-chi">
                          <b>{sh.contact_name || 'Contatto'}</b>
                          <span>revocato</span>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}
