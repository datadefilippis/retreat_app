/**
 * MultiSelectDropdown — searchable multi-select with creatable values.
 *
 * Designed specifically for the cashflow filter popup (lives inside a
 * Dialog / Drawer / Sheet). For that reason it does NOT render its
 * dropdown into a Radix Popover portal — nested overlays inside an
 * already-portaled container behave inconsistently on touch devices
 * (the dropdown can end up hidden behind the Drawer scrim, or the
 * outside-click handler closes the wrong layer).
 *
 * Instead, the expanded panel is rendered INLINE below the trigger as
 * a sibling. Layout-wise this means the parent container needs to allow
 * vertical growth — the cashflow filter popup already has overflow-y on
 * the content area so this works naturally. On collapse the panel
 * disappears (display: none) so the surrounding layout reflows back.
 *
 * UX shape
 * --------
 *   Trigger        : button showing "{count} selezionati" / "Seleziona…"
 *                    + chevron. Click toggles the panel.
 *   Panel          : <input type="text"> search bar +
 *                    scrollable list of options, each rendered as a
 *                    button-row with a check icon when selected.
 *                    A "+ Aggiungi: {query}" row appears at the top
 *                    when the user's search matches no existing option
 *                    (the parent's data is "creatable" — same pattern
 *                    as CreatableAutocomplete in the EntryForms).
 *   Selected chips : Badge list below the trigger. Click a chip → it
 *                    is removed from the selection.
 *
 * Props
 * -----
 *   value         — string[] of currently selected values
 *   onChange      — (next: string[]) => void
 *   options       — string[] suggestions from the API
 *   placeholder   — placeholder for the trigger when nothing is selected
 *   searchPlaceholder — placeholder for the panel's search input
 *   emptyLabel    — label shown when search matches no options and no
 *                   creatable hint is shown
 *   createLabel   — function (query) => string for the "+ Add" row
 *   maxOptions    — cap how many filtered options the list renders
 *                   (defaults to 50; keeps long lists snappy)
 *   selectedLabel — (count) => string for the trigger when count > 0.
 *                   Lets the parent inject pluralized i18n strings;
 *                   defaults to a hard-coded English fallback.
 *   moreOptionsHint — (count) => string for the "+ N more" footer
 *                     hint shown when options.length exceeds maxOptions.
 */

import React, { useState, useRef, useEffect, useMemo } from 'react';
import { ChevronDown, X, Check, Search, Plus } from 'lucide-react';
import { Badge } from '../../../components/ui/badge';


export default function MultiSelectDropdown({
  value = [],
  onChange,
  options = [],
  placeholder = 'Seleziona…',
  searchPlaceholder = 'Cerca…',
  emptyLabel = 'Nessun risultato',
  createLabel = (q) => `+ Aggiungi: "${q}"`,
  selectedLabel = (count) => `${count} selected`,
  moreOptionsHint = (count) => `+ ${count} more`,
  maxOptions = 50,
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const wrapRef = useRef(null);
  const inputRef = useRef(null);

  // Close panel on click outside the wrapper. Listens to the document
  // so taps on the surrounding Dialog scrim also close it — same UX as
  // the EntryForm's CreatableAutocomplete.
  useEffect(() => {
    if (!open) return;
    const handler = (e) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) {
        setOpen(false);
        setQuery('');
      }
    };
    document.addEventListener('mousedown', handler);
    document.addEventListener('touchstart', handler);
    return () => {
      document.removeEventListener('mousedown', handler);
      document.removeEventListener('touchstart', handler);
    };
  }, [open]);

  // Auto-focus the search input when the panel opens so the user can
  // start typing immediately. Use a microtask delay so the input
  // exists in the DOM by the time we reach for it.
  useEffect(() => {
    if (open) {
      queueMicrotask(() => inputRef.current?.focus());
    }
  }, [open]);

  // Filter options against the search query (case-insensitive
  // substring). Already-selected entries are kept in the list so the
  // user can spot what they already picked — we just show a check icon
  // next to them. Capped to ``maxOptions`` for performance on suppliers
  // / categories lists that can grow into the hundreds.
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return options.slice(0, maxOptions);
    return options
      .filter((o) => o.toLowerCase().includes(q))
      .slice(0, maxOptions);
  }, [query, options, maxOptions]);

  // Whether the user's typed value is a brand new entry (not in the
  // options list, not already selected). Drives the "+ Add" row.
  const trimmedQuery = query.trim();
  const canCreate =
    trimmedQuery.length > 0 &&
    !options.some((o) => o.toLowerCase() === trimmedQuery.toLowerCase()) &&
    !value.some((v) => v.toLowerCase() === trimmedQuery.toLowerCase());

  const toggle = (opt) => {
    if (value.includes(opt)) {
      onChange(value.filter((v) => v !== opt));
    } else {
      onChange([...value, opt]);
    }
  };

  const create = () => {
    if (!canCreate) return;
    onChange([...value, trimmedQuery]);
    setQuery('');
  };

  const removeChip = (v) => {
    onChange(value.filter((x) => x !== v));
  };

  // Label inside the trigger button: number of selected values for
  // brevity (the chips below the trigger show the actual values).
  // selectedLabel is passed in by the parent with the right pluralized
  // i18n form — falls back to a plain English string if omitted.
  const triggerLabel = value.length === 0
    ? placeholder
    : selectedLabel(value.length);

  return (
    <div ref={wrapRef} className="relative">
      {/* Trigger button — same border / hover styling as the search
          input in CreatableAutocomplete so the popup feels consistent. */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className={`w-full flex items-center justify-between gap-2 rounded-md border bg-background px-3 py-2 text-sm transition-colors hover:bg-muted/50 ${
          value.length > 0 ? 'border-primary/40' : 'border-input'
        }`}
        aria-expanded={open}
        aria-haspopup="listbox"
      >
        <span className={value.length === 0 ? 'text-muted-foreground' : ''}>
          {triggerLabel}
        </span>
        <ChevronDown
          className={`h-4 w-4 text-muted-foreground transition-transform ${open ? 'rotate-180' : ''}`}
        />
      </button>

      {/* Inline panel (NOT a Popover — see file docstring for the why) */}
      {open && (
        <div className="mt-1 rounded-md border bg-popover shadow-md overflow-hidden">
          {/* Search input */}
          <div className="flex items-center gap-2 border-b px-3 py-2">
            <Search className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={searchPlaceholder}
              className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
              onKeyDown={(e) => {
                // Enter when search hits nothing creates the new value.
                if (e.key === 'Enter' && canCreate) {
                  e.preventDefault();
                  create();
                }
                // Escape closes the panel.
                if (e.key === 'Escape') {
                  e.preventDefault();
                  setOpen(false);
                  setQuery('');
                }
              }}
            />
          </div>

          {/* Options list — capped at maxOptions with a quiet hint when
              the cap kicks in. The list is scrollable so the parent
              popup never overflows the viewport. */}
          <div className="max-h-48 overflow-y-auto py-1">
            {canCreate && (
              <button
                type="button"
                onClick={create}
                className="w-full flex items-center gap-2 px-3 py-1.5 text-sm text-left hover:bg-muted/70"
              >
                <Plus className="h-3.5 w-3.5 text-primary shrink-0" />
                <span className="truncate">{createLabel(trimmedQuery)}</span>
              </button>
            )}

            {filtered.length === 0 && !canCreate && (
              <p className="px-3 py-2 text-xs text-muted-foreground text-center">
                {emptyLabel}
              </p>
            )}

            {filtered.map((opt) => {
              const selected = value.includes(opt);
              return (
                <button
                  key={opt}
                  type="button"
                  onClick={() => toggle(opt)}
                  className={`w-full flex items-center justify-between gap-2 px-3 py-1.5 text-sm text-left hover:bg-muted/70 ${
                    selected ? 'bg-muted/40' : ''
                  }`}
                >
                  <span className="truncate">{opt}</span>
                  {selected && <Check className="h-3.5 w-3.5 text-primary shrink-0" />}
                </button>
              );
            })}

            {options.length > maxOptions && !query && (
              <p className="px-3 pt-1.5 pb-1 text-[10px] text-muted-foreground italic text-center">
                {moreOptionsHint(options.length - maxOptions)}
              </p>
            )}
          </div>
        </div>
      )}

      {/* Selected chips — always visible below the trigger so the user
          sees what is filtering even when the panel is collapsed. */}
      {value.length > 0 && (
        <div className="mt-1.5 flex flex-wrap gap-1">
          {value.map((v) => (
            <Badge
              key={v}
              variant="secondary"
              className="text-xs gap-1 cursor-pointer hover:bg-secondary/70 max-w-[200px]"
              onClick={() => removeChip(v)}
            >
              <span className="truncate">{v}</span>
              <X className="h-2.5 w-2.5 shrink-0" />
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
}
