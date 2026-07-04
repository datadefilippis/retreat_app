/**
 * BookingLandingPage — public page for a single confirmed service booking.
 *
 * Route: /b/:token (no authentication; the access_token is the key).
 * Backed by GET /api/public/bookings/{token} (Onda 14).
 *
 * Role in the distribution flow:
 *   When a customer books a consulenza, the confirmation email contains
 *   an "Apri prenotazione →" link per booking row. Clicking lands here.
 *   The page shows: appointment date/time, service option, location,
 *   booking code, and an "Aggiungi al calendario" button that downloads
 *   a .ics file (generated server-side by GET /api/public/bookings/{token}/ics).
 *
 * Security: leaking the URL only grants read access to this page. It
 * does NOT allow the visitor to reschedule, cancel, or mutate the booking
 * from the frontend — those actions require admin auth server-side.
 */

import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import PublicStorefrontShell from './PublicStorefrontShell';


function formatDatePretty(ymd, locale = 'it-IT') {
  if (!ymd) return '';
  try {
    const [y, m, d] = ymd.split('-').map(Number);
    const dt = new Date(y, m - 1, d, 12, 0, 0);
    return dt.toLocaleDateString(locale, {
      weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
    });
  } catch {
    return ymd;
  }
}


export default function BookingLandingPage() {
  const { token } = useParams();
  const { t, i18n } = useTranslation('landings');
  const [booking, setBooking] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      try {
        const res = await fetch(`/api/public/bookings/${encodeURIComponent(token)}`);
        if (!mounted) return;
        if (res.status === 404) { setError('not_found'); return; }
        if (!res.ok) { setError('generic'); return; }
        const data = await res.json();
        if (mounted) setBooking(data);
      } catch {
        if (mounted) setError('generic');
      } finally {
        if (mounted) setLoading(false);
      }
    };
    load();
    return () => { mounted = false; };
  }, [token]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-gray-400">{t('landings:booking.loading')}</div>
      </div>
    );
  }

  if (error === 'not_found') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
        <div className="max-w-md w-full bg-white rounded-2xl shadow-sm border p-8 text-center">
          <div className="text-4xl mb-3">🔒</div>
          <h1 className="text-xl font-bold text-gray-900 mb-2">{t('landings:booking.notFoundTitle')}</h1>
          <p className="text-sm text-gray-600">
            {t('landings:booking.notFoundBody')}
          </p>
        </div>
      </div>
    );
  }

  if (error || !booking) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
        <div className="max-w-md w-full bg-white rounded-2xl shadow-sm border p-8 text-center">
          <h1 className="text-xl font-bold text-gray-900 mb-2">{t('landings:booking.errorTitle')}</h1>
          <p className="text-sm text-gray-600">
            {t('landings:booking.errorBody')}
          </p>
        </div>
      </div>
    );
  }

  const datePretty = formatDatePretty(booking.booking_date, i18n.language);
  const timeRange = `${booking.booking_start_time || ''}${booking.booking_end_time ? ' → ' + booking.booking_end_time : ''}`;

  const icsUrl = `/api/public/bookings/${encodeURIComponent(token)}/ics`;

  // Status badge — i18n labels for the 3 known statuses, fallback to the
  // raw server status string for unknown values (defensive — should never
  // happen in practice but cheap to keep).
  const statusBadge = {
    confirmed: { label: t('landings:booking.status.confirmed'), cls: 'bg-green-100 text-green-800 border-green-200' },
    completed: { label: t('landings:booking.status.completed'), cls: 'bg-gray-100 text-gray-700 border-gray-200' },
    no_show:   { label: t('landings:booking.status.noShow'), cls: 'bg-amber-100 text-amber-800 border-amber-200' },
  }[booking.status] || { label: booking.status, cls: 'bg-gray-100 text-gray-700 border-gray-200' };

  // Wrap success render in PublicStorefrontShell so the page resolves
  // i18n.language from the storefront's storefront_languages instead
  // of leaking the locale from a previous storefront visit. Loading
  // and error states render without the shell — they have no slug yet.
  return (
    <PublicStorefrontShell slug={booking.store_slug || null}>
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-lg mx-auto">
        {/* Store header */}
        {booking.store_name && (
          <div className="mb-4 text-center">
            {booking.store_slug ? (
              <a href={`/s/${booking.store_slug}`} className="text-sm text-gray-600 hover:text-gray-900">
                ← {booking.store_name}
              </a>
            ) : (
              <div className="text-sm text-gray-600">{booking.store_name}</div>
            )}
          </div>
        )}

        {/* Main card */}
        <div className="bg-white rounded-2xl shadow-sm border overflow-hidden">
          {/* Hero */}
          {booking.product_image_url && (
            <div className="aspect-[16/9] bg-gray-100 overflow-hidden">
              <img
                src={booking.product_image_url}
                alt=""
                className="w-full h-full object-cover"
              />
            </div>
          )}

          <div className="p-6">
            <div className="flex items-start justify-between gap-3 mb-4">
              <div className="min-w-0">
                <div className="text-[11px] uppercase tracking-widest text-gray-500 font-semibold mb-1">
                  {t('landings:booking.eyebrow')}
                </div>
                <h1 className="text-2xl font-bold text-gray-900 leading-tight">
                  {booking.product_name}
                </h1>
                {booking.service_option_label && (
                  <div className="text-sm text-gray-600 mt-1">
                    {booking.service_option_label}
                  </div>
                )}
              </div>
              <span className={`shrink-0 inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-semibold border ${statusBadge.cls}`}>
                {statusBadge.label}
              </span>
            </div>

            {/* When */}
            <div className="rounded-xl border border-gray-200 p-4 mb-3">
              <div className="text-[11px] uppercase tracking-widest text-gray-500 font-semibold mb-1">
                {t('landings:booking.whenHeading')}
              </div>
              <div className="text-base text-gray-900 font-semibold capitalize">
                {datePretty}
              </div>
              <div className="text-sm text-gray-700 mt-0.5">
                {timeRange}
              </div>
            </div>

            {/* Where */}
            {booking.location && (
              <div className="rounded-xl border border-gray-200 p-4 mb-3">
                <div className="text-[11px] uppercase tracking-widest text-gray-500 font-semibold mb-1">
                  {t('landings:booking.whereHeading')}
                </div>
                <div className="text-sm text-gray-900">
                  📍 {booking.location}
                </div>
              </div>
            )}

            {/* Holder */}
            {booking.holder_name && (
              <div className="rounded-xl border border-gray-200 p-4 mb-3">
                <div className="text-[11px] uppercase tracking-widest text-gray-500 font-semibold mb-1">
                  {t('landings:booking.holderHeading')}
                </div>
                <div className="text-sm text-gray-900">
                  {booking.holder_name}
                </div>
                {booking.holder_email && (
                  <div className="text-xs text-gray-500 mt-0.5">
                    {booking.holder_email}
                  </div>
                )}
              </div>
            )}

            {/* Code */}
            <div className="rounded-xl border border-gray-200 p-4 mb-4">
              <div className="text-[11px] uppercase tracking-widest text-gray-500 font-semibold mb-1">
                {t('landings:booking.codeHeading')}
              </div>
              <div className="font-mono text-base text-gray-900 tracking-wider">
                {booking.code}
              </div>
              <div className="text-xs text-gray-500 mt-1">
                {t('landings:booking.codeHint')}
              </div>
            </div>

            {/* Add to calendar CTA */}
            {booking.status === 'confirmed' && (
              <a
                href={icsUrl}
                className="w-full inline-flex items-center justify-center gap-2 bg-[var(--sf-accent,#111827)] text-[var(--sf-accent-fg,#ffffff)] font-semibold px-4 py-3 rounded-xl hover:bg-[var(--sf-accent-hover,#1f2937)] transition-colors"
              >
                {t('landings:booking.addToCalendar')}
              </a>
            )}
          </div>
        </div>

        <p className="text-center text-xs text-gray-400 mt-6">
          {t('landings:booking.privateLinkHint')}
        </p>
      </div>
    </div>
    </PublicStorefrontShell>
  );
}
