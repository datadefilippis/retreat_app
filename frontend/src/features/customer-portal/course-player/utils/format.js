/**
 * Format helpers — pure functions used across the course player surface.
 *
 * Extracted from the 1392-line monolith `courses/CourseDetailPage.js`
 * during the Fase 4 architectural split. No React, no JSX, no side
 * effects → trivially testable, importable from anywhere (sidebar
 * summary, lesson rows, action bar, details card, skeleton, etc.).
 *
 * Italian-locale formatting choices intentional: this surface is
 * customer-area only (i18n storefront work is decoupled). When a
 * second locale is added the helpers gain a `locale` parameter; for
 * now Italian is the only consumer.
 */

/**
 * formatLessonDuration — short "ms" / "m:ss" / "m min" string for a
 * single lesson row in the sidebar. Returns "—" for missing/zero.
 *
 * Examples:
 *   45     → "45s"
 *   60     → "1 min"
 *   90     → "1:30"
 *   3600   → "60:00"
 */
export function formatLessonDuration(seconds) {
  if (!seconds || seconds <= 0) return '—';
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  if (m === 0) return `${s}s`;
  if (s === 0) return `${m} min`;
  return `${m}:${String(s).padStart(2, '0')}`;
}


/**
 * formatDurationHM — "X h Y m" / "X h" / "Y min" for a course total
 * (sum of all lesson durations). Used in the sidebar Riepilogo tile.
 * Returns "" for missing/zero so the consumer can hide the row.
 *
 * Examples:
 *   45 * 60   → "45 min"
 *   60 * 60   → "1h"
 *   90 * 60   → "1h 30m"
 */
export function formatDurationHM(seconds) {
  if (!seconds || seconds <= 0) return '';
  const mins = Math.round(seconds / 60);
  if (mins < 60) return `${mins} min`;
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return m === 0 ? `${h}h` : `${h}h ${m}m`;
}


/**
 * formatDateShort — locale-aware short date "31 dic 2025" / "Dec 31,
 * 2025" / "31. Dez. 2025" / "31 déc. 2025" depending on `locale`.
 * Defaults to it-IT for callers that haven't migrated to thread the
 * locale yet. Empty string on missing/invalid input so the consumer
 * can hide.
 */
export function formatDateShort(iso, locale = 'it-IT') {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleDateString(locale, {
      day: 'numeric', month: 'short', year: 'numeric',
    });
  } catch { return ''; }
}
