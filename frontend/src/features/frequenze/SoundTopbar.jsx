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
import { useAuth } from '../../context/AuthContext';
import SoundAccountMenu from './SoundAccountMenu';

const PASSERELLA = [
  { to: '/meditazioni', label: 'Meditazioni' },
  /* L3-bis — /sound e' la landing CHIARA di sistema: l'hub del mondo
     scuro e' la biblioteca */
  { to: '/sound/esplora', label: 'Sound' },
  { to: '/sound/lab', label: 'Lab' },
  { to: '/blog', label: 'Magazine' },
];

export default function SoundTopbar({ firma = 'Sound', qui = null, extra = null }) {
  /* M7a (26/8) — la porta di Sound Professional: visibile SOLO a chi
     ha il privilegio. Per tutti gli altri la passerella resta
     identica a prima: un link che porta a un cartello «su invito»
     sarebbe rumore, non una porta. AuthProvider avvolge l'app intera,
     quindi il hook e' sicuro anche sulle pagine pubbliche. */
  const { user } = useAuth();
  /* IL TRIGGER (richiesta founder): ogni operatore loggato vede la
     via Professional — chi ha il privilegio va allo strumento, chi
     non ce l'ha va alla pagina di vendita. Una voce, due destinazioni.
     Gli anonimi la scoprono dalla landing di sistema. */
  const voci = user
    ? [...PASSERELLA, {
        to: user.sound_professional ? '/sound/pro' : '/sound/professional',
        label: 'Professional',
      }]
    : PASSERELLA;
  return (
    <div className="topbar">
      <a className="fqzbrand" href="/" data-testid="fqz-brand" title="Torna su Aurya">
        <img src="/logo-aurya-512.png" alt="" width="36" height="36" />
        <span>
          <b>Aurya</b>
          <i>{firma}</i>
        </span>
      </a>
      <nav className="tb-nav" data-testid="fqz-nav">
        {voci.map((v) => (
          <a key={v.to} href={v.to}
            aria-current={qui === v.to ? 'page' : undefined}>{v.label}</a>
        ))}
      </nav>
      <span className="tb-spacer" />
      {extra}
      <SoundAccountMenu />
    </div>
  );
}
