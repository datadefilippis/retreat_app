import api from './client';

/**
 * E5 — Tickets admin client.
 *
 * Pairs with backend/routers/tickets.py. All endpoints are
 * authenticated and org-scoped via the bearer token on api client.
 */
export const ticketsAPI = {
  // Atomic check-in. Returns {ok, reason, ticket}.
  //   ok=true:  "ok" (first-time) | "already_checked_in"
  //   ok=false: "not_found" | "voided" | "wrong_occurrence"
  checkIn: ({ code, occurrence_id } = {}) =>
    api.post('/tickets/check-in', { code, occurrence_id: occurrence_id || null }),

  // Attendance list for an occurrence. Pass includeVoided=true to
  // include cancelled tickets (audit view).
  listForOccurrence: (occurrenceId, { includeVoided = false } = {}) =>
    api.get(`/tickets/occurrence/${occurrenceId}`,
            { params: { include_voided: includeVoided ? 1 : 0 } }),

  // Quick counters for the check-in dashboard header.
  //   { issued, valid, checked_in, voided, remaining }
  stats: (occurrenceId) =>
    api.get(`/tickets/occurrence/${occurrenceId}/stats`),

  // G4 — re-send a single ticket email to the holder.
  resendEmail: (code) =>
    api.post(`/tickets/${code}/resend-email`, {}),

  // G4 — void a single ticket (does NOT cancel the order).
  voidTicket: (code, reason = null) =>
    api.post(`/tickets/${code}/void`, { reason }),

  // G4 — broadcast a templated email to every attendee of the occurrence.
  //   body: { template, message?, subject_override?,
  //           include_voided?, include_checked_in? }
  broadcast: (occurrenceId, body) =>
    api.post(`/tickets/occurrence/${occurrenceId}/email-attendees`, body),

  // F1 Onda 8 — resend the per-holder personal ticket email to every
  // guest of this occurrence whose holder_email != customer_email.
  // Returns { ok, sent, skipped, errors, target }.
  resendIndividualForOccurrence: (occurrenceId) =>
    api.post(`/tickets/occurrence/${occurrenceId}/resend-individual`, {}),
};
