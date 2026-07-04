/**
 * CoursePreviewCardSkeleton — placeholder for the CoursePreviewCard.
 *
 * Matches the "full" variant geometry (the more substantial of the two
 * — includes instructor line + CTA chevron). The compact variant uses
 * the same outer footprint so a single skeleton works for both.
 *
 * Layout mirror:
 *   - 16:9 cover placeholder (matches `aspect-[16/9]` in the real card)
 *   - Title placeholder (two lines, since the real one uses line-clamp-2)
 *   - Instructor line placeholder (smaller, narrower)
 *   - Progress bar placeholder (1px line)
 *   - Bottom row: completion count + CTA chevron
 *
 * Used by CoursesIndexPage grid + HomePage "Continua un corso" section.
 */

import React from 'react';
import Skeleton from '../Skeleton';


export default function CoursePreviewCardSkeleton() {
  return (
    <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
      {/* Cover area — same 16:9 ratio as the real card's image slot */}
      <Skeleton.Block aspectRatio="16/9" className="rounded-none" />

      {/* Body */}
      <div className="p-4 space-y-2">
        {/* Title — two-line clamp simulation */}
        <Skeleton.Text width="90%" tall />
        <Skeleton.Text width="60%" tall />

        {/* Instructor line */}
        <Skeleton.Text width="40%" />

        {/* Progress bar */}
        <Skeleton className="h-1 w-full mt-2" />

        {/* Footer row: completion count + CTA */}
        <div className="flex items-center justify-between pt-1">
          <Skeleton.Text width="30%" />
          <Skeleton.Text width="20%" />
        </div>
      </div>
    </div>
  );
}
