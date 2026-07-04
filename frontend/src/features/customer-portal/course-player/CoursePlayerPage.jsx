/**
 * CoursePlayerPage — orchestrator for the customer course player.
 *
 * Route: /account/courses/:enrollment_id (protected, lives under
 * <CustomerLayout> via the re-export at pages/CoursePlayerPage.jsx).
 *
 * Phase 4 architectural split: this file is the thin orchestrator
 * that ties together the atomic components extracted into
 * `course-player/components/` and the navigation hook in
 * `course-player/hooks/`. It owns:
 *
 *   • The data fetch (`load`) + auto-select-on-load logic
 *   • The two server-mutation handlers (mark completed, lesson ended)
 *   • The mobile bottom-sheet drawer state
 *   • The desktop "?" cheatsheet state
 *   • The grid layout that hosts everything else
 *
 * Everything VISUAL or REUSABLE-OUTSIDE-LOAD lives in a sibling file.
 *
 * Provenance: extracted from the 1392-line monolithic
 * `customer-portal/courses/CourseDetailPage.js`, which is now
 * deleted. The route still resolves through
 * `customer-portal/pages/CoursePlayerPage.jsx` as a thin re-export
 * shim so App.js keeps the single-import-per-route convention.
 *
 * Functional behaviour preserved 1:1 across the split:
 *
 *   - Initial lesson selection priority:
 *     1. `#lesson-<id>` URL hash (refresh-stable resumption)
 *     2. First lesson without `completed_at` (continue where you left)
 *     3. Cold-start: first lesson in the course
 *   - Auto-complete on Bunny iframe `ended` event (Q3=a)
 *   - Manual mark-complete via the action bar (with celebratory toast)
 *   - Keyboard shortcuts: ← → M (skip on input focus / modifiers)
 *   - URL hash updates on selection change (replaceState, no history
 *     pollution)
 *   - Mobile bottom-sheet drawer for the sidebar; auto-closes on
 *     lesson select
 *   - Desktop floating "?" → modal cheatsheet
 *   - Backend errors mapped to dedicated error screens
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { X as XIcon } from 'lucide-react';
import { useCustomerAuth } from '../../../context/CustomerAuthContext';
import { customerPortalAPI } from '../../../api/customerPortal';

// Local atomic components (extracted in Fase 4)
import LessonPlayer from './components/LessonPlayer';
import LessonActionBar from './components/LessonActionBar';
import LessonDetails from './components/LessonDetails';
import CourseSidebar from './components/CourseSidebar';
import CoursePlayerSkeleton from './components/CoursePlayerSkeleton';
import CourseErrorScreen from './components/CourseErrorScreen';
import HelpCheatsheet from './components/HelpCheatsheet';

// Hook
import useLessonNavigation from './hooks/useLessonNavigation';


export default function CoursePlayerPage() {
  const { enrollment_id: enrollmentId } = useParams();
  const navigate = useNavigate();
  const { customer } = useCustomerAuth();
  const { t } = useTranslation('customer_portal');

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedLessonId, setSelectedLessonId] = useState(null);
  // Mobile bottom-sheet drawer for the lesson list. Desktop (≥lg) has
  // the sidebar always visible in the grid's left column, so this
  // state is a no-op there. On mobile the sidebar is hidden in the
  // grid and accessed exclusively through the "📚 Lezioni" button in
  // the sticky LessonActionBar.
  const [lessonsDrawerOpen, setLessonsDrawerOpen] = useState(false);
  // Keyboard-shortcuts cheatsheet — desktop power-user affordance.
  const [helpOpen, setHelpOpen] = useState(false);

  /* ─── Data fetch ─────────────────────────────────────────────────────── */

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await customerPortalAPI.getCourseDetail(enrollmentId);
      setData(data);
      const modules = data?.course?.modules || [];
      const all = modules.flatMap(m => m.lessons || []);

      // Initial lesson selection priority:
      //   1. URL hash `#lesson-<id>` if it points to a real lesson
      //      (refresh-stable resumption + intra-account shareable)
      //   2. First incomplete lesson (continue where you left off)
      //   3. First lesson in the course (cold start)
      const hash = typeof window !== 'undefined' ? window.location.hash : '';
      const hashId = hash.startsWith('#lesson-') ? hash.slice('#lesson-'.length) : null;
      const fromHash = hashId ? all.find(l => l.id === hashId) : null;
      const firstIncomplete = all.find(l => !data?.progress?.[l.id]?.completed_at);
      setSelectedLessonId((fromHash || firstIncomplete || all[0])?.id || null);
    } catch (err) {
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail;
      const code = typeof detail === 'object' ? detail.error : null;
      if (status === 404) setError({ kind: 'not_found' });
      else if (status === 403 && code === 'enrollment_revoked') setError({ kind: 'revoked' });
      else if (status === 403 && code === 'enrollment_expired') setError({ kind: 'expired' });
      else if (status === 410) setError({ kind: 'course_unavailable' });
      else setError({ kind: 'generic' });
    } finally {
      setLoading(false);
    }
  }, [enrollmentId]);

  useEffect(() => { load(); }, [load]);

  /* ─── Derived state ──────────────────────────────────────────────────── */

  const course = data?.course;
  const progress = data?.progress || {};
  const progressStats = data?.progress_stats || {};

  const flatLessons = useMemo(() => {
    if (!course?.modules) return [];
    return course.modules.flatMap(m =>
      (m.lessons || []).map(l => ({ ...l, module_id: m.id, module_title: m.title })),
    );
  }, [course]);

  const selectedLesson = flatLessons.find(l => l.id === selectedLessonId) || null;
  const isCurrentCompleted = !!(selectedLessonId && progress?.[selectedLessonId]?.completed_at);

  /* ─── Mutation handlers ──────────────────────────────────────────────── */

  /* Callback from LessonPlayer when /progress returns fresh state */
  const handleProgressUpdate = useCallback((resp) => {
    if (!resp?.lesson_id) return;
    setData(prev => {
      if (!prev) return prev;
      const newProgress = { ...(prev.progress || {}) };
      newProgress[resp.lesson_id] = {
        watched_seconds: resp.watched_seconds,
        completed_at: resp.completed_at,
      };
      return {
        ...prev,
        progress: newProgress,
        progress_stats: resp.progress_stats || prev.progress_stats,
      };
    });
  }, []);

  /* Called by the player when the server responds with 403 */
  const handleAccessRevoked = useCallback((code) => {
    const msg = code === 'enrollment_expired'
      ? t('customer_portal:player.toast.accessExpired')
      : t('customer_portal:player.toast.accessRevoked');
    toast.error(msg);
    navigate('/account/courses');
  }, [navigate, t]);

  /* Mark the currently selected lesson as completed.
   *
   * We send `lesson.duration_seconds` as `watched_seconds` so the
   * lesson reads as 100% even if the user clicked "completed" early.
   * The server's max() preserves any larger heartbeat-recorded value,
   * so this never regresses progress.
   */
  const handleMarkCompleted = useCallback(async () => {
    const lessonId = selectedLessonId;
    if (!lessonId) return;
    const lessonDef = flatLessons.find(l => l.id === lessonId);
    if (!lessonDef) return;
    try {
      const { data: resp } = await customerPortalAPI.sendProgress(enrollmentId, {
        lesson_id: lessonId,
        watched_seconds: lessonDef.duration_seconds || 0,
        completed: true,
      });
      handleProgressUpdate(resp);
      toast.success(t('customer_portal:player.toast.lessonCompleted'));
    } catch (err) {
      const code = err?.response?.data?.detail?.error;
      if (code === 'enrollment_revoked' || code === 'enrollment_expired') {
        handleAccessRevoked(code);
        return;
      }
      toast.error(t('customer_portal:player.toast.progressError'));
    }
  }, [enrollmentId, selectedLessonId, flatLessons, handleProgressUpdate, handleAccessRevoked, t]);

  /* Auto-complete on natural video end (Q3=a — fires immediately
   * when Bunny's iframe sends the `ended` event via postMessage).
   *
   * Idempotency: skip if the lesson is already marked completed.
   * Friendlier toast than the manual handler — the customer didn't
   * take an action, so we celebrate rather than report.
   */
  const handleLessonEnded = useCallback(async () => {
    const lessonId = selectedLessonId;
    if (!lessonId) return;
    if (data?.progress?.[lessonId]?.completed_at) return;  // already done
    const lessonDef = flatLessons.find(l => l.id === lessonId);
    if (!lessonDef) return;
    try {
      const { data: resp } = await customerPortalAPI.sendProgress(enrollmentId, {
        lesson_id: lessonId,
        watched_seconds: lessonDef.duration_seconds || 0,
        completed: true,
      });
      handleProgressUpdate(resp);
      toast.success(t('customer_portal:player.toast.lessonCompletedAuto'));
    } catch (err) {
      const code = err?.response?.data?.detail?.error;
      if (code === 'enrollment_revoked' || code === 'enrollment_expired') {
        handleAccessRevoked(code);
      }
    }
  }, [enrollmentId, selectedLessonId, flatLessons, data, handleProgressUpdate, handleAccessRevoked, t]);

  /* ─── Navigation hook (handles prev/next + keyboard + hash sync) ─────── */

  const { handlePrev, handleNext, hasPrev, hasNext } = useLessonNavigation({
    flatLessons,
    selectedLessonId,
    setSelectedLessonId,
    isCurrentCompleted,
    onMarkCompleted: handleMarkCompleted,
  });

  /* ─── Loading + error guards ─────────────────────────────────────────── */

  if (!loading && error) return <CourseErrorScreen kind={error.kind} />;
  if (loading || !data || !course) return <CoursePlayerSkeleton />;

  /* ─── Page render ────────────────────────────────────────────────────── */

  // Lesson selection that ALSO closes the mobile bottom-sheet drawer.
  // No-op on desktop where the drawer state is unused, so we can pass
  // this single callback into both surfaces (sidebar + drawer).
  const handleLessonSelect = (lessonId) => {
    setSelectedLessonId(lessonId);
    setLessonsDrawerOpen(false);
  };

  // Sidebar shared between desktop column + mobile drawer — same JSX
  // tree, two placements. CourseSidebar handles its own internals.
  const sidebar = (
    <CourseSidebar
      course={course}
      progress={progress}
      progressStats={progressStats}
      enrollment={data.enrollment}
      selectedLessonId={selectedLessonId}
      onLessonSelect={handleLessonSelect}
    />
  );

  return (
    <div className="space-y-3">
      {/* Page header — back link + course title */}
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="min-w-0">
          <Link
            to="/account/courses"
            className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            {t('customer_portal:player.backToCourses')}
          </Link>
          <h1 className="text-xl font-bold text-gray-900 mt-1 truncate">
            {course.title}
          </h1>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-4">
        {/* Sidebar — desktop only (mobile uses the bottom-sheet drawer below) */}
        <aside className="hidden lg:block space-y-2">
          {sidebar}
        </aside>

        {/* Main column — player + sticky bar + details + instructor */}
        <main className="space-y-4 min-w-0">
          {selectedLesson ? (
            <LessonPlayer
              enrollmentId={enrollmentId}
              lesson={selectedLesson}
              customerEmail={customer?.email || null}
              onProgressUpdate={handleProgressUpdate}
              onAccessRevoked={handleAccessRevoked}
              onLessonEnded={handleLessonEnded}
            />
          ) : (
            // Empty state — no lesson selected. Shouldn't happen in
            // practice (we auto-select firstIncomplete on load) but
            // appears briefly during edge cases (course with 0 lessons,
            // hash pointing at a deleted lesson, etc.).
            <div className="bg-white rounded-2xl border border-gray-200 shadow-sm aspect-video flex flex-col items-center justify-center text-center px-6 gap-2">
              <div className="text-4xl" aria-hidden>📺</div>
              <p className="text-sm font-semibold text-gray-900">{t('customer_portal:player.readyTitle')}</p>
              {flatLessons.length > 0 ? (
                <>
                  <p className="text-xs text-gray-600 max-w-md">
                    <span className="lg:hidden">{t('customer_portal:player.pickLessonMobile')}</span>
                    <span className="hidden lg:inline">{t('customer_portal:player.pickLessonDesktop')}</span>
                  </p>
                  <button
                    type="button"
                    onClick={() => handleLessonSelect(flatLessons[0].id)}
                    className="mt-2 rounded-md bg-gray-900 text-white px-3 py-1.5 text-xs font-semibold hover:bg-gray-800"
                  >
                    {t('customer_portal:player.startFirstLesson')}
                  </button>
                </>
              ) : (
                <p className="text-xs text-gray-600 max-w-md">
                  {t('customer_portal:player.noLessonsYet')}
                </p>
              )}
            </div>
          )}

          {/* Sticky action bar — Mark / Prev / Next + mobile drawer trigger */}
          {selectedLesson && (
            <LessonActionBar
              lesson={selectedLesson}
              isCompleted={isCurrentCompleted}
              hasPrev={hasPrev}
              hasNext={hasNext}
              onMarkCompleted={handleMarkCompleted}
              onPrev={handlePrev}
              onNext={handleNext}
              onOpenLessons={() => setLessonsDrawerOpen(true)}
            />
          )}

          {/* Lesson details — title + duration + description + resources */}
          {selectedLesson && (
            <LessonDetails
              lesson={selectedLesson}
              completedAt={progress?.[selectedLesson.id]?.completed_at}
            />
          )}

          {/* Instructor card — last because it's static "about" content */}
          {course.instructor_name && (
            <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5">
              <h3 className="text-base font-semibold text-gray-900">
                {course.instructor_name}
              </h3>
              {course.instructor_bio && (
                <p className="text-sm text-gray-700 mt-2 whitespace-pre-line leading-relaxed">
                  {course.instructor_bio}
                </p>
              )}
            </div>
          )}
        </main>
      </div>

      {/* ── Floating help button + cheatsheet (desktop only) ──────────── */}
      <button
        type="button"
        onClick={() => setHelpOpen(true)}
        className="hidden lg:flex fixed bottom-4 right-4 z-30 h-10 w-10 items-center justify-center rounded-full bg-gray-900 text-white shadow-lg hover:bg-gray-800 transition-colors text-sm font-bold"
        title={t('customer_portal:player.shortcutsTitle')}
        aria-label={t('customer_portal:player.shortcutsAria')}
      >
        ?
      </button>
      <HelpCheatsheet open={helpOpen} onClose={() => setHelpOpen(false)} />

      {/* ── Mobile bottom-sheet drawer for the lesson list ────────────────
          Hidden on desktop where the sidebar is always visible. Opened
          by the 📚 trigger inside LessonActionBar. Auto-closes when the
          customer picks a lesson (via handleLessonSelect above). */}
      {lessonsDrawerOpen && (
        <div className="lg:hidden fixed inset-0 z-50">
          {/* Backdrop — click to close */}
          <button
            type="button"
            aria-label={t('customer_portal:player.closeLessonsAria')}
            onClick={() => setLessonsDrawerOpen(false)}
            className="absolute inset-0 bg-black/50 cursor-default"
          />
          {/* Panel — slides up from bottom */}
          <div className="absolute inset-x-0 bottom-0 bg-white rounded-t-2xl max-h-[80vh] flex flex-col shadow-2xl animate-in slide-in-from-bottom duration-200">
            <div className="shrink-0 px-4 pt-2 pb-3 border-b border-gray-100">
              <div className="mx-auto w-10 h-1 rounded-full bg-gray-300 mb-3" aria-hidden />
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-semibold text-gray-900">{t('customer_portal:player.lessonsHeading')}</h2>
                <button
                  type="button"
                  onClick={() => setLessonsDrawerOpen(false)}
                  className="p-1.5 -mr-1.5 rounded-md hover:bg-gray-100"
                  aria-label={t('customer_portal:player.closeShort')}
                >
                  <XIcon className="h-4 w-4 text-gray-700" />
                </button>
              </div>
            </div>
            {/* Scrollable content — same as desktop sidebar */}
            <div className="flex-1 overflow-y-auto p-3">
              {sidebar}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
