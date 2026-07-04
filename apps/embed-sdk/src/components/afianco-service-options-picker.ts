/**
 * <afianco-service-options-picker> — Track E Step 2.4.7 (service variants).
 *
 * Radio picker per le opzioni di un service product. Mirror del React
 * component nel storefront (ProductLandingPage → service options radio
 * cards). Esempio uso:
 *
 *   <afianco-service-options-picker
 *     .options=${product.service_options}
 *     currency=${currency}
 *     selected=${selectedId}
 *     @afianco:service-option-selected=${e => this.selectedId = e.detail.option.id}>
 *   </afianco-service-options-picker>
 *
 * Custom events:
 *   - afianco:service-option-selected (detail: { option: EmbedServiceOption })
 *
 * Accessibility:
 *   - role="radiogroup" con aria-label localizzato
 *   - Ogni card ha role="radio" + aria-checked
 *   - Keyboard nav (tab + arrow keys built-in dal browser per radio)
 */

import { LitElement, html, css, nothing } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { afiancoBaseStyles } from '@afianco/design-tokens';
import type { EmbedServiceOption } from '@afianco/api-client';
// W4.9 — i18n
import { t } from '../i18n/index.js';


@customElement('afianco-service-options-picker')
export class AfiancoServiceOptionsPicker extends LitElement {
  /** Lista delle opzioni del servizio (da EmbedProductDetail.service_options). */
  @property({ type: Array })
  options: EmbedServiceOption[] = [];

  /** Currency ISO code per il formatting del prezzo (es. "EUR"). */
  @property({ type: String })
  currency = 'EUR';

  /** ID dell'opzione attualmente selezionata. */
  @property({ type: String })
  selected: string | null = null;

  /** Label legend del gruppo (i18n via prop). */
  @property({ type: String, attribute: 'group-label' })
  groupLabel = ''; // W4.9 — fallback at render via t('service.group_label')

  // ── Handlers ────────────────────────────────────────────────────────

  private handleSelect(option: EmbedServiceOption): void {
    this.selected = option.id;
    this.dispatchEvent(
      new CustomEvent<{ option: EmbedServiceOption }>(
        'afianco:service-option-selected',
        {
          detail: { option },
          bubbles: true,
          composed: true,
        },
      ),
    );
  }

  // ── Helpers ─────────────────────────────────────────────────────────

  private formatPrice(amount: number): string {
    try {
      return new Intl.NumberFormat(undefined, {
        style: 'currency',
        currency: this.currency,
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }).format(amount);
    } catch {
      return `${amount.toFixed(2)} ${this.currency}`;
    }
  }

  // ── Styles ──────────────────────────────────────────────────────────

  static styles = [
    afiancoBaseStyles,
    css`
      :host {
        display: block;
      }
      .group-label {
        font-size: 13px;
        font-weight: 600;
        color: var(--afianco-color-text, #111827);
        margin-bottom: 10px;
        display: block;
      }
      .options {
        display: flex;
        flex-direction: column;
        gap: 8px;
      }
      .option {
        display: flex;
        align-items: flex-start;
        gap: 12px;
        padding: 14px 16px;
        border: 1.5px solid var(--afianco-color-border, #e5e7eb);
        border-radius: 10px;
        cursor: pointer;
        transition: border-color 0.15s ease, background 0.15s ease;
        background: var(--afianco-color-surface, #ffffff);
      }
      .option:hover {
        border-color: var(--afianco-color-primary, #4b72ce);
        background: var(--afianco-color-muted, #f9fafb);
      }
      .option[aria-checked='true'] {
        border-color: var(--afianco-color-primary, #4b72ce);
        background: var(--afianco-color-primary-soft, #eef2ff);
      }
      .option:focus-visible {
        outline: 2px solid var(--afianco-color-primary, #4b72ce);
        outline-offset: 2px;
      }
      .radio {
        flex-shrink: 0;
        width: 18px;
        height: 18px;
        border-radius: 50%;
        border: 1.5px solid var(--afianco-color-border-strong, #d1d5db);
        position: relative;
        margin-top: 2px;
      }
      .option[aria-checked='true'] .radio {
        border-color: var(--afianco-color-primary, #4b72ce);
        background: var(--afianco-color-bg, #ffffff);
      }
      .option[aria-checked='true'] .radio::after {
        content: '';
        position: absolute;
        inset: 3px;
        border-radius: 50%;
        background: var(--afianco-color-primary, #4b72ce);
      }
      .body {
        flex: 1;
        min-width: 0;
      }
      .label-row {
        display: flex;
        align-items: baseline;
        gap: 8px;
        justify-content: space-between;
      }
      .label {
        font-size: 14px;
        font-weight: 600;
        color: var(--afianco-color-text, #111827);
      }
      .price {
        font-size: 14px;
        font-weight: 700;
        color: var(--afianco-color-text, #111827);
        flex-shrink: 0;
      }
      .description {
        font-size: 13px;
        color: var(--afianco-color-text-secondary, #6b7280);
        margin-top: 4px;
        line-height: 1.5;
      }
      .duration {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        font-size: 12px;
        color: var(--afianco-color-text-secondary, #6b7280);
        margin-top: 4px;
      }
      .empty {
        font-size: 13px;
        color: var(--afianco-color-text-muted, #9ca3af);
        font-style: italic;
        padding: 8px 0;
      }
    `,
  ];

  // ── Render ──────────────────────────────────────────────────────────

  render() {
    if (!this.options || this.options.length === 0) {
      return html`<div class="empty">${t('service.empty_options')}</div>`;
    }

    return html`
      <span class="group-label">${this.groupLabel || t('service.group_label')}</span>
      <div class="options" role="radiogroup" aria-label=${this.groupLabel || t('service.group_label')}>
        ${this.options.map((opt) => {
          const checked = this.selected === opt.id;
          return html`
            <div
              class="option"
              role="radio"
              aria-checked=${checked ? 'true' : 'false'}
              tabindex=${checked ? '0' : '-1'}
              @click=${() => this.handleSelect(opt)}
              @keydown=${(e: KeyboardEvent) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  this.handleSelect(opt);
                }
              }}>
              <span class="radio" aria-hidden="true"></span>
              <div class="body">
                <div class="label-row">
                  <span class="label">${opt.label}</span>
                  <span class="price">${this.formatPrice(opt.price)}</span>
                </div>
                ${opt.description
                  ? html`<div class="description">${opt.description}</div>`
                  : nothing}
                ${opt.duration_minutes_override
                  ? html`
                      <div class="duration">
                        <span aria-hidden="true">⏱</span>
                        ${opt.duration_minutes_override} min
                      </div>
                    `
                  : nothing}
              </div>
            </div>
          `;
        })}
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'afianco-service-options-picker': AfiancoServiceOptionsPicker;
  }
  interface HTMLElementEventMap {
    'afianco:service-option-selected': CustomEvent<{ option: EmbedServiceOption }>;
  }
}
