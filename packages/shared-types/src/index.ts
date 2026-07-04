/**
 * @afianco/shared-types — Phase 1 Step 19
 *
 * TypeScript interfaces che riflettono i Pydantic models del backend
 * embed public API (Stream A). Manuale per V1 — futuro V2 può usare
 * pydantic2ts per generazione automatica.
 *
 * Source of truth: `backend/routers/embed_public.py` + `backend/routers/public.py`
 * I tipi qui sono *clone* — il sentinel "shape parity" verifica che ogni
 * Pydantic public model abbia un counterpart TS.
 */

export * from './embed-init.js';
export * from './embed-products.js';
export * from './embed-cart.js';
export * from './embed-checkout.js';
export * from './customer-auth.js';
// Track E Step 2.4.6 — customer portal asset views (downloads/bookings/
// reservations/courses) per il widget embed customer-portal tabs.
export * from './customer-assets.js';
// Track E Step 4.1 — Coupon validate (dry-run preview) per checkout widget.
export * from './embed-coupons.js';
// Track E Step 4.2 — Shipping options picker (multi-option radio + cost preview).
export * from './embed-shipping.js';
export * from './embed-newsletter.js';
export * from './common.js';
