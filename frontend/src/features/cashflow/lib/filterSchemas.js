/**
 * filterSchemas — declarative description of the filter UI for each
 * cashflow record category.
 *
 * Each category has a list of fields with:
 *   - key      : the property name on the record (matches backend)
 *   - type     : how to render and how to apply the filter
 *   - i18nKey  : the i18n label key (resolved via cashflow_monitor namespace)
 *   - optionsKey?    : for ``multi_autocomplete``, name of the options
 *                      bucket the parent passes in (e.g. "categories",
 *                      "suppliers", "channels", "categories_macro")
 *   - staticOptions? : for ``multi_static``, name of the constant
 *                      bucket in ``STATIC_OPTIONS`` below
 *
 * Filter types
 * ------------
 *   date_range       → two <input type="date"> (from / to)
 *   number_range     → two <input type="number"> (min / max)
 *   text_contains    → <input type="text">, case-insensitive substring
 *   multi_autocomplete → CreatableAutocomplete-driven multi-select; the
 *                        parent loads the options bucket dynamically
 *                        from the same API the EntryForm already uses
 *   multi_static     → checkbox list against a constant tuple defined
 *                      below (units, IVA, payment statuses, …)
 *   multi_source     → checkbox list for the synthetic "manual" / "file"
 *                      source. Maps to ``dataset_id`` on the record:
 *                      manual → dataset_id === 'manual'
 *                      file   → dataset_id !== 'manual'
 *   tri_state        → three-way ('' = any, 'active', 'inactive') for
 *                      time-based active status on fixed_costs
 *
 * Filter state convention
 * -----------------------
 * Range types expand to two keys with suffixes:
 *   date_range    → ``{key}_from``, ``{key}_to``        (ISO yyyy-mm-dd)
 *   number_range  → ``{key}_min``, ``{key}_max``        (parseFloat-able)
 * Multi types store an array of selected values.
 * Text types store a string.
 *
 * Why a single declarative schema vs four hand-written popups
 * ----------------------------------------------------------
 * The four cashflow sections share 90% of the filter UX (date, amount,
 * description, source). Diverging only on category-specific fields
 * means the popup component itself stays category-agnostic — it reads
 * the schema and renders accordingly. Adding a new category later is
 * one new entry in ``SCHEMAS`` plus any new STATIC_OPTIONS; the popup
 * + hook + integration code stay untouched.
 */


// ── Static value buckets (referenced by ``staticOptions``) ─────────────

export const STATIC_OPTIONS = {
  PAYMENT_STATUSES: [
    { value: 'pending', i18nKey: 'enums.payment_pending' },
    { value: 'paid', i18nKey: 'enums.payment_paid' },
    { value: 'overdue', i18nKey: 'enums.payment_overdue' },
  ],
  UNITS: [
    { value: 'kg', i18nKey: 'enums.unit_kg' },
    { value: 'pezzi', i18nKey: 'enums.unit_pieces' },
    { value: 'metri', i18nKey: 'enums.unit_meters' },
    { value: 'litri', i18nKey: 'enums.unit_liters' },
  ],
  IVA_OPTIONS: [
    { value: '0', label: '0%' },
    { value: '4', label: '4%' },
    { value: '10', label: '10%' },
    { value: '22', label: '22%' },
  ],
  FIXED_COST_CATEGORIES: [
    { value: 'affitto', i18nKey: 'enums.cat_rent' },
    { value: 'stipendio', i18nKey: 'enums.cat_salary' },
    { value: 'finanziamento', i18nKey: 'enums.cat_financing' },
    { value: 'leasing', i18nKey: 'enums.cat_leasing' },
    { value: 'abbonamento', i18nKey: 'enums.cat_subscription' },
    { value: 'altro', i18nKey: 'enums.cat_other' },
  ],
  FREQUENCIES: [
    { value: 'mensile', i18nKey: 'enums.freq_monthly' },
    { value: 'settimanale', i18nKey: 'enums.freq_weekly' },
    { value: 'trimestrale', i18nKey: 'enums.freq_quarterly' },
    { value: 'annuale', i18nKey: 'enums.freq_annual' },
  ],
  SOURCES: [
    { value: 'manual', i18nKey: 'sections.source_manual' },
    { value: 'file', i18nKey: 'sections.source_file' },
  ],
};


// ── Per-category schemas ───────────────────────────────────────────────

export const SCHEMAS = {
  sales: [
    { key: 'date', type: 'date_range', i18nKey: 'forms.date' },
    { key: 'amount', type: 'number_range', i18nKey: 'forms.amount' },
    { key: 'category', type: 'multi_autocomplete', i18nKey: 'forms.category', optionsKey: 'categories' },
    { key: 'description', type: 'text_contains', i18nKey: 'forms.description' },
    { key: 'channel', type: 'multi_autocomplete', i18nKey: 'forms.channel', optionsKey: 'channels' },
    { key: 'due_date', type: 'date_range', i18nKey: 'forms.due_date' },
    { key: 'payment_status', type: 'multi_static', i18nKey: 'forms.payment_status', staticOptions: 'PAYMENT_STATUSES' },
    { key: 'source', type: 'multi_source', i18nKey: 'sections.source' },
  ],
  expenses: [
    { key: 'date', type: 'date_range', i18nKey: 'forms.date' },
    { key: 'amount', type: 'number_range', i18nKey: 'forms.amount' },
    { key: 'category', type: 'multi_autocomplete', i18nKey: 'forms.category', optionsKey: 'categories' },
    { key: 'description', type: 'text_contains', i18nKey: 'forms.description' },
    { key: 'supplier', type: 'multi_autocomplete', i18nKey: 'forms.supplier', optionsKey: 'suppliers' },
    { key: 'source', type: 'multi_source', i18nKey: 'sections.source' },
  ],
  purchases: [
    { key: 'date', type: 'date_range', i18nKey: 'forms.date' },
    { key: 'supplier_name', type: 'multi_autocomplete', i18nKey: 'forms.supplier', optionsKey: 'suppliers' },
    { key: 'quantity', type: 'number_range', i18nKey: 'forms.quantity' },
    { key: 'unit', type: 'multi_static', i18nKey: 'forms.unit', staticOptions: 'UNITS' },
    { key: 'unit_price', type: 'number_range', i18nKey: 'forms.unit_price' },
    { key: 'iva', type: 'multi_static', i18nKey: 'forms.iva', staticOptions: 'IVA_OPTIONS' },
    { key: 'category', type: 'multi_autocomplete', i18nKey: 'forms.purchase_category', optionsKey: 'categories' },
    { key: 'category_macro', type: 'multi_autocomplete', i18nKey: 'forms.purchase_category_macro', optionsKey: 'categories_macro' },
    { key: 'description', type: 'text_contains', i18nKey: 'forms.description' },
    { key: 'invoice_number', type: 'text_contains', i18nKey: 'forms.invoice_number' },
    { key: 'due_date', type: 'date_range', i18nKey: 'forms.due_date' },
    { key: 'payment_status', type: 'multi_static', i18nKey: 'forms.payment_status', staticOptions: 'PAYMENT_STATUSES' },
    { key: 'source', type: 'multi_source', i18nKey: 'sections.source' },
  ],
  fixed_costs: [
    { key: 'name', type: 'text_contains', i18nKey: 'forms.name' },
    { key: 'category', type: 'multi_static', i18nKey: 'forms.category', staticOptions: 'FIXED_COST_CATEGORIES' },
    { key: 'amount', type: 'number_range', i18nKey: 'forms.amount' },
    { key: 'frequency', type: 'multi_static', i18nKey: 'forms.frequency', staticOptions: 'FREQUENCIES' },
    { key: 'start_date', type: 'date_range', i18nKey: 'forms.start_date' },
    { key: 'end_date', type: 'date_range', i18nKey: 'forms.end_date' },
    { key: 'active_status', type: 'tri_state', i18nKey: 'sections.status' },
    { key: 'source', type: 'multi_source', i18nKey: 'sections.source' },
  ],
};


/**
 * Build an empty filter state for the given category — the canonical
 * "no filter applied" object. Stored as the initial state in the hook
 * and used by the Reset button.
 *
 * The shape stays stable across renders so React equality checks work
 * naturally; the hook builds it once via useMemo keyed on categoryType.
 */
export function emptyFilterState(categoryType) {
  const schema = SCHEMAS[categoryType];
  if (!schema) {
    // Defensive: an unknown category yields no filterable fields rather
    // than a crash. The popup will simply render an empty form (the
    // smoke test would catch this via React PropTypes had we declared
    // them, but the codebase convention is not to).
    return {};
  }
  const out = {};
  for (const field of schema) {
    switch (field.type) {
      case 'date_range':
        out[field.key + '_from'] = '';
        out[field.key + '_to'] = '';
        break;
      case 'number_range':
        out[field.key + '_min'] = '';
        out[field.key + '_max'] = '';
        break;
      case 'multi_autocomplete':
      case 'multi_static':
      case 'multi_source':
        out[field.key] = [];
        break;
      case 'text_contains':
        out[field.key] = '';
        break;
      case 'tri_state':
        // '' = any, 'active', 'inactive'
        out[field.key] = '';
        break;
      default:
        break;
    }
  }
  return out;
}


/**
 * Count how many fields in a filter state are actively constraining the
 * results (i.e. non-empty). Drives the badge on the trigger button.
 *
 * A range counts as ONE active filter even when both ends are set —
 * conceptually it is a single constraint on a single column. This
 * matches what the merchant sees in the popup ("Date: 1 Jan → 31 Jan"
 * is one row).
 */
export function countActiveFilters(state, categoryType) {
  const schema = SCHEMAS[categoryType];
  if (!schema) return 0;
  let n = 0;
  for (const field of schema) {
    switch (field.type) {
      case 'date_range': {
        const from = state[field.key + '_from'];
        const to = state[field.key + '_to'];
        if (from || to) n += 1;
        break;
      }
      case 'number_range': {
        const min = state[field.key + '_min'];
        const max = state[field.key + '_max'];
        if (min !== '' && min != null) { n += 1; break; }
        if (max !== '' && max != null) n += 1;
        break;
      }
      case 'multi_autocomplete':
      case 'multi_static':
      case 'multi_source':
        if (Array.isArray(state[field.key]) && state[field.key].length > 0) n += 1;
        break;
      case 'text_contains':
        if (state[field.key] && state[field.key].trim() !== '') n += 1;
        break;
      case 'tri_state':
        if (state[field.key]) n += 1;
        break;
      default:
        break;
    }
  }
  return n;
}
