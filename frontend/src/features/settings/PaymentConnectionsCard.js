/**
 * PaymentConnectionsCard — payment provider connection management.
 *
 * Supports Stripe Connect OAuth onboarding for Standard accounts.
 * Shows truthful connection + runtime readiness status.
 *
 * States:
 *   not connected     — "Collega Stripe" CTA
 *   connecting        — OAuth flow in progress
 *   configured        — connection exists, runtime may not be ready
 *   runtime ready     — checkout can be created
 *   error             — last connection attempt or runtime check failed
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Badge } from '../../components/ui/badge';
import { Button } from '../../components/ui/button';
import { CreditCard, CheckCircle2, AlertCircle, Loader2, ExternalLink, Lock } from 'lucide-react';
import { paymentConnectionsAPI } from '../../api/paymentConnections';
import { useAuth } from '../../context/AuthContext';
import { useBilling } from '../../hooks/useBilling';
import { toast } from 'sonner';

const PROVIDER_CONFIG = {
  stripe: { label: 'Stripe', color: 'bg-purple-100 text-purple-700' },
  paypal: { label: 'PayPal', color: 'bg-blue-100 text-blue-700' },
};

const STATUS_CONFIG = {
  pending: { key: 'conn_status_pending', color: 'bg-amber-100 text-amber-700', icon: AlertCircle },
  active: { key: 'conn_status_active', color: 'bg-blue-100 text-blue-700', icon: CheckCircle2 },
  disconnected: { key: 'conn_status_disconnected', color: 'bg-gray-100 text-gray-500', icon: AlertCircle },
};

const RUNTIME_CONFIG = {
  unavailable: { key: 'runtime_unavailable', color: 'bg-gray-100 text-gray-500' },
  needs_auth: { key: 'runtime_needs_auth', color: 'bg-amber-100 text-amber-700' },
  ready: { key: 'runtime_ready', color: 'bg-emerald-100 text-emerald-700' },
  error: { key: 'runtime_error', color: 'bg-red-100 text-red-700' },
};

export default function PaymentConnectionsCard({ isAdmin }) {
  const { t } = useTranslation('settings');
  const [searchParams, setSearchParams] = useSearchParams();
  const [connections, setConnections] = useState([]);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState(false);

  // v5.8 / Onda 9.Y.0 — Pre-emptive plan gate.
  // commerce.checkout_stripe is enabled from `core` (Commerce Starter)
  // upwards. hasPlan('core') matches the backend gate exactly: free
  // and starter (Solo) return false, core/pro/enterprise return true.
  // We disable the CTA client-side as UX hint; the backend gate in
  // routers/payment_connections.py is the actual security boundary.
  const { hasPlan, loading: billingLoading } = useBilling();
  const canConnectStripe = hasPlan('core');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [connRes, statusRes] = await Promise.all([
        paymentConnectionsAPI.list(),
        paymentConnectionsAPI.getStatus(),
      ]);
      setConnections(connRes.data?.connections || []);
      setStatus(statusRes.data);
    } catch { /* empty */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  // Handle Stripe Connect return flows (Express only after Block 6).
  // Legacy Standard OAuth callback (?stripe_connect=callback&code=...)
  // was removed in Fase 10b — any residual bookmark hitting this page
  // will simply not be recognized and fall through silently.
  useEffect(() => {
    const scParam = searchParams.get('stripe_connect');

    // Express return: ?stripe_connect=express_return
    // Merchant has completed (or abandoned) Stripe-hosted onboarding.
    // We verify server-side to get the truthful capability state.
    if (scParam === 'express_return') {
      searchParams.delete('stripe_connect');
      setSearchParams(searchParams, { replace: true });

      (async () => {
        setConnecting(true);
        try {
          const res = await paymentConnectionsAPI.expressComplete();
          if (res.data?.status === 'ready') {
            toast.success(t('payments.toast_connected'));
          } else {
            toast.info(t('payments.toast_express_pending', { defaultValue: 'Onboarding Stripe non ancora completato' }));
          }
          load();
        } catch (err) {
          toast.error(err?.response?.data?.detail || t('payments.toast_connect_error'));
        } finally { setConnecting(false); }
      })();
      return;
    }

    // Express refresh: ?stripe_connect=express_refresh
    // The onboarding link expired — regenerate and redirect immediately.
    if (scParam === 'express_refresh') {
      searchParams.delete('stripe_connect');
      setSearchParams(searchParams, { replace: true });

      (async () => {
        setConnecting(true);
        try {
          const res = await paymentConnectionsAPI.expressRefresh();
          const url = res.data?.url;
          if (url) {
            window.location.href = url;
            return;
          }
          toast.error(t('payments.toast_url_error'));
        } catch (err) {
          toast.error(err?.response?.data?.detail || t('payments.toast_generic_error'));
        } finally { setConnecting(false); }
      })();
    }
  }, [searchParams, setSearchParams, load, t]);

  // Primary CTA — now starts Express onboarding by default.
  const handleConnectStripe = async () => {
    setConnecting(true);
    try {
      const res = await paymentConnectionsAPI.expressStart();
      const url = res.data?.url;
      if (res.data?.status === 'ready') {
        toast.success(t('payments.toast_connected'));
        load();
        setConnecting(false);
        return;
      }
      if (url) {
        window.location.href = url;
      } else {
        toast.error(t('payments.toast_url_error'));
        setConnecting(false);
      }
    } catch (err) {
      toast.error(err?.response?.data?.detail || t('payments.toast_generic_error'));
      setConnecting(false);
    }
  };

  // Continue an incomplete Express onboarding (link expired or abandoned).
  const handleContinueExpress = async () => {
    setConnecting(true);
    try {
      const res = await paymentConnectionsAPI.expressRefresh();
      const url = res.data?.url;
      if (url) {
        window.location.href = url;
      } else {
        toast.error(t('payments.toast_url_error'));
        setConnecting(false);
      }
    } catch (err) {
      toast.error(err?.response?.data?.detail || t('payments.toast_generic_error'));
      setConnecting(false);
    }
  };

  // Open the merchant's own Stripe Express dashboard in a new tab.
  // The login URL is single-use and expires within minutes, so we do not
  // cache it — request on click, open immediately.
  //
  // IMPORTANT: popup blockers only allow window.open() when it's called
  // synchronously from a user gesture. Awaiting the API first makes the
  // call "programmatic" and most browsers block it. We open a placeholder
  // tab immediately at click time, then set its location once the URL
  // arrives. Fall back to same-tab navigation if the browser still blocks.
  const handleOpenStripeDashboard = async () => {
    const win = window.open('', '_blank');
    try {
      const res = await paymentConnectionsAPI.expressDashboardLink();
      const url = res.data?.url;
      if (!url) {
        win?.close();
        toast.error(t('payments.toast_url_error'));
        return;
      }
      if (win && !win.closed) {
        win.location.href = url;
      } else {
        // Hard popup block — navigate in the current tab as a fallback.
        // The merchant keeps the URL via back-button if they want to return.
        toast.info(t('payments.toast_popup_blocked', {
          defaultValue: 'Popup bloccato: apertura nella stessa scheda',
        }));
        window.location.href = url;
      }
    } catch (err) {
      win?.close();
      toast.error(err?.response?.data?.detail || t('payments.toast_generic_error'));
    }
  };

  const handleToggleStatus = async (conn) => {
    const newStatus = conn.status === 'active' ? 'disconnected' : 'active';
    try {
      await paymentConnectionsAPI.update(conn.id, { status: newStatus });
      toast.success(newStatus === 'active' ? t('payments.toast_activated') : t('payments.toast_deactivated'));
      load();
    } catch {
      toast.error(t('payments.toast_update_error'));
    }
  };

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2"><CreditCard className="h-4 w-4" />{t('payments.title')}</CardTitle>
        </CardHeader>
        <CardContent><Loader2 className="h-5 w-5 animate-spin text-muted-foreground" /></CardContent>
      </Card>
    );
  }

  const hasStripe = connections.some(c => c.provider === 'stripe');

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <CreditCard className="h-4 w-4" />
            {t('payments.title')}
          </CardTitle>
          {status?.checkout_available ? (
            <Badge className="bg-emerald-100 text-emerald-700 text-xs">{t('payments.status_checkout_available')}</Badge>
          ) : status?.connection_configured ? (
            <Badge className="bg-amber-100 text-amber-700 text-xs">{t('payments.status_configured_not_ready')}</Badge>
          ) : status?.connection_exists ? (
            <Badge className="bg-gray-100 text-gray-500 text-xs">{t('payments.status_not_active')}</Badge>
          ) : (
            <Badge className="bg-gray-100 text-gray-500 text-xs">{t('payments.status_not_configured')}</Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Connection list */}
        {connections.length === 0 && (
          <div className="text-center py-4">
            <p className="text-sm text-muted-foreground">
              {t('payments.empty_title')}
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              {t('payments.empty_desc')}
            </p>
          </div>
        )}

        {connections.map(conn => {
          const prov = PROVIDER_CONFIG[conn.provider] || PROVIDER_CONFIG.stripe;
          const st = STATUS_CONFIG[conn.status] || STATUS_CONFIG.pending;
          const rt = RUNTIME_CONFIG[conn.runtime_status] || RUNTIME_CONFIG.unavailable;
          const StatusIcon = st.icon;
          return (
            <div key={conn.id} className="rounded-lg border p-3 space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Badge className={`text-xs ${prov.color}`}>{prov.label}</Badge>
                  <Badge className={`text-xs ${st.color}`}>
                    <StatusIcon className="h-3 w-3 mr-0.5" />{t(`payments.${st.key}`)}
                  </Badge>
                  <Badge className={`text-[10px] ${rt.color}`}>{t(`payments.${rt.key}`)}</Badge>
                  {conn.is_default && <Badge className="text-[10px] bg-gray-100 text-gray-500">{t('payments.badge_default', 'Default')}</Badge>}
                </div>
                {isAdmin && (
                  <Button variant="outline" size="sm" className="text-xs" onClick={() => handleToggleStatus(conn)}>
                    {conn.status === 'active' ? t('payments.deactivate') : t('payments.activate')}
                  </Button>
                )}
              </div>
              <p className="text-xs text-muted-foreground">
                {conn.display_name || conn.provider}
                {conn.external_account_id && (
                  <span className="ml-1.5 font-mono text-[11px]">({conn.external_account_id.slice(0, 16)}...)</span>
                )}
              </p>
              {conn.runtime_status === 'error' && conn.runtime_error && (
                <p className="text-xs text-red-600">{conn.runtime_error}</p>
              )}
              {/* Express: requirements to complete */}
              {conn.connect_type === 'express' && conn.requirements_currently_due?.length > 0 && (
                <p className="text-[11px] text-amber-700">
                  {t('payments.express_requirements', { defaultValue: 'Completa le informazioni richieste da Stripe' })}
                </p>
              )}
              {/* Express: continue onboarding */}
              {isAdmin && conn.connect_type === 'express' && conn.runtime_status !== 'ready' && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleContinueExpress}
                  disabled={connecting}
                  className="w-full gap-1.5 text-xs"
                >
                  {connecting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <ExternalLink className="h-3.5 w-3.5" />}
                  {t('payments.continue_express_onboarding', { defaultValue: 'Continua onboarding Stripe' })}
                </Button>
              )}
              {/* Express: open merchant's own Stripe dashboard (only when ready) */}
              {isAdmin && conn.connect_type === 'express' &&
               conn.status === 'active' && conn.runtime_status === 'ready' && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleOpenStripeDashboard}
                  className="w-full gap-1.5 text-xs"
                >
                  <ExternalLink className="h-3.5 w-3.5" />
                  {t('payments.open_stripe_dashboard', { defaultValue: 'Apri Dashboard Stripe' })}
                </Button>
              )}
            </div>
          );
        })}

        {/* Connect Stripe CTA — Express onboarding (new default).
            v5.8 / Onda 9.Y.0 — Plan-gated. Free + Solo see the CTA
            disabled with an inline upgrade hint linking to /billing.
            Core / Pro / Enterprise see the normal active button. */}
        {isAdmin && !hasStripe && (
          <div className="space-y-2">
            <Button
              size="sm"
              onClick={canConnectStripe ? handleConnectStripe : undefined}
              disabled={connecting || billingLoading || !canConnectStripe}
              className="w-full gap-1.5"
              title={!canConnectStripe
                ? t('payments.stripe_connect_locked_hint', {
                    defaultValue: 'Disponibile dal piano Commerce Starter',
                  })
                : undefined}
            >
              {connecting ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : !canConnectStripe ? (
                <Lock className="h-3.5 w-3.5" />
              ) : (
                <ExternalLink className="h-3.5 w-3.5" />
              )}
              {t('payments.connect_stripe')}
            </Button>
            {!canConnectStripe && !billingLoading && (
              <p className="text-xs text-muted-foreground text-center">
                {t('payments.stripe_connect_locked_body', {
                  defaultValue: 'Per ricevere pagamenti con carta tramite Stripe Connect serve il piano Commerce Starter o superiore.',
                })}
                {' '}
                <Link to="/billing" className="underline font-medium text-primary">
                  {t('payments.stripe_connect_locked_cta', {
                    defaultValue: 'Aggiorna piano',
                  })}
                </Link>
              </p>
            )}
          </div>
        )}

        {/* Legacy Standard re-connect path removed in Fase 10b.
            All fresh connections go through Express. */}

        {connecting && (
          <p className="text-xs text-muted-foreground text-center animate-pulse">
            {t('payments.connecting')}
          </p>
        )}

        {/* Reason message when not ready */}
        {status && !status.checkout_available && status.reason_message && status.connection_exists && (
          <p className="text-xs text-muted-foreground text-center italic">{status.reason_message}</p>
        )}
      </CardContent>
    </Card>
  );
}
