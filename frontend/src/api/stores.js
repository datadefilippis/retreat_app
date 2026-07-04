/**
 * Stores API — multi-store CRUD operations.
 *
 * Each organization can have multiple stores (storefronts).
 * This client manages the stores collection separately from
 * the legacy store-settings embedded in organization.
 */

import api from './client';

export const storesAPI = {
  list: () => api.get('/stores'),
  get: (storeId) => api.get(`/stores/${storeId}`),
  create: (data) => api.post('/stores', data),
  update: (storeId, data) => api.patch(`/stores/${storeId}`, data),
  publish: (storeId) => api.post(`/stores/${storeId}/publish`),
  unpublish: (storeId) => api.post(`/stores/${storeId}/unpublish`),
  uploadLogo: (storeId, file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post(`/stores/${storeId}/logo`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
};

// ─── Wave GDPR-Commerce Phase CG-3 ─────────────────────────────────────
// Admin-side endpoints for per-store legal docs (privacy + terms).
// All require an org admin JWT (the underlying client.js handles it).

export const storeLegalAPI = {
  /** Render a fresh template stateless — does NOT save. */
  generateDraft: (storeId, payload) =>
    api.post(`/stores/${storeId}/legal/generate-draft`, payload).then((r) => r.data),

  /** Admin snapshot: all 8 content slots + status + version. */
  get: (storeId) =>
    api.get(`/stores/${storeId}/legal`).then((r) => r.data),

  /** Save ONE locale slot of ONE doc — never bumps version. */
  patchContent: (storeId, payload) =>
    api.patch(`/stores/${storeId}/legal/content`, payload).then((r) => r.data),

  /** Switch the locale that customers see. Bumps version on a published store. */
  patchDisplayLocale: (storeId, locale) =>
    api.patch(`/stores/${storeId}/legal/display-locale`, { locale }).then((r) => r.data),

  /** Publish the current display-locale bundle. Idempotent on no-op.
   * Response carries no_change + no_change_reason + edited_non_display_locales
   * + active_locale so the UI can render a precise toast. */
  publish: (storeId, releaseNotes = null) =>
    api.post(`/stores/${storeId}/legal/publish`, {
      release_notes: releaseNotes,
    }).then((r) => r.data),

  // Wave CG-3-Polish — persistent wizard variables.
  /** Save the merchant's identity / configuration vars on the store
   * doc. NEVER bumps the legal version (these are not content, they
   * are identity inputs used at template render time). */
  patchTemplateVars: (storeId, vars) =>
    api.patch(`/stores/${storeId}/legal/template-vars`, { vars }).then((r) => r.data),
};
