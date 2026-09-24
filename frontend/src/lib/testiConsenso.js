/**
 * I testi della casella di consenso, versionati — Lotto D (24/9/2026).
 *
 * SPECCHIO ESATTO di backend/services/testi_consenso.py: stesse chiavi,
 * stessi testi, stessa versione corrente (guardia di parita' in
 * backend/tests/test_testi_consenso_parita.py). Il registro del
 * consenso cita la versione e ne conserva il testo: la versione che il
 * form dichiara (`consenso_versione`) deve esistere di la', e il testo
 * che la persona ha letto deve essere quello, parola per parola.
 *
 * Regola: un testo, una volta pubblicato, non si tocca. Per cambiare
 * la casella si aggiunge una versione nuova QUI e nel backend, e si
 * sposta VERSIONE_CORRENTE.
 */

export const TESTI = {
  // la casella della landing del Cerchio, della home e delle meditazioni
  'cerchio-v1': 'Acconsento a ricevere le email del Cerchio di Aurya.',
  // la variante dei cancelli Sound (CancelloLettera)
  'cerchio-v2': 'Acconsento a ricevere le email del Cerchio di Aurya '
    + '(meditazioni, anteprime, la Lettera). Confermerai dall\'email '
    + 'che ti arriva; ti cancelli con un clic.',
  // dal 24/9: un testo solo, su tutte le porte
  'cerchio-v3': 'Sì, mandami la Lettera del Cerchio di Aurya '
    + '(meditazioni, guide, ritiri). Ti cancelli con un clic.',
  // cerca-ritiro (TravelerLandingPage): la promessa dei ritiri su misura
  'cerchio-ritiri-v1': 'Acconsento a ricevere le email del Cerchio di Aurya, '
    + 'con ritiri ed esperienze selezionati in base alle mie preferenze.',
  // i CTA del Magazine e i cancelli delle guide
  'lettera-v1': 'Acconsento a ricevere la lettera di Aurya via email.',
  // InvitoSound (esplora, lab)
  'sound-v1': 'Acconsento a ricevere la newsletter; disiscrizione in un click.',
  // i lead viaggiatori del prelancio (poi migrati con bn2)
  'lancio-v1': 'Acconsento a essere contattato via email sul lancio di Aurya.',
};

export const VERSIONE_CORRENTE = 'cerchio-v3';

/** La casella di oggi: { versione, testo }. Ogni superficie del Cerchio
 *  mostra QUESTO testo e dichiara QUESTA versione al subscribe. */
export function testoConsenso(versione = VERSIONE_CORRENTE) {
  const v = TESTI[versione] ? versione : VERSIONE_CORRENTE;
  return { versione: v, testo: TESTI[v] };
}

/**
 * La provenienza che il form manda insieme all'iscrizione (Lotto B1):
 * l'URL, chi ci ha mandato, gli utm della query. Tutto best-effort:
 * fuori dal browser (SSR, test) torna vuoto.
 */
export function provenienzaCorrente() {
  if (typeof window === 'undefined') return {};
  let utm = null;
  try {
    const q = new URLSearchParams(window.location.search);
    const pulisci = (k) => (q.get(k) || '').trim().slice(0, 80) || null;
    const source = pulisci('utm_source');
    const medium = pulisci('utm_medium');
    const campaign = pulisci('utm_campaign');
    if (source || medium || campaign) utm = { source, medium, campaign };
  } catch { /* query illeggibile: niente utm */ }
  return {
    url: String(window.location.href || '').slice(0, 500) || null,
    referrer: String((typeof document !== 'undefined' && document.referrer) || '').slice(0, 500) || null,
    ...(utm ? { utm } : {}),
  };
}
