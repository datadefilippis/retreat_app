/**
 * PlansAddonsSection — add-on packs grid for the public PlansPage.
 *
 * v5.8 / Onda 9.G — rewritten to:
 *   · stop relying on `features_display` i18n keys (those were leaking raw
 *     keys to the UI because they were never translated). The add-on
 *     description + addon_provides + max_quantity now form the visible
 *     content, all i18n via dedicated keys.
 *   · clearer visual hierarchy: big metric headline, helper line, badges
 *     for stack + compatibility, prominent CTA.
 *   · explicit compatibility hint (which plans this add-on requires) so
 *     users on Free/Solo see WHY a button is disabled.
 *
 * Self-loading via billingAPI.listAddons. The endpoint pre-decorates
 * each addon with `is_compatible` (vs the org's current plan) and
 * `active_quantity` (so the UI can show "Active: 2x" + the increase
 * button). For free / signed-out / no-stripe-sub users, all addons
 * are shown disabled with a "Available from paid plans" tooltip.
 *
 * Anchor: section id="addons" so /plans#addons auto-scrolls into view.
 *
 * Mounts inside the PlansPage main column. Failures render inline
 * (no impact on the rest of PlansPage's plan cards).
 */
import React, { useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Loader2, Plus, Check, ShoppingBag, Lock, Layers, Zap } from 'lucide-react';
import { billingAPI } from '../api/billing';


// Per-addon visual metadata. Keyed by addon slug — the backend slug stays
// stable across price/name edits, so we can safely hardcode UI overrides.
const ADDON_META = {
  addon_ai_chat_pack:  { icon: Zap,         iconColor: 'text-violet-500', accent: 'border-violet-200' },
  addon_ai_chat_pro:   { icon: Zap,         iconColor: 'text-violet-600', accent: 'border-violet-300' },
  addon_orders_pack:   { icon: ShoppingBag, iconColor: 'text-blue-500',   accent: 'border-blue-200'   },
  addon_extra_store:   { icon: Layers,      iconColor: 'text-emerald-500', accent: 'border-emerald-200' },
};

function _formatPrice(amount, currency = 'EUR') {
  if (amount == null) return '-';
  // Plain "€9 / mese" — no fractional part for whole-euro addons.
  const intPart = Math.round(amount);
  return `${currency === 'EUR' ? '€' : currency + ' '}${intPart}`;
}

// Build the user-facing "what does this add-on give you" headline string
// from the structured `addon_provides` data the backend ships. Falls back
// to the addon name when shape is unexpected.
function _buildProvidesLine(addon, t) {
  const provides = addon.addon_provides || {};
  // shape: { module_key: { feature_key: amount } }
  // We pick the first (module, feature) pair — every add-on declares exactly one.
  for (const moduleKey of Object.keys(provides)) {
    const featureMap = provides[moduleKey] || {};
    for (const featureKey of Object.keys(featureMap)) {
      const amount = featureMap[featureKey];
      // Construct an i18n key like 'billing.addons.provides.ai_assistant.chat'
      const key = `billing.addons.provides.${moduleKey}.${featureKey}`;
      // Defaults intentionally include the amount inline (e.g. "+50 chat AI / mese")
      const fallbackByFeature = {
        chat:           `+${amount} chat AI / mese`,
        digest:         `+${amount} digest AI / mese`,
        orders_monthly: `+${amount} ordini / mese`,
        stores_max:     `+${amount} store`,
      };
      return t(key, { count: amount, defaultValue: fallbackByFeature[featureKey] || `+${amount} ${featureKey}` });
    }
  }
  return addon.name;
}


export default function PlansAddonsSection({ onAddonAdded }) {
  const { t } = useTranslation('settings');
  const [addons, setAddons] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [pendingSlug, setPendingSlug] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await billingAPI.listAddons();
      // API returns array; preserve sort_order
      setAddons(Array.isArray(data) ? data : []);
    } catch (e) {
      setError(e?.response?.data?.detail || e?.message || 'load_failed');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleAdd = async (addon) => {
    if (!addon.is_compatible) return;
    const newQty = (addon.active_quantity || 0) + 1;
    if (newQty > (addon.max_quantity || 1)) return;

    const priceFmt = (newQty * (addon.price_monthly || 0)).toFixed(0);
    const confirmMsg = t('billing.addons.buy_confirm', {
      name: addon.name,
      price: priceFmt,
    });
    // eslint-disable-next-line no-alert
    if (!window.confirm(confirmMsg)) return;

    setPendingSlug(addon.slug);
    try {
      await billingAPI.addAddon(addon.slug, newQty);
      // Onda 24 Phase F — give the webhook a moment, then explicitly
      // reconcile DB with Stripe state via verify-addon-state. Critical
      // in localhost (no `stripe listen` → webhook never arrives) and
      // a useful safety net in production for delayed deliveries.
      // Failure of verify is non-fatal: the next webhook arrival will
      // catch up. We just want to maximize the chance the user sees
      // their addon active immediately.
      setTimeout(async () => {
        try {
          await billingAPI.verifyAddonState();
        } catch (verifyErr) {
          // eslint-disable-next-line no-console
          console.warn('verify-addon-state failed (non-fatal):', verifyErr);
        }
        await load();
        setPendingSlug(null);
        if (onAddonAdded) onAddonAdded(addon.slug, newQty);
      }, 1500);
    } catch (e) {
      setPendingSlug(null);
      const detail = e?.response?.data?.detail;
      const code = detail?.code;
      const msg = detail?.message || e?.message;

      if (code === 'plan_required') {
        // eslint-disable-next-line no-alert
        alert(msg || t('billing.addons.incompatible_free', 'Disponibile dai piani a pagamento'));
      } else if (code === 'stripe_error') {
        // Onda 24 Phase B — surface the actual Stripe error message so
        // the admin can identify what's misconfigured (currency, archived
        // Price, etc.) instead of a generic "purchase failed".
        // eslint-disable-next-line no-alert
        alert(msg || t('billing.addons.stripe_misconfigured', 'L\'add-on non è configurato correttamente. Contatta il supporto.'));
      } else {
        // eslint-disable-next-line no-alert
        alert(msg || t('billing.addons.purchase_error', 'Errore durante l\'acquisto del pack.'));
      }
    }
  };

  // ── Loading / empty / error states ─────────────────────────────────────
  if (loading) {
    return (
      <section id="addons" className="space-y-3 pt-6 border-t">
        <h2 className="text-xl font-bold text-foreground">
          {t('billing.addons.section_title', 'Add-on packs')}
        </h2>
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          {t('billing.addons.loading', 'Caricamento add-on…')}
        </div>
      </section>
    );
  }

  if (error || addons.length === 0) {
    return (
      <section id="addons" className="space-y-3 pt-6 border-t">
        <h2 className="text-xl font-bold text-foreground">
          {t('billing.addons.section_title', 'Add-on packs')}
        </h2>
        <p className="text-sm text-muted-foreground italic">
          {t('billing.addons.empty_state', 'Nessun add-on disponibile per il tuo piano attuale.')}
        </p>
      </section>
    );
  }

  return (
    <section id="addons" className="space-y-5 pt-6 border-t">
      <div className="text-center max-w-2xl mx-auto">
        <h2 className="text-2xl font-bold text-foreground">
          {t('billing.addons.section_title', 'Add-on packs')}
        </h2>
        <p className="text-sm text-muted-foreground mt-2">
          {t(
            'billing.addons.section_subtitle',
            'Estendi una metrica del tuo piano senza upgrade completo. Si attivano sulla subscription esistente.',
          )}
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {addons.map((addon) => {
          const meta = ADDON_META[addon.slug] || { icon: ShoppingBag, iconColor: 'text-gray-500', accent: 'border-gray-200' };
          const Icon = meta.icon;
          const compat = addon.compatible_plans || [];
          const compatList = compat.map((c) => t(`billing.plan_label_${c}`, c)).join(' · ');
          const tooltip = !addon.is_compatible
            ? compatList
              ? t('billing.addons.incompatible_tooltip', { plans: compatList })
              : t('billing.addons.incompatible_free', 'Disponibile dai piani a pagamento')
            : '';
          const isMaxed = addon.is_compatible
            && (addon.active_quantity || 0) >= (addon.max_quantity || 1);
          const isActive = (addon.active_quantity || 0) > 0;
          const isPending = pendingSlug === addon.slug;

          const ctaLabel = isActive
            ? t('billing.addons.increase_btn', '+ Aumenta')
            : t('billing.addons.add_btn', 'Aggiungi al piano');

          // Headline metric (e.g. "+50 chat AI / mese") built from addon_provides.
          const providesLine = _buildProvidesLine(addon, t);

          return (
            <div
              key={addon.slug}
              className={`relative rounded-xl border-2 p-5 flex flex-col gap-3 transition-all bg-white ${
                addon.is_compatible
                  ? `${meta.accent} hover:shadow-lg`
                  : 'border-gray-100 bg-gray-50/60'
              }`}
              title={tooltip}
            >
              {/* Active badge */}
              {isActive && (
                <div className="absolute -top-2.5 right-3 bg-emerald-600 text-white text-[10px] font-semibold px-2 py-0.5 rounded-full shadow-sm">
                  {t('billing.addons.active_label', 'Attivo: {{qty}}×', { qty: addon.active_quantity })}
                </div>
              )}

              {/* Header: icon + name */}
              <div className={`flex items-center gap-2 ${addon.is_compatible ? '' : 'opacity-60'}`}>
                <div className={`flex items-center justify-center h-8 w-8 rounded-lg bg-gray-50 ${meta.iconColor}`}>
                  <Icon className="h-4 w-4" />
                </div>
                <div className="min-w-0 flex-1">
                  <h3 className="text-sm font-bold text-foreground truncate">
                    {addon.name}
                  </h3>
                </div>
              </div>

              {/* Tagline (one-liner positioning) */}
              {addon.tagline && (
                <p className="text-[11px] text-muted-foreground leading-relaxed min-h-[2.4em]">
                  {addon.tagline}
                </p>
              )}

              {/* Big "what you get" line */}
              <div className="rounded-lg bg-gray-50 border border-gray-200 px-3 py-2">
                <div className="text-[10px] uppercase tracking-wide text-muted-foreground font-medium mb-0.5">
                  {t('billing.addons.you_get', 'Cosa ottieni')}
                </div>
                <div className="text-sm font-semibold text-foreground">
                  {providesLine}
                </div>
              </div>

              {/* Price */}
              <div className="flex items-baseline gap-1">
                <span className="text-2xl font-bold text-foreground">
                  {_formatPrice(addon.price_monthly, addon.currency)}
                </span>
                <span className="text-[11px] text-muted-foreground">
                  {t('billing.addons.per_month', '/ mese')}
                </span>
              </div>

              {/* Stack + compatibility hints */}
              <div className="flex flex-col gap-1 text-[10.5px] text-muted-foreground">
                {addon.max_quantity > 1 && (
                  <div className="flex items-center gap-1">
                    <Layers className="h-3 w-3" />
                    <span>{t('billing.addons.stack_hint', { max: addon.max_quantity })}</span>
                  </div>
                )}
                {compatList && (
                  <div className="flex items-center gap-1 leading-snug">
                    <Lock className="h-3 w-3 flex-shrink-0" />
                    <span>{t('billing.addons.requires_plans', 'Richiede: {{plans}}', { plans: compatList })}</span>
                  </div>
                )}
              </div>

              {/* CTA */}
              <div className="mt-auto pt-1">
                {/* Onda 24 Phase E — Stripe-not-configured check has
                    priority over plan-compat check: even on a compatible
                    plan, an addon with no Stripe Price linked cannot be
                    purchased. Renders a distinct "in setup" CTA so admin
                    knows to complete the catalog config. */}
                {addon.purchasable === false && addon.purchasable_reason === 'stripe_not_configured' ? (
                  <button
                    type="button"
                    disabled
                    title={t('billing.addons.cta_setup_pending_hint', 'Stripe Price non ancora configurato dall\'amministratore')}
                    className="w-full py-2 px-3 rounded-lg bg-amber-50 text-amber-700 border border-amber-200 text-sm font-medium inline-flex items-center justify-center gap-1 cursor-not-allowed"
                  >
                    <Lock className="h-3.5 w-3.5" />
                    {t('billing.addons.cta_setup_pending', 'In configurazione')}
                  </button>
                ) : !addon.is_compatible ? (
                  <button
                    type="button"
                    disabled
                    className="w-full py-2 px-3 rounded-lg bg-gray-100 text-gray-400 text-sm font-medium inline-flex items-center justify-center gap-1 cursor-not-allowed"
                  >
                    <Lock className="h-3.5 w-3.5" />
                    {t('billing.addons.cta_locked', 'Aggiorna piano')}
                  </button>
                ) : isMaxed ? (
                  <button
                    type="button"
                    disabled
                    className="w-full py-2 px-3 rounded-lg bg-gray-100 text-gray-500 text-sm font-medium cursor-not-allowed"
                  >
                    <Check className="h-3.5 w-3.5 inline mr-1" />
                    {t('billing.addons.max_reached', { max: addon.max_quantity })}
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={() => handleAdd(addon)}
                    disabled={isPending}
                    className="w-full py-2 px-3 rounded-lg bg-gray-900 text-white text-sm font-semibold hover:bg-gray-800 transition-colors disabled:opacity-50 inline-flex items-center justify-center gap-1.5"
                  >
                    {isPending ? (
                      <>
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        {t('billing.addons.adding', 'Aggiunta in corso…')}
                      </>
                    ) : (
                      <>
                        <Plus className="h-3.5 w-3.5" />
                        {ctaLabel}
                      </>
                    )}
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
