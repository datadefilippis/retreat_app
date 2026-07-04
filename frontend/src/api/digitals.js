/**
 * Release 3 (Digital) — admin API helpers for item_type=digital.
 *
 * Splits cleanly into:
 *   - product CRUD is delegated to the shared productsAPI (same as physical).
 *   - digital-specific: secure file upload + issued_downloads list/resend.
 *
 * Importing productsAPI here rather than re-implementing keeps the single
 * source of truth on `/products/*` and avoids subtle drift when product
 * fields evolve.
 */

import api from './client';
import { productsAPI } from './products';


export const digitalsAPI = {
  // Product CRUD is identical to physical; we proxy so the wizard/dashboard
  // can keep a stable import.
  create: productsAPI.create,
  update: productsAPI.update,
  deactivate: productsAPI.deactivate,
  get: productsAPI.get,
  duplicate: productsAPI.duplicate,
  uploadImage: productsAPI.uploadImage,
  uploadDigitalFile: productsAPI.uploadDigitalFile,
};


export const issuedDownloadsAPI = {
  list: (params = {}) => api.get('/issued-downloads', { params }),
  resend: (downloadId) => api.post(`/issued-downloads/${downloadId}/resend`),
};
