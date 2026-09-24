/**
 * GrazieCerchio — «Entra nel Cerchio di Aurya» dopo l'acquisto (E4,
 * Lotto E del 24/9/2026, docs/PIANO_ESECUZIONE_ADMIN_CERCHIO_2026-09-24.md).
 *
 * Il cliente ha comprato dall'OPERATORE: il Cerchio e' marketing di un
 * altro titolare, quindi qui c'e' una casella sua (mai preselezionata)
 * col testo unico e versionato, e un bottone. Passa da lib/cerchio.js
 * (iscriviESblocca: consenso, versione, provenienza, prova nel browser)
 * con fonte «pagina-grazie».
 *
 * Non si mostra a chi ha gia' spuntato la casella del Cerchio al
 * checkout (sessionStorage 'storefront:cerchio_optin' = '1': il redirect
 * Stripe e' un full reload, lo state di router non sopravvive).
 */
import React, { useState } from 'react';
import { iscriviESblocca } from '../../../../lib/cerchio';
import { testoConsenso } from '../../../../lib/testiConsenso';

function giaSpuntatoAlCheckout() {
  try { return sessionStorage.getItem('storefront:cerchio_optin') === '1'; } catch { return false; }
}

function emailDalCheckout() {
  try { return sessionStorage.getItem('storefront:mktp_email') || ''; } catch { return ''; }
}

export default function GrazieCerchio({ email: emailProp, source = 'pagina-grazie', className = '' }) {
  const [nascosto] = useState(giaSpuntatoAlCheckout);
  const [email, setEmail] = useState(() => emailProp || emailDalCheckout());
  const [consenso, setConsenso] = useState(false);   // mai preselezionata
  const [stato, setStato] = useState('idle');        // idle | sending | done | error
  if (nascosto || stato === 'done') {
    return stato === 'done' ? (
      <p className={`text-sm text-gray-700 ${className}`} data-testid="grazie-cerchio-done">
        Fatto: sei nel Cerchio di Aurya. Controlla l'email, la prima Lettera sta arrivando.
      </p>
    ) : null;
  }
  const invia = async () => {
    if (!consenso || !email.trim()) return;
    setStato('sending');
    try {
      await iscriviESblocca({ email: email.trim(), source, language: 'it' });
      setStato('done');
    } catch {
      setStato('error');
    }
  };
  return (
    <div className={`rounded-xl border border-primary/25 bg-primary/5 p-4 text-left space-y-2 ${className}`}
         data-testid="grazie-cerchio">
      <p className="text-sm font-semibold text-gray-900">Entra nel Cerchio di Aurya</p>
      {!emailProp && (
        <input
          type="email" value={email} onChange={e => setEmail(e.target.value)}
          placeholder="La tua email" autoComplete="email"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
        />
      )}
      <label className="flex items-start gap-2 cursor-pointer select-none">
        <input
          type="checkbox" checked={consenso}
          onChange={e => setConsenso(e.target.checked)}
          data-testid="grazie-cerchio-consenso"
          className="mt-0.5 shrink-0 h-4 w-4 rounded border-gray-300 text-gray-900 focus:ring-gray-900"
        />
        <span className="text-sm text-gray-600">
          {testoConsenso().testo}{' '}
          <a href="/privacy" target="_blank" rel="noopener noreferrer" className="underline text-blue-700 hover:no-underline">Privacy</a>
        </span>
      </label>
      <button type="button" onClick={invia} disabled={!consenso || !email.trim() || stato === 'sending'}
              data-testid="grazie-cerchio-invia"
              className="block w-full rounded-full bg-primary text-white px-5 py-2.5 text-sm font-bold hover:opacity-90 disabled:opacity-50">
        {stato === 'sending' ? 'Un attimo…' : 'Entro nel Cerchio'}
      </button>
      {stato === 'error' && (
        <p className="text-xs text-red-700">Non riusciamo a iscriverti ora, riprova tra poco.</p>
      )}
    </div>
  );
}
