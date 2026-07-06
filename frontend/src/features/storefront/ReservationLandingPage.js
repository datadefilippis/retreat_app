/**
 * ReservationLandingPage — public landing for rental products (Onda 16).
 *
 * Route: /r/:org_slug/:product_slug
 * Handles both reservation flavors:
 *   - range: date-range picker (B&B, cars, equipment)
 *   - slot:  single-slot time picker (meeting rooms, courts)
 *
 * UX:
 *   1. Hero (image + name + short description)
 *   2. Date / slot picker (flavor-aware)
 *   3. ProductExtrasPicker (mandatory summary + optional checkboxes + radio groups)
 *   4. Live PricePreview (debounced POST /api/orders/price-preview)
 *   5. Procedi al checkout (handoff to /s/:org_slug with preloadCart state)
 */

import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Trans, useTranslation } from 'react-i18next';
import i18nInstance from '../../i18n';
import { toast } from 'sonner';
import { storefrontAPI } from '../../api/storefront';
import ProductExtrasPicker from './components/ProductExtrasPicker';
import PricePreview, { usePricePreview } from './components/PricePreview';
import AvailabilityDayPicker from './components/AvailabilityDayPicker';
import AvailabilityRangeSlotPicker from './components/AvailabilityRangeSlotPicker';
import OpenCheckoutButton from './components/OpenCheckoutButton';
import { formatAmount } from '../../utils/currency';
import useCartCount from './hooks/useCartCount';
import StoreContextNav from './components/StoreContextNav';


function isoToday(offsetDays = 0) {
  const d = new Date();
  d.setDate(d.getDate() + offsetDays);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${dd}`;
}


function computeDayCount(from, to) {
  if (!from) return null;
  if (!to || to === from) return 1;
  try {
    const d1 = new Date(from + 'T00:00');
    const d2 = new Date(to + 'T00:00');
    const diff = Math.round((d2 - d1) / 86400000);
    return diff >= 0 ? diff + 1 : null;
  } catch { return null; }
}


// Helper — Convert a Date to YYYY-MM-DD (local time, matches the ISO strings
// we get from the backend). Kept module-local so both RangePicker and the
// proceed gate share one implementation.
function toIsoYmd(d) {
  if (!(d instanceof Date) || isNaN(d)) return null;
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}


function RangePicker({ dateFrom, dateTo, onChange, blockedDates = [] }) {
  const { t } = useTranslation('landings');
  // Convert our ISO-string state to the Date shape react-day-picker expects,
  // and vice-versa in onSelect. Using local-time parse to match how the rest
  // of the app produces YYYY-MM-DD strings.
  const selected = useMemo(() => {
    const out = {};
    if (dateFrom) out.from = new Date(dateFrom + 'T00:00');
    if (dateTo) out.to = new Date(dateTo + 'T00:00');
    return (out.from || out.to) ? out : undefined;
  }, [dateFrom, dateTo]);

  const handleSelect = (next) => {
    if (!next) {
      onChange({ dateFrom: '', dateTo: '' });
      return;
    }
    onChange({
      dateFrom: toIsoYmd(next.from) || '',
      dateTo: toIsoYmd(next.to) || '',
    });
  };

  return (
    <div className="space-y-3">
      <AvailabilityDayPicker
        mode="range"
        selected={selected}
        onSelect={handleSelect}
        blockedDates={blockedDates}
        numberOfMonths={1}
      />
      {!dateFrom && (
        <p className="text-xs text-gray-500">
          {t('landings:reservation.rangePicker.hintStart')}
        </p>
      )}
      {dateFrom && !dateTo && (
        <p className="text-xs text-gray-500">
          {t('landings:reservation.rangePicker.hintEnd')}
        </p>
      )}
      {dateFrom && dateTo && (
        <p className="text-xs text-gray-700">
          <Trans
            i18nKey="landings:reservation.rangePicker.selected"
            values={{ from: dateFrom, to: dateTo }}
            components={[<strong />, <strong />]}
          />
        </p>
      )}
    </div>
  );
}


// The ad-hoc SlotPickerSimple used a native date+time pair with no visibility
// of availability. Replaced by AvailabilitySlotPicker which loads server-
// computed slots (rules ∩ ¬blocked) and renders a carousel + time grid so
// unavailable windows are invisible to the customer instead of producing a
// late-surfacing error at submit.


export default function ReservationLandingPage() {
  const { org_slug: orgSlug, product_slug: productSlug } = useParams();
  // 7/7 — contesto negozio: i link delle card store portano ?store=1;
  // la landing mantiene la barra menu dello store (mai uscire).
  const fromStore = new URLSearchParams(window.location.search).get('store') === '1';

  const navigate = useNavigate();
  const { t } = useTranslation('landings');
  // Live cart count for the back-link badge (see hooks/useCartCount.js).
  const cartCount = useCartCount(orgSlug);

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Selection state
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [slotDate, setSlotDate] = useState('');
  const [slotStart, setSlotStart] = useState('');
  const [slotEnd, setSlotEnd] = useState('');
  // Onda 17 — cross-day end date (same value as slotDate when slot is same-day).
  const [slotDateEnd, setSlotDateEnd] = useState('');
  const [extraSelections, setExtraSelections] = useState({
    optional_ids: [],
    radio_picks: {},
  });
  // Advisory list of dates that are already booked/blocked for range flavor.
  // Populated once product.id is known; used only to surface warnings — the
  // atomic server-side guard at confirm time remains the source of truth.
  const [blockedDates, setBlockedDates] = useState([]);

  // Onda 17 — availability windows for rental flavor=slot. Replaces the
  // discrete slot grid: we now receive the free intervals per day + config
  // (min_duration, step, max_duration) so the customer can compose any
  // [start, end) subject to those constraints (incl. cross-day).
  const [slotWindows, setSlotWindows] = useState([]);
  const [slotConfig, setSlotConfig] = useState({
    min_duration_minutes: 30,
    step_minutes: 30,
    max_duration_minutes: null,
    default_duration_minutes: 60,
  });

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    storefrontAPI.getProductLanding(orgSlug, productSlug, (i18nInstance.language || 'it').slice(0, 2))
      .then(res => { if (mounted) { setData(res.data); setLoading(false); } })
      .catch(err => {
        if (!mounted) return;
        setError(err?.response?.status === 404 ? 'not_found' : 'generic');
        setLoading(false);
      });
    return () => { mounted = false; };
  }, [orgSlug, productSlug, i18nInstance.language]);

  const product = data?.product;
  const flavor = useMemo(() => {
    if (!product) return 'range';
    const f = product.reservation_flavor;
    if (f === 'range' || f === 'slot') return f;
    // Derive from rental_unit if missing on old products.
    const unit = product.rental_unit;
    if (unit === 'ora') return 'slot';
    return 'range';
  }, [product]);

  // Fetch the advisory list of already-booked dates for range flavor.
  // Window is clamped to [today, today+90d] to match the backend cap.
  useEffect(() => {
    if (!product?.id || flavor !== 'range') {
      setBlockedDates([]);
      return;
    }
    let mounted = true;
    const from = isoToday();
    const to = isoToday(90);
    storefrontAPI.getRentalBlockedDates(product.id, from, to)
      .then((res) => {
        if (!mounted) return;
        setBlockedDates(Array.isArray(res.data?.blocked_dates) ? res.data.blocked_dates : []);
      })
      .catch(() => {
        // Non-blocking: if the advisory endpoint fails we degrade to the old
        // behavior (no warning) and rely on the backend guard at submit time.
        if (mounted) setBlockedDates([]);
      });
    return () => { mounted = false; };
  }, [product?.id, flavor]);

  // Onda 17 — fetch availability windows (not a discrete grid) for
  // rental+flavor=slot products. Falls back to the legacy /slots endpoint on
  // error so a backend rollback (or misconfigured product) degrades to the
  // old picker behavior.
  useEffect(() => {
    if (!product?.id || flavor !== 'slot') {
      setSlotWindows([]);
      return;
    }
    let mounted = true;
    storefrontAPI.getRentalAvailabilityWindows(product.id, 30)
      .then((res) => {
        if (!mounted) return;
        const payload = res.data || {};
        setSlotWindows(Array.isArray(payload.days) ? payload.days : []);
        setSlotConfig({
          min_duration_minutes: Number(payload.min_duration_minutes) || 30,
          step_minutes: Number(payload.step_minutes) || 30,
          max_duration_minutes: payload.max_duration_minutes || null,
          default_duration_minutes: Number(payload.default_duration_minutes) || 60,
        });
      })
      .catch(() => {
        if (mounted) setSlotWindows([]);
      });
    return () => { mounted = false; };
  }, [product?.id, flavor]);

  // Seed default radio picks from is_default flags on first product load.
  useEffect(() => {
    if (!product?.extras) return;
    const defaults = { ...extraSelections };
    const radiosByGroup = {};
    for (const ex of product.extras) {
      if (ex.kind === 'radio_variant' && ex.is_default) {
        radiosByGroup[ex.group_key || '_default'] = ex.id;
      }
    }
    if (Object.keys(radiosByGroup).length > 0 && Object.keys(defaults.radio_picks || {}).length === 0) {
      setExtraSelections({ ...defaults, radio_picks: radiosByGroup });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [product?.id]);

  const dayCount = computeDayCount(dateFrom, dateTo);

  const { result, loading: previewLoading } = usePricePreview({
    slug: orgSlug,  // R9 — scoping org del price-preview pubblico
    productId: product?.id,
    quantity: 1,
    discountPct: 0,
    dateFrom: flavor === 'range' ? dateFrom : null,
    dateTo: flavor === 'range' ? dateTo : null,
    extraSelections,
    // Onda 17 — slot timing for hourly pricing on flavor=slot. When all four
    // are populated, the backend treats unit_price as €/hour and computes
    // multiplier = (slot_date_to+time_to − slot_date_from+time_from) / 1h.
    slotDateFrom: flavor === 'slot' ? (slotDate || null) : null,
    slotTimeFrom: flavor === 'slot' ? (slotStart || null) : null,
    slotDateTo: flavor === 'slot' ? (slotDateEnd || slotDate || null) : null,
    slotTimeTo: flavor === 'slot' ? (slotEnd || null) : null,
  });

  const currency = data?.currency || data?.store_info?.currency || 'EUR';

  // Range conflicts are prevented at selection time by AvailabilityDayPicker
  // (react-day-picker's `disabled` matcher blocks clicks on blocked days and
  // rejects ranges that cross one). The atomic server-side guard at order
  // confirm is the final backstop if any rogue selection sneaks through.
  const canProceed = flavor === 'range'
    ? !!(dateFrom && dateTo && dateTo >= dateFrom)
    // Slot flavor: same-day → slotDate+start+end; cross-day → also slotDateEnd.
    : !!(slotDate && slotStart && slotEnd && (!slotDateEnd || slotDateEnd >= slotDate));

  const handleProceed = () => {
    if (!canProceed || !product) return;
    const preloadCart = {
      productId: product.id,
      qty: 1,
      extra_selections: extraSelections,
    };
    if (flavor === 'range') {
      preloadCart.rental_date_from = dateFrom;
      preloadCart.rental_date_to = dateTo;
    } else {
      preloadCart.booking_date = slotDate;
      preloadCart.booking_start_time = slotStart;
      preloadCart.booking_end_time = slotEnd;
      // Onda 17 — cross-day end date (optional, same as booking_date for
      // same-day slots). Back-compat: when omitted the order_service
      // defaults booking_end_date to booking_date.
      if (slotDateEnd && slotDateEnd !== slotDate) {
        preloadCart.booking_end_date = slotDateEnd;
      }
    }
    navigate(`/s/${orgSlug}`, { state: { preloadCart } });
    toast.success(t('landings:reservation.toastAdded'), {
      action: {
        label: t('landings:reservation.toastAction'),
        onClick: () => navigate(`/s/${orgSlug}?checkout=1`),
      },
      duration: 4000,
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-gray-400">{t('landings:reservation.loading')}</div>
      </div>
    );
  }

  if (error === 'not_found') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
        <div className="max-w-md w-full bg-white rounded-2xl shadow-sm border p-8 text-center">
          <div className="text-4xl mb-3">🔎</div>
          <h1 className="text-xl font-bold text-gray-900 mb-2">{t('landings:reservation.notFoundTitle')}</h1>
          <p className="text-sm text-gray-600">{t('landings:reservation.notFoundBody')}</p>
        </div>
      </div>
    );
  }

  if (error || !product) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
        <div className="max-w-md w-full bg-white rounded-2xl shadow-sm border p-8 text-center">
          <h1 className="text-xl font-bold text-gray-900 mb-2">{t('landings:reservation.errorTitle')}</h1>
          <p className="text-sm text-gray-600">{t('landings:reservation.errorBody')}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 pb-24">
      {fromStore && <StoreContextNav slug={orgSlug} />}
      {/* Back link with optional cart badge (hidden when cart is empty). */}
      <div className="max-w-5xl mx-auto px-4 py-4">
        <button
          onClick={() => navigate(`/s/${orgSlug}`)}
          className="text-sm text-gray-600 hover:text-gray-900 inline-flex items-center gap-2"
        >
          <span>{t('landings:reservation.backToCatalog')}</span>
          {cartCount > 0 && (
            <span className="inline-flex items-center rounded-full bg-gray-900 text-white text-[10px] font-bold px-2 py-0.5">
              🛒 {cartCount}
            </span>
          )}
        </button>
      </div>

      {/* "Vai al checkout" banner — appears when the cart has items. Gives
          customers a clear way to exit the multi-add flow and proceed. */}
      {cartCount > 0 && (
        <div className="max-w-5xl mx-auto px-4 pb-3">
          <OpenCheckoutButton slug={orgSlug} itemCount={cartCount} variant="landing" />
        </div>
      )}

      <div className="max-w-5xl mx-auto px-4 grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-6">
        {/* Left — product info + pickers */}
        <div className="space-y-6">
          <div className="bg-white rounded-2xl shadow-sm border overflow-hidden">
            {product.cover_image_url || product.image_url ? (
              <div className="aspect-[16/9] bg-gray-100 overflow-hidden">
                <img
                  src={product.cover_image_url || product.image_url}
                  alt={product.name}
                  className="w-full h-full object-cover"
                />
              </div>
            ) : null}
            <div className="p-5 sm:p-6">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-gray-500">
                  {flavor === 'range'
                    ? t('landings:reservation.eyebrowRange')
                    : t('landings:reservation.eyebrowSlot')}
                </span>
                {product.rental_unit && (
                  <span className="text-xs text-gray-400">{t('landings:reservation.perUnit', { unit: product.rental_unit })}</span>
                )}
              </div>
              <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">{product.name}</h1>
              {product.description && (
                <p className="text-sm text-gray-600 mt-2 leading-relaxed">{product.description}</p>
              )}
              {product.long_description && (
                <div className="text-sm text-gray-700 mt-4 whitespace-pre-line leading-relaxed">
                  {product.long_description}
                </div>
              )}
              {product.unit_price != null && (
                <div className="mt-4 text-lg text-gray-700">
                  <span className="text-sm text-gray-500">{t('landings:reservation.basePrice')}</span>{' '}
                  <span className="font-semibold text-gray-900">{formatAmount(Number(product.unit_price), currency)}</span>
                  {product.rental_unit && (
                    <span className="text-gray-500">{t('landings:reservation.basePriceUnitSuffix', { unit: product.rental_unit })}</span>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Date / slot picker */}
          <div className="bg-white rounded-2xl shadow-sm border p-5 sm:p-6">
            <h2 className="text-base font-semibold text-gray-900 mb-3">
              {flavor === 'range'
                ? t('landings:reservation.whenHeadingRange')
                : t('landings:reservation.whenHeadingSlot')}
            </h2>
            {flavor === 'range' ? (
              <RangePicker
                dateFrom={dateFrom}
                dateTo={dateTo}
                blockedDates={blockedDates}
                onChange={({ dateFrom: f, dateTo: t }) => {
                  setDateFrom(f);
                  setDateTo(t);
                }}
              />
            ) : (
              <AvailabilityRangeSlotPicker
                windows={slotWindows}
                minDuration={slotConfig.min_duration_minutes}
                stepMinutes={slotConfig.step_minutes}
                maxDuration={slotConfig.max_duration_minutes}
                selected={
                  slotDate && slotStart
                    ? {
                        date: slotDate,
                        start_time: slotStart,
                        end_time: slotEnd,
                        date_end: slotDateEnd || slotDate,
                      }
                    : null
                }
                onSelect={(s) => {
                  setSlotDate(s.date);
                  setSlotStart(s.start_time);
                  setSlotEnd(s.end_time);
                  setSlotDateEnd(s.date_end || s.date);
                }}
              />
            )}
          </div>

          {/* Extras picker */}
          {(product.extras || []).length > 0 && (
            <ProductExtrasPicker
              extras={product.extras}
              value={extraSelections}
              onChange={setExtraSelections}
              dayCount={flavor === 'range' ? dayCount : null}
              currency={currency}
            />
          )}
        </div>

        {/* Right — sticky price summary */}
        <aside className="lg:sticky lg:top-4 lg:self-start space-y-4">
          <PricePreview result={result} loading={previewLoading} currency={currency} flavor={flavor} />

          {canProceed ? (
            <button
              onClick={handleProceed}
              className="w-full rounded-md bg-[var(--sf-accent,#111827)] text-[var(--sf-accent-fg,#ffffff)] px-4 py-3 text-sm font-semibold hover:bg-[var(--sf-accent-hover,#1f2937)] flex items-center justify-center gap-2 transition-colors"
            >
              {t('landings:reservation.ctaAdd')}
            </button>
          ) : (
            <div
              aria-disabled="true"
              className="w-full rounded-md bg-gray-100 text-gray-500 px-4 py-3 text-sm font-semibold flex items-center justify-center gap-2 border border-dashed border-gray-300 cursor-not-allowed select-none"
            >
              {flavor === 'range'
                ? t('landings:reservation.ctaLockedRange')
                : t('landings:reservation.ctaLockedSlot')}
            </div>
          )}

          <p className="text-[11px] text-gray-500 text-center px-2">
            {t('landings:reservation.checkoutHint')}
          </p>
        </aside>
      </div>
    </div>
  );
}
