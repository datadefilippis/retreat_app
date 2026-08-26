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
};
