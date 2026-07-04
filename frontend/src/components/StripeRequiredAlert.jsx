/**
 * StripeRequiredAlert — inline warning that surfaces next to the
 * "transaction_mode" selector in product forms.
 *
 * Renders nothing unless ALL of:
 *   1. the active mode is "direct" (the only mode that needs Stripe), and
 *   2. the readiness hook reports the org is NOT yet ready.
 *
 * In every other case (mode != direct, mode-not-yet-selected, hook
 * still loading, or org actually ready) we return null so the form
 * layout doesn't shift between renders.
 *
 * Contract
 * --------
 *
 *   <StripeRequiredAlert
 *     whenTransactionMode={selectedMode}   // 'direct' | 'request' | 'approval'
 *     variant="inline"                     // 'inline' (default) | 'banner'
 *     className="mt-2"                     // optional extra classes
 *   />
 *
 * The component is "smart": it owns the data fetch via useStripeReadiness.
 * The 6 product editors that consume it just drop a one-liner next to
 * the radio button — no lifting, no prop-drilling of the readiness state.
 *
 * Why an alert and not a hard block: the admin may want to save the
 * product as a draft, finish Stripe onboarding later, and have things
 * "just work" once charges_enabled flips. Hard-blocking the radio
 * would force a particular workflow order and be more frustrating
 * than helpful. The storefront fallback (direct → request) already
 * covers the runtime risk; this alert is purely about visibility.
 */

import React from 'react';
import { AlertTriangle } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useStripeReadiness } from '../hooks/useStripeReadiness';
import { useNavigate } from 'react-router-dom';
import { Button } from './ui/button';

const VARIANT_CLASSES = {
  inline: 'mt-2 rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900',
  banner: 'rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900',
};

// Reason codes that have a dedicated localized message. Anything not
// in this list falls back to the generic `defaultMessage`.
const KNOWN_REASON_CODES = [
  'no_connection',
  'connection_inactive',
  'no_default',
  'runtime_unavailable',
  'runtime_needs_auth',
  'runtime_error',
  'provider_not_configured',
];

// Map of backend-suggested internal paths to the actual React route
// that hosts them. The backend keeps requesting "/settings/payments"
// because that is the conceptual destination, but the SPA renders
// PaymentConnectionsCard inside the unified `/settings` page (no
// dedicated sub-route). Centralizing the rewrite here keeps:
//   - the backend free of frontend routing concerns,
//   - the StripeRequiredAlert the single source of truth for "where
//     do I send the admin to fix payments",
//   - and adding future remappings a one-line change.
//
// Anything not in this map is passed through as-is.
const INTERNAL_ROUTE_FALLBACKS = {
  '/settings/payments': '/settings',
};

function resolveInternalUrl(url) {
  if (!url) return null;
  return INTERNAL_ROUTE_FALLBACKS[url] || url;
}

export default function StripeRequiredAlert({
  whenTransactionMode,
  variant = 'inline',
  className = '',
}) {
  const navigate = useNavigate();
  const { t, i18n } = useTranslation('common');
  const { loading, ready, reasonCode, message, actionUrl } = useStripeReadiness();

  // Render-gates, in order of cheapness — short-circuit before any work.
  if (whenTransactionMode !== 'direct') return null;
  if (loading) return null;
  if (ready) return null;

  const onCta = () => {
    if (!actionUrl) return;
    // External http(s) → leave the SPA. Internal absolute path → SPA navigate
    // through the local rewrite table so backend-suggested paths that don't
    // map to a real React route (e.g. /settings/payments) still land on the
    // correct page.
    if (/^https?:\/\//.test(actionUrl)) {
      window.location.href = actionUrl;
    } else {
      navigate(resolveInternalUrl(actionUrl));
    }
  };

  // Resolve the localized message:
  //   1. If reasonCode matches a known key → use the localized version
  //      (overrides the backend's Italian message_it).
  //   2. If the user is in Italian and the backend supplied a message,
  //      surface that (richer than the static fallback).
  //   3. Otherwise → static localized fallback.
  const localized = (reasonCode && KNOWN_REASON_CODES.includes(reasonCode))
    ? t(`stripeAlert.reason.${reasonCode}`)
    : null;
  const isItalian = (i18n.language || '').toLowerCase().startsWith('it');
  const displayMessage = localized || (isItalian && message) || t('stripeAlert.defaultMessage');

  const baseClass = VARIANT_CLASSES[variant] || VARIANT_CLASSES.inline;

  return (
    <div className={`${baseClass} ${className}`} role="alert" data-testid="stripe-required-alert">
      <div className="flex items-start gap-2">
        <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0 text-amber-700" aria-hidden="true" />
        <div className="flex-1">
          <p className="leading-snug">{displayMessage}</p>
          {actionUrl && (
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onCta}
              className="mt-2 border-amber-400 bg-white text-amber-900 hover:bg-amber-100"
            >
              {t('stripeAlert.configureBtn')}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
