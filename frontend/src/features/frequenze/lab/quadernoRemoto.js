/**
 * IL QUADERNO CHE TI SEGUE (FA4, piano FARO, 30/8/2026).
 *
 * I quaderni del Lab nascono in localStorage (un dispositivo, una
 * vita). Con l'account Aurya diventano persistenti: qui vive il
 * sincronizzatore — legge locale e server, FONDE per client_id
 * (vince il piu' recente), scrive da entrambe le parti. Regole:
 * - anonimo/offline: localStorage come sempre, MAI un salvataggio
 *   perso o bloccato (ogni chiamata e' best-effort, try/catch);
 * - le voci vecchie senza client_id lo ricevono alla prima fusione;
 * - il server e' un deposito passivo: numeri ed etichette, mai audio.
 */
import platformApi, { PLATFORM_TOKEN_KEY } from '../../../api/platformClient';
import api from '../../../api/client';
import { leggiQuaderno, salvaListaQuaderno } from './cimatica';
import { leggiRitratti, salvaListaRitratti } from './fonderia';

/* I DUE CAPPELLI (founder 30/8): il quaderno segue chi sei, con
   qualunque cappello — account Aurya (platform_token) O operatore
   loggato (token). Il client giusto porta il token giusto; il
   backend distingue dal type del JWT. */
export const haAccount = () => {
  try {
    return !!localStorage.getItem(PLATFORM_TOKEN_KEY)
      || !!localStorage.getItem('token');
  } catch { return false; }
};

const clientGiusto = () => {
  try {
    return localStorage.getItem(PLATFORM_TOKEN_KEY) ? platformApi : api;
  } catch { return platformApi; }
};

const idNuovo = () =>
  Math.random().toString(16).slice(2) + Date.now().toString(16);

/* battesimo: ogni voce ha un client_id e una data di salvataggio */
const battezza = (voci) => (voci || []).map((v) => (
  v && v.client_id ? v : { ...v, client_id: idNuovo(),
    salvata_il: v?.salvata_il || Date.now() }
));

/* fusione per client_id: vince la piu' recente; l'ordine resta
   dal-piu'-nuovo (come i quaderni locali) */
const fondi = (locali, remote) => {
  const per = new Map();
  [...(remote || []), ...(locali || [])].forEach((v) => {
    if (!v || !v.client_id) return;
    const g = per.get(v.client_id);
    if (!g || (v.salvata_il || 0) >= (g.salvata_il || 0)) per.set(v.client_id, v);
  });
  return [...per.values()].sort(
    (a, b) => (b.salvata_il || 0) - (a.salvata_il || 0));
};

/**
 * Sincronizza entrambi i registri. Ritorna true se ha parlato col
 * server. Best-effort totale: qualsiasi errore lascia il locale
 * com'era.
 */
export async function sincronizza() {
  if (!haAccount()) return false;
  try {
    const locali = {
      risonanze: battezza(leggiQuaderno()),
      ritratti: battezza(leggiRitratti()),
    };
    const r = await clientGiusto().get('/frequencies/quaderno');
    const remote = (r.data && r.data.registri) || {};
    const fusi = {
      risonanze: fondi(locali.risonanze, remote.risonanze),
      ritratti: fondi(locali.ritratti, remote.ritratti),
    };
    salvaListaQuaderno(fusi.risonanze);
    salvaListaRitratti(fusi.ritratti);
    await clientGiusto().put('/frequencies/quaderno', { registri: fusi });
    return true;
  } catch { return false; }
}

/* dopo un salvataggio locale: spingi (fire-and-forget) */
export function spingi() {
  if (!haAccount()) return;
  sincronizza().catch(() => { /* best-effort */ });
}
