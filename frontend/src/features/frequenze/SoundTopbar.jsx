/**
 * SoundTopbar — la testata del mondo Sound (DN1/DN2/DN4, 21/8/2026).
 *
 * Una sola testata per le quattro viste (landing, workspace,
 * meditazioni, traccia condivisa): prima ognuna ricomponeva a mano il
 * marchio, e infatti erano gia' scivolate via l'una dall'altra.
 *
 * Tre cose fisse, le stesse del sito — perche' cambia la LUCE, non
 * l'identita':
 *   - il marchio (Cinzel maiuscolo, oro di marca), che e' anche
 *     l'uscita: clic → si torna su Aurya;
 *   - la passerella: due o tre voci, non l'intero menu del sito;
 *   - l'omino, con le stesse voci del menu chiaro (lib/cappelli).
 */
import React, { useState } from 'react';
import SoundAccountMenu from './SoundAccountMenu';
import { SOUND_CASA_NUOVA } from './stato';
import { cappelliAddosso } from '../../lib/cappelli';
import './casa/foglio-suono.css';   // MR7/ES0 — il foglio «Il suono», ovunque

/* SN1 (8/10, piano Aurya Sound §4.0) — LA PASSERELLA DELLA CASA: tre
   porte al massimo. Meditazioni (ascoltare) · Il suono (capire) · Crea
   (comporre, solo per chi porta il cappello del professionista: il
   portiere della pagina decide poi se la stanza e' sua). Le vecchie
   voci restano sotto, dietro il flag, finche' la casa non e' in prod. */
const CASA_PASSERELLA = [
  { to: '/meditazioni', label: 'Meditazioni' },
  { to: '/sound', label: 'Il suono' },
];
const CASA_VOCE_CREA = { to: '/sound/crea', label: 'Crea' };

const PASSERELLA = [
  { to: '/meditazioni', label: 'Meditazioni' },
  /* NV2 (27/8, analisi BUSSOLA) — la voce si chiamava «Sound» come
     quella del menu del sito, ma portava altrove (biblioteca, non
     landing): stessa parola, due posti. Ora dice il suo nome vero —
     lo stesso della porta sulla landing («La Biblioteca»). E il Lab
     esce dalla passerella: e' una STANZA della biblioteca, vive
     nella barra delle stanze (StanzeSound), non nel menu. */
  /* TM7 (27/8, founder) — la voce porta il nome del MONDO: dentro il
     buio «Aurya Sound» e' casa, non una stanza. */
  { to: '/sound/esplora', label: 'Aurya Sound' },
  /* Founder (30/8): il Lab TORNA in passerella col suo nome — e' una
     delle tre porte del mondo. Magazine esce: non e' casa Sound. */
  { to: '/sound/lab', label: 'Aurya Lab' },
];

export default function SoundTopbar({ firma = 'Sound', qui = null,
  extra = null, primaDiUscire = null }) {
  /* TM6 — la passerella e il marchio sono <a href> (ricarica piena):
     con una sessione sporca il click passa dalla campana della
     pagina, che decide (Salva ed esci / Esci / Resta). */
  const guardia = (e, to) => {
    if (primaDiUscire && primaDiUscire(to, true)) e.preventDefault();
  };
  /* Deciso dal founder (27/8, ribadito): Professional NON si usa —
     niente voce in passerella, per NESSUNO. Lo strumento /sound/pro
     resta vivo per URL (col suo portiere), substrato della futura
     fase-vibrazioni: un menu che lo nomina sarebbe una vetrina, e la
     vetrina l'abbiamo spenta. */
  /* MR7 (8/10 sera, founder): «Crea» si vede SOLO a chi puo' comporre (Pro o
     concessione del system admin): il segnale e' la cache che Crea stesso
     scrive dal profilo (aurya_sound_crea), non il semplice token operatore.
     Il portiere vero resta sul server (require_sound_crea). */
  let puoComporre = false;
  try { puoComporre = cappelliAddosso().operatore && localStorage.getItem('aurya_sound_crea') === '1'; } catch { /* privato */ }
  const voci = SOUND_CASA_NUOVA
    ? (puoComporre ? [...CASA_PASSERELLA, CASA_VOCE_CREA] : CASA_PASSERELLA)
    : PASSERELLA;
  /* MR7 — dalla casa «Il suono» non porta fuori: apre un foglio con le tre
     porte (schede, fondamenta, Lab) e, in fondo, il rimando alle meditazioni. */
  const [foglioSuono, setFoglioSuono] = useState(false);
  /* ES0 (8/10 sera, founder): il foglio si apre da OGNI pagina scura (casa,
     esplora, fondamenta, Lab, scheda): «Il suono» non porta mai fuori. */
  const inCasa = SOUND_CASA_NUOVA && !!qui && (qui === '/meditazioni' || qui.startsWith('/sound'));
  let dove = qui || '';
  try { dove = window.location.pathname || dove; } catch { /* ssr */ }
  const portaCorrente = (to) => dove === to || dove.startsWith(to + '/');
  const suonoCorrente = dove.startsWith('/sound');
  return (
    <div className="topbar">
      <a className="fqzbrand" href="/" onClick={(e) => guardia(e, '/')} data-testid="fqz-brand" title="Torna su Aurya">
        <img src="/logo-aurya-512.png" alt="" width="36" height="36" />
        <span>
          <b>Aurya</b>
          <i>{firma}</i>
        </span>
      </a>
      <nav className="tb-nav" data-testid="fqz-nav">
        {voci.map((v) => (inCasa && v.to === '/sound'
          ? <button key={v.to} type="button" className="tb-voce" data-testid="fqz-nav-suono" aria-current={suonoCorrente ? 'page' : undefined} onClick={() => setFoglioSuono(true)}>{v.label}</button>
          : <a key={v.to} href={v.to}
            onClick={(e) => guardia(e, v.to)}
            aria-current={qui === v.to ? 'page' : undefined}>{v.label}</a>
        ))}
      </nav>
      {foglioSuono && (
        <div className="gate foglio-suono" onClick={() => setFoglioSuono(false)} data-testid="fqz-foglio-suono">
          <div className="gatebox" onClick={(e) => e.stopPropagation()}>
            <h2 style={{ marginTop: 0 }}>Il suono</h2>
            <p style={{ color: 'var(--dim)', fontSize: 14, marginTop: 4 }}>Dietro ogni meditazione c'è un suono composto apposta. Tre porte per capirlo.</p>
            <div className="porte-suono">
              {[['/sound/esplora', 'Esplora le frequenze', 'Le schede: bande cerebrali, frequenze, metodi.'],
                ['/sound/impara', 'Le fondamenta', 'Come funziona il suono, con parole semplici e un glossario.'],
                ['/sound/lab', 'Il Lab', 'Cinque stanze per provare con le orecchie.']].map(([to, t, d]) => (
                <a key={to} href={to} className={`porta-suono${portaCorrente(to) ? ' corrente' : ''}`} aria-current={portaCorrente(to) ? 'page' : undefined} onClick={(e) => guardia(e, to)}>
                  <b>{t}</b><span>{portaCorrente(to) ? 'Sei qui' : d}</span>
                </a>
              ))}
            </div>
            {/* 8/10 sera (founder): dal foglio non si esce verso la landing;
                l'unico rimando e' alle meditazioni, il valore principale
                (nascosto quando si e' gia' nella casa). */}
            <div className="gatefoot" style={{ justifyContent: 'space-between', marginTop: 14 }}>
              {dove.startsWith('/meditazioni')
                ? <span />
                : <a href="/meditazioni" className="porta-landing" onClick={(e) => guardia(e, '/meditazioni')} data-testid="fqz-foglio-meditazioni">Le meditazioni →</a>}
              <button type="button" onClick={() => setFoglioSuono(false)}>Chiudi</button>
            </div>
          </div>
        </div>
      )}
      <span className="tb-spacer" />
      {extra}
      <SoundAccountMenu />
    </div>
  );
}
