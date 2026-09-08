/**
 * Le chiamate delle strutture (SR, fase 0). Una sola cosa da sapere:
 * FastAPI legge le liste come parametri RIPETUTI (regione=Puglia&regione=Lazio),
 * mentre axios di default scrive regione[]=…: la query si costruisce a mano.
 */
import api from '../../../api/client';

let schemaCache = null;

export async function caricaSchema() {
  if (schemaCache) return schemaCache;
  const res = await api.get('/admin/strutture/schema');
  schemaCache = res.data;
  return schemaCache;
}

export function etichetta(schema, lista, valore) {
  const voce = (schema?.liste?.[lista] || []).find((v) => v.valore === valore);
  return voce ? voce.etichetta : (valore || '—');
}

export function queryDaFiltri(filtri) {
  const p = new URLSearchParams();
  Object.entries(filtri || {}).forEach(([k, v]) => {
    if (v === undefined || v === null || v === '' || v === false) return;
    if (Array.isArray(v)) v.forEach((x) => x !== '' && p.append(k, x));
    else p.append(k, String(v));
  });
  return p.toString();
}

export async function lista(filtri) {
  const q = queryDaFiltri(filtri);
  const res = await api.get(`/admin/strutture${q ? `?${q}` : ''}`);
  return res.data;
}

export const crea = (body) => api.post('/admin/strutture', body).then((r) => r.data);
export const scheda = (id) => api.get(`/admin/strutture/${id}`).then((r) => r.data);
export const salva = (id, body) => api.patch(`/admin/strutture/${id}`, body).then((r) => r.data);
export const elimina = (id) => api.delete(`/admin/strutture/${id}`).then((r) => r.data);
export const aggiungiStoria = (id, nota) => api.post(`/admin/strutture/${id}/storia`, { nota }).then((r) => r.data);
export const caricaFoto = (id, file) => {
  const fd = new FormData();
  fd.append('file', file);
  return api.post(`/admin/strutture/${id}/foto`, fd, { headers: { 'Content-Type': 'multipart/form-data' } }).then((r) => r.data);
};
export const richieste = (stato) => api.get(`/admin/strutture/richieste/tutte${stato ? `?stato=${stato}` : ''}`).then((r) => r.data);
export const salvaRichiesta = (id, body) => api.patch(`/admin/strutture/richieste/${id}`, body).then((r) => r.data);
