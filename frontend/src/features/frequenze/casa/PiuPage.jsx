/**
 * PiuPage — AURYA PIÙ, la pagina (SN4, 8/10/2026, piano §5).
 * /meditazioni/piu: cosa c'è nel Più, il prezzo (annuale, solo annuale),
 * «Abbonati» (Stripe Checkout) o «Gestisci» (portale). Finché il Più è
 * spento rimanda alla casa: la pagina esiste, non si vede.
 */
import React, { useEffect, useState } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { PLATFORM_TOKEN_KEY } from '../../../api/platformClient';
import { soundPiuAPI } from '../../../api/soundPiu';
import { creaAccount } from '../../../utils/authLinks';
import useSeoMeta from '../../storefront/lib/useSeoMeta';
import SoundTopbar from '../SoundTopbar';
import { SOUND_PIU_ATTIVO, PIU_PREZZO } from '../stato';
import '../frequenze.css';
import '../meditazioni.css';
import './casa.css';

export const COSA_DA_IL_PIU = [
  'Le meditazioni e le playlist riservate al Più, intere',
  'Le nuove ogni settimana, prima di tutti',
  'Riprendi da dove eri, su ogni telefono',
  'Nessuna pubblicità, nessun gioco a punti: solo il suono',
];

export default function PiuPage() {
  const hasAccount = !!localStorage.getItem(PLATFORM_TOKEN_KEY);
  const [stato, setStato] = useState(null);
  const [occupato, setOccupato] = useState(false);
  const [msg, setMsg] = useState('');
  const annullato = /[?&]annullato=1/.test(window.location.search);
  useSeoMeta({ title: 'Aurya Più | Le meditazioni riservate', description: `Tutte le meditazioni e le playlist riservate, ${PIU_PREZZO}, solo annuale. Il Cerchio resta gratuito.`, canonicalPath: '/meditazioni/piu' });
  useEffect(() => {
    if (!SOUND_PIU_ATTIVO || !hasAccount) return;
    soundPiuAPI.stato().then((r) => setStato(r.data)).catch(() => setStato(null));
  }, [hasAccount]);
  if (!SOUND_PIU_ATTIVO) return <Navigate to="/meditazioni" replace />;

  const vai = async (fn) => {
    setOccupato(true); setMsg('');
    try { const r = await fn(); if (r.data?.url) window.location.href = r.data.url; }
    catch (err) { setMsg(err?.response?.data?.detail || 'Non sono riuscito ad aprire il pagamento: riprova.'); }
    finally { setOccupato(false); }
  };
  return (
    <div className="fqz med casa" data-testid="piu-page">
      <SoundTopbar firma="Meditazioni" qui="/meditazioni" />
      <header>
        <div>
          <h1>Aurya <em>Più</em></h1>
          <div className="sub">le meditazioni riservate, per chi ascolta ogni giorno</div>
        </div>
      </header>
      <main style={{ maxWidth: 680 }}>
        <section className="casa-sezione" style={{ marginTop: 8 }}>
          <span className="etichetta">{PIU_PREZZO} · solo annuale · si disdice quando vuoi</span>
          <ul style={{ margin: '14px 0 0', padding: 0, listStyle: 'none', color: 'var(--dim)', fontSize: 15, lineHeight: 1.6 }}>
            {COSA_DA_IL_PIU.map((r) => <li key={r}>✦ {r}</li>)}
          </ul>
          <p style={{ color: 'var(--dimmer)', fontSize: 13, marginTop: 14 }}>Il Cerchio resta gratuito: tutte le meditazioni che oggi ascolti con l'email restano tue.</p>
          {annullato && <p style={{ color: 'var(--dim)', fontSize: 13 }}>Nessun addebito: puoi riprovare quando vuoi.</p>}
          <div style={{ marginTop: 18, display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
            {!hasAccount ? (
              <a className="casa-cta" href={creaAccount('', '/meditazioni/piu')} data-testid="piu-crea-account">Crea il tuo account per entrare</a>
            ) : stato?.abbonato ? (
              <>
                <span style={{ color: 'var(--bone)' }}>Sei nel Più{stato.cancel_at_period_end ? ' · si chiude a fine periodo' : ''}.</span>
                <button type="button" className="primary" disabled={occupato} onClick={() => vai(soundPiuAPI.portale)} data-testid="piu-portale">Gestisci</button>
              </>
            ) : (
              <button type="button" className="primary" disabled={occupato} onClick={() => vai(() => soundPiuAPI.checkout('/account#meditazioni'))} data-testid="piu-abbonati">Entra nel Più · {PIU_PREZZO}</button>
            )}
            <Link to="/meditazioni" style={{ color: 'var(--water)', fontSize: 13 }}>Torna alle meditazioni</Link>
          </div>
          {msg && <p style={{ color: 'var(--alert)', fontSize: 13, marginTop: 10 }}>{msg}</p>}
        </section>
      </main>
    </div>
  );
}
