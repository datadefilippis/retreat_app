import api from './client';

/**
 * storeSettingsAPI — store identity + branding.
 *
 * History:
 * - Fase 2 Track F — Step 9 cleanup: five wizard-only endpoints were
 *   removed from the backend (/ai/store/generate-identity,
 *   /ai/store/generate-products, /ai/store/suggest-fulfillment,
 *   /ai/store/generate-setup, /ai/store/extract-from-url) in the
 *   commit that shipped the dynamic dashboard SetupWizardWidget. The
 *   new wizard flow lives at /api/setup/wizard (read-only).
 * - Wave 8E.2: /ai/store/enrich-product endpoint and its client method
 *   `enrichProduct` were also removed — the method had no callers
 *   anywhere in the frontend (its only consumer ProductsPage had
 *   silently stopped using it). The whole routers/ai_store.py backend
 *   file is gone too.
 *
 * The /api/store/setup-progress endpoint is untouched on the server
 * for backward compatibility but its only frontend caller (the legacy
 * SetupPage) is gone, so the client method that wrapped it was
 * removed as well.
 */
export const storeSettingsAPI = {
  // Read + write store_settings document for the current org.
  get: () => api.get('/store-settings'),
  update: (data) => api.patch('/store-settings', data),

  // Logo upload (multipart). Returns the persisted URL on success.
  uploadLogo: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/store-settings/logo', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
};
