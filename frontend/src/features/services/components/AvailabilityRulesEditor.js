/**
 * AvailabilityRulesEditor — editor for weekly availability_rules that
 * define when a service product is bookable (F5 Onda 12).
 *
 * Each rule is: { day_of_week: 0..6, start_time: "HH:MM",
 *                  end_time: "HH:MM", slot_duration_minutes: int }
 *
 * UI approach: a simple per-weekday toggle list. For each day the
 * admin enables the flag, types start/end and slot duration. The
 * component serialises the internal state into the array shape the
 * backend expects.
 *
 * Note: does NOT persist by itself; the Wizard aggregates + POSTs on
 * submit; the Dashboard calls a dedicated API. This is a pure
 * controlled input component.
 */

import React, { useCallback, useMemo } from 'react';


const DAYS = [
  { n: 0, label: 'Lunedì' },
  { n: 1, label: 'Martedì' },
  { n: 2, label: 'Mercoledì' },
  { n: 3, label: 'Giovedì' },
  { n: 4, label: 'Venerdì' },
  { n: 5, label: 'Sabato' },
  { n: 6, label: 'Domenica' },
];


export default function AvailabilityRulesEditor({
  rules = [],
  onChange,
  defaultSlotMinutes = 60,
}) {
  // Map rules to a by-weekday dict for easy UI editing.
  const byDay = useMemo(() => {
    const m = {};
    for (const r of rules) {
      if (typeof r?.day_of_week === 'number') m[r.day_of_week] = r;
    }
    return m;
  }, [rules]);

  const update = useCallback((day, patch) => {
    const current = byDay[day];
    // If patch disables the day (enabled=false) drop the rule
    if (patch.__disable) {
      const next = rules.filter(r => r.day_of_week !== day);
      onChange(next);
      return;
    }
    if (current) {
      const next = rules.map(r => r.day_of_week === day ? { ...r, ...patch } : r);
      onChange(next);
    } else {
      // Create
      onChange([
        ...rules,
        {
          day_of_week: day,
          start_time: patch.start_time || '09:00',
          end_time: patch.end_time || '18:00',
          slot_duration_minutes: patch.slot_duration_minutes || defaultSlotMinutes,
        },
      ]);
    }
  }, [rules, byDay, onChange, defaultSlotMinutes]);

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 space-y-3">
      <div>
        <h3 className="text-sm font-semibold text-gray-900">Quando sei disponibile</h3>
        <p className="text-xs text-gray-500 mt-0.5">
          Definisci i giorni della settimana in cui accetti prenotazioni. Gli slot vengono calcolati dinamicamente dalla durata.
        </p>
      </div>

      <div className="space-y-2">
        {DAYS.map(d => {
          const rule = byDay[d.n];
          const enabled = !!rule;
          return (
            <div
              key={d.n}
              className="rounded-lg border border-gray-200 p-3 flex flex-wrap items-center gap-3"
            >
              <label className="flex items-center gap-2 cursor-pointer w-24 shrink-0">
                <input
                  type="checkbox"
                  checked={enabled}
                  onChange={e => update(d.n, e.target.checked ? {} : { __disable: true })}
                  className="rounded border-gray-300"
                />
                <span className="text-sm font-medium text-gray-900">{d.label}</span>
              </label>
              {enabled && (
                <>
                  <div className="flex items-center gap-1">
                    <label className="text-[11px] text-gray-600">Dalle</label>
                    <input
                      type="time"
                      value={rule.start_time || '09:00'}
                      onChange={e => update(d.n, { start_time: e.target.value })}
                      className="rounded-md border border-gray-300 px-2 py-1 text-sm"
                    />
                  </div>
                  <div className="flex items-center gap-1">
                    <label className="text-[11px] text-gray-600">alle</label>
                    <input
                      type="time"
                      value={rule.end_time || '18:00'}
                      onChange={e => update(d.n, { end_time: e.target.value })}
                      className="rounded-md border border-gray-300 px-2 py-1 text-sm"
                    />
                  </div>
                  <div className="flex items-center gap-1">
                    <label className="text-[11px] text-gray-600">Slot (min)</label>
                    <input
                      type="number"
                      min="5"
                      max="1440"
                      value={rule.slot_duration_minutes ?? defaultSlotMinutes}
                      onChange={e => update(d.n, { slot_duration_minutes: Number(e.target.value) || defaultSlotMinutes })}
                      className="w-20 rounded-md border border-gray-300 px-2 py-1 text-sm"
                    />
                  </div>
                </>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
