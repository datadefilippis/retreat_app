/**
 * EventDashboardPage — unified admin control center for one event
 * (E6 + G3).
 *
 * Route: /events/:occurrence_id   (authenticated)
 *
 * Sections (top → bottom):
 *   - Hero: title + date + status chip + cover image
 *   - Quick action bar: preview landing / copy link / check-in /
 *     export CSV
 *   - G3 Revenue card: € total + tickets sold + per-tier breakdown
 *   - G3 Sales timeline sparkline (last-30d by day)
 *   - Capacity progress bar
 *   - Tier list
 *   - Attendance summary (issued / entrati / valid)
 *   - G3 Inline participants list with search + pagination
 *   - Location + description
 *
 * Data sources (loaded in parallel at mount):
 *   eventOccurrencesAPI.get(id)        occurrence + product snapshot
 *   eventTicketTiersAPI.list(id)       tiers
 *   ticketsAPI.stats(id)               status counters
 *   eventOccurrencesAPI.analytics(id)  revenue + timeline (G3)
 *   ticketsAPI.listForOccurrence(id)   participants (G3)
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useParams, Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import api from '../../api/client';
import { eventOccurrencesAPI, eventTicketTiersAPI } from '../../api/eventOccurrences';
import { ticketsAPI } from '../../api/tickets';
import { ordersAPI } from '../../api/orders';
import { storesAPI } from '../../api/stores';
import { productsAPI } from '../../api';
import FieldEditorList from './components/FieldEditorList';
import { pruneFieldConfigs } from './components/fieldConfigUtils';
// W1.S5/Phase 2.9 — additive cost composition editor for edits.
import CostSourceEditor from '../products/components/CostSourceEditor';
import { MiniBars } from '../../components/charts';
import ContactActions from '../../components/ContactActions';
import RetreatContentEditor from './components/RetreatContentEditor';
import MultiLangSection from '../../components/MultiLangSection';


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

function formatPrice(n, currency = 'EUR', locale = 'it-IT') {
  if (n === null || n === undefined) return '';
  try {
    return new Intl.NumberFormat(locale, { style: 'currency', currency }).format(n);
  } catch { return `${n} ${currency}`; }
}

// ── Fase 2 S2 (retreat) — card Incassi ─────────────────────────────────────
// Autonoma: carica GET /event-occurrences/{id}/payments per conto suo, così
// non tocca il Promise.all principale. Fonte di verità: payment_schedules.

function PaymentsCard({ occurrenceId }) {
  const { t, i18n } = useTranslation('products');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busyRow, setBusyRow] = useState(null);

  const load = useCallback(async () => {
    try {
      const res = await eventOccurrencesAPI.payments(occurrenceId);
      setData(res.data);
    } catch { setData(null); }
    finally { setLoading(false); }
  }, [occurrenceId]);

  useEffect(() => { load(); }, [load]);

  const fmt = (minor) => formatPrice((minor || 0) / 100, data?.orders?.[0]?.currency || 'EUR', i18n.language);
  const fmtDate = (iso) => iso ? new Date(iso).toLocaleDateString(i18n.language) : '';

  const postponeRow = async (orderId, seq) => {
    const date = window.prompt(t('dashboards.event.payments.postponePrompt'));
    if (!date || !/^\d{4}-\d{2}-\d{2}$/.test(date.trim())) return;
    setBusyRow(`${orderId}:${seq}`);
    try {
      await ordersAPI.postponeScheduleRow(orderId, seq, `${date.trim()}T12:00:00+00:00`);
      toast.success(t('dashboards.event.payments.postponeOk'));
      await load();
    } catch (err) {
      toast.error(err?.response?.data?.detail || t('dashboards.event.payments.actionErr'));
    } finally { setBusyRow(null); }
  };

  const waiveRow = async (orderId, seq) => {
    const reason = window.prompt(t('dashboards.event.payments.waivePrompt'));
    if (!reason || !reason.trim()) return;
    setBusyRow(`${orderId}:${seq}`);
    try {
      await ordersAPI.waiveScheduleRow(orderId, seq, reason.trim());
      toast.success(t('dashboards.event.payments.waiveOk'));
      await load();
    } catch (err) {
      toast.error(err?.response?.data?.detail || t('dashboards.event.payments.actionErr'));
    } finally { setBusyRow(null); }
  };

  const refundOrder = async (o) => {
    if (!window.confirm(t('dashboards.event.payments.refundConfirm',
        { percent: '—', amount: '—' }))) return;
    const reason = window.prompt(t('dashboards.event.payments.refundReasonPrompt')) || '';
    setBusyRow(o.order_id);
    try {
      const res = await ordersAPI.refundOrder(o.order_id, { reason: reason.trim() });
      toast.success(t('dashboards.event.payments.refundOk'));
      const manual = res.data?.refunded_manual_minor || 0;
      if (manual > 0) {
        toast.warning(t('dashboards.event.payments.refundManualNote',
          { amount: fmt(manual) }), { duration: 9000 });
      }
      await load();
    } catch (err) {
      toast.error(err?.response?.data?.detail || t('dashboards.event.payments.actionErr'));
    } finally { setBusyRow(null); }
  };

  const cancelRetreat = async () => {
    if (!window.confirm(t('dashboards.event.payments.cancelRetreatConfirm1'))) return;
    if (!window.confirm(t('dashboards.event.payments.cancelRetreatConfirm2'))) return;
    setBusyRow('cascade');
    try {
      const res = await eventOccurrencesAPI.cancelCascade(occurrenceId);
      toast.success(t('dashboards.event.payments.cancelRetreatOk',
        { count: res.data?.orders_processed ?? 0 }));
      await load();
    } catch (err) {
      toast.error(err?.response?.data?.detail || t('dashboards.event.payments.actionErr'));
    } finally { setBusyRow(null); }
  };

  const exportCsv = async () => {
    try {
      const res = await api.get(eventOccurrencesAPI.paymentsCsvUrl(occurrenceId),
        { responseType: 'blob' });
      const url = URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement('a');
      a.href = url; a.download = `incassi-${occurrenceId.slice(0, 8)}.csv`;
      a.click(); URL.revokeObjectURL(url);
    } catch {
      toast.error(t('dashboards.event.payments.actionErr'));
    }
  };

  const markPaid = async (orderId, seq) => {
    const note = window.prompt(t('dashboards.event.payments.markPaidPrompt'));
    if (!note || !note.trim()) return;
    setBusyRow(`${orderId}:${seq}`);
    try {
      await ordersAPI.markSchedulePaidManual(orderId, seq, note.trim());
      toast.success(t('dashboards.event.payments.markPaidOk'));
      await load();
    } catch (err) {
      toast.error(err?.response?.data?.detail || t('dashboards.event.payments.markPaidErr'));
    } finally { setBusyRow(null); }
  };

  if (loading) return (
    <div className="rounded-xl border border-gray-200 bg-white px-5 py-4 text-sm text-gray-500">
      {t('dashboards.event.payments.loading')}
    </div>
  );
  const summary = data?.summary;
  const orders = (data?.orders || []).filter(o => o.order_status !== 'draft' || o.payment_state !== 'none');

  return (
    <div className="rounded-xl border border-gray-200 bg-white px-5 py-4">
      <h2 className="text-sm font-semibold text-gray-900 mb-3">{t('dashboards.event.payments.title')}</h2>
      {!summary || orders.length === 0 ? (
        <p className="text-sm text-gray-500">{t('dashboards.event.payments.empty')}</p>
      ) : (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
            {[
              ['chipIncassato', summary.incassato_minor, 'text-emerald-700 bg-emerald-50 border-emerald-200'],
              ['chipInArrivo', summary.in_arrivo_minor, 'text-gray-700 bg-gray-50 border-gray-200'],
              ['chipInRitardo', summary.in_ritardo_minor, 'text-amber-700 bg-amber-50 border-amber-200'],
              ['chipARischio', summary.a_rischio_minor, 'text-red-700 bg-red-50 border-red-200'],
            ].map(([key, minor, cls]) => (
              <div key={key} className={`rounded-lg border px-3 py-2 ${cls}`}>
                <p className="text-[11px] font-semibold uppercase tracking-wide">{t(`dashboards.event.payments.${key}`)}</p>
                <p className="text-lg font-bold tabular-nums">{fmt(minor)}</p>
              </div>
            ))}
          </div>
          <p className="text-xs font-semibold text-gray-700 uppercase tracking-wide mb-2">
            {t('dashboards.event.payments.ordersHeading')}
          </p>
          <div className="space-y-3">
            {orders.map(o => (
              <div key={o.order_id} className="rounded-lg border border-gray-100 px-3 py-2">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {o.customer_name || o.order_number || o.order_id.slice(0, 8)}
                  </p>
                  <span className="flex items-center gap-2">
                    <span className="text-[11px] text-gray-500">{o.order_number}</span>
                    {['deposit_paid', 'fully_paid'].includes(o.payment_state)
                      && o.order_status !== 'cancelled' && (
                      <button
                        type="button"
                        disabled={busyRow === o.order_id}
                        onClick={() => refundOrder(o)}
                        className="rounded border border-red-200 px-2 py-0.5 text-[11px] font-medium text-red-700 hover:border-red-500 disabled:opacity-50"
                      >
                        {t('dashboards.event.payments.refund')}
                      </button>
                    )}
                  </span>
                </div>
                <div className="mt-1 space-y-1">
                  {(o.rows || []).map(r => (
                    <div key={r.seq} className="flex items-center justify-between gap-2 text-xs">
                      <span className="text-gray-600">
                        {r.label} · <span className="tabular-nums">{fmt(r.amount_minor)}</span>
                        {' — '}
                        {['paid', 'paid_manual'].includes(r.status)
                          ? t('dashboards.event.payments.rowPaidAt', { date: fmtDate(r.paid_at) })
                          : ['pending', 'processing', 'overdue', 'at_risk'].includes(r.status)
                            ? t('dashboards.event.payments.rowDue', { date: fmtDate(r.due_at) })
                            : null}
                        {' '}
                        <span className="font-semibold">
                          {t(`dashboards.event.payments.statusLabels.${r.status}`)}
                        </span>
                        {r.manual_note && (
                          <span className="text-gray-400"> · {t('dashboards.event.payments.manualNoteLabel', { note: r.manual_note })}</span>
                        )}
                      </span>
                      {['pending', 'overdue', 'at_risk'].includes(r.status) && (
                        <span className="shrink-0 flex gap-1">
                          <button
                            type="button"
                            disabled={busyRow === `${o.order_id}:${r.seq}`}
                            onClick={() => markPaid(o.order_id, r.seq)}
                            className="rounded border border-gray-300 px-2 py-0.5 text-[11px] font-medium text-gray-700 hover:border-gray-900 disabled:opacity-50"
                          >
                            {t('dashboards.event.payments.markPaid')}
                          </button>
                          <button
                            type="button"
                            disabled={busyRow === `${o.order_id}:${r.seq}`}
                            onClick={() => postponeRow(o.order_id, r.seq)}
                            className="rounded border border-gray-300 px-2 py-0.5 text-[11px] font-medium text-gray-700 hover:border-gray-900 disabled:opacity-50"
                          >
                            {t('dashboards.event.payments.postpone')}
                          </button>
                          <button
                            type="button"
                            disabled={busyRow === `${o.order_id}:${r.seq}`}
                            onClick={() => waiveRow(o.order_id, r.seq)}
                            className="rounded border border-gray-300 px-2 py-0.5 text-[11px] font-medium text-gray-700 hover:border-gray-900 disabled:opacity-50"
                          >
                            {t('dashboards.event.payments.waive')}
                          </button>
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
          {data.abandoned_drafts > 0 && (
            <p className="text-[11px] text-gray-400 mt-3">
              {t('dashboards.event.payments.abandonedNote', { count: data.abandoned_drafts })}
            </p>
          )}
          <div className="mt-4 pt-3 border-t border-gray-100 flex items-center justify-between gap-2">
            <button
              type="button"
              onClick={exportCsv}
              className="rounded border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700 hover:border-gray-900"
            >
              {t('dashboards.event.payments.exportCsv')}
            </button>
            <button
              type="button"
              disabled={busyRow === 'cascade'}
              onClick={cancelRetreat}
              className="rounded border border-red-200 px-3 py-1.5 text-xs font-medium text-red-700 hover:border-red-500 disabled:opacity-50"
            >
              {t('dashboards.event.payments.cancelRetreat')}
            </button>
          </div>
        </>
      )}
    </div>
  );
}


function StatusBadge({ status }) {
  const { t } = useTranslation('products');
  const presets = {
    draft:     { key: 'draft',     cls: 'bg-gray-100 text-gray-700' },
    published: { key: 'published', cls: 'bg-green-100 text-green-900' },
    closed:    { key: 'closed',    cls: 'bg-amber-100 text-amber-900' },
    cancelled: { key: 'cancelled', cls: 'bg-red-100 text-red-900' },
  };
  const cfg = presets[status] || { key: null, cls: 'bg-gray-100 text-gray-700' };
  const label = cfg.key ? t(`dashboards.event.statusBadge.${cfg.key}`) : status;
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${cfg.cls}`}>
      {label}
    </span>
  );
}


export default function EventDashboardPage() {
  const { occurrence_id: occurrenceId } = useParams();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  // Banner one-shot post-creazione (?creato=1 dal wizard): porta
  // l'operatore dritto alla Pagina di vendita per programma/foto/FAQ.
  const [showCreatedBanner, setShowCreatedBanner] = useState(
    searchParams.get('creato') === '1');
  const { t, i18n } = useTranslation('products');
  const [occurrence, setOccurrence] = useState(null);

  // E1/F5: product edit panel — opened by ?edit=product (e.g. from EventsGrid pencil)
  const [editProductOpen, setEditProductOpen] = useState(() => searchParams.get('edit') === 'product');
  const [productForm, setProductForm] = useState({
    name: '', description: '', image_url: '',
    unit_price: '', transaction_mode: 'direct', is_published: false,
    requires_attendee_details: false,  // F1 Onda 8
    // F2 Onda 9 — configurable contacts + custom fields
    require_attendee_email: true,
    require_attendee_phone: false,
    attendee_fields: [],
    order_fields: [],
    // F4 Onda 11 — per-event T&C override (markdown)
    terms_content: '',
  });
  const [savingProduct, setSavingProduct] = useState(false);
  const [uploadingImage, setUploadingImage] = useState(false);

  // E2: occurrence edit (Quando e dove)
  const [editOccurrenceOpen, setEditOccurrenceOpen] = useState(false);
  const [occurrenceForm, setOccurrenceForm] = useState({
    start_at: '', end_at: '', capacity: '', status: 'draft',
    venue_name: '', address: '', city: '', postal_code: '', country: 'IT',
    cover_image_url: '', latitude: '', longitude: '', slug: '',
  });
  const [savingOccurrence, setSavingOccurrence] = useState(false);

  // E3: long description edit
  const [editLongDescOpen, setEditLongDescOpen] = useState(false);
  const [longDescForm, setLongDescForm] = useState('');
  // Multilingua manuale — le lingue offerte dall'operatore (per campo);
  // la fonte e' product.translations, il salvataggio passa dal PATCH prodotto
  const [trName, setTrName] = useState({});
  const [trDescription, setTrDescription] = useState({});
  const [trLong, setTrLong] = useState({});
  const buildTranslationsPayload = () => {
    const langs = new Set([...Object.keys(trName), ...Object.keys(trDescription), ...Object.keys(trLong)]);
    const out = {};
    langs.forEach(l => {
      const entry = {};
      if ((trName[l] || '').trim()) entry.name = trName[l].trim();
      if ((trDescription[l] || '').trim()) entry.description = trDescription[l].trim();
      if ((trLong[l] || '').trim()) entry.long_description = trLong[l].trim();
      if (Object.keys(entry).length) out[l] = entry;
    });
    return out;
  };
  const [savingLongDesc, setSavingLongDesc] = useState(false);

  // E4: tier CRUD inline
  const [tierEditId, setTierEditId] = useState(null);
  const [tierForms, setTierForms] = useState({});
  const [savingTierIds, setSavingTierIds] = useState(new Set());
  const [deletingTierIds, setDeletingTierIds] = useState(new Set());
  const [showAddTier, setShowAddTier] = useState(false);
  const [newTierForm, setNewTierForm] = useState({ label: '', price: '', capacity: '', description: '' });
  const [savingNewTier, setSavingNewTier] = useState(false);
  const [tiers, setTiers] = useState([]);
  const [stats, setStats] = useState({
    issued: 0, valid: 0, checked_in: 0, voided: 0, remaining: 0,
    // F1 Onda 8 — per-holder delivery counters
    delivery_sent: 0, delivery_pending: 0, delivery_unsent: 0, delivery_targets: 0,
  });
  const [resendingAll, setResendingAll] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // G3 additions
  const [analytics, setAnalytics] = useState(null); // {revenue_total, tickets_sold_total, revenue_by_tier, sales_timeline, currency}
  const [participants, setParticipants] = useState([]);
  const [participantSearch, setParticipantSearch] = useState('');
  const [participantStatusFilter, setParticipantStatusFilter] = useState('');
  const [participantsPage, setParticipantsPage] = useState(1);
  const [exportingCsv, setExportingCsv] = useState(false);
  // F4: store assignment
  const [availableStores, setAvailableStores] = useState([]);
  const [storeIds, setStoreIds] = useState([]);
  const [savingStores, setSavingStores] = useState(false);

  useEffect(() => {
    storesAPI.list().then(r => setAvailableStores(r.data?.stores || [])).catch(() => {});
  }, []);

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      try {
        // G3: fetch 5 sources in parallel (analytics + participants added)
        const [occRes, tiersRes, statsRes, analyticsRes, ticketsRes] = await Promise.all([
          eventOccurrencesAPI.get(occurrenceId),
          eventTicketTiersAPI.list(occurrenceId),
          ticketsAPI.stats(occurrenceId),
          eventOccurrencesAPI.analytics(occurrenceId).catch(() => ({ data: null })),
          ticketsAPI.listForOccurrence(occurrenceId).catch(() => ({ data: { tickets: [] } })),
        ]);
        if (!mounted) return;
        const occ = occRes.data || {};
        setOccurrence(occ);
        setStoreIds(occ.product_store_ids || []);
        // E1: full product form hydration
        setProductForm({
          name: occ.product_name || '',
          description: occ.product_description || '',
          image_url: occ.product_image_url || '',
          unit_price: occ.product_unit_price != null ? String(occ.product_unit_price) : '',
          transaction_mode: occ.product_transaction_mode || 'direct',
          is_published: occ.product_is_published || false,
          // F1 Onda 8 — hydrate from product.metadata
          requires_attendee_details: !!(occ.product_metadata?.requires_attendee_details),
          // F2 Onda 9
          require_attendee_email: occ.product_metadata?.require_attendee_email ?? true,
          require_attendee_phone: occ.product_metadata?.require_attendee_phone ?? false,
          attendee_fields: occ.product_metadata?.attendee_fields || [],
          order_fields: occ.product_metadata?.order_fields || [],
          // F4 Onda 11
          terms_content: occ.product_metadata?.terms_content || '',
          // W1.S5/Phase 2.9 — hydrate cost composition. The
          // occurrence_details endpoint returns `product_cost_source`
          // when present; null when the merchant hasn't configured it.
          cost_source: occ.product_cost_source || null,
        });
        // E2: occurrence form hydration
        setOccurrenceForm({
          start_at: occ.start_at ? occ.start_at.slice(0, 16) : '',
          end_at: occ.end_at ? occ.end_at.slice(0, 16) : '',
          capacity: occ.capacity != null ? String(occ.capacity) : '',
          status: occ.status || 'draft',
          venue_name: occ.venue_name || '',
          address: occ.address || '',
          city: occ.city || '',
          postal_code: occ.postal_code || '',
          country: occ.country || 'IT',
          cover_image_url: occ.cover_image_url || '',
          latitude: occ.latitude != null ? String(occ.latitude) : '',
          longitude: occ.longitude != null ? String(occ.longitude) : '',
          slug: occ.slug || '',
        });
        // E3: long description
        setLongDescForm(occ.long_description || '');
        // multilingua manuale: split per campo per i due editor
        const ptr = occ.product_translations || {};
        const nm = {}, d = {}, ld = {};
        Object.entries(ptr).forEach(([l, f]) => {
          if (f?.name) nm[l] = f.name;
          if (f?.description) d[l] = f.description;
          if (f?.long_description) ld[l] = f.long_description;
        });
        setTrName(nm);
        setTrDescription(d);
        setTrLong(ld);
        // E4: tier forms
        const tiersData = tiersRes.data.tiers || [];
        setTiers(tiersData);
        const forms = {};
        tiersData.forEach(t => {
          forms[t.id] = {
            label: t.label || '',
            price: t.price != null ? String(t.price) : '',
            capacity: t.capacity != null ? String(t.capacity) : '',
            description: t.description || '',
            is_active: t.is_active !== false,
          };
        });
        setTierForms(forms);
        setStats(statsRes.data);
        setAnalytics(analyticsRes.data || null);
        setParticipants(ticketsRes.data?.tickets || []);
        setError(null);
      } catch (err) {
        if (!mounted) return;
        setError(err?.response?.status === 404 ? 'not_found' : (err?.response?.data?.detail || 'generic'));
      } finally {
        if (mounted) setLoading(false);
      }
    };
    load();
    return () => { mounted = false; };
  }, [occurrenceId]);

  // G6: Duplicate this event — ask the backend for a wizard-ready
  // payload, then hand it off to /events/new via navigation state.
  // The wizard reads location.state.prefillData and renders with
  // everything filled in except start_at (so the merchant must pick
  // a new date — the whole point of duplicating).
  const [duplicating, setDuplicating] = useState(false);
  const handleDuplicate = useCallback(async () => {
    if (duplicating) return;
    setDuplicating(true);
    try {
      const res = await eventOccurrencesAPI.duplicateData(occurrenceId);
      navigate('/events/new', {
        state: {
          prefillData: res.data,
          sourceLabel: res.data?.source_event_name || null,
        },
      });
    } catch (err) {
      toast.error(err?.response?.data?.detail || t('dashboards.event.toasts.duplicateError'));
      setDuplicating(false);
    }
    // note: no finally — success leaves the page anyway
  }, [occurrenceId, duplicating, navigate]);

  // G6: Archive / unarchive — single PATCH on the occurrence.
  const [togglingArchive, setTogglingArchive] = useState(false);
  const handleToggleArchive = useCallback(async () => {
    if (togglingArchive || !occurrence) return;
    const willArchive = !occurrence.is_archived;
    const msg = willArchive
      ? t('dashboards.event.toasts.archiveConfirm')
      : t('dashboards.event.toasts.unarchiveConfirm');
    if (!window.confirm(msg)) return;
    setTogglingArchive(true);
    try {
      await eventOccurrencesAPI.update(occurrenceId, { is_archived: willArchive });
      setOccurrence(prev => prev ? { ...prev, is_archived: willArchive } : prev);
      toast.success(willArchive ? t('dashboards.event.toasts.archived') : t('dashboards.event.toasts.unarchived'));
    } catch (err) {
      toast.error(err?.response?.data?.detail || t('dashboards.event.toasts.genericError'));
    } finally {
      setTogglingArchive(false);
    }
  }, [occurrenceId, occurrence, togglingArchive]);

  // G3: CSV export. Uses the authenticated api client so the cookie/
  // bearer token reaches the backend; writes a blob to a hidden link
  // and auto-clicks it. Works on modern browsers without popups.
  const handleExportCsv = useCallback(async () => {
    if (exportingCsv) return;
    setExportingCsv(true);
    try {
      const res = await api.get(`/event-occurrences/${occurrenceId}/tickets-csv`, {
        responseType: 'blob',
      });
      const blob = new Blob([res.data], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `attendance-${occurrenceId}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      toast.success(t('dashboards.event.toasts.csvDownloaded'));
    } catch (err) {
      toast.error(err?.response?.data?.detail || t('dashboards.event.toasts.csvError'));
    } finally {
      setExportingCsv(false);
    }
  }, [occurrenceId, exportingCsv]);

  // G3: filtered + paginated participants (client-side; attendance
  // lists stay under a few hundred rows)
  const PAGE_SIZE = 20;
  const filteredParticipants = useMemo(() => {
    const q = participantSearch.trim().toLowerCase();
    return participants.filter(p => {
      if (participantStatusFilter && p.status !== participantStatusFilter) return false;
      if (!q) return true;
      return (p.code || '').toLowerCase().includes(q)
        || (p.holder_name || '').toLowerCase().includes(q)
        || (p.holder_email || '').toLowerCase().includes(q)
        || (p.tier_label || '').toLowerCase().includes(q);
    });
  }, [participants, participantSearch, participantStatusFilter]);

  const pagedParticipants = useMemo(() => {
    const start = (participantsPage - 1) * PAGE_SIZE;
    return filteredParticipants.slice(start, start + PAGE_SIZE);
  }, [filteredParticipants, participantsPage]);

  const totalPages = Math.max(1, Math.ceil(filteredParticipants.length / PAGE_SIZE));

  // Reset to page 1 when filters change
  useEffect(() => { setParticipantsPage(1); }, [participantSearch, participantStatusFilter]);

  const dt = useMemo(() => occurrence ? formatDateTime(occurrence.start_at, i18n.language) : null, [occurrence, i18n.language]);
  // CF5 — ritiro concluso? Decide il contesto del contatto partecipante:
  // prima = info pratiche (pre_retreat), dopo = invito recensione.
  const isPastEvent = useMemo(() => {
    const ref = occurrence?.end_at || occurrence?.start_at;
    return Boolean(ref && new Date(ref) < new Date());
  }, [occurrence]);
  const outreachVars = useMemo(() => {
    // formatDateTime restituisce {date, time} — le vars outreach vogliono stringhe
    const fd = occurrence?.start_at ? formatDateTime(occurrence.start_at, i18n.language) : null;
    return {
      retreat_name: occurrence?.product_name || '',
      start_date: fd ? `${fd.date}${fd.time ? `, ${fd.time}` : ''}` : '',
      location: occurrence?.location ? `, ${occurrence.location}` : '',
    };
  }, [occurrence, i18n.language]);
  const dtEnd = useMemo(() => occurrence?.end_at ? formatDateTime(occurrence.end_at, i18n.language) : null, [occurrence, i18n.language]);

  // Prefer store slug (multi-store) over legacy org public_slug.
  const effectiveOrgSlug = occurrence?.org_store_slug || occurrence?.org_public_slug || null;
  const landingUrl = useMemo(() => {
    if (!effectiveOrgSlug || !occurrence?.slug) return null;
    return `${window.location.origin}/e/${effectiveOrgSlug}/${occurrence.slug}`;
  }, [effectiveOrgSlug, occurrence]);

  // Why is the landing unavailable?
  // The catalog filter ANDs three flags: occurrence.status + product.is_published + product.is_active.
  // If any of them is off, the event is hidden — we surface all of them so the
  // merchant doesn't see "Online" on one control and silent invisibility on the storefront.
  const landingBlockers = useMemo(() => {
    if (!occurrence) return [];
    const b = [];
    if (!effectiveOrgSlug) b.push(t('dashboards.event.diagnostic.noStoreSlug'));
    if (!occurrence.slug) b.push(t('dashboards.event.diagnostic.noEventSlug'));
    if (occurrence.status !== 'published') b.push(t('dashboards.event.diagnostic.statusNotPublished', { status: occurrence.status }));
    if (occurrence.product_is_published === false) b.push(t('dashboards.event.diagnostic.productDisabled'));
    if (occurrence.product_is_active === false) b.push(t('dashboards.event.diagnostic.productDeactivated'));
    return b;
  }, [occurrence, effectiveOrgSlug, t]);

  const address = useMemo(() => {
    if (!occurrence) return '';
    const parts = [occurrence.address, occurrence.postal_code, occurrence.city, occurrence.country].filter(Boolean);
    return parts.join(', ');
  }, [occurrence]);

  const capacity = occurrence?.capacity;
  const reservedSeats = occurrence?.reserved_seats || 0;
  const capacityProgress = capacity ? Math.min(100, Math.round((reservedSeats / capacity) * 100)) : 0;

  const copyLandingUrl = async () => {
    if (!landingUrl) return;
    try {
      await navigator.clipboard.writeText(landingUrl);
      toast.success(t('dashboards.event.toasts.linkCopied'));
    } catch {
      toast.error(t('dashboards.event.toasts.linkCopyError'));
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-sm text-gray-500">
        {t('dashboards.common.loading')}
      </div>
    );
  }

  if (error === 'not_found') {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
        <div className="max-w-md text-center bg-white rounded-xl border p-8">
          <h1 className="text-2xl font-bold mb-2">{t('dashboards.event.notFound')}</h1>
          <p className="text-gray-600 mb-4">{t('dashboards.event.notFoundDesc')}</p>
          <Link to="/products" className="inline-block rounded-md bg-gray-900 text-white px-4 py-2 text-sm">
            {t('dashboards.event.notFoundBackToProducts')}
          </Link>
        </div>
      </div>
    );
  }

  if (error || !occurrence) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
        <div className="text-sm text-red-700">{t('dashboards.event.errorPrefix', { detail: error })}</div>
      </div>
    );
  }

  const hero = occurrence.cover_image_url || occurrence.product_image_url;

  return (
    <div className="min-h-screen bg-gray-50 pb-20">
      {/* Hero */}
      <div className="relative bg-gray-900 text-white overflow-hidden">
        {hero && (
          <img src={hero} alt="" className="absolute inset-0 w-full h-full object-cover opacity-50" />
        )}
        <div className="relative max-w-4xl mx-auto px-4 sm:px-6 py-6 sm:py-10">
          <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
            <div className="min-w-0">
              <Link to="/products?type=event_ticket" className="inline-flex items-center gap-1 text-sm font-medium text-white/70 hover:text-white transition-colors">{t('dashboards.event.back')}</Link>
              <p className="text-[10px] uppercase tracking-widest opacity-70 mt-2">{t('dashboards.event.typeLabel')}</p>
              <h1 className="text-2xl sm:text-3xl font-bold mt-1">
                {occurrence.product_name || t('dashboards.event.fallbackName')}
              </h1>
              {dt && (
                <div className="mt-2 text-sm sm:text-base opacity-90 flex flex-wrap gap-3">
                  <span className="capitalize">{dt.date}</span>
                  <span>· {dt.time}{dtEnd ? ` – ${dtEnd.time}` : ''}</span>
                </div>
              )}
            </div>
            <div className="shrink-0 flex flex-col sm:items-end gap-2">
              <StatusBadge status={occurrence.status || 'draft'} />
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-5 sm:py-8 space-y-5">
        {showCreatedBanner && (
          <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-emerald-900">
              🎉 {t('dashboards.event.createdBanner.text', {
                defaultValue: 'Ritiro creato! Ora costruisci la pagina di vendita: programma giorno per giorno, galleria foto, cosa è incluso e FAQ.',
              })}
            </p>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => {
                  // niente behavior:'smooth': su alcuni browser lo scroll
                  // animato viene ignorato/cancellato — il salto secco
                  // funziona ovunque
                  document.getElementById('pagina-di-vendita')
                    ?.scrollIntoView({ block: 'start' });
                }}
                className="rounded-md bg-emerald-700 text-white px-3 py-1.5 text-xs font-semibold hover:bg-emerald-800"
              >
                {t('dashboards.event.createdBanner.cta', {
                  defaultValue: 'Aggiungi il programma →',
                })}
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowCreatedBanner(false);
                  searchParams.delete('creato');
                  setSearchParams(searchParams, { replace: true });
                }}
                className="text-emerald-700 hover:text-emerald-900 text-sm px-1"
                aria-label="Chiudi"
              >×</button>
            </div>
          </div>
        )}
        {/* Diagnostic banner — shown when landing or store visibility is blocked */}
        {/* Fase 2 S2 — Incassi in cima: la prima cosa che l'operatore guarda */}
        <PaymentsCard occurrenceId={occurrenceId} />

        {/* Fase 3 — editor contenuti pagina di vendita */}
        <div id="pagina-di-vendita">
          <RetreatContentEditor occurrenceId={occurrenceId} occurrence={occurrence} />
        </div>

        {landingBlockers.length > 0 && (
          <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3">
            <p className="text-xs font-semibold text-amber-900 mb-1">{t('dashboards.event.notVisibleWarning')}</p>
            <ul className="text-xs text-amber-800 space-y-0.5 list-disc list-inside">
              {landingBlockers.map((b, i) => <li key={i}>{b}</li>)}
            </ul>
          </div>
        )}

        {/* Stato evento — dedicated, prominent status control */}
        <div className="rounded-xl border border-gray-200 bg-white px-5 py-4">
          <div className="flex items-center justify-between gap-3">
            <div className="min-w-0">
              <h2 className="text-sm font-semibold text-gray-900">{t('dashboards.event.statusTitle')}</h2>
              <p className="text-xs text-gray-500 mt-0.5">
                {occurrence.status === 'published'
                  ? t('dashboards.event.statusOnlineDesc')
                  : occurrence.status === 'closed'
                    ? t('dashboards.event.statusClosedDesc')
                    : occurrence.status === 'cancelled'
                      ? t('dashboards.event.statusCancelledDesc')
                      : t('dashboards.event.statusOfflineDesc')}
              </p>
            </div>
            <div className="relative inline-flex shrink-0">
              <select
                value={occurrence.status || 'draft'}
                onChange={async (e) => {
                  const next = e.target.value;
                  const prevStatus = occurrence.status;
                  const prevProductPublished = occurrence?.product_is_published;
                  // Optimistic update for instant feedback
                  setOccurrence(prev => prev ? { ...prev, status: next } : prev);
                  setOccurrenceForm(f => ({ ...f, status: next }));
                  try {
                    await eventOccurrencesAPI.update(occurrenceId, { status: next });
                    // Auto-repair: the storefront catalog filter requires both
                    // occurrence.status == 'published' AND product.is_published.
                    // When the merchant sets the occurrence to published but the
                    // product is still draft (from an unchecked "Pubblica subito"
                    // in the wizard, or a manual disable), flip the product too
                    // so the event actually shows up. Matches the diagnostic
                    // blocker message that promises this behaviour.
                    if (next === 'published' && occurrence?.product_id && prevProductPublished === false) {
                      try {
                        await productsAPI.update(occurrence.product_id, { is_published: true });
                        setOccurrence(prev => prev ? { ...prev, product_is_published: true } : prev);
                      } catch {
                        // Non-blocking — the occurrence update already succeeded.
                        // The diagnostic banner will keep surfacing the issue.
                      }
                    }
                    toast.success(t('dashboards.event.toasts.statusUpdated'));
                  } catch {
                    // Roll back on failure
                    setOccurrence(prev => prev ? { ...prev, status: prevStatus } : prev);
                    setOccurrenceForm(f => ({ ...f, status: prevStatus }));
                    toast.error(t('dashboards.event.toasts.statusError'));
                  }
                }}
                className={`rounded-full pl-4 pr-8 py-1.5 text-sm font-semibold border-0 cursor-pointer appearance-none focus:outline-none focus:ring-2 focus:ring-gray-900/10 ${
                  { draft: 'bg-gray-100 text-gray-700', published: 'bg-green-100 text-green-900', closed: 'bg-amber-100 text-amber-900', cancelled: 'bg-red-100 text-red-900' }[occurrence.status] || 'bg-gray-100 text-gray-700'
                }`}
              >
                <option value="draft">{t('dashboards.event.statusBadge.draft')}</option>
                <option value="published">{t('dashboards.event.statusBadge.published')}</option>
                <option value="closed">{t('dashboards.event.statusBadge.closed')}</option>
                <option value="cancelled">{t('dashboards.event.statusBadge.cancelled')}</option>
              </select>
              <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-[10px] opacity-60">▾</span>
            </div>
          </div>
        </div>

        {/* F1 Onda 8 — Email partecipanti delivery status. Shown only for
            occurrences whose product has the attendee_details flag on AND
            that have at least one target holder (guest with own email). */}
        {occurrence.product_metadata?.requires_attendee_details && stats.delivery_targets > 0 && (
          <div className="rounded-xl border border-gray-200 bg-white px-5 py-4">
            <div className="flex items-center justify-between gap-3">
              <div className="min-w-0">
                <h2 className="text-sm font-semibold text-gray-900">{t('dashboards.event.emailDelivery.title')}</h2>
                <p className="text-xs text-gray-500 mt-0.5">
                  {stats.delivery_sent} / {stats.delivery_targets} {t('dashboards.event.emailDelivery.sent')}
                  {stats.delivery_pending > 0 && ` · ${stats.delivery_pending} ${t('dashboards.event.emailDelivery.pending')}`}
                  {stats.delivery_unsent > 0 && ` · ${stats.delivery_unsent} ${t('dashboards.event.emailDelivery.failed')}`}
                </p>
                <div className="mt-2 h-1.5 bg-gray-100 rounded-full overflow-hidden max-w-xs">
                  <div
                    className="h-full bg-green-500 transition-all"
                    style={{ width: `${Math.round((stats.delivery_sent / Math.max(1, stats.delivery_targets)) * 100)}%` }}
                  />
                </div>
              </div>
              <button
                type="button"
                disabled={resendingAll}
                onClick={async () => {
                  setResendingAll(true);
                  try {
                    const res = await ticketsAPI.resendIndividualForOccurrence(occurrence.id);
                    toast.success(`${res.data?.sent ?? 0} ${t('dashboards.event.emailDelivery.sent')}`);
                    // Refresh stats to reflect updated delivery_status
                    const s = await ticketsAPI.stats(occurrence.id);
                    setStats(s.data);
                  } catch {
                    toast.error(t('dashboards.event.toasts.emailResendError'));
                  } finally { setResendingAll(false); }
                }}
                className="shrink-0 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-xs font-semibold text-gray-900 hover:border-gray-900 disabled:opacity-50"
              >
                {resendingAll ? t('dashboards.event.emailDelivery.resending') : t('dashboards.event.emailDelivery.resendBtn')}
              </button>
            </div>
          </div>
        )}

        {/* Action bar */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
          {landingUrl && occurrence.status === 'published' ? (
            <a
              href={landingUrl} target="_blank" rel="noopener noreferrer"
              className="rounded-xl border border-gray-300 bg-white px-4 py-3 text-sm font-semibold text-gray-900 hover:border-gray-900 text-center"
            >
              {t('dashboards.event.actionBar.landingPreview')}
            </a>
          ) : (
            <div className="rounded-xl border border-dashed border-gray-300 bg-gray-50 px-4 py-3 text-sm text-gray-500 text-center">
              {t('dashboards.event.actionBar.landingUnavailable')}
              {landingUrl && <p className="text-[11px] mt-0.5 font-mono break-all text-gray-400">{landingUrl}</p>}
            </div>
          )}
          <button
            type="button" onClick={copyLandingUrl}
            disabled={!landingUrl}
            className="rounded-xl border border-gray-300 bg-white px-4 py-3 text-sm font-semibold text-gray-900 hover:border-gray-900 disabled:opacity-50"
          >
            {t('dashboards.event.actionBar.landingCopy')}
          </button>
          <Link
            to={`/events/${occurrence.id}/check-in`}
            className="rounded-xl bg-gray-900 text-white px-4 py-3 text-sm font-semibold text-center hover:bg-gray-800"
          >
            {t('dashboards.event.actionBar.checkInOpen')}
          </Link>
        </div>

        {/* Secondary action bar (G3 + G4 + E5) */}
        <div className="flex flex-wrap gap-2">
          {/* E5: global edit shortcut */}
          <button
            type="button"
            onClick={() => {
              setEditProductOpen(true);
              window.scrollTo({ top: 0, behavior: 'smooth' });
            }}
            className="inline-flex items-center gap-1.5 rounded-md border border-gray-900 bg-white px-3 py-1.5 text-xs font-semibold text-gray-900 hover:bg-gray-900 hover:text-white"
          >
            {t('dashboards.event.actionBar.editEvent')}
          </button>
          <button
            type="button"
            onClick={handleExportCsv}
            disabled={exportingCsv || stats.issued === 0}
            className="inline-flex items-center gap-1.5 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 hover:border-gray-900 disabled:opacity-50"
          >
            {exportingCsv ? t('dashboards.event.actionBar.exportingCsv') : t('dashboards.event.actionBar.exportCsv')}
          </button>
          {/* G4: link to the ticketing management center */}
          <Link
            to={`/events/${occurrence.id}/tickets`}
            className="inline-flex items-center gap-1.5 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 hover:border-gray-900"
          >
            {t('dashboards.event.actionBar.ticketsManage')}
          </Link>
          {/* G6: Duplicate — clone product/venue/tiers into a new event */}
          <button
            type="button"
            onClick={handleDuplicate}
            disabled={duplicating}
            className="inline-flex items-center gap-1.5 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 hover:border-gray-900 disabled:opacity-50"
          >
            {duplicating ? t('dashboards.event.actionBar.duplicateLoading') : t('dashboards.event.actionBar.duplicateBtn')}
          </button>
          {/* G6: Archive / unarchive */}
          <button
            type="button"
            onClick={handleToggleArchive}
            disabled={togglingArchive}
            className={`inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-xs font-medium disabled:opacity-50 ${
              occurrence.is_archived
                ? 'border-gray-300 bg-white text-gray-700 hover:border-gray-900'
                : 'border-gray-300 bg-white text-gray-700 hover:border-gray-900'
            }`}
          >
            {togglingArchive ? t('dashboards.event.actionBar.archivingLoading') : occurrence.is_archived ? t('dashboards.event.actionBar.unarchive') : t('dashboards.event.actionBar.archive')}
          </button>
        </div>

        {/* G6: archive banner when currently archived */}
        {occurrence.is_archived && (
          <div className="rounded-md bg-gray-100 border border-gray-300 px-3 py-2 text-xs text-gray-700">
            {t('dashboards.event.actionBar.archiveBanner')}
          </div>
        )}

        {/* ── E1: Prodotto edit panel ─────────────────────────────── */}
        <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
          <button
            type="button"
            onClick={() => {
              const next = !editProductOpen;
              setEditProductOpen(next);
              if (next) { searchParams.set('edit', 'product'); }
              else { searchParams.delete('edit'); }
              setSearchParams(searchParams, { replace: true });
            }}
            className="w-full flex items-center justify-between px-5 py-3 text-left hover:bg-gray-50"
          >
            <span className="text-sm font-semibold text-gray-900">{t('dashboards.event.product.title')}</span>
            <span className="text-gray-400 text-xs">{editProductOpen ? '▲' : '▼'}</span>
          </button>

          {editProductOpen && (
            <div className="border-t border-gray-100 px-5 py-4 space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="sm:col-span-2">
                <MultiLangSection fields={[
                  { key: 'name', label: t('dashboards.event.product.nameLabel'), it: productForm.name,
                    value: trName, onChange: setTrName, input: true, maxLength: 255 },
                  { key: 'description', label: t('dashboards.event.product.shortDescLabel'), it: productForm.description,
                    value: trDescription, onChange: setTrDescription, rows: 2, maxLength: 2000 },
                ]}>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">{t('dashboards.event.product.nameLabel')}</label>
                  <input type="text" value={productForm.name}
                    onChange={e => setProductForm(f => ({ ...f, name: e.target.value }))}
                    maxLength={255}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">{t('dashboards.event.product.shortDescLabel')}</label>
                  <textarea value={productForm.description}
                    onChange={e => setProductForm(f => ({ ...f, description: e.target.value }))}
                    rows={2} maxLength={2000}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none resize-none"
                  />
                </div>
                </MultiLangSection>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">{t('dashboards.event.product.imageLabel')}</label>
                  {/* File upload */}
                  <label className={`flex items-center gap-2 cursor-pointer rounded-md border border-dashed border-gray-300 px-3 py-2 text-sm text-gray-600 hover:border-gray-900 transition-colors ${uploadingImage ? 'opacity-50 pointer-events-none' : ''}`}>
                    <span>{uploadingImage ? t('dashboards.event.product.uploading') : t('dashboards.event.product.uploadLabel')}</span>
                    <input
                      type="file"
                      accept=".jpg,.jpeg,.png,.webp"
                      className="hidden"
                      disabled={uploadingImage}
                      onChange={async e => {
                        const file = e.target.files?.[0];
                        if (!file || !occurrence?.product_id) return;
                        setUploadingImage(true);
                        try {
                          const res = await productsAPI.uploadImage(occurrence.product_id, file);
                          const url = res.data?.image_url;
                          setProductForm(f => ({ ...f, image_url: url }));
                          setOccurrence(prev => prev ? { ...prev, product_image_url: url } : prev);
                          toast.success(t('dashboards.event.toasts.imageUploaded'));
                        } catch (err) {
                          toast.error(err?.response?.data?.detail || t('dashboards.event.toasts.imageUploadError'));
                        } finally {
                          setUploadingImage(false);
                          e.target.value = '';
                        }
                      }}
                    />
                  </label>
                  {/* URL fallback */}
                  <input type="url" value={productForm.image_url}
                    onChange={e => setProductForm(f => ({ ...f, image_url: e.target.value }))}
                    placeholder={t('dashboards.event.product.imageUrlPlaceholder')}
                    className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
                  />
                  {productForm.image_url && (
                    <img src={productForm.image_url} alt="" className="mt-2 h-16 w-full object-cover rounded-md border" />
                  )}
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">{t('dashboards.event.product.priceLabel')}</label>
                  <input type="number" step="0.01" min="0" value={productForm.unit_price}
                    onChange={e => setProductForm(f => ({ ...f, unit_price: e.target.value }))}
                    placeholder={t('dashboards.event.product.pricePlaceholder')}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
                  />
                  <p className="text-[11px] text-gray-400 mt-1">{t('dashboards.event.product.priceHint')}</p>
                </div>
              </div>

              <div className="flex flex-wrap gap-3">
                <div>
                  <p className="text-xs font-medium text-gray-700 mb-1.5">{t('dashboards.event.product.modeLabel')}</p>
                  <div className="flex gap-1.5">
                    {[{ v: 'direct', labelKey: 'dashboards.event.product.modeDirect' }, { v: 'request', labelKey: 'dashboards.event.product.modeRequest' }].map(opt => (
                      <button key={opt.v} type="button"
                        onClick={() => setProductForm(f => ({ ...f, transaction_mode: opt.v }))}
                        className={`rounded-full px-3 py-1 text-xs font-semibold border transition-all ${
                          productForm.transaction_mode === opt.v
                            ? 'bg-gray-900 text-white border-gray-900'
                            : 'bg-white text-gray-700 border-gray-300 hover:border-gray-900'
                        }`}
                      >{t(opt.labelKey)}</button>
                    ))}
                  </div>
                </div>
              </div>

              {/* F1 Onda 8 — attendee details policy */}
              <label className="flex items-start gap-3 cursor-pointer rounded-lg border border-gray-200 bg-gray-50 p-3">
                <input
                  type="checkbox"
                  checked={productForm.requires_attendee_details}
                  onChange={e => setProductForm(f => ({ ...f, requires_attendee_details: e.target.checked }))}
                  className="mt-0.5 h-4 w-4 rounded border-gray-300 text-gray-900 focus:ring-gray-900"
                />
                <div className="flex-1">
                  <span className="block text-sm font-semibold text-gray-900">
                    {t('dashboards.event.product.requireDetailsTitle')}
                  </span>
                  <span className="block text-xs text-gray-500 mt-0.5">
                    {productForm.requires_attendee_details
                      ? t('dashboards.event.product.requireDetailsDescOn')
                      : t('dashboards.event.product.requireDetailsDescOff')}
                  </span>
                </div>
              </label>

              {/* F2 Onda 9 — required-ness for email/phone (solo se F1 attivo) */}
              {productForm.requires_attendee_details && (
                <div className="rounded-lg border border-gray-200 bg-white p-3 space-y-2">
                  <p className="text-xs font-semibold text-gray-700 uppercase tracking-wide">
                    {t('dashboards.event.product.baseFieldsHeading')}
                  </p>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-900">{t('dashboards.event.tickets.nameField')}</span>
                    <span className="text-xs text-gray-500">{t('dashboards.event.product.alwaysRequired')}</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-900">{t('dashboards.event.tickets.emailField')}</span>
                    <label className="flex items-center gap-2 text-xs cursor-pointer">
                      <input
                        type="checkbox"
                        checked={productForm.require_attendee_email}
                        onChange={e => setProductForm(f => ({ ...f, require_attendee_email: e.target.checked }))}
                        className="rounded border-gray-300"
                      />
                      <span>{t('dashboards.event.product.emailRequired')}</span>
                    </label>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-900">{t('dashboards.event.tickets.phoneField')}</span>
                    <label className="flex items-center gap-2 text-xs cursor-pointer">
                      <input
                        type="checkbox"
                        checked={productForm.require_attendee_phone}
                        onChange={e => setProductForm(f => ({ ...f, require_attendee_phone: e.target.checked }))}
                        className="rounded border-gray-300"
                      />
                      <span>{t('dashboards.event.product.phoneRequired')}</span>
                    </label>
                  </div>
                  {!productForm.require_attendee_email && (
                    <p className="text-[11px] text-amber-700 bg-amber-50 border border-amber-200 rounded-md px-2 py-1">
                      {t('dashboards.event.product.noEmailWarning')}
                    </p>
                  )}
                </div>
              )}

              {/* F2 Onda 9 — attendee custom fields (solo se F1 attivo) */}
              {productForm.requires_attendee_details && (
                <FieldEditorList
                  fields={productForm.attendee_fields || []}
                  onChange={(next) => setProductForm(f => ({ ...f, attendee_fields: next }))}
                  title={t('dashboards.event.product.attendeeFieldsTitle')}
                  subtitle={t('dashboards.event.product.attendeeFieldsSubtitle')}
                  emptyHint={t('wizards.event.tickets.attendeeFieldsEmpty')}
                />
              )}

              {/* F2 Onda 9 — order-level custom fields (sempre visibile) */}
              <FieldEditorList
                fields={productForm.order_fields || []}
                onChange={(next) => setProductForm(f => ({ ...f, order_fields: next }))}
                title={t('wizards.event.tickets.orderFieldsTitle')}
                subtitle={t('wizards.event.tickets.orderFieldsSubtitle')}
                emptyHint={t('wizards.event.tickets.orderFieldsEmpty')}
              />

              {/* F4 Onda 11 — per-event Terms & Conditions override */}
              <div className="rounded-lg border border-gray-200 bg-white p-3 space-y-2">
                <p className="text-sm font-semibold text-gray-900">{t('wizards.event.publish.termsTitle')}</p>
                <p className="text-[11px] text-gray-500">
                  {t('wizards.event.publish.termsDesc')}
                </p>
                <textarea
                  value={productForm.terms_content || ''}
                  onChange={e => setProductForm(f => ({ ...f, terms_content: e.target.value }))}
                  rows={6} maxLength={20000}
                  placeholder={t('wizards.event.publish.termsPlaceholder')}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-xs font-mono focus:border-gray-900 focus:outline-none resize-y"
                />
              </div>

              {/* W1.S5/Phase 2.9 — Cost composition (edit). */}
              <div className="rounded-lg border border-gray-200 bg-gray-50 p-3 space-y-2">
                <div>
                  <span className="text-sm font-medium text-gray-900">
                    {t('product_cost:section.title', 'Costo del prodotto')}
                  </span>
                  <p className="text-xs text-gray-500 mt-0.5">
                    {t('product_cost:section.subtitle', 'Definisci come calcolare il margine per questo prodotto.')}
                  </p>
                </div>
                <CostSourceEditor
                  value={productForm.cost_source}
                  onChange={(next) => setProductForm(f => ({ ...f, cost_source: next }))}
                />
              </div>

              <div className="flex justify-end">
                <button type="button" disabled={savingProduct || !productForm.name.trim()}
                  onClick={async () => {
                    setSavingProduct(true);
                    try {
                      // Merge: preserve any existing metadata keys (rental_unit,
                      // service_notes, etc.) while updating attendees policy.
                      const existingMeta = occurrence?.product_metadata || {};
                      const upd = {
                        name: productForm.name.trim(),
                        description: productForm.description?.trim() || null,
                        translations: buildTranslationsPayload(),
                        image_url: productForm.image_url?.trim() || null,
                        unit_price: productForm.unit_price !== '' ? Number(productForm.unit_price) : null,
                        transaction_mode: productForm.transaction_mode,
                        is_published: true,
                        metadata: {
                          ...existingMeta,
                          requires_attendee_details: !!productForm.requires_attendee_details,
                          // F2 Onda 9
                          require_attendee_email: !!productForm.require_attendee_email,
                          require_attendee_phone: !!productForm.require_attendee_phone,
                          attendee_fields: pruneFieldConfigs(productForm.attendee_fields),
                          order_fields: pruneFieldConfigs(productForm.order_fields),
                          // F4 Onda 11 — per-event T&C override
                          terms_content: productForm.terms_content?.trim() || null,
                        },
                        // W1.S5/Phase 2.9 — additive cost composition.
                        cost_source: productForm.cost_source || null,
                      };
                      await productsAPI.update(occurrence.product_id, upd);
                      setOccurrence(prev => prev ? {
                        ...prev,
                        product_name: upd.name,
                        product_image_url: upd.image_url,
                        product_is_published: true,
                        product_metadata: upd.metadata,
                        product_cost_source: upd.cost_source,
                      } : prev);
                      toast.success(t('dashboards.event.toasts.productUpdated'));
                    } catch { toast.error(t('dashboards.event.toasts.productSaveError')); }
                    finally { setSavingProduct(false); }
                  }}
                  className="rounded-md bg-gray-900 text-white px-4 py-2 text-sm font-semibold hover:bg-gray-800 disabled:opacity-50"
                >{savingProduct ? t('dashboards.common.saving') : t('dashboards.event.product.saveBtn')}</button>
              </div>
            </div>
          )}
        </div>

        {/* ── E2: Occorrenza (Quando e dove) edit panel ──────────── */}
        <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
          <button type="button"
            onClick={() => setEditOccurrenceOpen(o => !o)}
            className="w-full flex items-center justify-between px-5 py-3 text-left hover:bg-gray-50"
          >
            <span className="text-sm font-semibold text-gray-900">{t('dashboards.event.occurrence.title')}</span>
            <span className="text-gray-400 text-xs">{editOccurrenceOpen ? '▲' : '▼'}</span>
          </button>

          {editOccurrenceOpen && (
            <div className="border-t border-gray-100 px-5 py-4 space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">{t('wizards.event.where.startLabel')}</label>
                  <input type="datetime-local" value={occurrenceForm.start_at}
                    onChange={e => setOccurrenceForm(f => ({ ...f, start_at: e.target.value }))}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">{t('wizards.event.where.endLabel')}</label>
                  <input type="datetime-local" value={occurrenceForm.end_at}
                    onChange={e => setOccurrenceForm(f => ({ ...f, end_at: e.target.value }))}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">{t('wizards.event.where.capacityLabel')}</label>
                  <input type="number" min="1" value={occurrenceForm.capacity}
                    onChange={e => setOccurrenceForm(f => ({ ...f, capacity: e.target.value }))}
                    placeholder={t('dashboards.event.publish.summaryCapacityUnlimited')}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">{t('dashboards.event.occurrence.statusLabel')}</label>
                  <select value={occurrenceForm.status}
                    onChange={e => setOccurrenceForm(f => ({ ...f, status: e.target.value }))}
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm bg-white focus:border-gray-900 focus:outline-none"
                  >
                    <option value="draft">{t('dashboards.event.statusBadge.draft')}</option>
                    <option value="published">{t('dashboards.event.statusBadge.published')}</option>
                    <option value="closed">{t('dashboards.event.statusBadge.closed')}</option>
                    <option value="cancelled">{t('dashboards.event.statusBadge.cancelled')}</option>
                  </select>
                </div>
              </div>

              <div>
                <p className="text-xs font-semibold text-gray-700 mb-2">{t('dashboards.event.occurrence.venueHeader')}</p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="sm:col-span-2">
                    <label className="block text-xs font-medium text-gray-700 mb-1">{t('wizards.event.where.venueNameLabel')}</label>
                    <input type="text" value={occurrenceForm.venue_name}
                      onChange={e => setOccurrenceForm(f => ({ ...f, venue_name: e.target.value }))}
                      placeholder={t('dashboards.event.occurrence.venuePlaceholder')}
                      className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
                    />
                  </div>
                  <div className="sm:col-span-2">
                    <label className="block text-xs font-medium text-gray-700 mb-1">{t('wizards.event.where.addressLabel')}</label>
                    <input type="text" value={occurrenceForm.address}
                      onChange={e => setOccurrenceForm(f => ({ ...f, address: e.target.value }))}
                      className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">{t('wizards.event.where.cityLabel')}</label>
                    <input type="text" value={occurrenceForm.city}
                      onChange={e => setOccurrenceForm(f => ({ ...f, city: e.target.value }))}
                      className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">{t('wizards.event.where.postalCodeLabel')}</label>
                    <input type="text" value={occurrenceForm.postal_code}
                      onChange={e => setOccurrenceForm(f => ({ ...f, postal_code: e.target.value }))}
                      className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">{t('wizards.event.where.countryLabel')}</label>
                    <input type="text" value={occurrenceForm.country} maxLength={2}
                      onChange={e => setOccurrenceForm(f => ({ ...f, country: e.target.value.toUpperCase() }))}
                      placeholder={t('dashboards.event.occurrence.countryDefault')}
                      className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">{t('dashboards.event.occurrence.coverLabel')}</label>
                    <label className={`flex items-center gap-2 cursor-pointer rounded-md border border-dashed border-gray-300 px-3 py-2 text-sm text-gray-600 hover:border-gray-900 transition-colors ${uploadingImage ? 'opacity-50 pointer-events-none' : ''}`}>
                      <span>{uploadingImage ? t('dashboards.event.product.uploading') : `📁 ${t('wizards.event.where.coverFileLabel')}`}</span>
                      <input
                        type="file"
                        accept=".jpg,.jpeg,.png,.webp"
                        className="hidden"
                        disabled={uploadingImage}
                        onChange={async e => {
                          const file = e.target.files?.[0];
                          if (!file) return;
                          setUploadingImage(true);
                          try {
                            const res = await eventOccurrencesAPI.uploadCoverImage(occurrenceId, file);
                            const url = res.data?.cover_image_url;
                            setOccurrenceForm(f => ({ ...f, cover_image_url: url }));
                            setOccurrence(prev => prev ? { ...prev, cover_image_url: url } : prev);
                            toast.success(t('dashboards.event.occurrence.coverUploaded'));
                          } catch (err) {
                            toast.error(err?.response?.data?.detail || t('dashboards.event.toasts.imageUploadError'));
                          } finally {
                            setUploadingImage(false);
                            e.target.value = '';
                          }
                        }}
                      />
                    </label>
                    <input type="url" value={occurrenceForm.cover_image_url}
                      onChange={e => setOccurrenceForm(f => ({ ...f, cover_image_url: e.target.value }))}
                      placeholder={t('dashboards.event.occurrence.coverUrlPlaceholder')}
                      className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
                    />
                    {occurrenceForm.cover_image_url && (
                      <img src={occurrenceForm.cover_image_url} alt="" className="mt-2 h-16 w-full object-cover rounded-md border" />
                    )}
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">{t('wizards.event.where.latitudeLabel')}</label>
                    <input type="number" step="any" value={occurrenceForm.latitude}
                      onChange={e => setOccurrenceForm(f => ({ ...f, latitude: e.target.value }))}
                      placeholder={t('dashboards.event.occurrence.latitudePlaceholder')}
                      className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">{t('wizards.event.where.longitudeLabel')}</label>
                    <input type="number" step="any" value={occurrenceForm.longitude}
                      onChange={e => setOccurrenceForm(f => ({ ...f, longitude: e.target.value }))}
                      placeholder={t('dashboards.event.occurrence.longitudePlaceholder')}
                      className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
                    />
                  </div>
                </div>
              </div>

              {/* Slug + landing URL */}
              <div>
                <p className="text-xs font-semibold text-gray-700 mb-2">{t('dashboards.event.occurrence.publicLandingHeader')}</p>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  {t('dashboards.event.occurrence.slugLabel')} <span className="text-gray-400 font-normal">({t('dashboards.event.occurrence.slugExample')})</span>
                </label>
                <input type="text" value={occurrenceForm.slug}
                  onChange={e => setOccurrenceForm(f => ({ ...f, slug: e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '-').replace(/-+/g, '-') }))}
                  placeholder={t('dashboards.event.occurrence.slugPlaceholder')}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none"
                />
                {occurrenceForm.slug && effectiveOrgSlug && (
                  <p className="text-[11px] text-green-700 mt-1 font-medium break-all">
                    {t('dashboards.event.occurrence.landingAvailable')}{' '}
                    <span className="underline">
                      {window.location.origin}/e/{effectiveOrgSlug}/{occurrenceForm.slug}
                    </span>
                  </p>
                )}
                {occurrenceForm.slug && !effectiveOrgSlug && (
                  <p className="text-[11px] text-amber-700 mt-1">
                    {t('dashboards.event.occurrence.publishStoreFirst')}
                  </p>
                )}
                {!occurrenceForm.slug && (
                  <p className="text-[11px] text-gray-400 mt-1">{t('dashboards.event.occurrence.slugMissingHint')}</p>
                )}
              </div>

              <div className="flex justify-end">
                <button type="button" disabled={savingOccurrence || !occurrenceForm.start_at}
                  onClick={async () => {
                    setSavingOccurrence(true);
                    try {
                      const upd = {
                        start_at: occurrenceForm.start_at,
                        end_at: occurrenceForm.end_at || null,
                        capacity: occurrenceForm.capacity !== '' ? Number(occurrenceForm.capacity) : null,
                        status: occurrenceForm.status,
                        venue_name: occurrenceForm.venue_name?.trim() || null,
                        address: occurrenceForm.address?.trim() || null,
                        city: occurrenceForm.city?.trim() || null,
                        postal_code: occurrenceForm.postal_code?.trim() || null,
                        country: occurrenceForm.country?.trim() || null,
                        cover_image_url: occurrenceForm.cover_image_url?.trim() || null,
                        latitude: occurrenceForm.latitude !== '' ? Number(occurrenceForm.latitude) : null,
                        longitude: occurrenceForm.longitude !== '' ? Number(occurrenceForm.longitude) : null,
                        slug: occurrenceForm.slug?.trim() || null,
                      };
                      await eventOccurrencesAPI.update(occurrenceId, upd);
                      setOccurrence(prev => prev ? { ...prev, ...upd } : prev);
                      toast.success(t('dashboards.event.toasts.occurrenceUpdated'));
                    } catch { toast.error(t('dashboards.event.toasts.productSaveError')); }
                    finally { setSavingOccurrence(false); }
                  }}
                  className="rounded-md bg-gray-900 text-white px-4 py-2 text-sm font-semibold hover:bg-gray-800 disabled:opacity-50"
                >{savingOccurrence ? t('dashboards.common.saving') : t('dashboards.event.occurrence.saveBtn')}</button>
              </div>
            </div>
          )}
        </div>

        {/* G3: Revenue card */}
        {analytics && (analytics.revenue_total > 0 || analytics.tickets_sold_total > 0) ? (
          <div className="rounded-xl border border-gray-200 bg-white p-5">
            <div className="flex items-start justify-between gap-4 flex-wrap">
              <div className="min-w-0">
                <p className="text-xs uppercase tracking-wide text-gray-500">{t('dashboards.event.revenue.title')}</p>
                <p className="text-3xl font-bold text-gray-900 tabular-nums mt-1">
                  {formatPrice(analytics.revenue_total, analytics.currency)}
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  {t('dashboards.event.revenue.fromTickets', { count: analytics.tickets_sold_total })}
                </p>
              </div>
            </div>

            {/* Per-tier breakdown */}
            {analytics.revenue_by_tier.length > 0 && (
              <div className="mt-4 space-y-2">
                <p className="text-xs font-semibold text-gray-700 uppercase tracking-wide">{t('dashboards.event.revenue.perTier')}</p>
                {analytics.revenue_by_tier.map((row, i) => {
                  const pct = analytics.revenue_total > 0
                    ? Math.round((row.revenue / analytics.revenue_total) * 100)
                    : 0;
                  return (
                    <div key={`${row.tier_id || 'mono'}-${i}`} className="text-sm">
                      <div className="flex justify-between items-baseline gap-2">
                        <span className="font-medium text-gray-900 truncate">
                          {row.tier_label || t('dashboards.event.revenue.basePrice')}
                        </span>
                        <span className="font-semibold text-gray-900 tabular-nums whitespace-nowrap">
                          {formatPrice(row.revenue, analytics.currency)}
                        </span>
                      </div>
                      <div className="flex justify-between items-center text-[11px] text-gray-500 mt-0.5">
                        <span>{row.tickets_sold} × {row.price != null ? formatPrice(row.price, analytics.currency) : '—'}</span>
                        <span className="tabular-nums">{pct}%</span>
                      </div>
                      <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden mt-1">
                        <div className="h-full bg-gray-900" style={{ width: `${pct}%` }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Sales timeline sparkline */}
            {analytics.sales_timeline.length > 0 && (
              <div className="mt-5">
                <p className="text-xs font-semibold text-gray-700 uppercase tracking-wide mb-2">
                  {t('dashboards.event.revenue.salesLast30')}
                </p>
                <MiniBars
                  height={64}
                  data={analytics.sales_timeline.map(d => ({ label: d.date, value: d.tickets_sold }))}
                  valueFormatter={(n) => `${n} · ${t('dashboards.event.history.comparedTickets')}`}
                />
                <div className="flex justify-between text-[10px] text-gray-500 mt-1">
                  <span>{analytics.sales_timeline[0]?.date}</span>
                  <span>{analytics.sales_timeline[analytics.sales_timeline.length - 1]?.date}</span>
                </div>
              </div>
            )}
          </div>
        ) : null}

{/* capacity card removed — merged into Ingresso card below */}

        {/* ── E4: Tipologie biglietto CRUD inline ─────────────── */}
        <div className="rounded-xl border border-gray-200 bg-white p-5">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-base font-semibold text-gray-900">{t('dashboards.event.tiers.title')}</h2>
            <button
              type="button"
              onClick={() => { setShowAddTier(true); setTierEditId(null); }}
              className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-xs font-semibold text-gray-700 hover:border-gray-900"
            >{t('dashboards.event.tiers.addBtn')}</button>
          </div>

          {tiers.length === 0 && !showAddTier && (
            <p className="text-sm text-gray-400 text-center py-4">
              {t('dashboards.event.tiers.emptyHint')}
            </p>
          )}

          <div className="space-y-2">
            {tiers.map(tier => {
              const pct = tier.capacity ? Math.min(100, Math.round((tier.reserved_seats || 0) / tier.capacity * 100)) : 0;
              const soldOut = tier.capacity && (tier.reserved_seats || 0) >= tier.capacity;
              const isEditing = tierEditId === tier.id;
              const form = tierForms[tier.id] || {};

              return (
                <div key={tier.id} className={`rounded-lg border p-3 ${!tier.is_active ? 'border-gray-200 bg-gray-50 opacity-75' : 'border-gray-200'}`}>
                  {!isEditing ? (
                    // Read-only row
                    <div>
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2 flex-wrap">
                            <p className="font-semibold text-gray-900">{tier.label}</p>
                            {!tier.is_active && (
                              <span className="text-[10px] uppercase bg-gray-200 text-gray-700 px-1.5 py-0.5 rounded">{t('dashboards.event.tiers.disabled')}</span>
                            )}
                            {soldOut && (
                              <span className="text-[10px] uppercase bg-red-100 text-red-700 px-1.5 py-0.5 rounded font-semibold">{t('dashboards.event.tiers.depleted')}</span>
                            )}
                          </div>
                          {tier.description && <p className="text-xs text-gray-600 mt-0.5">{tier.description}</p>}
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          <div className="text-right">
                            <p className="text-base font-bold text-gray-900 whitespace-nowrap">{formatPrice(tier.price)}</p>
                            <p className="text-[11px] text-gray-500 tabular-nums mt-0.5">
                              {tier.reserved_seats || 0}{tier.capacity ? ` / ${tier.capacity}` : ''} {t('dashboards.event.tiers.soldCount')}
                            </p>
                          </div>
                          <button
                            type="button"
                            onClick={() => setTierEditId(tier.id)}
                            className="ml-1 rounded-md border border-gray-300 px-2 py-1 text-xs hover:border-gray-900"
                          >✏️</button>
                        </div>
                      </div>
                      {tier.capacity && (
                        <div className="mt-2 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                          <div
                            className={`h-full ${pct >= 90 ? 'bg-red-500' : pct >= 70 ? 'bg-amber-500' : 'bg-green-500'}`}
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      )}
                    </div>
                  ) : (
                    // Inline edit form
                    <div className="space-y-3">
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <div>
                          <label className="block text-xs font-medium text-gray-700 mb-1">{t('dashboards.event.tiers.labelLabel')}</label>
                          <input
                            type="text"
                            value={form.label || ''}
                            maxLength={80}
                            onChange={e => setTierForms(f => ({ ...f, [tier.id]: { ...f[tier.id], label: e.target.value } }))}
                            className="w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-gray-900 focus:outline-none"
                          />
                        </div>
                        <div>
                          <label className="block text-xs font-medium text-gray-700 mb-1">{t('dashboards.event.tiers.priceLabel')}</label>
                          <input
                            type="number" step="0.01" min="0"
                            value={form.price || ''}
                            onChange={e => setTierForms(f => ({ ...f, [tier.id]: { ...f[tier.id], price: e.target.value } }))}
                            className="w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-gray-900 focus:outline-none"
                          />
                        </div>
                        <div>
                          <label className="block text-xs font-medium text-gray-700 mb-1">{t('dashboards.event.tiers.capacityLabel')}</label>
                          <input
                            type="number" min="1"
                            value={form.capacity || ''}
                            onChange={e => setTierForms(f => ({ ...f, [tier.id]: { ...f[tier.id], capacity: e.target.value } }))}
                            className="w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-gray-900 focus:outline-none"
                          />
                        </div>
                        <div>
                          <label className="block text-xs font-medium text-gray-700 mb-1">{t('dashboards.event.tiers.activeToggle')}</label>
                          <button
                            type="button"
                            onClick={() => setTierForms(f => ({ ...f, [tier.id]: { ...f[tier.id], is_active: !f[tier.id]?.is_active } }))}
                            className={`rounded-full px-3 py-1 text-xs font-semibold border ${
                              form.is_active !== false
                                ? 'bg-green-600 text-white border-green-600'
                                : 'bg-white text-gray-700 border-gray-300 hover:border-gray-900'
                            }`}
                          >{form.is_active !== false ? t('dashboards.event.tiers.activeBadge') : t('dashboards.event.tiers.disabledBadge')}</button>
                        </div>
                        <div className="sm:col-span-2">
                          <label className="block text-xs font-medium text-gray-700 mb-1">{t('dashboards.event.tiers.descriptionLabel')}</label>
                          <input
                            type="text"
                            value={form.description || ''}
                            maxLength={500}
                            onChange={e => setTierForms(f => ({ ...f, [tier.id]: { ...f[tier.id], description: e.target.value } }))}
                            placeholder={t('dashboards.event.tiers.descriptionPlaceholder')}
                            className="w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-gray-900 focus:outline-none"
                          />
                        </div>
                      </div>
                      <div className="flex items-center justify-between gap-2">
                        <button
                          type="button"
                          disabled={deletingTierIds.has(tier.id)}
                          onClick={async () => {
                            if (!window.confirm(
                              (tier.reserved_seats || 0) > 0
                                ? t('dashboards.event.tiers.softDeleteWarning')
                                : t('dashboards.event.tiers.deleteConfirm')
                            )) return;
                            setDeletingTierIds(s => new Set([...s, tier.id]));
                            try {
                              await eventTicketTiersAPI.remove(occurrenceId, tier.id);
                              setTiers(prev => prev.filter(x => x.id !== tier.id));
                              setTierForms(f => { const n = { ...f }; delete n[tier.id]; return n; });
                              setTierEditId(null);
                              toast.success(t('dashboards.event.toasts.tierRemoved'));
                            } catch { toast.error(t('dashboards.event.toasts.tierRemoveError')); }
                            finally { setDeletingTierIds(s => { const n = new Set(s); n.delete(tier.id); return n; }); }
                          }}
                          className="rounded-md border border-red-300 text-red-700 px-3 py-1.5 text-xs font-medium hover:border-red-600 disabled:opacity-50"
                        >{deletingTierIds.has(tier.id) ? t('dashboards.event.tiers.removingBtn') : t('dashboards.event.tiers.removeBtn')}</button>

                        <div className="flex gap-2">
                          <button
                            type="button"
                            onClick={() => setTierEditId(null)}
                            className="rounded-md border border-gray-300 text-gray-700 px-3 py-1.5 text-xs font-medium hover:border-gray-900"
                          >{t('dashboards.event.tiers.cancelBtn')}</button>
                          <button
                            type="button"
                            disabled={savingTierIds.has(tier.id) || !form.label?.trim()}
                            onClick={async () => {
                              setSavingTierIds(s => new Set([...s, tier.id]));
                              try {
                                const upd = {
                                  label: form.label.trim(),
                                  price: form.price !== '' ? Number(form.price) : 0,
                                  capacity: form.capacity !== '' ? Number(form.capacity) : null,
                                  description: form.description?.trim() || null,
                                  is_active: form.is_active !== false,
                                };
                                const res = await eventTicketTiersAPI.update(occurrenceId, tier.id, upd);
                                const updated = res.data;
                                setTiers(prev => prev.map(x => x.id === tier.id ? { ...x, ...updated } : x));
                                setTierEditId(null);
                                toast.success(t('dashboards.event.toasts.tierUpdated'));
                              } catch { toast.error(t('dashboards.event.toasts.tierSaveError')); }
                              finally { setSavingTierIds(s => { const n = new Set(s); n.delete(tier.id); return n; }); }
                            }}
                            className="rounded-md bg-gray-900 text-white px-3 py-1.5 text-xs font-semibold hover:bg-gray-800 disabled:opacity-50"
                          >{savingTierIds.has(tier.id) ? t('dashboards.common.saving') : t('dashboards.event.tiers.saveBtn')}</button>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}

            {/* Add new tier form */}
            {showAddTier && (
              <div className="rounded-lg border-2 border-dashed border-gray-300 p-4 space-y-3">
                <p className="text-xs font-semibold text-gray-700 uppercase tracking-wide">{t('dashboards.event.tiers.newTitle')}</p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">{t('dashboards.event.tiers.labelLabel')}</label>
                    <input
                      type="text" maxLength={80}
                      value={newTierForm.label}
                      onChange={e => setNewTierForm(f => ({ ...f, label: e.target.value }))}
                      placeholder={t('dashboards.event.tiers.newLabelPlaceholder')}
                      className="w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-gray-900 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">{t('dashboards.event.tiers.priceLabel')}</label>
                    <input
                      type="number" step="0.01" min="0"
                      value={newTierForm.price}
                      onChange={e => setNewTierForm(f => ({ ...f, price: e.target.value }))}
                      placeholder={t('dashboards.event.tiers.newPricePlaceholder')}
                      className="w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-gray-900 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">{t('dashboards.event.tiers.capacityLabel')}</label>
                    <input
                      type="number" min="1"
                      value={newTierForm.capacity}
                      onChange={e => setNewTierForm(f => ({ ...f, capacity: e.target.value }))}
                      className="w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-gray-900 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">{t('dashboards.event.tiers.descriptionLabel')}</label>
                    <input
                      type="text" maxLength={500}
                      value={newTierForm.description}
                      onChange={e => setNewTierForm(f => ({ ...f, description: e.target.value }))}
                      placeholder={t('dashboards.event.tiers.newDescPlaceholder')}
                      className="w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-gray-900 focus:outline-none"
                    />
                  </div>
                </div>
                <div className="flex justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => { setShowAddTier(false); setNewTierForm({ label: '', price: '', capacity: '', description: '' }); }}
                    className="rounded-md border border-gray-300 text-gray-700 px-3 py-1.5 text-xs font-medium hover:border-gray-900"
                  >{t('dashboards.event.tiers.cancelBtn')}</button>
                  <button
                    type="button"
                    disabled={savingNewTier || !newTierForm.label.trim()}
                    onClick={async () => {
                      setSavingNewTier(true);
                      try {
                        const payload = {
                          label: newTierForm.label.trim(),
                          price: newTierForm.price !== '' ? Number(newTierForm.price) : 0,
                          capacity: newTierForm.capacity !== '' ? Number(newTierForm.capacity) : null,
                          description: newTierForm.description?.trim() || null,
                        };
                        const res = await eventTicketTiersAPI.create(occurrenceId, payload);
                        const created = res.data;
                        setTiers(prev => [...prev, created]);
                        setTierForms(f => ({
                          ...f,
                          [created.id]: {
                            label: created.label,
                            price: String(created.price),
                            capacity: created.capacity != null ? String(created.capacity) : '',
                            description: created.description || '',
                            is_active: created.is_active !== false,
                          },
                        }));
                        setNewTierForm({ label: '', price: '', capacity: '', description: '' });
                        setShowAddTier(false);
                        toast.success(t('dashboards.event.toasts.tierAdded'));
                      } catch (err) {
                        toast.error(err?.response?.data?.detail || t('dashboards.event.toasts.tierSaveError'));
                      } finally {
                        setSavingNewTier(false);
                      }
                    }}
                    className="rounded-md bg-gray-900 text-white px-3 py-1.5 text-xs font-semibold hover:bg-gray-800 disabled:opacity-50"
                  >{savingNewTier ? t('dashboards.common.saving') : t('dashboards.event.tiers.addAction')}</button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* G5: historical comparison — past events of the same product */}
        {analytics && analytics.past_comparison && analytics.past_comparison.length > 0 && (
          <div className="rounded-xl border border-gray-200 bg-white p-5">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h2 className="text-base font-semibold text-gray-900">{t('dashboards.event.history.title')}</h2>
                <p className="text-xs text-gray-500 mt-0.5">
                  {t('dashboards.event.history.subtitle', { count: analytics.past_comparison.length })}
                </p>
              </div>
            </div>
            <div className="overflow-x-auto -mx-5">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100 text-left text-[11px] uppercase tracking-wide text-gray-500">
                    <th className="px-5 py-2 font-semibold">{t('dashboards.event.history.colDate')}</th>
                    <th className="px-2 py-2 font-semibold text-right">{t('dashboards.event.history.colTickets')}</th>
                    <th className="px-2 py-2 font-semibold text-right">{t('dashboards.event.history.colRevenue')}</th>
                    <th className="px-5 py-2 font-semibold text-right">{t('dashboards.event.history.colAttendance')}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {analytics.past_comparison.map(p => {
                    // Delta vs current to highlight trend
                    const revDelta = analytics.revenue_total - p.revenue;
                    const qtyDelta = analytics.tickets_sold_total - p.tickets_sold;
                    return (
                      <tr key={p.occurrence_id} className="hover:bg-gray-50">
                        <td className="px-5 py-2 text-xs text-gray-700">
                          {p.start_at ? new Date(p.start_at).toLocaleDateString(i18n.language, { day: 'numeric', month: 'short', year: 'numeric' }) : '—'}
                        </td>
                        <td className="px-2 py-2 text-right tabular-nums">
                          <span className="text-sm text-gray-900">{p.tickets_sold}</span>
                          {p.capacity ? <span className="text-[11px] text-gray-400"> / {p.capacity}</span> : null}
                        </td>
                        <td className="px-2 py-2 text-right tabular-nums text-sm text-gray-900">
                          {formatPrice(p.revenue, analytics.currency)}
                        </td>
                        <td className="px-5 py-2 text-right tabular-nums text-xs">
                          {p.attendance_rate !== null && p.attendance_rate !== undefined
                            ? <span className="text-gray-900">{p.attendance_rate}%</span>
                            : <span className="text-gray-400">—</span>}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            {/* Summary vs current */}
            {(() => {
              const past = analytics.past_comparison;
              if (past.length === 0) return null;
              const avgRev = past.reduce((s, p) => s + p.revenue, 0) / past.length;
              const avgQty = past.reduce((s, p) => s + p.tickets_sold, 0) / past.length;
              const revDelta = analytics.revenue_total - avgRev;
              const qtyDelta = analytics.tickets_sold_total - avgQty;
              const revPct = avgRev > 0 ? Math.round((revDelta / avgRev) * 100) : null;
              return (
                <div className="mt-3 pt-3 border-t border-gray-100 text-[11px] text-gray-600">
                  <p>
                    <strong className="text-gray-900">{t('dashboards.event.history.compareNow')}</strong>{' '}
                    {t('dashboards.event.history.comparedTickets')}{' '}
                    <span className={qtyDelta >= 0 ? 'text-green-700 font-semibold' : 'text-red-700 font-semibold'}>
                      {qtyDelta >= 0 ? '+' : ''}{qtyDelta.toFixed(0)}
                    </span>
                    {' · '}
                    {t('dashboards.event.history.comparedRevenue')}{' '}
                    <span className={revDelta >= 0 ? 'text-green-700 font-semibold' : 'text-red-700 font-semibold'}>
                      {revDelta >= 0 ? '+' : ''}{formatPrice(revDelta, analytics.currency)}
                      {revPct !== null && ` (${revPct >= 0 ? '+' : ''}${revPct}%)`}
                    </span>
                  </p>
                </div>
              );
            })()}
          </div>
        )}

        {/* CF5 — ritiro concluso: il momento giusto per chiedere una recensione */}
        {isPastEvent && participants.length > 0 && (
          <div className="rounded-xl border border-[#376254]/30 bg-[#376254]/5 p-4 flex items-start gap-3">
            <span className="text-xl" aria-hidden>🌿</span>
            <div>
              <p className="text-sm font-semibold text-[#376254]">
                {t('dashboards.event.reviewAsk.title', { defaultValue: 'Ritiro concluso — chiedi una recensione' })}
              </p>
              <p className="text-xs text-gray-600 mt-0.5">
                {t('dashboards.event.reviewAsk.hint', { defaultValue: 'I bottoni di contatto qui sotto hanno già il messaggio pronto: ringraziamento + link alla tua pagina per recensire. Il momento migliore è nei primi giorni dopo il rientro.' })}
              </p>
            </div>
          </div>
        )}

        {/* G3: Lista partecipanti inline */}
        {participants.length > 0 && (
          <div className="rounded-xl border border-gray-200 bg-white p-5">
            <div className="flex items-center justify-between mb-3 gap-2 flex-wrap">
              <h2 className="text-base font-semibold text-gray-900">{t('dashboards.event.participants.title')}</h2>
              <span className="text-[11px] text-gray-500">
                {t('dashboards.event.participants.result', { count: filteredParticipants.length })}
              </span>
            </div>

            {/* Filters */}
            <div className="flex flex-col sm:flex-row gap-2 mb-3">
              <input
                type="search"
                value={participantSearch}
                onChange={e => setParticipantSearch(e.target.value)}
                placeholder={t('dashboards.event.participants.searchPlaceholder')}
                className="flex-1 rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-gray-900 focus:outline-none"
              />
              <select
                value={participantStatusFilter}
                onChange={e => setParticipantStatusFilter(e.target.value)}
                className="rounded-md border border-gray-300 px-3 py-1.5 text-sm bg-white"
              >
                <option value="">{t('dashboards.event.participants.filterAll')}</option>
                <option value="valid">{t('dashboards.event.participants.filterPending')}</option>
                <option value="checked_in">{t('dashboards.event.participants.filterEntered')}</option>
                <option value="voided">{t('dashboards.event.participants.filterCancelled')}</option>
              </select>
            </div>

            {/* Table */}
            {filteredParticipants.length === 0 ? (
              <p className="text-sm text-gray-500 text-center py-6">
                {t('dashboards.event.participants.empty')}
              </p>
            ) : (
              <div className="overflow-x-auto -mx-5">
                <table className="min-w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-100 text-left text-[11px] uppercase tracking-wide text-gray-500">
                      <th className="px-5 py-2 font-semibold">{t('dashboards.event.participants.colName')}</th>
                      <th className="px-2 py-2 font-semibold">{t('dashboards.event.participants.colCode')}</th>
                      <th className="px-2 py-2 font-semibold">{t('dashboards.event.participants.colTier')}</th>
                      {/* F2 Onda 9 — dynamic columns for attendee custom fields */}
                      {(occurrence?.product_metadata?.attendee_fields || [])
                        .slice().sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0))
                        .map(fc => (
                          <th key={fc.id} className="px-2 py-2 font-semibold">{fc.label}</th>
                        ))}
                      <th className="px-2 py-2 font-semibold">{t('dashboards.event.participants.colContact', { defaultValue: 'Contatta' })}</th>
                      <th className="px-5 py-2 font-semibold text-right">{t('dashboards.event.participants.colStatus')}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {pagedParticipants.map(p => (
                      <tr key={p.id} className="hover:bg-gray-50">
                        <td className="px-5 py-2">
                          <p className="font-medium text-gray-900 truncate max-w-[200px]">{p.holder_name || '—'}</p>
                          {p.holder_email && (
                            <p className="text-[11px] text-gray-500 truncate max-w-[200px]">{p.holder_email}</p>
                          )}
                        </td>
                        <td className="px-2 py-2 font-mono text-xs text-gray-700 whitespace-nowrap">{p.code}</td>
                        <td className="px-2 py-2 text-xs text-gray-700 whitespace-nowrap">{p.tier_label || '—'}</td>
                        {(occurrence?.product_metadata?.attendee_fields || [])
                          .slice().sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0))
                          .map(fc => {
                            const v = p.attendee_fields_data?.[fc.id];
                            return (
                              <td key={fc.id} className="px-2 py-2 text-xs text-gray-700 max-w-[180px] truncate">
                                {v == null || v === '' ? '—' : String(v)}
                              </td>
                            );
                          })}
                        <td className="px-2 py-2 whitespace-nowrap">
                          <ContactActions
                            name={p.holder_name}
                            email={p.contact_email || p.holder_email}
                            phone={p.contact_phone || p.holder_phone}
                            context={isPastEvent ? 'post_retreat_review' : 'pre_retreat'}
                            vars={outreachVars}
                          />
                        </td>
                        <td className="px-5 py-2 text-right whitespace-nowrap">
                          <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                            p.status === 'checked_in' ? 'bg-green-100 text-green-900'
                              : p.status === 'voided' ? 'bg-gray-200 text-gray-700'
                              : 'bg-blue-100 text-blue-900'
                          }`}>
                            {p.status === 'checked_in' ? t('dashboards.event.participants.statusEntered') : p.status === 'voided' ? t('dashboards.event.participants.statusCancelled') : t('dashboards.event.participants.statusPending')}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="mt-3 flex items-center justify-between text-xs">
                <span className="text-gray-500">{t('dashboards.event.participants.pageLabel', { current: participantsPage, total: totalPages })}</span>
                <div className="flex gap-1">
                  <button
                    type="button"
                    onClick={() => setParticipantsPage(p => Math.max(1, p - 1))}
                    disabled={participantsPage <= 1}
                    className="rounded border border-gray-300 px-2 py-1 hover:border-gray-900 disabled:opacity-40"
                  >{t('dashboards.event.participants.prev')}</button>
                  <button
                    type="button"
                    onClick={() => setParticipantsPage(p => Math.min(totalPages, p + 1))}
                    disabled={participantsPage >= totalPages}
                    className="rounded border border-gray-300 px-2 py-1 hover:border-gray-900 disabled:opacity-40"
                  >{t('dashboards.event.participants.next')}</button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Location */}
        {(occurrence.venue_name || occurrence.address || occurrence.location || occurrence.map_url) && (
          <div className="rounded-xl border border-gray-200 bg-white p-5">
            <h2 className="text-base font-semibold text-gray-900 mb-2">{t('dashboards.event.location.title')}</h2>
            {occurrence.venue_name && (
              <p className="font-medium text-gray-900">{occurrence.venue_name}</p>
            )}
            {address && (
              <p className="text-sm text-gray-600">{address}</p>
            )}
            {!occurrence.venue_name && !address && occurrence.location && (
              <p className="text-sm text-gray-700">{occurrence.location}</p>
            )}
            {occurrence.map_url && (
              <a
                href={occurrence.map_url} target="_blank" rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 mt-2 text-sm font-medium text-gray-900 hover:underline"
              >
                {t('dashboards.event.location.openMaps')}
              </a>
            )}
          </div>
        )}

        {/* ── E3: Descrizione lunga ─────────────────────────────── */}
        <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
          <button
            type="button"
            onClick={() => setEditLongDescOpen(o => !o)}
            className="w-full flex items-center justify-between px-5 py-3 text-left hover:bg-gray-50"
          >
            <span className="text-sm font-semibold text-gray-900">{t('dashboards.event.description.title')}</span>
            <span className="text-gray-400 text-xs">{editLongDescOpen ? '▲' : '▼'}</span>
          </button>

          {!editLongDescOpen && occurrence.long_description && (
            <div className="px-5 pb-4">
              <pre className="text-sm text-gray-700 whitespace-pre-wrap font-sans line-clamp-4">{occurrence.long_description}</pre>
            </div>
          )}

          {!editLongDescOpen && !occurrence.long_description && (
            <p className="px-5 pb-4 text-xs text-gray-400">{t('dashboards.event.description.empty')}</p>
          )}

          {editLongDescOpen && (
            <div className="border-t border-gray-100 px-5 py-4 space-y-3">
              <MultiLangSection fields={[
                { key: 'long_description', label: null, it: longDescForm,
                  value: trLong, onChange: setTrLong, rows: 6, maxLength: 5000 },
              ]}>
              <textarea
                value={longDescForm}
                onChange={e => setLongDescForm(e.target.value)}
                rows={8}
                placeholder={t('dashboards.event.description.placeholder')}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-gray-900 focus:outline-none resize-y"
              />
              </MultiLangSection>
              <div className="flex justify-end">
                <button
                  type="button"
                  disabled={savingLongDesc}
                  onClick={async () => {
                    setSavingLongDesc(true);
                    try {
                      await eventOccurrencesAPI.update(occurrenceId, { long_description: longDescForm || null });
                      // le traduzioni del racconto lungo vivono sul prodotto
                      if (occurrence?.product_id) {
                        await productsAPI.update(occurrence.product_id, { translations: buildTranslationsPayload() });
                      }
                      setOccurrence(prev => prev ? { ...prev, long_description: longDescForm || null } : prev);
                      toast.success(t('dashboards.event.toasts.descriptionUpdated'));
                      setEditLongDescOpen(false);
                    } catch { toast.error(t('dashboards.event.toasts.productSaveError')); }
                    finally { setSavingLongDesc(false); }
                  }}
                  className="rounded-md bg-gray-900 text-white px-4 py-2 text-sm font-semibold hover:bg-gray-800 disabled:opacity-50"
                >{savingLongDesc ? t('dashboards.common.saving') : t('dashboards.event.description.saveBtn')}</button>
              </div>
            </div>
          )}
        </div>

        {/* F4 — Store / Commerce assignment */}
        {availableStores.length > 0 && (
          <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-semibold text-gray-900">{t('dashboards.event.distribution.title')}</h2>
                <p className="text-xs text-gray-500 mt-0.5">
                  {t('dashboards.event.distribution.subtitle')}
                  {storeIds.length === 0 ? ` ${t('dashboards.event.distribution.currentlyAll')}` : ''}
                </p>
              </div>
              <button
                type="button"
                disabled={savingStores}
                onClick={async () => {
                  setSavingStores(true);
                  try {
                    await productsAPI.update(occurrence.product_id, { store_ids: storeIds });
                    toast.success(t('dashboards.event.toasts.distributionUpdated'));
                  } catch {
                    toast.error(t('dashboards.event.toasts.productSaveError'));
                  } finally {
                    setSavingStores(false);
                  }
                }}
                className="rounded-md bg-gray-900 text-white px-3 py-1.5 text-xs font-semibold hover:bg-gray-800 disabled:opacity-50"
              >
                {savingStores ? t('dashboards.common.saving') : t('dashboards.event.tiers.saveBtn')}
              </button>
            </div>
            <div className="flex flex-wrap gap-2">
              {availableStores.map(s => {
                const selected = storeIds.includes(s.id);
                return (
                  <button
                    key={s.id}
                    type="button"
                    onClick={() => setStoreIds(prev =>
                      selected ? prev.filter(id => id !== s.id) : [...prev, s.id]
                    )}
                    className={`rounded-full px-3 py-1 text-xs font-semibold border transition-all ${
                      selected
                        ? 'bg-gray-900 text-white border-gray-900'
                        : 'bg-white text-gray-700 border-gray-300 hover:border-gray-900'
                    }`}
                  >
                    {selected ? '✓ ' : ''}{s.name}
                  </button>
                );
              })}
            </div>
            {storeIds.length === 0 && (
              <p className="text-[11px] text-gray-400">{t('dashboards.event.distribution.noneSelected')}</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
