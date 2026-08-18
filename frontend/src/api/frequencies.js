import api from './client';

// Frequenze by Aurya (FQ0) — bozze org-scoped. La traccia e' la RICETTA
// (score JSON), mai l'audio: vedi docs/FREQUENZE_PLAN_2026-08.md.
export const frequenciesAPI = {
  list: () => api.get('/frequencies/tracks'),
  get: (trackId) => api.get(`/frequencies/tracks/${trackId}`),
  create: (data) => api.post('/frequencies/tracks', data),
  update: (trackId, updates) => api.patch(`/frequencies/tracks/${trackId}`, updates),
  remove: (trackId) => api.delete(`/frequencies/tracks/${trackId}`),

  // FQ1 — pubblicazione e ascolto pubblico
  publish: (trackId) => api.post(`/frequencies/tracks/${trackId}/publish`),
  unpublish: (trackId) => api.post(`/frequencies/tracks/${trackId}/unpublish`),
  getPublic: (slug) => api.get(`/frequencies/public/${slug}`),
  registerPlay: (slug) => api.post(`/frequencies/public/${slug}/play`),

  // FQ3 — vetrina /meditazioni: catalogo dietro sblocco server-side
  catalogUnlock: (email) => api.post('/frequencies/catalog/unlock', { email }),
  getCatalog: (unlock) => api.get('/frequencies/catalog',
    unlock ? { headers: { 'X-Fqz-Unlock': `${unlock.email}:${unlock.token}` } } : {}),

  // FQ2 — libreria suoni curata: lettura per tutti, scrittura solo
  // system admin (multipart)
  listSounds: () => api.get('/frequencies/sounds'),
  uploadSound: ({ file, title, category, durationSec, licenseNote }) => {
    const fd = new FormData();
    fd.append('file', file);
    fd.append('title', title);
    fd.append('category', category);
    fd.append('duration_sec', durationSec || 0);
    fd.append('license_note', licenseNote || '');
    return api.post('/frequencies/sounds', fd,
      { headers: { 'Content-Type': 'multipart/form-data' } });
  },
  removeSound: (assetId) => api.delete(`/frequencies/sounds/${assetId}`),
};
