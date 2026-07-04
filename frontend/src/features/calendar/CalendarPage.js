import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { AppLayout, Header } from '../../components/Layout';
import { PageSubheader } from '../../components/PageSubheader';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from '../../components/ui/dialog';
import {
  ChevronLeft, ChevronRight, Loader2, MapPin, Clock, User, ExternalLink,
  Ban, Trash2, Repeat,
} from 'lucide-react';
import { calendarAPI } from '../../api/calendar';
import { availabilityAPI } from '../../api/availability';
import { getItemTypeBadgeClass } from '../../constants/itemTypes';
import { toast } from 'sonner';
import CalendarListView from './components/CalendarListView';
import { calendarItemPath } from '../../utils/productPaths';

const STATUS_COLORS = {
  published: 'bg-emerald-500', draft: 'bg-gray-400', closed: 'bg-amber-500',
  cancelled: 'bg-red-400', confirmed: 'bg-blue-500', completed: 'bg-emerald-500',
};

const TYPE_CONFIG = {
  event_occurrence: { labelKey: 'type.event_occurrence', badgeClass: getItemTypeBadgeClass('event_ticket') || 'bg-purple-50 text-purple-600' },
  rental_order: { labelKey: 'type.rental_order', badgeClass: getItemTypeBadgeClass('rental') || 'bg-orange-50 text-orange-600' },
  service_booking: { labelKey: 'type.service_booking', badgeClass: getItemTypeBadgeClass('service') || 'bg-indigo-50 text-indigo-600' },
};

const REASON_BADGE = { personal: 'bg-red-100 text-red-700', holiday: 'bg-amber-100 text-amber-700', booking: 'bg-blue-100 text-blue-700', event: 'bg-purple-100 text-purple-700', rental: 'bg-orange-100 text-orange-700' };
// 2026-05-20 — Auto-blocks are created by ``order_service.try_reserve_*``
// when an order is confirmed (so concurrent shoppers can't double-book
// the same slot). They appear in blocked_slots_collection ALONGSIDE the
// real order, which means the calendar's "Slot bloccati" section was
// showing each booking twice — once as the order, once as the auto
// block. Adding rental here so the day-detail filter (below) hides ALL
// three auto-block reasons consistently.
const isAutoBlock = (b) => b.reason === 'booking' || b.reason === 'event' || b.reason === 'rental';

function buildMonthGrid(year, month) {
  const lastDay = new Date(year, month, 0);
  const daysInMonth = lastDay.getDate();
  let startDow = new Date(year, month - 1, 1).getDay() - 1;
  if (startDow < 0) startDow = 6;
  const cells = [];
  for (let i = 0; i < startDow; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(d);
  return cells;
}

/* ── Block Slot Dialog ────────────────────────────────────────────────────── */

/** Format a Date to YYYY-MM-DD using local timezone (avoids UTC shift bugs). */
function fmtLocalDate(d) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

/** Parse YYYY-MM-DD to a local Date (noon to avoid any DST edge cases). */
function parseLocalDate(s) {
  const [y, m, d] = s.split('-').map(Number);
  return new Date(y, m - 1, d, 12, 0, 0);
}

/** Compute all dates matching the same weekday between start and endDate (inclusive). */
function computeWeeklyDates(startDate, endDate) {
  const dates = [];
  const current = parseLocalDate(startDate);
  const end = parseLocalDate(endDate);
  while (current <= end) {
    dates.push(fmtLocalDate(current));
    current.setDate(current.getDate() + 7);
  }
  return dates;
}

/** Compute all consecutive dates from start to end (inclusive). */
function computeRangeDates(startDate, endDate) {
  const dates = [];
  const current = parseLocalDate(startDate);
  const end = parseLocalDate(endDate);
  while (current <= end) {
    dates.push(fmtLocalDate(current));
    current.setDate(current.getDate() + 1);
  }
  return dates;
}

// Module-level constants use labelKey pattern — no t() calls at module scope
const BLOCK_MODES = [
  { key: 'single', labelKey: 'block_dialog.modes.single' },
  { key: 'range', labelKey: 'block_dialog.modes.range' },
  { key: 'weekly', labelKey: 'block_dialog.modes.weekly' },
];

function BlockSlotDialog({ open, onClose, onSubmit, onSubmitBatch, saving, prefilledDate, calView, rentalProducts }) {
  const { t } = useTranslation('calendar');
  const [form, setForm] = useState({
    mode: 'single', date: '', dateTo: '', allDay: true,
    start_time: '09:00', end_time: '18:00', reason: 'personal', note: '',
    repeatUntil: '', target: 'agenda', targetProduct: '',
  });

  const hasRentals = (rentalProducts || []).length > 0;

  useEffect(() => {
    if (open) {
      const today = new Date();
      const defaultDate = prefilledDate || `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
      const twoMonths = new Date(today); twoMonths.setMonth(twoMonths.getMonth() + 2);
      const repeatUntil = fmtLocalDate(twoMonths);
      const oneWeek = parseLocalDate(defaultDate); oneWeek.setDate(oneWeek.getDate() + 7);
      const dateTo = fmtLocalDate(oneWeek);
      setForm({
        mode: 'single', date: defaultDate, dateTo, allDay: true,
        start_time: '09:00', end_time: '18:00', reason: 'personal', note: '', repeatUntil,
        target: calView || 'agenda', targetProduct: '',
      });
    }
  }, [open, prefilledDate, calView]);

  const batchDates = useMemo(() => {
    if (form.mode === 'range' && form.date && form.dateTo && form.dateTo >= form.date) {
      return computeRangeDates(form.date, form.dateTo);
    }
    if (form.mode === 'weekly' && form.date && form.repeatUntil && form.repeatUntil >= form.date) {
      return computeWeeklyDates(form.date, form.repeatUntil);
    }
    return [];
  }, [form.mode, form.date, form.dateTo, form.repeatUntil]);

  const daysFull = t('days_full', { returnObjects: true }) || [];
  const selectedDayName = form.date ? daysFull[parseLocalDate(form.date).getDay()] : '';
  const isBatch = form.mode !== 'single' && batchDates.length > 1;

  const handleSubmit = () => {
    if (!form.date) { toast.error(t('validation.select_date')); return; }
    if (!form.allDay && form.start_time >= form.end_time) {
      toast.error(t('validation.end_time_after_start'));
      return;
    }
    if (form.mode === 'range' && (!form.dateTo || form.dateTo < form.date)) {
      toast.error(t('validation.end_date_gte_start'));
      return;
    }
    if (form.mode === 'weekly' && (!form.repeatUntil || form.repeatUntil < form.date)) {
      toast.error(t('validation.until_date_after_start'));
      return;
    }
    const startTime = form.allDay ? '00:00' : form.start_time;
    const endTime = form.allDay ? '23:59' : form.end_time;
    const note = form.note?.trim() || undefined;

    // Target → scope mapping:
    //   agenda  → scope="agenda", product_id=null
    //   rentals → scope="rentals", product_id=selected or null
    //   both    → scope=null (global), product_id=null
    const scope = form.target === 'both' ? undefined : form.target;
    const productId = form.target === 'rentals' && form.targetProduct ? form.targetProduct : undefined;
    const payload = { start_time: startTime, end_time: endTime, reason: form.reason, note, product_id: productId, scope };

    if (isBatch) {
      onSubmitBatch({ ...payload, dates: batchDates });
    } else {
      onSubmit({ ...payload, date: form.date });
    }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-[calc(100vw-1rem)] sm:max-w-sm mx-2 sm:mx-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Ban className="h-4 w-4 text-red-500" /> {t('block_dialog.title')}
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-4 py-2">

          {/* Mode selector */}
          <div className="flex rounded-lg border overflow-hidden">
            {BLOCK_MODES.map(m => (
              <button
                key={m.key}
                type="button"
                onClick={() => setForm(f => ({ ...f, mode: m.key }))}
                className={`flex-1 px-2 py-1.5 text-xs font-medium transition-colors ${
                  form.mode === m.key ? 'bg-primary text-primary-foreground' : 'hover:bg-muted/50 text-muted-foreground'
                }`}
              >
                {t(m.labelKey)}
              </button>
            ))}
          </div>

          {/* Date fields — vary by mode */}
          {form.mode === 'single' && (
            <div>
              <Label>{t('block_dialog.labels.date')}</Label>
              <Input type="date" value={form.date} onChange={e => setForm(f => ({ ...f, date: e.target.value }))} />
            </div>
          )}

          {form.mode === 'range' && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <Label className="text-xs">{t('block_dialog.labels.from')}</Label>
                <Input type="date" value={form.date} onChange={e => setForm(f => ({ ...f, date: e.target.value }))} />
              </div>
              <div>
                <Label className="text-xs">{t('block_dialog.labels.to')}</Label>
                <Input type="date" value={form.dateTo} onChange={e => setForm(f => ({ ...f, dateTo: e.target.value }))} />
              </div>
            </div>
          )}

          {form.mode === 'weekly' && (
            <div className="space-y-3">
              <div>
                <Label>{t('block_dialog.labels.starting_from')}</Label>
                <Input type="date" value={form.date} onChange={e => setForm(f => ({ ...f, date: e.target.value }))} />
              </div>
              <div>
                <Label className="text-xs">{t('block_dialog.labels.until')}</Label>
                <Input type="date" value={form.repeatUntil} onChange={e => setForm(f => ({ ...f, repeatUntil: e.target.value }))} />
              </div>
            </div>
          )}

          {/* Preview */}
          {isBatch && (
            <div className="rounded-lg bg-muted/40 px-3 py-2">
              <p className="text-xs text-muted-foreground">
                {form.mode === 'range' && (
                  <><strong>{batchDates.length}</strong> {t('block_dialog.preview_range_days', { count: batchDates.length })}</>
                )}
                {form.mode === 'weekly' && (
                  <>{t('block_dialog.preview_weekly_prefix')} <strong>{selectedDayName}</strong> — <strong>{batchDates.length}</strong> {t('block_dialog.preview_weekly_suffix', { count: batchDates.length })}</>
                )}
              </p>
            </div>
          )}

          {/* All day toggle */}
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" checked={form.allDay} onChange={e => setForm(f => ({ ...f, allDay: e.target.checked }))} className="rounded border-gray-300" />
              <span className="text-sm">{t('actions.all_day')}</span>
            </label>
          </div>

          {!form.allDay && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div><Label className="text-xs">{t('block_dialog.time_from')}</Label><Input type="time" value={form.start_time} onChange={e => setForm(f => ({ ...f, start_time: e.target.value }))} /></div>
              <div><Label className="text-xs">{t('block_dialog.time_to')}</Label><Input type="time" value={form.end_time} onChange={e => setForm(f => ({ ...f, end_time: e.target.value }))} /></div>
            </div>
          )}

          {/* Reason + Note */}
          <div>
            <Label className="text-xs">{t('block_dialog.labels.reason')}</Label>
            <select value={form.reason} onChange={e => setForm(f => ({ ...f, reason: e.target.value }))} className="w-full mt-1 rounded-md border border-input bg-background px-3 py-2 text-sm">
              <option value="personal">{t('block_dialog.reasons.personal')}</option>
              <option value="holiday">{t('block_dialog.reasons.holiday')}</option>
            </select>
          </div>

          <div>
            <Label>{t('block_dialog.labels.note')}</Label>
            <Input value={form.note} onChange={e => setForm(f => ({ ...f, note: e.target.value }))} placeholder={t('block_dialog.note_placeholder')} maxLength={500} />
          </div>

          {/* Target calendar selector */}
          {hasRentals && (
            <div className="border-t pt-3 space-y-2">
              <Label className="text-xs">{t('block_dialog.labels.apply_to')}</Label>
              <div className="flex rounded-lg border overflow-hidden">
                {['agenda', 'rentals', 'both'].map(key => (
                  <button key={key} type="button"
                    onClick={() => setForm(f => ({ ...f, target: key, targetProduct: '' }))}
                    className={`flex-1 px-2 py-1.5 text-xs font-medium transition-colors ${
                      form.target === key ? 'bg-primary text-primary-foreground' : 'hover:bg-muted/50 text-muted-foreground'
                    }`}
                  >{t(`block_dialog.targets.${key}`)}</button>
                ))}
              </div>
              {form.target === 'rentals' && rentalProducts.length > 0 && (
                <div>
                  <Label className="text-[11px] text-muted-foreground">{t('block_dialog.labels.rental_product')}</Label>
                  <select
                    value={form.targetProduct}
                    onChange={e => setForm(f => ({ ...f, targetProduct: e.target.value }))}
                    className="w-full mt-1 rounded-md border border-input bg-background px-3 py-2 text-sm"
                  >
                    <option value="">{t('block_dialog.labels.all_rental_products')}</option>
                    {rentalProducts.map(p => (
                      <option key={p.id} value={p.id}>{p.name}</option>
                    ))}
                  </select>
                </div>
              )}
            </div>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" size="sm" onClick={() => onClose(false)}>{t('block_dialog.cancel')}</Button>
          <Button size="sm" onClick={handleSubmit} disabled={saving} className="gap-1.5 bg-red-600 hover:bg-red-700">
            {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Ban className="h-3.5 w-3.5" />}
            {isBatch ? t('block_dialog.submit_batch', { count: batchDates.length }) : t('block_dialog.submit_single')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/* ── Day Cell ─────────────────────────────────────────────────────────────── */

function DayCell({ day, year, month, items, blockedSlots, isToday, onSelect, isSelected }) {
  const { t } = useTranslation('calendar');
  if (day === null) return <div className="min-h-[5rem]" />;

  const dateStr = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
  const dayItems = items.filter(it => {
    if (it.date === dateStr) return true;
    if (it.type === 'rental_order' && it.end_date && it.date <= dateStr && it.end_date >= dateStr) return true;
    return false;
  });
  // 2026-05-20 — Hide auto-blocks from the cell summary (consistent with
  // the DayDetail panel below). Auto-blocks duplicate information already
  // surfaced by the order in ``dayItems`` (orange/purple type indicators
  // + colored status dot). Keeping them would make "3 prenotazioni" days
  // appear as "3 prenotazioni + 3 slot bloccati" which is misleading.
  const dayBlocks = blockedSlots.filter(b => b.date === dateStr && !isAutoBlock(b));
  const hasBlocks = dayBlocks.length > 0;

  // Onda 15 Fase 3 — dominant type for the left-accent stripe. When a day
  // mixes types, pick the one with the highest count; ties break in the
  // order event > service > rental (roughly visibility priority).
  let accentClass = '';
  if (dayItems.length > 0) {
    const counts = {};
    for (const it of dayItems) counts[it.type] = (counts[it.type] || 0) + 1;
    const dominant = ['event_occurrence', 'service_booking', 'rental_order']
      .filter(t => counts[t] > 0)
      .sort((a, b) => counts[b] - counts[a])[0];
    accentClass = {
      event_occurrence: 'border-l-4 border-l-purple-400',
      service_booking:  'border-l-4 border-l-indigo-400',
      rental_order:     'border-l-4 border-l-orange-400',
    }[dominant] || '';
  }

  return (
    <button
      onClick={() => onSelect(dateStr)}
      className={`min-h-[3.25rem] sm:min-h-[4rem] md:min-h-[5rem] p-1 sm:p-1.5 text-left border rounded-lg transition-colors hover:bg-gray-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-1 ${accentClass} ${
        isToday ? 'border-gray-900 bg-gray-50' : hasBlocks ? 'border-red-200 bg-red-50/30' : 'border-gray-200'
      } ${isSelected ? 'ring-2 ring-gray-900 ring-offset-1' : ''}`}
    >
      <div className="flex items-center gap-1">
        <span className={`text-xs font-medium ${isToday ? 'text-gray-900' : 'text-gray-500'}`}>{day}</span>
        {hasBlocks && <Ban className="h-3 w-3 text-red-400" />}
        {/* Onda 15 Fase 1 — type indicators: quick visual count per item type.
            Helps scan "what kind of stuff is on this day" at a glance. */}
        {dayItems.length > 0 && (() => {
          const counts = {};
          for (const it of dayItems) counts[it.type] = (counts[it.type] || 0) + 1;
          return (
            <span className="ml-auto flex items-center gap-0.5 text-[9px] leading-none">
              {counts.event_occurrence > 0 && (
                <span className="text-purple-600" title={`${counts.event_occurrence} eventi`}>🎟</span>
              )}
              {counts.service_booking > 0 && (
                <span className="text-indigo-600" title={`${counts.service_booking} consulenze`}>📅</span>
              )}
              {counts.rental_order > 0 && (
                <span className="text-orange-600" title={`${counts.rental_order} affitti`}>🧾</span>
              )}
            </span>
          );
        })()}
      </div>
      <div className="mt-0.5 space-y-0.5">
        {dayItems.slice(0, 3).map((it, i) => (
          <div key={i} className="flex items-center gap-1">
            <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${STATUS_COLORS[it.status] || 'bg-gray-400'}`} />
            <span className="text-[10px] text-gray-700 truncate leading-tight">{it.title}</span>
          </div>
        ))}
        {hasBlocks && dayItems.length < 3 && dayBlocks.map((b, i) => (
          <div key={`b-${i}`} className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full shrink-0 bg-red-400" />
            <span className="text-[10px] text-red-600 truncate leading-tight">{b.note || t(`reasons.${b.reason}`, { defaultValue: b.reason })}</span>
          </div>
        )).slice(0, 3 - dayItems.length)}
        {(dayItems.length + dayBlocks.length) > 3 && (
          <span className="text-[10px] text-gray-400">{t('summary.overflow', { count: dayItems.length + dayBlocks.length - 3 })}</span>
        )}
      </div>
    </button>
  );
}

/* ── Day Detail Panel ─────────────────────────────────────────────────────── */

function DayDetail({ dateStr, items, blockedSlots, allBlockedSlots, onClose, onNavigate, onDeleteBlock, onDeleteBlockGroup, blockSaving }) {
  const { t } = useTranslation('calendar');
  const [confirmDelete, setConfirmDelete] = useState(null); // { id, group_id, groupCount }

  const dayItems = items.filter(it => {
    if (it.date === dateStr) return true;
    if (it.type === 'rental_order' && it.end_date && it.date <= dateStr && it.end_date >= dateStr) return true;
    return false;
  });
  // 2026-05-20 — Bug fix: previously this filter included auto-blocks,
  // which made every booking/event/rental appear twice in the day
  // detail panel (once as the order row in dayItems, once as a "Slot
  // bloccato" row). Auto-blocks (reason=booking|event|rental) exist
  // only for the availability checker — they prevent two concurrent
  // shoppers from grabbing the same slot — and the merchant doesn't
  // need them in the day view because the corresponding order already
  // carries time, customer, and status. Personal/holiday blocks are
  // still shown — those are the ones the merchant actually manages.
  const dayBlocks = blockedSlots.filter(b => b.date === dateStr && !isAutoBlock(b));

  const fmtDate = (d) => parseLocalDate(d).toLocaleDateString('it-IT', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });

  const handleDeleteClick = (b) => {
    if (b.group_id) {
      // Count how many blocks share this group
      const groupCount = allBlockedSlots.filter(s => s.group_id === b.group_id).length;
      setConfirmDelete({ id: b.id, group_id: b.group_id, groupCount });
    } else {
      onDeleteBlock(b.id);
    }
  };

  return (
    <div className="rounded-xl border bg-card p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-sm capitalize">{fmtDate(dateStr)}</h3>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-sm">{t('actions.close')}</button>
      </div>

      {/* Calendar items */}
      {dayItems.length === 0 && dayBlocks.length === 0 ? (
        <p className="text-sm text-muted-foreground">{t('empty.day')}</p>
      ) : (
        <>
          {dayItems.length > 0 && (
            <div className="space-y-2">
              {dayItems.map((it, i) => {
                const cfg = TYPE_CONFIG[it.type] || TYPE_CONFIG.event_occurrence;
                return (
                  <div key={i} className={`rounded-lg border p-3 text-sm space-y-1 ${
                    it.type === 'rental_order' && it.status === 'draft' && it.review_reason ? 'border-amber-200 bg-amber-50/30' : ''
                  }`}>
                    <div className="flex items-center gap-1.5">
                      <span className={`w-2 h-2 rounded-full shrink-0 ${STATUS_COLORS[it.status] || 'bg-gray-400'}`} />
                      <span className="font-medium">{it.title}</span>
                      <Badge className={`text-[10px] px-1.5 py-0 ${cfg.badgeClass}`}>{t(cfg.labelKey)}</Badge>
                      {it.status_label && <span className="text-[10px] text-muted-foreground">{it.status_label}</span>}
                    </div>
                    <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-muted-foreground">
                      {it.time && (
                        <span className="flex items-center gap-0.5">
                          <Clock className="h-3 w-3" />
                          {it.time}{it.end_time ? `–${it.end_time}` : ''}
                        </span>
                      )}
                      {it.location && <span className="flex items-center gap-0.5"><MapPin className="h-3 w-3" />{it.location}</span>}
                      {it.customer_name && <span className="flex items-center gap-0.5"><User className="h-3 w-3" />{it.customer_name}</span>}
                      {it.end_date && it.end_date !== it.date && <span>{it.date} → {it.end_date}</span>}
                      {it.capacity != null && (
                        <span className={it.booked_count >= it.capacity ? 'text-red-600 font-medium' : ''}>
                          {it.booked_count || 0}/{it.capacity} {t('summary.seats')}
                        </span>
                      )}
                    </div>
                    {/* Onda 14 — Consulenza detail block: customer contacts,
                        service option, booking code, custom fields. Shows only
                        for service_booking rows; other types keep their lean display. */}
                    {it.type === 'service_booking' && (
                      <div className="mt-2 rounded-md bg-indigo-50/50 border border-indigo-100 p-2 space-y-1">
                        {it.service_option_label && (
                          <div className="text-xs text-indigo-900">
                            <span className="font-semibold">Opzione:</span> {it.service_option_label}
                          </div>
                        )}
                        {(it.customer_email || it.customer_phone) && (
                          <div className="flex flex-wrap gap-x-3 text-xs text-indigo-900">
                            {it.customer_email && (
                              <a href={`mailto:${it.customer_email}`} className="hover:underline">
                                ✉️ {it.customer_email}
                              </a>
                            )}
                            {it.customer_phone && (
                              <a href={`tel:${it.customer_phone}`} className="hover:underline">
                                📞 {it.customer_phone}
                              </a>
                            )}
                          </div>
                        )}
                        {it.booking_code && (
                          <div className="text-[11px] font-mono text-indigo-800">
                            Codice: {it.booking_code}
                          </div>
                        )}
                        {it.attendee_fields_data && Object.keys(it.attendee_fields_data).length > 0 && (
                          <div className="pt-1 border-t border-indigo-100">
                            <div className="text-[10px] font-semibold uppercase tracking-wider text-indigo-700 mb-0.5">
                              Info cliente
                            </div>
                            <dl className="grid grid-cols-[auto_1fr] gap-x-2 gap-y-0.5 text-xs">
                              {Object.entries(it.attendee_fields_data).map(([k, v]) => (
                                <React.Fragment key={k}>
                                  <dt className="text-indigo-700">{k}:</dt>
                                  <dd className="text-indigo-900">{String(v)}</dd>
                                </React.Fragment>
                              ))}
                            </dl>
                          </div>
                        )}
                      </div>
                    )}
                    {it.review_reason && it.status === 'draft' && (
                      <p className="text-[11px] text-amber-600">{t(`review.${it.review_reason}`, { defaultValue: t('review.default') })}</p>
                    )}
                    {it.notes && <p className="text-xs text-muted-foreground italic">{it.notes}</p>}
                    {/* Onda 15 Fase 1 — primary + secondary action buttons,
                        outlined rather than plain links. 3x more tap-friendly
                        on mobile and much more visible at a glance. */}
                    <div className="flex flex-wrap items-center gap-2 mt-2 pt-2 border-t border-gray-100">
                      <button
                        onClick={() => onNavigate(it)}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-gray-900 text-white text-xs font-semibold hover:bg-gray-800 transition-colors"
                      >
                        <ExternalLink className="h-3.5 w-3.5" />
                        {it.type === 'rental_order' || it.type === 'service_booking'
                          ? t('actions.go_to_order', { defaultValue: 'Apri ordine' })
                          : t('actions.go_to_product', { defaultValue: 'Apri prodotto' })}
                      </button>
                      {it.type === 'service_booking' && it.booking_access_token && (
                        <a
                          href={`/b/${it.booking_access_token}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-gray-300 text-gray-700 text-xs font-medium hover:bg-gray-50 transition-colors"
                        >
                          <ExternalLink className="h-3.5 w-3.5" />
                          Apri prenotazione
                        </a>
                      )}
                      {it.customer_email && it.type === 'service_booking' && (
                        <a
                          href={`mailto:${it.customer_email}`}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-gray-300 text-gray-700 text-xs font-medium hover:bg-gray-50 transition-colors"
                          title={`Scrivi a ${it.customer_email}`}
                        >
                          ✉️ Email
                        </a>
                      )}
                      {it.customer_phone && it.type === 'service_booking' && (
                        <a
                          href={`tel:${it.customer_phone}`}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-gray-300 text-gray-700 text-xs font-medium hover:bg-gray-50 transition-colors"
                          title={`Chiama ${it.customer_phone}`}
                        >
                          📞 Chiama
                        </a>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Blocked slots in day detail */}
          {dayBlocks.length > 0 && (
            <div className="space-y-1.5">
              <h4 className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
                <Ban className="h-3.5 w-3.5 text-red-400" /> {t('blocked_slots.heading')}
              </h4>
              {dayBlocks.map(b => (
                <div key={b.id} className="flex items-center justify-between rounded-lg border border-red-200 bg-red-50/50 px-3 py-2 text-sm">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="text-xs font-mono text-red-700 shrink-0">
                      {b.start_time === '00:00' && b.end_time === '23:59' ? t('blocked_slots.all_day') : `${b.start_time}–${b.end_time}`}
                    </span>
                    <Badge className={`text-[10px] px-1.5 py-0 shrink-0 ${REASON_BADGE[b.reason] || REASON_BADGE.personal}`}>
                      {t(`reasons.${b.reason}`, { defaultValue: b.reason })}
                    </Badge>
                    {isAutoBlock(b) && <Badge className="text-[10px] px-1.5 py-0 bg-slate-100 text-slate-500 shrink-0">Auto</Badge>}
                    {b.group_id && !isAutoBlock(b) && (
                      <Badge className="text-[10px] px-1.5 py-0 bg-indigo-50 text-indigo-600 shrink-0 flex items-center gap-0.5">
                        <Repeat className="h-2.5 w-2.5" /> {t('blocked_slots.recurring')}
                      </Badge>
                    )}
                    {b.note && <span className="text-xs text-muted-foreground italic truncate">{b.note}</span>}
                  </div>
                  {!isAutoBlock(b) && (
                    <button
                      onClick={() => handleDeleteClick(b)}
                      disabled={blockSaving}
                      className="p-1 rounded hover:bg-red-100 text-red-500 hover:text-red-700 disabled:opacity-50 shrink-0 ml-2"
                      title={t('blocked_slots.remove_title')}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* Group delete confirmation */}
      {confirmDelete && (
        <div className="rounded-lg border-2 border-red-300 bg-red-50 p-3 space-y-2">
          <p className="text-sm font-medium text-red-800">{t('confirm_delete.recurring_message', { count: confirmDelete.groupCount })}</p>
          <p className="text-xs text-red-700">{t('confirm_delete.recurring_question')}</p>
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              disabled={blockSaving}
              onClick={() => { onDeleteBlock(confirmDelete.id); setConfirmDelete(null); }}
              className="text-xs h-7"
            >
              {t('confirm_delete.only_this_day')}
            </Button>
            <Button
              size="sm"
              disabled={blockSaving}
              onClick={() => { onDeleteBlockGroup(confirmDelete.group_id); setConfirmDelete(null); }}
              className="text-xs h-7 bg-red-600 hover:bg-red-700"
            >
              {blockSaving ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : null}
              {t('confirm_delete.all_days', { count: confirmDelete.groupCount })}
            </Button>
            <button onClick={() => setConfirmDelete(null)} className="text-xs text-muted-foreground hover:text-foreground">
              {t('confirm_delete.cancel')}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Main Calendar Page ───────────────────────────────────────────────────── */

export default function CalendarPage() {
  const { t } = useTranslation('calendar');
  const navigate = useNavigate();
  const location = useLocation();
  const today = new Date();
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth() + 1);
  const [items, setItems] = useState([]);
  const [blockedSlots, setBlockedSlots] = useState([]);
  const [loading, setLoading] = useState(true);
  const [blockSaving, setBlockSaving] = useState(false);
  const [selectedDate, setSelectedDate] = useState(null);
  const [blockDialogOpen, setBlockDialogOpen] = useState(false);
  const [calView, setCalView] = useState('agenda'); // 'agenda' | 'rentals' | 'list'
  const [quickRange, setQuickRange] = useState('month'); // 'today' | 'week' | 'month' (Onda 15 Fase 4)
  const [productFilter, setProductFilter] = useState(''); // '' = all, 'xxx' = per product
  const [calendarProducts, setCalendarProducts] = useState([]); // products with calendar relevance

  const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;

  const dateFrom = useMemo(() => `${year}-${String(month).padStart(2, '0')}-01`, [year, month]);
  const dateTo = useMemo(() => {
    const last = new Date(year, month, 0);
    return `${year}-${String(month).padStart(2, '0')}-${String(last.getDate()).padStart(2, '0')}`;
  }, [year, month]);

  // Fetch calendar-relevant products
  useEffect(() => {
    const fetchProducts = async () => {
      try {
        const { productsAPI } = await import('../../api');
        const res = await productsAPI.list(true);
        const prods = (res.data || []).filter(p =>
          ['rental', 'event_ticket', 'booking', 'service'].includes(p.item_type)
        );
        setCalendarProducts(prods);
      } catch { /* empty */ }
    };
    fetchProducts();
  }, []);

  const rentalProducts = useMemo(() => calendarProducts.filter(p => p.item_type === 'rental'), [calendarProducts]);
  const hasRentals = rentalProducts.length > 0;

  // Count of blocked slots per rental product in the currently loaded range.
  // Used by the rental filter chip badges so the merchant sees at a glance
  // how many days are occupied for each rental. Derived purely from local
  // state — no API call.
  const blocksCountByProduct = useMemo(() => {
    const out = {};
    for (const b of blockedSlots || []) {
      if (b.scope !== 'rentals') continue;
      const pid = b.product_id || '';
      out[pid] = (out[pid] || 0) + 1;
    }
    return out;
  }, [blockedSlots]);
  const totalRentalBlocks = useMemo(
    () => (blockedSlots || []).filter(b => b.scope === 'rentals').length,
    [blockedSlots],
  );

  // Reset product filter when switching views
  useEffect(() => { setProductFilter(''); setSelectedDate(null); }, [calView]);

  // Onda 14 Parte C — deep-link from ServiceDashboardPage:
  //   /calendar?product_id=<id>  → preselect the product filter so the
  // admin immediately sees only that service's bookings.
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const pid = params.get('product_id');
    if (pid && pid !== productFilter) {
      setProductFilter(pid);
    }
    // Only runs once per URL change; no need to include productFilter in deps.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.search]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const pid = productFilter || undefined;
      const [calRes, blockRes] = await Promise.all([
        calendarAPI.getItems(year, month, pid),
        availabilityAPI.listBlocked(dateFrom, dateTo, undefined, pid).catch(() => ({ data: { blocked_slots: [] } })),
      ]);
      let loadedItems = calRes.data?.items || [];
      let loadedBlocks = blockRes.data?.blocked_slots || [];

      if (calView === 'agenda') {
        // Agenda: events, bookings, personal blocks — NO rental items
        // Show blocks with scope=agenda OR scope=null(global) — NOT scope=rentals
        loadedItems = loadedItems.filter(i => i.type !== 'rental_order');
        loadedBlocks = loadedBlocks.filter(b => b.scope !== 'rentals');
      } else if (calView === 'rentals') {
        // Noleggi: only rental orders + rental-scoped blocks + global blocks
        // Show blocks with scope=rentals OR scope=null(global) — NOT scope=agenda
        loadedItems = loadedItems.filter(i => i.type === 'rental_order');
        loadedBlocks = loadedBlocks.filter(b => b.scope !== 'agenda');
      }
      // 2026-05-20 — Bug fix: ``calView === 'list'`` is the third view
      // (a flat searchable table of EVERY engagement of the month —
      // see CalendarListView's header comment for the design intent).
      // The previous else-only branch above wrongly filtered the list
      // view down to ``rental_order`` only, leaving merchants with
      // no rentals staring at an empty list. We now leave loadedItems
      // untouched for 'list' so all three item types reach the table;
      // ``CalendarListView`` has its own per-type chip filters built in.

      setItems(loadedItems);
      setBlockedSlots(loadedBlocks);
    } catch { /* empty */ }
    finally { setLoading(false); }
  }, [year, month, dateFrom, dateTo, productFilter, calView]);

  useEffect(() => { load(); }, [load]);

  const grid = useMemo(() => buildMonthGrid(year, month), [year, month]);

  // Onda 15 Fase 4 — quick-range filter applied to the items fed into
  // DayCell / DayDetail / ListView. 'month' = all items (no filter).
  // 'today' = only items on today's date (or today falls within rental span).
  // 'week' = ISO week around today (Mon-Sun).
  const filteredItems = useMemo(() => {
    if (quickRange === 'month') return items;
    if (quickRange === 'today') {
      return items.filter(it => {
        if (it.date === todayStr) return true;
        if (it.type === 'rental_order' && it.end_date && it.date <= todayStr && it.end_date >= todayStr) return true;
        return false;
      });
    }
    if (quickRange === 'week') {
      // ISO week Mon-Sun containing today
      const d = new Date();
      const dow = (d.getDay() + 6) % 7; // 0=Mon..6=Sun
      const mon = new Date(d); mon.setDate(d.getDate() - dow);
      const sun = new Date(mon); sun.setDate(mon.getDate() + 6);
      const toISO = (x) => `${x.getFullYear()}-${String(x.getMonth() + 1).padStart(2, '0')}-${String(x.getDate()).padStart(2, '0')}`;
      const weekFrom = toISO(mon);
      const weekTo = toISO(sun);
      return items.filter(it => {
        if (it.date >= weekFrom && it.date <= weekTo) return true;
        if (it.type === 'rental_order' && it.end_date && it.date <= weekTo && it.end_date >= weekFrom) return true;
        return false;
      });
    }
    return items;
  }, [items, quickRange, todayStr]);

  const prevMonth = () => { if (month === 1) { setMonth(12); setYear(y => y - 1); } else setMonth(m => m - 1); setSelectedDate(null); };
  const nextMonth = () => { if (month === 12) { setMonth(1); setYear(y => y + 1); } else setMonth(m => m + 1); setSelectedDate(null); };
  const goToday = () => { setYear(today.getFullYear()); setMonth(today.getMonth() + 1); setSelectedDate(todayStr); };

  // Onda 15 Fase 5 — swipe gesture on mobile for month navigation.
  // Lightweight, touch-events-only (no library). Threshold 60px horizontal
  // dominant delta, max vertical drift 50px to avoid hijacking scrolls.
  const swipeStart = useRef(null);
  const handleTouchStart = (e) => {
    const t = e.touches[0];
    swipeStart.current = { x: t.clientX, y: t.clientY, t: Date.now() };
  };
  const handleTouchEnd = (e) => {
    const s = swipeStart.current;
    swipeStart.current = null;
    if (!s) return;
    const t = e.changedTouches[0];
    const dx = t.clientX - s.x;
    const dy = t.clientY - s.y;
    const elapsed = Date.now() - s.t;
    if (elapsed > 600) return; // too slow, ignore
    if (Math.abs(dx) < 60) return; // not enough horizontal
    if (Math.abs(dy) > 50) return; // too much vertical, it's a scroll
    if (dx < 0) nextMonth();
    else prevMonth();
  };

  // Block CRUD
  const handleAddBlock = async (data) => {
    setBlockSaving(true);
    try {
      await availabilityAPI.createBlocked(data);
      toast.success(t('toast.block_created'));
      setBlockDialogOpen(false);
      await load();
    } catch (err) {
      toast.error(err?.response?.data?.detail || t('toast.block_created_error'));
    } finally { setBlockSaving(false); }
  };

  const handleAddBatchBlock = async (data) => {
    setBlockSaving(true);
    try {
      await availabilityAPI.createBatchBlocked(data);
      toast.success(t('toast.blocks_created'));
      setBlockDialogOpen(false);
      await load();
    } catch (err) {
      toast.error(err?.response?.data?.detail || t('toast.blocks_created_error'));
    } finally { setBlockSaving(false); }
  };

  const handleDeleteBlock = async (slotId) => {
    setBlockSaving(true);
    try {
      await availabilityAPI.deleteBlocked(slotId);
      toast.success(t('toast.block_removed'));
      setBlockedSlots(prev => prev.filter(b => b.id !== slotId));
    } catch (err) {
      toast.error(err?.response?.data?.detail || t('toast.block_removed_error'));
    } finally { setBlockSaving(false); }
  };

  const handleDeleteBlockGroup = async (groupId) => {
    setBlockSaving(true);
    try {
      const res = await availabilityAPI.deleteBlockedGroup(groupId);
      toast.success(res.data?.message || t('toast.blocks_removed'));
      setBlockedSlots(prev => prev.filter(b => b.group_id !== groupId));
    } catch (err) {
      toast.error(err?.response?.data?.detail || t('toast.blocks_removed_error'));
    } finally { setBlockSaving(false); }
  };

  const eventCount = items.filter(it => it.type === 'event_occurrence').length;
  const rentalCount = items.filter(it => it.type === 'rental_order').length;
  const blockCount = blockedSlots.length;

  return (
    <AppLayout>
      <Header title={t('page.title')} subtitle={t('page.subtitle')} />
      <PageSubheader
        actions={
          <>
            <Button variant="outline" size="sm" onClick={goToday} className="gap-1 text-xs">
              {t('actions.today')}
            </Button>
            <Button
              size="sm"
              onClick={() => setBlockDialogOpen(true)}
              className="gap-1.5 bg-red-600 hover:bg-red-700 text-white"
            >
              <Ban className="h-3.5 w-3.5" /> {t('actions.block_slot')}
            </Button>
          </>
        }
      />

      <div className="p-4 md:p-6 max-w-6xl mx-auto space-y-4">
        {/* Month navigation */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={prevMonth} className="h-8 w-8 p-0">
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <h2 className="text-lg font-semibold min-w-[12rem] text-center">
              {t(`months.${month - 1}`)} {year}
            </h2>
            <Button variant="outline" size="sm" onClick={nextMonth} className="h-8 w-8 p-0">
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            {eventCount > 0 && (
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-purple-500" /> {t('summary.events', { count: eventCount })}
              </span>
            )}
            {rentalCount > 0 && (
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-orange-500" /> {t('summary.rentals', { count: rentalCount })}
              </span>
            )}
            {blockCount > 0 && (
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-red-400" /> {t('summary.blocks', { count: blockCount })}
              </span>
            )}
            {eventCount === 0 && rentalCount === 0 && blockCount === 0 && !loading && (
              <span>{t('empty.month')}</span>
            )}
          </div>
        </div>

        {/* View tabs: Agenda vs Rentals vs Lista (Onda 15 Fase 2) */}
        <div className="flex items-center gap-4 flex-wrap">
          <div className="flex rounded-lg border overflow-hidden">
            <button
              onClick={() => setCalView('agenda')}
              className={`px-4 py-1.5 text-xs font-medium transition-colors ${
                calView === 'agenda' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              {t('views.agenda')}
            </button>
            {hasRentals && (
              <button
                onClick={() => setCalView('rentals')}
                className={`px-4 py-1.5 text-xs font-medium transition-colors ${
                  calView === 'rentals' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                {t('views.rentals')}
              </button>
            )}
            <button
              onClick={() => setCalView('list')}
              className={`px-4 py-1.5 text-xs font-medium transition-colors border-l ${
                calView === 'list' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground'
              }`}
              title="Vista elenco — trova ordini e consulenze senza cliccare giorni"
            >
              📋 {t('views.list', { defaultValue: 'Lista' })}
            </button>
          </div>

          {calView === 'agenda' && (
            <span className="text-[11px] text-muted-foreground">{t('views.agenda_subtitle')}</span>
          )}

          {/* Onda 15 Fase 4 — quick range chips. Filter the items fed to
              the calendar body without touching the month nav. "Oggi" and
              "Settimana" highlight a narrower timeframe; "Mese" is the
              default (no filter). Useful when the admin wants to focus on
              'what do I need to do today/this week' without leaving the
              current month view. */}
          <div className="flex items-center gap-1 rounded-lg border bg-card p-1 ml-auto">
            {[
              { key: 'today',   label: '📅 Oggi' },
              { key: 'week',    label: '📆 Settimana' },
              { key: 'month',   label: 'Mese' },
            ].map(opt => (
              <button
                key={opt.key}
                onClick={() => setQuickRange(opt.key)}
                className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-colors ${
                  quickRange === opt.key
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {/* Rental product filter — visual chip row shown below the main tab
            bar when the user is on the "Affitti" view. Each chip includes an
            icon, the product name, and a badge with the number of days
            currently blocked in the loaded range so the merchant sees where
            the activity is concentrated at a glance. The "Tutti" chip
            aggregates the total. Layout is flex-wrap so it degrades well on
            mobile (chips break to new lines; min target ≥44px for touch). */}
        {calView === 'rentals' && rentalProducts.length > 1 && (
          <div className="flex flex-wrap gap-2 items-center">
            <button
              type="button"
              onClick={() => setProductFilter('')}
              className={`flex items-center gap-2 rounded-xl border px-3 py-2 text-sm font-medium transition-colors ${
                !productFilter
                  ? 'bg-orange-50 border-orange-500 text-orange-900'
                  : 'bg-white border-gray-200 text-gray-700 hover:border-gray-900'
              }`}
            >
              <span aria-hidden>📋</span>
              <span>{t('views.filter_all')}</span>
              <span className={`inline-flex items-center justify-center min-w-[1.5rem] px-1.5 py-0.5 rounded-full text-[10px] font-semibold ${
                !productFilter ? 'bg-orange-200 text-orange-900' : 'bg-gray-100 text-gray-600'
              }`}>
                {totalRentalBlocks}
              </span>
            </button>
            {rentalProducts.map(p => {
              const active = productFilter === p.id;
              const count = blocksCountByProduct[p.id] || 0;
              return (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => setProductFilter(active ? '' : p.id)}
                  className={`flex items-center gap-2 rounded-xl border px-3 py-2 text-sm font-medium transition-colors ${
                    active
                      ? 'bg-orange-50 border-orange-500 text-orange-900'
                      : 'bg-white border-gray-200 text-gray-700 hover:border-gray-900'
                  }`}
                  title={p.name}
                >
                  <span aria-hidden>🔑</span>
                  <span className="max-w-[14rem] truncate">{p.name}</span>
                  <span className={`inline-flex items-center justify-center min-w-[1.5rem] px-1.5 py-0.5 rounded-full text-[10px] font-semibold ${
                    active ? 'bg-orange-200 text-orange-900' : 'bg-gray-100 text-gray-600'
                  }`}>
                    {count}
                  </span>
                </button>
              );
            })}
          </div>
        )}

        {/* Onda 15 Fase 5 — mobile swipe hint. Visible only on xs screens
            and only on the month grid (not in list view). Teaches the
            user they can swipe the calendar left/right to navigate. */}
        {!loading && calView !== 'list' && (
          <p className="md:hidden text-[10px] text-center text-muted-foreground italic">
            ← swipe per cambiare mese →
          </p>
        )}

        {/* Onda 15 Fase 3 — compact legend strip. Mirrors the emoji + accent
            used in DayCell / ListView so users learn the mapping once. Only
            renders when there's at least one item in the month. */}
        {!loading && items.length > 0 && (
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-muted-foreground px-1">
            <span className="font-medium text-foreground/80">Legenda:</span>
            <span className="inline-flex items-center gap-1">
              <span className="w-2 h-3 bg-purple-400 rounded-sm" aria-hidden />
              <span>🎟 Eventi</span>
            </span>
            <span className="inline-flex items-center gap-1">
              <span className="w-2 h-3 bg-indigo-400 rounded-sm" aria-hidden />
              <span>📅 Consulenze</span>
            </span>
            <span className="inline-flex items-center gap-1">
              <span className="w-2 h-3 bg-orange-400 rounded-sm" aria-hidden />
              <span>🧾 Affitti</span>
            </span>
            <span className="inline-flex items-center gap-1">
              <Ban className="h-3 w-3 text-red-400" />
              <span>Blocchi</span>
            </span>
          </div>
        )}

        {/* Calendar body — month grid OR list view (Onda 15 Fase 2) */}
        {loading ? (
          <div className="flex justify-center py-16"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
        ) : calView === 'list' ? (
          <CalendarListView
            items={filteredItems}
            year={year}
            month={month}
            // Routing dispatched centrally — see utils/productPaths.js. Keeps
            // the calendar agnostic of how each typed product chooses to
            // present its admin dashboard, so adding a new type tomorrow
            // is one line in productPaths instead of two here.
            onNavigate={(item) => {
              const url = calendarItemPath(item);
              if (url) navigate(url);
            }}
          />
        ) : (
          <div
            className="rounded-xl border bg-card overflow-hidden touch-pan-y"
            onTouchStart={handleTouchStart}
            onTouchEnd={handleTouchEnd}
          >
            <div className="grid grid-cols-7 border-b bg-muted/30">
              {(t('days', { returnObjects: true }) || []).map(d => (
                <div key={d} className="px-2 py-2 text-center text-xs font-medium text-muted-foreground">{d}</div>
              ))}
            </div>
            <div className="grid grid-cols-7 gap-px bg-gray-200 p-px">
              {grid.map((day, i) => (
                <div key={i} className="bg-white">
                  <DayCell
                    day={day} year={year} month={month} items={filteredItems} blockedSlots={quickRange === 'month' ? blockedSlots : []}
                    isToday={day && todayStr === `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`}
                    isSelected={day && selectedDate === `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`}
                    onSelect={setSelectedDate}
                  />
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Day detail — Onda 15 Fase 1: bottom-sheet on mobile, inline on desktop */}
        {selectedDate && (
          <>
            {/* Mobile-only backdrop. Tap to dismiss. Hidden on md+ where the
                panel lives inline under the calendar grid. */}
            <div
              className="fixed inset-0 bg-black/40 z-40 md:hidden"
              onClick={() => setSelectedDate(null)}
              aria-hidden="true"
            />
            {/* Container wraps DayDetail with viewport-adaptive positioning:
                - mobile: fixed bottom sheet, rounded-t, max 85vh, scrollable
                - tablet+: static inline block (same as before) */}
            <div
              className={`
                md:static fixed inset-x-0 bottom-0 z-50 md:z-auto
                max-h-[85vh] md:max-h-none overflow-y-auto md:overflow-visible
                bg-card rounded-t-2xl md:rounded-xl
                shadow-2xl md:shadow-none md:border md:mt-4
              `}
              role="dialog"
              aria-modal="true"
              aria-label="Dettaglio giornata"
            >
              {/* Mobile drag handle — pure visual, helps convey "I'm a sheet" */}
              <div className="md:hidden flex justify-center pt-2 pb-1" aria-hidden="true">
                <div className="w-10 h-1 rounded-full bg-gray-300"></div>
              </div>
              <DayDetail
                dateStr={selectedDate} items={filteredItems} blockedSlots={blockedSlots} allBlockedSlots={blockedSlots}
                onClose={() => setSelectedDate(null)}
                // Same dispatch as CalendarListView — see utils/productPaths.
                onNavigate={(item) => {
                  const url = calendarItemPath(item);
                  if (url) navigate(url);
                }}
                onDeleteBlock={handleDeleteBlock}
                onDeleteBlockGroup={handleDeleteBlockGroup}
                blockSaving={blockSaving}
              />
            </div>
          </>
        )}
      </div>

      {/* Block Slot Dialog */}
      <BlockSlotDialog
        open={blockDialogOpen}
        onClose={setBlockDialogOpen}
        onSubmit={handleAddBlock}
        onSubmitBatch={handleAddBatchBlock}
        saving={blockSaving}
        prefilledDate={selectedDate}
        calView={calView}
        rentalProducts={rentalProducts}
      />
    </AppLayout>
  );
}
