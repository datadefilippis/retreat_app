/**
 * useLessonNavigation — bundles three concerns that all key off the
 * same data (selected lesson + flat lesson list):
 *
 *   1. handlePrev / handleNext (with hasPrev / hasNext flags)
 *   2. Keyboard shortcuts: ← → for nav, M for mark-completed
 *   3. URL hash sync: `#lesson-<id>` reflects the active lesson
 *
 * Why one hook for three things: they're all "navigation-y" concerns
 * that consume `flatLessons` + `selectedLessonId` and that any future
 * feature (e.g. a shareable lesson URL builder) would also want
 * grouped. Splitting them into three separate hooks would force the
 * orchestrator to thread the same dependencies into each one — more
 * import surface, no clarity win.
 *
 * Inputs:
 *   flatLessons          — array of `{ id, ... }` in playback order
 *   selectedLessonId     — current selection (string | null)
 *   setSelectedLessonId  — state setter from the orchestrator
 *   isCurrentCompleted   — boolean, tells the M shortcut whether to
 *                          fire (M is a no-op on already-completed)
 *   onMarkCompleted      — handler for the M shortcut
 *
 * Outputs:
 *   handlePrev, handleNext, hasPrev, hasNext
 *
 * Side effects (handled internally via useEffect):
 *   • window.addEventListener('keydown', ...) — input/modifier guards
 *   • window.history.replaceState — write hash on selection change
 *
 * Initial-load hash reading is NOT part of this hook — it has to
 * happen in the orchestrator's `load` callback because hash priority
 * mixes with "first incomplete" and "first lesson" fallbacks (see
 * the orchestrator's `load` for the priority chain).
 *
 * Extracted from the 1392-line monolith during Fase 4 architectural
 * split.
 */

import { useEffect } from 'react';


export default function useLessonNavigation({
  flatLessons,
  selectedLessonId,
  setSelectedLessonId,
  isCurrentCompleted,
  onMarkCompleted,
}) {
  // Derived navigation state — recomputed on every render. Cheap;
  // wrapping in useMemo would add complexity without real benefit.
  const selectedIndex = flatLessons.findIndex(l => l.id === selectedLessonId);
  const hasPrev = selectedIndex > 0;
  const hasNext = selectedIndex >= 0 && selectedIndex < flatLessons.length - 1;

  const handlePrev = () => {
    if (hasPrev) setSelectedLessonId(flatLessons[selectedIndex - 1].id);
  };
  const handleNext = () => {
    if (hasNext) setSelectedLessonId(flatLessons[selectedIndex + 1].id);
  };

  /* Keyboard shortcuts — ← → for prev/next, M for mark-completed.
   *
   * Power-user UX. Ignored when:
   *   • Focus is in an input/textarea/contenteditable (so typing
   *     letters in the email-verification banner doesn't navigate)
   *   • Any modifier (Cmd/Ctrl/Alt/Shift) is held — those belong to
   *     system shortcuts (cmd+arrow = page nav, etc.)
   *   • The selected lesson is already completed (M is a no-op)
   *
   * The Bunny iframe captures Space / J / L / arrows when focused
   * (its own seek/play shortcuts), so our window-level ← → only fire
   * when the iframe doesn't have focus — exactly the desired behavior.
   */
  useEffect(() => {
    const handleKey = (e) => {
      const tag = e.target?.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || e.target?.isContentEditable) return;
      if (e.metaKey || e.ctrlKey || e.altKey || e.shiftKey) return;

      if (e.key === 'ArrowLeft' && hasPrev) {
        e.preventDefault();
        handlePrev();
      } else if (e.key === 'ArrowRight' && hasNext) {
        e.preventDefault();
        handleNext();
      } else if ((e.key === 'm' || e.key === 'M') && selectedLessonId) {
        if (!isCurrentCompleted) {
          e.preventDefault();
          onMarkCompleted?.();
        }
      }
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hasPrev, hasNext, selectedLessonId, isCurrentCompleted, onMarkCompleted]);

  /* URL hash sync — `#lesson-<lid>` reflects the selected lesson.
   *
   * Why: lets the customer refresh the page (or bookmark a specific
   * lesson within their own course) and resume exactly where they
   * were. Hash-based vs path-based was chosen so we don't need
   * server-side route handling for individual lessons — the hash is
   * pure client-side state.
   *
   * Replace (not push) so the browser back button still goes to
   * /account/courses, not through every lesson the customer browsed.
   */
  useEffect(() => {
    if (!selectedLessonId) return;
    const desired = `#lesson-${selectedLessonId}`;
    if (window.location.hash !== desired) {
      window.history.replaceState(
        null,
        '',
        `${window.location.pathname}${window.location.search}${desired}`,
      );
    }
  }, [selectedLessonId]);

  return { handlePrev, handleNext, hasPrev, hasNext };
}
