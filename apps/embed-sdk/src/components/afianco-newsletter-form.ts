/**
 * <afianco-newsletter-form> — F2 (modulo Newsletter).
 *
 * Form di iscrizione newsletter embeddabile, AUTONOMO: non dipende dallo
 * storefront-context / kernel / client store-centrici, perché il form può
 * vivere standalone su qualsiasi sito (anche senza store). Legge:
 *   - ``form-id`` (required): id del form (uuid) → identità embed pubblica.
 *   - ``base-url`` (optional): origin del backend; fallback a getPageConfig().
 *   - ``source`` (optional): etichetta sorgente (D7), es. "blog-footer".
 *
 * Flusso: fetch config pubblica → render campi (built-in + custom) →
 * validazione + consenso → POST submit con sorgente (window.location.href,
 * document.referrer, attributo source) → messaggio di successo / redirect.
 *
 * Custom events:
 *   - afianco:newsletter-subscribed (detail: { email, subscriber_id })
 */

import { LitElement, html, css, nothing } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { afiancoBaseStyles } from '@afianco/design-tokens';
import type {
  NewsletterFormPublic,
  NewsletterFieldConfig,
  NewsletterSubmitResponse,
} from '@afianco/api-client';
import type { PropertyValues } from 'lit';
import { t } from '../i18n/index.js';
import { getPageConfig } from '../store/page-config.js';

type Status = 'loading' | 'ready' | 'submitting' | 'done' | 'error';

@customElement('afianco-newsletter-form')
export class AfiancoNewsletterForm extends LitElement {
  /** Id del form (uuid) — identità embed pubblica. */
  @property({ type: String, attribute: 'form-id' })
  formId = '';

  /** Origin backend; fallback a data-afianco-base-url della pagina. */
  @property({ type: String, attribute: 'base-url' })
  baseUrl = '';

  /** Etichetta sorgente (D7) per attribuzione campagna/posizionamento. */
  @property({ type: String })
  source = '';

  /** F7 — config iniettata (admin preview): se presente bypassa il fetch. */
  @property({ attribute: false })
  config: NewsletterFormPublic | null = null;

  /** F7 — modalità preview: nessun submit reale (mostra solo l'esito locale). */
  @property({ type: Boolean })
  preview = false;

  @state() private status: Status = 'loading';
  @state() private error: string | null = null;
  /** Valori dei campi: built-in (name/phone) + custom (per FieldConfig.id). */
  @state() private values: Record<string, string> = {};
  @state() private email = '';
  @state() private consent = false;
  /** Honeypot: deve restare vuoto; se valorizzato → bot. */
  @state() private hp = '';

  private resolvedBaseUrl(): string {
    return (this.baseUrl || getPageConfig().baseUrl || '').replace(/\/$/, '');
  }

  connectedCallback(): void {
    super.connectedCallback();
    // F7 — in preview (config iniettata o attributo preview) NON si fetcha.
    if (this.config) {
      this.status = 'ready';
      this.applyTheme();
    } else if (!this.preview) {
      void this.loadConfig();
    }
  }

  willUpdate(changed: PropertyValues): void {
    // F7 — quando l'admin aggiorna la config iniettata (preview live),
    // ripassa a 'ready' e riapplica i colori senza rifare il fetch.
    if (changed.has('config') && this.config) {
      if (this.status === 'loading' || this.status === 'error') {
        this.status = 'ready';
      }
      this.applyTheme();
    }
  }

  /** Mappa il theme del form alle CSS custom properties dell'host.
   *  Set-or-remove così l'anteprima live riflette anche il reset di un colore. */
  private applyTheme(): void {
    const theme = this.config?.theme;
    const apply = (cssVar: string, value?: string | null) => {
      if (value) this.style.setProperty(cssVar, value);
      else this.style.removeProperty(cssVar);
    };
    apply('--afianco-color-primary', theme?.primary_color);
    apply('--afianco-color-primary-contrast', theme?.primary_text_color);
  }

  private async loadConfig(): Promise<void> {
    if (!this.formId) {
      this.status = 'error';
      this.error = t('newsletter.error_misconfigured');
      return;
    }
    this.status = 'loading';
    this.error = null;
    try {
      const res = await fetch(
        `${this.resolvedBaseUrl()}/api/public/embed/newsletter/${encodeURIComponent(this.formId)}`,
        { method: 'GET', headers: { Accept: 'application/json' } },
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      this.config = (await res.json()) as NewsletterFormPublic;
      this.status = 'ready';
    } catch {
      this.status = 'error';
      this.error = t('newsletter.error_load');
    }
  }

  private sortedFields(): NewsletterFieldConfig[] {
    return [...(this.config?.field_configs ?? [])].sort(
      (a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0),
    );
  }

  private onInput(key: string, e: Event): void {
    const target = e.target as HTMLInputElement;
    this.values = { ...this.values, [key]: target.value };
  }

  private validate(): string | null {
    const emailOk = /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(this.email.trim());
    if (!emailOk) return t('newsletter.error_email');
    if (this.config?.privacy_required && !this.consent) {
      return t('newsletter.error_consent');
    }
    for (const fc of this.sortedFields()) {
      if (fc.required) {
        const v = (this.values[fc.id] ?? '').trim();
        if (!v) return t('newsletter.error_required');
      }
    }
    return null;
  }

  private async handleSubmit(e: Event): Promise<void> {
    e.preventDefault();
    if (this.status === 'submitting') return;
    const err = this.validate();
    if (err) {
      this.error = err;
      return;
    }
    this.error = null;

    // F7 — preview: nessuna chiamata di rete, mostra solo l'esito.
    if (this.preview) {
      this.status = 'done';
      return;
    }

    this.status = 'submitting';

    // Campi custom (esclusi i built-in name/phone gestiti a parte).
    const fields_data: Record<string, unknown> = {};
    for (const fc of this.sortedFields()) {
      if (this.values[fc.id] != null && this.values[fc.id] !== '') {
        fields_data[fc.id] = this.values[fc.id];
      }
    }

    const body = {
      email: this.email.trim(),
      name: this.config?.collect_name ? this.values.__name ?? null : null,
      phone: this.config?.collect_phone ? this.values.__phone ?? null : null,
      fields_data,
      consent_privacy: this.consent,
      // D7 — sorgente lato client.
      source_url: typeof window !== 'undefined' ? window.location.href : null,
      source_referrer: typeof document !== 'undefined' ? document.referrer || null : null,
      source_label: this.source || null,
      hp: this.hp || null,
    };

    try {
      const res = await fetch(
        `${this.resolvedBaseUrl()}/api/public/embed/newsletter/${encodeURIComponent(this.formId)}/submit`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
          body: JSON.stringify(body),
        },
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = (await res.json()) as NewsletterSubmitResponse;
      this.status = 'done';
      this.dispatchEvent(
        new CustomEvent<{ email: string; subscriber_id?: string | null }>(
          'afianco:newsletter-subscribed',
          {
            detail: { email: body.email, subscriber_id: data.subscriber_id },
            bubbles: true,
            composed: true,
          },
        ),
      );
      const redirect = this.config?.redirect_url;
      if (redirect && typeof window !== 'undefined') {
        window.location.href = redirect;
      }
    } catch {
      this.status = 'error';
      this.error = t('newsletter.error_submit');
    }
  }

  static styles = [
    afiancoBaseStyles,
    css`
      :host { display: block; }
      form { display: flex; flex-direction: column; gap: 12px; }
      .field { display: flex; flex-direction: column; gap: 5px; min-width: 0; }
      label { font-size: 13px; font-weight: 500; color: var(--afianco-color-text-secondary, #6b7280); }
      input, textarea, select {
        width: 100%; box-sizing: border-box;
        padding: 11px 13px; border: 1.5px solid var(--afianco-color-border, #e5e7eb);
        border-radius: 10px; font-family: inherit; font-size: 14px;
        color: var(--afianco-color-text, #111827); background: var(--afianco-color-surface, #fff);
        transition: border-color 0.15s ease, box-shadow 0.15s ease;
      }
      input:focus, textarea:focus, select:focus {
        outline: none; border-color: var(--afianco-color-primary, #4b72ce);
        box-shadow: 0 0 0 3px color-mix(in srgb, var(--afianco-color-primary, #4b72ce) 18%, transparent);
      }
      .consent { display: flex; align-items: flex-start; gap: 8px; font-size: 13px; color: var(--afianco-color-text-secondary, #6b7280); }
      .consent input { width: auto; }
      .privacy-link { color: var(--afianco-color-primary, #4b72ce); text-decoration: underline; }
      /* Honeypot: invisibile agli umani, riempito solo dai bot. */
      .hp { position: absolute; left: -9999px; width: 1px; height: 1px; overflow: hidden; }
      button {
        padding: 11px 18px; border: none; border-radius: 10px; cursor: pointer;
        font-size: 14px; font-weight: 600; color: var(--afianco-color-primary-contrast, #fff);
        background: var(--afianco-color-primary, #4b72ce);
        transition: filter 0.15s ease, transform 0.05s ease;
      }
      button:hover:not([disabled]) { filter: brightness(0.94); }
      button:active:not([disabled]) { transform: translateY(1px); }
      button[disabled] { opacity: 0.6; cursor: default; }
      .error { font-size: 13px; color: var(--afianco-color-danger, #ef4444); background: #fef2f2; border-radius: 8px; padding: 8px 12px; }
      .success { font-size: 14px; color: var(--afianco-color-success, #16a34a); background: #f0fdf4; border-radius: 10px; padding: 14px; }
      .muted { font-size: 13px; color: var(--afianco-color-text-secondary, #6b7280); }

      /* ── Layout: orizzontale (campi distribuiti in riga, responsive) ── */
      form[data-layout='horizontal'] {
        flex-direction: row; flex-wrap: wrap; align-items: flex-end; gap: 12px;
      }
      form[data-layout='horizontal'] .field { flex: 1 1 180px; }
      form[data-layout='horizontal'] button { flex: 0 0 auto; align-self: flex-end; }
      form[data-layout='horizontal'] .consent,
      form[data-layout='horizontal'] .error,
      form[data-layout='horizontal'] .success { flex-basis: 100%; }

      /* ── Layout: inline (compatto, label nascoste → placeholder) ── */
      form[data-layout='inline'] {
        flex-direction: row; flex-wrap: wrap; align-items: flex-end; gap: 8px;
      }
      form[data-layout='inline'] .field { flex: 1 1 160px; }
      form[data-layout='inline'] .field label { display: none; }
      form[data-layout='inline'] button { flex: 0 0 auto; }
      form[data-layout='inline'] .consent,
      form[data-layout='inline'] .error,
      form[data-layout='inline'] .success { flex-basis: 100%; }

      /* Responsive senza media query (un widget embed non conosce il viewport
         del sito ospite): il flex-wrap distribuisce i campi in riga quando il
         container è largo e li manda a capo (riga propria) quando è stretto.
         Container-query come progressive enhancement: se l'host è strettissimo,
         i layout in riga ripristinano le label dell'inline per leggibilità. */
      :host { container-type: inline-size; }
      @container (max-width: 340px) {
        form[data-layout='inline'] .field label { display: block; }
      }
    `,
  ];

  render() {
    if (this.status === 'loading') {
      return html`<div class="muted">${t('newsletter.loading')}</div>`;
    }
    if (this.status === 'error' && !this.config) {
      return html`<div class="error" role="alert">${this.error}</div>`;
    }
    if (this.status === 'done') {
      return html`<div class="success" role="status">
        ${this.config?.success_message || t('newsletter.success')}
      </div>`;
    }

    const cfg = this.config!;
    // F8 — layout selezionabile (vertical | horizontal | inline). Il NOME del
    // form è solo un'etichetta admin: NON va mostrato nel form pubblico.
    const layout = cfg.layout || 'vertical';
    return html`
      <form data-layout=${layout} @submit=${this.handleSubmit} novalidate>
        <div class="field">
          <label for="nl-email">${t('newsletter.email_label')}</label>
          <input id="nl-email" type="email" required
            placeholder=${t('newsletter.email_label')}
            aria-label=${t('newsletter.email_label')}
            .value=${this.email}
            @input=${(e: Event) => (this.email = (e.target as HTMLInputElement).value)}>
        </div>

        ${cfg.collect_name ? html`
          <div class="field">
            <label for="nl-name">${t('newsletter.name_label')}</label>
            <input id="nl-name" type="text"
              placeholder=${t('newsletter.name_label')}
              aria-label=${t('newsletter.name_label')}
              .value=${this.values.__name ?? ''}
              @input=${(e: Event) => this.onInput('__name', e)}>
          </div>` : nothing}

        ${cfg.collect_phone ? html`
          <div class="field">
            <label for="nl-phone">${t('newsletter.phone_label')}</label>
            <input id="nl-phone" type="tel"
              placeholder=${t('newsletter.phone_label')}
              aria-label=${t('newsletter.phone_label')}
              .value=${this.values.__phone ?? ''}
              @input=${(e: Event) => this.onInput('__phone', e)}>
          </div>` : nothing}

        ${this.sortedFields().map((fc) => this.renderField(fc))}

        ${cfg.privacy_required ? html`
          <label class="consent">
            <input type="checkbox" .checked=${this.consent}
              @change=${(e: Event) => (this.consent = (e.target as HTMLInputElement).checked)}>
            <span>
              ${cfg.consent_text || t('newsletter.privacy_label')}
              ${cfg.privacy_policy_url ? html`
                <a class="privacy-link" href=${cfg.privacy_policy_url}
                  target="_blank" rel="noopener noreferrer"
                  @click=${(e: Event) => e.stopPropagation()}>
                  ${t('newsletter.privacy_link')}
                </a>` : nothing}
            </span>
          </label>` : nothing}

        <!-- Honeypot anti-bot: nascosto, mai compilato da un umano. -->
        <div class="hp" aria-hidden="true">
          <label>Non compilare<input type="text" tabindex="-1" autocomplete="off"
            .value=${this.hp}
            @input=${(e: Event) => (this.hp = (e.target as HTMLInputElement).value)}></label>
        </div>

        ${this.error ? html`<div class="error" role="alert">${this.error}</div>` : nothing}

        <button type="submit" ?disabled=${this.status === 'submitting'}>
          ${this.status === 'submitting' ? t('newsletter.submitting') : t('newsletter.submit')}
        </button>
      </form>
    `;
  }

  private renderField(fc: NewsletterFieldConfig) {
    const val = this.values[fc.id] ?? '';
    const onInput = (e: Event) => this.onInput(fc.id, e);
    let control;
    if (fc.type === 'textarea') {
      control = html`<textarea id="nl-${fc.id}" ?required=${fc.required}
        placeholder=${fc.placeholder ?? ''} .value=${val} @input=${onInput}></textarea>`;
    } else if (fc.type === 'select') {
      control = html`<select id="nl-${fc.id}" ?required=${fc.required}
        .value=${val} @change=${onInput}>
        <option value="">—</option>
        ${(fc.options ?? []).map((o) => html`<option value=${o}>${o}</option>`)}
      </select>`;
    } else if (fc.type === 'checkbox') {
      control = html`<label class="consent"><input type="checkbox"
        .checked=${val === 'true'}
        @change=${(e: Event) =>
          (this.values = { ...this.values, [fc.id]: (e.target as HTMLInputElement).checked ? 'true' : '' })}>
        <span>${fc.label}</span></label>`;
    } else {
      const inputType = fc.type === 'email' ? 'email' : fc.type === 'tel' ? 'tel' : fc.type === 'number' ? 'number' : 'text';
      control = html`<input id="nl-${fc.id}" type=${inputType} ?required=${fc.required}
        placeholder=${fc.placeholder ?? ''} .value=${val} @input=${onInput}>`;
    }
    // Per il checkbox la label è inline; per gli altri sopra.
    if (fc.type === 'checkbox') {
      return html`<div class="field">${control}${fc.help_text ? html`<span class="muted">${fc.help_text}</span>` : nothing}</div>`;
    }
    return html`<div class="field">
      <label for="nl-${fc.id}">${fc.label}${fc.required ? ' *' : ''}</label>
      ${control}
      ${fc.help_text ? html`<span class="muted">${fc.help_text}</span>` : nothing}
    </div>`;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'afianco-newsletter-form': AfiancoNewsletterForm;
  }
  interface HTMLElementEventMap {
    'afianco:newsletter-subscribed': CustomEvent<{ email: string; subscriber_id?: string | null }>;
  }
}
