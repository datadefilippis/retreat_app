/**
 * OrderItemService — order line for `item_type=service` (consulenza /
 * appointment-style booking).
 *
 * Renders, for each issued booking on this line:
 *   - day + start/end time, formatted human-readable
 *   - service option (when the merchant offers multiple)
 *   - location (when set)
 *   - booking code (font-mono, copy-friendly)
 *   - status badge (confirmed / completed / no_show / cancelled)
 *   - "Apri prenotazione" CTA -> /b/<access_token>
 *   - "Aggiungi al calendario" link -> /api/public/bookings/<token>/ics
 *     (existing backend endpoint, no new server work)
 *
 * Data sources
 * ------------
 * `order._issued_bookings` populated when the page calls
 * /customer/orders/<id>?with_issued=true. We filter to bookings that
 * belong to this specific order line (match by product_id since
 * IssuedBooking does not carry the OrderLine index).
 *
 * Empty / fallback
 * ----------------
 * Same three-case fallback as OrderItemEvent:
 *   1. Backend not in with_issued mode  -> minimal render
 *   2. Bookings array is empty          -> "in attesa di pagamento" hint
 *   3. Bookings present                  -> rich grid
 *
 * The booking_date / booking_start_time fields ALSO live on the
 * OrderLine snapshot (so the merchant can see them even before
 * confirm). We deliberately render from `_issued_bookings` because
 * that's the authoritative source and carries the access_token we
 * need for the CTAs. The line-snapshot fields are only used in the
 * "no issued yet" hint path.
 */

import React from 'react';
import { useTranslation } from 'react-i18next';
import OrderItemBase from './OrderItemBase';


function fmtBookingDate(iso, locale = 'it-IT') {
  if (!iso) return '';
  try {
    const d = new Date(iso + 'T00:00:00');
    return d.toLocaleDateString(locale, {
      weekday: 'long', day: 'numeric', month: 'long',
    });
  } catch { return iso; }
}


function bookingStatusBadge(status, t) {
  const map = {
    confirmed:  { label: t('customer_portal:orderItemService.status.confirmed'),  classes: 'bg-blue-50 text-blue-700 border-blue-200' },
    completed:  { label: t('customer_portal:orderItemService.status.completed'),  classes: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
    no_show:    { label: t('customer_portal:orderItemService.status.noShow'),     classes: 'bg-amber-50 text-amber-700 border-amber-200' },
    cancelled:  { label: t('customer_portal:orderItemService.status.cancelled'),  classes: 'bg-red-50 text-red-700 border-red-200' },
  };
  return map[status] || { label: status, classes: 'bg-gray-50 text-gray-700 border-gray-200' };
}


export default function OrderItemService({ item, currency = 'EUR', order = null }) {
  const { t, i18n } = useTranslation('customer_portal');
  const allBookings = (order && order._issued_bookings) || [];
  const lineBookings = allBookings.filter(b => b.product_id === item.product_id);

  const hasIssuedField = order && Array.isArray(order._issued_bookings);
  if (!hasIssuedField) {
    return <OrderItemBase item={item} currency={currency} />;
  }

  if (lineBookings.length === 0) {
    return (
      <OrderItemBase item={item} currency={currency}>
        <div className="mt-2 rounded-md border border-dashed border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-900">
          {t('customer_portal:orderItemService.pendingHint')}
        </div>
      </OrderItemBase>
    );
  }

  return (
    <OrderItemBase item={item} currency={currency}>
      <ul className="mt-2 space-y-1.5">
        {lineBookings.map((b) => {
          const badge = bookingStatusBadge(b.status, t);
          const detailUrl = b.access_token ? `/b/${b.access_token}` : null;
          const icsUrl = b.access_token ? `/api/public/bookings/${b.access_token}/ics` : null;
          const dateLabel = fmtBookingDate(b.booking_date, i18n.language);
          const timeLabel = b.booking_start_time
            ? (b.booking_end_time ? `${b.booking_start_time} \u2192 ${b.booking_end_time}` : b.booking_start_time)
            : '';
          return (
            <li
              key={b.id || b.code}
              className="rounded-lg border border-gray-200 bg-white px-3 py-2"
            >
              <div className="flex items-start gap-3">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-gray-900 capitalize">
                    {dateLabel}
                  </p>
                  {timeLabel && (
                    <p className="text-xs text-gray-700 tabular-nums mt-0.5">{timeLabel}</p>
                  )}
                  <div className="text-[11px] text-muted-foreground mt-1 space-x-1.5">
                    {b.service_option_label && <span>{b.service_option_label}</span>}
                    {b.location && (
                      <>
                        {b.service_option_label && <span aria-hidden>·</span>}
                        <span>📍 {b.location}</span>
                      </>
                    )}
                  </div>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="font-mono text-[10px] text-muted-foreground">{b.code}</span>
                    <span
                      className={`px-1.5 py-0.5 text-[10px] font-medium rounded border ${badge.classes}`}
                    >
                      {badge.label}
                    </span>
                  </div>
                </div>
                {detailUrl && b.status !== 'cancelled' && (
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
              {icsUrl && b.status === 'confirmed' && (
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
