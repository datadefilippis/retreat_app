/**
 * ProductExtrasEditor — inline CRUD for ProductExtra rows on any product
 * (Onda 16 Prenotazione consolidation).
 *
 * Generalizes the ServiceOptionsEditor pattern with three distinct kinds:
 *   - mandatory:    auto-applied at checkout (e.g. B&B cleaning fee)
 *   - optional:     customer opts in via checkbox (e.g. breakfast)
 *   - radio_variant: mutually exclusive within a group_key
 *                   (e.g. car insurance basic/full)
 *
 * Contract:
 *   <ProductExtrasEditor
 *     extras={extras}              // ProductExtra[] — full list of all kinds
 *     onChange={(next) => ...}     // fires with the full updated array
 *     productItemType="rental"     // optional, hides irrelevant per_day on non-range types
 *     title="Extras & opzioni"
 *   />
 *
 * Each extra:
 *   { id?, kind, group_key?, label, description?, price, price_modifier_type,
 *     duration_minutes_override?, is_default?, sort_order, is_active,
 *     _localId? }  // internal React key — NEVER send to backend
 *
 * IDs are optional; the backend assigns them on create. Local edits use
 * a `_localId` key internally to track unsaved rows without id collisions.
 *
 * IMPORTANT — focus stability contract:
 *   onChange payloads include `_localId` on each row. The parent MUST preserve
 *   `_localId` unchanged across edits and strip it only right before calling
 *   the backend API. Stripping `_localId` between keystrokes causes React to
 *   regenerate the key for every row with no persistent `id`, unmounting the
 *   inputs and losing focus.
 */

import React, { useCallback, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';


// Static keys for the dispatch tables. Labels are resolved at render
// time from the `products` namespace so language switching is reactive
// and JSON ownership is centralised — no Italian fallback hardcoded
// in this file. The `defaultValue` on each `t()` call below is a safety
// net for the (impossible) case where products.json is missing/empty
// at runtime; in normal operation the JSON drives the UI.
const KIND_KEYS = ['mandatory', 'optional', 'radio_variant'];
const MODIFIER_KEYS_DEFAULT = ['flat', 'per_unit'];
const MODIFIER_KEYS_RENTAL = ['flat', 'per_day', 'per_unit'];


function localId() {
  return `local-${Math.random().toString(36).slice(2, 10)}`;
}


function ExtraRow({ extra, onPatch, onRemove, onMove, isFirst, isLast, showPerDay }) {
  const { t } = useTranslation('products');
  const modifierKeys = showPerDay ? MODIFIER_KEYS_RENTAL : MODIFIER_KEYS_DEFAULT;

  return (
    <div className="grid grid-cols-[auto_1fr_auto] gap-2 items-start rounded-lg border border-gray-200 bg-gray-50/40 p-2.5">
      <div className="flex flex-col gap-1 pt-1">
        <button
          type="button"
          onClick={() => onMove(-1)}
          disabled={isFirst}
          className="text-xs text-gray-500 hover:text-gray-800 disabled:opacity-30"
          title={t('extras.row.moveUp')}
        >▲</button>
        <button
          type="button"
          onClick={() => onMove(+1)}
          disabled={isLast}
          className="text-xs text-gray-500 hover:text-gray-800 disabled:opacity-30"
          title={t('extras.row.moveDown')}
        >▼</button>
      </div>

      <div className="space-y-2 min-w-0">
        <div className="grid grid-cols-1 sm:grid-cols-[1fr_120px_140px] gap-2">
          <input
            type="text"
            value={extra.label || ''}
            onChange={(e) => onPatch({ label: e.target.value })}
            placeholder={t('extras.row.namePlaceholder')}
            className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:ring-2 focus:ring-gray-800 focus:border-transparent outline-none"
            maxLength={120}
          />
          <div className="flex">
            <span className="inline-flex items-center rounded-l border border-r-0 border-gray-300 bg-gray-100 px-2 text-xs text-gray-500">€</span>
            <input
              type="number"
              step="0.01"
              min="0"
              value={extra.price ?? ''}
              onChange={(e) => onPatch({ price: e.target.value === '' ? '' : parseFloat(e.target.value) })}
              placeholder="0.00"
              className="w-full rounded-r border border-gray-300 px-2 py-1.5 text-sm focus:ring-2 focus:ring-gray-800 focus:border-transparent outline-none"
            />
          </div>
          <select
            value={extra.price_modifier_type || 'flat'}
            onChange={(e) => onPatch({ price_modifier_type: e.target.value })}
            className="rounded border border-gray-300 px-2 py-1.5 text-sm focus:ring-2 focus:ring-gray-800 focus:border-transparent outline-none"
          >
            {modifierKeys.map(m => (
              <option key={m} value={m}>{t(`extras.modifier.${m}`)}</option>
            ))}
          </select>
        </div>
        <input
          type="text"
          value={extra.description || ''}
          onChange={(e) => onPatch({ description: e.target.value })}
          placeholder={t('extras.row.descriptionPlaceholder')}
          maxLength={500}
          className="w-full rounded border border-gray-300 px-2 py-1.5 text-xs text-gray-700 focus:ring-2 focus:ring-gray-800 focus:border-transparent outline-none"
        />
        <div className="flex flex-wrap items-center gap-3 text-xs">
          {extra.kind !== 'mandatory' && (
            <label className="flex items-center gap-1.5 text-gray-600">
              <input
                type="checkbox"
                checked={!!extra.is_default}
                onChange={(e) => onPatch({ is_default: e.target.checked })}
              />
              {extra.kind === 'radio_variant'
                ? t('extras.row.isDefaultRadio')
                : t('extras.row.isDefault')}
            </label>
          )}
          <label className="flex items-center gap-1.5 text-gray-600">
            <input
              type="checkbox"
              checked={extra.is_active !== false}
              onChange={(e) => onPatch({ is_active: e.target.checked })}
            />
            {t('extras.row.isActive')}
          </label>
        </div>
      </div>

      <button
        type="button"
        onClick={onRemove}
        className="text-xs text-red-600 hover:text-red-800 px-2 py-1"
        title={t('extras.row.remove')}
      >{t('extras.row.remove')}</button>
    </div>
  );
}


export default function ProductExtrasEditor({
  extras = [],
  onChange,
  productItemType,
  // `title` is now optional. When the consumer doesn't pass one we fall
  // back to the localized default in the products namespace. Consumers
  // that already pass a custom title (e.g. "Camera fee" on a specific
  // dashboard) keep that exact behaviour — `??` only kicks in for
  // undefined / null.
  title = null,
}) {
  const { t } = useTranslation('products');
  const [activeKind, setActiveKind] = useState('mandatory');
  const [radioGroupFilter, setRadioGroupFilter] = useState(null);
  const [newGroupName, setNewGroupName] = useState('');
  const displayTitle = title ?? t('extras.title');

  const showPerDay = productItemType === 'rental';

  // Ensure every row has a stable localId for React keys.
  const normalizedExtras = useMemo(() => {
    return extras.map(e => ({ ...e, _localId: e._localId || e.id || localId() }));
  }, [extras]);

  const rowsByKind = useMemo(() => {
    const by = { mandatory: [], optional: [], radio_variant: [] };
    normalizedExtras.forEach(e => {
      if (by[e.kind]) by[e.kind].push(e);
    });
    return by;
  }, [normalizedExtras]);

  // Radio groups = all distinct group_keys in radio_variant rows.
  const radioGroups = useMemo(() => {
    const set = new Set();
    rowsByKind.radio_variant.forEach(e => { if (e.group_key) set.add(e.group_key); });
    return Array.from(set);
  }, [rowsByKind.radio_variant]);

  // When the user switches to radio_variant tab and no group filter is set,
  // default to the first group (or null if none exists).
  const effectiveGroup = radioGroupFilter !== null
    ? radioGroupFilter
    : (radioGroups[0] || null);

  // Note on onChange payloads: we emit the full normalized list INCLUDING the
  // internal `_localId` key on every row. The parent is expected to preserve
  // `_localId` unchanged on re-render and strip it only when calling the API.
  // Stripping it between keystrokes would regenerate keys → unmount inputs →
  // focus loss.

  const patch = useCallback((target, patchObj) => {
    const next = normalizedExtras.map(e => (
      e._localId === target._localId ? { ...e, ...patchObj } : e
    ));
    onChange(next);
  }, [normalizedExtras, onChange]);

  const remove = useCallback((target) => {
    const next = normalizedExtras.filter(e => e._localId !== target._localId);
    onChange(next);
  }, [normalizedExtras, onChange]);

  const move = useCallback((target, delta) => {
    const bucket = normalizedExtras
      .filter(e => e.kind === target.kind &&
        (target.kind !== 'radio_variant' || e.group_key === target.group_key))
      .map(e => e._localId);
    const idx = bucket.indexOf(target._localId);
    const j = idx + delta;
    if (j < 0 || j >= bucket.length) return;
    const swapWith = bucket[j];
    const next = normalizedExtras.map(e => {
      if (e._localId === target._localId) return { ...e, sort_order: j };
      if (e._localId === swapWith) return { ...e, sort_order: idx };
      return e;
    });
    onChange(next);
  }, [normalizedExtras, onChange]);

  const addRow = useCallback((kind, groupKey = null) => {
    const bucket = normalizedExtras.filter(e =>
      e.kind === kind && (kind !== 'radio_variant' || e.group_key === groupKey)
    );
    // Assign `_localId` up-front so the newly-added row has a stable React
    // key from its first render.
    const newRow = {
      _localId: localId(),
      kind,
      group_key: groupKey,
      label: '',
      description: '',
      price: '',
      price_modifier_type: 'flat',
      is_default: false,
      sort_order: bucket.length,
      is_active: true,
    };
    onChange([...normalizedExtras, newRow]);
  }, [normalizedExtras, onChange]);

  const createGroup = useCallback(() => {
    const name = newGroupName.trim();
    if (!name) return;
    // Slug it to avoid whitespace in group_key.
    const groupKey = name.toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, '').slice(0, 80);
    if (!groupKey) return;
    addRow('radio_variant', groupKey);
    setRadioGroupFilter(groupKey);
    setNewGroupName('');
  }, [newGroupName, addRow]);

  return (
    <div className="space-y-3">
      <div>
        <h3 className="text-base font-semibold text-gray-900">{displayTitle}</h3>
        <p className="text-xs text-gray-500">{t(`extras.kindHint.${activeKind}`)}</p>
      </div>

      {/* Kind tabs */}
      <div className="flex rounded-lg border border-gray-200 overflow-hidden text-sm">
        {KIND_KEYS.map((k) => (
          <button
            key={k}
            type="button"
            onClick={() => setActiveKind(k)}
            className={`flex-1 px-3 py-2 transition-colors ${
              activeKind === k
                ? 'bg-gray-900 text-white'
                : 'bg-white text-gray-600 hover:bg-gray-50'
            }`}
          >
            {t(`extras.kindLabel.${k}`)}
            <span className="ml-1.5 text-xs opacity-70">({rowsByKind[k]?.length || 0})</span>
          </button>
        ))}
      </div>

      {/* Mandatory + Optional — flat list */}
      {(activeKind === 'mandatory' || activeKind === 'optional') && (
        <div className="space-y-2">
          {rowsByKind[activeKind].length === 0 ? (
            <p className="text-xs text-gray-400 italic">{t('extras.emptyList')}</p>
          ) : (
            rowsByKind[activeKind].map((e, i, arr) => (
              <ExtraRow
                key={e._localId}
                extra={e}
                onPatch={(p) => patch(e, p)}
                onRemove={() => remove(e)}
                onMove={(d) => move(e, d)}
                isFirst={i === 0}
                isLast={i === arr.length - 1}
                showPerDay={showPerDay}
              />
            ))
          )}
          <button
            type="button"
            onClick={() => addRow(activeKind)}
            className="rounded-md border border-dashed border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 hover:border-gray-400"
          >
            {activeKind === 'mandatory' ? t('extras.addMandatory') : t('extras.addOptional')}
          </button>
        </div>
      )}

      {/* Radio variant — grouped by group_key */}
      {activeKind === 'radio_variant' && (
        <div className="space-y-3">
          {radioGroups.length > 0 && (
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs font-medium text-gray-700">{t('extras.radio.groupLabel')}</span>
              {radioGroups.map(g => (
                <button
                  key={g}
                  type="button"
                  onClick={() => setRadioGroupFilter(g)}
                  className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors border ${
                    effectiveGroup === g
                      ? 'bg-gray-900 text-white border-gray-900'
                      : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'
                  }`}
                >{g}</button>
              ))}
            </div>
          )}

          {/* New group creator */}
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={newGroupName}
              onChange={(e) => setNewGroupName(e.target.value)}
              placeholder={t('extras.radio.newGroupPlaceholder')}
              className="flex-1 rounded border border-gray-300 px-2 py-1.5 text-sm focus:ring-2 focus:ring-gray-800 focus:border-transparent outline-none"
              maxLength={80}
            />
            <button
              type="button"
              onClick={createGroup}
              disabled={!newGroupName.trim()}
              className="rounded-md bg-gray-900 text-white text-xs font-semibold px-3 py-1.5 disabled:opacity-40"
            >{t('extras.radio.newGroupButton')}</button>
          </div>

          {effectiveGroup && (
            <div className="space-y-2">
              <div className="text-xs text-gray-500">
                {t('extras.radio.groupHint', { group: effectiveGroup })}
              </div>
              {rowsByKind.radio_variant
                .filter(e => e.group_key === effectiveGroup)
                .map((e, i, arr) => (
                  <ExtraRow
                    key={e._localId}
                    extra={e}
                    onPatch={(p) => patch(e, p)}
                    onRemove={() => remove(e)}
                    onMove={(d) => move(e, d)}
                    isFirst={i === 0}
                    isLast={i === arr.length - 1}
                    showPerDay={showPerDay}
                  />
                ))}
              <button
                type="button"
                onClick={() => addRow('radio_variant', effectiveGroup)}
                className="rounded-md border border-dashed border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 hover:border-gray-400"
              >{t('extras.addRadioVariant', { group: effectiveGroup })}</button>
            </div>
          )}

          {!effectiveGroup && radioGroups.length === 0 && (
            <p className="text-xs text-gray-400 italic">{t('extras.radio.emptyHint')}</p>
          )}
        </div>
      )}
    </div>
  );
}
