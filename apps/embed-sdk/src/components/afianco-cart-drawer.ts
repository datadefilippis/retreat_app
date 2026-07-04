/**
 * <afianco-cart-drawer> — Phase 1 Step 25 (Track C).
 *
 * Slide-in mini cart drawer per il widget Stream A. Ascolta gli eventi
 * `afianco:add-to-cart` (bubbles+composed) dispatchati dai product-card
 * children, gestisce il cart server-side via api-client e renderizza
 * un panel laterale con items + qty controls + CTA checkout.
 *
 * Uso tipico (nested sotto storefront-init):
 *
 *   <afianco-storefront-init slug="acme">
 *     <afianco-product-grid show-filter-nav></afianco-product-grid>
 *     <afianco-cart-drawer></afianco-cart-drawer>  <!-- always-mounted -->
 *   </afianco-storefront-init>
 *
 * Persistence
 * -----------
 * Il cart_id viene salvato in localStorage chiavato per merchant slug
 * (es. `afianco_cart_id_acme`). Al mount, se esiste un cart_id valido,
 * lo carica via client.embed.cart.get() (riprende lo stato cart cross-
 * page-load). Se la chiave è missing o stale, ne crea uno nuovo al
 * primo add-to-cart.
 *
 * Trigger UI
 * ----------
 * Un floating button in basso-destra mostra il badge con item_count e
 * apre/chiude il drawer slide-in da destra. Il drawer è position:fixed
 * con z-index sopra il merchant content (-> --afianco-z-modal).
 *
 * Custom events emessi
 * --------------------
 * - `afianco:cart-updated` (detail: CartResponse) — ad ogni mutazione
 * - `afianco:cart-opened` / `afianco:cart-closed`
 * - `afianco:checkout-requested` (detail: { cart_id, cart }) — al click
 *   "Checkout" CTA. Il futuro <afianco-checkout-button> (Step 26)
 *   listenа questo evento per orchestrare lo Stripe popup.
 *
 * Attributes
 * ----------
 * - `auto-open` (boolean, default true): apri drawer al primo add-to-cart
 * - `position` ("right" | "left", default "right"): lato slide-in
 */

import { LitElement, html, css, nothing, type PropertyValues } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { consume } from '@lit/context';
import { afiancoBaseStyles } from '@afianco/design-tokens';
import { SingletonController } from '../store/singleton-guard.js';
// Sprint 4 W4.7 — i18n wiring (parity React 4 lingue)
import { t } from '../i18n/index.js';
import type {
  CartResponse,
  CartItemInput,
  CartUpdate,
  EmbedProductCard,
} from '@afianco/api-client';
import {
  storefrontContext,
  STOREFRONT_INITIAL,
  type StorefrontContext,
} from '../context.js';
import { StoreConsumerController } from '../store/store-consumer.js';

@customElement('afianco-cart-drawer')
export class AfiancoCartDrawer extends LitElement {
  /**
   * Apri automaticamente il drawer dopo ogni add-to-cart.
   *
   * Track E Step 2.4.4 — DEFAULT CAMBIATO a `false` per allinearsi
   * allo standard e-commerce moderno (Shopify, Amazon, Stripe Checkout):
   *   - add-to-cart → badge cart-icon si aggiorna (visual feedback)
   *   - drawer si apre SOLO se user clicca l'icona carrello nell'header
   *
   * Rationale UX: aprire un drawer ogni volta interrompe il browsing del
   * customer che sta confrontando piu' prodotti. Il merchant puo' fare
   * opt-in al vecchio comportamento con `<afianco-cart-drawer auto-open>`.
   */
  @property({ type: Boolean, attribute: 'auto-open' })
  autoOpen = false;

  /** "right" (default) | "left" slide-in side. */
  @property({ type: String })
  position: 'right' | 'left' = 'right';

  /**
   * Track E Step 2.4.4 — quando true, nasconde il floating trigger
   * button interno. Usato quando il merchant include <afianco-header>
   * che fornisce i trigger button in un layout unificato.
   * Il drawer si apre via document-level event 'afianco:open-cart'.
   */
  @property({ type: Boolean, attribute: 'hide-trigger', reflect: true })
  hideTrigger = false;

  /** Open/close state (controllabile via toggle()) */
  @property({ type: Boolean, reflect: true })
  open = false;

  @consume({ context: storefrontContext, subscribe: true })
  @state()
  ctx: StorefrontContext = STOREFRONT_INITIAL;

  /** À-la-carte: aggancio al kernel se fuori da un provider (no-op se dentro). */
  protected _store = new StoreConsumerController(this);

  /** Guard singleton: un solo cart-drawer attivo per slug. */
  protected _singleton = new SingletonController(this, 'cart-drawer');

  /** Current cart loaded from server (null until first add). */
  @state()
  private cart: CartResponse | null = null;

  /** UI sync state. */
  @state()
  private syncing = false;

  /** Last error (network or backend). */
  @state()
  private errorMsg: string | null = null;

  /** Guard: prevent duplicate event listener attach. */
  private _listenerAttached = false;

  /** Guard: prevent re-init on every updated() cycle. */
  private _initialized = false;

  static styles = [
    afiancoBaseStyles,
    css`
      :host {
        display: contents;
        position: relative;
      }
      .trigger {
        position: fixed;
        bottom: var(--afianco-spacing-xl);
        z-index: var(--afianco-z-modal);
        background: var(--afianco-color-primary);
        color: var(--afianco-color-primary-text);
        border: none;
        border-radius: var(--afianco-radius-pill);
        padding: var(--afianco-spacing-md) var(--afianco-spacing-lg);
        font-family: var(--afianco-font-family);
        font-size: var(--afianco-font-size-md);
        font-weight: var(--afianco-font-weight-medium);
        cursor: pointer;
        box-shadow: var(--afianco-shadow-lg);
        display: inline-flex;
        align-items: center;
        gap: var(--afianco-spacing-sm);
        transition: transform var(--afianco-duration-fast)
          var(--afianco-easing-standard);
      }
      :host([position='right']) .trigger {
        right: var(--afianco-spacing-xl);
      }
      :host([position='left']) .trigger {
        left: var(--afianco-spacing-xl);
      }
      /* Track E Step 2.4.4 — quando l'header unificato e' presente,
         hide-trigger nasconde il floating FAB del cart per evitare
         duplicazione visiva. Il drawer continua a funzionare normalmente. */
      :host([hide-trigger]) .trigger {
        display: none;
      }
      .trigger:hover {
        transform: translateY(-1px);
      }
      .badge {
        background: rgba(255, 255, 255, 0.25);
        color: inherit;
        border-radius: var(--afianco-radius-pill);
        padding: 0 var(--afianco-spacing-sm);
        font-size: var(--afianco-font-size-xs);
        font-weight: var(--afianco-font-weight-bold);
        min-width: 18px;
        text-align: center;
      }
      .scrim {
        position: fixed;
        inset: 0;
        /* E2.4.4 — opacita' rinforzata 0.32 → 0.5 per dare segnale
           visivo chiaro "questo e' modale, click fuori per chiudere". */
        background: rgba(15, 23, 42, 0.5);
        opacity: 0;
        pointer-events: none;
        transition: opacity var(--afianco-duration-normal)
          var(--afianco-easing-standard);
        z-index: var(--afianco-z-modal);
        cursor: pointer;
      }
      :host([open]) .scrim {
        opacity: 1;
        pointer-events: auto;
      }
      .drawer {
        position: fixed;
        top: 0;
        bottom: 0;
        width: min(420px, 100vw);
        background: var(--afianco-color-bg);
        box-shadow: var(--afianco-shadow-lg);
        z-index: calc(var(--afianco-z-modal) + 1);
        display: flex;
        flex-direction: column;
        transform: translateX(100%);
        transition: transform var(--afianco-duration-normal)
          var(--afianco-easing-standard);
        /* E2.4.4 defense-in-depth: oltre al transform che porta off-screen,
           also use visibility:hidden quando chiuso. Cosi' anche se transform
           viene override da CSS merchant, il drawer resta invisibile +
           non riceve eventi click "fantasma". */
        visibility: hidden;
        pointer-events: none;
      }
      :host([position='left']) .drawer {
        left: 0;
        transform: translateX(-100%);
      }
      :host([position='right']) .drawer {
        right: 0;
      }
      :host([open]) .drawer {
        transform: translateX(0);
        visibility: visible;
        pointer-events: auto;
      }
      .drawer-header {
        padding: var(--afianco-spacing-lg);
        border-bottom: 1px solid var(--afianco-color-border);
        display: flex;
        align-items: center;
        justify-content: space-between;
      }
      .drawer-title {
        margin: 0;
        font-size: var(--afianco-font-size-lg);
        font-weight: var(--afianco-font-weight-bold);
      }
      .close-btn {
        /* E2.4.4 — target click size aumentato 24x24 → 36x36 (Apple HIG
           min 44x44 e Material 48x48 suggeriti). Tap target piu' grande
           = piu' affidabile sia desktop che mobile. */
        background: transparent;
        border: 1px solid transparent;
        color: var(--afianco-color-text-secondary);
        cursor: pointer;
        font-size: 24px;
        line-height: 1;
        width: 36px;
        height: 36px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        border-radius: var(--afianco-radius-md);
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
      .drawer-body {
        flex: 1;
        overflow-y: auto;
        padding: var(--afianco-spacing-lg);
      }
      .item {
        display: flex;
        gap: var(--afianco-spacing-md);
        padding: var(--afianco-spacing-md) 0;
        border-bottom: 1px solid var(--afianco-color-border);
      }
      .item:last-child {
        border-bottom: none;
      }
      .item-info {
        flex: 1;
        min-width: 0;
      }
      .item-name {
        font-size: var(--afianco-font-size-md);
        font-weight: var(--afianco-font-weight-medium);
        margin: 0 0 var(--afianco-spacing-xs);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      .item-price {
        font-size: var(--afianco-font-size-sm);
        color: var(--afianco-color-text-secondary);
      }
      .qty-controls {
        display: inline-flex;
        align-items: center;
        gap: var(--afianco-spacing-xs);
        background: var(--afianco-color-surface);
        border-radius: var(--afianco-radius-md);
        padding: 4px;
      }
      .qty-btn {
        background: var(--afianco-color-bg);
        border: 1px solid var(--afianco-color-border);
        border-radius: var(--afianco-radius-sm);
        width: 28px;
        height: 28px;
        cursor: pointer;
        font-size: var(--afianco-font-size-md);
        font-weight: var(--afianco-font-weight-bold);
        color: var(--afianco-color-text-primary);
      }
      .qty-btn:hover {
        background: var(--afianco-color-surface);
      }
      .qty-display {
        min-width: 28px;
        text-align: center;
        font-size: var(--afianco-font-size-sm);
        font-weight: var(--afianco-font-weight-medium);
      }
      .remove-btn {
        background: transparent;
        border: none;
        color: var(--afianco-color-danger);
        cursor: pointer;
        font-size: var(--afianco-font-size-xs);
        padding: var(--afianco-spacing-xs);
        align-self: flex-start;
        text-decoration: underline;
      }
      .empty {
        text-align: center;
        padding: var(--afianco-spacing-xxl) var(--afianco-spacing-lg);
        color: var(--afianco-color-text-muted);
      }
      .drawer-footer {
        padding: var(--afianco-spacing-lg);
        border-top: 1px solid var(--afianco-color-border);
        background: var(--afianco-color-surface);
      }
      .subtotal {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: var(--afianco-font-size-md);
        font-weight: var(--afianco-font-weight-bold);
        margin-bottom: var(--afianco-spacing-md);
      }
      .checkout-cta {
        width: 100%;
        background: var(--afianco-color-primary);
        color: var(--afianco-color-primary-text);
        border: none;
        border-radius: var(--afianco-radius-md);
        padding: var(--afianco-spacing-md);
        font-family: var(--afianco-font-family);
        font-size: var(--afianco-font-size-md);
        font-weight: var(--afianco-font-weight-medium);
        cursor: pointer;
      }
      .checkout-cta:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }
      .error-banner {
        background: #fff5f5;
        border: 1px solid #fed7d7;
        color: var(--afianco-color-danger);
        padding: var(--afianco-spacing-sm) var(--afianco-spacing-md);
        border-radius: var(--afianco-radius-sm);
        font-size: var(--afianco-font-size-xs);
        margin-bottom: var(--afianco-spacing-md);
      }
    `,
  ];

  // ── Lifecycle ─────────────────────────────────────────────────────────

  connectedCallback(): void {
    super.connectedCallback();
    if (!this._listenerAttached) {
      // Listen the bubbles+composed `afianco:add-to-cart` event from
      // any product-card descendant of the storefront-init parent.
      // The drawer e' tipicamente sibling, ma il document-level listener
      // funziona indipendentemente dalla posizione DOM.
      document.addEventListener(
        'afianco:add-to-cart',
        this._handleAddToCart as EventListener,
      );
      // Track E Step 2.4.4 — listener per apertura remota dal
      // <afianco-header> trigger button. Permette UX unificata
      // senza coupling diretto tra header e cart-drawer.
      document.addEventListener(
        'afianco:open-cart',
        this._handleOpenCart as EventListener,
      );
      // Track E Step 2.4.4 — ESC key per chiudere (accessibility +
      // UX standard moderna allineata ai drawer Shopify/Amazon/Stripe).
      document.addEventListener('keydown', this._handleKeydown);
      // Sprint 2 W2.6 — listen customer login per guest->auth cart merge.
      // Quando il customer fa login con un guest cart attivo, chiamiamo
      // POST /embed/cart/{guest_id}/merge con Bearer JWT (auto-attached
      // dal SDK client). Il cart guest viene assorbito dal cart customer.
      document.addEventListener(
        'afianco:customer-logged-in',
        this._handleCustomerLoggedIn as unknown as EventListener,
      );
      // B5 — sync cross-tab: un'altra tab dello stesso slug che muta il cart
      // scrive un segnale in localStorage → qui rifetchiamo per restare allineati.
      window.addEventListener('storage', this._onCartStorage);
      this._listenerAttached = true;
    }
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    if (this._listenerAttached) {
      document.removeEventListener(
        'afianco:add-to-cart',
        this._handleAddToCart as EventListener,
      );
      document.removeEventListener(
        'afianco:open-cart',
        this._handleOpenCart as EventListener,
      );
      document.removeEventListener('keydown', this._handleKeydown);
      document.removeEventListener(
        'afianco:customer-logged-in',
        this._handleCustomerLoggedIn as unknown as EventListener,
      );
      window.removeEventListener('storage', this._onCartStorage);
      this._listenerAttached = false;
    }
  }

  /**
   * Track E Step 2.4.4 — handle document-level open request dispatched
   * dal <afianco-header> trigger button (loose coupling via event bus).
   */
  private _handleOpenCart = (): void => {
    if (!this._singleton.active) return;
    this.setOpen(true);
  };

  /**
   * Sprint 2 W2.6 — handle customer login event per guest cart merge.
   *
   * Quando il customer fa login con un guest cart attivo, chiamiamo
   * POST /embed/cart/{guest_id}/merge che lato backend:
   *   1. valida Bearer JWT (customer_account_id + organization_id)
   *   2. trova un eventuale cart customer esistente
   *   3. merge guest_cart_items dentro customer_cart (server-side dedup
   *      su signature product+slot+tier)
   *   4. soft-delete del guest cart
   *   5. ritorna il cart merged (customer-owned)
   *
   * Edge cases:
   *   - guest cart empty -> skip merge (no need)
   *   - customer no existing cart -> server creates one + assorbe guest
   *   - merge fail -> mantieni guest cart locale + log warning (no UX break)
   *
   * Sentinel pinned by TestSEC_E_8_11_CartMergeOnLogin.
   */
  private _handleCustomerLoggedIn = async (
    e: CustomEvent<{ customer?: { id?: string }; access_token?: string }>,
  ): Promise<void> => {
    try {
      const client = this.ctx?.client;
      if (!client) return;
      const guestCartId = this.readCartIdFromStorage();
      if (!guestCartId) {
        // No guest cart — nothing to merge.
        return;
      }
      const currentItems = this.cart?.items ?? [];
      if (currentItems.length === 0) {
        // Cart locally empty — backend cart could be empty too. Skip
        // to avoid an unneeded round-trip + audit log noise.
        return;
      }
      const customerAccountId = e?.detail?.customer?.id;
      if (!customerAccountId) {
        // Login event senza customer.id — defensive, skip.
        return;
      }
      // POST /embed/cart/{guest_id}/merge con Bearer JWT (auto-attached
      // dal SDK request helper se token in localStorage). Backend valida
      // (cart_id, customer_account_id) compound + assorbe guest items.
      const mergedCart = await client.embed.cart.merge(guestCartId, {
        customer_account_id: customerAccountId,
      });
      if (mergedCart?.id) {
        // Update local cart_id + items con cart merged
        this.writeCartIdToStorage(mergedCart.id);
        this.cart = mergedCart;
        this.requestUpdate();
        this.dispatchEvent(
          new CustomEvent('afianco:cart-merged', {
            detail: { cart: mergedCart },
            bubbles: true,
            composed: true,
          }),
        );
      }
    } catch (exc) {
      // Soft-fail: guest cart stays locally + log warning. UX continua
      // a funzionare. Customer puo' completare checkout dal cart guest
      // (verra' associato all'order via auth-attached JWT comunque).
      // eslint-disable-next-line no-console
      console.warn('[afianco-cart-drawer] cart merge on login failed:', exc);
    }
  };

  /**
   * Track E Step 2.4.4 — ESC closes the drawer (a11y standard).
   * No-op se drawer e' gia' chiuso, evita event consumption inutile.
   */
  private _handleKeydown = (e: KeyboardEvent): void => {
    if (e.key === 'Escape' && this.open) {
      e.preventDefault();
      this.setOpen(false);
    }
  };

  protected updated(_changed: PropertyValues): void {
    if (this._initialized) return;
    // Solo il drawer ATTIVO carica il carrello: un eventuale drawer passivo
    // (duplicato per-route in SPA) non deve fare fetch/dispatch ridondanti.
    if (!this._singleton.active) return;
    if (this.ctx.status !== 'ready' || !this.ctx.client) return;
    this._initialized = true;
    // Try to recover cart from localStorage
    void this.loadPersistedCart();
  }

  // ── Persistence helpers ───────────────────────────────────────────────

  private get storageKey(): string {
    const slug = this.ctx.init?.slug ?? this.ctx.client?.slug ?? 'unknown';
    return `afianco_cart_id_${slug}`;
  }

  /** B5 — chiave segnale cross-tab: cambia ad ogni mutazione del cart. */
  private get touchKey(): string {
    const slug = this.ctx.init?.slug ?? this.ctx.client?.slug ?? 'unknown';
    return `afianco_cart_touch_${slug}`;
  }

  /** B5 — notifica le ALTRE tab (stesso slug) che il cart e' cambiato.
   *  Da chiamare SOLO dopo una mutazione locale (mai durante un refetch:
   *  altrimenti ping-pong tra tab). Lo storage event non scatta nella tab
   *  che scrive, solo nelle altre. */
  private _broadcastCartTouch(): void {
    try {
      if (typeof localStorage === 'undefined') return;
      localStorage.setItem(this.touchKey, String(Date.now()));
    } catch {
      // ignore (Safari private mode / storage piena)
    }
  }

  /** B5 — un'altra tab ha mutato il cart (o creato/cambiato cart_id) →
   *  rifetch per restare allineati. Solo il drawer attivo reagisce. */
  private _onCartStorage = (e: StorageEvent): void => {
    if (!e.key) return;
    if (e.key !== this.touchKey && e.key !== this.storageKey) return;
    if (!this._singleton.active) return;
    if (this.ctx.status !== 'ready' || !this.ctx.client) return;
    void this.loadPersistedCart();
  };

  private readCartIdFromStorage(): string | null {
    try {
      if (typeof localStorage === 'undefined') return null;
      return localStorage.getItem(this.storageKey);
    } catch {
      return null;
    }
  }

  private writeCartIdToStorage(cartId: string | null): void {
    try {
      if (typeof localStorage === 'undefined') return;
      if (cartId) {
        localStorage.setItem(this.storageKey, cartId);
      } else {
        localStorage.removeItem(this.storageKey);
      }
    } catch {
      // ignore
    }
  }

  private async loadPersistedCart(): Promise<void> {
    if (!this.ctx.client) return;
    const cartId = this.readCartIdFromStorage();
    if (!cartId) return;
    try {
      const cart = await this.ctx.client.embed.cart.get(cartId);
      this.cart = cart;
      this.notifyUpdated(cart);
    } catch {
      // Stale cart id (expired or deleted server-side) → drop it
      this.writeCartIdToStorage(null);
      this.cart = null;
    }
  }

  // ── Cart mutations ────────────────────────────────────────────────────

  /**
   * Public method: aggiunge un item al cart (creando il cart se necessario).
   * Usato sia dal listener afianco:add-to-cart sia da test/integration.
   *
   * Track E Step 2.4.7 — accetta `extras` con i campi type-specific
   * (service_option_id, booking_date, occurrence_id, ticket_tier_id,
   * rental_date_from, rental_date_to, ecc.) dal product-detail drawer.
   *
   * Idempotency dedup: la presenza di extras crea un compound key per
   * il merge — DUE add-to-cart dello stesso product_id con slot diversi
   * generano DUE linee separate (non vengono mergiate sulla qty).
   */
  async addItem(input: {
    product: EmbedProductCard;
    quantity: number;
    extras?: Record<string, unknown>;
  }): Promise<void> {
    if (!this.ctx.client) {
      this.errorMsg = t('cart.error_storefront_not_ready');
      return;
    }
    this.syncing = true;
    this.errorMsg = null;
    try {
      // Step 1: ensure cart exists
      let cart = this.cart;
      if (!cart) {
        cart = await this.ctx.client.embed.cart.create();
        this.writeCartIdToStorage(cart.id);
      }

      // Step 2: snapshot existing items (preserva tutti i type-specific)
      const existingItems = cart.items.map((it) => ({
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
        attendees: it.attendees,
        service_option_id: it.service_option_id,
        service_custom_request: it.service_custom_request, // R4
        extra_selections: it.extra_selections, // R2
      })) satisfies CartItemInput[];

      // Extract extras (default null per i campi assenti)
      const extras = input.extras ?? {};
      const newItem: CartItemInput = {
        product_id: input.product.id,
        quantity: input.quantity,
        occurrence_id: (extras.occurrence_id as string | undefined) ?? null,
        ticket_tier_id: (extras.ticket_tier_id as string | undefined) ?? null,
        rental_date_from: (extras.rental_date_from as string | undefined) ?? null,
        rental_date_to: (extras.rental_date_to as string | undefined) ?? null,
        rental_notes: (extras.rental_notes as string | undefined) ?? null,
        booking_date: (extras.booking_date as string | undefined) ?? null,
        booking_start_time: (extras.booking_start_time as string | undefined) ?? null,
        booking_end_time: (extras.booking_end_time as string | undefined) ?? null,
        booking_end_date: (extras.booking_end_date as string | undefined) ?? null,
        attendees: (extras.attendees as Record<string, unknown>[] | undefined) ?? null,
        service_option_id: (extras.service_option_id as string | undefined) ?? null,
        // R4 — richiesta personalizzata (slot proposto fuori dalle regole).
        service_custom_request: (extras.service_custom_request as boolean | undefined) ?? false,
        // R2 — extra selezionati (optional/radio) dal product-detail.
        extra_selections: (extras.extra_selections as Record<string, unknown> | undefined) ?? null,
      };

      // Step 3: dedup logic
      //   - Item "vanilla" (no extras) → match by product_id, increment qty
      //   - Item "type-specific" (con slot/occurrence/etc.) → match by
      //     compound signature (product_id + key extras). Stesso slot e'
      //     incrementabile, slot diverso = nuova linea cart.
      const sig = this.buildItemSignature(newItem);
      const idx = existingItems.findIndex(
        (it) => this.buildItemSignature(it) === sig,
      );
      if (idx >= 0) {
        existingItems[idx]!.quantity += input.quantity;
      } else {
        // Cast a `existingItems[0]` shape (concrete non-optional version
        // di CartItemInput). I null nei vari field opzionali sono safe
        // per il PATCH endpoint backend (Pydantic Optional[None] = null).
        existingItems.push(newItem as (typeof existingItems)[number]);
      }

      // Step 4: PATCH cart with merged items
      const body: CartUpdate = { items: existingItems };
      const updated = await this.ctx.client.embed.cart.update(cart.id, body);
      this.cart = updated;
      this.notifyUpdated(updated);
      this._broadcastCartTouch(); // B5 — allinea le altre tab

      // Step 5: optional auto-open (default false in E2.4.4)
      if (this.autoOpen) {
        this.setOpen(true);
      }
    } catch (e) {
      this.errorMsg = (e as Error)?.message ?? t('cart.error_update');
    } finally {
      this.syncing = false;
    }
  }

  /**
   * Track E Step 2.4.7 — compound signature per dedup item.
   *
   * Due item dello stesso prodotto con slot/occurrence/date diversi
   * sono linee separate del cart. Stesso prodotto + stessi extras =
   * stessa linea (qty incremented).
   */
  private buildItemSignature(it: {
    product_id: string;
    occurrence_id?: string | null;
    ticket_tier_id?: string | null;
    service_option_id?: string | null;
    service_custom_request?: boolean | null;
    booking_date?: string | null;
    booking_start_time?: string | null;
    booking_end_time?: string | null;
    booking_end_date?: string | null;
    rental_date_from?: string | null;
    rental_date_to?: string | null;
    rental_notes?: string | null;
  }): string {
    return [
      it.product_id,
      it.occurrence_id ?? '',
      it.ticket_tier_id ?? '',
      it.service_option_id ?? '',
      // R4 — una richiesta personalizzata è una riga distinta da uno slot standard
      it.service_custom_request ? 'cr' : '',
      it.booking_date ?? '',
      it.booking_start_time ?? '',
      // B4 — orario/data di fine + note distinguono righe altrimenti fuse
      it.booking_end_time ?? '',
      it.booking_end_date ?? '',
      it.rental_date_from ?? '',
      it.rental_date_to ?? '',
      it.rental_notes ?? '',
    ].join('|');
  }

  /**
   * Public: cambia la quantità di una RIGA del cart (qty=0 rimuove).
   *
   * B4 — il match e' per *signature* di riga (product + slot/occurrence/tier/
   * date/note), non per solo product_id: così due righe dello stesso prodotto
   * con slot diversi restano indipendenti.
   */
  async updateItemQuantity(signature: string, newQty: number): Promise<void> {
    if (!this.ctx.client || !this.cart) return;
    this.syncing = true;
    this.errorMsg = null;
    try {
      const updatedItems = this.cart.items
        .map((it) => {
          if (this.buildItemSignature(it) === signature) {
            return { ...it, quantity: Math.max(0, newQty) };
          }
          return { ...it };
        })
        .filter((it) => it.quantity > 0)
        .map((it) => ({
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
          attendees: it.attendees,
          service_option_id: it.service_option_id,
          extra_selections: it.extra_selections, // R2
        })) satisfies CartItemInput[];

      const updated = await this.ctx.client.embed.cart.update(this.cart.id, {
        items: updatedItems,
      });
      this.cart = updated;
      this.notifyUpdated(updated);
      this._broadcastCartTouch(); // B5 — allinea le altre tab
    } catch (e) {
      this.errorMsg = (e as Error)?.message ?? t('cart.error_update');
    } finally {
      this.syncing = false;
    }
  }

  // ── UI handlers ───────────────────────────────────────────────────────

  /** Public: open/close del drawer. */
  setOpen(value: boolean): void {
    if (this.open === value) return;
    this.open = value;
    this.dispatchEvent(
      new CustomEvent(value ? 'afianco:cart-opened' : 'afianco:cart-closed', {
        bubbles: true,
        composed: true,
      }),
    );
  }

  /** Public: toggle del drawer. */
  toggle(): void {
    this.setOpen(!this.open);
  }

  private _handleAddToCart = (e: Event): void => {
    if (!this._singleton.active) return; // solo il drawer attivo gestisce
    // Track E Step 2.4.7 — payload include opzionalmente `extras` con i
    // campi type-specific dal product-detail drawer.
    const detail = (e as CustomEvent<{
      product: EmbedProductCard;
      quantity: number;
      extras?: Record<string, unknown>;
    }>).detail;
    if (!detail?.product) return;
    void this.addItem(detail);
  };

  private handleCheckoutClick(): void {
    if (!this.cart) return;
    this.dispatchEvent(
      new CustomEvent<{ cart_id: string; cart: CartResponse }>(
        'afianco:checkout-requested',
        {
          detail: { cart_id: this.cart.id, cart: this.cart },
          bubbles: true,
          composed: true,
        },
      ),
    );
    // Track E Step 3.1 — UX fix: il cart drawer si chiude automaticamente
    // quando il customer lancia il checkout. Pre-fix: il drawer cart rimaneva
    // aperto SOPRA il checkout modal (z-index 2001 vs 2000) creando
    // layering confusing. Slight delay (50ms) per permettere all'evento
    // checkout-requested di propagare PRIMA che il context cambi.
    setTimeout(() => this.setOpen(false), 50);
  }

  private notifyUpdated(cart: CartResponse): void {
    this.dispatchEvent(
      new CustomEvent<CartResponse>('afianco:cart-updated', {
        detail: cart,
        bubbles: true,
        composed: true,
      }),
    );
  }

  // ── Helpers ───────────────────────────────────────────────────────────

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

  private get itemCount(): number {
    return this.cart?.item_count ?? 0;
  }

  // ── Render ────────────────────────────────────────────────────────────

  render() {
    // Singleton passivo (un altro cart-drawer e' gia' attivo) → non rende.
    if (!this._singleton.active) return nothing;
    const currency =
      this.cart?.currency_snapshot ?? this.ctx.init?.currency ?? 'EUR';
    const items = this.cart?.items ?? [];

    return html`
      <button
        class="trigger"
        type="button"
        aria-label=${t('cart.open_label')}
        @click=${() => this.toggle()}>
        ${t('cart.trigger_label')}
        ${this.itemCount > 0
          ? html`<span class="badge" aria-label=${t('cart.items_aria_label', { count: this.itemCount })}>
              ${this.itemCount}
            </span>`
          : ''}
      </button>

      <div class="scrim" @click=${() => this.setOpen(false)}></div>

      <aside
        class="drawer"
        role="dialog"
        aria-modal="true"
        aria-label=${t('cart.title')}
        aria-hidden=${!this.open}>
        <header class="drawer-header">
          <h2 class="drawer-title">${t('cart.title')}</h2>
          <button
            class="close-btn"
            type="button"
            aria-label=${t('cart.close_label')}
            @click=${() => this.setOpen(false)}>
            ×
          </button>
        </header>

        <div class="drawer-body">
          ${this.errorMsg
            ? html`<div class="error-banner" role="alert">${this.errorMsg}</div>`
            : ''}
          ${items.length === 0
            ? html`<div class="empty">${t('cart.empty')}</div>`
            : items.map((it) => {
                // B4 — signature di riga: identifica la singola linea (anche
                // due righe stesso prodotto con slot/tier diversi).
                const sig = this.buildItemSignature(it);
                return html`
                  <div class="item" data-product-id=${it.product_id}>
                    <div class="item-info">
                      <p class="item-name">
                        ${it.product_name_snapshot ?? it.product_id}
                      </p>
                      <p class="item-price">
                        ${this.formatPrice(it.unit_price_snapshot, currency)}
                      </p>
                      <div class="qty-controls">
                        <button
                          class="qty-btn"
                          type="button"
                          aria-label=${t('cart.qty_decrease')}
                          ?disabled=${this.syncing}
                          @click=${() =>
                            this.updateItemQuantity(sig, it.quantity - 1)}>
                          −
                        </button>
                        <span class="qty-display">${it.quantity}</span>
                        <button
                          class="qty-btn"
                          type="button"
                          aria-label=${t('cart.qty_increase')}
                          ?disabled=${this.syncing}
                          @click=${() =>
                            this.updateItemQuantity(sig, it.quantity + 1)}>
                          +
                        </button>
                      </div>
                    </div>
                    <button
                      class="remove-btn"
                      type="button"
                      ?disabled=${this.syncing}
                      @click=${() => this.updateItemQuantity(sig, 0)}>
                      ${t('cart.remove')}
                    </button>
                  </div>
                `;
              })}
        </div>

        ${items.length > 0
          ? html`
              <footer class="drawer-footer">
                <div class="subtotal">
                  <span>${t('cart.total')}</span>
                  <span>
                    ${this.formatPrice(
                      this.cart?.subtotal_snapshot ?? 0,
                      currency,
                    )}
                  </span>
                </div>
                <button
                  class="checkout-cta"
                  type="button"
                  ?disabled=${this.syncing || items.length === 0}
                  @click=${() => this.handleCheckoutClick()}>
                  ${t('cart.proceed_checkout')}
                </button>
              </footer>
            `
          : ''}
      </aside>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'afianco-cart-drawer': AfiancoCartDrawer;
  }
  interface HTMLElementEventMap {
    'afianco:cart-updated': CustomEvent<CartResponse>;
    'afianco:cart-opened': CustomEvent;
    'afianco:cart-closed': CustomEvent;
    'afianco:checkout-requested': CustomEvent<{
      cart_id: string;
      cart: CartResponse;
    }>;
  }
}
