/**
 * <afianco-occurrence-picker> — Track E Step 2.4.7 (event_ticket dates).
 *
 * Date carousel per la scelta dell'occurrence (data evento) di un
 * event_ticket product. Mirror del React component nel storefront
 * (EventLandingPage → occurrence selector).
 *
 * Pattern simile a <afianco-availability-picker> ma:
 *   - Data viene da product.occurrences[] (gia' embedded nel detail)
 *     NO side-fetch endpoint /availability (le occurrence sono finite)
 *   - Mostra location + remaining capacity + price_override per ogni
 *   - Disabled state per occurrence sold-out (remaining === 0)
 *
 * Custom events:
 *   - afianco:occurrence-selected (detail: { occurrence: EmbedOccurrence })
 *
 * Accessibility:
 *   - role="radiogroup"
 *   - Cards con role="radio" + aria-checked
 *   - aria-disabled per sold-out
 */

import { LitElement, html, css, nothing } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { afiancoBaseStyles } from '@afianco/design-tokens';
import type { EmbedOccurrence } from '@afianco/api-client';
// W4.9 — i18n
import { t } from '../i18n/index.js';


@customElement('afianco-occurrence-picker')
export class AfiancoOccurrencePicker extends LitElement {
  @property({ type: Array })
  occurrences: EmbedOccurrence[] = [];

  @property({ type: String })
  currency = 'EUR';

  @property({ type: String })
  selected: string | null = null;

  @property({ type: String, attribute: 'group-label' })
  groupLabel = ''; // W4.9 — fallback at render via t()

  // ── Handlers ────────────────────────────────────────────────────────

  private handleSelect(occ: EmbedOccurrence): void {
    if (this.isSoldOut(occ)) return;
    this.selected = occ.id;
    this.dispatchEvent(
      new CustomEvent<{ occurrence: EmbedOccurrence }>(
        'afianco:occurrence-selected',
        {
          detail: { occurrence: occ },
          bubbles: true,
          composed: true,
        },
      ),
    );
  }

  // ── Helpers ─────────────────────────────────────────────────────────

  private isSoldOut(o: EmbedOccurrence): boolean {
    return o.remaining === 0;
  }

  private formatDateTime(isoString: string): { date: string; time: string } {
    try {
      const d = new Date(isoString);
      const dateStr = d.toLocaleDateString('it-IT', {
        weekday: 'short',
        day: 'numeric',
        month: 'short',
        year: 'numeric',
      });
      const timeStr = d.toLocaleTimeString('it-IT', {
        hour: '2-digit',
        minute: '2-digit',
      });
      return { date: dateStr, time: timeStr };
    } catch {
      return { date: isoString, time: '' };
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

  private getOccurrencePrice(o: EmbedOccurrence): number | null {
    // Priority: price_override > min(tier.price) > none
    if (typeof o.price_override === 'number') return o.price_override;
    if (o.tiers && o.tiers.length > 0) {
      return Math.min(...o.tiers.map((t) => t.price));
    }
    return null;
  }

  /**
   * Track E Step 5.5 — Build URL mappa (OpenStreetMap o Google Maps).
   *
   * Priority:
   *   1. occ.map_url esplicito (configurato dal merchant nell'admin)
   *   2. occ.latitude + longitude → OpenStreetMap URL (no API key needed)
   *   3. occ.address → Google Maps search URL (encoded)
   *   4. null = no map link
   */
  private buildMapUrl(o: EmbedOccurrence): string | null {
    if (o.map_url) return o.map_url;
    if (typeof o.latitude === 'number' && typeof o.longitude === 'number') {
      return `https://www.openstreetmap.org/?mlat=${o.latitude}&mlon=${o.longitude}#map=17/${o.latitude}/${o.longitude}`;
    }
    const address = o.address ?? o.city ?? o.venue_name;
    if (address) {
      return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(address)}`;
    }
    return null;
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
      .occurrences {
        display: flex;
        flex-direction: column;
        gap: 8px;
      }
      .occurrence {
        display: flex;
        align-items: flex-start;
        gap: 12px;
        padding: 12px 14px;
        border: 1.5px solid var(--afianco-color-border, #e5e7eb);
        border-radius: 10px;
        cursor: pointer;
        transition: border-color 0.15s ease, background 0.15s ease;
        background: var(--afianco-color-surface, #ffffff);
      }
      .occurrence:hover:not([aria-disabled='true']) {
        border-color: var(--afianco-color-primary, #4b72ce);
        background: var(--afianco-color-muted, #f9fafb);
      }
      .occurrence[aria-checked='true'] {
        border-color: var(--afianco-color-primary, #4b72ce);
        background: var(--afianco-color-primary-soft, #eef2ff);
      }
      .occurrence[aria-disabled='true'] {
        opacity: 0.5;
        cursor: not-allowed;
        background: var(--afianco-color-muted, #f3f4f6);
      }
      .occurrence:focus-visible {
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
      .occurrence[aria-checked='true'] .radio {
        border-color: var(--afianco-color-primary, #4b72ce);
      }
      .occurrence[aria-checked='true'] .radio::after {
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
      .header {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        gap: 8px;
      }
      .date {
        font-size: 14px;
        font-weight: 600;
        color: var(--afianco-color-text, #111827);
      }
      .price {
        font-size: 14px;
        font-weight: 700;
        color: var(--afianco-color-text, #111827);
      }
      .meta {
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
        margin-top: 4px;
        font-size: 12px;
        color: var(--afianco-color-text-secondary, #6b7280);
      }
      .meta-item {
        display: inline-flex;
        align-items: center;
        gap: 4px;
      }
      .sold-out-badge {
        display: inline-flex;
        align-items: center;
        padding: 2px 8px;
        background: #fee2e2;
        color: #991b1b;
        border-radius: 9999px;
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
      }
      .remaining-warning {
        color: #92400e;
        font-weight: 600;
      }
      .empty {
        font-size: 13px;
        color: var(--afianco-color-text-muted, #9ca3af);
        font-style: italic;
        padding: 12px;
        text-align: center;
        background: var(--afianco-color-muted, #f3f4f6);
        border-radius: 8px;
      }
    `,
  ];

  // ── Render ──────────────────────────────────────────────────────────

  render() {
    if (!this.occurrences || this.occurrences.length === 0) {
      return html`<div class="empty">${t('occurrence.empty')}</div>`;
    }

    return html`
      <span class="group-label">${this.groupLabel || t('occurrence.group_label')}</span>
      <div class="occurrences" role="radiogroup" aria-label=${this.groupLabel || t('occurrence.group_label')}>
        ${this.occurrences.map((occ) => {
          const checked = this.selected === occ.id;
          const soldOut = this.isSoldOut(occ);
          const { date, time } = this.formatDateTime(occ.start_at);
          const price = this.getOccurrencePrice(occ);
          const location = occ.venue_name ?? occ.location;
          const lowRemaining =
            typeof occ.remaining === 'number' &&
            occ.remaining > 0 &&
            occ.remaining <= 5;

          return html`
            <div
              class="occurrence"
              role="radio"
              aria-checked=${checked ? 'true' : 'false'}
              aria-disabled=${soldOut ? 'true' : 'false'}
              tabindex=${soldOut ? '-1' : (checked ? '0' : '-1')}
              @click=${() => this.handleSelect(occ)}
              @keydown=${(e: KeyboardEvent) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  this.handleSelect(occ);
                }
              }}>
              <span class="radio" aria-hidden="true"></span>
              <div class="body">
                <div class="header">
                  <span class="date">${date}${time ? ` · ${time}` : ''}</span>
                  ${soldOut
                    ? html`<span class="sold-out-badge">${t('occurrence.sold_out')}</span>`
                    : price !== null
                      ? html`<span class="price">da ${this.formatPrice(price)}</span>`
                      : nothing}
                </div>
                <div class="meta">
                  ${location
                    ? html`
                        <span class="meta-item">
                          <span aria-hidden="true">📍</span>
                          ${location}
                          ${this.buildMapUrl(occ)
                            ? html`
                                <a
                                  href=${this.buildMapUrl(occ)}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  style="margin-left: 6px;
                                         font-size: 11px;
                                         color: var(--afianco-color-primary, #4b72ce);
                                         text-decoration: underline;"
                                  @click=${(e: Event) => e.stopPropagation()}>
                                  ${t('occurrence.map_link')}
                                </a>
                              `
                            : ''}
                        </span>
                      `
                    : nothing}
                  ${lowRemaining && occ.remaining != null
                    ? html`
                        <span class="meta-item remaining-warning">
                          ${occ.remaining === 1
                            ? t('product.remaining_seats_one', { count: occ.remaining })
                            : t('product.remaining_seats_other', { count: occ.remaining })}
                        </span>
                      `
                    : nothing}
                </div>
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
    'afianco-occurrence-picker': AfiancoOccurrencePicker;
  }
  interface HTMLElementEventMap {
    'afianco:occurrence-selected': CustomEvent<{ occurrence: EmbedOccurrence }>;
  }
}
