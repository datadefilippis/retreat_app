/**
 * I cappelli — il MODELLO del menu dell'omino, DN2 (21/8/2026).
 *
 * Il menu account viveva solo dentro MarketplaceShell, cioe' solo nel
 * mondo chiaro: chi entrava in Aurya Sound o nelle meditazioni smetteva
 * di vedere di essere loggato — niente «chi sono», niente account,
 * niente «Esci». In un posto con preferiti e contenuti riservati e' un
 * vuoto, non una scelta estetica.
 *
 * Qui vivono le VOCI e le AZIONI, una volta sola; ogni mondo le veste
 * come vuole (Tailwind/Radix nel chiaro, .fqz nel buio). Stesso disegno
 * di utils/authLinks e lib/cerchio: la regola in un modulo, mai
 * ricomposta a mano nelle pagine — altrimenti i due menu divergono al
 * primo cambiamento, ed e' esattamente cosi' che nascono i due mondi
 * che si contraddicono.
 */
import api from '../api/client';
import { PLATFORM_TOKEN_KEY } from '../api/platformClient';
import { scordaProva } from './cerchio';

export function cappelliAddosso() {
  let cliente = false;
  let operatore = false;
  try {
    cliente = Boolean(localStorage.getItem(PLATFORM_TOKEN_KEY));
    operatore = Boolean(localStorage.getItem('token'));
  } catch { /* private mode */ }
  return { cliente, operatore, dentro: cliente || operatore };
}

/**
 * Le voci del menu, identiche nei due mondi (ID/ID-bis/ID-quater):
 * chi e' dentro non legge mai un invito a entrare; l'operatore senza
 * cappello cliente ha il gesto per indossarlo, non un link che rimbalza.
 * `to` = navigazione · `action` = gesto (vedi indossaCappelloCliente).
 */
export function vociAccount({ cliente, operatore }) {
  const tue = cliente
    ? [{ to: '/account', label: 'Il mio account', testid: 'account-menu-my' }]
    : operatore
      ? [{ action: 'addClientHat', label: 'Usa Aurya come cliente', testid: 'account-menu-add-client' }]
      : [
        { to: '/accedi', label: 'Accedi', testid: 'account-menu-signin' },
        { to: '/accedi?vista=crea', label: 'Crea il tuo account', testid: 'account-menu-signup' },
      ];
  const professionisti = operatore
    ? [{ to: '/dashboard', label: 'Il tuo gestionale', testid: 'account-menu-gestionale' }]
    : [{ to: '/entra-nella-rete', label: 'Lavora con Aurya', testid: 'account-menu-operator-join' }];
  return { tue, professionisti };
}

/**
 * ID-quinquies — il cappello cliente si INDOSSA con un gesto: il token
 * cliente torna nella stessa risposta, niente secondo accesso.
 * `onErrore` riceve il messaggio da mostrare (ogni mondo lo dice a modo suo).
 */
export async function indossaCappelloCliente(onErrore) {
  let opToken = null;
  try { opToken = localStorage.getItem('token'); } catch { /* private mode */ }
  if (!opToken) { window.location.assign('/accedi'); return; }
  try {
    const res = await api.post('/auth/hats/client', {}, {
      headers: { Authorization: `Bearer ${opToken}` },
    });
    if (res.data?.access_token) {
      localStorage.setItem(PLATFORM_TOKEN_KEY, res.data.access_token);
    }
    window.location.assign('/account');
  } catch (err) {
    const detail = err?.response?.data?.detail;
    onErrore?.(typeof detail === 'string' ? detail
      : 'Non siamo riusciti ad attivare il tuo profilo cliente. Riprova tra poco.');
  }
}

/**
 * ID-quater — «Esci» esce DAVVERO: una persona ha una sessione sola (a
 * volte con due cappelli), quindi si chiudono entrambi i token e la
 * prova del cerchio. Hard navigate: l'AuthContext riparte pulito.
 */
export function esci(dove = '/') {
  try {
    localStorage.removeItem(PLATFORM_TOKEN_KEY);
    localStorage.removeItem('token');
    scordaProva();
  } catch { /* private mode */ }
  window.location.assign(dove);
}
