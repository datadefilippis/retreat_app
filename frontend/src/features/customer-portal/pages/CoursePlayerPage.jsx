/**
 * CoursePlayerPage — re-export of the orchestrator.
 *
 * Phase 4 of the course player optimization split the monolithic
 * `customer-portal/courses/CourseDetailPage.js` (1392 lines) into ~10
 * small files under `customer-portal/course-player/`. This file is
 * the single import point used by App.js (mounting the route under
 * <CustomerLayout>), so the indirection lets the orchestrator change
 * shape (e.g. become an Outlet host for sub-routes in the future)
 * without touching App.js.
 *
 * Naming convention: every customer-portal route lives in pages/
 * even when its implementation is elsewhere — keeps App.js's import
 * block readable as a flat index of routes.
 */

export { default } from '../course-player/CoursePlayerPage';
