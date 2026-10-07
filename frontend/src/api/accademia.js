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

export const ETICHETTA_STATO_VIDEO = {
  caricamento: 'Caricamento…',
  codifica: 'In codifica',
  pronto: 'Pronto',
  errore: 'Errore',
};
