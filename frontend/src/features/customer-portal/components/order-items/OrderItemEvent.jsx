/**
 * OrderItemEvent — order line for `item_type=event_ticket`.
 *
 * Renders, in order:
 *   - product name + occurrence date + venue (via OrderItemBase)
 *   - per-seat ticket grid: code, holder name, tier label, status
 *     badge, "Apri biglietto + QR" CTA -> /t/<access_token>
 *
 * Data sources
 * ------------
 * The ticket array comes from `order._issued_tickets` populated by
 * the backend when the page calls /customer/orders/<id>?with_issued=true
 * (see routers/customer_portal.py::_attach_issued_assets). Tickets
 * are filtered to (organization_id, order_id) server-side, then
 * filtered HERE to only the tickets matching this specific order line
 * — important when an order has multiple event_ticket lines for
 * different occurrences (e.g. concert + workshop in one cart).
 *
 * Empty state
 * -----------
 * Three cases produce an empty grid:
 *   1. Backend was called WITHOUT with_issued=true (e.g. an old
 *      mobile build of the app). Show nothing extra — the line still
 *      renders with name + date + price.
 *   2. Order is direct-pay and the customer has not paid yet, so
 *      tickets have not been issued. Show a soft hint.
 *   3. Order request not yet confirmed by the merchant. Same hint.
 *
 * Status mapping
 * --------------
 *   valid       blue    "Da utilizzare"
 *   checked_in  green   "Entrato il <date>"
 *   voided      red     "Annullato"
 */

import React from 'react';
import { useTranslation } from 'react-i18next';
import OrderItemBase from './OrderItemBase';


function fmtOccurrenceDate(iso, locale = 'it-IT') {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleDateString(locale, {
      weekday: 'short', day: 'numeric', month: 'short',
    });
  } catch { return iso.slice(0, 10); }
}


function fmtCheckInTime(iso, locale = 'it-IT') {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleString(locale, {
      day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit',
    });
  } catch { return ''; }
}


// status -> {label, classes}. Kept small + inline because there are
// only three statuses for tickets and they don't need to be exported.
function ticketStatusBadge(status, checkedInAt, t, locale) {
  if (status === 'checked_in') {
    return {
      label: checkedInAt
        ? t('customer_portal:orderItemEvent.status.checkedInAt', { time: fmtCheckInTime(checkedInAt, locale) })
        : t('customer_portal:orderItemEvent.status.checkedIn'),
      classes: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    };
  }
  if (status === 'voided') {
    return {
      label: t('customer_portal:orderItemEvent.status.voided'),
      classes: 'bg-red-50 text-red-700 border-red-200',
    };
  }
  return {
    label: t('customer_portal:orderItemEvent.status.toUse'),
    classes: 'bg-blue-50 text-blue-700 border-blue-200',
  };
}


export default function OrderItemEvent({ item, currency = 'EUR', order = null }) {
  const { t, i18n } = useTranslation('customer_portal');
  const occurrenceDate = fmtOccurrenceDate(item.occurrence_start_at, i18n.language);
  const occurrenceLocation = item.occurrence_location || '';

  // Tickets for THIS line only. The order may carry multiple
  // event_ticket lines (different occurrences) — match by occurrence_id
  // when available (most reliable) or by product_id (fallback for
  // legacy data without occurrence_id on the issued ticket).
  const allTickets = (order && order._issued_tickets) || [];
  const lineTickets = allTickets.filter(t => {
    if (item.occurrence_id && t.occurrence_id) {
      return t.occurrence_id === item.occurrence_id;
    }
    return t.product_id === item.product_id;
  });

  const extras = occurrenceDate ? (
    <p className="text-xs text-muted-foreground">
      {occurrenceDate}
      {occurrenceLocation ? ` \u2014 ${occurrenceLocation}` : ''}
    </p>
  ) : null;

  // No tickets and no array passed at all => keep the existing
  // minimal layout. The line rendered fine before this step.
  const hasIssuedField = order && Array.isArray(order._issued_tickets);
  if (!hasIssuedField) {
    return <OrderItemBase item={item} currency={currency} extras={extras} />;
  }

  // Array present but empty => paid order pending issuance, show hint
  if (lineTickets.length === 0) {
    return (
      <OrderItemBase item={item} currency={currency} extras={extras}>
        <div className="mt-2 rounded-md border border-dashed border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-900">
          {t('customer_portal:orderItemEvent.pendingHint')}
        </div>
      </OrderItemBase>
    );
  }

  return (
    <OrderItemBase item={item} currency={currency} extras={extras}>
      <ul className="mt-2 space-y-1.5">
        {lineTickets.map((tk) => {
          const badge = ticketStatusBadge(tk.status, tk.checked_in_at, t, i18n.language);
          const url = tk.access_token ? `/t/${tk.access_token}` : null;
          return (
            <li
              key={tk.id || tk.code}
              className="rounded-lg border border-gray-200 bg-white px-3 py-2 flex items-start gap-3"
            >
              <div className="flex-1 min-w-0">
                <p className="font-mono text-xs font-semibold tracking-wide truncate">
                  {tk.code}
                </p>
                <div className="text-[11px] text-muted-foreground mt-0.5 space-x-1.5">
                  {tk.holder_name && <span>{tk.holder_name}</span>}
                  {tk.tier_label && (
                    <>
                      {tk.holder_name && <span aria-hidden>·</span>}
                      <span>{tk.tier_label}</span>
                    </>
                  )}
                  {(tk.seat_count || 1) > 1 && (
                    <>
                      <span aria-hidden>·</span>
                      <span>{t('customer_portal:orderItemEvent.seatLine', { index: tk.seat_index || 1, total: tk.seat_count })}</span>
                    </>
                  )}
                </div>
                <span
                  className={`inline-block mt-1 px-1.5 py-0.5 text-[10px] font-medium rounded border ${badge.classes}`}
                >
                  {badge.label}
                </span>
              </div>
              {url && tk.status !== 'voided' && (
                <a
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="shrink-0 inline-flex items-center gap-1 px-3 py-1.5 rounded-md bg-gray-900 text-white text-xs font-semibold hover:bg-gray-800 transition-colors"
                >
                  {t('customer_portal:orderItemEvent.openTicket')}
                </a>
              )}
            </li>
          );
        })}
      </ul>
    </OrderItemBase>
  );
}
