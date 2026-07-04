/**
 * UpgradePaywall — standardised paywall modal triggered by 429 quota errors.
 *
 * Onda 6 (v5.8). Replaces the generic toast / inline error that pages
 * showed when a feature returned 429. Visually emphatic but not blocking
 * (user can dismiss to read the error in context); offers two CTAs:
 *
 *   1. "Buy pack"     — when an add-on can fix the specific quota
 *   2. "Upgrade plan" — always available, deeper fix
 *
 * Props:
 *   open           bool      — modal visibility (controlled)
 *   onClose        func      — close handler
 *   metric         string    — metric key (matches `billing.quota.metric.<metric>`)
 *   used, limit    number    — usage context (passed to copy)
 *   addonSlug      string    — optional addon to suggest
 *   onAddonClick   func      — handler when user wants to buy the addon
 *                              (typically navigates to /plans#addons or opens
 *                              the dedicated addon checkout flow)
 *   onUpgradeClick func      — handler when user wants to upgrade plan
 *                              (typically navigates to /plans)
 *
 * Globally listenable via the existing `billing:quota-exceeded` axios event.
 * For pages that want the rich paywall (vs the generic banner), wrap their
 * 429 handler to call this component locally.
 */
import React, { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { AlertCircle, X, ShoppingBag, ArrowUpCircle } from 'lucide-react';


export default function UpgradePaywall({
  open,
  onClose,
  metric,
  used,
  limit,
  addonSlug,
  onAddonClick,
  onUpgradeClick,
}) {
  const { t } = useTranslation('settings');

  // Close on ESC for keyboard a11y
  useEffect(() => {
    if (!open) return undefined;
    const handler = (e) => {
      if (e.key === 'Escape') onClose?.();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [open, onClose]);

  if (!open) return null;

  const metricLabel = t(`billing.quota.metric.${metric}`, { defaultValue: metric });

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="upgrade-paywall-title"
      // v5.8 / Onda 9.P — coherent stacking with other paywalls (above z-50 dialogs)
      className="fixed inset-0 flex items-end sm:items-center justify-center p-0 sm:p-4 bg-black/40"
      style={{ zIndex: 60 }}
      onClick={onClose}
    >
      <div
        className="bg-white rounded-t-2xl sm:rounded-xl shadow-xl w-full max-w-md p-6 animate-in slide-in-from-bottom-4 sm:slide-in-from-bottom-0"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-full bg-red-100">
              <AlertCircle className="h-5 w-5 text-red-600" aria-hidden />
            </div>
            <h2 id="upgrade-paywall-title" className="text-lg font-bold text-gray-900">
              {t('billing.quota.exceeded_title', {
                metric: metricLabel,
                defaultValue: 'Limit reached',
              })}
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-md hover:bg-gray-100 text-gray-500"
            aria-label={t('common.close', { defaultValue: 'Close' })}
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Body */}
        <p className="text-sm text-gray-700 mb-4">
          {t('billing.quota.exceeded_body', {
            used,
            limit,
            metric: metricLabel,
            defaultValue: `You've reached your monthly quota of ${limit} ${metricLabel}.`,
          })}
        </p>

        <p className="text-xs text-gray-500 mb-5">
          {t('billing.quota.exceeded_helper', {
            defaultValue: 'Choose how to extend your quota: buy a one-shot add-on pack or upgrade to the next plan.',
          })}
        </p>

        {/* CTAs */}
        <div className="space-y-2">
          {addonSlug && onAddonClick && (
            <button
              type="button"
              onClick={() => {
                onAddonClick(addonSlug);
                onClose?.();
              }}
              className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg bg-gray-900 text-white font-semibold text-sm hover:bg-gray-800 transition-colors"
            >
              <ShoppingBag className="h-4 w-4" />
              {t('billing.quota.cta_buy_addon', { defaultValue: 'Buy add-on pack' })}
            </button>
          )}
          {onUpgradeClick && (
            <button
              type="button"
              onClick={() => {
                onUpgradeClick();
                onClose?.();
              }}
              className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg border-2 border-gray-900 text-gray-900 font-semibold text-sm hover:bg-gray-50 transition-colors"
            >
              <ArrowUpCircle className="h-4 w-4" />
              {t('billing.quota.cta_upgrade_plan', { defaultValue: 'Upgrade plan' })}
            </button>
          )}
          <button
            type="button"
            onClick={onClose}
            className="w-full py-2.5 px-4 text-sm text-gray-500 hover:text-gray-700 transition-colors"
          >
            {t('common.maybe_later', { defaultValue: 'Maybe later' })}
          </button>
        </div>
      </div>
    </div>
  );
}
