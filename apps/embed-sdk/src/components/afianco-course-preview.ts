/**
 * <afianco-course-preview> — Track E Step 2.4.7 (course landing preview).
 *
 * Preview informativo per course products (no buy flow — solo info).
 * Mostra:
 *   - Counter lessons + durata totale (course_lessons_count + course_duration_seconds)
 *   - Access policy badge ("Accesso a vita" | "Accesso N giorni")
 *   - CTA hint "Effettua il login per accedere ai contenuti dopo l'acquisto"
 *
 * NON mostra:
 *   - Lista lezioni (richiede enrollment lato customer)
 *   - Video player (richiede signed URL, post-acquisto)
 *
 * Mirror minimale di CourseLandingPage.js dello storefront. La lista
 * lezioni completa + player viene mostrata nel customer portal tab
 * "I miei corsi" (Step E2.4.8) dopo acquisto + enrollment.
 *
 * Pattern: pure presenter, no events emessi (no scelte da fare).
 */

import { LitElement, html, css, nothing } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { afiancoBaseStyles } from '@afianco/design-tokens';
// W4.9 — i18n
import { t } from '../i18n/index.js';


@customElement('afianco-course-preview')
export class AfiancoCoursePreview extends LitElement {
  /** Numero lezioni totali nel corso. */
  @property({ type: Number, attribute: 'lessons-count' })
  lessonsCount: number | null = null;

  /** Durata totale in secondi (somma dei video). */
  @property({ type: Number, attribute: 'duration-seconds' })
  durationSeconds: number | null = null;

  /** "lifetime" | "expiring". */
  @property({ type: String, attribute: 'access-policy' })
  accessPolicy: string | null = null;

  /** Numero giorni se accessPolicy === "expiring". */
  @property({ type: Number, attribute: 'access-expiry-days' })
  accessExpiryDays: number | null = null;

  // ── Helpers ─────────────────────────────────────────────────────────

  private formatDuration(seconds: number): string {
    if (seconds < 60) return `${seconds}s`;
    const totalMin = Math.round(seconds / 60);
    if (totalMin < 60) return `${totalMin} min`;
    const hours = Math.floor(totalMin / 60);
    const mins = totalMin % 60;
    return mins > 0 ? `${hours}h ${mins}min` : `${hours}h`;
  }

  private get accessLabel(): string {
    if (this.accessPolicy === 'expiring' && this.accessExpiryDays) {
      return t('course.access_expiry_days', { count: this.accessExpiryDays });
    }
    if (this.accessPolicy === 'lifetime') {
      return t('course.access_lifetime');
    }
    return t('course.access_unlimited');
  }

  // ── Styles ──────────────────────────────────────────────────────────

  static styles = [
    afiancoBaseStyles,
    css`
      :host {
        display: block;
      }
      .container {
        background: var(--afianco-color-muted, #f9fafb);
        border: 1px solid var(--afianco-color-border, #e5e7eb);
        border-radius: 10px;
        padding: 16px;
      }
      .title {
        font-size: 13px;
        font-weight: 700;
        color: var(--afianco-color-text, #111827);
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-bottom: 12px;
      }
      .stats {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
        gap: 12px;
        margin-bottom: 14px;
      }
      .stat {
        background: var(--afianco-color-surface, #ffffff);
        border-radius: 8px;
        padding: 10px 12px;
        text-align: center;
      }
      .stat-value {
        font-size: 18px;
        font-weight: 700;
        color: var(--afianco-color-text, #111827);
        line-height: 1.2;
      }
      .stat-label {
        font-size: 11px;
        color: var(--afianco-color-text-secondary, #6b7280);
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-top: 2px;
      }
      .access-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 6px 12px;
        background: var(--afianco-color-primary-soft, #eef2ff);
        color: var(--afianco-color-primary, #4b72ce);
        border-radius: 9999px;
        font-size: 12px;
        font-weight: 600;
      }
      .login-hint {
        margin-top: 12px;
        font-size: 12px;
        color: var(--afianco-color-text-secondary, #6b7280);
        line-height: 1.5;
        background: #fff7ed;
        border-left: 3px solid #f59e0b;
        padding: 10px 12px;
        border-radius: 4px;
      }
    `,
  ];

  // ── Render ──────────────────────────────────────────────────────────

  render() {
    const hasStats = this.lessonsCount != null || this.durationSeconds != null;
    if (!hasStats && !this.accessPolicy) return nothing;

    return html`
      <div class="container">
        <div class="title">${t('course.preview_title')}</div>

        ${hasStats
          ? html`
              <div class="stats">
                ${this.lessonsCount != null
                  ? html`
                      <div class="stat">
                        <div class="stat-value">${this.lessonsCount}</div>
                        <div class="stat-label">${t('course.lessons_label_short')}</div>
                      </div>
                    `
                  : nothing}
                ${this.durationSeconds != null && this.durationSeconds > 0
                  ? html`
                      <div class="stat">
                        <div class="stat-value">${this.formatDuration(this.durationSeconds)}</div>
                        <div class="stat-label">${t('course.duration_label_short')}</div>
                      </div>
                    `
                  : nothing}
              </div>
            `
          : nothing}

        ${this.accessPolicy
          ? html`
              <span class="access-badge">
                <span aria-hidden="true">🔓</span>
                ${this.accessLabel}
              </span>
            `
          : nothing}

        <div class="login-hint">
          📚 ${t('course.profile_access_hint')}
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'afianco-course-preview': AfiancoCoursePreview;
  }
}
