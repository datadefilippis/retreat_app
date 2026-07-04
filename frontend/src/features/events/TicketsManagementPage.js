/**
 * TicketsManagementPage — admin ticket operations for one event (G4).
 *
 * Route: /events/:occurrence_id/tickets   (ProtectedRoute)
 *
 * Companion to the event Dashboard (G3/E6): this page is for the
 * deeper ticket-level operations the dashboard's inline list can't
 * comfortably host — resend email on a lost ticket, void a single
 * ticket without cancelling its order, broadcast a templated email
 * to every attendee.
 *
 * Sections (top → bottom):
 *   1. Sticky page header with event name + quick links back to the
 *      dashboard and check-in surfaces.
 *   2. Broadcast card: template picker (reminder / logistics /
 *      cancellation / custom) + optional message + send button;
 *      counters of the last run appear below.
 *   3. Tickets table: search + status filter, expandable rows with
 *      per-ticket Resend / Void actions.
 *
 * No business logic lives here — every action calls the existing G4
 * endpoints (resend / void / broadcast) and refreshes the list on
 * success.
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { eventOccurrencesAPI } from '../../api/eventOccurrences';
import { ticketsAPI } from '../../api/tickets';


const BROADCAST_TEMPLATE_KEYS = ['reminder', 'logistics', 'cancellation', 'custom'];


function StatusPill({ status }) {
  const { t } = useTranslation('products');
  const presets = {
    valid:      { key: 'statusValid',     cls: 'bg-blue-100 text-blue-900' },
    checked_in: { key: 'statusCheckedIn', cls: 'bg-green-100 text-green-900' },
    voided:     { key: 'statusVoided',    cls: 'bg-gray-200 text-gray-700' },
  };
  const cfg = presets[status] || { key: null, cls: 'bg-gray-100 text-gray-700' };
  const label = cfg.key ? t(`dashboards.event.ticketsPage.${cfg.key}`) : status;
  return (
    <span className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold ${cfg.cls}`}>
      {label}
    </span>
  );
}


export default function TicketsManagementPage() {
  const { occurrence_id: occurrenceId } = useParams();
  const { t, i18n } = useTranslation('products');
  const [occurrence, setOccurrence] = useState(null);
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [expandedId, setExpandedId] = useState(null);

  // Broadcast
  const [broadcastTemplate, setBroadcastTemplate] = useState('reminder');
  const [broadcastMessage, setBroadcastMessage] = useState('');
  const [broadcastSending, setBroadcastSending] = useState(false);
  const [broadcastResult, setBroadcastResult] = useState(null);

  // Per-row busy tracking
  const [rowBusy, setRowBusy] = useState(null); // {code, action:'resend'|'void'}

  const load = useCallback(async () => {
    try {
      const [occRes, ticketsRes] = await Promise.all([
        eventOccurrencesAPI.get(occurrenceId),
        ticketsAPI.listForOccurrence(occurrenceId, { includeVoided: true }),
      ]);
      setOccurrence(occRes.data);
      setTickets(ticketsRes.data?.tickets || []);
      setError(null);
    } catch (err) {
      setError(err?.response?.status === 404 ? 'not_found' : (err?.response?.data?.detail || 'generic'));
    } finally {
      setLoading(false);
    }
  }, [occurrenceId]);

  useEffect(() => { load(); }, [load]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return tickets.filter(tk => {
      if (statusFilter && tk.status !== statusFilter) return false;
      if (!q) return true;
      return (tk.code || '').toLowerCase().includes(q)
        || (tk.holder_name || '').toLowerCase().includes(q)
        || (tk.holder_email || '').toLowerCase().includes(q)
        || (tk.tier_label || '').toLowerCase().includes(q);
    });
  }, [tickets, search, statusFilter]);

  const handleResend = useCallback(async (code) => {
    if (rowBusy) return;
    setRowBusy({ code, action: 'resend' });
    try {
      const res = await ticketsAPI.resendEmail(code);
      if (res.data.ok) {
        toast.success(t('dashboards.event.ticketsPage.resendSuccess'));
      } else {
        const messages = {
          not_found:    t('dashboards.event.ticketsPage.resendNotFound'),
          no_email:     t('dashboards.event.ticketsPage.resendNoEmail'),
          voided:       t('dashboards.event.ticketsPage.resendVoided'),
          send_failed:  t('dashboards.event.ticketsPage.resendFailed'),
        };
        toast.error(messages[res.data.reason] || t('dashboards.event.ticketsPage.resendErrorPrefix', { reason: res.data.reason }));
      }
    } catch (err) {
      toast.error(err?.response?.data?.detail || t('dashboards.event.ticketsPage.errorNetwork'));
    } finally {
      setRowBusy(null);
    }
  }, [rowBusy, t]);

  const handleVoid = useCallback(async (code, holderName) => {
    if (rowBusy) return;
    const ok = window.confirm(t('dashboards.event.ticketsPage.voidConfirm', { name: holderName || code }));
    if (!ok) return;
    setRowBusy({ code, action: 'void' });
    try {
      const res = await ticketsAPI.voidTicket(code);
      const reasons = {
        voided:         t('dashboards.event.ticketsPage.voidedSuccess'),
        already_voided: t('dashboards.event.ticketsPage.voidedAlready'),
        checked_in:     t('dashboards.event.ticketsPage.voidedCheckedIn'),
        not_found:      t('dashboards.event.ticketsPage.voidedNotFound'),
        invalid_status: t('dashboards.event.ticketsPage.voidedInvalidStatus'),
      };
      if (res.data.ok) {
        toast.success(reasons[res.data.reason] || t('dashboards.event.ticketsPage.voidedFallback'));
      } else {
        toast.error(reasons[res.data.reason] || t('dashboards.event.ticketsPage.resendErrorPrefix', { reason: res.data.reason }));
      }
      // Refresh list to reflect status changes
      load();
    } catch (err) {
      toast.error(err?.response?.data?.detail || t('dashboards.event.ticketsPage.errorNetwork'));
    } finally {
      setRowBusy(null);
    }
  }, [rowBusy, load, t]);

  const handleBroadcast = useCallback(async () => {
    if (broadcastSending) return;
    if (broadcastTemplate === 'custom' && !broadcastMessage.trim()) {
      toast.error(t('dashboards.event.ticketsPage.broadcastCustomEmpty'));
      return;
    }
    if (!window.confirm(t('dashboards.event.ticketsPage.broadcastConfirm', { template: broadcastTemplate }))) return;
    setBroadcastSending(true);
    setBroadcastResult(null);
    try {
      const res = await ticketsAPI.broadcast(occurrenceId, {
        template: broadcastTemplate,
        message: broadcastMessage?.trim() || null,
        include_voided: false,
        include_checked_in: broadcastTemplate !== 'cancellation',
      });
      setBroadcastResult(res.data);
      if (res.data.error_message) {
        toast.error(t('dashboards.event.ticketsPage.broadcastErrorPrefix', { message: res.data.error_message }));
      } else {
        toast.success(t('dashboards.event.ticketsPage.broadcastSummary', {
          sent: res.data.sent,
          errors: res.data.errors,
          noEmail: res.data.skipped_no_email,
        }));
      }
    } catch (err) {
      toast.error(err?.response?.data?.detail || t('dashboards.event.ticketsPage.broadcastSendError'));
    } finally {
      setBroadcastSending(false);
    }
  }, [broadcastSending, broadcastTemplate, broadcastMessage, occurrenceId, t]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-sm text-gray-500">
        {t('dashboards.event.ticketsPage.loading')}
      </div>
    );
  }

  if (error === 'not_found' || !occurrence) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
        <div className="max-w-md text-center bg-white rounded-xl border p-8">
          <h1 className="text-2xl font-bold mb-2">{t('dashboards.event.ticketsPage.notFoundTitle')}</h1>
          <Link to="/events" className="inline-block rounded-md bg-gray-900 text-white px-4 py-2 text-sm">
            {t('dashboards.event.ticketsPage.backToEvents')}
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 pb-20">
      {/* Header */}
      <div className="bg-white border-b sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-4">
          <Link to={`/events/${occurrenceId}`} className="text-xs text-gray-500 hover:text-gray-900 underline">
            {t('dashboards.event.ticketsPage.headerBack')}
          </Link>
          <div className="flex items-start justify-between gap-2 mt-1">
            <div className="min-w-0">
              <h1 className="text-xl sm:text-2xl font-bold text-gray-900 truncate">
                {t('dashboards.event.ticketsPage.headerTitle', { event: occurrence.product_name || t('dashboards.event.ticketsPage.fallbackEventName') })}
              </h1>
              <p className="text-xs text-gray-500 mt-0.5">
                {t('dashboards.event.ticketsPage.headerSubtitle')}
              </p>
            </div>
            <Link
              to={`/events/${occurrenceId}/check-in`}
              className="rounded-md border border-gray-300 px-3 py-1.5 text-xs font-semibold text-gray-700 hover:border-gray-900 whitespace-nowrap"
            >{t('dashboards.event.ticketsPage.checkInBtn')}</Link>
          </div>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-5 space-y-5">

        {/* ── Broadcast card ─────────────────────────────────────────── */}
        <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-3">
          <div>
            <h2 className="text-base font-semibold text-gray-900">{t('dashboards.event.ticketsPage.broadcastTitle')}</h2>
            <p className="text-xs text-gray-500 mt-0.5">
              {t('dashboards.event.ticketsPage.broadcastSubtitle')}
            </p>
          </div>

          {/* Template picker */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {BROADCAST_TEMPLATE_KEYS.map(key => (
              <button
                key={key}
                type="button"
                onClick={() => setBroadcastTemplate(key)}
                className={`rounded-lg border px-3 py-2 text-left ${
                  broadcastTemplate === key
                    ? 'border-gray-900 bg-gray-50'
                    : 'border-gray-300 hover:border-gray-500'
                }`}
              >
                <p className="text-sm font-semibold text-gray-900">{t(`dashboards.event.ticketsPage.broadcastTemplates.${key}.label`)}</p>
                <p className="text-[11px] text-gray-500 mt-0.5">{t(`dashboards.event.ticketsPage.broadcastTemplates.${key}.hint`)}</p>
              </button>
            ))}
          </div>

          {/* Custom message */}
          <div>
            <label className="block text-xs font-medium text-gray-700 mb-1">
              {broadcastTemplate === 'custom'
                ? t('dashboards.event.ticketsPage.messageLabelCustom')
                : t('dashboards.event.ticketsPage.messageLabelOptional')}
            </label>
            <textarea
              value={broadcastMessage}
              onChange={e => setBroadcastMessage(e.target.value)}
              rows={broadcastTemplate === 'custom' ? 6 : 3}
              maxLength={5000}
              placeholder={
                broadcastTemplate === 'custom'
                  ? t('dashboards.event.ticketsPage.messagePlaceholderCustom')
                  : t('dashboards.event.ticketsPage.messagePlaceholderOptional')
              }
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none resize-y"
            />
          </div>

          <div className="flex items-center justify-between gap-3">
            <button
              type="button"
              onClick={handleBroadcast}
              disabled={broadcastSending}
              className="rounded-md bg-gray-900 text-white px-4 py-2 text-sm font-semibold hover:bg-gray-800 disabled:opacity-50"
            >
              {broadcastSending ? t('dashboards.event.ticketsPage.broadcastSendingBtn') : t('dashboards.event.ticketsPage.broadcastSendBtn')}
            </button>

            {broadcastResult && (
              <div className="text-xs text-gray-600">
                {t('dashboards.event.ticketsPage.broadcastResultPrefix')} <strong>{broadcastResult.sent}</strong> {t('dashboards.event.ticketsPage.broadcastSentLabel')} ·{' '}
                {broadcastResult.errors ? <span className="text-red-700"><strong>{broadcastResult.errors}</strong> {t('dashboards.event.ticketsPage.broadcastErrorsLabel')} · </span> : ''}
                {broadcastResult.skipped_no_email} {t('dashboards.event.ticketsPage.broadcastNoEmailLabel')}
              </div>
            )}
          </div>
        </div>

        {/* ── Tickets table ──────────────────────────────────────────── */}
        <div className="rounded-xl border border-gray-200 bg-white p-5">
          <div className="flex items-center justify-between gap-2 mb-3 flex-wrap">
            <h2 className="text-base font-semibold text-gray-900">{t('dashboards.event.ticketsPage.ticketsTitle', { count: filtered.length })}</h2>
          </div>

          {/* Filters */}
          <div className="flex flex-col sm:flex-row gap-2 mb-3">
            <input
              type="search"
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder={t('dashboards.event.ticketsPage.searchPlaceholder')}
              className="flex-1 rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-gray-900 focus:outline-none"
            />
            <select
              value={statusFilter}
              onChange={e => setStatusFilter(e.target.value)}
              className="rounded-md border border-gray-300 px-3 py-1.5 text-sm bg-white"
            >
              <option value="">{t('dashboards.event.ticketsPage.filterAll')}</option>
              <option value="valid">{t('dashboards.event.ticketsPage.filterValid')}</option>
              <option value="checked_in">{t('dashboards.event.ticketsPage.filterCheckedIn')}</option>
              <option value="voided">{t('dashboards.event.ticketsPage.filterVoided')}</option>
            </select>
          </div>

          {filtered.length === 0 ? (
            <p className="text-sm text-gray-500 text-center py-8">
              {t('dashboards.event.ticketsPage.emptyFilter')}
            </p>
          ) : (
            <div className="overflow-x-auto -mx-5">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100 text-left text-[11px] uppercase tracking-wide text-gray-500">
                    <th className="px-5 py-2 font-semibold">{t('dashboards.event.ticketsPage.colName')}</th>
                    <th className="px-2 py-2 font-semibold">{t('dashboards.event.ticketsPage.colCode')}</th>
                    <th className="px-2 py-2 font-semibold">{t('dashboards.event.ticketsPage.colTier')}</th>
                    <th className="px-2 py-2 font-semibold">{t('dashboards.event.ticketsPage.colStatus')}</th>
                    <th className="px-5 py-2 font-semibold text-right">{t('dashboards.event.ticketsPage.colActions')}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {filtered.map(tk => {
                    const isExpanded = expandedId === tk.id;
                    const busy = rowBusy?.code === tk.code;
                    const disableResend = tk.status === 'voided' || !tk.holder_email || busy;
                    const disableVoid   = tk.status === 'voided' || tk.status === 'checked_in' || busy;
                    return (
                      <React.Fragment key={tk.id}>
                        <tr className="hover:bg-gray-50">
                          <td className="px-5 py-2">
                            <button
                              type="button"
                              onClick={() => setExpandedId(isExpanded ? null : tk.id)}
                              className="text-left"
                            >
                              <p className="font-medium text-gray-900 truncate max-w-[200px]">
                                {tk.holder_name || '—'}
                              </p>
                              {tk.holder_email && (
                                <p className="text-[11px] text-gray-500 truncate max-w-[200px]">{tk.holder_email}</p>
                              )}
                            </button>
                          </td>
                          <td className="px-2 py-2 font-mono text-xs text-gray-700 whitespace-nowrap">{tk.code}</td>
                          <td className="px-2 py-2 text-xs text-gray-700 whitespace-nowrap">{tk.tier_label || '—'}</td>
                          <td className="px-2 py-2"><StatusPill status={tk.status} /></td>
                          <td className="px-5 py-2 text-right whitespace-nowrap">
                            <div className="inline-flex gap-1">
                              <button
                                type="button"
                                onClick={() => handleResend(tk.code)}
                                disabled={disableResend}
                                title={!tk.holder_email ? t('dashboards.event.ticketsPage.resendNoEmailTitle') : t('dashboards.event.ticketsPage.resendTitle')}
                                className="rounded border border-gray-300 px-2 py-1 text-[11px] font-medium text-gray-700 hover:border-gray-900 disabled:opacity-40"
                              >
                                {busy && rowBusy?.action === 'resend' ? '…' : t('dashboards.event.ticketsPage.resendBtn')}
                              </button>
                              <button
                                type="button"
                                onClick={() => handleVoid(tk.code, tk.holder_name)}
                                disabled={disableVoid}
                                title={
                                  tk.status === 'checked_in' ? t('dashboards.event.ticketsPage.voidedTitleCheckedIn')
                                  : tk.status === 'voided' ? t('dashboards.event.ticketsPage.voidedTitleAlready')
                                  : t('dashboards.event.ticketsPage.voidedTitleAnnul')
                                }
                                className="rounded border border-red-300 bg-red-50 px-2 py-1 text-[11px] font-medium text-red-800 hover:border-red-700 hover:bg-red-100 disabled:opacity-40 disabled:bg-gray-50 disabled:border-gray-300 disabled:text-gray-500"
                              >
                                {busy && rowBusy?.action === 'void' ? '…' : t('dashboards.event.ticketsPage.voidBtn')}
                              </button>
                            </div>
                          </td>
                        </tr>
                        {isExpanded && (
                          <tr className="bg-gray-50 border-b border-gray-100">
                            <td colSpan={5} className="px-5 py-3 text-xs text-gray-600">
                              <dl className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                                <div>
                                  <dt className="text-[10px] uppercase tracking-wide text-gray-400">{t('dashboards.event.ticketsPage.expandSeat')}</dt>
                                  <dd className="font-medium text-gray-900">
                                    {t('dashboards.event.ticketsPage.expandSeatVal', { index: tk.seat_index, total: tk.seat_count })}
                                  </dd>
                                </div>
                                <div>
                                  <dt className="text-[10px] uppercase tracking-wide text-gray-400">{t('dashboards.event.ticketsPage.expandIssued')}</dt>
                                  <dd className="font-medium text-gray-900">
                                    {tk.created_at ? new Date(tk.created_at).toLocaleString(i18n.language) : '—'}
                                  </dd>
                                </div>
                                <div>
                                  <dt className="text-[10px] uppercase tracking-wide text-gray-400">{t('dashboards.event.ticketsPage.expandCheckIn')}</dt>
                                  <dd className="font-medium text-gray-900">
                                    {tk.checked_in_at ? new Date(tk.checked_in_at).toLocaleString(i18n.language) : '—'}
                                  </dd>
                                </div>
                                {tk.voided_at && (
                                  <div className="sm:col-span-3">
                                    <dt className="text-[10px] uppercase tracking-wide text-gray-400">{t('dashboards.event.ticketsPage.expandVoidedAt')}</dt>
                                    <dd className="font-medium text-gray-900">
                                      {new Date(tk.voided_at).toLocaleString(i18n.language)}
                                      {tk.void_reason && <span className="text-gray-500"> · {tk.void_reason}</span>}
                                    </dd>
                                  </div>
                                )}
                                {tk.order_id && (
                                  <div className="sm:col-span-3">
                                    <dt className="text-[10px] uppercase tracking-wide text-gray-400">{t('dashboards.event.ticketsPage.expandOrder')}</dt>
                                    <dd className="font-mono text-[11px] text-gray-700">{tk.order_id}</dd>
                                  </div>
                                )}
                              </dl>
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
