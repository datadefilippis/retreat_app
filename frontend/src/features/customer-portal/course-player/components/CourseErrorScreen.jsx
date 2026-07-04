/**
 * CourseErrorScreen — full-page friendly error state for the course
 * player route.
 *
 * Replaces 5 different error UIs that used to render inline in the
 * page when the initial fetch failed. The kinds map to the four
 * server-side error codes plus a generic catch-all:
 *
 *   not_found          — 404 from /customer/courses/:id (bad URL or
 *                        enrollment belongs to a different customer)
 *   revoked            — 403 enrollment_revoked (admin manually revoked)
 *   expired            — 403 enrollment_expired (lifetime/expiring policy)
 *   course_unavailable — 410 (course was hard-deleted by the merchant)
 *   generic            — anything else, retry-friendly
 *
 * Single CTA: "Torna a I miei corsi" — it's the only action that
 * always works regardless of the error kind. Retry would only be
 * useful for `generic` but the customer can also just refresh.
 *
 * Extracted from the 1392-line monolith during Fase 4 architectural
 * split.
 */

import React from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';


// Icon glyphs are universal, the title/body strings come from i18n.
// Keys map kind → namespace key under courseError.<key>.{title,body}.
const ICONS = {
  not_found: '🔎',
  revoked: '🚫',
  expired: '⏰',
  course_unavailable: '🛠️',
  generic: '⚠️',
};

// kind ↔ i18n sub-key (snake_case kinds → camelCase keys to match JSON).
const I18N_KEY = {
  not_found: 'notFound',
  revoked: 'revoked',
  expired: 'expired',
  course_unavailable: 'courseUnavailable',
  generic: 'generic',
};


export default function CourseErrorScreen({ kind = 'generic' }) {
  const { t } = useTranslation('customer_portal');
  const safeKind = ICONS[kind] ? kind : 'generic';
  const subKey = I18N_KEY[safeKind];
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 px-4">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-sm border p-8 text-center space-y-3">
        <div className="text-4xl">{ICONS[safeKind]}</div>
        <h1 className="text-xl font-bold text-gray-900">{t(`customer_portal:courseError.${subKey}.title`)}</h1>
        <p className="text-sm text-gray-600">{t(`customer_portal:courseError.${subKey}.body`)}</p>
        <Link
          to="/account/courses"
          className="inline-block rounded-md bg-gray-900 text-white px-4 py-2 text-sm font-semibold hover:bg-gray-800"
        >
          {t('customer_portal:courseError.backCta')}
        </Link>
      </div>
    </div>
  );
}
