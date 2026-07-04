/**
 * IssuedEntitiesSection — aggregated view of tickets/bookings/reservations
 * that have been issued for an order.
 *
 * Loads data from GET /api/orders/{id}/issued. Provides quick actions:
 *   - Copy the code (TCK-… / BKG-… / RSV-…)
 *   - Open the public landing page (/t/, /b/, /rsv/)
 *   - Resend the confirmation email
 *   - Download the ICS calendar file (reservations only — where available)
 *
 * The section collapses gracefully to nothing when an order hasn't been
 * confirmed yet or its lines don't produce issued entities (e.g. a pure
 * physical order).
 */

import { useState, useEffect, useCallback } from 'react';
import { Mail, ExternalLink, Ticket, Briefcase, Calendar, Download, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { ordersAPI } from '../../../api';
import CopyButton from './CopyButton';

function formatSentAt(iso) {
  if (!iso) return null;
  try {
    const d = new Date(iso);
    return d.toLocaleString('it-IT', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
  } catch {
    return iso;
  }
}

function DeliveryBadge({ status, t }) {
  const label = {
    sent: t?.('detail.delivery_sent', { defaultValue: 'Email inviata' }),
    failed: t?.('detail.delivery_failed', { defaultValue: 'Invio fallito' }),
    pending: t?.('detail.delivery_pending', { defaultValue: 'In coda' }),
  }[status] || status;
  const cls = {
    sent: 'bg-emerald-100 text-emerald-700',
    failed: 'bg-red-100 text-red-700',
    pending: 'bg-amber-100 text-amber-700',
  }[status] || 'bg-gray-100 text-gray-600';
  if (!status) return null;
  return <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${cls}`}>{label}</span>;
}

function IssuedRow({ entity, kind, t, onResend, resending }) {
  const openUrl = entity.landing_url;
  const isCancelled = entity.status === 'cancelled' || entity.status === 'voided';
  const label = {
    ticket: t?.('detail.kind_ticket', { defaultValue: 'Biglietto' }),
    booking: t?.('detail.kind_booking', { defaultValue: 'Prenotazione consulenza' }),
    reservation: t?.('detail.kind_reservation', { defaultValue: 'Prenotazione' }),
  }[kind];
  const Icon = { ticket: Ticket, booking: Briefcase, reservation: Calendar }[kind] || Ticket;

  return (
    <div className={`rounded-md border p-2.5 space-y-1 text-xs ${isCancelled ? 'opacity-60' : ''}`}>
      <div className="flex items-center gap-2 flex-wrap">
        <Icon className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
        <span className="text-[10px] uppercase tracking-wide text-muted-foreground">{label}</span>
        {entity.code && (
          <>
            <span className="font-mono font-medium text-foreground">{entity.code}</span>
            <CopyButton value={entity.code} title={t?.('detail.copy_code', { defaultValue: 'Copia codice' })} />
          </>
        )}
        <DeliveryBadge status={entity.delivery_status} t={t} />
        {isCancelled && (
          <span className="text-[10px] px-1.5 py-0.5 rounded-full font-medium bg-red-100 text-red-700">
            {t?.('detail.cancelled', { defaultValue: 'Cancellato' })}
          </span>
        )}
      </div>
      {entity.holder_email && (
        <div className="text-muted-foreground pl-5 truncate">{entity.holder_email}</div>
      )}
      {entity.sent_at && (
        <div className="text-[10px] text-muted-foreground pl-5">
          {t?.('detail.sent_at', { defaultValue: 'Inviato' })}: {formatSentAt(entity.sent_at)}
        </div>
      )}
      {!isCancelled && (
        <div className="flex items-center gap-1.5 pt-1">
          {openUrl && (
            <a
              href={openUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-[11px] text-primary hover:underline"
            >
              <ExternalLink className="h-3 w-3" />
              {t?.('detail.open_landing', { defaultValue: 'Apri landing' })}
            </a>
          )}
          <button
            type="button"
            onClick={onResend}
            disabled={resending}
            className="inline-flex items-center gap-1 text-[11px] text-primary hover:underline disabled:opacity-50"
          >
            {resending ? <Loader2 className="h-3 w-3 animate-spin" /> : <Mail className="h-3 w-3" />}
            {t?.('detail.resend_email', { defaultValue: 'Rinvia email' })}
          </button>
          {kind === 'reservation' && entity.access_token && (
            <a
              href={`/api/public/reservations/${entity.access_token}/ics`}
              className="inline-flex items-center gap-1 text-[11px] text-primary hover:underline"
            >
              <Download className="h-3 w-3" />
              {t?.('detail.download_ics', { defaultValue: 'ICS' })}
            </a>
          )}
        </div>
      )}
    </div>
  );
}

export default function IssuedEntitiesSection({ orderId, orderStatus, t }) {
  const [data, setData] = useState({ tickets: [], bookings: [], reservations: [] });
  const [loading, setLoading] = useState(false);
  const [resendingKey, setResendingKey] = useState(null);

  const load = useCallback(async () => {
    if (!orderId) return;
    setLoading(true);
    try {
      const res = await ordersAPI.getIssued(orderId);
      setData(res.data || { tickets: [], bookings: [], reservations: [] });
    } catch {
      setData({ tickets: [], bookings: [], reservations: [] });
    } finally {
      setLoading(false);
    }
  }, [orderId]);

  useEffect(() => {
    // Only fetch for orders where issuance has happened.
    if (orderStatus === 'confirmed' || orderStatus === 'completed' || orderStatus === 'cancelled') {
      load();
    }
  }, [orderId, orderStatus, load]);

  const handleResend = async (kind, entity) => {
    const key = `${kind}:${entity.id || entity.code}`;
    setResendingKey(key);
    try {
      // Tickets resend by code; bookings/reservations by id (with code fallback).
      const idOrCode = kind === 'ticket'
        ? entity.code
        : (entity.id || entity.code);
      await ordersAPI.resendIssued(kind, idOrCode);
      toast.success(t?.('detail.resend_success', { defaultValue: 'Email rinviata' }));
      await load();
    } catch {
      toast.error(t?.('detail.resend_error', { defaultValue: 'Rinvio fallito' }));
    } finally {
      setResendingKey(null);
    }
  };

  const total = (data.tickets?.length || 0) + (data.bookings?.length || 0) + (data.reservations?.length || 0);
  if (!loading && total === 0) return null;

  return (
    <div className="rounded-lg border p-3 space-y-2">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold">
          {t?.('detail.issued_entities', { defaultValue: 'Conferme emesse' })}
          {total > 0 && <span className="ml-1.5 text-xs text-muted-foreground">({total})</span>}
        </h4>
        {loading && <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />}
      </div>
      <div className="space-y-2">
        {(data.tickets || []).map((e) => {
          const key = `ticket:${e.id || e.code}`;
          return (
            <IssuedRow
              key={key}
              entity={e}
              kind="ticket"
              t={t}
              resending={resendingKey === key}
              onResend={() => handleResend('ticket', e)}
            />
          );
        })}
        {(data.bookings || []).map((e) => {
          const key = `booking:${e.id || e.code}`;
          return (
            <IssuedRow
              key={key}
              entity={e}
              kind="booking"
              t={t}
              resending={resendingKey === key}
              onResend={() => handleResend('booking', e)}
            />
          );
        })}
        {(data.reservations || []).map((e) => {
          const key = `reservation:${e.id || e.code}`;
          return (
            <IssuedRow
              key={key}
              entity={e}
              kind="reservation"
              t={t}
              resending={resendingKey === key}
              onResend={() => handleResend('reservation', e)}
            />
          );
        })}
      </div>
    </div>
  );
}
