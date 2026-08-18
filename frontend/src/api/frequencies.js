import api from './client';

// Frequenze by Aurya (FQ0) — bozze org-scoped. La traccia e' la RICETTA
// (score JSON), mai l'audio: vedi docs/FREQUENZE_PLAN_2026-08.md.
export const frequenciesAPI = {
  list: () => api.get('/frequencies/tracks'),
  get: (trackId) => api.get(`/frequencies/tracks/${trackId}`),
  create: (data) => api.post('/frequencies/tracks', data),
  update: (trackId, updates) => api.patch(`/frequencies/tracks/${trackId}`, updates),
  remove: (trackId) => api.delete(`/frequencies/tracks/${trackId}`),

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
