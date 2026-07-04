/**
 * Admin API client for video courses (Release 4 Step 2).
 *
 * Mirrors the shape of `productsAPI` in api/products.js so call sites
 * feel familiar. All endpoints are org-scoped server-side via the admin
 * JWT; callers do not need to pass organization_id.
 *
 * Usage:
 *   import { coursesAPI } from '@/api/courses';
 *   const { data: courses } = await coursesAPI.list();
 *   const { data: course } = await coursesAPI.get(courseId);
 *   await coursesAPI.addModule(courseId, { title: 'Modulo 1' });
 *   await coursesAPI.addLesson(courseId, moduleId, {
 *     title: 'Intro', duration_seconds: 180,
 *     bunny_video_guid: 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx',
 *   });
 *
 * All methods return the axios response (`.data` is the parsed body).
 */

import api from './client';

export const coursesAPI = {
  // ── Course CRUD ──────────────────────────────────────────────────────────

  list: ({ activeOnly = true, limit = 500 } = {}) =>
    api.get('/courses', { params: { active_only: activeOnly, limit } }),

  get: (courseId) =>
    api.get(`/courses/${courseId}`),

  create: (data) =>
    api.post('/courses', data),

  update: (courseId, updates) =>
    api.patch(`/courses/${courseId}`, updates),

  /**
   * Soft-delete (is_active=false). Returns 204 on success.
   * Returns 409 if the course is still referenced by an active Product.
   */
  deactivate: (courseId) =>
    api.delete(`/courses/${courseId}`),

  // ── Modules CRUD ─────────────────────────────────────────────────────────

  addModule: (courseId, { title, description } = {}) =>
    api.post(`/courses/${courseId}/modules`, { title, description }),

  /**
   * Update a module. Pass only the fields to change (title, description, order).
   * Changing `order` re-sorts the modules list server-side.
   */
  updateModule: (courseId, moduleId, updates) =>
    api.patch(`/courses/${courseId}/modules/${moduleId}`, updates),

  deleteModule: (courseId, moduleId) =>
    api.delete(`/courses/${courseId}/modules/${moduleId}`),

  // ── Lessons CRUD ─────────────────────────────────────────────────────────

  addLesson: (courseId, moduleId, payload) =>
    api.post(`/courses/${courseId}/modules/${moduleId}/lessons`, payload),

  updateLesson: (courseId, moduleId, lessonId, updates) =>
    api.patch(
      `/courses/${courseId}/modules/${moduleId}/lessons/${lessonId}`,
      updates,
    ),

  deleteLesson: (courseId, moduleId, lessonId) =>
    api.delete(`/courses/${courseId}/modules/${moduleId}/lessons/${lessonId}`),

  // ── Linked Product (Release 4 follow-up: Dashboard layout) ──────────────
  // Each Course has exactly one "primary" Product(item_type='course') that
  // carries the commerce-facing fields (price, store_ids, is_published,
  // transaction_mode). The backend auto-creates it on course create +
  // fetch-or-create on first read, so the Sales card is always populated.

  getLinkedProduct: (courseId) =>
    api.get(`/courses/${courseId}/product`),

  /** Accepts a subset of { name, slug, description, unit_price, currency,
   *  transaction_mode, is_published, store_ids, image_url }.
   *  Slug changes are synchronized with the Course slug server-side. */
  updateLinkedProduct: (courseId, updates) =>
    api.patch(`/courses/${courseId}/product`, updates),

  // ── Enrollments (Release 4 Step 8) ───────────────────────────────────────

  /**
   * GET /courses/:course_id/enrollments
   * Returns `{ enrollments: [...], total }` with customer email + progress
   * stats. Set `include_revoked=true` to see revoked rows in the table.
   */
  listEnrollments: (courseId, { includeRevoked = false, limit = 500 } = {}) =>
    api.get(`/courses/${courseId}/enrollments`, {
      params: { include_revoked: includeRevoked, limit },
    }),

  /**
   * POST /courses/enrollments/:enrollment_id/revoke
   * Revokes a single enrollment. The reason is stored on the row and
   * logged — it is NEVER shown to the customer.
   */
  revokeEnrollment: (enrollmentId, { reason } = {}) =>
    api.post(`/courses/enrollments/${enrollmentId}/revoke`, {
      reason: reason || 'admin_revoked',
    }),
};

/**
 * Per-org Bunny Stream integration config (Release 4 Step 2).
 * Exposed as a separate module since it lives on the Organization
 * document rather than on the Course.
 */
export const bunnyIntegrationAPI = {
  /**
   * Create or update the Bunny credentials for the current org.
   * Merge semantics — only send changed fields.
   * Accepts: { library_id?, api_key?, cdn_hostname?, watermark_enabled? }
   *
   * Side effect (Step 3 of bunny consolidation): the backend now
   * auto-verifies the credentials against Bunny BEFORE persisting and
   * stamps the result on the org doc. The PATCH succeeds regardless
   * of probe outcome (bad creds save with status=unauthorized so the
   * admin can fix them later). Read the new fields from the response:
   *   integrations.bunny.last_verification_status
   *   integrations.bunny.last_verification_error
   *   integrations.bunny.library_name
   *   integrations.bunny.video_count
   *   integrations.bunny.last_verified_at
   */
  update: (payload) =>
    api.patch('/organizations/current/integrations/bunny', payload),

  /**
   * Clear the integration. Existing enrollments lose playback until
   * the integration is re-enabled (no data loss).
   */
  clear: () =>
    api.delete('/organizations/current/integrations/bunny'),

  /**
   * Probe Bunny with the supplied (or saved) credentials WITHOUT
   * persisting. Used by the admin form's "Testa connessione" button
   * to validate before saving. Returns:
   *
   *   { status: BunnyStatus,
   *     library_name: string | null,
   *     video_count: number | null,
   *     error_message: string | null }
   *
   * BunnyStatus values: 'ok' | 'unauthorized' | 'library_not_found' |
   * 'network_error' | 'unknown' | 'not_configured'.
   *
   * The payload is optional — if omitted, tests the saved credentials.
   * Useful for the "ri-controlla" affordance after a flaky probe.
   * Rate-limited server-side at 10/minute (Bunny shouldn't be hammered).
   */
  testConnection: (payload = null) =>
    api.post('/organizations/current/integrations/bunny/test', payload),

  /**
   * Read the last cached verification status without re-probing. Open
   * to any authenticated org user (not just admin) so non-admin
   * surfaces (e.g. course list with "Bunny status" widget) can render
   * the badge without bumping the role gate.
   *
   * Returns the same shape as testConnection but augmented with
   * `last_verified_at` (when the cached status was recorded).
   * Returns status='not_configured' when the integration is missing
   * (distinct from "configured but never tested").
   */
  getStatus: () =>
    api.get('/organizations/current/integrations/bunny/status'),

  /**
   * Multi-library namespace (Step 6 of multi-library feature).
   *
   * Manages `org.integrations.bunny_libraries[]` — N independent Bunny
   * libraries per org. Backward compat: the legacy single-library
   * methods above (update / clear / testConnection / getStatus)
   * continue to work on the `org.integrations.bunny` field. Use
   * `bunnyIntegrationAPI.migrateLegacy()` to promote legacy → array.
   *
   * Endpoint shape mirrors the backend (see backend/routers/
   * organizations.py multi-library block):
   *
   *   list()             → GET    /libraries          → { libraries: [...] }
   *   create(payload)    → POST   /libraries          → library doc
   *   get(id)            → GET    /libraries/{id}     → library doc
   *   update(id, p)      → PATCH  /libraries/{id}     → library doc
   *   remove(id)         → DELETE /libraries/{id}     → { deleted_id }
   *                                                     409 when lessons reference it
   *   test(id, p?)       → POST   /libraries/{id}/test       → status DTO (no save)
   *   setDefault(id)     → POST   /libraries/{id}/default    → { default_id }
   *
   * Each library doc carries the same status fields the legacy
   * single-library doc has: last_verification_status, library_name,
   * video_count, etc. The frontend reads these for the per-library
   * badge in BunnyLibrariesCard.
   */
  libraries: {
    list: () =>
      api.get('/organizations/current/integrations/bunny/libraries'),
    create: (payload) =>
      api.post('/organizations/current/integrations/bunny/libraries', payload),
    get: (id) =>
      api.get(`/organizations/current/integrations/bunny/libraries/${id}`),
    update: (id, payload) =>
      api.patch(`/organizations/current/integrations/bunny/libraries/${id}`, payload),
    remove: (id) =>
      api.delete(`/organizations/current/integrations/bunny/libraries/${id}`),
    test: (id, payload = null) =>
      api.post(`/organizations/current/integrations/bunny/libraries/${id}/test`, payload),
    setDefault: (id) =>
      api.post(`/organizations/current/integrations/bunny/libraries/${id}/default`),
  },

  /**
   * One-shot migration: promote `org.integrations.bunny` (legacy
   * single library) into `bunny_libraries[0]` with alias='Default'
   * + is_default=true, then clear the legacy field.
   *
   * Idempotent on the server. Returns:
   *   { status: 'migrated' | 'noop', message?, library? }
   *
   * The frontend should refresh the org doc + libraries list after
   * a successful migration to reflect the new structural shape.
   */
  migrateLegacy: () =>
    api.post('/organizations/current/integrations/bunny/migrate-legacy'),
};
