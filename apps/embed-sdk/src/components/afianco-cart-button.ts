/**
 * <afianco-cart-button> — Embed à-la-carte, Fase 2.
 *
 * Trigger carrello leggero, pensato per stare nel MENU del sito merchant
 * (a differenza di <afianco-header> che impone un intero layout navbar).
 *
 *   <afianco-cart-button></afianco-cart-button>
 *
 * Funziona ovunque, anche fuori da <afianco-storefront-init>, grazie allo
 * Store Kernel per-slug (StoreConsumerController). Richiede che in pagina
 * ci sia UNA volta <afianco-cart-drawer hide-trigger> (lo snippet generato
 * lo include automaticamente).
 *
 * Architettura: event bus document-level (loose coupling, identico a
 * <afianco-header>):
 *   - click → dispatch ``afianco:open-cart``  (il drawer lo apre)
 *   - ascolta ``afianco:cart-updated``        (aggiorna il badge count)
 */

import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { consume } from '@lit/context';
import { afiancoBaseStyles } from '@afianco/design-tokens';
import { storefrontContext, type StorefrontContext } from '../context.js';
import { StoreConsumerController } from '../store/store-consumer.js';
import { t } from '../i18n/index.js';

@customElement('afianco-cart-button')
export class AfiancoCartButton extends LitElement {
  /** Override slug (multi-store nella stessa pagina). Default: slug di pagina. */
  @property({ type: String, reflect: true })
  store = '';

  @consume({ context: storefrontContext, subscribe: true })
  @state()
  ctx?: StorefrontContext;

  /** Kernel binding standalone (no-op se dentro un provider). */
  protected _store = new StoreConsumerController(this);

  @state()
  private count = 0;

  static styles = [
    afiancoBaseStyles,
    css`
      :host { display: inline-block; }
      .btn {
        position: relative;
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: transparent;
        color: var(--afianco-color-text, #111827);
        border: 1px solid var(--afianco-color-border, #e5e7eb);
        border-radius: 9999px;
        padding: 8px 14px;
        font-family: inherit;
        font-size: 13px;
        font-weight: 500;
        cursor: pointer;
        min-height: 36px;
        transition: background 0.15s ease, border-color 0.15s ease;
      }
      .btn:hover {
        background: var(--afianco-color-muted, #f3f4f6);
        border-color: var(--afianco-color-border-strong, #d1d5db);
      }
      .btn:focus-visible {
        outline: 2px solid var(--afianco-color-primary, #4b72ce);
        outline-offset: 2px;
      }
      .icon { width: 18px; height: 18px; flex-shrink: 0; }
      .badge {
        position: absolute;
        top: -4px;
        right: -4px;
        min-width: 18px;
        height: 18px;
        padding: 0 5px;
        background: var(--afianco-color-primary, #4b72ce);
        color: var(--afianco-color-primary-text, #ffffff);
        border-radius: 9999px;
        font-size: 11px;
        font-weight: 600;
        line-height: 18px;
        text-align: center;
        box-shadow: 0 0 0 2px var(--afianco-color-surface, #ffffff);
      }
    `,
  ];

  connectedCallback(): void {
    super.connectedCallback();
    document.addEventListener('afianco:cart-updated', this._onCartUpdated as EventListener);
    document.addEventListener('afianco:locale-changed', this._onLocaleChanged);
  }

  disconnectedCallback(): void {
    document.removeEventListener('afianco:cart-updated', this._onCartUpdated as EventListener);
    document.removeEventListener('afianco:locale-changed', this._onLocaleChanged);
    super.disconnectedCallback();
  }

  private _onCartUpdated = (e: Event): void => {
    const cart = (e as CustomEvent).detail as { item_count?: number } | undefined;
    this.count = cart?.item_count ?? 0;
  };

  private _onLocaleChanged = (): void => {
    this.requestUpdate();
  };

  private _open(): void {
    document.dispatchEvent(
      new CustomEvent('afianco:open-cart', { bubbles: true, composed: true }),
    );
  }

  render() {
    return html`
      <button
        class="btn"
        type="button"
        aria-label=${this.count > 0
          ? `${t('header.cart')} (${this.count})`
          : t('header.cart_empty_aria')}
        @click=${() => this._open()}>
        <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"
          stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <circle cx="9" cy="21" r="1"></circle>
          <circle cx="20" cy="21" r="1"></circle>
          <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path>
        </svg>
        <span>${t('header.cart')}</span>
        ${this.count > 0 ? html`<span class="badge">${this.count}</span>` : ''}
      </button>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'afianco-cart-button': AfiancoCartButton;
  }
}
