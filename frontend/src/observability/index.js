/**
 * Observability module for the frontend.
 *
 * Public API:
 *     captureException(error, context)  — report an error to Sentry
 *     captureMessage(message, level)    — report a notable event
 *
 * SEO-E (14/9/2026 sera): l'SDK di Sentry pesava ~360 KB di sorgente
 * (~100 KB gzip) nel bundle INIZIALE di ogni pagina pubblica. Ora si carica
 * in un chunk proprio DOPO il primo paint (idle/load): le pagine per Google
 * e per il telefono partono senza. Gli errori dei primissimi millisecondi
 * (prima che il chunk arrivi) restano nel console del browser: scelta
 * consapevole, il costo era su ogni visita.
 *
 * Fail-safe: senza REACT_APP_SENTRY_DSN il chunk non si carica affatto.
 */
let _modulo = null;
let _caricamento = null;

function carica() {
  if (!_caricamento) {
    _caricamento = import(/* webpackChunkName: "osservabilita" */ "./sentry")
      .then((m) => { _modulo = m; try { m.initSentry(); } catch { /* fail-safe */ } return m; })
      .catch(() => null);
  }
  return _caricamento;
}

const dsn = (process.env.REACT_APP_SENTRY_DSN || "").trim();
if (dsn && typeof window !== "undefined") {
  const avvia = () => { carica(); };
  if ("requestIdleCallback" in window) window.requestIdleCallback(avvia, { timeout: 4000 });
  else window.addEventListener("load", () => setTimeout(avvia, 1500), { once: true });
}

export function captureException(error, context) {
  if (_modulo) return _modulo.captureException(error, context);
  if (dsn) carica().then((m) => m && m.captureException(error, context));
  return undefined;
}

export function captureMessage(message, level) {
  if (_modulo) return _modulo.captureMessage(message, level);
  if (dsn) carica().then((m) => m && m.captureMessage(message, level));
  return undefined;
}
