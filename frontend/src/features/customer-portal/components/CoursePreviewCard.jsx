/**
 * CoursePreviewCard — compact course tile used in:
 *   - The "Continua un corso" carousel on the HomePage (Fase 4)
 *   - The "I miei corsi" preview on /account (Fase 1, current)
 *   - Anywhere else a quick course shortcut is needed
 *
 * Renders cover image (or 🎓 fallback) + title + thin progress bar +
 * lessons completed count. Clicking the whole card opens the player
 * (CoursePlayerPage) at /account/courses/:enrollment_id.
 *
 * Extracted from MyCoursesPreview inline in CustomerPortalPages.js so
 * that the HomePage dashboard can present a richer carousel without
 * duplicating the markup.
 */

import React from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';


export default function CoursePreviewCard({ entry, ctaLabel, variant = 'compact' }) {
  const { t } = useTranslation('customer_portal');
  const resolvedCta = ctaLabel ?? t('customer_portal:courses.openCta');
  if (!entry) return null;
  const { enrollment, course, progress_stats } = entry;
  const c = course || {};
  const stats = progress_stats || {};
  const pct = Math.max(0, Math.min(100, Number(stats.percentage) || 0));
  const completed = stats.lessons_completed || 0;
  const total = stats.total_lessons || 0;

  const href = `/account/courses/${enrollment.id}`;
  const isFull = variant === 'full';

  return (
    <Link
      to={href}
      className="block rounded-xl border border-gray-200 bg-white overflow-hidden hover:shadow-sm transition-shadow"
    >
      {c.cover_image_url ? (
        <div className="aspect-[16/9] bg-gray-100 overflow-hidden">
          <img src={c.cover_image_url} alt="" className="w-full h-full object-cover" />
        </div>
      ) : (
        <div className="aspect-[16/9] bg-gradient-to-br from-indigo-700 to-blue-500 flex items-center justify-center text-3xl">
          🎓
        </div>
      )}
      <div className={`${isFull ? 'p-4' : 'p-3'} space-y-1.5`}>
        <p className={`${isFull ? 'text-base' : 'text-sm'} font-semibold text-gray-900 line-clamp-2 leading-tight`}>
          {c.title || t('customer_portal:coursePreview.fallbackTitle')}
        </p>
        {isFull && c.instructor_name && (
          <p className="text-xs text-gray-500">{c.instructor_name}</p>
        )}
        <div className="w-full h-1 rounded-full bg-gray-200 overflow-hidden">
          <div
            className={`h-full transition-all ${pct >= 100 ? 'bg-emerald-500' : 'bg-gray-900'}`}
            style={{ width: `${pct}%` }}
          />
        </div>
        <div className="flex items-center justify-between text-[10px] text-gray-500">
          <span>{completed}/{total} · {pct}%</span>
          {isFull && (
            <span className="font-semibold text-gray-700">{resolvedCta} →</span>
          )}
        </div>
      </div>
    </Link>
  );
}
