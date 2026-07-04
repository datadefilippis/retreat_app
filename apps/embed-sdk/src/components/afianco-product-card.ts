/**
 * <afianco-product-card> — Phase 1 Step 23 (Track C).
 *
 * Singolo prodotto card: image + name + description + price + CTA
 * type-aware. Primo component "consumer" del context, dimostra il
 * pattern @consume(storefrontContext) + branding inheritance via CSS
 * + add-to-cart event dispatch al parent.
 *
 * 2 modalità d'uso:
 *
 *   1) Standalone (fetch da product-id):
 *      <afianco-storefront-init slug="acme">
 *        <afianco-product-card product-id="p-123"></afianco-product-card>
 *      </afianco-storefront-init>
 *
 *   2) Pre-loaded (product injected by parent, es. da product-grid):
 *      <afianco-product-card .product=${productCardObject}></afianco-product-card>
 *
 * Custom events:
 *   - ``afianco:add-to-cart`` (detail: { product, quantity }) — emesso al
 *     click sul CTA. Il <afianco-cart-drawer> (Step 25) listen e fa fetch.
 *     bubbles+composed → merchant può listen su window se serve.
 *
 * Attributes:
 *   - ``product-id`` (string) — required se ``product`` property non set
 *   - ``quantity`` (number, default 1) — quanti pezzi al click "Add to cart"
 *
 * Type-aware CTA:
 *   transaction_mode === "request"  → "Richiedi info"
 *   transaction_mode === "approval" → "Richiedi noleggio"
 *   transaction_mode === "direct"   → "Aggiungi al carrello"
 *   price_mode === "inquiry"        → "Richiedi preventivo" (override)
 */

import { LitElement, html, css, nothing, type PropertyValues } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { consume } from '@lit/context';
import { afiancoBaseStyles } from '@afianco/design-tokens';
// W4.8 — i18n CTA labels
import { t } from '../i18n/index.js';
import type {
  EmbedProductCard,
} from '@afianco/api-client';
import {
  storefrontContext,
  STOREFRONT_INITIAL,
  type StorefrontContext,
} from '../context.js';

@customElement('afianco-product-card')
export class AfiancoProductCard extends LitElement {
  /**
   * Pre-loaded product (preferred when parent has the data, es. product-grid).
   * Quando set, il component NON fa fetch.
   */
  @property({ type: Object, attribute: false })
  product: EmbedProductCard | null = null;

  /**
   * Fallback: product-id da usare per fetch da context.client.embed.getProducts().
   * Ignored se ``product`` property è set.
   */
  @property({ type: String, attribute: 'product-id' })
  productId = '';

  /**
   * Quantity al click "Add to cart". Default 1.
   */
  @property({ type: Number })
  quantity = 1;

  /**
   * Consume the storefront context (provided by <afianco-storefront-init>).
   * Subscribe true → re-renders quando il context cambia (es. status
   * passa da loading a ready).
   */
  @consume({ context: storefrontContext, subscribe: true })
  @state()
  ctx: StorefrontContext = STOREFRONT_INITIAL;

  /** Local fetched product (when product-id mode and ctx ready). */
  @state()
  private resolvedProduct: EmbedProductCard | null = null;

  /** Last error message dalla fetch. */
  @state()
  private fetchError: string | null = null;

  static styles = [
    afiancoBaseStyles,
    css`
      :host {
        display: block;
        max-width: 320px;
      }
      .card {
        background: var(--afianco-color-bg);
        border: 1px solid var(--afianco-color-border);
        border-radius: var(--afianco-radius-lg);
        overflow: hidden;
        box-shadow: var(--afianco-shadow-sm);
        transition: box-shadow var(--afianco-duration-normal)
          var(--afianco-easing-standard);
      }
      .card:hover {
        box-shadow: var(--afianco-shadow-md);
      }
      .image-wrap {
        background: var(--afianco-color-surface);
        aspect-ratio: 4 / 3;
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
      }
      .image-wrap img {
        width: 100%;
        height: 100%;
        object-fit: cover;
      }
      .image-placeholder {
        color: var(--afianco-color-text-muted);
        font-size: var(--afianco-font-size-xs);
      }
      .body {
        padding: var(--afianco-spacing-lg);
        display: flex;
        flex-direction: column;
        gap: var(--afianco-spacing-sm);
      }
      .category {
        font-size: var(--afianco-font-size-xs);
        color: var(--afianco-color-text-muted);
        text-transform: uppercase;
        letter-spacing: 0.04em;
      }
      .name {
        margin: 0;
        font-size: var(--afianco-font-size-lg);
        font-weight: var(--afianco-font-weight-bold);
        line-height: var(--afianco-line-height-tight);
        color: var(--afianco-color-text-primary);
      }
      .description {
        margin: 0;
        font-size: var(--afianco-font-size-sm);
        color: var(--afianco-color-text-secondary);
        display: -webkit-box;
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
        overflow: hidden;
      }
      .price {
        font-size: var(--afianco-font-size-lg);
        font-weight: var(--afianco-font-weight-bold);
        color: var(--afianco-color-text-primary);
      }
      .price-inquiry {
        font-size: var(--afianco-font-size-sm);
        color: var(--afianco-color-text-muted);
        font-style: italic;
      }
      .cta {
        background: var(--afianco-color-primary);
        color: var(--afianco-color-primary-text);
        border: none;
        border-radius: var(--afianco-radius-md);
        padding: var(--afianco-spacing-md) var(--afianco-spacing-lg);
        font-family: var(--afianco-font-family);
        font-size: var(--afianco-font-size-md);
        font-weight: var(--afianco-font-weight-medium);
        cursor: pointer;
        transition: opacity var(--afianco-duration-fast)
          var(--afianco-easing-standard);
        margin-top: var(--afianco-spacing-sm);
      }
      .cta:hover:not(:disabled) {
        opacity: 0.92;
      }
      .cta:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }
      .meta {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: var(--afianco-spacing-sm);
      }
      .stock-warning {
        font-size: var(--afianco-font-size-xs);
        color: var(--afianco-color-warning);
        font-weight: var(--afianco-font-weight-medium);
      }
      .skeleton {
        padding: var(--afianco-spacing-xl);
        text-align: center;
        color: var(--afianco-color-text-muted);
        font-size: var(--afianco-font-size-sm);
      }
      .error {
        padding: var(--afianco-spacing-md);
        background: #fff5f5;
        border: 1px solid #fed7d7;
        border-radius: var(--afianco-radius-md);
        color: var(--afianco-color-danger);
        font-size: var(--afianco-font-size-sm);
      }
    `,
  ];

  // ── Lifecycle ─────────────────────────────────────────────────────────

  protected updated(changed: PropertyValues): void {
    // Quando il context diventa ready o il productId cambia, re-fetch
    // se siamo in "fetch by id" mode.
    if (changed.has('ctx') || changed.has('productId') || changed.has('product')) {
      this.maybeFetchProduct();
    }
  }

  private async maybeFetchProduct(): Promise<void> {
    // 1) Se `product` property è injected, niente fetch.
    if (this.product) return;
    // 2) Se non c'è productId, niente fetch (warning state).
    if (!this.productId) return;
    // 3) Context deve essere ready (client disponibile).
    if (this.ctx.status !== 'ready' || !this.ctx.client) return;
    // 4) Già risolto questo productId → skip.
    if (this.resolvedProduct && this.resolvedProduct.id === this.productId) return;

    this.fetchError = null;

    try {
      // Per V1: fetch lista prodotti + filter client-side. Per V2 sarebbe
      // meglio un endpoint dedicato /embed/products/{slug}/{id} (Step 14b).
      const resp = await this.ctx.client.embed.getProducts({ limit: 100 });
      const found = resp.items.find((p) => p.id === this.productId);
      this.resolvedProduct = found ?? null;
      if (!found) {
        this.fetchError = `Product "${this.productId}" not found.`;
      }
    } catch (e) {
      this.fetchError = (e as Error)?.message ?? 'Fetch failed';
      this.resolvedProduct = null;
    }
  }

  // ── Helpers ───────────────────────────────────────────────────────────

  /** Resolved product: property injected OR fetched. */
  private get activeProduct(): EmbedProductCard | null {
    return this.product ?? this.resolvedProduct;
  }

  /**
   * Format price using Intl.NumberFormat — locale-aware.
   * Returns "—" if price not set (inquiry mode).
   */
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

  /**
   * Type-aware CTA label.
   *
   * Track E Step 2.4.5 — CTA labels semplificate "Scopri" / "Dettagli"
   * perche' il click adesso apre il drawer detail (no direct-to-cart).
   * Le label "Aggiungi al carrello" / "Acquista biglietto" / etc.
   * sono spostate nel detail drawer dove l'azione e' davvero finale.
   *
   * UX: customer vede card → click → drawer detail (description full +
   * qty + extras type-specific) → click CTA detail → add-to-cart reale.
   */
  private ctaLabel(_p: EmbedProductCard): string {
    // W4.8 — Click su card apre drawer detail (no direct-to-cart),
    // quindi CTA card e' sempre 'Scopri di piu'' (i18n resolved at render).
    return t('product.cta_discover');
  }

  /** Disabled state: out-of-stock (stock_quantity 0). */
  private get isDisabled(): boolean {
    const p = this.activeProduct;
    if (!p) return true;
    return p.stock_quantity === 0;
  }

  /** Stock warning copy (W4.9 — i18n). */
  private stockHint(p: EmbedProductCard): string | null {
    if (p.stock_quantity == null) return null;
    if (p.stock_quantity === 0) return t('product.out_of_stock');
    if (p.stock_quantity <= 3) return t('product.limited_stock', { count: p.stock_quantity });
    return null;
  }

  // ── Click handlers ────────────────────────────────────────────────────

  /**
   * Track E Step 2.4.5 — CLICK BEHAVIOR CHANGE.
   *
   * Pre-2.4.5: click sul CTA → emette `afianco:add-to-cart` (direct add).
   * Post-2.4.5: click sulla card o sul CTA → emette
   * `afianco:product-view-requested` → apre <afianco-product-detail>
   * drawer. Il drawer poi gestisce qty + CTA finale che emette
   * `afianco:add-to-cart`.
   *
   * Razionale: standard e-commerce (Shopify, Amazon, Stripe Checkout) →
   * landing page detail per ogni prodotto prima dell'add-to-cart. Da li
   * il customer puo' leggere description full, selezionare opzioni
   * type-specific (calendar/tier/date in v2), choose quantity.
   *
   * Backward compat: se nessun <afianco-product-detail> e' presente
   * nel DOM (merchant snippet legacy senza detail), il browser emette
   * l'evento ma nessuno lo ascolta. Per evitare "click silenzioso",
   * il merchant DEVE includere <afianco-product-detail> nello snippet.
   * Il backend ``embed_distribution.generate_embed_snippet()`` lo fa
   * automaticamente dal E2.4.5.
   */
  private handleViewRequest(): void {
    const p = this.activeProduct;
    if (!p || this.isDisabled) return;
    this.dispatchEvent(
      new CustomEvent<{
        product_id: string;
        product: EmbedProductCard;
      }>('afianco:product-view-requested', {
        detail: {
          product_id: p.id,
          product: p,
        },
        bubbles: true,
        composed: true,
      }),
    );
  }

  /** Alias mantenuto per backward compat (Lit template ref). */
  private handleCtaClick(): void {
    this.handleViewRequest();
  }

  // ── Render ────────────────────────────────────────────────────────────

  render() {
    const p = this.activeProduct;

    // Decisione importante: se abbiamo gia' il prodotto, renderizziamo
    // SUBITO ignorando il loading state del context. Questo permette al
    // parent (es. afianco-product-grid) di iniettare ``.product`` senza
    // dover aspettare che storefront-init completi il fetch /embed/init.
    if (p) {
      return this.renderCard(p);
    }

    // Nessun product caricato → controlla i vari stati di fallback.
    if (this.fetchError) {
      return html`<div class="error" role="alert">${this.fetchError}</div>`;
    }

    if (this.ctx.status === 'error') {
      return html`<div class="error" role="alert">
        Storefront error: ${this.ctx.error ?? 'unknown'}
      </div>`;
    }

    if (!this.productId) {
      return html`<div class="error" role="alert">
        Missing <code>product-id</code> attribute or <code>product</code> property.
      </div>`;
    }

    // Loading (context ancora non ready, o fetch by id in volo)
    return html`<div class="skeleton">Loading product&hellip;</div>`;
  }

  private renderCard(p: EmbedProductCard) {

    const currency =
      p.currency || this.ctx.init?.currency || 'EUR';
    const stockHint = this.stockHint(p);

    // Track E Step 2.4.5 — l'intera card e' un click target che apre il
    // detail drawer (UX standard e-commerce: card click → product page).
    return html`
      <article
        class="card"
        aria-labelledby="product-name-${p.id}"
        @click=${(e: Event) => {
          // Evita doppio dispatch se il click viene dal CTA button
          // (che gia' chiama handleCtaClick) o da link/button interni
          const target = e.target as HTMLElement;
          if (target.closest('button, a, input')) return;
          this.handleViewRequest();
        }}
        @keydown=${(e: KeyboardEvent) => {
          if (e.key === 'Enter' || e.key === ' ') {
            const target = e.target as HTMLElement;
            if (target.closest('button, a, input')) return;
            e.preventDefault();
            this.handleViewRequest();
          }
        }}
        tabindex="0"
        role="button"
        style="cursor: pointer;">
        <div class="image-wrap">
          ${p.image_url
            ? html`<img src=${p.image_url} alt=${p.name} loading="lazy">`
            : html`<span class="image-placeholder">No image</span>`}
        </div>
        <div class="body">
          ${p.category
            ? html`<div class="category">${p.category}</div>`
            : nothing}
          <h3 class="name" id=${`product-name-${p.id}`}>${p.name}</h3>
          ${p.description
            ? html`<p class="description">${p.description}</p>`
            : nothing}
          <div class="meta">
            ${p.price_mode === 'inquiry'
              ? html`<span class="price-inquiry">Su richiesta</span>`
              : html`<span class="price">
                  ${this.formatPrice(p.unit_price, currency)}
                  ${p.unit_label
                    ? html`<small style="opacity:0.6; font-weight:normal">/ ${p.unit_label}</small>`
                    : nothing}
                </span>`}
            ${stockHint
              ? html`<span class="stock-warning">${stockHint}</span>`
              : nothing}
          </div>
          <button
            class="cta"
            type="button"
            ?disabled=${this.isDisabled}
            @click=${this.handleCtaClick}
            aria-label=${`${this.ctaLabel(p)} — ${p.name}`}>
            ${this.ctaLabel(p)}
          </button>
        </div>
      </article>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'afianco-product-card': AfiancoProductCard;
  }
  interface HTMLElementEventMap {
    'afianco:add-to-cart': CustomEvent<{
      product: EmbedProductCard;
      quantity: number;
    }>;
  }
}
