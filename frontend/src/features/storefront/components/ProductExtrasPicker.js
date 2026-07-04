/**
 * ProductExtrasPicker — customer-facing selector for ProductExtra rows
 * on a reservation landing page (Onda 16).
 *
 * Three lanes:
 *   - mandatory    → summary only, disabled checkbox pre-selected
 *   - optional     → checkbox list, customer toggles; total updates live
 *   - radio_variant → one group per `group_key`, radio selection
 *
 * Controlled component. Parent owns the selection state:
 *
 *   <ProductExtrasPicker
 *     extras={product.extras}      // full list from GET /api/products/:id
 *     value={{
 *       optional_ids: ["ext_1", ...],
 *       radio_picks:  { "insurance": "ext_2", ... },
 *     }}
 *     onChange={next => setSelection(next)}
 *     dayCount={3}                 // for per_day pricing hints
 *   />
 *
 * The component never computes the total itself — that's the server's
 * job via POST /api/orders/price-preview. We only show per-extra hint
 * prices (unit × modifier) so the customer sees what each toggle costs.
 */

import React, { useMemo } from 'react';
import { formatAmount } from '../../../utils/currency';


const MODIFIER_LABEL = {
  flat: '',
  per_day: 'al giorno',
  per_unit: 'a unità',
};


function formatExtraPrice(extra, dayCount, currency = 'EUR') {
  const p = Number(extra.price || 0);
  if (p === 0) return 'incluso';
  const mod = extra.price_modifier_type || 'flat';
  // Honour the per-extra currency override when present, otherwise the
  // parent's currency (which itself falls back to "EUR" if the page
  // didn't pass it explicitly).
  const extraCurrency = extra.currency || currency;
  const baseLine = formatAmount(p, extraCurrency);
  if (mod === 'per_day' && dayCount && dayCount > 1) {
    const total = p * dayCount;
    return `${baseLine} × ${dayCount} gg = ${formatAmount(total, extraCurrency)}`;
  }
  const suffix = MODIFIER_LABEL[mod];
  return suffix ? `${baseLine} ${suffix}` : baseLine;
}


export default function ProductExtrasPicker({
  extras = [],
  value = { optional_ids: [], radio_picks: {} },
  onChange,
  dayCount = null,
  // CH compliance v1: parent (landing page) passes the resolved currency
  // so per-extra hint prices read in CHF on a Swiss store. Default
  // "EUR" preserves the previous output for callers that don't pass it.
  currency = 'EUR',
}) {
  const active = extras.filter(e => e.is_active !== false);

  const { mandatory, optionals, radioGroups } = useMemo(() => {
    const m = [];
    const o = [];
    const groups = {};
    for (const e of active) {
      if (e.kind === 'mandatory') m.push(e);
      else if (e.kind === 'optional') o.push(e);
      else if (e.kind === 'radio_variant') {
        const g = e.group_key || '_default';
        if (!groups[g]) groups[g] = [];
        groups[g].push(e);
      }
    }
    const sortFn = (a, b) => (a.sort_order || 0) - (b.sort_order || 0);
    m.sort(sortFn); o.sort(sortFn);
    Object.values(groups).forEach(rows => rows.sort(sortFn));
    return { mandatory: m, optionals: o, radioGroups: groups };
  }, [active]);

  if (mandatory.length === 0 && optionals.length === 0 && Object.keys(radioGroups).length === 0) {
    return null;
  }

  const toggleOptional = (id) => {
    const ids = value.optional_ids || [];
    const next = ids.includes(id) ? ids.filter(x => x !== id) : [...ids, id];
    onChange({ ...value, optional_ids: next });
  };

  const pickRadio = (groupKey, extraId) => {
    const picks = { ...(value.radio_picks || {}) };
    picks[groupKey] = extraId;
    onChange({ ...value, radio_picks: picks });
  };

  return (
    <div className="space-y-6">
      {/* Mandatory — shown as read-only summary */}
      {mandatory.length > 0 && (
        <section className="rounded-xl border border-amber-200 bg-amber-50/50 p-4">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-amber-900">
            Incluso automaticamente
          </h3>
          <ul className="mt-2 space-y-1.5">
            {mandatory.map(ex => (
              <li key={ex.id} className="flex items-center justify-between text-sm text-amber-950">
                <span className="flex items-center gap-1.5">
                  <span className="text-amber-700">✓</span>
                  <span className="font-medium">{ex.label}</span>
                  {ex.description && <span className="text-xs text-amber-800/70">· {ex.description}</span>}
                </span>
                <span className="text-sm font-semibold">{formatExtraPrice(ex, dayCount, currency)}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Radio groups — one <fieldset> per group_key */}
      {Object.entries(radioGroups).map(([groupKey, rows]) => {
        const selected = value.radio_picks?.[groupKey];
        const defaultRow = rows.find(r => r.is_default);
        const effectiveSelected = selected || (defaultRow && defaultRow.id) || null;
        return (
          <section key={groupKey} className="rounded-xl border border-gray-200 bg-white p-4">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-700 capitalize">
              {groupKey.replace(/_/g, ' ')}
            </h3>
            <div className="mt-3 space-y-2">
              {rows.map(ex => {
                const isChecked = effectiveSelected === ex.id;
                return (
                  <label
                    key={ex.id}
                    className={`flex items-start justify-between gap-3 rounded-lg border p-3 cursor-pointer transition-colors ${
                      isChecked
                        ? 'border-gray-900 bg-gray-50'
                        : 'border-gray-200 hover:border-gray-400'
                    }`}
                  >
                    <div className="flex items-start gap-3 min-w-0">
                      <input
                        type="radio"
                        name={`group-${groupKey}`}
                        checked={isChecked}
                        onChange={() => pickRadio(groupKey, ex.id)}
                        className="mt-0.5"
                      />
                      <div className="min-w-0">
                        <div className="text-sm font-medium text-gray-900">{ex.label}</div>
                        {ex.description && (
                          <div className="text-xs text-gray-500 mt-0.5">{ex.description}</div>
                        )}
                      </div>
                    </div>
                    <span className="shrink-0 text-sm font-semibold text-gray-900">
                      {formatExtraPrice(ex, dayCount, currency)}
                    </span>
                  </label>
                );
              })}
            </div>
          </section>
        );
      })}

      {/* Optional — checkbox list */}
      {optionals.length > 0 && (
        <section className="rounded-xl border border-gray-200 bg-white p-4">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-700">
            Extra opzionali
          </h3>
          <p className="text-xs text-gray-500 mt-1">
            Seleziona quelli che ti interessano. Il prezzo si aggiorna in tempo reale.
          </p>
          <div className="mt-3 space-y-2">
            {optionals.map(ex => {
              const checked = (value.optional_ids || []).includes(ex.id);
              return (
                <label
                  key={ex.id}
                  className={`flex items-start justify-between gap-3 rounded-lg border p-3 cursor-pointer transition-colors ${
                    checked
                      ? 'border-gray-900 bg-gray-50'
                      : 'border-gray-200 hover:border-gray-400'
                  }`}
                >
                  <div className="flex items-start gap-3 min-w-0">
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => toggleOptional(ex.id)}
                      className="mt-0.5"
                    />
                    <div className="min-w-0">
                      <div className="text-sm font-medium text-gray-900">{ex.label}</div>
                      {ex.description && (
                        <div className="text-xs text-gray-500 mt-0.5">{ex.description}</div>
                      )}
                    </div>
                  </div>
                  <span className="shrink-0 text-sm font-semibold text-gray-900">
                    {formatExtraPrice(ex, dayCount, currency)}
                  </span>
                </label>
              );
            })}
          </div>
        </section>
      )}
    </div>
  );
}
