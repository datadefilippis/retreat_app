/**
 * useEntitlements — Generic React Context + hook for ALL plan entitlements.
 *
 * v5.8 / Onda 9.Y.0.2 (Step D), live-refresh extension Onda 10 Step A.1.
 *
 * Sibling of `useAiAccess` (which only covers AI features). This hook covers
 * EVERY (module, feature_key) the backend exposes via /api/billing/usage-summary,
 * including:
 *   · Counter quotas (data_rows, products, stores_max, orders_monthly, chat,
 *     digest, team_members)
 *   · Boolean feature flags (export, email_alerts, email_digest, alert_config,
 *     alert_analysis, health_explanation, checkout_stripe)
 *
 * Refresh strategy (Onda 10 Step A.1):
 *   1. On mount of <EntitlementsProvider>
 *   2. Polling every REFRESH_INTERVAL_MS (default 60s) while authenticated
 *   3. On window 'focus' event (debounced — skips if a poll happened <5s ago)
 *   4. On demand via the exposed `refresh()` callback
 *
 * Why polling + focus:
 *   When system_admin changes a tier limit (e.g. data_rows Solo 200→500), the
 *   backend reflects the new limit on every gate check immediately (no cache).
 *   Pre-Onda 10 the FE fetched usage-summary ONLY at provider mount — the user
 *   would still see "Limit reached 200/200" until they reloaded the page.
 *   The polling + focus pattern propagates admin mutations to all logged-in
 *   sessions within ~60s without requiring a websocket / push channel.
 *
 * Public API:
 *   - canUse(moduleKey, featureKey)        → bool
 *   - quotaExhausted(moduleKey, featureKey) → bool (counter only; flags always false)
 *   - getMetric(featureKey)                → {used, limit, remaining, status, addon_slug, ...}
 *   - getFeatureFlag(featureKey)           → {included, requires_plan, ...}
 *   - loading                              → bool
 *   - refresh()                            → re-fetch
 *   - lastRefreshAt                        → epoch ms of last successful fetch
 *
 * Why a separate hook from `useAiAccess`:
 *   `useAiAccess` calls `GET /ai/access-status` (a hand-rolled AI-specific
 *   endpoint that pre-dates the generic usage-summary). Keeping them
 *   separate is intentional: AI-specific UI (ChatWidget, HealthScoreGauge,
 *   etc.) keeps using the more focused hook; everything else uses this one.
 *   Both eventually unify if/when /ai/access-status is deprecated.
 */
import React, { createContext, useContext, useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { billingAPI } from '../api';
import { useAuth } from '../context/AuthContext';

const EntitlementsContext = createContext(null);

// Onda 10 Step A.1 — Polling cadence for live entitlement updates.
// 60s is a reasonable balance between freshness and server load: a system
// admin's plan/limit edit propagates to all logged-in sessions within ~60s
// max. Configurable via window.__ENTITLEMENTS_REFRESH_MS for QA/testing.
const REFRESH_INTERVAL_MS =
  (typeof window !== 'undefined' && Number(window.__ENTITLEMENTS_REFRESH_MS)) ||
  60_000;

// Debounce window for focus-triggered refresh: if the last successful fetch
// completed less than this many ms ago, skip the focus refresh. Prevents a
// burst of fetches when the user rapidly switches tabs.
const FOCUS_REFRESH_DEBOUNCE_MS = 5_000;


export function EntitlementsProvider({ children }) {
  const { isAuthenticated } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastRefreshAt, setLastRefreshAt] = useState(0);
  // Use a ref so the latest timestamp is visible to event listeners and
  // intervals registered with stale closures.
  const lastRefreshRef = useRef(0);

  const refresh = useCallback(async () => {
    if (!isAuthenticated) {
      setData(null);
      setLoading(false);
      return;
    }
    try {
      const summary = await billingAPI.getUsageSummary();
      setData(summary);
      const now = Date.now();
      lastRefreshRef.current = now;
      setLastRefreshAt(now);
    } catch {
      // Defensive: a 401/500 here should not crash dependent components.
      // We expose `loading=false` and empty state; consumers fall back
      // to "always allow + paywall handles 429 server-side".
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated]);

  // Initial fetch + identity changes
  useEffect(() => {
    refresh();
  }, [refresh]);

  // Onda 10 Step A.1 — Polling + focus refresh.
  // Both effects bail when !isAuthenticated to avoid unauthenticated
  // background traffic on /login or /signup pages.
  useEffect(() => {
    if (!isAuthenticated) return undefined;

    // Polling
    const intervalId = setInterval(() => {
      refresh();
    }, REFRESH_INTERVAL_MS);

    // Focus-triggered refresh (debounced)
    const onFocus = () => {
      const sinceLast = Date.now() - lastRefreshRef.current;
      if (sinceLast < FOCUS_REFRESH_DEBOUNCE_MS) return;
      refresh();
    };
    window.addEventListener('focus', onFocus);

    return () => {
      clearInterval(intervalId);
      window.removeEventListener('focus', onFocus);
    };
  }, [isAuthenticated, refresh]);

  // Index metrics by feature_key for O(1) lookup. Backend returns an array
  // because the dashboard wants ordered iteration; consumers want lookup.
  const metricsByKey = useMemo(() => {
    const idx = {};
    for (const m of data?.metrics || []) {
      idx[m.key] = m;
    }
    return idx;
  }, [data]);

  const featuresByKey = useMemo(() => {
    const idx = {};
    for (const f of data?.features || []) {
      idx[f.key] = f;
    }
    return idx;
  }, [data]);

  /**
   * canUse(module, feature) → can this org use the feature right now?
   *
   * - Counter: false when usage >= limit (exhausted)
   * - Flag:    false when limit == 0 (not included in plan)
   * - Unlimited: always true
   *
   * Loading state: returns TRUE (optimistic) — the server-side gate is the
   * real boundary. Showing a disabled button while we don't know the state
   * would be a worse UX than letting the user click and getting a paywall.
   */
  const canUse = useCallback((moduleKey, featureKey) => {
    if (loading) return true;
    const m = metricsByKey[featureKey];
    if (m && m.module === moduleKey) {
      if (m.limit === -1) return true;
      if (m.limit === 0) return false;
      return (m.used || 0) < m.limit;
    }
    const f = featuresByKey[featureKey];
    if (f && f.module === moduleKey) {
      return Boolean(f.included);
    }
    // Unknown feature key — fall back to optimistic. Server will reject.
    return true;
  }, [loading, metricsByKey, featuresByKey]);

  const quotaExhausted = useCallback((moduleKey, featureKey) => {
    if (loading) return false;
    const m = metricsByKey[featureKey];
    if (!m || m.module !== moduleKey) return false;
    if (m.limit === -1) return false;
    if (m.limit === 0) return true; // not included acts like exhausted for UX
    return (m.used || 0) >= m.limit;
  }, [loading, metricsByKey]);

  const getMetric = useCallback((featureKey) => {
    const m = metricsByKey[featureKey];
    if (!m) return null;
    const remaining = (m.limit === -1) ? Infinity : Math.max(0, m.limit - (m.used || 0));
    return { ...m, remaining };
  }, [metricsByKey]);

  const getFeatureFlag = useCallback((featureKey) => {
    return featuresByKey[featureKey] || null;
  }, [featuresByKey]);

  const value = useMemo(() => ({
    plan: data?.commercial_plan_slug || 'free',
    metrics: data?.metrics || [],
    features: data?.features || [],
    activeAddons: data?.active_addons || [],
    loading,
    refresh,
    canUse,
    quotaExhausted,
    getMetric,
    getFeatureFlag,
    // Onda 10 Step A.1 — exposed for components that want to display
    // "last updated" UX hints (e.g. dashboard timestamp).
    lastRefreshAt,
  }), [data, loading, refresh, canUse, quotaExhausted, getMetric, getFeatureFlag, lastRefreshAt]);

  return (
    <EntitlementsContext.Provider value={value}>
      {children}
    </EntitlementsContext.Provider>
  );
}


export function useEntitlements() {
  const ctx = useContext(EntitlementsContext);
  if (!ctx) {
    throw new Error('useEntitlements must be used inside <EntitlementsProvider>');
  }
  return ctx;
}
