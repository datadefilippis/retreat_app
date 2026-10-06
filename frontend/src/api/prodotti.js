/**
 * P1 (6/10/2026) — PRODOTTI (fisici e digitali venduti dal profilo).
 * Backend: routers/prodotti.py sotto require_module("prodotti").
 * L'upload del file e della foto riusano gli endpoint /products/{id}/*.
 */
import api from './client';
import { productsAPI } from './products';

export const prodottiAPI = {
  list: () => api.get('/prodotti'),
  get: (id) => api.get(`/prodotti/${id}`),
  create: (data) => api.post('/prodotti', data),
  update: (id, data) => api.patch(`/prodotti/${id}`, data),
  pubblica: (id) => api.post(`/prodotti/${id}/pubblica`),
  ritira: (id) => api.post(`/prodotti/${id}/ritira`),
  elimina: (id) => api.delete(`/prodotti/${id}`),
  vendite: (id) => api.get(`/prodotti/${id}/vendite`),
  uploadFile: (id, file, config) => productsAPI.uploadDigitalFile(id, file, config),
  uploadImage: (id, file, config) => productsAPI.uploadImage(id, file, config),
};

export function fmtBytes(n) {
  if (!n && n !== 0) return '';
  if (n < 1024 * 1024) return `${Math.max(1, Math.round(n / 1024))} KB`;
  return `${(n / (1024 * 1024)).toFixed(n < 10 * 1024 * 1024 ? 1 : 0)} MB`;
}
