/**
 * useBilling — React Context + Hook for billing state.
 *
 * Provides the current organization's billing status, plan info,
 * and helpers for upgrade/downgrade flows.
 *
 * Usage:
 *   // In App.js or layout:
 *   <BillingProvider>
 *     <App />
 *   </BillingProvider>
 *
 *   // In any component:
 *   const { plan, billingStatus, isTrialing, isPastDue, canUpgrade, refresh } = useBilling();
 */

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { billingAPI } from '../api/billing';
import { useAuth } from '../context/AuthContext';

const BillingContext = createContext(null);

const PLAN_TIERS = { free: 0, starter: 1, core: 2, pro: 3, enterprise: 4 };

// Onda 10 Step A.2 — Focus refresh debounce.
// Plans/status change less frequently than entitlements usage, so we don't
// poll on a fixed cadence — we only refetch when the window regains focus.
// 10s debounce: skip refetch if the last successful one was < 10s ago.
const FOCUS_REFRESH_DEBOUNCE_MS = 10_000;

export function BillingProvider({ children }) {
  const { isAuthenticated } = useAuth();
  const [state, setState] = useState({
    loading: true,
    error: null,
    // Billing status from backend
    commercialPlanSlug: 'free',
    billingStatus: 'none',
    billingInterval: null,
    trialEndsAt: null,
    currentPeriodEnd: null,
    cancelAtPeriodEnd: false,
    planAssignedBy: 'system',
    hasStripeCustomer: false,
    hasHadTrial: false,
    // Plan catalog
    plans: [],
    // Stripe config
    billingEnabled: false,
    stripePublishableKey: '',
    // Onda 13 — exposed so dependent components can re-fetch on refresh
    lastRefreshAt: 0,
  });

  // Track last successful refresh timestamp via a ref so the focus
  // listener can read the latest value without re-binding.
  const lastRefreshRef = useRef(0);

  const fetchStatus = useCallback(async () => {
    if (!isAuthenticated) return;
    try {
      const [status, config, plans] = await Promise.all([
        billingAPI.getStatus(),
        billingAPI.getConfig(),
        billingAPI.listPlans(),
      ]);

      const now = Date.now();
      setState((prev) => ({
        ...prev,
        loading: false,
        error: null,
        commercialPlanSlug: status.commercial_plan_slug || 'free',
        billingStatus: status.billing_status || 'none',
        billingInterval: status.billing_interval,
        trialEndsAt: status.trial_ends_at,
        currentPeriodEnd: status.current_period_end,
        cancelAtPeriodEnd: status.cancel_at_period_end || false,
        planAssignedBy: status.plan_assigned_by || 'system',
        hasStripeCustomer: status.has_stripe_customer || false,
        hasHadTrial: status.has_had_trial || false,
        plans,
        billingEnabled: config.billing_enabled || false,
        stripePublishableKey: config.stripe_publishable_key || '',
        // Onda 13 — expose as state so dependent components
        // (BillingUsageDashboard) can react to refresh events.
        lastRefreshAt: now,
      }));
      lastRefreshRef.current = now;
    } catch (err) {
      setState((prev) => ({
        ...prev,
        loading: false,
        error: err.message || 'Failed to load billing status',
      }));
    }
  }, [isAuthenticated]);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  // Onda 10 Step A.2 — Focus refresh.
  // Plans + billing status change rarely (admin edits), so we don't poll
  // on a fixed cadence — we refetch only when the window regains focus.
  // Result: a system_admin's PATCH on a plan's metadata or pricing
  // propagates to all logged-in tabs the next time the user clicks on
  // that tab (typical delay: seconds), without WebSocket or push.
  useEffect(() => {
    if (!isAuthenticated) return undefined;
    const onFocus = () => {
      const sinceLast = Date.now() - lastRefreshRef.current;
      if (sinceLast < FOCUS_REFRESH_DEBOUNCE_MS) return;
      fetchStatus();
    };
    window.addEventListener('focus', onFocus);
    return () => window.removeEventListener('focus', onFocus);
  }, [isAuthenticated, fetchStatus]);

  const currentPlanDetails = useMemo(
    () => state.plans.find((p) => p.slug === state.commercialPlanSlug) || null,
    [state.plans, state.commercialPlanSlug],
  );

  const hasPlan = useCallback(
    (requiredPlan) =>
      (PLAN_TIERS[state.commercialPlanSlug] || 0) >= (PLAN_TIERS[requiredPlan] || 0),
    [state.commercialPlanSlug],
  );

  const value = useMemo(() => ({
    ...state,
    // Derived state
    plan: state.commercialPlanSlug,
    isFreePlan: state.commercialPlanSlug === 'free',
    isTrialing: state.billingStatus === 'trialing',
    isPastDue: state.billingStatus === 'past_due',
    isCanceled: state.billingStatus === 'canceled',
    isActive: ['active', 'trialing', 'manual'].includes(state.billingStatus),
    canUpgrade: state.commercialPlanSlug !== 'enterprise',
    isPaid: state.commercialPlanSlug !== 'free',
    hasHadTrial: state.hasHadTrial,
    hasPlan,
    currentPlanDetails,
    refresh: fetchStatus,
  }), [state, currentPlanDetails, hasPlan, fetchStatus]);

  return <BillingContext.Provider value={value}>{children}</BillingContext.Provider>;
}

export function useBilling() {
  const ctx = useContext(BillingContext);
  if (!ctx) {
    throw new Error('useBilling must be used within a <BillingProvider>');
  }
  return ctx;
}

export default useBilling;
