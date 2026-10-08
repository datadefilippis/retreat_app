/**
 * PiuAccount — la sezione «Aurya Più» dentro /account (SN4, 8/10/2026).
 * Lo stato dal server (`attivo`, `abbonato`, scadenza), «Gestisci» apre il
 * portale Stripe (carta, fatture, disdetta), «Entra nel Più» il checkout.
 * Finché il Più è spento e l'account non ha nulla, non si vede.
 */
import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { soundPiuAPI } from '../../../api/soundPiu';
import { PIU_PREZZO } from '../stato';

const data = (v) => { try { return v ? new Date(v).toLocaleDateString('it-IT', { day: 'numeric', month: 'long', year: 'numeric' }) : ''; } catch { return ''; } };

export default function PiuAccount() {
  const [stato, setStato] = useState(null);
  const [msg, setMsg] = useState('');
  const appena = /[?&]piu=ok/.test(window.location.search);
  useEffect(() => { soundPiuAPI.stato().then((r) => setStato(r.data)).catch(() => setStato(null)); }, []);
  if (!stato || (!stato.attivo && !stato.status && !stato.omaggio_until)) return null;
  const apri = async (fn) => {
    setMsg('');
    try { const r = await fn(); if (r.data?.url) window.location.href = r.data.url; }
    catch (err) { setMsg(err?.response?.data?.detail || 'Non riesco ad aprire Stripe: riprova.'); }
  };
  return (
    <section id="piu" className="scroll-mt-24 mt-6 rounded-2xl border border-[#e6dcc3] bg-[#faf6ec] p-5" data-testid="account-piu">
      <h2 className="text-sm font-semibold text-gray-900 mb-1">Aurya Più</h2>
      {appena && <p className="text-sm text-[#2f5749] mb-2" data-testid="account-piu-benvenuto">Sei nel Più: grazie. Le meditazioni riservate sono tue da adesso.</p>}
      {stato.abbonato ? (
        <p className="text-sm text-gray-700">
          Abbonamento attivo{stato.current_period_end ? ` fino al ${data(stato.current_period_end)}` : ''}
          {stato.cancel_at_period_end ? ' · non si rinnova' : stato.status === 'past_due' ? ' · pagamento da sistemare' : ''}.
        </p>
      ) : stato.status ? (
        <p className="text-sm text-gray-700">Abbonamento chiuso{stato.current_period_end ? ` il ${data(stato.current_period_end)}` : ''}.</p>
      ) : (
        <p className="text-sm text-gray-700">Le meditazioni riservate, {PIU_PREZZO}, solo annuale. Il Cerchio resta gratuito.</p>
      )}
      <div className="mt-3 flex flex-wrap gap-2">
        {stato.attivo && stato.ha_cliente_stripe && (
          <button type="button" className="rounded-full border border-[#2f5749] px-4 py-2 text-sm font-semibold text-[#2f5749]" onClick={() => apri(soundPiuAPI.portale)} data-testid="account-piu-portale">Gestisci</button>
        )}
        {stato.attivo && !stato.abbonato && (
          <button type="button" className="rounded-full bg-[#2f5749] px-4 py-2 text-sm font-semibold text-white" onClick={() => apri(() => soundPiuAPI.checkout('/account#meditazioni'))} data-testid="account-piu-entra">Entra nel Più</button>
        )}
        <Link to="/meditazioni" className="text-sm text-[#2f5749] underline self-center">Le meditazioni</Link>
      </div>
      {msg && <p className="mt-2 text-sm text-[#a03434]">{msg}</p>}
    </section>
  );
}
