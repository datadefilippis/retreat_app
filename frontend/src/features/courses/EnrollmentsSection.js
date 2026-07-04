/**
 * EnrollmentsSection — admin table of customers enrolled in a course
 * (Release 4 Step 8).
 *
 * Rendered inside CourseEditor when mode === "edit". Fetches on mount
 * from GET /api/courses/:id/enrollments (already admin-scoped server-side
 * so cross-org bleeding is impossible). Supports:
 *   - Toggle "Mostra revocati"
 *   - Per-row "Revoca" modal with reason textarea
 *   - Live progress bar per row
 *
 * Intentionally a flat table, no pagination for MVP — the endpoint caps
 * at 500 rows (Step 9 can add pagination if needed).
 */

import React, { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { coursesAPI } from '../../api/courses';


function formatDateShort(iso, locale = 'it-IT') {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleDateString(locale, {
      day: '2-digit', month: 'short', year: 'numeric',
    });
  } catch { return '—'; }
}


function StatusBadge({ enrollment }) {
  const { t } = useTranslation('products');
  if (enrollment.revoked_at) {
    return (
      <span className="inline-flex items-center rounded-full bg-red-100 text-red-900 px-2 py-0.5 text-[11px] font-semibold">
        {t('dashboards.course.enrollmentsSection.statusRevoked')}
      </span>
    );
  }
  const stats = enrollment.progress_stats || {};
  const pct = stats.percentage || 0;
  if (pct >= 100) {
    return (
      <span className="inline-flex items-center rounded-full bg-emerald-100 text-emerald-900 px-2 py-0.5 text-[11px] font-semibold">
        {t('dashboards.course.enrollmentsSection.statusCompleted')}
      </span>
    );
  }
  if (pct > 0) {
    return (
      <span className="inline-flex items-center rounded-full bg-blue-100 text-blue-900 px-2 py-0.5 text-[11px] font-semibold">
        {t('dashboards.course.enrollmentsSection.statusInProgress')}
      </span>
    );
  }
  return (
    <span className="inline-flex items-center rounded-full bg-gray-100 text-gray-700 px-2 py-0.5 text-[11px] font-semibold">
      {t('dashboards.course.enrollmentsSection.statusToStart')}
    </span>
  );
}


function RevokeModal({ enrollment, onClose, onConfirm }) {
  const { t, i18n } = useTranslation('products');
  const [reason, setReason] = useState(t('dashboards.course.enrollmentsSection.revokeModal.reasonDefault'));
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!reason.trim()) { toast.error(t('dashboards.course.enrollmentsSection.revokeModal.reasonRequired')); return; }
    setSubmitting(true);
    try {
      await onConfirm(reason.trim());
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl max-w-md w-full p-5 space-y-3">
        <div>
          <h3 className="text-base font-semibold text-gray-900">{t('dashboards.course.enrollmentsSection.revokeModal.title')}</h3>
          <p className="text-xs text-gray-600 mt-1">
            {t('dashboards.course.enrollmentsSection.revokeModal.warning')}
          </p>
        </div>
        <div className="rounded-md bg-gray-50 border border-gray-200 p-3 text-xs text-gray-700 space-y-0.5">
          <div><strong>{t('dashboards.course.enrollmentsSection.revokeModal.customer')}</strong> {enrollment.customer_name || '—'}</div>
          <div><strong>{t('dashboards.course.enrollmentsSection.revokeModal.email')}</strong> {enrollment.customer_email || '—'}</div>
          <div><strong>{t('dashboards.course.enrollmentsSection.revokeModal.enrolled')}</strong> {formatDateShort(enrollment.enrolled_at, i18n.language)}</div>
        </div>
        <div>
          <label className="block text-xs font-semibold uppercase tracking-wider text-gray-600 mb-1">
            {t('dashboards.course.enrollmentsSection.revokeModal.reasonLabel')}
          </label>
          <textarea
            value={reason}
            onChange={e => setReason(e.target.value)}
            rows={3}
            maxLength={500}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            placeholder={t('dashboards.course.enrollmentsSection.revokeModal.reasonPlaceholder')}
          />
        </div>
        <div className="flex items-center justify-end gap-2 pt-1">
          <button
            type="button"
            onClick={onClose}
            className="text-sm font-semibold text-gray-600 hover:text-gray-900 px-3 py-2"
          >
            {t('dashboards.course.enrollmentsSection.revokeModal.cancel')}
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={submitting}
            className="rounded-md bg-red-600 text-white text-sm font-semibold px-4 py-2 hover:bg-red-700 disabled:opacity-60"
          >
            {submitting ? t('dashboards.course.enrollmentsSection.revokeModal.submitting') : t('dashboards.course.enrollmentsSection.revokeModal.submit')}
          </button>
        </div>
      </div>
    </div>
  );
}


export default function EnrollmentsSection({ courseId }) {
  const { t, i18n } = useTranslation('products');
  const [enrollments, setEnrollments] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [includeRevoked, setIncludeRevoked] = useState(false);
  const [revokeTarget, setRevokeTarget] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await coursesAPI.listEnrollments(courseId, { includeRevoked });
      setEnrollments(data?.enrollments || []);
      setTotal(data?.total || 0);
    } catch {
      toast.error(t('dashboards.course.enrollmentsSection.loadError'));
      setEnrollments([]);
    } finally {
      setLoading(false);
    }
  }, [courseId, includeRevoked, t]);

  useEffect(() => { load(); }, [load]);

  const handleRevoke = useCallback(async (reason) => {
    if (!revokeTarget) return;
    try {
      await coursesAPI.revokeEnrollment(revokeTarget.id, { reason });
      toast.success(t('dashboards.course.enrollmentsSection.revokeModal.successToast'));
      setRevokeTarget(null);
      await load();
    } catch (e) {
      const detail = e?.response?.data?.detail;
      toast.error(typeof detail === 'string' ? detail : t('dashboards.course.enrollmentsSection.revokeModal.errorToast'));
    }
  }, [revokeTarget, load, t]);

  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-gray-900">
          {t('dashboards.course.enrollmentsSection.title')} {total > 0 && <span className="text-gray-500 font-normal">({total})</span>}
        </h2>
        <label className="inline-flex items-center gap-2 text-xs text-gray-600">
          <input
            type="checkbox"
            checked={includeRevoked}
            onChange={e => setIncludeRevoked(e.target.checked)}
            className="rounded border-gray-300"
          />
          {t('dashboards.course.enrollmentsSection.showRevoked')}
        </label>
      </div>

      {loading ? (
        <div className="bg-white rounded-xl border border-gray-200 p-6 text-center text-gray-500 text-sm">
          {t('dashboards.course.enrollmentsSection.loading')}
        </div>
      ) : enrollments.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-6 text-center">
          <p className="text-sm text-gray-600">
            {includeRevoked
              ? t('dashboards.course.enrollmentsSection.emptyAll')
              : t('dashboards.course.enrollmentsSection.emptyHidingRevoked')}
          </p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-gray-600 text-xs uppercase">
                <tr>
                  <th className="px-4 py-3 text-left font-semibold">{t('dashboards.course.enrollmentsSection.colCustomer')}</th>
                  <th className="px-4 py-3 text-left font-semibold">{t('dashboards.course.enrollmentsSection.colEnrolled')}</th>
                  <th className="px-4 py-3 text-left font-semibold">{t('dashboards.course.enrollmentsSection.colExpiry')}</th>
                  <th className="px-4 py-3 text-left font-semibold">{t('dashboards.course.enrollmentsSection.colLastAccess')}</th>
                  <th className="px-4 py-3 text-left font-semibold">{t('dashboards.course.enrollmentsSection.colProgress')}</th>
                  <th className="px-4 py-3 text-left font-semibold">{t('dashboards.course.enrollmentsSection.colStatus')}</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {enrollments.map(e => {
                  const stats = e.progress_stats || {};
                  const pct = stats.percentage || 0;
                  return (
                    <tr key={e.id} className={e.revoked_at ? 'bg-red-50/40' : 'hover:bg-gray-50'}>
                      <td className="px-4 py-3">
                        <div className="font-medium text-gray-900">
                          {e.customer_name || '—'}
                        </div>
                        <div className="text-xs text-gray-500 truncate max-w-[220px]">
                          {e.customer_email || '—'}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-600">
                        {formatDateShort(e.enrolled_at, i18n.language)}
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-600">
                        {e.expires_at ? formatDateShort(e.expires_at, i18n.language) : (
                          <span className="text-emerald-700">{t('dashboards.course.enrollmentsSection.lifetime')}</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-xs text-gray-600">
                        {formatDateShort(e.last_accessed_at, i18n.language)}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <div className="w-20 h-1.5 rounded-full bg-gray-200 overflow-hidden">
                            <div
                              className={`h-full ${pct >= 100 ? 'bg-emerald-500' : 'bg-gray-900'}`}
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                          <span className="text-xs text-gray-700 tabular-nums">
                            {stats.lessons_completed || 0}/{stats.total_lessons || 0}
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge enrollment={e} />
                        {e.revoked_at && e.revoked_reason && (
                          <div className="text-[10px] text-red-800 mt-1 max-w-[180px] truncate"
                               title={e.revoked_reason}>
                            {e.revoked_reason}
                          </div>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right whitespace-nowrap">
                        {!e.revoked_at && (
                          <button
                            type="button"
                            onClick={() => setRevokeTarget(e)}
                            className="text-xs font-semibold text-red-700 hover:text-red-900"
                          >
                            {t('dashboards.course.enrollmentsSection.revokeAction')}
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {revokeTarget && (
        <RevokeModal
          enrollment={revokeTarget}
          onClose={() => setRevokeTarget(null)}
          onConfirm={handleRevoke}
        />
      )}
    </section>
  );
}
