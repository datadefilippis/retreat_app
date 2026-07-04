/**
 * FieldEditorList — reusable editor for a list of merchant-defined
 * custom form fields (F2 Onda 9).
 *
 * Used in two places:
 *   - EventWizard Tab "Biglietti" → configures order_fields + attendee_fields
 *     on a brand-new product.
 *   - EventDashboardPage product panel → edits the same on an existing one.
 *
 * Contract:
 *   <FieldEditorList
 *     fields={fields}            // FieldConfig[]
 *     onChange={(next) => ...}   // fires with the full new array
 *     title="Campi aggiuntivi partecipante"
 *     subtitle="Chiesti per ogni biglietto"
 *     addButtonLabel="+ Aggiungi campo"
 *     allowedTypes={['text', 'textarea', 'number']}  // optional, defaults to MVP set
 *     emptyHint="Nessun campo. Clicca + Aggiungi campo per iniziare."
 *   />
 *
 * Each field in the array has the shape:
 *   { id, label, type, required, placeholder?, help_text?, sort_order }
 *
 * The component auto-generates a stable `id` from the label when the admin
 * first types a label (slugify). Admin can edit it later to fix collisions,
 * but the input visible by default is the label — keeps UI friendly.
 */

import React, { useCallback, useState } from 'react';
import { useTranslation } from 'react-i18next';


const DEFAULT_TYPES = ['text', 'textarea', 'number'];


function slugify(s) {
  return String(s || '')
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')
    .slice(0, 40);
}


export default function FieldEditorList({
  fields = [],
  onChange,
  title,
  subtitle,
  addButtonLabel = null,
  allowedTypes = DEFAULT_TYPES,
  emptyHint = null,
}) {
  const { t } = useTranslation('products');
  const displayAddButtonLabel = addButtonLabel ?? t('fields.addButton');
  const displayEmptyHint = emptyHint ?? t('fields.emptyHint');
  // Track which fields have a user-edited `id` (don't auto-sync from label
  // after manual edit).
  const [manualIdByIndex, setManualIdByIndex] = useState({});

  const update = useCallback((idx, patch) => {
    const next = fields.map((f, i) => (i === idx ? { ...f, ...patch } : f));
    onChange(next);
  }, [fields, onChange]);

  const add = useCallback(() => {
    const newField = {
      id: `field_${Date.now().toString(36).slice(-5)}`,
      label: '',
      type: allowedTypes[0] || 'text',
      required: false,
      placeholder: '',
      help_text: '',
      sort_order: fields.length,
    };
    onChange([...fields, newField]);
  }, [fields, onChange, allowedTypes]);

  const remove = useCallback((idx) => {
    const next = fields.filter((_, i) => i !== idx);
    onChange(next);
    setManualIdByIndex(m => {
      const { [idx]: _, ...rest } = m;
      return rest;
    });
  }, [fields, onChange]);

  const move = useCallback((idx, delta) => {
    const j = idx + delta;
    if (j < 0 || j >= fields.length) return;
    const next = [...fields];
    [next[idx], next[j]] = [next[j], next[idx]];
    // Re-sync sort_order
    next.forEach((f, i) => { f.sort_order = i; });
    onChange(next);
  }, [fields, onChange]);

  const onLabelChange = (idx, label) => {
    const patch = { label };
    // Auto-generate id from label when the admin hasn't manually edited it
    if (!manualIdByIndex[idx]) {
      const generated = slugify(label);
      if (generated) patch.id = generated;
    }
    update(idx, patch);
  };

  const onIdChange = (idx, id) => {
    setManualIdByIndex(m => ({ ...m, [idx]: true }));
    update(idx, { id: slugify(id) });
  };

  // Duplicate-id detection across fields
  const idCounts = fields.reduce((acc, f) => {
    const k = f.id || '';
    acc[k] = (acc[k] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          {title && <h3 className="text-sm font-semibold text-gray-900">{title}</h3>}
          {subtitle && <p className="text-xs text-gray-500 mt-0.5">{subtitle}</p>}
        </div>
        <button
          type="button"
          onClick={add}
          className="shrink-0 text-xs font-semibold rounded-md bg-gray-900 text-white px-3 py-1.5 hover:bg-gray-800"
        >
          {displayAddButtonLabel}
        </button>
      </div>

      {fields.length === 0 ? (
        <p className="text-xs text-gray-500 italic">{displayEmptyHint}</p>
      ) : (
        <div className="space-y-2">
          {fields.map((f, idx) => {
            const idDup = (f.id && idCounts[f.id] > 1);
            return (
              <div
                key={idx}
                className="rounded-lg border border-gray-200 p-3 space-y-2 bg-gray-50/50"
              >
                <div className="grid grid-cols-12 gap-2">
                  <div className="col-span-12 sm:col-span-5">
                    <label className="block text-[11px] text-gray-600">{t('fields.row.labelLabel')}</label>
                    <input
                      type="text"
                      value={f.label || ''}
                      onChange={e => onLabelChange(idx, e.target.value)}
                      maxLength={120}
                      placeholder={t('fields.row.labelPlaceholder')}
                      className="w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm focus:border-gray-900 focus:outline-none"
                    />
                  </div>
                  <div className="col-span-7 sm:col-span-3">
                    <label className="block text-[11px] text-gray-600">{t('fields.row.typeLabel')}</label>
                    <select
                      value={f.type || 'text'}
                      onChange={e => update(idx, { type: e.target.value })}
                      className="w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm bg-white focus:border-gray-900 focus:outline-none"
                    >
                      {allowedTypes.map(typeKey => (
                        <option key={typeKey} value={typeKey}>{t(`fields.typeLabel.${typeKey}`, { defaultValue: typeKey })}</option>
                      ))}
                    </select>
                  </div>
                  <div className="col-span-5 sm:col-span-2 flex items-end">
                    <label className="flex items-center gap-1.5 cursor-pointer text-xs text-gray-700">
                      <input
                        type="checkbox"
                        checked={!!f.required}
                        onChange={e => update(idx, { required: e.target.checked })}
                        className="rounded border-gray-300"
                      />
                      {t('fields.row.required')}
                    </label>
                  </div>
                  <div className="col-span-12 sm:col-span-2 flex items-end gap-1">
                    <button
                      type="button"
                      onClick={() => move(idx, -1)}
                      disabled={idx === 0}
                      title={t('fields.row.moveUp')}
                      className="rounded border border-gray-300 px-1.5 py-0.5 text-xs hover:border-gray-900 disabled:opacity-30"
                    >↑</button>
                    <button
                      type="button"
                      onClick={() => move(idx, +1)}
                      disabled={idx === fields.length - 1}
                      title={t('fields.row.moveDown')}
                      className="rounded border border-gray-300 px-1.5 py-0.5 text-xs hover:border-gray-900 disabled:opacity-30"
                    >↓</button>
                    <button
                      type="button"
                      onClick={() => remove(idx)}
                      title={t('fields.row.remove')}
                      className="rounded border border-gray-300 px-1.5 py-0.5 text-xs text-red-700 hover:border-red-500"
                    >🗑</button>
                  </div>
                </div>

                {/* Placeholder + id (secondary row) */}
                <div className="grid grid-cols-12 gap-2">
                  <div className="col-span-12 sm:col-span-8">
                    <label className="block text-[11px] text-gray-600">{t('fields.row.placeholderLabel')}</label>
                    <input
                      type="text"
                      value={f.placeholder || ''}
                      onChange={e => update(idx, { placeholder: e.target.value })}
                      maxLength={120}
                      placeholder={t('fields.row.placeholderPlaceholder')}
                      className="w-full rounded-md border border-gray-300 px-2 py-1.5 text-xs focus:border-gray-900 focus:outline-none"
                    />
                  </div>
                  <div className="col-span-12 sm:col-span-4">
                    <label className="block text-[11px] text-gray-600">
                      {t('fields.row.idLabel')} {idDup && <span className="text-red-600">{t('fields.row.idDuplicate')}</span>}
                    </label>
                    <input
                      type="text"
                      value={f.id || ''}
                      onChange={e => onIdChange(idx, e.target.value)}
                      maxLength={40}
                      placeholder={t('fields.row.idPlaceholder')}
                      className={`w-full rounded-md border px-2 py-1.5 text-xs font-mono focus:outline-none ${
                        idDup ? 'border-red-400 bg-red-50' : 'border-gray-300 focus:border-gray-900'
                      }`}
                    />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
