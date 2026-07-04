/**
 * Track E Step 4.2 — Shipping options embed types.
 *
 * Mirror di backend EmbedShippingOption/EmbedShippingOptionsResponse
 * (backend/routers/embed_public.py).
 *
 * Endpoint: GET /api/public/embed/shipping-options/{slug}
 *
 * Flow widget:
 *   1. Customer apre checkout drawer + ha physical products + sceglie shipping
 *   2. Widget fetcha shipping-options del store
 *   3. Render radio picker con label + base_price + free_shipping hint
 *   4. Selezione → passa shipping_option_id al price-preview + checkout
 */

export interface EmbedShippingOption {
  id: string;
  label: string;
  description?: string | null;
  /** Prezzo base (in store currency). */
  base_price: number;
  /**
   * None = no free-shipping threshold. Quando set, customer con physical
   * subtotal >= threshold paga 0 per questa option (UX badge "Spedizione
   * gratuita oltre €{threshold}").
   */
  free_shipping_threshold?: number | null;
  sort_order?: number;
}

export interface EmbedShippingOptionsResponse {
  options: EmbedShippingOption[];
}
