/**
 * PlanIndicator — persistent admin topbar chip showing the org's current
 * plan + a discreet warning badge when any quota crosses 80%.
 *
 * Onda 7 (v5.8). Opt-in component; the parent layout decides where to
 * mount it (typically alongside the user avatar). Self-loading via
 * billingAPI.getStatus + billingAPI.getUsageSummary on a 5-minute
 * interval — refreshes between polls when the user actively interacts
 * with /plans (focus event triggers a refetch).
 *
 * Click → navigates to /settings#billing for the merchant to drill in.
 *
 * Hidden completely when:
 *   · billing data hasn't loaded yet
 *   · status fetch errors out (no badge spam on transient failures)
 *
 * Three visual states:
 *   normal    — gray pill, plan name only
 *   warning   — amber pill, "⚠ Plan name" (any metric ≥ 80%)
 *   exceeded  — red pill, "🚨 Plan name" (any metric ≥ 100%)
 *
 * Why a separate component (vs adding to BillingSection): persistent
 * top-bar visibility means the merchant always sees their plan + state,
 * even when navigating away from /settings/billing. This is the
 * cheapest "are we approaching limits?" hint we can give.
 */
import React, { useEffect, useState, useCallback, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { Crown, AlertTriangle, AlertCircle } from 'lucide-react';
import { billingAPI } from '../api/billing';


const REFRESH_INTERVAL_MS = 5 * 60 * 1000;   // 5 min


function _stateFromUsage(metrics) {
  if (!Array.isArray(metrics) || metrics.length === 0) return 'normal';
  let exceeded = false;
  let warn = false;
  for (const m of metrics) {
    if (m.status === 'exceeded') exceeded = true;
    else if (m.status === 'warn') warn = true;
  }
  if (exceeded) return 'exceeded';
  if (warn) return 'warning';
  return 'normal';
}


function _classes(state) {
  switch (state) {
    case 'exceeded':
      return {
        wrapper: 'bg-red-50 text-red-800 border-red-200 hover:bg-red-100',
        icon: <AlertCircle className="h-3.5 w-3.5 flex-shrink-0" aria-hidden />,
      };
    case 'warning':
      return {
        wrapper: 'bg-amber-50 text-amber-800 border-amber-200 hover:bg-amber-100',
        icon: <AlertTriangle className="h-3.5 w-3.5 flex-shrink-0" aria-hidden />,
      };
    default:
      return {
        wrapper: 'bg-gray-50 text-gray-700 border-gray-200 hover:bg-gray-100',
        icon: <Crown className="h-3.5 w-3.5 flex-shrink-0" aria-hidden />,
      };
  }
}


export default function PlanIndicator({ to = '/settings#billing', className = '' }) {
  const { t } = useTranslation('settings');
  const [planName, setPlanName] = useState(null);
  const [usageState, setUsageState] = useState('normal');
  const [legacyLock, setLegacyLock] = useState(false);
  const intervalRef = useRef(null);

  const refresh = useCallback(async () => {
    try {
      // Two parallel fetches — usage-summary already exposes plan slug,
      // but plan NAME comes from the catalog list. We can avoid the
      // second roundtrip by caching the plan list in localStorage
      // (storefront_meta-style) — out of scope for v5.8 onda 7.
      const [status, usage] = await Promise.all([
        billingAPI.getStatus().catch(() => null),
        billingAPI.getUsageSummary().catch(() => null),
      ]);

      if (!status) return;

      // Plan name resolution — use the slug as fallback if catalog fetch fails
      const slug = status.commercial_plan_slug || 'free';
      const plans = await billingAPI.listPlans().catch(() => []);
      const plan = plans.find((p) => p.slug === slug);
      setPlanName((plan?.name) || slug);
      setLegacyLock(!!status.legacy_pricing_lock);

      if (usage?.metrics) {
        setUsageState(_stateFromUsage(usage.metrics));
      }
    } catch {
      // Silent — don't spam the topbar with error states
    }
  }, []);

  useEffect(() => {
    refresh();
    intervalRef.current = setInterval(refresh, REFRESH_INTERVAL_MS);
    // Also refresh on tab focus so the chip catches up after the merchant
    // returns from /plans without waiting for the next interval tick.
    const onFocus = () => refresh();
    window.addEventListener('focus', onFocus);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
      window.removeEventListener('focus', onFocus);
    };
  }, [refresh]);

  if (!planName) return null;

  const cls = _classes(usageState);
  const tooltip =
    usageState === 'exceeded'
      ? t('billing.usage.exceeded_tooltip', { defaultValue: 'A quota has been reached — click to see details' })
      : usageState === 'warning'
        ? t('billing.usage.warning_tooltip', { defaultValue: 'Approaching a quota limit — click to see details' })
        : t('billing.plan_label', 'Plan');

  return (
    <Link
      to={to}
      title={tooltip}
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-medium transition-colors ${cls.wrapper} ${className}`.trim()}
    >
      {cls.icon}
      <span className="truncate max-w-[120px]">{planName}</span>
      {legacyLock && (
        <span className="text-[10px]" title={t('billing.legacy_lock_tooltip', 'Stai pagando il prezzo originale.')}>
          🔒
        </span>
      )}
    </Link>
  );
}
