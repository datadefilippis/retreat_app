/**
 * useCouponValidation — Sprint 2 W2.1 hook (parity widget E4.1).
 *
 * Debounced dry-run validation di un coupon code lato React storefront.
 * Mirror del comportamento del widget Lit (afianco-checkout-button.ts
 * applyCoupon method): l'utente digita il codice, dopo 350ms di
 * inattivita' il hook chiama POST /api/public/embed/coupons/validate/
 * {slug} con il subtotal corrente e ritorna lo stato (valid/invalid/
 * loading/error) per render inline.
 *
 * Anti-race contract
 * ==================
 * Il dry-run NON incrementa usage counter — il checkout reale chiama
 * validate_coupon (atomic increment) che pu fallire se l'ultimo
 * slot del coupon e' stato consumato fra dry-run e checkout. UI deve
 * mostrare error "coupon_exhausted" gracefully al submit (non e' un
 * bug del hook, e' design).
 *
 * Usage
 * =====
 *   const couponState = useCouponValidation({
 *     slug,
 *     code: form.coupon_code,
 *     cartSubtotal: orderTotal,
 *     enabled: !!form.coupon_code,
 *   });
 *   // couponState: { status, message, discountAmount, valid }
 *   //   status: 'idle' | 'loading' | 'valid' | 'invalid' | 'error'
 *
 * Edge cases
 * ==========
 *  - Empty code → status='idle', no fetch
 *  - subtotal=0 → backend ritorna valid=false reason=min_order_amount
 *  - Network error → status='error' con message generic
 *  - Race: 2 keystroke rapidi → solo l'ultimo fetch viene processato
 *    via cancellation + active flag pattern
 */

import { useEffect, useState } from 'react';

import { storefrontAPI } from '../../../api/storefront';


const DEBOUNCE_MS = 350;


export function useCouponValidation({
  slug,
  code,
  cartSubtotal,
  enabled = true,
}) {
  const [status, setStatus] = useState('idle');
  const [message, setMessage] = useState(null);
  const [discountAmount, setDiscountAmount] = useState(0);
  const [reason, setReason] = useState(null);

  // Normalize code per evitare fetch su differenze cosmetiche
  const normalizedCode = (code || '').trim().toUpperCase();

  useEffect(() => {
    // Reset stato quando code vuoto o feature disabled
    if (!enabled || !normalizedCode || !slug) {
      setStatus('idle');
      setMessage(null);
      setDiscountAmount(0);
      setReason(null);
      return;
    }

    let active = true;
    setStatus('loading');

    const timer = setTimeout(async () => {
      try {
        const res = await storefrontAPI.validateCoupon(
          slug,
          normalizedCode,
          cartSubtotal,
        );
        if (!active) return;
        const data = res?.data || {};
        if (data.valid === true) {
          setStatus('valid');
          setMessage(data.message || null);
          setDiscountAmount(Number(data.discount_amount) || 0);
          setReason(null);
        } else {
          setStatus('invalid');
          setMessage(data.message || 'Codice non valido');
          setDiscountAmount(0);
          setReason(data.reason || 'not_found');
        }
      } catch (err) {
        if (!active) return;
        const detail = err?.response?.data?.detail;
        setStatus('error');
        setMessage(
          typeof detail === 'string'
            ? detail
            : (detail && (detail.message || detail.error)) ||
              'Errore validazione coupon. Riprova piu\' tardi.'
        );
        setDiscountAmount(0);
        setReason('network_error');
      }
    }, DEBOUNCE_MS);

    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [enabled, slug, normalizedCode, cartSubtotal]);

  return {
    status,
    message,
    discountAmount,
    reason,
    valid: status === 'valid',
  };
}

export default useCouponValidation;
