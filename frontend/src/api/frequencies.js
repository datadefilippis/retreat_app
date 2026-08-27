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
  publish: (trackId, visibility = null) => api.post(
    `/frequencies/tracks/${trackId}/publish`,
    visibility ? { visibility } : {}),
  // IL MASTER (23/8): il mix renderizzato alla pubblicazione dal
  // browser dell'operatore — chi ascolta riceve un file in streaming
  uploadMaster: (trackId, blob) => {
    const fd = new FormData();
    fd.append('file', blob, 'master.mp3');
    return api.post(`/frequencies/tracks/${trackId}/master`, fd,
      { headers: { 'Content-Type': 'multipart/form-data' } });
  },
  masterPass: (slug, provaToken) => api.get(
    `/frequencies/public/${slug}/master-pass`,
    { skipAuthRedirect: true,
      ...(provaToken ? { headers: { 'X-Fqz-Unlock': provaToken } } : {}) }),
  unpublish: (trackId) => api.post(`/frequencies/tracks/${trackId}/unpublish`),
  getPublic: (slug) => api.get(`/frequencies/public/${slug}`),

  // TR3 — le CONDIVISIONI: un link per contatto, revocabile a persona
  createShare: (trackId, contactId) => api.post(
    `/frequencies/tracks/${trackId}/condivisioni`, { contact_id: contactId }),
  listShares: (trackId) => api.get(`/frequencies/tracks/${trackId}/condivisioni`),
  revokeShare: (shareId) => api.post(`/frequencies/condivisioni/${shareId}/revoca`),
  // il lato del cliente: senza account, la porta e' il token
  getCondivisa: (token) => api.get(`/frequencies/condivise/${token}`,
    { skipAuthRedirect: true }),
  condivisaMasterUrl: (token) => `${process.env.REACT_APP_BACKEND_URL || ''}`
    + `/api/frequencies/condivise/${token}/master`,
  registerPlay: (slug) => api.post(`/frequencies/public/${slug}/play`),

  // FQ3 — vetrina /meditazioni: catalogo dietro sblocco server-side.
  // SB1 (20/8): lo sblocco viaggia con la PROVA UNICA del cerchio (il
  // JWT della Lettera, lib/cerchio.js), non piu' con la coppia
  // email:HMAC — una prova sola per guide e meditazioni.
  getCatalog: (provaToken, before) => api.get('/frequencies/catalog', {
    ...(provaToken ? { headers: { 'X-Fqz-Unlock': provaToken } } : {}),
    ...(before ? { params: { before } } : {}),
  }),

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

  // FV1 — spezzoni voce dell'operatore: org-scoped, SOLO registrazione
  // in-app (il blob arriva dal MediaRecorder, mai da un file manager)
  listVoice: () => api.get('/frequencies/voice'),
  recordVoice: ({ blob, mime, title, durationSec, trackId = null }) => {
    const fd = new FormData();
    const ext = (mime || '').includes('mp4') ? 'm4a'
      : (mime || '').includes('ogg') ? 'ogg' : 'webm';
    fd.append('file', new File([blob], `voce.${ext}`, { type: mime }));
    fd.append('title', title);
    fd.append('duration_sec', durationSec || 0);
    if (trackId) fd.append('track_id', trackId);   // TM8: nasce legata
    return api.post('/frequencies/voice', fd,
      { headers: { 'Content-Type': 'multipart/form-data' } });
  },
  // TM8 — l'adozione: lega lo spezzone alla sua sessione
  updateVoice: (assetId, patch) =>
    api.patch(`/frequencies/voice/${assetId}`, patch),
  renameVoice: (assetId, title) =>
    api.patch(`/frequencies/voice/${assetId}`, { title }),
  // FV6 — il taglio e' una proprieta' della REGISTRAZIONE: si decide
  // una volta nel leggio e vale ovunque quello spezzone venga usato
  // VP (24/8) — il modo di pulizia sceglie l'autore, sullo spezzone
  setVoiceClean: (assetId, cleanMode) =>
    api.patch(`/frequencies/voice/${assetId}`, { clean_mode: cleanMode }),
  trimVoice: (assetId, { trimStart, trimEnd }) =>
    api.patch(`/frequencies/voice/${assetId}`,
      { trim_start: trimStart, trim_end: trimEnd }),
  removeVoice: (assetId) => api.delete(`/frequencies/voice/${assetId}`),
};
