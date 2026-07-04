/**
 * issuedReservationsAPI — thin wrapper for /api/issued-reservations endpoints.
 *
 * Used by the admin ReservationsDashboard. Backend endpoint supports filtering
 * by order_id, flavor, status, date_from, date_to, and free-text search.
 */

import api from './client';
import customerApi from './customerClient';

export const issuedReservationsAPI = {
  // params: { order_id, flavor, status, date_from, date_to, search, limit }
  list: (params = {}) => {
    // Strip empty values so the URL stays clean.
    const clean = Object.fromEntries(
      Object.entries(params).filter(([, v]) => v != null && v !== ''),
    );
    return api.get('/issued-reservations', { params: clean });
  },
  resend: (id) => api.post(`/issued-reservations/${id}/resend`),
  // ICS download via the public token endpoint. Uses customerApi so the
  // request hits the backend origin (in dev the frontend runs on :3000 and
  // a raw `<a href="/api/...">` would 404 on the React dev server).
  downloadIcs: (accessToken) =>
    customerApi.get(
      `/api/public/reservations/${encodeURIComponent(accessToken)}/ics`,
      { responseType: 'blob' },
    ),
};
