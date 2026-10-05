/**
 * MP1 (5/10/2026) — IL punto di verita' del consenso cookie.
 *
 * Due categorie oltre agli essenziali:
 *   - statistiche: Google Analytics 4 (Consent Mode)
 *   - marketing:   Meta Pixel + Conversions API (misurare le inserzioni)
 *
 * Regole:
 *   - niente parte senza il si' della sua categoria;
 *   - la scelta si salva in `aurya_consent_v3` e vale finche' l'utente
 *     non la cambia da «Preferenze cookie» nel pie' di pagina;
 *   - chi aveva scelto con la versione precedente (una sola categoria)
 *     rivede il banner UNA volta, perche' le categorie sono cambiate; nel
 *     frattempo la sua scelta sulle statistiche resta valida (legacy);
 *   - chi deve reagire a un cambio (GA, Meta) si registra con onCambio():
 *     questo modulo non importa nessuno dei due, cosi' niente cicli.
 */
const CHIAVE = 'aurya_consent_v3';
const CHIAVE_LEGACY = 'aurya_analytics_consent_v1';   // GA1: {analytics, at}
export const VERSIONE_TESTO_BANNER = 'banner-2026-10-05';

const ascoltatori = new Set();

function leggi(chiave) {
  try {
    const raw = window.localStorage.getItem(chiave);
    return raw ? JSON.parse(raw) : null;
  } catch { return null; }
}

/** {analytics, marketing, at, versione, legacy} oppure null se mai scelto. */
export function leggiConsenso() {
  if (typeof window === 'undefined') return null;
  const v3 = leggi(CHIAVE);
  if (v3 && typeof v3 === 'object') {
    return { analytics: v3.analytics === true, marketing: v3.marketing === true,
             at: v3.at || null, versione: v3.versione || null, legacy: false };
  }
  const v1 = leggi(CHIAVE_LEGACY);
  if (v1 && typeof v1 === 'object') {
    // scelta vecchia: le statistiche valgono, il marketing non e' mai stato chiesto
    return { analytics: v1.analytics === true, marketing: false, at: v1.at || null,
             versione: null, legacy: true };
  }
  return null;
}

/** Il banner va mostrato? Mai scelto, o scelto con le categorie vecchie. */
export function bannerDaMostrare() {
  const c = leggiConsenso();
  return !c || c.legacy === true;
}

export const consensoStatistiche = () => leggiConsenso()?.analytics === true;
export const consensoMarketing = () => leggiConsenso()?.marketing === true;

/** Salva la scelta e avvisa chi ascolta (GA, Meta). */
export function salvaConsenso({ analytics = false, marketing = false } = {}) {
  const scelta = { analytics: !!analytics, marketing: !!marketing,
                   at: new Date().toISOString(), versione: VERSIONE_TESTO_BANNER };
  try { window.localStorage.setItem(CHIAVE, JSON.stringify(scelta)); }
  catch { /* storage negato: la scelta vale per la sessione, via gli ascoltatori */ }
  ascoltatori.forEach((cb) => { try { cb(scelta); } catch { /* un ascoltatore rotto non ferma gli altri */ } });
  return scelta;
}

/** Registra un ascoltatore; ritorna la funzione per toglierlo. */
export function onCambio(cb) {
  ascoltatori.add(cb);
  return () => ascoltatori.delete(cb);
}

/** «Preferenze cookie» nel pie' di pagina: riapre il banner. */
export const EVENTO_APRI = 'aurya:preferenze-cookie';
export function apriPreferenzeCookie() {
  if (typeof window !== 'undefined') window.dispatchEvent(new Event(EVENTO_APRI));
}
