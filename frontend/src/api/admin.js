import api from './client';

/**
 * adminAPI — wrappers for all /api/admin/* endpoints.
 *
 * ALL calls require a system_admin JWT.  If a non-system-admin token is used,
 * the backend returns 403 and axios will reject the promise.
 *
 * Import via the barrel:  import { adminAPI } from '../../api';
 */
export const adminAPI = {
  // ── Organizations (read) ──────────────────────────────────────────────────

  listOrganizations: (skip = 0, limit = 100) =>
    api.get('/admin/organizations', { params: { skip, limit } }),

  getOrganization: (orgId) =>
    api.get(`/admin/organizations/${orgId}`),

  getOrgModules: (orgId) =>
    api.get(`/admin/organizations/${orgId}/modules`),

  // ── Organizations (write) ─────────────────────────────────────────────────

  setOrgStatus: (orgId, isActive) =>
    api.put(`/admin/organizations/${orgId}/status`, { is_active: isActive }),

  activateModule: (orgId, moduleKey) =>
    api.post(`/admin/organizations/${orgId}/modules/${moduleKey}/activate`),

  deactivateModule: (orgId, moduleKey) =>
    api.post(`/admin/organizations/${orgId}/modules/${moduleKey}/deactivate`),

  // ── Users (read) ──────────────────────────────────────────────────────────

  /**
   * params: { skip, limit, org_id, role, is_active }
   * All optional — omit to list all users.
   */
  listUsers: (params = {}) =>
    api.get('/admin/users', { params }),

  getUser: (userId) =>
    api.get(`/admin/users/${userId}`),

  // ── Users (write) ─────────────────────────────────────────────────────────

  setUserStatus: (userId, isActive) =>
    api.put(`/admin/users/${userId}/status`, { is_active: isActive }),

  resetUserPassword: (userId) =>
    api.post(`/admin/users/${userId}/reset-password`),

  // ── Audit Log (read) ──────────────────────────────────────────────────────

  /**
   * params: { skip, limit, org_id, user_id, action }
   * All optional — omit to see the global audit log.
   */
  listAuditLog: (params = {}) =>
    api.get('/admin/audit-log', { params }),

  // ── Module catalog (v3.1) ─────────────────────────────────────────────────
  // Returns all known modules (registered + future) from GET /modules/available.
  // This is NOT an admin-protected endpoint — no auth required.
  // Used by admin UI to show the full module list in the org detail dialog.
  listAvailableModules: () =>
    api.get('/modules/available'),

  // ── Subscriptions (v4.0-E) ──────────────────────────────────────────────────

  listPricingPlans: (moduleKey) =>
    api.get('/admin/pricing-plans', { params: moduleKey ? { module_key: moduleKey } : {} }),

  listOrgSubscriptions: (orgId) =>
    api.get(`/admin/organizations/${orgId}/subscriptions`),

  setOrgSubscription: (orgId, moduleKey, pricingPlanId) =>
    api.put(`/admin/organizations/${orgId}/subscriptions/${moduleKey}`, {
      pricing_plan_id: pricingPlanId,
    }),

  cancelOrgSubscription: (orgId, moduleKey) =>
    api.delete(`/admin/organizations/${orgId}/subscriptions/${moduleKey}`),

  // ── Commercial billing (v5+) ─────────────────────────────────────────────

  /** List all commercial plans (admin catalog view — includes Stripe IDs). */
  getCommercialPlans: () =>
    api.get('/admin/commercial-plans').then((r) => r.data),

  /** Set canonical commercial plan for an org. Triggers provision_commercial_plan(). */
  setOrgCommercialPlan: (orgId, commercialPlanSlug, notes = '') =>
    api.put(`/admin/organizations/${orgId}/commercial-plan`, {
      commercial_plan_slug: commercialPlanSlug,
      notes,
    }),

  /** Get comprehensive billing summary for an org. */
  getOrgBilling: (orgId) =>
    api.get(`/admin/organizations/${orgId}/billing`).then((r) => r.data),

  /** Reconcile org billing with Stripe. apply=false for dry-run. */
  reconcileOrgBilling: (orgId, apply = false) =>
    api.post(`/admin/organizations/${orgId}/billing/reconcile`, null, {
      params: { apply },
    }).then((r) => r.data),

  // ── Commercial Catalog Control Plane (Phase 3) ─────────────────────────────

  /** Get commercial-state diagnostic for an org (drift flags, recommended actions). */
  getOrgCommercialState: (orgId) =>
    api.get(`/admin/catalog/organizations/${orgId}/commercial-state`).then((r) => r.data),

  /** Reprovision an org to its current catalog plan definition. */
  reprovisionOrg: (orgId, notes = '') =>
    api.post(`/admin/catalog/organizations/${orgId}/reprovision-commercial-plan`, {
      confirm: true,
      notes: notes || undefined,
    }).then((r) => r.data),

  /** Get cross-org commercial overview (batch, read-only). */
  getCommercialOverview: (skip = 0, limit = 100) =>
    api.get('/admin/catalog/organizations/commercial-overview', {
      params: { skip, limit },
    }).then((r) => r.data),

  // ── Catalog Control Plane — catalog-level endpoints (Phase 3E) ─────────────

  /** List all commercial plans with enriched entitlements + subscriber counts. */
  getCatalogPlans: () =>
    api.get('/admin/catalog/plans').then((r) => r.data),

  /** Get single plan with full enrichment + subscribing orgs. */
  getCatalogPlan: (slug) =>
    api.get(`/admin/catalog/plans/${slug}`).then((r) => r.data),

  /** Patch safe metadata fields on a commercial plan. */
  patchCatalogPlan: (slug, fields) =>
    api.patch(`/admin/catalog/plans/${slug}`, fields).then((r) => r.data),

  /** Get entitlement tiers grouped by module_key. */
  getEntitlementTiers: () =>
    api.get('/admin/catalog/entitlement-tiers').then((r) => r.data),

  /** Patch limits on an entitlement tier (requires confirm). */
  patchTierLimits: (slug, limits, notes = '') =>
    api.patch(`/admin/catalog/entitlement-tiers/${slug}/limits`, {
      limits, confirm: true, notes: notes || undefined,
    }).then((r) => r.data),

  /** Patch module_plans mapping on a commercial plan (requires confirm). */
  patchPlanModulePlans: (slug, modulePlans, notes = '') =>
    api.patch(`/admin/catalog/plans/${slug}/module-plans`, {
      module_plans: modulePlans, confirm: true, notes: notes || undefined,
    }).then((r) => r.data),

  /** Patch pricing on a commercial plan (requires confirm).
   *  Onda 11 Step 1: `pricing` may include `stripe_product_id` (prod_xxx)
   *  and `confirm_active_subscriptions: true` to bypass the
   *  active-subscriber guardrail when intentionally relinking. */
  patchPlanPricing: (slug, pricing, notes = '') =>
    api.patch(`/admin/catalog/plans/${slug}/pricing`, {
      ...pricing, confirm: true, notes: notes || undefined,
    }).then((r) => r.data),

  /** Onda 11 Step 2 — full plan↔Stripe linkage snapshot for the
   *  system_admin "Stripe linking" UI. Read-only; combines DB + live
   *  Stripe Product/Price state + active-subscriber count + advisories. */
  getPlanStripeLinkage: (slug) =>
    api.get(`/admin/catalog/plans/${slug}/stripe-linkage`).then((r) => r.data),

  /** Get catalog audit log entries. */
  getCatalogAuditLog: (params = {}) =>
    api.get('/admin/catalog/audit-log', { params }).then((r) => r.data),

  // ── Onda 10 Step C.1+C.2+C.3+C.6 — self-serve create/archive ─────────────

  /** Create a brand-new entitlement tier (PricingPlan). Step C.1. */
  createTier: (payload) =>
    api.post('/admin/catalog/entitlement-tiers', payload).then((r) => r.data),

  /** Create a brand-new commercial plan (non-addon). Step C.2.
   *  Pass `auto_create_stripe: true` to provision Stripe Product+Price. */
  createPlan: (payload) =>
    api.post('/admin/catalog/plans', payload).then((r) => r.data),

  /** Create a brand-new addon (CommercialPlan with is_addon=true). Step C.3.
   *  Pass `auto_create_stripe: true` to provision Stripe Product+Price. */
  createAddon: (payload) =>
    api.post('/admin/catalog/addons', payload).then((r) => r.data),

  /** Soft-delete a commercial plan. Step C.6. */
  archivePlan: (slug, notes = '') =>
    api.patch(`/admin/catalog/plans/${slug}/archive`, {
      confirm: true, notes: notes || undefined,
    }).then((r) => r.data),

  /** Restore an archived commercial plan. Step C.6. */
  unarchivePlan: (slug, notes = '') =>
    api.patch(`/admin/catalog/plans/${slug}/unarchive`, {
      confirm: true, notes: notes || undefined,
    }).then((r) => r.data),

  /** Onda 10 Step E.2 — run the daily billing/catalog drift audit on demand.
   *  Returns { scanned, high_issues, medium_issues, issues_per_org[], email_sent }.
   *  Read-only: does NOT mutate any org/sub. May email the system_admin
   *  if HIGH issues are found and CATALOG_DRIFT_DIGEST_RECIPIENT is set. */
  runBillingAuditNow: () =>
    api.post('/admin/billing/audit-now').then((r) => r.data),

  // ── Controlled Access (v6.0) ────────────────────────────────────────────────

  getRegistrationMode: () =>
    api.get('/admin/settings/registration').then((r) => r.data),

  setRegistrationMode: (mode) =>
    api.put('/admin/settings/registration', { registration_mode: mode }).then((r) => r.data),

  createInvite: (email) =>
    api.post('/admin/invites', { email }).then((r) => r.data),

  listInvites: (skip = 0, limit = 50) =>
    api.get('/admin/invites', { params: { skip, limit } }).then((r) => r.data),

  revokeInvite: (inviteId) =>
    api.delete(`/admin/invites/${inviteId}`),

  // ── Hard Delete (v6.1) ───────────────────────────────────────────────────

  hardDeleteOrganization: (orgId) =>
    api.delete(`/admin/organizations/${orgId}`).then((r) => r.data),

  hardDeleteUser: (userId) =>
    api.delete(`/admin/users/${userId}`).then((r) => r.data),

  // ── v5.8 / Onda 8 — Billing dashboard (system admin) ───────────────────────

  /** Per-org usage + active addons + recent quota notices (system admin view). */
  getOrgUsage: (orgId) =>
    api.get(`/admin/organizations/${orgId}/usage`).then((r) => r.data),

  /**
   * Create a custom CommercialPlan for one org with override limits/price.
   * Body: { template_slug, overrides: {module: {feature: limit}}, price_monthly_override?, trial_days_override?, notes? }
   * Returns { ok, custom_plan_slug, module_plans, next_step }.
   * After this returns, the caller should `setOrgCommercialPlan(orgId, custom_plan_slug)`
   * to actually apply the new plan.
   */
  createCustomPlan: (orgId, body) =>
    api.post(`/admin/organizations/${orgId}/custom-plan`, body).then((r) => r.data),

  /** Extend an org's trial_ends_at by N days. Body: {extra_days, reason}. */
  extendTrial: (orgId, extraDays, reason) =>
    api.post(`/admin/organizations/${orgId}/extend-trial`, {
      extra_days: extraDays,
      reason,
    }).then((r) => r.data),

  /**
   * Mint a 30-min impersonation JWT for the org's first admin.
   * Returns { ok, access_token, token_type, ttl_minutes, target_user }.
   * Caller stores the token under a SEPARATE localStorage key so the
   * system admin's session is preserved.
   */
  impersonate: (orgId, reason = '') =>
    api.post(`/admin/organizations/${orgId}/impersonate`, { reason }).then((r) => r.data),

  /** Cross-org MRR + churn + upsell candidates (system admin dashboard). */
  getMrrOverview: (months = 6) =>
    api.get('/admin/billing-overview/mrr', { params: { months } }).then((r) => r.data),

  // ── v5.8 / Onda 9.A.2 — Admin manual add-on assignment ─────────────────────

  /** List active add-ons of any org (enriched with plan details). */
  listOrgAddons: (orgId) =>
    api.get(`/admin/organizations/${orgId}/addons`).then((r) => r.data),

  /**
   * Manually assign an add-on (custom override, no Stripe billing).
   * Body: { addon_slug, quantity (default 1), notes (optional), reason (required for audit) }
   */
  assignOrgAddon: (orgId, body) =>
    api.post(`/admin/organizations/${orgId}/addons`, body).then((r) => r.data),

  /**
   * Remove an active add-on from an org.
   * Reason is REQUIRED (audit trail). Returns warning if the addon was
   * Stripe-linked — admin must also stop billing in Stripe Dashboard.
   */
  removeOrgAddon: (orgId, addonSlug, reason) =>
    api.delete(`/admin/organizations/${orgId}/addons/${encodeURIComponent(addonSlug)}`, {
      params: { reason },
    }).then((r) => r.data),

  // ── Wave 8C.1 — AI Governance dashboard ───────────────────────────────────

  /**
   * Top-line platform-wide AI spend summary.
   * Returns: { period, totals {events, cost_usd, distinct_orgs},
   *            by_org[], by_model[] }
   */
  getAIUsageSummary: (startDate, endDate) =>
    api.get('/admin/ai-usage/summary', {
      params: { start_date: startDate, end_date: endDate },
    }).then((r) => r.data),

  /**
   * Per-user / per-agent / per-feature breakdown sorted by cost desc.
   * Optional filters: orgId, userId, agentId.
   */
  getAIUsageByUser: (startDate, endDate, { orgId, userId, agentId, limit = 100 } = {}) =>
    api.get('/admin/ai-usage/by-user', {
      params: {
        start_date: startDate,
        end_date: endDate,
        org_id: orgId,
        user_id: userId,
        agent_id: agentId,
        limit,
      },
    }).then((r) => r.data),

  /**
   * Daily timeseries + feature/agent rollups for chart rendering.
   * Returns: { period, totals {events, cost_usd, tokens_total,
   *            cache_read_tokens, cache_hit_ratio_pct},
   *            days[{date, events, cost_usd, ...}],
   *            by_feature[], by_agent[] }
   */
  getAIUsageTimeseries: (startDate, endDate, { orgId } = {}) =>
    api.get('/admin/ai-usage/timeseries', {
      params: { start_date: startDate, end_date: endDate, org_id: orgId },
    }).then((r) => r.data),

  // ── Wave 8C.2 — Budget CRUD + Kill switch ─────────────────────────────────

  /**
   * List AI budgets with live current_spend_usd per row.
   * Returns: { budgets: [{id, scope, scope_id, period, soft_limit_usd,
   *                       hard_limit_usd, current_spend_usd,
   *                       soft_limit_reached, hard_limit_reached, ...}],
   *            count }
   */
  listAIBudgets: ({ organizationId, scope, isActive, limit = 200 } = {}) =>
    api.get('/admin/ai-budgets', {
      params: {
        organization_id: organizationId,
        scope,
        is_active: isActive,
        limit,
      },
    }).then((r) => r.data),

  /** Upsert keyed on (scope, scope_id, period). */
  createAIBudget: (payload) =>
    api.post('/admin/ai-budgets', payload).then((r) => r.data),

  /** Partial update. */
  updateAIBudget: (id, payload) =>
    api.patch(`/admin/ai-budgets/${encodeURIComponent(id)}`, payload).then((r) => r.data),

  /** Hard delete. */
  deleteAIBudget: (id) =>
    api.delete(`/admin/ai-budgets/${encodeURIComponent(id)}`).then((r) => r.data),

  /** Read kill switch state. */
  getAIKillSwitch: () =>
    api.get('/admin/ai-governance/kill-switch').then((r) => r.data),

  /** Update kill switch. `reason` required when ai_enabled=false or throttle > 0. */
  setAIKillSwitch: ({ ai_enabled, ai_throttle_pct = 0, reason = null }) =>
    api.post('/admin/ai-governance/kill-switch', {
      ai_enabled,
      ai_throttle_pct,
      reason,
    }).then((r) => r.data),

  // ── Wave 10.C — Dashboard V2 observability endpoints ─────────────────────

  /**
   * Recent governance mutations (kill switch + budget CRUD) audit log.
   * Returns: { total, offset, limit, rows: [{user_id, action, resource_type,
   *            resource_id, details, created_at}] }
   */
  getAIGovernanceAuditLog: ({ limit = 100, offset = 0 } = {}) =>
    api.get('/admin/ai-governance/audit-log', {
      params: { limit, offset },
    }).then((r) => r.data),

  /**
   * Top-N most expensive chat conversations in the window.
   * Returns: { period, filters, rows: [{conversation_id, organization_id,
   *            organization_name, user_id, user_name, rounds, cost_usd,
   *            tokens_total, first_at, last_at}] }
   */
  getAITopConversations: (startDate, endDate, { orgId, limit = 10 } = {}) =>
    api.get('/admin/ai-usage/top-conversations', {
      params: { start_date: startDate, end_date: endDate,
                org_id: orgId, limit },
    }).then((r) => r.data),

  /**
   * Round-by-round breakdown of one conversation.
   * Returns: { conversation_id, rounds, total_cost_usd, total_tokens,
   *            events: [...] }
   */
  getAIConversationDetail: (conversationId) =>
    api.get(`/admin/ai-usage/conversations/${encodeURIComponent(conversationId)}`)
      .then((r) => r.data),

  /**
   * Recent failed events (error_code != null) in the window.
   * Returns: { period, filters, totals {events, by_code[]}, rows: [...] }
   */
  getAIFailedEvents: (startDate, endDate, { orgId, limit = 100 } = {}) =>
    api.get('/admin/ai-usage/failed-events', {
      params: { start_date: startDate, end_date: endDate,
                org_id: orgId, limit },
    }).then((r) => r.data),
};
