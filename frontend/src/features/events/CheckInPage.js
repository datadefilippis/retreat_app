/**
 * CheckInPage — admin door-scanner for an event occurrence (E5).
 *
 * Route: /events/:occurrence_id/check-in   (authenticated)
 * Backend: POST /api/tickets/check-in      (E5)
 *
 * Design:
 *   - Mobile-first. One primary action at a time — the whole screen
 *     is biased towards "scan, see feedback, scan next".
 *   - Big live counter at top: "17 / 30 entrati" auto-refreshes.
 *   - Last scan result card renders green / yellow / red banner for
 *     ok / already_checked_in / voided-not_found-wrong_occurrence.
 *   - Manual input field is ALWAYS visible (phone keyboard friendly).
 *   - Optional camera scanner using html5-qrcode — tap "Avvia scanner"
 *     to request camera permission, tap "Stop" to release.
 *   - Collapsible attendance list at the bottom with filter tabs
 *     (Tutti / Da controllare / Entrati).
 */

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { ticketsAPI } from '../../api/tickets';
import { eventOccurrencesAPI } from '../../api/eventOccurrences';
import CameraScanner from './checkin/CameraScanner';


// Local error boundary scoped to the camera scanner. The door check-in
// flow MUST keep working even if html5-qrcode (or its dependency chain)
// throws during render in some browser combination — the operator can
// still type EVT-XXXX codes manually. Without this boundary a scanner
// crash propagates up to the global ErrorBoundary in App.js and the
// entire CheckInPage shows "Qualcosa è andato storto", taking the
// manual-input lifeline down with it.
class ScannerBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { failed: false };
  }
  static getDerivedStateFromError() {
    return { failed: true };
  }
  componentDidCatch(error, info) {
    // Console only — ErrorBoundary reset happens via the parent
    // closing/reopening the scanner.
    // eslint-disable-next-line no-console
    console.error('[CheckInPage] CameraScanner crashed:', error, info);
  }
  render() {
    if (this.state.failed) {
      return (
        <ScannerFailedFallback onClose={this.props.onClose} />
      );
    }
    return this.props.children;
  }
}


function ScannerFailedFallback({ onClose }) {
  const { t } = useTranslation('products');
  return (
    <div className="rounded-xl border border-red-200 bg-red-50 p-4">
      <p className="text-sm font-semibold text-red-900 mb-1">
        {t('dashboards.event.checkIn.scannerUnavailable')}
      </p>
      <p className="text-xs text-red-800">
        {t('dashboards.event.checkIn.scannerUnavailableHint')}
      </p>
      {onClose && (
        <button
          type="button"
          onClick={onClose}
          className="mt-2 text-xs text-red-900 underline"
        >{t('dashboards.event.checkIn.scannerCloseBtn')}</button>
      )}
    </div>
  );
}


// ── Result feedback styling ────────────────────────────────────────────────

const FEEDBACK_CFG = {
  ok:                 { bg: 'bg-green-50',  border: 'border-green-300',  text: 'text-green-900',  icon: '✅', labelKey: 'ok' },
  already_checked_in: { bg: 'bg-amber-50',  border: 'border-amber-300',  text: 'text-amber-900',  icon: '⚠️', labelKey: 'alreadyCheckedIn' },
  voided:             { bg: 'bg-red-50',    border: 'border-red-300',    text: 'text-red-900',    icon: '❌', labelKey: 'voided' },
  not_found:          { bg: 'bg-red-50',    border: 'border-red-300',    text: 'text-red-900',    icon: '❌', labelKey: 'notFound' },
  wrong_occurrence:   { bg: 'bg-red-50',    border: 'border-red-300',    text: 'text-red-900',    icon: '❌', labelKey: 'wrongOccurrence' },
  invalid_status:     { bg: 'bg-gray-100',  border: 'border-gray-300',   text: 'text-gray-800',   icon: '❓', labelKey: 'invalidStatus' },
};


function StatusBadge({ status }) {
  const { t } = useTranslation('products');
  const presets = {
    valid:        { key: 'valid',      cls: 'bg-blue-100 text-blue-900' },
    checked_in:   { key: 'checkedIn',  cls: 'bg-green-100 text-green-900' },
    voided:       { key: 'voided',     cls: 'bg-gray-200 text-gray-700' },
  };
  const cfg = presets[status] || { key: null, cls: 'bg-gray-100 text-gray-700' };
  const label = cfg.key ? t(`dashboards.event.checkIn.ticketStatus.${cfg.key}`) : status;
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${cfg.cls}`}>
      {label}
    </span>
  );
}


// CameraScanner is now in ./checkin/CameraScanner.jsx — better error
// mapping for camera-permission failures (NotAllowedError, NotFoundError,
// SecurityError on http://, etc.) and reports errors back to the page
// so we can autofocus the manual-input fallback.

// ── Main page ──────────────────────────────────────────────────────────────

export default function CheckInPage() {
  const { occurrence_id: occurrenceId } = useParams();
  const { t, i18n } = useTranslation('products');

  const [stats, setStats] = useState({ issued: 0, checked_in: 0, valid: 0, voided: 0, remaining: 0 });
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [occurrence, setOccurrence] = useState(null);

  const [manualCode, setManualCode] = useState('');
  const [lastResult, setLastResult] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [scannerOpen, setScannerOpen] = useState(false);
  const [filter, setFilter] = useState('all'); // all | pending | in
  const [listExpanded, setListExpanded] = useState(false);
  const [lockToOccurrence, setLockToOccurrence] = useState(true);

  // Ref to the manual input — used to autofocus when the camera scanner
  // reports a permission/device error so the operator can keep working
  // immediately by typing the EVT-XXXX code instead of getting stuck.
  const manualInputRef = useRef(null);

  const refresh = useCallback(async () => {
    try {
      const [statsRes, listRes] = await Promise.all([
        ticketsAPI.stats(occurrenceId),
        ticketsAPI.listForOccurrence(occurrenceId),
      ]);
      setStats(statsRes.data);
      setTickets(listRes.data.tickets || []);
      setError(null);
    } catch (err) {
      setError(err?.response?.data?.detail || t('dashboards.event.checkIn.loadError'));
    } finally {
      setLoading(false);
    }
  }, [occurrenceId, t]);

  // Initial load + occurrence lookup for the header
  useEffect(() => {
    let mounted = true;
    refresh();
    // Best-effort: fetch the occurrence itself to show title + date.
    // Non-blocking — we don't have a direct-by-id endpoint, so we
    // infer from the first ticket when available.
    return () => { mounted = false; };
  }, [refresh]);

  // Derive occurrence header info from the first ticket's snapshot
  useEffect(() => {
    if (!occurrence && tickets.length > 0) {
      setOccurrence({
        id: occurrenceId,
        product_name: null, // not snapshotted on ticket; shown via product fetch below
      });
    }
  }, [tickets, occurrence, occurrenceId]);

  // Poll every 10s while the screen is open
  useEffect(() => {
    const interval = setInterval(refresh, 10000);
    return () => clearInterval(interval);
  }, [refresh]);

  const handleCheckIn = useCallback(async (rawCode) => {
    const code = (rawCode || '').trim();
    if (!code || submitting) return;
    setSubmitting(true);
    try {
      const res = await ticketsAPI.checkIn({
        code,
        occurrence_id: lockToOccurrence ? occurrenceId : null,
      });
      const { ok, reason, ticket } = res.data;
      setLastResult({ code, ok, reason, ticket, at: Date.now() });
      // Any response — refresh counters so the header stays truthful
      refresh();
    } catch (err) {
      setLastResult({
        code, ok: false, reason: 'error', ticket: null, at: Date.now(),
        errorMsg: err?.response?.data?.detail || t('dashboards.event.checkIn.errorNetwork'),
      });
    } finally {
      setSubmitting(false);
      setManualCode('');
    }
  }, [submitting, lockToOccurrence, occurrenceId, refresh, t]);

  const filteredTickets = useMemo(() => {
    if (filter === 'pending') return tickets.filter(t => t.status === 'valid');
    if (filter === 'in') return tickets.filter(t => t.status === 'checked_in');
    return tickets;
  }, [tickets, filter]);

  const fbCfg = lastResult ? (FEEDBACK_CFG[lastResult.reason] || FEEDBACK_CFG.invalid_status) : null;
  const fbLabel = fbCfg ? t(`dashboards.event.checkIn.feedback.${fbCfg.labelKey}`) : null;

  return (
    <div className="min-h-screen bg-gray-50 pb-20">
      {/* Header */}
      <div className="bg-gray-900 text-white px-4 sm:px-6 py-5 sm:py-6 sticky top-0 z-10 shadow">
        <div className="max-w-2xl mx-auto flex items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="text-xs uppercase tracking-widest opacity-70">{t('dashboards.event.checkIn.headerKicker')}</p>
            <h1 className="text-xl sm:text-2xl font-bold truncate">
              {occurrence?.product_name || t('dashboards.event.checkIn.fallbackEventName')}
            </h1>
          </div>
          <div className="text-right shrink-0">
            <p className="text-3xl sm:text-4xl font-bold tabular-nums">
              {stats.checked_in}<span className="text-gray-400 text-xl"> / {stats.issued}</span>
            </p>
            <p className="text-[10px] uppercase tracking-wide opacity-70">{t('dashboards.event.checkIn.headerEntered')}</p>
          </div>
        </div>
      </div>

      <div className="max-w-2xl mx-auto px-4 sm:px-6 py-4 sm:py-6 space-y-4">
        {error && (
          <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-800">
            {error}
          </div>
        )}

        {/* Summary pills */}
        <div className="grid grid-cols-3 gap-2 text-center">
          <div className="rounded-xl bg-white border border-gray-200 p-3">
            <p className="text-xl font-bold text-gray-900 tabular-nums">{stats.valid}</p>
            <p className="text-[10px] uppercase tracking-wide text-gray-500 mt-0.5">{t('dashboards.event.checkIn.summary.toEnter')}</p>
          </div>
          <div className="rounded-xl bg-white border border-gray-200 p-3">
            <p className="text-xl font-bold text-green-700 tabular-nums">{stats.checked_in}</p>
            <p className="text-[10px] uppercase tracking-wide text-gray-500 mt-0.5">{t('dashboards.event.checkIn.summary.entered')}</p>
          </div>
          <div className="rounded-xl bg-white border border-gray-200 p-3">
            <p className="text-xl font-bold text-gray-500 tabular-nums">{stats.voided}</p>
            <p className="text-[10px] uppercase tracking-wide text-gray-500 mt-0.5">{t('dashboards.event.checkIn.summary.voided')}</p>
          </div>
        </div>

        {/* Last scan feedback */}
        {lastResult && fbCfg && (
          <div className={`rounded-xl border-2 p-4 ${fbCfg.bg} ${fbCfg.border}`}>
            <div className="flex items-start gap-3">
              <div className="text-3xl">{fbCfg.icon}</div>
              <div className="flex-1 min-w-0">
                <p className={`text-lg font-bold ${fbCfg.text}`}>{fbLabel}</p>
                {lastResult.ticket && (
                  <div className={`text-sm mt-1 ${fbCfg.text} opacity-90`}>
                    {lastResult.ticket.holder_name && (
                      <p className="font-medium">{lastResult.ticket.holder_name}</p>
                    )}
                    {lastResult.ticket.tier_label && (
                      <p className="text-xs opacity-80">{t('dashboards.event.checkIn.tierLabel', { tier: lastResult.ticket.tier_label })}</p>
                    )}
                    <p className="font-mono text-xs mt-1 opacity-80">{lastResult.ticket.code}</p>
                    {lastResult.reason === 'already_checked_in' && lastResult.ticket.checked_in_at && (
                      <p className="text-xs mt-1 opacity-80">
                        {t('dashboards.event.checkIn.checkedInAt', { time: new Date(lastResult.ticket.checked_in_at).toLocaleTimeString(i18n.language, { hour: '2-digit', minute: '2-digit' }) })}
                      </p>
                    )}
                  </div>
                )}
                {!lastResult.ticket && lastResult.code && (
                  <p className={`text-sm mt-1 font-mono opacity-80 ${fbCfg.text}`}>{lastResult.code}</p>
                )}
                {lastResult.errorMsg && (
                  <p className={`text-sm mt-1 ${fbCfg.text}`}>{lastResult.errorMsg}</p>
                )}
              </div>
              <button
                type="button" onClick={() => setLastResult(null)}
                className={`text-xs underline ${fbCfg.text} opacity-70 hover:opacity-100`}
              >{t('dashboards.event.checkIn.closeBtn')}</button>
            </div>
          </div>
        )}

        {/* Manual input */}
        <form onSubmit={(e) => { e.preventDefault(); handleCheckIn(manualCode); }}
              className="rounded-xl border border-gray-200 bg-white p-4 space-y-3">
          <label className="block">
            <span className="text-sm font-medium text-gray-900">{t('dashboards.event.checkIn.manualLabel')}</span>
            <input
              ref={manualInputRef}
              type="text"
              value={manualCode}
              onChange={(e) => setManualCode(e.target.value.toUpperCase())}
              placeholder={t('dashboards.event.checkIn.manualPlaceholder')}
              className="mt-1 w-full rounded-md border border-gray-300 px-3 py-3 text-base font-mono tracking-wider uppercase focus:border-gray-900 focus:outline-none"
              autoComplete="off" autoCapitalize="characters" autoCorrect="off"
              inputMode="text"
            />
          </label>
          <button
            type="submit" disabled={!manualCode.trim() || submitting}
            className="w-full rounded-md bg-gray-900 text-white px-4 py-3 text-sm font-semibold hover:bg-gray-800 disabled:opacity-50"
          >
            {submitting ? t('dashboards.event.checkIn.verifyingBtn') : t('dashboards.event.checkIn.submitBtn')}
          </button>
          <label className="flex items-center gap-2 text-xs text-gray-600">
            <input
              type="checkbox" checked={lockToOccurrence}
              onChange={(e) => setLockToOccurrence(e.target.checked)}
              className="rounded"
            />
            {t('dashboards.event.checkIn.lockToOccurrence')}
          </label>
        </form>

        {/* Camera scanner — opens on demand, closes on dismiss or fatal
            error. When the scanner reports a permission/device failure
            we keep its error banner visible (so the operator sees what
            went wrong) but autofocus the manual input so they can keep
            checking people in immediately. The ScannerBoundary above
            ensures a scanner-level crash never tears the rest of the
            page down — the manual input above must always work. */}
        {scannerOpen ? (
          <ScannerBoundary onClose={() => setScannerOpen(false)}>
            <CameraScanner
              onCode={(decoded) => handleCheckIn(decoded)}
              onClose={() => setScannerOpen(false)}
              onError={() => {
                // Defer to the next tick so the scanner's own "error
                // banner" mounts first; otherwise the focus shift can
                // happen before the user even sees what went wrong.
                setTimeout(() => {
                  if (manualInputRef.current) {
                    manualInputRef.current.focus();
                    if (typeof manualInputRef.current.select === 'function') {
                      manualInputRef.current.select();
                    }
                  }
                }, 0);
              }}
            />
          </ScannerBoundary>
        ) : (
          <button
            type="button"
            onClick={() => setScannerOpen(true)}
            className="w-full rounded-xl border-2 border-dashed border-gray-300 bg-white px-4 py-4 text-sm font-medium text-gray-700 hover:border-gray-500 hover:text-gray-900 flex items-center justify-center gap-2"
          >
            {t('dashboards.event.checkIn.openScanner')}
          </button>
        )}

        {/* Attendance list */}
        <div className="rounded-xl border border-gray-200 bg-white">
          <button
            type="button" onClick={() => setListExpanded(!listExpanded)}
            className="w-full flex items-center justify-between px-4 py-3 text-sm font-semibold text-gray-900"
          >
            <span>{t('dashboards.event.checkIn.listTitle', { count: stats.valid + stats.checked_in })}</span>
            <span className={`transition-transform text-gray-400 ${listExpanded ? 'rotate-90' : ''}`}>▸</span>
          </button>

          {listExpanded && (
            <>
              <div className="flex gap-1 px-3 pb-2 border-b border-gray-100">
                {[
                  { k: 'all',     labelKey: 'filterAll',     n: stats.valid + stats.checked_in + stats.voided },
                  { k: 'pending', labelKey: 'filterPending', n: stats.valid },
                  { k: 'in',      labelKey: 'filterEntered', n: stats.checked_in },
                ].map(tab => (
                  <button
                    key={tab.k} type="button" onClick={() => setFilter(tab.k)}
                    className={`rounded-full px-3 py-1 text-xs font-medium ${
                      filter === tab.k
                        ? 'bg-gray-900 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    {t(`dashboards.event.checkIn.${tab.labelKey}`)} · {tab.n}
                  </button>
                ))}
              </div>
              <ul className="divide-y divide-gray-100 max-h-96 overflow-y-auto">
                {loading && (
                  <li className="px-4 py-3 text-xs text-gray-500">{t('dashboards.event.checkIn.loading')}</li>
                )}
                {!loading && filteredTickets.length === 0 && (
                  <li className="px-4 py-4 text-xs text-gray-500 text-center">{t('dashboards.event.checkIn.listEmpty')}</li>
                )}
                {filteredTickets.map(ticket => (
                  <li key={ticket.id} className="px-4 py-3 flex items-center justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {ticket.holder_name || t('dashboards.event.checkIn.guestPlaceholder')}
                        {ticket.tier_label && <span className="text-xs text-gray-500 font-normal ml-2">· {ticket.tier_label}</span>}
                      </p>
                      <p className="text-xs font-mono text-gray-500">{ticket.code}</p>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <StatusBadge status={ticket.status} />
                      {ticket.status === 'valid' && (
                        <button
                          type="button" onClick={() => handleCheckIn(ticket.code)}
                          className="text-xs rounded-md bg-gray-900 text-white px-2.5 py-1 hover:bg-gray-800"
                        >{t('dashboards.event.checkIn.rowEnterBtn')}</button>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>

        <div className="text-center pt-2">
          <Link to="/products" className="text-xs text-gray-600 underline hover:text-gray-900">
            {t('dashboards.event.checkIn.backToProducts')}
          </Link>
        </div>
      </div>
    </div>
  );
}
