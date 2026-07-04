/**
 * CourseSidebar — left rail with progress summary + module accordion.
 *
 * On desktop (≥lg) it lives in the grid's left column always visible.
 * On mobile it's reused inside the bottom-sheet drawer (see the
 * orchestrator). This single component renders identically in both
 * contexts; the parent picks the placement.
 *
 * Three nested pieces, all defined in this file because they're
 * tightly coupled and never reused outside the course player:
 *
 *   • SummaryCard       — ProgressRing + headline + 2 micro-tiles
 *   • ModuleAccordion   — collapsible per-module list of lessons
 *   • LessonRow         — single lesson with status icon + duration
 *
 * Splitting these into separate files would have created 3 ~50-line
 * files that always import each other; co-located here is more
 * maintainable. If a piece ever gets reused outside the sidebar
 * (e.g. LessonRow on a course landing page), it can be promoted to
 * its own file at that point with no churn.
 *
 * Extracted from the 1392-line monolith during Fase 4 architectural
 * split.
 */

import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import ProgressRing from './ProgressRing';
import { formatDurationHM, formatLessonDuration, formatDateShort } from '../utils/format';


/* ─── LessonRow — single lesson button in the accordion ──────────────────
 *
 * Visual language for the status indicator (sighted hint):
 *   ✅  completed lesson
 *   ⏱  partially watched (heartbeat-recorded watched_seconds > 0)
 *   ○   not started
 *
 * The currently-selected lesson REPLACES the static glyph with an
 * animated emerald dot ("In corso" badge) to signal "this is the
 * one you're watching right now". `aria-current="true"` carries the
 * same meaning for screen readers.
 */
function LessonRow({ lesson, progress, isSelected, onSelect }) {
  const { t } = useTranslation('customer_portal');
  const completed = !!progress?.completed_at;
  const watched = Number(progress?.watched_seconds || 0);
  const duration = Number(lesson.duration_seconds || 0);
  const partial = !completed && watched > 0 && duration > 0;
  const icon = completed ? '✅' : partial ? '⏱' : '○';

  return (
    <button
      type="button"
      onClick={() => onSelect(lesson.id)}
      className={`w-full text-left flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors ${
        isSelected
          ? 'bg-gray-900 text-white'
          : completed
          ? 'bg-emerald-50 text-gray-900 hover:bg-emerald-100'
          : 'text-gray-700 hover:bg-gray-100'
      }`}
      aria-current={isSelected ? 'true' : undefined}
    >
      {/* Status indicator — animated dot for the selected lesson, glyph
          for the rest. The dot pulses gently to signal "I'm the one
          you're watching" without being attention-stealing (no fast
          blinking, no color change). */}
      {isSelected ? (
        <span className="shrink-0 w-4 flex items-center justify-center" aria-hidden>
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75 animate-ping" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-400" />
          </span>
        </span>
      ) : (
        <span className="shrink-0 w-4 text-center">{icon}</span>
      )}

      <span className="flex-1 min-w-0 truncate">{lesson.title}</span>

      {/* "In corso" pill replaces the duration on the active lesson.
          Other lessons still show duration as the right-aligned
          secondary info. */}
      {isSelected ? (
        <span className="text-[10px] shrink-0 font-semibold uppercase tracking-wider text-emerald-300">
          {t('customer_portal:courseSidebar.row.inProgress')}
        </span>
      ) : (
        <span className={`text-[11px] shrink-0 tabular-nums ${
          completed ? 'text-emerald-700' : 'text-gray-500'
        }`}>
          {formatLessonDuration(lesson.duration_seconds)}
        </span>
      )}
    </button>
  );
}


/* ─── ModuleAccordion — collapsible group of lessons ────────────────────── */

function ModuleAccordion({ mod, progress, selectedId, onSelect, defaultOpen }) {
  const { t } = useTranslation('customer_portal');
  const [open, setOpen] = useState(defaultOpen);
  const lessons = mod.lessons || [];
  const completed = lessons.filter(l => progress?.[l.id]?.completed_at).length;

  return (
    <div className="border border-gray-200 rounded-lg bg-white overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-center justify-between gap-2 px-3 py-2 text-left hover:bg-gray-50"
      >
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-gray-900 truncate">{mod.title}</p>
          <p className="text-[11px] text-gray-500 mt-0.5">
            {t('customer_portal:courseSidebar.lessonsCompleted', {
              completed,
              total: lessons.length,
              count: lessons.length,
            })}
          </p>
        </div>
        <span aria-hidden className="text-gray-400 text-lg leading-none">
          {open ? '−' : '+'}
        </span>
      </button>
      {open && (
        <div className="px-1 pb-1 space-y-0.5">
          {lessons.map(l => (
            <LessonRow
              key={l.id}
              lesson={l}
              progress={progress?.[l.id]}
              isSelected={selectedId === l.id}
              onSelect={onSelect}
            />
          ))}
        </div>
      )}
    </div>
  );
}


/* ─── SummaryCard — ProgressRing + headline + 2 micro-tiles ────────────── */

function SummaryCard({ stats, course, enrollment }) {
  const { t, i18n } = useTranslation('customer_portal');
  const pct = stats.percentage || 0;
  const totalSeconds = course.modules?.reduce(
    (s, m) => s + (m.lessons || []).reduce(
      (ss, l) => ss + (l.duration_seconds || 0), 0,
    ),
    0,
  ) || 0;

  // Headline copy that adapts to current progress — sets the right
  // tone before the customer scans the numbers.
  const headline = pct >= 100
    ? t('customer_portal:courseSidebar.headlineDone')
    : pct > 0
      ? t('customer_portal:courseSidebar.headlineProgress')
      : t('customer_portal:courseSidebar.headlineStart');

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-3 space-y-3">
      <div className="flex items-center gap-3">
        <ProgressRing value={pct} size={68} stroke={6} />
        <div className="flex-1 min-w-0">
          <p
            className="text-sm font-semibold text-gray-900 leading-tight"
            aria-label={t('customer_portal:courseSidebar.percentCompletedAria', { pct })}
          >
            {headline}
          </p>
          <p className="text-[11px] text-gray-500 mt-0.5">
            {t('customer_portal:courseSidebar.lessonsRatio', {
              completed: stats.lessons_completed || 0,
              total: stats.total_lessons || 0,
            })}
          </p>
        </div>
      </div>

      {/* Micro-tile row — durata + scadenza (the latter is color-coded:
          amber when limited, emerald when "lifetime"). */}
      <div className="grid grid-cols-2 gap-2 text-center">
        <div className="rounded-lg bg-gray-50 border border-gray-100 px-2 py-1.5">
          <p className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold">{t('customer_portal:courseSidebar.tile.duration')}</p>
          <p className="text-xs font-semibold text-gray-900 tabular-nums mt-0.5">
            {formatDurationHM(totalSeconds) || '—'}
          </p>
        </div>
        <div className={`rounded-lg px-2 py-1.5 border ${
          enrollment?.expires_at
            ? 'bg-amber-50 border-amber-100'
            : 'bg-emerald-50 border-emerald-100'
        }`}>
          <p className={`text-[10px] uppercase tracking-wider font-semibold ${
            enrollment?.expires_at ? 'text-amber-700' : 'text-emerald-700'
          }`}>
            {t('customer_portal:courseSidebar.tile.access')}
          </p>
          <p className={`text-xs font-semibold tabular-nums mt-0.5 ${
            enrollment?.expires_at ? 'text-amber-900' : 'text-emerald-900'
          }`}>
            {enrollment?.expires_at
              ? formatDateShort(enrollment.expires_at, i18n.language)
              : t('customer_portal:courseSidebar.tile.accessLifetime')}
          </p>
        </div>
      </div>
    </div>
  );
}


/* ─── CourseSidebar — public top-level component ─────────────────────────
 *
 * `onLessonSelect` should close the mobile bottom-sheet drawer (when
 * called from there) AND set the selected lesson — the orchestrator
 * combines both into a single callback so this component doesn't need
 * to know about the drawer at all.
 */

export default function CourseSidebar({
  course,
  progress,
  progressStats,
  enrollment,
  selectedLessonId,
  onLessonSelect,
}) {
  return (
    <div className="space-y-2">
      <SummaryCard stats={progressStats} course={course} enrollment={enrollment} />

      {/* Module accordions — first one (or the one containing the
          selected lesson) opens by default. Subsequent renders keep
          their toggled state because each ModuleAccordion owns its
          own `open` useState. */}
      <div className="space-y-2">
        {(course.modules || []).map((m, i) => (
          <ModuleAccordion
            key={m.id}
            mod={m}
            progress={progress}
            selectedId={selectedLessonId}
            onSelect={onLessonSelect}
            defaultOpen={
              (m.lessons || []).some(l => l.id === selectedLessonId) || i === 0
            }
          />
        ))}
      </div>
    </div>
  );
}
