/**
 * CouponInput — Sprint 2 W2.1 standalone component (parity widget E4.1).
 *
 * Input + live validation feedback per il coupon code lato React main
 * checkout. Wrappa useCouponValidation hook + render badge inline
 * (loading / valid / invalid / error) con messaggio backend.
 *
 * Mirror del comportamento widget Lit:
 *   afianco-checkout-button.ts renderCouponBlock()
 *
 * Props:
 *   slug             store slug per endpoint
 *   value            current value del coupon input (controlled)
 *   onChange         (newValue: string) => void — upstream sync
 *   cartSubtotal     numero EUR per validation server-side
 *   placeholder      i18n string
 *   disabled         optional disable input (es. submitting)
 *
 * Render contract:
 *   - Input full-width (uppercase coerce, max 30 char)
 *   - Badge stato sotto input:
 *     * loading: spinner + "Verifica in corso..."
 *     * valid: badge verde con discount_amount
 *     * invalid: badge rosso con backend reason message
 *     * error: badge giallo network error
 *   - Zero state quando code vuoto
 */

import React from 'react';
import { CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';

import useCouponValidation from '../hooks/useCouponValidation';


export function CouponInput({
  slug,
  value,
  onChange,
  cartSubtotal,
  placeholder = 'Inserisci codice promo',
  disabled = false,
}) {
  const { status, message, discountAmount, valid } = useCouponValidation({
    slug,
    code: value,
    cartSubtotal,
    enabled: !disabled,
  });

  const formatAmount = (n) => {
    try {
      return new Intl.NumberFormat(undefined, {
        style: 'currency',
        currency: 'EUR',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }).format(n);
    } catch {
      return `${(n || 0).toFixed(2)} €`;
    }
  };

  return (
    <div>
      <input
        type="text"
        value={value || ''}
        onChange={(e) => onChange(e.target.value.toUpperCase())}
        disabled={disabled}
        className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-gray-800 focus:border-transparent outline-none disabled:bg-gray-100 disabled:cursor-not-allowed"
        placeholder={placeholder}
        maxLength={30}
        autoComplete="off"
        spellCheck={false}
      />
      {status === 'loading' && (
        <div className="mt-2 flex items-center gap-2 text-xs text-gray-600">
          <Loader2 className="h-3 w-3 animate-spin" />
          <span>Verifica in corso…</span>
        </div>
      )}
      {status === 'valid' && (
        <div className="mt-2 flex items-start gap-2 rounded-md border border-emerald-200 bg-emerald-50 p-2 text-xs text-emerald-900">
          <CheckCircle2 className="h-4 w-4 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-semibold">Codice valido</p>
            {discountAmount > 0 && (
              <p className="mt-0.5">
                Sconto applicato: <strong>-{formatAmount(discountAmount)}</strong>
              </p>
            )}
            {message && <p className="mt-0.5 text-emerald-800">{message}</p>}
          </div>
        </div>
      )}
      {status === 'invalid' && (
        <div className="mt-2 flex items-start gap-2 rounded-md border border-red-200 bg-red-50 p-2 text-xs text-red-900">
          <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-semibold">Codice non valido</p>
            {message && <p className="mt-0.5 text-red-800">{message}</p>}
          </div>
        </div>
      )}
      {status === 'error' && (
        <div className="mt-2 flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 p-2 text-xs text-amber-900">
          <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-semibold">Errore di verifica</p>
            {message && <p className="mt-0.5 text-amber-800">{message}</p>}
            <p className="mt-0.5 text-amber-700">
              Il codice verra' validato al checkout.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

export default CouponInput;
