/**
 * ReservationLineDetails — per-type renderer for rental order lines (Onda 16).
 *
 * Handles both "range" flavor (date_from → date_to, multi-day) and "slot"
 * flavor (single-date time window, inherited from the deprecated booking
 * item_type). Also surfaces the extras[] breakdown (mandatory / optional /
 * radio_variant) captured at checkout — this is key info the admin needs to
 * actually fulfill the reservation (e.g. "include breakfast").
 */

import { Calendar, Clock, StickyNote, CirclePlus } from 'lucide-react';

const fmtEur = (v) => (v != null
  ? new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR', maximumFractionDigits: 2 }).format(v)
  : '-');

function formatDateIt(dateStr) {
  if (!dateStr) return '';
  try {
    const d = new Date(`${dateStr}T12:00`);
    return d.toLocaleDateString('it-IT', { day: 'numeric', month: 'short', year: 'numeric' });
  } catch {
    return dateStr;
  }
}

function humanizeKind(kind, t) {
  switch (kind) {
    case 'mandatory':
      return t?.('detail.extra_mandatory', { defaultValue: 'Obbligatorio' });
    case 'optional':
      return t?.('detail.extra_optional', { defaultValue: 'Opzionale' });
    case 'radio_variant':
      return t?.('detail.extra_variant', { defaultValue: 'Variante' });
    default:
      return kind || '';
  }
}

export default function ReservationLineDetails({ item, t }) {
  // Flavor detection: range when date_from is present and no single-date slot info;
  // slot when booking_date / booking_start_time style is present (legacy booking).
  const isRange = !!item?.rental_date_from;
  const isSlot = !isRange && (item?.booking_date || item?.booking_start_time || item?.slot_date);

  const notes = item?.reservation_notes || item?.rental_notes || '';
  const extras = Array.isArray(item?.extras) ? item.extras : [];

  return (
    <div className="text-xs text-muted-foreground space-y-0.5 mt-0.5">
      {isRange && (
        <p className="flex items-center gap-1.5">
          <Calendar className="h-3 w-3 shrink-0" />
          <span>
            {formatDateIt(item.rental_date_from)}
            {item.rental_date_to && ` → ${formatDateIt(item.rental_date_to)}`}
          </span>
        </p>
      )}
      {isSlot && (() => {
        // Onda 17 — cross-day slot. booking_end_date / slot_date_to carries the
        // end day when different from the start day. When equal or missing,
        // same-day semantics (single date + start → end times).
        const startDate = item.booking_date || item.slot_date;
        const endDate = item.booking_end_date || item.slot_date_to;
        const startTime = item.booking_start_time || item.slot_start_time;
        const endTime = item.booking_end_time || item.slot_end_time;
        const crossDay = endDate && endDate !== startDate;
        return (
          <>
            {crossDay ? (
              <p className="flex items-center gap-1.5">
                <Calendar className="h-3 w-3 shrink-0" />
                <span>
                  {formatDateIt(startDate)} {startTime || ''}
                  {' → '}
                  {formatDateIt(endDate)} {endTime || ''}
                </span>
              </p>
            ) : (
              <>
                {startDate && (
                  <p className="flex items-center gap-1.5">
                    <Calendar className="h-3 w-3 shrink-0" />
                    <span>{formatDateIt(startDate)}</span>
                  </p>
                )}
                {startTime && (
                  <p className="flex items-center gap-1.5">
                    <Clock className="h-3 w-3 shrink-0" />
                    <span>
                      {startTime}
                      {endTime && ` → ${endTime}`}
                    </span>
                  </p>
                )}
              </>
            )}
          </>
        );
      })()}

      {extras.length > 0 && (
        <div className="pt-1.5 space-y-0.5">
          <p className="flex items-center gap-1.5 text-[11px] font-medium text-foreground/80">
            <CirclePlus className="h-3 w-3" />
            {t?.('detail.extras', { defaultValue: 'Extras' })}
          </p>
          <ul className="pl-4 space-y-0.5">
            {extras.map((e, idx) => (
              <li key={idx} className="flex items-center justify-between gap-2">
                <span className="truncate">
                  <span className="text-foreground/80">{e.label}</span>
                  {e.kind && (
                    <span className="ml-1.5 text-[10px] uppercase tracking-wide text-muted-foreground">
                      · {humanizeKind(e.kind, t)}
                    </span>
                  )}
                  {e.quantity && e.quantity !== 1 && (
                    <span className="ml-1.5 text-[10px] text-muted-foreground">× {e.quantity}</span>
                  )}
                </span>
                <span className="shrink-0 tabular-nums">{fmtEur(e.line_total)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {notes && (
        <p className="flex items-start gap-1.5 text-[11px] italic pt-1">
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
