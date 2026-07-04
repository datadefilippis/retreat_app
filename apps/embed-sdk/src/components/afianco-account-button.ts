/**
 * <afianco-account-button> — Embed à-la-carte, Fase 2.
 *
 * Trigger account leggero per il MENU del sito merchant. Gemello di
 * <afianco-cart-button>. Richiede UNA volta in pagina
 * <afianco-account hide-trigger> (incluso auto dallo snippet generato).
 *
 *   <afianco-account-button></afianco-account-button>
 *
 * Event bus document-level:
 *   - click → dispatch ``afianco:open-account``
 *   - ascolta login/signup/logout + storage → aggiorna il pallino auth
 */

import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { consume } from '@lit/context';
import { afiancoBaseStyles } from '@afianco/design-tokens';
import { storefrontContext, type StorefrontContext } from '../context.js';
import { StoreConsumerController } from '../store/store-consumer.js';
import { t } from '../i18n/index.js';

@customElement('afianco-account-button')
export class AfiancoAccountButton extends LitElement {
  /** Override slug (multi-store). Default: slug di pagina. */
  @property({ type: String, reflect: true })
  store = '';

  @consume({ context: storefrontContext, subscribe: true })
  @state()
  ctx?: StorefrontContext;

  protected _store = new StoreConsumerController(this);

  @state()
  private authenticated = false;

  static styles = [
    afiancoBaseStyles,
    css`
      :host { display: inline-block; }
      .btn {
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
      .dot {
        width: 7px; height: 7px; border-radius: 50%;
        background: var(--afianco-color-success, #10b981);
        margin-left: 2px;
      }
    `,
  ];

  connectedCallback(): void {
    super.connectedCallback();
    document.addEventListener('afianco:customer-logged-in', this._onAuthChange);
    document.addEventListener('afianco:customer-signed-up', this._onAuthChange);
    document.addEventListener('afianco:portal-logout', this._onAuthChange);
    document.addEventListener('afianco:locale-changed', this._onAuthChange);
    window.addEventListener('storage', this._onStorage);
    this._evaluate();
  }

  disconnectedCallback(): void {
    document.removeEventListener('afianco:customer-logged-in', this._onAuthChange);
    document.removeEventListener('afianco:customer-signed-up', this._onAuthChange);
    document.removeEventListener('afianco:portal-logout', this._onAuthChange);
    document.removeEventListener('afianco:locale-changed', this._onAuthChange);
    window.removeEventListener('storage', this._onStorage);
    super.disconnectedCallback();
  }

  updated(): void {
    // Quando il kernel diventa ready (client disponibile) ri-valuta l'auth.
    this._evaluate();
  }

  private _onAuthChange = (): void => {
    this._evaluate();
    this.requestUpdate();
  };

  private _onStorage = (e: StorageEvent): void => {
    // B10 — solo la key del proprio slug (multi-store safe).
    if (!e.key) return;
    const slug = this.ctx?.init?.slug ?? this.ctx?.client?.slug;
    const isMine = slug ? e.key === `afianco_token_${slug}` : e.key.startsWith('afianco_token_');
    if (isMine) this._evaluate();
  };

  private _evaluate(): void {
    const token = this.ctx?.client?.tokenStorage?.get?.();
    const next = Boolean(token);
    if (next !== this.authenticated) this.authenticated = next;
  }

  private _open(): void {
    document.dispatchEvent(
      new CustomEvent('afianco:open-account', { bubbles: true, composed: true }),
    );
  }

  render() {
    return html`
      <button
        class="btn"
        type="button"
        aria-label=${this.authenticated
          ? t('account.open_authenticated')
          : t('account.open_guest')}
        @click=${() => this._open()}>
        <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"
          stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
          <circle cx="12" cy="7" r="4"></circle>
        </svg>
        <span>${this.authenticated ? t('header.account_logged') : t('header.account_login')}</span>
        ${this.authenticated ? html`<span class="dot" aria-hidden="true"></span>` : ''}
      </button>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'afianco-account-button': AfiancoAccountButton;
  }
}
