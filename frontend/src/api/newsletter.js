import api from './client';

/**
 * Newsletter forms — admin API (F3, modulo Newsletter).
 *
 * Risorsa org-scoped (store opzionale). Mappa 1:1 con
 * backend/routers/newsletter_forms.py.
 */
export const newsletterAPI = {
  list: (storeId) =>
    api.get('/newsletter-forms', { params: storeId ? { store_id: storeId } : {} }),
  get: (formId) => api.get(`/newsletter-forms/${formId}`),
  create: (data) => api.post('/newsletter-forms', data),
  update: (formId, data) => api.patch(`/newsletter-forms/${formId}`, data),
  delete: (formId) => api.delete(`/newsletter-forms/${formId}`),
  updateOrigins: (formId, allowedOrigins) =>
    api.patch(`/newsletter-forms/${formId}/allowed-origins`, {
      allowed_origins: allowedOrigins,
    }),
  submissions: (formId, source) =>
    api.get(`/newsletter-forms/${formId}/submissions`, {
      params: source ? { source } : {},
    }),
};

/** Base URL del backend (per snippet embed). '' = stessa origine. */
export const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';

/**
 * Genera lo snippet embed copia-incolla per un form.
 * Il bundle è servito da {backend}/embed/v1/afianco-embed.es.js.
 */
export function buildNewsletterSnippet(formId) {
  const base = BACKEND_URL || window.location.origin;
  return [
    `<script type="module" src="${base}/embed/v1/afianco-embed.es.js"></script>`,
    `<afianco-newsletter-form form-id="${formId}" base-url="${base}" source="sito-web"></afianco-newsletter-form>`,
  ].join('\n');
}
