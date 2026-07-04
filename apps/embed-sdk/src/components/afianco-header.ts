/**
 * <afianco-header> — Track E Step 2.4.4 (UX refactor unified navbar).
 *
 * Header sticky/fixed che fornisce un layout ORDINATO per i trigger
 * button dei drawer account + cart. Risolve il bug "FAB sparsi sui
 * prodotti" mettendo i pulsanti in un header coerente con il design
 * di qualsiasi e-commerce moderno.
 *
 * Architettura — loose coupling via document events
 * =================================================
 *
 * Il componente NON contiene logica auth/cart. Si limita a:
 *   1. Renderizzare un header layout (logo space + spacer + actions)
 *   2. Dispatch document events 'afianco:open-account' e 'afianco:open-cart'
 *      al click degli icon button
 *
 * I componenti <afianco-account> e <afianco-cart-drawer> ascoltano questi
 * eventi via document.addEventListener e aprono il loro drawer.
 *
 * Pattern: event bus (pubsub) — header e' producer-only, drawer sono
 * consumer-only. Zero direct reference tra header e drawer (testable,
 * mantenibile, swappabile).
 *
 * Co-existence con i FAB esistenti
 * =================================
 *
 * Quando il merchant include <afianco-header>, i drawer companion devono
 * avere attributo `hide-trigger`:
 *
 *   <afianco-header></afianco-header>
 *   <afianco-account hide-trigger></afianco-account>
 *   <afianco-cart-drawer hide-trigger></afianco-cart-drawer>
 *
 * Senza `hide-trigger` i drawer mostrano ancora il loro FAB → 2 trigger
 * button visibili → duplicazione UX. Lo snippet generato dal backend
 * (embed_distribution.py) e' coordinato per emettere insieme header +
 * hide-trigger.
 *
 * Attributi
 * =========
 *
 *   - `sticky` (boolean, default true)
 *       position: sticky vs static. Sticky e' il pattern standard
 *       e-commerce moderno (sempre accessibile durante scroll).
 *
 *   - `store-name` (string, optional)
 *       Mostrato a sinistra come brand label. Se vuoto, mostra solo
 *       lo spacer (giusto le icon a destra). In produzione, lo store
 *       name puo' essere letto dal context (init.org_name) — vedi
 *       evoluzione futura.
 *
 *   - `hide-account` / `hide-cart` (boolean, default false)
 *       Permette di nascondere singoli trigger se il merchant vuole
 *       solo cart (es. store senza customer auth) o solo account
 *       (es. SaaS senza shopping cart).
 *
 * Custom events emessi
 * ====================
 *
 *   - `afianco:open-account` (no detail)
 *   - `afianco:open-cart` (no detail)
 *
 * Accessibility
 * =============
 *
 *   - role="banner" sul host (landmark ARIA)
 *   - aria-label localizzato sui button
 *   - Tastiera: tab navigation funziona naturalmente (button HTML)
 */

import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { consume } from '@lit/context';
import { afiancoBaseStyles } from '@afianco/design-tokens';
import { storefrontContext, type StorefrontContext } from '../context.js';
import { StoreConsumerController } from '../store/store-consumer.js';
// Track E Step 4.5 — language switcher (i18n)
import './afianco-language-switcher.js';
import { t } from '../i18n/index.js';


@customElement('afianco-header')
export class AfiancoHeader extends LitElement {
  // ── Context consumption (per leggere store name + auth state) ────────

  @consume({ context: storefrontContext, subscribe: true })
  @state()
  private ctx?: StorefrontContext;

  /** À-la-carte: aggancio al kernel se fuori da un provider (no-op se dentro). */
  protected _store = new StoreConsumerController(this);

  // ── Public attributes ────────────────────────────────────────────────

  /** Sticky positioning. Default true (e-commerce standard). */
  @property({ type: Boolean, reflect: true })
  sticky = true;

  /**
   * Override del nome store da mostrare a sinistra. Se vuoto, il
   * componente legge `ctx.init.store_info.display_name`. Se anche
   * quello manca, header mostra solo lo spacer + icone a destra.
   */
  @property({ type: String, attribute: 'store-name' })
  storeName = '';

  /** Nascondi singolo trigger account (per store senza auth). */
  @property({ type: Boolean, attribute: 'hide-account', reflect: true })
  hideAccount = false;

  /** Nascondi singolo trigger cart (per store SaaS senza shop). */
  @property({ type: Boolean, attribute: 'hide-cart', reflect: true })
  hideCart = false;

  // ── Internal: cart item count + auth state (per badge UI) ────────────

  @state()
  private cartItemCount = 0;

  @state()
  private authenticated = false;

  // ── Lifecycle ────────────────────────────────────────────────────────

  connectedCallback(): void {
    super.connectedCallback();
    // Listen cart updates per aggiornare il badge count
    document.addEventListener('afianco:cart-updated', this.handleCartUpdated as EventListener);
    // Listen auth state changes per aggiornare l'icon dot
    document.addEventListener('afianco:customer-logged-in', this.handleAuthChange as EventListener);
    document.addEventListener('afianco:customer-signed-up', this.handleAuthChange as EventListener);
    document.addEventListener('afianco:portal-logout', this.handleAuthChange as EventListener);
    window.addEventListener('storage', this.handleStorageEvent);
    // Track E Step 4.5 — re-render al cambio locale per aggiornare label
    document.addEventListener('afianco:locale-changed', this.handleLocaleChanged);
    this.evaluateAuthState();
  }

  disconnectedCallback(): void {
    document.removeEventListener('afianco:cart-updated', this.handleCartUpdated as EventListener);
    document.removeEventListener('afianco:customer-logged-in', this.handleAuthChange as EventListener);
    document.removeEventListener('afianco:customer-signed-up', this.handleAuthChange as EventListener);
    document.removeEventListener('afianco:portal-logout', this.handleAuthChange as EventListener);
    window.removeEventListener('storage', this.handleStorageEvent);
    document.removeEventListener('afianco:locale-changed', this.handleLocaleChanged);
    super.disconnectedCallback();
  }

  /** Track E Step 4.5 — trigger re-render quando il locale cambia. */
  private handleLocaleChanged = (): void => {
    this.requestUpdate();
  };

  // ── State sync handlers ──────────────────────────────────────────────

  private handleCartUpdated = (e: CustomEvent): void => {
    const cart = e.detail as { item_count?: number } | undefined;
    this.cartItemCount = cart?.item_count ?? 0;
  };

  private handleAuthChange = (): void => {
    this.evaluateAuthState();
  };

  private handleStorageEvent = (e: StorageEvent): void => {
    // B10 — solo la key del proprio slug (multi-store safe).
    if (!e.key) return;
    const slug = this.ctx?.init?.slug ?? this.ctx?.client?.slug;
    const isMine = slug ? e.key === `afianco_token_${slug}` : e.key.startsWith('afianco_token_');
    if (isMine) {
      this.evaluateAuthState();
    }
  };

  private evaluateAuthState(): void {
    const client = this.ctx?.client;
    if (!client) {
      this.authenticated = false;
      return;
    }
    const token = client.tokenStorage?.get();
    this.authenticated = Boolean(token);
  }

  // ── Trigger handlers ─────────────────────────────────────────────────

  private dispatchOpenAccount(): void {
    document.dispatchEvent(
      new CustomEvent('afianco:open-account', { bubbles: true, composed: true }),
    );
  }

  private dispatchOpenCart(): void {
    document.dispatchEvent(
      new CustomEvent('afianco:open-cart', { bubbles: true, composed: true }),
    );
  }

  // ── Derived values ───────────────────────────────────────────────────

  private get displayStoreName(): string {
    if (this.storeName) return this.storeName;
    // Fall back al context (server-derived display name)
    return this.ctx?.init?.store_info?.display_name ?? '';
  }

  /**
   * Sprint 2 W2.5 — Logo URL display (parity React storefront header).
   *
   * Source priority:
   *   1. context init.store_info.logo_url (resolved server-side branding)
   *   2. null → render text-only fallback
   *
   * UX semantica: logo + store_name affiancati come React
   * StorefrontHeader.js. Se logo missing, mostra solo testo (no broken
   * img). Se entrambi missing, header e' senza brand block.
   */
  private get displayLogoUrl(): string | null {
    return this.ctx?.init?.store_info?.logo_url ?? null;
  }

  // ── Render ───────────────────────────────────────────────────────────

  static styles = [
    afiancoBaseStyles,
    css`
      :host {
        display: block;
        /* Reset eventuali bordi/padding del parent merchant container */
        box-sizing: border-box;
        width: 100%;
        background: var(--afianco-color-surface, #ffffff);
        border-bottom: 1px solid var(--afianco-color-border, #e5e7eb);
        z-index: 100;
      }
      :host([sticky]) {
        position: sticky;
        top: 0;
      }

      .header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
        padding: 12px 20px;
        max-width: 100%;
        font-family: var(--afianco-font-body, system-ui, -apple-system, sans-serif);
      }

      .brand {
        display: flex;
        align-items: center;
        gap: 10px;
        min-width: 0;
        flex: 1;
      }
      /* Sprint 2 W2.5 — Logo display (parity React StorefrontHeader). */
      .brand-logo {
        display: block;
        height: 36px;
        width: auto;
        max-width: 140px;
        object-fit: contain;
        flex-shrink: 0;
      }
      .brand-name {
        font-size: 15px;
        font-weight: 600;
        color: var(--afianco-color-text, #111827);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }

      .actions {
        display: flex;
        align-items: center;
        gap: 8px;
        flex-shrink: 0;
      }

      /* Track E Step 4.3 — custom nav links (Phase 8) */
      .custom-nav {
        display: flex;
        align-items: center;
        gap: 16px;
        flex: 1;
        justify-content: center;
      }
      .nav-link {
        font-size: 13px;
        font-weight: 500;
        color: var(--afianco-color-text-secondary, #6b7280);
        text-decoration: none;
        transition: color 0.15s ease;
        white-space: nowrap;
      }
      .nav-link:hover {
        color: var(--afianco-color-primary, #4b72ce);
      }
      @media (max-width: 720px) {
        .custom-nav {
          display: none;
        }
      }

      /* ── Icon trigger button (account + cart hanno stesso pattern) ── */
      .icon-btn {
        position: relative;
        display: inline-flex;
        align-items: center;
        justify-content: center;
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
        transition: background 0.15s ease, border-color 0.15s ease;
        min-height: 36px;
      }
      .icon-btn:hover {
        background: var(--afianco-color-muted, #f3f4f6);
        border-color: var(--afianco-color-border-strong, #d1d5db);
      }
      .icon-btn:focus-visible {
        outline: 2px solid var(--afianco-color-primary, #4b72ce);
        outline-offset: 2px;
      }
      .icon-btn[aria-pressed='true'] {
        background: var(--afianco-color-muted, #f3f4f6);
      }

      .icon-svg {
        width: 18px;
        height: 18px;
        flex-shrink: 0;
      }

      .label {
        white-space: nowrap;
      }

      /* Auth state dot (green when logged-in) */
      .auth-dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background: var(--afianco-color-success, #10b981);
        margin-left: 2px;
      }

      /* Cart badge (item count) */
      .cart-badge {
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

      /* ── Responsive: mobile compact (hide labels, show only icons) ── */
      @media (max-width: 480px) {
        .header {
          padding: 10px 14px;
        }
        .label {
          display: none;
        }
        .icon-btn {
          padding: 8px 10px;
          min-width: 36px;
        }
      }
    `,
  ];

  render() {
    const storeName = this.displayStoreName;
    const logoUrl = this.displayLogoUrl;
    // Track E Step 4.3 — custom nav links da admin Phase 8
    const navLinks = this.ctx?.init?.custom_nav_links ?? [];

    return html`
      <div class="header" role="banner">
        <div class="brand">
          ${/* Sprint 2 W2.5 — Logo display (parity React StorefrontHeader).
              Mostra <img> quando logo_url e' configurato dal merchant.
              Fall-back: solo testo. Entrambi mancanti: brand vuoto. */ ''}
          ${logoUrl
            ? html`<img
                class="brand-logo"
                src=${logoUrl}
                alt=${storeName || 'Logo'}
                loading="lazy"
                @error=${(e: Event) => {
                  // Hide broken logo gracefully (CDN down / wrong URL)
                  const img = e.target as HTMLImageElement;
                  img.style.display = 'none';
                }}>`
            : ''}
          ${storeName
            ? html`<span class="brand-name">${storeName}</span>`
            : ''}
        </div>

        ${navLinks.length > 0
          ? html`
              <nav class="custom-nav" aria-label="Navigazione store">
                ${navLinks.map((link) => html`
                  <a
                    class="nav-link"
                    href=${link.url}
                    target=${link.external ? '_blank' : '_self'}
                    rel=${link.external ? 'noopener noreferrer' : ''}>
                    ${link.label}
                  </a>
                `)}
              </nav>
            `
          : ''}

        <div class="actions">
          <!-- Track E Step 4.5 — Language switcher (auto-hide se solo 1 lingua) -->
          <afianco-language-switcher variant="compact"></afianco-language-switcher>
          ${this.hideAccount
            ? ''
            : html`
                <button
                  class="icon-btn"
                  type="button"
                  aria-label=${this.authenticated ? t('account.open_authenticated') : t('account.open_guest')}
                  @click=${() => this.dispatchOpenAccount()}>
                  <svg
                    class="icon-svg"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    aria-hidden="true">
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                    <circle cx="12" cy="7" r="4"></circle>
                  </svg>
                  <span class="label">
                    ${this.authenticated ? t('header.account_logged') : t('header.account_login')}
                  </span>
                  ${this.authenticated
                    ? html`<span class="auth-dot" aria-hidden="true"></span>`
                    : ''}
                </button>
              `}
          ${this.hideCart
            ? ''
            : html`
                <button
                  class="icon-btn"
                  type="button"
                  aria-label=${this.cartItemCount > 0
                    ? `${t('header.cart')} (${this.cartItemCount})`
                    : t('header.cart_empty_aria')}
                  @click=${() => this.dispatchOpenCart()}>
                  <svg
                    class="icon-svg"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    aria-hidden="true">
                    <circle cx="9" cy="21" r="1"></circle>
                    <circle cx="20" cy="21" r="1"></circle>
                    <path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path>
                  </svg>
                  <span class="label">${t('header.cart')}</span>
                  ${this.cartItemCount > 0
                    ? html`<span class="cart-badge">${this.cartItemCount}</span>`
                    : ''}
                </button>
              `}
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'afianco-header': AfiancoHeader;
  }
  interface HTMLElementEventMap {
    'afianco:open-account': CustomEvent;
    'afianco:open-cart': CustomEvent;
  }
}
