/**
 * StorefrontCards — co-located storefront card components + helpers.
 *
 * Phase 7.3 — extracted from StorefrontPage.js so the new
 * `ProductGrid` (and the upcoming `CategoryPage` in Phase 7.5) can
 * render the same cards without duplicating ~500 lines of code.
 *
 * What's in here
 * --------------
 *   Helpers
 *     - fmtPrice                  locale-aware currency formatter
 *     - fmtOccDate                event occurrence date formatter
 *     - computeRentalMultiplier   rental qty multiplier (days/weeks/months)
 *     - resolveTransactionModeCopy  i18n CTA copy by transaction_mode
 *
 *   Big components
 *     - BookingCalendarModal    mini-calendar modal for booking products
 *     - ProductCard             grid card with inline pickers (legacy
 *                               products without a dedicated landing)
 *
 *   Thin wrappers over CommerceCard (one per landing-page type)
 *     - EventOccurrenceCard     /e/:org/:occurrence_slug
 *     - ServiceCard             /p/:org/:product_slug
 *     - ReservationCard         /r/:org/:product_slug
 *     - PhysicalCard            /ph/:org/:product_slug
 *     - DigitalCard             /dg/:org/:product_slug
 *     - CourseCard              /co/:org/:product_slug
 *
 * Design contract
 * ---------------
 * Every card is "stateless" in the sense that it owns no cart state —
 * the parent page passes the slot/qty/date setters as props. This keeps
 * the cards reusable across StorefrontPage (legacy single-page view)
 * and CategoryPage (Phase 7.5 per-category routes).
 *
 * The cards rely on:
 *   - useTranslation('storefront')           inside each card
 *   - Link from react-router-dom             for landing-page navigation
 *   - CommerceCard + variant prop builders   for the 6 thin wrappers
 *   - ITEM_TYPE_LABELS / badge helpers       for the inline ProductCard
 *
 * Bundle impact: ZERO runtime change — pure file move with named
 * exports. Webpack just splits one big bundle into a slightly larger
 * graph; downstream code-splitting is unaffected.
 */

import React, { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

import i18nInstance from '../../../i18n';
import CommerceCard from './CommerceCard';
import {
  buildEventCardProps,
  buildServiceCardProps,
  buildReservationCardProps,
  buildPhysicalCardProps,
  buildDigitalCardProps,
  buildCourseCardProps,
} from './CommerceCardVariants';
import {
  ITEM_TYPE_LABELS,
  getItemTypeBadgeClass,
} from '../../../constants/itemTypes';


// ── Helpers ────────────────────────────────────────────────────────────────


/**
 * Locale-aware currency formatter. Used by ProductCard for unit-price
 * display. The 6 thin-wrapper cards use the price formatter inside
 * CommerceCardVariants instead.
 */
export const fmtPrice = (v, currency = 'EUR', locale) => {
  if (v == null) return '';
  const loc = locale || i18nInstance.language || 'it-IT';
  return new Intl.NumberFormat(loc, {
    style: 'currency', currency, maximumFractionDigits: 2,
  }).format(v);
};


/**
 * Locale-aware occurrence date formatter. Used by ProductCard for the
 * event-ticket occurrence select dropdown.
 */
export const fmtOccDate = (iso, locale = 'it-IT') => {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleDateString(locale, {
    weekday: 'short', day: 'numeric', month: 'short', year: 'numeric',
  }) + ' — ' + d.toLocaleTimeString(locale, {
    hour: '2-digit', minute: '2-digit',
  });
};


/**
 * Compute rental duration multiplier from date range and rental_unit.
 * Returns the number of rental_units (giorni, settimane, mesi) to
 * multiply by unit_price.
 *
 * Kept exported because OrderSummary in StorefrontPage uses it to
 * display the cart row total for rental products.
 */
export function computeRentalMultiplier(rentalDate, rentalUnit) {
  if (!rentalDate?.from) return 1;
  const from = new Date(rentalDate.from + 'T00:00');
  const to = rentalDate.to ? new Date(rentalDate.to + 'T00:00') : from;
  const days = Math.max(1, Math.round((to - from) / 86400000) + 1);
  const unit = (rentalUnit || 'giorno').toLowerCase();
  if (unit === 'settimana') return Math.ceil(days / 7);
  if (unit === 'mese') return Math.ceil(days / 30);
  return days; // giorno (default), ora treated as day for now
}


/**
 * Resolve the per-transaction-mode CTA / modal copy via i18n.
 *
 * Three modes ship: `direct` (immediate payment), `request` (merchant
 * confirms), `approval` (merchant approves). Anything unknown falls
 * back to the `request` copy — same default the legacy hardcoded map
 * produced when handed an unexpected mode string.
 */
export function resolveTransactionModeCopy(t, mode) {
  const m = ['direct', 'request', 'approval'].includes(mode) ? mode : 'request';
  return {
    headerCta:     t(`storefront:transactionMode.${m}.headerCta`),
    modalTitle:    t(`storefront:transactionMode.${m}.modalTitle`),
    modalDesc:     t(`storefront:transactionMode.${m}.modalDesc`),
    submitBtn:     t(`storefront:transactionMode.${m}.submitBtn`),
    inquiryToggle: t(`storefront:transactionMode.${m}.inquiryToggle`),
  };
}


// ── BookingCalendarModal ────────────────────────────────────────────────────


/**
 * Mini-calendar modal for legacy `booking` item_type products. Renders
 * a month grid + per-day slot list, gated by `bookingSlot._pickerOpen`.
 *
 * Mounted at the page level (not inside ProductGrid) because it's a
 * SINGLE modal shared across all booking products — the parent finds
 * the product with `_pickerOpen=true` and passes ITS slot state.
 *
 * Note: `booking` is the deprecated predecessor of `service`. Once
 * Onda 16 Fase 6 migration is fully done this component can be
 * removed entirely; for now it stays for legacy products.
 */
export function BookingCalendarModal({
  availableSlots, bookingSlot, onBookingSlotChange, onQtyChange,
}) {
  const { t, i18n } = useTranslation('storefront');
  // Localized abbreviated weekday headers (Mon..Sun). Resolved on every
  // render so a language switch repaints the calendar without remount.
  const WEEKDAYS_SHORT = [
    t('storefront:calendar.weekdayShort.mon'),
    t('storefront:calendar.weekdayShort.tue'),
    t('storefront:calendar.weekdayShort.wed'),
    t('storefront:calendar.weekdayShort.thu'),
    t('storefront:calendar.weekdayShort.fri'),
    t('storefront:calendar.weekdayShort.sat'),
    t('storefront:calendar.weekdayShort.sun'),
  ];
  const isOpen = bookingSlot?._pickerOpen;
  const today = new Date();
  const [viewYear, setViewYear] = useState(today.getFullYear());
  const [viewMonth, setViewMonth] = useState(today.getMonth());
  const [tempSlot, setTempSlot] = useState({ date: '', start: '', end: '' });

  // Sync temp with existing selection when opening
  useEffect(() => {
    if (isOpen) {
      setTempSlot({ date: bookingSlot?.date || '', start: bookingSlot?.start || '', end: bookingSlot?.end || '' });
      if (bookingSlot?.date) {
        const d = new Date(bookingSlot.date + 'T12:00');
        setViewYear(d.getFullYear());
        setViewMonth(d.getMonth());
      }
    }
  }, [isOpen]); // eslint-disable-line react-hooks/exhaustive-deps

  const slotsByDate = useMemo(() => {
    const map = {};
    for (const day of (availableSlots || [])) map[day.date] = day.slots || [];
    return map;
  }, [availableSlots]);

  const grid = useMemo(() => {
    const daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate();
    let startDow = new Date(viewYear, viewMonth, 1).getDay() - 1;
    if (startDow < 0) startDow = 6;
    const cells = [];
    for (let i = 0; i < startDow; i++) cells.push(null);
    for (let d = 1; d <= daysInMonth; d++) cells.push(d);
    return cells;
  }, [viewYear, viewMonth]);

  const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
  const fmtDate = (day) => `${viewYear}-${String(viewMonth + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
  const prevMonth = () => { if (viewMonth === 0) { setViewMonth(11); setViewYear(y => y - 1); } else setViewMonth(m => m - 1); };
  const nextMonth = () => { if (viewMonth === 11) { setViewMonth(0); setViewYear(y => y + 1); } else setViewMonth(m => m + 1); };
  const monthLabel = new Date(viewYear, viewMonth).toLocaleDateString(i18n.language, { month: 'long', year: 'numeric' });
  const selectedDaySlots = tempSlot.date ? (slotsByDate[tempSlot.date] || []) : [];
  const canConfirm = tempSlot.date && tempSlot.start && tempSlot.end;

  const handleClose = () => onBookingSlotChange({ ...bookingSlot, _pickerOpen: false });
  const handleConfirm = () => {
    onBookingSlotChange({ date: tempSlot.date, start: tempSlot.start, end: tempSlot.end });
    onQtyChange(1);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-end sm:items-center justify-center" onClick={handleClose}>
      <div
        className="bg-white rounded-t-2xl sm:rounded-2xl shadow-xl w-full max-w-sm max-h-[85vh] overflow-y-auto"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 pt-5 pb-2">
          <h3 className="font-bold text-base">{t('storefront:calendar.pickerTitle')}</h3>
          <button type="button" onClick={handleClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">&times;</button>
        </div>

        <div className="px-5 pb-5 space-y-4">
          {/* Month nav */}
          <div className="flex items-center justify-between">
            <button type="button" onClick={prevMonth} className="w-8 h-8 rounded-full border flex items-center justify-center text-gray-500 hover:bg-gray-100 text-lg">‹</button>
            <span className="text-sm font-semibold capitalize">{monthLabel}</span>
            <button type="button" onClick={nextMonth} className="w-8 h-8 rounded-full border flex items-center justify-center text-gray-500 hover:bg-gray-100 text-lg">›</button>
          </div>

          {/* Weekday headers */}
          <div className="grid grid-cols-7 gap-1">
            {WEEKDAYS_SHORT.map(d => (
              <div key={d} className="text-center text-[10px] font-medium text-gray-400 py-0.5">{d}</div>
            ))}
          </div>

          {/* Day grid */}
          <div className="grid grid-cols-7 gap-1">
            {grid.map((day, i) => {
              if (day === null) return <div key={i} className="h-10" />;
              const dateStr = fmtDate(day);
              const isPast = dateStr < todayStr;
              const slots = slotsByDate[dateStr] || [];
              const hasSlots = slots.length > 0 && !isPast;
              const isSelected = tempSlot.date === dateStr;
              const isToday = dateStr === todayStr;
              return (
                <button
                  key={i} type="button" disabled={!hasSlots}
                  onClick={() => setTempSlot({ date: dateStr, start: '', end: '' })}
                  className={`h-10 rounded-xl text-sm font-medium transition-all ${
                    isSelected ? 'bg-[var(--sf-accent,#111827)] text-[var(--sf-accent-fg,#ffffff)] shadow-md'
                    : hasSlots ? 'bg-white border border-gray-200 hover:border-gray-900 text-gray-900'
                    : 'text-gray-200 cursor-not-allowed'
                  } ${isToday && !isSelected ? 'ring-1 ring-gray-400' : ''}`}
                >
                  {day}
                </button>
              );
            })}
          </div>

          {/* Slot grid */}
          {tempSlot.date && (
            <div>
              <p className="text-xs font-medium text-gray-500 mb-2">
                {new Date(tempSlot.date + 'T12:00').toLocaleDateString(i18n.language, { weekday: 'long', day: 'numeric', month: 'long' })}
              </p>
              {selectedDaySlots.length > 0 ? (
                <div className="grid grid-cols-4 gap-1.5">
                  {selectedDaySlots.map(s => {
                    const active = tempSlot.start === s.start && tempSlot.end === s.end;
                    return (
                      <button key={`${s.start}-${s.end}`} type="button"
                        onClick={() => setTempSlot(prev => ({ ...prev, start: s.start, end: s.end }))}
                        className={`rounded-lg px-2 py-2.5 text-sm font-medium transition-all ${
                          active ? 'bg-[var(--sf-accent,#111827)] text-[var(--sf-accent-fg,#ffffff)] shadow-md' : 'bg-white border border-gray-200 hover:border-gray-900'
                        }`}
                      >
                        {s.start}
                      </button>
                    );
                  })}
                </div>
              ) : (
                <p className="text-xs text-gray-400 italic text-center py-3">{t('storefront:calendar.noSlots')}</p>
              )}
            </div>
          )}

          {/* Confirm button */}
          <button
            type="button"
            disabled={!canConfirm}
            onClick={handleConfirm}
            className={`w-full rounded-xl py-3 text-sm font-semibold transition-all ${
              canConfirm
                ? 'bg-[var(--sf-accent,#111827)] text-[var(--sf-accent-fg,#ffffff)] hover:bg-[var(--sf-accent-hover,#1f2937)] shadow-md'
                : 'bg-gray-100 text-gray-400 cursor-not-allowed'
            }`}
          >
            {canConfirm
              ? t('storefront:calendar.confirmWithDate', {
                  date: new Date(tempSlot.date + 'T12:00').toLocaleDateString(i18n.language, { day: 'numeric', month: 'short' }),
                  start: tempSlot.start,
                  end: tempSlot.end,
                })
              : t('storefront:calendar.confirmPlaceholder')}
          </button>
        </div>
      </div>
    </div>
  );
}


// ── Thin CommerceCard wrappers ──────────────────────────────────────────────


/**
 * EventOccurrenceCard (F2) — a distinctive tile for a single event
 * occurrence. One card per occurrence (not per product). Deep-links
 * to /e/:org/:occurrence_slug.
 */
export function EventOccurrenceCard({ product, occurrence, orgSlug, currency }) {
  const { t, i18n } = useTranslation('storefront');
  const cardProps = buildEventCardProps({ product, occurrence, orgSlug, currency, t, locale: i18n.language });
  return <CommerceCard {...cardProps} />;
}


/**
 * Service (consulenza) card — deep-links to /p/:org/:slug
 * (ProductLandingPage). User picks option + slot before checkout.
 */
export function ServiceCard({ product, orgSlug, currency }) {
  const { t, i18n } = useTranslation('storefront');
  const cardProps = buildServiceCardProps({ product, orgSlug, currency, t, locale: i18n.language });
  return <CommerceCard {...cardProps} />;
}


/**
 * Reservation (rental) card — deep-links to /r/:org/:slug
 * (ReservationLandingPage). Applies to rental products of both
 * flavors (range + slot) as long as they have a slug.
 */
export function ReservationCard({ product, orgSlug, currency }) {
  const { t, i18n } = useTranslation('storefront');
  const cardProps = buildReservationCardProps({ product, orgSlug, currency, t, locale: i18n.language });
  return <CommerceCard {...cardProps} />;
}


/**
 * Physical product card — deep-links to /ph/:org/:slug
 * (PhysicalLandingPage). Used for physical products with a slug;
 * legacy slug-less products fall back to inline ProductCard.
 */
export function PhysicalCard({ product, orgSlug, currency }) {
  const { t, i18n } = useTranslation('storefront');
  const cardProps = buildPhysicalCardProps({ product, orgSlug, currency, t, locale: i18n.language });
  return <CommerceCard {...cardProps} />;
}


/**
 * Digital product card — deep-links to /dg/:org/:slug
 * (DigitalLandingPage). Only published digitals with a slug AND a
 * file attached surface here; the landing endpoint filters the rest.
 */
export function DigitalCard({ product, orgSlug, currency }) {
  const { t, i18n } = useTranslation('storefront');
  const cardProps = buildDigitalCardProps({ product, orgSlug, currency, t, locale: i18n.language });
  return <CommerceCard {...cardProps} />;
}


/**
 * Course card — deep-links to /co/:org/:slug (CourseLandingPage).
 * Account required at checkout; landing renders curriculum + CTA.
 */
export function CourseCard({ product, orgSlug, currency }) {
  const { t, i18n } = useTranslation('storefront');
  const cardProps = buildCourseCardProps({ product, orgSlug, currency, t, locale: i18n.language });
  return <CommerceCard {...cardProps} />;
}


// ── Inline ProductCard (legacy fallback) ───────────────────────────────────


/**
 * Inline product card with on-card pickers (qty / occurrence /
 * rental date range / booking slot button).
 *
 * Used for any product that DOESN'T have a dedicated landing page
 * (i.e. no slug, OR an item_type that doesn't have a landing route):
 *   - legacy products without a slug
 *   - inquiry-mode products
 *   - the deprecated `booking` item_type
 *
 * Modern products with a slug render via the thin wrapper cards above
 * (EventOccurrenceCard, ServiceCard, etc.) which deep-link to the
 * relevant landing page.
 */
export function ProductCard({
  product, qty, onQtyChange,
  selectedOccurrence, onOccurrenceChange,
  rentalDate, onRentalDateChange,
  bookingSlot, onBookingSlotChange,
  availableSlots, currency, orgSlug,
}) {
  const { t, i18n } = useTranslation('storefront');
  const isInquiry = product.price_mode === 'inquiry';
  const isEvent = product.item_type === 'event_ticket';
  const isRental = product.item_type === 'rental';
  const isBooking = product.item_type === 'booking';
  const typeLabel = ITEM_TYPE_LABELS[product.item_type];
  const unitLabel = product.unit_label || product.unit;
  const occurrences = product.occurrences || [];

  // For event_ticket: effective price may come from occurrence's price_override
  const effectivePrice = isEvent && selectedOccurrence?.price_override != null
    ? selectedOccurrence.price_override
    : product.unit_price;

  return (
    // Onda 13 fix — h-full stretches the card to the grid cell height
    // so sibling cards in the same row share the same height. aspect-[16/10]
    // matches EventOccurrenceCard so the hero image is proportional (not
    // stretched on tall images, not squashed on wide ones).
    // min-h-[28rem] gives cards consistent visual weight across sections
    // (Prossimi eventi vs. Catalogo) even when the product card has less
    // content than an event card.
    <div className="h-full min-h-[28rem] rounded-2xl border bg-white shadow-sm overflow-hidden flex flex-col">
      <div className="relative aspect-[16/10] overflow-hidden bg-gray-100">
        {product.image_url ? (
          <img src={product.image_url} alt={product.name} className="w-full h-full object-cover" />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-gray-300 text-4xl">
            {product.name?.charAt(0)?.toUpperCase()}
          </div>
        )}
      </div>
      <div className="p-4 flex-1 flex flex-col">
        <div className="flex items-start justify-between gap-2">
          <h3 className="font-semibold text-base">{product.name}</h3>
          {typeLabel && (
            <span className={`shrink-0 text-[10px] px-1.5 py-0.5 rounded-full font-medium ${getItemTypeBadgeClass(product.item_type) || 'bg-blue-50 text-blue-600'}`}>{typeLabel}</span>
          )}
        </div>
        {product.category && <p className="text-xs text-gray-500 mt-0.5">{product.category}</p>}
        {product.stock_quantity != null && product.stock_quantity <= 0 && (
          <p className="text-xs text-red-600 font-medium mt-0.5">{t('storefront:product.soldOut')}</p>
        )}
        {product.stock_quantity != null && product.stock_quantity > 0 && product.stock_quantity <= 5 && (
          <p className="text-xs text-amber-600 mt-0.5">{t('storefront:product.lastN', { count: product.stock_quantity })}</p>
        )}
        {product.item_type === 'service' && product.duration_label && (
          <p className="text-xs text-gray-400 mt-0.5">{product.duration_label}</p>
        )}
        {product.item_type === 'rental' && product.rental_unit && (
          <p className="text-xs text-gray-400 mt-0.5">{t('storefront:product.perUnit', { unit: product.rental_unit })}</p>
        )}
        {product.description && <p className="text-sm text-gray-600 mt-2 line-clamp-2">{product.description}</p>}

        {/* Rental date picker */}
        {isRental && (
          <div className="mt-3 space-y-1.5">
            <label className="block text-xs font-medium text-gray-500">{t('storefront:rental.periodLabel')}</label>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <span className="block text-[11px] text-gray-400 mb-0.5">{t('storefront:rental.fromLabel')}</span>
                <input
                  type="date"
                  value={rentalDate?.from || ''}
                  onChange={(e) => {
                    onRentalDateChange({ ...rentalDate, from: e.target.value });
                    if (!e.target.value) onQtyChange(0);
                  }}
                  className="w-full rounded-lg border border-gray-300 px-2 py-1.5 text-sm focus:ring-2 focus:ring-gray-800 focus:border-transparent outline-none"
                />
              </div>
              <div>
                <span className="block text-[11px] text-gray-400 mb-0.5">{t('storefront:rental.toLabel')}</span>
                <input
                  type="date"
                  value={rentalDate?.to || ''}
                  min={rentalDate?.from || ''}
                  onChange={(e) => onRentalDateChange({ ...rentalDate, to: e.target.value })}
                  className="w-full rounded-lg border border-gray-300 px-2 py-1.5 text-sm focus:ring-2 focus:ring-gray-800 focus:border-transparent outline-none"
                />
              </div>
            </div>
            <input
              type="text"
              value={rentalDate?.notes || ''}
              onChange={(e) => onRentalDateChange({ ...rentalDate, notes: e.target.value })}
              placeholder={t('storefront:rental.notesPlaceholder')}
              maxLength={500}
              className="w-full rounded-lg border border-gray-300 px-2 py-1.5 text-sm focus:ring-2 focus:ring-gray-800 focus:border-transparent outline-none"
            />
          </div>
        )}

        {/* Booking — compact button + modal picker */}
        {isBooking && (() => {
          const hasSelection = bookingSlot?.date && bookingSlot?.start && bookingSlot?.end;
          return (
            <div className="mt-3 space-y-2">
              {hasSelection ? (
                <button
                  type="button"
                  onClick={() => onBookingSlotChange({ ...bookingSlot, _pickerOpen: true })}
                  className="w-full rounded-lg border border-gray-900 bg-gray-50 px-3 py-2.5 text-sm text-left flex items-center justify-between hover:bg-gray-100 transition-colors"
                >
                  {(() => {
                    const fmtLong = (iso) => new Date(iso + 'T12:00').toLocaleDateString(i18n.language, { weekday: 'long', day: 'numeric', month: 'long' });
                    const crossDay = bookingSlot.date_end && bookingSlot.date_end !== bookingSlot.date;
                    return (
                      <span>
                        {crossDay ? (
                          <span className="font-medium">
                            {fmtLong(bookingSlot.date)} {bookingSlot.start}
                            <span className="text-gray-500"> → </span>
                            {fmtLong(bookingSlot.date_end)} {bookingSlot.end}
                          </span>
                        ) : (
                          <>
                            <span className="font-medium">{fmtLong(bookingSlot.date)}</span>
                            <span className="text-gray-500"> · {bookingSlot.start}–{bookingSlot.end}</span>
                          </>
                        )}
                      </span>
                    );
                  })()}
                  <span className="text-xs text-gray-400">{t('storefront:booking.changeBtn')}</span>
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => onBookingSlotChange({ date: '', start: '', end: '', _pickerOpen: true })}
                  disabled={availableSlots === null}
                  className="w-full rounded-lg border-2 border-dashed border-gray-300 px-3 py-3 text-sm text-gray-500 hover:border-gray-400 hover:text-gray-700 transition-colors flex items-center justify-center gap-2"
                >
                  {availableSlots === null ? (
                    <>
                      <span className="w-3.5 h-3.5 border-2 border-gray-300 border-t-gray-500 rounded-full animate-spin" />
                      {t('storefront:common.loading')}
                    </>
                  ) : (
                    <>{t('storefront:booking.openPickerCta')}</>
                  )}
                </button>
              )}
            </div>
          );
        })()}

        {/* Occurrence picker for event_ticket */}
        {isEvent && occurrences.length > 0 && (
          <div className="mt-3">
            <label className="block text-xs font-medium text-gray-500 mb-1">{t('storefront:event.pickDate')}</label>
            <select
              value={selectedOccurrence?.id || ''}
              onChange={(e) => {
                const occ = occurrences.find(o => o.id === e.target.value) || null;
                onOccurrenceChange(occ);
                if (!occ) onQtyChange(0);
              }}
              className="w-full rounded-lg border border-gray-300 px-2 py-1.5 text-sm focus:ring-2 focus:ring-gray-800 focus:border-transparent outline-none"
            >
              <option value="">{t('storefront:event.selectDateOption')}</option>
              {occurrences.map(occ => {
                const soldOut = occ.capacity != null && occ.remaining != null && occ.remaining <= 0;
                const remainingLabel = occ.capacity != null && occ.remaining != null && occ.remaining > 0
                  ? ` (${t('storefront:event.seatsRemaining', { count: occ.remaining })})`
                  : '';
                return (
                  <option key={occ.id} value={occ.id} disabled={soldOut}>
                    {fmtOccDate(occ.start_at, i18n.language)}{occ.location ? ` · ${occ.location}` : ''}{soldOut ? ` ${t('storefront:event.soldOutSuffix')}` : remainingLabel}
                  </option>
                );
              })}
            </select>
            {selectedOccurrence?.remaining != null && selectedOccurrence.remaining > 0 && (
              <p className="text-xs text-amber-600 mt-1">
                {t('storefront:event.seatsRemainingFull', { count: selectedOccurrence.remaining })}
              </p>
            )}
            {selectedOccurrence?.remaining != null && selectedOccurrence.remaining <= 0 && (
              <p className="text-xs text-red-600 font-medium mt-1">{t('storefront:event.soldOut')}</p>
            )}
          </div>
        )}
        {isEvent && occurrences.length === 0 && (
          <p className="mt-3 text-xs text-gray-400 italic">{t('storefront:event.noDates')}</p>
        )}

        <div className="mt-auto pt-3 flex items-center justify-between">
          {isInquiry ? (
            <span className="text-sm font-medium text-gray-500">{t('storefront:product.priceOnRequest')}</span>
          ) : (
            <span className="text-lg font-bold">
              {fmtPrice(effectivePrice, currency)}
              {unitLabel && <span className="text-xs text-gray-400 font-normal ml-1">/ {unitLabel}</span>}
            </span>
          )}
          {/* Onda 13 — services con slug aprono la landing dedicata
              (/p/:org/:slug). Il cliente lì sceglie opzione + slot
              e poi arriva al checkout con preloadCart.
              Fallback: se il servizio non ha slug (legacy), resta
              il qty control inline. */}
          {product.item_type === 'service' && product.slug && orgSlug ? (
            <Link
              to={`/p/${orgSlug}/${product.slug}`}
              className="rounded-md bg-[var(--sf-accent,#111827)] text-[var(--sf-accent-fg,#ffffff)] px-3 py-1.5 text-xs font-semibold hover:bg-[var(--sf-accent-hover,#1f2937)]"
            >{t('storefront:product.discoverCta')}</Link>
          ) : !isInquiry && (!isEvent || selectedOccurrence) && (!isRental || rentalDate?.from) && (!isBooking || bookingSlot?.start) && (() => {
            // Capacity limit: events use occurrence remaining, physical uses stock_quantity
            const stockMax = product.stock_quantity != null ? product.stock_quantity : 99;
            const maxQty = isEvent && selectedOccurrence?.remaining != null
              ? selectedOccurrence.remaining
              : stockMax;
            const atMax = qty >= maxQty;
            return (
              <div className="flex items-center gap-1">
                <button
                  onClick={() => onQtyChange(Math.max(0, qty - 1))}
                  className="w-8 h-8 rounded-full border text-center text-lg hover:bg-gray-100"
                >-</button>
                <span className="w-8 text-center font-medium">{qty}</span>
                <button
                  onClick={() => !atMax && onQtyChange(qty + 1)}
                  disabled={atMax}
                  className={`w-8 h-8 rounded-full border text-center text-lg ${atMax ? 'opacity-30 cursor-not-allowed' : 'hover:bg-gray-100'}`}
                >+</button>
              </div>
            );
          })()}
          {isInquiry && (
            <button
              onClick={() => onQtyChange(qty > 0 ? 0 : 1)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                qty > 0 ? 'bg-[var(--sf-accent,#111827)] text-[var(--sf-accent-fg,#ffffff)]' : 'border border-gray-300 text-gray-700 hover:bg-gray-50'
              }`}
            >
              {qty > 0 ? t('storefront:product.selected') : resolveTransactionModeCopy(t, product.transaction_mode).inquiryToggle}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
