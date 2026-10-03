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
import { VERSIONE_CORRENTE, provenienzaCorrente } from './testiConsenso';

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

/* SO (3/10/2026) — cosa ha mandato il server all'ultima iscrizione:
   «benvenuto» (singolo opt-in acceso: la prima Lettera e' gia' in arrivo,
   un suo link apre i contenuti) oppure «conferma» (doppio opt-in: l'email
   con «Entro nel Cerchio»). I cancelli lo leggono per dire la cosa vera. */
let _ultimaModalita = 'conferma';
export const ultimaModalita = () => _ultimaModalita;

/** La riga d'attesa dei cancelli, secondo la modalita' del server. */
export function testoAttesa(cosa = 'con le meditazioni sbloccate') {
  return _ultimaModalita === 'benvenuto'
    ? `Ti abbiamo mandato la prima Lettera del Cerchio: apri l’email e tocca un suo link. Ti riporta qui, ${cosa}.`
    : `Ti abbiamo scritto: apri l’email e clicca «Entro nel Cerchio». Ti riporta qui, ${cosa}.`;
}

/**
 * SB2 — il cervello unico dei form della Lettera.
 * Ritorna 'sbloccato' (gia' confermato: prova salvata, tutto aperto)
 * oppure 'attesa' (si aspetta il clic nell'email: di conferma o di benvenuto,
 * vedi ultimaModalita()).
 * Gli errori del subscribe risalgono al chiamante (il copy e' suo).
 */
export async function iscriviESblocca({ email, source, returnTo,
  wantsExperiences = null, language = 'it', name, ritiri = null }) {
  // FV5 (10/9/2026 sera) — l'avviso ritiri NON si accende di passaggio:
  // dai cancelli (meditazioni, guide, InvitoSound) arriva solo l'email,
  // e il flag viaggia soltanto quando un form lo ha davvero chiesto.
  // Prima era `true` di default: sei iscritti dalle meditazioni
  // «volevano i ritiri» senza averlo mai detto.
  // US (10/9 notte) — i cancelli ora LO CHIEDONO, col blocco condiviso
  // AvvisamiRitiri: `ritiri` e' il suo payload (wants_experiences, vie,
  // citta', dove, budget), e vince sul vecchio flag nudo.
  const risposta = await api.post('/public/newsletter/subscribe', {
    email: (email || '').trim(), consent: true, language, source,
    ...(typeof wantsExperiences === 'boolean' ? { wants_experiences: wantsExperiences } : {}),
    ...(ritiri && typeof ritiri === 'object' ? ritiri : {}),
    return_to: returnTo || undefined,
    // questo E' un cancello di sblocco: al gia'-confermato la prova
    // arriva dalla riga sotto, niente magic link via email
    unlock_flow: true,
    ...(name ? { name } : {}),
    // Lotto D (24/9/2026) — la provenienza scritta all'iscrizione (url,
    // referrer, utm) e la VERSIONE del testo di consenso che la casella
    // mostrava: e' quello che il registro del consenso conserva.
    ...provenienzaCorrente(),
    consenso_versione: VERSIONE_CORRENTE,
  });
  _ultimaModalita = risposta?.data?.modalita === 'benvenuto' ? 'benvenuto' : 'conferma';
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
