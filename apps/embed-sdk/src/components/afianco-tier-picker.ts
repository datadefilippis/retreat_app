/**
 * <afianco-tier-picker> — Track E Step 2.4.7 (event_ticket tier + qty).
 *
 * Multi-tier picker per event_ticket products (F3 Onda 10).
 * Permette al customer di scegliere tier diversi (es. "Standard", "VIP")
 * + quantita' per ogni tier. Risultato: tier_quantities map.
 *
 * UX: ogni tier ha +/- counter (max=tier.remaining). Totale aggregato
 * mostrato in summary.
 *
 * Fallback: se l'occurrence non ha tiers[] (legacy mono-tier), il parent
 * dovrebbe mostrare uno qty stepper plain invece di questo componente.
 *
 * Custom events:
 *   - afianco:tier-quantities-changed (detail: { quantities: Record<string, number>, total: number })
 *
 * Note: il pattern multi-tier del storefront mantiene UN solo tier
 * selezionato finale per cart item (ticket_tier_id). Per multi-tier:
 *   - V1 limito a UN tier selezionato max (radio) + qty
 *   - V2 supporto multi-line cart (un cart item per tier) — futuro
 */

import { LitElement, html, css, nothing } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { afiancoBaseStyles } from '@afianco/design-tokens';
import type { EmbedTier } from '@afianco/api-client';
// Sprint 4 W4.7 — i18n wiring
import { t } from '../i18n/index.js';


@customElement('afianco-tier-picker')
export class AfiancoTierPicker extends LitElement {
  @property({ type: Array })
  tiers: EmbedTier[] = [];

  @property({ type: String })
  currency = 'EUR';

  /** Tier id attualmente selezionato (V1: single-select). */
  @property({ type: String, attribute: 'selected-tier' })
  selectedTier: string | null = null;

  /** Quantita' selezionata per il tier corrente. */
  @property({ type: Number })
  quantity = 1;

  @property({ type: String, attribute: 'group-label' })
  groupLabel = ''; // Sprint 4 W4.7 — default resolved at render via t('tier.title')

  // ── Handlers ────────────────────────────────────────────────────────

  private handleSelectTier(tier: EmbedTier): void {
    if (this.isSoldOut(tier)) return;
    this.selectedTier = tier.id;
    this.quantity = 1;
    this.emitChange(tier);
  }

  private updateQty(delta: number): void {
    if (!this.selectedTier) return;
    const tier = this.tiers.find((t) => t.id === this.selectedTier);
    if (!tier) return;
    const max = tier.remaining ?? 99;
    const next = Math.max(1, Math.min(max, this.quantity + delta));
    if (next === this.quantity) return;
    this.quantity = next;
    this.emitChange(tier);
  }

  private emitChange(tier: EmbedTier): void {
    this.dispatchEvent(
      new CustomEvent<{ tier: EmbedTier; quantity: number }>(
        'afianco:tier-changed',
        {
          detail: { tier, quantity: this.quantity },
          bubbles: true,
          composed: true,
        },
      ),
    );
  }

  // ── Helpers ─────────────────────────────────────────────────────────

  private isSoldOut(t: EmbedTier): boolean {
    return t.remaining === 0;
  }

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

  private get selectedTierObj(): EmbedTier | null {
    if (!this.selectedTier) return null;
    return this.tiers.find((t) => t.id === this.selectedTier) ?? null;
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
      .tiers {
        display: flex;
        flex-direction: column;
        gap: 8px;
        margin-bottom: 12px;
      }
      .tier {
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
      .tier:hover:not([aria-disabled='true']) {
        border-color: var(--afianco-color-primary, #4b72ce);
        background: var(--afianco-color-muted, #f9fafb);
      }
      .tier[aria-checked='true'] {
        border-color: var(--afianco-color-primary, #4b72ce);
        background: var(--afianco-color-primary-soft, #eef2ff);
      }
      .tier[aria-disabled='true'] {
        opacity: 0.5;
        cursor: not-allowed;
      }
      .tier:focus-visible {
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
      .tier[aria-checked='true'] .radio {
        border-color: var(--afianco-color-primary, #4b72ce);
      }
      .tier[aria-checked='true'] .radio::after {
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
      .tier-header {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        gap: 8px;
      }
      .tier-label {
        font-size: 14px;
        font-weight: 600;
        color: var(--afianco-color-text, #111827);
      }
      .tier-price {
        font-size: 14px;
        font-weight: 700;
        color: var(--afianco-color-text, #111827);
      }
      .tier-description {
        font-size: 12px;
        color: var(--afianco-color-text-secondary, #6b7280);
        margin-top: 4px;
        line-height: 1.5;
      }
      .tier-remaining {
        font-size: 11px;
        color: var(--afianco-color-text-muted, #9ca3af);
        margin-top: 4px;
      }
      .sold-out-badge {
        display: inline-flex;
        padding: 2px 8px;
        background: #fee2e2;
        color: #991b1b;
        border-radius: 9999px;
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
      }

      /* ── Qty stepper (visibile solo se selezionato) ───────────────── */
      .qty-section {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        padding: 12px 14px;
        background: var(--afianco-color-muted, #f3f4f6);
        border-radius: 10px;
      }
      .qty-label {
        font-size: 13px;
        font-weight: 600;
        color: var(--afianco-color-text, #111827);
      }
      .qty-controls {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        background: var(--afianco-color-bg, #ffffff);
        border-radius: 8px;
        padding: 4px;
      }
      .qty-btn {
        width: 32px;
        height: 32px;
        background: var(--afianco-color-surface, #ffffff);
        border: 1px solid var(--afianco-color-border, #e5e7eb);
        border-radius: 6px;
        cursor: pointer;
        font-size: 16px;
        font-weight: 600;
        color: var(--afianco-color-text, #111827);
        display: inline-flex;
        align-items: center;
        justify-content: center;
      }
      .qty-btn:hover:not(:disabled) {
        background: var(--afianco-color-muted, #f3f4f6);
      }
      .qty-btn:disabled {
        opacity: 0.4;
        cursor: not-allowed;
      }
      .qty-value {
        min-width: 32px;
        text-align: center;
        font-size: 14px;
        font-weight: 600;
      }
    `,
  ];

  // ── Render ──────────────────────────────────────────────────────────

  render() {
    if (!this.tiers || this.tiers.length === 0) {
      return nothing;
    }
    const selectedTier = this.selectedTierObj;
    const maxQty = selectedTier?.remaining ?? 99;

    return html`
      <span class="group-label">${this.groupLabel || t('tier.title')}</span>
      <div class="tiers" role="radiogroup" aria-label=${this.groupLabel || t('tier.title')}>
        ${this.tiers
          .slice()
          .sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0))
          .map((tier) => {
            const checked = this.selectedTier === tier.id;
            const soldOut = this.isSoldOut(tier);
            const lowRemaining =
              typeof tier.remaining === 'number' &&
              tier.remaining > 0 &&
              tier.remaining <= 5;
            return html`
              <div
                class="tier"
                role="radio"
                aria-checked=${checked ? 'true' : 'false'}
                aria-disabled=${soldOut ? 'true' : 'false'}
                tabindex=${soldOut ? '-1' : (checked ? '0' : '-1')}
                @click=${() => this.handleSelectTier(tier)}
                @keydown=${(e: KeyboardEvent) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    this.handleSelectTier(tier);
                  }
                }}>
                <span class="radio" aria-hidden="true"></span>
                <div class="body">
                  <div class="tier-header">
                    <span class="tier-label">${tier.label}</span>
                    ${soldOut
                      ? html`<span class="sold-out-badge">${t('tier.sold_out')}</span>`
                      : html`<span class="tier-price">${this.formatPrice(tier.price)}</span>`}
                  </div>
                  ${tier.description
                    ? html`<div class="tier-description">${tier.description}</div>`
                    : nothing}
                  ${lowRemaining && tier.remaining != null
                    ? html`<div class="tier-remaining">${tier.remaining === 1
                        ? t('tier.limited_one', { count: tier.remaining })
                        : t('tier.limited_other', { count: tier.remaining })}</div>`
                    : nothing}
                </div>
              </div>
            `;
          })}
      </div>

      ${selectedTier
        ? html`
            <div class="qty-section">
              <span class="qty-label">${t('tier.qty_label')}</span>
              <div class="qty-controls">
                <button
                  class="qty-btn"
                  type="button"
                  aria-label=${t('tier.decrease_aria')}
                  ?disabled=${this.quantity <= 1}
                  @click=${() => this.updateQty(-1)}>
                  −
                </button>
                <span class="qty-value" aria-live="polite">${this.quantity}</span>
                <button
                  class="qty-btn"
                  type="button"
                  aria-label=${t('tier.increase_aria')}
                  ?disabled=${this.quantity >= maxQty}
                  @click=${() => this.updateQty(1)}>
                  +
                </button>
              </div>
            </div>
          `
        : nothing}
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'afianco-tier-picker': AfiancoTierPicker;
  }
  interface HTMLElementEventMap {
    'afianco:tier-changed': CustomEvent<{ tier: EmbedTier; quantity: number }>;
  }
}
