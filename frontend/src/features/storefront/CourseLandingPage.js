/**
 * CourseLandingPage — public landing for a video course (Release 4 Step 3).
 *
 * Route: /co/:org_slug/:product_slug
 *
 * Mirrors DigitalLandingPage's structure but is purpose-built for course
 * discovery:
 *   - Accordion curriculum (modules → lessons with duration, no video)
 *   - Instructor bio card
 *   - Access policy badge (lifetime / N days)
 *   - "Account required" banner when the visitor is not logged in
 *   - CTA "Aggiungi al carrello" that handoffs to storefront via preloadCart
 *
 * Security note: the backend intentionally omits bunny_video_guid from
 * course_preview (see public.py PublicCourseLesson). The landing is
 * 100% public — nothing on this page can play any video.
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { GraduationCap, ShoppingCart } from 'lucide-react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { Trans, useTranslation } from 'react-i18next';
import i18nInstance from '../../i18n';
import { toast } from 'sonner';
import { storefrontAPI } from '../../api/storefront';
import useProductSeo from './lib/useProductSeo';
import OpenCheckoutButton from './components/OpenCheckoutButton';
import useCartCount from './hooks/useCartCount';
import { useCustomerAuth } from '../../context/CustomerAuthContext';
import { formatAmount } from '../../utils/currency';
import StoreContextNav from './components/StoreContextNav';


/* ─── Helpers ─────────────────────────────────────────────────────────────── */

// `t` is threaded in so the "h"/"min" suffixes localize. Falls back to IT
// when t is not provided (legacy callers).
function formatDurationHM(seconds, t = null) {
  const tt = t || ((k, v) => {
    // IT fallback so the function still works in pure-JS contexts.
    if (k === 'landings:course.fmt.durationZero') return '0 min';
    if (k === 'landings:course.fmt.durationLessThanHour') return `${v.m} min`;
    if (k === 'landings:course.fmt.durationHourOnly') return `${v.h}h`;
    if (k === 'landings:course.fmt.durationHourMin') return `${v.h}h ${v.m}min`;
    return '';
  });
  if (!seconds || seconds <= 0) return tt('landings:course.fmt.durationZero');
  const mins = Math.round(seconds / 60);
  if (mins < 60) return tt('landings:course.fmt.durationLessThanHour', { m: mins });
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return m === 0
    ? tt('landings:course.fmt.durationHourOnly', { h })
    : tt('landings:course.fmt.durationHourMin', { h, m });
}


function formatLessonDuration(seconds) {
  if (!seconds || seconds <= 0) return '—';
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  if (m === 0) return `${s}s`;
  if (s === 0) return `${m} min`;
  return `${m}:${String(s).padStart(2, '0')}`;
}


function formatEuro(n, currency = 'EUR', locale = 'it-IT') {
  if (n == null || n === '') return '—';
  // CH compliance v1: route CHF through the shared Swiss-style formatter
  // so the storefront, the email and the PDF all read the same.
  if (String(currency || '').toUpperCase() === 'CHF') {
    return formatAmount(Number(n), 'CHF');
  }
  try {
    return new Intl.NumberFormat(locale, {
      style: 'currency', currency,
    }).format(Number(n));
  } catch { return `${n} ${currency}`; }
}


/* ─── Accordion module ────────────────────────────────────────────────────── */

function ModuleAccordion({ mod, defaultOpen = false }) {
  const { t } = useTranslation('landings');
  const [open, setOpen] = useState(defaultOpen);
  const lessons = mod.lessons || [];
  const totalSec = lessons.reduce((s, l) => s + (l.duration_seconds || 0), 0);

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden bg-white">
      <button
        type="button"
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-center justify-between gap-3 px-4 py-3 text-left hover:bg-gray-50"
        aria-expanded={open}
      >
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-gray-900">{mod.title}</h3>
          <p className="text-[11px] text-gray-500 mt-0.5">
            {t('landings:course.module.lessons', { count: lessons.length })}
            {totalSec > 0 && ` · ${formatDurationHM(totalSec, t)}`}
          </p>
        </div>
        <span aria-hidden className="text-gray-400 text-lg leading-none">
          {open ? '−' : '+'}
        </span>
      </button>
      {open && (
        <ul className="divide-y divide-gray-100 border-t border-gray-100">
          {lessons.map(l => (
            <li key={l.id} className="flex items-center gap-3 px-4 py-2 text-sm">
              <span className="text-gray-400 text-[11px] font-mono w-5 shrink-0">
                {String(l.order + 1).padStart(2, '0')}
              </span>
              <span className="flex-1 min-w-0 truncate text-gray-800">
                {l.title}
              </span>
              {l.is_preview && (
                <span className="inline-flex items-center rounded-full bg-blue-100 text-blue-900 px-2 py-0.5 text-[10px] font-semibold shrink-0">
                  {t('landings:course.lessonPreview')}
                </span>
              )}
              <span className="text-xs text-gray-500 shrink-0 tabular-nums">
                ⏱ {formatLessonDuration(l.duration_seconds)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}


/* ─── Main page ───────────────────────────────────────────────────────────── */

export default function CourseLandingPage() {
  const { org_slug: orgSlug, product_slug: productSlug } = useParams();
  // 7/7 — contesto negozio: i link delle card store portano ?store=1;
  // la landing mantiene la barra menu dello store (mai uscire).
  const fromStore = new URLSearchParams(window.location.search).get('store') === '1';

  const navigate = useNavigate();
  const { t, i18n } = useTranslation('landings');
  const cartCount = useCartCount(orgSlug);
  const { isCustomerAuthenticated } = useCustomerAuth();

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    storefrontAPI.getProductLanding(orgSlug, productSlug, (i18nInstance.language || 'it').slice(0, 2))
      .then(res => { if (mounted) { setData(res.data); setLoading(false); } })
      .catch(err => {
        if (!mounted) return;
        setError(err?.response?.status === 404 ? 'not_found' : 'generic');
        setLoading(false);
      });
    return () => { mounted = false; };
  }, [orgSlug, productSlug, i18nInstance.language]);

  const product = data?.product;

  // S1 — parità SEO: meta + JSON-LD (vedi SEO_MASTER_PLAN)
  useProductSeo({ kind: 'co', orgSlug, productSlug, product,
    storeName: data?.store_info?.display_name, currency: data?.currency });
  const course = data?.course_preview;
  const currency = data?.currency || data?.store_info?.currency || 'EUR';

  const totalLessons = course?.total_lessons || 0;
  const totalDuration = course?.total_duration_seconds || 0;

  const canProceed = !!product && !!course;

  const handleProceed = useCallback(() => {
    if (!canProceed) return;
    const preloadCart = { productId: product.id, qty: 1 };
    navigate(`/s/${orgSlug}`, { state: { preloadCart } });
    toast.success(t('landings:course.toastAdded'), {
      action: {
        label: t('landings:course.toastAction'),
        onClick: () => navigate(`/s/${orgSlug}?checkout=1`),
      },
      duration: 4000,
    });
  }, [canProceed, navigate, orgSlug, product, t]);

  /* ─── Loading / errors ────────────────────────────────────────────────── */

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-gray-400">{t('landings:course.loading')}</div>
      </div>
    );
  }

  if (error === 'not_found') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
        <div className="max-w-md w-full bg-white rounded-2xl shadow-sm border p-8 text-center">
          <div className="mb-3 flex justify-center"><GraduationCap className="h-10 w-10 text-gray-300" aria-hidden /></div>
          <h1 className="text-xl font-bold text-gray-900 mb-2">{t('landings:course.notFoundTitle')}</h1>
          <p className="text-sm text-gray-600">{t('landings:course.notFoundBody')}</p>
        </div>
      </div>
    );
  }

  if (error || !product) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
        <div className="max-w-md w-full bg-white rounded-2xl shadow-sm border p-8 text-center">
          <h1 className="text-xl font-bold text-gray-900 mb-2">{t('landings:course.errorTitle')}</h1>
          <p className="text-sm text-gray-600">{t('landings:course.errorBody')}</p>
        </div>
      </div>
    );
  }

  const hero = course?.cover_image_url || product.cover_image_url || product.image_url;

  /* ─── Page ────────────────────────────────────────────────────────────── */

  return (
    <div className="min-h-screen bg-gray-50 pb-24">
      {fromStore && <StoreContextNav slug={orgSlug} />}
      {/* Back link with cart badge */}
      <div className="max-w-5xl mx-auto px-4 py-4">
        <Link
          to={`/s/${orgSlug}`}
          className="text-sm text-gray-600 hover:text-gray-900 inline-flex items-center gap-2"
        >
          <span>{t('landings:course.backToCatalog')}</span>
          {cartCount > 0 && (
            <span className="inline-flex items-center rounded-full bg-gray-900 text-white text-[10px] font-bold px-2 py-0.5">
              <ShoppingCart className="h-3 w-3 inline-block mr-0.5 align-[-1px]" aria-hidden /> {cartCount}
            </span>
          )}
        </Link>
      </div>

      {/* "Vai al checkout" banner when the cart already has items */}
      {cartCount > 0 && (
        <div className="max-w-5xl mx-auto px-4 pb-3">
          <OpenCheckoutButton slug={orgSlug} itemCount={cartCount} variant="landing" />
        </div>
      )}

      {/* Main two-column grid */}
      <div className="max-w-5xl mx-auto px-4 grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-6">

        {/* ───── LEFT: course details ────────────────────────────────── */}
        <div className="space-y-6">

          {/* Hero */}
          <div className="bg-white rounded-2xl shadow-sm border overflow-hidden">
            {hero ? (
              <div className="aspect-[16/9] bg-gray-100 overflow-hidden">
                <img src={hero} alt={product.name} className="w-full h-full object-cover" />
              </div>
            ) : null}
            <div className="p-5 sm:p-6">
              <div className="flex items-center gap-2 mb-2 flex-wrap">
                <span className="text-xs font-semibold uppercase tracking-wider text-gray-500">
                  {t('landings:course.eyebrow')}
                </span>
                {totalLessons > 0 && (
                  <span className="text-xs text-gray-500">
                    {t('landings:course.headerCount', { count: totalLessons })}
                  </span>
                )}
                {totalDuration > 0 && (
                  <span className="text-xs text-gray-500">
                    {t('landings:course.headerDuration', { duration: formatDurationHM(totalDuration, t) })}
                  </span>
                )}
              </div>
              <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">{product.name}</h1>
              {course?.instructor_name && (
                <p className="text-sm text-gray-700 mt-2">
                  <Trans
                    i18nKey="landings:course.byInstructor"
                    values={{ name: course.instructor_name }}
                    components={[<strong />]}
                  />
                </p>
              )}
              {product.description && (
                <p className="text-sm text-gray-600 mt-3 leading-relaxed">
                  {product.description}
                </p>
              )}
            </div>
          </div>

          {/* Long description */}
          {product.long_description && (
            <div className="bg-white rounded-2xl shadow-sm border p-5 sm:p-6">
              <h2 className="text-base font-semibold text-gray-900 mb-2">{t('landings:course.longDescriptionHeading')}</h2>
              <div className="text-sm text-gray-700 whitespace-pre-line leading-relaxed">
                {product.long_description}
              </div>
            </div>
          )}

          {/* Curriculum accordion */}
          {course?.modules && course.modules.length > 0 && (
            <div className="bg-white rounded-2xl shadow-sm border p-5 sm:p-6 space-y-3">
              <div className="flex items-baseline justify-between">
                <h2 className="text-base font-semibold text-gray-900">{t('landings:course.curriculumHeading')}</h2>
                <p className="text-xs text-gray-500">
                  {t('landings:course.moduleCount', { count: course.modules.length })}
                </p>
              </div>
              <div className="space-y-2">
                {course.modules.map((m, i) => (
                  <ModuleAccordion key={m.id} mod={m} defaultOpen={i === 0} />
                ))}
              </div>
            </div>
          )}

          {/* Instructor bio */}
          {course?.instructor_bio && (
            <div className="bg-white rounded-2xl shadow-sm border p-5 sm:p-6">
              <h2 className="text-base font-semibold text-gray-900 mb-2">
                {course.instructor_name
                  ? t('landings:course.instructorHeadingNamed', { name: course.instructor_name })
                  : t('landings:course.instructorHeadingFallback')}
              </h2>
              <p className="text-sm text-gray-700 whitespace-pre-line leading-relaxed">
                {course.instructor_bio}
              </p>
            </div>
          )}
        </div>

        {/* ───── RIGHT: sticky sidebar with price + CTA ───────────────── */}
        <aside className="lg:sticky lg:top-4 lg:self-start space-y-4">
          <div className="bg-white rounded-2xl shadow-sm border p-5 space-y-3">
            {/* Price */}
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wider">{t('landings:course.priceLabel')}</p>
              <p className="text-2xl font-bold text-gray-900 mt-0.5">
                {formatEuro(product.unit_price, currency, i18n.language)}
              </p>
            </div>

            {/* Access policy */}
            <div className="rounded-lg bg-gray-50 border border-gray-200 px-3 py-2">
              <p className="text-[11px] uppercase tracking-wider text-gray-500 font-semibold">
                {t('landings:course.accessLabel')}
              </p>
              <p className="text-sm text-gray-900 mt-0.5">
                {course?.access_policy === 'expiring' && course?.access_expiry_days
                  ? t('landings:course.accessExpiring', { count: course.access_expiry_days })
                  : t('landings:course.accessLifetime')}
              </p>
            </div>

            {/* Account required banner */}
            {!isCustomerAuthenticated && (
              <div className="rounded-lg bg-blue-50 border border-blue-200 px-3 py-2 text-xs text-blue-900">
                <strong>{t('landings:course.accountRequired.title')}</strong><br/>
                {t('landings:course.accountRequired.body')}
              </div>
            )}

            {/* CTA */}
            {canProceed ? (
              <button
                type="button"
                onClick={handleProceed}
                className="w-full rounded-md bg-[var(--sf-accent,#111827)] text-[var(--sf-accent-fg,#ffffff)] px-4 py-3 text-sm font-semibold hover:bg-[var(--sf-accent-hover,#1f2937)] flex items-center justify-center gap-2 transition-colors"
              >
                {t('landings:course.ctaAdd')}
              </button>
            ) : (
              <div
                aria-disabled="true"
                className="w-full rounded-md bg-gray-100 text-gray-500 px-4 py-3 text-sm font-semibold flex items-center justify-center gap-2 border border-dashed border-gray-300 cursor-not-allowed select-none"
              >
                {t('landings:course.ctaUnavailable')}
              </div>
            )}

            <p className="text-[11px] text-gray-500 text-center px-2">
              {t('landings:course.afterPurchaseHint')}
            </p>
          </div>
        </aside>
      </div>
    </div>
  );
}
