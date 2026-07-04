/**
 * EventLineDetails — per-type renderer for event_ticket order lines.
 *
 * Shows occurrence date/time/venue and the attendee roster (with custom_fields)
 * captured at checkout. Issued tickets and their codes are surfaced by the
 * sibling IssuedEntitiesSection; this component focuses on the static info
 * the customer provided at purchase time.
 */

import { useState } from 'react';
import { Calendar, MapPin, Users, ChevronDown, ChevronUp } from 'lucide-react';

function formatDateTime(iso) {
  if (!iso) return { date: '', time: '' };
  try {
    const d = new Date(iso);
    return {
      date: d.toLocaleDateString('it-IT', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' }),
      time: d.toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' }),
    };
  } catch {
    return { date: iso, time: '' };
  }
}

export default function EventLineDetails({ item, t }) {
  const { date, time } = formatDateTime(item?.occurrence_start_at);
  const attendees = Array.isArray(item?.attendees) ? item.attendees : [];
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="text-xs text-muted-foreground space-y-0.5 mt-0.5">
      {date && (
        <p className="flex items-center gap-1.5">
          <Calendar className="h-3 w-3 shrink-0" />
          <span>{date}{time && ` — ${time}`}</span>
        </p>
      )}
      {item?.occurrence_location && (
        <p className="flex items-center gap-1.5">
          <MapPin className="h-3 w-3 shrink-0" />
          <span>{item.occurrence_location}</span>
        </p>
      )}
      {item?.tier_label && (
        <p className="text-[11px]">
          <span className="font-medium text-foreground/80">{t?.('detail.tier', { defaultValue: 'Tier' })}:</span>{' '}
          {item.tier_label}
        </p>
      )}
      {attendees.length > 0 && (
        <div className="pt-1">
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className="inline-flex items-center gap-1 text-[11px] text-primary hover:underline"
          >
            <Users className="h-3 w-3" />
            {t?.('detail.attendees_count', {
              count: attendees.length,
              defaultValue: `Partecipanti (${attendees.length})`,
            })}
            {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
          </button>
          {expanded && (
            <ul className="mt-1 space-y-1.5 pl-4 border-l-2 border-border">
              {attendees.map((a, idx) => (
                <li key={idx} className="text-[11px]">
                  <div className="font-medium text-foreground/90">
                    {a.name || a.full_name || `${t?.('detail.attendee', { defaultValue: 'Partecipante' })} ${idx + 1}`}
                  </div>
                  {a.email && <div className="text-muted-foreground">{a.email}</div>}
                  {a.custom_fields && typeof a.custom_fields === 'object' && Object.entries(a.custom_fields).length > 0 && (
                    <dl className="mt-0.5 space-y-0.5">
                      {Object.entries(a.custom_fields).map(([k, v]) => (
                        <div key={k} className="flex gap-1">
                          <dt className="text-muted-foreground">{k}:</dt>
                          <dd className="text-foreground/80">{v == null ? '—' : String(v)}</dd>
                        </div>
                      ))}
                    </dl>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
