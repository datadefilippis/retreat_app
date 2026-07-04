/**
 * Types for POST /api/public/embed/checkout/start (Step 16 + 18) and
 *           GET  /api/public/embed/checkout/complete (Step 17)
 *
 * Mirror di backend `routers/embed_public.py`:
 *   - EmbedCheckoutStartRequest
 *   - EmbedCheckoutStartResponse
 */

import type { FulfillmentMode } from './common.js';

export interface EmbedCheckoutStartRequest {
  slug: string;
  cart_id: string;
  customer_name: string;
  customer_email: string;
  customer_phone?: string | null;

  /**
   * Validato server-side contro store.allowed_origins. URL non
   * autorizzato → 400 return_url_rejected.
   */
  embed_return_url: string;

  // GDPR consent flags — privacy + terms entrambi OBBLIGATORI server-side
  gdpr_terms_accepted: boolean;
  gdpr_privacy_accepted: boolean;
  gdpr_marketing_accepted: boolean;

  // Legacy T&C parity field (additivo)
  terms_accepted: boolean;

  // Optional fulfillment
  fulfillment_mode?: FulfillmentMode | null;
  notes?: string | null;

  // ── Track E Step 3.2 — Dynamic order_fields (custom merchant fields) ──
  /**
   * Dict {field_id: value} dai FieldConfig configurati dal merchant in
   * product.metadata.order_fields[]. Validato server-side.
   */
  order_fields?: Record<string, unknown> | null;

  // ── Track E Step 3.3 — Shipping address per physical products ──
  shipping_address_details?: EmbedShippingAddress | null;
  shipping_option_id?: string | null;
  shipping_option_label?: string | null;

  // ── Track E Step 4.1 — Coupon code (discount promo) ──
  /**
   * Codice promo applicato. Validato server-side al checkout con
   * atomic increment di current_uses. Customer puo' fare dry-run
   * preview via POST /api/public/embed/coupons/validate/{slug}.
   */
  coupon_code?: string | null;

  // ── Step 18c — Inline signup-during-checkout ──
  /** Set to true to create a customer account during checkout */
  create_account?: boolean;
  /**
   * Required when create_account=true. Min 8 chars, validate_password_strength
   * applied server-side.
   */
  account_password?: string | null;
  /** Locale per email post-signup (it/en/de/fr) */
  account_locale?: string | null;
}

/**
 * Mirror di backend ShippingAddressInput (routers/public.py:308).
 * Tutti i campi required quando fulfillment_mode=shipping + cart ha physical.
 */
export interface EmbedShippingAddress {
  recipient_name?: string | null;
  /** Via / Street (es. "Via Roma"). */
  line1: string;
  /** Numero civico (es. "12B"). */
  civic?: string | null;
  /** CAP / Postal code (5 digits per IT). */
  postal_code: string;
  city: string;
  /** Sigla provincia IT (2 lettere uppercase) o region per altri paesi. */
  province?: string | null;
  /** ISO 3166-1 alpha-2, default "IT". */
  country?: string;
}

export interface EmbedCheckoutStartResponse {
  order_id: string;
  transaction_mode: string; // "direct" | "request" | "approval"
  order_status: string; // "draft" | "pending" | "confirmed" | ...
  message: string;
  /** Stripe Checkout URL — non-null SOLO per direct mode */
  payment_checkout_url?: string | null;
  payment_reason?: string | null;
  /** Echo del field di request — utile per widget postMessage handler */
  embed_return_url: string;

  // ── Step 18c — Signup-inline result ──
  /** Token JWT customer (auto_login=True), null in guest/auth modes */
  customer_access_token?: string | null;
  /** True quando inline signup ha avuto luogo */
  account_created: boolean;
}

/**
 * postMessage event payload emitted by Step 17 bridge to window.opener.
 * Type-narrowable in TS:
 *   addEventListener('message', (e) => {
 *     if (e.data?.source === 'afianco-embed') {
 *       const msg = e.data as EmbedPostMessage;
 *       // ...
 *     }
 *   });
 */
export interface EmbedPostMessage {
  source: 'afianco-embed';
  type: 'checkout_complete';
  order_id: string;
  order_status: string;
  payment_status: string;
}
