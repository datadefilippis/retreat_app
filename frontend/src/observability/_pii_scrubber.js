/**
 * PII scrubbing for Sentry events (frontend).
 *
 * Strategy (4-layer defense, mirrors backend/core/observability/_pii_scrubber.py):
 *     - Sensitive field NAMES   → values redacted recursively in event tree
 *     - Sensitive HTTP HEADERS  → redacted in request.headers section
 *     - Free-text strings       → emails/JWT/Bearer tokens masked
 *     - Keyword-value pairs     → "password was X" / "token=Y" / "secret: Z"
 *
 * Internal module (underscore prefix) — only used by sentry.js.
 * Extension: add patterns to PII_FIELDS / PII_HEADERS as needed.
 */

// Field names whose VALUES must be redacted (case-insensitive substring match)
const PII_FIELDS = new Set([
  "password", "passwd", "pwd",
  "token", "api_key", "apikey", "secret",
  "authorization", "auth",
  "card_number", "cardnumber", "cvc", "cvv",
  "iban", "ssn", "tax_id", "fiscal_code", "codice_fiscale",
  "session_id", "session", "cookie",
  "private_key", "client_secret",
]);

// HTTP header names to redact (case-insensitive, exact match)
const PII_HEADERS = new Set([
  "authorization", "cookie", "set-cookie",
  "x-api-key", "x-auth-token", "x-csrf-token",
]);

// Regex patterns for free-text masking.
// `g` flag is essential — without it, .replace only swaps the first match.
const EMAIL_PATTERN = /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g;
const BEARER_PATTERN = /Bearer\s+[A-Za-z0-9._-]+/gi;
const JWT_PATTERN = /eyJ[A-Za-z0-9_=-]+\.[A-Za-z0-9_=-]+\.[A-Za-z0-9_.+/=-]+/g;
// Inline keyword-value: "password was X", "secret=Y", "token: Z"
const KEYWORD_VALUE_PATTERN =
  /\b(password|passwd|pwd|secret|token|api[\s_-]?key|auth)\b\s*(?:was|is|=|:)\s*([^\s.,;]+)/gi;

const REDACTED = "[Filtered]";

function isPiiKey(key) {
  if (typeof key !== "string") return false;
  const lower = key.toLowerCase();
  for (const pii of PII_FIELDS) {
    if (lower.includes(pii)) return true;
  }
  return false;
}

function isPiiHeader(key) {
  return typeof key === "string" && PII_HEADERS.has(key.toLowerCase());
}

function maskText(text) {
  if (typeof text !== "string") return text;
  return text
    .replace(EMAIL_PATTERN, REDACTED)
    .replace(BEARER_PATTERN, `Bearer ${REDACTED}`)
    .replace(JWT_PATTERN, REDACTED)
    .replace(KEYWORD_VALUE_PATTERN, `$1 ${REDACTED}`);
}

/**
 * Recursively walk an event/breadcrumb tree and redact sensitive values.
 *
 * @param {*} obj - Any value (object, array, primitive)
 * @param {boolean} inHeaders - true when traversing an HTTP headers dict
 *                               (different rules apply: header-name match)
 */
function scrubRecursive(obj, inHeaders = false) {
  if (obj === null || obj === undefined) return obj;
  if (Array.isArray(obj)) {
    return obj.map((item) => scrubRecursive(item, inHeaders));
  }
  if (typeof obj === "object") {
    const result = {};
    for (const [k, v] of Object.entries(obj)) {
      const recurseInHeaders =
        inHeaders ||
        (typeof k === "string" &&
          (k.toLowerCase() === "headers" || k.toLowerCase() === "request_headers"));
      if ((inHeaders && isPiiHeader(k)) || (!inHeaders && isPiiKey(k))) {
        result[k] = REDACTED;
      } else {
        result[k] = scrubRecursive(v, recurseInHeaders);
      }
    }
    return result;
  }
  if (typeof obj === "string") {
    return maskText(obj);
  }
  return obj;
}

/**
 * Sentry beforeSend hook. Returns scrubbed event, or null to drop entirely.
 * Errors during scrubbing fall through to dropping (better than send PII unmasked).
 */
export function scrubEvent(event, _hint) {
  try {
    return scrubRecursive(event);
  } catch (_e) {
    return null;
  }
}

/**
 * Sentry beforeBreadcrumb hook. Same scrubbing logic as events.
 */
export function scrubBreadcrumb(crumb, _hint) {
  try {
    return scrubRecursive(crumb);
  } catch (_e) {
    return null;
  }
}

// Export helpers for unit testing (do NOT use from app code).
export const __testing = {
  maskText,
  scrubRecursive,
  isPiiKey,
  isPiiHeader,
  PII_FIELDS,
  PII_HEADERS,
};
