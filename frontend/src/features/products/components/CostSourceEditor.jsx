/**
 * CostSourceEditor — additive cost composition UI (Wave 1, W1.S5).
 *
 * Lives inside the product create/edit dialog (ProductsPage.js). Receives
 * the current ``cost_source`` value and an onChange callback; renders
 * an inline editor that bubbles every change up.
 *
 * Design choices (deliberately minimal for production safety)
 * -----------------------------------------------------------
 *  - One function component, no class boundary, no sub-components.
 *    The original draft of this file split into AddComponentMenu,
 *    ComponentRow, CategoryPicker, PreviewFooter and an inline error
 *    boundary; that exploded the surface area and (somewhere in the
 *    interaction between them) crashed the dialog mount. The minimal
 *    rewrite keeps every interaction inline so problems are localised.
 *
 *  - No live preview API call. The resolver remains the source of truth
 *    at refresh time; the merchant sees the computed margin in
 *    Performance Prodotti right after saving. Removing the in-form
 *    POST /cost-preview eliminates an entire class of async/setState
 *    race conditions for zero loss of value at this stage.
 *
 *  - Searchable purchase-item picker (CreatableAutocomplete).
 *    The dropdown is populated from /modules/product-catalog/cost-categories
 *    via the dedicated useCostCategories hook. The merchant sees the
 *    same widget as in the Acquisti module's "Prodotto" field, so the
 *    naming and behaviour stay aligned across the app. Free-text typing
 *    is still supported (graceful fallback if the API errors).
 *
 *  - No error boundary. If anything were to throw in this much smaller
 *    component, react-error-overlay already surfaces it in dev — and in
 *    production the global ErrorBoundary catches it without taking down
 *    the rest of the app's chrome.
 *
 * Isolation contract (still honoured)
 * -----------------------------------
 *  - Pure controlled component: zero local DB state.
 *  - Safe to render with ``value=null`` (CREATE flow) — shows a friendly
 *    empty state. ``value=undefined`` (form state not yet initialised)
 *    is treated identically.
 *  - ``onChange(null)`` is invoked when the user removes the last
 *    component so the parent persists null (cleaner than an empty array).
 *  - Strips any non-canonical fields (``_migration_marker`` from the
 *    cost_price migration) so they don't round-trip into Mongo forever.
 *
 * i18n
 * ----
 * Uses the ``product_cost`` namespace. Every label, placeholder and
 * enum value is translated. The component falls back to the key name
 * if a translation is missing (i18next default behaviour).
 */

import React from 'react';
import { useTranslation } from 'react-i18next';
import { Plus, Trash2 } from 'lucide-react';
import { Button } from '../../../components/ui/button';
import { Input } from '../../../components/ui/input';
import { Label } from '../../../components/ui/label';
// W1 Phase 2.10 — purchase-item picker (searchable dropdown with
// free-text fallback). Existing shared component, same pattern used
// in PurchaseEntryForm so the merchant sees the SAME widget on both
// sides of the cost link.
import { CreatableAutocomplete } from '../../../components/CreatableAutocomplete';
import useCostCategories from '../hooks/useCostCategories';


// ── Constants (mirror backend enums) ────────────────────────────────────────
// Single source of truth on the frontend. The matching backend constants
// live in models/cost_source.py (COST_METHODS, COST_COMPONENT_TYPES,
// COST_UNITS). When adding a new method or unit, edit both sides.

const METHODS = ['fixed', 'latest', 'wac_30d', 'wac_90d', 'wac_180d', 'wac_365d'];
const COMPONENT_TYPES = ['manual', 'category_quantity', 'category_share'];
const UNITS = ['kg', 'g', 'L', 'ml', 'pcs', 'h', 'm', 'm2', 'm3'];


// ── Pure helpers ────────────────────────────────────────────────────────────


/**
 * Normalise the prop ``value`` into a safe object with the canonical
 * shape. Tolerates null / undefined / malformed inputs (e.g. legacy
 * objects with extra fields like ``_migration_marker``) by returning a
 * sanitised view. Never throws.
 */
function _normalise(value) {
  if (!value || typeof value !== 'object') {
    return { method: 'wac_90d', components: [] };
  }
  return {
    method: typeof value.method === 'string' ? value.method : 'wac_90d',
    components: Array.isArray(value.components) ? value.components : [],
  };
}


/**
 * Format a numeric value as a localised currency string. We intentionally
 * delegate to ``Intl.NumberFormat`` rather than the shared formatCurrency
 * helper because this editor lives in many contexts (wizard, dashboard
 * dialog) and we don't always have the org currency in scope here —
 * defaulting to EUR is acceptable for an in-form preview.
 */
function _fmtMoney(value) {
  if (value == null || Number.isNaN(Number(value))) return '—';
  try {
    return new Intl.NumberFormat('it-IT', {
      style: 'currency',
      currency: 'EUR',
      maximumFractionDigits: 2,
    }).format(Number(value));
  } catch {
    return `€${Number(value).toFixed(2)}`;
  }
}


/**
 * Build a fresh component of the given type with all required fields
 * populated to safe defaults. Keeps the rest of the form logic free of
 * type-specific initialisation noise.
 */
function _makeComponent(type) {
  if (type === 'manual') return { type, label: '', manual_value: 0 };
  if (type === 'category_quantity') return { type, label: '', category: '', qty_per_unit: 0, qty_unit: 'kg' };
  if (type === 'category_share') return { type, label: '', category: '', share_pct: null };
  return { type, label: '' };
}


// ── Component ───────────────────────────────────────────────────────────────


export default function CostSourceEditor({ value, onChange }) {
  const { t } = useTranslation('product_cost');

  // Read-only normalised view used for rendering. All mutators emit a
  // NEW object via onChange — we never mutate this in place.
  const cs = _normalise(value);
  const hasComponents = cs.components.length > 0;

  // Pull the merchant's existing "Prodotto" values from the Purchases
  // module. The hook handles loading/error gracefully: when the fetch
  // fails (or returns empty) the merchant can still type free-text,
  // which is exactly the contract of CreatableAutocomplete.
  //
  // ``byName`` is a Map<name, fullOption> we use to surface per-item
  // metadata (avg_unit_price, units, total_spent) once the merchant
  // has picked a category.
  const { options: categoryOptions, byName: categoryByName } = useCostCategories();
  // Flatten to plain strings — CreatableAutocomplete expects string[]
  // and we don't need the full envelope inside the dropdown itself.
  const categoryNames = React.useMemo(
    () => (categoryOptions || []).map((c) => c.name).filter(Boolean),
    [categoryOptions]
  );

  // ── Mutators ────────────────────────────────────────────────────────────

  const setMethod = (method) => {
    onChange({ method, components: cs.components });
  };

  const addComponent = (type) => {
    const next = [...cs.components, _makeComponent(type)];
    onChange({ method: cs.method, components: next });
  };

  const updateComponent = (idx, patch) => {
    const next = cs.components.map((c, i) => (i === idx ? { ...c, ...patch } : c));
    onChange({ method: cs.method, components: next });
  };

  const removeComponent = (idx) => {
    const next = cs.components.filter((_, i) => i !== idx);
    // Empty list ⇒ signal "no cost configured" to the parent so it
    // persists null in the payload rather than an empty container.
    onChange(next.length === 0 ? null : { method: cs.method, components: next });
  };

  // ── Render ──────────────────────────────────────────────────────────────

  return (
    <div className="space-y-3">
      {/* Method selector — applies to every category-based component. */}
      <div className="flex items-center gap-2">
        <Label className="text-xs shrink-0">{t('method.label')}</Label>
        <select
          value={cs.method}
          onChange={(e) => setMethod(e.target.value)}
          className="flex-1 rounded-md border border-input bg-background px-2 py-1.5 text-xs"
        >
          {METHODS.map((m) => (
            <option key={m} value={m}>{t(`method.${m}`)}</option>
          ))}
        </select>
      </div>

      {/* Components list — one row per contribution. Empty state below. */}
      {hasComponents ? (
        <div className="space-y-2">
          {cs.components.map((comp, idx) => (
            <div key={idx} className="border rounded-md p-2 bg-white space-y-1.5">
              {/* Header: type badge + label input + remove */}
              <div className="flex items-start gap-2">
                <span className="text-[10px] uppercase tracking-wide text-gray-500 mt-1.5 shrink-0 min-w-[60px]">
                  {t(`component.type.${comp.type}_short`)}
                </span>
                <Input
                  value={comp.label || ''}
                  onChange={(e) => updateComponent(idx, { label: e.target.value })}
                  placeholder={t('component.label_placeholder')}
                  className="text-xs h-7 flex-1"
                  maxLength={100}
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => removeComponent(idx)}
                  aria-label={t('component.remove')}
                  className="h-7 w-7 p-0 text-gray-400 hover:text-red-600 shrink-0"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </div>

              {/* Type-specific fields */}
              {comp.type === 'manual' && (
                <div className="flex items-center gap-2 pl-[68px]">
                  <Label className="text-[10px] text-gray-500 shrink-0">
                    {t('component.manual_value')}:
                  </Label>
                  <Input
                    type="number"
                    step="0.01"
                    min="0"
                    value={comp.manual_value ?? ''}
                    onChange={(e) => updateComponent(idx, {
                      manual_value: e.target.value === '' ? null : parseFloat(e.target.value),
                    })}
                    placeholder={t('component.manual_value_placeholder')}
                    className="text-xs h-7 flex-1"
                  />
                </div>
              )}

              {comp.type === 'category_quantity' && (() => {
                // Resolve the merchant's purchase metadata for this
                // picked item (if any). When the merchant just typed a
                // free-text value that isn't in Purchases yet, info
                // stays null and we render a softer "not in Purchases
                // yet" hint instead of misleading price numbers.
                const info = comp.category ? categoryByName.get(comp.category) : null;
                const allUnits = info?.unit_details || [];
                // Auto-resolve the unit when info is known and the
                // current qty_unit either is empty or doesn't actually
                // belong to this item. Keeps the merchant from picking
                // a unit the resolver can't match against purchases.
                const knownUnits = allUnits.map(u => u.unit);
                const effectiveUnit = (comp.qty_unit && knownUnits.includes(comp.qty_unit))
                  ? comp.qty_unit
                  : (allUnits[0]?.unit || comp.qty_unit || '');
                const unitDetail = allUnits.find(u => u.unit === effectiveUnit);
                const avgPrice = unitDetail?.avg_unit_price;
                const contribution = (typeof comp.qty_per_unit === 'number' && typeof avgPrice === 'number')
                  ? comp.qty_per_unit * avgPrice
                  : null;

                return (
                  <div className="space-y-2 pl-[68px]">
                    {/* Purchase-item picker */}
                    <div>
                      <Label className="text-[10px] text-gray-500 mb-0.5 block">
                        {t('component.category')}
                      </Label>
                      <CreatableAutocomplete
                        value={comp.category || ''}
                        onChange={(v) => {
                          // When the merchant picks a known item, snap
                          // qty_unit to its most-used unit so the
                          // numbers immediately make sense without an
                          // extra click. If they type a free-text
                          // value we don't know yet, leave qty_unit
                          // alone (they can still type the quantity).
                          const picked = categoryByName.get(v);
                          const firstUnit = picked?.unit_details?.[0]?.unit;
                          if (firstUnit) {
                            updateComponent(idx, { category: v, qty_unit: firstUnit });
                          } else {
                            updateComponent(idx, { category: v });
                          }
                        }}
                        options={categoryNames}
                        placeholder={t('component.category_placeholder')}
                        className="text-xs h-7"
                      />
                      {/* Show the avg price when we have it, else a
                          "not in Purchases" hint, else just the help. */}
                      {info && avgPrice != null ? (
                        <p className="text-[10px] text-emerald-700 mt-1 font-medium">
                          {allUnits.length > 1
                            ? t('component.category_avg_price_multi_unit', {
                                price: _fmtMoney(avgPrice),
                                unit: t(`unit.${effectiveUnit}`, effectiveUnit),
                                others: allUnits.slice(1)
                                  .map(u => t(`unit.${u.unit}`, u.unit))
                                  .join(', '),
                              })
                            : t('component.category_avg_price', {
                                price: _fmtMoney(avgPrice),
                                unit: t(`unit.${effectiveUnit}`, effectiveUnit),
                              })}
                        </p>
                      ) : (comp.category && !info) ? (
                        <p className="text-[10px] text-amber-700 mt-1">
                          {t('component.category_not_in_purchases')}
                        </p>
                      ) : (
                        <p className="text-[10px] text-gray-400 mt-1">
                          {t('component.category_help')}
                        </p>
                      )}
                    </div>

                    {/* Quantity + unit. When we know the units this
                        item comes in, show a constrained select; when
                        the merchant typed a free-text value we don't
                        recognise, fall back to the full UNITS list. */}
                    <div>
                      <Label className="text-[10px] text-gray-500 mb-0.5 block">
                        {t('component.qty_per_unit')}
                      </Label>
                      <div className="flex items-center gap-2">
                        <Input
                          type="number"
                          step="0.001"
                          min="0"
                          value={comp.qty_per_unit ?? ''}
                          onChange={(e) => updateComponent(idx, {
                            qty_per_unit: e.target.value === '' ? null : parseFloat(e.target.value),
                          })}
                          placeholder={t('component.qty_per_unit_placeholder')}
                          className="text-xs h-7 flex-1"
                        />
                        {knownUnits.length === 1 ? (
                          // Single unit known → render as read-only
                          // chip; no merchant choice to make.
                          <span className="text-[11px] text-gray-700 bg-gray-100 px-2 py-1 rounded font-medium min-w-[44px] text-center">
                            {t(`unit.${effectiveUnit}`, effectiveUnit)}
                          </span>
                        ) : (
                          <select
                            value={effectiveUnit}
                            onChange={(e) => updateComponent(idx, { qty_unit: e.target.value })}
                            className="rounded-md border border-input bg-background px-2 h-7 text-xs"
                          >
                            {(knownUnits.length > 0 ? knownUnits : UNITS).map((u) => (
                              <option key={u} value={u}>{t(`unit.${u}`, u)}</option>
                            ))}
                          </select>
                        )}
                      </div>
                      <p className="text-[10px] text-gray-400 mt-0.5">
                        {t('component.qty_per_unit_help')}
                      </p>
                    </div>

                    {/* Live preview of the contribution. Shows only
                        when we have all 3 ingredients (item known,
                        unit resolved, qty entered). */}
                    {contribution != null && contribution >= 0 && (
                      <div className="text-[11px] bg-emerald-50 border border-emerald-200 rounded px-2 py-1.5 text-emerald-800">
                        {t('component.preview_contribution_quantity', {
                          value: _fmtMoney(contribution),
                          qty: comp.qty_per_unit,
                          unit: t(`unit.${effectiveUnit}`, effectiveUnit),
                          price: _fmtMoney(avgPrice),
                        })}
                      </div>
                    )}
                  </div>
                );
              })()}

              {comp.type === 'category_share' && (() => {
                const info = comp.category ? categoryByName.get(comp.category) : null;
                const pool = info?.total_spent;
                const pct = typeof comp.share_pct === 'number' ? comp.share_pct : null;
                // Contribution preview only when we have a fixed share %
                // AND a known pool. The "auto-proportional" mode
                // (share_pct=null) gets distributed at refresh time by
                // the backend resolver against current revenue mix —
                // not predictable client-side.
                const contribution = (pct != null && typeof pool === 'number')
                  ? (pool * pct / 100)
                  : null;

                return (
                  <div className="space-y-2 pl-[68px]">
                    {/* Purchase-item picker */}
                    <div>
                      <Label className="text-[10px] text-gray-500 mb-0.5 block">
                        {t('component.category')}
                      </Label>
                      <CreatableAutocomplete
                        value={comp.category || ''}
                        onChange={(v) => updateComponent(idx, { category: v })}
                        options={categoryNames}
                        placeholder={t('component.category_placeholder')}
                        className="text-xs h-7"
                      />
                      {info ? (
                        <p className="text-[10px] text-emerald-700 mt-1 font-medium">
                          {t('component.category_total_spent', {
                            amount: _fmtMoney(info.total_spent),
                            count: info.purchase_count,
                          })}
                        </p>
                      ) : (comp.category && !info) ? (
                        <p className="text-[10px] text-amber-700 mt-1">
                          {t('component.category_not_in_purchases')}
                        </p>
                      ) : (
                        <p className="text-[10px] text-gray-400 mt-1">
                          {t('component.category_help')}
                        </p>
                      )}
                    </div>

                    {/* Share % input */}
                    <div>
                      <Label className="text-[10px] text-gray-500 mb-0.5 block">
                        {t('component.share_pct')}
                      </Label>
                      <Input
                        type="number"
                        step="0.1"
                        min="0"
                        max="100"
                        value={comp.share_pct ?? ''}
                        onChange={(e) => updateComponent(idx, {
                          share_pct: e.target.value === '' ? null : parseFloat(e.target.value),
                        })}
                        placeholder={t('component.share_pct_placeholder')}
                        className="text-xs h-7"
                      />
                      <p className="text-[10px] text-gray-400 mt-0.5">
                        {t('component.share_pct_auto_hint')}
                      </p>
                    </div>

                    {/* Live preview — fixed-share only */}
                    {contribution != null && contribution >= 0 && (
                      <div className="text-[11px] bg-emerald-50 border border-emerald-200 rounded px-2 py-1.5 text-emerald-800">
                        {t('component.preview_contribution_share', {
                          value: _fmtMoney(contribution),
                          pct: pct,
                          pool: _fmtMoney(pool),
                        })}
                      </div>
                    )}
                  </div>
                );
              })()}
            </div>
          ))}
        </div>
      ) : (
        <p className="text-xs text-gray-500 italic text-center py-3 bg-gray-50 rounded">
          {t('empty.description')}
        </p>
      )}

      {/* Add-component buttons — one per type, always visible. */}
      <div className="flex gap-2 flex-wrap">
        {COMPONENT_TYPES.map((type) => (
          <Button
            key={type}
            type="button"
            variant="outline"
            size="sm"
            onClick={() => addComponent(type)}
            className="text-xs"
          >
            <Plus className="h-3 w-3 mr-1" />
            {t(`component.type.${type}_short`)}
          </Button>
        ))}
      </div>
    </div>
  );
}
