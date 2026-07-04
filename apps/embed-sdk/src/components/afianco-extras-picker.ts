/**
 * <afianco-extras-picker> — Track E Step 2.4.9 (product extras add-on).
 *
 * Picker generalizzato per i 3 kind di ProductExtra (Onda 16):
 *   - mandatory:    sempre auto-applicati (read-only display, server li
 *                   include automaticamente nel cart)
 *   - optional:     checkbox multi-select (es. "Aggiungi GPS", "Colazione")
 *   - radio_variant: gruppi mutually exclusive (un solo pick per group_key,
 *                   es. "Franchigia Standard vs Zero")
 *
 * Pricing visual aid: ogni extra mostra il modificatore prezzo (+12€,
 * +5€/giorno, +20€/unità) basato su price_modifier_type. Per la quote
 * preview live (con day count / quantity multiplier) il componente
 * emette l'evento — il parent (product-detail) lo aggrega.
 *
 * Custom events:
 *   - afianco:extras-changed (detail: { selections: EmbedExtraSelection[] })
 *
 * Attributes:
 *   - currency (string, default "EUR") — formatting price modifiers
 *   - day-count (number, optional) — se passato + ci sono per_day extras,
 *     mostra il totale "× N giorni"
 */

import { LitElement, html, css, nothing } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { afiancoBaseStyles } from '@afianco/design-tokens';
// Sprint 4 W4.7 — i18n wiring
import { t } from '../i18n/index.js';
import type {
  EmbedProductExtra,
  EmbedExtraSelection,
} from '@afianco/api-client';


@customElement('afianco-extras-picker')
export class AfiancoExtrasPicker extends LitElement {
  /** Lista degli extras (da EmbedProductDetail.extras). */
  @property({ type: Array })
  extras: EmbedProductExtra[] = [];

  /** Currency ISO code per formatting prices. */
  @property({ type: String })
  currency = 'EUR';

  /** Day count (per rental flavor=range) — moltiplicatore per_day extras. */
  @property({ type: Number, attribute: 'day-count' })
  dayCount: number | null = null;

  /** Quantity line (per_unit extras moltiplicatore). */
  @property({ type: Number })
  quantity = 1;

  /** Label del gruppo (i18n via prop). */
  @property({ type: String, attribute: 'group-label' })
  groupLabel = ''; // Sprint 4 W4.7 — default resolved at render via t('extras.title')

  // ── Internal state ────────────────────────────────────────────────────

  /**
   * Optional selections — set di id selezionati.
   * Radio_variant selections — map group_key → extra_id selected.
   */
  @state()
  private optionalSelected = new Set<string>();

  @state()
  private radioSelected: Record<string, string> = {};

  // ── Lifecycle ────────────────────────────────────────────────────────

  protected willUpdate(changedProps: Map<string, unknown>): void {
    if (changedProps.has('extras')) {
      this.initDefaults();
    }
  }

  /** Inizializza is_default per optional (pre-checked) + radio (default pick). */
  private initDefaults(): void {
    const optDefaults = new Set<string>();
    const radioGroups: Record<string, string> = {};
    for (const ex of this.extras ?? []) {
      if (!ex.is_default) continue;
      if (ex.kind === 'optional') {
        optDefaults.add(ex.id);
      } else if (ex.kind === 'radio_variant' && ex.group_key) {
        // Per gruppo: prima default vince (sort_order rispettato)
        if (!radioGroups[ex.group_key]) {
          radioGroups[ex.group_key] = ex.id;
        }
      }
    }
    this.optionalSelected = optDefaults;
    this.radioSelected = radioGroups;
    // Emit initial selections (per pricing preview parent)
    this.emitChange();
  }

  // ── Handlers ────────────────────────────────────────────────────────

  private toggleOptional(extra: EmbedProductExtra): void {
    const next = new Set(this.optionalSelected);
    if (next.has(extra.id)) next.delete(extra.id);
    else next.add(extra.id);
    this.optionalSelected = next;
    this.emitChange();
  }

  private selectRadio(extra: EmbedProductExtra): void {
    if (!extra.group_key) return;
    this.radioSelected = {
      ...this.radioSelected,
      [extra.group_key]: extra.id,
    };
    this.emitChange();
  }

  private emitChange(): void {
    const selections: EmbedExtraSelection[] = [];
    // Mandatory: sempre incluso
    for (const ex of this.extras ?? []) {
      if (ex.kind === 'mandatory') {
        selections.push({ extra_id: ex.id, kind: 'mandatory' });
      }
    }
    // Optional: solo quelli checkati
    for (const id of this.optionalSelected) {
      selections.push({ extra_id: id, kind: 'optional' });
    }
    // Radio: uno per gruppo
    for (const [group_key, id] of Object.entries(this.radioSelected)) {
      selections.push({ extra_id: id, kind: 'radio_variant', group_key });
    }
    this.dispatchEvent(
      new CustomEvent<{ selections: EmbedExtraSelection[] }>(
        'afianco:extras-changed',
        {
          detail: { selections },
          bubbles: true,
          composed: true,
        },
      ),
    );
  }

  // ── Helpers ─────────────────────────────────────────────────────────

  private formatPriceModifier(ex: EmbedProductExtra): string {
    const sign = '+';
    const amt = this.formatPrice(ex.price);
    switch (ex.price_modifier_type) {
      case 'per_day':
        return `${sign}${amt}/giorno`;
      case 'per_unit':
        return `${sign}${amt}/unità`;
      case 'flat':
      default:
        return `${sign}${amt}`;
    }
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

  /**
   * Aggregate price preview hint (lato client — il prezzo finale e'
   * computato server-side dal price-preview endpoint per consistency).
   * Per kind=mandatory: sempre incluso. Per optional: solo checked.
   * Per radio: solo quello selected per group.
   */
  private get computedExtrasTotal(): number {
    let total = 0;
    const days = this.dayCount ?? 1;
    const qty = this.quantity ?? 1;
    const apply = (ex: EmbedProductExtra) => {
      switch (ex.price_modifier_type) {
        case 'per_day': total += ex.price * days; break;
        case 'per_unit': total += ex.price * qty; break;
        case 'flat':
        default: total += ex.price; break;
      }
    };
    for (const ex of this.extras ?? []) {
      if (ex.kind === 'mandatory') apply(ex);
      else if (ex.kind === 'optional' && this.optionalSelected.has(ex.id)) apply(ex);
      else if (ex.kind === 'radio_variant' && ex.group_key && this.radioSelected[ex.group_key] === ex.id) apply(ex);
    }
    return total;
  }

  // ── Grouping helpers ────────────────────────────────────────────────

  private get mandatoryExtras(): EmbedProductExtra[] {
    return (this.extras ?? []).filter((e) => e.kind === 'mandatory');
  }

  private get optionalExtras(): EmbedProductExtra[] {
    return (this.extras ?? []).filter((e) => e.kind === 'optional');
  }

  /** Map group_key → extras del gruppo (per render radio groups). */
  private get radioGroups(): Record<string, EmbedProductExtra[]> {
    const groups: Record<string, EmbedProductExtra[]> = {};
    for (const ex of this.extras ?? []) {
      if (ex.kind !== 'radio_variant') continue;
      const key = ex.group_key ?? '__nogroup__';
      groups[key] = groups[key] ?? [];
      groups[key].push(ex);
    }
    // Sort each group by sort_order
    for (const key of Object.keys(groups)) {
      groups[key]!.sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));
    }
    return groups;
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
      .subgroup-label {
        font-size: 12px;
        font-weight: 600;
        color: var(--afianco-color-text-secondary, #6b7280);
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin: 12px 0 6px;
        display: block;
      }

      .extras-list {
        display: flex;
        flex-direction: column;
        gap: 8px;
      }

      .extra-row {
        display: flex;
        align-items: flex-start;
        gap: 12px;
        padding: 12px 14px;
        background: var(--afianco-color-surface, #ffffff);
        border: 1.5px solid var(--afianco-color-border, #e5e7eb);
        border-radius: 10px;
        cursor: pointer;
        transition: border-color 0.15s ease, background 0.15s ease;
      }
      .extra-row:hover {
        border-color: var(--afianco-color-primary, #4b72ce);
      }
      .extra-row[aria-checked='true'],
      .extra-row[data-checked='true'] {
        border-color: var(--afianco-color-primary, #4b72ce);
        background: var(--afianco-color-primary-soft, #eef2ff);
      }
      .extra-row[data-readonly='true'] {
        cursor: default;
        background: var(--afianco-color-muted, #f9fafb);
        border-color: var(--afianco-color-border, #e5e7eb);
      }
      .extra-row:focus-visible {
        outline: 2px solid var(--afianco-color-primary, #4b72ce);
        outline-offset: 2px;
      }

      /* Control icon (checkbox / radio) */
      .ctrl {
        flex-shrink: 0;
        width: 18px;
        height: 18px;
        border: 1.5px solid var(--afianco-color-border-strong, #d1d5db);
        position: relative;
        margin-top: 2px;
      }
      .ctrl.checkbox {
        border-radius: 4px;
      }
      .ctrl.radio {
        border-radius: 50%;
      }
      .extra-row[data-checked='true'] .ctrl,
      .extra-row[aria-checked='true'] .ctrl {
        border-color: var(--afianco-color-primary, #4b72ce);
      }
      .extra-row[data-checked='true'] .ctrl.checkbox::after {
        content: '✓';
        position: absolute;
        inset: 0;
        background: var(--afianco-color-primary, #4b72ce);
        color: white;
        border-radius: 3px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 12px;
        font-weight: 700;
      }
      .extra-row[aria-checked='true'] .ctrl.radio::after {
        content: '';
        position: absolute;
        inset: 3px;
        border-radius: 50%;
        background: var(--afianco-color-primary, #4b72ce);
      }
      /* Mandatory: filled solid (no checkbox interactivity) */
      .extra-row[data-mandatory='true'] .ctrl {
        background: var(--afianco-color-primary, #4b72ce);
        border-color: var(--afianco-color-primary, #4b72ce);
      }
      .extra-row[data-mandatory='true'] .ctrl::after {
        content: '★';
        position: absolute;
        inset: 0;
        color: white;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 10px;
      }

      .body {
        flex: 1;
        min-width: 0;
      }
      .top-row {
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        gap: 10px;
      }
      .label {
        font-size: 14px;
        font-weight: 600;
        color: var(--afianco-color-text, #111827);
      }
      .price-tag {
        font-size: 13px;
        font-weight: 700;
        color: var(--afianco-color-primary, #4b72ce);
        white-space: nowrap;
      }
      .description {
        font-size: 12px;
        color: var(--afianco-color-text-secondary, #6b7280);
        margin-top: 4px;
        line-height: 1.5;
      }
      .mandatory-badge {
        display: inline-block;
        margin-left: 6px;
        font-size: 10px;
        font-weight: 600;
        color: #92400e;
        background: #fef3c7;
        padding: 1px 6px;
        border-radius: 9999px;
        text-transform: uppercase;
        letter-spacing: 0.04em;
      }

      .total-hint {
        margin-top: 12px;
        padding: 8px 12px;
        font-size: 12px;
        color: var(--afianco-color-text-secondary, #6b7280);
        background: var(--afianco-color-muted, #f3f4f6);
        border-radius: 6px;
        display: flex;
        justify-content: space-between;
      }
      .total-amount {
        font-weight: 700;
        color: var(--afianco-color-text, #111827);
      }
    `,
  ];

  // ── Render ──────────────────────────────────────────────────────────

  render() {
    const mandatory = this.mandatoryExtras;
    const optional = this.optionalExtras;
    const radioGroups = this.radioGroups;
    const hasMandatory = mandatory.length > 0;
    const hasOptional = optional.length > 0;
    const hasRadio = Object.keys(radioGroups).length > 0;

    if (!hasMandatory && !hasOptional && !hasRadio) return nothing;

    const total = this.computedExtrasTotal;

    return html`
      <span class="group-label">${this.groupLabel || t('extras.title')}</span>

      <!-- Radio variants (gruppi mutually exclusive) -->
      ${Object.entries(radioGroups).map(([groupKey, extras]) => html`
        <div>
          <span class="subgroup-label">
            ${this.formatGroupLabel(groupKey)}
          </span>
          <div class="extras-list" role="radiogroup" aria-label=${this.formatGroupLabel(groupKey)}>
            ${extras.map((ex) => {
              const checked = this.radioSelected[groupKey] === ex.id;
              return html`
                <div
                  class="extra-row"
                  role="radio"
                  aria-checked=${checked ? 'true' : 'false'}
                  tabindex=${checked ? '0' : '-1'}
                  @click=${() => this.selectRadio(ex)}
                  @keydown=${(e: KeyboardEvent) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      this.selectRadio(ex);
                    }
                  }}>
                  <span class="ctrl radio" aria-hidden="true"></span>
                  <div class="body">
                    <div class="top-row">
                      <span class="label">${ex.label}</span>
                      <span class="price-tag">${this.formatPriceModifier(ex)}</span>
                    </div>
                    ${ex.description
                      ? html`<div class="description">${ex.description}</div>`
                      : nothing}
                  </div>
                </div>
              `;
            })}
          </div>
        </div>
      `)}

      <!-- Optional (checkbox multi-select) -->
      ${hasOptional
        ? html`
            <div>
              <span class="subgroup-label">Opzionali</span>
              <div class="extras-list">
                ${optional.map((ex) => {
                  const checked = this.optionalSelected.has(ex.id);
                  return html`
                    <div
                      class="extra-row"
                      data-checked=${checked ? 'true' : 'false'}
                      role="checkbox"
                      aria-checked=${checked ? 'true' : 'false'}
                      tabindex="0"
                      @click=${() => this.toggleOptional(ex)}
                      @keydown=${(e: KeyboardEvent) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          this.toggleOptional(ex);
                        }
                      }}>
                      <span class="ctrl checkbox" aria-hidden="true"></span>
                      <div class="body">
                        <div class="top-row">
                          <span class="label">${ex.label}</span>
                          <span class="price-tag">${this.formatPriceModifier(ex)}</span>
                        </div>
                        ${ex.description
                          ? html`<div class="description">${ex.description}</div>`
                          : nothing}
                      </div>
                    </div>
                  `;
                })}
              </div>
            </div>
          `
        : nothing}

      <!-- Mandatory (auto-applied, read-only display) -->
      ${hasMandatory
        ? html`
            <div>
              <span class="subgroup-label">Incluso nel prezzo</span>
              <div class="extras-list">
                ${mandatory.map((ex) => html`
                  <div
                    class="extra-row"
                    data-mandatory="true"
                    data-readonly="true">
                    <span class="ctrl" aria-hidden="true"></span>
                    <div class="body">
                      <div class="top-row">
                        <span class="label">
                          ${ex.label}
                          <span class="mandatory-badge">Obbligatorio</span>
                        </span>
                        <span class="price-tag">${this.formatPriceModifier(ex)}</span>
                      </div>
                      ${ex.description
                        ? html`<div class="description">${ex.description}</div>`
                        : nothing}
                    </div>
                  </div>
                `)}
              </div>
            </div>
          `
        : nothing}

      ${total > 0
        ? html`
            <div class="total-hint" role="status" aria-live="polite">
              <span>Extra inclusi</span>
              <span class="total-amount">${this.formatPrice(total)}</span>
            </div>
          `
        : nothing}
    `;
  }

  /** Localizza il group_key per la display (titlecase, fallback raw). */
  private formatGroupLabel(groupKey: string): string {
    if (groupKey === '__nogroup__') return 'Opzioni';
    // titlecase: "insurance" → "Insurance"; "package_tier" → "Package Tier"
    return groupKey
      .split(/[_\-\s]+/)
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
      .join(' ');
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'afianco-extras-picker': AfiancoExtrasPicker;
  }
  interface HTMLElementEventMap {
    'afianco:extras-changed': CustomEvent<{ selections: EmbedExtraSelection[] }>;
  }
}
