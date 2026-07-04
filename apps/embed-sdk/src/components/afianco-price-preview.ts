/**
 * <afianco-price-preview> — Track E Step 2.4.10 (live total).
 *
 * Sticky price summary che chiama `POST /api/public/embed/price-preview/{slug}`
 * con debounced fetch (300ms) ogni volta che le sue prop cambiano (qty,
 * date range, slot, extras).
 *
 * Pattern: pure presenter + fetch logic. Riceve TUTTE le selezioni come
 * props dal parent (<afianco-product-detail>) e ricomputa il totale
 * server-side per consistency con il checkout finale (che usa la STESSA
 * pricing pipeline `compute_line_total`).
 *
 * Razionale: prezzi calcolati lato server eliminano la classe di bug
 * "client mostra X ma server ti addebita Y" — tipica fonte di reclami
 * customer. Server e' sempre source of truth.
 *
 * Custom events:
 *   - afianco:price-updated (detail: { result }) — fired ogni volta che
 *     il backend risponde con nuovi totali (utile per parent che vuole
 *     mostrare il prezzo anche fuori dal preview component).
 *
 * Attributes:
 *   - product-id (required)
 *   - quantity (number, default 1)
 *   - currency (string, fallback EUR)
 *
 * Props (set via Lit .prop=...):
 *   - dateFrom / dateTo (rental flavor=range)
 *   - slotDate / slotStart / slotEnd (service slot or rental flavor=slot)
 *   - extraSelections (oggetto Onda 16: {mandatory_confirmed, optional_ids, radio_picks})
 */

import { LitElement, html, css, nothing } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { consume } from '@lit/context';
import { afiancoBaseStyles } from '@afianco/design-tokens';
// Sprint 4 W4.7 — i18n wiring
import { t } from '../i18n/index.js';
import type {
  EmbedPricePreviewRequest,
  EmbedPricePreviewResponse,
  EmbedExtraSelectionsPayload,
} from '@afianco/api-client';
import {
  storefrontContext,
  STOREFRONT_INITIAL,
  type StorefrontContext,
} from '../context.js';


// Debounce window per coalescer di multiple change event veloci
const DEBOUNCE_MS = 300;


@customElement('afianco-price-preview')
export class AfiancoPricePreview extends LitElement {
  @consume({ context: storefrontContext, subscribe: true })
  @state()
  ctx: StorefrontContext = STOREFRONT_INITIAL;

  @property({ type: String, attribute: 'product-id', reflect: true })
  productId = '';

  @property({ type: Number })
  quantity = 1;

  @property({ type: String })
  currency = 'EUR';

  /** Discount % opzionale (0-100). */
  @property({ type: Number, attribute: 'discount-pct' })
  discountPct = 0;

  // ── Rental flavor=range ──
  @property({ type: String })
  dateFrom: string | null = null;

  @property({ type: String })
  dateTo: string | null = null;

  // ── Slot flavor (service + rental flavor=slot) ──
  @property({ type: String })
  slotDate: string | null = null;

  @property({ type: String })
  slotStart: string | null = null;

  @property({ type: String })
  slotEnd: string | null = null;

  /** Extras selections (Onda 16 payload shape). */
  @property({ attribute: false })
  extraSelections: EmbedExtraSelectionsPayload | null = null;

  // ── Internal state ────────────────────────────────────────────────────

  @state()
  private result: EmbedPricePreviewResponse | null = null;

  @state()
  private loading = false;

  @state()
  private error: string | null = null;

  private _debounceTimer: ReturnType<typeof setTimeout> | null = null;

  // ── Lifecycle ────────────────────────────────────────────────────────

  protected updated(changedProps: Map<string, unknown>): void {
    // Trigger debounced re-fetch on ANY input change.
    // Salto solo i changes che NON sono input (es. result/loading/error)
    const inputProps = [
      'productId', 'quantity', 'currency', 'discountPct',
      'dateFrom', 'dateTo',
      'slotDate', 'slotStart', 'slotEnd',
      'extraSelections',
    ];
    if (Array.from(changedProps.keys()).some((k) => inputProps.includes(String(k)))) {
      this.scheduleDebouncedFetch();
    }
  }

  disconnectedCallback(): void {
    if (this._debounceTimer) {
      clearTimeout(this._debounceTimer);
      this._debounceTimer = null;
    }
    super.disconnectedCallback();
  }

  // ── Debounce + fetch ────────────────────────────────────────────────

  private scheduleDebouncedFetch(): void {
    if (this._debounceTimer) clearTimeout(this._debounceTimer);
    this._debounceTimer = setTimeout(() => void this.fetchPrice(), DEBOUNCE_MS);
  }

  private async fetchPrice(): Promise<void> {
    if (!this.ctx?.client || !this.productId) return;

    // Build payload — campi conditional in base alla type-specific selection
    const body: EmbedPricePreviewRequest = {
      product_id: this.productId,
      quantity: this.quantity,
      discount_pct: this.discountPct,
    };
    if (this.dateFrom) body.date_from = this.dateFrom;
    if (this.dateTo) body.date_to = this.dateTo;
    if (this.slotDate && this.slotStart) {
      // Slot booking for service or rental flavor=slot
      body.slot_date_from = this.slotDate;
      body.slot_time_from = this.slotStart;
      if (this.slotEnd) {
        body.slot_date_to = this.slotDate;
        body.slot_time_to = this.slotEnd;
      }
    }
    if (this.extraSelections) {
      body.extra_selections = this.extraSelections;
    }

    this.loading = true;
    this.error = null;
    try {
      const res = await this.ctx.client.embed.pricePreview(body);
      this.result = res;
      this.dispatchEvent(
        new CustomEvent<{ result: EmbedPricePreviewResponse }>(
          'afianco:price-updated',
          {
            detail: { result: res },
            bubbles: true,
            composed: true,
          },
        ),
      );
    } catch (e) {
      this.error = (e as Error)?.message ?? t('price.error_calc');
    } finally {
      this.loading = false;
    }
  }

  // ── Helpers ─────────────────────────────────────────────────────────

  private formatPrice(amount: number | undefined | null): string {
    if (amount == null) return '—';
    try {
      return new Intl.NumberFormat(undefined, {
        style: 'currency',
        currency: this.result?.currency || this.currency,
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
      :host { display: block; }

      .preview {
        background: var(--afianco-color-surface, #ffffff);
        border: 1px solid var(--afianco-color-border, #e5e7eb);
        border-radius: 10px;
        padding: 14px 16px;
      }

      .title {
        font-size: 11px;
        font-weight: 700;
        color: var(--afianco-color-text-secondary, #6b7280);
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-bottom: 8px;
      }

      .row {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        padding: 4px 0;
        font-size: 13px;
        color: var(--afianco-color-text, #111827);
      }
      .row.muted {
        color: var(--afianco-color-text-secondary, #6b7280);
        font-size: 12px;
      }
      .row.total {
        border-top: 1px solid var(--afianco-color-border, #e5e7eb);
        margin-top: 8px;
        padding-top: 10px;
        font-size: 16px;
        font-weight: 700;
      }
      .row.total .amount {
        color: var(--afianco-color-primary, #4b72ce);
        font-size: 18px;
      }

      .loading-tag {
        font-size: 10px;
        color: var(--afianco-color-text-muted, #9ca3af);
        text-transform: uppercase;
        letter-spacing: 0.04em;
      }

      .error {
        font-size: 12px;
        color: var(--afianco-color-danger, #ef4444);
        padding: 8px 10px;
        background: #fef2f2;
        border-radius: 6px;
      }

      .placeholder {
        font-size: 12px;
        color: var(--afianco-color-text-muted, #9ca3af);
        text-align: center;
        padding: 12px;
        font-style: italic;
      }
    `,
  ];

  // ── Render ──────────────────────────────────────────────────────────

  render() {
    // Stato iniziale prima del primo fetch — placeholder neutro
    if (!this.result && !this.error && !this.loading) {
      return html`
        <div class="preview">
          <div class="title">${t('price.summary_title')}</div>
          <div class="placeholder">
            Le scelte qui aggiorneranno il prezzo finale.
          </div>
        </div>
      `;
    }

    if (this.error) {
      return html`
        <div class="preview">
          <div class="title">${t('price.summary_title')}</div>
          <div class="error" role="alert">${this.error}</div>
        </div>
      `;
    }

    const r = this.result;
    // Backend response shape (compute_line_total.to_dict):
    //   {base, extras_total, extras_breakdown, total, day_count, ...}
    // Fallback per compat con future shape change (es. subtotal/tax).
    const base = (r?.base as number) ?? (r?.subtotal as number) ?? 0;
    const extrasTotal = (r?.extras_total as number) ?? 0;
    const discount = (r?.discount as number) ?? 0;
    const tax = (r?.tax as number) ?? 0;
    const total = (r?.total as number) ?? 0;
    const dayCount = (r?.day_count as number | undefined) ?? null;

    return html`
      <div class="preview" aria-busy=${this.loading ? 'true' : 'false'}>
        <div class="title">
          ${t('price.summary_title')}
          ${this.loading ? html`<span class="loading-tag">— ${t('common.loading')}</span>` : nothing}
        </div>
        <div class="row">
          <span>
            ${dayCount && dayCount > 1
              ? html`${t('price.subtotal_with_days_other', { count: dayCount })}`
              : dayCount === 1
                ? html`${t('price.subtotal_with_days_one', { count: 1 })}`
                : html`${t('price.subtotal')}`}
          </span>
          <span>${this.formatPrice(base)}</span>
        </div>
        ${extrasTotal > 0
          ? html`
              <div class="row muted">
                <span>Inclusi extra</span>
                <span>+ ${this.formatPrice(extrasTotal)}</span>
              </div>
            `
          : nothing}
        ${discount > 0
          ? html`
              <div class="row muted">
                <span>Sconto</span>
                <span>− ${this.formatPrice(discount)}</span>
              </div>
            `
          : nothing}
        ${tax > 0
          ? html`
              <div class="row muted">
                <span>IVA</span>
                <span>${this.formatPrice(tax)}</span>
              </div>
            `
          : nothing}
        <div class="row total">
          <span>${t('price.total')}</span>
          <span class="amount">${this.formatPrice(total)}</span>
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'afianco-price-preview': AfiancoPricePreview;
  }
  interface HTMLElementEventMap {
    'afianco:price-updated': CustomEvent<{ result: EmbedPricePreviewResponse }>;
  }
}
