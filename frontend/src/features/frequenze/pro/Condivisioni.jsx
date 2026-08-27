/**
 * CondivisioniTraccia — il pannello dei LINK RISERVATI (TR4, 27/8).
 *
 * Vive dentro la scheda di una traccia pubblicata come riservata, in
 * «Le mie tracce»: scegli un contatto dal CRM (ScegliPersona, lo
 * stesso del rito), nasce IL SUO link, lo copi o lo mandi. La revoca
 * e' chirurgica: quel contatto smette subito, gli altri continuano.
 *
 * I contatori (ascolti, ultimo accesso) sono il termometro
 * dell'operatore: chi inoltra il link, inoltra il proprio nome.
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

export default function CondivisioniTraccia({ trackId, onCambio = null }) {
  const [items, setItems] = useState(null);   // null = caricamento
  const [persona, setPersona] = useState(null);
  const [msg, setMsg] = useState('');
  const [busy, setBusy] = useState(false);

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

  return (
    <div className="livectl" style={{ display: 'flex' }}
      data-testid="fq-condivisioni">
      <div className="lbl" style={{ border: 'none', cursor: 'default' }}>
        Link riservati — uno per contatto, revocabile
      </div>
      {items === null ? (
        <span className="vd-hint">Un momento…</span>
      ) : (
        <>
          {items.map((sh) => (
            <div key={sh.id} className="vd-clip"
              style={sh.stato === 'revocato' ? { opacity: 0.5 } : undefined}
              data-testid="fq-share">
              <span className="vd-name" style={{ border: 'none' }}>
                {sh.contact_name || 'Contatto'}
              </span>
              <span className="vd-dur">
                {sh.stato === 'revocato' ? 'revocato'
                  : `${sh.accessi || 0} ascolti · ${quando(sh.ultimo_accesso)}`}
              </span>
              {sh.stato === 'attivo' && (
                <>
                  <button type="button" className="chip"
                    onClick={() => copia(sh.token)}>Copia link</button>
                  <a className="chip" style={{ textDecoration: 'none' }}
                    href={`https://wa.me/?text=${encodeURIComponent(
                      'Un ascolto riservato per te: ' + linkDi(sh.token))}`}
                    target="_blank" rel="noreferrer">WhatsApp</a>
                  <button type="button" className="chip m"
                    data-testid="fq-share-revoca"
                    onClick={() => revoca(sh)}>Revoca</button>
                </>
              )}
            </div>
          ))}
          <div className="vd-tryrow">
            <ScegliPersona valore={persona} onScegli={setPersona}
              placeholder="A chi vuoi mandarla?"
              testid="fq-share-persona" />
            <button type="button" className="add" disabled={!persona || busy}
              data-testid="fq-share-crea" onClick={crea}>
              {busy ? 'Creo…' : 'Crea link'}
            </button>
          </div>
        </>
      )}
      {msg && <span className="vd-hint" style={{ opacity: 1 }}>{msg}</span>}
    </div>
  );
}
