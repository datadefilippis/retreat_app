/**
 * Skeleton — base shimmer placeholder.
 *
 * Phase 7 of the customer area refactor (polish). Replaces the centered
 * `<Loader2 />` spinner that used to fill the page during data fetch
 * with content-shaped placeholders. The win: the customer sees the page
 * structure (header, sections, cards) immediately, and the actual data
 * fades into place when ready. Reduces perceived latency vs. a generic
 * spinner that gives no spatial cues.
 *
 * Implementation: a plain `<div>` with `animate-pulse` and a neutral
 * gray background. Tailwind's built-in pulse keyframes are good enough
 * — no custom CSS needed. We expose two convenience variants:
 *
 *   <Skeleton.Text width="60%" />   → single line of text
 *   <Skeleton.Block aspectRatio="16/9" /> → image/cover placeholder
 *
 * Both fall back to `<Skeleton />` (a vanilla rectangle) when the
 * caller wants total control via className. This keeps the API tiny
 * (one component + two thin wrappers) while covering the 95% case.
 *
 * Accessibility: skeletons are decorative. The page-level container
 * sets `role="status"` + `aria-busy="true"` so screen readers announce
 * the loading state once instead of yelling about every grey box.
 */

import React from 'react';


function Skeleton({ className = '', style }) {
  return (
    <div
      aria-hidden="true"
      className={`animate-pulse bg-gray-200/80 rounded ${className}`}
      style={style}
    />
  );
}


/**
 * Skeleton.Text — single-line text placeholder.
 * Use for headings, meta lines, single-row info. Default height is
 * 0.75rem (text-xs) — bump with the `tall` prop for larger text.
 */
function SkeletonText({ width = '100%', tall = false, className = '' }) {
  return (
    <Skeleton
      className={`${tall ? 'h-4' : 'h-3'} ${className}`}
      style={{ width }}
    />
  );
}


/**
 * Skeleton.Block — rectangular placeholder with optional aspect ratio.
 * Use for cover images, banners, avatar squares. When `aspectRatio` is
 * set, the height is derived from width (Tailwind's `aspect-[…]` class).
 */
function SkeletonBlock({ aspectRatio, className = '', style }) {
  const aspectClass = aspectRatio ? `aspect-[${aspectRatio}]` : '';
  return <Skeleton className={`${aspectClass} ${className}`} style={style} />;
}


Skeleton.Text = SkeletonText;
Skeleton.Block = SkeletonBlock;

export default Skeleton;
