/**
 * AvailabilityRangeSlotPicker — Onda 17 picker a doppio pannello "Da / A".
 *
 * Layout (Opzione 2):
 *   Desktop (lg+):  grid 2 colonne → pannello "Da" a sinistra, "A" a destra.
 *   Mobile      :  stacked; "A" appare solo quando "Da" è completo.
 *
 * Ogni pannello è autoconsistente: calendario mensile + griglia orari del
 * giorno in focus, dentro un contenitore dedicato. Zero scroll tra calendario
 * e orari per selezionare start/end, zero toggle cross-day: se l'utente
 * seleziona un giorno diverso nel pannello "A", il range diventa cross-day
 * automaticamente.
 *
 * Contratto (invariato):
 *   windows:     Array<{date, windows: [{start, end}]}>
 *   minDuration: minuti (default 30)
 *   stepMinutes: minuti (default 30)
 *   maxDuration: minuti | null
 *   selected:    { date, start_time, end_time, date_end } | null
 *   onSelect:    ({date, start_time, end_time, date_end}) => void
 *
 * Validazione continuità blocked_slots tra giorni distanti: delegata al
 * backend (try_reserve_booking_slot_range atomic guard al confirm).
 */

import React, { useEffect, useMemo, useState } from 'react';
import { useTranslation, Trans } from 'react-i18next';
import AvailabilityDayPicker from './AvailabilityDayPicker';


// ── Helpers ─────────────────────────────────────────────────────────────────

function toIsoYmd(d) {
  if (!(d instanceof Date) || isNaN(d)) return null;
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

function hhmmToMin(s) {
  if (!s || typeof s !== 'string') return 0;
  const [h, m] = s.split(':');
  return (parseInt(h, 10) || 0) * 60 + (parseInt(m, 10) || 0);
}

function minToHhmm(n) {
  const h = Math.floor(n / 60);
  const m = n % 60;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
}

// Both formatters take an explicit `lng` argument so callers can pass
// the resolved storefront locale from `i18n.language`. Falling back to
// `it-IT` when omitted keeps the legacy contract for any test that
// imports them in isolation.
function fmtFullDay(iso, lng = 'it-IT') {
  if (!iso) return '';
  try {
    const dt = new Date(iso + 'T00:00');
    return dt.toLocaleDateString(lng, { weekday: 'long', day: 'numeric', month: 'long' });
  } catch { return iso; }
}

function fmtShortDay(iso, lng = 'it-IT') {
  if (!iso) return '';
  try {
    const dt = new Date(iso + 'T00:00');
    return dt.toLocaleDateString(lng, { weekday: 'short', day: 'numeric', month: 'short' });
  } catch { return iso; }
}

function fmtDurationMinutes(n) {
  if (!n || n <= 0) return '';
  const h = Math.floor(n / 60);
  const m = n % 60;
  if (h === 0) return `${m} min`;
  if (m === 0) return `${h}h`;
  return `${h}h ${m}min`;
}

/** Absolute minute from a {date, time} point, relative to a reference date. */
function absMinutes(point, refDateIso) {
  if (!point?.date || !point?.time) return 0;
  const ref = new Date((refDateIso || point.date) + 'T00:00');
  const p = new Date(point.date + 'T00:00');
  const dayOffset = Math.round((p - ref) / 86400000);
  return dayOffset * 24 * 60 + hhmmToMin(point.time);
}

/** Step-aligned HH:MM points inside a day's windows (endpoints included). */
function enumerateDayPoints(dayWindows, step) {
  if (!dayWindows || dayWindows.length === 0) return [];
  const out = new Set();
  for (const w of dayWindows) {
    const ws = hhmmToMin(w.start);
    const we = hhmmToMin(w.end);
    const first = Math.ceil(ws / step) * step;
    for (let t = first; t <= we; t += step) out.add(t);
    if (ws % step === 0) out.add(ws);
  }
  return Array.from(out).sort((a, b) => a - b);
}

/** True when the day has any window that can host a slot of `minDur` starting at `t`. */
function pointCanBeStart(dayWindows, t, minDur) {
  for (const w of dayWindows || []) {
    const ws = hhmmToMin(w.start);
    const we = hhmmToMin(w.end);
    if (ws <= t && t + minDur <= we) return true;
  }
  return false;
}


// ── Inner panel ─────────────────────────────────────────────────────────────

function DayTimePanel({
  role,                 // 'from' | 'to'
  stepNumber,           // 1 | 2
  title,                // already-translated label ("Inizio"/"Start"/...)
  disabled = false,     // panel "A" disabled until "Da" is filled
  disabledHint,         // already-translated copy when disabled
  value,                // {date, time} | null
  onPick,               // (point) => void
  onClear,              // () => void
  availableDates,       // string[] ISO — computed by parent
  blockedDates,         // string[] ISO (for calendar)
  windowsByDate,        // {[iso]: [{start, end}]}
  step,
  classifyPoint,        // (viewedDate, t) => {kind, disabled, label}
}) {
  const { t, i18n } = useTranslation('landings');
  // Each panel has its own "viewed day" (calendario focus).
  const [viewedDate, setViewedDate] = useState(
    value?.date || availableDates[0] || null,
  );

  // Reset viewed day if it falls outside available set or when value changes.
  useEffect(() => {
    if (value?.date && windowsByDate[value.date]) {
      setViewedDate(value.date);
      return;
    }
    if (viewedDate && windowsByDate[viewedDate]) return;
    setViewedDate(availableDates[0] || null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value?.date, availableDates.length]);

  const viewedWindows = viewedDate ? (windowsByDate[viewedDate] || []) : [];
  const points = useMemo(
    () => enumerateDayPoints(viewedWindows, step),
    [viewedWindows, step],
  );

  const handleDaySelect = (d) => {
    const iso = toIsoYmd(d);
    if (iso && windowsByDate[iso]) setViewedDate(iso);
  };

  const calendarSelected = viewedDate ? new Date(viewedDate + 'T00:00') : undefined;

  // Group by time-of-day for readability.
  const classified = points.map(t => ({
    t,
    ...classifyPoint(viewedDate, t),
  }));
  const morning = classified.filter(p => p.t < 12 * 60);
  const afternoon = classified.filter(p => p.t >= 12 * 60 && p.t < 18 * 60);
  const evening = classified.filter(p => p.t >= 18 * 60);

  const stepBadgeCls = role === 'from'
    ? 'bg-blue-600'
    : 'bg-amber-600';

  const renderGroup = (label, items) => {
    if (items.length === 0) return null;
    return (
      <div>
        <p className="text-[11px] uppercase tracking-wide text-gray-500 font-semibold mb-1.5">{label}</p>
        <div className="grid grid-cols-3 sm:grid-cols-4 gap-1.5">
          {items.map(p => {
            const base = 'rounded-lg border px-2 py-2 text-sm font-semibold transition tabular-nums ';
            let cls;
            if (p.disabled) {
              cls = base + 'bg-gray-50 border-gray-100 text-gray-300 cursor-not-allowed';
            } else if (p.kind === 'selected') {
              cls = base + 'bg-[var(--sf-accent,#111827)] text-[var(--sf-accent-fg,#ffffff)] border-gray-900 shadow-sm';
            } else if (p.kind === 'between') {
              cls = base + 'bg-gray-100 text-gray-700 border-gray-200';
            } else {
              cls = base + 'bg-white border-gray-200 text-gray-800 hover:border-gray-900 hover:bg-gray-50';
            }
            return (
              <button
                key={p.t}
                type="button"
                disabled={p.disabled}
                onClick={() => !p.disabled && onPick({ date: viewedDate, time: minToHhmm(p.t) })}
                className={cls}
                title={p.label || ''}
              >
                {minToHhmm(p.t)}
              </button>
            );
          })}
        </div>
      </div>
    );
  };

  // Disabled placeholder (panel "A" prima che "Da" sia scelto).
  if (disabled) {
    return (
      <div className="rounded-xl border-2 border-dashed border-gray-200 bg-gray-50/60 p-4 flex flex-col items-center justify-center text-center min-h-[200px] lg:min-h-[320px]">
        <div className={`inline-flex items-center justify-center rounded-full ${stepBadgeCls} text-white text-xs font-bold w-6 h-6 mb-2 opacity-50`}>
          {stepNumber}
        </div>
        <div className="text-sm font-semibold text-gray-400">{title}</div>
        <p className="text-xs text-gray-400 mt-1 max-w-[240px]">
          {disabledHint || t('availability.range.disabled_step_hint')}
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
      {/* Panel header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-gray-100 bg-gray-50/60">
        <div className="flex items-center gap-2 min-w-0">
          <span className={`inline-flex items-center justify-center rounded-full ${stepBadgeCls} text-white text-xs font-bold w-5 h-5`}>
            {stepNumber}
          </span>
          <span className="text-sm font-semibold text-gray-900">{title}</span>
          {value && (
            <span className="text-xs text-gray-500 hidden sm:inline truncate">
              · {fmtShortDay(value.date, i18n.language)} · {value.time}
            </span>
          )}
        </div>
        {value && onClear && (
          <button
            type="button"
            onClick={onClear}
            className="text-xs text-gray-500 hover:text-gray-900 underline"
          >
            {t('availability.range.restart')}
          </button>
        )}
      </div>

      {/* Calendar */}
      <div className="p-1 flex justify-center border-b border-gray-100">
        <AvailabilityDayPicker
          mode="single"
          selected={calendarSelected}
          onSelect={handleDaySelect}
          blockedDates={blockedDates}
          numberOfMonths={1}
        />
      </div>

      {/* Time grid */}
      <div className="p-4 space-y-3">
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <p className="text-sm font-semibold text-gray-900 capitalize">
            {fmtFullDay(viewedDate, i18n.language)}
          </p>
        </div>
        {points.length === 0 ? (
          <p className="text-sm text-gray-500">{t('availability.no_slots_today')}</p>
        ) : (
          <>
            {renderGroup(t('availability.morning'), morning)}
            {renderGroup(t('availability.afternoon'), afternoon)}
            {renderGroup(t('availability.evening'), evening)}
          </>
        )}
      </div>
    </div>
  );
}


// ── Main component ─────────────────────────────────────────────────────────

export default function AvailabilityRangeSlotPicker({
  windows,
  minDuration = 30,
  stepMinutes = 30,
  maxDuration = null,
  selected,
  onSelect,
  emptyLabel,
  emptyHint,
}) {
  const { t, i18n } = useTranslation('landings');
  const resolvedEmptyLabel = emptyLabel || t('availability.empty_30d');
  const resolvedEmptyHint = emptyHint !== undefined ? emptyHint : t('availability.empty_hint');

  const step = Math.max(5, Number(stepMinutes) || 30);
  const minDur = Math.max(5, Number(minDuration) || step);
  const maxDur = maxDuration && Number(maxDuration) > 0 ? Number(maxDuration) : null;

  const windowsByDate = useMemo(() => {
    const m = {};
    for (const d of windows || []) {
      if (d?.date) m[d.date] = d.windows || [];
    }
    return m;
  }, [windows]);

  const availableDates = useMemo(
    () => Object.keys(windowsByDate).sort(),
    [windowsByDate],
  );

  // Days within the 30-day horizon that carry no windows → marked blocked in the
  // month calendar (strikethrough + not clickable).
  const baseBlocked = useMemo(() => {
    const set = new Set(availableDates);
    const blocked = [];
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    for (let i = 0; i < 30; i++) {
      const d = new Date(today);
      d.setDate(today.getDate() + i);
      const iso = toIsoYmd(d);
      if (iso && !set.has(iso)) blocked.push(iso);
    }
    return blocked;
  }, [availableDates]);

  // Selection state
  const [from, setFrom] = useState(() =>
    selected?.start_time && selected?.date
      ? { date: selected.date, time: selected.start_time }
      : null,
  );
  const [to, setTo] = useState(() =>
    selected?.end_time && selected?.date
      ? {
          date: selected.date_end || selected.date,
          time: selected.end_time,
        }
      : null,
  );

  const emit = (f, t) => {
    if (!onSelect) return;
    if (!f) {
      onSelect({ date: '', start_time: '', end_time: '', date_end: '' });
      return;
    }
    if (!t) {
      // Partial (only from): do NOT emit so the parent's canProceed stays false.
      onSelect({ date: '', start_time: '', end_time: '', date_end: '' });
      return;
    }
    onSelect({
      date: f.date,
      start_time: f.time,
      end_time: t.time,
      date_end: t.date,
    });
  };

  // Handlers
  const handlePickFrom = (point) => {
    setFrom(point);
    // If existing "to" is no longer valid (before the new from, or out of
    // min/max duration), drop it.
    if (to) {
      const fAbs = absMinutes(point, point.date);
      const tAbs = absMinutes(to, point.date);
      const dur = tAbs - fAbs;
      if (dur <= 0 || dur < minDur || (maxDur && dur > maxDur)) {
        setTo(null);
        emit(point, null);
        return;
      }
      emit(point, to);
    } else {
      emit(point, null);
    }
  };

  const handlePickTo = (point) => {
    if (!from) return;
    const fAbs = absMinutes(from, from.date);
    const tAbs = absMinutes(point, from.date);
    const dur = tAbs - fAbs;
    if (dur <= 0 || dur < minDur) return; // UI already disables these, defensive
    if (maxDur && dur > maxDur) return;
    setTo(point);
    emit(from, point);
  };

  const handleClearFrom = () => {
    setFrom(null);
    setTo(null);
    emit(null, null);
  };

  const handleClearTo = () => {
    setTo(null);
    emit(from, null);
  };

  // Classifier for points in the "Da" panel — highlight selected from, mark
  // window-start candidates unfit for minDur as disabled.
  // NOTE: parameter renamed from `t` to `tMin` to avoid shadowing the
  // i18n `t` function captured at the top of the component.
  const classifyFrom = (viewedDate, tMin) => {
    const isSel = from && from.date === viewedDate && hhmmToMin(from.time) === tMin;
    if (isSel) return { kind: 'selected', disabled: false, label: t('availability.range.aria.from_selected') };
    const dayWindows = windowsByDate[viewedDate] || [];
    if (!pointCanBeStart(dayWindows, tMin, minDur)) {
      return { kind: 'free', disabled: true, label: t('availability.range.aria.not_enough_space') };
    }
    return { kind: 'free', disabled: false, label: t('availability.range.help.from_pick') };
  };

  // Classifier for points in the "A" panel — enable only points that:
  //  • come after `from` (global minutes)
  //  • satisfy minDur ≤ duration ≤ maxDur
  // In-between points on the same day as from/to show the "between" grey tint.
  const classifyTo = (viewedDate, tMin) => {
    if (!from) return { kind: 'free', disabled: true, label: t('availability.range.help.to_pick_first') };
    const fAbs = absMinutes(from, from.date);
    const pointAbs = absMinutes({ date: viewedDate, time: minToHhmm(tMin) }, from.date);
    const dur = pointAbs - fAbs;

    const isToPoint = to && to.date === viewedDate && hhmmToMin(to.time) === tMin;
    if (isToPoint) return { kind: 'selected', disabled: false, label: t('availability.range.aria.to_selected') };
    const isFromPoint = from.date === viewedDate && hhmmToMin(from.time) === tMin;
    if (isFromPoint) return { kind: 'selected', disabled: true, label: t('availability.range.aria.from_selected') };

    if (to) {
      const tAbs = absMinutes(to, from.date);
      if (pointAbs > fAbs && pointAbs < tAbs) {
        return { kind: 'between', disabled: false, label: t('availability.range.aria.between') };
      }
    }

    if (dur <= 0) return { kind: 'free', disabled: true, label: t('availability.range.aria.before_start') };
    if (dur < minDur) return { kind: 'free', disabled: true, label: t('availability.range.aria.too_short', { duration: fmtDurationMinutes(minDur) }) };
    if (maxDur && dur > maxDur) return { kind: 'free', disabled: true, label: t('availability.range.aria.too_long', { duration: fmtDurationMinutes(maxDur) }) };
    return { kind: 'free', disabled: false, label: t('availability.range.help.to_pick') };
  };

  // For the "A" panel, also block days strictly before from.date and days
  // beyond from + maxDur.
  const toBlocked = useMemo(() => {
    if (!from) return baseBlocked;
    const block = new Set(baseBlocked);
    const fromDate = new Date(from.date + 'T00:00');
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const maxDate = maxDur
      ? new Date(fromDate.getTime() + maxDur * 60 * 1000)
      : null;
    for (let i = 0; i < 30; i++) {
      const d = new Date(today);
      d.setDate(today.getDate() + i);
      if (d < fromDate) {
        block.add(toIsoYmd(d));
        continue;
      }
      if (maxDate && d > maxDate) {
        block.add(toIsoYmd(d));
      }
    }
    return Array.from(block);
  }, [baseBlocked, from, maxDur]);

  // Status banner
  let banner = null;
  if (availableDates.length === 0) {
    return (
      <div className="rounded-xl border-2 border-dashed border-gray-200 bg-gray-50 p-4 text-center">
        <p className="text-sm text-gray-600">{resolvedEmptyLabel}</p>
        {resolvedEmptyHint && <p className="text-xs text-gray-500 mt-1">{resolvedEmptyHint}</p>}
      </div>
    );
  }

  if (from && to) {
    const dur = absMinutes(to, from.date) - absMinutes(from, from.date);
    banner = (
      <div className="rounded-lg bg-green-50 border border-green-200 px-3 py-2 text-sm text-green-900 flex items-center justify-between gap-2 flex-wrap">
        <div className="min-w-0">
          <div className="font-semibold">
            {fmtShortDay(from.date, i18n.language)} · {from.time} → {fmtShortDay(to.date, i18n.language)} · {to.time}
          </div>
          <div className="text-xs text-green-700">{t('availability.range.duration_label', { duration: fmtDurationMinutes(dur) })}</div>
        </div>
        <button
          type="button"
          onClick={handleClearFrom}
          className="text-xs text-green-700 underline hover:text-green-900"
        >
          {t('availability.range.restart')}
        </button>
      </div>
    );
  } else if (from) {
    banner = (
      <div className="rounded-lg bg-amber-50 border border-amber-200 px-3 py-2 text-sm text-amber-900 flex items-center gap-2">
        <span className="inline-flex items-center justify-center rounded-full bg-amber-600 text-white text-xs font-bold w-5 h-5">2</span>
        <span>
          {/* `<1>` and `<2>` map to <strong> tags below — Trans
              keeps the bold-emphasis structure consistent across
              translations without splitting the sentence into
              fragile fragments. */}
          <Trans
            i18nKey="availability.range.banner.step2"
            ns="landings"
            components={[<strong />, <strong />]}
          />
        </span>
      </div>
    );
  } else {
    banner = (
      <div className="rounded-lg bg-blue-50 border border-blue-200 px-3 py-2 text-sm text-blue-900 flex items-center gap-2">
        <span className="inline-flex items-center justify-center rounded-full bg-blue-600 text-white text-xs font-bold w-5 h-5">1</span>
        <span>
          <Trans
            i18nKey="availability.range.banner.step1"
            ns="landings"
            components={[<strong />, <strong />]}
          />
        </span>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {banner}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <DayTimePanel
          role="from"
          stepNumber={1}
          title={t('availability.range.from')}
          value={from}
          onPick={handlePickFrom}
          onClear={handleClearFrom}
          availableDates={availableDates}
          blockedDates={baseBlocked}
          windowsByDate={windowsByDate}
          step={step}
          classifyPoint={classifyFrom}
        />
        <DayTimePanel
          role="to"
          stepNumber={2}
          title={t('availability.range.to')}
          disabled={!from}
          disabledHint={t('availability.range.help.from_after_to')}
          value={to}
          onPick={handlePickTo}
          onClear={handleClearTo}
          availableDates={availableDates}
          blockedDates={toBlocked}
          windowsByDate={windowsByDate}
          step={step}
          classifyPoint={classifyTo}
        />
      </div>
    </div>
  );
}
