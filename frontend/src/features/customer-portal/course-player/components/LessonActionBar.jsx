/**
 * LessonActionBar — sticky bar between the player and the lesson
 * details, owning the three high-priority lesson actions:
 *
 *   1. Mark completed (the high-value action: "I'm done with this")
 *   2. Prev / Next   (navigation, secondary)
 *
 * The bar stays sticky at top:3.5rem (under the CustomerLayout's
 * h-14 TopBar) so Mark / Prev / Next remain reachable during scroll.
 * On mobile a 📚 icon button to the left opens the lessons bottom-
 * sheet drawer (the sidebar is hidden in the responsive grid).
 *
 * History: this bar is the result of fixing a UX bug where the
 * "Mark completed" button used to be an absolute overlay at
 * bottom-right of the iframe — covering Bunny's volume / fullscreen
 * / settings controls. Moving the action OUT of the iframe area was
 * the fix; making it sticky was the polish.
 *
 * Three visual modes via Tailwind responsive classes:
 *   • Mobile (<sm): icon-only buttons + 📚 lessons-drawer trigger left
 *   • Tablet (sm-lg): icon + label, drawer trigger still visible
 *   • Desktop (≥lg): drawer trigger hidden (sidebar always visible),
 *     full label buttons
 *
 * Extracted from the 1392-line monolith during Fase 4 architectural
 * split.
 */

import React from 'react';
import { useTranslation } from 'react-i18next';
import { BookOpen, Check, ChevronLeft, ChevronRight } from 'lucide-react';


export default function LessonActionBar({
  lesson,
  isCompleted,
  hasPrev,
  hasNext,
  onMarkCompleted,
  onPrev,
  onNext,
  onOpenLessons,
}) {
  const { t } = useTranslation('customer_portal');
  if (!lesson) return null;

  return (
    <div
      // `top-14` = under the TopBar (h-14). z-20 < TopBar's z-30 so the
      // TopBar always paints above us when both sticky. backdrop-blur
      // gives the bar a frosted-glass feel when scrolled-over content
      // shows through (modern feel on iOS/macOS Safari + Chromium).
      className="sticky top-14 z-20 bg-white/95 backdrop-blur supports-[backdrop-filter]:bg-white/80 border border-gray-200 rounded-xl shadow-sm"
    >
      <div className="flex items-center gap-2 px-3 py-2">
        {/* Mobile-only: open lessons bottom-sheet drawer.
            Hidden on lg+ where the sidebar is always visible. */}
        <button
          type="button"
          onClick={onOpenLessons}
          className="lg:hidden inline-flex items-center justify-center h-8 w-8 rounded-md border border-gray-300 hover:bg-gray-100 shrink-0"
          aria-label={t('customer_portal:actionBar.openLessonsAria')}
          title={t('customer_portal:player.lessonsHeading')}
        >
          <BookOpen className="h-4 w-4 text-gray-700" />
        </button>

        {/* Lesson context — module breadcrumb + title.
            Truncates on narrow viewports so the bar never wraps to 2
            lines (a sticky bar that grows is jarring on scroll). */}
        <div className="flex-1 min-w-0">
          <p className="text-[10px] uppercase tracking-wider text-gray-500 font-semibold truncate leading-tight">
            {lesson.module_title}
          </p>
          <p className="text-sm font-semibold text-gray-900 truncate leading-tight">
            {lesson.title}
          </p>
        </div>

        {/* Action cluster — mark + prev + next. Icons-only on mobile;
            icon+label from sm up. Mark uses emerald to signal "positive
            progress action", prev is outline-secondary, next is the
            primary dark CTA (the most-used navigation in a course). */}
        <div className="flex items-center gap-1.5 shrink-0">
          {isCompleted ? (
            <span
              className="inline-flex items-center gap-1 rounded-md bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 sm:px-3 h-8 text-xs font-semibold cursor-default"
              title={t('customer_portal:actionBar.alreadyCompletedTitle')}
              aria-label={t('customer_portal:actionBar.alreadyCompletedAria')}
            >
              <Check className="h-3.5 w-3.5 shrink-0" />
              <span className="hidden sm:inline">{t('customer_portal:actionBar.completedLabel')}</span>
            </span>
          ) : (
            <button
              type="button"
              onClick={onMarkCompleted}
              className="inline-flex items-center gap-1 rounded-md bg-emerald-600 text-white hover:bg-emerald-700 px-2 sm:px-3 h-8 text-xs font-semibold transition-colors"
              title={t('customer_portal:actionBar.markCompletedTitle')}
              aria-label={t('customer_portal:actionBar.markCompletedTitle')}
            >
              <Check className="h-3.5 w-3.5 shrink-0" />
              <span className="hidden sm:inline">{t('customer_portal:actionBar.completeLabel')}</span>
            </button>
          )}
          <button
            type="button"
            onClick={onPrev}
            disabled={!hasPrev}
            className="inline-flex items-center justify-center h-8 w-8 sm:w-auto sm:gap-1 sm:px-3 rounded-md border border-gray-300 hover:bg-gray-100 text-xs font-semibold disabled:opacity-40 disabled:cursor-not-allowed"
            title={t('customer_portal:actionBar.prevTitle')}
            aria-label={t('customer_portal:actionBar.prevTitle')}
          >
            <ChevronLeft className="h-4 w-4" />
            <span className="hidden sm:inline">{t('customer_portal:actionBar.prevShort')}</span>
          </button>
          <button
            type="button"
            onClick={onNext}
            disabled={!hasNext}
            className="inline-flex items-center justify-center h-8 w-8 sm:w-auto sm:gap-1 sm:px-3 rounded-md bg-gray-900 text-white hover:bg-gray-800 text-xs font-semibold disabled:opacity-40 disabled:cursor-not-allowed"
            title={t('customer_portal:actionBar.nextTitle')}
            aria-label={t('customer_portal:actionBar.nextTitle')}
          >
            <span className="hidden sm:inline">{t('customer_portal:actionBar.nextShort')}</span>
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
