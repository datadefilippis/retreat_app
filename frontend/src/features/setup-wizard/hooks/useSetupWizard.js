/**
 * useSetupWizard — data-fetching hook for the dashboard wizard widget
 * (Fase 2 Track F — Step 6).
 *
 * Behaviour:
 *   - Mount: triggers an initial fetch immediately (loading=true at
 *     first paint).
 *   - Cache: in-memory TTL of CACHE_TTL_MS (30s). Re-fetches inside the
 *     window are no-ops unless `refresh()` is called explicitly.
 *   - Focus: window focus events trigger a soft re-fetch (respects TTL).
 *     This way coming back from a different tab refreshes the wizard
 *     when state may have changed (e.g. user just saved settings in
 *     another tab).
 *   - Unmount: outstanding requests are not cancelled (axios doesn't
 *     have a built-in abort controller in our setup), but the hook
 *     guards setState with a `mountedRef` so unmounted updates are
 *     silently dropped.
 *
 * No external state-management library (no SWR, no React Query). The
 * widget only needs ONE endpoint, refreshed at most every ~30s — a
 * 60-line custom hook is the right fit.
 *
 * Public surface:
 *
 *   const { data, loading, error, refresh } = useSetupWizard({
 *     enabled: true,           // false = don't fetch at all (e.g.
 *                              // user not authenticated yet)
 *   });
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { setupWizardAPI } from '../api/setupWizard';


// 30 seconds. Long enough to avoid hammering the API on tab-switching;
// short enough that "I just clicked save in another tab" reflects soon
// after coming back. Manual refresh() bypasses this regardless.
const CACHE_TTL_MS = 30_000;


export function useSetupWizard({ enabled = true } = {}) {
  // Reactive state
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(enabled);
  const [error, setError] = useState(null);

  // Non-reactive refs (don't trigger re-renders)
  const lastFetchAtRef = useRef(0);
  const mountedRef = useRef(true);
  const inFlightRef = useRef(false);

  /**
   * Run a fetch.
   *   force=false → respects cache TTL (skips if last fetch <30s ago)
   *   force=true  → always fetches (used by manual refresh button +
   *                 first mount)
   */
  const fetchOnce = useCallback(async (force = false) => {
    if (!enabled) return;

    // Cache TTL guard
    const now = Date.now();
    if (!force && now - lastFetchAtRef.current < CACHE_TTL_MS) {
      return;
    }

    // Prevent concurrent fetches (e.g. focus + manual refresh racing).
    if (inFlightRef.current) return;
    inFlightRef.current = true;

    lastFetchAtRef.current = now;
    setLoading(true);
    setError(null);

    try {
      const res = await setupWizardAPI.get();
      if (mountedRef.current) {
        setData(res.data || null);
        setError(null);
      }
    } catch (err) {
      if (mountedRef.current) {
        // 401/403 → user lost session. Surface as error so the widget
        // can collapse gracefully; the global axios interceptor will
        // typically redirect to login anyway.
        setError(err);
      }
    } finally {
      inFlightRef.current = false;
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, [enabled]);

  /**
   * Public refresh handler. Always bypasses the TTL cache.
   * Returned by the hook so consumer components can wire it to a
   * "refresh" button.
   */
  const refresh = useCallback(() => {
    return fetchOnce(true);
  }, [fetchOnce]);

  /**
   * Initial fetch on mount + when `enabled` flips from false to true.
   * Force=true on first run so a stale-cache state from a previous
   * mount doesn't suppress the very first load.
   */
  useEffect(() => {
    mountedRef.current = true;
    if (enabled) {
      fetchOnce(true);
    } else {
      // Disabled: blank the state so subsequent re-enable triggers a
      // fresh load instead of showing stale data.
      setData(null);
      setLoading(false);
      setError(null);
    }
    return () => {
      mountedRef.current = false;
    };
  }, [enabled, fetchOnce]);

  /**
   * Re-fetch when the window regains focus. Soft refresh (respects
   * TTL) so coming back from a 5-second tab switch doesn't burn a new
   * round-trip.
   */
  useEffect(() => {
    if (!enabled) return undefined;

    const onFocus = () => {
      // Soft fetch: skip if within TTL.
      fetchOnce(false);
    };
    const onVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        fetchOnce(false);
      }
    };

    window.addEventListener('focus', onFocus);
    document.addEventListener('visibilitychange', onVisibilityChange);
    return () => {
      window.removeEventListener('focus', onFocus);
      document.removeEventListener('visibilitychange', onVisibilityChange);
    };
  }, [enabled, fetchOnce]);

  return { data, loading, error, refresh };
}
