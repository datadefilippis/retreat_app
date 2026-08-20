/**
 * Il cerchio — SB1/SB2 (20/8/2026, founder).
 *
 * «Far parte del cerchio» (Lettera confermata, o account Aurya) e' UN
 * diritto, ma la prova era spezzata in quattro artefatti: il JWT della
 * Lettera apriva solo le guide, una coppia email+HMAC solo le
 * meditazioni, un flag solo il player della traccia condivisa. La
 * stessa persona, gia' dentro, trovava chiuso il cancello accanto.
 *
 * Da qui in poi la prova e' UNA — il token della Lettera (JWT scope
 * newsletter_subscriber) — e vive in UN posto: questa e' l'unica
 * porta per leggerla e scriverla. Stesso disegno di utils/authLinks:
 * la regola in un modulo, mai ricomposta a mano nelle pagine.
 *
 * Qui vive anche il cervello dei form (SB2): dopo OGNI iscrizione si
 * tenta lo sblocco immediato — chi e' gia' confermato entra subito
 * («sei gia' dei nostri»), chi e' nuovo aspetta il click nell'email.
 * Prima ogni form aveva la sua variante di questa logica, e
 * divergevano.
 */
import api from '../api/client';

export const PROVA_KEY = 'aurya_nl_token';

// Chiavi del vecchio mondo (P2/P3): non si scrivono piu', si leggono
// solo per migrare i browser che le hanno gia' (vedi migraVecchieChiavi).
const VECCHIA_FQZ = 'fqz_catalog_unlock';
const VECCHIO_FLAG = 'fqz_listener_ok';

export function salvaProva(token) {
  try { localStorage.setItem(PROVA_KEY, token); } catch { /* private mode */ }
}

export function prova() {
  try { return localStorage.getItem(PROVA_KEY) || null; } catch { return null; }
}

export function scordaProva() {
  try {
    localStorage.removeItem(PROVA_KEY);
    localStorage.removeItem(VECCHIA_FQZ);
    localStorage.removeItem(VECCHIO_FLAG);
  } catch { /* private mode */ }
}

/**
 * L'email dentro la prova (payload del JWT, leggibile senza segreto).
 * E' la memoria dell'indirizzo per chi non ha ancora un account: la
 * porta di registrazione la precompila da qui (SB5).
 */
export function emailDellaProva() {
  const t = prova();
  if (!t) return null;
  try {
    const body = t.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
    return JSON.parse(atob(body)).email || null;
  } catch { return null; }
}

/**
 * Sblocco per chi e' GIA' iscritto e confermato: dichiara l'email,
 * riceve la prova. 404 = non risulta (il chiamante decide il copy).
 */
export async function sblocca(email) {
  const r = await api.post('/public/newsletter/unlock',
    { email: (email || '').trim() });
  salvaProva(r.data.subscriber_token);
  return r.data.subscriber_token;
}

/**
 * SB2 — il cervello unico dei form della Lettera.
 * Ritorna 'sbloccato' (gia' confermato: prova salvata, tutto aperto)
 * oppure 'attesa' (double opt-in in corso: si aspetta il click).
 * Gli errori del subscribe risalgono al chiamante (il copy e' suo).
 */
export async function iscriviESblocca({ email, source, returnTo,
  wantsExperiences = true, language = 'it', name }) {
  await api.post('/public/newsletter/subscribe', {
    email: (email || '').trim(), consent: true, language, source,
    wants_experiences: wantsExperiences, return_to: returnTo || undefined,
    ...(name ? { name } : {}),
  });
  try {
    await sblocca(email);
    return 'sbloccato';
  } catch {
    return 'attesa';
  }
}

/**
 * Migrazione dolce dei browser col vecchio artefatto HMAC: se non c'e'
 * la prova ma c'e' la vecchia coppia {email}, si prova lo sblocco con
 * quell'email; comunque vada, le vecchie chiavi si tolgono (chi non
 * risulta confermato rivedra' il cancello, che ora dice cosa fare).
 */
export async function migraVecchieChiavi() {
  if (prova()) return;
  let vecchia = null;
  try { vecchia = JSON.parse(localStorage.getItem(VECCHIA_FQZ) || 'null'); }
  catch { /* corrotta: si butta */ }
  try {
    localStorage.removeItem(VECCHIA_FQZ);
    localStorage.removeItem(VECCHIO_FLAG);
  } catch { /* private mode */ }
  if (vecchia?.email) {
    try { await sblocca(vecchia.email); } catch { /* non confermata */ }
  }
}
