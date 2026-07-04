/**
 * LessonDetails — descriptive card below the player + action bar.
 *
 * Owns the long-form content for the currently-selected lesson:
 *   • Breadcrumb (module · title · duration)
 *   • Description (multi-line, preserves whitespace)
 *   • Resources (downloadable / external links)
 *   • Completion timestamp (when the lesson is marked done)
 *
 * Note: the action row (Mark / Prev / Next) used to live here too,
 * but it's now in the sticky LessonActionBar above so it stays
 * reachable during scroll. The title remains here as a "long-form"
 * anchor for the description and resources block.
 *
 * Extracted from the 1392-line monolith during Fase 4 architectural
 * split. Pure presentational — receives `lesson` + `completedAt`,
 * never fetches.
 */

import React from 'react';
import { useTranslation } from 'react-i18next';
import { formatLessonDuration, formatDateShort } from '../utils/format';


export default function LessonDetails({ lesson, completedAt }) {
  const { t, i18n } = useTranslation('customer_portal');
  if (!lesson) return null;
  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5 space-y-3">
      <div className="min-w-0">
        <p className="text-[11px] uppercase tracking-wider text-gray-500 font-semibold">
          {lesson.module_title}
        </p>
        <h2 className="text-lg font-bold text-gray-900 mt-0.5">
          {lesson.title}
        </h2>
        <p className="text-xs text-gray-500 mt-1">
          {t('customer_portal:lessonDetails.durationLabel', { duration: formatLessonDuration(lesson.duration_seconds) })}
        </p>
      </div>

      {lesson.description && (
        <p className="text-sm text-gray-700 whitespace-pre-line leading-relaxed">
          {lesson.description}
        </p>
      )}

      {(lesson.resources || []).length > 0 && (
        <div className="border-t border-gray-100 pt-3">
          <p className="text-xs font-semibold uppercase tracking-wider text-gray-600 mb-2">
            {t('customer_portal:lessonDetails.resources')}
          </p>
          <ul className="space-y-1">
            {lesson.resources.map((r, i) => (
              <li key={i}>
                <a
                  href={r.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-gray-900 hover:underline"
                >
                  📎 {r.label}
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}

      {completedAt && (
        <div className="border-t border-gray-100 pt-3 text-xs text-emerald-700 font-medium">
          {t('customer_portal:lessonDetails.completedOn', { date: formatDateShort(completedAt, i18n.language) })}
        </div>
      )}
    </div>
  );
}
