/**
 * AC2 (7/10/2026) — I CORSI dello studente, con l'account Aurya.
 * Stessi nomi di metodo di customerPortalAPI (getCourseDetail, getPlayUrl,
 * sendProgress) cosi' i componenti del player legacy si riusano cambiando
 * solo il client: qui platformApi (token dell'account Aurya).
 */
import platformApi, { PLATFORM_TOKEN_KEY } from './platformClient';

function headers() {
  let tk = null;
  try { tk = localStorage.getItem(PLATFORM_TOKEN_KEY); } catch { /* private mode */ }
  return tk ? { Authorization: `Bearer ${tk}` } : {};
}

export const corsiAPI = {
  getMyCourses: () => platformApi.get('/platform/me/corsi', { headers: headers() }),
  getCourseDetail: (enrollmentId) => platformApi.get(`/platform/me/corsi/${enrollmentId}`, { headers: headers() }),
  getPlayUrl: (enrollmentId, lessonId) =>
    platformApi.post(`/platform/me/corsi/${enrollmentId}/lezioni/${lessonId}/play-url`, {}, { headers: headers() }),
  sendProgress: (enrollmentId, { lesson_id, watched_seconds = 0, completed = false } = {}) =>
    platformApi.post(`/platform/me/corsi/${enrollmentId}/progresso`, { lesson_id, watched_seconds, completed }, { headers: headers() }),
};
