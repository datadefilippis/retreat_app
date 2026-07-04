/**
 * <afianco-product> — Embed à-la-carte, Fase 2.
 *
 * Renderizza UN SINGOLO prodotto inline in una pagina (caso d'uso
 * "pagina prodotto dedicata"):
 *
 *   <afianco-product product-id="abc123"></afianco-product>
 *
 * Fetcha il prodotto via ``client.embed.getProduct(id)`` e lo renderizza
 * riusando <afianco-product-card> (stesso look + CTA add-to-cart + apertura
 * del drawer dettaglio al click). Funziona ovunque grazie allo Store Kernel
 * per-slug (StoreConsumerController). Richiede in pagina una volta
 * <afianco-cart-drawer hide-trigger> (per l'add-to-cart) e
 * <afianco-product-detail> (per il drawer dettaglio) — inclusi auto dallo
 * snippet generato.
 */

import { LitElement, html, css, type PropertyValues } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { consume } from '@lit/context';
import { afiancoBaseStyles } from '@afianco/design-tokens';
import type { EmbedProductDetail } from '@afianco/api-client';
import {
  storefrontContext,
  STOREFRONT_INITIAL,
  type StorefrontContext,
} from '../context.js';
import { StoreConsumerController } from '../store/store-consumer.js';
import { t } from '../i18n/index.js';

// Side-effect: registra <afianco-product-card> nel registry.
import './afianco-product-card.js';

@customElement('afianco-product')
export class AfiancoProduct extends LitElement {
  /** Id del prodotto da mostrare (required). */
  @property({ type: String, attribute: 'product-id', reflect: true })
  productId = '';

  /** Override slug (multi-store). Default: slug di pagina. */
  @property({ type: String, reflect: true })
  store = '';

  @consume({ context: storefrontContext, subscribe: true })
  @state()
  ctx: StorefrontContext = STOREFRONT_INITIAL;

  protected _store = new StoreConsumerController(this);

  @state()
  private product: EmbedProductDetail | null = null;

  @state()
  private loading = false;

  @state()
  private error: string | null = null;

  /** Guard anti re-fetch: chiave (status+productId) gia' fetchata. */
  private _fetchedKey = '';

  static styles = [
    afiancoBaseStyles,
    css`
      :host { display: block; max-width: 420px; }
      .state {
        padding: var(--afianco-spacing-lg, 16px);
        text-align: center;
        font-size: 14px;
        color: var(--afianco-color-text-muted, #6b7280);
      }
      .error {
        color: var(--afianco-color-danger, #dc2626);
        background: #fff5f5;
        border: 1px solid #fed7d7;
        border-radius: 8px;
      }
    `,
  ];

  protected updated(_changed: PropertyValues): void {
    if (this.ctx.status !== 'ready' || !this.ctx.client) return;
    if (!this.productId) return;
    const key = `${this.productId}`;
    if (key === this._fetchedKey) return;
    this._fetchedKey = key;
    void this._fetch();
  }

  private async _fetch(): Promise<void> {
    if (!this.ctx.client) return;
    this.loading = true;
    this.error = null;
    try {
      this.product = await this.ctx.client.embed.getProduct(this.productId);
    } catch (e) {
      this.product = null;
      this.error = (e as Error)?.message ?? 'Fetch failed';
      this._fetchedKey = ''; // consenti retry su cambio stato
    } finally {
      this.loading = false;
    }
  }

  render() {
    if (!this.productId) {
      return html`<div class="state error">Manca l'attributo product-id.</div>`;
    }
    if (this.ctx.status === 'error') {
      return html`<div class="state error">${this.ctx.error ?? 'errore storefront'}</div>`;
    }
    if (this.error) {
      return html`<div class="state error">${this.error}</div>`;
    }
    if (this.loading || !this.product) {
      return html`<div class="state">${t('product.loading', { defaultValue: 'Caricamento…' })}</div>`;
    }
    return html`<afianco-product-card .product=${this.product}></afianco-product-card>`;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'afianco-product': AfiancoProduct;
  }
}
