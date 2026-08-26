/**
 * IL MESSAGGIO D'ERRORE, reso sempre una frase (fix 26/8).
 *
 * Il bug che ha fatto nascere questo file: su un 422 FastAPI il
 * `detail` non è una stringa — è un ARRAY di oggetti di validazione —
 * e renderizzarlo dritto in un <p> ammazza React («Objects are not
 * valid as a React child»): il rito crashava sull'intera pagina
 * invece di dire cosa non andava.
 *
 * Da qui la regola: NIENTE `e?.response?.data?.detail` diretto nel
 * JSX — si passa sempre da qui, e da qui esce SEMPRE una stringa.
 * Puro, zero import, testato in Node.
 */

/** L'errore di una chiamata API → una frase da mostrare. */
export function messaggio(e, fallback) {
  const d = e?.response?.data?.detail;
  if (typeof d === 'string' && d) return d;
  if (Array.isArray(d)) {
    const frasi = d
      .map((v) => (typeof v === 'string' ? v : v?.msg))
      .filter((v) => typeof v === 'string' && v);
    if (frasi.length) return frasi.join(' · ');
  }
  return fallback;
}
