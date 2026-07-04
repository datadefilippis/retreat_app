/**
 * StoreMetaContext — single source of truth for public store metadata.
 *
 * Architectural intent
 * --------------------
 * Every public storefront surface (catalog `/s/:slug` + 12 landings) needs
 * to know two things BEFORE it can render correctly:
 *
 *   1. `storefrontLanguages` — drives the language resolver chain
 *      (browser ∩ allowed, customer.locale ∩ allowed, store default, …).
 *      Without this, the resolver collapses to FALLBACK_LOCALE='it' and
 *      the user sees an Italian flicker even on a German-only store.
 *
 *   2. `storeInfo` — branded header (logo, colors) so the landing pages
 *      can paint themselves consistently with the catalog.
 *
 * Before this context, only the catalog endpoint exposed those fields.
 * The 12 landing endpoints had to either fetch them themselves (network
 * waste) or render without them (UX inconsistency). This provider
 * fetches `/api/public/storefront/{slug}/meta` ONCE per slug per session,
 * caches in memory + localStorage with a 1-hour TTL, and broadcasts to
 * every descendant via the context API.
 *
 * Lifecycle
 * ---------
 *   slug=null         → status='idle', no fetch (safe to mount on
 *                       non-storefront routes; provider just no-ops)
 *   slug provided     → check localStorage cache:
 *                         hit + fresh → hydrate inline, status='ready'
 *                         miss/stale  → status='loading', fetch /meta
 *                       on response   → status='ready', persist cache
 *                       on error      → status='error', keep last data
 *   slug changes      → re-run the same path with the new key
 *
 * Strict-mode safety: an AbortController cancels in-flight requests when
 * the provider unmounts or the slug changes mid-flight, so React 18
 * double-mount under StrictMode doesn't fire a duplicate /meta request
 * (or worse, race two responses into the same state).
 *
 * Failure mode is never blocking. If `/meta` returns a 5xx or the cache
 * is corrupted, the provider exposes the last-known-good data (or a
 * `null` state). Consumers must handle the `idle`/`loading` window
 * gracefully — see `useStoreMeta` for the canonical accessor.
 */

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from 'react';
import { storefrontAPI } from '../api/storefront';


// ── Cache layer (localStorage) ────────────────────────────────────────────

// Bumped when the on-disk schema changes incompatibly. Old entries with
// a different version key are silently ignored on read so the next /meta
// fetch repopulates them in the new shape.
const CACHE_VERSION = 1;
// Hard TTL — beyond this the cache is treated as missing. The actual
// in-session freshness is much tighter thanks to the stale-while-
// revalidate pattern below: every Provider mount triggers a background
// refresh, so an admin who flips a store language sees the change on
// the storefront within one round-trip (~50ms) regardless of the TTL.
// The TTL is just a safety net for offline / closed-tab scenarios.
const CACHE_TTL_MS = 5 * 60 * 1000;   // 5 minutes
const CACHE_KEY_PREFIX = 'storefront_meta_';


function _cacheKey(slug) {
  return slug ? `${CACHE_KEY_PREFIX}${slug}` : null;
}


/**
 * Read the cached `/meta` payload for a slug. Returns null when:
 *   - slug is missing
 *   - localStorage is unavailable (Safari private mode, server-side render)
 *   - the entry doesn't exist
 *   - the entry is older than CACHE_TTL_MS
 *   - the entry was written by a different cache version
 *   - the JSON is corrupted
 *
 * Pure read — no side effects.
 */
function readCachedMeta(slug) {
  const key = _cacheKey(slug);
  if (!key || typeof localStorage === 'undefined') return null;
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (
      !parsed
      || parsed.version !== CACHE_VERSION
      || typeof parsed.fetched_at !== 'number'
      || !parsed.data
    ) return null;
    if (Date.now() - parsed.fetched_at > CACHE_TTL_MS) return null;
    return parsed.data;
  } catch {
    return null;
  }
}


/**
 * Persist a `/meta` payload to localStorage. Failures (full quota, private
 * mode) are swallowed — caching is a perf optimization, not a correctness
 * boundary, so a write failure doesn't break the runtime.
 */
function writeCachedMeta(slug, data) {
  const key = _cacheKey(slug);
  if (!key || typeof localStorage === 'undefined') return;
  try {
    localStorage.setItem(
      key,
      JSON.stringify({ version: CACHE_VERSION, fetched_at: Date.now(), data }),
    );
  } catch {
    // localStorage may be full or unavailable; ignore.
  }
}


// ── Context shape ────────────────────────────────────────────────────────

/**
 * Default value used when the provider is absent (defensive — components
 * outside the storefront tree won't crash if they accidentally call
 * `useStoreMeta`). Status='idle' tells consumers there's nothing to wait
 * for: render a generic shell or skip locale-aware bits.
 */
const DEFAULT_VALUE = {
  slug: null,
  orgName: null,
  storefrontLanguages: null,    // null = unknown (NOT same as []!)
  storeInfo: null,
  status: 'idle',               // 'idle' | 'loading' | 'ready' | 'error'
  error: null,
  // Imperative refresh — for future use (e.g. an admin-edit broadcast).
  refresh: () => {},
};


export const StoreMetaContext = createContext(DEFAULT_VALUE);


// ── Provider ─────────────────────────────────────────────────────────────

/**
 * Mount this above any public storefront surface that wants automatic
 * language + branding resolution. Slug should come from the URL params
 * (`useParams().slug` for /s/:slug, `useParams().org_slug` for the 12
 * landings). Pass null/undefined to render children without fetching
 * (safe).
 *
 * Children re-render when status transitions or data refreshes — the
 * context value is memoized only by reference equality of the state
 * object, which is stable between transitions of the same status.
 */
export function StoreMetaProvider({ slug, children }) {
  const [state, setState] = useState(() => {
    // Synchronous cache hydration on first render — no flash for
    // returning visitors. If the cache is empty/stale, we fall through
    // to the loading effect below.
    const cached = readCachedMeta(slug);
    if (cached) {
      return {
        slug,
        orgName: cached.org_name || null,
        storefrontLanguages: Array.isArray(cached.storefront_languages)
          ? cached.storefront_languages : null,
        storeInfo: cached.store_info || null,
        // v5.8 / Onda 4 — `checkout_stripe_enabled` from /meta payload.
        // Default true so the storefront CTA stays "Acquista" even when
        // the field is missing (legacy caches, older API responses).
        checkoutStripeEnabled: cached.checkout_stripe_enabled !== false,
        status: 'ready',
        error: null,
      };
    }
    return {
      slug,
      orgName: null,
      storefrontLanguages: null,
      storeInfo: null,
      checkoutStripeEnabled: true,
      status: slug ? 'loading' : 'idle',
      error: null,
    };
  });

  // Track the in-flight slug separately so we can compare incoming
  // responses against the current slug — guards against late responses
  // mutating state for a stale slug (e.g. user navigated away mid-fetch).
  const inFlightSlugRef = useRef(null);

  const fetchMeta = useCallback(async (targetSlug, abortSignal) => {
    if (!targetSlug) return;
    inFlightSlugRef.current = targetSlug;
    try {
      // Pass the abort signal so axios actually cancels the underlying
      // request (not just ignores the late response). Cuts wasted
      // bandwidth on rapid slug changes.
      const res = await storefrontAPI.getStorefrontMeta(targetSlug, {
        signal: abortSignal,
      });
      // Belt + braces: even with `signal`, defensively skip the state
      // update if the slug changed or the controller fired before
      // network completion.
      if (abortSignal?.aborted) return;
      if (inFlightSlugRef.current !== targetSlug) return;
      const data = res.data || {};
      writeCachedMeta(targetSlug, data);
      // Functional update so we can compare with the current state
      // and skip the re-render when nothing changed (cache was already
      // up-to-date). This is what makes stale-while-revalidate cheap:
      // the background fetch confirms the cache, no React work happens.
      setState((prev) => {
        const nextLangs = Array.isArray(data.storefront_languages)
          ? data.storefront_languages : null;
        const sameLangs = (
          prev.status === 'ready'
          && Array.isArray(prev.storefrontLanguages)
          && Array.isArray(nextLangs)
          && prev.storefrontLanguages.length === nextLangs.length
          && prev.storefrontLanguages.every((l, i) => l === nextLangs[i])
        );
        const sameOrg = prev.orgName === (data.org_name || null);
        const sameStoreInfo = JSON.stringify(prev.storeInfo) === JSON.stringify(data.store_info || null);
        // v5.8 / Onda 4 — track checkout_stripe_enabled flag changes so the
        // storefront CTA flips dynamically when the merchant upgrades plan.
        const nextCheckoutStripe = data.checkout_stripe_enabled !== false;
        const sameCheckoutStripe = prev.checkoutStripeEnabled === nextCheckoutStripe;
        if (sameLangs && sameOrg && sameStoreInfo && sameCheckoutStripe && prev.status === 'ready' && !prev.error) {
          // Nothing changed — return SAME reference to skip re-render.
          return prev;
        }
        return {
          slug: targetSlug,
          orgName: data.org_name || null,
          storefrontLanguages: nextLangs,
          storeInfo: data.store_info || null,
          checkoutStripeEnabled: nextCheckoutStripe,
          status: 'ready',
          error: null,
        };
      });
    } catch (err) {
      if (abortSignal?.aborted) return;
      if (inFlightSlugRef.current !== targetSlug) return;
      setState((prev) => ({
        ...prev,
        slug: targetSlug,
        // Only flip to 'error' if we don't already have data — a
        // transient 5xx during a stale-while-revalidate refresh
        // shouldn't wipe a known-good cache hit.
        status: prev.status === 'ready' ? 'ready' : 'error',
        error: err?.response?.status
          ? { kind: 'http', status: err.response.status }
          : { kind: 'network' },
      }));
    }
  }, []);

  /* Sync state.slug with the prop, hydrate from cache, and ALWAYS
   * background-refresh from the server (stale-while-revalidate).
   *
   * This pattern is the answer to: "I just changed the store language
   * in admin but the storefront still shows the old one." The cache
   * gives instant first-paint, while the background fetch corrects
   * any drift within ~50ms. The user never sees stale data for more
   * than one render after a server-side change. */
  useEffect(() => {
    if (!slug) {
      setState({
        slug: null,
        orgName: null,
        storefrontLanguages: null,
        storeInfo: null,
        status: 'idle',
        error: null,
      });
      return;
    }

    // Step 1: synchronous cache hydration (no flicker for returners).
    const cached = readCachedMeta(slug);
    if (cached) {
      setState({
        slug,
        orgName: cached.org_name || null,
        storefrontLanguages: Array.isArray(cached.storefront_languages)
          ? cached.storefront_languages : null,
        storeInfo: cached.store_info || null,
        checkoutStripeEnabled: cached.checkout_stripe_enabled !== false,
        status: 'ready',
        error: null,
      });
    } else {
      // Cache miss → show loading explicitly so consumers can render
      // a skeleton until the response arrives.
      setState({
        slug,
        orgName: null,
        storefrontLanguages: null,
        storeInfo: null,
        checkoutStripeEnabled: true,
        status: 'loading',
        error: null,
      });
    }

    // Step 2: ALWAYS fire a background refresh (regardless of cache
    // hit). The fetchMeta callback only re-renders when the response
    // shape genuinely differs from the current state — see the
    // shallow comparison inside fetchMeta. This is the SWR contract:
    // serve cache, validate against truth.
    const controller = new AbortController();
    fetchMeta(slug, controller.signal);
    return () => {
      controller.abort();
      inFlightSlugRef.current = null;
    };
  }, [slug, fetchMeta]);

  /* Manual refresh — bypasses the cache. Useful for admin-driven
   * invalidation flows (e.g. "Just changed the store language? Reload
   * meta now.") which we don't yet have but are inexpensive to expose. */
  const refresh = useCallback(() => {
    if (!state.slug) return;
    const controller = new AbortController();
    fetchMeta(state.slug, controller.signal);
    return () => controller.abort();
  }, [state.slug, fetchMeta]);

  const value = { ...state, refresh };
  return (
    <StoreMetaContext.Provider value={value}>
      {children}
    </StoreMetaContext.Provider>
  );
}


// ── Accessor (re-exported via hooks/useStoreMeta for ergonomic imports) ──

export function useStoreMetaContext() {
  return useContext(StoreMetaContext);
}
