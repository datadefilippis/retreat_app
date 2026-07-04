/**
 * TicketLandingPage — public page for a single issued ticket.
 *
 * Route: /t/:token (no authentication; the access_token is the key).
 * Backed by GET /api/public/tickets/{token} (F1 Onda 8).
 *
 * Role in the distribution flow:
 *   Instead of embedding N inline QR images in the confirmation email
 *   (which breaks at ~20 tickets due to 5MB size), every issued ticket
 *   carries a unique `access_token`. The email for the main customer
 *   contains a "Apri biglietto" link per ticket; each per-holder email
 *   contains exactly one link for that guest's own ticket.
 *
 *   Clicking the link lands here. The page shows the QR big and clear,
 *   the holder name, tier, event details, and an "Aggiungi al calendario"
 *   shortcut. Zero auth — the URL is the credential.
 *
 * Security: leaking the URL does NOT enable door check-in. The scanner
 * validates the ticket `code` (EVT-AAAA-BBBB) via a separate endpoint;
 * the access_token only grants read access to the landing page.
 */

import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import PublicStorefrontShell from './PublicStorefrontShell';


function formatDateTime(iso, locale = 'it-IT') {
  if (!iso) return { date: '', time: '' };
  try {
    const d = new Date(iso);
    return {
      date: d.toLocaleDateString(locale, { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }),
      time: d.toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit' }),
    };
  } catch { return { date: iso, time: '' }; }
}


function buildICS(ticket, t) {
  // Minimal iCalendar event for one-click "Add to calendar" (Apple / Google / Outlook).
  // The ICS DESCRIPTION + fallback event name are localized — passed in via `t`.
  if (!ticket?.event_start_at) return null;
  const start = ticket.event_start_at.replace(/[-:]/g, '').split('.')[0] + 'Z';
  const endIso = ticket.event_end_at || ticket.event_start_at;
  const end = endIso.replace(/[-:]/g, '').split('.')[0] + 'Z';
  const fallbackName = t('landings:ticket.icsFallbackEventName');
  const codePrefix = t('landings:ticket.icsCodePrefix');
  const name = (ticket.event_name || fallbackName).replace(/,/g, '\\,');
  const loc = [ticket.venue_name, ticket.address, ticket.city].filter(Boolean).join(', ').replace(/,/g, '\\,');
  const ics = [
    'BEGIN:VCALENDAR', 'VERSION:2.0',
    'BEGIN:VEVENT',
    `SUMMARY:${name}`,
    `DTSTART:${start}`,
    `DTEND:${end}`,
    `LOCATION:${loc}`,
    `DESCRIPTION:${codePrefix} ${ticket.code}`,
    'END:VEVENT', 'END:VCALENDAR',
  ].join('\r\n');
  return URL.createObjectURL(new Blob([ics], { type: 'text/calendar' }));
}


export default function TicketLandingPage() {
  return (
    <TicketLandingInner />
  );
}


// Inner component so we can wrap `TicketContent` (the actual ticket UI)
// in <PublicStorefrontShell> AFTER the payload arrives carrying the
// `store_slug`. Loading + error states render without the shell (no
// slug to feed it) — they fall back to the i18n language already
// resolved by the user's prior storefront visit, which is the right
// UX during the brief fetch window.
function TicketLandingInner() {
  const { token } = useParams();
  const { t, i18n } = useTranslation('landings');
  const [ticket, setTicket] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      try {
        const res = await fetch(`/api/public/tickets/${encodeURIComponent(token)}`);
        if (!mounted) return;
        if (res.status === 404) {
          setError('not_found');
          return;
        }
        if (!res.ok) {
          setError('generic');
          return;
        }
        const data = await res.json();
        setTicket(data);
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
      <div className="min-h-screen flex items-center justify-center text-sm text-gray-500">
        {t('landings:ticket.loadingTicket')}
      </div>
    );
  }

  if (error === 'not_found') {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
        <div className="max-w-md text-center bg-white rounded-xl border p-8">
          <div className="text-5xl mb-3">🎫</div>
          <h1 className="text-xl font-bold mb-2">{t('landings:ticket.invalidTitle')}</h1>
          <p className="text-sm text-gray-600">
            {t('landings:ticket.invalidBody')}
          </p>
        </div>
      </div>
    );
  }

  if (error || !ticket) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6">
        <p className="text-sm text-red-700">{t('landings:ticket.errorBody')}</p>
      </div>
    );
  }

  const dt = formatDateTime(ticket.event_start_at, i18n.language);
  const endDt = ticket.event_end_at ? formatDateTime(ticket.event_end_at, i18n.language) : null;
  const icsUrl = buildICS(ticket, t);
  const venueLine = [ticket.venue_name, ticket.address, ticket.city].filter(Boolean).join(' · ');
  const statusBadge = ticket.status === 'checked_in'
    ? { cls: 'bg-green-100 text-green-800', label: t('landings:ticket.status.checkedIn') }
    : ticket.status === 'voided'
      ? { cls: 'bg-red-100 text-red-800', label: t('landings:ticket.status.voided') }
      : { cls: 'bg-blue-100 text-blue-800', label: t('landings:ticket.status.valid') };
  const icsFilenamePrefix = t('landings:ticket.icsFilenamePrefix');

  // Wrap the content in PublicStorefrontShell so the page resolves
  // i18n.language from the storefront's storefront_languages chain
  // instead of leaking whatever locale the user's last storefront
  // visit left in localStorage. When the backend payload doesn't
  // include `store_slug` (legacy tokens issued before Onda 3) we
  // skip the shell and fall back to current i18n state.
  return (
    <PublicStorefrontShell slug={ticket.store_slug || null}>
    <div className="min-h-screen bg-gray-50">
      {/* Hero */}
      <div className="relative bg-[var(--sf-accent,#111827)] text-[var(--sf-accent-fg,#ffffff)]">
        {ticket.cover_image_url && (
          <img
            src={ticket.cover_image_url}
            alt=""
            className="absolute inset-0 w-full h-full object-cover opacity-40"
          />
        )}
        <div className="relative max-w-lg mx-auto px-4 py-6 sm:py-8">
          <p className="text-[11px] uppercase tracking-widest opacity-70">{t('landings:ticket.eyebrow')}</p>
          <h1 className="text-xl sm:text-2xl font-bold mt-1">{ticket.event_name}</h1>
          {dt.date && (
            <p className="text-sm mt-1 capitalize opacity-90">
              {dt.date}
              {dt.time ? ` · ${dt.time}` : ''}
              {endDt?.time ? ` – ${endDt.time}` : ''}
            </p>
          )}
        </div>
      </div>

      <div className="max-w-lg mx-auto px-4 py-5 space-y-4">
        {/* Holder + seat info */}
        <div className="rounded-xl border border-gray-200 bg-white px-4 py-3 flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-[11px] uppercase tracking-wide text-gray-500">{t('landings:ticket.holderLabel')}</p>
            <p className="text-base font-semibold text-gray-900 truncate">
              {ticket.holder_name || t('landings:ticket.missingHolder')}
            </p>
            {ticket.tier_label && (
              <p className="text-xs text-gray-600 mt-0.5">{ticket.tier_label}</p>
            )}
            {ticket.seat_count > 1 && (
              <p className="text-[11px] text-gray-500 mt-0.5">
                {t('landings:ticket.seatLine', { index: ticket.seat_index, total: ticket.seat_count })}
              </p>
            )}
          </div>
          <span className={`shrink-0 inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${statusBadge.cls}`}>
            {statusBadge.label}
          </span>
        </div>

        {/* QR card — the main payload */}
        <div className="rounded-xl border border-gray-200 bg-white p-5 flex flex-col items-center">
          <img
            src={ticket.qr_data_uri}
            alt={t('landings:ticket.qrAlt')}
            className="w-64 h-64 object-contain"
          />
          <p className="mt-3 font-mono text-lg tracking-wider text-gray-900">{ticket.code}</p>
          <p className="text-[11px] text-gray-500 mt-1 text-center">
            {t('landings:ticket.qrHint')}
          </p>
        </div>

        {/* Venue + calendar */}
        {venueLine && (
          <div className="rounded-xl border border-gray-200 bg-white px-4 py-3">
            <p className="text-[11px] uppercase tracking-wide text-gray-500">{t('landings:ticket.locationLabel')}</p>
            <p className="text-sm text-gray-900 mt-0.5">📍 {venueLine}</p>
          </div>
        )}

        {icsUrl && (
          <a
            href={icsUrl}
            download={`${icsFilenamePrefix}-${ticket.code}.ics`}
            className="block w-full rounded-xl bg-[var(--sf-accent,#111827)] text-[var(--sf-accent-fg,#ffffff)] px-4 py-3 text-sm font-semibold text-center hover:bg-[var(--sf-accent-hover,#1f2937)]"
          >
            {t('landings:ticket.addToCalendar')}
          </a>
        )}

        <p className="text-center text-[11px] text-gray-400 mt-2">
          {t('landings:ticket.offlineHint')}
        </p>
      </div>
    </div>
    </PublicStorefrontShell>
  );
}
