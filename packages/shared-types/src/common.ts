/**
 * Common types shared across embed surfaces.
 */

/**
 * Product types canonical (mirror di backend/models/product_types.py:
 * PRODUCT_TYPE_KEYS).
 *
 * Cambiare questo enum = breaking change widget (sentinel pinned).
 */
export type ProductType =
  | 'physical'
  | 'service'
  | 'rental'
  | 'event_ticket'
  | 'digital'
  | 'course'
  | 'booking'; // deprecated → rental, kept for backward-compat with legacy products

/**
 * Transaction modes che indicano cosa succede al "buy" click.
 *  - direct  → Stripe Checkout immediato
 *  - request → richiesta merchant (no charge, conferma manuale)
 *  - approval → review with approve/reject (es. rental)
 */
export type TransactionMode = 'direct' | 'request' | 'approval';

/**
 * Price modes: prezzo fisso vs richiedi preventivo.
 */
export type PriceMode = 'fixed' | 'inquiry';

/**
 * Fulfillment modes esposti per checkout shipping/pickup selection.
 */
export type FulfillmentMode =
  | 'shipping'
  | 'local_pickup'
  | 'local_delivery'
  | 'courier'
  | 'not_required';

/**
 * Sort modes accettati da GET /embed/products.
 * Mirror di backend `EMBED_PRODUCT_SORT_MODES`.
 */
export type EmbedProductSortMode =
  | 'name'
  | 'price_asc'
  | 'price_desc'
  | 'newest';

/**
 * Pagination meta (used by /embed/products and similar list endpoints).
 */
export interface EmbedPagination {
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

/**
 * StoreInfo: branding pubblico-safe (no PII admin).
 * Mirror di backend `routers/public.py::StoreInfo`.
 */
export interface StoreInfo {
  display_name?: string | null;
  store_description?: string | null;
  contact_email?: string | null;
  contact_phone?: string | null;
  logo_url?: string | null;
  brand_color?: string | null;
  brand_color_text?: string | null;
  seo_title?: string | null;
  seo_description?: string | null;
}
