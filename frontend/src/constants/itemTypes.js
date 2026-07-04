/**
 * Typed sellable items — single source of truth for the frontend.
 *
 * Must stay in sync with backend ITEM_TYPES in models/product.py.
 * When a new type is added there, add it here too.
 */

export const ITEM_TYPES = ['physical', 'service', 'rental', 'event_ticket'];

export const PRICE_MODES = ['fixed', 'inquiry'];

export const PRICE_MODE_LABELS = {
  fixed: null,           // no badge for default
  inquiry: 'Su richiesta',
};

export const PRICE_MODE_OPTIONS = [
  { value: 'fixed', label: 'Prezzo fisso', labelKey: 'catalog:price_mode.fixed' },
  { value: 'inquiry', label: 'Su richiesta', labelKey: 'catalog:price_mode.inquiry' },
];

/**
 * Transaction modes — how an item is sold/processed.
 * Separates "what is sold" (item_type) from "how it transacts".
 *   request  — visitor submits request, admin confirms manually
 *   direct   — visitor completes transaction directly (future: checkout)
 *   approval — request with heavier review (availability, custom quote)
 */
export const TRANSACTION_MODES = ['request', 'direct', 'approval'];

export const TRANSACTION_MODE_OPTIONS = [
  { value: 'request', label: 'Su richiesta', labelKey: 'catalog:transaction_mode.request' },
  { value: 'direct', label: 'Diretto', labelKey: 'catalog:transaction_mode.direct' },
  { value: 'approval', label: 'Con approvazione', labelKey: 'catalog:transaction_mode.approval' },
];

/**
 * Public-facing copy per transaction_mode — i18n key references.
 * Consumers call t(`catalog:storefront.${key}`) at render time.
 */
export const TRANSACTION_MODE_COPY_KEYS = {
  request: { headerCta: 'request_header', modalTitle: 'request_modal', modalDesc: 'request_desc', submitBtn: 'request_submit', inquiryToggle: 'request_inquiry' },
  direct: { headerCta: 'direct_header', modalTitle: 'direct_modal', modalDesc: 'direct_desc', submitBtn: 'direct_submit', inquiryToggle: 'request_inquiry' },
  approval: { headerCta: 'approval_header', modalTitle: 'approval_modal', modalDesc: 'approval_desc', submitBtn: 'approval_submit', inquiryToggle: 'request_inquiry' },
};

/**
 * Resolve storefront copy with i18n. Call from a React component.
 */
export const resolveModeCopy = (mode, t) => {
  const keys = TRANSACTION_MODE_COPY_KEYS[mode] || TRANSACTION_MODE_COPY_KEYS.request;
  return {
    headerCta: t(`catalog:storefront.${keys.headerCta}`),
    modalTitle: t(`catalog:storefront.${keys.modalTitle}`),
    modalDesc: t(`catalog:storefront.${keys.modalDesc}`),
    submitBtn: t(`catalog:storefront.${keys.submitBtn}`),
    inquiryToggle: t(`catalog:storefront.${keys.inquiryToggle}`),
  };
};

/**
 * Resolve the dominant transaction_mode for a set of products.
 * If all share the same mode, use it. If mixed, fall back to "request".
 */
export const resolveDominantMode = (productModes) => {
  const unique = [...new Set(productModes.filter(Boolean))];
  return unique.length === 1 ? unique[0] : 'request';
};

/** Human-readable labels (Italian). null = no badge shown. */
export const ITEM_TYPE_LABELS = {
  physical: null,
  service: 'Servizio',
  rental: 'Noleggio',
  event_ticket: 'Evento',
  booking: 'Prenotazione',
};

/**
 * Options for <select> dropdowns in admin forms.
 *
 * Onda 16 Fase 6: `booking` is no longer offered as a creation choice. Admins
 * create 1:1 appointment products via `rental + reservation_flavor=slot`
 * through the ReservationWizard. `ITEM_TYPE_LABELS.booking` and the teal
 * badge style are intentionally kept below so legacy orders and products
 * that haven't been migrated still render correctly.
 */
export const ITEM_TYPE_OPTIONS = [
  { value: 'physical', label: 'Prodotto fisico', labelKey: 'catalog:item_type.physical' },
  { value: 'service', label: 'Servizio', labelKey: 'catalog:item_type.service' },
  { value: 'rental', label: 'Noleggio', labelKey: 'catalog:item_type.rental' },
  { value: 'event_ticket', label: 'Evento/biglietto', labelKey: 'catalog:item_type.event_ticket' },
];

/**
 * Badge color scheme per item type.
 * Used in Products table, Storefront cards, and Orders list/detail.
 */
export const ITEM_TYPE_BADGE_STYLES = {
  service: 'bg-blue-50 text-blue-600',
  rental: 'bg-orange-50 text-orange-600',
  event_ticket: 'bg-purple-50 text-purple-600',
  booking: 'bg-teal-50 text-teal-600',
};

/**
 * Returns the badge className for a given item_type, or null if no badge.
 * Usage: const cls = getItemTypeBadgeClass('rental') → 'bg-orange-50 text-orange-600'
 */
export const getItemTypeBadgeClass = (type) =>
  ITEM_TYPE_BADGE_STYLES[type] || null;


/**
 * Offer Profiles — higher-level business configuration patterns.
 *
 * Each profile maps to recommended defaults for item_type, transaction_mode,
 * and price_mode. Admins can start from a profile and then override.
 *
 * These are NOT new domain types — they're derived guidance from the
 * existing 3 configuration axes.
 */
export const OFFER_PROFILES = [
  {
    id: 'direct_sale',
    label: 'Vendita diretta',
    labelKey: 'catalog:profile.direct_sale.label',
    description: 'Prodotto o servizio acquistabile con pagamento immediato',
    descriptionKey: 'catalog:profile.direct_sale.description',
    icon: '💳',
    behavior: 'checkout',
    behavior_label: 'Pagamento diretto',
    behavior_labelKey: 'catalog:profile.direct_sale.behavior',
    runtime_noteKey: 'catalog:profile.direct_sale.runtime',
    defaults: { item_type: 'physical', transaction_mode: 'direct', price_mode: 'fixed' },
    suggested_unit_label: 'pz',
    runtime_note: 'Il cliente paga direttamente. L\'ordine viene confermato dopo il pagamento.',
    field_hints: {
      unit_price: 'Obbligatorio per il checkout diretto',
    },
    use_cases: ['sell_products_online', 'ecommerce', 'direct_purchase', 'physical_goods'],
  },
  {
    id: 'request_sale',
    label: 'Vendita su richiesta',
    labelKey: 'catalog:profile.request_sale.label',
    description: 'Il cliente richiede, tu confermi e gestisci il pagamento',
    descriptionKey: 'catalog:profile.request_sale.description',
    icon: '📋',
    behavior: 'review',
    behavior_label: 'Conferma manuale',
    behavior_labelKey: 'catalog:profile.request_sale.behavior',
    runtime_noteKey: 'catalog:profile.request_sale.runtime',
    defaults: { item_type: 'physical', transaction_mode: 'request', price_mode: 'fixed' },
    suggested_unit_label: 'pz',
    runtime_note: 'Il cliente invia una richiesta. Tu la rivedi e confermi dalla pagina Ordini.',
    use_cases: ['take_orders', 'b2b_sales', 'wholesale', 'custom_orders', 'manual_confirmation'],
  },
  {
    id: 'quote',
    label: 'Preventivo / Su richiesta',
    labelKey: 'catalog:profile.quote.label',
    description: 'Il cliente chiede informazioni, il prezzo viene definito dopo',
    descriptionKey: 'catalog:profile.quote.description',
    icon: '💬',
    behavior: 'conversation',
    behavior_label: 'Preventivo',
    behavior_labelKey: 'catalog:profile.quote.behavior',
    runtime_noteKey: 'catalog:profile.quote.runtime',
    defaults: { item_type: 'service', transaction_mode: 'request', price_mode: 'inquiry' },
    suggested_unit_label: 'servizio',
    runtime_note: 'Il cliente chiede info senza vedere il prezzo. Gestisci la richiesta dalla pagina Ordini e contatta il cliente con il preventivo.',
    field_hints: {
      unit_price: 'Non necessario — il prezzo è su richiesta',
    },
    use_cases: ['custom_service', 'consulting', 'quote_request', 'price_on_request', 'professional_services'],
  },
  {
    id: 'rental',
    label: 'Noleggio',
    labelKey: 'catalog:profile.rental.label',
    description: 'Il cliente richiede un periodo, tu verifichi la disponibilità',
    descriptionKey: 'catalog:profile.rental.description',
    icon: '📅',
    behavior: 'review',
    behavior_label: 'Verifica disponibilità',
    behavior_labelKey: 'catalog:profile.rental.behavior',
    runtime_noteKey: 'catalog:profile.rental.runtime',
    defaults: { item_type: 'rental', transaction_mode: 'approval', price_mode: 'fixed' },
    suggested_unit_label: 'giorno',
    runtime_note: 'Il cliente sceglie le date dal catalogo. Le richieste arrivano negli Ordini dove puoi verificare la disponibilità prima di confermare.',
    post_save_hint: true,
    temporal_setup_cues: ['setup_cue_unit', 'setup_cue_price'],
    field_hints: {
      unit_price: 'Prezzo per unità di noleggio (giorno, ora, settimana)',
      unit_label: 'Unità di noleggio: giorno, ora, settimana',
      rental_unit: 'Come viene misurato il periodo di noleggio',
    },
    use_cases: ['equipment_rental', 'vehicle_rental', 'space_rental', 'tool_rental', 'availability_check'],
  },
  {
    id: 'open_event',
    label: 'Evento aperto',
    labelKey: 'catalog:profile.open_event.label',
    description: 'Evento senza limite di posti, acquistabile direttamente',
    descriptionKey: 'catalog:profile.open_event.description',
    icon: '🎫',
    behavior: 'checkout',
    behavior_label: 'Pagamento diretto',
    behavior_labelKey: 'catalog:profile.open_event.behavior',
    runtime_noteKey: 'catalog:profile.open_event.runtime',
    defaults: { item_type: 'event_ticket', transaction_mode: 'direct', price_mode: 'fixed' },
    suggested_unit_label: 'posto',
    runtime_note: 'Il cliente acquista direttamente. Dopo aver salvato, apri il prodotto per aggiungere le date e i luoghi dell\'evento.',
    post_save_hint: true,
    temporal_setup_cues: ['setup_cue_dates', 'setup_cue_publish'],
    field_hints: {
      unit_price: 'Prezzo base per biglietto (può essere sovrascritto per singola data)',
    },
    use_cases: ['sell_tickets', 'open_event', 'workshop', 'concert', 'class'],
  },
  {
    id: 'capped_event',
    label: 'Evento con posti limitati',
    labelKey: 'catalog:profile.capped_event.label',
    description: 'Evento con capienza, il cliente richiede e tu verifichi i posti',
    descriptionKey: 'catalog:profile.capped_event.description',
    icon: '🎟️',
    behavior: 'review',
    behavior_label: 'Verifica posti',
    behavior_labelKey: 'catalog:profile.capped_event.behavior',
    runtime_noteKey: 'catalog:profile.capped_event.runtime',
    defaults: { item_type: 'event_ticket', transaction_mode: 'request', price_mode: 'fixed' },
    suggested_unit_label: 'posto',
    runtime_note: 'Il cliente richiede posti. Dopo aver salvato, imposta le date e la capienza massima dalla sezione "Date evento". Le richieste arrivano negli Ordini.',
    post_save_hint: true,
    temporal_setup_cues: ['setup_cue_dates', 'setup_cue_capacity', 'setup_cue_publish'],
    field_hints: {
      unit_price: 'Prezzo base per biglietto (può essere sovrascritto per singola data)',
    },
    use_cases: ['limited_event', 'dinner', 'tasting', 'private_class', 'exclusive_experience', 'reservation'],
  },
];

/**
 * Offer Families — higher-level grouping above profiles.
 *
 * Each family groups profiles that share the same commercial behavior pattern.
 * Family-level metadata describes traits shared by ALL profiles in the family.
 *
 * Usage:
 *   - AI structuring: "instant-purchase offer" → instant family → suggest profiles
 *   - Template foundation: group profiles for template creation
 *   - Analytics: classify catalog by commercial behavior family
 *
 * Families are derived from the existing `behavior` field on profiles.
 * No new persistence needed — purely structural.
 */
export const OFFER_FAMILIES = {
  instant: {
    id: 'instant',
    behavior: 'checkout',
    labelKey: 'family.instant',
    profiles: ['direct_sale', 'open_event'],
    traits: {
      requires_price: true,
      requires_payment_provider: true,
      creates_draft: false,        // auto-confirms after payment
      operator_review: false,
      availability_sensitive: false, // except event with capacity (handled per-profile)
      scheduling: false,            // open_event needs occurrences but not availability check
    },
  },
  manual: {
    id: 'manual',
    behavior: 'review',
    labelKey: 'family.manual',
    profiles: ['request_sale', 'rental', 'capped_event'],
    traits: {
      requires_price: true,         // price shown but operator confirms
      requires_payment_provider: false,
      creates_draft: true,
      operator_review: true,
      availability_sensitive: true,  // rental dates, event capacity
      scheduling: true,             // rental periods, event dates
    },
  },
  dialogue: {
    id: 'dialogue',
    behavior: 'conversation',
    labelKey: 'family.dialogue',
    profiles: ['quote'],
    traits: {
      requires_price: false,        // price defined after conversation
      requires_payment_provider: false,
      creates_draft: true,
      operator_review: true,
      availability_sensitive: false,
      scheduling: false,
    },
  },
};

/**
 * Get the family for a given profile ID.
 */
export const getProfileFamily = (profileId) => {
  for (const family of Object.values(OFFER_FAMILIES)) {
    if (family.profiles.includes(profileId)) return family;
  }
  return OFFER_FAMILIES.manual; // safe default
};

/**
 * Find profiles matching a use case keyword.
 * Returns array of matching profile IDs, best match first.
 *
 * Usage (future AI/onboarding):
 *   findProfilesByUseCase('rental') → ['rental']
 *   findProfilesByUseCase('tickets') → ['open_event', 'capped_event']
 *   findProfilesByUseCase('consulting') → ['quote']
 */
export const findProfilesByUseCase = (keyword) => {
  const kw = keyword.toLowerCase();
  return OFFER_PROFILES
    .filter(p => p.use_cases?.some(uc => uc.includes(kw) || kw.includes(uc)))
    .map(p => p.id);
};

/**
 * Catalog Completeness — profile-aware product readiness checks.
 *
 * Returns an array of {key, message, severity} issues.
 * severity: 'error' = blocking for intended use, 'warning' = weak setup
 *
 * Accepts either a stored product or a form state object.
 * The caller decides how to render the issues.
 */
export const getProductIssues = (product) => {
  const issues = [];
  const it = product.item_type || 'physical';
  const tm = product.transaction_mode || 'request';
  const pm = product.price_mode || 'fixed';
  const price = product.unit_price;
  const meta = product.metadata || {};

  // Issues use key as i18n reference: t(`catalog:issue.${key}`)
  if (tm === 'direct' && pm === 'inquiry')
    issues.push({ key: 'direct_inquiry', severity: 'error' });
  if (tm === 'direct' && pm === 'fixed' && !price && price !== 0)
    issues.push({ key: 'direct_no_price', severity: 'error' });
  if (it === 'rental' && !meta.rental_unit)
    issues.push({ key: 'rental_no_unit', severity: 'warning' });
  if (it === 'event_ticket' && !product.is_published)
    issues.push({ key: 'event_unpublished', severity: 'warning' });
  if (pm === 'fixed' && tm !== 'direct' && !price && price !== 0 && it !== 'service')
    issues.push({ key: 'no_price', severity: 'warning' });

  return issues;
};

/**
 * Derive the closest offer profile for a given configuration.
 * Returns the profile id or null if no close match.
 */
export const deriveOfferProfile = (itemType, transactionMode, priceMode) => {
  if (priceMode === 'inquiry') return 'quote';
  if (itemType === 'rental') return 'rental';
  if (itemType === 'event_ticket') {
    return transactionMode === 'direct' ? 'open_event' : 'capped_event';
  }
  if (transactionMode === 'direct') return 'direct_sale';
  return 'request_sale';
};

// getConfigGuidance() removed — responsibilities consolidated:
//   Error detection → getProductIssues() (direct+inquiry, direct+no price)
//   Runtime info → OFFER_PROFILES[].runtime_note (profile-specific expectations)
// This avoids duplicate messages and unclear concept boundaries.
