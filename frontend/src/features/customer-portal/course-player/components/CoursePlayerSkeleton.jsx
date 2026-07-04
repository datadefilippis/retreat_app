/**
 * CoursePlayerSkeleton — full-page placeholder during the initial
 * course-detail fetch.
 *
 * Replaces the flat "Caricamento…" centered text with a layout-shaped
 * skeleton (sidebar + player area + lesson details). Matches the
 * real grid breakpoints (1-col mobile, 320px+1fr ≥lg) so the page
 * doesn't shift when data lands. Coherent with the Phase 7 polish on
 * the rest of the customer portal (OrdersPage, CoursesIndexPage,
 * OrderDetailPage).
 *
 * The skeleton intentionally does NOT include the sticky action bar
 * shape — when there's no lesson selected the action bar isn't
 * visible in the real page either, so no point promising it during
 * loading.
 *
 * Extracted from the 1392-line monolith during Fase 4 architectural
 * split. Reuses the Phase 7 `<Skeleton>` atom for individual blocks.
 */

import React from 'react';
import { useTranslation } from 'react-i18next';
import Skeleton from '../../components/Skeleton';


export default function CoursePlayerSkeleton() {
  const { t } = useTranslation('customer_portal');
  return (
    <div
      className="space-y-3"
      role="status"
      aria-busy="true"
      aria-label={t('customer_portal:playerSkeleton.loadingAria')}
    >
      {/* Header row — back link + title */}
      <div className="space-y-2">
        <Skeleton.Text width="100px" />
        <Skeleton className="h-6 w-2/3 max-w-md" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-4">
        {/* Sidebar skeleton — desktop only (mirrors the real `hidden lg:block`) */}
        <aside className="hidden lg:block space-y-2">
          {/* Riepilogo card with ring + tiles placeholder */}
          <div className="bg-white rounded-xl border border-gray-200 p-3">
            <div className="flex items-center gap-3">
              <Skeleton className="rounded-full h-[72px] w-[72px] shrink-0" />
              <div className="flex-1 space-y-1.5">
                <Skeleton.Text width="60%" />
                <Skeleton.Text width="80%" />
                <Skeleton.Text width="50%" />
              </div>
            </div>
          </div>
          {/* 3 module placeholders */}
          {[1, 2, 3].map(i => (
            <div
              key={i}
              className="bg-white rounded-xl border border-gray-200 p-3 space-y-2"
            >
              <Skeleton.Text width="70%" tall />
              <Skeleton.Text width="50%" />
            </div>
          ))}
        </aside>

        {/* Main column — player + lesson details */}
        <main className="space-y-4 min-w-0">
          {/* Player aspect-video block */}
          <Skeleton.Block aspectRatio="16/9" className="rounded-2xl" />
          {/* Lesson details card placeholder */}
          <div className="bg-white rounded-2xl border border-gray-200 p-5 space-y-3">
            <Skeleton.Text width="20%" />
            <Skeleton className="h-5 w-2/3 max-w-md" />
            <Skeleton.Text width="30%" />
            <div className="space-y-2 pt-2">
              <Skeleton.Text width="100%" />
              <Skeleton.Text width="90%" />
              <Skeleton.Text width="70%" />
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
