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

// PS6.5 — `hideAmount`: la pagina CANCEL non deve mostrare importi.
// `status.total` e' il TOTALE ordine, ma la session Stripe annullata
// poteva essere la sola caparra (o una rata): l'importo della session
// non e' ricostruibile dallo status pubblico, quindi meglio nessun
// numero che un numero sbagliato.
function OrderSummary({ status, hideAmount = false }) {
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
      {!hideAmount && typeof total === 'number' && total > 0 && (
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

        {/* TA4 — i pass in mano subito: appena l'ordine è confermato la
            success page linka /t/ e /b/ senza aspettare l'email. */}
        {(status?.passes || []).length > 0 && (
          <div className="mt-5 space-y-2">
            {status.passes.map((p, i) => (
              <a key={p.access_token}
                href={p.kind === 'booking' ? `/b/${p.access_token}` : `/t/${p.access_token}`}
                className="block w-full rounded-full border-2 border-primary text-primary px-5 py-2.5 text-sm font-bold hover:bg-primary hover:text-white transition-colors">
                {p.kind === 'booking'
                  ? t('storefront:checkoutResult.openBooking', { defaultValue: 'Apri la tua prenotazione' })
                  : t('storefront:checkoutResult.openTicket', {
                      n: i + 1,
                      defaultValue: status.passes.filter(x => x.kind === 'ticket').length > 1
                        ? `Apri il tuo pass ${i + 1}` : 'Apri il tuo pass',
                    })}
              </a>
            ))}
          </div>
        )}

        {/* K3 → TA5 — la proposta account vale su OGNI superficie di
            acquisto (prima solo marketplace: chi comprava dal profilo
            operatore o embed non la vedeva mai). Il contesto mktp decide
            solo il link di ritorno, non l'esistenza della CTA. */}
        {(() => {
          let mktp = false;
          try { mktp = sessionStorage.getItem('storefront:mktp_ctx') === '1'; } catch { /* no-op */ }
          let mktpEmail = null;
          try { mktpEmail = sessionStorage.getItem('storefront:mktp_email'); } catch { /* no-op */ }
          const activate = async () => {
            if (!mktpEmail) { window.location.assign('/accedi'); return; }
            try {
              const { default: platformApi } = await import('../../api/platformClient');
              // R2a — lingua UI insieme alla richiesta: l'email OTP del
              // Passaporto parte nella lingua con cui l'utente ha comprato.
              const { default: i18nInst } = await import('../../i18n');
              const lang = (i18nInst.language || '').slice(0, 2).toLowerCase();
              await platformApi.post('/platform/auth/magic-link', {
                email: mktpEmail,
                language: ['it', 'en', 'de', 'fr'].includes(lang) ? lang : undefined,
              });
            } catch { /* enumeration-safe: si prosegue comunque */ }
            window.location.assign(`/accedi?email=${encodeURIComponent(mktpEmail)}&sent=1`);
          };
          return (
            <div className="mt-6 space-y-2">
              <button type="button" onClick={activate}
                className="block w-full rounded-full bg-primary text-white px-5 py-2.5 text-sm font-bold hover:opacity-90">
                <img src="/logo-aurya-128.png" alt="" aria-hidden className="inline h-5 w-5 mr-1 -mt-0.5 select-none" draggable={false} />
                {t('storefront:checkoutResult.activatePassport', { defaultValue: 'Attiva il tuo account Aurya: tutti i tuoi acquisti in un posto solo' })}
              </button>
              {/* PS6.6 — il ritorno dice il vero: se il viaggio e'
                  partito da un ritiro/directory (mktp_return) si torna
                  LI'; altrimenti label neutra verso la home (in fase
                  network la home non ha ritiri: "Torna ai ritiri"
                  sarebbe una promessa falsa). Solo in contesto mktp:
                  fuori dal marketplace il ritorno e' StoreBackLink. */}
              {mktp && (() => {
                let ret = null;
                try { ret = sessionStorage.getItem('storefront:mktp_return'); } catch { /* no-op */ }
                const to = ret || '/';
                const label = ret
                  ? (ret.startsWith('/e/')
                      ? t('storefront:checkoutResult.backToRetreat', { defaultValue: 'Torna al ritiro' })
                      : t('storefront:checkoutResult.backToRetreats', { defaultValue: 'Torna ai ritiri' }))
                  : t('storefront:checkoutResult.backToHome', { defaultValue: 'Torna alla home' });
                return (
                  <Link to={to}
                    className="block w-full rounded-full border border-gray-300 px-5 py-2.5 text-sm font-semibold text-gray-700 hover:border-primary hover:text-primary">
                    {label}
                  </Link>
                );
              })()}
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

// PS6.3 — atterraggio umano dei link /pay/{token} non piu' servibili
// (token ignoto, rata non pagabile, Stripe momentaneamente giu'). Il
// backend REINDIRIZZA qui invece di rispondere JSON nudo: questi link
// viaggiano nelle email di promemoria e li apre un cliente, non un
// client API. Copy onesta + CTA verso l'account (dove vivono ordini e
// pagamenti) e, quando l'org e' nota (?slug=), verso l'operatore.
export function PayLinkUnavailablePage() {
  const [searchParams] = useSearchParams();
  const { t } = useTranslation('storefront');
  const slug = searchParams.get('slug');
  const temporary = searchParams.get('reason') === 'temporary';

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <div className="text-center max-w-md" data-testid="pay-unavailable">
        <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-amber-100 flex items-center justify-center">
          <svg className="w-8 h-8 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M12 9v2m0 4h.01M4.93 19.07A10 10 0 1 1 19.07 4.93 10 10 0 0 1 4.93 19.07z" />
          </svg>
        </div>
        <h2 className="text-xl font-bold text-gray-900">
          {temporary
            ? t('storefront:checkoutResult.payUnavailable.tempTitle', { defaultValue: 'Pagamento momentaneamente non disponibile' })
            : t('storefront:checkoutResult.payUnavailable.title', { defaultValue: 'Questo link di pagamento non è più attivo' })}
        </h2>
        <p className="text-gray-600 mt-2">
          {temporary
            ? t('storefront:checkoutResult.payUnavailable.tempBody', { defaultValue: 'Non siamo riusciti ad avviare il pagamento in questo momento. Nessun addebito è stato effettuato: riprova tra qualche minuto dallo stesso link.' })
            : t('storefront:checkoutResult.payUnavailable.body', { defaultValue: 'La rata collegata a questo link non risulta più in attesa di pagamento. Nessun addebito è stato effettuato. Trovi lo stato aggiornato dei tuoi ordini e pagamenti nel tuo account.' })}
        </p>
        <div className="mt-6 space-y-2">
          <Link to="/account"
            className="block w-full rounded-full bg-primary text-white px-5 py-2.5 text-sm font-bold hover:opacity-90">
            {t('storefront:checkoutResult.payUnavailable.ctaAccount', { defaultValue: 'Vai al tuo account' })}
          </Link>
          {slug && (
            <Link to={`/o/${slug}`}
              className="block w-full rounded-full border border-gray-300 px-5 py-2.5 text-sm font-semibold text-gray-700 hover:border-primary hover:text-primary">
              {t('storefront:checkoutResult.payUnavailable.ctaOperator', { defaultValue: "Torna all'operatore" })}
            </Link>
          )}
        </div>
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

  // PS6.5 — la pagina cancel legge il funnel: se il viaggio e' partito
  // da un ritiro (mktp_return in sessione) la CTA primaria e' RIPROVARE
  // tornando alla landing; il link all'operatore resta come secondaria.
  let mktpReturn = null;
  try { mktpReturn = sessionStorage.getItem('storefront:mktp_return'); } catch { /* no-op */ }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <div className="text-center max-w-md">
        <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-amber-100 flex items-center justify-center">
          <svg className="w-8 h-8 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </div>
        <h2 className="text-xl font-bold text-gray-900">{t('storefront:checkoutResult.cancelTitle')}</h2>
        {/* PS6.5 — copy onesta: nessun addebito, ordine NON confermato.
            (Niente promesse di ricontatto su un draft che nessuno
            lavorera'.) L'importo non si mostra: vedi OrderSummary. */}
        <p className="text-gray-600 mt-2">
          {t('storefront:checkoutResult.cancelDesc')}
        </p>
        {!loading && <OrderSummary status={status} hideAmount />}
        {mktpReturn && (
          <Link to={mktpReturn}
            className="inline-flex items-center justify-center mt-6 w-full rounded-full bg-primary text-white px-5 py-2.5 text-sm font-bold hover:opacity-90"
            data-testid="cancel-retry-retreat">
            {t('storefront:checkoutResult.cancelRetryRetreat', { defaultValue: 'Riprova: torna al ritiro' })}
          </Link>
        )}
        <StoreBackLink storeSlug={status?.store_slug} storeName={status?.store_name} />
      </div>
    </div>
  );
}
