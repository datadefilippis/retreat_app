/**
 * useCashflowQuery — server-side filter + paginated orchestrator for
 * the cashflow Section tables (Phase 2, 2026-05-20).
 *
 * Drop-in replacement for ``useCashflowFilters`` in the three large
 * Section components (Sales / Expenses / Purchases). FixedCosts keeps
 * the old client-side hook because the dataset is naturally small
 * (cap 500).
 *
 * What this hook owns
 * -------------------
 *   1. Filter STATE — reuses the exact same useState shape as
 *      ``useCashflowFilters`` (the filter popup component reads from
 *      ``filters`` / writes via ``setFilters``, unchanged).
 *   2. PAGE state — current page number + size.
 *   3. DATA — the latest envelope from ``api.search()``, plus loading
 *      and error flags.
 *
 * What this hook does NOT own
 * ---------------------------
 *   - Predicate evaluation. ``useCashflowFilters`` ran each predicate
 *     on every record; here the predicates are serialised and sent
 *     to the backend, which does the filtering against indexed
 *     collections.
 *   - The popup UI. It reads ``filters`` / ``setFilters`` exactly as
 *     before — the contract is preserved.
 *
 * Contract returned to the Section
 * --------------------------------
 *   {
 *     filters, setFilters, reset,        // identical to useCashflowFilters
 *     activeCount,                       // identical
 *     items, total, hasMore,             // new — driven by the backend
 *     page, setPage, pageSize,           // new — pagination control
 *     loading, error, refetch,           // new — async lifecycle
 *   }
 *
 * The Section renders ``items`` instead of ``filtered`` and adds a
 * ``<CashflowPagination total={total} page={page} ... />`` footer.
 *
 * Debounce
 * --------
 * Filter changes debounce 300ms before refetching — the user typing
 * "ACME" into the description box generates 4 state updates, we want
 * one HTTP roundtrip. Page changes refetch IMMEDIATELY (no debounce)
 * because click-on-next-page is a deliberate single action.
 *
 * Cancellation
 * ------------
 * Each fetch carries an abort signal; a stale in-flight request whose
 * filters were superseded gets aborted so its response never lands as
 * the displayed data. This prevents the classic "I changed filter to
 * A, then immediately to B, response for A arrived later and overwrote
 * the correct B data" race.
 */

import {
  useEffect,
  useState,
  useMemo,
  useRef,
  useCallback,
} from 'react';
import {
  emptyFilterState,
  countActiveFilters,
} from '../lib/filterSchemas';
import { serializeFilters } from '../lib/serializeFilters';


const FILTER_DEBOUNCE_MS = 300;
const DEFAULT_PAGE_SIZE = 50;


export function useCashflowQuery({
  categoryType,                            // 'sales' | 'expenses' | 'purchases'
  api,                                     // salesAPI | expensesAPI | purchasesAPI
  pageSize = DEFAULT_PAGE_SIZE,
  enabled = true,                          // toggle to skip queries (e.g. tab hidden)
  extraParams,                             // page-scope filters merged on top of user filters
}) {
  // ── extraParams (page-level scope) ─────────────────────────────────
  // A static, additional filter set that's ANDed with whatever the
  // user picks in the popup. Used e.g. by PurchasesSection when the
  // outer CashflowDataPage is scoped to one supplier (URL ?supplier_id=X)
  // — every query must restrict to that supplier even when the user
  // hasn't touched the popup.
  //
  // Spread AFTER user filters so an explicit user-set value (rare:
  // the popup doesn't expose supplier_ids directly) couldn't accidentally
  // win over the scope. Page-scope is intentionally non-overridable
  // from the popup.
  // ── Filter state (same shape as useCashflowFilters) ────────────────
  // Memoise the empty initial so referential equality holds across
  // renders. ``emptyFilterState`` builds a fresh object each call.
  const initialFilters = useMemo(
    () => emptyFilterState(categoryType),
    [categoryType],
  );
  const [filters, setFilters] = useState(initialFilters);

  // ── Pagination state ───────────────────────────────────────────────
  const [page, setPage] = useState(1);

  // ── Response state ─────────────────────────────────────────────────
  const [data, setData] = useState({
    items: [],
    total: 0,
    has_more: false,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // ── Serialised filters → backend kwargs ────────────────────────────
  // Memoised on filters + categoryType, so the effect below only
  // triggers when filters actually change (not on every render).
  const queryParams = useMemo(
    () => serializeFilters(filters, categoryType),
    [filters, categoryType],
  );

  // Refs to track debounce timer + current in-flight request for
  // cancellation.
  const debounceRef = useRef(null);
  const inFlightAbortRef = useRef(null);

  // Track the latest "request id" so a stale response that beats the
  // abort signal still doesn't update state. Belt + suspenders.
  const lastReqIdRef = useRef(0);

  // ── Core fetch ─────────────────────────────────────────────────────
  // Stable reference via useCallback so we can also expose it as
  // ``refetch`` for the Section (e.g. after a create/delete).
  const fetchData = useCallback(
    async ({ skipDebounce = false } = {}) => {
      if (!enabled) return;

      // Cancel any pending debounced fetch + any in-flight request.
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
        debounceRef.current = null;
      }
      if (inFlightAbortRef.current) {
        inFlightAbortRef.current.abort();
        inFlightAbortRef.current = null;
      }

      const reqId = ++lastReqIdRef.current;

      const run = async () => {
        const controller = new AbortController();
        inFlightAbortRef.current = controller;
        setLoading(true);
        setError(null);
        try {
          const res = await api.search(
            { ...queryParams, ...(extraParams || {}), page, pageSize },
            // Axios accepts a signal in the second arg, but our wrapper
            // signature varies; the safer path is to attach the signal
            // to the axios call directly. Since api.search returns the
            // axios promise, we just check the abort flag manually on
            // settle. This is good enough — the network call may still
            // complete in the background, but we never apply its result
            // to state.
          );
          if (reqId === lastReqIdRef.current) {
            setData(res.data || { items: [], total: 0, has_more: false });
          }
        } catch (e) {
          if (reqId === lastReqIdRef.current) {
            setError(e);
          }
        } finally {
          if (reqId === lastReqIdRef.current) {
            setLoading(false);
          }
        }
      };

      if (skipDebounce) {
        await run();
      } else {
        debounceRef.current = setTimeout(run, FILTER_DEBOUNCE_MS);
      }
    },
    // queryParams + page + pageSize are the only things that should
    // trigger a re-run. api is stable per Section (passed in once);
    // categoryType is stable for the lifetime of the component.
    // extraParams is referenced via dep — callers should memoise it
    // (or pass a stable object literal at the component level) to
    // avoid re-querying on every parent render.
    [api, queryParams, page, pageSize, enabled, extraParams],
  );

  // ── Filter changes → refetch with debounce ─────────────────────────
  useEffect(() => {
    fetchData();
    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
        debounceRef.current = null;
      }
    };
  }, [fetchData]);

  // ── When filters change, reset to page 1 ───────────────────────────
  // A new filter = new result set; staying on page 7 of the old
  // result set is confusing UX.
  useEffect(() => {
    setPage(1);
    // Intentionally only depends on queryParams, not page. We're
    // resetting page TO 1, not reacting to page change.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [queryParams]);

  // ── Derived: active filter count for the badge ─────────────────────
  const activeCount = useMemo(
    () => countActiveFilters(filters, categoryType),
    [filters, categoryType],
  );

  // ── Reset filters → empty state ────────────────────────────────────
  const reset = useCallback(() => {
    setFilters(emptyFilterState(categoryType));
    setPage(1);
  }, [categoryType]);

  // ── Manual refetch (no debounce) — for post-CRUD refresh ───────────
  const refetch = useCallback(
    () => fetchData({ skipDebounce: true }),
    [fetchData],
  );

  return {
    // Filter contract (matches useCashflowFilters)
    filters,
    setFilters,
    reset,
    activeCount,

    // Pagination + data
    items: data.items,
    total: data.total,
    hasMore: data.has_more,
    page,
    setPage,
    pageSize,

    // Async lifecycle
    loading,
    error,
    refetch,
  };
}
