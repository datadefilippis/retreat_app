/**
 * ServiceLineDetails — per-type renderer for service (consulenza) order lines.
 *
 * Shows booking date + time window + service option label + any notes the
 * customer left. Issued BKG-codes and resend affordances are rendered by the
 * sibling IssuedEntitiesSection.
 */

import { Calendar, Clock, Tag, StickyNote } from 'lucide-react';

function formatBookingDate(dateStr) {
  if (!dateStr) return '';
  try {
    const d = new Date(`${dateStr}T12:00`);
    return d.toLocaleDateString('it-IT', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' });
  } catch {
    return dateStr;
  }
}

export default function ServiceLineDetails({ item, t }) {
  const datePretty = formatBookingDate(item?.booking_date);
  const timeRange = item?.booking_start_time
    ? `${item.booking_start_time}${item.booking_end_time ? ` → ${item.booking_end_time}` : ''}`
    : '';
  // Onda 16: service_notes is the new dedicated field; rental_notes was also
  // historically reused for service notes, so fall back to it for legacy data.
  const notes = item?.service_notes || item?.rental_notes || '';

  return (
    <div className="text-xs text-muted-foreground space-y-0.5 mt-0.5">
      {datePretty && (
        <p className="flex items-center gap-1.5">
          <Calendar className="h-3 w-3 shrink-0" />
          <span>{datePretty}</span>
        </p>
      )}
      {timeRange && (
        <p className="flex items-center gap-1.5">
          <Clock className="h-3 w-3 shrink-0" />
          <span>{timeRange}</span>
        </p>
      )}
      {item?.service_option_label && (
        <p className="flex items-center gap-1.5">
          <Tag className="h-3 w-3 shrink-0" />
          <span>{item.service_option_label}</span>
        </p>
      )}
      {notes && (
        <p className="flex items-start gap-1.5 text-[11px] italic">
          <StickyNote className="h-3 w-3 shrink-0 mt-0.5" />
          <span className="break-words">
            <span className="not-italic text-foreground/70 mr-1">
              {t?.('detail.customer_note', { defaultValue: 'Nota cliente' })}:
            </span>
            {notes}
          </span>
        </p>
      )}
    </div>
  );
}
