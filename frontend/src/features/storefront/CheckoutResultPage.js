import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

import { storefrontAPI } from '../../api/storefront';
import { useStorefrontLocaleSync } from './hooks/useStorefrontLocaleSync';

/**
 * Checkout result pages for Stripe redirect.
 *
 * /s/checkout-success?order_id=X — shown after successful Stripe payment
 * /s/checkout-cancel?order_id=X  — shown if visitor cancels Stripe checkout
 *
 * Both are public (no auth). Fetch minimal, public-safe order data and poll
 * for webhook-driven state transitions so the customer sees a truthful
 * "pending → confirmed" handoff rather than a static message that lies.
 *
 * LANGUAGE STRATEGY: drives i18n via `useStorefrontLocaleSync` once the
 * status response arrives (it carries `store_slug` so the resolver can
 * remember the language the customer chose for that store). Until then
 * we paint with the inherited fallback (typically the customer's saved
 * locale or the global default), which is good enough for a transient
 * loading screen.
 */

// Poll payment_intent until it flips from "required" to "collected"
// (or terminal). Customer-facing, so keep polling tight but bounded.
const POLL_INTERVAL_MS = 2000;
const POLL_TIMEOUT_MS = 30000;

function formatAmount(amount, currency, locale = 'it-IT') {
  try {
    return new Intl.NumberFormat(locale, {
      style: 'currency',
      currency: currency || 'EUR',
    }).format(amount);
  } catch {
    return `${(amount ?? 0).toFixed(2)} ${currency || 'EUR'}`;
  }
}

function useOrderStatusPolling(orderId, { pollWhilePending = true } = {}) {
  const [status, setStatus] = useState(null);  // public order status object
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [pollingStopped, setPollingStopped] = useState(false);
  const timerRef = useRef(null);
  const deadlineRef = useRef(null);

  const fetchOnce = useCallback(async () => {
    if (!orderId) return null;
    const res = await storefrontAPI.getOrderStatus(orderId);
    return res.data;
  }, [orderId]);

  useEffect(() => {
    if (!orderId) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    deadlineRef.current = Date.now() + POLL_TIMEOUT_MS;

    const tick = async () => {
      try {
        const data = await fetchOnce();
        if (cancelled) return;
        setStatus(data);
        setError(null);
        setLoading(false);

        // Stop polling once payment confirmed, or past deadline, or not pending mode
        const isPending = data?.payment_intent === 'required';
        const isTerminal =
          data?.payment_intent === 'collected' || data?.payment_intent === 'waived';
        const deadlineReached = Date.now() >= (deadlineRef.current ?? 0);

        if (!pollWhilePending || isTerminal || !isPending || deadlineReached) {
          setPollingStopped(true);
          return;
        }
        timerRef.current = setTimeout(tick, POLL_INTERVAL_MS);
      } catch (err) {
        if (cancelled) return;
        setError(err);
        setLoading(false);
        setPollingStopped(true);
      }
    };

    tick();
    return () => {
      cancelled = true;
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [orderId, fetchOnce, pollWhilePending]);

  return { status, loading, error, pollingStopped };
}

function StoreBackLink({ storeSlug, storeName }) {
  const { t } = useTranslation('storefront');
  // If we can't resolve a slug (legacy order without store_id, or unpublished),
  // we intentionally don't show the CTA — sending to a 404 is worse than omitting.
  if (!storeSlug) return null;
  return (
    <a
      href={`/s/${storeSlug}`}
      className="inline-flex items-center justify-center mt-6 px-5 py-2.5 rounded-lg
                 bg-[var(--sf-accent,#111827)] text-[var(--sf-accent-fg,#ffffff)] text-sm font-medium hover:bg-[var(--sf-accent-hover,#1f2937)] transition"
    >
      {storeName ? t('storefront:checkoutResult.backToStoreNamed', { name: storeName }) : t('storefront:checkoutResult.backToStore')}
    </a>
  );
}

function OrderSummary({ status }) {
  const { t, i18n } = useTranslation('storefront');
  if (!status) return null;
  const { order_number: orderNumber, order_id: orderId, total, currency } = status;
  return (
    <div className="mt-5 text-sm text-gray-600 space-y-1">
      {orderNumber ? (
        <p>
          {t('storefront:checkoutResult.orderLine')}{' '}
          <span className="font-semibold text-gray-900">{orderNumber}</span>
        </p>
      ) : orderId ? (
        <p className="text-xs text-gray-400">
          {t('storefront:submitted.reference', { ref: String(orderId).slice(0, 8) })}
        </p>
      ) : null}
      {typeof total === 'number' && total > 0 && (
        <p className="text-gray-900 font-semibold">
          {formatAmount(total, currency, i18n.language)}
        </p>
      )}
    </div>
  );
}

export function CheckoutSuccessPage() {
  const [searchParams] = useSearchParams();
  const orderId = searchParams.get('order_id');
  const { t } = useTranslation('storefront');
  const { status, loading, error, pollingStopped } = useOrderStatusPolling(orderId, {
    pollWhilePending: true,
  });

  // Sync the storefront locale once the order status carries a slug.
  // While loading the resolver short-circuits to the safe fallback.
  useStorefrontLocaleSync({
    storeSlug: status?.store_slug,
    supportedLanguages: undefined,
  });

  const isConfirmed = status?.payment_intent === 'collected';
  const stillPending = status?.payment_intent === 'required';

  // Visual state machine
  let icon;
  let title;
  let description;
  let badgeColor = 'bg-green-100 text-green-600';

  if (loading) {
    icon = (
      <svg className="w-8 h-8 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor">
        <circle cx="12" cy="12" r="10" strokeWidth="2" strokeOpacity="0.25" />
        <path d="M22 12a10 10 0 0 1-10 10" strokeWidth="2" strokeLinecap="round" />
      </svg>
    );
    title = t('storefront:checkoutResult.loadingTitle');
    description = t('storefront:checkoutResult.loadingDesc');
    badgeColor = 'bg-gray-100 text-gray-600';
  } else if (error) {
    icon = (
      <svg className="w-8 h-8" viewBox="0 0 24 24" fill="none" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M12 9v2m0 4h.01M4.93 19.07A10 10 0 1 1 19.07 4.93 10 10 0 0 1 4.93 19.07z" />
      </svg>
    );
    title = t('storefront:checkoutResult.paymentReceived');
    description = t('storefront:checkoutResult.errorDesc');
    badgeColor = 'bg-amber-100 text-amber-600';
  } else if (isConfirmed) {
    icon = (
      <svg className="w-8 h-8" viewBox="0 0 24 24" fill="none" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
      </svg>
    );
    title = t('storefront:checkoutResult.confirmedTitle');
    description = t('storefront:checkoutResult.confirmedDesc');
    badgeColor = 'bg-green-100 text-green-600';
  } else if (stillPending && !pollingStopped) {
    icon = (
      <svg className="w-8 h-8 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor">
        <circle cx="12" cy="12" r="10" strokeWidth="2" strokeOpacity="0.25" />
        <path d="M22 12a10 10 0 0 1-10 10" strokeWidth="2" strokeLinecap="round" />
      </svg>
    );
    title = t('storefront:checkoutResult.paymentReceived');
    description = t('storefront:checkoutResult.pendingDesc');
    badgeColor = 'bg-blue-100 text-blue-600';
  } else {
    // Polling stopped but still required → webhook running late; remain truthful.
    icon = (
      <svg className="w-8 h-8" viewBox="0 0 24 24" fill="none" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
      </svg>
    );
    title = t('storefront:checkoutResult.paymentReceived');
    description = t('storefront:checkoutResult.lateWebhookDesc');
    badgeColor = 'bg-green-100 text-green-600';
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <div className="text-center max-w-md">
        <div className={`w-16 h-16 mx-auto mb-4 rounded-full flex items-center justify-center ${badgeColor}`}>
          {icon}
        </div>
        <h2 className="text-xl font-bold text-gray-900">{title}</h2>
        <p className="text-gray-600 mt-2">{description}</p>
        <OrderSummary status={status} />

        {/* K3 — contesto marketplace (flag messo dal checkout mktp):
            il viaggio continua sulla piattaforma, non nella vetrina */}
        {(() => {
          let mktp = false;
          try { mktp = sessionStorage.getItem('storefront:mktp_ctx') === '1'; } catch { /* no-op */ }
          if (!mktp) return null;
          let mktpEmail = null;
          try { mktpEmail = sessionStorage.getItem('storefront:mktp_email'); } catch { /* no-op */ }
          const activate = async () => {
            if (!mktpEmail) { window.location.assign('/account/accedi'); return; }
            try {
              const { default: platformApi } = await import('../../api/platformClient');
              await platformApi.post('/platform/auth/magic-link', { email: mktpEmail });
            } catch { /* enumeration-safe: si prosegue comunque */ }
            window.location.assign(`/account/accedi?email=${encodeURIComponent(mktpEmail)}&sent=1`);
          };
          return (
            <div className="mt-6 space-y-2">
              <button type="button" onClick={activate}
                className="block w-full rounded-full bg-primary text-white px-5 py-2.5 text-sm font-bold hover:opacity-90">
                🌿 {t('storefront:checkoutResult.activatePassport', { defaultValue: 'Attiva il tuo Passaporto — tutti i tuoi viaggi in un posto solo' })}
              </button>
              <Link to="/ritiri"
                className="block w-full rounded-full border border-gray-300 px-5 py-2.5 text-sm font-semibold text-gray-700 hover:border-primary hover:text-primary">
                {t('storefront:checkoutResult.backToRetreats', { defaultValue: 'Torna ai ritiri' })}
              </Link>
            </div>
          );
        })()}

        {(() => {
          try { if (sessionStorage.getItem('storefront:mktp_ctx') === '1') return null; } catch { /* no-op */ }
          return <StoreBackLink storeSlug={status?.store_slug} storeName={status?.store_name} />;
        })()}
      </div>
    </div>
  );
}

export function CheckoutCancelPage() {
  const [searchParams] = useSearchParams();
  const orderId = searchParams.get('order_id');
  const { t } = useTranslation('storefront');
  // Cancel page: no polling — the payment did not complete.
  const { status, loading } = useOrderStatusPolling(orderId, {
    pollWhilePending: false,
  });

  useStorefrontLocaleSync({
    storeSlug: status?.store_slug,
    supportedLanguages: undefined,
  });

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <div className="text-center max-w-md">
        <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-amber-100 flex items-center justify-center">
          <svg className="w-8 h-8 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </div>
        <h2 className="text-xl font-bold text-gray-900">{t('storefront:checkoutResult.cancelTitle')}</h2>
        <p className="text-gray-600 mt-2">
          {t('storefront:checkoutResult.cancelDesc')}
        </p>
        {!loading && <OrderSummary status={status} />}
        <StoreBackLink storeSlug={status?.store_slug} storeName={status?.store_name} />
      </div>
    </div>
  );
}
