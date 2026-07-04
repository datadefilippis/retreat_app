/**
 * useCostCategories — fetches the list of purchase categories an
 * organisation has actually used, for use in the cost-source editor's
 * dropdown.
 *
 * Why a dedicated hook
 * --------------------
 * The CostSourceEditor needs the same data in two component types
 * (category_quantity AND category_share) AND from the dashboard edit
 * forms (5 dashboards). Centralising the fetch here:
 *   - eliminates 7 duplicate axios calls
 *   - puts loading/error handling in one place
 *   - makes mocking trivial in tests
 *   - keeps the editor itself focused on rendering
 *
 * Terminology note (W1 consolidation)
 * -----------------------------------
 * In AFianco the field that the merchant fills in as "Prodotto" in the
 * Acquisti module is stored as ``purchase_records.category`` in the
 * database. The endpoint /modules/product-catalog/cost-categories
 * therefore returns the distinct values of that same column. For UX
 * consistency the CostSourceEditor labels this dropdown "Prodotto"
 * (matching what the merchant typed during purchase entry) — even
 * though internally it carries the technical name "category".
 *
 * Contract
 * --------
 * Returns ``{ options, byName, loading, error, refetch }``:
 *
 *   options — Array<{ name, units, unit_details, purchase_count,
 *                     total_spent, last_seen }>
 *             Pre-sorted server-side by purchase_count desc. Empty array
 *             on error (graceful degradation: the CreatableAutocomplete
 *             still accepts free-text input).
 *
 *             ``unit_details`` is the authoritative shape (added in the
 *             Wave 1 UX consolidation): each entry is
 *               { unit, purchase_count, avg_unit_price, total_spent }
 *             sorted by purchase_count desc, so the first element is the
 *             "most-used" unit for the item.
 *
 *   byName  — Map<string, option> keyed on category name for O(1) lookup
 *             when the editor needs the full envelope for the currently
 *             selected category (e.g. to surface the avg price). Built
 *             once per fetch so consumers don't re-do it on every render.
 *
 *   loading — true during the in-flight fetch
 *   error   — error object if the request failed, else null
 *   refetch — () => void, manually trigger a refetch (e.g. after the
 *             merchant adds a new purchase record while the editor is open)
 *
 * Caching
 * -------
 * The hook holds a per-instance cache only. Each consuming component
 * instance triggers its own fetch on mount. If the same dialog mounts
 * the editor twice (rare), we'll fetch twice — acceptable: the endpoint
 * is cheap (one aggregation, indexed) and the alternative (a global
 * store) would be premature optimisation for this volume.
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import { productCatalogAPI } from '../../../api/productCatalog';


export default function useCostCategories() {
  const [options, setOptions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  // Refetch counter — bumping it triggers the useEffect below to
  // re-fire. Simpler and more predictable than passing an async
  // function around.
  const [refetchTick, setRefetchTick] = useState(0);

  // O(1) name→option lookup. Rebuilt only when options change.
  const byName = useMemo(() => {
    const m = new Map();
    for (const opt of (options || [])) {
      if (opt && opt.name) m.set(opt.name, opt);
    }
    return m;
  }, [options]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    productCatalogAPI.getCostCategories()
      .then((res) => {
        if (cancelled) return;
        // Defensive: the API contract is { categories: [...] } but a
        // future schema change could shift this. We accept both
        // { categories } and a bare array so the editor doesn't crash
        // on a backend update lag.
        const raw = res?.data?.categories ?? res?.data ?? [];
        setOptions(Array.isArray(raw) ? raw : []);
      })
      .catch((err) => {
        if (cancelled) return;
        // Graceful degradation: log so the developer sees the issue
        // in dev tools but the UI keeps working (free-text fallback).
        // eslint-disable-next-line no-console
        console.warn('[useCostCategories] fetch failed:', err);
        setError(err);
        setOptions([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [refetchTick]);

  const refetch = useCallback(() => {
    setRefetchTick((n) => n + 1);
  }, []);

  return { options, byName, loading, error, refetch };
}
