/**
 * ModuleAccessPaywall — global paywall modal for module/feature access blocks.
 *
 * v5.8 / Onda 9.I — fixes the "errore generico" UX gap identified in
 * BILLING_HOLISTIC_STRESS_TEST_PLAN.md (UXM-01).
 *
 * BEFORE this component existed:
 *   · Solo user clicks "Crea store" → backend returns 403 FEATURE_NOT_AVAILABLE
 *   · Frontend has no specific handler → axios rejects with generic error
 *   · User sees a vague toast or no feedback at all → confusion
 *
 * AFTER:
 *   · Same backend response → axios interceptor in api/client.js dispatches
 *     'billing:module-not-available' or 'billing:feature-not-available'
 *   · This component listens and shows a clear modal explaining what the
 *     user needs to do (upgrade plan, see /plans).
 *
 * Onda 17 — rewritten on top of the Radix Dialog primitive (same as
 * QuotaExceededPaywall) so this paywall stacks correctly when triggered
 * while another Radix Dialog is already open. Without this, the modal
 * would render visually but its buttons would be unclickable due to
 * Radix's pointer-events isolation on portal-sibling DOM nodes.
 *
 * Mounted at App.js root level alongside the other billing banners
 * (BillingStatusBanner, ReadOnlyGraceBanner, QuotaExceededPaywall).
 *
 * Distinct from QuotaExceededPaywall which handles 429 (quota usage hit
 * the limit) — this one handles 403 (the feature is structurally not
 * available on this plan, regardless of usage).
 */
import React, { useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { Lock, ArrowUpCircle } from 'lucide-react';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
} from './ui/dialog';


export default function ModuleAccessPaywall() {
  const { t } = useTranslation(['settings', 'common']);
  const navigateTo = useNavigate();
  const [open, setOpen] = useState(false);
  // 'module' | 'feature' — controls the headline copy
  const [variant, setVariant] = useState('module');
  const [detail, setDetail] = useState({});

  const handleEvent = useCallback((variantType) => (e) => {
    const d = e.detail || {};
    setDetail(d);
    setVariant(variantType);
    setOpen(true);
  }, []);

  useEffect(() => {
    const onModule = handleEvent('module');
    const onFeature = handleEvent('feature');
    window.addEventListener('billing:module-not-available', onModule);
    window.addEventListener('billing:feature-not-available', onFeature);
    return () => {
      window.removeEventListener('billing:module-not-available', onModule);
      window.removeEventListener('billing:feature-not-available', onFeature);
    };
  }, [handleEvent]);

  // ── Build localized copy ────────────────────────────────────────────────
  const featureKey = detail.feature_key || '';
  const metric = featureKey
    ? t(`settings:billing.quota.metric.${featureKey}`, { defaultValue: '' })
    : '';

  const titleKey = variant === 'module'
    ? 'settings:billing.module_paywall.title_module'
    : 'settings:billing.module_paywall.title_feature';
  const title = t(titleKey, { defaultValue: 'Not available on your plan' });

  // Body resolution: feature-specific → generic → backend message → literal
  const body = (() => {
    if (featureKey) {
      const specific = t(
        `settings:billing.module_paywall.body_by_feature.${featureKey}`,
        { metric, defaultValue: '__MISSING__' },
      );
      if (specific !== '__MISSING__') return specific;
    }
    const generic = t('settings:billing.module_paywall.body', {
      metric,
      defaultValue: '__MISSING__',
    });
    if (generic !== '__MISSING__') return generic;
    return detail.message || 'Upgrade your plan to unlock this feature.';
  })();

  const helper = t('settings:billing.module_paywall.helper', {
    defaultValue: '',
  });

  const handleUpgrade = () => {
    setOpen(false);
    navigateTo('/plans');
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-full bg-amber-100 flex-shrink-0">
              <Lock className="h-5 w-5 text-amber-600" aria-hidden />
            </div>
            <DialogTitle className="text-lg font-bold text-gray-900 leading-tight">
              {title}
            </DialogTitle>
          </div>
        </DialogHeader>

        <DialogDescription className="text-sm text-gray-700 leading-relaxed">
          {body}
        </DialogDescription>

        {helper && (
          <p className="text-xs text-gray-500 leading-relaxed">{helper}</p>
        )}

        <div className="space-y-2 pt-2">
          <button
            type="button"
            onClick={handleUpgrade}
            className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-lg bg-gray-900 text-white font-semibold text-sm hover:bg-gray-800 active:bg-black transition-colors min-h-[44px]"
          >
            <ArrowUpCircle className="h-4 w-4" />
            {t('settings:billing.module_paywall.cta_upgrade', { defaultValue: 'View plans' })}
          </button>
          <button
            type="button"
            onClick={() => setOpen(false)}
            className="w-full py-3 px-4 text-sm text-gray-500 hover:text-gray-700 transition-colors min-h-[44px]"
          >
            {t('common:actions.close', { defaultValue: 'Close' })}
          </button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
