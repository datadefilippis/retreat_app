/**
 * <afianco-date-range-picker> — Track E Step 2.4.7 (rental date range).
 *
 * Date range picker per rental products con flavor=range. UX semplice:
 * 2 input type="date" (from / to) con validazione:
 *   - from >= today (no past dates)
 *   - to >= from
 *   - max range hardcoded a 365 giorni (sanity)
 *
 * Mirror funzionale di AvailabilityDayPicker.js (storefront React).
 *
 * R3 — blocked_dates advisory: il parent (product-detail) precarica le date
 * occupate da `/api/public/embed/products/{slug}/{id}/blocked-dates` e le
 * passa via `.blockedDates`. La validazione inline rifiuta un range che le
 * include (UX immediata); il guard atomico server-side a confirm-time resta
 * comunque la verità sulla disponibilità.
 *
 * V2 enhancements:
 *   - Visual calendar widget custom (anziche' input type=date) per greyare
 *     le singole date occupate (gli input nativi non lo permettono).
 *
 * Custom events:
 *   - afianco:date-range-selected (detail: { from, to })
 *   - afianco:date-range-cleared
 *
 * Attributes:
 *   - rental-unit (optional): "giorno" | "settimana" | "ora" (display only)
 */

import { LitElement, html, css, nothing } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { afiancoBaseStyles } from '@afianco/design-tokens';
// W4.9 — i18n
import { t } from '../i18n/index.js';


@customElement('afianco-date-range-picker')
export class AfiancoDateRangePicker extends LitElement {
  /** Unit label per UX ("giorno", "settimana", ecc.). */
  @property({ type: String, attribute: 'rental-unit' })
  rentalUnit = 'giorno';

  /** Label localizzata del gruppo. */
  @property({ type: String, attribute: 'group-label' })
  groupLabel = ''; // W4.9 — fallback at render via t('rental.group_label')

  /** Min days range (default 1). */
  @property({ type: Number, attribute: 'min-days' })
  minDays = 1;

  /** Max days range (default 365 — sanity, server has own check). */
  @property({ type: Number, attribute: 'max-days' })
  maxDays = 365;

  /** R3 — date occupate (YYYY-MM-DD) iniettate dal parent (product-detail).
   *  Advisory: il guard atomico a confirm-time resta la verità. */
  @property({ attribute: false })
  blockedDates: string[] = [];

  // ── Internal state ────────────────────────────────────────────────────

  @state()
  private dateFrom = '';

  @state()
  private dateTo = '';

  @state()
  private error: string | null = null;

  // ── Lifecycle ────────────────────────────────────────────────────────

  connectedCallback(): void {
    super.connectedCallback();
    // Default: from = oggi, to = vuoto (user sceglie)
    if (!this.dateFrom) {
      this.dateFrom = this.todayISO();
    }
  }

  // ── Handlers ────────────────────────────────────────────────────────

  private handleFromChange(e: Event): void {
    const value = (e.target as HTMLInputElement).value;
    this.dateFrom = value;
    if (this.dateTo && this.dateTo < value) {
      // Reset dateTo se ora invalida
      this.dateTo = '';
    }
    this.validateAndEmit();
  }

  private handleToChange(e: Event): void {
    const value = (e.target as HTMLInputElement).value;
    this.dateTo = value;
    this.validateAndEmit();
  }

  private validateAndEmit(): void {
    this.error = null;
    if (!this.dateFrom || !this.dateTo) {
      this.dispatchEvent(
        new CustomEvent('afianco:date-range-cleared', {
          bubbles: true,
          composed: true,
        }),
      );
      return;
    }
    const from = new Date(this.dateFrom);
    const to = new Date(this.dateTo);
    if (Number.isNaN(from.getTime()) || Number.isNaN(to.getTime())) {
      this.error = t('rental.error_invalid_date');
      return;
    }
    if (to < from) {
      this.error = t('rental.error_end_before_start');
      return;
    }
    const dayDiff = Math.ceil((to.getTime() - from.getTime()) / (1000 * 60 * 60 * 24)) + 1;
    if (dayDiff < this.minDays) {
      this.error = this.minDays === 1
        ? t('rental.error_min_days_one', { count: this.minDays })
        : t('rental.error_min_days_other', { count: this.minDays });
      return;
    }
    if (dayDiff > this.maxDays) {
      this.error = t('rental.error_max_days', { count: this.maxDays });
      return;
    }
    // R3 — il range non deve includere date occupate (advisory UX).
    if (this.blockedDates.length && this.rangeHasBlockedDate(this.dateFrom, this.dateTo)) {
      this.error = t('rental.error_dates_unavailable');
      return;
    }

    this.dispatchEvent(
      new CustomEvent<{ from: string; to: string; days: number }>(
        'afianco:date-range-selected',
        {
          detail: { from: this.dateFrom, to: this.dateTo, days: dayDiff },
          bubbles: true,
          composed: true,
        },
      ),
    );
  }

  /** R3 — true se una qualsiasi data in [from,to] è tra le blockedDates.
   *  Usa i componenti locali (NO toISOString, che shifta in TZ != UTC). */
  private rangeHasBlockedDate(from: string, to: string): boolean {
    const blocked = new Set(this.blockedDates);
    if (!blocked.size) return false;
    const fmt = (d: Date): string =>
      `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
    const cur = new Date(from + 'T00:00:00');
    const end = new Date(to + 'T00:00:00');
    while (cur <= end) {
      if (blocked.has(fmt(cur))) return true;
      cur.setDate(cur.getDate() + 1);
    }
    return false;
  }

  // ── Helpers ─────────────────────────────────────────────────────────

  private todayISO(): string {
    const d = new Date();
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  }

  private get rentalDays(): number {
    if (!this.dateFrom || !this.dateTo) return 0;
    const from = new Date(this.dateFrom);
    const to = new Date(this.dateTo);
    if (Number.isNaN(from.getTime()) || Number.isNaN(to.getTime())) return 0;
    return Math.ceil((to.getTime() - from.getTime()) / (1000 * 60 * 60 * 24)) + 1;
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
      .inputs {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 12px;
      }
      .field {
        display: flex;
        flex-direction: column;
        gap: 4px;
      }
      .field-label {
        font-size: 12px;
        font-weight: 500;
        color: var(--afianco-color-text-secondary, #6b7280);
      }
      .field input[type='date'] {
        padding: 10px 12px;
        border: 1.5px solid var(--afianco-color-border, #e5e7eb);
        border-radius: 8px;
        font-family: inherit;
        font-size: 14px;
        color: var(--afianco-color-text, #111827);
        background: var(--afianco-color-surface, #ffffff);
        transition: border-color 0.15s ease;
      }
      .field input[type='date']:hover {
        border-color: var(--afianco-color-border-strong, #d1d5db);
      }
      .field input[type='date']:focus {
        outline: none;
        border-color: var(--afianco-color-primary, #4b72ce);
      }
      .summary {
        margin-top: 12px;
        background: var(--afianco-color-primary-soft, #eef2ff);
        border: 1px solid var(--afianco-color-primary, #4b72ce);
        border-radius: 8px;
        padding: 10px 14px;
        font-size: 13px;
        color: var(--afianco-color-primary-text-on-soft, #1e3a8a);
      }
      .error {
        margin-top: 8px;
        font-size: 13px;
        color: var(--afianco-color-danger, #ef4444);
        background: #fef2f2;
        border-radius: 6px;
        padding: 8px 12px;
      }
      @media (max-width: 480px) {
        .inputs {
          grid-template-columns: 1fr;
        }
      }
    `,
  ];

  // ── Render ──────────────────────────────────────────────────────────

  render() {
    const days = this.rentalDays;
    const hasValidRange = days > 0 && !this.error;

    return html`
      <span class="group-label">${this.groupLabel || t('rental.group_label')}</span>
      <div class="inputs">
        <div class="field">
          <label class="field-label" for="rental-date-from">Inizio</label>
          <input
            id="rental-date-from"
            type="date"
            min=${this.todayISO()}
            .value=${this.dateFrom}
            @input=${this.handleFromChange}>
        </div>
        <div class="field">
          <label class="field-label" for="rental-date-to">Fine</label>
          <input
            id="rental-date-to"
            type="date"
            min=${this.dateFrom || this.todayISO()}
            .value=${this.dateTo}
            @input=${this.handleToChange}>
        </div>
      </div>

      ${this.error
        ? html`<div class="error" role="alert">${this.error}</div>`
        : nothing}

      ${hasValidRange
        ? html`
            <div class="summary" role="status" aria-live="polite">
              ✓ Noleggio di <strong>${days} ${days === 1 ? this.rentalUnit : this.rentalUnit + (this.rentalUnit.endsWith('a') ? 'e' : 'i')}</strong>
              dal ${this.dateFrom} al ${this.dateTo}
            </div>
          `
        : nothing}
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'afianco-date-range-picker': AfiancoDateRangePicker;
  }
  interface HTMLElementEventMap {
    'afianco:date-range-selected': CustomEvent<{ from: string; to: string; days: number }>;
    'afianco:date-range-cleared': CustomEvent;
  }
}
