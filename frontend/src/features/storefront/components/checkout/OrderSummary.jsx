/**
 * OrderSummary — riepilogo carrello del checkout storefront.
 *
 * PN2 (PROFILO_NEGOZIO_PIANO_2026-07) — funzione locale spostata TALE E
 * QUALE da StorefrontPage.js (righe ~111-338). Props gia' esplicite in
 * origine: nessuna closure, nessun cambio di comportamento.
 */
import { useTranslation } from 'react-i18next';
import { effectivePlan } from '../../lib/paymentPlan';
import {
  fmtPrice,
  fmtOccDate,
  computeRentalMultiplier,
} from '../StorefrontCards';

/* ── Order Summary ─────────────────────────────────────────────────────────── */

/**
 * Shared trash icon for cart-remove actions. Inline SVG to avoid adding a
 * lucide-react import in this file (already heavy on dependencies) and to
 * match the small-icon size used elsewhere in the storefront.
 */
function TrashIcon({ size = 14 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M3 6h18" />
      <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
      <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
    </svg>
  );
}


export default function OrderSummary({ items, products, selectedOccurrences, selectedTiers, rentalDates, bookingSlots, currency, shipping, onRemove, onQtyChange, couponDiscount = 0, couponLabel = null }) {
  const { t, i18n } = useTranslation('storefront');
  if (items.length === 0) return null;
  const hasInquiry = items.some(it => products.find(pp => pp.id === it.product_id)?.price_mode === 'inquiry');
  // Resolve the effective unit price following the same precedence the
  // backend applies at order_service.create_order: tier.price (most
  // specific) > occurrence.price_override > product.unit_price. Keeps
  // the cart total honest when the selection came from the event
  // landing page handoff.
  const resolveUnitPrice = (it) => {
    const p = products.find(pp => pp.id === it.product_id);
    if (!p || p.price_mode === 'inquiry') return { p, price: 0, isInq: true };
    const occ = selectedOccurrences?.[it.product_id];
    // F3 Onda 10 — selectedItems now carries ticket_tier_id per line;
    // prefer that over the multi-tier map on selectedTiers. Fallback to
    // the legacy single-entry map {tierId: qty}.
    let tier = null;
    if (it.ticket_tier_id && occ?.tiers) {
      tier = occ.tiers.find(t => t.id === it.ticket_tier_id);
    } else {
      const tierMap = selectedTiers?.[it.product_id];
      if (tierMap && typeof tierMap === 'object' && occ?.tiers) {
        const tierIds = Object.keys(tierMap);
        if (tierIds.length === 1) tier = occ.tiers.find(t => t.id === tierIds[0]);
      }
    }
    // F5 Onda 12 — service option price override
    let serviceOption = null;
    if (it.service_option_id && Array.isArray(p.service_options)) {
      serviceOption = p.service_options.find(o => o.id === it.service_option_id);
    }
    const price = serviceOption?.price != null
      ? serviceOption.price
      : (tier?.price != null
          ? tier.price
          : (occ?.price_override != null ? occ.price_override : (p.unit_price || 0)));
    return { p, price, isInq: false, tier, occ, serviceOption };
  };
  const total = items.reduce((sum, it) => {
    const { p, price, isInq } = resolveUnitPrice(it);
    if (isInq) return sum;
    const rentalMult = p?.item_type === 'rental'
      ? computeRentalMultiplier(rentalDates?.[it.product_id], p.rental_unit)
      : 1;
    return sum + price * it.quantity * rentalMult;
  }, 0);
  return (
    <div className="rounded-xl border bg-white p-4 shadow-sm">
      <h3 className="font-semibold mb-2">{t('storefront:summary.title')}</h3>
      <ul className="space-y-1 text-sm">
        {items.map(it => {
          const resolved = resolveUnitPrice(it);
          const { p, price, isInq, tier, occ, serviceOption } = resolved;
          const rentalMult = p?.item_type === 'rental'
            ? computeRentalMultiplier(rentalDates?.[it.product_id], p?.rental_unit)
            : 1;
          const lineLabel = p?.item_type === 'rental' && rentalMult > 1
            ? t('storefront:summary.rentalLine', { name: p?.name, count: rentalMult, unit: p?.rental_unit || t('storefront:rental.unitFallback') })
            : t('storefront:summary.qtyLine', { name: p?.name, count: it.quantity });
          return (
            <li key={`${it.product_id}:${it.ticket_tier_id || it.service_option_id || 'base'}`}>
              <div className="flex justify-between items-start gap-2">
                <span className="flex-1 min-w-0">{lineLabel}{tier ? ` — ${tier.label}` : (serviceOption ? ` — ${serviceOption.label}` : '')}</span>
                <span className="font-medium whitespace-nowrap">{isInq ? t('storefront:summary.onRequest') : fmtPrice(price * it.quantity * rentalMult, currency)}</span>
                {/* Fix qty (4/7/2026) — una persona prenota per 2: la
                    quantità si corregge QUI, senza tornare alla landing.
                    Solo per righe a quantità semplice (no tier/rental/
                    slot: quelle hanno i loro selettori dedicati). */}
                {onQtyChange && !it.ticket_tier_id && !it.service_option_id
                  && ['event_ticket', 'physical', 'digital'].includes(p?.item_type) && (
                  <span className="shrink-0 inline-flex items-center border rounded-md overflow-hidden"
                        aria-label={t('storefront:summary.qtyAria', { name: p?.name })}>
                    <button type="button"
                      onClick={() => onQtyChange(it.product_id, Math.max(1, it.quantity - 1))}
                      className="px-1.5 py-0.5 text-xs hover:bg-gray-100 disabled:opacity-40"
                      disabled={it.quantity <= 1}>−</button>
                    <span className="px-1.5 text-xs font-semibold tabular-nums">{it.quantity}</span>
                    <button type="button"
                      onClick={() => onQtyChange(it.product_id, Math.min(99, it.quantity + 1))}
                      className="px-1.5 py-0.5 text-xs hover:bg-gray-100">+</button>
                  </span>
                )}
                {onRemove && (
                  <button
                    type="button"
                    onClick={() => onRemove(it.product_id)}
                    className="shrink-0 text-gray-400 hover:text-red-600 transition-colors p-0.5 -mr-1"
                    aria-label={t('storefront:summary.removeAria', { name: p?.name || t('storefront:summary.removeFallbackName') })}
                    title={t('storefront:summary.removeTitle')}
                  >
                    <TrashIcon />
                  </button>
                )}
              </div>
              {tier && (
                <p className="text-xs text-gray-400 ml-1">{t('storefront:summary.tierLine', { label: tier.label })}</p>
              )}
              {serviceOption && (
                <p className="text-xs text-gray-400 ml-1">{t('storefront:summary.optionLine', { label: serviceOption.label })}</p>
              )}
              {occ && (
                <p className="text-xs text-gray-400 ml-1">{fmtOccDate(occ.start_at, i18n.language)}</p>
              )}
              {rentalDates?.[it.product_id]?.from && (
                <p className="text-xs text-gray-400 ml-1">
                  {new Date(rentalDates[it.product_id].from + 'T00:00').toLocaleDateString(i18n.language, { day: 'numeric', month: 'short' })}
                  {rentalDates[it.product_id].to
                    ? ` → ${new Date(rentalDates[it.product_id].to + 'T00:00').toLocaleDateString(i18n.language, { day: 'numeric', month: 'short' })}`
                    : ''}
                </p>
              )}
              {bookingSlots?.[it.product_id]?.date && bookingSlots[it.product_id]?.start && (() => {
                const bs = bookingSlots[it.product_id];
                const fmtDay = (iso) => new Date(iso + 'T12:00').toLocaleDateString(i18n.language, { weekday: 'short', day: 'numeric', month: 'short' });
                const crossDay = bs.date_end && bs.date_end !== bs.date;
                return (
                  <p className="text-xs text-gray-400 ml-1">
                    {crossDay
                      ? <>{fmtDay(bs.date)} {bs.start} → {fmtDay(bs.date_end)} {bs.end}</>
                      : <>{fmtDay(bs.date)} {bs.start}–{bs.end}</>}
                  </p>
                );
              })()}
            </li>
          );
        })}
      </ul>
      {/* Shipping line — rendered only when the caller resolved a shipping
          cost for the current fulfillment choice. For inquiry-priced carts
          the total remains a "stima" and the shipping row is suppressed to
          avoid implying a commitment before the merchant confirms. */}
      {!hasInquiry && shipping && shipping.active && (
        <div className="border-t mt-3 pt-3 space-y-1 text-sm">
          <div className="flex justify-between text-gray-700">
            <span>
              {t('storefront:summary.shipping')}
              {shipping.label ? <span className="text-gray-500"> — {shipping.label}</span> : null}
            </span>
            <span className="font-medium">
              {shipping.cost > 0
                ? fmtPrice(shipping.cost, currency)
                : <span className="text-green-700 font-semibold">{t('storefront:summary.shippingFree')}</span>}
            </span>
          </div>
          {shipping.addMoreForFree > 0 && (
            <p className="text-[11px] text-gray-500">
              {t('storefront:summary.addMoreForFree', { amount: fmtPrice(shipping.addMoreForFree, currency) })}
            </p>
          )}
        </div>
      )}
      {/* Sprint 2 W2.2 — Live coupon discount line (parity widget E4.1).
          Renders solo quando coupon valid + discountAmount > 0. Hook
          useCouponValidation upstream lo calcola debounced 350ms. */}
      {!hasInquiry && couponDiscount > 0 && (
        <div className="border-t mt-3 pt-3 space-y-1 text-sm">
          <div className="flex justify-between text-emerald-700">
            <span>
              {t('storefront:summary.couponDiscount', 'Sconto coupon')}
              {couponLabel ? <span className="text-gray-500"> — {couponLabel}</span> : null}
            </span>
            <span className="font-medium">-{fmtPrice(couponDiscount, currency)}</span>
          </div>
        </div>
      )}
      <div className="border-t mt-3 pt-3 flex justify-between font-bold">
        <span>{hasInquiry ? t('storefront:summary.subtotalEstimate') : t('storefront:summary.totalEstimate')}</span>
        <span>{fmtPrice(
          Math.max(0, total + (shipping?.active ? shipping.cost : 0) - (couponDiscount || 0)),
          currency,
        )}</span>
      </div>
      {/* Fix caparra (4/7/2026) — se l'ordine ha un piano acconto, dirlo
          QUI: senza questa riga il cliente vede "Totale 1600€" e crede di
          pagarlo subito (Stripe chiede la caparra giusta, ma la fiducia è
          già persa). Stesso estimator della landing (effectivePlan) sulla
          stessa base del backend: totale ordine, piano della prima riga
          evento (create_schedule_for_new_order fa identico). */}
      {!hasInquiry && (() => {
        const evIt = items.find(it => {
          const p = products.find(pp => pp.id === it.product_id);
          return p?.item_type === 'event_ticket' && p?.payment_plan && selectedOccurrences?.[it.product_id];
        });
        if (!evIt) return null;
        const p = products.find(pp => pp.id === evIt.product_id);
        const occ = selectedOccurrences[evIt.product_id];
        const netTotal = Math.max(0, total + (shipping?.active ? shipping.cost : 0) - (couponDiscount || 0));
        const ep = effectivePlan(p.payment_plan, netTotal, occ?.start_at);
        if (ep.mode !== 'deposit') return null;
        const dueDate = ep.balanceDueDate
          ? ep.balanceDueDate.toLocaleDateString(i18n.language, { day: 'numeric', month: 'long', year: 'numeric' })
          : '';
        return (
          <div className="mt-3 rounded-lg bg-emerald-50 border border-emerald-200 p-3">
            <div className="flex justify-between items-baseline font-bold text-emerald-800">
              <span>{t('storefront:summary.depositToday')}</span>
              <span>{fmtPrice(ep.depositMinor / 100, currency)}</span>
            </div>
            <p className="text-xs text-emerald-700 mt-1">
              {t('storefront:summary.depositBalance', {
                amount: fmtPrice(ep.balanceMinor / 100, currency),
                date: dueDate,
              })}
            </p>
          </div>
        );
      })()}
    </div>
  );
}
