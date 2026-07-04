/**
 * Track E Step 4.1 — Coupon validation embed types.
 *
 * Mirror di backend `EmbedCouponValidateRequest/Response`
 * (backend/routers/embed_public.py).
 *
 * Usage flow:
 *   1. Customer inserisce codice nel checkout drawer
 *   2. Widget POST /api/public/embed/coupons/validate/{slug} con {code, subtotal}
 *   3. Backend dry-run validate (no usage increment)
 *   4. Response 200 → mostra discount applicato; 400 → mostra error message
 *   5. Al checkout.start, widget include coupon_code nel payload —
 *      backend rivaliderebbe con atomic increment (anti race-condition)
 */

export interface EmbedCouponValidateRequest {
  /** Codice promo inserito dal customer (case-insensitive, trimmed). */
  code: string;
  /** Cart subtotal corrente (per min_order_amount check + discount compute). */
  subtotal: number;
}

export interface EmbedCouponValidateResponse {
  coupon_id: string;
  /** Codice normalizzato uppercase. */
  code: string;
  /** Discount calcolato sul subtotal corrente. */
  discount: number;
  /** Solo se coupon e' percentage-based. */
  discount_pct?: number | null;
  /** Solo se coupon e' amount-based. */
  discount_amount?: number | null;
}
