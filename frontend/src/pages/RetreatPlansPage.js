/**
 * RetreatPlansPage — pagina piani del verticale ritiri (Blocco B, 4/7/2026).
 *
 * Sostituisce la matrice legacy AFianco per le org su piani retreat_*:
 * due card (Gratis / Pro) con "cosa è incluso" leggibile e la FEE
 * PIATTAFORMA in evidenza, dichiarata SEPARATA dalle commissioni Stripe
 * (decisione founder: trasparenza totale — Stripe applica le sue
 * commissioni di processing sull'account connesso, noi la nostra fee).
 *
 * I bullet vengono dal catalogo (plan.features_display → chiavi i18n),
 * la fee da plan.transaction_fee_percent: cambiare piano/fee dal seed
 * aggiorna la pagina senza redeploy frontend.
 */
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { AppLayout, Header } from '../components/Layout';
import { Button } from '../components/ui/button';
import { Check, Loader2, ArrowLeft, Sparkles, Percent } from 'lucide-react';
import { toast } from 'sonner';
import { billingAPI } from '../api/billing';
import { useBilling } from '../hooks/useBilling';

const STRIPE_FEE_ESTIMATE = (amount) => amount * 0.015 + 0.25; // carte EU

export default function RetreatPlansPage() {
  const { t } = useTranslation('settings');
  const navigate = useNavigate();
  const {
    plans, plan: currentPlan, billingEnabled,
    hasStripeCustomer, isPaid, refresh,
  } = useBilling();

  const [loadingSlug, setLoadingSlug] = useState(null);
  const [interval] = useState('month');

  const retreatPlans = (plans || [])
    .filter((p) => p.slug?.startsWith('retreat_') && !p.is_addon)
    .sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0));
  const isFounding = currentPlan === 'retreat_founding';

  const handleUpgrade = async (plan) => {
    if (!billingEnabled) {
      toast.error(t('billing.stripe_not_configured', 'Stripe non configurato.'));
      return;
    }
    setLoadingSlug(plan.slug);
    try {
      if (hasStripeCustomer && isPaid) {
        await billingAPI.modifySubscription(plan.slug, interval);
        toast.success(t('billing.plan_changed', { plan: plan.name }));
        await refresh();
        setLoadingSlug(null);
        return;
      }
      const { url } = await billingAPI.createCheckoutSession(plan.slug, interval);
      if (url) { window.location.href = url; return; }
      toast.error(t('billing.checkout_no_url', 'Nessun URL di checkout dal server.'));
      setLoadingSlug(null);
    } catch (err) {
      const detail = err.response?.data?.detail;
      toast.error(
        (typeof detail === 'object' ? detail.message : detail)
        || t('billing.checkout_error', 'Errore nel checkout.'),
      );
      setLoadingSlug(null);
    }
  };

  const feeExample = (pct) => {
    const platform = 100 * (pct / 100);
    const stripe = STRIPE_FEE_ESTIMATE(100);
    const net = 100 - platform - stripe;
    const eur = (n) => `${n.toFixed(2).replace('.', ',')} €`;
    return { platform: eur(platform), stripe: eur(stripe), net: eur(net) };
  };

  return (
    <AppLayout>
      <Header
        title={t('billing.retreat.title', 'Piani e commissioni')}
        subtitle={t('billing.retreat.subtitle', 'Semplice: un piano, una fee sul transato. Nessun costo nascosto.')}
      >
        <Button variant="outline" size="sm" onClick={() => navigate('/settings')}>
          <ArrowLeft className="h-4 w-4 mr-1.5" />
          {t('billing.back_to_settings', 'Impostazioni')}
        </Button>
      </Header>

      <div className="p-4 md:p-8 space-y-6 animate-fade-in max-w-4xl mx-auto">

        {isFounding && (
          <div className="rounded-xl border border-amber-300 bg-amber-50 p-4 flex items-start gap-3">
            <Sparkles className="h-5 w-5 text-amber-600 mt-0.5 flex-shrink-0" />
            <div>
              <p className="font-semibold text-amber-900 text-sm">
                {t('billing.retreat.founding_badge', 'Piano Founding attivo')}
              </p>
              <p className="text-sm text-amber-800 mt-0.5">
                {t('billing.retreat.founding_note')}
              </p>
            </div>
          </div>
        )}

        {/* Card piani */}
        <div className="grid gap-5 sm:grid-cols-2">
          {retreatPlans.map((plan) => {
            const isCurrent = plan.slug === currentPlan;
            const isPro = plan.slug === 'retreat_pro';
            const pct = plan.transaction_fee_percent;
            return (
              <div
                key={plan.slug}
                className={`relative rounded-2xl border-2 bg-white p-6 flex flex-col transition-all ${
                  isCurrent
                    ? 'border-gray-900 ring-2 ring-gray-200'
                    : isPro ? 'border-emerald-300 shadow-md' : 'border-gray-200'
                }`}
              >
                {isCurrent && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                    <span className="inline-flex items-center gap-1 bg-gray-900 text-white text-[11px] font-semibold px-3 py-1 rounded-full">
                      <Check className="h-3 w-3" />
                      {t('billing.retreat.current', 'Piano attuale')}
                    </span>
                  </div>
                )}

                <h3 className="font-bold text-lg">{plan.name}</h3>
                <p className="text-sm text-muted-foreground mt-0.5 min-h-[2.5em]">{plan.tagline}</p>

                <div className="mt-3 flex items-baseline gap-1">
                  <span className="text-3xl font-extrabold tracking-tight">
                    {plan.price_monthly === 0
                      ? t('billing.free_label', 'Gratis')
                      : `€${plan.price_monthly}`}
                  </span>
                  {plan.price_monthly > 0 && (
                    <span className="text-sm text-muted-foreground">/{t('billing.month_short', 'mese')}</span>
                  )}
                </div>
                {isPro && plan.price_yearly > 0 && (
                  <p className="text-xs text-muted-foreground mt-1">
                    {t('billing.retreat.yearly_hint', '290 €/anno (2 mesi gratis)')}
                  </p>
                )}

                {/* Fee piattaforma — il cuore del modello */}
                {pct != null && (
                  <div className={`mt-4 rounded-xl p-3 ${isPro ? 'bg-emerald-50 border border-emerald-200' : 'bg-gray-50 border border-gray-200'}`}>
                    <div className="flex items-center gap-2">
                      <Percent className={`h-4 w-4 ${isPro ? 'text-emerald-700' : 'text-gray-600'}`} />
                      <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                        {t('billing.retreat.fee_label', 'Fee piattaforma')}
                      </span>
                    </div>
                    <p className={`text-xl font-bold mt-1 ${isPro ? 'text-emerald-700' : 'text-gray-900'}`}>
                      {t('billing.retreat.fee_value', { pct })}
                    </p>
                    {plan.price_monthly === 0 && (
                      <p className="text-[11px] text-muted-foreground mt-0.5">
                        {t('billing.retreat.fee_free_note', 'Paghi solo quando incassi')}
                      </p>
                    )}
                  </div>
                )}

                {/* Cosa è incluso */}
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mt-5 mb-2">
                  {t('billing.retreat.included_title', 'Cosa è incluso')}
                </p>
                <ul className="space-y-2 flex-1">
                  {(plan.features_display || []).map((key) => (
                    <li key={key} className="flex items-start gap-2 text-sm">
                      <span className="inline-flex items-center justify-center h-4 w-4 rounded-full bg-green-100 mt-0.5 flex-shrink-0">
                        <Check className="h-2.5 w-2.5 text-green-600" />
                      </span>
                      <span>{t(key)}</span>
                    </li>
                  ))}
                </ul>

                {/* CTA */}
                <div className="mt-6">
                  {isCurrent ? (
                    <Button className="w-full" variant="outline" disabled>
                      {t('billing.retreat.current', 'Piano attuale')}
                    </Button>
                  ) : isPro && !isFounding ? (
                    <Button
                      className="w-full font-semibold"
                      onClick={() => handleUpgrade(plan)}
                      disabled={loadingSlug !== null}
                    >
                      {loadingSlug === plan.slug && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                      {t('billing.retreat.cta_upgrade', 'Passa a Pro')}
                    </Button>
                  ) : !isPro && currentPlan === 'retreat_pro' ? (
                    <p className="text-xs text-muted-foreground text-center">
                      {t('billing.retreat.downgrade_hint')}
                    </p>
                  ) : null}
                </div>
              </div>
            );
          })}
        </div>

        {/* Commissioni Stripe — SEPARATE, dichiarate una volta per tutte */}
        <div className="rounded-xl border border-blue-200 bg-blue-50 p-4">
          <p className="font-semibold text-blue-900 text-sm">
            {t('billing.retreat.stripe_fees_title', 'Commissioni Stripe (separate)')}
          </p>
          <p className="text-sm text-blue-800 mt-1 leading-relaxed">
            {t('billing.retreat.stripe_fees_body')}
          </p>
        </div>

        {/* Esempio concreto: 100 € incassati, per ogni piano */}
        <div className="rounded-xl border border-gray-200 bg-white p-4">
          <p className="font-semibold text-sm mb-3">
            {t('billing.retreat.example_title', 'Esempio su un incasso di 100 €')}
          </p>
          <div className="grid gap-4 sm:grid-cols-2">
            {retreatPlans.filter((p) => p.transaction_fee_percent != null).map((plan) => {
              const ex = feeExample(plan.transaction_fee_percent);
              return (
                <div key={plan.slug} className="rounded-lg bg-gray-50 p-3 text-sm">
                  <p className="font-semibold mb-2">{plan.name}</p>
                  <div className="flex justify-between text-muted-foreground">
                    <span>{t('billing.retreat.example_platform', { pct: plan.transaction_fee_percent })}</span>
                    <span>−{ex.platform}</span>
                  </div>
                  <div className="flex justify-between text-muted-foreground mt-1">
                    <span>{t('billing.retreat.example_stripe', 'Commissioni Stripe (≈)')}</span>
                    <span>−{ex.stripe}</span>
                  </div>
                  <div className="flex justify-between font-bold mt-2 pt-2 border-t border-gray-200">
                    <span>{t('billing.retreat.example_net', 'A te restano (≈)')}</span>
                    <span>{ex.net}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
