/**
 * AvailabilitySlotPicker — two-step date + time slot picker.
 *
 * Extracted from ProductLandingPage.js (Onda 13) so that both service and
 * rental-slot landing pages can share the same UX without duplicating logic:
 *
 *   1. Horizontal carousel of day chips (weekday + day/month label). The user
 *      picks a day first. A count badge shows how many slots that day has;
 *      days with no slots are not displayed at all because the backend only
 *      emits available slots (blocked windows are filtered out).
 *   2. Below the carousel, a grid of morning / afternoon / evening slot
 *      buttons for the selected day. Selection drives `onSelect`.
 *
 * Contract:
 *   slots: Array<{date: "YYYY-MM-DD", start_time: "HH:MM", end_time: "HH:MM"}>
 *   selected: { date, start_time, end_time } | null
 *   onSelect: (slot) => void
 *   emptyLabel?: string  — override the "no slots available" message (optional).
 *
 * Behaviour mirrors the original inline implementation exactly so service
 * landing pages retain their existing UX (regression-free extraction).
 */

import React, { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';


export default function AvailabilitySlotPicker({
  slots,
  selected,
  onSelect,
  emptyLabel,
  emptyHint,
}) {
  const { t, i18n } = useTranslation('landings');
  const resolvedEmptyLabel = emptyLabel || t('availability.empty_30d');
  const resolvedEmptyHint = emptyHint !== undefined ? emptyHint : t('availability.empty_hint');
  // Group by date
  const byDate = useMemo(() => {
    const m = {};
    for (const s of slots || []) {
      (m[s.date] = m[s.date] || []).push(s);
    }
    return m;
  }, [slots]);
  const dates = useMemo(() => Object.keys(byDate).sort(), [byDate]);

  // Track which date is currently expanded in the UI. Default to either
  // the selected date (if any) or the first available date.
  const [activeDate, setActiveDate] = useState(null);
  useEffect(() => {
    if (activeDate && byDate[activeDate]) return;
    if (selected?.date && byDate[selected.date]) {
      setActiveDate(selected.date);
    } else if (dates.length > 0) {
      setActiveDate(dates[0]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dates.length, selected?.date]);

  if (dates.length === 0) {
    return (
      <div className="rounded-xl border-2 border-dashed border-gray-200 bg-gray-50 p-4 text-center">
        <p className="text-sm text-gray-600">{resolvedEmptyLabel}</p>
        {resolvedEmptyHint && <p className="text-xs text-gray-500 mt-1">{resolvedEmptyHint}</p>}
      </div>
    );
  }

  const activeSlots = activeDate ? (byDate[activeDate] || []) : [];
  // Split slots by period of day for visual grouping
  const morning = activeSlots.filter(s => s.start_time < '12:00');
  const afternoon = activeSlots.filter(s => s.start_time >= '12:00' && s.start_time < '18:00');
  const evening = activeSlots.filter(s => s.start_time >= '18:00');

  // All four formatted parts share the resolved storefront language so a
  // German-store visitor sees `Mo · 15 · Sept` and a French-store one
  // sees `lun · 15 · sept` — consistent with the calendar header.
  const fmtDay = (iso) => {
    const dt = new Date(iso + 'T00:00');
    const lng = i18n.language;
    return {
      weekday: dt.toLocaleDateString(lng, { weekday: 'short' }).replace('.', ''),
      day: dt.toLocaleDateString(lng, { day: 'numeric' }),
      month: dt.toLocaleDateString(lng, { month: 'short' }).replace('.', ''),
      full: dt.toLocaleDateString(lng, { weekday: 'long', day: 'numeric', month: 'long' }),
    };
  };

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
    <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
      {/* Step 1 — Date carousel */}
      <div className="border-b border-gray-100 bg-gray-50/50 p-3">
        <p className="text-[11px] uppercase tracking-wide text-gray-500 font-semibold mb-2">{t('availability.pick_day')}</p>
        <div className="flex gap-1.5 overflow-x-auto pb-1 -mx-1 px-1 snap-x snap-mandatory scroll-smooth">
          {dates.map(date => {
            const parts = fmtDay(date);
            const isActive = activeDate === date;
            const hasSelection = selected?.date === date;
            const slotsCount = byDate[date]?.length || 0;
            return (
              <button
                key={date}
                type="button"
                onClick={() => setActiveDate(date)}
                className={`snap-start shrink-0 rounded-lg px-3 py-2 text-center transition min-w-[64px] ${
                  isActive
                    ? 'bg-[var(--sf-accent,#111827)] text-[var(--sf-accent-fg,#ffffff)] shadow-sm'
                    : hasSelection
                      ? 'bg-green-100 text-green-900 border border-green-300'
                      : 'bg-white text-gray-700 border border-gray-200 hover:border-gray-900'
                }`}
              >
                <p className={`text-[10px] uppercase tracking-wide font-semibold ${isActive ? 'opacity-70' : 'text-gray-500'}`}>
                  {parts.weekday}
                </p>
                <p className="text-lg font-bold leading-none mt-0.5 tabular-nums">{parts.day}</p>
                <p className={`text-[9px] uppercase ${isActive ? 'opacity-70' : 'text-gray-400'} mt-0.5`}>
                  {parts.month}
                </p>
                {hasSelection && !isActive && (
                  <p className="text-[9px] mt-0.5">✓ {selected.start_time}</p>
                )}
                {!hasSelection && (
                  <p className={`text-[9px] mt-0.5 ${isActive ? 'opacity-70' : 'text-gray-400'}`}>
                    {slotsCount}
                  </p>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Step 2 — Time slots for selected date */}
      <div className="p-4 space-y-3">
        {activeDate && (
          <p className="text-sm font-semibold text-gray-900 capitalize">
            {fmtDay(activeDate).full}
          </p>
        )}
        {activeSlots.length === 0 ? (
          <p className="text-sm text-gray-500">{t('availability.no_slots_today')}</p>
        ) : (
          <>
            {renderSlotGroup(t('availability.morning'), morning)}
            {renderSlotGroup(t('availability.afternoon'), afternoon)}
            {renderSlotGroup(t('availability.evening'), evening)}
          </>
        )}
      </div>
    </div>
  );
}
