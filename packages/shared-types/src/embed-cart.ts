/**
 * Types for /api/public/embed/cart/* (Step 15) +
 *           /api/public/embed/cart/{cart_id}/merge (Step 18b)
 *
 * Mirror di backend `models/cart.py`:
 *   - CartItem (internal)
 *   - CartItemInput (PATCH input)
 *   - CartCreate
 *   - CartUpdate
 *   - CartResponse
 *   - CartMergeRequest
 */

export interface CartItem {
  product_id: string;
  quantity: number;
  occurrence_id?: string | null;
  ticket_tier_id?: string | null;
  rental_date_from?: string | null;
  rental_date_to?: string | null;
  rental_notes?: string | null;
  booking_date?: string | null;
  booking_start_time?: string | null;
  booking_end_time?: string | null;
  booking_end_date?: string | null;
  attendees?: Record<string, unknown>[] | null;
  service_option_id?: string | null;
  /** R4 — slot proposto fuori dalle regole (richiesta personalizzata). */
  service_custom_request?: boolean | null;
  extra_selections?: Record<string, unknown> | null;
  /** Snapshot client-friendly (server populates) */
  product_name_snapshot?: string | null;
  unit_price_snapshot?: number | null;
  currency_snapshot?: string | null;
}

export interface CartItemInput {
  product_id: string;
  /** 0 = remove that product line (semantica DELETE inline) */
  quantity: number;
  occurrence_id?: string | null;
  ticket_tier_id?: string | null;
  rental_date_from?: string | null;
  rental_date_to?: string | null;
  rental_notes?: string | null;
  booking_date?: string | null;
  booking_start_time?: string | null;
  booking_end_time?: string | null;
  booking_end_date?: string | null;
  attendees?: Record<string, unknown>[] | null;
  service_option_id?: string | null;
  /** R4 — slot proposto fuori dalle regole (richiesta personalizzata). */
  service_custom_request?: boolean | null;
  /** R2 — extra selezionati (optional/radio). Shape ExtraSelections lato BE. */
  extra_selections?: Record<string, unknown> | null;
}

export interface CartCreate {
  slug: string;
  /** Server-side forced "embed" su /embed/cart endpoint */
  source?: string;
}

export interface CartUpdate {
  items?: CartItemInput[] | null;
  customer_email?: string | null;
}

export interface CartMergeRequest {
  customer_account_id: string;
}

export interface CartResponse {
  id: string;
  /** NB: exposed in legacy storefront response; non rimuovere senza coordinarsi col widget */
  organization_id: string;
  store_id?: string | null;
  items: CartItem[];
  customer_email?: string | null;
  /** Sum of quantities (computed) */
  item_count: number;
  /** Sum of unit_price_snapshot × qty (computed, non-authoritative) */
  subtotal_snapshot: number;
  currency_snapshot?: string | null;
  created_at: string; // ISO datetime
  updated_at: string;
  expires_at: string;
  source: string;
}
