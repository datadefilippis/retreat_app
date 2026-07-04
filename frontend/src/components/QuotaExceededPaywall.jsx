/**
 * QuotaExceededPaywall — global modal that auto-opens on quota-exceeded events.
 *
 * v5.8 / Onda 9.Q — Hardened for multi-language + multi-platform:
 *   · ALL user-facing strings come from i18n keys (no hardcoded Italian
 *     fallbacks visible to non-IT users).
 *   · defaultValue chains use ENGLISH-style placeholder text only when an
 *     i18n lookup fails — but the keys exist in all 4 locales (it/en/de/fr)
 *     so the fallback should never display in production.
 *
 * Onda 17 — rewritten on top of the Radix Dialog primitive (same as the
 * rest of the app's modals) instead of a raw `<div className="fixed">`.
 * Fixes a stacking bug where the paywall would render visually but its
 * buttons would be unclickable when another Radix Dialog (e.g. the
 * TeamPage Invite dialog) was open underneath: Radix sets
 * `pointer-events: none` on body siblings of its portal, which silently
 * disabled the raw paywall. Using Radix here makes the two modals stack
 * correctly — the latest opened wins, focus trap is shared, ESC and
 * click-outside close handling come for free.
 *
 * Sits next to ModuleAccessPaywall (handles 403 MODULE/FEATURE_NOT_AVAILABLE)
 * and BillingStatusBanner (handles BILLING_TRIAL_EXPIRED / BILLING_PAST_DUE).
 *
 * Mounted at App.js root level — single instance, listens globally.
 */
import React, { useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { AlertCircle, ShoppingBag, ArrowUpCircle } from 'lucide-react';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
} from './ui/dialog';


export default function QuotaExceededPaywall() {
  const { t } = useTranslation(['settings', 'common']);
  const navigateTo = useNavigate();
  const [open, setOpen] = useState(false);
  const [detail, setDetail] = useState({});

  const handleEvent = useCallback((e) => {
    setDetail(e.detail || {});
    setOpen(true);
  }, []);

  useEffect(() => {
    window.addEventListener('billing:quota-exceeded', handleEvent);
    return () => window.removeEventListener('billing:quota-exceeded', handleEvent);
  }, [handleEvent]);

  // ── Build localized copy ────────────────────────────────────────────────
  const featureKey = detail.feature_key || '';
  const used = detail.used ?? detail.current_count ?? 0;
  const limit = detail.limit ?? detail.effective_limit ?? 0;
  const addonSlug = detail.addon_slug;

  const metric = t(`settings:billing.quota.metric.${featureKey}`, {
    defaultValue: featureKey || t('settings:billing.quota.metric.unknown', { defaultValue: 'feature' }),
  });

  const title = t(`settings:billing.quota.title_by_feature.${featureKey}`, {
    metric,
    defaultValue: t('settings:billing.quota.exceeded_title', { defaultValue: 'Limit reached' }),
  });

  const body = t(`settings:billing.quota.body_by_feature.${featureKey}`, {
    used,
    limit,
    metric,
    defaultValue: t('settings:billing.quota.exceeded_body', {
      used,
      limit,
      metric,
      defaultValue: detail.message || `${used}/${limit} ${metric}`,
    }),
  });

  const helper = addonSlug
    ? t('settings:billing.quota.exceeded_helper_with_addon', {
        defaultValue: t('settings:billing.quota.exceeded_helper', {
          defaultValue: '',
        }),
      })
    : t('settings:billing.quota.exceeded_helper', { defaultValue: '' });

  const addonLabel = addonSlug
    ? t(`settings:billing.quota.addon_cta.${addonSlug}`, {
        defaultValue: t('settings:billing.quota.cta_buy_addon', { defaultValue: 'Buy add-on pack' }),
      })
    : null;

  const handleBuyAddon = () => {
    setOpen(false);
    navigateTo('/plans#addons');
  };

  const handleUpgrade = () => {
    setOpen(false);
    navigateTo('/plans');
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-full bg-red-100 flex-shrink-0">
              <AlertCircle className="h-5 w-5 text-red-600" aria-hidden />
            </div>
            <DialogTitle className="text-lg font-bold text-gray-900 leading-tight">
              {title}
            </DialogTitle>
          </div>
        </DialogHeader>

        {/* Usage stat */}
        {(used > 0 || limit > 0) && (
          <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-md bg-gray-100 text-xs font-medium text-gray-700 self-start">
            <span>{used}</span>
            <span className="text-gray-400">/</span>
            <span>{limit}</span>
            <span className="text-gray-500">{metric}</span>
          </div>
        )}

        {/* Body */}
        <DialogDescription className="text-sm text-gray-700 leading-relaxed">
          {body}
        </DialogDescription>

        {helper && (
          <p className="text-xs text-gray-500 leading-relaxed">{helper}</p>
        )}

        {/* CTAs — min-h 44px for touch targets */}
        <div className="space-y-2 pt-2">
          {addonSlug && (
            <button
              type="button"
              onClick={handleBuyAddon}
              className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-lg bg-gray-900 text-white font-semibold text-sm hover:bg-gray-800 active:bg-black transition-colors min-h-[44px]"
            >
              <ShoppingBag className="h-4 w-4" />
              {addonLabel}
            </button>
          )}
          <button
            type="button"
            onClick={handleUpgrade}
            className={`w-full flex items-center justify-center gap-2 py-3 px-4 rounded-lg font-semibold text-sm transition-colors min-h-[44px] ${
              addonSlug
                ? 'border-2 border-gray-900 text-gray-900 hover:bg-gray-50 active:bg-gray-100'
                : 'bg-gray-900 text-white hover:bg-gray-800 active:bg-black'
            }`}
          >
            <ArrowUpCircle className="h-4 w-4" />
            {t('settings:billing.quota.cta_upgrade_plan', { defaultValue: 'Upgrade plan' })}
          </button>
          <button
            type="button"
            onClick={() => setOpen(false)}
            className="w-full py-3 px-4 text-sm text-gray-500 hover:text-gray-700 transition-colors min-h-[44px]"
          >
            {t('common:actions.maybe_later', { defaultValue: 'Maybe later' })}
          </button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
