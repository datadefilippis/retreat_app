/**
 * OrderItemCourse — order line for `item_type=course`.
 *
 * Renders, for each issued course access on this line:
 *   - course title (from snapshot)
 *   - access policy ("Accesso a vita" / "Scade il <date>")
 *   - revoked / expired badge when applicable
 *   - "Vai al corso →" deep link -> /account/courses/<enrollment_id>
 *
 * Why we surface a per-enrollment deep-link instead of relying on the
 * global "Accedi ai tuoi corsi" CTA at the top of OrderDetailPage:
 * a customer who buys multiple courses in one cart wants to jump
 * straight to the right enrollment, not bounce through the listing.
 *
 * Lesson-by-lesson progress (e.g. "2/8 lezioni completate") is NOT
 * computed here — the order detail page would have to walk the course
 * structure for every order render, which is wasteful. The per-course
 * page at /account/courses/<id> already shows the full progress.
 *
 * Empty / fallback follows the same pattern as the other issued-aware
 * renderers.
 */

import React from 'react';
import { useTranslation } from 'react-i18next';
import OrderItemBase from './OrderItemBase';


function fmtExpiryDate(iso, locale = 'it-IT') {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleDateString(locale, {
      day: '2-digit', month: 'long', year: 'numeric',
    });
  } catch { return iso.slice(0, 10); }
}


function accessSummary(enrollment, t, locale) {
  if (enrollment.revoked_at) {
    return { label: t('customer_portal:orderItemCourse.access.revoked'), classes: 'bg-red-50 text-red-700 border-red-200', accessible: false };
  }
  if (enrollment.expires_at) {
    const exp = new Date(enrollment.expires_at);
    if (!isNaN(exp.getTime()) && exp < new Date()) {
      return { label: t('customer_portal:orderItemCourse.access.expired'), classes: 'bg-amber-50 text-amber-700 border-amber-200', accessible: false };
    }
    return {
      label: t('customer_portal:orderItemCourse.access.expiresOn', { date: fmtExpiryDate(enrollment.expires_at, locale) }),
      classes: 'bg-blue-50 text-blue-700 border-blue-200',
      accessible: true,
    };
  }
  return { label: t('customer_portal:orderItemCourse.access.lifetime'), classes: 'bg-emerald-50 text-emerald-700 border-emerald-200', accessible: true };
}


export default function OrderItemCourse({ item, currency = 'EUR', order = null }) {
  const { t, i18n } = useTranslation('customer_portal');
  const allEnrollments = (order && order._issued_course_accesses) || [];
  // Match by course_id (the Lesson the customer wants is keyed on the
  // course, not on the OrderLine which carries the product reference).
  // The Course doc id is stored as `metadata.course_id` on the Product;
  // the IssuedCourseAccess carries `course_id` directly.
  const lineEnrollments = allEnrollments.filter(e => {
    if (!e.course_id) return false;
    // Two possible paths to match: explicit course_id on the line's
    // metadata, OR product_id when the issued access was indexed by
    // product link (defensive — both shapes exist in production data).
    const courseIdOnLine = (item.metadata && item.metadata.course_id) || null;
    if (courseIdOnLine && e.course_id === courseIdOnLine) return true;
    return e.product_id === item.product_id;
  });

  const hasIssuedField = order && Array.isArray(order._issued_course_accesses);
  if (!hasIssuedField) {
    return <OrderItemBase item={item} currency={currency} />;
  }

  if (lineEnrollments.length === 0) {
    return (
      <OrderItemBase item={item} currency={currency}>
        <div className="mt-2 rounded-md border border-dashed border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-900">
          {t('customer_portal:orderItemCourse.pendingHint')}
        </div>
      </OrderItemBase>
    );
  }

  return (
    <OrderItemBase item={item} currency={currency}>
      <ul className="mt-2 space-y-1.5">
        {lineEnrollments.map((e) => {
          const access = accessSummary(e, t, i18n.language);
          const url = e.id ? `/account/courses/${e.id}` : null;
          const title = e.course_title_snapshot || t('customer_portal:orderItemCourse.fallbackTitle');
          return (
            <li
              key={e.id}
              className="rounded-lg border border-gray-200 bg-white px-3 py-2 flex items-start gap-3"
            >
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-gray-900 truncate">🎓 {title}</p>
                <span
                  className={`inline-block mt-1 px-1.5 py-0.5 text-[10px] font-medium rounded border ${access.classes}`}
                >
                  {access.label}
                </span>
              </div>
              {url && access.accessible && (
                <a
                  href={url}
                  className="shrink-0 inline-flex items-center gap-1 px-3 py-1.5 rounded-md bg-gray-900 text-white text-xs font-semibold hover:bg-gray-800 transition-colors"
                >
                  {t('customer_portal:orderItemCourse.openCourse')}
                </a>
              )}
            </li>
          );
        })}
      </ul>
    </OrderItemBase>
  );
}
