/**
 * PlansPage — full-page plan selection with detailed plan cards.
 *
 * v5.8 / Onda 9.G: features are now grouped into 4 visual categories
 * (Cashflow / Commerce / AI / Team & support) inside each card so users
 * can scan horizontally between plans for the same category. The 4
 * quick-stats grid stays at the top for at-a-glance comparison.
 *
 * Add-on packs section is shown below the main plan grid (was buggy:
 * add-ons were being rendered as main plan cards in the grid because
 * the `/billing/plans` endpoint returns both — now we filter is_addon
 * out of the main grid and render PlansAddonsSection separately).
 *
 * Features: checkout (free→paid), modify (paid→paid), confirmation dialog,
 * rate limiting, responsive grid, visual hierarchy, error toasts.
 */
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { AppLayout, Header } from '../components/Layout';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../components/ui/dialog';
import {
  Check, Sparkles, Loader2, ArrowLeft, ArrowRight,
  Zap, Shield, Crown, Rocket, Infinity as InfinityIcon,
  TrendingUp, ShoppingBag, Bot, Users,
} from 'lucide-react';
import { toast } from 'sonner';
import { billingAPI } from '../api/billing';
import { useBilling } from '../hooks/useBilling';
import PlansAddonsSection from '../components/PlansAddonsSection';
import RetreatPlansPage from './RetreatPlansPage';

const PLAN_TIERS = { free: 0, starter: 1, core: 2, pro: 3, enterprise: 4 };

const PLAN_THEME = {
  free: {
    gradient: 'from-gray-50 to-gray-100/50',
    border: 'border-gray-200',
    activeBorder: 'border-gray-400 ring-2 ring-gray-200',
    badge: 'bg-gray-100 text-gray-700',
    icon: Shield,
    iconColor: 'text-gray-500',
    statBg: 'bg-white/80',
    buttonVariant: 'outline',
  },
  starter: {
    gradient: 'from-emerald-50 to-teal-50/50',
    border: 'border-emerald-200',
    activeBorder: 'border-emerald-500 ring-2 ring-emerald-200',
    badge: 'bg-emerald-100 text-emerald-700',
    icon: Zap,
    iconColor: 'text-emerald-500',
    statBg: 'bg-white/80',
    buttonVariant: 'secondary',
  },
  core: {
    gradient: 'from-blue-50 to-indigo-50/50',
    border: 'border-blue-300',
    activeBorder: 'border-blue-500 ring-2 ring-blue-200',
    badge: 'bg-blue-100 text-blue-700',
    icon: Crown,
    iconColor: 'text-blue-500',
    statBg: 'bg-white/80',
    buttonVariant: 'default',
  },
  pro: {
    gradient: 'from-violet-50 to-purple-50/50',
    border: 'border-violet-200',
    activeBorder: 'border-violet-500 ring-2 ring-violet-200',
    badge: 'bg-violet-100 text-violet-700',
    icon: Rocket,
    iconColor: 'text-violet-500',
    statBg: 'bg-white/80',
    buttonVariant: 'secondary',
  },
};

// ── Plan comparison matrix ──────────────────────────────────────────────────
//
// v5.8 / Onda 9.H — replaces the old per-plan PLAN_HIGHLIGHTS + free-form
// features_display approach. Now every card renders the SAME rows in
// 4 sections, in the same order, so users can scan horizontally between
// cards to compare a single metric (e.g. "ordini/mese" sits at the same
// vertical position in Free / Solo / Commerce Starter / Commerce Pro).
//
// v5.8 / Onda 10 Step A.3 — Each row references a (module_key, feature_key)
// or a literal value/string. The actual numeric/boolean is resolved AT RENDER
// TIME from `plan.derived_limits[module_key][feature_key]` (provided by the
// backend in `/api/billing/plans` since Onda 10 Step A.3). When system_admin
// edits a tier limit (e.g. data_rows Solo 200→500), the matrix automatically
// reflects the new number on next focus refresh — no frontend redeploy.
//
// Row schema:
//   { labelKey, defaultLabel,
//     // Either:
//     module: '<module_key>', feature: '<feature_key>',  → resolves int from derived_limits
//     // Or for literal values not in catalog:
//     literal: { free:..., starter:..., core:..., pro:... },  → static fallback
//     // Optional fallback when module/feature missing:
//     fallback: 0
//   }
//
// VALUE ENCODING (handled by renderMatrixValue):
//   number > 0  → bold number ("200")
//   number = 0  → muted "—" (means: not in this plan)
//   number = -1 → ∞ icon (unlimited)
//   true        → green ✓
//   false       → muted "—"
//   string      → translated label via billing.matrix.value.<token>
//
// SOURCE OF TRUTH: backend/services/seed_pricing.py PricingPlan tier limits
// (live, queryable). For team_members the source is _TEAM_LIMITS hardcoded —
// migrating to catalog in Step B.1.

const PLAN_MATRIX_SECTIONS = [
  {
    titleKey: 'billing.matrix.section.commerce',
    defaultTitle: 'Commerce',
    icon: ShoppingBag,
    color: 'text-blue-600',
    bgColor: 'bg-blue-50/50',
    rows: [
      { labelKey: 'billing.matrix.row.orders_monthly', defaultLabel: 'Ordini gestiti / mese',
        module: 'commerce', feature: 'orders_monthly' },
      { labelKey: 'billing.matrix.row.stores_max',     defaultLabel: 'Negozi online',
        module: 'commerce', feature: 'stores_max' },
      { labelKey: 'billing.matrix.row.products',       defaultLabel: 'Prodotti a catalogo',
        module: 'product_catalog', feature: 'products' },
      { labelKey: 'billing.matrix.row.checkout_stripe', defaultLabel: 'Checkout Stripe nativo',
        // Boolean: render as ✓/— based on whether the limit is -1 (enabled) or 0 (disabled)
        module: 'commerce', feature: 'checkout_stripe', encodeAs: 'flag' },
    ],
  },
  {
    titleKey: 'billing.matrix.section.ai',
    defaultTitle: 'AI',
    icon: Bot,
    color: 'text-violet-600',
    bgColor: 'bg-violet-50/50',
    rows: [
      { labelKey: 'billing.matrix.row.ai_chat',    defaultLabel: 'Chat AI / mese',
        module: 'ai_assistant', feature: 'chat' },
      { labelKey: 'billing.matrix.row.ai_digest',  defaultLabel: 'Digest AI / mese',
        module: 'ai_assistant', feature: 'digest' },
      { labelKey: 'billing.matrix.row.ai_alerts',  defaultLabel: 'Analisi anomalie AI',
        module: 'ai_assistant', feature: 'alert_analysis', encodeAs: 'flag' },
      { labelKey: 'billing.matrix.row.ai_health',  defaultLabel: 'Health Score AI',
        module: 'ai_assistant', feature: 'health_explanation', encodeAs: 'flag' },
    ],
  },
  {
    titleKey: 'billing.matrix.section.analytics',
    defaultTitle: 'Cashflow & analytics',
    icon: TrendingUp,
    color: 'text-emerald-600',
    bgColor: 'bg-emerald-50/50',
    rows: [
      { labelKey: 'billing.matrix.row.data_rows', defaultLabel: 'Righe dati / mese',
        module: 'cashflow_monitor', feature: 'data_rows' },
      { labelKey: 'billing.matrix.row.email_alerts', defaultLabel: 'Email alert critici',
        module: 'cashflow_monitor', feature: 'email_alerts', encodeAs: 'flag' },
      { labelKey: 'billing.matrix.row.email_digest', defaultLabel: 'Digest email settimanale',
        // Mixed string-token semantics: kept as literal until catalog supports a string-typed limit
        literal: { free: false, starter: 'kpi', core: 'ai', pro: 'ai' } },
      { labelKey: 'billing.matrix.row.export', defaultLabel: 'Export CSV / PDF',
        module: 'cashflow_monitor', feature: 'export', encodeAs: 'flag' },
    ],
  },
  {
    titleKey: 'billing.matrix.section.team',
    defaultTitle: 'Team & supporto',
    icon: Users,
    color: 'text-amber-600',
    bgColor: 'bg-amber-50/50',
    rows: [
      { labelKey: 'billing.matrix.row.members', defaultLabel: 'Membri team',
        // _TEAM_LIMITS is hardcoded backend-side (organizations.py:1246) but
        // exposed via `derived_limits.team.team_members` since Step A.3.
        module: 'team', feature: 'team_members' },
      { labelKey: 'billing.matrix.row.support', defaultLabel: 'Supporto',
        // Support tier is descriptive copy, kept as literal pending future
        // structured representation (e.g. an Onda 10+ "support_tier" field).
        literal: { free: false, starter: false, core: 'email', pro: 'priority' } },
    ],
  },
];

// Onda 10 Step A.3 — Resolve a row's value for a given plan slug, dynamically
// from the backend-provided derived_limits. Falls back to literal mapping.
//
// `plan` is the plan dict from /api/billing/plans (with derived_limits).
// Returns the value to feed into renderMatrixValue.
function resolveMatrixValue(row, plan) {
  // Literal-only row: use the static map
  if (row.literal !== undefined) {
    return row.literal[plan?.slug] !== undefined ? row.literal[plan.slug] : false;
  }
  // Module/feature row: read from derived_limits
  const derived = plan?.derived_limits?.[row.module] || {};
  const value = derived[row.feature];
  if (value === undefined || value === null) {
    return row.fallback !== undefined ? row.fallback : 0;
  }
  // Encode as flag: -1 → true (enabled), >0 → true, 0 → false
  if (row.encodeAs === 'flag') {
    if (value === -1) return true;
    if (value === 0) return false;
    return Boolean(value);
  }
  return value;
}


export const PlansPage = () => {
  const { t } = useTranslation('settings');
  const navigate = useNavigate();
  const {
    plans, plan: currentPlan, billingEnabled, isPaid,
    hasStripeCustomer, hasHadTrial, refresh,
    // Onda 14 — surface trial state in the upgrade confirm dialog so
    // the user understands the trial transfers on plan change.
    isTrialing, trialEndsAt,
  } = useBilling();

  const [loadingSlug, setLoadingSlug] = useState(null);
  const [interval, setInterval] = useState('month');
  const [error, setError] = useState(null);
  const [confirmPlan, setConfirmPlan] = useState(null);

  // Retreat fork (Blocco B) — le org sul catalogo ritiri vedono la pagina
  // piani dedicata (2 card + fee trasparente), non la matrice legacy
  // Aurya. Hook sopra, early-return sotto: ordine hook invariato.
  if ((currentPlan || '').startsWith('retreat_')) {
    return <RetreatPlansPage />;
  }

  const isDowngrade = (slug) => (PLAN_TIERS[slug] || 0) < (PLAN_TIERS[currentPlan] || 0);

  const handleSelect = async (planSlug) => {
    if (planSlug === currentPlan || planSlug === 'free') return;
    setError(null);
    setConfirmPlan(null);

    const selectedPlan = plans.find((p) => p.slug === planSlug);
    if (selectedPlan && !selectedPlan.is_self_serve) {
      window.location.href = 'mailto:info@aurya.life?subject=Piano%20Enterprise%20Aurya';
      return;
    }
    if (!billingEnabled) {
      const msg = t('billing.stripe_not_configured', 'Stripe non configurato.');
      setError(msg);
      toast.error(msg);
      return;
    }

    if (hasStripeCustomer && isPaid) {
      setConfirmPlan(selectedPlan);
      return;
    }

    setLoadingSlug(planSlug);
    try {
      const { url } = await billingAPI.createCheckoutSession(planSlug, interval);
      if (url) {
        window.location.href = url;
        return;
      }
      const noUrlMsg = t('billing.checkout_no_url', 'Nessun URL di checkout dal server. Riprova o contatta il supporto.');
      setError(noUrlMsg);
      toast.error(noUrlMsg);
      setLoadingSlug(null);
    } catch (err) {
      const detail = err.response?.data?.detail;
      const code = typeof detail === 'object' ? detail.code : '';

      // Onda 20 — backend's Layer 1 guard refused checkout because Stripe
      // already has an active sub (DB was stale). Auto-recover by
      // refreshing billing state and routing to the modify-plan flow,
      // exactly as if the user had clicked an upgrade from a known
      // paid state. Self-healing — the user never sees the error.
      if (code === 'duplicate_subscription' || code === 'DUPLICATE_SUBSCRIPTION') {
        try {
          await refresh();  // pulls fresh /billing/status
          setLoadingSlug(null);
          // Open the same confirm-change dialog we use for normal
          // upgrades. handleConfirmModify will call modifySubscription.
          setConfirmPlan(selectedPlan);
          toast.info(t('billing.duplicate_resolved', {
            defaultValue: 'Hai già un abbonamento attivo. Conferma il cambio piano.',
          }));
          return;
        } catch {
          // fall through to the generic error below
        }
      }

      const message =
        typeof detail === 'object'
          ? detail.message
          : detail || err.message || t('billing.checkout_error', 'Errore nel checkout.');
      setError(message);
      toast.error(message);
      setLoadingSlug(null);
    }
  };

  const handleConfirmModify = async () => {
    if (!confirmPlan) return;
    setLoadingSlug(confirmPlan.slug);
    setError(null);
    try {
      await billingAPI.modifySubscription(confirmPlan.slug, interval);
      toast.success(t('billing.plan_changed', { plan: confirmPlan.name }) || `Piano cambiato a ${confirmPlan.name}`);
      setConfirmPlan(null);
      setLoadingSlug(null);
      const poll = async () => { for (let i = 0; i < 5; i++) { await new Promise(r => setTimeout(r, 2000)); await refresh(); } };
      poll();
    } catch (err) {
      const detail = err.response?.data?.detail;
      const code = typeof detail === 'object' ? detail.code : '';
      const errorMsg = typeof detail === 'object' ? detail.message : detail;
      if (code === 'no_subscription') {
        try { const { url } = await billingAPI.createCheckoutSession(confirmPlan.slug, interval); if (url) window.location.href = url; return; } catch { setError('Errore nel checkout.'); }
      } else { setError(errorMsg || 'Errore nel cambio piano.'); }
      setLoadingSlug(null);
    }
  };

  const formatPrice = (plan) => {
    if (!plan || plan.price_monthly === 0) return t('billing.free_label', 'Gratis');
    const price = interval === 'year' && plan.price_yearly ? plan.price_yearly : plan.price_monthly;
    const period = interval === 'year' ? t('billing.year_short', 'anno') : t('billing.month_short', 'mese');
    return { amount: price, period };
  };

  const getButtonLabel = (plan) => {
    if (plan.slug === currentPlan) return t('billing.current_plan', 'Piano attuale');
    if (plan.slug === 'free') return t('billing.free_label', 'Gratis');
    if (!plan.is_self_serve) return t('billing.contact_sales', 'Contattaci');
    if (isPaid && hasStripeCustomer) {
      return isDowngrade(plan.slug)
        ? t('billing.downgrade_to', 'Passa a {{plan}}', { plan: plan.name })
        : t('billing.upgrade_to', 'Passa a {{plan}}', { plan: plan.name });
    }
    if (plan.trial_days > 0 && !hasHadTrial)
      return t('billing.start_trial', 'Prova gratis {{days}} giorni', { days: plan.trial_days });
    return t('billing.subscribe', 'Abbonati');
  };

  // Render a matrix value with consistent visual semantics:
  //   number > 0 → bold number (e.g. "200", "1.000")
  //   number = 0 → muted "—" (means "not in this plan")
  //   number = -1 → ∞ icon (unlimited)
  //   true → green ✓
  //   false → muted "—"
  //   string → translated label via billing.matrix.value.<token>
  const renderMatrixValue = (value) => {
    if (value === -1) {
      return <InfinityIcon className="h-3.5 w-3.5 text-foreground inline-block" />;
    }
    if (value === true) {
      return (
        <span className="inline-flex items-center justify-center h-4 w-4 rounded-full bg-green-100">
          <Check className="h-2.5 w-2.5 text-green-600" />
        </span>
      );
    }
    if (value === false || value === 0 || value === null || value === undefined) {
      return <span className="text-muted-foreground">—</span>;
    }
    if (typeof value === 'string') {
      // Translated label token (e.g. 'kpi' → "Settimanale (KPI)")
      return (
        <span className="font-semibold text-foreground text-[11px]">
          {t(`billing.matrix.value.${value}`, value)}
        </span>
      );
    }
    // Number > 0
    const formatted = typeof value === 'number' && value >= 1000 ? value.toLocaleString() : String(value);
    return <span className="font-bold text-foreground tabular-nums">{formatted}</span>;
  };

  // Legacy renderStat kept for backwards compatibility — unused after 9.H but
  // referenced nowhere else; will be removed once we're sure no other page
  // imports this function. Currently dead code in the bundle.
  // eslint-disable-next-line no-unused-vars
  const renderStat = (stat, theme) => {
    const label = t(`billing.stats.${stat.metric}`, stat.metric);
    const unitText = stat.unit ? t(`billing.stats.units.${stat.unit}`, '') : '';
    const isUnlimited = stat.value === 'unlimited';
    const isNoShop = stat.unit === 'no_shop';
    return (
      <div className={`rounded-lg ${theme.statBg} px-2.5 py-2 flex flex-col gap-0.5 ${stat.highlight ? 'ring-1 ring-blue-300' : ''}`}>
        <div className="text-[10px] uppercase tracking-wide text-muted-foreground font-medium">
          {label}
        </div>
        <div className="flex items-baseline gap-1">
          {isUnlimited ? (
            <InfinityIcon className="h-5 w-5 text-foreground" />
          ) : isNoShop ? (
            <span className="text-base font-semibold text-muted-foreground italic">
              {t('billing.stats.units.no_shop', 'no shop')}
            </span>
          ) : (
            <span className="text-base font-bold text-foreground tabular-nums">{stat.value}</span>
          )}
          {unitText && !isNoShop && (
            <span className="text-[10px] text-muted-foreground">{unitText}</span>
          )}
        </div>
      </div>
    );
  };

  return (
    <AppLayout>
      <Header
        title={t('billing.plans_page_title', 'Piani e abbonamenti')}
        subtitle={t('billing.plans_page_subtitle', 'Scegli il piano giusto per la tua azienda')}
      >
        <Button variant="outline" size="sm" onClick={() => navigate('/settings')}>
          <ArrowLeft className="h-4 w-4 mr-1.5" />
          {t('billing.back_to_settings', 'Impostazioni')}
        </Button>
      </Header>

      <div className="p-4 md:p-8 space-y-8 animate-fade-in max-w-6xl mx-auto">

        {/* Interval toggle */}
        <div className="flex justify-center">
          <div className="inline-flex items-center bg-muted rounded-full p-1">
            <button
              className={`px-5 py-2 rounded-full text-sm font-medium transition-all ${
                interval === 'month'
                  ? 'bg-white text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
              onClick={() => setInterval('month')}
            >
              {t('billing.monthly', 'Mensile')}
            </button>
            <button
              className={`px-5 py-2 rounded-full text-sm font-medium transition-all flex items-center gap-1.5 ${
                interval === 'year'
                  ? 'bg-white text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
              onClick={() => setInterval('year')}
            >
              {t('billing.yearly', 'Annuale')}
              <span className="text-[10px] font-bold text-green-600 bg-green-100 px-1.5 py-0.5 rounded-full">
                -17%
              </span>
            </button>
          </div>
        </div>

        {/* Error banner — visible immediately above the cards. Also redundantly fires
            a toast.error in handleSelect for users scrolled mid-page. */}
        {error && !confirmPlan && (
          <div className="bg-destructive/10 border border-destructive/20 rounded-xl p-4 text-center">
            <p className="text-sm text-destructive font-medium">{error}</p>
          </div>
        )}

        {/* Plan cards.
            v5.8 / Onda 9.G — filter out add-ons here: the /billing/plans
            endpoint returns ALL public commercial plans including is_addon
            ones. Add-ons are rendered separately by <PlansAddonsSection />
            below with their own grid + behaviour. */}
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {plans.filter((p) => !p.is_addon).map((plan) => {
            const isCurrent = plan.slug === currentPlan;
            const theme = PLAN_THEME[plan.slug] || PLAN_THEME.free;
            const isRecommended = plan.slug === 'core';
            const IconComponent = theme.icon;
            const priceData = formatPrice(plan);

            return (
              <div
                key={plan.slug}
                className={`relative rounded-2xl bg-gradient-to-b ${theme.gradient} border-2 transition-all duration-200 hover:shadow-lg ${
                  isCurrent ? theme.activeBorder : isRecommended && !isCurrent ? `${theme.border} shadow-md` : `${theme.border} hover:shadow-md`
                }`}
              >
                {/* Recommended badge */}
                {isRecommended && !isCurrent && (
                  <div className="absolute -top-3.5 left-1/2 -translate-x-1/2 z-10">
                    <div className="flex items-center gap-1 bg-blue-600 text-white text-[11px] font-semibold px-3 py-1 rounded-full shadow-md">
                      <Sparkles className="h-3 w-3" />
                      {t('billing.recommended', 'Consigliato')}
                    </div>
                  </div>
                )}

                {/* Current plan indicator */}
                {isCurrent && (
                  <div className="absolute -top-3.5 left-1/2 -translate-x-1/2 z-10">
                    <div className="flex items-center gap-1 bg-foreground text-background text-[11px] font-semibold px-3 py-1 rounded-full shadow-md">
                      <Check className="h-3 w-3" />
                      {t('billing.current_plan', 'Piano attuale')}
                    </div>
                  </div>
                )}

                <div className="p-6 flex flex-col h-full">
                  {/* Header: icon + name */}
                  <div className="flex items-center gap-2.5 mb-3">
                    <div className={`flex items-center justify-center h-9 w-9 rounded-xl bg-white/80 shadow-sm ${theme.iconColor}`}>
                      <IconComponent className="h-5 w-5" />
                    </div>
                    <div className="min-w-0">
                      <h3 className="font-bold text-base">{plan.name}</h3>
                    </div>
                  </div>

                  {/* Tagline (one-liner positioning statement) */}
                  {plan.tagline && (
                    <p className="text-xs text-muted-foreground leading-relaxed mb-4 min-h-[2.5em]">
                      {plan.tagline}
                    </p>
                  )}

                  {/* Price + trial */}
                  <div className="mb-4">
                    {typeof priceData === 'string' ? (
                      <div className="text-3xl font-extrabold tracking-tight">{priceData}</div>
                    ) : (
                      <div className="flex items-baseline gap-1">
                        <span className="text-3xl font-extrabold tracking-tight">
                          €{priceData.amount}
                        </span>
                        <span className="text-sm text-muted-foreground font-medium">
                          /{priceData.period}
                        </span>
                      </div>
                    )}
                    {plan.trial_days > 0 && plan.is_self_serve && (
                      <Badge className="mt-2 bg-blue-50 text-blue-700 border-0 text-[11px] font-medium">
                        🎁 {t('billing.trial_badge', 'Prova gratis {{days}} giorni', { days: plan.trial_days })}
                      </Badge>
                    )}
                  </div>

                  {/* Divider */}
                  <div className="h-px bg-border/60 mb-3" />

                  {/* Unified plan matrix — every card renders the SAME rows in
                      the SAME order so users can scan horizontally between
                      cards to compare a single metric. Section headers are
                      colored + iconified for visual anchoring. */}
                  <div className="space-y-3 mb-6 flex-1">
                    {PLAN_MATRIX_SECTIONS.map((section) => {
                      const SecIcon = section.icon;
                      return (
                        <div key={section.titleKey} className="rounded-lg overflow-hidden">
                          {/* Section header */}
                          <div className={`flex items-center gap-1.5 px-2 py-1 ${section.bgColor}`}>
                            <SecIcon className={`h-3 w-3 ${section.color}`} />
                            <span className={`text-[10px] font-semibold uppercase tracking-wider ${section.color}`}>
                              {t(section.titleKey, section.defaultTitle)}
                            </span>
                          </div>
                          {/* Rows */}
                          <div className="divide-y divide-border/30">
                            {section.rows.map((row) => {
                              // Onda 10 Step A.3 — resolve dynamically from
                              // backend-provided derived_limits; falls back
                              // to literal map for non-catalog rows.
                              const value = resolveMatrixValue(row, plan);
                              const isPresent = value !== false && value !== 0 && value !== null && value !== undefined;
                              return (
                                <div
                                  key={row.labelKey}
                                  className={`flex items-center justify-between px-2 py-1 text-[12px] ${
                                    isPresent ? '' : 'opacity-60'
                                  }`}
                                >
                                  <span className="text-muted-foreground leading-tight pr-1">
                                    {t(row.labelKey, row.defaultLabel)}
                                  </span>
                                  <span className="flex-shrink-0">
                                    {renderMatrixValue(value)}
                                  </span>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {/* CTA Button */}
                  <Button
                    className={`w-full h-10 font-semibold text-sm ${
                      isRecommended && !isCurrent ? 'shadow-md' : ''
                    }`}
                    variant={isCurrent || plan.slug === 'free' ? 'outline' : theme.buttonVariant}
                    disabled={isCurrent || plan.slug === 'free' || loadingSlug !== null}
                    onClick={() => handleSelect(plan.slug)}
                  >
                    {loadingSlug === plan.slug && (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    )}
                    {getButtonLabel(plan)}
                  </Button>
                </div>
              </div>
            );
          })}
        </div>

        {/* Trial-once disclaimer (kept compact; the addons section below
            covers the second hint we used to render here). */}
        <div className="text-center pt-2">
          <p className="text-xs text-muted-foreground">
            {t(
              'billing.plans_footer_trial',
              'La prova gratuita di 14 giorni è una sola: utilizzata su un piano, non sarà più disponibile sugli altri.',
            )}
          </p>
        </div>

        {/* v5.8 / Onda 9.G — Add-on packs section.
            Self-loading via billingAPI.listAddons. Renders disabled cards for
            free/signed-out users; full card for paid users with add/+1 button.
            Anchor `#addons` on the section so external links can scroll to it. */}
        <PlansAddonsSection />

        {/* Confirmation dialog */}
        <Dialog open={!!confirmPlan} onOpenChange={(open) => { if (!open) { setConfirmPlan(null); setError(null); } }}>
          <DialogContent className="max-w-sm">
            <DialogHeader>
              <DialogTitle className="text-center text-lg">
                {confirmPlan && isDowngrade(confirmPlan.slug)
                  ? t('billing.confirm_downgrade_title', 'Conferma downgrade')
                  : t('billing.confirm_upgrade_title', 'Conferma upgrade')}
              </DialogTitle>
              <DialogDescription className="text-center">
                {confirmPlan && (() => {
                  // Onda 15 (Strategy B) — during trial, plan change ends
                  // the trial immediately and creates a prorated invoice
                  // for the new plan. Tell the user explicitly so the
                  // commitment is clear before they confirm.
                  if (isTrialing) {
                    return t('billing.confirm_change_ends_trial', {
                      plan: confirmPlan.name,
                      defaultValue: 'Cambiando piano interrompi il trial e attivi {{plan}} subito. Verrai addebitato pro-rata per il periodo restante.',
                    });
                  }
                  return isDowngrade(confirmPlan.slug)
                    ? t('billing.confirm_downgrade_note', 'Riceverai un credito proporzionale per il periodo non utilizzato.')
                    : t('billing.confirm_upgrade_note', 'Ti verrà addebitata la differenza proporzionale.');
                })()}
              </DialogDescription>
            </DialogHeader>

            {confirmPlan && (
              <div className="space-y-5 pt-2">
                {/* Visual comparison */}
                <div className="flex items-center justify-center gap-3">
                  <div className="flex flex-col items-center gap-1.5 p-3 rounded-xl bg-muted/50 min-w-[100px]">
                    <Badge className={`${PLAN_THEME[currentPlan]?.badge || 'bg-gray-100'} border-0 text-[11px]`}>
                      {plans.find(p => p.slug === currentPlan)?.name || currentPlan}
                    </Badge>
                    <span className="text-sm font-bold">
                      {(() => { const p = formatPrice(plans.find(pp => pp.slug === currentPlan) || { price_monthly: 0 }); return typeof p === 'string' ? p : `€${p.amount}`; })()}
                    </span>
                  </div>

                  <div className="flex items-center justify-center h-8 w-8 rounded-full bg-muted">
                    <ArrowRight className="h-4 w-4 text-muted-foreground" />
                  </div>

                  <div className="flex flex-col items-center gap-1.5 p-3 rounded-xl bg-primary/5 border border-primary/20 min-w-[100px]">
                    <Badge className={`${PLAN_THEME[confirmPlan.slug]?.badge || 'bg-gray-100'} border-0 text-[11px]`}>
                      {confirmPlan.name}
                    </Badge>
                    <span className="text-sm font-bold text-primary">
                      {(() => { const p = formatPrice(confirmPlan); return typeof p === 'string' ? p : `€${p.amount}`; })()}
                    </span>
                  </div>
                </div>

                {error && (
                  <p className="text-sm text-destructive text-center bg-destructive/10 rounded-lg p-2">{error}</p>
                )}

                <div className="flex flex-col gap-2">
                  <Button
                    className="w-full h-11 font-semibold"
                    onClick={handleConfirmModify}
                    disabled={loadingSlug !== null}
                  >
                    {loadingSlug && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                    {t('billing.confirm_change', 'Conferma cambio piano')}
                  </Button>
                  <Button
                    className="w-full"
                    variant="ghost"
                    onClick={() => { setConfirmPlan(null); setError(null); }}
                    disabled={loadingSlug !== null}
                  >
                    {t('billing.cancel', 'Annulla')}
                  </Button>
                </div>
              </div>
            )}
          </DialogContent>
        </Dialog>
      </div>
    </AppLayout>
  );
};

export default PlansPage;
