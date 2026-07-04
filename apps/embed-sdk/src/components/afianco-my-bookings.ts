/**
 * <afianco-my-bookings> — Track E Step 2.4.8 (customer bookings + reservations).
 *
 * Vista unificata di:
 *   - Bookings (service products con slot riservato — IssuedBooking)
 *   - Reservations (rental products con date — IssuedReservation)
 *
 * Mostra una timeline cronologica (piu' recenti in cima) con badge tipo
 * (Servizio / Noleggio) + status + dettagli temporali.
 *
 * Fetch parallelo:
 *   - GET /api/customer/bookings (servizi)
 *   - GET /api/customer/reservations (noleggi)
 *
 * Custom events:
 *   - afianco:booking-clicked (detail: { type, id })
 *
 * Attributes:
 *   - no-auto-fetch (boolean)
 */

import { LitElement, html, css, nothing, type PropertyValues } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { consume } from '@lit/context';
import { afiancoBaseStyles } from '@afianco/design-tokens';
// W4.9 — i18n
import { t } from '../i18n/index.js';
import type {
  CustomerBooking,
  CustomerReservation,
} from '@afianco/api-client';
import {
  storefrontContext,
  STOREFRONT_INITIAL,
  type StorefrontContext,
} from '../context.js';


// Unified row type per la timeline (bookings + reservations)
type TimelineEntry =
  | ({ type: 'booking' } & CustomerBooking)
  | ({ type: 'reservation' } & CustomerReservation);


@customElement('afianco-my-bookings')
export class AfiancoMyBookings extends LitElement {
  @consume({ context: storefrontContext, subscribe: true })
  @state()
  ctx: StorefrontContext = STOREFRONT_INITIAL;

  @property({ type: Boolean, attribute: 'no-auto-fetch' })
  noAutoFetch = false;

  @state()
  private entries: TimelineEntry[] = [];

  @state()
  private loading = false;

  @state()
  private error: string | null = null;

  private _initialized = false;

  protected updated(_changed: PropertyValues): void {
    if (this._initialized) return;
    if (this.noAutoFetch) return;
    if (this.ctx?.status !== 'ready' || !this.ctx.client) return;
    this._initialized = true;
    void this.fetchAll();
  }

  // ── Fetch parallelo ─────────────────────────────────────────────────

  async fetchAll(): Promise<void> {
    if (!this.ctx?.client) return;
    this.loading = true;
    this.error = null;
    try {
      const [bookingsResp, reservationsResp] = await Promise.all([
        this.ctx.client.customer.bookings().catch(() => ({ bookings: [], total: 0 })),
        this.ctx.client.customer.reservations().catch(() => ({ reservations: [], total: 0 })),
      ]);
      const bookings: TimelineEntry[] = (bookingsResp.bookings ?? []).map(
        (b) => ({ ...b, type: 'booking' as const }),
      );
      const reservations: TimelineEntry[] = (reservationsResp.reservations ?? []).map(
        (r) => ({ ...r, type: 'reservation' as const }),
      );
      // Merge + sort cronologico (più recente in cima per data evento)
      this.entries = [...bookings, ...reservations].sort((a, b) => {
        const da = this.getSortDate(a);
        const db = this.getSortDate(b);
        return db.localeCompare(da);
      });
    } catch (e) {
      this.error = (e as Error)?.message ?? t('booking.error_load');
    } finally {
      this.loading = false;
    }
  }

  // ── Helpers ─────────────────────────────────────────────────────────

  private getSortDate(e: TimelineEntry): string {
    if (e.type === 'booking') return e.booking_date ?? '';
    return e.rental_date_from ?? e.booking_date ?? '';
  }

  private formatDate(iso: string | null | undefined): string {
    if (!iso) return '—';
    try {
      return new Date(iso).toLocaleDateString('it-IT', {
        weekday: 'short',
        day: 'numeric',
        month: 'short',
        year: 'numeric',
      });
    } catch {
      return iso;
    }
  }

  private statusBadge(e: TimelineEntry): { label: string; cls: string } {
    const status = e.type === 'reservation'
      ? (e.approval_status ?? e.status ?? 'pending')
      : (e.status ?? 'confirmed');
    if (status === 'cancelled' || status === 'rejected') {
      return { label: 'Cancellato', cls: 'badge-cancelled' };
    }
    if (status === 'pending' || status === 'awaiting_approval') {
      return { label: 'In attesa', cls: 'badge-pending' };
    }
    if (status === 'approved' || status === 'confirmed') {
      return { label: t('booking.status_confirmed'), cls: 'badge-confirmed' };
    }
    return { label: status, cls: 'badge-default' };
  }

  private handleClick(e: TimelineEntry): void {
    this.dispatchEvent(
      new CustomEvent<{ type: 'booking' | 'reservation'; id: string }>(
        'afianco:booking-clicked',
        {
          detail: { type: e.type, id: e.id },
          bubbles: true,
          composed: true,
        },
      ),
    );
  }

  // ── Styles ──────────────────────────────────────────────────────────

  static styles = [
    afiancoBaseStyles,
    css`
      :host { display: block; }

      .state-msg {
        padding: 32px 16px;
        text-align: center;
        color: var(--afianco-color-text-secondary, #6b7280);
        font-size: 14px;
      }
      .state-msg.error { color: var(--afianco-color-danger, #ef4444); }

      .empty {
        background: var(--afianco-color-muted, #f3f4f6);
        border-radius: 10px;
        padding: 32px 20px;
        text-align: center;
        color: var(--afianco-color-text-secondary, #6b7280);
      }
      .empty-icon { font-size: 32px; margin-bottom: 8px; }
      .empty-title {
        font-size: 15px; font-weight: 600;
        color: var(--afianco-color-text, #111827);
        margin-bottom: 4px;
      }

      .list {
        display: flex;
        flex-direction: column;
        gap: 10px;
      }
      .item {
        display: flex;
        gap: 14px;
        padding: 14px 16px;
        background: var(--afianco-color-surface, #ffffff);
        border: 1px solid var(--afianco-color-border, #e5e7eb);
        border-radius: 10px;
      }
      .item-icon {
        flex-shrink: 0;
        width: 44px;
        height: 44px;
        border-radius: 10px;
        background: var(--afianco-color-primary-soft, #eef2ff);
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 22px;
      }
      .item-body {
        flex: 1;
        min-width: 0;
      }
      .item-header {
        display: flex;
        justify-content: space-between;
        align-items: baseline;
        gap: 10px;
        flex-wrap: wrap;
      }
      .item-name {
        font-size: 14px;
        font-weight: 600;
        color: var(--afianco-color-text, #111827);
        line-height: 1.3;
      }
      .item-time {
        font-size: 13px;
        font-weight: 600;
        color: var(--afianco-color-primary, #4b72ce);
        margin-top: 4px;
      }
      .item-meta {
        display: flex;
        gap: 12px;
        font-size: 11px;
        color: var(--afianco-color-text-secondary, #6b7280);
        margin-top: 6px;
        flex-wrap: wrap;
      }

      .badge {
        display: inline-flex;
        padding: 2px 10px;
        border-radius: 9999px;
        font-size: 11px;
        font-weight: 600;
      }
      .badge-confirmed {
        background: #d1fae5;
        color: #065f46;
      }
      .badge-pending {
        background: #fef3c7;
        color: #92400e;
      }
      .badge-cancelled {
        background: #fee2e2;
        color: #991b1b;
      }
      .badge-default {
        background: var(--afianco-color-muted, #f3f4f6);
        color: var(--afianco-color-text-secondary, #6b7280);
      }
      .badge-type {
        background: var(--afianco-color-primary-soft, #eef2ff);
        color: var(--afianco-color-primary, #4b72ce);
        font-size: 10px;
        padding: 2px 8px;
        border-radius: 9999px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
      }
    `,
  ];

  // ── Render ──────────────────────────────────────────────────────────

  render() {
    if (this.loading) {
      return html`<div class="state-msg">${t('booking.loading')}</div>`;
    }
    if (this.error) {
      return html`<div class="state-msg error" role="alert">${this.error}</div>`;
    }
    if (this.entries.length === 0) {
      return html`
        <div class="empty">
          <div class="empty-icon" aria-hidden="true">📅</div>
          <div class="empty-title">${t('booking.empty')}</div>
          <div>Le tue prenotazioni servizi e noleggi compariranno qui.</div>
        </div>
      `;
    }

    return html`
      <div class="list">
        ${this.entries.map((e) => {
          const badge = this.statusBadge(e);
          const isBooking = e.type === 'booking';
          const icon = isBooking ? '🗓' : '📦';
          const typeLabel = isBooking ? 'Servizio' : 'Noleggio';

          let timeStr = '';
          if (isBooking) {
            const b = e as { type: 'booking' } & CustomerBooking;
            timeStr = `${this.formatDate(b.booking_date)}${b.booking_start_time ? ' · ' + b.booking_start_time : ''}`;
            if (b.booking_end_time) timeStr += ' – ' + b.booking_end_time;
          } else {
            const r = e as { type: 'reservation' } & CustomerReservation;
            if (r.rental_date_from && r.rental_date_to) {
              timeStr = `Dal ${this.formatDate(r.rental_date_from)} al ${this.formatDate(r.rental_date_to)}`;
            } else if (r.booking_date) {
              timeStr = this.formatDate(r.booking_date);
            }
          }

          return html`
            <div class="item" @click=${() => this.handleClick(e)}>
              <div class="item-icon" aria-hidden="true">${icon}</div>
              <div class="item-body">
                <div class="item-header">
                  <div class="item-name">${e.product_name}</div>
                  <span class="badge ${badge.cls}">${badge.label}</span>
                </div>
                <div class="item-time">${timeStr}</div>
                <div class="item-meta">
                  <span class="badge-type">${typeLabel}</span>
                  ${isBooking && (e as CustomerBooking).service_option_label
                    ? html`<span>${(e as CustomerBooking).service_option_label}</span>`
                    : nothing}
                  ${isBooking && (e as CustomerBooking).location
                    ? html`<span>📍 ${(e as CustomerBooking).location}</span>`
                    : nothing}
                  <span>Cod. ${e.code}</span>
                </div>
                <div style="margin-top: 8px; display:flex; gap:14px; flex-wrap:wrap;">
                  ${(e as { access_token?: string | null }).access_token
                    ? html`
                        <a
                          href=${this.buildIcsUrl(e)}
                          target="_blank"
                          rel="noopener noreferrer"
                          style="display:inline-flex; align-items:center; gap:4px;
                                 font-size: 12px; font-weight: 600;
                                 color: var(--afianco-color-primary, #4b72ce);
                                 text-decoration: none;">
                          <span aria-hidden="true">📅</span>
                          Aggiungi al calendario (.ics)
                        </a>
                      `
                    : nothing}
                  <!-- Track E Step 5.5 — cancel booking button -->
                  ${e.type === 'booking' && e.status !== 'cancelled'
                    ? html`
                        <button
                          type="button"
                          @click=${() => void this.cancelBookingClick(e.id)}
                          style="display:inline-flex; align-items:center; gap:4px;
                                 background: transparent; border: none;
                                 padding: 0; cursor: pointer;
                                 font-size: 12px; font-weight: 600;
                                 color: var(--afianco-color-danger, #ef4444);
                                 text-decoration: underline;
                                 font-family: inherit;">
                          <span aria-hidden="true">🗙</span>
                          Cancella prenotazione
                        </button>
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

  /**
   * Track E Step 5.2 — build .ics download URL per booking o reservation.
   * Booking → /api/public/bookings/{token}/ics
   * Reservation → /api/public/reservations/{token}/ics
   */
  private buildIcsUrl(e: TimelineEntry): string {
    const token = (e as { access_token?: string | null }).access_token;
    if (!token) return '#';
    const base = this.ctx?.client?.baseUrl ?? '';
    const subpath = e.type === 'booking' ? 'bookings' : 'reservations';
    return `${base}/api/public/${subpath}/${encodeURIComponent(token)}/ics`;
  }

  /**
   * Track E Step 5.5 — Cancel booking handler.
   * Confirm via browser confirm() (light UX). V2: modal dedicato.
   */
  private async cancelBookingClick(bookingId: string): Promise<void> {
    if (!this.ctx?.client) return;
    const ok = typeof confirm !== 'undefined'
      ? confirm('Sei sicuro di voler cancellare questa prenotazione?')
      : true;
    if (!ok) return;
    try {
      await this.ctx.client.customer.cancelBooking(bookingId);
      // Refresh list — re-fetch bookings + reservations
      this._initialized = false;
      await this.fetchAll();
    } catch (e) {
      const msg = (e as Error)?.message ?? t('booking.error_cancel');
      this.error = msg;
    }
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'afianco-my-bookings': AfiancoMyBookings;
  }
  interface HTMLElementEventMap {
    'afianco:booking-clicked': CustomEvent<{ type: 'booking' | 'reservation'; id: string }>;
  }
}
