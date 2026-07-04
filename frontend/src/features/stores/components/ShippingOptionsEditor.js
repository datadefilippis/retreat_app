/**
 * ShippingOptionsEditor — inline CRUD for shipping options for ONE scope.
 *
 * Scope is determined by the parent:
 *   - storeId !== null  → editing that store's options (per-store scope)
 *   - storeId === null  → editing the org-global options
 *
 * Pattern mirrors ProductExtrasEditor (inline list with _localId for focus
 * stability). The parent provides the current rows and handles the
 * reconciliation with the backend on save (delete-all + recreate keeps the
 * contract simple; the dataset is very small — typically < 10 options).
 *
 * Contract:
 *   <ShippingOptionsEditor
 *     options={options}     // ShippingOption[] for this scope
 *     onChange={(next) => ...}   // fires with the full updated array
 *     storeId={string|null}      // purely informational — for copy hints
 *   />
 */

import React, { useCallback } from 'react';
import { useTranslation } from 'react-i18next';


// Short-lived key for React reconciliation on unsaved rows. We set it
// on-first-render and strip it right before calling the API.
let _localIdSeq = 0;
function nextLocalId() {
  _localIdSeq += 1;
  return `local-${Date.now()}-${_localIdSeq}`;
}


function ensureLocalIds(list) {
  return (list || []).map(o => o._localId ? o : { ...o, _localId: nextLocalId() });
}


export default function ShippingOptionsEditor({ options, onChange, storeId }) {
  const { t } = useTranslation('stores');
  const rows = ensureLocalIds(options);

  const emit = useCallback((nextRows) => {
    // Parent receives rows WITH _localId (focus stability); it strips
    // _localId only at save time.
    onChange(nextRows);
  }, [onChange]);

  const updateRow = (localId, patch) => {
    const next = rows.map(r => r._localId === localId ? { ...r, ...patch } : r);
    emit(next);
  };

  const removeRow = (localId) => {
    emit(rows.filter(r => r._localId !== localId));
  };

  const moveRow = (localId, dir) => {
    const idx = rows.findIndex(r => r._localId === localId);
    if (idx < 0) return;
    const target = idx + dir;
    if (target < 0 || target >= rows.length) return;
    const next = [...rows];
    [next[idx], next[target]] = [next[target], next[idx]];
    // Keep sort_order in sync with the new positions so the server-side
    // ordering matches what the admin sees.
    next.forEach((r, i) => { r.sort_order = i; });
    emit(next);
  };

  const addRow = () => {
    const next = [
      ...rows,
      {
        _localId: nextLocalId(),
        label: '',
        description: '',
        base_price: '',
        free_shipping_threshold: '',
        sort_order: rows.length,
        is_active: true,
      },
    ];
    emit(next);
  };

  return (
    <div className="space-y-3">
      {rows.length === 0 && (
        <div className="rounded-md border-2 border-dashed border-gray-200 bg-gray-50 px-4 py-6 text-center">
          <p className="text-sm text-gray-600">
            {storeId === null
              ? t('shipping.editor.empty_global')
              : t('shipping.editor.empty_store')}
          </p>
          <p className="text-xs text-gray-500 mt-1">
            {t('shipping.editor.empty_hint')}
          </p>
        </div>
      )}

      {rows.map((row, i) => (
        <div
          key={row._localId}
          className="rounded-lg border border-gray-200 bg-white p-3 space-y-2"
        >
          <div className="flex items-center gap-2">
            <div className="flex flex-col gap-0.5">
              <button
                type="button"
                onClick={() => moveRow(row._localId, -1)}
                disabled={i === 0}
                className="text-xs text-gray-500 hover:text-gray-900 disabled:opacity-30"
                aria-label={t('shipping.editor.move_up_aria')}
              >▲</button>
              <button
                type="button"
                onClick={() => moveRow(row._localId, +1)}
                disabled={i === rows.length - 1}
                className="text-xs text-gray-500 hover:text-gray-900 disabled:opacity-30"
                aria-label={t('shipping.editor.move_down_aria')}
              >▼</button>
            </div>
            <input
              type="text"
              value={row.label || ''}
              onChange={e => updateRow(row._localId, { label: e.target.value })}
              maxLength={120}
              placeholder={t('shipping.editor.name_placeholder')}
              className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
            />
            <label className="flex items-center gap-1 text-xs text-gray-600 cursor-pointer">
              <input
                type="checkbox"
                checked={row.is_active !== false}
                onChange={e => updateRow(row._localId, { is_active: e.target.checked })}
                className="rounded border-gray-300"
              />
              {t('shipping.editor.active_label')}
            </label>
            <button
              type="button"
              onClick={() => removeRow(row._localId)}
              className="text-xs text-red-600 hover:text-red-800"
              title={t('shipping.editor.delete_title')}
            >✕</button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            <div>
              <label className="block text-[11px] font-medium text-gray-600 mb-1">
                {t('shipping.editor.price_label')}
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={row.base_price ?? ''}
                onChange={e => updateRow(row._localId, { base_price: e.target.value })}
                placeholder="0.00"
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none tabular-nums"
              />
            </div>
            <div>
              <label className="block text-[11px] font-medium text-gray-600 mb-1">
                {t('shipping.editor.free_threshold_label')}
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={row.free_shipping_threshold ?? ''}
                onChange={e => updateRow(row._localId, { free_shipping_threshold: e.target.value })}
                placeholder={t('shipping.editor.free_threshold_placeholder')}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none tabular-nums"
              />
            </div>
          </div>

          <div>
            <input
              type="text"
              value={row.description || ''}
              onChange={e => updateRow(row._localId, { description: e.target.value })}
              maxLength={500}
              placeholder={t('shipping.editor.description_placeholder')}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
            />
          </div>
        </div>
      ))}

      <button
        type="button"
        onClick={addRow}
        className="w-full rounded-lg border-2 border-dashed border-gray-300 bg-white px-3 py-2 text-sm font-semibold text-gray-700 hover:border-gray-900 hover:bg-gray-50"
      >
        {t('shipping.editor.add')}
      </button>
    </div>
  );
}
