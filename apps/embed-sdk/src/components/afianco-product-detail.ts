/**
 * <afianco-product-detail> — Track E Step 2.4.5 (Product landing drawer).
 *
 * Drawer modal che mostra il dettaglio di un singolo prodotto quando
 * l'utente clicca su una product-card nel widget grid. Risolve il problema
 * UX "tutti i prodotti vengono aggiunti al carrello senza landing":
 *
 *   prima: card click → afianco:add-to-cart (cart drawer)
 *   adesso: card click → afianco:product-view-requested → questo drawer
 *           → CTA "Aggiungi al carrello" → afianco:add-to-cart
 *
 * Architettura — loose coupling via document event bus
 * ====================================================
 *
 * Il componente NON e' wired direttamente alle product-card. Ascolta
 * il document event ``afianco:product-view-requested`` (bubbles+composed)
 * dispatched dalle card al click. Pattern publish-subscribe coerente con
 * <afianco-header> / <afianco-cart-drawer> / <afianco-account>.
 *
 * Flow del fetch
 * ==============
 *
 *   1. Card click → event ``afianco:product-view-requested`` (detail:
 *      { product_id })
 *   2. Questo componente apre il drawer + chiama
 *      ``client.embed.getProduct(productId)``
 *   3. Render type-aware UX:
 *      - physical / digital / course: qty stepper + CTA
 *      - service: qty stepper + CTA (v1 — calendario in v2)
 *      - event_ticket: qty stepper + CTA (v1 — tier picker in v2)
 *      - rental: qty stepper + CTA (v1 — date range in v2)
 *   4. User clicca "Aggiungi al carrello" → dispatch ``afianco:add-to-cart``
 *      che <afianco-cart-drawer> intercetta + aggiunge l'item
 *   5. Drawer si chiude automaticamente
 *
 * Custom events emessi
 * ====================
 *
 *   - ``afianco:product-detail-opened`` (detail: { product_id })
 *   - ``afianco:product-detail-closed``
 *   - ``afianco:add-to-cart`` (detail: { product, quantity }) — al click CTA
 *
 * Custom events consumati
 * =======================
 *
 *   - ``afianco:product-view-requested`` (detail: { product_id }) — apre
 *
 * Accessibility
 * =============
 *   - role="dialog" + aria-modal="true"
 *   - aria-labelledby legato al titolo del prodotto
 *   - ESC chiude il drawer
 *   - Focus trap futuro (V2) — per ora click outside / ESC sufficienti
 */

import { LitElement, html, css, nothing } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { consume } from '@lit/context';
import { afiancoBaseStyles } from '@afianco/design-tokens';
// Sprint 4 W4.7 — i18n wiring
import { t } from '../i18n/index.js';
import type {
  EmbedProductDetail,
  EmbedProductCard,
  EmbedServiceOption,
  EmbedOccurrence,
  EmbedTier,
  EmbedExtraSelection,
} from '@afianco/api-client';
import {
  storefrontContext,
  STOREFRONT_INITIAL,
  type StorefrontContext,
} from '../context.js';
import { StoreConsumerController } from '../store/store-consumer.js';
import { SingletonController } from '../store/singleton-guard.js';

// Track E Step 2.4.7 — Import side-effect dei sub-component pickers per
// garantire la registrazione del custom element (questi componenti sono
// usati nel render in base a item_type del prodotto).
import './afianco-service-options-picker.js';
import './afianco-availability-picker.js';
import './afianco-occurrence-picker.js';
import './afianco-tier-picker.js';
import './afianco-date-range-picker.js';
import './afianco-custom-request.js';
import type { CustomRequestDetail } from './afianco-custom-request.js';
import './afianco-course-preview.js';
// Track E Step 2.4.9 — Extras picker (mandatory/optional/radio_variant)
import './afianco-extras-picker.js';
// Track E Step 2.4.10 — Price preview live (debounced server-side compute)
import './afianco-price-preview.js';


@customElement('afianco-product-detail')
export class AfiancoProductDetail extends LitElement {
  // ── Context consumption ─────────────────────────────────────────────

  @consume({ context: storefrontContext, subscribe: true })
  @state()
  private ctx: StorefrontContext = STOREFRONT_INITIAL;

  /** À-la-carte: aggancio al kernel se fuori da un provider (no-op se dentro). */
  protected _store = new StoreConsumerController(this);

  /** Guard singleton: un solo product-detail attivo per slug. */
  protected _singleton = new SingletonController(this, 'product-detail');

  // ── Public attributes ────────────────────────────────────────────────

  /** Open/close state (reflectato sul host per CSS state). */
  @property({ type: Boolean, reflect: true })
  open = false;

  // ── Internal state ───────────────────────────────────────────────────

  /** Currently displayed product (fetched). */
  @state()
  private product: EmbedProductDetail | null = null;

  /** Loading state. */
  @state()
  private loading = false;

  /** Last fetch error message (i18n italian for v1). */
  @state()
  private error: string | null = null;

  /** Quantity selector value (clamped >=1 e <= stock_quantity quando tracked). */
  @state()
  private quantity = 1;

  // ── Track E Step 2.4.7 — Type-specific selection state ──
  //
  // Ogni type del prodotto richiede uno specifico set di scelte prima
  // dell'add-to-cart. Lo state qui sotto e' popolato dai sub-component
  // picker via custom events; il CTA "Aggiungi al carrello" e' disabled
  // finche' lo stato required non e' completo (vedi `isReady` getter).

  /** SERVICE — Opzione selezionata (radio cards di service_options[]). */
  @state()
  private selectedServiceOption: EmbedServiceOption | null = null;

  /** SERVICE — Slot selezionato {date, start, end, day_name}. */
  @state()
  private selectedSlot: {
    date: string;
    start: string;
    end: string;
    day_name: string;
  } | null = null;

  /** EVENT_TICKET — Occurrence (data evento) selezionata. */
  @state()
  private selectedOccurrence: EmbedOccurrence | null = null;

  /** EVENT_TICKET — Tier biglietto selezionato. */
  @state()
  private selectedTier: EmbedTier | null = null;

  /** RENTAL — Date range selezionato (flavor=range). */
  @state()
  private selectedDateRange: { from: string; to: string; days: number } | null = null;

  /** R3 — date occupate per il rental corrente (advisory UX nel picker). */
  @state()
  private rentalBlockedDates: string[] = [];

  /** R4 — richiesta personalizzata (service senza slot). null = non proposta
   *  o incompleta; valorizzata solo quando complete=true. */
  @state()
  private customRequest: CustomRequestDetail | null = null;

  /**
   * EXTRAS — selezioni del picker mandatory/optional/radio_variant (E2.4.9).
   * Mandatory sempre incluso, optional checkbox, radio uno per group_key.
   * Passato al cart payload come `extra_selections`.
   */
  @state()
  private selectedExtras: EmbedExtraSelection[] = [];

  /** Guard per listener attach. */
  private _listenerAttached = false;

  // ── Lifecycle ────────────────────────────────────────────────────────

  connectedCallback(): void {
    super.connectedCallback();
    if (!this._listenerAttached) {
      // Primary trigger: product-card click bubbles a document
      document.addEventListener(
        'afianco:product-view-requested',
        this._handleViewRequested as unknown as EventListener,
      );
      // ESC closes (a11y standard)
      document.addEventListener('keydown', this._handleKeydown);
      this._listenerAttached = true;
    }
  }

  disconnectedCallback(): void {
    if (this._listenerAttached) {
      document.removeEventListener(
        'afianco:product-view-requested',
        this._handleViewRequested as unknown as EventListener,
      );
      document.removeEventListener('keydown', this._handleKeydown);
      this._listenerAttached = false;
    }
    super.disconnectedCallback();
  }

  // ── Event handlers ───────────────────────────────────────────────────

  private _handleViewRequested = async (e: CustomEvent): Promise<void> => {
    if (!this._singleton.active) return; // solo il detail attivo apre
    const detail = e.detail as { product_id?: string; product?: EmbedProductCard } | undefined;
    const productId = detail?.product_id ?? detail?.product?.id;
    if (!productId) return;

    this.setOpen(true);
    await this.fetchProduct(productId);
  };

  private _handleKeydown = (e: KeyboardEvent): void => {
    if (e.key === 'Escape' && this.open) {
      e.preventDefault();
      this.setOpen(false);
    }
  };

  private setOpen(value: boolean): void {
    if (this.open === value) return;
    this.open = value;
    this.dispatchEvent(
      new CustomEvent(
        value ? 'afianco:product-detail-opened' : 'afianco:product-detail-closed',
        {
          detail: value && this.product ? { product_id: this.product.id } : {},
          bubbles: true,
          composed: true,
        },
      ),
    );
    // Quando si chiude, resettiamo lo stato per il prossimo open
    if (!value) {
      // Piccolo delay per non flash sulla transition di chiusura
      setTimeout(() => {
        if (!this.open) {
          this.product = null;
          this.error = null;
          this.quantity = 1;
          this.resetTypeSpecificState();
        }
      }, 250);
    }
  }

  private async fetchProduct(productId: string): Promise<void> {
    if (!this.ctx?.client) {
      this.error = t('product.error_storefront_not_ready');
      return;
    }
    this.loading = true;
    this.error = null;
    this.product = null;
    this.quantity = 1;
    // Reset type-specific selections quando si carica un nuovo prodotto
    this.resetTypeSpecificState();

    try {
      const product = await this.ctx.client.embed.getProduct(productId);
      this.product = product;
      // R3 — rental flavor=range: precarica le date occupate (advisory UX).
      // Best-effort: un errore non deve bloccare il render del prodotto.
      if (
        product.item_type === 'rental' &&
        (product.reservation_flavor === 'range' || product.reservation_flavor == null)
      ) {
        void this.loadRentalBlockedDates(productId);
      }
      // Auto-select prima service_option se ce n'e' UNA sola (UX: skip click)
      if (
        product.item_type === 'service' &&
        product.service_options &&
        product.service_options.length === 1
      ) {
        this.selectedServiceOption = product.service_options[0]!;
      }
      // Auto-select prima occurrence se ce n'e' UNA sola
      if (
        product.item_type === 'event_ticket' &&
        product.occurrences &&
        product.occurrences.length === 1
      ) {
        this.selectedOccurrence = product.occurrences[0]!;
      }
    } catch (e) {
      const msg = (e as Error)?.message ?? t('product.error_load');
      this.error = msg;
    } finally {
      this.loading = false;
    }
  }

  /**
   * R3 — carica le date occupate per un rental (flavor=range) e le passa
   * al date-range-picker come hint advisory. Best-effort: errori silenziati,
   * il guard atomico a confirm-time resta la verità sulla disponibilità.
   */
  private async loadRentalBlockedDates(productId: string): Promise<void> {
    if (!this.ctx?.client) return;
    try {
      const now = new Date();
      const from = now.toISOString().slice(0, 10);
      const horizon = new Date(now);
      horizon.setDate(horizon.getDate() + 365);
      const to = horizon.toISOString().slice(0, 10);
      const res = await this.ctx.client.embed.getRentalBlockedDates(productId, { from, to });
      // Guard: il prodotto potrebbe essere cambiato durante la fetch.
      if (this.product?.id === productId) {
        this.rentalBlockedDates = Array.isArray(res?.blocked_dates) ? res.blocked_dates : [];
      }
    } catch {
      // silenzioso — il picker funziona comunque, validazione server-side resta
    }
  }

  private updateQuantity(delta: number): void {
    if (!this.product) return;
    const next = this.quantity + delta;
    const min = 1;
    const max = typeof this.product.stock_quantity === 'number' && this.product.stock_quantity > 0
      ? this.product.stock_quantity
      : 99; // sensible cap quando stock untracked
    this.quantity = Math.max(min, Math.min(max, next));
  }

  // ── Track E Step 2.4.7 — Sub-component picker event handlers ────────

  private handleServiceOptionSelected = (e: CustomEvent): void => {
    this.selectedServiceOption = e.detail?.option ?? null;
  };

  private handleSlotSelected = (e: CustomEvent): void => {
    this.selectedSlot = e.detail ?? null;
  };

  private handleSlotCleared = (): void => {
    this.selectedSlot = null;
  };

  private handleOccurrenceSelected = (e: CustomEvent): void => {
    this.selectedOccurrence = e.detail?.occurrence ?? null;
    // Reset tier quando cambia occurrence (tiers sono per-occurrence)
    this.selectedTier = null;
  };

  private handleTierChanged = (e: CustomEvent): void => {
    this.selectedTier = e.detail?.tier ?? null;
    this.quantity = e.detail?.quantity ?? 1;
  };

  private handleDateRangeSelected = (e: CustomEvent): void => {
    this.selectedDateRange = e.detail ?? null;
  };

  private handleDateRangeCleared = (): void => {
    this.selectedDateRange = null;
  };

  private handleExtrasChanged = (e: CustomEvent): void => {
    this.selectedExtras = e.detail?.selections ?? [];
  };

  /**
   * Reset di tutto lo state type-specific. Chiamato quando il drawer
   * viene chiuso o quando si carica un nuovo prodotto.
   */
  private resetTypeSpecificState(): void {
    this.selectedServiceOption = null;
    this.selectedSlot = null;
    this.selectedOccurrence = null;
    this.selectedTier = null;
    this.selectedDateRange = null;
    this.selectedExtras = [];
    this.rentalBlockedDates = [];
    this.customRequest = null;
  }

  /** R4 — riceve la proposta dal form custom-request: tiene solo le complete. */
  private handleCustomRequestChanged(e: CustomEvent<CustomRequestDetail>): void {
    this.customRequest = e.detail.complete ? e.detail : null;
  }

  /**
   * Computa se i required fields per il type corrente sono tutti
   * popolati. Disabilita il CTA finche' false.
   *
   * Type-by-type:
   *   - physical / digital / course: sempre ready (solo qty stepper)
   *   - service: ready se has_availability_slots=false OPPURE slot selezionato
   *              + (se service_options.length > 0) opzione selezionata
   *   - event_ticket: ready se occurrence selezionata
   *                   + (se tier presenti) tier selezionato
   *   - rental: ready se date range selezionato (per flavor=range)
   */
  private get isTypeRequiredReady(): boolean {
    const p = this.product;
    if (!p) return false;

    switch (p.item_type) {
      case 'service': {
        // Service options: se la lista esiste e non e' vuota, richiediamo selezione
        if ((p.service_options?.length ?? 0) > 0 && !this.selectedServiceOption) {
          return false;
        }
        // Slot: se has_availability_slots e' true, richiediamo selezione
        if (p.has_availability_slots && !this.selectedSlot) {
          return false;
        }
        return true;
      }
      case 'event_ticket': {
        if ((p.occurrences?.length ?? 0) > 0 && !this.selectedOccurrence) {
          return false;
        }
        // Tier required solo se l'occurrence ha tiers
        const tiers = this.selectedOccurrence?.tiers ?? [];
        if (tiers.length > 0 && !this.selectedTier) {
          return false;
        }
        return true;
      }
      case 'rental': {
        // Per ora supportiamo solo flavor=range nel widget (V1).
        // flavor=slot (rental con slot picker) verra' in V2 — fallback ad add-to-cart
        // diretto (quantity-only) per non bloccare il customer.
        if (p.reservation_flavor === 'range' && !this.selectedDateRange) {
          return false;
        }
        return true;
      }
      case 'course':
      case 'digital':
      case 'physical':
      default:
        return true;
    }
  }

  private handleAddToCart(): void {
    if (!this.product) return;
    if (!this.isTypeRequiredReady) return;

    // Track E Step 2.4.7 — Build cart payload type-specific.
    // <afianco-cart-drawer> intercetta l'evento e mappa i campi extras
    // sul CartItemInput per la chiamata POST /api/public/embed/cart.
    const extras: Record<string, unknown> = {};

    if (this.product.item_type === 'service') {
      if (this.selectedServiceOption) {
        extras.service_option_id = this.selectedServiceOption.id;
      }
      if (this.selectedSlot) {
        extras.booking_date = this.selectedSlot.date;
        extras.booking_start_time = this.selectedSlot.start;
        extras.booking_end_time = this.selectedSlot.end;
      } else if (this.customRequest) {
        // R4 — richiesta personalizzata: slot proposto fuori dalle regole.
        // Marca il flag così il validator backend lo accetta e l'admin lo vede.
        extras.booking_date = this.customRequest.date;
        extras.booking_start_time = this.customRequest.start;
        extras.booking_end_time = this.customRequest.end;
        extras.service_custom_request = true;
        if (this.customRequest.notes) {
          extras.rental_notes = this.customRequest.notes;
        }
      }
    } else if (this.product.item_type === 'event_ticket') {
      if (this.selectedOccurrence) {
        extras.occurrence_id = this.selectedOccurrence.id;
      }
      if (this.selectedTier) {
        extras.ticket_tier_id = this.selectedTier.id;
      }
    } else if (this.product.item_type === 'rental') {
      if (this.selectedDateRange) {
        extras.rental_date_from = this.selectedDateRange.from;
        extras.rental_date_to = this.selectedDateRange.to;
      }
    }
    // physical / digital / course: no type-specific extras, ma extra_selections
    // (dal extras-picker) si applicano cross-type → aggiunti dopo.

    // Track E Step 2.4.9 — extra_selections cross-type (mandatory/optional/
    // radio_variant). Inviati al cart come array di {extra_id, kind, group_key}.
    if (this.selectedExtras.length > 0) {
      extras.extra_selections = this.selectedExtras;
    }

    this.dispatchEvent(
      new CustomEvent<{
        product: EmbedProductCard;
        quantity: number;
        extras?: Record<string, unknown>;
      }>('afianco:add-to-cart', {
        detail: {
          product: this.product as unknown as EmbedProductCard,
          quantity: this.quantity,
          extras: Object.keys(extras).length > 0 ? extras : undefined,
        },
        bubbles: true,
        composed: true,
      }),
    );

    // Chiudi drawer + apri cart drawer (UX: post-add, customer vuole
    // vedere il riepilogo cart per checkout o continue)
    this.setOpen(false);
    setTimeout(() => {
      document.dispatchEvent(
        new CustomEvent('afianco:open-cart', { bubbles: true, composed: true }),
      );
    }, 200);
  }

  // ── Derived helpers ──────────────────────────────────────────────────

  private formatPrice(amount: number | null | undefined, currency: string): string {
    if (amount == null) return '—';
    try {
      return new Intl.NumberFormat(undefined, {
        style: 'currency',
        currency,
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }).format(amount);
    } catch {
      return `${amount.toFixed(2)} ${currency}`;
    }
  }

  private ctaLabel(p: EmbedProductDetail): string {
    // W4.8 — Resolve label dinamicamente via i18n (4 lingue)
    if (p.price_mode === 'inquiry') return t('product.cta_request_quote');
    switch (p.transaction_mode) {
      case 'request':
        return t('product.cta_request_info');
      case 'approval':
        return p.item_type === 'rental'
          ? t('product.cta_request_rental')
          : t('product.cta_request');
      case 'direct':
      default:
        if (p.item_type === 'event_ticket') return t('product.cta_buy_ticket');
        if (p.item_type === 'course') return t('product.cta_enroll_course');
        if (p.item_type === 'rental') return t('product.cta_rent');
        if (p.item_type === 'digital') return t('product.cta_buy');
        return t('product.cta_add_to_cart');
    }
  }

  private get isDisabled(): boolean {
    if (!this.product) return true;
    if (this.product.stock_quantity === 0) return true;
    // Track E Step 2.4.7 — CTA disabled finche' i required type-specific
    // fields non sono popolati (es. slot selezionato per service).
    if (!this.isTypeRequiredReady) return true;
    return false;
  }

  private get typeBadgeLabel(): string | null {
    if (!this.product) return null;
    switch (this.product.item_type) {
      case 'service': return t('product.type_service');
      case 'event_ticket': return t('product.type_event');
      case 'rental': return t('product.type_rental');
      case 'course': return t('product.type_course');
      case 'digital': return t('product.type_digital');
      case 'physical': return t('product.type_physical');
      default: return null;
    }
  }

  // ── Styles ───────────────────────────────────────────────────────────

  static styles = [
    afiancoBaseStyles,
    css`
      :host {
        display: contents;
      }

      /* ── Scrim ─────────────────────────────────────────────────────── */
      .scrim {
        position: fixed;
        inset: 0;
        background: rgba(15, 23, 42, 0.5);
        opacity: 0;
        pointer-events: none;
        transition: opacity 0.2s ease;
        z-index: 9998;
        cursor: pointer;
      }
      :host([open]) .scrim {
        opacity: 1;
        pointer-events: auto;
      }

      /* ── Drawer (mobile: full screen, desktop: side panel) ────────── */
      .drawer {
        position: fixed;
        top: 0;
        right: 0;
        bottom: 0;
        width: 100%;
        max-width: 560px;
        background: var(--afianco-color-bg, #ffffff);
        box-shadow: -4px 0 24px rgba(0, 0, 0, 0.15);
        transform: translateX(100%);
        transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        z-index: 9999;
        display: flex;
        flex-direction: column;
        visibility: hidden;
        pointer-events: none;
      }
      :host([open]) .drawer {
        transform: translateX(0);
        visibility: visible;
        pointer-events: auto;
      }

      /* ── Header sticky con close ──────────────────────────────────── */
      .drawer-header {
        flex-shrink: 0;
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 14px 20px;
        border-bottom: 1px solid var(--afianco-color-border, #e5e7eb);
        background: var(--afianco-color-bg, #ffffff);
        position: sticky;
        top: 0;
        z-index: 1;
      }
      .drawer-title {
        font-size: 15px;
        font-weight: 600;
        color: var(--afianco-color-text, #111827);
        margin: 0;
      }
      .close-btn {
        background: transparent;
        border: 1px solid transparent;
        color: var(--afianco-color-text-secondary, #6b7280);
        cursor: pointer;
        font-size: 24px;
        line-height: 1;
        width: 36px;
        height: 36px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        border-radius: 6px;
        flex-shrink: 0;
      }
      .close-btn:hover {
        background: var(--afianco-color-muted, #f3f4f6);
        border-color: var(--afianco-color-border, #e5e7eb);
      }
      .close-btn:focus-visible {
        outline: 2px solid var(--afianco-color-primary, #4b72ce);
        outline-offset: 2px;
      }

      /* ── Body scrollable ──────────────────────────────────────────── */
      .drawer-body {
        flex: 1;
        overflow-y: auto;
        padding: 0;
      }

      .hero-image-wrap {
        width: 100%;
        aspect-ratio: 16 / 10;
        background: var(--afianco-color-muted, #f3f4f6);
        position: relative;
        overflow: hidden;
      }
      .hero-image-wrap img {
        width: 100%;
        height: 100%;
        object-fit: cover;
        display: block;
      }
      .hero-placeholder {
        width: 100%;
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
        color: var(--afianco-color-text-muted, #9ca3af);
        font-size: 14px;
      }

      .content {
        padding: 24px;
      }

      .badge-row {
        display: flex;
        gap: 8px;
        align-items: center;
        flex-wrap: wrap;
        margin-bottom: 12px;
      }
      .type-badge {
        display: inline-flex;
        align-items: center;
        padding: 4px 10px;
        background: var(--afianco-color-primary-soft, #eef2ff);
        color: var(--afianco-color-primary, #4b72ce);
        border-radius: 9999px;
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
      }
      .category-badge {
        display: inline-flex;
        align-items: center;
        padding: 4px 10px;
        background: var(--afianco-color-muted, #f3f4f6);
        color: var(--afianco-color-text-secondary, #6b7280);
        border-radius: 9999px;
        font-size: 11px;
        font-weight: 500;
      }

      .product-name {
        font-size: 22px;
        font-weight: 700;
        line-height: 1.3;
        color: var(--afianco-color-text, #111827);
        margin: 0 0 12px;
      }

      .price-row {
        display: flex;
        align-items: baseline;
        gap: 8px;
        margin-bottom: 20px;
      }
      .price {
        font-size: 24px;
        font-weight: 700;
        color: var(--afianco-color-text, #111827);
      }
      .price-unit {
        font-size: 13px;
        color: var(--afianco-color-text-secondary, #6b7280);
        font-weight: 400;
      }
      .price-inquiry {
        font-size: 16px;
        font-weight: 600;
        color: var(--afianco-color-text-secondary, #6b7280);
        font-style: italic;
      }

      .description {
        font-size: 14px;
        line-height: 1.6;
        color: var(--afianco-color-text, #111827);
        margin-bottom: 24px;
        white-space: pre-wrap;
      }

      .stock-warning {
        display: inline-block;
        padding: 4px 10px;
        background: #fef3c7;
        color: #92400e;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 500;
        margin-bottom: 16px;
      }
      .stock-out {
        background: #fee2e2;
        color: #991b1b;
      }

      /* ── Quantity stepper ─────────────────────────────────────────── */
      .qty-section {
        margin-bottom: 24px;
      }
      .qty-label {
        font-size: 13px;
        font-weight: 600;
        color: var(--afianco-color-text, #111827);
        margin-bottom: 8px;
        display: block;
      }
      .qty-controls {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        background: var(--afianco-color-muted, #f3f4f6);
        border-radius: 8px;
        padding: 4px;
      }
      .qty-btn {
        width: 32px;
        height: 32px;
        background: var(--afianco-color-bg, #ffffff);
        border: 1px solid var(--afianco-color-border, #e5e7eb);
        border-radius: 6px;
        cursor: pointer;
        font-size: 16px;
        font-weight: 600;
        color: var(--afianco-color-text, #111827);
        display: inline-flex;
        align-items: center;
        justify-content: center;
      }
      .qty-btn:hover:not(:disabled) {
        background: var(--afianco-color-muted, #f3f4f6);
      }
      .qty-btn:disabled {
        opacity: 0.4;
        cursor: not-allowed;
      }
      .qty-value {
        min-width: 36px;
        text-align: center;
        font-size: 14px;
        font-weight: 600;
      }

      /* ── Footer sticky con CTA ─────────────────────────────────────── */
      .drawer-footer {
        flex-shrink: 0;
        padding: 16px 20px;
        border-top: 1px solid var(--afianco-color-border, #e5e7eb);
        background: var(--afianco-color-bg, #ffffff);
        position: sticky;
        bottom: 0;
      }
      .cta {
        width: 100%;
        background: var(--afianco-color-primary, #4b72ce);
        color: var(--afianco-color-primary-text, #ffffff);
        border: none;
        border-radius: 8px;
        padding: 14px 20px;
        font-family: inherit;
        font-size: 15px;
        font-weight: 600;
        cursor: pointer;
        transition: opacity 0.15s ease;
      }
      .cta:hover:not(:disabled) {
        opacity: 0.9;
      }
      .cta:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }

      /* ── Loading + Error states ───────────────────────────────────── */
      .state-msg {
        padding: 60px 24px;
        text-align: center;
        color: var(--afianco-color-text-secondary, #6b7280);
      }
      .state-msg.error {
        color: var(--afianco-color-danger, #ef4444);
      }

      /* ── Type-specific picker section spacer ───────────────────────── */
      .type-section {
        margin-bottom: 20px;
      }
      .type-section:last-of-type {
        margin-bottom: 0;
      }

      /* ── Type-specific notice / hint ───────────────────────────────── */
      .v2-hint {
        background: #eff6ff;
        border-left: 3px solid #3b82f6;
        padding: 12px 16px;
        border-radius: 6px;
        font-size: 13px;
        color: #1e3a8a;
        margin-bottom: 16px;
        line-height: 1.5;
      }
    `,
  ];

  // ── Render ───────────────────────────────────────────────────────────

  render() {
    // Singleton passivo (un altro product-detail e' gia' attivo) → non rende.
    if (!this._singleton.active) return nothing;
    return html`
      <div
        class="scrim"
        @click=${() => this.setOpen(false)}
        aria-hidden="true"></div>

      <aside
        class="drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="product-detail-title"
        aria-hidden=${!this.open}>
        <header class="drawer-header">
          <h2 class="drawer-title" id="product-detail-title">
            ${this.product?.name ?? t('product.detail_header_fallback')}
          </h2>
          <button
            class="close-btn"
            type="button"
            aria-label=${t('product.close_label')}
            @click=${() => this.setOpen(false)}>
            ×
          </button>
        </header>

        <div class="drawer-body">
          ${this.loading
            ? html`<div class="state-msg">${t('product.loading')}</div>`
            : this.error
              ? html`<div class="state-msg error" role="alert">${this.error}</div>`
              : this.product
                ? this.renderDetail(this.product)
                : html`<div class="state-msg">${t('product.not_found')}</div>`}
        </div>

        ${this.product && !this.loading && !this.error
          ? html`
              <footer class="drawer-footer">
                <button
                  class="cta"
                  type="button"
                  ?disabled=${this.isDisabled}
                  @click=${() => this.handleAddToCart()}
                  aria-label=${this.ctaLabel(this.product)}>
                  ${this.ctaLabel(this.product)}
                  ${this.quantity > 1 ? html` &times; ${this.quantity}` : ''}
                </button>
              </footer>
            `
          : ''}
      </aside>
    `;
  }

  private renderDetail(p: EmbedProductDetail) {
    const currency = p.currency || this.ctx.init?.currency || 'EUR';
    const stockHint = p.stock_quantity != null
      ? p.stock_quantity === 0
        ? t('product.out_of_stock')
        : p.stock_quantity <= 3
          ? t('product.limited_stock', { count: p.stock_quantity })
          : null
      : null;
    // Track E Step 2.4.7 — qty stepper visibile solo per type "semplici"
    // (physical/digital/course). Per event_ticket lo qty e' nel tier-picker.
    // Per service/rental lo qty e' tipicamente 1 (1 slot, 1 reservation).
    const showQtyStepper = this.shouldShowQtyStepper(p);
    const stockMax = p.stock_quantity ?? 99;

    // Hero image: prefer cover_image_url > image_url > placeholder
    const heroUrl = p.cover_image_url || p.image_url;

    return html`
      <div class="hero-image-wrap">
        ${heroUrl
          ? html`<img src=${heroUrl} alt=${p.name} loading="eager">`
          : html`<div class="hero-placeholder">${t('product.no_image')}</div>`}
      </div>

      <div class="content">
        <div class="badge-row">
          ${this.typeBadgeLabel
            ? html`<span class="type-badge">${this.typeBadgeLabel}</span>`
            : nothing}
          ${p.category
            ? html`<span class="category-badge">${p.category}</span>`
            : nothing}
        </div>

        <h1 class="product-name">${p.name}</h1>

        <div class="price-row">
          ${p.price_mode === 'inquiry'
            ? html`<span class="price-inquiry">${t('product.price_inquiry')}</span>`
            : html`
                <span class="price">
                  ${this.formatPrice(this.computeDisplayPrice(p), currency)}
                </span>
                ${p.unit_label
                  ? html`<span class="price-unit">/ ${p.unit_label}</span>`
                  : nothing}
              `}
        </div>

        ${stockHint
          ? html`<div class="stock-warning ${p.stock_quantity === 0 ? 'stock-out' : ''}">${stockHint}</div>`
          : nothing}

        ${this.renderDescription(p)}

        <!-- Track E Step 2.4.7 — Type-specific picker dispatch -->
        ${this.renderTypeSpecificSection(p, currency)}

        <!-- Track E Step 2.4.9 — Extras picker (mandatory/optional/radio).
             Renderizzato per qualsiasi type che ha extras configurati. -->
        ${this.renderExtrasSection(p, currency)}

        <!-- Track E Step 2.4.10 — Live price preview (debounced server fetch).
             Renderizzato solo per direct + non-inquiry. Mostra subtotal,
             extras breakdown, discount, tax, total con aggiornamento al
             cambio di qty/slot/date/extras. -->
        ${this.renderPricePreviewSection(p, currency)}

        ${showQtyStepper
          ? html`
              <div class="qty-section">
                <label class="qty-label">${t('product.quantity_label')}</label>
                <div class="qty-controls">
                  <button
                    class="qty-btn"
                    type="button"
                    aria-label=${t('product.decrease_qty')}
                    ?disabled=${this.quantity <= 1}
                    @click=${() => this.updateQuantity(-1)}>
                    −
                  </button>
                  <span class="qty-value" aria-live="polite">${this.quantity}</span>
                  <button
                    class="qty-btn"
                    type="button"
                    aria-label=${t('product.increase_qty')}
                    ?disabled=${this.quantity >= stockMax}
                    @click=${() => this.updateQuantity(1)}>
                    +
                  </button>
                </div>
              </div>
            `
          : nothing}
      </div>
    `;
  }

  /**
   * Description: prefer long_description (markdown-like) > description.
   */
  private renderDescription(p: EmbedProductDetail) {
    const text = p.long_description ?? p.description;
    if (!text) return nothing;
    return html`<p class="description">${text}</p>`;
  }

  /**
   * Track E Step 2.4.7 — Dispatch type-aware picker. Renderizza il
   * sub-component appropriato in base a item_type del prodotto + lo
   * stato dei suoi field (es. has_availability_slots, occurrences,
   * reservation_flavor).
   *
   * Pattern: ogni branch e' isolato. Nuovi type futuri = aggiungere un
   * case senza toccare gli altri (open/closed principle).
   */
  private renderTypeSpecificSection(p: EmbedProductDetail, currency: string) {
    switch (p.item_type) {
      case 'service':
        return this.renderServiceSection(p, currency);
      case 'event_ticket':
        return this.renderEventSection(p, currency);
      case 'rental':
        return this.renderRentalSection(p);
      case 'course':
        return this.renderCourseSection(p);
      case 'digital':
      case 'physical':
      default:
        return nothing; // qty stepper sotto basta
    }
  }

  private renderServiceSection(p: EmbedProductDetail, currency: string) {
    const hasOptions = (p.service_options?.length ?? 0) > 0;
    const hasSlots = p.has_availability_slots === true;
    // Determina la duration effettiva per la calendar query
    const effectiveDuration =
      this.selectedServiceOption?.duration_minutes_override ??
      p.service_duration_minutes ??
      undefined;

    return html`
      ${hasOptions
        ? html`
            <div class="type-section">
              <afianco-service-options-picker
                .options=${p.service_options ?? []}
                .currency=${currency}
                .selected=${this.selectedServiceOption?.id ?? null}
                group-label=${t('product.service_options_label')}
                @afianco:service-option-selected=${this.handleServiceOptionSelected}>
              </afianco-service-options-picker>
            </div>
          `
        : nothing}

      ${hasSlots
        ? html`
            <div class="type-section">
              <afianco-availability-picker
                product-id=${p.id}
                .days=${14}
                .duration=${effectiveDuration ?? null}
                @afianco:slot-selected=${this.handleSlotSelected}
                @afianco:slot-cleared=${this.handleSlotCleared}>
              </afianco-availability-picker>
            </div>
          `
        : p.service_allow_custom_request
          ? html`
              <div class="type-section">
                <afianco-custom-request
                  group-label=${t('custom_request.group_label')}
                  @afianco:custom-request-changed=${this.handleCustomRequestChanged}>
                </afianco-custom-request>
              </div>
            `
          : nothing}
    `;
  }

  private renderEventSection(p: EmbedProductDetail, currency: string) {
    const occurrences = p.occurrences ?? [];
    if (occurrences.length === 0) {
      return html`
        <div class="v2-hint">${t('event.empty_occurrence_hint')}</div>
      `;
    }

    const occTiers = this.selectedOccurrence?.tiers ?? [];
    return html`
      <div class="type-section">
        <afianco-occurrence-picker
          .occurrences=${occurrences}
          .currency=${currency}
          .selected=${this.selectedOccurrence?.id ?? null}
          group-label=${t('occurrence.group_label')}
          @afianco:occurrence-selected=${this.handleOccurrenceSelected}>
        </afianco-occurrence-picker>
      </div>

      ${this.selectedOccurrence && occTiers.length > 0
        ? html`
            <div class="type-section">
              <afianco-tier-picker
                .tiers=${occTiers}
                .currency=${currency}
                .selectedTier=${this.selectedTier?.id ?? null}
                .quantity=${this.quantity}
                group-label=${t('tier.title')}
                @afianco:tier-changed=${this.handleTierChanged}>
              </afianco-tier-picker>
            </div>
          `
        : nothing}
    `;
  }

  private renderRentalSection(p: EmbedProductDetail) {
    const flavor = p.reservation_flavor;
    if (flavor === 'range' || flavor == null) {
      // Default flavor = range (date from/to)
      return html`
        <div class="type-section">
          <afianco-date-range-picker
            rental-unit=${p.rental_unit || 'giorno'}
            group-label=${t('rental.group_label')}
            .blockedDates=${this.rentalBlockedDates}
            @afianco:date-range-selected=${this.handleDateRangeSelected}
            @afianco:date-range-cleared=${this.handleDateRangeCleared}>
          </afianco-date-range-picker>
        </div>
      `;
    }
    // V2: flavor=slot (rental con slot picker) — fallback hint per ora
    return html`
      <div class="v2-hint">${t('rental.custom_request_hint')}</div>
    `;
  }

  private renderCourseSection(p: EmbedProductDetail) {
    return html`
      <div class="type-section">
        <afianco-course-preview
          .lessonsCount=${p.course_lessons_count ?? null}
          .durationSeconds=${p.course_duration_seconds ?? null}
          access-policy=${p.course_access_policy ?? ''}
          .accessExpiryDays=${p.course_access_expiry_days ?? null}>
        </afianco-course-preview>
      </div>
    `;
  }

  /**
   * Track E Step 2.4.9 — Extras picker visibility.
   *
   * Renderizza il picker se il prodotto ha extras configurati. Cross-type:
   * physical/digital/service/rental hanno extras potenzialmente; per
   * event_ticket/course tipicamente no (gestione via tier picker / direct).
   */
  private renderExtrasSection(p: EmbedProductDetail, currency: string) {
    const extras = p.extras ?? [];
    if (extras.length === 0) return nothing;
    // Day count per rental flavor=range (moltiplicatore per_day extras)
    const dayCount = this.selectedDateRange?.days ?? null;
    return html`
      <div class="type-section">
        <afianco-extras-picker
          .extras=${extras}
          .currency=${currency}
          .dayCount=${dayCount}
          .quantity=${this.quantity}
          group-label=${t('extras.title')}
          @afianco:extras-changed=${this.handleExtrasChanged}>
        </afianco-extras-picker>
      </div>
    `;
  }

  /**
   * Track E Step 2.4.10 — Live price preview.
   *
   * Mostrato solo per:
   *   - transaction_mode === 'direct' (no "richiedi preventivo")
   *   - price_mode !== 'inquiry' (prezzi su richiesta non hanno totale)
   *
   * Per type=course: skip (sempre prezzo fisso, no qty multiplier).
   * Per altri type: il preview chiama il backend ogni 300ms (debounced)
   * con le selezioni correnti (qty + slot + date + extras).
   */
  private renderPricePreviewSection(p: EmbedProductDetail, currency: string) {
    if (p.transaction_mode !== 'direct') return nothing;
    if (p.price_mode === 'inquiry') return nothing;
    // Course: no live preview (qty=1, no extras tipicamente)
    if (p.item_type === 'course') return nothing;

    // Build extras selections shape for backend (Onda 16):
    //   { mandatory_confirmed, optional_ids: [...], radio_picks: {group_key: extra_id} }
    const optionalIds = this.selectedExtras
      .filter((s) => s.kind === 'optional')
      .map((s) => s.extra_id);
    const radioPicks: Record<string, string> = {};
    for (const sel of this.selectedExtras) {
      if (sel.kind === 'radio_variant' && sel.group_key) {
        radioPicks[sel.group_key] = sel.extra_id;
      }
    }
    const extraSelections =
      optionalIds.length > 0 || Object.keys(radioPicks).length > 0
        ? {
            mandatory_confirmed: true,
            optional_ids: optionalIds,
            radio_picks: radioPicks,
          }
        : null;

    return html`
      <div class="type-section">
        <afianco-price-preview
          product-id=${p.id}
          .quantity=${this.quantity}
          .currency=${currency}
          .dateFrom=${this.selectedDateRange?.from ?? null}
          .dateTo=${this.selectedDateRange?.to ?? null}
          .slotDate=${this.selectedSlot?.date ?? null}
          .slotStart=${this.selectedSlot?.start ?? null}
          .slotEnd=${this.selectedSlot?.end ?? null}
          .extraSelections=${extraSelections}>
        </afianco-price-preview>
      </div>
    `;
  }

  /**
   * Qty stepper visibility per type. Logic:
   *   - event_ticket: nascosto, qty viene dal tier-picker interno
   *   - service: nascosto, qty=1 fisso (1 prenotazione)
   *   - rental: nascosto, qty=1 fisso (1 reservation, no multi-unit)
   *   - course: nascosto, qty=1 fisso (1 enrollment per acquisto)
   *   - physical / digital: visibile (multi-unit)
   */
  private shouldShowQtyStepper(p: EmbedProductDetail): boolean {
    if (p.price_mode === 'inquiry') return false;
    if (p.transaction_mode !== 'direct') return false;
    switch (p.item_type) {
      case 'physical':
      case 'digital':
        return true;
      case 'event_ticket':
      case 'service':
      case 'rental':
      case 'course':
      default:
        return false;
    }
  }

  /**
   * Display price con override type-specific:
   *   - service: usa price dell'opzione selezionata se scelta
   *   - event_ticket: usa price del tier selezionato * qty se scelti
   *   - default: unit_price
   */
  private computeDisplayPrice(p: EmbedProductDetail): number | null {
    if (p.item_type === 'service' && this.selectedServiceOption) {
      return this.selectedServiceOption.price;
    }
    if (p.item_type === 'event_ticket' && this.selectedTier) {
      return this.selectedTier.price * this.quantity;
    }
    return p.unit_price ?? null;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'afianco-product-detail': AfiancoProductDetail;
  }
  interface HTMLElementEventMap {
    'afianco:product-view-requested': CustomEvent<{ product_id?: string; product?: EmbedProductCard }>;
    'afianco:product-detail-opened': CustomEvent<{ product_id?: string }>;
    'afianco:product-detail-closed': CustomEvent;
  }
}
