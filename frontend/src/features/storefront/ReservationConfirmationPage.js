/**
 * ReservationConfirmationPage — public page for a single confirmed reservation.
 *
 * Route: /rsv/:token (no authentication; the access_token is the key).
 * Backed by GET /api/public/reservations/{token} (Onda 16 Fase 2).
 *
 * Handles both reservation flavors uniformly:
 *   - range: date_from → date_to (multi-day, e.g. B&B, car rental)
 *   - slot:  slot_date + slot_start_time → slot_end_time (single-shot, e.g. meeting room)
 *
 * Shows extras_snapshot[] breakdown (mandatory / optional / radio_variant)
 * so the customer sees exactly what they booked, with a per-item price.
 *
 * Security: leaking the URL only grants read access. Mutations require admin
 * auth server-side. The backend also returns 404 for cancelled reservations.
 */

import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import PublicStorefrontShell from './PublicStorefrontShell';
import { formatAmount } from '../../utils/currency';


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

function fmtEur(v, currency = 'EUR', locale = 'it-IT') {
  if (v == null) return '-';
  // CH compliance v1: CHF goes through the shared Swiss-style formatter,
  // EUR (and any future code) keeps its locale-aware Intl rendering.
  if (String(currency || '').toUpperCase() === 'CHF') {
    return formatAmount(v, 'CHF');
  }
  try {
    return new Intl.NumberFormat(locale, {
      style: 'currency', currency, maximumFractionDigits: 2,
    }).format(v);
  } catch {
    return String(v);
  }
}

function kindLabel(kind, t) {
  switch (kind) {
    case 'mandatory': return t('landings:reservationConfirmation.kind.mandatory');
    case 'optional': return t('landings:reservationConfirmation.kind.optional');
    case 'radio_variant': return t('landings:reservationConfirmation.kind.radioVariant');
    default: return kind || '';
  }
}

function kindClass(kind) {
  switch (kind) {
    case 'mandatory': return 'bg-gray-100 text-gray-700';
    case 'optional': return 'bg-blue-50 text-blue-700';
    case 'radio_variant': return 'bg-amber-50 text-amber-700';
    default: return 'bg-gray-100 text-gray-600';
  }
}

// Decide which "stage" the reservation is in, for the status badge.
// active + future → Confermata
// active + in-range / on-day → In corso
// active + past → Completata
// cancelled (backend returns 404, but keep guard for safety)
//
// `t` is threaded in so the labels respect the customer's locale.
function computeStageBadge(reservation, t) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  if (reservation.status === 'cancelled') {
    return { label: t('landings:reservationConfirmation.stage.cancelled'), cls: 'bg-red-100 text-red-800 border-red-200' };
  }
  try {
    if (reservation.reservation_flavor === 'range') {
      const from = reservation.date_from ? new Date(reservation.date_from + 'T00:00:00') : null;
      const to = reservation.date_to ? new Date(reservation.date_to + 'T23:59:59') : from;
      if (to && to < today) return { label: t('landings:reservationConfirmation.stage.completed'), cls: 'bg-gray-100 text-gray-700 border-gray-200' };
      if (from && from > today) return { label: t('landings:reservationConfirmation.stage.confirmed'), cls: 'bg-green-100 text-green-800 border-green-200' };
      return { label: t('landings:reservationConfirmation.stage.inProgress'), cls: 'bg-blue-100 text-blue-800 border-blue-200' };
    } else {
      // slot
      const day = reservation.slot_date ? new Date(reservation.slot_date + 'T00:00:00') : null;
      if (day) {
        const dayEnd = new Date(day);
        dayEnd.setHours(23, 59, 59, 999);
        if (dayEnd < today) return { label: t('landings:reservationConfirmation.stage.completed'), cls: 'bg-gray-100 text-gray-700 border-gray-200' };
        if (day > today) return { label: t('landings:reservationConfirmation.stage.confirmed'), cls: 'bg-green-100 text-green-800 border-green-200' };
        return { label: t('landings:reservationConfirmation.stage.today'), cls: 'bg-blue-100 text-blue-800 border-blue-200' };
      }
    }
  } catch {
    // fall through
  }
  return { label: t('landings:reservationConfirmation.stage.confirmed'), cls: 'bg-green-100 text-green-800 border-green-200' };
}


export default function ReservationConfirmationPage() {
  const { token } = useParams();
  const { t, i18n } = useTranslation('landings');
  const [reservation, setReservation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      try {
        const res = await fetch(`/api/public/reservations/${encodeURIComponent(token)}`);
        if (!mounted) return;
        if (res.status === 404) { setError('not_found'); return; }
        if (!res.ok) { setError('generic'); return; }
        const data = await res.json();
        if (mounted) setReservation(data);
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
        <div className="text-gray-400">{t('landings:reservationConfirmation.loading')}</div>
      </div>
    );
  }

  if (error === 'not_found') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
        <div className="max-w-md w-full bg-white rounded-2xl shadow-sm border p-8 text-center">
          <div className="text-4xl mb-3">🔒</div>
          <h1 className="text-xl font-bold text-gray-900 mb-2">{t('landings:reservationConfirmation.notFoundTitle')}</h1>
          <p className="text-sm text-gray-600">
            {t('landings:reservationConfirmation.notFoundBody')}
          </p>
        </div>
      </div>
    );
  }

  if (error || !reservation) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
        <div className="max-w-md w-full bg-white rounded-2xl shadow-sm border p-8 text-center">
          <h1 className="text-xl font-bold text-gray-900 mb-2">{t('landings:reservationConfirmation.errorTitle')}</h1>
          <p className="text-sm text-gray-600">
            {t('landings:reservationConfirmation.errorBody')}
          </p>
        </div>
      </div>
    );
  }

  const isRange = reservation.reservation_flavor === 'range';
  const extras = Array.isArray(reservation.extras) ? reservation.extras : [];
  const stageBadge = computeStageBadge(reservation, t);
  const icsUrl = `/api/public/reservations/${encodeURIComponent(token)}/ics`;
  const canAddToCalendar = reservation.status !== 'cancelled';

  const whenLabel = isRange
    ? t('landings:reservationConfirmation.eyebrowRange')
    : t('landings:reservationConfirmation.eyebrowSlot');

  // Wrap success render in PublicStorefrontShell — the page now picks
  // up storefront_languages from the backend payload and the resolver
  // forces i18n into the storefront's primary language.
  return (
    <PublicStorefrontShell slug={reservation.store_slug || null}>
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-lg mx-auto">
        {/* Store header */}
        {reservation.store_name && (
          <div className="mb-4 text-center">
            {reservation.store_slug ? (
              <a href={`/s/${reservation.store_slug}`} className="text-sm text-gray-600 hover:text-gray-900">
                ← {reservation.store_name}
              </a>
            ) : (
              <div className="text-sm text-gray-600">{reservation.store_name}</div>
            )}
          </div>
        )}

        {/* Main card */}
        <div className="bg-white rounded-2xl shadow-sm border overflow-hidden">
          {/* Hero */}
          {reservation.product_image_url && (
            <div className="aspect-[16/9] bg-gray-100 overflow-hidden">
              <img
                src={reservation.product_image_url}
                alt=""
                className="w-full h-full object-cover"
              />
            </div>
          )}

          <div className="p-6">
            <div className="flex items-start justify-between gap-3 mb-4">
              <div className="min-w-0">
                <div className="text-[11px] uppercase tracking-widest text-gray-500 font-semibold mb-1">
                  {whenLabel}
                </div>
                <h1 className="text-2xl font-bold text-gray-900 leading-tight">
                  {reservation.product_name}
                </h1>
              </div>
              <span className={`shrink-0 inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-semibold border ${stageBadge.cls}`}>
                {stageBadge.label}
              </span>
            </div>

            {/* When */}
            <div className="rounded-xl border border-gray-200 p-4 mb-3">
              <div className="text-[11px] uppercase tracking-widest text-gray-500 font-semibold mb-1">
                {t('landings:reservationConfirmation.whenHeading')}
              </div>
              {isRange ? (
                <>
                  <div className="text-base text-gray-900 font-semibold capitalize">
                    {t('landings:reservationConfirmation.rangeFrom', { date: formatDatePretty(reservation.date_from, i18n.language) })}
                  </div>
                  {reservation.date_to && reservation.date_to !== reservation.date_from && (
                    <div className="text-base text-gray-900 font-semibold capitalize">
                      {t('landings:reservationConfirmation.rangeTo', { date: formatDatePretty(reservation.date_to, i18n.language) })}
                    </div>
                  )}
                </>
              ) : (
                <>
                  <div className="text-base text-gray-900 font-semibold capitalize">
                    {formatDatePretty(reservation.slot_date, i18n.language)}
                  </div>
                  {(reservation.slot_start_time || reservation.slot_end_time) && (
                    <div className="text-sm text-gray-700 mt-0.5">
                      {reservation.slot_start_time || ''}
                      {reservation.slot_end_time ? ` → ${reservation.slot_end_time}` : ''}
                    </div>
                  )}
                </>
              )}
            </div>

            {/* Where */}
            {reservation.location && (
              <div className="rounded-xl border border-gray-200 p-4 mb-3">
                <div className="text-[11px] uppercase tracking-widest text-gray-500 font-semibold mb-1">
                  {t('landings:reservationConfirmation.whereHeading')}
                </div>
                <div className="text-sm text-gray-900">
                  📍 {reservation.location}
                </div>
              </div>
            )}

            {/* Holder */}
            {reservation.holder_name && (
              <div className="rounded-xl border border-gray-200 p-4 mb-3">
                <div className="text-[11px] uppercase tracking-widest text-gray-500 font-semibold mb-1">
                  {t('landings:reservationConfirmation.holderHeading')}
                </div>
                <div className="text-sm text-gray-900">
                  {reservation.holder_name}
                </div>
                {reservation.holder_email && (
                  <div className="text-xs text-gray-500 mt-0.5">
                    {reservation.holder_email}
                  </div>
                )}
                {reservation.holder_phone && (
                  <div className="text-xs text-gray-500 mt-0.5">
                    {reservation.holder_phone}
                  </div>
                )}
              </div>
            )}

            {/* Extras */}
            {extras.length > 0 && (
              <div className="rounded-xl border border-gray-200 p-4 mb-3">
                <div className="text-[11px] uppercase tracking-widest text-gray-500 font-semibold mb-2">
                  {t('landings:reservationConfirmation.detailsHeading')}
                </div>
                <ul className="space-y-2">
                  {extras.map((e, idx) => (
                    <li key={idx} className="flex items-start justify-between gap-3 text-sm">
                      <div className="min-w-0">
                        <div className="text-gray-900">{e.label}</div>
                        <div className="flex items-center gap-1.5 mt-0.5">
                          {e.kind && (
                            <span className={`inline-flex items-center px-1.5 py-0.5 rounded-full text-[10px] font-medium ${kindClass(e.kind)}`}>
                              {kindLabel(e.kind, t)}
                            </span>
                          )}
                          {e.quantity && e.quantity !== 1 && (
                            <span className="text-[11px] text-gray-500">× {e.quantity}</span>
                          )}
                        </div>
                      </div>
                      <div className="shrink-0 text-sm text-gray-900 tabular-nums">
                        {fmtEur(e.line_total, reservation?.currency || reservation?.order?.currency, i18n.language)}
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Code */}
            <div className="rounded-xl border border-gray-200 p-4 mb-4">
              <div className="text-[11px] uppercase tracking-widest text-gray-500 font-semibold mb-1">
                {t('landings:reservationConfirmation.codeHeading')}
              </div>
              <div className="font-mono text-base text-gray-900 tracking-wider">
                {reservation.code}
              </div>
              <div className="text-xs text-gray-500 mt-1">
                {t('landings:reservationConfirmation.codeHint')}
              </div>
            </div>

            {/* Add to calendar CTA */}
            {canAddToCalendar && (
              <a
                href={icsUrl}
                className="w-full inline-flex items-center justify-center gap-2 bg-[var(--sf-accent,#111827)] text-[var(--sf-accent-fg,#ffffff)] font-semibold px-4 py-3 rounded-xl hover:bg-[var(--sf-accent-hover,#1f2937)] transition-colors"
              >
                {t('landings:reservationConfirmation.addToCalendar')}
              </a>
            )}
          </div>
        </div>

        <p className="text-center text-xs text-gray-400 mt-6">
          {t('landings:reservationConfirmation.privateLinkHint')}
        </p>
      </div>
    </div>
    </PublicStorefrontShell>
  );
}
