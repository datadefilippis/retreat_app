/**
 * Customer Portal API client (Release 4 Step 6).
 *
 * Uses customerClient so the JWT stored in localStorage as `customer_token`
 * is auto-attached. Endpoints are server-side scoped by
 * (customer_account_id + organization_id) claims on the token.
 *
 * Contract kept thin on purpose — each function is a single axios call.
 * Components own their loading/error state; we only return raw axios
 * responses so callers can read res.data.
 */

import customerApi from './customerClient';

export const customerPortalAPI = {
  // ── Courses (Step 6) ─────────────────────────────────────────────────────

  /**
   * GET /customer/courses
   * Returns `{ courses: [ {enrollment, course, progress_stats} ], total }`.
   * Only active (non-revoked, non-expired) enrollments surface.
   */
  getMyCourses: () => customerApi.get('/customer/courses'),

  /**
   * GET /customer/courses/:enrollment_id
   * Returns the full curriculum of a single enrollment + per-lesson
   * progress. No bunny_video_guid is exposed here — the player
   * endpoint (Step 7) will mint a signed URL per-lesson.
   */
  getCourseDetail: (enrollmentId) =>
    customerApi.get(`/customer/courses/${enrollmentId}`),

  /**
   * POST /customer/courses/:enrollment_id/lessons/:lesson_id/play-url
   * Returns `{ play_url, expires_at, watermark_text }`. The URL is signed
   * for a narrow window (default 2h) — the player must re-fetch before
   * expiry. 403 errors surface enrollment_revoked / enrollment_expired.
   */
  getPlayUrl: (enrollmentId, lessonId) =>
    customerApi.post(
      `/customer/courses/${enrollmentId}/lessons/${lessonId}/play-url`,
    ),

  /**
   * POST /customer/courses/:enrollment_id/progress
   * Server-side max() on watched_seconds + sticky completed_at.
   * Returns the updated progress state + aggregate progress_stats.
   */
  sendProgress: (enrollmentId, { lesson_id, watched_seconds = 0, completed = false } = {}) =>
    customerApi.post(`/customer/courses/${enrollmentId}/progress`, {
      lesson_id,
      watched_seconds,
      completed,
    }),

  // ── Profile (Phase 4 of the customer area refactor) ─────────────────
  // Backend whitelist on PATCH /customer/me accepts:
  //   - name, phone   — free-text identity fields
  //   - locale        — preferred language (it/en/de/fr)
  // Email + organization stay immutable from the customer side
  // (changing email would invalidate the verification gate; org is
  // a multi-tenant boundary).
  updateProfile: (updates) =>
    customerApi.patch('/customer/me', updates),

  // POST /customer/change-password
  // Body: { current_password, new_password }. Backend verifies the
  // current password before applying the change. Server enforces the
  // 8+ chars minimum; the UI also pre-validates.
  changePassword: ({ current_password, new_password }) =>
    customerApi.post('/customer/change-password', {
      current_password,
      new_password,
    }),

  // ── GDPR Art. 17 right-to-erasure (Sprint 1 W1.2 — parity widget) ───
  //
  // POST /customer/me/request-erasure
  // Body: { reason?: string, confirm: boolean }
  // Customer dichiara di voler esercitare il diritto all'oblio.
  // Backend valida confirm=true (defense-in-depth), marca account come
  // erasure_requested_at, manda email admin + email conferma customer.
  // Cascade DELETE asincrona dall'admin entro 30gg (GDPR Art. 12).
  // Idempotent: una seconda chiamata ritorna lo stesso request_id.
  // Response 202 Accepted con { status, message, request_id,
  // estimated_completion_days }.
  requestErasure: ({ reason, confirm }) =>
    customerApi.post('/customer/me/request-erasure', {
      reason: reason || null,
      confirm: confirm === true,
    }),
};
