/**
 * <afianco-login> — Phase 1 Step 27 (Track C).
 *
 * Form login customer standalone — utile per merchant che vogliono
 * offrire una pagina /accedi dedicata, separata dal flow checkout.
 *
 * Auto-stores customer JWT in localStorage (gestito da api-client).
 * Dispatcha `afianco:customer-logged-in` su successo.
 *
 * Uso (nested sotto storefront-init):
 *
 *   <afianco-storefront-init slug="acme">
 *     <afianco-login></afianco-login>
 *   </afianco-storefront-init>
 *
 * Custom events:
 *   - `afianco:customer-logged-in` (detail: { customer, access_token })
 *   - `afianco:customer-auth-error` (detail: { message })
 */

import { LitElement, html, css, type PropertyValues } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { consume } from '@lit/context';
import { afiancoBaseStyles } from '@afianco/design-tokens';
import {
  AfiancoAuthError,
  AfiancoLockedError,
  AfiancoValidationError,
  type CustomerProfile,
} from '@afianco/api-client';
// Sprint 4 W4.7 — i18n wiring
import { t } from '../i18n/index.js';
import {
  storefrontContext,
  STOREFRONT_INITIAL,
  type StorefrontContext,
} from '../context.js';

@customElement('afianco-login')
export class AfiancoLogin extends LitElement {
  /** Titolo personalizzabile via attribute, default "Accedi". */
  @property({ type: String })
  title = ''; // Sprint 4 W4.7 — default resolved at render via t('login.title')

  /** Mostra link "Hai dimenticato la password?" — default true. */
  @property({ type: Boolean, attribute: 'show-forgot' })
  showForgot = true;

  /** Mostra link "Non hai un account? Registrati" — default true. */
  @property({ type: Boolean, attribute: 'show-signup-link' })
  showSignupLink = true;

  @consume({ context: storefrontContext, subscribe: true })
  @state()
  ctx: StorefrontContext = STOREFRONT_INITIAL;

  @state()
  private email = '';
  @state()
  private password = '';
  // Sprint 3 W3.1 — Password visibility toggle (parity React AuthPage)
  @state()
  private showPassword = false;
  // Sprint 3 W3.2 — Account lockout countdown (Onda 29 parity React)
  @state()
  private lockoutUnlockAt: string | null = null;
  @state()
  private lockoutSecondsRemaining: number = 0;
  private _lockoutTimer: number | null = null;
  @state()
  private submitting = false;
  @state()
  private errorMsg: string | null = null;
  @state()
  private successProfile: CustomerProfile | null = null;

  static styles = [
    afiancoBaseStyles,
    css`
      :host {
        display: block;
        max-width: 400px;
      }
      .card {
        background: var(--afianco-color-bg);
        border: 1px solid var(--afianco-color-border);
        border-radius: var(--afianco-radius-lg);
        padding: var(--afianco-spacing-xl);
        box-shadow: var(--afianco-shadow-sm);
      }
      .title {
        margin: 0 0 var(--afianco-spacing-lg);
        font-size: var(--afianco-font-size-xl);
        font-weight: var(--afianco-font-weight-bold);
        color: var(--afianco-color-text-primary);
      }
      .field {
        margin-bottom: var(--afianco-spacing-md);
      }
      label {
        display: block;
        font-size: var(--afianco-font-size-sm);
        font-weight: var(--afianco-font-weight-medium);
        margin-bottom: var(--afianco-spacing-xs);
        color: var(--afianco-color-text-primary);
      }
      input {
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
      input:focus {
        outline: 2px solid var(--afianco-color-primary);
        outline-offset: 0;
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
      }
      .submit-btn:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }
      /* Sprint 3 W3.1 — Password visibility toggle (parity React AuthPage). */
      .password-wrap {
        position: relative;
      }
      .password-wrap input {
        padding-right: 44px;
      }
      .toggle-password {
        position: absolute;
        right: 6px;
        top: 50%;
        transform: translateY(-50%);
        background: transparent;
        border: none;
        cursor: pointer;
        padding: 6px;
        border-radius: 4px;
        color: var(--afianco-color-text-secondary, #6b7280);
        display: inline-flex;
        align-items: center;
        justify-content: center;
      }
      .toggle-password:hover {
        background: var(--afianco-color-muted, #f3f4f6);
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
      .success-banner {
        background: #f0fdf4;
        border: 1px solid #bbf7d0;
        color: var(--afianco-color-success);
        padding: var(--afianco-spacing-md);
        border-radius: var(--afianco-radius-md);
        font-size: var(--afianco-font-size-sm);
        text-align: center;
      }
      .links {
        margin-top: var(--afianco-spacing-md);
        display: flex;
        justify-content: space-between;
        font-size: var(--afianco-font-size-sm);
      }
      .links a {
        color: var(--afianco-color-primary);
        text-decoration: none;
        cursor: pointer;
      }
      .links a:hover {
        text-decoration: underline;
      }
    `,
  ];

  // ── Lifecycle ─────────────────────────────────────────────────────────

  protected updated(_changed: PropertyValues): void {
    // no-op
  }

  // ── Public API ────────────────────────────────────────────────────────

  async submit(): Promise<void> {
    if (!this.ctx.client) {
      this.errorMsg = t('login.error_storefront_not_ready');
      return;
    }
    // Client-side validation
    if (!this.email.trim() || !this.email.includes('@')) {
      this.errorMsg = t('login.error_email_invalid');
      return;
    }
    if (!this.password) {
      this.errorMsg = t('login.error_password_required');
      return;
    }

    this.submitting = true;
    this.errorMsg = null;
    try {
      const slug = this.ctx.init?.slug ?? this.ctx.client.slug;
      const resp = await this.ctx.client.customerAuth.login({
        slug,
        email: this.email.trim(),
        password: this.password,
      });
      this.successProfile = resp.customer;
      this.dispatchEvent(
        new CustomEvent<{ customer: CustomerProfile; access_token: string }>(
          'afianco:customer-logged-in',
          {
            detail: {
              customer: resp.customer,
              access_token: resp.access_token,
            },
            bubbles: true,
            composed: true,
          },
        ),
      );
      // Clear sensitive fields
      this.password = '';
    } catch (e) {
      // Sprint 3 W3.2 — 423 Locked (Onda 29 account lockout)
      if (e instanceof AfiancoLockedError) {
        this.lockoutUnlockAt = e.unlockAtIso;
        this._startLockoutCountdown();
        this.errorMsg = null; // banner separato per lockout
      } else if (e instanceof AfiancoAuthError) {
        this.errorMsg = t('login.error_credentials');
      } else if (e instanceof AfiancoValidationError) {
        const det = (e.detail as { detail?: unknown } | null)?.detail;
        this.errorMsg = typeof det === 'string' ? det : e.message;
      } else {
        this.errorMsg = (e as Error)?.message ?? t('login.error_generic');
      }
      this.dispatchEvent(
        new CustomEvent<{ message: string }>('afianco:customer-auth-error', {
          detail: { message: this.errorMsg ?? t('login.dispatch_error') },
          bubbles: true,
          composed: true,
        }),
      );
    } finally {
      this.submitting = false;
    }
  }

  // ── Link handlers ─────────────────────────────────────────────────────

  private handleForgotClick(e: Event): void {
    e.preventDefault();
    this.dispatchEvent(
      new CustomEvent('afianco:auth-action', {
        detail: { action: 'forgot-password' },
        bubbles: true,
        composed: true,
      }),
    );
  }

  private handleSignupClick(e: Event): void {
    e.preventDefault();
    this.dispatchEvent(
      new CustomEvent('afianco:auth-action', {
        detail: { action: 'show-signup' },
        bubbles: true,
        composed: true,
      }),
    );
  }

  // ── Render ────────────────────────────────────────────────────────────

  /**
   * Sprint 3 W3.2 — Account lockout countdown helpers (Onda 29 parity React).
   *
   * Backend ritorna 423 con detail.unlock_at ISO string. Avviamo un
   * setInterval che aggiorna secondsRemaining ogni 1s. Quando arriva a 0,
   * cleanup + il customer puo' riprovare il login.
   */
  private _startLockoutCountdown(): void {
    this._stopLockoutCountdown();
    if (!this.lockoutUnlockAt) return;
    const tick = () => {
      if (!this.lockoutUnlockAt) {
        this.lockoutSecondsRemaining = 0;
        return;
      }
      const unlockMs = Date.parse(this.lockoutUnlockAt);
      if (isNaN(unlockMs)) {
        this.lockoutSecondsRemaining = 0;
        this._stopLockoutCountdown();
        return;
      }
      const diff = Math.max(0, Math.ceil((unlockMs - Date.now()) / 1000));
      this.lockoutSecondsRemaining = diff;
      if (diff <= 0) {
        this._stopLockoutCountdown();
        this.lockoutUnlockAt = null;
      }
    };
    tick(); // immediate
    this._lockoutTimer = window.setInterval(tick, 1000);
  }

  private _stopLockoutCountdown(): void {
    if (this._lockoutTimer !== null) {
      clearInterval(this._lockoutTimer);
      this._lockoutTimer = null;
    }
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    this._stopLockoutCountdown();
  }

  private _formatLockoutCountdown(): string {
    const secs = this.lockoutSecondsRemaining;
    if (secs <= 0) return '0:00';
    const mins = Math.floor(secs / 60);
    const sec = secs % 60;
    return `${mins}:${String(sec).padStart(2, '0')}`;
  }

  render() {
    if (this.successProfile) {
      return html`<div class="card">
        <div class="success-banner">
          Benvenuto, ${this.successProfile.name}! Sei connesso.
        </div>
      </div>`;
    }
    return html`
      <div class="card">
        <h2 class="title">${this.title || t('login.title')}</h2>
        ${/* Sprint 3 W3.2 — Lockout countdown banner (parity Onda 29 React) */ ''}
        ${this.lockoutUnlockAt && this.lockoutSecondsRemaining > 0
          ? html`<div
              class="error-banner"
              role="alert"
              aria-live="polite"
              style="background: #fff7ed; border-color: #fed7aa; color: #9a3412;">
              ${t('login.account_locked_prefix')}
              <strong>${this._formatLockoutCountdown()}</strong>.
            </div>`
          : ''}
        ${this.errorMsg
          ? html`<div class="error-banner" role="alert">${this.errorMsg}</div>`
          : ''}
        <form
          @submit=${(e: SubmitEvent) => {
            e.preventDefault();
            void this.submit();
          }}>
          <div class="field">
            <label for="afianco-login-email">Email</label>
            <input
              id="afianco-login-email"
              type="email"
              required
              autocomplete="email"
              .value=${this.email}
              @input=${(e: InputEvent) =>
                (this.email = (e.target as HTMLInputElement).value)}>
          </div>
          <div class="field">
            <label for="afianco-login-password">Password</label>
            <div class="password-wrap">
              <input
                id="afianco-login-password"
                type=${this.showPassword ? 'text' : 'password'}
                required
                autocomplete="current-password"
                .value=${this.password}
                @input=${(e: InputEvent) =>
                  (this.password = (e.target as HTMLInputElement).value)}>
              <button
                type="button"
                class="toggle-password"
                aria-label=${this.showPassword
                  ? t('login.hide_password')
                  : t('login.show_password')}
                aria-pressed=${this.showPassword ? 'true' : 'false'}
                @click=${() => (this.showPassword = !this.showPassword)}>
                ${this.showPassword
                  ? html`<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                      <line x1="1" y1="1" x2="23" y2="23"></line>
                    </svg>`
                  : html`<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                      <circle cx="12" cy="12" r="3"></circle>
                    </svg>`}
              </button>
            </div>
          </div>
          <button
            class="submit-btn"
            type="submit"
            ?disabled=${this.submitting}>
            ${this.submitting ? t('login.submitting') : t('login.submit')}
          </button>
        </form>
        ${this.showForgot || this.showSignupLink
          ? html`<div class="links">
              ${this.showForgot
                ? html`<a href="#" @click=${this.handleForgotClick}>
                    ${t('login.forgot_password')}
                  </a>`
                : html`<span></span>`}
              ${this.showSignupLink
                ? html`<a href="#" @click=${this.handleSignupClick}>
                    ${t('login.create_account_link')}
                  </a>`
                : ''}
            </div>`
          : ''}
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'afianco-login': AfiancoLogin;
  }
  interface HTMLElementEventMap {
    'afianco:customer-logged-in': CustomEvent<{
      customer: CustomerProfile;
      access_token: string;
    }>;
    'afianco:customer-auth-error': CustomEvent<{ message: string }>;
    'afianco:auth-action': CustomEvent<{ action: string }>;
  }
}
