/**
 * <afianco-custom-request> — R4 (service custom request).
 *
 * Per servizi con `service_allow_custom_request` e SENZA slot pubblicati: il
 * cliente propone data/ora preferita + note. È una PROPOSTA — l'admin conferma
 * manualmente dopo l'acquisto. Mirror funzionale della custom-request dello
 * storefront (StorefrontPage `service_custom_request`), così A=B=C.
 *
 * La compilazione è OPZIONALE: il servizio resta acquistabile anche senza
 * (il validator backend accetta slot mancante quando custom request è
 * abilitata). Quando data+inizio+fine sono presenti, emette il payload
 * completo con `complete: true`; il parent allora marca l'order-item con
 * service_custom_request=true + booking_date/start/end + rental_notes.
 *
 * Custom events:
 *   - afianco:custom-request-changed (detail: { date, start, end, notes, complete })
 *
 * NB: i campi vuoti NON sono un errore (form opzionale): si emette
 * `complete: false` e il parent ignora la proposta parziale.
 */

import { LitElement, html, css } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { afiancoBaseStyles } from '@afianco/design-tokens';
import { t } from '../i18n/index.js';

export interface CustomRequestDetail {
  date: string;
  start: string;
  end: string;
  notes: string;
  complete: boolean;
}

@customElement('afianco-custom-request')
export class AfiancoCustomRequest extends LitElement {
  /** Label localizzata del gruppo. */
  @property({ type: String, attribute: 'group-label' })
  groupLabel = '';

  @state() private date = '';
  @state() private start = '';
  @state() private end = '';
  @state() private notes = '';
  @state() private error: string | null = null;

  private todayISO(): string {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(
      d.getDate(),
    ).padStart(2, '0')}`;
  }

  private get isComplete(): boolean {
    return Boolean(this.date && this.start && this.end);
  }

  private onField(field: 'date' | 'start' | 'end' | 'notes', e: Event): void {
    const value = (e.target as HTMLInputElement | HTMLTextAreaElement).value;
    this[field] = value;
    this.emit();
  }

  private emit(): void {
    this.error = null;
    // Validazione leggera: se data+inizio+fine ci sono, end > start.
    if (this.isComplete && this.end <= this.start) {
      this.error = t('rental.error_end_before_start');
      // Emette comunque complete=false così il parent non usa un range invalido.
      this.dispatchEvent(
        new CustomEvent<CustomRequestDetail>('afianco:custom-request-changed', {
          detail: { date: this.date, start: this.start, end: this.end, notes: this.notes, complete: false },
          bubbles: true,
          composed: true,
        }),
      );
      return;
    }
    this.dispatchEvent(
      new CustomEvent<CustomRequestDetail>('afianco:custom-request-changed', {
        detail: {
          date: this.date,
          start: this.start,
          end: this.end,
          notes: this.notes,
          complete: this.isComplete,
        },
        bubbles: true,
        composed: true,
      }),
    );
  }

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
        margin-bottom: 6px;
        display: block;
      }
      .hint {
        font-size: 12px;
        color: var(--afianco-color-text-secondary, #6b7280);
        margin-bottom: 10px;
      }
      .grid {
        display: grid;
        grid-template-columns: 1fr 1fr 1fr;
        gap: 10px;
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
      input,
      textarea {
        padding: 10px 12px;
        border: 1.5px solid var(--afianco-color-border, #e5e7eb);
        border-radius: 8px;
        font-family: inherit;
        font-size: 14px;
        color: var(--afianco-color-text, #111827);
        background: var(--afianco-color-surface, #ffffff);
      }
      input:focus,
      textarea:focus {
        outline: none;
        border-color: var(--afianco-color-primary, #4b72ce);
      }
      .notes {
        margin-top: 10px;
        display: flex;
        flex-direction: column;
        gap: 4px;
      }
      textarea {
        resize: vertical;
        min-height: 60px;
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
        .grid {
          grid-template-columns: 1fr;
        }
      }
    `,
  ];

  render() {
    return html`
      <span class="group-label">${this.groupLabel || t('custom_request.group_label')}</span>
      <div class="hint">${t('custom_request.hint')}</div>
      <div class="grid">
        <div class="field">
          <label class="field-label" for="cr-date">${t('custom_request.date_label')}</label>
          <input
            id="cr-date"
            type="date"
            min=${this.todayISO()}
            .value=${this.date}
            @input=${(e: Event) => this.onField('date', e)}>
        </div>
        <div class="field">
          <label class="field-label" for="cr-start">${t('custom_request.start_label')}</label>
          <input
            id="cr-start"
            type="time"
            .value=${this.start}
            @input=${(e: Event) => this.onField('start', e)}>
        </div>
        <div class="field">
          <label class="field-label" for="cr-end">${t('custom_request.end_label')}</label>
          <input
            id="cr-end"
            type="time"
            .value=${this.end}
            @input=${(e: Event) => this.onField('end', e)}>
        </div>
      </div>
      <div class="notes">
        <label class="field-label" for="cr-notes">${t('custom_request.notes_label')}</label>
        <textarea
          id="cr-notes"
          maxlength="500"
          .value=${this.notes}
          @input=${(e: Event) => this.onField('notes', e)}></textarea>
      </div>
      ${this.error ? html`<div class="error" role="alert">${this.error}</div>` : null}
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'afianco-custom-request': AfiancoCustomRequest;
  }
  interface HTMLElementEventMap {
    'afianco:custom-request-changed': CustomEvent<CustomRequestDetail>;
  }
}
