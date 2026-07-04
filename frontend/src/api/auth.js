import api from './client';

export const authAPI = {
  login: (email, password) => api.post('/auth/login', { email, password }),
  signup: (data) => api.post('/auth/signup', data),
  getMe: () => api.get('/auth/me'),
  changePassword: (currentPassword, newPassword) =>
    api.put('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    }),
  forgotPassword: (email) =>
    api.post('/auth/forgot-password', { email }),
  resetPassword: (token, newPassword) =>
    api.post('/auth/reset-password', {
      token,
      new_password: newPassword,
    }),
  updateLocale: (locale) =>
    api.patch('/auth/locale', { locale }),
  resendVerification: (email) =>
    api.post('/auth/resend-verification', { email }),
  verifyEmail: (token) =>
    api.post('/auth/verify-email', { token }),
  // ── Controlled Access (v6.0) ──────────────────────────────────────────
  getRegistrationMode: () =>
    api.get('/auth/registration-mode').then((r) => r.data),
  requestInvite: (name, email, business, locale) =>
    api.post('/auth/request-invite', { name, email, business, locale }),
  validateInvite: (token) =>
    api.get('/auth/validate-invite', { params: { token } }).then((r) => r.data),
  // ── Account Deactivation (v6.0, GDPR art. 17) ────────────────────────
  deactivateAccount: (password) =>
    api.post('/auth/deactivate-account', { password }),
  reactivateAccount: (email, password) =>
    api.post('/auth/reactivate-account', { email, password }),
  getAccountDataSummary: () =>
    api.get('/auth/account-data-summary').then((r) => r.data),
  exportData: () =>
    api.get('/auth/export-data', { responseType: 'blob' }),
  // ── Wave GDPR-Admin Phase E — re-consent on legal docs version bump ──
  // Records an immutable consent_audit entry (source="re_acceptance") AND
  // updates the user doc's accepted_terms_version + accepted_terms_locale.
  // Returns the fresh UserResponse so AuthContext can refresh without
  // a separate /auth/me roundtrip.
  reConsent: (locale) =>
    api.post('/auth/re-consent', { locale }).then((r) => r.data),
};

// ─── Wave GDPR-Commerce Phase CG-7 — DPA (Data Processing Agreement) ──
//
// The DPA is the Art. 28 GDPR agreement between afianco (Processor)
// and the merchant org (Controller). Admin-only — requires the user
// to be an org admin (the underlying client.js handles auth).

export const dpaAPI = {
  /**
   * Fetch the rendered DPA markdown for the current org in the given
   * locale. Variables interpolated server-side; never trust the client.
   */
  get: (locale = 'it') =>
    api.get('/legal/dpa', { params: { lang: locale } }).then((r) => r.data),

  /**
   * Record the DPA acknowledgement. Idempotent — a second POST returns
   * the original timestamp with status="already_acknowledged".
   */
  acknowledge: (locale = 'it') =>
    api.post('/legal/dpa/acknowledge', { locale }).then((r) => r.data),

  /** Check whether this org has already acknowledged the DPA. */
  status: () =>
    api.get('/legal/dpa/status').then((r) => r.data),
};
