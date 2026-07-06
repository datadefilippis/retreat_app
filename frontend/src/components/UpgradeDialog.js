/**
 * UpgradeDialog v5.8 -- Stripe-integrated plan selection.
 *
 * Shows the commercial plan catalog and either:
 *   - Redirects to Stripe Checkout for self-serve plans
 *   - Shows a "contact sales" CTA for enterprise
 *
 * v5.5: Handles 409 duplicate-subscription responses from the backend
 * by automatically redirecting to the Stripe Customer Portal when the
 * org already has an active subscription.
 *
 * v5.8: Adds explicit user feedback (info toast + 1.5s delay) before
 * portal redirect on 409. Fixes CTA labels for paid users upgrading
 * ("Gestisci abbonamento" instead of misleading "Abbonati").
 * Passes explicit return_url on all portal session calls.
 *
 * Props: open, onOpenChange (controlled dialog).
 */
import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from './ui/dialog';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Check, Sparkles, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { billingAPI } from '../api/billing';
import { useBilling } from '../hooks/useBilling';

const BADGE_COLORS = {
  free: 'bg-gray-100 text-gray-700',
  starter: 'bg-emerald-100 text-emerald-700',
  core: 'bg-blue-100 text-blue-700',
  pro: 'bg-violet-100 text-violet-700',
  enterprise: 'bg-amber-100 text-amber-700',
};

const PLAN_TIERS = { free: 0, starter: 1, core: 2, pro: 3, enterprise: 4 };

export const UpgradeDialog = ({ open, onOpenChange }) => {
  const { t } = useTranslation('settings');
  const { plans, plan: currentPlan, billingEnabled, isPaid, hasStripeCustomer, hasHadTrial } = useBilling();
  const [loadingSlug, setLoadingSlug] = useState(null);
  const [interval, setInterval] = useState('month');
  const [error, setError] = useState(null);
  const [confirmPlan, setConfirmPlan] = useState(null); // plan object pending confirmation

  const isDowngrade = (targetSlug) =>
    (PLAN_TIERS[targetSlug] || 0) < (PLAN_TIERS[currentPlan] || 0);

  const handleSelect = async (planSlug) => {
    if (planSlug === currentPlan) return;
    if (planSlug === 'free') return;
    setError(null);

    const selectedPlan = plans.find((p) => p.slug === planSlug);

    // Enterprise: contact sales
    if (selectedPlan && !selectedPlan.is_self_serve) {
      window.location.href = 'mailto:info@aurya.life?subject=Piano%20Enterprise%20Aurya';
      return;
    }

    if (!billingEnabled) {
      setError(t('billing.stripe_not_configured', 'Stripe non configurato. Contatta il supporto.'));
      return;
    }

    // ── Path A: User has active Stripe subscription → show confirmation first ──
    if (hasStripeCustomer && isPaid) {
      setConfirmPlan(selectedPlan);
      return;
    }

    // ── Path B: Free user, no Stripe sub → create new checkout ────────────
    setLoadingSlug(planSlug);
    try {
      const { url } = await billingAPI.createCheckoutSession(planSlug, interval);
      if (url) window.location.href = url;
    } catch (err) {
      const detail = err.response?.data?.detail;
      const errorMsg = typeof detail === 'object' ? detail.message : detail;
      setError(errorMsg || t('billing.checkout_error', 'Errore nella creazione del checkout.'));
      setLoadingSlug(null);
    }
  };

  const handleConfirmModify = async () => {
    if (!confirmPlan) return;
    const planSlug = confirmPlan.slug;
    setLoadingSlug(planSlug);
    setError(null);

    try {
      await billingAPI.modifySubscription(planSlug, interval);
      toast.success(
        t('billing.plan_changed', { plan: confirmPlan.name }) ||
        `Piano cambiato a ${confirmPlan.name}`
      );
      setConfirmPlan(null);
      onOpenChange(false);
      setTimeout(() => window.location.reload(), 2000);
    } catch (err) {
      const detail = err.response?.data?.detail;
      const code = typeof detail === 'object' ? detail.code : '';
      const errorMsg = typeof detail === 'object' ? detail.message : detail;

      if (code === 'no_subscription') {
        try {
          const { url } = await billingAPI.createCheckoutSession(planSlug, interval);
          if (url) window.location.href = url;
          return;
        } catch (e2) {
          setError(t('billing.checkout_error', 'Errore nella creazione del checkout.'));
        }
      } else if (code === 'rate_limited') {
        setError(errorMsg || t('billing.modify_rate_limited', 'Hai cambiato piano di recente. Riprova tra qualche ora.'));
      } else {
        setError(errorMsg || t('billing.modify_error', 'Errore nel cambio piano.'));
      }
      setLoadingSlug(null);
    }
  };

  const formatPrice = (plan) => {
    if (plan.price_monthly === 0) return t('billing.free_label', 'Gratis');
    if (interval === 'year' && plan.price_yearly) {
      return t('billing.price_per_year', { currency: plan.currency, amount: plan.price_yearly });
    }
    return t('billing.price_per_month', { currency: plan.currency, amount: plan.price_monthly });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 font-heading">
            <Sparkles className="h-5 w-5 text-primary" />
            {t('billing.upgrade_title', 'Scegli il piano giusto per te')}
          </DialogTitle>
          <DialogDescription>
            {t('billing.upgrade_desc', 'Sblocca tutte le funzionalita di Aurya per la tua organizzazione.')}
          </DialogDescription>
        </DialogHeader>

        {/* Interval toggle */}
        <div className="flex justify-center gap-2 py-2">
          <Button
            variant={interval === 'month' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setInterval('month')}
          >
            {t('billing.monthly', 'Mensile')}
          </Button>
          <Button
            variant={interval === 'year' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setInterval('year')}
          >
            {t('billing.yearly', 'Annuale')}
            <Badge className="ml-1 bg-green-100 text-green-700 border-0 text-[10px]">
              -17%
            </Badge>
          </Button>
        </div>

        {/* Plan cards */}
        <div className="grid gap-3 sm:grid-cols-2">
          {plans.map((plan) => {
            const isCurrent = plan.slug === currentPlan;
            const badgeColor = BADGE_COLORS[plan.slug] || 'bg-gray-100 text-gray-700';
            const features = plan.features_display || [];

            return (
              <div
                key={plan.slug}
                className={`rounded-lg border p-4 ${
                  isCurrent ? 'border-primary ring-1 ring-primary' : 'border-border'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <Badge className={`${badgeColor} border-0 text-xs font-semibold`}>
                    {plan.name}
                  </Badge>
                  {isCurrent && (
                    <Badge variant="outline" className="text-[10px]">
                      {t('billing.current_plan', 'Piano attuale')}
                    </Badge>
                  )}
                </div>

                <div className="text-lg font-bold mb-1">{formatPrice(plan)}</div>

                {plan.tagline && (
                  <p className="text-xs text-muted-foreground mb-3">{plan.tagline}</p>
                )}

                <ul className="space-y-1 mb-4">
                  {features.map((feat, i) => (
                    <li key={i} className="flex items-start gap-1.5 text-xs text-muted-foreground">
                      <Check className="h-3 w-3 mt-0.5 text-green-600 flex-shrink-0" />
                      <span>{t(feat, feat)}</span>
                    </li>
                  ))}
                </ul>

                <Button
                  className="w-full"
                  variant={isCurrent || plan.slug === 'free' ? 'outline' : 'default'}
                  size="sm"
                  disabled={isCurrent || plan.slug === 'free' || loadingSlug !== null}
                  onClick={() => handleSelect(plan.slug)}
                >
                  {loadingSlug === plan.slug && (
                    <Loader2 className="mr-2 h-3 w-3 animate-spin" />
                  )}
                  {isCurrent
                    ? t('billing.current_plan', 'Piano attuale')
                    : plan.slug === 'free'
                    ? t('billing.free_label', 'Gratis')
                    : plan.is_self_serve === false
                    ? t('billing.contact_sales', 'Contattaci')
                    : isPaid && hasStripeCustomer && isDowngrade(plan.slug)
                    ? t('billing.downgrade_to', 'Passa a {{plan}}', { plan: plan.name })
                    : isPaid && hasStripeCustomer
                    ? t('billing.upgrade_to', 'Passa a {{plan}}', { plan: plan.name })
                    : plan.trial_days > 0 && !hasHadTrial
                    ? t('billing.start_trial', 'Prova gratis {{days}} giorni', { days: plan.trial_days })
                    : t('billing.subscribe', 'Abbonati')}
                </Button>
              </div>
            );
          })}
        </div>

        {/* ── Confirmation panel for plan changes ──────────────────────── */}
        {confirmPlan && (
          <div className="border border-amber-200 bg-amber-50 rounded-lg p-4 mt-2">
            <h4 className="font-semibold text-sm mb-2">
              {isDowngrade(confirmPlan.slug)
                ? t('billing.confirm_downgrade_title', 'Conferma downgrade')
                : t('billing.confirm_upgrade_title', 'Conferma upgrade')}
            </h4>
            <p className="text-sm text-muted-foreground mb-1">
              {t('billing.confirm_from', 'Piano attuale')}: <strong>{plans.find(p => p.slug === currentPlan)?.name || currentPlan}</strong>
              {' → '}
              <strong>{confirmPlan.name}</strong>
            </p>
            <p className="text-sm text-muted-foreground mb-1">
              {t('billing.confirm_price', 'Nuovo prezzo')}: <strong>{interval === 'year' && confirmPlan.price_yearly ? `€${confirmPlan.price_yearly}/anno` : `€${confirmPlan.price_monthly}/mese`}</strong>
            </p>
            <p className="text-xs text-muted-foreground mb-3">
              {isDowngrade(confirmPlan.slug)
                ? t('billing.confirm_downgrade_note', 'Riceverai un credito proporzionale per il periodo non utilizzato del piano attuale.')
                : t('billing.confirm_upgrade_note', 'Ti verrà addebitata la differenza proporzionale per il periodo corrente.')}
            </p>
            <div className="flex gap-2">
              <Button
                size="sm"
                onClick={handleConfirmModify}
                disabled={loadingSlug !== null}
              >
                {loadingSlug && <Loader2 className="mr-2 h-3 w-3 animate-spin" />}
                {t('billing.confirm_change', 'Conferma cambio piano')}
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => { setConfirmPlan(null); setError(null); }}
                disabled={loadingSlug !== null}
              >
                {t('billing.cancel', 'Annulla')}
              </Button>
            </div>
          </div>
        )}

        {error && (
          <p className="text-sm text-destructive text-center mt-2">{error}</p>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default UpgradeDialog;
