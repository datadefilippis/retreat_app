/**
 * BillingStatusBanner — v6.0 billing enforcement UX layer.
 *
 * Listens for 'billing:trial-expired' and 'billing:past-due' custom events
 * dispatched by the Axios interceptor when the v6.0 billing gate returns
 * 403 with BILLING_TRIAL_EXPIRED or BILLING_PAST_DUE.
 *
 * Displays a persistent (non-dismissible) top banner with an actionable CTA:
 *   - Trial expired  -> "Subscribe now" opens UpgradeDialog
 *   - Past due blocked -> "Update payment" opens Stripe portal
 *
 * Non-dismissible because these are blocking states — the user cannot use
 * premium features until the billing issue is resolved.
 *
 * Precedence: when this banner is visible, the softer ReadOnlyGraceBanner
 * is suppressed (this banner already covers the blocking state).
 */
import React, { useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { AlertCircle, Loader2 } from 'lucide-react';
import { billingAPI } from '../api/billing';
import { useNavigate } from 'react-router-dom';

/**
 * @param {Object} props
 * @param {function} [props.onVisible] — called with true/false when banner visibility changes.
 *   Used by parent to suppress lower-priority banners.
 */
export function BillingStatusBanner({ onVisible }) {
  const { t } = useTranslation('settings');
  // Which blocking state is active (null = none, 'trial_expired' | 'past_due')
  const [activeState, setActiveState] = useState(null);
  const navigateTo = useNavigate();
  const [portalLoading, setPortalLoading] = useState(false);

  useEffect(() => {
    const handleTrialExpired = () => setActiveState('trial_expired');
    const handlePastDue = () => setActiveState('past_due');

    window.addEventListener('billing:trial-expired', handleTrialExpired);
    window.addEventListener('billing:past-due', handlePastDue);
    return () => {
      window.removeEventListener('billing:trial-expired', handleTrialExpired);
      window.removeEventListener('billing:past-due', handlePastDue);
    };
  }, []);

  // Notify parent of visibility changes (for banner precedence)
  useEffect(() => {
    onVisible?.(activeState !== null);
  }, [activeState, onVisible]);

  const handleUpdatePayment = useCallback(async () => {
    setPortalLoading(true);
    try {
      const { url } = await billingAPI.createPortalSession();
      if (url) window.location.href = url;
    } catch {
      // Portal creation failed — fall back to settings page
      window.location.href = '/settings';
    } finally {
      setPortalLoading(false);
    }
  }, []);

  if (!activeState) return null;

  const isTrialExpired = activeState === 'trial_expired';

  return (
    <>
      <div
        role="alert"
        // v5.8 / Onda 9.R — sticky top + z-[55] so the banner sits ABOVE the
        // sidebar (z-50) and the sticky header (z-30) when both are visible.
        // Sticky (vs fixed) keeps the banner in normal flow so it pushes
        // content down instead of overlapping it.
        className="sticky top-0 bg-red-50 border-b border-red-200 px-4 py-2.5 flex items-center justify-between text-sm text-red-800"
        style={{ zIndex: 55 }}
      >
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <AlertCircle className="h-4 w-4 flex-shrink-0" />
          <span>
            {isTrialExpired
              ? t(
                  'billing.trial_expired_banner',
                  'Il periodo di prova e\' terminato. Sottoscrivi un piano per continuare a usare le funzionalita\' premium.'
                )
              : t(
                  'billing.past_due_expired_banner',
                  'Il pagamento non e\' riuscito e il periodo di fatturazione e\' scaduto. Aggiorna il metodo di pagamento per ripristinare l\'accesso.'
                )}
          </span>
        </div>

        <div className="flex-shrink-0 ml-4">
          {isTrialExpired ? (
            <button
              onClick={() => navigateTo('/plans')}
              className="inline-flex items-center gap-1 rounded-md bg-red-700 px-3 py-1 text-xs font-semibold text-white hover:bg-red-800 transition-colors"
            >
              {t('billing.subscribe_now', 'Sottoscrivi ora')}
            </button>
          ) : (
            <button
              onClick={handleUpdatePayment}
              disabled={portalLoading}
              className="inline-flex items-center gap-1 rounded-md bg-red-700 px-3 py-1 text-xs font-semibold text-white hover:bg-red-800 transition-colors disabled:opacity-60"
            >
              {portalLoading && <Loader2 className="h-3 w-3 animate-spin" />}
              {t('billing.update_payment', 'Aggiorna pagamento')}
            </button>
          )}
        </div>
      </div>

    </>
  );
}

export default BillingStatusBanner;
