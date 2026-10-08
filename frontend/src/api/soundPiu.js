/**
 * SN4 (8/10/2026, piano Aurya Sound §5.2) — AURYA PIÙ, lato account.
 * Tutto sul token piattaforma: lo stato, il checkout, il portale.
 * Spento finché il server dice `attivo: false`.
 */
import platformApi from './platformClient';

export const soundPiuAPI = {
  stato: () => platformApi.get('/platform/me/piu'),
  checkout: (ritorno) => platformApi.post('/platform/me/piu/checkout', { ritorno: ritorno || '/account#meditazioni' }),
  portale: () => platformApi.post('/platform/me/piu/portale'),
};
