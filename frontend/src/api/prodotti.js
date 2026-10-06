/**
 * P1 (6/10/2026) — PRODOTTI (fisici e digitali venduti dal profilo).
 * Backend: routers/prodotti.py sotto require_module("prodotti").
 * L'upload del file e della foto riusano gli endpoint /products/{id}/*.
 */
import api from './client';
import { productsAPI } from './products';
import { compressImage } from '../lib/compressImage';

export const prodottiAPI = {
  list: () => api.get('/prodotti'),
  get: (id) => api.get(`/prodotti/${id}`),
  create: (data) => api.post('/prodotti', data),
  update: (id, data) => api.patch(`/prodotti/${id}`, data),
  pubblica: (id) => api.post(`/prodotti/${id}/pubblica`),
  ritira: (id) => api.post(`/prodotti/${id}/ritira`),
  elimina: (id) => api.delete(`/prodotti/${id}`),
  vendite: (id) => api.get(`/prodotti/${id}/vendite`),
  // P2 — come arrivano i fisici (modi + spedizione a costo fisso, org-global)
  consegna: () => api.get('/prodotti/consegna'),
  salvaConsegna: (data) => api.put('/prodotti/consegna', data),
  uploadFile: (id, file, config) => productsAPI.uploadDigitalFile(id, file, config),
  uploadImage: (id, file, config) => productsAPI.uploadImage(id, file, config),
  // GL — la galleria: piu' foto per prodotto (la prima e' la principale)
  aggiungiFoto: async (id, file, config = {}) => {
    const fd = new FormData();
    fd.append('file', await compressImage(file));
    return api.post(`/prodotti/${id}/foto`, fd, { ...config, headers: { 'Content-Type': 'multipart/form-data', ...(config.headers || {}) } });
  },
  togliFoto: (id, url) => api.delete(`/prodotti/${id}/foto`, { data: { url } }),
  fotoPrincipale: (id, url) => api.post(`/prodotti/${id}/foto/principale`, { url }),
};

/** 12 → «12 €», 12.5 → «12,50 €» */
export function fmtEuro(n) {
  const v = Number(n || 0);
  try {
    return new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR',
      minimumFractionDigits: Number.isInteger(v) ? 0 : 2, maximumFractionDigits: 2 }).format(v);
  } catch { return `${v} €`; }
}

export function fmtBytes(n) {
  if (!n && n !== 0) return '';
  if (n < 1024 * 1024) return `${Math.max(1, Math.round(n / 1024))} KB`;
  return `${(n / (1024 * 1024)).toFixed(n < 10 * 1024 * 1024 ? 1 : 0)} MB`;
}
