import api from './client';

// Frequenze by Aurya (FQ0) — bozze org-scoped. La traccia e' la RICETTA
// (score JSON), mai l'audio: vedi docs/FREQUENZE_PLAN_2026-08.md.
export const frequenciesAPI = {
  list: () => api.get('/frequencies/tracks'),
  get: (trackId) => api.get(`/frequencies/tracks/${trackId}`),
  create: (data) => api.post('/frequencies/tracks', data),
  update: (trackId, updates) => api.patch(`/frequencies/tracks/${trackId}`, updates),
  remove: (trackId) => api.delete(`/frequencies/tracks/${trackId}`),
};
