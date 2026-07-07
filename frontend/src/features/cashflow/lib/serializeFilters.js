/**
 * serializeFilters — translate the in-memory ``useCashflowFilters`` state
 * into the kwargs the per-category backend ``.search()`` helper expects.
 *
 * Phase 2 (2026-05-20). The filter state shape is identical to the
 * one ``useCashflowFilters`` builds (so the popup UI can stay unchanged
 * across the migration); we just stop running the predicates client-side
 * and instead push them to the backend.
 *
 * Per-category mapping
 * --------------------
 * Each cashflow category has its own backend ``/search`` endpoint with
 * a category-specific filter set. The serializer expands the field
 * suffix convention (``{key}_from / _to`` for date_range, ``_min / _max``
 * for number_range) into named API kwargs, and maps multi-select
 * arrays through unchanged (the API helper layer turns them into CSV).
 *
 * Tri-state ``active_status`` on fixed_costs is currently filtered
 * client-side and NOT sent to the backend — fixed_costs has no
 * ``/search`` endpoint (the cap-500 dataset is small enough to keep
 * client-side filtering). We export ``serializeFilters`` only for the
 * three paginated categories.
 *
 * Returning a plain object (no nesting) keeps the spread-into-axios
 * call site in ``useCashflowQuery`` minimal: ``api.search({...params, page})``.
 */


function _trim(s) {
  return s && String(s).trim() ? String(s).trim() : undefined;
}

function _nonEmptyArr(a) {
  return Array.isArray(a) && a.length > 0 ? a : undefined;
}

function _num(v) {
  // Accept '' (empty input from the popup) → undefined → no filter.
  if (v === '' || v === null || v === undefined) return undefined;
  const n = Number(v);
  return Number.isFinite(n) ? n : undefined;
}


/**
 * Map the ``sales`` filter state to ``salesAPI.search`` kwargs.
 *
 * Schema (filterSchemas.js:95-104):
 *   date_range:    date           → date_from/date_to
 *   number_range:  amount         → amount_min/amount_max
 *   multi:         category       → categories[]
 *   text:          description    → q
 *   multi:         channel        → channels[]
 *   date_range:    due_date       → due_date_from/due_date_to
 *   multi_static:  payment_status → paymentStatus[]
 *   multi_source:  source         → "manual" | "file" (single value;
 *                                   if both selected, omit = no filter)
 */
function _serializeSourceArray(arr) {
  // Frontend ``source`` is a multi-select but the backend takes a
  // single enum (manual|file). If the user selects BOTH, no filter
  // is constraining and we send undefined. If they select neither,
  // also undefined. Only one selected = pass it through.
  if (!Array.isArray(arr) || arr.length !== 1) return undefined;
  const v = arr[0];
  return v === 'manual' || v === 'file' ? v : undefined;
}


export function serializeSalesFilters(filters) {
  return {
    dateFrom: _trim(filters.date_from),
    dateTo: _trim(filters.date_to),
    dueDateFrom: _trim(filters.due_date_from),
    dueDateTo: _trim(filters.due_date_to),
    amountMin: _num(filters.amount_min),
    amountMax: _num(filters.amount_max),
    categories: _nonEmptyArr(filters.category),
    channels: _nonEmptyArr(filters.channel),
    paymentStatus: _nonEmptyArr(filters.payment_status),
    source: _serializeSourceArray(filters.source),
    q: _trim(filters.description),
  };
}


/**
 * Map the ``expenses`` filter state to ``expensesAPI.search`` kwargs.
 *
 * Schema (filterSchemas.js:105-112):
 *   date_range:    date         → date_from/date_to
 *   number_range:  amount       → amount_min/amount_max
 *   multi:         category     → categories[]
 *   text:          description  → q
 *   multi:         supplier     → suppliers[] (by name; the schema
 *                                  references the ``supplier`` field,
 *                                  not supplier_id)
 *   multi_source:  source       → "manual" | "file"
 */
export function serializeExpensesFilters(filters) {
  return {
    dateFrom: _trim(filters.date_from),
    dateTo: _trim(filters.date_to),
    amountMin: _num(filters.amount_min),
    amountMax: _num(filters.amount_max),
    categories: _nonEmptyArr(filters.category),
    suppliers: _nonEmptyArr(filters.supplier),
    source: _serializeSourceArray(filters.source),
    q: _trim(filters.description),
  };
}


/**
 * Map the ``purchases`` filter state to ``purchasesAPI.search`` kwargs.
 *
 * Schema (filterSchemas.js:113-127) — the richest filter set.
 * Special: ``q`` searches both description AND invoice_number on the
 * backend (single search box, two text fields). The popup has two
 * separate text inputs; we OR them into a single ``q`` payload — the
 * backend then does the same OR over the two columns.
 */
export function serializePurchasesFilters(filters) {
  const descQ = _trim(filters.description);
  const invQ = _trim(filters.invoice_number);
  // Merge the two free-text inputs into a single q. Most of the time
  // the user only types into one; if they fill both we concatenate
  // with a space so the regex matches either occurrence.
  let q;
  if (descQ && invQ) q = `${descQ} ${invQ}`;
  else if (descQ) q = descQ;
  else if (invQ) q = invQ;

  // ``iva`` is stored as strings ("0","4","10","22") in the static
  // options bucket — backend expects floats. Coerce here.
  const ivaRaw = _nonEmptyArr(filters.iva);
  const ivaValues = ivaRaw
    ? ivaRaw.map((v) => Number(v)).filter(Number.isFinite)
    : undefined;

  return {
    dateFrom: _trim(filters.date_from),
    dateTo: _trim(filters.date_to),
    dueDateFrom: _trim(filters.due_date_from),
    dueDateTo: _trim(filters.due_date_to),
    supplierNames: _nonEmptyArr(filters.supplier_name),
    categories: _nonEmptyArr(filters.category),
    categoriesMacro: _nonEmptyArr(filters.category_macro),
    units: _nonEmptyArr(filters.unit),
    ivaValues,
    paymentStatus: _nonEmptyArr(filters.payment_status),
    source: _serializeSourceArray(filters.source),
    quantityMin: _num(filters.quantity_min),
    quantityMax: _num(filters.quantity_max),
    unitPriceMin: _num(filters.unit_price_min),
    unitPriceMax: _num(filters.unit_price_max),
    q,
  };
}


/**
 * Dispatch by category. ``useCashflowQuery`` calls this with the
 * filter state + the static categoryType — keeps the per-category
 * branch out of the hook body.
 */
export function serializeFilters(filters, categoryType) {
  switch (categoryType) {
    case 'sales':
      return serializeSalesFilters(filters);
    case 'expenses':
      return serializeExpensesFilters(filters);
    case 'purchases':
      return serializePurchasesFilters(filters);
    default:
      // fixed_costs has no /search endpoint — caller should never
      // reach here. Returning {} keeps the hook from crashing if it
      // does, with a no-op (empty filter set = unfiltered query).
      return {};
  }
}
