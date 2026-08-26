import api from './client';

// Sound Professional (P2/P3) — protocolli a passi, org-scoped.
//
// IL CLIENT MANDA SOLO IL PROGETTO: nome, descrizione, note, passi,
// stato. Appartenenza, autore, versione, durata e score sono del
// server — e il server li RIFIUTA se arrivano da qui (extra="forbid"
// nei modelli di richiesta: farebbero 422, non verrebbero ignorati).
export const soundProAPI = {
  list: (stato) => api.get('/sound/pro/protocolli', stato ? { params: { stato } } : {}),
  get: (id) => api.get(`/sound/pro/protocolli/${id}`),
  create: (data) => api.post('/sound/pro/protocolli', data),
  update: (id, updates) => api.patch(`/sound/pro/protocolli/${id}`, updates),
  // DELETE archivia, non distrugge (decisione P2)
  archive: (id) => api.delete(`/sound/pro/protocolli/${id}`),

  // S2/S3 — il registro delle sessioni. Il client manda tipo e id del
  // protocollo, MAI uno score: snapshot, durate e appartenenza sono
  // del server (e l'ascolto dichiarato viene cappato lato server).
  sessioni: {
    apri: (data) => api.post('/sound/pro/sessioni', data),
    chiudi: (id, data) => api.post(`/sound/pro/sessioni/${id}/chiusura`, data),
    aggiorna: (id, data) => api.patch(`/sound/pro/sessioni/${id}`, data),
    list: (params) => api.get('/sound/pro/sessioni', { params }),
    get: (id) => api.get(`/sound/pro/sessioni/${id}`),
  },
};
