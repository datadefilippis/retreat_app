/**
 * <afianco-signup> — Phase 1 Step 27 (Track C).
 *
 * Form signup customer standalone. GDPR consent obbligatorio (Privacy
 * + Terms, opt-in Marketing). Calla client.customerAuth.signup() che
 * di default richiede email verification (no auto_login da questo
 * component — per inline signup-at-checkout vedi <afianco-checkout-button>).
 *
 * Custom events:
 *   - `afianco:customer-signed-up` (detail: { email })
 *       → backend ha mandato la verification email. Il merchant può
 *         redirect a thank-you page o mostrare istruzioni.
 *   - `afianco:customer-auth-error` (detail: { message })
 */

import { LitElement, html, css, type PropertyValues } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { consume } from '@lit/context';
import { afiancoBaseStyles } from '@afianco/design-tokens';
import { AfiancoValidationError } from '@afianco/api-client';
// Sprint 3 W3.1 — Password strength indicator (parity React AuthPage)
import {
  computePasswordStrength,
  levelMeta,
} from '../utils/password-strength.js';
// Sprint 4 W4.7 — i18n wiring
import { t } from '../i18n/index.js';
import {
  storefrontContext,
  STOREFRONT_INITIAL,
  type StorefrontContext,
} from '../context.js';

@customElement('afianco-signup')
export class AfiancoSignup extends LitElement {
  @property({ type: String })
  title = ''; // Sprint 4 W4.7 — default resolved at render via t('signup.title')

  @property({ type: Boolean, attribute: 'show-login-link' })
  showLoginLink = true;

  @consume({ context: storefrontContext, subscribe: true })
  @state()
  ctx: StorefrontContext = STOREFRONT_INITIAL;

  @state()
  private name = '';
  @state()
  private email = '';
  @state()
  private password = '';
  // Sprint 3 W3.1 — Password UX (parity React AuthPage)
  @state()
  private showPassword = false;
  @state()
  private gdprPrivacy = false;
  @state()
  private gdprTerms = false;
  @state()
  private gdprMarketing = false;
  @state()
  private submitting = false;
  @state()
  private errorMsg: string | null = null;
  @state()
  private successEmail: string | null = null;

  static styles = [
    afiancoBaseStyles,
    css`
      :host {
        display: block;
        max-width: 420px;
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
      }
      .field {
        margin-bottom: var(--afianco-spacing-md);
      }
      label {
        display: block;
        font-size: var(--afianco-font-size-sm);
        font-weight: var(--afianco-font-weight-medium);
        margin-bottom: var(--afianco-spacing-xs);
      }
      input[type='text'],
      input[type='email'],
      input[type='password'] {
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
      .password-hint {
        font-size: var(--afianco-font-size-xs);
        color: var(--afianco-color-text-muted);
        margin-top: var(--afianco-spacing-xs);
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
      /* Sprint 3 W3.1 — Password UX (parity React AuthPage) */
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
      .strength-bar {
        display: flex;
        gap: 3px;
        margin-top: 6px;
        height: 4px;
      }
      .strength-bar span {
        flex: 1;
        background: var(--afianco-color-border, #e5e7eb);
        border-radius: 2px;
        transition: background 0.15s ease;
      }
      .strength-label {
        font-size: 11px;
        margin-top: 4px;
        font-weight: 600;
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
        margin-top: var(--afianco-spacing-sm);
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
      .success-banner {
        background: #f0fdf4;
        border: 1px solid #bbf7d0;
        color: var(--afianco-color-success);
        padding: var(--afianco-spacing-lg);
        border-radius: var(--afianco-radius-md);
        font-size: var(--afianco-font-size-sm);
        text-align: center;
      }
      .login-link {
        margin-top: var(--afianco-spacing-md);
        font-size: var(--afianco-font-size-sm);
        text-align: center;
      }
      .login-link a {
        color: var(--afianco-color-primary);
        text-decoration: none;
        cursor: pointer;
      }
      .login-link a:hover {
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
      this.errorMsg = t('signup.error_storefront_not_ready');
      return;
    }
    // Validation
    if (!this.name.trim()) {
      this.errorMsg = t('signup.error_name_required');
      return;
    }
    if (!this.email.trim() || !this.email.includes('@')) {
      this.errorMsg = t('signup.error_email_invalid');
      return;
    }
    if (!this.password || this.password.length < 8) {
      this.errorMsg = t('signup.error_password_min');
      return;
    }
    if (!this.gdprPrivacy || !this.gdprTerms) {
      this.errorMsg = t('signup.error_gdpr_required');
      return;
    }

    this.submitting = true;
    this.errorMsg = null;
    try {
      const slug = this.ctx.init?.slug ?? this.ctx.client.slug;
      await this.ctx.client.customerAuth.signup({
        slug,
        email: this.email.trim(),
        name: this.name.trim(),
        password: this.password,
        accepted_terms: this.gdprTerms,
        accepted_privacy: this.gdprPrivacy,
        accepted_marketing: this.gdprMarketing,
      });
      this.successEmail = this.email.trim();
      this.dispatchEvent(
        new CustomEvent<{ email: string }>('afianco:customer-signed-up', {
          detail: { email: this.email.trim() },
          bubbles: true,
          composed: true,
        }),
      );
      // Clear sensitive
      this.password = '';
    } catch (e) {
      if (e instanceof AfiancoValidationError) {
        const det = (e.detail as { detail?: unknown } | null)?.detail;
        this.errorMsg = typeof det === 'string' ? det : e.message;
      } else {
        this.errorMsg = (e as Error)?.message ?? t('signup.error_generic');
      }
      this.dispatchEvent(
        new CustomEvent<{ message: string }>('afianco:customer-auth-error', {
          detail: { message: this.errorMsg },
          bubbles: true,
          composed: true,
        }),
      );
    } finally {
      this.submitting = false;
    }
  }

  private handleLoginClick(e: Event): void {
    e.preventDefault();
    this.dispatchEvent(
      new CustomEvent('afianco:auth-action', {
        detail: { action: 'show-login' },
        bubbles: true,
        composed: true,
      }),
    );
  }

  // ── Render ────────────────────────────────────────────────────────────

  render() {
    if (this.successEmail) {
      return html`<div class="card">
        <div class="success-banner">
          ${t('signup.verification_message_full', { email: this.successEmail })}
        </div>
      </div>`;
    }
    return html`
      <div class="card">
        <h2 class="title">${this.title || t('signup.title')}</h2>
        ${this.errorMsg
          ? html`<div class="error-banner" role="alert">${this.errorMsg}</div>`
          : ''}
        <form
          @submit=${(e: SubmitEvent) => {
            e.preventDefault();
            void this.submit();
          }}>
          <div class="field">
            <label for="afianco-signup-name">Nome*</label>
            <input
              id="afianco-signup-name"
              type="text"
              required
              autocomplete="name"
              .value=${this.name}
              @input=${(e: InputEvent) =>
                (this.name = (e.target as HTMLInputElement).value)}>
          </div>
          <div class="field">
            <label for="afianco-signup-email">Email*</label>
            <input
              id="afianco-signup-email"
              type="email"
              required
              autocomplete="email"
              .value=${this.email}
              @input=${(e: InputEvent) =>
                (this.email = (e.target as HTMLInputElement).value)}>
          </div>
          <div class="field">
            <label for="afianco-signup-password">Password*</label>
            <div class="password-wrap">
              <input
                id="afianco-signup-password"
                type=${this.showPassword ? 'text' : 'password'}
                required
                minlength="8"
                autocomplete="new-password"
                .value=${this.password}
                @input=${(e: InputEvent) =>
                  (this.password = (e.target as HTMLInputElement).value)}>
              <button
                type="button"
                class="toggle-password"
                aria-label=${this.showPassword
                  ? 'Nascondi password'
                  : 'Mostra password'}
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
            <div class="password-hint">Minimo 8 caratteri</div>
            ${this.password
              ? (() => {
                  // Sprint 3 W3.1 — Strength meter live
                  const strength = computePasswordStrength(this.password);
                  const meta = levelMeta(strength.level);
                  // 5 segments: filled count = score (max 5)
                  return html`
                    <div class="strength-bar" aria-hidden="true">
                      ${[0, 1, 2, 3, 4].map((i) => html`
                        <span style="background: ${i < strength.score ? meta.color : 'var(--afianco-color-border, #e5e7eb)'};"></span>
                      `)}
                    </div>
                    <div class="strength-label" style="color: ${meta.color};">
                      ${meta.label}
                    </div>
                  `;
                })()
              : ''}
          </div>
          <div class="checkbox-row">
            <input
              id="afianco-signup-privacy"
              type="checkbox"
              .checked=${this.gdprPrivacy}
              @change=${(e: Event) =>
                (this.gdprPrivacy = (e.target as HTMLInputElement).checked)}>
            <label for="afianco-signup-privacy">
              Accetto la
              <a
                class="gdpr-link"
                href=${this.ctx.init?.privacy_policy_url ?? '#'}
                target="_blank"
                rel="noopener noreferrer"
                @click=${(e: Event) => e.stopPropagation()}>
                Privacy Policy
              </a>
              del merchant*
            </label>
          </div>
          <div class="checkbox-row">
            <input
              id="afianco-signup-terms"
              type="checkbox"
              .checked=${this.gdprTerms}
              @change=${(e: Event) =>
                (this.gdprTerms = (e.target as HTMLInputElement).checked)}>
            <label for="afianco-signup-terms">
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
              id="afianco-signup-marketing"
              type="checkbox"
              .checked=${this.gdprMarketing}
              @change=${(e: Event) =>
                (this.gdprMarketing = (e.target as HTMLInputElement).checked)}>
            <label for="afianco-signup-marketing">
              Acconsento a ricevere comunicazioni marketing (opzionale)
            </label>
          </div>
          <button
            class="submit-btn"
            type="submit"
            ?disabled=${this.submitting}>
            ${this.submitting ? t('signup.submitting') : t('signup.submit')}
          </button>
        </form>
        ${this.showLoginLink
          ? html`<div class="login-link">
              ${t('signup.login_prompt')}
              <a href="#" @click=${this.handleLoginClick}>${t('signup.login_link')}</a>
            </div>`
          : ''}
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'afianco-signup': AfiancoSignup;
  }
  interface HTMLElementEventMap {
    'afianco:customer-signed-up': CustomEvent<{ email: string }>;
  }
}
