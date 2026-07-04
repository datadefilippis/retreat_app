/**
 * useCartStorage — sessionStorage persistence for the storefront cart.
 *
 * Problem it solves: StorefrontPage remounts when the URL route pattern
 * changes (/s/:slug ↔ /ph/:slug/:product_slug etc.), wiping all 10 cart
 * state objects that are held in `useState`. Without persistence, a
 * customer who adds Product A inline and then opens Product B's landing
 * returns to find their cart empty — making multi-product orders
 * effectively impossible from the storefront entry point.
 *
 * Design choices:
 *   - sessionStorage, not localStorage → dies with the tab, respects the
 *     merchant's existing "cart is ephemeral per session" contract while
 *     surviving React Router remounts and accidental F5.
 *   - Per-store slug key → each storefront keeps its own bag; navigating
 *     to a different org does not leak items into an incompatible context.
 *   - TTL guard (24h) → belt-and-suspenders against edge-case browsers
 *     that keep sessionStorage alive across tab close (some macOS Safari
 *     states) and against corrupted clocks.
 *   - Pure functions, not a React hook → testable without mounting a
 *     component, reusable by `useCartCount` which needs polling semantics
 *     rather than subscription.
 *
 * JSON-serializable invariant: the 10 snapshot slices are all plain
 * dicts/arrays (no Date, Map, Set). Existing StorefrontPage state
 * satisfies this — if a future slice adds non-serializable content,
 * sanitize before calling `persistCart`.
 */


// Prefix keeps the cart namespace separate from any other sessionStorage
// use (auth tokens, ephemeral UI flags) so a bad actor overwriting
// sessionStorage wouldn't silently poison the cart.
const KEY_PREFIX = 'storefront:cart:';

// Snapshots older than this are discarded on hydrate to avoid reviving
// stale carts. 24h is arbitrary but comfortable: covers overnight-tab
// sessions without becoming a permanent ghost.
const MAX_AGE_MS = 24 * 60 * 60 * 1000;


function _key(slug) {
  if (!slug) return null;
  return `${KEY_PREFIX}${slug}`;
}


function _safeParse(raw) {
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object') return null;
    return parsed;
  } catch {
    return null;
  }
}


/**
 * Load a previously-saved cart snapshot for the given store slug.
 * Returns null when nothing is stored, the stored value is corrupted, or
 * the saved snapshot is older than MAX_AGE_MS.
 */
export function hydrateCart(slug) {
  const key = _key(slug);
  if (!key) return null;
  try {
    const raw = window.sessionStorage.getItem(key);
    const parsed = _safeParse(raw);
    if (!parsed) return null;
    // TTL check — absence of savedAt is treated as fresh (back-compat
    // with any snapshot written by an earlier version).
    if (parsed.savedAt) {
      const saved = Date.parse(parsed.savedAt);
      if (!Number.isNaN(saved) && Date.now() - saved > MAX_AGE_MS) {
        // Clear the stale row so the tab doesn't keep paying the read
        // cost each remount.
        try { window.sessionStorage.removeItem(key); } catch { /* ignore */ }
        return null;
      }
    }
    return parsed.state || null;
  } catch {
    // Private browsing modes throw on getItem — treat as "no cart".
    return null;
  }
}


/**
 * Save the 10 cart slices for the given store slug.
 * `state` is the merged dict of all cart useState values. No-ops when
 * slug is missing or sessionStorage is unavailable.
 */
export function persistCart(slug, state) {
  const key = _key(slug);
  if (!key || !state) return;
  try {
    const payload = JSON.stringify({
      savedAt: new Date().toISOString(),
      state,
    });
    window.sessionStorage.setItem(key, payload);
  } catch {
    // QuotaExceededError or private-mode write block — silently ignore,
    // the in-memory cart still works, we just lose the tab-survival
    // property for this session. Better than crashing the checkout.
  }
}


/**
 * Remove any persisted snapshot for this slug. Called after a successful
 * order submission (so a fresh visit starts clean) and whenever the cart
 * returns to a fully-empty state (so we don't store `{quantities: {}, …}`
 * forever).
 */
export function clearCart(slug) {
  const key = _key(slug);
  if (!key) return;
  try {
    window.sessionStorage.removeItem(key);
  } catch {
    // ignore
  }
}


/**
 * Return the total number of items currently saved for a slug. Sums the
 * values of `quantities` (the authoritative count per product) — this
 * matches how OrderSummary + the storefront header already compute the
 * cart badge on the catalog page.
 *
 * Returns 0 for missing / corrupted / expired snapshots (consistent with
 * hydrateCart).
 */
export function readCartCount(slug) {
  const snap = hydrateCart(slug);
  if (!snap || !snap.quantities) return 0;
  let total = 0;
  for (const v of Object.values(snap.quantities)) {
    const n = Number(v);
    if (Number.isFinite(n) && n > 0) total += n;
  }
  return total;
}
