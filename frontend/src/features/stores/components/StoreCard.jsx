/**
 * StoreCard — single-store card for the StoresPage admin grid.
 *
 * 2026-05-19 redesign — inline action buttons (no more kebab)
 * -----------------------------------------------------------
 *
 * The previous layout collapsed every secondary action into a kebab
 * (⋮) dropdown at the top-right. Field feedback was that the merchant
 * had to discover the menu first AND open it before reaching common
 * actions like "Visualizza storefront" or "Apri POS" — those are
 * everyday gestures, not edge cases.
 *
 * New layout promotes ALL kebab actions to first-class inline buttons:
 *
 *  ┌──────────────────────────────────────────────────────────┐
 *  │ 🌐  Store name                                           │
 *  │     [Pubblicato] [Default]                               │
 *  │                                                          │
 *  │  Description, line-clamp-2                               │
 *  │                                                          │
 *  │  📦 12 Prodotti · acme.afianco.app/s/acme  📋            │
 *  │  ────────────────────────────────────────────────────── │
 *  │  [✎ Modifica] [👁 Visualizza] [🚚 Spedizioni]            │
 *  │  [🔒 Privacy] [⊝ Annulla pubblicazione]                  │
 *  └──────────────────────────────────────────────────────────┘
 *
 * Responsive behaviour
 *   · < sm (mobile)        2-column grid, full-width buttons (touch
 *                          target ≥ 36px, fits ≥320px viewport)
 *   · ≥ sm (tablet+)       flex-wrap row, buttons size auto, never
 *                          overflows because the row WRAPS
 *
 * Visual hierarchy
 *   · "Modifica" stays variant="default" (filled primary) — it is
 *     still THE most-used action in 80% of merchant workflows.
 *   · Everything else is variant="outline" — discoverable but visually
 *     subordinated to the primary CTA. This is the Linear / Stripe
 *     Dashboard / Vercel pattern: ONE filled CTA, N outline secondaries.
 *
 * Plan-violation lockout
 *   · ALL action buttons are disabled when ``deactivated_for_plan_violation``
 *     is true. The amber banner CTA "Aggiorna piano" remains the only
 *     reachable affordance — same policy as the previous kebab version.
 *
 * Props (unchanged from the previous redesign — backward-compat with
 * the single call site in StoresPage.js).
 *   store               required Store object
 *   storeProductCount   integer, defaults to 0
 *   visibilityConfig    { icon, labelKey, badge, descKey }
 *   onEdit, onShipping, onGdpr  callbacks (required)
 *   onTogglePublish     callback (only used when slug + visibility=public)
 *   onOpenPos           callback (only used when visibility=pos)
 *   onPlanUpgrade       callback for the amber banner "Aggiorna piano"
 *
 * Translation: receives ``t`` as a prop so it can use the page's
 * "stores" namespace without re-binding useTranslation.
 */

import React from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowUpCircle, Eye, EyeOff, Globe, Lock, Package, Pencil,
  ShoppingCart, Truck, ExternalLink, Share2,
} from 'lucide-react';

import { Card, CardContent } from '../../../components/ui/card';
import { Button } from '../../../components/ui/button';
import StoreBadgeRow from '../../../components/ui/StoreBadgeRow';
import CopyableUrl from '../../../components/ui/CopyableUrl';


export default function StoreCard({
  store,
  storeProductCount = 0,
  visibilityConfig,
  onEdit,
  onShipping,
  onGdpr,
  onTogglePublish,
  onOpenPos,
  onPlanUpgrade,
  // Track E Step 2.3 — share callback (opens ShareStoreModal in parent).
  // Wired through props per modular design (no API call dentro StoreCard).
  onShare,
  t,
}) {
  const vis = visibilityConfig;
  const VisIcon = vis.icon;
  const storeUrl = store.slug
    ? `${window.location.origin}/s/${store.slug}`
    : null;
  const displayHostPath = store.slug
    ? `${window.location.host}/s/${store.slug}`
    : null;

  // v5.8 / Onda 9.K — store deactivated by plan-limit reconciliation.
  const isPlanViolation = store.deactivated_for_plan_violation === true;

  // ── Build the badge list (priority order matters: first 2 win) ─────
  const badges = [
    // Visibility badge always wins position 0 — the most fundamental
    // attribute of the store.
    {
      key: 'visibility',
      label: t(vis.labelKey),
      className: vis.badge,
    },
    // Plan violation is critical when present — bump to position 1.
    isPlanViolation && {
      key: 'plan_violation',
      label: t('plan_violation.badge', 'Limite piano'),
      icon: Lock,
      className: 'bg-amber-200 text-amber-900',
      title: t('plan_violation.badge_tooltip', 'Disattivato per limite piano'),
    },
    // Published / Default badges drop to "+N" tooltip when there are
    // also visibility + plan-violation in front of them.
    store.is_published && !isPlanViolation && {
      key: 'published',
      label: t('status.published'),
      className: 'bg-emerald-100 text-emerald-700',
    },
    store.is_default && {
      key: 'default',
      label: t('status.default'),
      className: 'bg-blue-100 text-blue-700',
    },
  ];

  // ── Build the inline action list (was kebab pre-2026-05-19) ───────
  //
  // Order matters: this is the visual reading order in the actions row.
  // Highest-frequency actions sit closest to "Modifica" (the primary CTA)
  // so the merchant's eye flows naturally left→right by importance.
  //
  //   1. Modifica          — primary, ALWAYS first (built inline below)
  //   2. Visualizza        — frequent: "is my storefront live?" check
  //   3. Apri POS          — frequent for POS-only merchants
  //   4. Spedizioni        — periodic configuration
  //   5. Privacy & GDPR    — one-shot configuration
  //   6. Pubblica/Annulla  — rare, near-irreversible switch (last)
  //
  // Each entry mirrors a previous DropdownMenuItem 1:1 — same handler,
  // same condition, same icon — so behaviour is identical. Only the
  // surface (inline button vs dropdown item) changes.
  const inlineActions = [];

  if (storeUrl && store.is_published) {
    inlineActions.push({
      key: 'view',
      icon: Eye,
      label: t('actions.view'),
      onClick: () =>
        window.open(storeUrl, '_blank', 'noopener,noreferrer'),
    });
  }
  if (store.visibility === 'pos') {
    inlineActions.push({
      key: 'open_pos',
      icon: ShoppingCart,
      label: t('actions.open_pos'),
      onClick: () => onOpenPos?.(store),
    });
  }
  inlineActions.push({
    key: 'shipping',
    icon: Truck,
    label: t('actions.shipping', { defaultValue: 'Spedizioni' }),
    onClick: () => onShipping?.(store),
  });
  inlineActions.push({
    key: 'gdpr',
    icon: Lock,
    label: t('actions.gdpr', { defaultValue: 'Privacy & GDPR' }),
    onClick: () => onGdpr?.(store),
  });
  // Track E Step 2.3 — Condividi action (hosted link + embed code modal)
  inlineActions.push({
    key: 'share',
    icon: Share2,
    label: t('actions.share', { defaultValue: 'Condividi' }),
    onClick: () => onShare?.(store),
  });
  if (store.visibility === 'public' && store.slug) {
    inlineActions.push({
      key: 'toggle_publish',
      icon: store.is_published ? EyeOff : Globe,
      label: store.is_published ? t('actions.unpublish') : t('actions.publish'),
      onClick: () => onTogglePublish?.(store),
    });
  }

  return (
    <Card
      className={
        isPlanViolation
          ? 'border-amber-300 bg-amber-50/40 opacity-80 transition-opacity'
          : (store.is_published
              ? 'border-emerald-200 hover:border-emerald-300 transition-colors'
              : 'hover:border-border transition-colors')
      }
    >
      <CardContent className="py-4 px-4 sm:px-5 space-y-3">
        {/* Plan-violation banner — explain WHY hidden + CTA */}
        {isPlanViolation && (
          <div className="rounded-md bg-amber-100/70 border border-amber-300 px-3 py-2 flex items-start gap-2">
            <Lock className="h-3.5 w-3.5 mt-0.5 text-amber-700 shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-amber-900 leading-snug">
                {t('plan_violation.title', 'Store nascosto: limite del piano superato')}
              </p>
              <p className="text-[11px] text-amber-800 mt-0.5 leading-snug">
                {t(
                  'plan_violation.body',
                  'Lo store è stato disattivato automaticamente perché supera il numero di store del tuo piano attuale. I dati sono conservati e lo store si riattiverà automaticamente quando aggiorni il piano.',
                )}
              </p>
              <button
                type="button"
                onClick={() => onPlanUpgrade?.()}
                className="mt-1.5 inline-flex items-center gap-1 text-[11px] font-semibold text-amber-900 hover:underline"
              >
                <ArrowUpCircle className="h-3 w-3" />
                {t('plan_violation.cta_upgrade', 'Aggiorna piano per riattivare')}
              </button>
            </div>
          </div>
        )}

        {/* ── Header row: visibility icon + title + badges ─────── */}
        {/* No more kebab here — every action is promoted inline at the
            bottom of the card (see actions row below). The header is
            now purely identity: who this store is + how it's classified. */}
        <div className="flex items-start gap-2">
          <VisIcon className="h-4 w-4 mt-0.5 text-muted-foreground shrink-0" />
          <div className="flex-1 min-w-0">
            <h3
              className="text-sm font-semibold leading-tight truncate"
              title={store.name}
            >
              {store.name}
            </h3>
            <StoreBadgeRow
              badges={badges}
              maxVisible={2}
              className="mt-1.5"
            />
          </div>
        </div>

        {/* Description (max 2 lines) */}
        {store.description && (
          <p className="text-xs text-muted-foreground line-clamp-2">
            {store.description}
          </p>
        )}

        {/* Metadata row: product count + storefront URL (or slug hint) */}
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground min-w-0">
          <Link
            to={`/products?store_id=${store.id}`}
            className="inline-flex items-center gap-1 hover:text-foreground transition-colors shrink-0"
          >
            <Package className="h-3 w-3" />
            {t('products', { count: storeProductCount })}
          </Link>

          {storeUrl && store.is_published && (
            <CopyableUrl
              url={storeUrl}
              displayText={displayHostPath}
              size="sm"
              className="max-w-full"
            />
          )}
          {store.slug && !store.is_published && (
            <span className="inline-flex items-center gap-1 truncate min-w-0">
              <ExternalLink className="h-3 w-3 opacity-50 shrink-0" />
              <span className="truncate" title={`/s/${store.slug}`}>
                /s/{store.slug}
              </span>
            </span>
          )}
        </div>

        {/* ── Action row: Modifica + all promoted actions ──────── */}
        {/* Responsive layout:
              · < sm (mobile): grid 2-cols, full-width buttons.
                36px touch target via h-9. Buttons span the card
                edge-to-edge with gap-2 for thumb-friendly spacing.
              · ≥ sm (tablet+): flex-wrap row. Buttons size auto
                (label-driven width). Wraps to a second line on
                narrow tablets / when many actions are present —
                NEVER overflows horizontally, which was the original
                pain point of the inline-actions layout before the
                kebab redesign.
            The visual hierarchy is preserved by variant: ONE filled
            primary ("Modifica") + N outlined secondaries. The eye
            finds the primary CTA immediately regardless of how the
            row wraps. */}
        <div className="grid grid-cols-2 sm:flex sm:flex-wrap gap-2 pt-3 border-t">
          <Button
            variant="default"
            size="sm"
            onClick={() => onEdit?.(store)}
            disabled={isPlanViolation}
            className="h-9 gap-1.5 w-full sm:w-auto"
          >
            <Pencil className="h-3.5 w-3.5 shrink-0" />
            <span className="truncate">{t('actions.edit')}</span>
          </Button>

          {inlineActions.map((a) => {
            const Icon = a.icon;
            return (
              <Button
                key={a.key}
                variant="outline"
                size="sm"
                onClick={a.onClick}
                disabled={isPlanViolation}
                className="h-9 gap-1.5 w-full sm:w-auto"
              >
                <Icon className="h-3.5 w-3.5 shrink-0" />
                <span className="truncate">{a.label}</span>
              </Button>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
