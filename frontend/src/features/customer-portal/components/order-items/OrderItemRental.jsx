/**
 * OrderItemRental — order line for `item_type=rental` (and the legacy
 * `booking` alias when the line carries rental fields). Two flavours:
 *
 *   range — multi-day span (e.g. equipment rental, vacation booking)
 *           date_from -> date_to, daily granularity
 *   slot  — single time window (e.g. meeting room, sports court),
 *           optionally cross-day via Onda 17 booking_end_date
 *
 * Rendering parity with the email's _render_reservations_section:
 *   - flavor-aware date/time line ("12 dic → 18 dic" vs "ven 12 dic, 14:00 → 18:00")
 *   - location when present
 *   - reservation code (font-mono)
 *   - status badge (active / cancelled)
 *   - "Vedi prenotazione" CTA -> /rsv/<access_token>
 *   - "Aggiungi al calendario" link for slot reservations -> .ics endpoint
 *
 * The backend list endpoint is /api/public/reservations/<token>/ics
 * (existing — same shape as bookings). For range reservations the
 * .ics representation is less useful (whole-day events) so we surface
 * the link only for slot.
 *
 * Empty / fallback follows the same three-case pattern as
 * OrderItemEvent and OrderItemService.
 */

import React from 'react';
import { useTranslation } from 'react-i18next';
import OrderItemBase from './OrderItemBase';


function fmtDay(iso, locale = 'it-IT') {
  if (!iso) return '';
  try {
    const d = new Date(iso + 'T00:00:00');
    return d.toLocaleDateString(locale, {
      weekday: 'short', day: 'numeric', month: 'short',
    });
  } catch { return iso; }
}


function reservationStatusBadge(status, t) {
  if (status === 'cancelled') {
    return { label: t('customer_portal:orderItemRental.status.cancelled'), classes: 'bg-red-50 text-red-700 border-red-200' };
  }
  return { label: t('customer_portal:orderItemRental.status.active'), classes: 'bg-blue-50 text-blue-700 border-blue-200' };
}


function describeWhen(reservation, locale) {
  const flavor = reservation.reservation_flavor;
  if (flavor === 'range') {
    const from = fmtDay(reservation.date_from, locale);
    const to = fmtDay(reservation.date_to, locale);
    if (from && to && reservation.date_from !== reservation.date_to) {
      return `${from} \u2192 ${to}`;
    }
    return from || to || '';
  }
  // slot flavour
  const day = fmtDay(reservation.slot_date, locale);
  const start = reservation.slot_start_time;
  const end = reservation.slot_end_time;
  if (!day) return '';
  if (start && end) return `${day}, ${start} \u2192 ${end}`;
  if (start) return `${day}, ${start}`;
  return day;
}


export default function OrderItemRental({ item, currency = 'EUR', order = null }) {
  const { t, i18n } = useTranslation('customer_portal');
  const allReservations = (order && order._issued_reservations) || [];
  const lineReservations = allReservations.filter(r => r.product_id === item.product_id);

  // Fallback to the line snapshot when issued list missing — mirrors
  // the previous OrderDetailPage behaviour exactly.
  const snapshotExtras = item.rental_date_from ? (
    <p className="text-xs text-muted-foreground">
      {item.rental_date_from}
      {item.rental_date_to && item.rental_date_to !== item.rental_date_from
        ? ` \u2192 ${item.rental_date_to}` : ''}
    </p>
  ) : null;

  const hasIssuedField = order && Array.isArray(order._issued_reservations);
  if (!hasIssuedField) {
    return <OrderItemBase item={item} currency={currency} extras={snapshotExtras} />;
  }

  if (lineReservations.length === 0) {
    return (
      <OrderItemBase item={item} currency={currency} extras={snapshotExtras}>
        <div className="mt-2 rounded-md border border-dashed border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-900">
          {t('customer_portal:orderItemRental.pendingHint')}
        </div>
      </OrderItemBase>
    );
  }

  return (
    <OrderItemBase item={item} currency={currency}>
      <ul className="mt-2 space-y-1.5">
        {lineReservations.map((r) => {
          const badge = reservationStatusBadge(r.status, t);
          const detailUrl = r.access_token ? `/rsv/${r.access_token}` : null;
          const icsUrl = r.access_token && r.reservation_flavor === 'slot'
            ? `/api/public/reservations/${r.access_token}/ics`
            : null;
          const whenLabel = describeWhen(r, i18n.language);
          return (
            <li
              key={r.id || r.code}
              className="rounded-lg border border-gray-200 bg-white px-3 py-2"
            >
              <div className="flex items-start gap-3">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-gray-900 capitalize">{whenLabel}</p>
                  {r.location && (
                    <p className="text-[11px] text-muted-foreground mt-0.5">📍 {r.location}</p>
                  )}
                  <div className="flex items-center gap-2 mt-1">
                    <span className="font-mono text-[10px] text-muted-foreground">{r.code}</span>
                    <span
                      className={`px-1.5 py-0.5 text-[10px] font-medium rounded border ${badge.classes}`}
                    >
                      {badge.label}
                    </span>
                  </div>
                </div>
                {detailUrl && r.status !== 'cancelled' && (
                  <a
                    href={detailUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="shrink-0 inline-flex items-center gap-1 px-3 py-1.5 rounded-md bg-gray-900 text-white text-xs font-semibold hover:bg-gray-800 transition-colors"
                  >
                    {t('customer_portal:orderItemService.openShort')}
                  </a>
                )}
              </div>
              {icsUrl && r.status !== 'cancelled' && (
                <div className="mt-1.5 pt-1.5 border-t border-gray-100">
                  <a
                    href={icsUrl}
                    className="text-[11px] font-medium text-gray-600 hover:text-gray-900 hover:underline"
                  >
                    {t('customer_portal:orderItemService.addToCalendar')}
                  </a>
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </OrderItemBase>
  );
}
