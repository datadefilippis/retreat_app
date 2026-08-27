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
import React from 'react';
import SoundAccountMenu from './SoundAccountMenu';

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
  { to: '/blog', label: 'Magazine' },
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
  const voci = PASSERELLA;
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
        {voci.map((v) => (
          <a key={v.to} href={v.to}
            onClick={(e) => guardia(e, v.to)}
            aria-current={qui === v.to ? 'page' : undefined}>{v.label}</a>
        ))}
      </nav>
      <span className="tb-spacer" />
      {extra}
      <SoundAccountMenu />
    </div>
  );
}
