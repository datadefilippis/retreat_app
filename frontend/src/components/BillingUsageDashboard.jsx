/**
 * BillingUsageDashboard — "USO CORRENTE" + "ADD-ON ATTIVI" sections
 * for the BillingSection settings card.
 *
 * Onda 7 (v5.8). Fetches `/api/billing/usage-summary` once on mount and
 * renders:
 *   1. A grid of QuotaProgressBanner for each metric with limit > 0
 *   2. A list of currently active add-ons with quantity + remove button
 *
 * Mounted by BillingSection so the existing summary / actions blocks
 * stay clean. Self-loading (loading + error states inline) so the parent
 * doesn't need to coordinate fetches.
 *
 * Best-effort: a backend hiccup renders an inline error and the rest of
 * BillingSection (plan summary, manage button) keeps working unchanged.
 *
 * Uses billingAPI.getUsageSummary, billingAPI.removeAddon. Add-on grid
 * for buying NEW add-ons lives on the PlansPage (linked via the
 * "Browse available add-ons" button below).
 */
import React, { useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { Loader2, RefreshCw, X, ShoppingBag, Check, Lock, ArrowUpCircle } from 'lucide-react';
import { billingAPI } from '../api/billing';
import { useBilling } from '../hooks/useBilling';

// Onda 25 Phase 4 — QuotaProgressBanner intentionally NOT imported here.
// That component is the page-level warning banner mounted on
// OrdersPage / CashflowDataPage and is designed to HIDE when usage is
// below 60 % so it doesn't intrude during normal operation. The
// settings dashboard, instead, must always show the limit even at 0/N
// — the user wants to see "what does my plan include?" at a glance.
// The compact `MetricRow` sub-component below renders the always-on
// list row used by this dashboard only.


// ── Always-visible compact metric row (Onda 25 Phase 4) ────────────────────
//
// Renders one limit as: label · used/limit · progress bar. Stays visible
// at any usage ratio (unlike QuotaProgressBanner which hides under 60 %).
// Visual state escalates: gray → amber → red. CTAs ("Acquista pack",
// "Aggiorna piano") only render when ratio ≥ 80 % so the row stays calm
// during normal operation but pushes upgrade signals when needed.
function MetricRow({
  metricKey,
  used,
  limit,
  addonSlug,
  onAddonClick,
  onUpgradeClick,
  t,
}) {
  // limit must be > 0 here (caller filters out -1 / 0 paths)
  const ratio = limit > 0 ? used / limit : 0;
  const pct = Math.min(100, Math.round(ratio * 100));

  let barColor;
  let labelTone;
  let usageTone;
  let rowBg;
  if (ratio >= 1) {
    barColor = 'bg-red-500';
    labelTone = 'text-red-700';
    usageTone = 'text-red-700';
    rowBg = 'bg-red-50/40 border-red-100';
  } else if (ratio >= 0.8) {
    barColor = 'bg-amber-500';
    labelTone = 'text-amber-700';
    usageTone = 'text-amber-700';
    rowBg = 'bg-amber-50/40 border-amber-100';
  } else if (ratio >= 0.6) {
    barColor = 'bg-amber-400';
    labelTone = 'text-foreground';
    usageTone = 'text-foreground';
    rowBg = 'bg-white border-gray-100';
  } else {
    barColor = 'bg-gray-400';
    labelTone = 'text-foreground';
    usageTone = 'text-muted-foreground';
    rowBg = 'bg-white border-gray-100';
  }

  const metricLabel = t(`billing.quota.metric.${metricKey}`, {
    defaultValue: metricKey,
  });
  const showCtas = ratio >= 0.8;

  return (
    <div className={`px-3 py-2 rounded-md border ${rowBg}`}>
      <div className="flex items-center justify-between gap-3 mb-1.5">
        <span className={`text-xs font-medium ${labelTone}`}>{metricLabel}</span>
        <span className={`text-xs font-semibold tabular-nums ${usageTone}`}>
          {used} / {limit}
        </span>
      </div>
      <div className="h-1.5 rounded-full bg-gray-100 overflow-hidden">
        <div
          className={`h-full ${barColor} transition-all duration-300`}
          style={{ width: `${pct}%` }}
        />
      </div>
      {showCtas && (onAddonClick || onUpgradeClick) && (
        <div className="mt-2 flex flex-wrap gap-3 text-[11px]">
          {addonSlug && onAddonClick && (
            <button
              type="button"
              onClick={onAddonClick}
              className="font-medium text-blue-600 hover:underline"
            >
              {t('billing.quota.cta_buy_addon', { defaultValue: 'Acquista pack' })}
            </button>
          )}
          {onUpgradeClick && (
            <button
              type="button"
              onClick={onUpgradeClick}
              className="font-medium text-blue-600 hover:underline"
            >
              {t('billing.quota.cta_upgrade_plan', { defaultValue: 'Aggiorna piano' })}
            </button>
          )}
        </div>
      )}
    </div>
  );
}


export default function BillingUsageDashboard({ onAddonRemoved }) {
  const { t } = useTranslation('settings');
  const navigateTo = useNavigate();
  // Onda 13 — react to global billing state updates so this widget
  // refreshes when the plan changes elsewhere (e.g. user upgrades on
  // /plans, then navigates back to /settings). Pre-Onda 13 this
  // component fetched once on mount and never refreshed, leaving the
  // "Uso corrente" section showing the OLD plan's quotas after an
  // upgrade.
  const billing = useBilling();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [removing, setRemoving] = useState(null);   // addon_slug currently being removed

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await billingAPI.getUsageSummary();
      setData(res || null);
    } catch (e) {
      setError(e?.response?.data?.detail || e?.message || 'load_failed');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  // Onda 13 — reload usage summary whenever the global billing context
  // refreshes (e.g. after a plan upgrade triggered from another page,
  // or after the focus-event refresh). Tied to lastRefreshAt so we
  // don't poll on every render. Skip the very first render: load()
  // already fired in the useEffect above.
  useEffect(() => {
    if (!billing?.lastRefreshAt) return;
    load();
  }, [billing?.lastRefreshAt, load]);

  const handleRemoveAddon = async (addon) => {
    const confirmMsg = t('billing.active_addons.remove_confirm', { name: addon.name });
    if (!window.confirm(confirmMsg)) return;
    setRemoving(addon.addon_slug);
    try {
      await billingAPI.removeAddon(addon.addon_slug);
      // Wait briefly for webhook to land then reload — same delay logic the
      // post-checkout polling uses elsewhere. Hard refresh of usage-summary
      // gives the most truthful UI.
      setTimeout(async () => {
        await load();
        setRemoving(null);
        if (onAddonRemoved) onAddonRemoved(addon.addon_slug);
      }, 1500);
    } catch (e) {
      setRemoving(null);
      const msg = e?.response?.data?.detail?.message || e?.message;
      alert(msg || 'Errore durante la rimozione del pack.');
    }
  };

  const handleBrowseAddons = () => {
    navigateTo('/plans#addons');
  };

  // ── Loading / error states ──────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground py-2">
        <Loader2 className="h-4 w-4 animate-spin" />
        {t('billing.usage.loading', 'Caricamento dati di utilizzo…')}
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-between gap-3 p-3 rounded-md bg-red-50 border border-red-200 text-sm text-red-800">
        <span>{t('billing.usage.error', 'Impossibile caricare i dati di utilizzo.')}</span>
        <button
          type="button"
          onClick={load}
          className="inline-flex items-center gap-1 text-xs font-medium hover:underline"
        >
          <RefreshCw className="h-3 w-3" /> Retry
        </button>
      </div>
    );
  }

  if (!data) return null;

  const visibleMetrics = (data.metrics || []).filter(
    (m) => m.limit > 0 || m.status === 'unlimited' || m.status === 'exceeded',
  );
  const activeAddons = data.active_addons || [];

  return (
    <div className="space-y-6">
      {/* ── Section: USO CORRENTE ─────────────────────────────────────────── */}
      <section>
        <h3 className="text-sm font-semibold text-foreground mb-1">
          {t('billing.usage.section_title', 'Uso corrente')}
        </h3>
        <p className="text-xs text-muted-foreground mb-3">
          {t('billing.usage.section_subtitle', 'Quote del periodo in corso (base plan + add-on attivi)')}
        </p>

        {visibleMetrics.length === 0 ? (
          <div className="text-sm text-muted-foreground italic py-2">
            {t('billing.usage.no_metrics', 'Nessuna metrica monitorata per questo piano.')}
          </div>
        ) : (
          <div className="space-y-2">
            {visibleMetrics.map((m) => {
              if (m.status === 'unlimited') {
                // Don't show a bar for unlimited — just a small confirmation row
                return (
                  <div
                    key={m.key}
                    className="flex items-center justify-between text-xs px-3 py-2 rounded-md bg-green-50 border border-green-100 text-green-800"
                  >
                    <span>
                      {t(`billing.quota.metric.${m.key}`, { defaultValue: m.key })}
                    </span>
                    <span className="font-medium">
                      ∞ {t('billing.usage.unlimited_label', 'Illimitato')}
                    </span>
                  </div>
                );
              }

              return (
                <MetricRow
                  key={m.key}
                  metricKey={m.key}
                  used={m.used}
                  limit={m.limit}
                  addonSlug={m.addon_slug}
                  onAddonClick={m.addon_slug ? handleBrowseAddons : null}
                  onUpgradeClick={() => navigateTo('/plans')}
                  t={t}
                />
              );
            })}
          </div>
        )}
      </section>

      {/* ── Section: FEATURES INCLUSE NEL PIANO (v5.8 / Onda 9.W) ──────────
          Boolean features that are NOT counters (alert_analysis, health
          AI, email alerts, etc.). Showing them as quotas in USO CORRENTE
          would be misleading — they're sì/no flags. Locked items show an
          upgrade CTA so the user discovers what's available on higher
          plans without scrolling away. */}
      {(data.features || []).length > 0 && (
        <section>
          <h3 className="text-sm font-semibold text-foreground mb-1">
            {t('billing.features_section.title', 'Features incluse nel piano')}
          </h3>
          <p className="text-xs text-muted-foreground mb-3">
            {t('billing.features_section.subtitle', 'Cosa e\' attivo (e cosa puoi sbloccare con un upgrade)')}
          </p>
          <div className="space-y-1">
            {(data.features || []).map((f) => {
              const label = t(
                `billing.features_section.feature.${f.key}.label`,
                t(`billing.quota.metric.${f.key}`, { defaultValue: f.key })
              );
              const description = t(
                `billing.features_section.feature.${f.key}.desc`,
                { defaultValue: '' }
              );
              return (
                <div
                  key={f.key}
                  className={`flex items-center justify-between gap-2 px-2 py-1.5 rounded-md ${
                    f.included ? 'bg-green-50/40' : 'bg-gray-50 opacity-90'
                  }`}
                >
                  <div className="flex items-start gap-2 min-w-0 flex-1">
                    {f.included ? (
                      <span className="mt-0.5 flex items-center justify-center h-4 w-4 rounded-full bg-green-100 flex-shrink-0">
                        <Check className="h-2.5 w-2.5 text-green-600" />
                      </span>
                    ) : (
                      <span className="mt-0.5 flex items-center justify-center h-4 w-4 rounded-full bg-gray-200 flex-shrink-0">
                        <Lock className="h-2 w-2 text-gray-500" />
                      </span>
                    )}
                    <div className="min-w-0">
                      <div className={`text-xs font-medium ${f.included ? 'text-foreground' : 'text-muted-foreground'}`}>
                        {label}
                      </div>
                      {description && (
                        <div className="text-[10.5px] text-muted-foreground leading-tight">
                          {description}
                        </div>
                      )}
                    </div>
                  </div>
                  {!f.included && (
                    <button
                      type="button"
                      onClick={() => navigateTo('/plans')}
                      className="text-[10.5px] font-medium text-blue-600 hover:underline inline-flex items-center gap-0.5 flex-shrink-0"
                    >
                      <ArrowUpCircle className="h-3 w-3" />
                      {t('billing.features_section.upgrade_cta', 'Aggiorna')}
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* ── Section: ADD-ON ATTIVI ────────────────────────────────────────── */}
      <section>
        <div className="flex items-center justify-between mb-1">
          <h3 className="text-sm font-semibold text-foreground">
            {t('billing.active_addons.section_title', 'Add-on attivi')}
          </h3>
          <button
            type="button"
            onClick={handleBrowseAddons}
            className="text-xs font-medium text-blue-600 hover:underline inline-flex items-center gap-1"
          >
            <ShoppingBag className="h-3 w-3" />
            {t('billing.active_addons.browse_btn', 'Sfoglia add-on')}
          </button>
        </div>
        <p className="text-xs text-muted-foreground mb-3">
          {t('billing.active_addons.section_subtitle', 'Pacchetti aggiuntivi sulla tua subscription')}
        </p>

        {activeAddons.length === 0 ? (
          <div className="text-sm text-muted-foreground italic py-2">
            {t('billing.active_addons.empty', 'Nessun add-on attivo. Visita la pagina piani per scoprirli.')}
          </div>
        ) : (
          <div className="space-y-2">
            {activeAddons.map((a) => {
              const total = (a.quantity || 1) * (a.price_monthly || 0);
              const totalFmt = total.toFixed(2);
              const isRemoving = removing === a.addon_slug;
              return (
                <div
                  key={a.addon_slug}
                  className="flex items-center justify-between gap-3 p-3 rounded-md border border-gray-200 bg-white"
                >
                  <div className="min-w-0 flex-1">
                    <div className="font-semibold text-sm text-foreground truncate">
                      {a.name}
                      {a.is_custom_override && (
                        <span className="ml-2 text-[10px] uppercase tracking-wide text-purple-600 bg-purple-50 px-1.5 py-0.5 rounded">
                          custom
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-muted-foreground tabular-nums">
                      {t('billing.active_addons.quantity_label', { qty: a.quantity || 1, total: totalFmt })}
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleRemoveAddon(a)}
                    disabled={isRemoving}
                    className="text-xs font-medium text-red-600 hover:bg-red-50 rounded-md px-2 py-1 inline-flex items-center gap-1 disabled:opacity-50"
                  >
                    {isRemoving ? (
                      <>
                        <Loader2 className="h-3 w-3 animate-spin" />
                        ...
                      </>
                    ) : (
                      <>
                        <X className="h-3 w-3" />
                        {t('billing.active_addons.remove_btn', 'Rimuovi')}
                      </>
                    )}
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
