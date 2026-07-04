/**
 * <afianco-account> — Track E Step 2.4.2 (full embedding 360).
 *
 * Componente unificato che gestisce l'intera UX customer auth:
 *   - Pulsante account (icon person) floating top-right
 *   - Click apre drawer/sheet con contenuto conditional:
 *       · Customer NON autenticato → tabs Login / Registrazione
 *       · Customer autenticato → portal area (profilo + ordini)
 *
 * Composito di componenti esistenti — NO duplicazione logica auth:
 *   <afianco-login>, <afianco-signup>, <afianco-customer-portal>
 *
 * Pattern allineato a <afianco-cart-drawer>: floating button + scrim +
 * slide-in drawer. Cart drawer = basso destra, Account drawer = alto destra.
 *
 * Custom events emessi:
 *   - `afianco:account-opened` (detail: { authenticated: bool })
 *   - `afianco:account-closed`
 *
 * Custom events consumati (delegated dai children):
 *   - `afianco:customer-logged-in` → switch view a portal
 *   - `afianco:customer-signed-up` → switch view a portal
 *   - `afianco:portal-logout` → switch view a login tab
 *
 * Auth state detection: legge tokenStorage del client (singleton per slug).
 * Re-evaluation on storage events + custom events.
 *
 * Uso (default snippet E2.4.2):
 *
 *   <afianco-storefront-init slug="mio-store">
 *     <afianco-account></afianco-account>
 *     <afianco-product-grid></afianco-product-grid>
 *     <afianco-cart-drawer></afianco-cart-drawer>
 *     <afianco-checkout-button></afianco-checkout-button>
 *   </afianco-storefront-init>
 */

import { LitElement, html, css, nothing, type PropertyValues } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { consume } from '@lit/context';
import { afiancoBaseStyles } from '@afianco/design-tokens';
import { storefrontContext, type StorefrontContext } from '../context.js';
import { StoreConsumerController } from '../store/store-consumer.js';
import { SingletonController } from '../store/singleton-guard.js';
// Sprint 4 W4.7 — i18n wiring
import { t } from '../i18n/index.js';

// Import sibling components per garantire registrazione (side-effect):
import './afianco-login.js';
import './afianco-signup.js';
import './afianco-customer-portal.js';


type AccountView = 'login' | 'signup' | 'portal' | 'forgot';


@customElement('afianco-account')
export class AfiancoAccount extends LitElement {
  // ── Context consumption ─────────────────────────────────────────────

  @consume({ context: storefrontContext, subscribe: true })
  @state()
  private ctx?: StorefrontContext;

  /** À-la-carte: aggancio al kernel se fuori da un provider (no-op se dentro). */
  protected _store = new StoreConsumerController(this);

  /** Guard singleton: un solo account drawer attivo per slug. */
  protected _singleton = new SingletonController(this, 'account');

  // ── Public attributes ────────────────────────────────────────────────

  /**
   * Posizione del floating button. Default 'top-right' per evitare
   * collisione con <afianco-cart-drawer> che e' 'bottom-right'.
   * Valori validi: 'top-right' | 'top-left' | 'inline'
   *
   * 'inline' = render senza posizionamento fixed (per merchant che
   * vogliono integrare il button nel proprio header HTML).
   */
  @property({ type: String, attribute: 'position' })
  position: 'top-right' | 'top-left' | 'inline' = 'top-right';

  /**
   * Track E Step 2.4.4 — quando true, nasconde il floating trigger
   * button interno. Usato quando il merchant include <afianco-header>
   * che fornisce i trigger button in un layout unificato.
   * Il drawer si apre via document-level event 'afianco:open-account'.
   */
  @property({ type: Boolean, attribute: 'hide-trigger', reflect: true })
  hideTrigger = false;

  // ── Internal state ───────────────────────────────────────────────────

  /** Drawer open/closed. */
  @property({ type: Boolean, reflect: true })
  private open = false;

  /** Current view inside the drawer. */
  @state()
  private view: AccountView = 'login';

  /** Cached auth state — re-evaluated on open + events. */
  @state()
  private authenticated = false;

  // ── Lifecycle ────────────────────────────────────────────────────────

  connectedCallback(): void {
    super.connectedCallback();
    // Listen to children events bubbling up (composed: true)
    this.addEventListener('afianco:customer-logged-in', this.handleLoggedIn);
    this.addEventListener('afianco:customer-signed-up', this.handleSignedUp);
    this.addEventListener('afianco:portal-logout', this.handleLogout);
    // Track E Step 5.3 — listener su afianco:auth-action dal child
    // <afianco-login> per cambiare view a 'forgot'.
    this.addEventListener('afianco:auth-action', this.handleAuthAction as EventListener);
    // Storage event for cross-tab sync
    window.addEventListener('storage', this.handleStorageEvent);
    // Track E Step 2.4.4 — listener per apertura remota dal <afianco-header>
    // trigger button (loose coupling via document event bus).
    document.addEventListener('afianco:open-account', this.handleOpenAccount);
    // Track E Step 2.4.4 — ESC key per chiudere il drawer (a11y standard).
    document.addEventListener('keydown', this.handleKeydown);
    this.evaluateAuthState();
  }

  disconnectedCallback(): void {
    this.removeEventListener('afianco:customer-logged-in', this.handleLoggedIn);
    this.removeEventListener('afianco:customer-signed-up', this.handleSignedUp);
    this.removeEventListener('afianco:portal-logout', this.handleLogout);
    this.removeEventListener('afianco:auth-action', this.handleAuthAction as EventListener);
    window.removeEventListener('storage', this.handleStorageEvent);
    document.removeEventListener('afianco:open-account', this.handleOpenAccount);
    document.removeEventListener('keydown', this.handleKeydown);
    super.disconnectedCallback();
  }

  /**
   * Track E Step 5.3 — auth-action event dal child <afianco-login> per
   * gestire "Password dimenticata?" click. Switch view a 'forgot'.
   */
  private handleAuthAction = (e: CustomEvent): void => {
    const action = e.detail?.action;
    if (action === 'forgot-password') {
      this.view = 'forgot';
    } else if (action === 'show-signup') {
      this.view = 'signup';
    } else if (action === 'show-login') {
      this.view = 'login';
    }
  };

  /**
   * Track E Step 2.4.4 — handle document-level open request dispatched
   * dal <afianco-header> trigger button.
   */
  private handleOpenAccount = (): void => {
    if (!this._singleton.active) return;
    this.setOpen(true);
  };

  /**
   * Track E Step 2.4.4 — ESC closes the drawer (a11y standard).
   */
  private handleKeydown = (e: KeyboardEvent): void => {
    if (e.key === 'Escape' && this.open) {
      e.preventDefault();
      this.setOpen(false);
    }
  };

  protected updated(changed: PropertyValues): void {
    if (changed.has('open') && this.open) {
      // Re-evaluate auth state quando l'utente apre il drawer
      this.evaluateAuthState();
      // Initial view based on auth
      this.view = this.authenticated ? 'portal' : 'login';
    }
  }

  // ── Handlers ─────────────────────────────────────────────────────────

  private handleLoggedIn = (): void => {
    this.authenticated = true;
    this.view = 'portal';
  };

  private handleSignedUp = (): void => {
    // signup flow: il customer potrebbe NON essere auto-logged se backend
    // ha auto_login=False (verification_required). Re-evaluate.
    this.evaluateAuthState();
    if (this.authenticated) {
      this.view = 'portal';
    } else {
      // Stay on signup form; backend ha mostrato "controlla email"
      this.view = 'signup';
    }
  };

  private handleLogout = (): void => {
    this.authenticated = false;
    this.view = 'login';
  };

  private handleStorageEvent = (e: StorageEvent): void => {
    // B10 — reagisci solo alla key del PROPRIO slug (in pagine multi-store il
    // login di un altro store non deve toccare questo account).
    if (!e.key) return;
    const slug = this.ctx?.init?.slug ?? this.ctx?.client?.slug;
    const isMine = slug ? e.key === `afianco_token_${slug}` : e.key.startsWith('afianco_token_');
    if (isMine) {
      this.evaluateAuthState();
      // If logged out from another tab while drawer open, switch view
      if (this.open && !this.authenticated) {
        this.view = 'login';
      }
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

  private toggleDrawer(): void {
    this.setOpen(!this.open);
  }

  private setOpen(value: boolean): void {
    if (this.open === value) return;
    this.open = value;
    this.dispatchEvent(
      new CustomEvent(value ? 'afianco:account-opened' : 'afianco:account-closed', {
        detail: value ? { authenticated: this.authenticated } : {},
        bubbles: true,
        composed: true,
      }),
    );
  }

  private switchView(view: AccountView): void {
    this.view = view;
  }

  // ── Render ───────────────────────────────────────────────────────────

  static styles = [
    afiancoBaseStyles,
    css`
      :host {
        display: contents;
        /* Position is applied to inner fragments per 'position' attr */
      }

      /* ── Floating button ────────────────────────────────────────── */
      .fab {
        position: fixed;
        z-index: 9998;
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: var(--afianco-color-surface, #ffffff);
        color: var(--afianco-color-text, #111827);
        border: 1px solid var(--afianco-color-border, #e5e7eb);
        border-radius: 9999px;
        padding: 10px 16px;
        font-family: var(--afianco-font-body, system-ui, -apple-system, sans-serif);
        font-size: 14px;
        font-weight: 500;
        cursor: pointer;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
      }
      .fab:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 16px rgba(0, 0, 0, 0.15);
      }
      .fab:active {
        transform: translateY(0);
      }

      :host([position='top-right']) .fab {
        top: 16px;
        right: 16px;
      }
      :host([position='top-left']) .fab {
        top: 16px;
        left: 16px;
      }
      :host([position='inline']) .fab {
        position: static;
      }

      /* Track E Step 2.4.4 — quando l'header unificato e' presente,
         hide-trigger nasconde il floating FAB per evitare duplicazione.
         Il drawer continua a funzionare normalmente via document event. */
      :host([hide-trigger]) .fab {
        display: none;
      }

      .fab-icon {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 20px;
        height: 20px;
      }

      .fab-label {
        white-space: nowrap;
      }

      .fab-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: var(--afianco-color-success, #10b981);
        margin-left: 2px;
      }

      /* ── Scrim ────────────────────────────────────────────────────── */
      .scrim {
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.5);
        opacity: 0;
        pointer-events: none;
        transition: opacity 0.2s ease;
        z-index: 9998;
      }
      :host([open]) .scrim {
        opacity: 1;
        pointer-events: auto;
      }

      /* ── Drawer ───────────────────────────────────────────────────── */
      .drawer {
        position: fixed;
        top: 0;
        right: 0;
        bottom: 0;
        width: 100%;
        max-width: 440px;
        background: var(--afianco-color-surface, #ffffff);
        box-shadow: -4px 0 24px rgba(0, 0, 0, 0.15);
        transform: translateX(100%);
        transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        z-index: 9999;
        display: flex;
        flex-direction: column;
        /* E2.4.4 defense-in-depth: garantisce drawer invisibile +
           inerte agli eventi finche' [open] non e' impostato. Anti-
           override CSS merchant. */
        visibility: hidden;
        pointer-events: none;
      }
      :host([open]) .drawer {
        transform: translateX(0);
        visibility: visible;
        pointer-events: auto;
      }

      .drawer-header {
        flex-shrink: 0;
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 16px 20px;
        border-bottom: 1px solid var(--afianco-color-border, #e5e7eb);
      }
      .drawer-title {
        font-size: 16px;
        font-weight: 600;
        color: var(--afianco-color-text, #111827);
      }
      .close-btn {
        background: transparent;
        border: none;
        cursor: pointer;
        color: var(--afianco-color-text-muted, #6b7280);
        padding: 4px;
        border-radius: 4px;
        display: inline-flex;
      }
      .close-btn:hover {
        background: var(--afianco-color-muted, #f3f4f6);
        color: var(--afianco-color-text, #111827);
      }

      /* ── Tabs (login / signup switch) ──────────────────────────── */
      .tabs {
        display: flex;
        border-bottom: 1px solid var(--afianco-color-border, #e5e7eb);
        flex-shrink: 0;
      }
      .tab {
        flex: 1;
        padding: 12px 16px;
        background: transparent;
        border: none;
        border-bottom: 2px solid transparent;
        cursor: pointer;
        font-family: inherit;
        font-size: 14px;
        font-weight: 500;
        color: var(--afianco-color-text-muted, #6b7280);
        transition: color 0.15s ease, border-color 0.15s ease;
      }
      .tab:hover {
        color: var(--afianco-color-text, #111827);
      }
      .tab[aria-selected='true'] {
        color: var(--afianco-color-primary, #4f5dca);
        border-bottom-color: var(--afianco-color-primary, #4f5dca);
      }

      /* ── Drawer body (scrollable) ──────────────────────────────── */
      .drawer-body {
        flex: 1;
        overflow-y: auto;
        padding: 20px;
      }

      /* Footer help text */
      .switch-hint {
        text-align: center;
        font-size: 13px;
        color: var(--afianco-color-text-muted, #6b7280);
        margin-top: 16px;
      }
      .switch-hint a {
        color: var(--afianco-color-primary, #4f5dca);
        text-decoration: none;
        cursor: pointer;
        font-weight: 500;
      }
      .switch-hint a:hover {
        text-decoration: underline;
      }
    `,
  ];

  render() {
    // Singleton passivo (un altro account drawer e' gia' attivo) → non rende.
    if (!this._singleton.active) return nothing;
    return html`
      <button
        class="fab"
        type="button"
        @click=${this.toggleDrawer}
        aria-label=${this.authenticated ? t('account.open_authenticated') : t('account.open_guest')}
        aria-expanded=${this.open}
      >
        <span class="fab-icon" aria-hidden="true">
          ${this.renderIcon()}
        </span>
        <span class="fab-label">
          ${this.authenticated ? t('header.account_logged') : t('header.account_login')}
        </span>
        ${this.authenticated ? html`<span class="fab-dot"></span>` : null}
      </button>

      <div
        class="scrim"
        @click=${() => this.setOpen(false)}
        aria-hidden=${!this.open}
      ></div>

      <aside
        class="drawer"
        role="dialog"
        aria-modal="true"
        aria-label=${t('account.title')}
        aria-hidden=${!this.open}
      >
        <header class="drawer-header">
          <span class="drawer-title">
            ${this.authenticated
              ? t('account.title_authenticated')
              : (this.view === 'signup' ? t('account.title_signup') : t('account.title_login'))}
          </span>
          <button
            class="close-btn"
            type="button"
            @click=${() => this.setOpen(false)}
            aria-label=${t('account.close_label')}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M18 6L6 18M6 6l12 12"/>
            </svg>
          </button>
        </header>

        ${this.authenticated
          ? this.renderPortal()
          : this.renderAuthTabs()}
      </aside>
    `;
  }

  private renderIcon() {
    return html`
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
        <circle cx="12" cy="7" r="4"/>
      </svg>
    `;
  }

  private renderAuthTabs() {
    return html`
      <div class="tabs" role="tablist">
        <button
          class="tab"
          type="button"
          role="tab"
          aria-selected=${this.view === 'login'}
          @click=${() => this.switchView('login')}
        >
          ${t('account.tab_login')}
        </button>
        <button
          class="tab"
          type="button"
          role="tab"
          aria-selected=${this.view === 'signup'}
          @click=${() => this.switchView('signup')}
        >
          ${t('account.tab_signup')}
        </button>
      </div>
      <div class="drawer-body">
        ${this.view === 'login'
          ? html`
              <afianco-login></afianco-login>
              <div class="switch-hint">
                ${t('account.no_account_question')}
                <a @click=${() => this.switchView('signup')}>${t('account.signup_cta')}</a>
              </div>
            `
          : this.view === 'forgot'
            ? this.renderForgotPassword()
            : html`
                <afianco-signup></afianco-signup>
                <div class="switch-hint">
                  ${t('account.have_account_question')}
                  <a @click=${() => this.switchView('login')}>${t('account.login_cta')}</a>
                </div>
              `}
      </div>
    `;
  }

  // ── Track E Step 5.3 — Forgot password inline form ──
  /**
   * Render del form "Password dimenticata?" inline nel drawer account.
   *
   * Customer inserisce email → POST /api/customer-auth/forgot-password
   * → success message "Controlla la tua email per il link reset".
   * Il link reset porta al storefront classico afianco.app/reset-password
   * (la nuova password si imposta li, non nel widget — limitazione
   * cross-origin del token reset che e' single-use).
   */
  @state()
  private forgotEmail = '';
  @state()
  private forgotSubmitting = false;
  @state()
  private forgotMsg: { type: 'success' | 'error'; text: string } | null = null;

  private async submitForgotPassword(e: Event): Promise<void> {
    e.preventDefault();
    const email = this.forgotEmail.trim();
    if (!email || !email.includes('@')) {
      this.forgotMsg = { type: 'error', text: 'Email non valida.' };
      return;
    }
    const client = this.ctx?.client;
    if (!client) {
      this.forgotMsg = { type: 'error', text: 'Storefront non pronto. Riprova.' };
      return;
    }
    this.forgotSubmitting = true;
    this.forgotMsg = null;
    try {
      await client.customerAuth.forgotPassword({ email } as never);
      this.forgotMsg = {
        type: 'success',
        text: t('account.forgot_password_success'),
      };
      this.forgotEmail = '';
    } catch (err) {
      // Backend ritorna 200 generico anche per email non esistente
      // (anti-enumeration). 4xx = errore network o validation.
      this.forgotMsg = {
        type: 'error',
        text: (err as Error)?.message ?? t('account.forgot_password_error'),
      };
    } finally {
      this.forgotSubmitting = false;
    }
  }

  private renderForgotPassword() {
    return html`
      <div style="padding: 20px;">
        <h3 style="margin: 0 0 12px; font-size: 18px; font-weight: 700;">
          Password dimenticata?
        </h3>
        <p style="font-size: 14px; color: var(--afianco-color-text-secondary, #6b7280); margin-bottom: 16px; line-height: 1.5;">
          Inserisci la tua email. Ti invieremo un link per reimpostare la password.
        </p>
        <form @submit=${(e: Event) => void this.submitForgotPassword(e)}>
          <div style="display:flex; flex-direction:column; gap:6px; margin-bottom: 12px;">
            <label for="forgot-email" style="font-size:12px; font-weight:600;">Email*</label>
            <input
              id="forgot-email"
              type="email"
              required
              placeholder="tua@email.com"
              style="padding: 10px 14px;
                     border: 1px solid var(--afianco-color-border, #e5e7eb);
                     border-radius: 8px;
                     font-family: inherit; font-size: 14px;"
              .value=${this.forgotEmail}
              @input=${(e: InputEvent) =>
                (this.forgotEmail = (e.target as HTMLInputElement).value)}>
          </div>
          ${this.forgotMsg
            ? html`
                <div
                  role="status"
                  style="padding: 10px 12px;
                         border-radius: 6px;
                         font-size: 13px;
                         margin-bottom: 12px;
                         background: ${this.forgotMsg.type === 'success' ? '#d1fae5' : '#fef2f2'};
                         color: ${this.forgotMsg.type === 'success' ? '#065f46' : 'var(--afianco-color-danger, #ef4444)'};">
                  ${this.forgotMsg.text}
                </div>
              `
            : ''}
          <button
            type="submit"
            ?disabled=${this.forgotSubmitting}
            style="width: 100%;
                   padding: 12px;
                   background: var(--afianco-color-primary, #4b72ce);
                   color: var(--afianco-color-primary-text, #ffffff);
                   border: none;
                   border-radius: 8px;
                   font-family: inherit;
                   font-size: 14px;
                   font-weight: 600;
                   cursor: pointer;">
            ${this.forgotSubmitting ? 'Invio in corso…' : 'Invia link reset'}
          </button>
        </form>
        <div class="switch-hint" style="margin-top:16px; text-align:center; font-size:13px;">
          <a
            style="color: var(--afianco-color-primary, #4b72ce); cursor: pointer; text-decoration: underline;"
            @click=${() => this.switchView('login')}>
            ← Torna al login
          </a>
        </div>
      </div>
    `;
  }

  private renderPortal() {
    return html`
      <div class="drawer-body">
        <afianco-customer-portal></afianco-customer-portal>
      </div>
    `;
  }
}


declare global {
  interface HTMLElementTagNameMap {
    'afianco-account': AfiancoAccount;
  }
}
