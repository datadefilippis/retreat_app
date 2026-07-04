/**
 * Types for GET /api/public/embed/init/{slug}
 *
 * Mirror di backend `routers/embed_public.py`:
 *   - EmbedCapabilities
 *   - EmbedCategorySummary
 *   - EmbedInitResponse
 */

import type { ProductType, StoreInfo } from './common.js';

export interface EmbedCapabilities {
  checkout_stripe_enabled: boolean;
  cart_enabled: boolean;
  customer_auth_enabled: boolean;
}

export interface EmbedCategorySummary {
  name: string;
  slug: string;
  count: number;
}

export interface EmbedCategoryItem extends EmbedCategorySummary {
  thumbnail_url?: string | null;
}

/**
 * Track E Step 4.3 — Design tokens (Phase 9) per brand customization.
 *
 * Mirror del payload merchant-configurable nell'admin storefront. Tutti
 * i field opzionali — empty dict = merchant non ha customizzato, widget
 * usa defaults.
 *
 * Il widget Lit applica come CSS variables sul host <afianco-storefront-init>:
 *   accent_color    → --afianco-color-primary
 *   font_family     → --afianco-font-family (manrope|inter|serif|system)
 *   border_radius   → --afianco-radius-md   (sharp|standard|soft|pill)
 *   density         → --afianco-spacing-md  (compact|standard|spacious)
 *   header_style    → CSS attribute modifier (solid|translucent|minimal)
 *   card_style      → CSS attribute modifier (shadow|flat|outlined)
 */
export interface EmbedDesignTokens {
  accent_color?: string | null;
  font_family?: 'manrope' | 'inter' | 'serif' | 'system' | string | null;
  border_radius?: 'sharp' | 'standard' | 'soft' | 'pill' | string | null;
  density?: 'compact' | 'standard' | 'spacious' | string | null;
  header_style?: 'solid' | 'translucent' | 'minimal' | string | null;
  card_style?: 'shadow' | 'flat' | 'outlined' | string | null;
  logo_height?: 'sm' | 'md' | 'lg' | string | null;
  logo_fit?: 'contain' | 'cover' | string | null;
  show_store_name?: boolean | null;
}

/**
 * Custom navigation link configurato dal merchant nell'admin (Phase 8).
 * Renderizzato dal widget <afianco-header> tra brand-name e icone account/cart.
 */
export interface EmbedCustomNavLink {
  label: string;
  url: string;
  /** Future: target='_blank' opt-in (default same window). */
  external?: boolean;
}

export interface EmbedInitResponse {
  slug: string;
  org_name: string;
  store_info?: StoreInfo | null;
  currency: string;
  storefront_languages: string[];
  available_product_types: ProductType[];
  categories: EmbedCategorySummary[];
  capabilities: EmbedCapabilities;
  fulfillment_modes: string[];
  /** Track E Step 4.3 — design tokens propagation. */
  design_tokens?: EmbedDesignTokens;
  /** Track E Step 4.3 — custom nav links (Phase 8). */
  custom_nav_links?: EmbedCustomNavLink[];
  /**
   * Track E Step 7.4 — Legal disclosure URLs (Privacy + Termini).
   *
   * Default backend: `${APP_BASE_URL}/s/{slug}/privacy` + `.../terms`
   * (storefront hosted, contenuto JSON da /api/legal/storefront/{slug}/...).
   * Override merchant via store config (privacy_policy_url / terms_service_url)
   * → custom dominio merchant.
   *
   * Il widget Lit usa questi URL per gli anchor `<a target="_blank">` dei
   * checkbox GDPR in `<afianco-signup>` e `<afianco-checkout-button>`,
   * raggiungendo parita' con lo storefront classico che gia' linkava
   * `/s/{slug}/privacy` e `/terms`.
   */
  privacy_policy_url?: string | null;
  terms_service_url?: string | null;
}

export interface EmbedCategoriesResponse {
  slug: string;
  categories: EmbedCategoryItem[];
}
