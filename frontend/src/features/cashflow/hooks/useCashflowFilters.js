/**
 * useCashflowFilters — stateful filter engine for the cashflow record
 * tables (sales / expenses / purchases / fixed_costs).
 *
 * Contract
 * --------
 *   const { filters, setFilters, filtered, activeCount, reset } =
 *     useCashflowFilters({ records, categoryType });
 *
 *   filters       Current filter state, shape driven by filterSchemas.
 *   setFilters    State setter (accepts object or updater function).
 *   filtered      Memoised array — `records` minus rows the filters
 *                 exclude. Returns the same reference between renders
 *                 when neither `records` nor `filters` changed, so
 *                 downstream slice() / map() can rely on shallow eq.
 *   activeCount   Number of constraining filter fields (drives the
 *                 badge on the trigger button).
 *   reset         Clears every filter back to empty state.
 *
 * Filter semantics
 * ----------------
 * Every populated field is ANDed together — a record must pass ALL
 * active constraints to make it into `filtered`. Within a multi-select,
 * the values are ORed (a record passes if its column matches ANY of
 * the selected options). This matches the merchant's mental model:
 * "show me invoices from these 3 suppliers" (OR within), AND "paid in
 * January" (AND across).
 *
 * Filtering is client-side (PR plan v1). Records are already loaded in
 * full by the sections' .list() calls (default 500, max 5000). For
 * orgs that grow past that limit a follow-up will surface server-side
 * filtering on the same SCHEMAS — the popup + hook stay unchanged
 * because the parent simply switches who computes `filtered`.
 */

import { useState, useMemo, useCallback } from 'react';
import { SCHEMAS, emptyFilterState, countActiveFilters } from '../lib/filterSchemas';


// ── Per-field predicate factories ──────────────────────────────────────
//
// Each factory inspects the current filter state for one schema entry
// and returns either `null` (this field is not constraining anything)
// or a predicate `(record) => boolean`. The orchestrator below ANDs all
// non-null predicates.

function dateRangePredicate(field, state) {
  const from = state[field.key + '_from'];
  const to = state[field.key + '_to'];
  if (!from && !to) return null;
  // Compare on the raw ISO string (yyyy-mm-dd) — lexicographic order
  // matches chronological order, so we skip the Date() detour. This is
  // also robust to records whose .date is itself a string in the same
  // format (the common case for the cashflow records).
  return (r) => {
    const v = r[field.key];
    if (!v) return false;
    // Normalise to yyyy-mm-dd (records may contain ISO timestamps).
    const dv = String(v).slice(0, 10);
    if (from && dv < from) return false;
    if (to && dv > to) return false;
    return true;
  };
}

function numberRangePredicate(field, state) {
  const minRaw = state[field.key + '_min'];
  const maxRaw = state[field.key + '_max'];
  const min = minRaw !== '' && minRaw != null ? Number(minRaw) : null;
  const max = maxRaw !== '' && maxRaw != null ? Number(maxRaw) : null;
  if (min == null && max == null) return null;
  // Special-case purchases.quantity * unit_price → "total" — the schema
  // exposes per-column ranges so we don't need that here; we just read
  // the raw record field. Records always store unit_price / quantity /
  // amount as numbers (verified from the *EntryForm save handlers).
  return (r) => {
    const v = Number(r[field.key]);
    if (!Number.isFinite(v)) return false;
    if (min != null && v < min) return false;
    if (max != null && v > max) return false;
    return true;
  };
}

function textContainsPredicate(field, state) {
  const q = (state[field.key] || '').trim().toLowerCase();
  if (!q) return null;
  return (r) => {
    const v = r[field.key];
    if (v == null) return false;
    return String(v).toLowerCase().includes(q);
  };
}

function multiValuePredicate(field, state) {
  const selected = state[field.key];
  if (!Array.isArray(selected) || selected.length === 0) return null;
  // ``multi_autocomplete`` and ``multi_static`` both reduce to:
  // "is the record's column among the selected values?". The schema
  // doesn't distinguish at filter time — only at render time the popup
  // shows a different control.
  return (r) => {
    const v = r[field.key];
    return selected.includes(v);
  };
}

function sourcePredicate(field, state) {
  const selected = state[field.key];
  if (!Array.isArray(selected) || selected.length === 0) return null;
  const allowManual = selected.includes('manual');
  const allowFile = selected.includes('file');
  // ``manual`` ↔ dataset_id === 'manual'; everything else (a real dataset
  // UUID) is considered ``file``. This matches the badge the section
  // already renders on each row.
  return (r) => {
    const isManual = r.dataset_id === 'manual';
    if (isManual && allowManual) return true;
    if (!isManual && allowFile) return true;
    return false;
  };
}

function triStatePredicate(field, state) {
  const v = state[field.key];
  if (!v) return null;
  // Only documented use today: fixed_costs.active_status
  //   active   → no end_date OR end_date >= today
  //   inactive → end_date set AND end_date < today
  // Today is computed once per render — good enough for the merchant
  // who is unlikely to leave the popup open across midnight.
  const todayISO = new Date().toISOString().slice(0, 10);
  return (r) => {
    if (field.key !== 'active_status') {
      // Generic fallback: treat the tri-state as an exact-match string
      // on the same key. Currently unused; keeps the engine general.
      return r[field.key] === v;
    }
    const endDate = r.end_date ? String(r.end_date).slice(0, 10) : null;
    const isActive = !endDate || endDate >= todayISO;
    return v === 'active' ? isActive : !isActive;
  };
}


/**
 * Build the array of active predicates for one filter state.
 * Order-independent (AND is commutative) but kept stable for clarity.
 */
function buildPredicates(state, categoryType) {
  const schema = SCHEMAS[categoryType];
  if (!schema) return [];
  const preds = [];
  for (const field of schema) {
    let p = null;
    switch (field.type) {
      case 'date_range': p = dateRangePredicate(field, state); break;
      case 'number_range': p = numberRangePredicate(field, state); break;
      case 'text_contains': p = textContainsPredicate(field, state); break;
      case 'multi_autocomplete':
      case 'multi_static':
        p = multiValuePredicate(field, state); break;
      case 'multi_source':
        p = sourcePredicate(field, state); break;
      case 'tri_state':
        p = triStatePredicate(field, state); break;
      default:
        break;
    }
    if (p) preds.push(p);
  }
  return preds;
}


export function useCashflowFilters({ records, categoryType }) {
  // ``initial`` is memoised so the empty state object identity is stable
  // for the lifetime of the component (or until categoryType changes).
  // This keeps the setFilters identity from drifting when callers wrap
  // it in useCallback chains.
  const initial = useMemo(() => emptyFilterState(categoryType), [categoryType]);
  const [filters, setFilters] = useState(initial);

  // If the category changes (theoretically — today each section mounts
  // its own hook with a static categoryType) we resync the state shape.
  // Cheap defensive guard; runs only when categoryType is unstable.
  const lastCatRef = useMemoRef(categoryType);
  if (lastCatRef.current !== categoryType) {
    lastCatRef.current = categoryType;
    // Defer to next render to avoid setState-during-render warnings.
    queueMicrotask(() => setFilters(emptyFilterState(categoryType)));
  }

  const filtered = useMemo(() => {
    const safeRecords = Array.isArray(records) ? records : [];
    const preds = buildPredicates(filters, categoryType);
    if (preds.length === 0) return safeRecords;
    return safeRecords.filter((r) => preds.every((p) => p(r)));
  }, [records, filters, categoryType]);

  const activeCount = useMemo(
    () => countActiveFilters(filters, categoryType),
    [filters, categoryType]
  );

  const reset = useCallback(() => {
    setFilters(emptyFilterState(categoryType));
  }, [categoryType]);

  return { filters, setFilters, filtered, activeCount, reset };
}


// ── Internal: tiny ref helper that mimics ``useRef`` without requiring
//    a React import for it. Kept inline so the hook file stays a single
//    self-contained unit. Behaviour matches React.useRef for value refs.
function useMemoRef(initial) {
  // useState produces a stable [ref] across renders; mutating ref.current
  // is allowed and doesn't trigger re-renders.
  // eslint-disable-next-line react-hooks/rules-of-hooks
  const [ref] = useState({ current: initial });
  return ref;
}
