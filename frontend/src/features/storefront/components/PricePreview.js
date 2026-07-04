/**
 * PricePreview — hook + component for live reservation pricing (Onda 16).
 *
 * Posts to POST /api/public/price-preview with debounce so the customer sees
 * the server-authoritative total as they toggle extras / change dates.
 *
 *   usePricePreview({ productId, quantity, dateFrom, dateTo, extraSelections })
 *     → { loading, result, error }  where result = { base, extras_total,
 *        total, day_count, extras[], extras_breakdown[] }
 *
 *   <PricePreview result={result} loading={loading} />
 *     → Breakdown card with base, per-extra lines, and total.
 *
 * Uses the public variant of the endpoint so that anonymous visitors on the
 * reservation landing see an accurate total (the admin variant at
 * /api/orders/price-preview requires a Bearer token).
 */

import React, { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { publicPricePreview } from '../../../api/productExtras';


const EMPTY = { base: 0, extras_total: 0, total: 0, day_count: null, extras: [], extras_breakdown: [] };


export function usePricePreview({
  slug,
  productId,
  quantity = 1,
  discountPct = 0,
  dateFrom,
  dateTo,
  extraSelections,
  // Onda 17 — slot flavor variable-duration timing.
  slotDateFrom = null,
  slotTimeFrom = null,
  slotDateTo = null,
  slotTimeTo = null,
}) {
  const { t } = useTranslation('landings');
  const [result, setResult] = useState(EMPTY);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const timerRef = useRef(null);
  const reqIdRef = useRef(0);

  useEffect(() => {
    // R9 — il backend richiede lo slug per scoping org. Senza, non chiamare.
    if (!productId || !slug) return;
    // Debounce 250ms so rapid extra toggles coalesce into one call.
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      const myReqId = ++reqIdRef.current;
      setLoading(true);
      setError(null);
      publicPricePreview({
        slug,
        product_id: productId,
        quantity: quantity || 1,
        discount_pct: discountPct || 0,
        date_from: dateFrom || null,
        date_to: dateTo || null,
        extra_selections: extraSelections || null,
        slot_date_from: slotDateFrom || null,
        slot_time_from: slotTimeFrom || null,
        slot_date_to: slotDateTo || null,
        slot_time_to: slotTimeTo || null,
      })
        .then(res => {
          // Drop stale responses if a newer request has been issued.
          if (myReqId !== reqIdRef.current) return;
          setResult(res.data || EMPTY);
        })
        .catch(err => {
          if (myReqId !== reqIdRef.current) return;
          setError(err?.response?.data?.detail?.message || t('priceSummary.error'));
          setResult(EMPTY);
        })
        .finally(() => {
          if (myReqId === reqIdRef.current) setLoading(false);
        });
    }, 250);
    return () => clearTimeout(timerRef.current);
  }, [slug, productId, quantity, discountPct, dateFrom, dateTo, slotDateFrom, slotTimeFrom, slotDateTo, slotTimeTo, JSON.stringify(extraSelections)]);

  return { loading, result, error };
}


export default function PricePreview({ result, loading, currency = 'EUR', flavor = 'range' }) {
  const { t, i18n } = useTranslation('landings');
  // Locale-aware currency formatter — drives "1.299,00 €" (it) vs
  // "€1,299.00" (en) vs "1.299,00 €" (de) vs "1 299,00 €" (fr) so the
  // total reads naturally in the storefront's language. Uses
  // i18n.language (the resolved storefront locale) instead of a fixed
  // 'it-IT', so a German storefront formats prices in German style.
  const fmt = (v) => v != null
    ? new Intl.NumberFormat(i18n.language, { style: 'currency', currency, maximumFractionDigits: 2 }).format(v)
    : '—';

  return (
    <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-100 bg-gray-50/50">
        <h3 className="text-sm font-semibold text-gray-900">{t('priceSummary.heading')}</h3>
        {flavor === 'range' && result?.day_count > 0 && (
          <p className="text-xs text-gray-500 mt-0.5">
            {/* i18next pluralization picks `_one`/`_other` automatically
                from the `count` value — handles 0/1/N correctly across
                locales (e.g. French uses singular for 0, English uses
                plural for 0). */}
            {t('priceSummary.nights', { count: result.day_count })}
          </p>
        )}
      </div>

      <div className="px-4 py-3 space-y-2 text-sm">
        <div className="flex items-center justify-between text-gray-700">
          <span>{t('priceSummary.base')}</span>
          <span className={loading ? 'opacity-50 transition-opacity' : ''}>{fmt(result?.base)}</span>
        </div>

        {(result?.extras || []).map((ex, i) => (
          <div key={i} className="flex items-center justify-between text-gray-600">
            <span className="flex items-center gap-1.5 min-w-0 truncate">
              <span className="text-xs text-gray-400">+</span>
              <span className="truncate">{ex.label}</span>
              {ex.price_modifier_type === 'per_day' && ex.quantity > 1 && (
                <span className="text-[11px] text-gray-400">(×{ex.quantity})</span>
              )}
            </span>
            <span className={loading ? 'opacity-50' : ''}>{fmt(ex.line_total)}</span>
          </div>
        ))}
      </div>

      <div className="px-4 py-3 border-t border-gray-100 bg-gray-50/50 flex items-center justify-between">
        <span className="text-sm font-semibold text-gray-900">{t('priceSummary.total')}</span>
        <span className={`text-xl font-bold text-gray-900 ${loading ? 'opacity-50 transition-opacity' : ''}`}>
          {fmt(result?.total)}
        </span>
      </div>
    </div>
  );
}
