/**
 * Billing API client (v5.7)
 *
 * Endpoints:
 *   GET  /billing/plans            — public plan catalog
 *   GET  /billing/config           — Stripe publishable key
 *   GET  /billing/status           — current org billing status
 *   POST /billing/checkout-session — create Stripe Checkout
 *   POST /billing/portal-session   — create Stripe Customer Portal
 *   POST /billing/verify-checkout  — verify & recover checkout completion (v5.7)
 */

import api from './client';

export const billingAPI = {
  // ── Public ────────────────────────────────────────────────────────────────

  /** List public commercial plans for the pricing page. */
  listPlans: () => api.get('/billing/plans').then((r) => r.data),

  /** Get Stripe config (publishable key, billing_enabled flag). */
  getConfig: () => api.get('/billing/config').then((r) => r.data),

  // ── Authenticated ─────────────────────────────────────────────────────────

  /** Get billing status for the current user's organization. */
  getStatus: () => api.get('/billing/status').then((r) => r.data),

  // ── Checkout & Portal (org admin) ─────────────────────────────────────────

  /** Create a Stripe Checkout Session. Returns { session_id, url }. */
  createCheckoutSession: (planSlug, interval = 'month', { successUrl, cancelUrl } = {}) =>
    api
      .post('/billing/checkout-session', {
        plan_slug: planSlug,
        interval,
        success_url: successUrl,
        cancel_url: cancelUrl,
      })
      .then((r) => r.data),

  /** Create a Stripe Customer Portal session. Returns { url }. */
  createPortalSession: (returnUrl) =>
    api
      .post('/billing/portal-session', {
        return_url: returnUrl,
      })
      .then((r) => r.data),

  // ── Subscription modification (upgrade/downgrade) ───────────────────────────

  /** Modify an active subscription to a different plan. Returns { status, new_plan }. */
  modifySubscription: (planSlug, interval = 'month') =>
    api
      .post('/billing/modify-subscription', { plan_slug: planSlug, interval })
      .then((r) => r.data),

  // ── Subscription cancel / reactivate (v5.8 / Onda 9.A) ─────────────────────

  /**
   * Cancel the active subscription.
   * Default: at_period_end=true (customer keeps access until period end).
   * Pass at_period_end=false for immediate hard cancel.
   * Idempotent — re-cancelling returns existing state.
   */
  cancelSubscription: ({ atPeriodEnd = true, reason = '' } = {}) =>
    api.post('/billing/cancel-subscription', {
      at_period_end: atPeriodEnd,
      reason,
    }).then((r) => r.data),

  /**
   * Reverse a cancel-at-period-end before it takes effect.
   * "I changed my mind" UX. Idempotent — no-op if not currently cancel-pending.
   */
  reactivateSubscription: () =>
    api.post('/billing/reactivate-subscription').then((r) => r.data),

  // ── Checkout verification / recovery (v5.7) ────────────────────────────────

  /** Verify a checkout session and provision the plan if webhook was missed. */
  verifyCheckout: (sessionId) =>
    api.post('/billing/verify-checkout', { session_id: sessionId }).then((r) => r.data),

  // ── Add-ons (v5.8 / Onda 3) ────────────────────────────────────────────────

  /**
   * List add-ons available for the current org's plan, with `is_compatible`
   * + `active_quantity` decorations. Powers the PlansPage add-on grid.
   */
  listAddons: () => api.get('/billing/addons').then((r) => r.data),

  /** List currently active add-ons of the org. Powers the BillingSection list. */
  listMyAddons: () => api.get('/billing/my-addons').then((r) => r.data),

  /**
   * Add or update_quantity an add-on on the org's active subscription.
   * Returns { status, addon_slug, quantity, subscription_id, note }.
   * Backend resolves the action (add vs update) based on whether the
   * addon is already active.
   */
  addAddon: (addonSlug, quantity = 1) =>
    api
      .post('/billing/add-addon', { addon_slug: addonSlug, quantity })
      .then((r) => r.data),

  /** Remove an active add-on. Returns { status, addon_slug, ... }. */
  removeAddon: (addonSlug) =>
    api.delete(`/billing/addon/${encodeURIComponent(addonSlug)}`).then((r) => r.data),

  /** Onda 24 Phase F — pull-based reconciliation of addon_subscriptions
   *  with live Stripe sub items. Self-healing safety net called by the
   *  frontend a few seconds after add-addon / remove-addon completes,
   *  in case the webhook hasn't landed yet (esp. localhost). */
  verifyAddonState: () =>
    api.post('/billing/verify-addon-state').then((r) => r.data),

  // ── Usage summary (v5.8 / Onda 7) ──────────────────────────────────────────

  /**
   * Single endpoint that returns "used / limit" for every monitored metric +
   * the active add-ons. Powers the BillingSection "USO CORRENTE" dashboard.
   * Read-only / no side effects. Always 200.
   */
  getUsageSummary: () =>
    api.get('/billing/usage-summary').then((r) => r.data),
};
