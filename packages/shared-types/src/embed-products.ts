/**
 * Types for GET /api/public/embed/products/{slug} and /products/{slug}/{id}
 *
 * Mirror di backend `routers/embed_public.py`:
 *   - EmbedProductCard
 *   - EmbedProductsResponse
 *   - EmbedProductDetail (Track E Step 2.4.5 — landing drawer)
 */

import type {
  PriceMode,
  ProductType,
  TransactionMode,
  EmbedPagination,
} from './common.js';

export interface EmbedProductCard {
  id: string;
  slug?: string | null;
  name: string;
  description?: string | null;
  image_url?: string | null;
  unit_price?: number | null;
  currency: string;
  category?: string | null;
  /** URL-safe slug normalized server-side */
  category_slug?: string | null;
  item_type: ProductType;
  unit?: string | null;
  unit_label?: string | null;
  price_mode: PriceMode;
  transaction_mode: TransactionMode;
  stock_quantity?: number | null;
}

export interface EmbedProductsResponse {
  slug: string;
  currency: string;
  items: EmbedProductCard[];
  pagination: EmbedPagination;
}

/**
 * Query options for client builders (api-client).
 * Mirror dei query params del backend endpoint.
 */
export interface EmbedProductsQuery {
  category?: string;
  type?: ProductType;
  sort?: 'name' | 'price_asc' | 'price_desc' | 'newest' | 'relevance';
  limit?: number;
  offset?: number;
  /**
   * Track E Step 5.1 — Full-text search (Mongo $text con italian stemmer).
   * Cerca in product.name (weight 3) + product.description (weight 1).
   * Empty/whitespace = no filter. Max 200 char (defense-in-depth).
   */
  q?: string;
}

/**
 * Detail surface per GET /api/public/embed/products/{slug}/{product_id}.
 *
 * Track E Step 2.4.5 → 2.4.6 — landing drawer del widget con parita'
 * storefront completa: type-aware UX per service/event/rental/course/digital.
 *
 * Mirror del Pydantic `EmbedProductDetail` (backend/routers/embed_public.py)
 * che a sua volta riusa `PublicServiceOption`, `PublicOccurrence`,
 * `PublicTier`, `FieldConfig` (backend/routers/public.py) per consistency
 * tra storefront-hosted e widget embed.
 */

export interface EmbedServiceOption {
  id: string;
  label: string;
  description?: string | null;
  price: number;
  duration_minutes_override?: number | null;
  sort_order?: number;
}

export interface EmbedTier {
  id: string;
  label: string;
  description?: string | null;
  price: number;
  /** None / undefined = unlimited (within occurrence capacity). */
  remaining?: number | null;
  sort_order?: number;
}

export interface EmbedOccurrence {
  id: string;
  /** ISO datetime string. */
  start_at: string;
  end_at?: string | null;
  location?: string | null;
  capacity?: number | null;
  booked_count?: number | null;
  remaining?: number | null;
  price_override?: number | null;
  tiers?: EmbedTier[];
  // Structured presentation (E2)
  venue_name?: string | null;
  address?: string | null;
  city?: string | null;
  postal_code?: string | null;
  country?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  map_url?: string | null;
  cover_image_url?: string | null;
  long_description?: string | null;
  slug?: string | null;
}

/**
 * Field config per attendee_fields + order_fields. Mirror Pydantic
 * FieldConfig (backend/models/field_config.py).
 *
 * Onda 16 MVP: solo 3 types (text/textarea/number). Future F3 estende
 * con date/select/checkbox.
 */
export interface EmbedFieldConfig {
  /** Slug-like stable identifier (1-40 chars, [a-z0-9_-]). */
  id: string;
  label: string;
  type?: 'text' | 'textarea' | 'number';
  required?: boolean;
  placeholder?: string | null;
  help_text?: string | null;
  /** Order within scope (lower = first). Default 0. */
  sort_order?: number;
}

/**
 * ProductExtra — add-on cross-type (services/rental/physical/digital).
 * Onda 16 — generalizzazione di ServiceOption con 3 kind + 3 modifier.
 *
 * Mirror del Pydantic ProductExtra (backend/models/product_extra.py).
 */
export type EmbedExtraKind = 'mandatory' | 'optional' | 'radio_variant';
export type EmbedPriceModifierType = 'flat' | 'per_day' | 'per_unit';

export interface EmbedProductExtra {
  id: string;
  kind: EmbedExtraKind;
  /** Required when kind === 'radio_variant'; raggruppa picker mutually exclusive. */
  group_key?: string | null;
  label: string;
  description?: string | null;
  price: number;
  price_modifier_type: EmbedPriceModifierType;
  /** Override slot duration (solo per service/slot radio_variant). */
  duration_minutes_override?: number | null;
  is_default?: boolean;
  sort_order?: number;
}

/**
 * Selezione user-side dei product extras (passata al cart payload come
 * `extra_selections`). Per kind=optional: presente nella lista se checkbox
 * spuntato. Per kind=radio_variant: presente solo per quello selezionato
 * nel gruppo. Per kind=mandatory: sempre presente (server auto-applica).
 */
export interface EmbedExtraSelection {
  extra_id: string;
  /** Echo del kind per validazione client-side (server riverifica). */
  kind?: EmbedExtraKind;
  group_key?: string | null;
}

export interface EmbedProductDetail extends EmbedProductCard {
  offer_profile_id?: string | null;

  // Hero / landing display
  cover_image_url?: string | null;
  long_description?: string | null;

  // SERVICE — opzioni + slot booking
  service_options?: EmbedServiceOption[];
  service_duration_minutes?: number | null;
  service_allow_custom_request?: boolean;
  has_availability_slots?: boolean;
  duration_label?: string | null;
  slot_duration_minutes?: number | null;

  // EVENT_TICKET — occurrences + tier + attendee form
  occurrences?: EmbedOccurrence[];
  requires_attendee_details?: boolean;
  require_attendee_email?: boolean;
  require_attendee_phone?: boolean;
  attendee_fields?: EmbedFieldConfig[];
  order_fields?: EmbedFieldConfig[];

  // RENTAL — flavor + extras (extras anche cross-type: physical/digital/service)
  rental_unit?: string | null;
  reservation_flavor?: string | null;
  extras?: EmbedProductExtra[];

  // COURSE — light counters
  course_lessons_count?: number | null;
  course_duration_seconds?: number | null;
  course_access_policy?: string | null;
  course_access_expiry_days?: number | null;

  // T&C
  terms_content?: string | null;
}

// ─────────────────────────────────────────────────────────────────────
// Availability endpoint shape — Track E Step 2.4.6
// GET /api/public/embed/products/{slug}/{id}/availability
// Mirror of EmbedAvailabilityResponse Pydantic (backend/routers/embed_public.py)
// ─────────────────────────────────────────────────────────────────────

export interface EmbedAvailabilitySlot {
  start: string;  // HH:MM
  end: string;    // HH:MM
}

export interface EmbedAvailabilityDay {
  date: string;     // YYYY-MM-DD
  day_name: string; // localized "lunedi" etc.
  slots: EmbedAvailabilitySlot[];
}

export interface EmbedAvailabilityResponse {
  slug: string;
  product_id: string;
  duration_minutes?: number | null;
  days: EmbedAvailabilityDay[];
}

export interface EmbedAvailabilityQuery {
  date_from?: string;  // YYYY-MM-DD
  date_to?: string;    // YYYY-MM-DD
  duration?: number;   // override slot duration
}

// ─────────────────────────────────────────────────────────────────────
// Price preview — Track E Step 2.4.10
// POST /api/public/embed/price-preview/{slug}
// Mirror del Pydantic EmbedPricePreviewRequest (backend/routers/embed_public.py)
// ─────────────────────────────────────────────────────────────────────

/**
 * Shape ExtraSelections inviata al backend per il calcolo extras pricing.
 * Mirror del Pydantic ``ExtraSelections`` (backend/models/product_extra.py).
 *
 *   mandatory_confirmed: ignorato server-side (sempre True), courtesy flag UI
 *   optional_ids: lista id degli extras optional checkati
 *   radio_picks: map group_key → extra_id (uno per gruppo)
 */
export interface EmbedExtraSelectionsPayload {
  mandatory_confirmed?: boolean;
  optional_ids?: string[];
  radio_picks?: Record<string, string>;
}

export interface EmbedPricePreviewRequest {
  product_id: string;
  quantity?: number;
  discount_pct?: number;
  // Rental flavor=range
  date_from?: string | null;
  date_to?: string | null;
  // Extras
  extra_selections?: EmbedExtraSelectionsPayload | null;
  // Rental flavor=slot (Onda 17)
  slot_date_from?: string | null;
  slot_time_from?: string | null;
  slot_date_to?: string | null;
  slot_time_to?: string | null;
}

/**
 * Response shape — mirror di pricing.compute_line_total result.
 * Tutti i prezzi sono in unit della product currency (es. EUR).
 */
export interface EmbedPricePreviewResponse {
  subtotal: number;
  discount: number;
  total: number;
  currency?: string;
  /** Breakdown opzionale: { extra_id: amount_applied }. */
  extras_breakdown?: Record<string, number>;
  /** Tasse calcolate (può essere 0 se merchant senza VAT settings). */
  tax?: number;
  // Catch-all per campi extra che il backend potrebbe aggiungere
  [k: string]: unknown;
}
