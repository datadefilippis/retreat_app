/**
 * Customer Authentication API — all customer-facing auth + portal endpoints.
 *
 * Uses customerClient (separate from admin client) with customer_token in localStorage.
 * ORG-SCOPED: signup and login require a store slug to identify the organization.
 */

import customerApi from './customerClient';

export const customerAuthAPI = {
  // ── Auth (public, no token needed — require slug for org context) ────
  signup: (data) => customerApi.post('/api/customer-auth/signup', data),
  login: (slug, email, password) => customerApi.post('/api/customer-auth/login', { slug, email, password }),
  forgotPassword: (slug, email, locale) => customerApi.post('/api/customer-auth/forgot-password', { slug, email, locale }),
  resetPassword: (token, newPassword) => customerApi.post('/api/customer-auth/reset-password', { token, new_password: newPassword }),
  verifyEmail: (token) => customerApi.post('/api/customer-auth/verify-email', { token }),
  resendVerification: (slug, email) => customerApi.post('/api/customer-auth/resend-verification', { slug, email }),

  // ── Portal (requires customer_token — org scoped by token) ──────────
  getMe: () => customerApi.get('/api/customer/me'),
  getMyOrders: () => customerApi.get('/api/customer/orders'),
  // The detail endpoint is called with `with_issued=true` so the
  // backend joins issued tickets / bookings / reservations / downloads
  // onto the order. The list endpoint deliberately does NOT pass this
  // flag — keeps that call lean (one Mongo find with projection).
  getOrder: (id) => customerApi.get(`/api/customer/orders/${id}`, { params: { with_issued: true } }),

  // Wave GDPR-Commerce CG-4 — re-accept the merchant's current Privacy
  // + Terms version. Used by <CustomerReconsentModal/> on the customer
  // portal when /me returns consent_needs_refresh=true. Empty body —
  // version is resolved server-side from the customer's signup_slug.
  reConsent: () => customerApi.post('/api/customer/me/re-consent'),
};
