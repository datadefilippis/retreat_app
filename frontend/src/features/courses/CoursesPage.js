/**
 * CoursesPage — admin list of video courses (Release 4 Step 2).
 *
 * Mirrors the layout of the other admin dashboards (Digital, Physical, ...)
 * while keeping the UI intentionally minimal for MVP. Each row links to
 * CourseEditor for structured editing.
 *
 * The page deliberately does NOT consume Product — a Course is the content
 * entity; the commerce listing happens later via a Product with
 * item_type="course" pointing at Course.id (Step 3).
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { coursesAPI } from '../../api/courses';
// Onda 26 — admin shell. Every protected admin route MUST render its
// content inside <AppLayout> so the sidebar (defined in Layout.js)
// stays mounted on navigation. Pre-Onda 26 this page returned a bare
// <div className="min-h-screen …"> which clipped the sidebar away —
// clicking "Corsi" from the menu made the menu vanish.
import { AppLayout } from '../../components/Layout';
// Unified Bunny manager (Step 2 of UI unification).
// Same logic + visuals as the dialog version used elsewhere — single
// source of truth for the entire Bunny admin experience.
import BunnyManagerCard from './bunny-manager/BunnyManagerCard';


function formatDateShort(iso, locale = 'it-IT') {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleDateString(locale, {
      day: 'numeric', month: 'short', year: 'numeric',
    });
  } catch { return iso; }
}


function countLessons(course) {
  return (course.modules || []).reduce(
    (sum, m) => sum + (m.lessons?.length || 0),
    0,
  );
}


function countDurationMinutes(course) {
  const total = (course.modules || []).reduce(
    (sum, m) => sum + (m.lessons || []).reduce(
      (s, l) => s + (l.duration_seconds || 0), 0,
    ),
    0,
  );
  return Math.round(total / 60);
}


function PolicyBadge({ course }) {
  const { t } = useTranslation('products');
  if (course.access_policy === 'expiring') {
    return (
      <span className="inline-flex items-center rounded-full bg-amber-100 text-amber-900 px-2 py-0.5 text-[11px] font-semibold">
        {t('dashboards.course.pageList.expiringDays', { count: course.access_expiry_days })}
      </span>
    );
  }
  return (
    <span className="inline-flex items-center rounded-full bg-emerald-100 text-emerald-900 px-2 py-0.5 text-[11px] font-semibold">
      {t('dashboards.course.pageList.policyLifetime')}
    </span>
  );
}


function StatusBadge({ isActive }) {
  const { t } = useTranslation('products');
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold ${
      isActive ? 'bg-green-100 text-green-900' : 'bg-gray-200 text-gray-700'
    }`}>
      {isActive ? t('dashboards.course.pageList.statusActive') : t('dashboards.course.pageList.statusArchived')}
    </span>
  );
}


export default function CoursesPage() {
  const navigate = useNavigate();
  const { t, i18n } = useTranslation('products');
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showInactive, setShowInactive] = useState(false);
  const [enrollCounts, setEnrollCounts] = useState({});

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await coursesAPI.list({ activeOnly: !showInactive });
      // CG3 — iscritti per corso (best-effort, non blocca la lista)
      Promise.allSettled(
        (data || []).map((c) => coursesAPI.listEnrollments(c.id).then((r) => [c.id, r.data?.total ?? (r.data?.enrollments || []).length]))
      ).then((rs) => {
        const m = {};
        rs.forEach((r) => { if (r.status === 'fulfilled') m[r.value[0]] = r.value[1]; });
        setEnrollCounts(m);
      });
      setCourses(Array.isArray(data) ? data : []);
    } catch (e) {
      setError(e?.response?.data?.detail || t('dashboards.course.pageList.errorLoad'));
    } finally {
      setLoading(false);
    }
  }, [showInactive, t]);

  useEffect(() => { load(); }, [load]);

  const handleDelete = useCallback(async (course) => {
    if (!window.confirm(t('dashboards.course.pageList.archiveConfirm', { title: course.title }))) return;
    try {
      await coursesAPI.deactivate(course.id);
      toast.success(t('dashboards.course.pageList.archived'));
      await load();
    } catch (e) {
      const detail = e?.response?.data?.detail;
      toast.error(typeof detail === 'string' ? detail : t('dashboards.course.pageList.archiveError'));
    }
  }, [load, t]);

  const sorted = useMemo(() => (
    [...courses].sort((a, b) => a.title.localeCompare(b.title))
  ), [courses]);

  return (
    <AppLayout>
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6 sm:py-10">

        {/* Header */}
        <div className="flex flex-wrap items-start justify-between gap-3 mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
              <span aria-hidden>🎓</span> {t('dashboards.course.pageList.title')}
            </h1>
            <p className="text-sm text-gray-600 mt-1">
              {t('dashboards.course.pageList.subtitle')}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <label className="inline-flex items-center gap-2 text-sm text-gray-600">
              <input
                type="checkbox"
                checked={showInactive}
                onChange={(e) => setShowInactive(e.target.checked)}
                className="rounded border-gray-300"
              />
              {t('dashboards.course.pageList.showArchived')}
            </label>
            <button
              type="button"
              onClick={() => navigate('/courses/new')}
              className="rounded-md bg-gray-900 text-white px-4 py-2 text-sm font-semibold hover:bg-gray-800"
            >
              {t('dashboards.course.pageList.newCourse')}
            </button>
          </div>
        </div>

        {/* Bunny integration card — unified manager.
            Renders the right mode based on org state:
              • migrate (legacy field present, no libraries)
              • empty   (no config at all)
              • list    (1+ libraries)
              • edit    (during add/modify)
            Same component is used inside BunnyManagerDialog from the
            other entry points (Products page, CourseEditor sidebar). */}
        <div className="mb-6">
          <BunnyManagerCard />
        </div>

        {/* Body */}
        {loading ? (
          <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-500">
            {t('dashboards.course.loading')}
          </div>
        ) : error ? (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-800">
            {String(error)}
          </div>
        ) : sorted.length === 0 ? (
          <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
            <div className="text-3xl mb-2">🎬</div>
            <h2 className="text-base font-semibold text-gray-900 mb-1">
              {t('dashboards.course.pageList.emptyTitle')}
            </h2>
            <p className="text-sm text-gray-600 mb-4">
              {t('dashboards.course.pageList.emptyText')}
            </p>
            <button
              type="button"
              onClick={() => navigate('/courses/new')}
              className="rounded-md bg-gray-900 text-white px-4 py-2 text-sm font-semibold hover:bg-gray-800"
            >
              {t('dashboards.course.pageList.emptyCta')}
            </button>
          </div>
        ) : (
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-gray-600 text-xs uppercase">
                <tr>
                  <th className="px-4 py-3 text-left font-semibold">{t('dashboards.course.pageList.colTitle')}</th>
                  <th className="px-4 py-3 text-left font-semibold">{t('dashboards.course.pageList.colSlug')}</th>
                  <th className="px-4 py-3 text-left font-semibold">{t('dashboards.course.pageList.colModules')}</th>
                  <th className="px-4 py-3 text-left font-semibold">{t('dashboards.course.pageList.colLessons')}</th>
                  <th className="px-4 py-3 text-left font-semibold">{t('dashboards.course.pageList.colDuration')}</th>
                  <th className="px-4 py-3 text-left font-semibold">{t('dashboards.course.pageList.colAccess')}</th>
                  <th className="px-4 py-3 text-left font-semibold">{t('dashboards.course.pageList.colEnrolled', { defaultValue: 'Iscritti' })}</th>
                  <th className="px-4 py-3 text-left font-semibold">{t('dashboards.course.pageList.colStatus')}</th>
                  <th className="px-4 py-3 text-left font-semibold">{t('dashboards.course.pageList.colUpdated')}</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {sorted.map(c => (
                  <tr key={c.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <Link
                        to={`/courses/${c.id}`}
                        className="font-semibold text-gray-900 hover:underline"
                      >
                        {c.title}
                      </Link>
                      {c.instructor_name && (
                        <div className="text-xs text-gray-500 mt-0.5">
                          {c.instructor_name}
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3 text-gray-600 font-mono text-xs">{c.slug}</td>
                    <td className="px-4 py-3 text-gray-700">{(c.modules || []).length}</td>
                    <td className="px-4 py-3 text-gray-700">{countLessons(c)}</td>
                    <td className="px-4 py-3 text-gray-700">
                      {countDurationMinutes(c) > 0 ? t('dashboards.course.pageList.minutesSuffix', { minutes: countDurationMinutes(c) }) : '—'}
                    </td>
                    <td className="px-4 py-3"><PolicyBadge course={c} /></td>
                    <td className="px-4 py-3 text-gray-700 tabular-nums">{enrollCounts[c.id] ?? '—'}</td>
                    <td className="px-4 py-3"><StatusBadge isActive={c.is_active} /></td>
                    <td className="px-4 py-3 text-gray-500 text-xs">
                      {formatDateShort(c.updated_at, i18n.language)}
                    </td>
                    <td className="px-4 py-3 text-right whitespace-nowrap">
                      <Link
                        to={`/courses/${c.id}`}
                        className="text-xs font-semibold text-gray-700 hover:text-gray-900 mr-3"
                      >
                        {t('dashboards.course.pageList.editAction')}
                      </Link>
                      {c.is_active && (
                        <button
                          type="button"
                          onClick={() => handleDelete(c)}
                          className="text-xs font-semibold text-red-700 hover:text-red-900"
                        >
                          {t('dashboards.course.pageList.archiveAction')}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

      </div>
    </AppLayout>
  );
}
