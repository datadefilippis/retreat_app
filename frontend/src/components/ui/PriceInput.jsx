/**
 * PriceInput — locale-aware currency/decimal input.
 *
 * 2026-05-20 — Drop-in replacement for ``<input type="number" step="0.01">``
 * across the wizard forms. Italian users could not enter "10,50" because
 * HTML5 ``type="number"`` rejects the comma in the Italian locale. This
 * component:
 *
 *   · Renders ``type="text"`` with ``inputMode="decimal"`` so mobile gets
 *     the decimal keyboard but desktop accepts BOTH "," and ".".
 *   · Accepts the in-progress string as the caller's state — lets the
 *     user type freely without normalisation eating the comma.
 *   · Calls ``onValueChange(numericValue, rawString)`` with TWO values:
 *       numericValue: number | null  (what to submit)
 *       rawString:    string         (what to render in the next paint)
 *     So the parent can store EITHER the raw string OR the parsed number,
 *     depending on its existing state shape.
 *
 * The component is intentionally NOT a controlled-by-number-only input —
 * if we forced ``value`` to be a number we'd have to re-format on every
 * keystroke and the user would see their typing weirdly mangled.
 *
 * Backward-compat with existing wizard code:
 *   · Accepts a ``value`` prop that may be number, string, or null.
 *   · Forwards all other HTML props (id, name, placeholder, className,
 *     disabled, autoFocus, ...) to the underlying Input.
 *   · Has a default ``min={0}`` (no negative prices) — caller can override.
 *
 * Validation:
 *   · ``min`` / ``max`` are enforced at parse time (out-of-range → null).
 *   · ``decimals`` (default 2) controls how many decimals the parser keeps
 *     when the value is committed via ``onBlur``.
 */

import React, { useCallback, useEffect, useRef, useState } from 'react';

import { Input } from './input';
import {
  parseLocaleNumber,
  isValidDecimalInput,
  formatLocaleNumber,
} from '../../lib/decimalParsing';


export const PriceInput = React.forwardRef(function PriceInput(
  {
    value,
    onValueChange,
    onChange,         // legacy event handler — still forwarded but secondary
    min = 0,
    max,
    decimals = 2,
    placeholder,
    disabled,
    className,
    ...rest
  },
  ref,
) {
  // ── Local string state to avoid the "controlled number" problem ────
  // The parent may pass a number OR a string OR null as ``value``. We
  // mirror it locally as the display string, normalising only on
  // mount + when the parent value changes to something materially
  // different (so external resets like "clear form" still work).
  const [display, setDisplay] = useState(() =>
    _initialDisplay(value, decimals),
  );

  // Track whether the user is mid-edit. While editing we do NOT echo
  // the parent's reformatted value back, otherwise the cursor jumps.
  const editingRef = useRef(false);

  useEffect(() => {
    if (editingRef.current) return;
    setDisplay(_initialDisplay(value, decimals));
  }, [value, decimals]);

  const handleChange = useCallback((e) => {
    const next = e.target.value;
    editingRef.current = true;
    if (!isValidDecimalInput(next)) {
      // Reject the keystroke silently — keep previous display.
      return;
    }
    setDisplay(next);
    const parsed = parseLocaleNumber(next, { min, max });
    if (onValueChange) onValueChange(parsed, next);
    if (onChange) onChange(e);
  }, [min, max, onValueChange, onChange]);

  const handleBlur = useCallback((e) => {
    editingRef.current = false;
    const parsed = parseLocaleNumber(display, { min, max });
    // On blur, re-format to a canonical N-decimal string so the field
    // looks tidy ("10,5" → "10,50"). If parsing failed, clear the field
    // so the user sees no stale typo + the parent gets null.
    if (parsed == null) {
      setDisplay('');
      if (onValueChange) onValueChange(null, '');
    } else {
      const normalised = formatLocaleNumber(parsed, { decimals });
      setDisplay(normalised);
      if (onValueChange) onValueChange(parsed, normalised);
    }
    if (rest.onBlur) rest.onBlur(e);
  }, [display, min, max, decimals, onValueChange, rest]);

  return (
    <Input
      ref={ref}
      type="text"
      inputMode="decimal"
      autoComplete="off"
      // pattern hint for mobile autofill heuristics; not a validator
      pattern="[0-9.,]*"
      value={display}
      onChange={handleChange}
      onBlur={handleBlur}
      placeholder={placeholder}
      disabled={disabled}
      className={className}
      {...rest}
    />
  );
});


function _initialDisplay(value, decimals) {
  if (value == null || value === '') return '';
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) return '';
    return formatLocaleNumber(value, { decimals });
  }
  // String — accept it as-is (user-friendly: respects whatever the
  // parent put there). The blur handler will normalise on first focus loss.
  return String(value);
}


export default PriceInput;
