/**
 * PaymentMethodsSection — Settings panel that surfaces which payment
 * methods the merchant's connected provider (Stripe today, Datatrans
 * in v1.5) has actually enabled.
 *
 * CH compliance v1: a Swiss merchant typically connects Stripe in
 * minutes but forgets to flip the TWINT toggle in their Stripe
 * dashboard, which silently leaves their checkout in card-only mode.
 * This component reads `/organizations/current/payment-capabilities`
 * and surfaces:
 *   - "✅ Card active"
 *   - "✅ TWINT active" (when on)
 *   - "⚠️ TWINT not active" + a deep-link to dashboard.stripe.com
 *     when the org currency is CHF and TWINT is not enabled.
 *
 * Display-only — there is nothing to *configure* in afianco itself
 * because the toggle lives on Stripe's side. We render status and
 * route the merchant out.
 */

import React, { useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../../components/ui/card';
import { Button } from '../../../components/ui/button';
import { Badge } from '../../../components/ui/badge';
import { CreditCard, ExternalLink, RefreshCw, AlertTriangle, CheckCircle2, XCircle, Loader2 } from 'lucide-react';
import { organizationsAPI } from '../../../api';

const STRIPE_DASHBOARD_FALLBACK_URL = 'https://dashboard.stripe.com/settings/payment_methods';


/**
 * One-row status indicator for a payment method.
 */
function MethodRow({ name, active, hint, helpUrl, helpLabel }) {
  return (
    <div className="flex items-start justify-between gap-3 rounded-lg border bg-white p-3">
      <div className="flex items-start gap-2 min-w-0">
        {active ? (
          <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0 mt-0.5" />
        ) : (
          <AlertTriangle className="h-4 w-4 text-amber-500 shrink-0 mt-0.5" />
        )}
        <div className="min-w-0">
          <p className="font-medium text-sm">{name}</p>
          {hint ? (
            <p className="text-xs text-muted-foreground mt-0.5">{hint}</p>
          ) : null}
        </div>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        {active ? (
          <Badge className="bg-emerald-100 text-emerald-800 hover:bg-emerald-100">{helpLabel || 'Attivo'}</Badge>
        ) : (
          helpUrl ? (
            <a
              href={helpUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs underline text-blue-700 hover:text-blue-900 inline-flex items-center gap-1"
            >
              {helpLabel || 'Attiva'} <ExternalLink className="h-3 w-3" />
            </a>
          ) : (
            <Badge variant="outline">Non attivo</Badge>
          )
        )}
      </div>
    </div>
  );
}


export default function PaymentMethodsSection() {
  const { t } = useTranslation('settings');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);

  // ``forceRefresh`` toggles the server-side cache bypass on the
  // ↻ button click. The auto-fetch on mount uses the cache so we
  // don't hammer Stripe on every Settings page render.
  const fetchData = useCallback(async ({ forceRefresh = false } = {}) => {
    try {
      const res = await organizationsAPI.getPaymentCapabilities({ forceRefresh });
      setData(res.data);
      setError(null);
    } catch (err) {
      setError(err?.response?.data?.detail || err?.message || 'unknown');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleRefresh = () => {
    setRefreshing(true);
    // Manual refresh always bypasses the cache so the merchant sees the
    // latest provider state immediately after toggling a payment method
    // on their Stripe dashboard.
    fetchData({ forceRefresh: true });
  };

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CreditCard className="h-4 w-4" />
            {t('paymentMethods.title', 'Metodi di pagamento')}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-6 text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin mr-2" />
            <span className="text-sm">{t('paymentMethods.loading', 'Verifica metodi attivi…')}</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  const status = data?.status || 'not_connected';
  const provider = data?.provider || 'none';
  const currency = String(data?.currency || 'EUR').toUpperCase();
  const caps = data?.capabilities || {};
  const stripeUrl = data?.stripe_dashboard_payment_methods_url || STRIPE_DASHBOARD_FALLBACK_URL;

  // Top-level state copy for clarity.
  let topBanner = null;
  if (status === 'not_connected') {
    topBanner = (
      <div className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 mb-3 text-sm text-amber-900">
        <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
        <div>
          <p className="font-medium">{t('paymentMethods.notConnected.title', 'Stripe non connesso')}</p>
          <p className="text-xs mt-0.5 opacity-90">
            {t('paymentMethods.notConnected.body', 'Collega un account Stripe per accettare pagamenti online. Senza connessione, il checkout pubblico è disabilitato.')}
          </p>
        </div>
      </div>
    );
  } else if (status === 'error') {
    topBanner = (
      <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 mb-3 text-sm text-red-900">
        <XCircle className="h-4 w-4 mt-0.5 shrink-0" />
        <div>
          <p className="font-medium">{t('paymentMethods.error.title', 'Errore lettura metodi')}</p>
          <p className="text-xs mt-0.5 opacity-90">
            {data?.error_message || t('paymentMethods.error.body', 'Impossibile contattare il provider di pagamento. Riprova fra qualche minuto.')}
          </p>
        </div>
      </div>
    );
  }

  // CHF + no TWINT → strong CTA banner above the rows.
  const showTwintCta = currency === 'CHF' && status === 'ok' && !caps.twint_active;

  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between space-y-0">
        <div>
          <CardTitle className="flex items-center gap-2">
            <CreditCard className="h-4 w-4" />
            {t('paymentMethods.title', 'Metodi di pagamento')}
          </CardTitle>
          <CardDescription>
            {t('paymentMethods.description',
              "Lo stato dei metodi attivi sul tuo provider. Per modificarli vai sul dashboard del provider, le impostazioni si rispecchiano qui.")}
          </CardDescription>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleRefresh}
          disabled={refreshing}
          data-testid="payment-methods-refresh"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? 'animate-spin' : ''}`} />
        </Button>
      </CardHeader>
      <CardContent>
        {error ? (
          <div className="text-sm text-red-700">
            {String(error)}
          </div>
        ) : null}

        {topBanner}

        {showTwintCta ? (
          <div className="flex items-start gap-2 rounded-lg border border-blue-200 bg-blue-50 p-3 mb-3 text-sm text-blue-900">
            <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="font-medium">
                {t('paymentMethods.twintCta.title', 'Attiva TWINT su Stripe per i clienti svizzeri')}
              </p>
              <p className="text-xs mt-0.5 opacity-90">
                {t('paymentMethods.twintCta.body',
                  "TWINT è il metodo di pagamento più diffuso in Svizzera. L'attivazione è gratuita e richiede 30 secondi sul dashboard Stripe.")}
              </p>
              <a
                href={stripeUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 mt-1.5 text-xs font-medium underline"
              >
                {t('paymentMethods.twintCta.button', 'Apri impostazioni Stripe')}
                <ExternalLink className="h-3 w-3" />
              </a>
            </div>
          </div>
        ) : null}

        {status === 'ok' || status === 'error' ? (
          <div className="space-y-2">
            <MethodRow
              name={t('paymentMethods.card.name', 'Carte di credito')}
              active={caps.card_active}
              hint={t('paymentMethods.card.hint', 'Visa, Mastercard, Amex, Apple Pay, Google Pay')}
              helpUrl={!caps.card_active ? stripeUrl : null}
              helpLabel={caps.card_active
                ? t('paymentMethods.activeBadge', 'Attivo')
                : t('paymentMethods.activateOnStripe', 'Attiva su Stripe')}
            />
            {currency === 'CHF' ? (
              <MethodRow
                name={t('paymentMethods.twint.name', 'TWINT')}
                active={caps.twint_active}
                hint={t('paymentMethods.twint.hint', 'Pagamento mobile più diffuso in Svizzera')}
                helpUrl={!caps.twint_active ? stripeUrl : null}
                helpLabel={caps.twint_active
                  ? t('paymentMethods.activeBadge', 'Attivo')
                  : t('paymentMethods.activateOnStripe', 'Attiva su Stripe')}
              />
            ) : null}
          </div>
        ) : null}

        {data?.connected_account ? (
          <p className="mt-3 text-[11px] text-muted-foreground">
            {t('paymentMethods.connectedAccountLabel', 'Account collegato')}:&nbsp;
            <span className="font-mono">{data.connected_account}</span>
            &nbsp;·&nbsp;
            <span className="capitalize">{provider}</span>
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}
