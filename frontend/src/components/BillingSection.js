/**
 * BillingSection v5.7 -- Enriched subscription overview.
 *
 * Three-section layout:
 *   A. Subscription Summary  (plan, status, price, dates, trial countdown, cancel messaging)
 *   B. Features & Usage      (included features checklist + AI usage meters)
 *   C. Actions               (upgrade/change plan, manage billing, explore higher plans)
 *
 * Also handles post-checkout polling (moved from SettingsPage for colocation).
 */
import React, { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Separator } from './ui/separator';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from './ui/dialog';
import { Textarea } from './ui/textarea';
import {
  CreditCard,
  ExternalLink,
  Loader2,
  Crown,
  Sparkles,
  AlertCircle,
  XCircle,
  RotateCcw,
} from 'lucide-react';
import { toast } from 'sonner';
import { billingAPI } from '../api/billing';
import BillingUsageDashboard from './BillingUsageDashboard';
import { useNavigate } from 'react-router-dom';
import { useBilling } from '../hooks/useBilling';
// Onda 25 — useAiAccess removed: the AI usage meters block that consumed
// it was deleted in favor of BillingUsageDashboard's unified rendering.
// Re-add the import if a future block needs aiEnabled/limits/usage from
// here directly.

// ── Color maps ───────────────────────────────────────────────────────────────

const STATUS_COLORS = {
  active: 'bg-green-100 text-green-700',
  trialing: 'bg-blue-100 text-blue-700',
  past_due: 'bg-red-100 text-red-700',
  canceled: 'bg-gray-100 text-gray-700',
  manual: 'bg-purple-100 text-purple-700',
  none: 'bg-gray-100 text-gray-500',
};

const PLAN_COLORS = {
  free: 'bg-gray-100 text-gray-700',
  starter: 'bg-emerald-100 text-emerald-700',
  core: 'bg-blue-100 text-blue-700',
  pro: 'bg-violet-100 text-violet-700',
  enterprise: 'bg-amber-100 text-amber-700',
};

// Onda 25 — AI_FEATURES const removed: the AI usage meters block that
// rendered them was deleted in favor of BillingUsageDashboard's unified
// rendering. The same metrics (chat / digest) and feature flags
// (alert_analysis / health_explanation) come from
// /billing/usage-summary now, with the same progress bar + check/lock UX.

// ── Component ────────────────────────────────────────────────────────────────

export default function BillingSection() {
  const { t } = useTranslation('settings');
  const billing = useBilling();
  const navigateTo = useNavigate();
  const goToPlans = () => navigateTo('/plans');
  const [portalLoading, setPortalLoading] = useState(false);

  // ── v5.8 / Onda 9.A.1: Native cancel & reactivate state ──────────────────
  const [cancelModalOpen, setCancelModalOpen] = useState(false);
  const [cancelMode, setCancelMode] = useState('at_period_end'); // 'at_period_end' | 'immediate'
  const [cancelReason, setCancelReason] = useState('');
  const [cancelLoading, setCancelLoading] = useState(false);
  const [reactivateLoading, setReactivateLoading] = useState(false);

  // ── Onda 13: refresh on mount ────────────────────────────────────────────
  // The useBilling context only auto-refreshes on window focus (10s
  // debounce). When the user navigates between in-app tabs (e.g.
  // /plans → /settings) the browser does NOT fire a focus event, so
  // the billing card here would render the stale plan after an upgrade
  // performed elsewhere. Trigger an explicit refresh on every mount of
  // this component to guarantee the card reflects the current state.
  // No dependencies — runs once per mount, no infinite loop.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { billing.refresh?.(); }, []);

  // ── Helpers ──────────────────────────────────────────────────────────────

  const formatDate = (iso) => {
    if (!iso) return '-';
    return new Date(iso).toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const daysRemaining = (isoDate) => {
    if (!isoDate) return 0;
    const diff = new Date(isoDate) - new Date();
    return Math.max(0, Math.ceil(diff / (1000 * 60 * 60 * 24)));
  };

  const handleManageBilling = async () => {
    setPortalLoading(true);
    try {
      const { url } = await billingAPI.createPortalSession();
      if (url) window.location.href = url;
    } catch {
      setPortalLoading(false);
    }
  };

  // ── v5.8 / Onda 9.A.1: Native cancel & reactivate handlers ───────────────

  const openCancelModal = () => {
    setCancelMode('at_period_end');
    setCancelReason('');
    setCancelModalOpen(true);
  };

  const handleConfirmCancel = async () => {
    setCancelLoading(true);
    try {
      const result = await billingAPI.cancelSubscription({
        atPeriodEnd: cancelMode === 'at_period_end',
        reason: cancelReason.trim(),
      });
      // Refresh state to reflect cancel_at_period_end / canceled
      await billing.refresh();
      setCancelModalOpen(false);
      if (result.status === 'cancel_pending' || cancelMode === 'at_period_end') {
        toast.success(
          t('billing.cancel_pending_toast', 'Abbonamento programmato per la cancellazione a fine periodo.'),
        );
      } else {
        toast.success(
          t('billing.cancel_immediate_toast', 'Abbonamento cancellato. Il piano è stato riportato a Free.'),
        );
      }
    } catch (err) {
      const msg = err?.response?.data?.detail || err?.message || 'Errore durante la cancellazione.';
      toast.error(typeof msg === 'string' ? msg : t('billing.cancel_error', 'Errore durante la cancellazione.'));
    } finally {
      setCancelLoading(false);
    }
  };

  const handleReactivate = async () => {
    setReactivateLoading(true);
    try {
      await billingAPI.reactivateSubscription();
      await billing.refresh();
      toast.success(
        t('billing.reactivate_toast', 'Abbonamento riattivato. La cancellazione è stata annullata.'),
      );
    } catch (err) {
      const msg = err?.response?.data?.detail || err?.message || 'Errore durante la riattivazione.';
      toast.error(typeof msg === 'string' ? msg : t('billing.reactivate_error', 'Errore durante la riattivazione.'));
    } finally {
      setReactivateLoading(false);
    }
  };

  // ── Post-checkout state refresh ──────────────────────────────────────────
  // After returning from Stripe Checkout with ?billing_success=1, poll the
  // billing status API directly (not via the billing context) to avoid
  // stale-closure issues.  The context is refreshed once the change is detected.
  const checkoutHandled = useRef(false);
  const previousPlanRef = useRef(billing.plan);
  // Keep the ref in sync so we always capture the plan *before* checkout redirect
  useEffect(() => { previousPlanRef.current = billing.plan; }, [billing.plan]);

  useEffect(() => {
    if (checkoutHandled.current) return;
    const params = new URLSearchParams(window.location.search);
    const isSuccess = params.get('billing_success') === '1';
    const isCancelled = params.get('billing_cancelled') === '1';

    if (!isSuccess && !isCancelled) return;
    checkoutHandled.current = true;

    // v5.7: Capture session_id BEFORE cleaning the URL — needed for verify fallback
    const sessionId = params.get('session_id');

    // Clean up URL query params without a reload
    const cleanUrl = window.location.pathname;
    window.history.replaceState({}, '', cleanUrl);

    if (isCancelled) return; // Nothing to do on cancel

    // Show processing toast, then poll for webhook to land
    const toastId = toast.loading(t('billing.checkout_processing'));
    const planBeforeCheckout = previousPlanRef.current;
    let attempts = 0;
    const maxAttempts = 8;       // v5.7: reduced from 12 (we have a verify fallback now)
    const pollInterval = 2000;   // v5.7: reduced from 2500ms (total: 16s vs 30s)

    // ── Phase 1: Poll for webhook delivery ────────────────────────────────
    const poll = async () => {
      attempts += 1;
      try {
        // Call the API directly to get the FRESH status — avoids stale closure
        const freshStatus = await billingAPI.getStatus();
        const currentPlan = freshStatus.commercial_plan_slug || 'free';
        const currentStatus = freshStatus.billing_status || 'none';

        if (currentPlan !== planBeforeCheckout) {
          // Webhook has landed — refresh the billing context and show success
          await billing.refresh();
          toast.success(t('billing.checkout_success'), { id: toastId });
          return;
        }
        // Also detect status change (e.g. none → trialing) even if slug
        // hasn't propagated yet (edge case with fast trial activation)
        if (currentStatus === 'trialing' || currentStatus === 'active') {
          await billing.refresh();
          toast.success(t('billing.checkout_success'), { id: toastId });
          return;
        }
      } catch {
        // Ignore transient fetch errors during polling
      }

      // Webhook hasn't landed yet — retry or enter Phase 2
      if (attempts >= maxAttempts) {
        // ── Phase 2: Verify fallback (v5.7) ─────────────────────────────
        // Polling exhausted without detecting a change.  If we have a
        // session_id, call the verify-checkout endpoint to pull-provision.
        if (sessionId) {
          try {
            const verifyResult = await billingAPI.verifyCheckout(sessionId);
            if (verifyResult.status === 'provisioned' || verifyResult.status === 'already_provisioned') {
              await billing.refresh();
              toast.success(t('billing.checkout_success'), { id: toastId });
              return;
            }
            if (verifyResult.status === 'session_incomplete') {
              toast.info(
                t('billing.checkout_pending', 'Pagamento ricevuto. L\'attivazione del piano è in corso, ricarica tra qualche istante.'),
                { id: toastId, duration: 8000 },
              );
              return;
            }
            // subscription_not_active or unexpected status — fall through to pending
          } catch {
            // Verify call failed — refresh in case webhook landed during the call
            await billing.refresh();
            const finalStatus = await billingAPI.getStatus().catch(() => null);
            const finalPlan = finalStatus?.commercial_plan_slug || 'free';
            const finalBillingStatus = finalStatus?.billing_status || 'none';
            if (finalPlan !== planBeforeCheckout || finalBillingStatus === 'trialing' || finalBillingStatus === 'active') {
              toast.success(t('billing.checkout_success'), { id: toastId });
              return;
            }
          }
        }

        // v5.6/5.7: Honest fallback — show pending message if nothing worked
        await billing.refresh();
        const finalStatus = await billingAPI.getStatus().catch(() => null);
        const finalPlan = finalStatus?.commercial_plan_slug || 'free';
        const finalBillingStatus = finalStatus?.billing_status || 'none';
        if (finalPlan !== planBeforeCheckout || finalBillingStatus === 'trialing' || finalBillingStatus === 'active') {
          toast.success(t('billing.checkout_success'), { id: toastId });
        } else {
          toast.info(
            t('billing.checkout_pending', 'Pagamento ricevuto. L\'attivazione del piano è in corso, ricarica tra qualche istante.'),
            { id: toastId, duration: 8000 },
          );
        }
        return;
      }
      setTimeout(poll, pollInterval);
    };

    // Start polling after a short initial delay (give webhook time to arrive)
    setTimeout(poll, 1500);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Loading state ────────────────────────────────────────────────────────

  if (billing.loading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  const planDetails = billing.currentPlanDetails;
  const planColor = PLAN_COLORS[billing.plan] || 'bg-gray-100 text-gray-700';
  const statusColor = STATUS_COLORS[billing.billingStatus] || STATUS_COLORS.none;
  // Onda 25 — `features` (planDetails.features_display) intentionally
  // dropped here. BillingUsageDashboard renders the authoritative,
  // dynamic per-org entitlement set; the static features_display list
  // is reserved for the public /plans pricing card (marketing copy).

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CreditCard className="h-5 w-5" />
            {t('billing.card_title', 'Piano e Fatturazione')}
          </CardTitle>
          <CardDescription>
            {t('billing.card_desc', 'Gestisci il tuo abbonamento e le informazioni di fatturazione.')}
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-4">
          {/* ══════════════════════════════════════════════════════════════════
              Section A: Subscription Summary  (v5.8 / Onda 9.B — hero card)
              ══════════════════════════════════════════════════════════════════
              Single glance answer: which plan, how much, when does it renew. */}

          {(() => {
            const isYearly = billing.billingInterval === 'year';
            const showPrice = planDetails && planDetails.price_monthly > 0;
            const priceAmount = isYearly && planDetails?.price_yearly
              ? planDetails.price_yearly
              : planDetails?.price_monthly;
            const priceLabel = showPrice
              ? (isYearly && planDetails.price_yearly
                  ? t('billing.price_per_year', { currency: planDetails.currency, amount: priceAmount })
                  : t('billing.price_per_month', { currency: planDetails.currency, amount: priceAmount }))
              : t('billing.free_price', 'Gratis');

            return (
              <div className="rounded-lg border border-gray-200 bg-gradient-to-br from-gray-50 to-white p-4">
                {/* Top: plan name + status badge */}
                <div className="flex flex-wrap items-center gap-2 mb-1">
                  <Crown className="h-4 w-4 text-muted-foreground" />
                  <span className="text-base font-semibold leading-none">
                    {planDetails?.name || billing.plan}
                  </span>
                  <Badge className={`${planColor} border-0 text-[10px] uppercase`}>
                    {billing.plan}
                  </Badge>
                  {/* Onda 14 — distinguish "trial active" from "trial cancelled but
                      still running until trial_end". Without this, a user who
                      cancelled during a trial would still see "In prova" and
                      could think they need to cancel again. */}
                  {billing.isTrialing && billing.cancelAtPeriodEnd ? (
                    <Badge className="bg-orange-100 text-orange-800 border-0 text-[10px]">
                      {t('billing.status_trial_cancelled', 'Prova cancellata')}
                    </Badge>
                  ) : (
                    <Badge className={`${statusColor} border-0 text-[10px]`}>
                      {t(`billing.status_${billing.billingStatus}`, billing.billingStatus)}
                    </Badge>
                  )}
                </div>

                {/* Big price line */}
                <div className="text-2xl font-bold tracking-tight mt-1">
                  {priceLabel}
                </div>

                {/* Subline: trial countdown OR renewal info OR canceled */}
                <div className="text-xs text-muted-foreground mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1">
                  {billing.isTrialing && billing.trialEndsAt && (
                    <span className={billing.cancelAtPeriodEnd ? 'text-orange-700 font-medium' : 'text-blue-700 font-medium'}>
                      {/* Onda 14 — different wording when the trial has been
                          cancelled: emphasizes "you have access until X" rather
                          than "you're in trial". */}
                      {billing.cancelAtPeriodEnd
                        ? t('billing.trial_cancelled_until_with_days', {
                            date: formatDate(billing.trialEndsAt),
                            days: daysRemaining(billing.trialEndsAt),
                            defaultValue: 'Trial cancellato — accesso fino al {{date}} ({{days}} giorni rimanenti)',
                          })
                        : t('billing.trial_until_with_days', {
                            date: formatDate(billing.trialEndsAt),
                            days: daysRemaining(billing.trialEndsAt),
                            defaultValue: 'In prova fino al {{date}} ({{days}} giorni rimanenti)',
                          })}
                    </span>
                  )}
                  {!billing.isTrialing && billing.currentPeriodEnd && !billing.isCanceled && (
                    <span>
                      {billing.cancelAtPeriodEnd
                        ? t('billing.hero_access_until', { date: formatDate(billing.currentPeriodEnd), defaultValue: 'Accesso fino al {{date}} (cancellazione programmata)' })
                        : t('billing.hero_next_renewal', { date: formatDate(billing.currentPeriodEnd), defaultValue: 'Prossimo rinnovo: {{date}}' })}
                    </span>
                  )}
                  {billing.billingInterval && (
                    <>
                      <span>·</span>
                      <span>
                        {isYearly
                          ? t('billing.yearly', 'Annuale')
                          : t('billing.monthly', 'Mensile')}
                      </span>
                    </>
                  )}
                  {billing.isCanceled && (
                    <span className="text-gray-700 font-medium">
                      {t('billing.canceled_message')}
                    </span>
                  )}
                </div>
              </div>
            );
          })()}

          {/* Cancel-at-period-end warning */}
          {billing.cancelAtPeriodEnd && billing.currentPeriodEnd && (
            <div className="rounded-md bg-orange-50 p-3 text-sm text-orange-700 flex items-start gap-2">
              <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
              <span>{t('billing.fallback_to_free')}</span>
            </div>
          )}

          {/* Canceled state */}
          {billing.isCanceled && (
            <div className="rounded-md bg-gray-50 p-3 text-sm text-gray-700 flex items-start gap-2">
              <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
              <div>
                <span>{t('billing.canceled_message')}</span>
                {' '}
                <Button
                  variant="link"
                  size="sm"
                  className="h-auto p-0 text-sm"
                  onClick={() => goToPlans()}
                >
                  {t('billing.resubscribe')}
                </Button>
              </div>
            </div>
          )}

          {/* Past due warning */}
          {billing.isPastDue && (
            <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
              {t('billing.past_due_warning')}
            </div>
          )}

          {/* ══════════════════════════════════════════════════════════════════
              v5.8 / Onda 7: Quota usage + active add-ons dashboard
              ══════════════════════════════════════════════════════════════════
              Inserted between the Subscription Summary (Section A) and the
              legacy Features & Usage block (Section B). Self-loading; the
              parent doesn't manage its data flow. Hidden inline if the
              backend has no usage data to surface (e.g. very fresh free org). */}
          <Separator className="my-2" />
          <BillingUsageDashboard />

          {/* ══════════════════════════════════════════════════════════════════
              Onda 25 — Block B (legacy "INCLUDED FEATURES" from
              planDetails.features_display) and Block C (AI Usage Meters
              from useAiAccess) were REMOVED here. Both rendered the same
              entitlements that BillingUsageDashboard already shows in a
              fully dynamic, per-effective-limit way (metrics with progress
              bars + boolean features with check/lock). The legacy blocks
              read STATIC text from CommercialPlan.features_display and
              never refreshed when the system_admin edited tier limits,
              causing the Settings page to show stale data alongside the
              fresh data — looked like a bug.
              ════════════════════════════════════════════════════════════════
              Section C: Actions
              ══════════════════════════════════════════════════════════════════ */}

          <Separator className="my-2" />

          <div className="flex flex-wrap gap-2 pt-1">
            {billing.canUpgrade && (
              <Button onClick={() => goToPlans()} size="sm">
                <Crown className="mr-2 h-3.5 w-3.5" />
                {billing.isFreePlan
                  ? t('billing.upgrade_cta', 'Passa a un piano a pagamento')
                  : t('billing.change_plan', 'Cambia piano')}
              </Button>
            )}

            {/* Secondary hint for Core users to explore Pro */}
            {billing.plan === 'core' && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => goToPlans()}
                className="text-muted-foreground"
              >
                <Sparkles className="mr-1.5 h-3.5 w-3.5" />
                {t('billing.explore_higher_plans')}
              </Button>
            )}

            {billing.hasStripeCustomer && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleManageBilling}
                disabled={portalLoading}
              >
                {portalLoading ? (
                  <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />
                ) : (
                  <ExternalLink className="mr-2 h-3.5 w-3.5" />
                )}
                {t('billing.manage_billing', 'Gestisci fatturazione')}
              </Button>
            )}

            {/* v5.8 / Onda 9.A.1: Native Reactivate (when cancel pending) */}
            {billing.hasStripeCustomer
              && !billing.isFreePlan
              && billing.cancelAtPeriodEnd && (
              <Button
                variant="default"
                size="sm"
                onClick={handleReactivate}
                disabled={reactivateLoading}
              >
                {reactivateLoading ? (
                  <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />
                ) : (
                  <RotateCcw className="mr-2 h-3.5 w-3.5" />
                )}
                {t('billing.reactivate_cta', 'Riprendi abbonamento')}
              </Button>
            )}

            {/* v5.8 / Onda 9.A.1: Native Cancel (when active, not yet cancel-pending) */}
            {billing.hasStripeCustomer
              && !billing.isFreePlan
              && !billing.cancelAtPeriodEnd
              && !billing.isCanceled && (
              <Button
                variant="ghost"
                size="sm"
                onClick={openCancelModal}
                className="text-red-600 hover:text-red-700 hover:bg-red-50"
              >
                <XCircle className="mr-2 h-3.5 w-3.5" />
                {t('billing.cancel_cta', 'Cancella abbonamento')}
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* ════════════════════════════════════════════════════════════════════
          v5.8 / Onda 9.A.1: Cancel confirmation modal
          ════════════════════════════════════════════════════════════════════ */}
      <Dialog open={cancelModalOpen} onOpenChange={setCancelModalOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <XCircle className="h-5 w-5 text-red-600" />
              {t('billing.cancel_modal_title', 'Cancella abbonamento')}
            </DialogTitle>
            <DialogDescription>
              {t(
                'billing.cancel_modal_desc',
                'Stai per cancellare il tuo abbonamento. Scegli come procedere.',
              )}
            </DialogDescription>
          </DialogHeader>

          {/* Mode picker — v5.8 / Onda 9.T:
              During trial, ONLY the at_period_end option is shown (no
              "cancel immediate"). Backend also enforces this server-side
              by silently forcing at_period_end=True for trialing subs. */}
          {billing.isTrialing ? (
            <div className="rounded-md bg-blue-50 border border-blue-200 px-3 py-3 space-y-1">
              <div className="text-sm font-medium text-blue-900">
                {/* Onda 14 — show the CURRENT plan name, since the trial
                    may have been transferred from a different plan via
                    upgrade/downgrade. e.g. "Sei in prova gratuita di Pro" */}
                {planDetails?.name
                  ? t('billing.cancel_during_trial_title_with_plan', {
                      plan: planDetails.name,
                      defaultValue: 'Sei in prova gratuita di {{plan}}',
                    })
                  : t('billing.cancel_during_trial_title', 'Sei in prova gratuita')}
              </div>
              <div className="text-xs text-blue-800 leading-relaxed">
                {billing.trialEndsAt
                  ? t('billing.cancel_during_trial_body_with_date', {
                      date: formatDate(billing.trialEndsAt),
                      defaultValue: 'Annullando ora, manterrai l\'accesso fino al {{date}} (fine prova), poi tornerai automaticamente a Free senza addebiti. Nessuna fattura.',
                    })
                  : t('billing.cancel_during_trial_body', 'Annullando ora, manterrai l\'accesso fino a fine prova, poi tornerai a Free senza addebiti.')}
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              <label
                className={`flex items-start gap-3 rounded-md border p-3 cursor-pointer ${cancelMode === 'at_period_end' ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:bg-gray-50'}`}
              >
                <input
                  type="radio"
                  name="cancelMode"
                  value="at_period_end"
                  checked={cancelMode === 'at_period_end'}
                  onChange={() => setCancelMode('at_period_end')}
                  className="mt-1"
                />
                <div className="flex-1">
                  <div className="text-sm font-medium">
                    {t('billing.cancel_mode_period_end', 'Cancella a fine periodo')}
                  </div>
                  <div className="text-xs text-muted-foreground mt-0.5">
                    {billing.currentPeriodEnd
                      ? t('billing.cancel_mode_period_end_desc_with_date', {
                          date: formatDate(billing.currentPeriodEnd),
                          defaultValue: 'Mantieni accesso fino al {{date}}, poi torna a Free. Nessun nuovo addebito.',
                        })
                      : t('billing.cancel_mode_period_end_desc', 'Mantieni accesso fino a fine periodo, poi torna a Free.')}
                  </div>
                </div>
              </label>

              <label
                className={`flex items-start gap-3 rounded-md border p-3 cursor-pointer ${cancelMode === 'immediate' ? 'border-red-500 bg-red-50' : 'border-gray-200 hover:bg-gray-50'}`}
              >
                <input
                  type="radio"
                  name="cancelMode"
                  value="immediate"
                  checked={cancelMode === 'immediate'}
                  onChange={() => setCancelMode('immediate')}
                  className="mt-1"
                />
                <div className="flex-1">
                  <div className="text-sm font-medium text-red-700">
                    {t('billing.cancel_mode_immediate', 'Cancella subito')}
                  </div>
                  <div className="text-xs text-muted-foreground mt-0.5">
                    {t('billing.cancel_mode_immediate_desc', 'Accesso revocato immediatamente. Nessun rimborso pro-rata automatico.')}
                  </div>
                </div>
              </label>
            </div>
          )}

          {/* Reason (optional) */}
          <div className="space-y-1">
            <label className="text-xs font-medium text-muted-foreground">
              {t('billing.cancel_reason_label', 'Motivo (opzionale)')}
            </label>
            <Textarea
              value={cancelReason}
              onChange={(e) => setCancelReason(e.target.value)}
              placeholder={t(
                'billing.cancel_reason_placeholder',
                'Ci aiuti a migliorare? Cosa ti ha portato a cancellare?',
              )}
              rows={3}
              maxLength={500}
              disabled={cancelLoading}
            />
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCancelModalOpen(false)}
              disabled={cancelLoading}
            >
              {t('billing.cancel_modal_back', 'Indietro')}
            </Button>
            <Button
              variant={cancelMode === 'immediate' ? 'destructive' : 'default'}
              size="sm"
              onClick={handleConfirmCancel}
              disabled={cancelLoading}
            >
              {cancelLoading ? (
                <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />
              ) : (
                <XCircle className="mr-2 h-3.5 w-3.5" />
              )}
              {cancelMode === 'immediate'
                ? t('billing.cancel_modal_confirm_immediate', 'Conferma cancellazione immediata')
                : t('billing.cancel_modal_confirm_period_end', 'Conferma cancellazione a fine periodo')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
