/**
 * QuotaExceededBanner — global quota limit notification.
 *
 * Listens for 'billing:quota-exceeded' custom events dispatched by the
 * Axios interceptor when a 429 with code QUOTA_EXCEEDED is received.
 *
 * v5.8 / Onda 9.M — i18n priority over backend message.
 *   The backend ships a localized-Italian-only `detail.message`. Without
 *   this fix, an English/German/French admin would see Italian text in the
 *   banner. Now we:
 *     1. Read `detail.feature_key` (e.g. "products", "orders_monthly", ...)
 *     2. Look up the localized metric label via `billing.quota.metric.<key>`
 *     3. Render the standard `billing.quota.exceeded_body` template with
 *        {used} / {limit} / {metric} interpolation in the user's locale
 *     4. Fall back to backend `detail.message` only if the i18n lookup fails
 *        (unknown feature_key — defensive default)
 *
 * Follows the same pattern as ReadOnlyGraceBanner for consistency.
 * Works for ALL quota types (data_rows, chat, digest, products, orders,
 * stores_max, team_members, etc.).
 */
import React, { useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { AlertTriangle, X, ArrowUpCircle } from 'lucide-react';

export function QuotaExceededBanner({ onUpgradeClick }) {
  const { t } = useTranslation(['common', 'settings']);
  const [visible, setVisible] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  const [detail, setDetail] = useState({});

  const handleEvent = useCallback((e) => {
    setDetail(e.detail || {});
    setDismissed(false);
    setVisible(true);
  }, []);

  useEffect(() => {
    window.addEventListener('billing:quota-exceeded', handleEvent);
    return () => window.removeEventListener('billing:quota-exceeded', handleEvent);
  }, [handleEvent]);

  if (!visible || dismissed) return null;

  // ── Build localized message (i18n priority, backend message as fallback) ──
  // detail shape per backend contract:
  //   { code:"QUOTA_EXCEEDED", feature_key:"products", module_key:"...",
  //     message:"...", used:50, limit:50, effective_limit:50, addon_slug:"..." }
  const featureKey = detail.feature_key || '';
  const used = detail.used ?? detail.current_count ?? 0;
  const limit = detail.limit ?? detail.effective_limit ?? 0;

  // Localized metric label (e.g. "products" → "prodotti" / "Produkte" / etc.)
  // If the feature_key is unknown to i18n, use the raw key as the metric
  // (better than nothing — the user sees the technical name).
  const metric = t(`settings:billing.quota.metric.${featureKey}`, {
    defaultValue: featureKey || 'feature',
  });

  // Build the message: "Hai raggiunto la quota mensile di 50 prodotti (50/50)."
  // The exceeded_body template lives in settings.billing.quota.exceeded_body.
  const localizedMessage = t('settings:billing.quota.exceeded_body', {
    used,
    limit,
    metric,
    defaultValue: detail.message ||
      t('common:quota.banner_default', 'Hai raggiunto il limite del tuo piano. Aggiorna per continuare.'),
  });

  return (
    <div className="bg-orange-50 border-b border-orange-200 px-4 py-2.5 flex items-center justify-between text-sm text-orange-800 animate-fade-in">
      <div className="flex items-center gap-2">
        <AlertTriangle className="h-4 w-4 flex-shrink-0 text-orange-600" />
        <span className="font-medium">
          {t('settings:billing.quota.exceeded_title', 'Limite raggiunto', {
            defaultValue: t('common:quota.banner_title', 'Limite raggiunto'),
          })}
        </span>
        <span className="hidden sm:inline">—</span>
        <span className="hidden sm:inline text-orange-700">{localizedMessage}</span>
      </div>
      <div className="flex items-center gap-2">
        {onUpgradeClick && (
          <button
            onClick={onUpgradeClick}
            className="flex items-center gap-1 bg-orange-600 text-white px-3 py-1 rounded-md text-xs font-medium hover:bg-orange-700 transition-colors"
          >
            <ArrowUpCircle className="h-3.5 w-3.5" />
            {t('common:quota.banner_upgrade', 'Aggiorna il piano')}
          </button>
        )}
        <button
          onClick={() => setDismissed(true)}
          className="ml-1 text-orange-500 hover:text-orange-700"
          aria-label={t('common:quota.banner_dismiss', 'Chiudi')}
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

export default QuotaExceededBanner;
