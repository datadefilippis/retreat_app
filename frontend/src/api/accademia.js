/**
 * AC1 (7/10/2026) — ACCADEMIA: i corsi online dell'operatore.
 * Backend: routers/accademia.py sotto require_module("accademia").
 * Il video NON passa da qui: il backend prepara le credenziali TUS e il
 * browser carica direttamente su Bunny (features/accademia/upload.js).
 */
import api from './client';
import { compressImage } from '../lib/compressImage';

export const accademiaAPI = {
  list: () => api.get('/accademia'),
  create: (data) => api.post('/accademia', data),
  get: (id) => api.get(`/accademia/${id}`),
  update: (id, data) => api.patch(`/accademia/${id}`, data),
  copertina: async (id, file) => {
    const fd = new FormData();
    fd.append('file', await compressImage(file));
    return api.post(`/accademia/${id}/copertina`, fd, { headers: { 'Content-Type': 'multipart/form-data' } });
  },
  pubblica: (id) => api.post(`/accademia/${id}/pubblica`),
  ritira: (id) => api.post(`/accademia/${id}/ritira`),
  elimina: (id) => api.delete(`/accademia/${id}`),
  // moduli e lezioni
  moduloCrea: (id, data) => api.post(`/accademia/${id}/moduli`, data),
  moduloModifica: (id, mid, data) => api.patch(`/accademia/${id}/moduli/${mid}`, data),
  moduloElimina: (id, mid) => api.delete(`/accademia/${id}/moduli/${mid}`),
  lezioneCrea: (id, data) => api.post(`/accademia/${id}/lezioni`, data),
  lezioneModifica: (id, lid, data) => api.patch(`/accademia/${id}/lezioni/${lid}`, data),
  lezioneElimina: (id, lid) => api.delete(`/accademia/${id}/lezioni/${lid}`),
  ordine: (id, moduli) => api.put(`/accademia/${id}/ordine`, { moduli }),
  // il video: prepara (credenziali TUS), stato, togli
  videoPrepara: (id, lid, { filename, size_bytes }) => api.post(`/accademia/${id}/lezioni/${lid}/video`, { filename, size_bytes }),
  videoStato: (id, lid) => api.get(`/accademia/${id}/lezioni/${lid}/video`),
  videoTogli: (id, lid) => api.delete(`/accademia/${id}/lezioni/${lid}/video`),
  // AU (8/10/2026): l'audio mp3 della lezione, le tracce Aurya Sound, gli allegati
  audioCarica: (id, lid, file, durata, onProgress) => {
    const fd = new FormData();
    fd.append('file', file);
    fd.append('duration_seconds', String(Math.round(durata || 0)));
    return api.post(`/accademia/${id}/lezioni/${lid}/audio`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => { if (onProgress && e.total) onProgress(Math.round((100 * e.loaded) / e.total)); },
    });
  },
  audioTogli: (id, lid) => api.delete(`/accademia/${id}/lezioni/${lid}/audio`),
  audioUrl: (id, lid) => `${api.defaults.baseURL || ''}/accademia/${id}/lezioni/${lid}/audio`,
  tracce: (id) => api.get(`/accademia/${id}/tracce`),
  allegatoCarica: (id, lid, file, label) => {
    const fd = new FormData();
    fd.append('file', file);
    if (label) fd.append('label', label);
    return api.post(`/accademia/${id}/lezioni/${lid}/allegati`, fd, { headers: { 'Content-Type': 'multipart/form-data' } });
  },
  allegatoTogli: (id, lid, aid) => api.delete(`/accademia/${id}/lezioni/${lid}/allegati/${aid}`),
  // il video di presentazione (trailer): stesso ciclo delle lezioni
  trailerPrepara: (id, { filename, size_bytes }) => api.post(`/accademia/${id}/trailer`, { filename, size_bytes }),
  trailerStato: (id) => api.get(`/accademia/${id}/trailer`),
  trailerTogli: (id) => api.delete(`/accademia/${id}/trailer`),
  // gli studenti
  studenti: (id) => api.get(`/accademia/${id}/studenti`),
  revoca: (id, eid, motivo) => api.post(`/accademia/${id}/studenti/${eid}/revoca`, { motivo }),
};

/** 754 → «12 min», 3900 → «1 h 05 min», 0 → «» */
export function fmtDurata(sec) {
  const s = Number(sec || 0);
  if (!s) return '';
  const h = Math.floor(s / 3600);
  const m = Math.round((s % 3600) / 60);
  if (h) return `${h} h ${String(m).padStart(2, '0')} min`;
  if (m) return `${m} min`;
  return `${s} s`;
}

/** la durata di un file audio, misurata dal browser prima di caricarlo (0 se non riesce) */
export function durataAudio(file) {
  return new Promise((resolve) => {
    try {
      const url = URL.createObjectURL(file);
      const a = document.createElement('audio');
      a.preload = 'metadata';
      a.onloadedmetadata = () => { URL.revokeObjectURL(url); resolve(Number.isFinite(a.duration) ? Math.round(a.duration) : 0); };
      a.onerror = () => { URL.revokeObjectURL(url); resolve(0); };
      a.src = url;
    } catch { resolve(0); }
  });
}

export const FORMATI_AUDIO = '.mp3,.m4a,.aac,.wav,.ogg,audio/mpeg,audio/mp4,audio/aac,audio/wav,audio/ogg';
export const MAX_AUDIO_BYTES = 50 * 1024 * 1024;
export const FORMATI_ALLEGATO = '.pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.txt,.md,.png,.jpg,.jpeg,.webp,.zip,.mp3,.m4a';
export const MAX_ALLEGATO_BYTES = 20 * 1024 * 1024;
export const fmtBytes = (n) => (n >= 1024 ** 2 ? `${(n / 1024 ** 2).toFixed(1)} MB` : `${Math.max(1, Math.round(n / 1024))} KB`);

export const ETICHETTA_STATO_VIDEO = {
  caricamento: 'Caricamento…',
  codifica: 'In codifica',
  pronto: 'Pronto',
  errore: 'Errore',
};
