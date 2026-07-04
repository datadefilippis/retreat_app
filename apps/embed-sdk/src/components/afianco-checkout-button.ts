/**
 * <afianco-checkout-button> — Phase 1 Step 26 (Track C).
 *
 * Componente orchestratore checkout. Ascolta `afianco:checkout-requested`
 * dispatchato dal cart-drawer, mostra un form modal per raccogliere
 * customer info + GDPR consent (con opzionale signup inline), chiama
 * /api/public/embed/checkout/start, apre il Stripe Checkout popup,
 * e ascolta il postMessage dal bridge afianco:checkout-complete
 * (Step 17) per dispatching dell'evento `afianco:order-completed`.
 *
 * Uso (mounted dentro storefront-init):
 *
 *   <afianco-storefront-init slug="acme">
 *     <afianco-product-grid show-filter-nav></afianco-product-grid>
 *     <afianco-cart-drawer></afianco-cart-drawer>
 *     <afianco-checkout-button></afianco-checkout-button>
 *   </afianco-storefront-init>
 *
 * Custom events:
 *   - `afianco:order-completed` (detail: {order_id, order_status, payment_status})
 *   - `afianco:order-failed` (detail: {message})
 *
 * Attributes:
 *   - return-url (optional): override del default
 *     `${window.location.origin}${window.location.pathname}` per il
 *     postMessage callback target. Il backend valida questo URL contro
 *     store.allowed_origins (Phase 1 Step 16 anti-phishing).
 *   - allow-signup (boolean, default true): mostra checkbox "Crea account"
 *     nel form. Disable per merchant che vogliono guest-only checkout.
 */

import { LitElement, html, css, type PropertyValues } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { consume } from '@lit/context';
import { afiancoBaseStyles } from '@afianco/design-tokens';
// Sprint 4 W4.7 — i18n wiring
import { t } from '../i18n/index.js';
import {
  AfiancoValidationError,
  type CartResponse,
  type EmbedCheckoutStartRequest,
} from '@afianco/api-client';
import {
  storefrontContext,
  STOREFRONT_INITIAL,
  type StorefrontContext,
} from '../context.js';
import { StoreConsumerController } from '../store/store-consumer.js';

// Track E Step 4.2 — sub-components per fulfillment + shipping options.
// Side-effect import per registrare custom elements.
import './afianco-fulfillment-picker.js';
import './afianco-shipping-options-picker.js';

interface OrderCompletedPayload {
  order_id: string;
  order_status: string;
  payment_status: string;
}

@customElement('afianco-checkout-button')
export class AfiancoCheckoutButton extends LitElement {
  @property({ type: String, attribute: 'return-url' })
  returnUrl = '';

  @property({ type: Boolean, attribute: 'allow-signup' })
  allowSignup = true;

  @consume({ context: storefrontContext, subscribe: true })
  @state()
  ctx: StorefrontContext = STOREFRONT_INITIAL;

  /** À-la-carte: aggancio al kernel se fuori da un provider (no-op se dentro). */
  protected _store = new StoreConsumerController(this);

  // ── Form state ───────────────────────────────────────────────────────

  /** Open/close modal */
  @state()
  private open = false;

  /** Cart attivo (passato da afianco:checkout-requested event) */
  @state()
  private activeCart: CartResponse | null = null;

  // ── Track E Step 3.2 — Dynamic order_fields (cart products) ──
  /**
   * Aggregated order_fields[] dei prodotti nel cart. Fetched via
   * client.embed.getProduct(id) per ogni unique product_id quando il
   * modal si apre. Dedup by field id (stessa key) — sort by sort_order.
   */
  @state()
  private aggregatedOrderFields: Array<{
    id: string;
    label: string;
    type?: string;
    required?: boolean;
    placeholder?: string;
    help_text?: string;
    sort_order?: number;
  }> = [];

  /** Valori popolati dall'utente per gli order_fields (id → value). */
  @state()
  private orderFieldsData: Record<string, string> = {};

  /** Loading state durante il fetch dei product details. */
  @state()
  private loadingProductFields = false;

  // ── Track E Step 3.3 — Shipping address (physical products) ──
  /**
   * True se il cart contiene almeno un prodotto physical. Computed
   * durante loadProductFields() — determina se mostrare il shipping
   * address form al checkout.
   */
  @state()
  private cartHasPhysical = false;

  // ── Track E Step 4.2 — Fulfillment mode + shipping options ──
  /**
   * Mode selezionato (shipping vs local_pickup vs pickup_at_store).
   * Default: prima mode in ctx.init.fulfillment_modes (tipicamente 'shipping').
   * Visible solo se store supporta >1 mode (altrimenti auto-set + hide picker).
   */
  @state()
  private fulfillmentMode = 'shipping';

  /** Shipping option scelta (id+label+price snapshot). Required se mode=shipping + cartHasPhysical. */
  @state()
  private selectedShippingOption: {
    id: string;
    label: string;
    base_price: number;
    free_shipping_threshold?: number | null;
  } | null = null;

  // ── Track E Step 5.1 — Order notes (free text per customer requests) ──
  @state()
  private orderNotes = '';

  // ── Track E Step 4.1 — Coupon picker state ──
  /** Codice coupon inserito dal customer (uppercase auto). */
  @state()
  private couponCode = '';

  /** Esito validation (dry-run). null = non ancora applicato. */
  @state()
  private couponApplied: {
    code: string;
    discount: number;
    discount_pct?: number | null;
  } | null = null;

  /** Error message della validation (visibile se != null). */
  @state()
  private couponError: string | null = null;

  /** Loading durante POST /coupons/validate. */
  @state()
  private couponValidating = false;

  // ── Track E Step 3.4 — Attendee fields per event_ticket ──
  /**
   * Map cart_item_signature → { product_meta, attendees[] }.
   * Una entry per ogni cart line di tipo event_ticket. Ogni attendee
   * ha: name, email, phone, custom_fields {field_id: value}.
   *
   * Cart line key = product_id + ':' + occurrence_id + ':' + ticket_tier_id
   * (matchando il dedup signature del cart-drawer).
   */
  @state()
  private ticketLines: Array<{
    productId: string;
    occurrenceId: string | null | undefined;
    ticketTierId: string | null | undefined;
    quantity: number;
    productName: string;
    requireEmail: boolean;
    requirePhone: boolean;
    attendeeFields: Array<{
      id: string;
      label: string;
      type?: string;
      required?: boolean;
      placeholder?: string | null;
      help_text?: string | null;
      sort_order?: number;
    }>;
    attendees: Array<{
      name: string;
      email: string;
      phone: string;
      custom_fields: Record<string, string>;
    }>;
  }> = [];

  /** Shipping address fields (parita con backend ShippingAddressInput). */
  @state()
  private shipRecipient = '';
  @state()
  private shipLine1 = '';
  @state()
  private shipCivic = '';
  @state()
  private shipPostalCode = '';
  @state()
  private shipCity = '';
  @state()
  private shipProvince = '';
  @state()
  private shipCountry = 'IT';

  /** Form values */
  @state()
  private name = '';
  @state()
  private email = '';
  @state()
  private phone = '';
  @state()
  private gdprPrivacy = false;
  @state()
  private gdprTerms = false;
  @state()
  private gdprMarketing = false;
  @state()
  private createAccount = false;
  @state()
  private password = '';

  /** UI state */
  @state()
  private submitting = false;
  @state()
  private errorMsg: string | null = null;
  @state()
  private status: 'idle' | 'submitting' | 'awaiting_payment' | 'completed' = 'idle';

  // ── Internal references ──────────────────────────────────────────────

  /** Stripe popup window handle (null when not open) */
  private popupRef: Window | null = null;

  /** postMessage listener attached flag */
  private _messageListenerAttached = false;
  private _checkoutListenerAttached = false;

  static styles = [
    afiancoBaseStyles,
    css`
      :host {
        display: contents;
      }
      .scrim {
        position: fixed;
        inset: 0;
        background: rgba(15, 23, 42, 0.5);
        /* Track E Step 3.1 — z-index defense-in-depth: il checkout modal
           deve apparire SOPRA il cart-drawer (anche se quello dovrebbe
           chiudersi al click di checkout — questo e' belt + suspenders).
           Cart-drawer panel = z-modal+1 = 2001 → checkout scrim a +10
           garantisce sovrapposizione anche con CSS override merchant. */
        z-index: calc(var(--afianco-z-modal) + 10);
        display: flex;
        align-items: center;
        justify-content: center;
        padding: var(--afianco-spacing-lg);
      }
      .modal {
        background: var(--afianco-color-bg);
        border-radius: var(--afianco-radius-lg);
        box-shadow: var(--afianco-shadow-lg);
        max-width: 480px;
        width: 100%;
        max-height: 90vh;
        overflow-y: auto;
        /* z-index modal: scrim+1 per sicurezza (Lit shadow root isolation
           dovrebbe gia' garantire, ma esplicito = piu' robusto). */
        z-index: calc(var(--afianco-z-modal) + 11);
        position: relative;
      }
      .modal-header {
        padding: var(--afianco-spacing-lg);
        border-bottom: 1px solid var(--afianco-color-border);
        display: flex;
        align-items: center;
        justify-content: space-between;
      }
      .modal-title {
        margin: 0;
        font-size: var(--afianco-font-size-lg);
        font-weight: var(--afianco-font-weight-bold);
      }
      .close-btn {
        background: transparent;
        border: none;
        color: var(--afianco-color-text-secondary);
        cursor: pointer;
        font-size: 24px;
        line-height: 1;
      }
      .modal-body {
        padding: var(--afianco-spacing-lg);
      }
      .form-group {
        margin-bottom: var(--afianco-spacing-md);
      }
      label {
        display: block;
        font-size: var(--afianco-font-size-sm);
        font-weight: var(--afianco-font-weight-medium);
        color: var(--afianco-color-text-primary);
        margin-bottom: var(--afianco-spacing-xs);
      }
      input[type='text'],
      input[type='email'],
      input[type='tel'],
      input[type='password'],
      input[type='number'],
      textarea,
      select {
        width: 100%;
        padding: var(--afianco-spacing-sm) var(--afianco-spacing-md);
        border: 1px solid var(--afianco-color-border);
        border-radius: var(--afianco-radius-md);
        font-family: var(--afianco-font-family);
        font-size: var(--afianco-font-size-md);
        background: var(--afianco-color-bg);
        color: var(--afianco-color-text-primary);
        box-sizing: border-box;
      }
      textarea {
        resize: vertical;
        min-height: 60px;
      }
      input:focus, textarea:focus, select:focus {
        outline: 2px solid var(--afianco-color-primary);
        outline-offset: 0;
      }
      .checkbox-row {
        display: flex;
        align-items: flex-start;
        gap: var(--afianco-spacing-sm);
        font-size: var(--afianco-font-size-sm);
        color: var(--afianco-color-text-secondary);
        margin-bottom: var(--afianco-spacing-sm);
      }
      .checkbox-row input[type='checkbox'] {
        margin-top: 3px;
      }
      /* Track E Step 7.4 — Linked GDPR labels (privacy + terms) */
      .checkbox-row label a.gdpr-link {
        color: var(--afianco-color-primary);
        text-decoration: underline;
        cursor: pointer;
      }
      .checkbox-row label a.gdpr-link:hover {
        text-decoration: none;
      }
      .checkbox-row label a.gdpr-link:focus-visible {
        outline: 2px solid var(--afianco-color-primary);
        outline-offset: 2px;
        border-radius: 2px;
      }
      .submit-btn {
        background: var(--afianco-color-primary);
        color: var(--afianco-color-primary-text);
        border: none;
        border-radius: var(--afianco-radius-md);
        padding: var(--afianco-spacing-md);
        font-family: var(--afianco-font-family);
        font-size: var(--afianco-font-size-md);
        font-weight: var(--afianco-font-weight-medium);
        cursor: pointer;
        width: 100%;
        margin-top: var(--afianco-spacing-md);
      }
      .submit-btn:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }
      .error-banner {
        background: #fff5f5;
        border: 1px solid #fed7d7;
        color: var(--afianco-color-danger);
        padding: var(--afianco-spacing-sm) var(--afianco-spacing-md);
        border-radius: var(--afianco-radius-sm);
        font-size: var(--afianco-font-size-sm);
        margin-bottom: var(--afianco-spacing-md);
      }
      .status-banner {
        background: var(--afianco-color-surface);
        padding: var(--afianco-spacing-md);
        border-radius: var(--afianco-radius-md);
        text-align: center;
        font-size: var(--afianco-font-size-sm);
        color: var(--afianco-color-text-secondary);
      }
    `,
  ];

  // ── Lifecycle ─────────────────────────────────────────────────────────

  connectedCallback(): void {
    super.connectedCallback();
    if (!this._checkoutListenerAttached) {
      document.addEventListener(
        'afianco:checkout-requested',
        this._handleCheckoutRequested as EventListener,
      );
      this._checkoutListenerAttached = true;
    }
    if (!this._messageListenerAttached) {
      window.addEventListener('message', this._handlePostMessage);
      this._messageListenerAttached = true;
    }
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    if (this._checkoutListenerAttached) {
      document.removeEventListener(
        'afianco:checkout-requested',
        this._handleCheckoutRequested as EventListener,
      );
      this._checkoutListenerAttached = false;
    }
    if (this._messageListenerAttached) {
      window.removeEventListener('message', this._handlePostMessage);
      this._messageListenerAttached = false;
    }
  }

  protected updated(_changed: PropertyValues): void {
    // No-op — niente lifecycle reactive da gestire qui
  }

  // ── Public API ────────────────────────────────────────────────────────

  /** Opens the modal with the given cart. */
  openWithCart(cart: CartResponse): void {
    this.activeCart = cart;
    this.errorMsg = null;
    this.status = 'idle';
    this.open = true;
    // Track E Step 3.2 — fetch product details per aggregating
    // order_fields dei prodotti nel cart (visible al checkout form).
    void this.loadProductFields(cart);
  }

  /**
   * Track E Step 3.2 — Aggregate order_fields[] from cart products.
   *
   * Strategy: Promise.all su getProduct(id) per ogni product_id unique.
   * O(n) network calls but parallelized. Dedup by field.id (stesso id
   * = stesso field merchant intende cross-product). Sort by sort_order.
   *
   * Mirror del React storefront (StorefrontPage.js lines 2434-2459)
   * dove `orderFieldsConfig` viene aggregato dai products event_ticket
   * in cart. Qui generalizzato a TUTTI i product types (un physical
   * product puo' avere order_fields custom esattamente come event_ticket).
   */
  private async loadProductFields(cart: CartResponse): Promise<void> {
    if (!this.ctx?.client) return;
    const productIds = Array.from(
      new Set((cart.items ?? []).map((it) => it.product_id).filter(Boolean)),
    );
    if (productIds.length === 0) {
      this.aggregatedOrderFields = [];
      this.orderFieldsData = {};
      return;
    }
    this.loadingProductFields = true;
    try {
      const details = await Promise.all(
        productIds.map((pid) =>
          this.ctx.client!.embed.getProduct(pid).catch(() => null),
        ),
      );
      // Track E Step 3.3 — detect physical products per mostrare shipping form
      this.cartHasPhysical = details.some(
        (d) => d?.item_type === 'physical',
      );
      // Track E Step 4.2 — auto-init fulfillmentMode dal primo supportato dal store
      const modes = this.ctx?.init?.fulfillment_modes ?? ['shipping'];
      if (modes.length > 0 && !modes.includes(this.fulfillmentMode)) {
        this.fulfillmentMode = modes[0]!;
      }
      // Aggregate order_fields cross-product (dedup by id)
      const byId = new Map<string, typeof this.aggregatedOrderFields[number]>();
      for (const d of details) {
        if (!d?.order_fields) continue;
        for (const f of d.order_fields) {
          if (!f?.id || byId.has(f.id)) continue;
          byId.set(f.id, {
            id: f.id,
            label: f.label,
            type: (f as { type?: string }).type ?? 'text',
            required: f.required,
            placeholder: f.placeholder ?? undefined,
            help_text: f.help_text ?? undefined,
            sort_order: f.sort_order,
          });
        }
      }

      // Track E Step 3.4 — Build ticket lines per event_ticket items.
      // Per ogni cart item event_ticket, creo una entry con attendees=[]
      // sized by quantity. requires_attendee_details=true (default per
      // event_ticket Onda 8) → renderizziamo il form.
      const productMetaById = new Map(details.filter(Boolean).map((d) => [d!.id, d!]));
      const newTicketLines: typeof this.ticketLines = [];
      for (const item of cart.items ?? []) {
        const meta = productMetaById.get(item.product_id);
        if (!meta || meta.item_type !== 'event_ticket') continue;
        // Skip se merchant non richiede attendee details (config opt-out)
        if (!meta.requires_attendee_details) continue;
        const qty = Math.max(1, Math.floor(item.quantity ?? 1));
        const attendeeFields = Array.isArray(meta.attendee_fields)
          ? meta.attendee_fields.map((f) => ({
              id: f.id,
              label: f.label,
              type: (f as { type?: string }).type ?? 'text',
              required: f.required,
              placeholder: f.placeholder ?? undefined,
              help_text: f.help_text ?? undefined,
              sort_order: f.sort_order,
            }))
          : [];
        // Initialize empty attendees array sized by quantity
        const attendees = Array.from({ length: qty }, () => ({
          name: '',
          email: '',
          phone: '',
          custom_fields: Object.fromEntries(
            attendeeFields.map((f) => [f.id, '']),
          ) as Record<string, string>,
        }));
        newTicketLines.push({
          productId: item.product_id,
          occurrenceId: item.occurrence_id,
          ticketTierId: item.ticket_tier_id,
          quantity: qty,
          productName: meta.name,
          requireEmail: meta.require_attendee_email !== false,
          requirePhone: meta.require_attendee_phone === true,
          attendeeFields,
          attendees,
        });
      }
      this.ticketLines = newTicketLines;
      // Sort by sort_order then by label
      const aggregated = Array.from(byId.values()).sort(
        (a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0)
          || a.label.localeCompare(b.label),
      );
      this.aggregatedOrderFields = aggregated;
      // Initialize empty values for each field
      const initData: Record<string, string> = {};
      for (const f of aggregated) initData[f.id] = '';
      this.orderFieldsData = initData;
    } catch (e) {
      // Soft fail — il checkout continua senza order_fields. Backend
      // validera' i required field e tornera' 400 con detail leggibile.
      // eslint-disable-next-line no-console
      console.warn('[afianco-checkout-button] order_fields fetch failed:', e);
    } finally {
      this.loadingProductFields = false;
    }
  }

  /** Closes the modal (resetting form state). */
  closeModal(): void {
    this.open = false;
    if (this.status !== 'awaiting_payment') {
      this.resetForm();
    }
  }

  /** Programmatically submit (used in tests). */
  async submit(): Promise<void> {
    if (!this.ctx.client || !this.activeCart) {
      this.errorMsg = t('checkout.error_storefront_not_ready');
      return;
    }
    // Validation
    if (!this.name.trim()) {
      this.errorMsg = t('checkout.error_name_empty');
      return;
    }
    if (!this.email.trim() || !this.email.includes('@')) {
      this.errorMsg = t('checkout.error_email_invalid');
      return;
    }
    if (!this.gdprPrivacy || !this.gdprTerms) {
      this.errorMsg = t('checkout.error_gdpr_missing');
      return;
    }
    if (this.createAccount && (!this.password || this.password.length < 8)) {
      this.errorMsg = t('checkout.error_password_short');
      return;
    }

    // Track E Step 3.2 — Validate required order_fields client-side.
    for (const f of this.aggregatedOrderFields) {
      if (!f.required) continue;
      const v = (this.orderFieldsData[f.id] ?? '').trim();
      if (!v) {
        this.errorMsg = `Compila il campo "${f.label}" per procedere.`;
        return;
      }
    }

    // Track E Step 3.3/4.2 — Validate shipping address + option quando
    // cart contiene physical + mode='shipping'. Pickup mode skippa validazioni.
    if (this.cartHasPhysical && this.fulfillmentMode === 'shipping') {
      if (!this.shipLine1.trim() || !this.shipPostalCode.trim()
          || !this.shipCity.trim() || !this.shipCountry.trim()) {
        this.errorMsg = t('checkout.error_shipping_address');
        return;
      }
      // CAP IT: 5 digit pattern
      if (this.shipCountry.toUpperCase() === 'IT'
          && !/^\d{5}$/.test(this.shipPostalCode.trim())) {
        this.errorMsg = t('checkout.error_postal_it');
        return;
      }
      // Track E Step 4.2 — shipping_option required se merchant ha
      // configurato opzioni. Se options array vuoto, il widget mostra
      // empty state nel picker — il customer non puo' procedere.
      if (!this.selectedShippingOption) {
        this.errorMsg = 'Seleziona un\'opzione di spedizione.';
        return;
      }
    }

    // Track E Step 3.4 — Validate attendee fields per ogni biglietto.
    // Pattern parita' con storefront (StorefrontPage attendee_fields).
    for (const line of this.ticketLines) {
      for (let i = 0; i < line.attendees.length; i++) {
        const a = line.attendees[i]!;
        const personLabel = line.quantity > 1
          ? `partecipante ${i + 1} (${line.productName})`
          : line.productName;
        if (!a.name.trim()) {
          this.errorMsg = `Inserisci il nome del ${personLabel}.`;
          return;
        }
        if (line.requireEmail && (!a.email.trim() || !a.email.includes('@'))) {
          this.errorMsg = `Inserisci l'email del ${personLabel}.`;
          return;
        }
        if (line.requirePhone && !a.phone.trim()) {
          this.errorMsg = `Inserisci il telefono del ${personLabel}.`;
          return;
        }
        // Custom attendee fields required check
        for (const f of line.attendeeFields) {
          if (!f.required) continue;
          const v = (a.custom_fields[f.id] ?? '').trim();
          if (!v) {
            this.errorMsg = `Compila "${f.label}" per ${personLabel}.`;
            return;
          }
        }
      }
    }

    this.submitting = true;
    this.status = 'submitting';
    this.errorMsg = null;

    const body: EmbedCheckoutStartRequest = {
      slug: this.ctx.init?.slug ?? this.ctx.client.slug,
      cart_id: this.activeCart.id,
      customer_name: this.name.trim(),
      customer_email: this.email.trim(),
      customer_phone: this.phone.trim() || null,
      embed_return_url: this.resolvedReturnUrl,
      gdpr_terms_accepted: this.gdprTerms,
      gdpr_privacy_accepted: this.gdprPrivacy,
      gdpr_marketing_accepted: this.gdprMarketing,
      terms_accepted: this.gdprTerms,
    };

    // Track E Step 3.2 — include order_fields (solo se almeno 1 valore non-empty
    // per evitare di sprecare bandwidth con dict vuoto)
    const nonEmpty: Record<string, string> = {};
    for (const [id, v] of Object.entries(this.orderFieldsData)) {
      const trimmed = (v ?? '').trim();
      if (trimmed) nonEmpty[id] = trimmed;
    }
    if (Object.keys(nonEmpty).length > 0) {
      body.order_fields = nonEmpty;
    }

    // Track E Step 3.3/4.2 — Fulfillment payload type-aware:
    // - mode='shipping' + cartHasPhysical: include shipping_address +
    //   shipping_option (id+label) + fulfillment_mode='shipping'
    // - mode='local_pickup' o 'pickup_at_store': include solo
    //   fulfillment_mode (no address, no shipping option)
    // - cart senza physical: skip tutto fulfillment block
    if (this.cartHasPhysical) {
      body.fulfillment_mode = this.fulfillmentMode as 'shipping' | 'local_pickup';
      if (this.fulfillmentMode === 'shipping') {
        body.shipping_address_details = {
          recipient_name: this.shipRecipient.trim() || this.name.trim(),
          line1: this.shipLine1.trim(),
          civic: this.shipCivic.trim() || null,
          postal_code: this.shipPostalCode.trim(),
          city: this.shipCity.trim(),
          province: this.shipProvince.trim().toUpperCase() || null,
          country: this.shipCountry.trim().toUpperCase() || 'IT',
        };
        if (this.selectedShippingOption) {
          body.shipping_option_id = this.selectedShippingOption.id;
          body.shipping_option_label = this.selectedShippingOption.label;
        }
      }
    }

    // Track E Step 4.1 — include coupon code se applicato (backend
    // rivalidera atomicamente con increment).
    if (this.couponApplied?.code) {
      body.coupon_code = this.couponApplied.code;
    }

    // Track E Step 5.1 — order notes (trim + max 2000 char)
    const notes = this.orderNotes.trim().slice(0, 2000);
    if (notes) {
      body.notes = notes;
    }

    if (this.createAccount) {
      body.create_account = true;
      body.account_password = this.password;
      body.account_locale = 'it';
    }

    try {
      // Track E Step 3.4 — Pre-checkout: persist attendees nel cart
      // (PATCH /cart/{id}) PRIMA del checkout.start. Backend cart
      // gia' supporta CartItemInput.attendees come List[Dict]. Il
      // checkout poi propaga al OrderRequestItem.attendees.
      if (this.ticketLines.length > 0) {
        await this.persistAttendeesInCart();
      }

      const resp = await this.ctx.client.embed.checkout.start(body);

      // direct mode: open Stripe popup
      if (resp.payment_checkout_url) {
        this.status = 'awaiting_payment';
        this.openStripePopup(resp.payment_checkout_url);
      } else {
        // request mode: ordine creato senza Stripe → completed
        this.status = 'completed';
        this.dispatchOrderCompleted({
          order_id: resp.order_id,
          order_status: resp.order_status,
          payment_status: 'not_required',
        });
        // Auto-close after small delay — gate on isConnected to evitare
        // updates su element rimossi (test env happy-dom DOMException).
        setTimeout(() => {
          if (this.isConnected) this.closeModal();
        }, 1500);
      }
    } catch (e) {
      if (e instanceof AfiancoValidationError) {
        const msg =
          typeof e.detail === 'object' && e.detail !== null && 'detail' in e.detail
            ? String((e.detail as Record<string, unknown>).detail)
            : e.message;
        this.errorMsg = msg;
      } else {
        this.errorMsg = (e as Error)?.message ?? t('checkout.error_generic');
      }
      this.status = 'idle';
    } finally {
      this.submitting = false;
    }
  }

  // ── Internal handlers ─────────────────────────────────────────────────

  private _handleCheckoutRequested = (e: Event): void => {
    const detail = (e as CustomEvent<{ cart: CartResponse }>).detail;
    if (!detail?.cart) return;
    this.openWithCart(detail.cart);
  };

  private _handlePostMessage = (e: MessageEvent): void => {
    // Validate origin matches our return URL origin (anti-spoof)
    const expectedOrigin = this.originOfReturnUrl;
    if (expectedOrigin && e.origin !== expectedOrigin) {
      // Allow message from afianco backend domain too (where bridge HTML
      // is served). The bridge runs the postMessage from the popup window
      // which has origin == backend URL.
      const backendOrigin = this.originOfBackendUrl;
      if (backendOrigin && e.origin !== backendOrigin) {
        return; // ignore — not from a trusted origin
      }
    }
    const data = e.data as Record<string, unknown> | null;
    if (!data || data.source !== 'afianco-embed') return;
    if (data.type !== 'checkout_complete') return;

    const payload: OrderCompletedPayload = {
      order_id: String(data.order_id ?? ''),
      order_status: String(data.order_status ?? 'unknown'),
      payment_status: String(data.payment_status ?? 'unknown'),
    };

    this.status = 'completed';
    this.dispatchOrderCompleted(payload);

    // Cleanup cart_id from localStorage (order completed)
    this.clearCartIdLocalStorage();

    // Close popup if still open
    try {
      this.popupRef?.close();
    } catch {
      // ignore
    }
    this.popupRef = null;

    // Close modal — gate on isConnected (cosi' test env evita
    // DOMException su elementi detached).
    setTimeout(() => {
      if (this.isConnected) this.closeModal();
    }, 1200);
  };

  private dispatchOrderCompleted(payload: OrderCompletedPayload): void {
    this.dispatchEvent(
      new CustomEvent<OrderCompletedPayload>('afianco:order-completed', {
        detail: payload,
        bubbles: true,
        composed: true,
      }),
    );
  }

  private clearCartIdLocalStorage(): void {
    try {
      const slug = this.ctx.init?.slug ?? this.ctx.client?.slug;
      if (!slug || typeof localStorage === 'undefined') return;
      localStorage.removeItem(`afianco_cart_id_${slug}`);
    } catch {
      // ignore
    }
  }

  private resetForm(): void {
    this.name = '';
    this.email = '';
    this.phone = '';
    this.gdprPrivacy = false;
    this.gdprTerms = false;
    this.gdprMarketing = false;
    this.createAccount = false;
    this.password = '';
    this.errorMsg = null;
    this.status = 'idle';
    // Track E Step 3.2 — reset dynamic fields
    this.aggregatedOrderFields = [];
    this.orderFieldsData = {};
    // Track E Step 3.3 — reset shipping form
    this.cartHasPhysical = false;
    this.shipRecipient = '';
    this.shipLine1 = '';
    this.shipCivic = '';
    this.shipPostalCode = '';
    this.shipCity = '';
    this.shipProvince = '';
    this.shipCountry = 'IT';
    // Track E Step 3.4 — reset attendees
    this.ticketLines = [];
    // Track E Step 4.1 — reset coupon
    this.couponCode = '';
    this.couponApplied = null;
    this.couponError = null;
    this.couponValidating = false;
    // Track E Step 4.2 — reset shipping
    this.fulfillmentMode = 'shipping';
    this.selectedShippingOption = null;
    // Track E Step 5.1 — reset order notes
    this.orderNotes = '';
  }

  /**
   * Track E Step 4.1 — Validate coupon code (dry-run).
   *
   * Chiamato al click "Applica" o all'Enter sull'input. POST a
   * /api/public/embed/coupons/validate/{slug} con {code, subtotal}.
   * Subtotal e' la somma del cart attuale (per applicare min_order_amount).
   *
   * On success: aggiorna couponApplied state + dispatcha event per il
   * price-preview che ricalcola il totale.
   * On error: mostra error message inline.
   */
  private async applyCoupon(): Promise<void> {
    if (!this.ctx?.client || !this.activeCart) return;
    const code = this.couponCode.trim().toUpperCase();
    if (!code) {
      this.couponError = t('coupon.empty_input');
      return;
    }
    this.couponValidating = true;
    this.couponError = null;
    try {
      const subtotal = this.activeCart.subtotal_snapshot ?? 0;
      const res = await this.ctx.client.embed.validateCoupon({
        code,
        subtotal,
      });
      this.couponApplied = {
        code: res.code,
        discount: res.discount,
        discount_pct: res.discount_pct ?? null,
      };
    } catch (e) {
      // Backend ritorna 400 con detail leggibile (es. "Codice promo esaurito")
      const errMsg = (e as { detail?: string; message?: string }).detail
        ?? (e as Error)?.message
        ?? t('coupon.invalid');
      this.couponError = errMsg;
      this.couponApplied = null;
    } finally {
      this.couponValidating = false;
    }
  }

  /** Rimuovi coupon applicato (toggle al click "Rimuovi"). */
  private removeCoupon(): void {
    this.couponApplied = null;
    this.couponCode = '';
    this.couponError = null;
  }

  /** Track E Step 4.2 — fulfillment mode change handler */
  private handleFulfillmentModeChanged = (e: CustomEvent): void => {
    this.fulfillmentMode = e.detail?.mode ?? 'shipping';
    // Reset shipping option se cambio mode (non rilevante per pickup)
    if (this.fulfillmentMode !== 'shipping') {
      this.selectedShippingOption = null;
    }
  };

  /** Track E Step 4.2 — shipping option selection handler */
  private handleShippingOptionSelected = (e: CustomEvent): void => {
    const opt = e.detail?.option;
    if (!opt) return;
    this.selectedShippingOption = {
      id: opt.id,
      label: opt.label,
      base_price: opt.base_price,
      free_shipping_threshold: opt.free_shipping_threshold,
    };
  };

  /**
   * Track E Step 3.4 — Persist attendees nel cart pre-checkout.
   *
   * Backend CartItemInput accetta gia' `attendees: Optional[List[Dict]]`.
   * Quando il checkout-start viene chiamato, il handler propaga
   * `attendees=item.get("attendees")` al OrderRequestItem.
   *
   * Quindi basta fare PATCH cart con items snapshot + attendees iniettati
   * per la cart line corrispondente (signature match by product_id +
   * occurrence_id + ticket_tier_id — stessa logica dedup del cart-drawer).
   */
  private async persistAttendeesInCart(): Promise<void> {
    if (!this.ctx?.client || !this.activeCart) return;
    const items = (this.activeCart.items ?? []).map((it) => {
      // Find matching ticket line by signature
      const tline = this.ticketLines.find(
        (t) =>
          t.productId === it.product_id
          && (t.occurrenceId ?? null) === (it.occurrence_id ?? null)
          && (t.ticketTierId ?? null) === (it.ticket_tier_id ?? null),
      );
      const baseItem = {
        product_id: it.product_id,
        quantity: it.quantity,
        occurrence_id: it.occurrence_id,
        ticket_tier_id: it.ticket_tier_id,
        rental_date_from: it.rental_date_from,
        rental_date_to: it.rental_date_to,
        rental_notes: it.rental_notes,
        booking_date: it.booking_date,
        booking_start_time: it.booking_start_time,
        booking_end_time: it.booking_end_time,
        booking_end_date: it.booking_end_date,
        service_option_id: it.service_option_id,
        attendees: it.attendees,
      };
      if (!tline) return baseItem;
      // Build attendees array: trim values + dedup custom_fields
      const attendees = tline.attendees.map((a) => {
        const customNonEmpty: Record<string, string> = {};
        for (const [k, v] of Object.entries(a.custom_fields)) {
          const trimmed = (v ?? '').trim();
          if (trimmed) customNonEmpty[k] = trimmed;
        }
        return {
          name: a.name.trim(),
          email: a.email.trim() || null,
          phone: a.phone.trim() || null,
          custom_fields: Object.keys(customNonEmpty).length > 0 ? customNonEmpty : null,
        };
      });
      return { ...baseItem, attendees };
    });
    try {
      const updated = await this.ctx.client.embed.cart.update(
        this.activeCart.id,
        { items },
      );
      this.activeCart = updated;
    } catch (e) {
      // Soft fail: log + continue al checkout.start. Il backend
      // validera' i required attendee_fields e tornera' 400 se serve.
      // eslint-disable-next-line no-console
      console.warn('[afianco-checkout-button] attendees persist failed:', e);
    }
  }

  /**
   * Track E Step 3.4 — Render attendee form per event_ticket cart lines.
   *
   * Per ogni biglietto (tline × quantity), genera un blocco "Partecipante N"
   * con: name (sempre required), email (require_email config), phone
   * (require_phone config), custom attendee_fields.
   *
   * Pattern mirror del React storefront (StorefrontPage.js lines 2185-2209).
   */
  private renderTicketLinesBlock() {
    if (this.ticketLines.length === 0) return '';
    const updateAttendee = (
      lineIdx: number,
      attIdx: number,
      field: 'name' | 'email' | 'phone',
      value: string,
    ): void => {
      const lines = [...this.ticketLines];
      const line = { ...lines[lineIdx]! };
      const attendees = [...line.attendees];
      attendees[attIdx] = { ...attendees[attIdx]!, [field]: value };
      line.attendees = attendees;
      lines[lineIdx] = line;
      this.ticketLines = lines;
    };
    const updateCustomField = (
      lineIdx: number,
      attIdx: number,
      fieldId: string,
      value: string,
    ): void => {
      const lines = [...this.ticketLines];
      const line = { ...lines[lineIdx]! };
      const attendees = [...line.attendees];
      const att = { ...attendees[attIdx]! };
      att.custom_fields = { ...att.custom_fields, [fieldId]: value };
      attendees[attIdx] = att;
      line.attendees = attendees;
      lines[lineIdx] = line;
      this.ticketLines = lines;
    };

    return html`
      <div
        style="margin-top: var(--afianco-spacing-md);
               padding-top: var(--afianco-spacing-md);
               border-top: 1px solid var(--afianco-color-border);">
        <div
          style="font-size: var(--afianco-font-size-sm);
                 font-weight: var(--afianco-font-weight-bold);
                 color: var(--afianco-color-text-secondary);
                 margin-bottom: var(--afianco-spacing-sm);
                 display: flex; align-items: center; gap: 6px;">
          <span aria-hidden="true">🎟️</span>
          Dati partecipanti
        </div>
        ${this.ticketLines.map((line, lineIdx) => html`
          <div style="margin-bottom: var(--afianco-spacing-md);">
            ${line.quantity > 1
              ? html`
                  <div
                    style="font-size: 12px;
                           font-weight: 600;
                           color: var(--afianco-color-text-secondary);
                           margin-bottom: var(--afianco-spacing-xs);">
                    ${line.productName} (${line.quantity} biglietti)
                  </div>
                `
              : html`
                  <div
                    style="font-size: 12px;
                           font-weight: 600;
                           color: var(--afianco-color-text-secondary);
                           margin-bottom: var(--afianco-spacing-xs);">
                    ${line.productName}
                  </div>
                `}
            ${line.attendees.map((att, attIdx) => html`
              <div
                style="background: var(--afianco-color-muted, #f9fafb);
                       border-radius: 8px;
                       padding: var(--afianco-spacing-md);
                       margin-bottom: var(--afianco-spacing-sm);">
                <div
                  style="font-size: 11px;
                         font-weight: 700;
                         color: var(--afianco-color-text, #111827);
                         text-transform: uppercase;
                         letter-spacing: 0.04em;
                         margin-bottom: var(--afianco-spacing-sm);">
                  Partecipante ${attIdx + 1}
                </div>
                <div class="form-group">
                  <label>${t('checkout.name_required')}</label>
                  <input
                    type="text"
                    required
                    placeholder="Nome e cognome"
                    .value=${att.name}
                    @input=${(e: InputEvent) =>
                      updateAttendee(lineIdx, attIdx, 'name', (e.target as HTMLInputElement).value)}>
                </div>
                ${line.requireEmail
                  ? html`
                      <div class="form-group">
                        <label>${t('checkout.email_required')}</label>
                        <input
                          type="email"
                          required
                          .value=${att.email}
                          @input=${(e: InputEvent) =>
                            updateAttendee(lineIdx, attIdx, 'email', (e.target as HTMLInputElement).value)}>
                      </div>
                    `
                  : ''}
                ${line.requirePhone
                  ? html`
                      <div class="form-group">
                        <label>Telefono*</label>
                        <input
                          type="tel"
                          required
                          .value=${att.phone}
                          @input=${(e: InputEvent) =>
                            updateAttendee(lineIdx, attIdx, 'phone', (e.target as HTMLInputElement).value)}>
                      </div>
                    `
                  : html`
                      <div class="form-group">
                        <label>${t('checkout.phone_optional')}</label>
                        <input
                          type="tel"
                          .value=${att.phone}
                          @input=${(e: InputEvent) =>
                            updateAttendee(lineIdx, attIdx, 'phone', (e.target as HTMLInputElement).value)}>
                      </div>
                    `}
                ${line.attendeeFields.map((f) => {
                  const v = att.custom_fields[f.id] ?? '';
                  const onInput = (e: Event) =>
                    updateCustomField(
                      lineIdx,
                      attIdx,
                      f.id,
                      (e.target as HTMLInputElement | HTMLTextAreaElement).value,
                    );
                  return html`
                    <div class="form-group">
                      <label>${f.label}${f.required ? '*' : ''}</label>
                      ${f.type === 'textarea'
                        ? html`
                            <textarea
                              rows="2"
                              placeholder=${f.placeholder ?? ''}
                              ?required=${f.required}
                              .value=${v}
                              @input=${onInput}></textarea>
                          `
                        : html`
                            <input
                              type=${f.type === 'number' ? 'number' : 'text'}
                              placeholder=${f.placeholder ?? ''}
                              ?required=${f.required}
                              .value=${v}
                              @input=${onInput}>
                          `}
                      ${f.help_text
                        ? html`<small style="display:block; margin-top:4px; color: var(--afianco-color-text-secondary); font-size: var(--afianco-font-size-xs);">${f.help_text}</small>`
                        : ''}
                    </div>
                  `;
                })}
              </div>
            `)}
          </div>
        `)}
      </div>
    `;
  }

  /**
   * Track E Step 3.2 — Render dynamic order_fields block.
   *
   * Per ogni FieldConfig aggregato dai products del cart, renderizza
   * un input dinamico in base al type (text/textarea/number). Required
   * fields hanno l'asterisco nel label. Backend rivalida il required
   * check (defense-in-depth).
   */
  private renderOrderFieldsBlock() {
    return html`
      <div
        style="margin-top: var(--afianco-spacing-md);
               padding-top: var(--afianco-spacing-md);
               border-top: 1px solid var(--afianco-color-border);">
        <div
          style="font-size: var(--afianco-font-size-sm);
                 font-weight: var(--afianco-font-weight-bold);
                 color: var(--afianco-color-text-secondary);
                 margin-bottom: var(--afianco-spacing-sm);">
          Informazioni aggiuntive
        </div>
        ${this.aggregatedOrderFields.map((f) => {
          const inputId = `afianco-order-field-${f.id}`;
          const handleInput = (e: Event) => {
            const v = (e.target as HTMLInputElement | HTMLTextAreaElement).value;
            this.orderFieldsData = { ...this.orderFieldsData, [f.id]: v };
          };
          return html`
            <div class="form-group">
              <label for=${inputId}>
                ${f.label}${f.required ? '*' : ''}
              </label>
              ${f.type === 'textarea'
                ? html`
                    <textarea
                      id=${inputId}
                      rows="3"
                      placeholder=${f.placeholder ?? ''}
                      ?required=${f.required}
                      .value=${this.orderFieldsData[f.id] ?? ''}
                      @input=${handleInput}></textarea>
                  `
                : html`
                    <input
                      id=${inputId}
                      type=${f.type === 'number' ? 'number' : 'text'}
                      placeholder=${f.placeholder ?? ''}
                      ?required=${f.required}
                      .value=${this.orderFieldsData[f.id] ?? ''}
                      @input=${handleInput}>
                  `}
              ${f.help_text
                ? html`<small style="display:block; margin-top:4px; color: var(--afianco-color-text-secondary); font-size: var(--afianco-font-size-xs);">${f.help_text}</small>`
                : ''}
            </div>
          `;
        })}
      </div>
    `;
  }

  /**
   * Track E Step 3.3 — Render shipping address form (visible quando
   * cart contiene almeno 1 physical product).
   *
   * Form structured con i 7 field di ShippingAddressInput backend:
   * recipient_name (opt), line1 (required), civic (opt), postal_code
   * (required), city (required), province (opt), country (required, IT default).
   *
   * Mirror del React storefront (StorefrontPage.js lines 2289-2358):
   * stessi field, stessi pattern di validazione (CAP IT 5 digit,
   * country ISO 3166-1 alpha-2).
   *
   * MVP scope: fulfillment_mode=shipping fisso. Picker shipping vs
   * local_pickup + shipping options selector arriveranno in V2 (richiede
   * fetch /api/public/shipping-options/{slug} + radio selector).
   */
  private renderShippingBlock() {
    const handle = (field: string) => (e: Event) => {
      const v = (e.target as HTMLInputElement | HTMLSelectElement).value;
      (this as unknown as Record<string, string>)[field] = v;
      this.requestUpdate();
    };
    return html`
      <div
        style="margin-top: var(--afianco-spacing-md);
               padding-top: var(--afianco-spacing-md);
               border-top: 1px solid var(--afianco-color-border);">
        <div
          style="font-size: var(--afianco-font-size-sm);
                 font-weight: var(--afianco-font-weight-bold);
                 color: var(--afianco-color-text-secondary);
                 margin-bottom: var(--afianco-spacing-sm);
                 display: flex; align-items: center; gap: 6px;">
          <span aria-hidden="true">📦</span>
          Indirizzo di spedizione
        </div>

        <div class="form-group">
          <label for="ship-recipient">Destinatario (opzionale)</label>
          <input
            id="ship-recipient"
            type="text"
            placeholder=${t('checkout.recipient_placeholder')}
            .value=${this.shipRecipient}
            @input=${handle('shipRecipient')}>
        </div>

        <div style="display: grid; grid-template-columns: 2fr 1fr; gap: var(--afianco-spacing-md);">
          <div class="form-group">
            <label for="ship-line1">Via*</label>
            <input
              id="ship-line1"
              type="text"
              required
              placeholder=${t('checkout.address_line_placeholder')}
              .value=${this.shipLine1}
              @input=${handle('shipLine1')}>
          </div>
          <div class="form-group">
            <label for="ship-civic">N. civico</label>
            <input
              id="ship-civic"
              type="text"
              placeholder=${t('checkout.civic_placeholder')}
              .value=${this.shipCivic}
              @input=${handle('shipCivic')}>
          </div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 2fr; gap: var(--afianco-spacing-md);">
          <div class="form-group">
            <label for="ship-postal">CAP*</label>
            <input
              id="ship-postal"
              type="text"
              required
              placeholder=${t('checkout.postal_placeholder')}
              maxlength="16"
              .value=${this.shipPostalCode}
              @input=${handle('shipPostalCode')}>
          </div>
          <div class="form-group">
            <label for="ship-city">Città*</label>
            <input
              id="ship-city"
              type="text"
              required
              placeholder=${t('checkout.city_placeholder')}
              .value=${this.shipCity}
              @input=${handle('shipCity')}>
          </div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--afianco-spacing-md);">
          <div class="form-group">
            <label for="ship-province">Provincia</label>
            <input
              id="ship-province"
              type="text"
              placeholder=${t('checkout.province_placeholder')}
              maxlength="8"
              style="text-transform: uppercase;"
              .value=${this.shipProvince}
              @input=${handle('shipProvince')}>
          </div>
          <div class="form-group">
            <label for="ship-country">Paese*</label>
            <select
              id="ship-country"
              required
              .value=${this.shipCountry}
              @change=${handle('shipCountry')}>
              <option value="IT">Italia</option>
              <option value="FR">Francia</option>
              <option value="DE">Germania</option>
              <option value="CH">Svizzera</option>
              <option value="AT">Austria</option>
              <option value="ES">Spagna</option>
              <option value="SI">Slovenia</option>
              <option value="HR">Croazia</option>
            </select>
          </div>
        </div>
      </div>
    `;
  }

  /**
   * Track E Step 4.1 — Render coupon picker block.
   *
   * UX pattern Shopify/Amazon: input + bottone "Applica". On success
   * mostra badge verde con discount + bottone "Rimuovi". On error
   * mostra alert rosso inline.
   *
   * Currency formatting riusa la locale browser (Intl.NumberFormat).
   */
  private renderCouponBlock() {
    const currency = this.activeCart?.currency_snapshot ?? 'EUR';
    const formatPrice = (amt: number): string => {
      try {
        return new Intl.NumberFormat(undefined, {
          style: 'currency',
          currency,
          minimumFractionDigits: 2,
        }).format(amt);
      } catch {
        return `${amt.toFixed(2)} ${currency}`;
      }
    };
    return html`
      <div
        style="margin-top: var(--afianco-spacing-md);
               padding-top: var(--afianco-spacing-md);
               border-top: 1px solid var(--afianco-color-border);">
        <div
          style="font-size: var(--afianco-font-size-sm);
                 font-weight: var(--afianco-font-weight-bold);
                 color: var(--afianco-color-text-secondary);
                 margin-bottom: var(--afianco-spacing-sm);
                 display: flex; align-items: center; gap: 6px;">
          <span aria-hidden="true">🎟️</span>
          Codice promo
        </div>

        ${this.couponApplied
          ? html`
              <div
                role="status"
                style="display: flex;
                       align-items: center;
                       justify-content: space-between;
                       gap: 12px;
                       padding: 10px 14px;
                       background: #d1fae5;
                       border: 1px solid #10b981;
                       border-radius: var(--afianco-radius-md);
                       font-size: 13px;">
                <span style="color: #065f46;">
                  ✓ Codice <strong>${this.couponApplied.code}</strong>
                  applicato — sconto ${formatPrice(this.couponApplied.discount)}
                  ${this.couponApplied.discount_pct
                    ? html` (${this.couponApplied.discount_pct}%)`
                    : ''}
                </span>
                <button
                  type="button"
                  @click=${() => this.removeCoupon()}
                  style="background: transparent;
                         border: none;
                         color: #065f46;
                         text-decoration: underline;
                         cursor: pointer;
                         font-size: 12px;
                         font-weight: 600;">
                  Rimuovi
                </button>
              </div>
            `
          : html`
              <div style="display: flex; gap: 8px;">
                <input
                  type="text"
                  placeholder=${t('coupon.placeholder')}
                  style="text-transform: uppercase; flex: 1;"
                  maxlength="30"
                  .value=${this.couponCode}
                  @input=${(e: InputEvent) =>
                    (this.couponCode = (e.target as HTMLInputElement).value)}
                  @keydown=${(e: KeyboardEvent) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      void this.applyCoupon();
                    }
                  }}>
                <button
                  type="button"
                  ?disabled=${this.couponValidating || !this.couponCode.trim()}
                  @click=${() => void this.applyCoupon()}
                  style="background: var(--afianco-color-primary);
                         color: var(--afianco-color-primary-text);
                         border: none;
                         border-radius: var(--afianco-radius-md);
                         padding: 0 16px;
                         font-family: inherit;
                         font-size: var(--afianco-font-size-sm);
                         font-weight: var(--afianco-font-weight-medium);
                         cursor: pointer;
                         white-space: nowrap;">
                  ${this.couponValidating ? '…' : 'Applica'}
                </button>
              </div>
              ${this.couponError
                ? html`
                    <div
                      role="alert"
                      style="margin-top: 8px;
                             padding: 8px 12px;
                             background: #fef2f2;
                             color: var(--afianco-color-danger);
                             border-radius: 6px;
                             font-size: 12px;">
                      ${this.couponError}
                    </div>
                  `
                : ''}
            `}
      </div>
    `;
  }

  private openStripePopup(url: string): void {
    if (typeof window === 'undefined') return;
    const w = 600;
    const h = 800;
    const left = Math.max(0, Math.round((window.outerWidth - w) / 2));
    const top = Math.max(0, Math.round((window.outerHeight - h) / 2));
    const specs = `width=${w},height=${h},left=${left},top=${top},scrollbars=yes,resizable=yes`;
    this.popupRef = window.open(url, 'afianco-checkout', specs);
    if (!this.popupRef) {
      this.errorMsg =
        t('checkout.popup_blocked');
      this.status = 'idle';
    }
  }

  // ── Computed ─────────────────────────────────────────────────────────

  /** Resolve the return URL — explicit attribute OR current page. */
  private get resolvedReturnUrl(): string {
    if (this.returnUrl) return this.returnUrl;
    if (typeof window !== 'undefined') {
      return `${window.location.origin}${window.location.pathname}`;
    }
    return '';
  }

  /** Origin (scheme://host:port) of the return URL — for postMessage check. */
  private get originOfReturnUrl(): string | null {
    try {
      return new URL(this.resolvedReturnUrl).origin;
    } catch {
      return null;
    }
  }

  /** Origin of the backend baseUrl — postMessage from bridge ha origin del backend. */
  private get originOfBackendUrl(): string | null {
    try {
      if (!this.ctx.client) return null;
      return new URL(this.ctx.client.baseUrl).origin;
    } catch {
      return null;
    }
  }

  // ── Render ────────────────────────────────────────────────────────────

  render() {
    if (!this.open) {
      return html``;
    }
    return html`
      <div class="scrim" @click=${(e: MouseEvent) => {
        if (e.target === e.currentTarget) this.closeModal();
      }}>
        <div class="modal" role="dialog" aria-modal="true" aria-label="Checkout">
          <div class="modal-header">
            <h2 class="modal-title">${t('checkout.title')}</h2>
            <button
              class="close-btn"
              type="button"
              aria-label=${t('checkout.close_label')}
              @click=${() => this.closeModal()}>×</button>
          </div>
          <div class="modal-body">
            ${this.errorMsg
              ? html`<div class="error-banner" role="alert">${this.errorMsg}</div>`
              : ''}
            ${this.status === 'awaiting_payment'
              ? html`<div class="status-banner">${t('checkout.payment_pending')}</div>`
              : this.status === 'completed'
                ? html`<div class="status-banner">${t('checkout.order_completed')}</div>`
                : html`
                    <form
                      @submit=${(e: SubmitEvent) => {
                        e.preventDefault();
                        void this.submit();
                      }}>
                      <div class="form-group">
                        <label for="afianco-name">${t('checkout.name_required')}</label>
                        <input
                          id="afianco-name"
                          type="text"
                          required
                          .value=${this.name}
                          @input=${(e: InputEvent) =>
                            (this.name = (e.target as HTMLInputElement).value)}>
                      </div>
                      <div class="form-group">
                        <label for="afianco-email">${t('checkout.email_required')}</label>
                        <input
                          id="afianco-email"
                          type="email"
                          required
                          .value=${this.email}
                          @input=${(e: InputEvent) =>
                            (this.email = (e.target as HTMLInputElement).value)}>
                      </div>
                      <div class="form-group">
                        <label for="afianco-phone">${t('checkout.phone_optional')}</label>
                        <input
                          id="afianco-phone"
                          type="tel"
                          .value=${this.phone}
                          @input=${(e: InputEvent) =>
                            (this.phone = (e.target as HTMLInputElement).value)}>
                      </div>

                      <!-- Track E Step 3.4 — Attendee per_ticket form (event_ticket) -->
                      ${this.ticketLines.length > 0
                        ? this.renderTicketLinesBlock()
                        : ''}

                      <!-- Track E Step 3.2 — Dynamic order_fields renderer. -->
                      ${this.aggregatedOrderFields.length > 0
                        ? this.renderOrderFieldsBlock()
                        : ''}

                      <!-- Track E Step 4.2 — Fulfillment mode picker (visible solo se store ha >1 mode) -->
                      ${this.cartHasPhysical
                        ? html`
                            <div style="margin-top: var(--afianco-spacing-md); padding-top: var(--afianco-spacing-md); border-top: 1px solid var(--afianco-color-border);">
                              <afianco-fulfillment-picker
                                .modes=${this.ctx?.init?.fulfillment_modes ?? ['shipping']}
                                .selected=${this.fulfillmentMode}
                                group-label=${t('checkout.section_fulfillment')}
                                @afianco:fulfillment-mode-changed=${this.handleFulfillmentModeChanged}>
                              </afianco-fulfillment-picker>
                            </div>
                          `
                        : ''}

                      <!-- Track E Step 4.2 — Shipping options picker (solo mode=shipping + cart physical) -->
                      ${this.cartHasPhysical && this.fulfillmentMode === 'shipping'
                        ? html`
                            <div style="margin-top: var(--afianco-spacing-md);">
                              <afianco-shipping-options-picker
                                .subtotal=${this.activeCart?.subtotal_snapshot ?? 0}
                                .currency=${this.activeCart?.currency_snapshot ?? 'EUR'}
                                .selectedId=${this.selectedShippingOption?.id ?? null}
                                group-label=${t('checkout.section_shipping_option')}
                                @afianco:shipping-option-selected=${this.handleShippingOptionSelected}>
                              </afianco-shipping-options-picker>
                            </div>
                          `
                        : ''}

                      <!-- Track E Step 3.3 — Shipping address form (solo mode=shipping + cart physical) -->
                      ${this.cartHasPhysical && this.fulfillmentMode === 'shipping'
                        ? this.renderShippingBlock()
                        : ''}

                      <!-- Track E Step 4.1 — Coupon picker -->
                      ${this.renderCouponBlock()}

                      <!-- Track E Step 5.1 — Order notes textarea (optional) -->
                      <div
                        style="margin-top: var(--afianco-spacing-md);
                               padding-top: var(--afianco-spacing-md);
                               border-top: 1px solid var(--afianco-color-border);">
                        <label
                          for="afianco-order-notes"
                          style="display:block;
                                 font-size: var(--afianco-font-size-sm);
                                 font-weight: var(--afianco-font-weight-bold);
                                 color: var(--afianco-color-text-secondary);
                                 margin-bottom: 6px;">
                          <span aria-hidden="true">💬</span>
                          ${t('checkout.notes_label')}
                        </label>
                        <textarea
                          id="afianco-order-notes"
                          rows="2"
                          maxlength="2000"
                          placeholder=${t('checkout.notes_placeholder')}
                          .value=${this.orderNotes}
                          @input=${(e: Event) =>
                            (this.orderNotes = (e.target as HTMLTextAreaElement).value)}>
                        </textarea>
                      </div>

                      <div class="checkbox-row">
                        <input
                          id="afianco-gdpr-privacy"
                          type="checkbox"
                          .checked=${this.gdprPrivacy}
                          @change=${(e: Event) =>
                            (this.gdprPrivacy = (e.target as HTMLInputElement).checked)}>
                        <label for="afianco-gdpr-privacy">
                          Accetto la
                          <a
                            class="gdpr-link"
                            href=${this.ctx.init?.privacy_policy_url ?? '#'}
                            target="_blank"
                            rel="noopener noreferrer"
                            @click=${(e: Event) => e.stopPropagation()}>
                            Privacy Policy
                          </a>
                          ${t('checkout.merchant_suffix')}
                        </label>
                      </div>
                      <div class="checkbox-row">
                        <input
                          id="afianco-gdpr-terms"
                          type="checkbox"
                          .checked=${this.gdprTerms}
                          @change=${(e: Event) =>
                            (this.gdprTerms = (e.target as HTMLInputElement).checked)}>
                        <label for="afianco-gdpr-terms">
                          Accetto i
                          <a
                            class="gdpr-link"
                            href=${this.ctx.init?.terms_service_url ?? '#'}
                            target="_blank"
                            rel="noopener noreferrer"
                            @click=${(e: Event) => e.stopPropagation()}>
                            Termini di Servizio
                          </a>
                          *
                        </label>
                      </div>
                      <div class="checkbox-row">
                        <input
                          id="afianco-gdpr-marketing"
                          type="checkbox"
                          .checked=${this.gdprMarketing}
                          @change=${(e: Event) =>
                            (this.gdprMarketing = (e.target as HTMLInputElement).checked)}>
                        <label for="afianco-gdpr-marketing">
                          ${t('checkout.gdpr_marketing')}
                        </label>
                      </div>
                      ${this.allowSignup
                        ? html`<div class="checkbox-row">
                            <input
                              id="afianco-create-account"
                              type="checkbox"
                              .checked=${this.createAccount}
                              @change=${(e: Event) =>
                                (this.createAccount = (e.target as HTMLInputElement).checked)}>
                            <label for="afianco-create-account">
                              ${t('checkout.create_account_checkbox')}
                            </label>
                          </div>`
                        : ''}
                      ${this.allowSignup && this.createAccount
                        ? html`<div class="form-group">
                            <label for="afianco-password">Password (min 8 caratteri)*</label>
                            <input
                              id="afianco-password"
                              type="password"
                              minlength="8"
                              .value=${this.password}
                              @input=${(e: InputEvent) =>
                                (this.password = (e.target as HTMLInputElement).value)}>
                          </div>`
                        : ''}
                      <button
                        class="submit-btn"
                        type="submit"
                        ?disabled=${this.submitting || this.loadingProductFields}>
                        ${this.submitting
                          ? t('checkout.submitting')
                          : this.loadingProductFields
                            ? t('checkout.loading_fields')
                            : t('checkout.submit')}
                      </button>
                    </form>
                  `}
          </div>
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'afianco-checkout-button': AfiancoCheckoutButton;
  }
  interface HTMLElementEventMap {
    'afianco:order-completed': CustomEvent<OrderCompletedPayload>;
    'afianco:order-failed': CustomEvent<{ message: string }>;
  }
}
