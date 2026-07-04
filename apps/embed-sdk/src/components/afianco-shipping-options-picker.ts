/**
 * <afianco-shipping-options-picker> — Track E Step 4.2 (tariffe spedizione).
 *
 * Radio picker delle ShippingOption configurate dal merchant per il store.
 * Fetcha automaticamente da GET /api/public/embed/shipping-options/{slug}
 * on mount + dispatch event al cambio selezione.
 *
 * UX:
 *   - Radio cards con label + descrizione + base_price formattato in currency
 *   - Badge "Spedizione gratuita oltre €X" quando free_shipping_threshold settato
 *     E subtotale corrente >= threshold → badge verde "✓ Gratis"
 *   - Empty state: "Nessuna opzione di spedizione configurata. Contatta il
 *     fornitore per ricevere il tuo ordine."
 *
 * Custom events:
 *   - afianco:shipping-option-selected (detail: { option: EmbedShippingOption })
 *
 * Attributes:
 *   - subtotal: number (cart subtotal, per check free_shipping_threshold)
 *   - currency: string (es. "EUR")
 *   - selected-id: string | null (id dell'option selezionata, controlled)
 */

import { LitElement, html, css, nothing, type PropertyValues } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { consume } from '@lit/context';
import { afiancoBaseStyles } from '@afianco/design-tokens';
// Sprint 4 W4.7 — i18n wiring
import { t } from '../i18n/index.js';
import type { EmbedShippingOption } from '@afianco/api-client';
import {
  storefrontContext,
  STOREFRONT_INITIAL,
  type StorefrontContext,
} from '../context.js';


@customElement('afianco-shipping-options-picker')
export class AfiancoShippingOptionsPicker extends LitElement {
  @consume({ context: storefrontContext, subscribe: true })
  @state()
  ctx: StorefrontContext = STOREFRONT_INITIAL;

  /** Cart subtotal corrente per applicare free_shipping_threshold. */
  @property({ type: Number })
  subtotal = 0;

  /** Currency formatting (ISO 4217). */
  @property({ type: String })
  currency = 'EUR';

  /** Id dell'opzione selezionata (controlled). Auto-select first se null al fetch. */
  @property({ type: String, attribute: 'selected-id' })
  selectedId: string | null = null;

  /** Label gruppo. */
  @property({ type: String, attribute: 'group-label' })
  groupLabel = ''; // W4.9 — fallback at render via t('shipping.group_label')

  // ── Internal state ────────────────────────────────────────────────────

  @state()
  private options: EmbedShippingOption[] = [];

  @state()
  private loading = false;

  @state()
  private error: string | null = null;

  private _initialized = false;

  // ── Lifecycle ────────────────────────────────────────────────────────

  protected updated(_changed: PropertyValues): void {
    if (this._initialized) return;
    if (this.ctx?.status !== 'ready' || !this.ctx.client) return;
    this._initialized = true;
    void this.fetchOptions();
  }

  private async fetchOptions(): Promise<void> {
    if (!this.ctx?.client) return;
    this.loading = true;
    this.error = null;
    try {
      const resp = await this.ctx.client.embed.getShippingOptions();
      this.options = resp.options ?? [];
      // Auto-select prima opzione se nessuna selezionata (UX shortcut)
      if (!this.selectedId && this.options.length > 0) {
        this.handleSelect(this.options[0]!);
      }
    } catch (e) {
      this.error = (e as Error)?.message ?? t('shipping.error_load');
    } finally {
      this.loading = false;
    }
  }

  private handleSelect(option: EmbedShippingOption): void {
    this.selectedId = option.id;
    this.dispatchEvent(
      new CustomEvent<{ option: EmbedShippingOption }>(
        'afianco:shipping-option-selected',
        {
          detail: { option },
          bubbles: true,
          composed: true,
        },
      ),
    );
  }

  private formatPrice(amt: number): string {
    try {
      return new Intl.NumberFormat(undefined, {
        style: 'currency',
        currency: this.currency,
        minimumFractionDigits: 2,
      }).format(amt);
    } catch {
      return `${amt.toFixed(2)} ${this.currency}`;
    }
  }

  /** Free shipping applicabile a questa option al subtotal corrente? */
  private isFreeShippingEligible(o: EmbedShippingOption): boolean {
    if (o.free_shipping_threshold == null) return false;
    return this.subtotal >= o.free_shipping_threshold;
  }

  // ── Styles ──────────────────────────────────────────────────────────

  static styles = [
    afiancoBaseStyles,
    css`
      :host { display: block; }
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
        padding: 12px 14px;
        border: 1.5px solid var(--afianco-color-border, #e5e7eb);
        border-radius: 10px;
        cursor: pointer;
        background: var(--afianco-color-surface, #ffffff);
        transition: border-color 0.15s ease, background 0.15s ease;
      }
      .option:hover {
        border-color: var(--afianco-color-primary, #4b72ce);
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
      }
      .option[aria-checked='true'] .radio::after {
        content: '';
        position: absolute;
        inset: 3px;
        border-radius: 50%;
        background: var(--afianco-color-primary, #4b72ce);
      }
      .body { flex: 1; min-width: 0; }
      .header-row {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        gap: 10px;
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
        white-space: nowrap;
      }
      .price.free {
        color: var(--afianco-color-success, #10b981);
      }
      .price.free-with-strike {
        display: inline-flex;
        align-items: baseline;
        gap: 6px;
      }
      .price-original {
        text-decoration: line-through;
        font-size: 12px;
        font-weight: 500;
        color: var(--afianco-color-text-muted, #9ca3af);
      }
      .description {
        font-size: 12px;
        color: var(--afianco-color-text-secondary, #6b7280);
        margin-top: 4px;
        line-height: 1.4;
      }
      .free-hint {
        font-size: 11px;
        color: var(--afianco-color-text-secondary, #6b7280);
        margin-top: 4px;
        font-style: italic;
      }
      .empty, .state-msg {
        padding: 16px;
        background: var(--afianco-color-muted, #f3f4f6);
        border-radius: 8px;
        font-size: 13px;
        color: var(--afianco-color-text-secondary, #6b7280);
        text-align: center;
      }
      .state-msg.error {
        color: var(--afianco-color-danger, #ef4444);
        background: #fef2f2;
      }
    `,
  ];

  // ── Render ──────────────────────────────────────────────────────────

  render() {
    if (this.loading && this.options.length === 0) {
      return html`<div class="state-msg">${t('shipping.loading')}</div>`;
    }
    if (this.error) {
      return html`<div class="state-msg error" role="alert">${this.error}</div>`;
    }
    if (this.options.length === 0) {
      return html`
        <div class="empty">${t('shipping.empty')}</div>
      `;
    }
    return html`
      <span class="group-label">${this.groupLabel || t('shipping.group_label')}</span>
      <div class="options" role="radiogroup" aria-label=${this.groupLabel || t('shipping.group_label')}>
        ${this.options
          .slice()
          .sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0))
          .map((o) => {
            const checked = this.selectedId === o.id;
            const isFree = this.isFreeShippingEligible(o);
            return html`
              <div
                class="option"
                role="radio"
                aria-checked=${checked ? 'true' : 'false'}
                tabindex=${checked ? '0' : '-1'}
                @click=${() => this.handleSelect(o)}
                @keydown=${(e: KeyboardEvent) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    this.handleSelect(o);
                  }
                }}>
                <span class="radio" aria-hidden="true"></span>
                <div class="body">
                  <div class="header-row">
                    <span class="label">${o.label}</span>
                    ${isFree
                      ? html`
                          <span class="price free-with-strike">
                            <span class="price-original">${this.formatPrice(o.base_price)}</span>
                            <span class="price free">✓ Gratis</span>
                          </span>
                        `
                      : o.base_price === 0
                        ? html`<span class="price free">Gratis</span>`
                        : html`<span class="price">${this.formatPrice(o.base_price)}</span>`}
                  </div>
                  ${o.description
                    ? html`<div class="description">${o.description}</div>`
                    : nothing}
                  ${!isFree && o.free_shipping_threshold != null
                    ? html`
                        <div class="free-hint">
                          ${t('shipping.free_threshold', { amount: this.formatPrice(o.free_shipping_threshold) })}
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
    'afianco-shipping-options-picker': AfiancoShippingOptionsPicker;
  }
  interface HTMLElementEventMap {
    'afianco:shipping-option-selected': CustomEvent<{ option: EmbedShippingOption }>;
  }
}
