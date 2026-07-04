/**
 * useProductOverview — single source of truth for the Product Performance
 * page's overview payload.
 *
 * Wraps ``productCatalogAPI.getOverview(period)`` with sensible defaults:
 *
 *   - Manages loading / error / data state so the page itself stays
 *     free of fetch boilerplate.
 *   - Cancels stale responses when ``period`` changes mid-flight (the
 *     last requested period always wins).
 *   - Exposes ``refetch()`` so a manual ``Refresh metrics`` button can
 *     re-trigger the fetch without reloading the page.
 *   - Survives backend transient errors gracefully — returns null
 *     ``overview`` plus the error code so the page can decide whether
 *     to show empty state or an error banner.
 *
 * Contract
 * --------
 * Returns ``{ overview, loading, error, refetch }``:
 *
 *   overview — the full /overview payload (kpi envelope + abc + tops +
 *              categories) or null when there is no data yet
 *   loading  — true during the in-flight fetch
 *   error    — backend "detail" string or null
 *   refetch  — () => void, manually retrigger
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { productCatalogAPI } from '../../../api/productCatalog';


export default function useProductOverview(period) {
  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  // Bump to force re-fire of the effect (used by refetch()).
  const [refetchTick, setRefetchTick] = useState(0);
  // Token-based stale-response guard. The latest request's token is
  // captured at fire time; when the response comes back later we
  // compare it to the current token and bail out if it's stale.
  const requestToken = useRef(0);

  useEffect(() => {
    const myToken = ++requestToken.current;
    setLoading(true);
    setError(null);

    productCatalogAPI.getOverview(period)
      .then((res) => {
        if (myToken !== requestToken.current) return;
        setOverview(res?.data || null);
      })
      .catch((err) => {
        if (myToken !== requestToken.current) return;
        const detail = err?.response?.data?.detail;
        const msg = typeof detail === 'string'
          ? detail
          : (err?.message || 'unknown');
        setError(msg);
        // Distinguish "no data yet" (404 or empty body) from real errors.
        if (err?.response?.status === 404) {
          setOverview(null);
        }
      })
      .finally(() => {
        if (myToken === requestToken.current) setLoading(false);
      });
  }, [period, refetchTick]);

  const refetch = useCallback(() => {
    setRefetchTick((n) => n + 1);
  }, []);

  return { overview, loading, error, refetch };
}
