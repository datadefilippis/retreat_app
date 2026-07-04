/**
 * Payments API client.
 *
 * Today the only surface is the readiness check used by the product
 * editor to decide whether `transaction_mode="direct"` is safe to
 * select. The corresponding backend router lives at
 * `backend/routers/payments.py` (Fase 3 of the direct-payment
 * consolidation).
 *
 * The shape returned by the backend is:
 *   {
 *     stripe_configured: boolean,
 *     reason_code: string,
 *     message_it: string,
 *     provider: string | null,
 *     action_url: string | null,
 *   }
 *
 * Adding a new payment endpoint: append it here and reuse the same
 * `api` client so auth headers and base URL stay consistent.
 */

import api from './client';

export const paymentsAPI = {
  /**
   * Get payment-readiness state for the current admin's organization.
   * Auth: required (admin JWT). The backend derives org_id from the
   * token, so the caller doesn't pass it.
   */
  getReadiness: () => api.get('/payments/readiness').then((r) => r.data),
};
