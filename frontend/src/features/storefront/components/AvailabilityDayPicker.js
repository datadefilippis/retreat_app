/**
 * AvailabilityDayPicker — date picker that visually greys-out unavailable
 * days so the customer sees what's bookable BEFORE clicking.
 *
 * Wraps the existing `Calendar` component (react-day-picker, already used by
 * admin pages) and adds:
 *   - `blockedDates`: a list of YYYY-MM-DD strings the customer cannot select.
 *     Internally converted to a Set for O(1) lookup inside the `disabled`
 *     matcher.
 *   - Visual emphasis on disabled days: a soft red background + strikethrough,
 *     so unavailability reads at a glance (the default react-day-picker
 *     `day_disabled` style is just a muted colour, which users miss).
 *   - "Past day" support out of the box via `minDate` (defaults to today).
 *
 * Supports both `mode="single"` and `mode="range"`. In range mode,
 * react-day-picker natively prevents selection of a range that crosses a
 * disabled day — exactly the UX we need for multi-day rentals.
 *
 * Contract:
 *   <AvailabilityDayPicker
 *     mode="range" | "single"
 *     selected={{from, to}} | Date | null
 *     onSelect={(next) => ...}
 *     blockedDates={["2026-04-24", ...]}
 *     minDate={Date} // defaults to today
 *     maxDate={Date} // optional
 *     numberOfMonths={1 | 2}  // default 1
 *   />
 *
 * Output types mirror react-day-picker:
 *   - single: Date | undefined
 *   - range:  { from: Date, to?: Date } | undefined
 */

import React, { useMemo } from 'react';
import { Calendar } from '../../../components/ui/calendar';
import { useDateFnsLocale } from '../../../hooks/useDateFnsLocale';


function toIsoYmd(d) {
  if (!(d instanceof Date) || isNaN(d)) return null;
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}


export default function AvailabilityDayPicker({
  mode = 'single',
  selected,
  onSelect,
  blockedDates = [],
  minDate,
  maxDate,
  numberOfMonths = 1,
  className = '',
}) {
  // Drive the calendar header (month names) + weekday labels from the
  // resolved storefront language. Without this prop the wrapped
  // react-day-picker falls back to English, which breaks the visual
  // consistency on FR/DE/IT storefronts.
  const dateFnsLocale = useDateFnsLocale();
  // Normalize blockedDates (array of ISO strings) into a Set for fast lookup.
  const blockedSet = useMemo(
    () => new Set(Array.isArray(blockedDates) ? blockedDates : []),
    [blockedDates],
  );

  // Default minDate: today at 00:00 so the customer can't pick past days.
  const effectiveMin = useMemo(() => {
    if (minDate instanceof Date) return minDate;
    const d = new Date();
    d.setHours(0, 0, 0, 0);
    return d;
  }, [minDate]);

  // `disabled` prop for react-day-picker: a function that returns true for
  // any date that should not be selectable. Combines:
  //   - before minDate
  //   - after maxDate (if provided)
  //   - inside the blockedSet
  const isDisabled = useMemo(() => (date) => {
    if (!(date instanceof Date) || isNaN(date)) return true;
    if (date < effectiveMin) return true;
    if (maxDate instanceof Date && date > maxDate) return true;
    const iso = toIsoYmd(date);
    return iso ? blockedSet.has(iso) : false;
  }, [blockedSet, effectiveMin, maxDate]);

  // Visual emphasis for blocked days: soft red background + strikethrough.
  // `modifiers` + `modifiersClassNames` is the official react-day-picker API
  // for custom day states, and it composes with `disabled` so the merge is
  // clean. We re-derive the same matcher minus the min/max guard so blocked
  // days *after today* keep the explicit red styling (before-today days just
  // look muted — standard past-day UX).
  const blockedMatcher = useMemo(() => (date) => {
    const iso = toIsoYmd(date);
    return iso ? blockedSet.has(iso) : false;
  }, [blockedSet]);

  return (
    <Calendar
      mode={mode}
      selected={selected}
      onSelect={onSelect}
      disabled={isDisabled}
      fromDate={effectiveMin}
      toDate={maxDate}
      numberOfMonths={numberOfMonths}
      locale={dateFnsLocale}
      modifiers={{ blocked: blockedMatcher }}
      modifiersClassNames={{
        blocked:
          'line-through text-red-600 bg-red-50 hover:bg-red-50 cursor-not-allowed opacity-70',
      }}
      className={className}
    />
  );
}
