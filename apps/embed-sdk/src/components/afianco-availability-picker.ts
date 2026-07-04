/**
 * <afianco-availability-picker> — Track E Step 2.4.7 (slot booking).
 *
 * Calendario + slot grid per la prenotazione di un service product.
 * Mirror funzionale di AvailabilityCalendarSlotPicker.js dello storefront
 * React. Componente self-contained: fetcha da
 * `client.embed.getProductAvailability(productId)` e gestisce internamente:
 *   - Date carousel (7-14 giorni consecutivi)
 *   - Time grid per data selezionata
 *   - Selezione slot finale → emette `afianco:slot-selected`
 *
 * UX flow:
 *   1. Mount → fetch availability (date range = next 30 giorni)
 *   2. User clicca un giorno → mostra slot grid per quel giorno
 *   3. User clicca uno slot → emette evento + lo highlights selected
 *   4. Parent (product-detail) accumula la selezione + chiama checkout
 *
 * Custom events:
 *   - afianco:slot-selected (detail: { date, start, end })
 *   - afianco:slot-cleared
 *
 * Attributes:
 *   - product-id (required): UUID del prodotto service
 *   - days (default 14): quanti giorni mostrare nel carousel
 *   - duration (optional): override slot duration in minuti
 *
 * Accessibility:
 *   - role="group" + aria-label per il container
 *   - Date button con aria-pressed per state
 *   - Slot button con aria-label localizzato (data + ora)
 *   - Keyboard nav: tab tra giorni + slot, Enter per selezione
 */

import { LitElement, html, css, nothing, type PropertyValues } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { consume } from '@lit/context';
import { afiancoBaseStyles } from '@afianco/design-tokens';
// W4.9 — i18n
import { t } from '../i18n/index.js';
import type {
  EmbedAvailabilityResponse,
  EmbedAvailabilityDay,
  EmbedAvailabilitySlot,
} from '@afianco/api-client';
import {
  storefrontContext,
  STOREFRONT_INITIAL,
  type StorefrontContext,
} from '../context.js';


interface SelectedSlot {
  date: string;       // YYYY-MM-DD
  start: string;      // HH:MM
  end: string;        // HH:MM
  day_name: string;   // localized
}


@customElement('afianco-availability-picker')
export class AfiancoAvailabilityPicker extends LitElement {
  // ── Context consumption ─────────────────────────────────────────────

  @consume({ context: storefrontContext, subscribe: true })
  @state()
  private ctx: StorefrontContext = STOREFRONT_INITIAL;

  // ── Public attributes ────────────────────────────────────────────────

  /** Product ID per fetch availability. Required. */
  @property({ type: String, attribute: 'product-id', reflect: true })
  productId = '';

  /** Quanti giorni mostrare (default 14). Cap a 30 (limite backend). */
  @property({ type: Number })
  days = 14;

  /** Override slot duration in minuti (default: product service_duration_minutes). */
  @property({ type: Number })
  duration: number | null = null;

  // ── Internal state ────────────────────────────────────────────────────

  /** Risposta dal backend (giorni con slot disponibili). */
  @state()
  private availability: EmbedAvailabilityResponse | null = null;

  /** Stato di loading durante il fetch. */
  @state()
  private loading = false;

  /** Errore eventuale (network o backend). */
  @state()
  private error: string | null = null;

  /** Data attualmente selezionata (YYYY-MM-DD). */
  @state()
  private selectedDate: string | null = null;

  /** Slot selezionato (con data full per cart payload). */
  @state()
  private selectedSlot: SelectedSlot | null = null;

  /** Tracking se gia' fetched (evita ricomincio in updated()). */
  private _initialized = false;

  // ── Lifecycle ────────────────────────────────────────────────────────

  protected updated(_changed: PropertyValues): void {
    // Fetch quando il context e' ready + productId presente + non gia' fatto
    if (this._initialized) return;
    if (this.ctx?.status !== 'ready' || !this.ctx.client) return;
    if (!this.productId) return;
    this._initialized = true;
    void this.fetchAvailability();
  }

  // ── Fetch ───────────────────────────────────────────────────────────

  private async fetchAvailability(): Promise<void> {
    if (!this.ctx?.client || !this.productId) return;
    this.loading = true;
    this.error = null;

    try {
      // Default: today → today + days
      const today = new Date();
      const dateFrom = this.formatISODate(today);
      const endDate = new Date(today);
      endDate.setDate(endDate.getDate() + Math.min(this.days, 30));
      const dateTo = this.formatISODate(endDate);

      const resp = await this.ctx.client.embed.getProductAvailability(
        this.productId,
        {
          date_from: dateFrom,
          date_to: dateTo,
          duration: this.duration ?? undefined,
        },
      );
      this.availability = resp;

      // Auto-select primo giorno disponibile per UX (riduce click)
      if (resp.days && resp.days.length > 0 && !this.selectedDate) {
        this.selectedDate = resp.days[0]!.date;
      }
    } catch (e) {
      const msg = (e as Error)?.message ?? t('availability.error_load');
      this.error = msg;
    } finally {
      this.loading = false;
    }
  }

  // ── Handlers ────────────────────────────────────────────────────────

  private handleDateClick(day: EmbedAvailabilityDay): void {
    this.selectedDate = day.date;
    // Clear slot se cambio giorno (UX: riselezione esplicita)
    if (this.selectedSlot && this.selectedSlot.date !== day.date) {
      this.selectedSlot = null;
      this.dispatchEvent(
        new CustomEvent('afianco:slot-cleared', {
          bubbles: true,
          composed: true,
        }),
      );
    }
  }

  private handleSlotClick(day: EmbedAvailabilityDay, slot: EmbedAvailabilitySlot): void {
    const selection: SelectedSlot = {
      date: day.date,
      start: slot.start,
      end: slot.end,
      day_name: day.day_name,
    };
    this.selectedSlot = selection;
    this.dispatchEvent(
      new CustomEvent<SelectedSlot>('afianco:slot-selected', {
        detail: selection,
        bubbles: true,
        composed: true,
      }),
    );
  }

  /** Public API: clear current selection. */
  clearSelection(): void {
    this.selectedSlot = null;
    this.dispatchEvent(
      new CustomEvent('afianco:slot-cleared', { bubbles: true, composed: true }),
    );
  }

  // ── Date helpers ────────────────────────────────────────────────────

  private formatISODate(d: Date): string {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  }

  /** Formato visualizzato sulla card data: "Lun 5" / "Mar 6". */
  private displayDayLabel(d: EmbedAvailabilityDay): { dayName: string; dayNum: string; month: string } {
    // d.day_name e' es. "lunedi", "martedi" — abbrevio a 3 char
    const dayName = (d.day_name || '').slice(0, 3);
    // d.date e' YYYY-MM-DD → estraggo day + month
    const [, mStr, dayStr] = d.date.split('-');
    const monthLabel = this.monthNameShort(Number(mStr ?? 0));
    return {
      dayName: dayName.charAt(0).toUpperCase() + dayName.slice(1),
      dayNum: String(Number(dayStr ?? 0)),
      month: monthLabel,
    };
  }

  private monthNameShort(monthNum: number): string {
    // monthNum: 1-12
    const months = [
      'gen', 'feb', 'mar', 'apr', 'mag', 'giu',
      'lug', 'ago', 'set', 'ott', 'nov', 'dic',
    ];
    return months[monthNum - 1] ?? '';
  }

  // ── Styles ──────────────────────────────────────────────────────────

  static styles = [
    afiancoBaseStyles,
    css`
      :host {
        display: block;
      }

      .container {
        display: flex;
        flex-direction: column;
        gap: 16px;
      }

      .label {
        font-size: 13px;
        font-weight: 600;
        color: var(--afianco-color-text, #111827);
      }

      /* ── State messages ───────────────────────────────────────────── */
      .state-msg {
        padding: 24px 16px;
        text-align: center;
        font-size: 13px;
        color: var(--afianco-color-text-secondary, #6b7280);
        background: var(--afianco-color-muted, #f3f4f6);
        border-radius: 8px;
      }
      .state-msg.error {
        color: var(--afianco-color-danger, #ef4444);
        background: #fef2f2;
      }

      /* ── Date carousel (horizontal scroll) ────────────────────────── */
      .dates-row {
        display: flex;
        gap: 8px;
        overflow-x: auto;
        padding: 4px 2px;
        scrollbar-width: thin;
      }
      .date-btn {
        flex-shrink: 0;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 2px;
        min-width: 64px;
        padding: 10px 8px;
        background: var(--afianco-color-surface, #ffffff);
        border: 1.5px solid var(--afianco-color-border, #e5e7eb);
        border-radius: 10px;
        cursor: pointer;
        transition: border-color 0.15s ease, background 0.15s ease;
        font-family: inherit;
      }
      .date-btn:hover {
        border-color: var(--afianco-color-primary, #4b72ce);
      }
      .date-btn[aria-pressed='true'] {
        border-color: var(--afianco-color-primary, #4b72ce);
        background: var(--afianco-color-primary, #4b72ce);
        color: var(--afianco-color-primary-text, #ffffff);
      }
      .date-btn:focus-visible {
        outline: 2px solid var(--afianco-color-primary, #4b72ce);
        outline-offset: 2px;
      }
      .date-day-name {
        font-size: 11px;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        opacity: 0.7;
      }
      .date-day-num {
        font-size: 18px;
        font-weight: 700;
        line-height: 1;
      }
      .date-month {
        font-size: 11px;
        font-weight: 500;
        opacity: 0.7;
      }

      /* ── Slot grid ────────────────────────────────────────────────── */
      .slots-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(94px, 1fr));
        gap: 8px;
      }
      .slot-btn {
        padding: 10px 8px;
        background: var(--afianco-color-surface, #ffffff);
        border: 1.5px solid var(--afianco-color-border, #e5e7eb);
        border-radius: 8px;
        cursor: pointer;
        font-family: inherit;
        font-size: 13px;
        font-weight: 600;
        color: var(--afianco-color-text, #111827);
        transition: border-color 0.15s ease, background 0.15s ease;
        text-align: center;
      }
      .slot-btn:hover {
        border-color: var(--afianco-color-primary, #4b72ce);
        background: var(--afianco-color-muted, #f9fafb);
      }
      .slot-btn[aria-pressed='true'] {
        border-color: var(--afianco-color-primary, #4b72ce);
        background: var(--afianco-color-primary, #4b72ce);
        color: var(--afianco-color-primary-text, #ffffff);
      }
      .slot-btn:focus-visible {
        outline: 2px solid var(--afianco-color-primary, #4b72ce);
        outline-offset: 2px;
      }

      /* ── Selected slot summary ─────────────────────────────────────── */
      .summary {
        background: var(--afianco-color-primary-soft, #eef2ff);
        border: 1px solid var(--afianco-color-primary, #4b72ce);
        border-radius: 8px;
        padding: 10px 14px;
        font-size: 13px;
        color: var(--afianco-color-primary-text-on-soft, #1e3a8a);
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
      }
      .summary-clear {
        background: transparent;
        border: none;
        color: var(--afianco-color-primary, #4b72ce);
        cursor: pointer;
        font-size: 12px;
        font-weight: 600;
        text-decoration: underline;
        font-family: inherit;
      }

      /* ── Empty state ──────────────────────────────────────────────── */
      .no-slots {
        font-size: 13px;
        color: var(--afianco-color-text-muted, #9ca3af);
        font-style: italic;
        padding: 12px;
        text-align: center;
      }
    `,
  ];

  // ── Render ──────────────────────────────────────────────────────────

  render() {
    if (this.loading && !this.availability) {
      return html`<div class="state-msg">${t('availability.loading')}</div>`;
    }
    if (this.error) {
      return html`<div class="state-msg error" role="alert">${this.error}</div>`;
    }
    if (!this.availability || this.availability.days.length === 0) {
      return html`
        <div class="state-msg">
          ${t('availability.empty_n_days', { days: this.days })}
        </div>
      `;
    }

    const days = this.availability.days;
    const currentDay = days.find((d) => d.date === this.selectedDate) ?? days[0]!;

    return html`
      <div class="container">
        <span class="label">${t('availability.choose_date_time')}</span>

        <!-- Date carousel -->
        <div class="dates-row" role="tablist" aria-label=${t('availability.dates_available_aria')}>
          ${days.map((d) => {
            const isSelected = this.selectedDate === d.date;
            const label = this.displayDayLabel(d);
            return html`
              <button
                class="date-btn"
                type="button"
                role="tab"
                aria-pressed=${isSelected ? 'true' : 'false'}
                aria-label="${d.day_name} ${label.dayNum} ${label.month}, ${d.slots.length} slot disponibili"
                @click=${() => this.handleDateClick(d)}>
                <span class="date-day-name">${label.dayName}</span>
                <span class="date-day-num">${label.dayNum}</span>
                <span class="date-month">${label.month}</span>
              </button>
            `;
          })}
        </div>

        <!-- Slot grid per data selezionata -->
        ${currentDay && currentDay.slots.length > 0
          ? html`
              <div class="slots-grid" role="group" aria-label=${t('availability.times_aria')}>
                ${currentDay.slots.map((slot) => {
                  const isSelected =
                    this.selectedSlot?.date === currentDay.date &&
                    this.selectedSlot?.start === slot.start;
                  return html`
                    <button
                      class="slot-btn"
                      type="button"
                      aria-pressed=${isSelected ? 'true' : 'false'}
                      aria-label="Slot ${slot.start} - ${slot.end}"
                      @click=${() => this.handleSlotClick(currentDay, slot)}>
                      ${slot.start}
                    </button>
                  `;
                })}
              </div>
            `
          : html`<div class="no-slots">${t('availability.empty_day')}</div>`}

        <!-- Selected slot summary -->
        ${this.selectedSlot
          ? html`
              <div class="summary" role="status" aria-live="polite">
                <span>
                  ✓ <strong>${this.selectedSlot.day_name}</strong>
                  ${this.selectedSlot.date} ore ${this.selectedSlot.start}
                </span>
                <button
                  class="summary-clear"
                  type="button"
                  @click=${() => this.clearSelection()}>
                  ${t('availability.change_btn')}
                </button>
              </div>
            `
          : nothing}
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'afianco-availability-picker': AfiancoAvailabilityPicker;
  }
  interface HTMLElementEventMap {
    'afianco:slot-selected': CustomEvent<SelectedSlot>;
    'afianco:slot-cleared': CustomEvent;
  }
}
