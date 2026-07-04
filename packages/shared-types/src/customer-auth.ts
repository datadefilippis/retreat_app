/**
 * Types for /api/customer-auth/* and /api/customer/* (already embed-ready
 * since Phase 1 hardening F3 — DynamicCORS opt-in guard).
 *
 * Mirror di backend `routers/customer_auth.py` + `routers/customer_portal.py`.
 * Solo i campi più usati dal widget Stream A — schema complete in V2.
 */

/**
 * POST /api/customer-auth/signup
 */
export interface CustomerSignupRequest {
  slug: string;
  email: string;
  name: string;
  password: string;
  /** GDPR consent — privacy + terms entrambi REQUIRED dal backend */
  accepted_terms: boolean;
  accepted_privacy: boolean;
  accepted_marketing?: boolean;
  /** Optional: 'it' (default) | 'en' | 'de' | 'fr' */
  locale?: string;
}

/**
 * POST /api/customer-auth/login
 */
export interface CustomerLoginRequest {
  slug: string;
  email: string;
  password: string;
}

/**
 * Response shape per login + signup (auto_login mode).
 */
export interface CustomerTokenResponse {
  access_token: string;
  token_type: string; // "bearer"
  /** Customer account info (subset of CustomerAccount) */
  customer: CustomerProfile;
}

/**
 * GET /api/customer/me + PATCH /api/customer/me
 *
 * Public-safe view del customer account. NO password / hash.
 */
export interface CustomerProfile {
  id: string;
  email: string;
  name: string;
  phone?: string | null;
  locale: string;
  email_verified: boolean;
  /** Marketing opt-in state (CG-4) */
  accepted_marketing?: boolean;
  /** ISO datetime */
  created_at: string;
}

export interface CustomerProfileUpdate {
  name?: string;
  phone?: string | null;
  locale?: string;
}

/**
 * GET /api/customer/orders → array di OrderSummary
 */
export interface CustomerOrderSummary {
  id: string;
  order_number?: string | null;
  order_status: string; // "draft" | "confirmed" | "fulfilled" | ...
  payment_intent: string; // "none" | "required" | "collected" | "waived"
  total: number;
  currency: string;
  /** ISO datetime */
  created_at: string;
}

/**
 * POST /api/customer-auth/forgot-password — body
 */
export interface ForgotPasswordRequest {
  slug: string;
  email: string;
}

/**
 * POST /api/customer-auth/reset-password — body
 */
export interface ResetPasswordRequest {
  token: string;
  new_password: string;
}

/**
 * POST /api/customer-auth/verify-email — body
 */
export interface VerifyEmailRequest {
  token: string;
}
