import api from './client';

export const aiAPI = {
  chat: (message, sessionId, periodContext) =>
    api.post('/ai/chat', {
      message,
      session_id: sessionId,
      ...(periodContext && { period_context: periodContext }),
    }),
  getHistory: (sessionId) =>
    api.get('/ai/chat/history', { params: { session_id: sessionId } }),
  getAccessStatus: () => api.get('/ai/access-status'),

  // Session management
  listSessions: () => api.get('/ai/chat/sessions'),
  createSession: () => api.post('/ai/chat/sessions'),
  deleteSession: (sessionId) => api.delete(`/ai/chat/sessions/${sessionId}`),
  renameSession: (sessionId, title) =>
    api.patch(`/ai/chat/sessions/${sessionId}/title`, { title }),
};
