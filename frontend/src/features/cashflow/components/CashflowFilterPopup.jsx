/**
 * CashflowFilterPopup — multi-field filter modal for cashflow record
 * tables.
 *
 * Responsive
 * ----------
 * Uses ResponsiveDialog, which mounts a centered Dialog on desktop and
 * a bottom-sheet Drawer on mobile (driven by the useIsMobile hook).
 * The same React tree is rendered in both modes — no JSX duplication.
 *
 * Field rendering
 * ---------------
 * The component is *category-agnostic*: it reads the SCHEMAS map from
 * ``../lib/filterSchemas`` keyed on ``categoryType`` and renders each
 * field according to its declared type. Adding a new product category
 * means a schema entry plus, if needed, a new ``STATIC_OPTIONS`` bucket
 * — never a change in this file.
 *
 * Controlled component
 * --------------------
 * The popup owns no filter state. Parents pass ``value`` (the current
 * filter object) and ``onChange`` (called on every keystroke). The
 * popup uses the live state so the parent's ``filtered`` derives
 * immediately; "Applica" closes the popup but doesn't change semantics
 * — its only job is to let the merchant signal "I'm done tweaking".
 *
 * Props
 * -----
 *   open, onOpenChange — Dialog/Drawer plumbing
 *   categoryType        — 'sales' | 'expenses' | 'purchases' | 'fixed_costs'
 *   value, onChange     — filter object + setter (controlled)
 *   onReset             — called when the user clicks Reset
 *   options             — autocomplete buckets:
 *                         { categories, suppliers, channels, categories_macro }
 *                         (only the buckets the schema references for
 *                         this categoryType are read; unused buckets
 *                         can be omitted)
 *   activeCount         — passed in by the parent for the badge in the
 *                         header (computed via countActiveFilters)
 */

import React, { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { X, RotateCcw } from 'lucide-react';
import {
  ResponsiveDialog,
  ResponsiveDialogContent,
  ResponsiveDialogHeader,
  ResponsiveDialogTitle,
  ResponsiveDialogFooter,
} from '../../../components/ui/responsive-dialog';
import { Button } from '../../../components/ui/button';
import { Input } from '../../../components/ui/input';
import { Label } from '../../../components/ui/label';
import { Badge } from '../../../components/ui/badge';
// MultiSelectDropdown: searchable + creatable multi-select that mirrors
// the dropdown UX of CreatableAutocomplete used in the EntryForms.
// Replaces the "input text + suggestion list" pattern previously used
// here, which was confusing in filter context (no visible list of
// available choices, no clear way to multi-pick).
import MultiSelectDropdown from './MultiSelectDropdown';
import { SCHEMAS, STATIC_OPTIONS } from '../lib/filterSchemas';


export default function CashflowFilterPopup({
  open,
  onOpenChange,
  categoryType,
  value,
  onChange,
  onReset,
  options = {},
  activeCount = 0,
}) {
  const { t } = useTranslation('cashflow_monitor');

  const schema = useMemo(() => SCHEMAS[categoryType] || [], [categoryType]);

  // Shallow setter for one field — keeps the patch immutable so
  // useMemo identity comparisons in the hook work correctly.
  const patch = (next) => {
    onChange({ ...value, ...next });
  };

  return (
    <ResponsiveDialog open={open} onOpenChange={onOpenChange}>
      <ResponsiveDialogContent className="sm:max-w-2xl">
        <ResponsiveDialogHeader>
          <div className="flex items-center justify-between gap-2">
            <ResponsiveDialogTitle className="text-base flex items-center gap-2">
              {t('filters.title')}
              {activeCount > 0 && (
                <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
                  {t('filters.active_count', { count: activeCount })}
                </Badge>
              )}
            </ResponsiveDialogTitle>
            {activeCount > 0 && (
              <Button
                variant="ghost"
                size="sm"
                className="h-7 px-2 text-xs"
                onClick={onReset}
              >
                <RotateCcw className="h-3 w-3 mr-1" />
                {t('filters.reset')}
              </Button>
            )}
          </div>
        </ResponsiveDialogHeader>

        {/* Field list — single column on mobile, fluid on desktop */}
        <div className="space-y-4 py-2 max-h-[60vh] overflow-y-auto sm:max-h-[55vh]">
          {schema.map((field) => (
            <FieldRow
              key={field.key}
              field={field}
              value={value}
              patch={patch}
              options={options}
              t={t}
            />
          ))}
        </div>

        <ResponsiveDialogFooter className="gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onOpenChange(false)}
          >
            <X className="h-3.5 w-3.5 mr-1" />
            {t('filters.close')}
          </Button>
          <Button
            size="sm"
            onClick={() => onOpenChange(false)}
          >
            {t('filters.apply')}
          </Button>
        </ResponsiveDialogFooter>
      </ResponsiveDialogContent>
    </ResponsiveDialog>
  );
}


// ── Field renderers ────────────────────────────────────────────────────

function FieldRow({ field, value, patch, options, t }) {
  return (
    <div>
      <Label className="text-xs font-medium text-muted-foreground mb-1.5 block">
        {t(field.i18nKey)}
      </Label>
      {field.type === 'date_range' && <DateRangeField field={field} value={value} patch={patch} t={t} />}
      {field.type === 'number_range' && <NumberRangeField field={field} value={value} patch={patch} t={t} />}
      {field.type === 'text_contains' && <TextContainsField field={field} value={value} patch={patch} t={t} />}
      {field.type === 'multi_autocomplete' && <MultiAutocompleteField field={field} value={value} patch={patch} options={options} t={t} />}
      {field.type === 'multi_static' && <MultiStaticField field={field} value={value} patch={patch} t={t} />}
      {field.type === 'multi_source' && <MultiSourceField field={field} value={value} patch={patch} t={t} />}
      {field.type === 'tri_state' && <TriStateField field={field} value={value} patch={patch} t={t} />}
    </div>
  );
}

function DateRangeField({ field, value, patch, t }) {
  const fromKey = field.key + '_from';
  const toKey = field.key + '_to';
  return (
    <div className="grid grid-cols-2 gap-2">
      <Input
        type="date"
        value={value[fromKey] || ''}
        onChange={(e) => patch({ [fromKey]: e.target.value })}
        placeholder={t('filters.from')}
        aria-label={t('filters.from')}
      />
      <Input
        type="date"
        value={value[toKey] || ''}
        onChange={(e) => patch({ [toKey]: e.target.value })}
        placeholder={t('filters.to')}
        aria-label={t('filters.to')}
      />
    </div>
  );
}

function NumberRangeField({ field, value, patch, t }) {
  const minKey = field.key + '_min';
  const maxKey = field.key + '_max';
  return (
    <div className="grid grid-cols-2 gap-2">
      <Input
        type="number"
        step="0.01"
        value={value[minKey] ?? ''}
        onChange={(e) => patch({ [minKey]: e.target.value })}
        placeholder={t('filters.min')}
        aria-label={t('filters.min')}
        inputMode="decimal"
      />
      <Input
        type="number"
        step="0.01"
        value={value[maxKey] ?? ''}
        onChange={(e) => patch({ [maxKey]: e.target.value })}
        placeholder={t('filters.max')}
        aria-label={t('filters.max')}
        inputMode="decimal"
      />
    </div>
  );
}

function TextContainsField({ field, value, patch, t }) {
  return (
    <Input
      type="text"
      value={value[field.key] ?? ''}
      onChange={(e) => patch({ [field.key]: e.target.value })}
      placeholder={t('filters.contains_placeholder')}
    />
  );
}

function MultiAutocompleteField({ field, value, patch, options, t }) {
  const bucket = options[field.optionsKey] || [];
  const selected = Array.isArray(value[field.key]) ? value[field.key] : [];
  // i18next plural keys: ``selected_one`` for count===1, ``selected_other``
  // for everything else. Resolved via the t() count-key fallback chain.
  return (
    <MultiSelectDropdown
      value={selected}
      onChange={(next) => patch({ [field.key]: next })}
      options={bucket}
      placeholder={t('filters.select_placeholder')}
      searchPlaceholder={t('filters.search_placeholder')}
      emptyLabel={t('filters.no_results')}
      createLabel={(q) => t('filters.create_label', { value: q })}
      selectedLabel={(count) => t(
        count === 1 ? 'filters.selected_one' : 'filters.selected_other',
        { count }
      )}
      moreOptionsHint={(count) => t('filters.more_options_hint', { count })}
    />
  );
}

function MultiStaticField({ field, value, patch, t }) {
  const bucket = STATIC_OPTIONS[field.staticOptions] || [];
  const selected = Array.isArray(value[field.key]) ? value[field.key] : [];
  const toggle = (v) => {
    if (selected.includes(v)) {
      patch({ [field.key]: selected.filter((x) => x !== v) });
    } else {
      patch({ [field.key]: [...selected, v] });
    }
  };
  return (
    <div className="flex flex-wrap gap-1.5">
      {bucket.map((opt) => {
        const active = selected.includes(opt.value);
        const label = opt.i18nKey ? t(opt.i18nKey) : opt.label;
        return (
          <button
            key={opt.value}
            type="button"
            onClick={() => toggle(opt.value)}
            className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors border ${
              active
                ? 'bg-primary text-primary-foreground border-primary'
                : 'bg-background text-muted-foreground border-input hover:bg-muted'
            }`}
          >
            {label}
          </button>
        );
      })}
    </div>
  );
}

function MultiSourceField({ field, value, patch, t }) {
  // Identical visual to MultiStaticField but uses SOURCES bucket.
  const bucket = STATIC_OPTIONS.SOURCES;
  const selected = Array.isArray(value[field.key]) ? value[field.key] : [];
  const toggle = (v) => {
    if (selected.includes(v)) {
      patch({ [field.key]: selected.filter((x) => x !== v) });
    } else {
      patch({ [field.key]: [...selected, v] });
    }
  };
  return (
    <div className="flex flex-wrap gap-1.5">
      {bucket.map((opt) => {
        const active = selected.includes(opt.value);
        return (
          <button
            key={opt.value}
            type="button"
            onClick={() => toggle(opt.value)}
            className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors border ${
              active
                ? 'bg-primary text-primary-foreground border-primary'
                : 'bg-background text-muted-foreground border-input hover:bg-muted'
            }`}
          >
            {t(opt.i18nKey)}
          </button>
        );
      })}
    </div>
  );
}

function TriStateField({ field, value, patch, t }) {
  const v = value[field.key] || '';
  // Documented values: '' (any), 'active', 'inactive'.
  const options = [
    { value: '', label: t('filters.any') },
    { value: 'active', label: t('sections.active_badge') },
    { value: 'inactive', label: t('sections.inactive_badge') },
  ];
  return (
    <div className="flex flex-wrap gap-1.5">
      {options.map((opt) => {
        const active = v === opt.value;
        return (
          <button
            key={opt.value || 'any'}
            type="button"
            onClick={() => patch({ [field.key]: opt.value })}
            className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors border ${
              active
                ? 'bg-primary text-primary-foreground border-primary'
                : 'bg-background text-muted-foreground border-input hover:bg-muted'
            }`}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
