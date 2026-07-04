/**
 * <afianco-my-courses> — Track E Step 2.4.8 (customer portal courses tab).
 *
 * Lista videocorsi acquistati dal customer corrente con progress bar.
 * Click su un corso → apre il <afianco-course-player> in vista lezioni.
 *
 * Flow:
 *   1. Mount → fetch `client.customer.courses()` (autenticato JWT)
 *   2. Render grid card per ogni enrollment (cover + nome + lessons count
 *      + progress %)
 *   3. Click sul card → emette `afianco:course-selected` (detail: { enrollment_id })
 *   4. Il parent (customer-portal) gestisce la transizione alla view "lezioni"
 *      con <afianco-course-player>.
 *
 * Pattern: smart-component (fetch + state), con CTA che delega a parent.
 *
 * Custom events:
 *   - afianco:course-selected (detail: { enrollment_id, course_id })
 *
 * Attributes:
 *   - auto-fetch (boolean, default true) — disable per test injection.
 */

import { LitElement, html, css, nothing, type PropertyValues } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { consume } from '@lit/context';
import { afiancoBaseStyles } from '@afianco/design-tokens';
// W4.9 — i18n
import { t } from '../i18n/index.js';
import type { CustomerCourseSummary } from '@afianco/api-client';
import {
  storefrontContext,
  STOREFRONT_INITIAL,
  type StorefrontContext,
} from '../context.js';


@customElement('afianco-my-courses')
export class AfiancoMyCourses extends LitElement {
  @consume({ context: storefrontContext, subscribe: true })
  @state()
  ctx: StorefrontContext = STOREFRONT_INITIAL;

  /** Disable auto-fetch (per test/integration). */
  @property({ type: Boolean, attribute: 'no-auto-fetch' })
  noAutoFetch = false;

  // ── Internal state ────────────────────────────────────────────────────

  @state()
  private courses: CustomerCourseSummary[] = [];

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
    void this.fetchCourses();
  }

  // ── Fetch ───────────────────────────────────────────────────────────

  async fetchCourses(): Promise<void> {
    if (!this.ctx?.client) return;
    this.loading = true;
    this.error = null;
    try {
      const resp = await this.ctx.client.customer.courses();
      this.courses = resp.courses ?? [];
    } catch (e) {
      // 401 = no auth (gestito dal portal parent), altri errori = display
      const msg = (e as Error)?.message ?? t('course.error_load_list');
      this.error = msg;
    } finally {
      this.loading = false;
    }
  }

  // ── Handlers ────────────────────────────────────────────────────────

  private handleSelectCourse(c: CustomerCourseSummary): void {
    this.dispatchEvent(
      new CustomEvent<{ enrollment_id: string; course_id: string }>(
        'afianco:course-selected',
        {
          detail: {
            enrollment_id: c.enrollment.id,
            course_id: c.course.id,
          },
          bubbles: true,
          composed: true,
        },
      ),
    );
  }

  // ── Helpers ─────────────────────────────────────────────────────────

  private formatDuration(seconds: number | null | undefined): string {
    if (!seconds) return '—';
    if (seconds < 60) return `${seconds}s`;
    const totalMin = Math.round(seconds / 60);
    if (totalMin < 60) return `${totalMin} min`;
    const h = Math.floor(totalMin / 60);
    const m = totalMin % 60;
    return m > 0 ? `${h}h ${m}min` : `${h}h`;
  }

  private getProgressPct(c: CustomerCourseSummary): number {
    return Math.max(0, Math.min(100, Math.round(c.progress_stats?.percent ?? 0)));
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
      .empty-icon {
        font-size: 32px;
        margin-bottom: 8px;
      }
      .empty-title {
        font-size: 15px;
        font-weight: 600;
        color: var(--afianco-color-text, #111827);
        margin-bottom: 4px;
      }
      .empty-desc {
        font-size: 13px;
      }

      .grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
        gap: 16px;
      }

      .card {
        background: var(--afianco-color-surface, #ffffff);
        border: 1px solid var(--afianco-color-border, #e5e7eb);
        border-radius: 12px;
        overflow: hidden;
        cursor: pointer;
        transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
        display: flex;
        flex-direction: column;
      }
      .card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.08);
        border-color: var(--afianco-color-primary, #4b72ce);
      }
      .card:focus-visible {
        outline: 2px solid var(--afianco-color-primary, #4b72ce);
        outline-offset: 2px;
      }

      .cover {
        width: 100%;
        aspect-ratio: 16 / 10;
        background: var(--afianco-color-muted, #f3f4f6);
        position: relative;
        overflow: hidden;
      }
      .cover img {
        width: 100%;
        height: 100%;
        object-fit: cover;
        display: block;
      }
      .cover-placeholder {
        width: 100%;
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 32px;
        color: var(--afianco-color-text-muted, #9ca3af);
      }

      .body {
        padding: 14px 16px;
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 8px;
      }
      .title {
        font-size: 14px;
        font-weight: 600;
        color: var(--afianco-color-text, #111827);
        line-height: 1.4;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
      }
      .meta {
        font-size: 11px;
        color: var(--afianco-color-text-secondary, #6b7280);
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
      }

      /* ── Progress bar ─────────────────────────────────────────── */
      .progress-row {
        margin-top: 4px;
      }
      .progress-label {
        font-size: 11px;
        color: var(--afianco-color-text-secondary, #6b7280);
        display: flex;
        justify-content: space-between;
        margin-bottom: 4px;
      }
      .progress-track {
        height: 6px;
        background: var(--afianco-color-muted, #f3f4f6);
        border-radius: 9999px;
        overflow: hidden;
      }
      .progress-fill {
        height: 100%;
        background: var(--afianco-color-primary, #4b72ce);
        border-radius: 9999px;
        transition: width 0.3s ease;
      }
      .progress-fill.complete {
        background: var(--afianco-color-success, #10b981);
      }

      /* Badge complete */
      .badge-complete {
        position: absolute;
        top: 8px;
        right: 8px;
        background: rgba(16, 185, 129, 0.95);
        color: white;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 11px;
        font-weight: 600;
      }
    `,
  ];

  // ── Render ──────────────────────────────────────────────────────────

  render() {
    if (this.loading) {
      return html`<div class="state-msg">${t('course.loading_list')}</div>`;
    }
    if (this.error) {
      return html`<div class="state-msg error" role="alert">${this.error}</div>`;
    }
    if (this.courses.length === 0) {
      return html`
        <div class="empty">
          <div class="empty-icon" aria-hidden="true">📚</div>
          <div class="empty-title">${t('course.empty_purchased')}</div>
          <div class="empty-desc">
            I videocorsi che acquisterai compariranno qui.
          </div>
        </div>
      `;
    }

    return html`
      <div class="grid">
        ${this.courses.map((c) => {
          const pct = this.getProgressPct(c);
          const isComplete = pct >= 100;
          return html`
            <article
              class="card"
              role="button"
              tabindex="0"
              aria-label="${c.course.title} — ${pct}% completato"
              @click=${() => this.handleSelectCourse(c)}
              @keydown=${(e: KeyboardEvent) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  this.handleSelectCourse(c);
                }
              }}>
              <div class="cover">
                ${c.course.cover_image_url
                  ? html`<img src=${c.course.cover_image_url} alt=${c.course.title} loading="lazy">`
                  : html`<div class="cover-placeholder" aria-hidden="true">📚</div>`}
                ${isComplete
                  ? html`<span class="badge-complete">${t('courses.completed_badge')}</span>`
                  : nothing}
              </div>
              <div class="body">
                <h3 class="title">${c.course.title}</h3>
                <div class="meta">
                  ${c.course.lessons_count != null
                    ? html`<span>${c.course.lessons_count} lezioni</span>`
                    : nothing}
                  ${c.course.duration_seconds != null && c.course.duration_seconds > 0
                    ? html`<span>${this.formatDuration(c.course.duration_seconds)}</span>`
                    : nothing}
                </div>
                <div class="progress-row">
                  <div class="progress-label">
                    <span>Progresso</span>
                    <span>${pct}%</span>
                  </div>
                  <div
                    class="progress-track"
                    role="progressbar"
                    aria-valuenow=${pct}
                    aria-valuemin="0"
                    aria-valuemax="100">
                    <div
                      class="progress-fill ${isComplete ? 'complete' : ''}"
                      style="width: ${pct}%"></div>
                  </div>
                </div>
              </div>
            </article>
          `;
        })}
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'afianco-my-courses': AfiancoMyCourses;
  }
  interface HTMLElementEventMap {
    'afianco:course-selected': CustomEvent<{ enrollment_id: string; course_id: string }>;
  }
}
