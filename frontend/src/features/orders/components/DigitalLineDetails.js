/**
 * DigitalLineDetails — per-type renderer for digital order lines.
 *
 * Release 3 (Digital) B11. Analog of ReservationLineDetails /
 * ServiceLineDetails. The OrderLineBase snapshot only carries generic
 * fields (product_name, extras, rental_notes), so this component stays
 * minimal: the full delivery status (code, count, status badge) is the
 * responsibility of DigitalDashboardPage / admin actions on the order
 * detail page, not of the line row.
 */

import { Download, StickyNote, CirclePlus, ExternalLink } from 'lucide-react';


const fmtEur = (v) => (v != null
  ? new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR', maximumFractionDigits: 2 }).format(v)
  : '-');

function humanizeKind(kind, t) {
  switch (kind) {
    case 'mandatory':     return t?.('detail.extra_mandatory', { defaultValue: 'Obbligatorio' });
    case 'optional':      return t?.('detail.extra_optional',  { defaultValue: 'Opzionale' });
    case 'radio_variant': return t?.('detail.extra_variant',   { defaultValue: 'Variante' });
    default: return kind || '';
  }
}


export default function DigitalLineDetails({ item, t }) {
  const extras = Array.isArray(item?.extras) ? item.extras : [];
  const notes = item?.rental_notes || '';

  return (
    <div className="text-xs text-muted-foreground space-y-0.5 mt-0.5">
      <p className="flex items-center gap-1.5">
        <Download className="h-3 w-3 shrink-0" />
        <span>
          Download digitale
          {item?.product_id && (
            <>
              {' · '}
              <a
                href={`/digitals/${item.product_id}`}
                className="text-primary hover:underline inline-flex items-center gap-0.5"
              >
                vedi consegna <ExternalLink className="h-2.5 w-2.5" />
              </a>
            </>
          )}
        </span>
      </p>

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
          <span className="break-words">{notes}</span>
        </p>
      )}
    </div>
  );
}
