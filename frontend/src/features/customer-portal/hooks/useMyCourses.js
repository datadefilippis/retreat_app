/**
 * useMyCourses — fetch the logged-in customer's active enrollments.
 *
 * Returns:
 *   { courses, loading, hasAnyCourse, inProgress, completed, retry }
 *
 *   - `courses`: full list as returned by GET /api/customer/courses
 *   - `hasAnyCourse`: boolean shortcut for conditional UI (sidebar
 *     pill, HomePage carousel, etc.)
 *   - `inProgress`: courses with 0 < percentage < 100 — the most
 *     useful set for the HomePage "Continua un corso" carousel
 *   - `completed`: percentage >= 100
 *
 * Failure is silent (returns empty list) — the courses area is
 * conditional anyway and we don't want to flag a customer that has
 * 0 courses as "errored".
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { customerPortalAPI } from '../../../api/customerPortal';


export default function useMyCourses() {
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(true);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);

  const load = useCallback(async () => {
    if (!mountedRef.current) return;
    setLoading(true);
    try {
      const res = await customerPortalAPI.getMyCourses();
      if (!mountedRef.current) return;
      setCourses(res.data?.courses || []);
    } catch {
      // Intentional silent failure — see header comment.
      if (mountedRef.current) setCourses([]);
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const inProgress = useMemo(
    () => courses.filter(e => {
      const pct = e.progress_stats?.percentage || 0;
      return pct > 0 && pct < 100;
    }),
    [courses],
  );

  const completed = useMemo(
    () => courses.filter(e => (e.progress_stats?.percentage || 0) >= 100),
    [courses],
  );

  const notStarted = useMemo(
    () => courses.filter(e => (e.progress_stats?.percentage || 0) === 0),
    [courses],
  );

  return {
    courses,
    loading,
    hasAnyCourse: courses.length > 0,
    inProgress,
    completed,
    notStarted,
    retry: load,
    reload: load,
  };
}
