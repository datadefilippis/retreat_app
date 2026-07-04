/**
 * <afianco-my-downloads> — Track E Step 2.4.8 (customer downloads).
 *
 * Lista dei file digitali acquistati dal customer. Per ogni IssuedDownload
 * mostra:
 *   - Nome prodotto + data acquisto
 *   - Status (issued / downloaded / expired)
 *   - Downloads count / max_downloads
 *   - Pulsante "Scarica" → apre link signed in nuova tab
 *
 * Il link signed e' costruito client-side concatenando il baseUrl del
 * client + `/api/public/downloads/{access_token}/file`. Il backend serve
 * il file con increment del counter atomico.
 *
 * Custom events:
 *   - afianco:download-clicked (detail: { code, product_id })
 *
 * Attributes:
 *   - no-auto-fetch (boolean) — disable per test
 */

import { LitElement, html, css, nothing, type PropertyValues } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { consume } from '@lit/context';
import { afiancoBaseStyles } from '@afianco/design-tokens';
// W4.9 — i18n
import { t } from '../i18n/index.js';
import type { CustomerDownload } from '@afianco/api-client';
import {
  storefrontContext,
  STOREFRONT_INITIAL,
  type StorefrontContext,
} from '../context.js';


@customElement('afianco-my-downloads')
export class AfiancoMyDownloads extends LitElement {
  @consume({ context: storefrontContext, subscribe: true })
  @state()
  ctx: StorefrontContext = STOREFRONT_INITIAL;

  @property({ type: Boolean, attribute: 'no-auto-fetch' })
  noAutoFetch = false;

  @state()
  private items: CustomerDownload[] = [];

  @state()
  private loading = false;

  @state()
  private error: string | null = null;

  private _initialized = false;

  // ── Lifecycle ────────────────────────────────────────────────────────

  protected updated(_changed: PropertyValues): void {
    if (this._initialized) return;
    if (this.noAutoFetch) return;
    if (this.ctx?.status !== 'ready' || !this.ctx.client) return;
    this._initialized = true;
    void this.fetchDownloads();
  }

  async fetchDownloads(): Promise<void> {
    if (!this.ctx?.client) return;
    this.loading = true;
    this.error = null;
    try {
      const resp = await this.ctx.client.customer.downloads();
      this.items = resp.downloads ?? [];
    } catch (e) {
      this.error = (e as Error)?.message ?? t('download.error_load');
    } finally {
      this.loading = false;
    }
  }

  // ── Helpers ─────────────────────────────────────────────────────────

  private buildFileUrl(token: string): string {
    const base = this.ctx?.client?.baseUrl ?? '';
    return `${base}/api/public/downloads/${encodeURIComponent(token)}/file`;
  }

  private handleDownloadClick(d: CustomerDownload): void {
    this.dispatchEvent(
      new CustomEvent<{ code: string; product_id: string }>(
        'afianco:download-clicked',
        {
          detail: { code: d.code, product_id: d.product_id },
          bubbles: true,
          composed: true,
        },
      ),
    );
  }

  private formatDate(iso: string | null | undefined): string {
    if (!iso) return '—';
    try {
      return new Date(iso).toLocaleDateString('it-IT', {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
      });
    } catch {
      return iso;
    }
  }

  private statusBadge(d: CustomerDownload): { label: string; cls: string } {
    const s = d.status ?? 'issued';
    if (s === 'expired') return { label: t('downloads.status_expired'), cls: 'badge-expired' };
    if (s === 'downloaded') return { label: t('downloads.status_downloaded'), cls: 'badge-downloaded' };
    return { label: t('downloads.status_issued'), cls: 'badge-issued' };
  }

  private isExpired(d: CustomerDownload): boolean {
    if (d.status === 'expired') return true;
    if (d.expires_at) {
      try {
        return new Date(d.expires_at).getTime() < Date.now();
      } catch {
        return false;
      }
    }
    return false;
  }

  private isExhausted(d: CustomerDownload): boolean {
    if (d.max_downloads == null) return false;
    return (d.downloads_count ?? 0) >= d.max_downloads;
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
      .state-msg.error {
        color: var(--afianco-color-danger, #ef4444);
      }

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
        align-items: center;
        gap: 12px;
        padding: 12px 14px;
        background: var(--afianco-color-surface, #ffffff);
        border: 1px solid var(--afianco-color-border, #e5e7eb);
        border-radius: 10px;
      }
      .item-icon {
        flex-shrink: 0;
        width: 40px;
        height: 40px;
        background: var(--afianco-color-primary-soft, #eef2ff);
        border-radius: 8px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 20px;
      }
      .item-body {
        flex: 1;
        min-width: 0;
      }
      .item-name {
        font-size: 14px;
        font-weight: 600;
        color: var(--afianco-color-text, #111827);
        line-height: 1.3;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      .item-meta {
        display: flex;
        gap: 12px;
        font-size: 11px;
        color: var(--afianco-color-text-secondary, #6b7280);
        margin-top: 4px;
        flex-wrap: wrap;
      }

      .badge {
        display: inline-flex;
        padding: 2px 8px;
        border-radius: 9999px;
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
      }
      .badge-issued {
        background: var(--afianco-color-primary-soft, #eef2ff);
        color: var(--afianco-color-primary, #4b72ce);
      }
      .badge-downloaded {
        background: #d1fae5;
        color: #065f46;
      }
      .badge-expired {
        background: #fee2e2;
        color: #991b1b;
      }

      .download-btn {
        flex-shrink: 0;
        background: var(--afianco-color-primary, #4b72ce);
        color: var(--afianco-color-primary-text, #ffffff);
        border: none;
        border-radius: 8px;
        padding: 8px 16px;
        font-family: inherit;
        font-size: 13px;
        font-weight: 600;
        cursor: pointer;
        text-decoration: none;
        display: inline-flex;
        align-items: center;
        gap: 4px;
      }
      .download-btn:hover {
        opacity: 0.92;
      }
      .download-btn:disabled,
      .download-btn[aria-disabled='true'] {
        opacity: 0.4;
        cursor: not-allowed;
        pointer-events: none;
      }
    `,
  ];

  // ── Render ──────────────────────────────────────────────────────────

  render() {
    if (this.loading) {
      return html`<div class="state-msg">${t('download.loading')}</div>`;
    }
    if (this.error) {
      return html`<div class="state-msg error" role="alert">${this.error}</div>`;
    }
    if (this.items.length === 0) {
      return html`
        <div class="empty">
          <div class="empty-icon" aria-hidden="true">📥</div>
          <div class="empty-title">${t('download.empty')}</div>
          <div>I file digitali acquistati compariranno qui.</div>
        </div>
      `;
    }

    return html`
      <div class="list">
        ${this.items.map((d) => {
          const badge = this.statusBadge(d);
          const expired = this.isExpired(d);
          const exhausted = this.isExhausted(d);
          const disabled = expired || exhausted || !d.access_token;
          const url = d.access_token ? this.buildFileUrl(d.access_token) : '#';
          return html`
            <div class="item">
              <div class="item-icon" aria-hidden="true">📄</div>
              <div class="item-body">
                <div class="item-name">${d.product_name}</div>
                <div class="item-meta">
                  <span class="badge ${badge.cls}">${badge.label}</span>
                  ${d.max_downloads != null
                    ? html`<span>${d.downloads_count ?? 0}/${d.max_downloads} download</span>`
                    : d.downloads_count != null && d.downloads_count > 0
                      ? html`<span>${d.downloads_count} download</span>`
                      : nothing}
                  ${d.created_at
                    ? html`<span>${t('download.purchased_at', { date: this.formatDate(d.created_at) })}</span>`
                    : nothing}
                  ${d.expires_at
                    ? html`<span>${t('download.expires_at', { date: this.formatDate(d.expires_at) })}</span>`
                    : nothing}
                </div>
              </div>
              <a
                class="download-btn"
                href=${url}
                target="_blank"
                rel="noopener noreferrer"
                aria-disabled=${disabled ? 'true' : 'false'}
                @click=${() => this.handleDownloadClick(d)}>
                ${disabled
                  ? expired
                    ? t('download.expired_badge')
                    : t('download.exhausted_badge')
                  : t('download.action_download')}
              </a>
            </div>
          `;
        })}
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'afianco-my-downloads': AfiancoMyDownloads;
  }
  interface HTMLElementEventMap {
    'afianco:download-clicked': CustomEvent<{ code: string; product_id: string }>;
  }
}
