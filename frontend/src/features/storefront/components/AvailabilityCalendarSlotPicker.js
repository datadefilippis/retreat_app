/**
 * AvailabilityCalendarSlotPicker — date-then-time picker for rental flavor=slot.
 *
 * Visual pattern (aligned with rental-range landing):
 *   1. Graphical month calendar on top (react-day-picker via AvailabilityDayPicker).
 *      Days with no available slots show red with strikethrough and are not
 *      clickable. Navigation via built-in prev/next month arrows — no
 *      horizontal carousel that can overflow the viewport.
 *   2. Slot grid underneath, shown once a day is selected: slots grouped in
 *      Mattina / Pomeriggio / Sera buckets, click-to-select.
 *
 * WHY a separate component from AvailabilitySlotPicker
 *   The existing AvailabilitySlotPicker (kept for Service consulenze) uses a
 *   horizontal day carousel that scales poorly past ~10 days. For rental slot
 *   products (meeting rooms, courts) the window is 30 days × many slots, and
 *   a monthly calendar is the industry-standard UX (Calendly / Doctolib /
 *   Airbnb all use a month grid for rentals). Sharing the DayPicker between
 *   the two rental flavors gives a consistent mental model to the customer.
 *
 * Contract:
 *   slots:    Array<{date: "YYYY-MM-DD", start_time: "HH:MM", end_time: "HH:MM"}>
 *   selected: {date, start_time, end_time} | null
 *   onSelect: (slot) => void
 */

import React, { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import AvailabilityDayPicker from './AvailabilityDayPicker';


function toIsoYmd(d) {
  if (!(d instanceof Date) || isNaN(d)) return null;
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}


export default function AvailabilityCalendarSlotPicker({
  slots,
  selected,
  onSelect,
  emptyLabel,
  emptyHint,
}) {
  const { t, i18n } = useTranslation('landings');
  // Resolve copy from i18n; the props remain as override hooks for
  // legacy callers / tests but are no longer the source of truth.
  const resolvedEmptyLabel = emptyLabel || t('availability.empty_30d');
  const resolvedEmptyHint = emptyHint !== undefined ? emptyHint : t('availability.empty_hint');
  // Group all available slots by their ISO date so we can derive both the
  // set of days that ARE bookable (calendar enables them) and the slot list
  // for the active day.
  const byDate = useMemo(() => {
    const m = {};
    for (const s of slots || []) {
      if (!s?.date) continue;
      (m[s.date] = m[s.date] || []).push(s);
    }
    return m;
  }, [slots]);

  const availableDates = useMemo(() => Object.keys(byDate).sort(), [byDate]);

  // Derive the window [today, today+30] and mark as "blocked" every day
  // that does NOT appear in the available set. This feeds AvailabilityDayPicker
  // which already knows how to grey-out + strikethrough blocked days.
  // We only compute 30 days forward because that's the backend `days` default
  // for the slot endpoint; any day outside that window is implicitly unknown
  // (still selectable — user lands on empty slot grid — rare edge case).
  const blockedDates = useMemo(() => {
    const availableSet = new Set(availableDates);
    const blocked = [];
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    for (let i = 0; i < 30; i++) {
      const d = new Date(today);
      d.setDate(today.getDate() + i);
      const iso = toIsoYmd(d);
      if (iso && !availableSet.has(iso)) blocked.push(iso);
    }
    return blocked;
  }, [availableDates]);

  // Track the day the user is focusing. Default to the selected day (if any)
  // or the first available day so the slot grid is not empty on first render.
  const [activeDate, setActiveDate] = useState(null);
  useEffect(() => {
    if (activeDate && byDate[activeDate]) return;
    if (selected?.date && byDate[selected.date]) {
      setActiveDate(selected.date);
    } else if (availableDates.length > 0) {
      setActiveDate(availableDates[0]);
    } else {
      setActiveDate(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [availableDates.length, selected?.date]);

  const activeSlots = activeDate ? (byDate[activeDate] || []) : [];
  const morning = activeSlots.filter(s => s.start_time < '12:00');
  const afternoon = activeSlots.filter(s => s.start_time >= '12:00' && s.start_time < '18:00');
  const evening = activeSlots.filter(s => s.start_time >= '18:00');

  // Locale-aware date format — drives "lunedì 15 settembre" (it),
  // "Monday September 15" (en), etc. Reads i18n.language directly so a
  // runtime language switch reflects on next render without any extra
  // wiring.
  const fmtFullDay = (iso) => {
    if (!iso) return '';
    try {
      const dt = new Date(iso + 'T00:00');
      return dt.toLocaleDateString(i18n.language, { weekday: 'long', day: 'numeric', month: 'long' });
    } catch { return iso; }
  };

  // react-day-picker single-mode onSelect returns a Date or undefined.
  const handleDaySelect = (d) => {
    const iso = toIsoYmd(d);
    if (iso && byDate[iso]) setActiveDate(iso);
  };

  const calendarSelected = activeDate ? new Date(activeDate + 'T00:00') : undefined;

  if (availableDates.length === 0) {
    return (
      <div className="rounded-xl border-2 border-dashed border-gray-200 bg-gray-50 p-4 text-center">
        <p className="text-sm text-gray-600">{resolvedEmptyLabel}</p>
        {resolvedEmptyHint && <p className="text-xs text-gray-500 mt-1">{resolvedEmptyHint}</p>}
      </div>
    );
  }

  const renderSlotGroup = (label, items) => {
    if (items.length === 0) return null;
    return (
      <div>
        <p className="text-[11px] uppercase tracking-wide text-gray-500 font-semibold mb-1.5">{label}</p>
        <div className="grid grid-cols-3 sm:grid-cols-4 gap-1.5">
          {items.map(s => {
            const isSelected = selected?.date === s.date && selected?.start_time === s.start_time;
            return (
              <button
                key={`${s.date}-${s.start_time}`}
                type="button"
                onClick={() => onSelect({ date: s.date, start_time: s.start_time, end_time: s.end_time })}
                className={`rounded-lg border px-2 py-2 text-sm font-semibold transition tabular-nums ${
                  isSelected
                    ? 'bg-[var(--sf-accent,#111827)] text-[var(--sf-accent-fg,#ffffff)] border-gray-900 shadow-sm'
                    : 'bg-white border-gray-200 text-gray-800 hover:border-gray-900 hover:bg-gray-50'
                }`}
              >
                {s.start_time}
              </button>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-3">
      {/* Step 1 — Month calendar (same visual language as rental range) */}
      <div className="rounded-xl border border-gray-200 bg-white overflow-hidden p-1 flex justify-center">
        <AvailabilityDayPicker
          mode="single"
          selected={calendarSelected}
          onSelect={handleDaySelect}
          blockedDates={blockedDates}
          numberOfMonths={1}
        />
      </div>

      {/* Step 2 — Time slots for the selected day */}
      <div className="rounded-xl border border-gray-200 bg-white p-4 space-y-3">
        {activeDate ? (
          <>
            <p className="text-sm font-semibold text-gray-900 capitalize">
              {fmtFullDay(activeDate)}
            </p>
            {activeSlots.length === 0 ? (
              <p className="text-sm text-gray-500">{t('availability.no_slots_today')}</p>
            ) : (
              <>
                {renderSlotGroup(t('availability.morning'), morning)}
                {renderSlotGroup(t('availability.afternoon'), afternoon)}
                {renderSlotGroup(t('availability.evening'), evening)}
              </>
            )}
          </>
        ) : (
          <p className="text-sm text-gray-500">{t('availability.pick_day_for_slots')}</p>
        )}
      </div>
    </div>
  );
}
