/**
 * Sentry SDK initialization for AFianco frontend.
 *
 * Opt-in via env vars:
 *     REACT_APP_SENTRY_DSN          → if unset, Sentry is fully disabled (noop)
 *     REACT_APP_SENTRY_ENVIRONMENT  → tag events (production/staging/development)
 *     REACT_APP_RELEASE_SHA         → tag events with git SHA for release tracking
 *     REACT_APP_SENTRY_TRACES_RATE  → 0.0–1.0, % of pageloads to trace (default 0.1)
 *
 * PII protection (4 layers, mirrors backend):
 *     1. sendDefaultPii=false       → SDK doesn't auto-include user data
 *     2. beforeSend hook            → custom event scrubber
 *     3. beforeBreadcrumb hook      → same scrubber for breadcrumbs
 *     4. recursive scrubber redacts:
 *          - field NAMES matching PII_FIELDS
 *          - HTTP HEADERS matching PII_HEADERS
 *          - free-text patterns (email, JWT, Bearer)
 *          - keyword-value pairs ("password was X", "token=Y")
 *
 * Privacy choice for MVP:
 *     - replaysSessionSampleRate=0  → NO session replay (would record DOM events)
 *     - replaysOnErrorSampleRate=0  → NO replay even on errors
 *     Both can be enabled post-GA when we are confident about scrubbing.
 *
 * Fail-safe:
 *     Any error during init is logged and swallowed. The app boots regardless.
 */
import * as Sentry from "@sentry/react";
import { scrubEvent, scrubBreadcrumb } from "./_pii_scrubber";

let _initialized = false;

export function initSentry() {
  const dsn = (process.env.REACT_APP_SENTRY_DSN || "").trim();
  const isDev = process.env.NODE_ENV !== "production";

  // Debug helper exposed on window in dev — useful for ad-blocker / cache
  // diagnostics. Inspect via console: `window.__AFIANCO_SENTRY_DEBUG`
  if (isDev && typeof window !== "undefined") {
    window.__AFIANCO_SENTRY_DEBUG = {
      dsn_present: !!dsn,
      dsn_prefix: dsn ? dsn.substring(0, 35) + "..." : null,
      env: process.env.REACT_APP_SENTRY_ENVIRONMENT || process.env.NODE_ENV,
      release: process.env.REACT_APP_RELEASE_SHA || "unknown",
      initialized: false,
      init_attempted_at: new Date().toISOString(),
    };
  }

  if (!dsn) {
    // console.warn is shown by default in browser DevTools (unlike console.info)
    console.warn(
      "[AFIANCO observability] ⚠️ Sentry DISABLED — REACT_APP_SENTRY_DSN not set in .env"
    );
    return false;
  }

  const environment =
    process.env.REACT_APP_SENTRY_ENVIRONMENT ||
    process.env.NODE_ENV ||
    "development";
  const release = process.env.REACT_APP_RELEASE_SHA || "unknown";
  const parsedRate = parseFloat(process.env.REACT_APP_SENTRY_TRACES_RATE || "0.1");
  const tracesSampleRate = Number.isFinite(parsedRate) ? parsedRate : 0.1;

  try {
    Sentry.init({
      dsn,
      environment,
      release,
      tracesSampleRate,
      // No session replay for MVP (privacy-first).
      replaysSessionSampleRate: 0,
      replaysOnErrorSampleRate: 0,
      sendDefaultPii: false,
      beforeSend: scrubEvent,
      beforeBreadcrumb: scrubBreadcrumb,
      // Filter common noise (browser extensions, benign warnings).
      ignoreErrors: [
        /^Script error\.?$/,
        /chrome-extension/i,
        /moz-extension/i,
        /safari-extension/i,
        // ResizeObserver loop noise (benign, common Chrome warning)
        /ResizeObserver loop limit exceeded/,
        /ResizeObserver loop completed with undelivered notifications/,
        // Network errors — not really errors, more user environment
        /Network request failed/,
        /Failed to fetch/,
      ],
      denyUrls: [
        /chrome-extension:\/\//,
        /^safari-extension:\/\//,
        /^moz-extension:\/\//,
      ],
    });
    _initialized = true;
    // Use console.warn for visibility (default DevTools filter shows it)
    console.warn(
      `[AFIANCO observability] ✅ Sentry INITIALIZED — env=${environment}, release=${release}, traces=${tracesSampleRate}`
    );

    // Update debug helper on window
    if (isDev && typeof window !== "undefined" && window.__AFIANCO_SENTRY_DEBUG) {
      window.__AFIANCO_SENTRY_DEBUG.initialized = true;
      window.__AFIANCO_SENTRY_DEBUG.init_completed_at = new Date().toISOString();
    }

    // Auto-fire a boot-marker event so the dashboard receives at least one
    // event proving the SDK <-> Sentry connection is healthy. Without this,
    // an ad-blocker silently dropping events looks identical to "Sentry off"
    // until a real exception occurs. Dev-only.
    if (isDev) {
      try {
        Sentry.captureMessage(
          `AFianco frontend boot — env=${environment}, release=${release}`,
          "info"
        );
      } catch (_e) {
        // captureMessage is fail-safe internally; ignore.
      }
    }

    return true;
  } catch (e) {
    console.error("[AFIANCO observability] ❌ Sentry INIT FAILED:", e);
    return false;
  }
}

/**
 * Capture an exception. No-op if Sentry is not initialized.
 * Safe to call from anywhere (e.g. ErrorBoundary.componentDidCatch).
 *
 * @param {Error} error - The error to report
 * @param {object} context - Extra context (errorInfo, custom fields, ...)
 */
export function captureException(error, context = {}) {
  if (!_initialized) return;
  try {
    Sentry.withScope((scope) => {
      for (const [key, value] of Object.entries(context || {})) {
        scope.setExtra(key, value);
      }
      Sentry.captureException(error);
    });
  } catch (e) {
    console.error("[observability] captureException failed:", e);
  }
}

/**
 * Capture a message (e.g. for tracking notable events). No-op if Sentry off.
 */
export function captureMessage(message, level = "info") {
  if (!_initialized) return;
  try {
    Sentry.captureMessage(message, level);
  } catch (e) {
    console.error("[observability] captureMessage failed:", e);
  }
}

/**
 * For tests: expose initialization state. Internal use only.
 */
export function _isSentryInitialized() {
  return _initialized;
}
