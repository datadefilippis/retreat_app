/**
 * CoursesIndexPage — list of all courses the customer is enrolled into.
 *
 * Phase 3 of the customer area refactor. Replaces the previous
 * MyCoursesPage that lived in customer-portal/courses/MyCoursesPage.js
 * (kept temporarily as a re-export so /account/courses keeps working
 * during the rollout). Differences from the legacy version:
 *
 *   - No local header — chrome comes from CustomerLayout
 *   - Uses the shared `useMyCourses` hook (handles silent failure +
 *     buckets in-progress / completed / not-started for free)
 *   - Uses `<CoursePreviewCard variant="full" />` for visual parity
 *     with the upcoming HomePage carousel (Phase 4)
 *   - `<EmptyState />` atom replaces the bespoke placeholder
 *
 * Behavior preserved 1:1: clicking a card opens the player at
 * /account/courses/:enrollment_id (handled by the Link inside the
 * CoursePreviewCard atom).
 */

import React from 'react';
import { useTranslation } from 'react-i18next';
import { useCustomerAuth } from '../../../context/CustomerAuthContext';
import useMyCourses from '../hooks/useMyCourses';
import CoursePreviewCard from '../components/CoursePreviewCard';
import CoursePreviewCardSkeleton from '../components/skeletons/CoursePreviewCardSkeleton';
import EmptyState from '../components/EmptyState';
import PageHeader from '../components/PageHeader';


export default function CoursesIndexPage() {
  const { storeSlug } = useCustomerAuth();
  const { courses, loading } = useMyCourses();
  const { t } = useTranslation('customer_portal');

  return (
    <div className="space-y-4">
      <PageHeader
        title={t('customer_portal:courses.title')}
        description={courses.length > 0
          ? t('customer_portal:courses.descriptionWithCount', { count: courses.length })
          : t('customer_portal:courses.descriptionEmpty')}
      />

      {loading ? (
        // Phase 7 polish — skeleton grid hints at the eventual layout
        // (1/2/3 columns responsive) so the page doesn't reflow when
        // real cards land. Six tiles fill a 3-column breakpoint without
        // looking sparse on tablet.
        <div
          role="status"
          aria-busy="true"
          aria-label={t('customer_portal:courses.loadingAria')}
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4"
        >
          {[1, 2, 3, 4, 5, 6].map(i => <CoursePreviewCardSkeleton key={i} />)}
        </div>
      ) : courses.length === 0 ? (
        <EmptyState
          icon="🎓"
          title={t('customer_portal:courses.emptyTitle')}
          description={t('customer_portal:courses.emptyDescription')}
          cta={storeSlug ? { to: `/s/${storeSlug}`, label: t('customer_portal:courses.exploreCatalog') } : null}
        />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {courses.map(entry => (
            <CoursePreviewCard
              key={entry.enrollment.id}
              entry={entry}
              variant="full"
              ctaLabel={t('customer_portal:courses.openCta')}
            />
          ))}
        </div>
      )}
    </div>
  );
}
