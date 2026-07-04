/**
 * <afianco-product-grid> — Phase 1 Step 24 (Track C).
 *
 * Renderizza una vetrina filterable di prodotti. Batch-fetcha la lista
 * via /embed/products UNA volta (no N+1), poi delega ogni item al
 * componente <afianco-product-card> via property injection (.product),
 * cosicché nessuna card faccia il proprio fetch.
 *
 * Uso tipico:
 *
 *   <afianco-storefront-init slug="acme">
 *     <afianco-product-grid
 *       category="catering"
 *       type="event_ticket"
 *       sort="price_asc"
 *       limit="20"
 *       show-filter-nav>
 *     </afianco-product-grid>
 *   </afianco-storefront-init>
 *
 * Re-fetch automatico quando cambiano gli attributi filter (category/
 * type/sort/limit) — il merchant puo' fare reactive update con JS.
 *
 * Custom events:
 *   - ``afianco:grid-loaded`` (detail: { items, total }) — fetch ok
 *   - ``afianco:grid-error`` (detail: { message }) — fetch fail
 *   - re-emette implicitamente ``afianco:add-to-cart`` dei children
 *     (bubbles), il merchant li listen sul parent del grid.
 *
 * Slots:
 *   - default: vuoto (children sono auto-rendered)
 *   - ``empty``: custom empty state UI
 *   - ``error``: custom error state UI
 */

import { LitElement, html, css, type PropertyValues } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { consume } from '@lit/context';
import { afiancoBaseStyles } from '@afianco/design-tokens';
// W4.9 — i18n wiring
import { t } from '../i18n/index.js';
import type {
  EmbedProductCard,
  EmbedProductsQuery,
  ProductType,
  EmbedProductSortMode,
} from '@afianco/api-client';
import {
  storefrontContext,
  STOREFRONT_INITIAL,
  type StorefrontContext,
} from '../context.js';
import { StoreConsumerController } from '../store/store-consumer.js';

// Side-effect import: garantisce che <afianco-product-card> sia
// registrato nel customElements registry quando il grid lo renderizza
// come child. Senza questo, un consumer che importa solo product-grid
// vedrebbe la card non-renderizzata.
import './afianco-product-card.js';

// Whitelist client-side per i sort mode (mirror del backend).
const SORT_MODES: ReadonlySet<EmbedProductSortMode> = new Set([
  'name',
  'price_asc',
  'price_desc',
  'newest',
]);

// Cap per il limit (allineato col backend max).
const LIMIT_MAX = 100;
const LIMIT_DEFAULT = 20;

@customElement('afianco-product-grid')
export class AfiancoProductGrid extends LitElement {
  /** Filter by category slug (es. "catering"). Empty = no filter. */
  @property({ type: String, reflect: true })
  category = '';

  /** Filter by item_type (es. "event_ticket"). Empty = no filter. */
  @property({ type: String, reflect: true })
  type: ProductType | '' = '';

  /** Sort mode. Default "name". */
  @property({ type: String, reflect: true })
  sort: EmbedProductSortMode = 'name';

  /** Max items per fetch. Capped 1..100. */
  @property({ type: Number, reflect: true })
  limit = LIMIT_DEFAULT;

  /** Pagination offset. */
  @property({ type: Number, reflect: true })
  offset = 0;

  /**
   * Mostra una nav superiore con i bottoni "Tutte" + 1 bottone per
   * ogni categoria pubblicata. Default false (il merchant lo abilita
   * via attribute ``show-filter-nav``).
   */
  @property({ type: Boolean, attribute: 'show-filter-nav', reflect: true })
  showFilterNav = false;

  /**
   * Track E Step 5.1 — Mostra search bar full-text sopra la grid.
   * Backend supporta ?q= via Mongo $text operator (italian stemmer).
   * Debounced 350ms per evitare flood network.
   */
  @property({ type: Boolean, attribute: 'show-search', reflect: true })
  showSearch = false;

  /**
   * Search query corrente. Auto-managed dalla search bar interna
   * quando showSearch=true, ma puo' essere controllata esternamente
   * (es. merchant ha proprio search input + passa via attribute).
   */
  @property({ type: String, reflect: true })
  q = '';

  /** Numero di colonne CSS grid (responsive minmax in CSS). Default 3. */
  @property({ type: Number })
  columns = 3;

  /** Consume context. */
  @consume({ context: storefrontContext, subscribe: true })
  @state()
  ctx: StorefrontContext = STOREFRONT_INITIAL;

  /** À-la-carte: aggancio al kernel se fuori da un provider (no-op se dentro). */
  protected _store = new StoreConsumerController(this);

  /** Items fetched. */
  @state()
  private items: EmbedProductCard[] = [];

  /** Pagination meta from response. */
  @state()
  private total = 0;

  /** Fetching state. */
  @state()
  private fetching = false;

  /** Last fetch error. */
  @state()
  private fetchError: string | null = null;

  /**
   * Hash dell'ultimo set di params usati per il fetch — evita re-fetch
   * inutili quando un attribute cambia ma il filter normalizzato e' uguale.
   */
  @state()
  private lastFetchKey = '';

  static styles = [
    afiancoBaseStyles,
    css`
      :host {
        display: block;
      }
      .filter-nav {
        display: flex;
        flex-wrap: wrap;
        gap: var(--afianco-spacing-sm);
        padding: var(--afianco-spacing-md) 0;
        margin-bottom: var(--afianco-spacing-lg);
        border-bottom: 1px solid var(--afianco-color-border);
      }
      .filter-pill {
        background: transparent;
        color: var(--afianco-color-text-secondary);
        border: 1px solid var(--afianco-color-border);
        border-radius: var(--afianco-radius-pill);
        padding: var(--afianco-spacing-xs) var(--afianco-spacing-md);
        font-family: var(--afianco-font-family);
        font-size: var(--afianco-font-size-sm);
        cursor: pointer;
        transition: all var(--afianco-duration-fast)
          var(--afianco-easing-standard);
      }
      .filter-pill:hover {
        background: var(--afianco-color-surface);
      }
      .filter-pill.active {
        background: var(--afianco-color-primary);
        color: var(--afianco-color-primary-text);
        border-color: var(--afianco-color-primary);
      }
      .pill-count {
        opacity: 0.7;
        margin-left: var(--afianco-spacing-xs);
      }
      .grid {
        display: grid;
        grid-template-columns: repeat(
          auto-fill,
          minmax(min(260px, 100%), 1fr)
        );
        gap: var(--afianco-spacing-lg);
      }
      .skeleton,
      .empty,
      .error {
        padding: var(--afianco-spacing-xxl);
        text-align: center;
        font-size: var(--afianco-font-size-sm);
      }
      .skeleton {
        color: var(--afianco-color-text-muted);
      }
      .empty {
        color: var(--afianco-color-text-muted);
        background: var(--afianco-color-surface);
        border-radius: var(--afianco-radius-lg);
      }
      .error {
        color: var(--afianco-color-danger);
        background: #fff5f5;
        border: 1px solid #fed7d7;
        border-radius: var(--afianco-radius-md);
      }
      .grid-footer {
        text-align: center;
        margin-top: var(--afianco-spacing-xl);
        font-size: var(--afianco-font-size-xs);
        color: var(--afianco-color-text-muted);
      }
    `,
  ];

  // ── Lifecycle ─────────────────────────────────────────────────────────

  /**
   * Tracking se abbiamo gia' kickstartato il fetch iniziale.
   * Evita update-loop dato che fetchItems() muta state che ri-trigger
   * updated() — il guard `started || !filterParamChanged` chiude il loop.
   */
  private _started = false;

  protected updated(changed: PropertyValues): void {
    // Guard 1: niente fetch finche' il context non e' pronto.
    if (this.ctx.status !== 'ready') return;
    // Guard 2: niente fetch concorrente.
    if (this.fetching) return;

    const filterParamChanged =
      changed.has('category') ||
      changed.has('type') ||
      changed.has('sort') ||
      changed.has('limit') ||
      changed.has('offset') ||
      changed.has('q');  // Track E Step 5.1 — search query re-fetch

    // First-time fetch + re-fetch su filter change. Niente trigger su
    // ogni updated() (es. fetching/items state change), così il loop
    // updated → fetch → state change → updated rimane stabile.
    if (!this._started || filterParamChanged) {
      this._started = true;
      void this.fetchItems();
    }
  }

  // ── Fetch ─────────────────────────────────────────────────────────────

  private buildQuery(): EmbedProductsQuery {
    const safeSort = SORT_MODES.has(this.sort as EmbedProductSortMode)
      ? (this.sort as EmbedProductSortMode)
      : 'name';
    // Note: don't use `Number(x) || DEFAULT` here — 0 is falsy and would
    // collapse to default 20. Use explicit Number.isFinite check + clamp.
    const rawLimit = Number(this.limit);
    const baseLimit = Number.isFinite(rawLimit) ? rawLimit : LIMIT_DEFAULT;
    const safeLimit = Math.max(1, Math.min(LIMIT_MAX, baseLimit));
    const safeOffset = Math.max(0, Number(this.offset) || 0);
    const q: EmbedProductsQuery = {
      sort: safeSort,
      limit: safeLimit,
      offset: safeOffset,
    };
    if (this.category) q.category = this.category;
    if (this.type) q.type = this.type as ProductType;
    // Track E Step 5.1 — search query (trim + skip se empty)
    const searchQ = (this.q || '').trim();
    if (searchQ) q.q = searchQ;
    return q;
  }

  /** Stable key per de-dup re-fetch. */
  private queryKey(q: EmbedProductsQuery): string {
    return `${q.category ?? ''}|${q.type ?? ''}|${q.sort}|${q.limit}|${q.offset}|${q.q ?? ''}`;
  }

  /** Fetch items from backend. Safe to call multiple times — has
   * concurrent-fetch guard + filter-key de-dup. */
  async fetchItems(): Promise<void> {
    if (this.ctx.status !== 'ready' || !this.ctx.client) return;
    if (this.fetching) return; // concurrent fetch guard
    const q = this.buildQuery();
    const key = this.queryKey(q);
    if (key === this.lastFetchKey && !this.fetchError) {
      // Identical filter set, no need to re-fetch
      return;
    }
    this.fetching = true;
    this.fetchError = null;
    try {
      const resp = await this.ctx.client.embed.getProducts(q);
      this.items = resp.items;
      this.total = resp.pagination.total;
      this.lastFetchKey = key;
      this.dispatchEvent(
        new CustomEvent('afianco:grid-loaded', {
          detail: { items: resp.items, total: resp.pagination.total },
          bubbles: true,
          composed: true,
        }),
      );
    } catch (e) {
      const msg = (e as Error)?.message ?? 'Fetch failed';
      this.fetchError = msg;
      this.items = [];
      this.total = 0;
      this.dispatchEvent(
        new CustomEvent('afianco:grid-error', {
          detail: { message: msg },
          bubbles: true,
          composed: true,
        }),
      );
    } finally {
      this.fetching = false;
    }
  }

  // ── Filter UI handlers ────────────────────────────────────────────────

  private setCategory(slug: string): void {
    this.category = slug;
    this.offset = 0; // reset to first page on filter change
  }

  render() {
    // Loading bootstrap state from provider.
    if (this.ctx.status === 'loading') {
      return html`<div class="skeleton">Loading storefront&hellip;</div>`;
    }
    if (this.ctx.status === 'error') {
      return html`<div class="error" role="alert">
        Storefront error: ${this.ctx.error ?? 'unknown'}
      </div>`;
    }

    const categories = this.ctx.init?.categories ?? [];
    const showNav = this.showFilterNav && categories.length > 0;

    // Track E Step 5.1 — search bar block (visible solo se showSearch=true)
    const searchBar = this.showSearch
      ? html`
          <div
            class="search-bar"
            style="margin-bottom: 12px; position: relative; max-width: 480px;">
            <input
              type="search"
              placeholder="Cerca prodotti…"
              aria-label="Cerca prodotti"
              .value=${this.q}
              @input=${(e: InputEvent) => this.handleSearchInput(
                (e.target as HTMLInputElement).value,
              )}
              style="
                width: 100%;
                padding: 10px 14px 10px 36px;
                border: 1px solid var(--afianco-color-border, #e5e7eb);
                border-radius: 9999px;
                font-family: inherit;
                font-size: 14px;
                background: var(--afianco-color-bg, #ffffff);
                color: var(--afianco-color-text, #111827);
                box-sizing: border-box;
                outline: none;
              ">
            <span
              aria-hidden="true"
              style="
                position: absolute;
                left: 12px;
                top: 50%;
                transform: translateY(-50%);
                font-size: 16px;
                color: var(--afianco-color-text-secondary, #6b7280);
              ">🔍</span>
          </div>
        `
      : '';

    // Body content
    let bodyContent;
    if (this.fetchError) {
      bodyContent = html`<div class="error" role="alert">${this.fetchError}</div>`;
    } else if (this.fetching && this.items.length === 0) {
      bodyContent = html`<div class="skeleton">Loading products&hellip;</div>`;
    } else if (!this.fetching && this.items.length === 0) {
      bodyContent = html`<div class="empty">${t('product.empty_catalog')}</div>`;
    } else {
      const cards = this.items.map(
        (p) => html`<afianco-product-card .product=${p}></afianco-product-card>`,
      );
      const showFooter = this.total > this.items.length;
      bodyContent = showFooter
        ? html`<div class="grid">${cards}</div><div class="grid-footer">${this.items.length} di ${this.total} mostrati</div>`
        : html`<div class="grid">${cards}</div>`;
    }

    // Inline filter nav (no separate method to avoid nested-template
    // rendering issues observed in happy-dom test env).
    if (showNav) {
      return html`
        ${searchBar}
        <nav class="filter-nav" aria-label="Filter products by category">
          <button
            class=${`filter-pill ${this.category === '' ? 'active' : ''}`}
            type="button"
            aria-pressed=${this.category === ''}
            @click=${() => this.setCategory('')}>
            Tutte
          </button>
          ${categories.map(
            (c) => html`<button
              class=${`filter-pill ${this.category === c.slug ? 'active' : ''}`}
              type="button"
              aria-pressed=${this.category === c.slug}
              @click=${() => this.setCategory(c.slug)}>
              ${c.name}
              <span class="pill-count">(${c.count})</span>
            </button>`,
          )}
        </nav>
        ${bodyContent}
      `;
    }

    // Render: search bar (if enabled) + grid body
    return this.showSearch ? html`${searchBar}${bodyContent}` : bodyContent;
  }

  /**
   * Track E Step 5.1 — Search input handler con debounce 350ms.
   * Aggiorna this.q + resetta offset a 0 + trigger re-fetch.
   */
  private _searchDebounceTimer: ReturnType<typeof setTimeout> | null = null;

  private handleSearchInput(value: string): void {
    this.q = value;
    if (this._searchDebounceTimer) {
      clearTimeout(this._searchDebounceTimer);
    }
    this._searchDebounceTimer = setTimeout(() => {
      this.offset = 0;  // reset pagination al cambio query
      void this.fetchItems();
    }, 350);
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'afianco-product-grid': AfiancoProductGrid;
  }
  interface HTMLElementEventMap {
    'afianco:grid-loaded': CustomEvent<{
      items: EmbedProductCard[];
      total: number;
    }>;
    'afianco:grid-error': CustomEvent<{ message: string }>;
  }
}
