/**
 * Org-level branding API — "olistic settings" feature.
 *
 * Backend mounts these under /api/organizations/current/branding (see
 * backend/routers/organizations.py). The values returned by `get` and
 * mutated by `update` cascade down to every store of the org through
 * the resolver in services/branding_service.py — meaning a logo
 * uploaded here automatically becomes the default logo of stores
 * that don't have their own.
 *
 * Mirrors the shape of `storesAPI` so call sites feel familiar:
 *   - get / update / clear  (the branding doc)
 *   - uploadLogo / deleteLogo  (the logo file)
 *
 * The upload endpoint AUTO-UPDATES `branding.logo_url` on the server
 * so callers don't need a follow-up `update({ logo_url })` step. The
 * response shape mirrors the per-store upload: `{ logo_url: "/uploads/..." }`.
 *
 * Permission notes:
 *   • `get` is open to any authenticated user of the org (so admin
 *     panels can render "Inherited from global" badges without
 *     bumping the role gate).
 *   • All mutations require admin role — the backend enforces it; the
 *     UI also hides the button for non-admins as a hint, but is not
 *     the source of truth.
 */

import api from './client';

export const orgBrandingAPI = {
  /**
   * GET /api/organizations/current/branding
   * Returns `{ logo_url, brand_color, brand_color_text, favicon_url }`
   * with `null` for fields that are not configured at the org level.
   */
  get: () => api.get('/organizations/current/branding'),

  /**
   * PATCH /api/organizations/current/branding
   *
   * Merge semantics: only fields present in `updates` (and non-null)
   * are touched. To explicitly clear a single field send "" (empty
   * string) — the resolver will treat that as "explicit, do not
   * inherit from a higher level". To clear the entire sub-object,
   * use `clear()` instead.
   */
  update: (updates) => api.patch('/organizations/current/branding', updates),

  /**
   * DELETE /api/organizations/current/branding
   * Removes the entire branding sub-object on the org. Per-store
   * branding is preserved. Useful when an admin wants to revert to
   * "no org-level defaults".
   */
  clear: () => api.delete('/organizations/current/branding'),

  /**
   * POST /api/organizations/current/branding/logo
   * Multipart upload (image/jpeg, image/png, image/webp, image/svg+xml,
   * max 2MB). On success, `branding.logo_url` is updated server-side
   * and the resolved URL is returned for immediate UI preview.
   */
  uploadLogo: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/organizations/current/branding/logo', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  /**
   * DELETE /api/organizations/current/branding/logo
   * Removes the logo file from disk AND clears `branding.logo_url`.
   * Other branding fields (colors, favicon) are preserved.
   */
  deleteLogo: () => api.delete('/organizations/current/branding/logo'),
};
