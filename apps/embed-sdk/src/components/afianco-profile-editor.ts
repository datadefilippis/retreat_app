/**
 * <afianco-profile-editor> — Track E Step 4.4 (customer portal editable).
 *
 * Compone 3 sezioni nel tab "Profilo" del customer portal:
 *   1. Profilo: modifica nome, telefono, locale (PATCH /me)
 *   2. Sicurezza: cambia password (POST /change-password)
 *   3. Privacy: richiesta cancellazione dati GDPR Art.17 (POST /me/request-erasure)
 *
 * Pattern collapsible/accordion per UX pulita — espandi solo la sezione
 * che ti interessa modificare. Tutti i form hanno validation client-side
 * + success/error feedback inline.
 *
 * Auto-fetch profile on mount + dispatch refresh event al parent
 * dopo update success per mantenere customer-portal in sync.
 *
 * Custom events:
 *   - afianco:profile-updated (detail: { profile })
 *   - afianco:password-changed
 *   - afianco:erasure-requested (detail: { request_id })
 */

import { LitElement, html, css, nothing, type PropertyValues } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { consume } from '@lit/context';
import { afiancoBaseStyles } from '@afianco/design-tokens';
// W4.9 — i18n
import { t } from '../i18n/index.js';
import type { CustomerProfile } from '@afianco/api-client';
import {
  storefrontContext,
  STOREFRONT_INITIAL,
  type StorefrontContext,
} from '../context.js';


type ActiveSection = 'profile' | 'password' | 'erasure' | null;


@customElement('afianco-profile-editor')
export class AfiancoProfileEditor extends LitElement {
  @consume({ context: storefrontContext, subscribe: true })
  @state()
  ctx: StorefrontContext = STOREFRONT_INITIAL;

  @property({ type: Boolean, attribute: 'no-auto-fetch' })
  noAutoFetch = false;

  // ── Internal state ────────────────────────────────────────────────────

  @state()
  private profile: CustomerProfile | null = null;

  @state()
  private loading = false;

  @state()
  private error: string | null = null;

  /** Currently expanded section (accordion pattern, 1 a la volta). */
  @state()
  private activeSection: ActiveSection = 'profile';

  // ── Profile form state ──
  @state()
  private editName = '';
  @state()
  private editPhone = '';
  @state()
  private editLocale = 'it';
  @state()
  private savingProfile = false;
  @state()
  private profileMsg: { type: 'success' | 'error'; text: string } | null = null;

  // ── Password form state ──
  @state()
  private currentPw = '';
  @state()
  private newPw = '';
  @state()
  private confirmPw = '';
  @state()
  private savingPw = false;
  @state()
  private passwordMsg: { type: 'success' | 'error'; text: string } | null = null;

  // ── Erasure form state ──
  @state()
  private erasureReason = '';
  @state()
  private erasureConfirm = false;
  @state()
  private requestingErasure = false;
  @state()
  private erasureMsg: { type: 'success' | 'error'; text: string } | null = null;

  private _initialized = false;

  // ── Lifecycle ────────────────────────────────────────────────────────

  protected updated(_changed: PropertyValues): void {
    if (this._initialized) return;
    if (this.noAutoFetch) return;
    if (this.ctx?.status !== 'ready' || !this.ctx.client) return;
    this._initialized = true;
    void this.fetchProfile();
  }

  async fetchProfile(): Promise<void> {
    if (!this.ctx?.client) return;
    this.loading = true;
    this.error = null;
    try {
      const p = await this.ctx.client.customer.me();
      this.profile = p;
      this.editName = p.name ?? '';
      this.editPhone = p.phone ?? '';
      this.editLocale = (p as CustomerProfile & { locale?: string }).locale ?? 'it';
    } catch (e) {
      this.error = (e as Error)?.message ?? t('profile.error_load');
    } finally {
      this.loading = false;
    }
  }

  // ── Profile update handler ─────────────────────────────────────────

  private async saveProfile(e: Event): Promise<void> {
    e.preventDefault();
    if (!this.ctx?.client) return;
    if (!this.editName.trim()) {
      this.profileMsg = { type: 'error', text: t('profile.error_name_empty') };
      return;
    }
    this.savingProfile = true;
    this.profileMsg = null;
    try {
      const updated = await this.ctx.client.customer.updateMe({
        name: this.editName.trim(),
        phone: this.editPhone.trim() || null,
        locale: this.editLocale,
      } as Parameters<typeof this.ctx.client.customer.updateMe>[0]);
      this.profile = updated;
      this.profileMsg = { type: 'success', text: 'Profilo aggiornato con successo.' };
      this.dispatchEvent(
        new CustomEvent('afianco:profile-updated', {
          detail: { profile: updated },
          bubbles: true,
          composed: true,
        }),
      );
    } catch (e) {
      const msg = (e as { detail?: string; message?: string }).detail
        ?? (e as Error)?.message
        ?? t('profile.error_update');
      this.profileMsg = { type: 'error', text: msg };
    } finally {
      this.savingProfile = false;
    }
  }

  // ── Password change handler ─────────────────────────────────────────

  private async savePassword(e: Event): Promise<void> {
    e.preventDefault();
    if (!this.ctx?.client) return;
    if (!this.currentPw || !this.newPw) {
      this.passwordMsg = { type: 'error', text: t('profile.error_password_fill') };
      return;
    }
    if (this.newPw.length < 8) {
      this.passwordMsg = { type: 'error', text: t('profile.error_password_min') };
      return;
    }
    if (this.newPw !== this.confirmPw) {
      this.passwordMsg = { type: 'error', text: t('profile.error_password_mismatch') };
      return;
    }
    this.savingPw = true;
    this.passwordMsg = null;
    try {
      await this.ctx.client.customer.changePassword({
        current_password: this.currentPw,
        new_password: this.newPw,
      });
      this.passwordMsg = { type: 'success', text: 'Password aggiornata con successo.' };
      this.currentPw = '';
      this.newPw = '';
      this.confirmPw = '';
      this.dispatchEvent(
        new CustomEvent('afianco:password-changed', {
          bubbles: true,
          composed: true,
        }),
      );
    } catch (e) {
      const msg = (e as { detail?: string; message?: string }).detail
        ?? (e as Error)?.message
        ?? t('profile.error_password_change');
      this.passwordMsg = { type: 'error', text: msg };
    } finally {
      this.savingPw = false;
    }
  }

  // ── Erasure request handler ─────────────────────────────────────────

  private async submitErasure(e: Event): Promise<void> {
    e.preventDefault();
    if (!this.ctx?.client) return;
    if (!this.erasureConfirm) {
      this.erasureMsg = { type: 'error', text: t('profile.error_confirm_required') };
      return;
    }
    this.requestingErasure = true;
    this.erasureMsg = null;
    try {
      const resp = await this.ctx.client.customer.requestErasure({
        reason: this.erasureReason.trim() || null,
      });
      this.erasureMsg = {
        type: 'success',
        text: resp.message ?? 'Richiesta cancellazione ricevuta. Verrai contattato entro 30 giorni.',
      };
      this.dispatchEvent(
        new CustomEvent('afianco:erasure-requested', {
          detail: { request_id: resp.request_id },
          bubbles: true,
          composed: true,
        }),
      );
      this.erasureReason = '';
      this.erasureConfirm = false;
    } catch (e) {
      const msg = (e as { detail?: string; message?: string }).detail
        ?? (e as Error)?.message
        ?? t('profile.error_erasure_request');
      this.erasureMsg = { type: 'error', text: msg };
    } finally {
      this.requestingErasure = false;
    }
  }

  // ── Helper: toggle section ──────────────────────────────────────────

  private toggleSection(section: ActiveSection): void {
    this.activeSection = this.activeSection === section ? null : section;
  }

  // ── Styles ──────────────────────────────────────────────────────────

  static styles = [
    afiancoBaseStyles,
    css`
      :host { display: block; }
      .state-msg {
        padding: 24px;
        text-align: center;
        color: var(--afianco-color-text-secondary, #6b7280);
        font-size: 14px;
      }
      .state-msg.error { color: var(--afianco-color-danger, #ef4444); }

      .section {
        background: var(--afianco-color-surface, #ffffff);
        border: 1px solid var(--afianco-color-border, #e5e7eb);
        border-radius: 10px;
        margin-bottom: 10px;
        overflow: hidden;
      }
      .section-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 14px 16px;
        cursor: pointer;
        background: var(--afianco-color-surface, #ffffff);
        transition: background 0.15s ease;
        user-select: none;
      }
      .section-header:hover {
        background: var(--afianco-color-muted, #f9fafb);
      }
      .section-title {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 14px;
        font-weight: 600;
        color: var(--afianco-color-text, #111827);
      }
      .section-chevron {
        font-size: 18px;
        color: var(--afianco-color-text-secondary, #6b7280);
        transition: transform 0.2s ease;
      }
      .section[data-expanded='true'] .section-chevron {
        transform: rotate(180deg);
      }
      .section-body {
        padding: 0 16px 16px;
        border-top: 1px solid var(--afianco-color-border, #e5e7eb);
      }

      .form-row {
        display: flex;
        flex-direction: column;
        gap: 4px;
        margin-top: 12px;
      }
      .form-row label {
        font-size: 12px;
        font-weight: 600;
        color: var(--afianco-color-text-secondary, #6b7280);
      }
      input[type='text'],
      input[type='email'],
      input[type='tel'],
      input[type='password'],
      textarea,
      select {
        padding: 10px 12px;
        border: 1px solid var(--afianco-color-border, #e5e7eb);
        border-radius: 8px;
        font-family: inherit;
        font-size: 14px;
        background: var(--afianco-color-bg, #ffffff);
        color: var(--afianco-color-text, #111827);
        box-sizing: border-box;
        width: 100%;
      }
      input:focus, textarea:focus, select:focus {
        outline: 2px solid var(--afianco-color-primary, #4b72ce);
        outline-offset: 0;
      }
      textarea { resize: vertical; min-height: 60px; }

      .submit-row {
        margin-top: 14px;
        display: flex;
        gap: 8px;
        align-items: center;
        justify-content: space-between;
      }
      .btn-primary {
        background: var(--afianco-color-primary, #4b72ce);
        color: var(--afianco-color-primary-text, #ffffff);
        border: none;
        border-radius: 8px;
        padding: 10px 18px;
        font-family: inherit;
        font-size: 13px;
        font-weight: 600;
        cursor: pointer;
      }
      .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
      .btn-danger {
        background: var(--afianco-color-danger, #ef4444);
        color: white;
      }

      .feedback {
        margin-top: 10px;
        padding: 8px 12px;
        border-radius: 6px;
        font-size: 13px;
      }
      .feedback.success {
        background: #d1fae5;
        color: #065f46;
      }
      .feedback.error {
        background: #fef2f2;
        color: var(--afianco-color-danger, #ef4444);
      }

      .read-only-display {
        margin-top: 8px;
        padding: 10px 12px;
        background: var(--afianco-color-muted, #f9fafb);
        border-radius: 6px;
        font-size: 13px;
        color: var(--afianco-color-text-secondary, #6b7280);
      }
      .read-only-display strong {
        color: var(--afianco-color-text, #111827);
      }

      /* GDPR warning */
      .erasure-warning {
        background: #fef3c7;
        border-left: 3px solid #f59e0b;
        padding: 10px 14px;
        border-radius: 6px;
        font-size: 12px;
        color: #92400e;
        margin-top: 12px;
        line-height: 1.5;
      }

      .checkbox-row {
        display: flex;
        align-items: flex-start;
        gap: 8px;
        margin-top: 12px;
        font-size: 13px;
      }
      .checkbox-row input { margin-top: 3px; }
    `,
  ];

  // ── Render ──────────────────────────────────────────────────────────

  render() {
    if (this.loading && !this.profile) {
      return html`<div class="state-msg">${t('profile.loading')}</div>`;
    }
    if (this.error) {
      return html`<div class="state-msg error" role="alert">${this.error}</div>`;
    }
    if (!this.profile) {
      return html`<div class="state-msg">${t('profile.empty')}</div>`;
    }
    return html`
      ${this.renderProfileSection()}
      ${this.renderPasswordSection()}
      ${this.renderErasureSection()}
    `;
  }

  private renderProfileSection() {
    const expanded = this.activeSection === 'profile';
    return html`
      <div class="section" data-expanded=${expanded ? 'true' : 'false'}>
        <div
          class="section-header"
          role="button"
          tabindex="0"
          @click=${() => this.toggleSection('profile')}
          @keydown=${(e: KeyboardEvent) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              this.toggleSection('profile');
            }
          }}>
          <span class="section-title">
            <span aria-hidden="true">👤</span>
            ${t('profile.section_title_edit')}
          </span>
          <span class="section-chevron" aria-hidden="true">▾</span>
        </div>
        ${expanded
          ? html`
              <div class="section-body">
                <div class="read-only-display">
                  <strong>Email:</strong> ${this.profile?.email}
                  ${(this.profile as CustomerProfile & { email_verified?: boolean })?.email_verified
                    ? html` <span style="color:#10b981;">✓ Verificata</span>`
                    : ''}
                </div>
                <form @submit=${(e: Event) => void this.saveProfile(e)}>
                  <div class="form-row">
                    <label for="profile-name">Nome*</label>
                    <input
                      id="profile-name"
                      type="text"
                      required
                      .value=${this.editName}
                      @input=${(e: InputEvent) =>
                        (this.editName = (e.target as HTMLInputElement).value)}>
                  </div>
                  <div class="form-row">
                    <label for="profile-phone">${t('profile.phone_label_full')}</label>
                    <input
                      id="profile-phone"
                      type="tel"
                      placeholder="+39 333 1234567"
                      .value=${this.editPhone}
                      @input=${(e: InputEvent) =>
                        (this.editPhone = (e.target as HTMLInputElement).value)}>
                  </div>
                  <div class="form-row">
                    <label for="profile-locale">Lingua</label>
                    <select
                      id="profile-locale"
                      .value=${this.editLocale}
                      @change=${(e: Event) =>
                        (this.editLocale = (e.target as HTMLSelectElement).value)}>
                      <option value="it">${t('profile.locale_italian')}</option>
                      <option value="en">English</option>
                      <option value="de">Deutsch</option>
                      <option value="fr">Français</option>
                    </select>
                  </div>
                  ${this.profileMsg
                    ? html`<div class="feedback ${this.profileMsg.type}" role="status">${this.profileMsg.text}</div>`
                    : nothing}
                  <div class="submit-row">
                    <button
                      class="btn-primary"
                      type="submit"
                      ?disabled=${this.savingProfile}>
                      ${this.savingProfile ? t('profile.saving') : t('profile.save')}
                    </button>
                  </div>
                </form>
              </div>
            `
          : ''}
      </div>
    `;
  }

  private renderPasswordSection() {
    const expanded = this.activeSection === 'password';
    return html`
      <div class="section" data-expanded=${expanded ? 'true' : 'false'}>
        <div
          class="section-header"
          role="button"
          tabindex="0"
          @click=${() => this.toggleSection('password')}
          @keydown=${(e: KeyboardEvent) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              this.toggleSection('password');
            }
          }}>
          <span class="section-title">
            <span aria-hidden="true">🔑</span>
            ${t('profile.password_section_title')}
          </span>
          <span class="section-chevron" aria-hidden="true">▾</span>
        </div>
        ${expanded
          ? html`
              <div class="section-body">
                <form @submit=${(e: Event) => void this.savePassword(e)}>
                  <div class="form-row">
                    <label for="pw-current">Password attuale*</label>
                    <input
                      id="pw-current"
                      type="password"
                      required
                      autocomplete="current-password"
                      .value=${this.currentPw}
                      @input=${(e: InputEvent) =>
                        (this.currentPw = (e.target as HTMLInputElement).value)}>
                  </div>
                  <div class="form-row">
                    <label for="pw-new">${t('profile.password_min_label_full')}</label>
                    <input
                      id="pw-new"
                      type="password"
                      required
                      minlength="8"
                      autocomplete="new-password"
                      .value=${this.newPw}
                      @input=${(e: InputEvent) =>
                        (this.newPw = (e.target as HTMLInputElement).value)}>
                  </div>
                  <div class="form-row">
                    <label for="pw-confirm">Conferma nuova password*</label>
                    <input
                      id="pw-confirm"
                      type="password"
                      required
                      minlength="8"
                      autocomplete="new-password"
                      .value=${this.confirmPw}
                      @input=${(e: InputEvent) =>
                        (this.confirmPw = (e.target as HTMLInputElement).value)}>
                  </div>
                  ${this.passwordMsg
                    ? html`<div class="feedback ${this.passwordMsg.type}" role="status">${this.passwordMsg.text}</div>`
                    : nothing}
                  <div class="submit-row">
                    <button
                      class="btn-primary"
                      type="submit"
                      ?disabled=${this.savingPw}>
                      ${this.savingPw ? t('profile.saving') : t('profile.password_change_btn')}
                    </button>
                  </div>
                </form>
              </div>
            `
          : ''}
      </div>
    `;
  }

  private renderErasureSection() {
    const expanded = this.activeSection === 'erasure';
    return html`
      <div class="section" data-expanded=${expanded ? 'true' : 'false'}>
        <div
          class="section-header"
          role="button"
          tabindex="0"
          @click=${() => this.toggleSection('erasure')}
          @keydown=${(e: KeyboardEvent) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              this.toggleSection('erasure');
            }
          }}>
          <span class="section-title">
            <span aria-hidden="true">🗑️</span>
            ${t('profile.erasure_section_title')}
          </span>
          <span class="section-chevron" aria-hidden="true">▾</span>
        </div>
        ${expanded
          ? html`
              <div class="section-body">
                <div class="erasure-warning">
                  <strong>Importante:</strong> la cancellazione e' irreversibile.
                  Tutti i tuoi dati (profilo, ordini, prenotazioni) verranno
                  rimossi entro 30 giorni dall'invio della richiesta, in
                  conformita' con l'Art.17 GDPR. Sarai contattato via email
                  per conferma.
                </div>
                <form @submit=${(e: Event) => void this.submitErasure(e)}>
                  <div class="form-row">
                    <label for="erasure-reason">${t('profile.erasure_reason_label')}</label>
                    <textarea
                      id="erasure-reason"
                      rows="2"
                      placeholder="Aiutaci a capire perche' vuoi cancellare l'account"
                      .value=${this.erasureReason}
                      @input=${(e: Event) =>
                        (this.erasureReason = (e.target as HTMLTextAreaElement).value)}></textarea>
                  </div>
                  <div class="checkbox-row">
                    <input
                      id="erasure-confirm"
                      type="checkbox"
                      .checked=${this.erasureConfirm}
                      @change=${(e: Event) =>
                        (this.erasureConfirm = (e.target as HTMLInputElement).checked)}>
                    <label for="erasure-confirm">${t('profile.erasure_confirm_label')}</label>
                  </div>
                  ${this.erasureMsg
                    ? html`<div class="feedback ${this.erasureMsg.type}" role="status">${this.erasureMsg.text}</div>`
                    : nothing}
                  <div class="submit-row">
                    <button
                      class="btn-primary btn-danger"
                      type="submit"
                      ?disabled=${this.requestingErasure || !this.erasureConfirm}>
                      ${this.requestingErasure ? t('profile.erasure_submitting') : t('profile.erasure_submit')}
                    </button>
                  </div>
                </form>
              </div>
            `
          : ''}
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'afianco-profile-editor': AfiancoProfileEditor;
  }
  interface HTMLElementEventMap {
    'afianco:profile-updated': CustomEvent<{ profile: CustomerProfile }>;
    'afianco:password-changed': CustomEvent;
    'afianco:erasure-requested': CustomEvent<{ request_id: string }>;
  }
}
