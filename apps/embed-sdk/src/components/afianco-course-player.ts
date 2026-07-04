/**
 * <afianco-course-player> — Track E Step 2.4.8 (course playback).
 *
 * Player video per i corsi acquistati. Workflow:
 *   1. Mount con enrollment-id → fetch `client.customer.course(id)` (lessons)
 *   2. User clicca una lezione → POST `coursePlayUrl(id, lessonId)` per
 *      signed Bunny URL (TTL ~15min) → mount iframe
 *   3. Progress heartbeat ogni 30s: POST `updateCourseProgress(id, body)` con
 *      watched_seconds += elapsed + completed se >=95% durata
 *   4. UI: lista lezioni a sinistra (sidebar) + iframe player a destra
 *      Su mobile: stack verticale (sidebar collassata sopra)
 *
 * Sicurezza
 * =========
 * Bunny signed URL expires in ~15min → al pause/inactive, ri-fetch nuovo
 * URL invece di mantener tab aperto (gestito automaticamente dal browser
 * quando l'iframe scade — il customer clicca "Riprendi" → nuovo URL).
 *
 * Progress sticky
 * ===============
 * Backend usa $max() su watched_seconds (no rewind) + sticky completed_at.
 * Quindi anche se il customer chiude/riapre, il progress mostrato non
 * regredisce.
 *
 * Custom events:
 *   - afianco:course-back → click "Indietro" (parent torna alla lista)
 *   - afianco:lesson-completed (detail: { lesson_id })
 *
 * Attributes:
 *   - enrollment-id (required): id dell'enrollment del customer
 */

import { LitElement, html, css, nothing, type PropertyValues } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { consume } from '@lit/context';
import { afiancoBaseStyles } from '@afianco/design-tokens';
// W4.9 — i18n
import { t } from '../i18n/index.js';
import type { CustomerCourseDetail } from '@afianco/api-client';
import {
  storefrontContext,
  STOREFRONT_INITIAL,
  type StorefrontContext,
} from '../context.js';


// Heartbeat: ogni 30s aggiorniamo watched_seconds sul server
const PROGRESS_HEARTBEAT_MS = 30_000;
// Threshold: %% di durata visto per considerare lesson "completed"
const COMPLETE_THRESHOLD_PCT = 0.95;


@customElement('afianco-course-player')
export class AfiancoCoursePlayer extends LitElement {
  @consume({ context: storefrontContext, subscribe: true })
  @state()
  ctx: StorefrontContext = STOREFRONT_INITIAL;

  /** Enrollment id del corso. Required. */
  @property({ type: String, attribute: 'enrollment-id', reflect: true })
  enrollmentId = '';

  // ── Internal state ────────────────────────────────────────────────────

  @state()
  private course: CustomerCourseDetail | null = null;

  @state()
  private loading = false;

  @state()
  private error: string | null = null;

  /** Current lesson id selezionato (per cui e' mostrato il player). */
  @state()
  private currentLessonId: string | null = null;

  /** Signed URL del player (Bunny iframe). Null = nessuna lezione attiva. */
  @state()
  private playUrl: string | null = null;

  /** Loading state del play URL fetch. */
  @state()
  private playUrlLoading = false;

  /** Errore fetch play URL. */
  @state()
  private playUrlError: string | null = null;

  /** Tracking interval per heartbeat. */
  private _heartbeatTimer: ReturnType<typeof setInterval> | null = null;

  /** Timestamp inizio playback (per delta watched_seconds). */
  private _playbackStartTs: number | null = null;

  /** Watched seconds locale prima dell'ultimo heartbeat (cumulativo). */
  private _localWatchedSec = 0;

  // ── Lifecycle ────────────────────────────────────────────────────────

  protected updated(changed: PropertyValues): void {
    // Re-fetch quando enrollmentId cambia
    if (changed.has('enrollmentId') && this.enrollmentId) {
      void this.fetchCourse();
    }
  }

  connectedCallback(): void {
    super.connectedCallback();
    if (this.enrollmentId && this.ctx?.client) {
      void this.fetchCourse();
    }
  }

  disconnectedCallback(): void {
    this.stopHeartbeat();
    super.disconnectedCallback();
  }

  // ── Fetch ───────────────────────────────────────────────────────────

  private async fetchCourse(): Promise<void> {
    if (!this.ctx?.client || !this.enrollmentId) return;
    this.loading = true;
    this.error = null;
    try {
      const resp = await this.ctx.client.customer.course(this.enrollmentId);
      this.course = resp;
    } catch (e) {
      this.error = (e as Error)?.message ?? t('course.error_load');
    } finally {
      this.loading = false;
    }
  }

  // ── Lesson selection + play URL ─────────────────────────────────────

  private async selectLesson(lessonId: string): Promise<void> {
    if (!this.ctx?.client) return;
    // Flush precedente heartbeat
    this.stopHeartbeat();

    this.currentLessonId = lessonId;
    this.playUrl = null;
    this.playUrlError = null;
    this.playUrlLoading = true;

    try {
      const resp = await this.ctx.client.customer.coursePlayUrl(
        this.enrollmentId,
        lessonId,
      );
      this.playUrl = resp.play_url;
      // Start heartbeat
      this.startHeartbeat();
    } catch (e) {
      this.playUrlError = (e as Error)?.message ?? t('course.error_video');
    } finally {
      this.playUrlLoading = false;
    }
  }

  // ── Heartbeat tracking ──────────────────────────────────────────────

  private startHeartbeat(): void {
    this.stopHeartbeat();
    this._playbackStartTs = Date.now();
    this._localWatchedSec = 0;
    this._heartbeatTimer = setInterval(
      () => void this.sendHeartbeat(),
      PROGRESS_HEARTBEAT_MS,
    );
  }

  private stopHeartbeat(): void {
    if (this._heartbeatTimer != null) {
      clearInterval(this._heartbeatTimer);
      this._heartbeatTimer = null;
    }
    // Send final heartbeat per non perdere gli ultimi secondi
    if (this._playbackStartTs && this.currentLessonId) {
      void this.sendHeartbeat();
    }
    this._playbackStartTs = null;
    this._localWatchedSec = 0;
  }

  private async sendHeartbeat(): Promise<void> {
    if (!this.ctx?.client || !this.currentLessonId || !this._playbackStartTs) {
      return;
    }
    const now = Date.now();
    const elapsedSec = Math.floor((now - this._playbackStartTs) / 1000);
    if (elapsedSec <= this._localWatchedSec) return;

    const newWatched = elapsedSec;
    // Find lesson duration to detect completion
    const lesson = this.findLesson(this.currentLessonId);
    const duration = lesson?.duration_seconds ?? 0;
    const completed = duration > 0 && newWatched >= duration * COMPLETE_THRESHOLD_PCT;

    try {
      await this.ctx.client.customer.updateCourseProgress(this.enrollmentId, {
        lesson_id: this.currentLessonId,
        watched_seconds: newWatched,
        completed,
      });
      this._localWatchedSec = newWatched;
      if (completed && lesson && !lesson.completed_at) {
        // Update local snapshot per riflettere visivamente
        lesson.completed_at = new Date().toISOString();
        this.dispatchEvent(
          new CustomEvent<{ lesson_id: string }>('afianco:lesson-completed', {
            detail: { lesson_id: this.currentLessonId },
            bubbles: true,
            composed: true,
          }),
        );
        this.requestUpdate();
      }
    } catch (e) {
      // Soft fail — non blocchiamo la UX, ma stop heartbeat se 401
      const status = (e as { status?: number })?.status;
      if (status === 401 || status === 403) {
        this.stopHeartbeat();
      }
    }
  }

  // ── Helpers ─────────────────────────────────────────────────────────

  private findLesson(lessonId: string) {
    if (!this.course?.course?.modules) return null;
    for (const mod of this.course.course.modules) {
      for (const lesson of (mod.lessons ?? [])) {
        if (lesson.id === lessonId) return lesson;
      }
    }
    return null;
  }

  private handleBack(): void {
    this.stopHeartbeat();
    this.dispatchEvent(
      new CustomEvent('afianco:course-back', { bubbles: true, composed: true }),
    );
  }

  private formatDuration(seconds: number | null | undefined): string {
    if (!seconds) return '—';
    if (seconds < 60) return `${seconds}s`;
    const totalMin = Math.round(seconds / 60);
    if (totalMin < 60) return `${totalMin} min`;
    const h = Math.floor(totalMin / 60);
    const m = totalMin % 60;
    return m > 0 ? `${h}h ${m}min` : `${h}h`;
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

      .back-bar {
        display: flex;
        align-items: center;
        margin-bottom: 16px;
      }
      .back-btn {
        background: transparent;
        border: 1px solid var(--afianco-color-border, #e5e7eb);
        color: var(--afianco-color-text, #111827);
        font-family: inherit;
        font-size: 13px;
        font-weight: 500;
        padding: 6px 12px;
        border-radius: 8px;
        cursor: pointer;
      }
      .back-btn:hover {
        background: var(--afianco-color-muted, #f3f4f6);
      }

      .course-title {
        font-size: 18px;
        font-weight: 700;
        color: var(--afianco-color-text, #111827);
        margin-bottom: 12px;
      }

      /* ── Layout: sidebar lezioni + player ──────────────────────── */
      .layout {
        display: grid;
        grid-template-columns: minmax(0, 320px) minmax(0, 1fr);
        gap: 20px;
      }
      @media (max-width: 720px) {
        .layout {
          grid-template-columns: 1fr;
        }
      }

      /* ── Lessons sidebar ───────────────────────────────────────── */
      .lessons-side {
        background: var(--afianco-color-muted, #f9fafb);
        border-radius: 10px;
        padding: 12px;
        max-height: 600px;
        overflow-y: auto;
      }
      .module {
        margin-bottom: 16px;
      }
      .module:last-child { margin-bottom: 0; }
      .module-title {
        font-size: 11px;
        font-weight: 700;
        color: var(--afianco-color-text-secondary, #6b7280);
        text-transform: uppercase;
        letter-spacing: 0.04em;
        padding: 4px 4px;
        margin-bottom: 4px;
      }
      .lesson-row {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 8px 10px;
        border-radius: 8px;
        cursor: pointer;
        background: var(--afianco-color-bg, #ffffff);
        border: 1px solid transparent;
        margin-bottom: 4px;
        transition: border-color 0.15s ease;
      }
      .lesson-row:hover {
        border-color: var(--afianco-color-border, #e5e7eb);
      }
      .lesson-row[aria-current='true'] {
        border-color: var(--afianco-color-primary, #4b72ce);
        background: var(--afianco-color-primary-soft, #eef2ff);
      }
      .lesson-row:focus-visible {
        outline: 2px solid var(--afianco-color-primary, #4b72ce);
        outline-offset: 2px;
      }
      .lesson-icon {
        flex-shrink: 0;
        width: 20px;
        height: 20px;
        border-radius: 50%;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 11px;
        background: var(--afianco-color-muted, #f3f4f6);
        color: var(--afianco-color-text-secondary, #6b7280);
      }
      .lesson-row.completed .lesson-icon {
        background: var(--afianco-color-success, #10b981);
        color: white;
      }
      .lesson-info {
        flex: 1;
        min-width: 0;
      }
      .lesson-title {
        font-size: 13px;
        font-weight: 500;
        color: var(--afianco-color-text, #111827);
        line-height: 1.3;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
      }
      .lesson-duration {
        font-size: 11px;
        color: var(--afianco-color-text-secondary, #6b7280);
        margin-top: 2px;
      }

      /* ── Player area ───────────────────────────────────────────── */
      .player-area {
        display: flex;
        flex-direction: column;
        gap: 12px;
      }
      .player-frame-wrap {
        aspect-ratio: 16 / 9;
        background: #000;
        border-radius: 10px;
        overflow: hidden;
        position: relative;
      }
      .player-frame-wrap iframe {
        width: 100%;
        height: 100%;
        border: 0;
      }
      .player-placeholder {
        width: 100%;
        height: 100%;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        color: #9ca3af;
        font-size: 14px;
        gap: 6px;
        padding: 20px;
        text-align: center;
      }
      .player-placeholder .icon {
        font-size: 36px;
      }
      .player-loading {
        position: absolute;
        inset: 0;
        background: rgba(0, 0, 0, 0.7);
        color: white;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 14px;
      }
      .player-error {
        background: #fef2f2;
        color: var(--afianco-color-danger, #ef4444);
        padding: 10px 14px;
        border-radius: 8px;
        font-size: 13px;
      }
      .player-info {
        font-size: 12px;
        color: var(--afianco-color-text-secondary, #6b7280);
        line-height: 1.5;
        padding: 8px 12px;
        background: var(--afianco-color-muted, #f3f4f6);
        border-radius: 6px;
      }
    `,
  ];

  // ── Render ──────────────────────────────────────────────────────────

  render() {
    if (this.loading) {
      return html`<div class="state-msg">${t('course.loading')}</div>`;
    }
    if (this.error) {
      return html`<div class="state-msg error" role="alert">${this.error}</div>`;
    }
    if (!this.course) {
      return html`<div class="state-msg">Corso non disponibile.</div>`;
    }

    const modules = this.course.course?.modules ?? [];
    const hasModules = modules.length > 0;

    return html`
      <div class="back-bar">
        <button class="back-btn" type="button" @click=${this.handleBack}>
          ← Torna ai miei corsi
        </button>
      </div>

      <h2 class="course-title">${this.course.course?.title}</h2>

      <div class="layout">
        <!-- Lessons sidebar -->
        <aside class="lessons-side" aria-label="Lezioni del corso">
          ${hasModules
            ? modules.map((mod) => html`
                <div class="module">
                  <div class="module-title">${mod.title}</div>
                  ${(mod.lessons ?? []).map((lesson) => {
                    const isCurrent = lesson.id === this.currentLessonId;
                    const isComplete = !!lesson.completed_at;
                    return html`
                      <div
                        class="lesson-row ${isComplete ? 'completed' : ''}"
                        role="button"
                        tabindex="0"
                        aria-current=${isCurrent ? 'true' : 'false'}
                        @click=${() => void this.selectLesson(lesson.id)}
                        @keydown=${(e: KeyboardEvent) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault();
                            void this.selectLesson(lesson.id);
                          }
                        }}>
                        <span class="lesson-icon">
                          ${isComplete ? '✓' : '▶'}
                        </span>
                        <div class="lesson-info">
                          <div class="lesson-title">${lesson.title}</div>
                          <div class="lesson-duration">
                            ${this.formatDuration(lesson.duration_seconds)}
                          </div>
                        </div>
                      </div>
                    `;
                  })}
                </div>
              `)
            : html`<div class="state-msg">${t('course.empty_lessons')}</div>`}
        </aside>

        <!-- Player -->
        <div class="player-area">
          <div class="player-frame-wrap">
            ${this.playUrl
              ? html`
                  <iframe
                    src=${this.playUrl}
                    title="Player video"
                    allow="accelerometer; encrypted-media; fullscreen; gyroscope; picture-in-picture"
                    allowfullscreen></iframe>
                `
              : html`
                  <div class="player-placeholder">
                    <span class="icon" aria-hidden="true">🎬</span>
                    <span>Seleziona una lezione per iniziare</span>
                  </div>
                `}
            ${this.playUrlLoading
              ? html`<div class="player-loading">${t('course.video_loading')}</div>`
              : nothing}
          </div>
          ${this.playUrlError
            ? html`<div class="player-error" role="alert">${this.playUrlError}</div>`
            : nothing}
          <div class="player-info">
            💡 Il progresso viene salvato automaticamente. Puoi riprendere
            la lezione da dove l'hai lasciata.
          </div>
        </div>
      </div>
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'afianco-course-player': AfiancoCoursePlayer;
  }
  interface HTMLElementEventMap {
    'afianco:course-back': CustomEvent;
    'afianco:lesson-completed': CustomEvent<{ lesson_id: string }>;
  }
}
