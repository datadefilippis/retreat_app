/**
 * ProductLandingPage — public landing page for a non-occurrence product
 * (Onda 13).
 *
 * Route: /p/:org_slug/:product_slug
 * Backed by GET /api/public/products/{org_slug}/{product_slug}.
 *
 * Role in the checkout flow — PURELY A PRESENTER (like EventLandingPage):
 *   Shows the product richly (hero with cover image, markdown long
 *   description, radio options picker, slot picker for bookable
 *   services) and collects the user's choice. When the user clicks
 *   "Procedi al checkout", the page navigates to /s/:org_slug with
 *   the selection embedded in React Router state. StorefrontPage
 *   reads the state, hydrates its cart, and opens the single checkout
 *   dialog — the same form used for every other purchase.
 *
 *   The landing itself never submits an order. Exactly one form in
 *   the whole app handles payment.
 *
 * MVP: designed for item_type=service (has options + slots). Extensible
 * to other types once they gain their own pickers (rental date range,
 * booking slot, etc.).
 */

import React, { useEffect, useMemo, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { Trans, useTranslation } from 'react-i18next';
import i18nInstance from '../../i18n';
import { toast } from 'sonner';
import { storefrontAPI } from '../../api/storefront';
import StorefrontHeader from './components/StorefrontHeader';
import AvailabilityCalendarSlotPicker from './components/AvailabilityCalendarSlotPicker';
import MarkdownLite from '../../components/MarkdownLite';
import OpenCheckoutButton from './components/OpenCheckoutButton';
import useCartCount from './hooks/useCartCount';
import StoreContextNav from './components/StoreContextNav';


function formatPrice(n, currency = 'EUR', locale = 'it-IT') {
  if (n === null || n === undefined) return '';
  try {
    return new Intl.NumberFormat(locale, { style: 'currency', currency }).format(n);
  } catch { return `${n} ${currency}`; }
}


// ── Option card (radio) ────────────────────────────────────────────────────

function OptionCard({ option, selected, onSelect, currency }) {
  const { t, i18n } = useTranslation('landings');
  return (
    <label
      className={`block rounded-xl border p-4 cursor-pointer transition ${
        selected ? 'border-gray-900 bg-gray-50' : 'border-gray-200 bg-white hover:border-gray-400'
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1 flex items-start gap-2">
          <input
            type="radio"
            name="service-option"
            checked={selected}
            onChange={() => onSelect(option.id)}
            className="mt-1"
          />
          <div className="min-w-0">
            <h3 className="font-semibold text-gray-900">{option.label}</h3>
            {option.description && (
              <p className="text-sm text-gray-600 mt-1">{option.description}</p>
            )}
            {option.duration_minutes_override && (
              <p className="text-xs text-gray-500 mt-2">{t('landings:product.optionDuration', { minutes: option.duration_minutes_override })}</p>
            )}
          </div>
        </div>
        <div className="text-right shrink-0">
          <p className="text-lg font-bold text-gray-900 whitespace-nowrap">
            {formatPrice(option.price, currency, i18n.language)}
          </p>
        </div>
      </div>
    </label>
  );
}


// SlotPicker extracted to ./components/AvailabilitySlotPicker.js so that the
// rental-slot landing (ReservationLandingPage) can reuse the same two-step
// date + time UX that was introduced for services in Onda 13.


// ── Custom request form (Onda 14 Parte B) ─────────────────────────────────
//
// Used when the service has NO availability rules (or the merchant explicitly
// allows custom requests alongside rules). The customer proposes a preferred
// date/time + optional notes. On submit the selection is treated like a slot
// — payload fields booking_date/start/end + rental_notes — but validator
// knows to accept it without a rule match when service_allow_custom_request
// is enabled on the product.
function CustomRequestForm({ durationMinutes, value, onChange }) {
  const { t } = useTranslation('landings');
  const today = new Date();
  const minDate = today.toISOString().slice(0, 10);

  // Build 15-min increments between 08:00 and 21:00
  const timeSlots = useMemo(() => {
    const arr = [];
    for (let h = 8; h <= 21; h += 1) {
      for (const m of [0, 15, 30, 45]) {
        if (h === 21 && m > 0) break;
        arr.push(`${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`);
      }
    }
    return arr;
  }, []);

  const duration = durationMinutes || 60;

  const handleChange = (field, raw) => {
    const next = { ...(value || {}), [field]: raw };
    // Whenever date or start_time change, recompute end_time from duration
    if (field === 'start_time' || field === 'date') {
      const st = field === 'start_time' ? raw : (next.start_time || null);
      if (st) {
        const [h, m] = st.split(':').map(Number);
        const endMin = h * 60 + m + duration;
        const eh = Math.floor(endMin / 60) % 24;
        const em = endMin % 60;
        next.end_time = `${String(eh).padStart(2, '0')}:${String(em).padStart(2, '0')}`;
      } else {
        next.end_time = null;
      }
    }
    onChange(next);
  };

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 space-y-3">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <label className="block">
          <span className="text-[11px] uppercase tracking-wide text-gray-500 font-semibold">{t('landings:product.customRequest.preferredDate')}</span>
          <input
            type="date"
            min={minDate}
            value={value?.date || ''}
            onChange={(e) => handleChange('date', e.target.value)}
            className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
          />
        </label>
        <label className="block">
          <span className="text-[11px] uppercase tracking-wide text-gray-500 font-semibold">{t('landings:product.customRequest.preferredTime')}</span>
          <select
            value={value?.start_time || ''}
            onChange={(e) => handleChange('start_time', e.target.value)}
            className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm bg-white"
          >
            <option value="">{t('landings:product.customRequest.selectPlaceholder')}</option>
            {timeSlots.map(slot => <option key={slot} value={slot}>{slot}</option>)}
          </select>
        </label>
      </div>
      <label className="block">
        <span className="text-[11px] uppercase tracking-wide text-gray-500 font-semibold">{t('landings:product.customRequest.notesLabel')}</span>
        <textarea
          rows={2}
          placeholder={t('landings:product.customRequest.notesPlaceholder')}
          value={value?.notes || ''}
          onChange={(e) => handleChange('notes', e.target.value)}
          className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
        />
      </label>
      <p className="text-[11px] text-gray-500">
        {t('landings:product.customRequest.footerHint', { minutes: duration })}
      </p>
    </div>
  );
}


// ── Proceed to checkout bar ────────────────────────────────────────────────

function ProceedToCheckoutBar({
  orgSlug, product, selectedOptionId, selectedSlot,
  customRequest, customRequestActive, effectiveCurrency,
}) {
  const navigate = useNavigate();
  const { t, i18n } = useTranslation('landings');
  const options = Array.isArray(product.service_options) ? product.service_options : [];
  const hasOptions = options.length > 0;
  const hasSlots = !!product.has_availability_slots;
  const allowCustom = !!product.service_allow_custom_request;

  const selectedOption = hasOptions ? options.find(o => o.id === selectedOptionId) : null;
  const unitPrice = selectedOption
    ? selectedOption.price
    : (product.unit_price != null ? Number(product.unit_price) : 0);

  const isDirectMode = product?.transaction_mode === 'direct';

  // Onda 14 Parte B — compute gating across the 3 scenarios:
  //  1) has rules, no custom   → require selectedSlot
  //  2) has rules, custom-also → require (selectedSlot OR full customRequest)
  //  3) no rules, custom-only  → require full customRequest
  //  4) no rules, no-custom    → pass (admin schedules manually)
  const needsOption = hasOptions && !selectedOptionId;
  const customRequestComplete = !!(customRequest?.date && customRequest?.start_time && customRequest?.end_time);

  let needsScheduling = false;
  if (hasSlots && !allowCustom) {
    needsScheduling = !selectedSlot?.date;
  } else if (hasSlots && allowCustom) {
    needsScheduling = !(selectedSlot?.date || (customRequestActive && customRequestComplete));
  } else if (!hasSlots && allowCustom) {
    needsScheduling = !customRequestComplete;
  } else {
    needsScheduling = false; // scenario 4
  }
  const canProceed = !needsOption && !needsScheduling;

  const handleProceed = () => {
    if (!canProceed) return;
    const preloadCart = {
      productId: product.id,
      qty: 1,
    };
    if (selectedOptionId) preloadCart.service_option_id = selectedOptionId;
    // Prefer the real slot if chosen; otherwise use the custom request.
    if (selectedSlot?.date) {
      preloadCart.service_slot = { ...selectedSlot };
    } else if (customRequestComplete) {
      preloadCart.service_slot = {
        date: customRequest.date,
        start_time: customRequest.start_time,
        end_time: customRequest.end_time,
        custom_request: true,
        notes: customRequest.notes || null,
      };
    }
    navigate(`/s/${orgSlug}`, { state: { preloadCart } });
    toast.success(t('landings:product.toastAdded'), {
      action: {
        label: t('landings:product.toastAction'),
        onClick: () => navigate(`/s/${orgSlug}?checkout=1`),
      },
      duration: 4000,
    });
  };

  // Figure out the scheduling summary shown in the "Riepilogo"
  const effectiveSlot = selectedSlot?.date
    ? selectedSlot
    : (customRequestComplete ? { date: customRequest.date, start_time: customRequest.start_time } : null);

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-3 shadow-sm">
      <div>
        <h3 className="font-semibold text-gray-900">{t('landings:product.summary.heading')}</h3>
        {selectedOption ? (
          <p className="text-sm text-gray-600 mt-1">{t('landings:product.summary.lineOption', { label: selectedOption.label })}</p>
        ) : (
          <p className="text-sm text-gray-500 mt-1">{hasOptions ? t('landings:product.summary.selectOption') : product.name}</p>
        )}
        {effectiveSlot?.date && (
          <p className="text-xs text-gray-500 mt-1">
            📅 {new Date(effectiveSlot.date + 'T12:00').toLocaleDateString(i18n.language, { weekday: 'short', day: 'numeric', month: 'short' })}
            {' · '}{effectiveSlot.start_time}
            {!selectedSlot?.date && customRequestComplete && (
              <span className="ml-1 text-amber-700">{t('landings:product.summary.customBadge')}</span>
            )}
          </p>
        )}
        <p className="text-2xl font-bold text-gray-900 mt-2">
          {formatPrice(unitPrice, effectiveCurrency, i18n.language)}
        </p>
      </div>

      {/* Onda 15 — Proceed button with distinct locked vs active states.
          Locked (pre-selection): grey background, lock icon, caption telling
          the user exactly what to pick next. Active (post-selection): solid
          primary button with checkout emoji. Click handler still guarded
          by canProceed for safety. */}
      {canProceed ? (
        <button
          type="button"
          onClick={handleProceed}
          className="w-full rounded-md bg-[var(--sf-accent,#111827)] text-[var(--sf-accent-fg,#ffffff)] px-4 py-3 text-sm font-semibold hover:bg-[var(--sf-accent-hover,#1f2937)] flex items-center justify-center gap-2 transition-colors"
        >
          {isDirectMode && <span aria-hidden>🛒</span>}
          {t('landings:product.summary.ctaAdd')}
        </button>
      ) : (
        <div
          aria-disabled="true"
          className="w-full rounded-md bg-gray-100 text-gray-500 px-4 py-3 text-sm font-semibold flex items-center justify-center gap-2 border border-dashed border-gray-300 cursor-not-allowed select-none"
          title={t('landings:product.summary.lockedTitle')}
        >
          {needsOption
            ? t('landings:product.summary.ctaLockedNeedsOption')
            : t('landings:product.summary.ctaLockedNeedsSchedule')}
        </div>
      )}

      <p className="text-[11px] text-gray-500 text-center">
        {canProceed
          ? t('landings:product.summary.checkoutHintActive')
          : t('landings:product.summary.checkoutHintLocked')}
      </p>
    </div>
  );
}


// ── Main component ─────────────────────────────────────────────────────────

export default function ProductLandingPage() {
  const { org_slug: orgSlug, product_slug: productSlug } = useParams();
  // 7/7 — contesto negozio: i link delle card store portano ?store=1;
  // la landing mantiene la barra menu dello store (mai uscire).
  const fromStore = new URLSearchParams(window.location.search).get('store') === '1';

  const { t } = useTranslation('landings');
  const cartCount = useCartCount(orgSlug);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [selectedOptionId, setSelectedOptionId] = useState(null);
  const [selectedSlot, setSelectedSlot] = useState(null);
  const [slots, setSlots] = useState([]);
  const [slotsLoading, setSlotsLoading] = useState(false);
  // Onda 14 Parte B — custom request (date/time/notes proposed by the
  // customer when the service has no rules or allows custom-on-top).
  const [customRequest, setCustomRequest] = useState(null);
  const [customRequestOpen, setCustomRequestOpen] = useState(false);

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

  // Fetch slots when landing has a service product with availability
  useEffect(() => {
    if (!data?.product?.id) return;
    if (!data.product.has_availability_slots) return;
    setSlotsLoading(true);
    storefrontAPI.getServiceSlots(data.product.id, 30)
      .then(res => setSlots(res.data?.slots || []))
      .catch(() => setSlots([]))
      .finally(() => setSlotsLoading(false));
  }, [data?.product?.id, data?.product?.has_availability_slots]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-sm text-gray-500">
        {t('landings:product.loading')}
      </div>
    );
  }

  if (error === 'not_found') {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
        <div className="max-w-md text-center bg-white rounded-xl border p-8">
          <h1 className="text-2xl font-bold mb-2">{t('landings:product.notFoundTitle')}</h1>
          <p className="text-sm text-gray-600 mb-4">{t('landings:product.notFoundBody')}</p>
          <Link to={`/s/${orgSlug}`} className="inline-block rounded-md bg-gray-900 text-white px-4 py-2 text-sm">
            {t('landings:product.backToCatalogShort')}
          </Link>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6">
        <p className="text-sm text-red-700">{t('landings:product.errorBody')}</p>
      </div>
    );
  }

  const { org_name: orgName, store_info: storeInfo, product } = data;
  // CH compliance v1: prefer the store's configured currency (set per
  // organisation in settings) over the previous EUR-hardcoded default.
  // Falling back to EUR keeps legacy storefronts unchanged.
  const effectiveCurrency = product?.currency || storeInfo?.currency || 'EUR';
  // Onda 14 Parte D — prefer dedicated cover_image_url, fallback on
  // product.image_url. The backend now surfaces both via PublicProduct.
  const hero = product?.cover_image_url || product?.image_url || null;

  const options = Array.isArray(product.service_options) ? product.service_options : [];
  const hasOptions = options.length > 0;
  const hasSlots = !!product.has_availability_slots;
  const allowCustomRequest = !!product.service_allow_custom_request;
  const durationMinutes = product.service_duration_minutes;

  return (
    <div className="min-h-screen bg-gray-50">
      <StorefrontHeader orgName={orgName} orgSlug={orgSlug} storeInfo={storeInfo} />
      {fromStore && <StoreContextNav slug={orgSlug} />}

      {/* Hero */}
      <div className="relative bg-gray-900 text-white overflow-hidden">
        {hero && (
          <img src={hero} alt="" className="absolute inset-0 w-full h-full object-cover opacity-50" />
        )}
        <div className="relative max-w-5xl mx-auto px-4 sm:px-6 py-8 sm:py-12">
          <Link to={`/s/${orgSlug}`} className="inline-flex items-center gap-2 text-sm font-medium text-white/70 hover:text-white">
            <span>{t('landings:product.catalogLink')}</span>
            {cartCount > 0 && (
              <span className="inline-flex items-center rounded-full bg-white text-gray-900 text-[10px] font-bold px-2 py-0.5">
                🛒 {cartCount}
              </span>
            )}
          </Link>
          <p className="text-[10px] uppercase tracking-widest opacity-70 mt-3">
            {product.item_type === 'service'
              ? t('landings:product.eyebrowService')
              : t('landings:product.eyebrowProduct')}
          </p>
          <h1 className="text-2xl sm:text-4xl font-bold mt-1">{product.name}</h1>
          {product.description && (
            <p className="text-sm sm:text-base opacity-90 mt-3 max-w-2xl">
              {product.description}
            </p>
          )}
          {durationMinutes && (
            <p className="text-xs opacity-80 mt-3">{t('landings:product.durationLabel', { minutes: durationMinutes })}</p>
          )}
        </div>
      </div>

      {/* "Vai al checkout" banner — appears when the cart has items. Gives
          customers a clear way to exit the multi-add flow and proceed. */}
      {cartCount > 0 && (
        <div className="max-w-5xl mx-auto px-4 sm:px-6 pt-4">
          <OpenCheckoutButton slug={orgSlug} itemCount={cartCount} variant="landing" />
        </div>
      )}

      {/* Main content */}
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-6 sm:py-10 grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Left — rich content */}
        <div className="md:col-span-2 space-y-4">
          {product.long_description && (
            <div className="rounded-xl border border-gray-200 bg-white p-5">
              <h2 className="text-base font-semibold text-gray-900 mb-3">{t('landings:product.descriptionHeading')}</h2>
              <MarkdownLite source={product.long_description} />
            </div>
          )}

          {hasOptions && (
            <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-3">
              <h2 className="text-base font-semibold text-gray-900">{t('landings:product.optionsHeading')}</h2>
              <p className="text-xs text-gray-500">{t('landings:product.optionsHint')}</p>
              <div className="space-y-2">
                {options.map(o => (
                  <OptionCard
                    key={o.id}
                    option={o}
                    selected={selectedOptionId === o.id}
                    onSelect={setSelectedOptionId}
                    currency={effectiveCurrency}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Scenario 1 + 2 — merchant has availability rules */}
          {hasSlots && (
            <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-3">
              <h2 className="text-base font-semibold text-gray-900">{t('landings:product.scheduleHeading')}</h2>
              <p className="text-xs text-gray-500">
                {t('landings:product.scheduleHint')}
              </p>
              {slotsLoading ? (
                <p className="text-sm text-gray-500">{t('landings:product.loadingSlots')}</p>
              ) : (
                <AvailabilityCalendarSlotPicker
                  slots={slots}
                  selected={selectedSlot}
                  onSelect={(s) => { setSelectedSlot(s); setCustomRequestOpen(false); }}
                />
              )}

              {/* Scenario 2 — rules + custom-request fallback toggle */}
              {allowCustomRequest && (
                <div className="border-t border-gray-100 pt-3">
                  {!customRequestOpen ? (
                    <button
                      type="button"
                      onClick={() => { setCustomRequestOpen(true); setSelectedSlot(null); }}
                      className="text-sm font-medium text-gray-700 hover:text-gray-900 underline"
                    >
                      {t('landings:product.customRequestToggle')}
                    </button>
                  ) : (
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <h3 className="text-sm font-semibold text-gray-900">{t('landings:product.customRequestPanelHeading')}</h3>
                        <button
                          type="button"
                          onClick={() => { setCustomRequestOpen(false); setCustomRequest(null); }}
                          className="text-xs text-gray-500 hover:text-gray-700"
                        >
                          {t('landings:product.customRequestCancel')}
                        </button>
                      </div>
                      <CustomRequestForm
                        durationMinutes={durationMinutes}
                        value={customRequest}
                        onChange={setCustomRequest}
                      />
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Scenario 3 — no rules, custom request enabled */}
          {!hasSlots && allowCustomRequest && (
            <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-3">
              <h2 className="text-base font-semibold text-gray-900">{t('landings:product.customRequest.headingNoSlots')}</h2>
              <p className="text-xs text-gray-500">
                {t('landings:product.customRequest.hintNoSlots')}
              </p>
              <CustomRequestForm
                durationMinutes={durationMinutes}
                value={customRequest}
                onChange={(v) => { setCustomRequest(v); setCustomRequestOpen(true); }}
              />
            </div>
          )}

          {/* Scenario 4 — no rules, no custom: just contact */}
          {!hasOptions && !hasSlots && !allowCustomRequest && (
            <div className="rounded-xl border border-gray-200 bg-white p-5 space-y-2">
              <h2 className="text-base font-semibold text-gray-900">{t('landings:product.scenario4.heading')}</h2>
              <p className="text-sm text-gray-700">
                {t('landings:product.scenario4.body')}
              </p>
              {storeInfo?.email && (
                <a
                  href={`mailto:${storeInfo.email}?subject=${encodeURIComponent('Richiesta: ' + product.name)}`}
                  className="inline-block text-sm font-medium text-gray-900 underline"
                >
                  {t('landings:product.scenario4.writeTo', { email: storeInfo.email })}
                </a>
              )}
            </div>
          )}

          {/* Has options but no scheduling at all */}
          {hasOptions && !hasSlots && !allowCustomRequest && (
            <div className="rounded-xl border border-gray-200 bg-white p-5">
              <p className="text-sm text-gray-700">
                {t('landings:product.scenarioOptionsOnly')}
              </p>
            </div>
          )}
        </div>

        {/* Right — sticky checkout bar */}
        <aside className="md:sticky md:top-4 md:self-start space-y-4">
          <ProceedToCheckoutBar
            orgSlug={orgSlug}
            product={product}
            selectedOptionId={selectedOptionId}
            selectedSlot={selectedSlot}
            customRequest={customRequest}
            customRequestActive={customRequestOpen}
            effectiveCurrency={effectiveCurrency}
          />
        </aside>
      </div>

      <div className="py-8 text-center text-[11px] text-gray-400">
        <Trans
          i18nKey="landings:product.footerOrganizedBy"
          values={{ name: orgName }}
          components={[<strong className="text-gray-600" />]}
        />
      </div>
    </div>
  );
}
