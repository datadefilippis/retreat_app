/**
 * ServiceOptionsEditor — inline CRUD editor for a service product's
 * options list (F5 Onda 12).
 *
 * Contract:
 *   <ServiceOptionsEditor
 *     options={options}            // ServiceOption[]
 *     onChange={(next) => ...}     // fires with the full new array
 *     title="Opzioni del servizio"
 *     subtitle="..."
 *     addButtonLabel="+ Aggiungi opzione"
 *     emptyHint="..."
 *   />
 *
 * Each option in the array has the shape:
 *   { id?, label, price, description?, duration_minutes_override?, sort_order, is_active }
 *
 * IDs are provisional until the Wizard persists to the backend; in the
 * Dashboard path the IDs come back from the server. The component is
 * schema-agnostic on id — treats it as an opaque identifier.
 *
 * Note: mirror pattern of EventWizard tier editor but scoped to a
 * product (not occurrence). Radio-select semantics on the storefront:
 * the customer picks exactly ONE of these at checkout.
 */

import React, { useCallback } from 'react';
import { useTranslation } from 'react-i18next';


function toInput(v) {
  if (v === null || v === undefined) return '';
  return String(v);
}


export default function ServiceOptionsEditor({
  options = [],
  onChange,
  title = null,
  subtitle = null,
  addButtonLabel = null,
  emptyHint = null,
}) {
  const { t } = useTranslation('products');
  const displayTitle = title ?? t('options.title');
  const displaySubtitle = subtitle ?? t('options.subtitle');
  const displayAddButtonLabel = addButtonLabel ?? t('options.addButton');
  const displayEmptyHint = emptyHint ?? t('options.emptyHint');
  const update = useCallback((idx, patch) => {
    const next = options.map((o, i) => (i === idx ? { ...o, ...patch } : o));
    onChange(next);
  }, [options, onChange]);

  const add = useCallback(() => {
    const newOption = {
      label: '',
      description: '',
      price: '',
      duration_minutes_override: '',
      sort_order: options.length,
      is_active: true,
    };
    onChange([...options, newOption]);
  }, [options, onChange]);

  const remove = useCallback((idx) => {
    const next = options.filter((_, i) => i !== idx);
    // Re-sync sort_order so the numbering stays consistent.
    next.forEach((o, i) => { o.sort_order = i; });
    onChange(next);
  }, [options, onChange]);

  const move = useCallback((idx, delta) => {
    const j = idx + delta;
    if (j < 0 || j >= options.length) return;
    const next = [...options];
    [next[idx], next[j]] = [next[j], next[idx]];
    next.forEach((o, i) => { o.sort_order = i; });
    onChange(next);
  }, [options, onChange]);

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          {displayTitle && <h3 className="text-sm font-semibold text-gray-900">{displayTitle}</h3>}
          {displaySubtitle && <p className="text-xs text-gray-500 mt-0.5">{displaySubtitle}</p>}
        </div>
        <button
          type="button"
          onClick={add}
          className="shrink-0 text-xs font-semibold rounded-md bg-gray-900 text-white px-3 py-1.5 hover:bg-gray-800"
        >
          {displayAddButtonLabel}
        </button>
      </div>

      {options.length === 0 ? (
        <p className="text-xs text-gray-500 italic">{displayEmptyHint}</p>
      ) : (
        <div className="space-y-2">
          {options.map((o, idx) => (
            <div
              key={idx}
              className="rounded-lg border border-gray-200 p-3 space-y-2 bg-gray-50/50"
            >
              <div className="grid grid-cols-12 gap-2">
                <div className="col-span-12 sm:col-span-5">
                  <label className="block text-[11px] text-gray-600">{t('options.row.labelLabel')}</label>
                  <input
                    type="text"
                    value={o.label || ''}
                    onChange={e => update(idx, { label: e.target.value })}
                    maxLength={120}
                    placeholder={t('options.row.labelPlaceholder')}
                    className="w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm focus:border-gray-900 focus:outline-none"
                  />
                </div>
                <div className="col-span-6 sm:col-span-3">
                  <label className="block text-[11px] text-gray-600">{t('options.row.priceLabel')}</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={toInput(o.price)}
                    onChange={e => update(idx, { price: e.target.value === '' ? '' : Number(e.target.value) })}
                    placeholder={t('options.row.pricePlaceholder')}
                    className="w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm focus:border-gray-900 focus:outline-none"
                  />
                </div>
                <div className="col-span-6 sm:col-span-3">
                  <label className="block text-[11px] text-gray-600">{t('options.row.durationLabel')}</label>
                  <input
                    type="number"
                    min="5"
                    max="1440"
                    value={toInput(o.duration_minutes_override)}
                    onChange={e => update(idx, { duration_minutes_override: e.target.value === '' ? '' : Number(e.target.value) })}
                    placeholder={t('options.row.durationPlaceholder')}
                    className="w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm focus:border-gray-900 focus:outline-none"
                  />
                </div>
                <div className="col-span-12 sm:col-span-1 flex sm:flex-col gap-1 items-end justify-end sm:pt-4">
                  <button
                    type="button"
                    onClick={() => move(idx, -1)}
                    disabled={idx === 0}
                    title={t('options.row.moveUp')}
                    className="rounded border border-gray-300 px-1.5 py-0.5 text-xs hover:border-gray-900 disabled:opacity-30"
                  >↑</button>
                  <button
                    type="button"
                    onClick={() => move(idx, +1)}
                    disabled={idx === options.length - 1}
                    title={t('options.row.moveDown')}
                    className="rounded border border-gray-300 px-1.5 py-0.5 text-xs hover:border-gray-900 disabled:opacity-30"
                  >↓</button>
                </div>
              </div>

              <div>
                <label className="block text-[11px] text-gray-600">{t('options.row.descriptionLabel')}</label>
                <input
                  type="text"
                  value={o.description || ''}
                  onChange={e => update(idx, { description: e.target.value })}
                  maxLength={500}
                  placeholder={t('options.row.descriptionPlaceholder')}
                  className="w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm focus:border-gray-900 focus:outline-none"
                />
              </div>

              <div className="flex items-center justify-between">
                <label className="flex items-center gap-1.5 cursor-pointer text-xs text-gray-700">
                  <input
                    type="checkbox"
                    checked={o.is_active !== false}
                    onChange={e => update(idx, { is_active: e.target.checked })}
                    className="rounded border-gray-300"
                  />
                  {t('options.row.isActive')}
                </label>
                <button
                  type="button"
                  onClick={() => remove(idx)}
                  className="text-[11px] text-red-700 hover:underline"
                >{t('options.row.remove')}</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
