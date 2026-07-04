/**
 * <afianco-fulfillment-picker> — Track E Step 4.2 (fulfillment mode selector).
 *
 * Radio picker per la modalita' di fulfillment (shipping vs local_pickup
 * vs pickup_at_store). Visible SOLO quando lo store supporta >1 mode.
 * Default: prima mode in lista, normalmente "shipping".
 *
 * Pattern parita' con storefront React (StorefrontPage line 2247-2273).
 *
 * Custom events:
 *   - afianco:fulfillment-mode-changed (detail: { mode: 'shipping'|'local_pickup'|'pickup_at_store' })
 *
 * Attributes:
 *   - modes: string[] (lista mode supportati, da ctx.init.fulfillment_modes)
 *   - selected: string (mode attivo, controllato dal parent)
 */

import { LitElement, html, css, nothing } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { afiancoBaseStyles } from '@afianco/design-tokens';
// Sprint 4 W4.7 — i18n wiring
import { t } from '../i18n/index.js';


/** I 3 mode possibili (FulfillmentMode in shared-types). */
type FulfillmentModeValue = 'shipping' | 'local_pickup' | 'pickup_at_store';

// Sprint 4 W4.7 — labels resolved al runtime via t() per supporto 4 lingue.
// Icon resta hardcoded (universale).
function modeMeta(mode: FulfillmentModeValue): { label: string; icon: string; description: string } {
  switch (mode) {
    case 'shipping':
      return { label: t('fulfillment.shipping'), icon: '📦', description: t('fulfillment.shipping_desc') };
    case 'local_pickup':
      return { label: t('fulfillment.local_pickup'), icon: '🏪', description: t('fulfillment.local_pickup_desc') };
    case 'pickup_at_store':
      return { label: t('fulfillment.external_pickup_label'), icon: '📍', description: t('fulfillment.external_pickup_desc') };
  }
}


@customElement('afianco-fulfillment-picker')
export class AfiancoFulfillmentPicker extends LitElement {
  /** Lista mode supportati (es. ['shipping', 'local_pickup']). */
  @property({ type: Array })
  modes: string[] = [];

  /** Mode attualmente selezionato. */
  @property({ type: String })
  selected: string | null = null;

  /** Label gruppo (i18n via prop, fallback resolved at render). */
  @property({ type: String, attribute: 'group-label' })
  groupLabel = '';

  // ── Handlers ────────────────────────────────────────────────────────

  private handleSelect(mode: string): void {
    if (mode === this.selected) return;
    this.selected = mode;
    this.dispatchEvent(
      new CustomEvent<{ mode: string }>('afianco:fulfillment-mode-changed', {
        detail: { mode },
        bubbles: true,
        composed: true,
      }),
    );
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
      .modes {
        display: flex;
        flex-direction: column;
        gap: 8px;
      }
      @media (min-width: 480px) {
        .modes {
          flex-direction: row;
          flex-wrap: wrap;
        }
        .mode {
          flex: 1 1 calc(50% - 4px);
          min-width: 180px;
        }
      }
      .mode {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 12px 14px;
        border: 1.5px solid var(--afianco-color-border, #e5e7eb);
        border-radius: 10px;
        cursor: pointer;
        background: var(--afianco-color-surface, #ffffff);
        transition: border-color 0.15s ease, background 0.15s ease;
      }
      .mode:hover {
        border-color: var(--afianco-color-primary, #4b72ce);
      }
      .mode[aria-checked='true'] {
        border-color: var(--afianco-color-primary, #4b72ce);
        background: var(--afianco-color-primary-soft, #eef2ff);
      }
      .mode:focus-visible {
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
      }
      .mode[aria-checked='true'] .radio {
        border-color: var(--afianco-color-primary, #4b72ce);
      }
      .mode[aria-checked='true'] .radio::after {
        content: '';
        position: absolute;
        inset: 3px;
        border-radius: 50%;
        background: var(--afianco-color-primary, #4b72ce);
      }
      .icon {
        font-size: 22px;
        line-height: 1;
        flex-shrink: 0;
      }
      .body { flex: 1; min-width: 0; }
      .label {
        font-size: 14px;
        font-weight: 600;
        color: var(--afianco-color-text, #111827);
        display: block;
      }
      .description {
        font-size: 12px;
        color: var(--afianco-color-text-secondary, #6b7280);
        margin-top: 2px;
      }
    `,
  ];

  // ── Render ──────────────────────────────────────────────────────────

  render() {
    if (!this.modes || this.modes.length <= 1) return nothing;
    return html`
      <span class="group-label">${this.groupLabel || t('fulfillment.group_label')}</span>
      <div class="modes" role="radiogroup" aria-label=${this.groupLabel || t('fulfillment.group_label')}>
        ${this.modes.map((mode) => {
          // Sprint 4 W4.7 — resolve label/desc at render via t() (4 lingue)
          const meta = ['shipping', 'local_pickup', 'pickup_at_store'].includes(mode)
            ? modeMeta(mode as FulfillmentModeValue)
            : { label: mode, icon: '🚚', description: '' };
          const checked = this.selected === mode;
          return html`
            <div
              class="mode"
              role="radio"
              aria-checked=${checked ? 'true' : 'false'}
              tabindex=${checked ? '0' : '-1'}
              @click=${() => this.handleSelect(mode)}
              @keydown=${(e: KeyboardEvent) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  this.handleSelect(mode);
                }
              }}>
              <span class="radio" aria-hidden="true"></span>
              <span class="icon" aria-hidden="true">${meta.icon}</span>
              <div class="body">
                <span class="label">${meta.label}</span>
                ${meta.description
                  ? html`<span class="description">${meta.description}</span>`
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
    'afianco-fulfillment-picker': AfiancoFulfillmentPicker;
  }
  interface HTMLElementEventMap {
    'afianco:fulfillment-mode-changed': CustomEvent<{ mode: string }>;
  }
}
