/**
 * Observability module for AFianco frontend.
 *
 * Public API:
 *     captureException(error, context)  — report an error to Sentry
 *     captureMessage(message, level)    — report a notable event
 *
 * Components (each opt-in via dedicated env var):
 *     - Sentry SDK (REACT_APP_SENTRY_DSN)  — Step A2
 *
 * Each component is fail-safe: missing env var → disabled, app continues.
 *
 * SIDE EFFECT: this module calls initSentry() on import.
 *
 * Importing this module as early as possible (in src/index.js, before other
 * imports) ensures Sentry is set up before other modules execute and possibly
 * throw. Without this, errors during i18n init / smartToast setup / etc. would
 * not be captured.
 */
import { initSentry } from "./sentry";

// Side-effect: initialize Sentry on module load.
// Runs once, regardless of how many places import this module.
initSentry();

export { captureException, captureMessage } from "./sentry";
