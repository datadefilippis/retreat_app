/**
 * apiErrorFormatting — shared utilities for turning backend error
 * payloads into something safe to render in a toast or alert.
 *
 * 2026-05-20 — Added after a production bug surfaced in PhysicalWizard:
 *
 *   > Error: Objects are not valid as a React child (found: object
 *   > with keys {type, loc, msg, input, ctx, url})
 *
 * The keys are the canonical Pydantic v2 / FastAPI 422 ValidationError
 * shape. When a request body fails server-side validation, FastAPI
 * returns ``{"detail": [{"type": ..., "loc": [...], "msg": "...",
 * "input": ..., "ctx": {...}, "url": "..."}, ...]}`` — an ARRAY of
 * objects. Call sites that do ``toast.error(err.response.data.detail
 * || fallback)`` then pass an array of objects to sonner, which
 * eventually hands it to React as children → React explodes.
 *
 * The audit found ~66 call sites doing this raw pattern. Rather than
 * touch every one, we centralise the fix in two places that ALL paths
 * eventually flow through:
 *
 *   · smartToastInit.js — global monkey-patch of toast.error
 *   · utils/handleApiError.js — central catch helper
 *
 * Both import the helpers below.
 */


/**
 * Heuristic: is ``payload`` a Pydantic v2 ValidationError list?
 *
 * Returns true iff payload is a non-empty array whose first element
 * looks like ``{msg, type|loc, ...}``. We sample only the first item
 * for speed — Pydantic always emits a homogeneous list, so a mismatch
 * here means the caller passed something unrelated and we should leave
 * it alone.
 */
export function isPydanticErrorArray(payload) {
  if (!Array.isArray(payload) || payload.length === 0) return false;
  const first = payload[0];
  if (first == null || typeof first !== 'object') return false;
  // ``msg`` is the canonical human-readable string in v2.
  if (typeof first.msg !== 'string') return false;
  // Either ``type`` (string) or ``loc`` (array) is present in v2 —
  // belt-and-braces against future Pydantic minor revisions.
  return typeof first.type === 'string' || Array.isArray(first.loc);
}


/**
 * Format a Pydantic v2 ValidationError list as a single human-readable
 * string suitable for a toast.
 *
 * Format: ``field.path: msg · field.path: msg (+N altri)``
 *
 * Design choices:
 *   · Drop the leading "body"/"query"/"path" segment from ``loc`` —
 *     FastAPI prepends it for request-body validation but it's noise
 *     for end users (they don't think "body.name", they think "name").
 *   · Cap at 3 errors in the toast — beyond that the toast becomes
 *     unreadable; the "(+N altri)" hint tells the user there are more.
 *   · Join with " · " not ", " — the dot-separator reads better with
 *     dotted field paths.
 */
export function formatPydanticErrors(errors) {
  if (!Array.isArray(errors) || errors.length === 0) return '';
  const MAX_SHOWN = 3;
  const lines = errors.slice(0, MAX_SHOWN).map((e) => {
    const rawLoc = Array.isArray(e?.loc) ? e.loc : [];
    // Strip the request-section prefix that FastAPI adds.
    const dropFirst = rawLoc[0] === 'body'
      || rawLoc[0] === 'query'
      || rawLoc[0] === 'path'
      || rawLoc[0] === 'header'
      || rawLoc[0] === 'cookie';
    const cleanLoc = dropFirst ? rawLoc.slice(1) : rawLoc;
    // Coerce loc segments to strings (some are numeric for array indices).
    const field = cleanLoc.map((x) => String(x)).join('.');
    const msg = typeof e?.msg === 'string' ? e.msg : 'Invalid value';
    return field ? `${field}: ${msg}` : msg;
  });
  const remainder = errors.length - MAX_SHOWN;
  const suffix = remainder > 0 ? ` (+${remainder} altri)` : '';
  return lines.join(' · ') + suffix;
}


/**
 * Last-resort coercion: turn anything safely into a string for a toast.
 *
 * Used as the fallback when none of the structured branches match
 * (e.g. a caller passed a raw object that isn't a Pydantic error list
 * and isn't a billing dict). Without this, a stray object would land
 * in React children as "[object Object]" or worse.
 *
 * Returns the empty string for null/undefined so the caller can decide
 * whether to substitute a fallback.
 */
export function coerceToToastString(value) {
  if (value == null) return '';
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }
  // For arrays of strings, join — covers `detail: ["msg1", "msg2"]`.
  if (Array.isArray(value) && value.every((v) => typeof v === 'string')) {
    return value.join(' · ');
  }
  // Last resort: try to extract a sensible field from an object,
  // otherwise JSON.stringify (capped to avoid a wall-of-text toast).
  if (typeof value === 'object') {
    if (typeof value.message === 'string') return value.message;
    if (typeof value.error === 'string') return value.error;
    if (typeof value.detail === 'string') return value.detail;
    try {
      const json = JSON.stringify(value);
      return json.length > 200 ? json.slice(0, 197) + '…' : json;
    } catch {
      return '';
    }
  }
  return '';
}
