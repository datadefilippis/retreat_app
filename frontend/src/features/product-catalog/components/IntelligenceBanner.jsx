/**
 * IntelligenceBanner — top-of-page health-check display for Product
 * Performance.
 *
 * 3-tier presentation (FB.3) so the merchant sees the most-impactful
 * issue first and isn't flattened by a list of equal-looking alerts:
 *
 *   HERO         — business_impact ≥ 60. Big card, always-expanded,
 *                  rendered front-and-centre. Typically: "products
 *                  without cost configured" (you don't know if you're
 *                  profitable) or "negative-margin products" (you're
 *                  losing money on every sale).
 *
 *   SECONDARY    — business_impact 25-59. Compact card, expandable.
 *                  Cashflow mismatches, trend deteriorations.
 *
 *   HOUSEKEEPING — business_impact < 25. Collapsed list below.
 *                  SKU hygiene, refresh prompts, unattributed
 *                  purchases — useful but no decision urgency.
 *
 * Wrapper colour is driven by the top tier present (Hero=red,
 * Secondary=amber, Housekeeping=blue, all-good=green).
 *
 * Dismissal
 * ─────────
 * Each card has "Hide for 30 days" which persists via the hook's
 * localStorage. Dismissed checks are NOT rendered and do NOT count
 * toward the tier classification.
 */

import React, { useState, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import {
  AlertCircle, AlertTriangle, Info, CheckCircle2,
  ChevronDown, ChevronUp, X, ExternalLink, Settings,
} from 'lucide-react';
import { Button } from '../../../components/ui/button';
import { useCurrency } from '../../../context/AuthContext';
import { formatCurrency } from '../../../lib/utils';


// Severity → visual mapping. Pure cosmetic; tier classification (which
// drives layout placement) is separate and lives in ``_tierFor`` below.
const SEVERITY_META = {
  critical: {
    Icon: AlertCircle,
    chipClass: 'bg-red-100 text-red-800 border-red-200',
    dotClass:  'bg-red-500',
  },
  warning: {
    Icon: AlertTriangle,
    chipClass: 'bg-amber-100 text-amber-800 border-amber-200',
    dotClass:  'bg-amber-500',
  },
  info: {
    Icon: Info,
    chipClass: 'bg-blue-100 text-blue-800 border-blue-200',
    dotClass:  'bg-blue-400',
  },
};


// Tier → wrapper colour palette. Hero (red border, prominent) vs
// Secondary (amber, normal) vs Housekeeping (blue/grey, muted).
const TIER_META = {
  hero: {
    bg:    'bg-red-50/60',
    border:'border-red-200',
    headerColor:    'text-red-900',
    bodyColor:      'text-red-800',
    Icon: AlertCircle,
    iconColor: 'text-red-600',
  },
  secondary: {
    bg:    'bg-amber-50/40',
    border:'border-amber-200',
    headerColor:    'text-amber-900',
    bodyColor:      'text-amber-800',
    Icon: AlertTriangle,
    iconColor: 'text-amber-600',
  },
  housekeeping: {
    bg:    'bg-slate-50/60',
    border:'border-slate-200',
    headerColor:    'text-slate-800',
    bodyColor:      'text-slate-700',
    Icon: Info,
    iconColor: 'text-slate-500',
  },
};


const ACTION_META = {
  navigate:             { Icon: ExternalLink, variant: 'outline' },
  external:             { Icon: ExternalLink, variant: 'outline' },
  bulk_configure_cost:  { Icon: Settings,     variant: 'default' },
  refresh_metrics:      { Icon: Settings,     variant: 'default' },
};


// Tier classification thresholds. Hero is reserved for issues that
// shake decision-making (60+), Secondary for important but not
// existential (25-59), Housekeeping for cosmetic/operational (<25).
function _tierFor(check) {
  const impact = check?.business_impact ?? 0;
  if (impact >= 60) return 'hero';
  if (impact >= 25) return 'secondary';
  return 'housekeeping';
}


export default function IntelligenceBanner({
  data,
  loading,
  isDismissed,
  onDismissCheck,
  onRefreshMetrics,
  currency: currencyProp,
}) {
  const { t } = useTranslation('product_catalog');
  const orgCurrency = useCurrency();
  const currency = currencyProp || orgCurrency || 'EUR';
  const navigate = useNavigate();

  // Filter out dismissed checks then group by tier.
  const buckets = useMemo(() => {
    const visible = (data?.checks || []).filter(c => !isDismissed(c.id));
    const hero = [];
    const secondary = [];
    const housekeeping = [];
    for (const c of visible) {
      const tier = _tierFor(c);
      if (tier === 'hero') hero.push(c);
      else if (tier === 'secondary') secondary.push(c);
      else housekeeping.push(c);
    }
    // Within each tier, sort by business_impact desc.
    const byImpact = (a, b) => (b.business_impact ?? 0) - (a.business_impact ?? 0);
    hero.sort(byImpact);
    secondary.sort(byImpact);
    housekeeping.sort(byImpact);
    return { hero, secondary, housekeeping, total: visible.length };
  }, [data, isDismissed]);

  if (loading) {
    return (
      <div className="rounded-lg border border-gray-200 bg-gray-50 p-3 animate-pulse">
        <div className="h-4 w-48 bg-gray-200 rounded" />
      </div>
    );
  }

  if (!data) return null;

  const summary = data.summary || {};

  // ── All good state ─────────────────────────────────────────────────────
  if (buckets.total === 0) {
    return (
      <div className="rounded-lg border border-emerald-200 bg-emerald-50/40 p-3 text-sm text-emerald-800 flex items-center gap-2">
        <CheckCircle2 className="h-4 w-4 shrink-0" />
        <div className="flex-1">
          <p className="font-semibold">
            {t('intelligenceBanner.title_all_good', {
              passed: summary.total_checks_run ?? 0,
              total: summary.total_checks_run ?? 0,
            })}
          </p>
          <p className="text-xs opacity-90 mt-0.5">
            {t('intelligenceBanner.title_all_good_sub')}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* HERO — always expanded, biggest visual weight. */}
      {buckets.hero.map((check) => (
        <HeroCard
          key={check.id}
          check={check}
          currency={currency}
          onDismiss={() => onDismissCheck(check.id)}
          onAction={(action) => handleAction(action, { navigate, onRefreshMetrics })}
          t={t}
        />
      ))}

      {/* SECONDARY + HOUSEKEEPING in a flex/grid row beneath the Hero */}
      {(buckets.secondary.length > 0 || buckets.housekeeping.length > 0) && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {buckets.secondary.length > 0 && (
            <CollapsibleSection
              tier="secondary"
              titleKey="intelligenceBanner.section_secondary"
              checks={buckets.secondary}
              currency={currency}
              onDismiss={onDismissCheck}
              onAction={(action) => handleAction(action, { navigate, onRefreshMetrics })}
              defaultExpanded={buckets.hero.length === 0}
              t={t}
            />
          )}
          {buckets.housekeeping.length > 0 && (
            <CollapsibleSection
              tier="housekeeping"
              titleKey="intelligenceBanner.section_housekeeping"
              checks={buckets.housekeeping}
              currency={currency}
              onDismiss={onDismissCheck}
              onAction={(action) => handleAction(action, { navigate, onRefreshMetrics })}
              defaultExpanded={false}
              t={t}
            />
          )}
        </div>
      )}
    </div>
  );
}


// ── Hero card ────────────────────────────────────────────────────────────────


function HeroCard({ check, currency, onDismiss, onAction, t }) {
  const meta = TIER_META.hero;
  const fmtMetrics = useFormattedMetrics(check.metrics, currency);

  return (
    <div className={`rounded-lg border-2 ${meta.border} ${meta.bg} p-4 space-y-3`}>
      <div className="flex items-start gap-3">
        <meta.Icon className={`h-6 w-6 mt-0.5 shrink-0 ${meta.iconColor}`} />
        <div className="flex-1 min-w-0">
          <p className={`text-base font-bold ${meta.headerColor}`}>
            {t(`checks.${check.id}.title`, fmtMetrics)}
          </p>
          <p className={`text-sm mt-1 ${meta.bodyColor}`}>
            {t(`checks.${check.id}.body`, fmtMetrics)}
          </p>
          {t(`checks.${check.id}.cause`, '') && (
            <p className={`text-xs mt-1.5 italic opacity-80 ${meta.bodyColor}`}>
              {t(`checks.${check.id}.cause`, fmtMetrics)}
            </p>
          )}
        </div>
        <DismissButton onClick={onDismiss} t={t} className={meta.bodyColor} />
      </div>

      {/* Drill data — full table in Hero (not truncated) */}
      {check.drill_data && (
        <DrillRenderer drill={check.drill_data} currency={currency} t={t} compact={false} />
      )}

      {/* Actions */}
      {check.actions?.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {check.actions.map((action, i) => {
            const am = ACTION_META[action.type] || ACTION_META.navigate;
            return (
              <Button
                key={i}
                size="sm"
                variant={am.variant}
                onClick={() => onAction(action)}
                className="text-sm h-8"
              >
                <am.Icon className="h-3.5 w-3.5 mr-1.5" />
                {t(`intelligenceBanner.actions.${action.label_key}`, action.label_key)}
              </Button>
            );
          })}
        </div>
      )}
    </div>
  );
}


// ── Collapsible section (secondary + housekeeping) ───────────────────────────


function CollapsibleSection({ tier, titleKey, checks, currency, onDismiss, onAction, defaultExpanded, t }) {
  const meta = TIER_META[tier] || TIER_META.housekeeping;
  const [expanded, setExpanded] = useState(defaultExpanded);
  const count = checks.length;

  return (
    <div className={`rounded-lg border ${meta.border} ${meta.bg}`}>
      <button
        type="button"
        onClick={() => setExpanded(v => !v)}
        className="w-full flex items-center gap-2 p-3 text-left"
      >
        <meta.Icon className={`h-4 w-4 shrink-0 ${meta.iconColor}`} />
        <div className="flex-1">
          <p className={`text-sm font-semibold ${meta.headerColor}`}>
            {t(titleKey, { count })}
          </p>
        </div>
        <div className={`shrink-0 ${meta.bodyColor}`}>
          {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        </div>
      </button>

      {expanded && (
        <div className="border-t border-current/10 divide-y divide-current/5">
          {checks.map((check) => (
            <CompactCheckCard
              key={check.id}
              check={check}
              tier={tier}
              currency={currency}
              onDismiss={() => onDismiss(check.id)}
              onAction={onAction}
              t={t}
            />
          ))}
        </div>
      )}
    </div>
  );
}


function CompactCheckCard({ check, tier, currency, onDismiss, onAction, t }) {
  const meta = TIER_META[tier] || TIER_META.housekeeping;
  const fmtMetrics = useFormattedMetrics(check.metrics, currency);
  const [drillOpen, setDrillOpen] = useState(false);

  return (
    <div className="p-3 space-y-1.5">
      <div className="flex items-start gap-2">
        <span className={`w-1.5 h-1.5 rounded-full ${SEVERITY_META[check.severity]?.dotClass} mt-2 shrink-0`} />
        <div className="flex-1 min-w-0">
          <p className={`text-sm font-semibold ${meta.headerColor}`}>
            {t(`checks.${check.id}.title`, fmtMetrics)}
          </p>
          <p className={`text-xs mt-0.5 ${meta.bodyColor}`}>
            {t(`checks.${check.id}.body`, fmtMetrics)}
          </p>
        </div>
        <DismissButton onClick={onDismiss} t={t} className={meta.bodyColor} compact />
      </div>

      {/* Compact actions row */}
      <div className="flex flex-wrap items-center gap-2 pl-3.5">
        {check.drill_data && (
          <button
            type="button"
            onClick={() => setDrillOpen(v => !v)}
            className={`text-xs underline-offset-2 hover:underline ${meta.bodyColor}`}
          >
            {drillOpen
              ? t('intelligenceBanner.actions.collapse')
              : t('intelligenceBanner.drill.see_details')}
          </button>
        )}
        {check.actions?.map((action, i) => {
          const am = ACTION_META[action.type] || ACTION_META.navigate;
          return (
            <button
              key={i}
              type="button"
              onClick={() => onAction(action)}
              className={`text-xs inline-flex items-center gap-1 underline-offset-2 hover:underline ${meta.bodyColor}`}
            >
              <am.Icon className="h-3 w-3" />
              {t(`intelligenceBanner.actions.${action.label_key}`, action.label_key)}
            </button>
          );
        })}
      </div>

      {drillOpen && check.drill_data && (
        <div className="pl-3.5">
          <DrillRenderer drill={check.drill_data} currency={currency} t={t} compact />
        </div>
      )}
    </div>
  );
}


// ── Drill renderer ──────────────────────────────────────────────────────────


function DrillRenderer({ drill, currency, t, compact = false }) {
  if (!drill) return null;
  const items = drill.items || drill.rows || [];
  if (items.length === 0) return null;

  const displayLimit = compact ? 5 : 10;

  if (drill.type === 'comparison') {
    return (
      <div className="rounded bg-white/70 border border-current/10 p-2.5 space-y-1.5">
        {items.map((row, i) => (
          <div key={i} className="flex items-center justify-between text-xs">
            <span className="opacity-80">
              {t(`intelligenceBanner.drill.${row.label_key}`, row.label_key)}
            </span>
            <span className="font-semibold tabular-nums">
              {formatCurrency(row.value, currency)}
              {row.subvalue != null && (
                <span className="opacity-70 ml-1 font-normal">({row.subvalue})</span>
              )}
            </span>
          </div>
        ))}
      </div>
    );
  }

  if (drill.type === 'product_list') {
    return (
      <div className="rounded bg-white/70 border border-current/10 divide-y divide-current/5">
        {items.slice(0, displayLimit).map((p) => (
          <div key={p.product_id} className="flex items-center justify-between text-xs px-2.5 py-1.5">
            <span className="truncate flex-1 min-w-0">
              <span className="font-medium">{p.name || '—'}</span>
              {p.margin_pct != null && (
                <span className={`ml-2 font-semibold ${
                  p.kind === 'negative' ? 'text-red-700' : 'text-amber-700'
                }`}>
                  {p.margin_pct.toFixed(1)}%
                </span>
              )}
            </span>
            {p.value != null && (
              <span className="font-semibold tabular-nums shrink-0 ml-2">
                {formatCurrency(p.value, currency)}
              </span>
            )}
          </div>
        ))}
        {items.length > displayLimit && (
          <div className="text-[10px] opacity-70 px-2.5 py-1.5">
            {t('intelligenceBanner.drill.see_more', { count: items.length })}
          </div>
        )}
      </div>
    );
  }

  if (drill.type === 'category_list') {
    return (
      <div className="rounded bg-white/70 border border-current/10 divide-y divide-current/5">
        {items.slice(0, displayLimit).map((c, i) => (
          <div key={i} className="flex items-center justify-between text-xs px-2.5 py-1.5">
            <span className="truncate flex-1 min-w-0">{c.category || c.name || '—'}</span>
            {c.amount != null ? (
              <span className="font-semibold tabular-nums shrink-0 ml-2">
                {formatCurrency(c.amount, currency)}
              </span>
            ) : c.purchase_count != null ? (
              <span className="opacity-70 tabular-nums shrink-0 ml-2">
                {c.purchase_count} acquisti
              </span>
            ) : null}
          </div>
        ))}
      </div>
    );
  }

  if (drill.type === 'orphan_sales_list') {
    return (
      <div className="rounded bg-white/70 border border-current/10 divide-y divide-current/5">
        {items.slice(0, displayLimit).map((r, i) => (
          <div key={i} className="flex items-center justify-between text-xs px-2.5 py-1.5 gap-2">
            <span className="truncate flex-1 min-w-0">
              {r.description}
              <span className="opacity-70 ml-1">· {r.date} · {r.source}</span>
            </span>
            <span className="font-semibold tabular-nums shrink-0">
              {formatCurrency(r.amount, currency)}
            </span>
          </div>
        ))}
      </div>
    );
  }

  if (drill.type === 'order_list') {
    return (
      <div className="rounded bg-white/70 border border-current/10 divide-y divide-current/5">
        {items.slice(0, displayLimit).map((o, i) => (
          <div key={i} className="flex items-center justify-between text-xs px-2.5 py-1.5 gap-2">
            <span className="truncate flex-1 min-w-0">
              <span className="font-mono font-semibold">{o.order_number}</span>
              {o.customer && o.customer !== '—' && (
                <span className="opacity-80 ml-2">{o.customer}</span>
              )}
              {o.date && <span className="opacity-60 ml-2">· {o.date}</span>}
            </span>
            {o.total != null && (
              <span className="font-semibold tabular-nums shrink-0">
                {formatCurrency(o.total, currency)}
              </span>
            )}
          </div>
        ))}
        {items.length > displayLimit && (
          <div className="text-[10px] opacity-70 px-2.5 py-1.5">
            {t('intelligenceBanner.drill.see_more', { count: items.length })}
          </div>
        )}
      </div>
    );
  }

  // Fallback for unknown drill types — render nothing rather than crash.
  return null;
}


function DismissButton({ onClick, t, className = '', compact = false }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`text-xs opacity-70 hover:opacity-100 shrink-0 inline-flex items-center gap-1 ${className}`}
      aria-label={t('intelligenceBanner.actions.dismiss')}
    >
      <X className="h-3 w-3" />
      {!compact && (
        <span className="hidden sm:inline">
          {t('intelligenceBanner.actions.dismiss')}
        </span>
      )}
    </button>
  );
}


// ── Helpers ──────────────────────────────────────────────────────────────────


/**
 * Builds an interpolation dict for i18n strings. Adds *_formatted
 * keys for every monetary metric so the i18n template can use
 * ``{{blind_revenue_formatted}}`` rather than hard-coding currency.
 */
function useFormattedMetrics(metrics, currency) {
  return useMemo(() => {
    const out = { ...(metrics || {}) };
    const money_keys = ['blind_revenue', 'total_revenue', 'products_revenue',
                       'cashflow_revenue', 'diff_amount', 'amount',
                       'unattr_amount', 'total_amount', 'pool', 'value',
                       'subvalue'];
    for (const k of money_keys) {
      if (typeof out[k] === 'number') {
        out[`${k}_formatted`] = formatCurrency(out[k], currency);
      }
    }
    return out;
  }, [metrics, currency]);
}


/** Default action router. Maps the action.type to a UX outcome. */
function handleAction(action, { navigate, onRefreshMetrics }) {
  if (!action) return;
  switch (action.type) {
    case 'navigate':
    case 'external':
      if (action.target) {
        if (action.target.startsWith('/')) navigate(action.target);
        else window.open(action.target, '_blank');
      }
      break;
    case 'bulk_configure_cost':
      navigate('/products?filter=missing_cost');
      break;
    case 'refresh_metrics':
      onRefreshMetrics?.();
      break;
    default:
      break;
  }
}
