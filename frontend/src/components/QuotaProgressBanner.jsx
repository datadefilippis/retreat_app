/**
 * QuotaProgressBanner — inline quota progress indicator with upsell CTA.
 *
 * Onda 6 (v5.8). Shown ABOVE specific feature pages (AI chat page, datasets
 * page, orders/storefront admin) to surface "X/Y this month" with a tactful
 * upgrade nudge when the merchant approaches a limit.
 *
 * Unlike `QuotaExceededBanner` (which reacts to 429 axios events globally),
 * this component is opt-in per page and READS the current usage from a prop.
 * The page that mounts it is responsible for fetching usage. This keeps the
 * data flow explicit and lets each page choose its own loading strategy.
 *
 * Props:
 *   metric        string  — i18n key suffix (chat / orders_monthly / data_rows / ...)
 *   used          number  — current usage this period
 *   limit         number  — effective limit (-1 = unlimited)
 *   addonSlug     string  — optional slug of the cheapest addon to suggest
 *   onAddonClick  func    — handler for the "Buy pack" CTA
 *   onUpgradeClick func   — handler for the "Upgrade plan" CTA
 *   className     string  — extra wrapper classes (e.g. "mb-4")
 *
 * The banner is hidden entirely when:
 *   · limit === -1                              (unlimited, nothing to warn)
 *   · limit ===  0                              (feature off — different banner)
 *   · used / limit < 0.6                        (well under the warn-zone)
 *
 * Three visual states based on usage ratio:
 *   60–79%   "informational" (gray bar, no CTAs visible)
 *   80–99%   "approaching"   (amber bar + upsell CTAs)
 *   100%+    "exceeded"      (red bar + upsell CTAs + emphatic copy)
 *
 * Translation keys live in `settings:billing.quota.*` (added in Onda 6
 * frontend i18n update). Falls back to inline English if a key is missing.
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import { AlertTriangle, AlertCircle, ArrowUpCircle } from 'lucide-react';


function _stateForRatio(ratio) {
  if (ratio >= 1) return 'exceeded';
  if (ratio >= 0.8) return 'approaching';
  if (ratio >= 0.6) return 'info';
  return null;  // hidden
}


function _stateClasses(state) {
  switch (state) {
    case 'exceeded':
      return {
        wrapper: 'bg-red-50 border-red-200 text-red-900',
        bar: 'bg-red-500',
        icon: <AlertCircle className="h-5 w-5 flex-shrink-0 text-red-600" aria-hidden />,
      };
    case 'approaching':
      return {
        wrapper: 'bg-amber-50 border-amber-200 text-amber-900',
        bar: 'bg-amber-500',
        icon: <AlertTriangle className="h-5 w-5 flex-shrink-0 text-amber-600" aria-hidden />,
      };
    default:  // info
      return {
        wrapper: 'bg-gray-50 border-gray-200 text-gray-700',
        bar: 'bg-gray-500',
        icon: <ArrowUpCircle className="h-5 w-5 flex-shrink-0 text-gray-500" aria-hidden />,
      };
  }
}


export default function QuotaProgressBanner({
  metric,
  used = 0,
  limit = 0,
  addonSlug,
  onAddonClick,
  onUpgradeClick,
  className = '',
}) {
  const { t } = useTranslation('settings');

  // Hide for unlimited / disabled / well-under-warn
  if (limit === -1) return null;
  if (limit <= 0) return null;
  const ratio = used / limit;
  const state = _stateForRatio(ratio);
  if (!state) return null;

  const cls = _stateClasses(state);

  // Translatable metric label — fall back to the key itself if missing.
  // Convention: settings.json holds `billing.quota.metric.<metric>`.
  const metricLabel = t(
    `billing.quota.metric.${metric}`,
    { defaultValue: metric },
  );

  // Title varies by state. Body always shows X/Y.
  const titleKey =
    state === 'exceeded'
      ? 'billing.quota.exceeded_title'
      : state === 'approaching'
        ? 'billing.quota.warning_title'
        : 'billing.quota.info_title';

  const title = t(titleKey, {
    metric: metricLabel,
    defaultValue:
      state === 'exceeded' ? 'Limit reached'
      : state === 'approaching' ? 'Approaching the limit'
      : 'Usage update',
  });

  const usageLabel = t('billing.quota.current_usage_label', {
    used,
    limit,
    metric: metricLabel,
    defaultValue: `${used}/${limit} ${metricLabel} this month`,
  });

  const showCtas = state !== 'info';

  return (
    <div
      role="status"
      className={`border rounded-lg p-3 sm:p-4 flex items-start gap-3 ${cls.wrapper} ${className}`.trim()}
    >
      <div className="pt-0.5">{cls.icon}</div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <div className="font-medium text-sm">{title}</div>
          <div className="text-xs tabular-nums opacity-80">{usageLabel}</div>
        </div>

        {/* progress bar */}
        <div className="mt-2 h-1.5 rounded-full bg-white/50 overflow-hidden">
          <div
            className={`h-full ${cls.bar} transition-all duration-300`}
            style={{ width: `${Math.min(100, Math.round(ratio * 100))}%` }}
          />
        </div>

        {showCtas && (
          <div className="mt-3 flex flex-wrap gap-2">
            {addonSlug && onAddonClick && (
              <button
                type="button"
                onClick={onAddonClick}
                className="text-xs font-semibold px-3 py-1.5 rounded-md bg-white border border-current hover:bg-gray-50 transition-colors"
              >
                {t('billing.quota.cta_buy_addon', { defaultValue: 'Buy add-on pack' })}
              </button>
            )}
            {onUpgradeClick && (
              <button
                type="button"
                onClick={onUpgradeClick}
                className="text-xs font-semibold px-3 py-1.5 rounded-md bg-gray-900 text-white hover:bg-gray-800 transition-colors"
              >
                {t('billing.quota.cta_upgrade_plan', { defaultValue: 'Upgrade plan' })}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
