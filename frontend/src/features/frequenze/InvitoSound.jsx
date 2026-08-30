/**
 * L'INVITO DEL MONDO SOUND (FA8, piano FARO, 30/8/2026).
 *
 * Il componente UNICO dei trigger email nel mondo gratuito: una riga
 * col form, mai un cancello (qui il materiale e' gratis e resta
 * gratis — l'invito offre di piu', non toglie). Ogni montaggio porta
 * la sua FONTE (sound:esplora:{slug}, sound:lab:{stanza}...) per il
 * targeting in admin (FA5).
 *
 * LA REGOLA DEL SILENZIO (contratto FARO, con guardia): il controllo
 * sta PRIMA del render — chi ha gia' la prova della Lettera o un
 * account Aurya non vede nulla. Mai due inviti nella stessa
 * schermata: chi monta InvitoSound non monta altro.
 */
import React, { useState } from 'react';
import { prova, iscriviESblocca } from '../../lib/cerchio';
import { PLATFORM_TOKEN_KEY } from '../../api/platformClient';

const servito = () => {
  try {
    return !!prova() || !!localStorage.getItem(PLATFORM_TOKEN_KEY)
      || !!localStorage.getItem('token');
  } catch { return false; }
};

export default function InvitoSound({ fonte, dove = '/sound', variante = 'scuro' }) {
  const [email, setEmail] = useState('');
  const [consent, setConsent] = useState(false);
  const [invio, setInvio] = useState(false);
  const [stato, setStato] = useState('');   // '' | 'attesa' | 'dentro' | errore

  if (servito()) return null;               // la regola del silenzio

  const iscrivi = async (e) => {
    e.preventDefault();
    if (!consent) { setStato('Serve il consenso alla newsletter'); return; }
    setInvio(true); setStato('');
    try {
      const esito = await iscriviESblocca({
        email, source: fonte || 'sound', returnTo: dove,
      });
      setStato(esito === 'sbloccato' ? 'dentro' : 'attesa');
    } catch (err) {
      setStato(err?.response?.data?.detail || 'Iscrizione non riuscita, riprova');
    } finally { setInvio(false); }
  };

  const chiaro = variante === 'chiaro';
  if (stato === 'dentro' || stato === 'attesa') {
    return (
      <p className={chiaro ? 'text-sm text-muted-foreground' : 'fqz-invito-sound'}
        data-testid="invito-sound-grazie">
        {stato === 'dentro'
          ? 'Sei dentro: la Lettera ti raggiunge alla prossima uscita.'
          : 'Ti abbiamo scritto: conferma dall’email che ti arriva e sei dentro.'}
      </p>
    );
  }

  return (
    <div className={chiaro ? 'mt-6' : 'fqz-invito-sound'}
      data-testid="invito-sound">
      <p className={chiaro ? 'text-sm text-muted-foreground mb-2' : undefined}>
        Vuoi ricevere nuovi contenuti come questo? Lascia la tua
        email: ti avvisiamo quando pubblichiamo nuove guide sul suono
        e nuove meditazioni da ascoltare. È gratis, una email ogni
        tanto, e ti disiscrivi quando vuoi.
      </p>
      <form onSubmit={iscrivi}>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <input type="email" required value={email}
            placeholder="la tua email"
            onChange={(e) => setEmail(e.target.value)}
            style={{ flex: 1, minWidth: 180 }} />
          <button type="submit" className="primary" disabled={invio}
            data-testid="invito-sound-iscriviti">
            {invio ? 'Un attimo…' : 'Iscrivimi'}
          </button>
        </div>
        <label style={{ display: 'flex', gap: 8, alignItems: 'flex-start',
                        fontSize: 12, marginTop: 8, cursor: 'pointer' }}>
          <input type="checkbox" checked={consent}
            onChange={(e) => setConsent(e.target.checked)} />
          <span>Acconsento a ricevere la newsletter; disiscrizione in
            un click. <a href="/privacy" target="_blank" rel="noreferrer">Privacy</a></span>
        </label>
      </form>
      {stato && stato !== 'attesa' && stato !== 'dentro' && (
        <p style={{ fontSize: 12, marginTop: 6 }} className="fqz-invito-errore">{stato}</p>
      )}
    </div>
  );
}
