/**
 * StorefrontPage — public-facing product catalog and order request flow.
 *
 * LANGUAGE STRATEGY (Milestone A complete):
 *   System copy (form labels, errors, empty states):
 *     → Uses the `storefront` i18n namespace (`useTranslation('storefront')`).
 *     → Locale resolution flows through `useStorefrontLocaleSync` which
 *       picks the right language from: ?lang=xx > customer.locale >
 *       localStorage[customer_lang_<slug>] > navigator.language >
 *       store.storefront_languages[0]. The resolved locale is always
 *       constrained to the merchant's `storefront_languages` whitelist.
 *
 *   CTA / brand copy (button text, modal descriptions):
 *     → Resolved per transaction_mode through `resolveTransactionModeCopy(t, mode)`.
 *     → Will become merchant-configurable in a future iteration.
 *
 *   Outcome messages (submission results, degraded flow):
 *     → Backend sends semantic codes (transaction_mode, payment_reason).
 *     → Frontend renders text from those codes via i18n.
 */
import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { useParams, Link, useLocation, useNavigate, useNavigationType } from 'react-router-dom';
import useSeoMeta from './lib/useSeoMeta';
import useTrackView from './lib/useTrackView';
import { useTranslation } from 'react-i18next';
import { effectivePlan } from './lib/paymentPlan';
import { storefrontAPI } from '../../api/storefront';
// Wave GDPR-Commerce CG-5 — fetch the merchant's legal status to know
// whether to render the GDPR consent block on checkout.
import { fetchStorefrontLegalMetadata } from '../../services/legalService';
import { customerAuthAPI } from '../../api/customerAuth';
import { publicShippingOptions } from '../../api/shippingOptions';
import { useCheckoutSubmit } from './hooks/useCheckoutSubmit';
import { useStorefrontLocaleSync } from './hooks/useStorefrontLocaleSync';
import { useStoreMeta } from '../../hooks/useStoreMeta';
import useStorefrontCart from './hooks/useStorefrontCart';
import useAvailableCategories from './hooks/useAvailableCategories';
import useDesignTokens from './hooks/useDesignTokens';
// 2026-05-20 — Symmetric marketing checkbox visibility (hides the
// box when the customer is already opted-in, regardless of guest or
// registered). See hooks/useIsMarketingOptedIn.js for the lookup
// strategy (logged-in synchronous derivation vs guest debounced
// public endpoint).
import useIsMarketingOptedIn from '../../hooks/useIsMarketingOptedIn';
import { CATEGORY_BY_SLUG, isKnownCategorySlug } from './categories';
import MarkdownLite from '../../components/MarkdownLite';
import StorefrontHeader from './components/StorefrontHeader';
// Sprint 2 W2.1 — coupon dry-run validation (parity widget E4.1)
import CouponInput from './components/CouponInput';
// Sprint 2 W2.2 — live price preview hook for breakdown discount
import useCouponValidation from './hooks/useCouponValidation';
// `OpenCheckoutButton` import removed in the post-Phase-7 cleanup
// pass — StorefrontPage now uses a single strengthened cart icon
// instead of the dedicated CTA pill. The component still ships and
// is used by the landing pages (EventLandingPage, ProductLandingPage,
// ReservationLandingPage, etc.) where the "Vai al checkout" CTA
// surfaces as a sticky card when the visitor drilled in with a
// non-empty cart.
// Phase 7.3 — cards + ProductGrid extracted into co-located modules so
// the upcoming CategoryPage (Phase 7.5) can reuse the same rendering
// path with a pre-filtered product subset. fmtPrice / fmtOccDate /
// computeRentalMultiplier / resolveTransactionModeCopy are re-exported
// from StorefrontCards so the OrderSummary block below keeps working.
import ProductGrid from './ProductGrid';
import StoreHome from './components/StoreHome';
import StoreAbout from './components/StoreAbout';
import {
  BookingCalendarModal,
  fmtPrice,
  fmtOccDate,
  computeRentalMultiplier,
  resolveTransactionModeCopy,
} from './components/StorefrontCards';
import { useCustomerAuth } from '../../context/CustomerAuthContext';
import { resolveDominantMode } from '../../constants/itemTypes';
import { formatAmount } from '../../utils/currency';
import { User, ShoppingCart } from 'lucide-react';
import { toast } from 'sonner';
import { BRAND_NAME } from '../../config/brand';

// `resolveTransactionModeCopy` and `fmtPrice` moved to
// components/StorefrontCards.jsx (Phase 7.3) so the new ProductGrid
// + CategoryPage can use them without re-importing this whole file.
// Re-imported at the top — same callers, identical behaviour.

// Password strength check mirrors backend policy (customer_auth validate_password_strength):
// 12+ chars, at least one uppercase, one lowercase, one digit.
//
// Returns { ok: bool, score: 0..4, reasonCodes: [string] } — the reason
// codes are stable identifiers the caller renders via
// `t('storefront:password.<code>')`. Decoupling the validator from i18n
// keeps it pure (no React/hook dependency) so it can be called from
// useMemo/render paths without coupling, AND lets the strings travel
// through future locales without touching this function.
function computePasswordStrength(pwd) {
  if (!pwd) return { ok: false, score: 0, reasonCodes: ['enter'] };
  const reasonCodes = [];
  if (pwd.length < 12) reasonCodes.push('minLength');
  if (!/[A-Z]/.test(pwd)) reasonCodes.push('upper');
  if (!/[a-z]/.test(pwd)) reasonCodes.push('lower');
  if (!/[0-9]/.test(pwd)) reasonCodes.push('digit');
  let score = 0;
  if (pwd.length >= 12) score++;
  if (pwd.length >= 16) score++;
  if (/[A-Z]/.test(pwd) && /[a-z]/.test(pwd)) score++;
  if (/[0-9]/.test(pwd) && /[^A-Za-z0-9]/.test(pwd)) score++;
  return { ok: reasonCodes.length === 0, score, reasonCodes };
}


/* ── Order Summary ─────────────────────────────────────────────────────────── */

/**
 * Shared trash icon for cart-remove actions. Inline SVG to avoid adding a
 * lucide-react import in this file (already heavy on dependencies) and to
 * match the small-icon size used elsewhere in the storefront.
 */
function TrashIcon({ size = 14 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M3 6h18" />
      <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
      <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
    </svg>
  );
}


function OrderSummary({ items, products, selectedOccurrences, selectedTiers, rentalDates, bookingSlots, currency, shipping, onRemove, onQtyChange, couponDiscount = 0, couponLabel = null }) {
  const { t, i18n } = useTranslation('storefront');
  if (items.length === 0) return null;
  const hasInquiry = items.some(it => products.find(pp => pp.id === it.product_id)?.price_mode === 'inquiry');
  // Resolve the effective unit price following the same precedence the
  // backend applies at order_service.create_order: tier.price (most
  // specific) > occurrence.price_override > product.unit_price. Keeps
  // the cart total honest when the selection came from the event
  // landing page handoff.
  const resolveUnitPrice = (it) => {
    const p = products.find(pp => pp.id === it.product_id);
    if (!p || p.price_mode === 'inquiry') return { p, price: 0, isInq: true };
    const occ = selectedOccurrences?.[it.product_id];
    // F3 Onda 10 — selectedItems now carries ticket_tier_id per line;
    // prefer that over the multi-tier map on selectedTiers. Fallback to
    // the legacy single-entry map {tierId: qty}.
    let tier = null;
    if (it.ticket_tier_id && occ?.tiers) {
      tier = occ.tiers.find(t => t.id === it.ticket_tier_id);
    } else {
      const tierMap = selectedTiers?.[it.product_id];
      if (tierMap && typeof tierMap === 'object' && occ?.tiers) {
        const tierIds = Object.keys(tierMap);
        if (tierIds.length === 1) tier = occ.tiers.find(t => t.id === tierIds[0]);
      }
    }
    // F5 Onda 12 — service option price override
    let serviceOption = null;
    if (it.service_option_id && Array.isArray(p.service_options)) {
      serviceOption = p.service_options.find(o => o.id === it.service_option_id);
    }
    const price = serviceOption?.price != null
      ? serviceOption.price
      : (tier?.price != null
          ? tier.price
          : (occ?.price_override != null ? occ.price_override : (p.unit_price || 0)));
    return { p, price, isInq: false, tier, occ, serviceOption };
  };
  const total = items.reduce((sum, it) => {
    const { p, price, isInq } = resolveUnitPrice(it);
    if (isInq) return sum;
    const rentalMult = p?.item_type === 'rental'
      ? computeRentalMultiplier(rentalDates?.[it.product_id], p.rental_unit)
      : 1;
    return sum + price * it.quantity * rentalMult;
  }, 0);
  return (
    <div className="rounded-xl border bg-white p-4 shadow-sm">
      <h3 className="font-semibold mb-2">{t('storefront:summary.title')}</h3>
      <ul className="space-y-1 text-sm">
        {items.map(it => {
          const resolved = resolveUnitPrice(it);
          const { p, price, isInq, tier, occ, serviceOption } = resolved;
          const rentalMult = p?.item_type === 'rental'
            ? computeRentalMultiplier(rentalDates?.[it.product_id], p?.rental_unit)
            : 1;
          const lineLabel = p?.item_type === 'rental' && rentalMult > 1
            ? t('storefront:summary.rentalLine', { name: p?.name, count: rentalMult, unit: p?.rental_unit || t('storefront:rental.unitFallback') })
            : t('storefront:summary.qtyLine', { name: p?.name, count: it.quantity });
          return (
            <li key={`${it.product_id}:${it.ticket_tier_id || it.service_option_id || 'base'}`}>
              <div className="flex justify-between items-start gap-2">
                <span className="flex-1 min-w-0">{lineLabel}{tier ? ` — ${tier.label}` : (serviceOption ? ` — ${serviceOption.label}` : '')}</span>
                <span className="font-medium whitespace-nowrap">{isInq ? t('storefront:summary.onRequest') : fmtPrice(price * it.quantity * rentalMult, currency)}</span>
                {/* Fix qty (4/7/2026) — una persona prenota per 2: la
                    quantità si corregge QUI, senza tornare alla landing.
                    Solo per righe a quantità semplice (no tier/rental/
                    slot: quelle hanno i loro selettori dedicati). */}
                {onQtyChange && !it.ticket_tier_id && !it.service_option_id
                  && ['event_ticket', 'physical', 'digital'].includes(p?.item_type) && (
                  <span className="shrink-0 inline-flex items-center border rounded-md overflow-hidden"
                        aria-label={t('storefront:summary.qtyAria', { name: p?.name })}>
                    <button type="button"
                      onClick={() => onQtyChange(it.product_id, Math.max(1, it.quantity - 1))}
                      className="px-1.5 py-0.5 text-xs hover:bg-gray-100 disabled:opacity-40"
                      disabled={it.quantity <= 1}>−</button>
                    <span className="px-1.5 text-xs font-semibold tabular-nums">{it.quantity}</span>
                    <button type="button"
                      onClick={() => onQtyChange(it.product_id, Math.min(99, it.quantity + 1))}
                      className="px-1.5 py-0.5 text-xs hover:bg-gray-100">+</button>
                  </span>
                )}
                {onRemove && (
                  <button
                    type="button"
                    onClick={() => onRemove(it.product_id)}
                    className="shrink-0 text-gray-400 hover:text-red-600 transition-colors p-0.5 -mr-1"
                    aria-label={t('storefront:summary.removeAria', { name: p?.name || t('storefront:summary.removeFallbackName') })}
                    title={t('storefront:summary.removeTitle')}
                  >
                    <TrashIcon />
                  </button>
                )}
              </div>
              {tier && (
                <p className="text-xs text-gray-400 ml-1">{t('storefront:summary.tierLine', { label: tier.label })}</p>
              )}
              {serviceOption && (
                <p className="text-xs text-gray-400 ml-1">{t('storefront:summary.optionLine', { label: serviceOption.label })}</p>
              )}
              {occ && (
                <p className="text-xs text-gray-400 ml-1">{fmtOccDate(occ.start_at, i18n.language)}</p>
              )}
              {rentalDates?.[it.product_id]?.from && (
                <p className="text-xs text-gray-400 ml-1">
                  {new Date(rentalDates[it.product_id].from + 'T00:00').toLocaleDateString(i18n.language, { day: 'numeric', month: 'short' })}
                  {rentalDates[it.product_id].to
                    ? ` → ${new Date(rentalDates[it.product_id].to + 'T00:00').toLocaleDateString(i18n.language, { day: 'numeric', month: 'short' })}`
                    : ''}
                </p>
              )}
              {bookingSlots?.[it.product_id]?.date && bookingSlots[it.product_id]?.start && (() => {
                const bs = bookingSlots[it.product_id];
                const fmtDay = (iso) => new Date(iso + 'T12:00').toLocaleDateString(i18n.language, { weekday: 'short', day: 'numeric', month: 'short' });
                const crossDay = bs.date_end && bs.date_end !== bs.date;
                return (
                  <p className="text-xs text-gray-400 ml-1">
                    {crossDay
                      ? <>{fmtDay(bs.date)} {bs.start} → {fmtDay(bs.date_end)} {bs.end}</>
                      : <>{fmtDay(bs.date)} {bs.start}–{bs.end}</>}
                  </p>
                );
              })()}
            </li>
          );
        })}
      </ul>
      {/* Shipping line — rendered only when the caller resolved a shipping
          cost for the current fulfillment choice. For inquiry-priced carts
          the total remains a "stima" and the shipping row is suppressed to
          avoid implying a commitment before the merchant confirms. */}
      {!hasInquiry && shipping && shipping.active && (
        <div className="border-t mt-3 pt-3 space-y-1 text-sm">
          <div className="flex justify-between text-gray-700">
            <span>
              {t('storefront:summary.shipping')}
              {shipping.label ? <span className="text-gray-500"> — {shipping.label}</span> : null}
            </span>
            <span className="font-medium">
              {shipping.cost > 0
                ? fmtPrice(shipping.cost, currency)
                : <span className="text-green-700 font-semibold">{t('storefront:summary.shippingFree')}</span>}
            </span>
          </div>
          {shipping.addMoreForFree > 0 && (
            <p className="text-[11px] text-gray-500">
              {t('storefront:summary.addMoreForFree', { amount: fmtPrice(shipping.addMoreForFree, currency) })}
            </p>
          )}
        </div>
      )}
      {/* Sprint 2 W2.2 — Live coupon discount line (parity widget E4.1).
          Renders solo quando coupon valid + discountAmount > 0. Hook
          useCouponValidation upstream lo calcola debounced 350ms. */}
      {!hasInquiry && couponDiscount > 0 && (
        <div className="border-t mt-3 pt-3 space-y-1 text-sm">
          <div className="flex justify-between text-emerald-700">
            <span>
              {t('storefront:summary.couponDiscount', 'Sconto coupon')}
              {couponLabel ? <span className="text-gray-500"> — {couponLabel}</span> : null}
            </span>
            <span className="font-medium">-{fmtPrice(couponDiscount, currency)}</span>
          </div>
        </div>
      )}
      <div className="border-t mt-3 pt-3 flex justify-between font-bold">
        <span>{hasInquiry ? t('storefront:summary.subtotalEstimate') : t('storefront:summary.totalEstimate')}</span>
        <span>{fmtPrice(
          Math.max(0, total + (shipping?.active ? shipping.cost : 0) - (couponDiscount || 0)),
          currency,
        )}</span>
      </div>
      {/* Fix caparra (4/7/2026) — se l'ordine ha un piano acconto, dirlo
          QUI: senza questa riga il cliente vede "Totale 1600€" e crede di
          pagarlo subito (Stripe chiede la caparra giusta, ma la fiducia è
          già persa). Stesso estimator della landing (effectivePlan) sulla
          stessa base del backend: totale ordine, piano della prima riga
          evento (create_schedule_for_new_order fa identico). */}
      {!hasInquiry && (() => {
        const evIt = items.find(it => {
          const p = products.find(pp => pp.id === it.product_id);
          return p?.item_type === 'event_ticket' && p?.payment_plan && selectedOccurrences?.[it.product_id];
        });
        if (!evIt) return null;
        const p = products.find(pp => pp.id === evIt.product_id);
        const occ = selectedOccurrences[evIt.product_id];
        const netTotal = Math.max(0, total + (shipping?.active ? shipping.cost : 0) - (couponDiscount || 0));
        const ep = effectivePlan(p.payment_plan, netTotal, occ?.start_at);
        if (ep.mode !== 'deposit') return null;
        const dueDate = ep.balanceDueDate
          ? ep.balanceDueDate.toLocaleDateString(i18n.language, { day: 'numeric', month: 'long', year: 'numeric' })
          : '';
        return (
          <div className="mt-3 rounded-lg bg-emerald-50 border border-emerald-200 p-3">
            <div className="flex justify-between items-baseline font-bold text-emerald-800">
              <span>{t('storefront:summary.depositToday')}</span>
              <span>{fmtPrice(ep.depositMinor / 100, currency)}</span>
            </div>
            <p className="text-xs text-emerald-700 mt-1">
              {t('storefront:summary.depositBalance', {
                amount: fmtPrice(ep.balanceMinor / 100, currency),
                date: dueDate,
              })}
            </p>
          </div>
        );
      })()}
    </div>
  );
}

/* ── Main Storefront Page ──────────────────────────────────────────────────── */

export default function StorefrontPage({ aboutMode = false } = {}) {
  // Phase 7.5 — `category` is set when mounted on `/s/:slug/c/:category`,
  // null when mounted on the bare `/s/:slug` root. Two different routes
  // mount the SAME component (App.js); the component branches on this
  // value to either filter the grid OR redirect to the first non-empty
  // category once the catalog has loaded.
  const { slug, category } = useParams();
  // VT2 — visita allo store per lo specchietto Visibilità (ping 3s)
  useTrackView('store', slug);
  const location = useLocation();
  const navigate = useNavigate();
  // L2 — 'POP' = back/forward del browser: serve alla guardia
  // anti-vetrina per distinguere il ritorno accidentale sull'entry
  // /s/:slug dalle visite deliberate (PUSH) alla vetrina.
  const navType = useNavigationType();
  const { t, i18n } = useTranslation('storefront');
  const { customer, isCustomerAuthenticated, login: customerLogin, signup: customerSignup } = useCustomerAuth();
  const [catalog, setCatalog] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);


  // Phase 1 hook: drives i18n.language from the resolved storefront locale.
  // Mounts once StorefrontPage is on screen; the resolved locale picks
  // ?lang=xx > customer.locale > localStorage > navigator.language >
  // store.storefront_languages[0]. While `catalog` is loading the hook
  // emits a stable fallback ('it') so the first paint is consistent.
  useStorefrontLocaleSync({
    storeSlug: slug,
    supportedLanguages: catalog?.storefront_languages,
  });

  // S7 (SEO_MASTER_PLAN) — SOLO il JSON-LD LocalBusiness: title/
  // description/canonical li governa già l'effetto Phase 7.6 qui sotto
  // (due writer sul title si pestano — lezione imparata sul campo).
  useSeoMeta({
    jsonLd: (catalog?.store_info?.display_name || catalog?.org_name) ? {
      '@context': 'https://schema.org',
      '@type': 'LocalBusiness',
      name: catalog?.store_info?.display_name || catalog?.org_name,
      url: `${window.location.origin}/s/${slug}`,
      ...(catalog?.store_info?.logo_url ? { image: catalog.store_info.logo_url } : {}),
      ...(catalog?.store_info?.store_description
        ? { description: String(catalog.store_info.store_description).slice(0, 300) } : {}),
    } : undefined,
  });

  // Phase 7.4 — derive the list of categories with ≥1 published product
  // from the loaded catalog. The hook is memoized on
  // `catalog?.products` reference so it only recomputes when products
  // actually change (not on cart-state updates). Passed to
  // StorefrontHeader which renders a CategoryNav strip when the list
  // has ≥2 entries — single-category stores stay header-only.
  const availableCategories = useAvailableCategories(catalog);

  // Phase 9 — design tokens (radius, density, font, accent, header
  // style, card style). The hook resolves the tokens with defaults
  // and emits a CSS-variables dict that we pour onto the root <div>
  // — every nested component can then read `var(--sf-radius)` etc.
  // without prop-drilling.
  //
  // Logo refinement — the hook also exposes `logo` ({height, fit,
  // showStoreName}) as direct props since the bool can't fit in a
  // CSS variable and inline px values render simpler.
  const { cssVars: designCssVars, logo: designLogo } = useDesignTokens(catalog);

  // Phase 7.5 — products filtered by active category.
  //
  // Must be computed UP HERE (before the loading / error early returns)
  // because `useMemo` is a React hook and the rules-of-hooks forbid
  // calling it conditionally.
  //
  // `categoryDef` resolves the URL slug to the canonical CATEGORY_DEFS
  // entry. When `category` param is null (root `/s/:slug` page during
  // the brief window before redirect) categoryDef stays null and the
  // grid shows ALL products. The cart / checkout flow always reads
  // from `catalog.products` directly so off-category items added
  // earlier are not lost when the visitor navigates between categories.
  const categoryDef = category ? CATEGORY_BY_SLUG[category] : null;
  const products = useMemo(() => {
    const all = catalog?.products || [];
    if (!categoryDef) return all;
    const allowed = new Set(categoryDef.itemTypes);
    return all.filter(p => allowed.has(p?.item_type));
  }, [catalog?.products, categoryDef]);

  // Phase 7.5 — root-URL redirect.
  //
  // When the visitor lands on `/s/:slug` (no `:category` in the URL),
  // and the catalog has finished loading, and at least one category
  // has products, replace the URL with `/s/:slug/c/<first-category>`.
  // First-category resolution follows the fixed order from
  // CATEGORY_DEFS (eventi → corsi → servizi → affitti → prodotti);
  // useAvailableCategories already filters to non-empty entries in that
  // order, so taking `[0]` lands on the first one with products.
  //
  // Why `replace: true` — the visitor types `/s/:slug` expecting a
  // home page; the redirect should NOT push a history entry that
  // would create a back-button trap (Back → back to /s/:slug → instantly
  // redirected forward again).
  //
  // Why this is safe with no products — when availableCategories is
  // empty, the redirect skips. The page then renders the existing
  // empty-state UI ("no products published yet"), unchanged.
  useEffect(() => {
    if (aboutMode) return;                      // S3: chi-siamo, niente redirect
    if (category) return;                       // already on a category page
    if (loading) return;                        // wait for catalog
    if (!availableCategories || availableCategories.length === 0) return;
    // T1 (6/7) — bio-first: la root e' SEMPRE la pagina Chi-siamo
    // (identita' prima del catalogo). Nessun redirect.
  }, [category, loading, availableCategories, catalog, slug, navigate]);

  // T1 — la root rende il Chi-siamo (bio-first, decisione founder)
  const isHome = false;
  const isRootAbout = !category && !loading;

  // Phase 7.5 — unknown-category guard.
  //
  // If the visitor hits `/s/:slug/c/<garbage>` (typo, stale bookmark,
  // category slug that was removed in a future redesign), bounce them
  // back to the storefront root which will redirect to the first
  // available category. Keeps URLs self-healing.
  useEffect(() => {
    if (!category) return;
    if (isKnownCategorySlug(category)) return;
    navigate(`/s/${slug}`, { replace: true });
  }, [category, slug, navigate]);

  // Wave GDPR-Commerce CG-5 — fetch the per-store legal metadata so
  // we know whether to render the GDPR consent block on checkout.
  // We only need ``status`` + ``version_string`` + ``display_locale``
  // here; the body content is fetched on demand from the linked pages.
  //
  // Fail-soft: any network/server error leaves ``legalMeta`` at null,
  // which makes the checkout flow fall back to legacy (no GDPR block).
  // Better to silently degrade than to block all checkouts because of
  // a metadata fetch hiccup.
  useEffect(() => {
    if (!slug) return;
    let active = true;
    fetchStorefrontLegalMetadata(slug).then(
      (meta) => { if (active) setLegalMeta(meta); },
      (err) => { console.warn('CG-5: legal metadata fetch failed:', err); }
    );
    return () => { active = false; };
  }, [slug]);

  // Phase 7.6 — per-category SEO meta tags.
  //
  // Updates document.title, <meta name="description">, og:title,
  // og:description, and <link rel="canonical"> based on:
  //   - the active category (categoryDef)
  //   - the active locale (i18n.language, indirectly via the t() call)
  //   - the store's branding (catalog.store_info)
  //
  // On the storefront root (no categoryDef) the title is the store's
  // SEO title. On a category page it becomes
  //   "<Category Label> — <Store Name>"
  // so "Servizi — Centro Benessere Lugano" / "Services — Centro Benessere
  // Lugano" / etc. The category label is fully translated via i18n.
  //
  // Why a separate effect: pre-Phase-7.6 the meta tags were set ONCE
  // inside the catalog `load()` async block. That meant:
  //   - Switching language didn't update the title
  //   - Navigating between categories didn't update the title either
  // Both are bad for SEO + bad for tab UX (visitor sees stale title
  // in the browser tab strip). This effect re-runs on every relevant
  // change.
  useEffect(() => {
    if (!catalog) return;
    const si = catalog.store_info;
    const storeName = si?.seo_title
      || si?.display_name
      || catalog.org_name
      || t('storefront:catalog.seoFallback');

    // Title: "<Category> — <Store>" on category pages, just "<Store>"
    // on the storefront root. Em dash matches Apple HIG / common
    // marketing-page conventions; tab strip rendering trims long
    // titles gracefully either way.
    const pageTitle = categoryDef
      ? `${t(categoryDef.labelKey)} — ${storeName}`
      : storeName;
    document.title = pageTitle;

    // Description follows the same shape: category-specific hint
    // (which already takes {{org}} interpolation from Phase 7.2) on
    // category pages, store seo_description otherwise.
    const description = categoryDef
      ? t(categoryDef.emptyHintKey, { org: catalog.org_name })
        // emptyHint reads as a positive marketing line for non-empty
        // categories too ("X non ha eventi" sounds odd — but on
        // category pages the user only sees it when 0 products are
        // here, otherwise the products themselves are the page).
        // For non-empty pages we'd ideally have a dedicated SEO line;
        // keeping the emptyHint as a placeholder is acceptable until
        // a future Phase 8 dedicates a `seo_description` per category.
      : si?.seo_description || si?.store_description || `Catalogo ${storeName}`;

    // <meta name="description"> — primary search-result snippet.
    let metaDesc = document.querySelector('meta[name="description"]');
    if (!metaDesc) {
      metaDesc = document.createElement('meta');
      metaDesc.setAttribute('name', 'description');
      document.head.appendChild(metaDesc);
    }
    metaDesc.content = description;

    // Open Graph — social preview cards.
    const upsertOg = (property, content) => {
      let el = document.querySelector(`meta[property="${property}"]`);
      if (!el) {
        el = document.createElement('meta');
        el.setAttribute('property', property);
        document.head.appendChild(el);
      }
      el.content = content;
    };
    upsertOg('og:title', pageTitle);
    upsertOg('og:description', description);

    // <link rel="canonical"> — points search engines at the
    // category-specific URL when on /c/:category, otherwise the bare
    // /s/:slug. Prevents duplicate-content scoring when the visitor
    // shares ?utm_* parameters or other tracking junk.
    let canonical = document.querySelector('link[rel="canonical"]');
    if (!canonical) {
      canonical = document.createElement('link');
      canonical.setAttribute('rel', 'canonical');
      document.head.appendChild(canonical);
    }
    const canonicalPath = categoryDef
      ? `/s/${slug}/c/${categoryDef.slug}`
      : `/s/${slug}`;
    canonical.href = window.location.origin + canonicalPath;
  }, [catalog, categoryDef, slug, t, i18n.language]);

  // ── Cart state — single source of truth via useStorefrontCart ──────────
  //
  // The hook owns the 10 product-scoped state slices, the sessionStorage
  // hydrate/persist cycle, and the 5-second undo-remove flow. Extracted
  // (Phase 7.1) so the new CategoryPage at /s/:slug/c/:category can use
  // identical cart logic without duplicating ~150 lines of state plumbing.
  // See hooks/useStorefrontCart.js for the full contract.
  //
  // `productsLookup` lets the hook resolve a product name for the
  // remove-toast even when this page renders a SUBSET of products
  // (CategoryPage filters but the cart can still contain off-category
  // items added on a previous page navigation).
  const {
    quantities, setQuantities,
    selectedOccurrences, setSelectedOccurrences,
    selectedTiers, setSelectedTiers,
    rentalDates, setRentalDates,
    bookingSlots, setBookingSlots,
    attendeeDetails, setAttendeeDetails,
    orderFieldsData, setOrderFieldsData,
    selectedServiceOptions, setSelectedServiceOptions,
    selectedServiceSlots, setSelectedServiceSlots,
    selectedExtraSelections, setSelectedExtraSelections,
    removeFromCart, undoRemoveFromCart, clearCartSnapshot,
  } = useStorefrontCart({
    slug,
    t,
    productsLookup: catalog?.products,
  });

  // F4 Onda 11 — T&C acceptance state. PAGE-LOCAL (not part of the
  // sessionStorage snapshot) because the checkbox state should reset
  // on every page mount — a returning visitor must re-affirm.
  const [termsAccepted, setTermsAccepted] = useState(false);
  const [termsExpanded, setTermsExpanded] = useState(false);

  // ── Wave GDPR-Commerce CG-5 (2026-05-19) — per-order consent state ──
  //
  // ``legalMeta`` is the response of GET /api/legal/storefront/<slug>/metadata.
  // Used to decide whether to RENDER the GDPR consent block on the
  // checkout form. If the merchant has not published their per-store
  // legal docs (status="not_configured" / "draft"), this stays null and
  // the block does NOT render — checkout proceeds via the legacy T&C
  // flow only.
  //
  // Three local booleans for the new checkboxes. Reset on every page
  // mount (same intent as termsAccepted above).
  const [legalMeta, setLegalMeta] = useState(null);
  const [gdprTermsAccepted, setGdprTermsAccepted] = useState(false);
  const [gdprPrivacyAccepted, setGdprPrivacyAccepted] = useState(false);
  const [gdprMarketingAccepted, setGdprMarketingAccepted] = useState(false);

  // Cache slot search results per product
  const [serviceSlotsByProduct, setServiceSlotsByProduct] = useState({});
  const [availableSlots, setAvailableSlots] = useState(null); // null | [{date, day_name, slots}]
  const [formOpen, setFormOpen] = useState(false);
  // (Removed `cartExpanded` state — the mini-cart bar that used it
  // was deleted in the post-Phase-7 cleanup pass. Cart review now
  // happens inside the checkout modal's OrderSummary.)
  const [form, setForm] = useState({
    name: '', email: '', phone: '', notes: '',
    fulfillment_mode: '',
    // Structured shipping address. Replaces the legacy single textarea.
    // Submitted as `shipping_address_details` — the backend synthesizes
    // the flattened `shipping_address` string server-side.
    shipping_address_details: {
      recipient_name: '',
      line1: '',
      civic: '',
      postal_code: '',
      city: '',
      province: '',
      country: 'IT',
    },
    fulfillment_notes: '',
    coupon_code: '',
    shipping_option_id: '',
  });
  // Shipping options resolved by the backend for this store. Empty list is
  // a legitimate state (merchant hasn't configured any) — the checkout
  // surfaces a banner in that case so the customer knows to get in touch.
  const [shippingOptions, setShippingOptions] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(null); // null | { transaction_mode, order_status, message, registered?: bool }
  // Shared checkout submitter (unifies the Stripe redirect path with
  // EventLandingPage). `submitting` above still drives the cart UI
  // loading state since it's woven into the pre-submit registration
  // step; the hook's own submitting flag is unused here on purpose.
  const { submit: submitCheckout } = useCheckoutSubmit();

  // 2026-05-20 — Marketing checkbox visibility resolver.
  // Logged-in path: synchronous from customer.accepted_marketing_at.
  // Guest path: debounced public lookup on form.email change.
  // The hook returns isOptedIn=false when "unknown" (network glitch,
  // email empty/invalid, lookup never ran) so the default behaviour
  // is to KEEP showing the checkbox — never hide it on uncertainty.
  const marketingStatus = useIsMarketingOptedIn({
    customer,
    isAuthenticated: isCustomerAuthenticated,
    email: form.email,
    slug,
  });

  // Optional ecommerce registration during checkout (Fase C1).
  // Strictly scoped to the storefront flow — NEVER touches admin auth.
  // Account creation is handled by POST /api/customer-auth/signup (org-scoped via slug).
  const [wantRegister, setWantRegister] = useState(false);
  // K1 — contesto MARKETPLACE (arrivo dalla landing directory): il
  // checkout e' l'unica cosa che l'utente deve vedere; alla chiusura
  // si torna alla landing. Il flag persiste in sessionStorage per la
  // success page (redirect Stripe = full reload).
  const [mktpCheckout, setMktpCheckout] = useState(null);   // {returnTo} | null
  const [regPassword, setRegPassword] = useState('');
  const [regPasswordConfirm, setRegPasswordConfirm] = useState('');
  const [showRegPassword, setShowRegPassword] = useState(false);

  // Auto-fill form from customer account
  useEffect(() => {
    if (isCustomerAuthenticated && customer) {
      setForm(prev => ({
        ...prev,
        name: prev.name || customer.name || '',
        email: prev.email || customer.email || '',
      }));
    }
  }, [isCustomerAuthenticated, customer]);

  // NOTE: the `useEffect` that forces `wantRegister=true` when the cart
  // contains a course has been moved below — after `requiresCustomerAccount`
  // is declared (see the useMemo further down the file). Referencing a
  // `const` before its declaration triggers a TDZ ReferenceError that
  // crashes the page at first render.

  // Fetch availability for booking products (next 30 days — max allowed by backend)
  const loadAvailability = useCallback(async (durationMinutes, productId) => {
    if (!slug) return;
    try {
      const today = new Date();
      const from = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
      const end = new Date(today); end.setDate(end.getDate() + 30);
      const to = `${end.getFullYear()}-${String(end.getMonth() + 1).padStart(2, '0')}-${String(end.getDate()).padStart(2, '0')}`;
      const res = await storefrontAPI.getAvailability(slug, from, to, durationMinutes, productId);
      setAvailableSlots(res.data?.available || []);
    } catch { setAvailableSlots([]); }
  }, [slug]);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await storefrontAPI.getCatalog(slug, (i18n.language || 'it').slice(0, 2));
        setCatalog(res.data);
        // Shipping options (non-blocking) — fetched once per store.
        // Empty array on failure keeps the catalog usable; the checkout
        // surfaces a warning only if the customer actually tries to buy
        // physical items without configured options.
        try {
          const shipRes = await publicShippingOptions.get(slug);
          setShippingOptions(shipRes.data?.options || []);
        } catch {
          setShippingOptions([]);
        }
        // SEO meta tags are now set by the dedicated useEffect below
        // (Phase 7.6) so they react to category navigation and locale
        // switches without re-fetching the catalog.

        // Fetch availability if there are booking products
        const bookingProduct = (res.data?.products || []).find(p => p.item_type === 'booking');
        if (bookingProduct) loadAvailability(bookingProduct.slot_duration_minutes || null, bookingProduct.id);
      } catch (err) {
        setError(err?.response?.status === 404
          ? t('storefront:errors.catalogNotFound')
          : t('storefront:errors.catalogLoadError'));
      } finally { setLoading(false); }
    };
    load();
  }, [slug, i18n.language]);

  // Consolidation: hydrate cart from landing-page hand-off.
  //
  // EventLandingPage navigates here with `state: { preloadCart }` after
  // the user has selected tier + qty on /e/:org_slug/:slug. We resolve
  // the product + occurrence from the loaded catalog (not from the
  // incoming state, to avoid trusting stale data) and populate the
  // same state the inline ProductCard would have populated. Then we
  // open the checkout dialog straight away so the user lands on the
  // form with one selection already in the cart.
  //
  // `window.history.replaceState({}, ...)` clears the Router state so
  // a refresh of /s/:slug doesn't re-trigger the hydration + dialog.
  useEffect(() => {
    const preload = location.state?.preloadCart;
    if (!preload || !catalog?.products) return;
    const product = (catalog.products || []).find(p => p.id === preload.productId);
    if (!product) return;  // catalog does not include the product (hidden?) — bail silently
    const occurrence = preload.occurrenceId
      ? (product.occurrences || []).find(o => o.id === preload.occurrenceId)
      : null;
    const qty = Math.max(1, Number(preload.qty) || 1);

    // F3 Onda 10 — hydration accepts both legacy `{tierId, qty}` and the
    // new `{tier_quantities: {tierId: qty, ...}}` shape. The multi-tier
    // map lands directly in selectedTiers; legacy is converted to a
    // one-entry map so downstream code treats both uniformly.
    let tierMap = null;
    if (preload.tier_quantities && typeof preload.tier_quantities === 'object') {
      tierMap = {};
      for (const [tid, q] of Object.entries(preload.tier_quantities)) {
        const n = Math.max(0, Number(q) || 0);
        if (n > 0) tierMap[tid] = n;
      }
    } else if (preload.tierId) {
      tierMap = { [preload.tierId]: qty };
    }
    // Total qty for the cart badge: multi-tier sum or legacy qty
    const totalQty = tierMap
      ? Object.values(tierMap).reduce((a, b) => a + b, 0)
      : qty;
    setQuantities(q => ({ ...q, [product.id]: totalQty }));
    if (occurrence) setSelectedOccurrences(o => ({ ...o, [product.id]: occurrence }));
    if (tierMap) setSelectedTiers(t => ({ ...t, [product.id]: tierMap }));

    // Onda 13 — service preload: option_id + slot from ProductLandingPage
    if (preload.service_option_id) {
      setSelectedServiceOptions(prev => ({ ...prev, [product.id]: preload.service_option_id }));
    }
    if (preload.service_slot?.date) {
      setSelectedServiceSlots(prev => ({ ...prev, [product.id]: preload.service_slot }));
    }

    // Onda 16 — reservation preload: rental dates / booking slot + extras from
    // ReservationLandingPage. The rental_date_* keys map to the existing
    // rentalDates state; booking_* to bookingSlots; extras go into a new
    // dedicated map consumed at submit time.
    if (preload.rental_date_from) {
      setRentalDates(prev => ({
        ...prev,
        [product.id]: {
          from: preload.rental_date_from,
          to: preload.rental_date_to || preload.rental_date_from,
        },
      }));
    }
    if (preload.booking_date && preload.booking_start_time && preload.booking_end_time) {
      setBookingSlots(prev => ({
        ...prev,
        [product.id]: {
          date: preload.booking_date,
          start: preload.booking_start_time,
          end: preload.booking_end_time,
          // Onda 17 — cross-day end date when present; picker stores it so
          // the line payload below carries booking_end_date to the server.
          date_end: preload.booking_end_date || preload.booking_date,
        },
      }));
    }
    if (preload.extra_selections) {
      setSelectedExtraSelections(prev => ({
        ...prev,
        [product.id]: preload.extra_selections,
      }));
    }

    // "Add to cart and stay" — default behaviour since the landing pages
    // now separate add-to-cart from open-checkout. Callers that want the
    // legacy auto-open opt in explicitly with preloadCart.openCheckout=true
    // (or by navigating to /s/:slug?checkout=1, handled by the effect below).
    if (preload.openCheckout === true) {
      setFormOpen(true);
    }
    if (preload.mktp === true) {
      setMktpCheckout({ returnTo: preload.returnTo || '/ritiri' });
      try {
        sessionStorage.setItem('storefront:mktp_ctx', '1');
        // L2 — meta del ritorno per la guardia anti-vetrina (back del
        // browser sull'entry /s/:slug dopo la chiusura del checkout)
        sessionStorage.setItem('storefront:mktp_return', preload.returnTo || '/ritiri');
      } catch { /* no-op */ }
    }

    // Strip the Router state so a manual refresh stays on the plain
    // storefront without re-hydrating the same pre-fill. We preserve the
    // query string so ?checkout=1 (if present) can still be consumed by
    // the dedicated effect below.
    // L2 — si azzera SOLO lo state utente (usr): key/idx sono i metadati
    // di React Router — cancellarli con {} faceva sembrare 'default'
    // (= cold start) la key di questa entry al ritorno con back/forward,
    // accecando la guardia anti-vetrina qui sotto.
    window.history.replaceState(
      { ...(window.history.state || {}), usr: undefined },
      '', window.location.pathname + window.location.search,
    );
    // Onda 15 — include location.state in deps so the effect also fires
    // when the user re-enters /s/:slug with fresh preloadCart while the
    // catalog is already cached (SPA navigation back from /p/:org/:slug).
    // Without this the effect only ran on first catalog load, leaving the
    // checkout modal closed after any subsequent ProductLandingPage →
    // Storefront handoff.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [catalog, location.state]);

  // F3 Onda 10 — helper: for a product with multi-tier cart, return
  // the ordered tier list {id, qty} matching occurrence.tiers order
  // (sort_order). Used by both selectedItems builder and attendee labels.
  const getOrderedTierEntries = useCallback((pid) => {
    const map = selectedTiers[pid];
    if (!map || typeof map !== 'object') return [];
    const occ = selectedOccurrences[pid];
    const tierDefs = occ?.tiers || [];
    const out = [];
    for (const t of tierDefs) {
      const q = Number(map[t.id] || 0);
      if (q > 0) out.push({ id: t.id, label: t.label, qty: q });
    }
    // Fallback: tiers present in the map that aren't in occurrence.tiers
    // (edge case if occurrence.tiers didn't load) — append at end.
    for (const [tid, q] of Object.entries(map)) {
      if (out.find(x => x.id === tid)) continue;
      const qn = Number(q || 0);
      if (qn > 0) out.push({ id: tid, label: null, qty: qn });
    }
    return out;
  }, [selectedTiers, selectedOccurrences]);

  const selectedItems = useMemo(() => {
    const items = [];
    for (const [pid, qty] of Object.entries(quantities)) {
      if (!(qty > 0)) continue;

      // F3 Onda 10 — multi-tier fan-out for event_ticket carts
      const tierEntries = getOrderedTierEntries(pid);
      const allAttendees = attendeeDetails[pid];
      const attendeesMatch = Array.isArray(allAttendees) && allAttendees.length === qty;
      const toAttendeeShape = (x) => ({
        name: (x?.name || '').trim(),
        email: (x?.email || '').trim() || null,
        phone: x?.phone ? x.phone.trim() : null,
        custom_fields: x?.custom_fields || {},
      });

      if (tierEntries.length > 0) {
        // One line item per tier. Split the flat attendees array in the
        // same order as tierEntries — consumers see chunks that match
        // the labels used in the dialog.
        let cursor = 0;
        for (const te of tierEntries) {
          const item = {
            product_id: pid,
            quantity: te.qty,
            ticket_tier_id: te.id,
          };
          if (selectedOccurrences[pid]) item.occurrence_id = selectedOccurrences[pid].id;
          if (attendeesMatch) {
            const chunk = allAttendees.slice(cursor, cursor + te.qty);
            item.attendees = chunk.map(toAttendeeShape);
          }
          cursor += te.qty;
          items.push(item);
        }
        continue;
      }

      // Legacy / non-event / single-tier path (no multi-tier cart)
      const item = { product_id: pid, quantity: qty };
      if (selectedOccurrences[pid]) item.occurrence_id = selectedOccurrences[pid].id;
      const rd = rentalDates[pid];
      if (rd?.from) {
        item.rental_date_from = rd.from;
        item.rental_date_to = rd.to || null;
        item.rental_notes = rd.notes || null;
      }
      const bs = bookingSlots[pid];
      if (bs?.date && bs?.start && bs?.end) {
        item.booking_date = bs.date;
        item.booking_start_time = bs.start;
        item.booking_end_time = bs.end;
        // Onda 17 — cross-day slot. Only include when the end date differs
        // from the start date so legacy same-day orders stay unchanged.
        if (bs.date_end && bs.date_end !== bs.date) {
          item.booking_end_date = bs.date_end;
        }
      }
      // F5 Onda 12 — service option + slot (service is scheduled like
      // booking via booking_date / start / end; plus service_option_id
      // carries the radio selection)
      const sOpt = selectedServiceOptions[pid];
      if (sOpt) item.service_option_id = sOpt;
      const sSlot = selectedServiceSlots[pid];
      if (sSlot?.date && sSlot?.start_time && sSlot?.end_time) {
        item.booking_date = sSlot.date;
        item.booking_start_time = sSlot.start_time;
        item.booking_end_time = sSlot.end_time;
        // Onda 14 Parte B — surface custom-request context to the order:
        // the flag is set by ProductLandingPage when the slot was
        // proposed by the customer rather than picked from the rule set.
        if (sSlot.custom_request) item.service_custom_request = true;
        if (sSlot.notes) item.rental_notes = sSlot.notes;
      }
      // Onda 16 — reservation extras (mandatory server-merges, optional
      // checkbox, radio_variant picks). Attached at create time; the
      // server resolves the full snapshot in pricing.compute_line_total.
      const extraSel = selectedExtraSelections[pid];
      if (extraSel && (extraSel.optional_ids?.length || Object.keys(extraSel.radio_picks || {}).length)) {
        item.extra_selections = {
          mandatory_confirmed: true,
          optional_ids: extraSel.optional_ids || [],
          radio_picks: extraSel.radio_picks || {},
        };
      }
      if (attendeesMatch) {
        item.attendees = allAttendees.map(toAttendeeShape);
      }
      items.push(item);
    }
    return items;
  }, [quantities, selectedOccurrences, selectedTiers, rentalDates, bookingSlots, attendeeDetails, getOrderedTierEntries, selectedServiceOptions, selectedServiceSlots]);

  // Total quantity across all selected items (for cart badge)
  const totalQty = useMemo(() =>
    selectedItems.reduce((sum, item) => sum + item.quantity, 0),
    [selectedItems]
  );

  // Sprint 2 W2.2 — Live coupon discount lifted to main scope so OrderSummary
  // puo' renderizzare il breakdown discount in tempo reale (parity widget E4.1).
  // Computa cart subtotal client-side (mirror del calcolo OrderSummary) e lo
  // passa al hook useCouponValidation che fa POST debounced a
  // /coupons/validate/{slug}. Quando il coupon e' valid, discountAmount > 0
  // -> OrderSummary mostra riga 'Sconto coupon -X EUR' + ricalcola totale.
  const couponSubtotal = useMemo(() => {
    try {
      const prods = catalog?.products || [];
      return (selectedItems || []).reduce((sum, it) => {
        const p = prods.find((x) => x.id === it.product_id);
        if (!p) return sum;
        const price = Number(p.unit_price) || 0;
        return sum + price * (it.quantity || 1);
      }, 0);
    } catch {
      return 0;
    }
  }, [selectedItems, catalog?.products]);

  const couponValidation = useCouponValidation({
    slug,
    code: form.coupon_code,
    cartSubtotal: couponSubtotal,
    enabled: !!form.coupon_code,
  });

  // Shape compatto per props OrderSummary
  const couponValidationState = useMemo(() => ({
    discountAmount: couponValidation.valid ? couponValidation.discountAmount : 0,
    code: couponValidation.valid ? (form.coupon_code || '').trim().toUpperCase() : null,
  }), [couponValidation.valid, couponValidation.discountAmount, form.coupon_code]);

  // Release 4 (Courses) — an order containing at least one course line
  // cannot be submitted as guest. The enrollment is nominative and the
  // customer needs a portal login to access the player. When this flag
  // is true AND the customer is not already authenticated, the checkout
  // modal surfaces the inline login/signup form and disables the
  // "continue as guest" path.
  const requiresCustomerAccount = useMemo(() => {
    const prods = catalog?.products || [];
    return selectedItems.some(it => {
      const p = prods.find(pp => pp.id === it.product_id);
      return p?.item_type === 'course';
    });
  }, [selectedItems, catalog]);

  // Release 4 (Courses) — when the cart contains a course AND the customer
  // is not yet authenticated, force the "crea un account" branch on.
  // Guest checkout is server-side blocked for orders with courses, so
  // the UI mirrors that constraint. Idempotent setter → no render loop.
  // NOTE: placed here (after `requiresCustomerAccount` is declared) to
  // avoid a TDZ ReferenceError on the first render.
  useEffect(() => {
    if (requiresCustomerAccount && !isCustomerAuthenticated && !wantRegister) {
      setWantRegister(true);
    }
  }, [requiresCustomerAccount, isCustomerAuthenticated, wantRegister]);

  // K1 — in contesto marketplace la chiusura del checkout riporta alla
  // landing: l'utente non deve mai "restare" nella vetrina.
  const mktpWasOpenRef = useRef(false);
  // il flag di contesto e' per-checkout: un checkout NORMALE dello store
  // nella stessa tab lo pulisce (niente CTA marketplace stantie sul
  // success di un acquisto da vetrina)
  useEffect(() => {
    if (formOpen && !mktpCheckout) {
      try { sessionStorage.removeItem('storefront:mktp_ctx'); } catch { /* no-op */ }
    }
  }, [formOpen, mktpCheckout]);
  useEffect(() => {
    if (!mktpCheckout) return;
    if (formOpen) { mktpWasOpenRef.current = true; return; }
    // BUG beccato dalla simulazione E2E (9/7): dopo un submit in
    // request-mode (niente redirect Stripe) il dialog si chiude per
    // mostrare la CONFERMA — il ritorno alla landing vale solo per la
    // chiusura senza acquisto.
    if (submitted) { mktpWasOpenRef.current = false; return; }
    if (mktpWasOpenRef.current) {
      mktpWasOpenRef.current = false;
      // L2 — replace, non push: l'entry /s/:slug (la vetrina nuda) non
      // deve restare nella history — il back del browser dopo la
      // chiusura riportava sull'ecommerce dell'operatore.
      navigate(mktpCheckout.returnTo, { replace: true });
    }
  }, [formOpen, mktpCheckout, submitted, navigate]);

  // L2 — guardia anti-vetrina: nel percorso directory l'utente non deve
  // MAI trovarsi sulla vetrina dell'operatore. Se questa pagina renderizza
  // in contesto marketplace (flag di sessione) SENZA un checkout mktp
  // attivo ne' uno in arrivo (preload/riapertura/?checkout=1), e ci si è
  // arrivati con back/forward del browser (POP su entry SPA — l'entry
  // /s/:slug ripulita dello state), si torna alla landing. Le visite
  // DELIBERATE alla vetrina (click su link = PUSH, o URL diretto =
  // location.key 'default') non vengono toccate: chiudono il contesto
  // marketplace, coerente con la pulizia del flag qui sotto.
  useEffect(() => {
    if (mktpCheckout || formOpen) return;
    if (location.state?.preloadCart || location.state?.mktpOpen) return;
    if (new URLSearchParams(location.search).get('checkout') === '1') return;
    let inMktp = false;
    let back = '/ritiri';
    try {
      inMktp = sessionStorage.getItem('storefront:mktp_ctx') === '1';
      back = sessionStorage.getItem('storefront:mktp_return') || back;
    } catch { /* no-op */ }
    if (!inMktp) return;
    if (navType === 'POP' && location.key !== 'default') {
      navigate(back, { replace: true });
    } else {
      // Vetrina raggiunta di proposito: il viaggio directory è finito,
      // il flag non deve più perseguitare questa tab.
      try {
        sessionStorage.removeItem('storefront:mktp_ctx');
        sessionStorage.removeItem('storefront:mktp_return');
      } catch { /* no-op */ }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mktpCheckout, formOpen, location.state, location.search, navType, location.key]);

  // K1+ — riapertura del checkout in contesto marketplace dal banner
  // della landing (carrello gia' pieno: niente preload prodotto).
  useEffect(() => {
    const mo = location.state?.mktpOpen;
    if (!mo) return;
    if (selectedItems.length === 0) return;   // aspetta l'idratazione del carrello
    setMktpCheckout({ returnTo: mo.returnTo || '/ritiri' });
    try {
      sessionStorage.setItem('storefront:mktp_ctx', '1');
      sessionStorage.setItem('storefront:mktp_return', mo.returnTo || '/ritiri');
    } catch { /* no-op */ }
    setFormOpen(true);
    // L2 — come sopra: azzera solo usr, preserva key/idx del router.
    window.history.replaceState(
      { ...(window.history.state || {}), usr: undefined },
      '', window.location.pathname + window.location.search,
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.state, selectedItems.length]);

  // Deep-link trigger: `?checkout=1` opens the modal from any entry point
  // (OpenCheckoutButton, toast action, shared link). Consumed once and
  // stripped from the URL so a refresh does not re-open the checkout.
  // We use navigate({replace: true}) to strip the param so React Router's
  // own location stays in sync — otherwise a second click on the same Link
  // would be a no-op because the Router would believe we're still on
  // ?checkout=1 after the first cleanup.
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    if (params.get('checkout') !== '1') return;
    // Only open if there is something to check out; otherwise wait for the
    // cart to hydrate (selectedItems.length will change, re-triggering).
    if (selectedItems.length === 0) return;
    setFormOpen(true);
    params.delete('checkout');
    const newSearch = params.toString();
    navigate(
      location.pathname + (newSearch ? `?${newSearch}` : '') + location.hash,
      { replace: true },
    );
  }, [location.search, location.pathname, location.hash, selectedItems.length, navigate]);

  // v10.0: Determine if fulfillment choice is needed
  const fulfillmentContext = useMemo(() => {
    const prods = catalog?.products || [];
    const selectedTypes = selectedItems.map(it => prods.find(p => p.id === it.product_id)?.item_type).filter(Boolean);
    const hasPhysical = selectedTypes.includes('physical');
    const hasRental = selectedTypes.includes('rental');
    const storeModes = catalog?.fulfillment_modes || ['shipping'];

    if (hasRental) return { needsChoice: false, autoMode: 'manual_arrangement' };
    if (!hasPhysical) return { needsChoice: false, autoMode: null }; // not_required
    if (storeModes.length === 1) return { needsChoice: false, autoMode: storeModes[0] };
    return { needsChoice: true, modes: storeModes };
  }, [selectedItems, catalog]);

  // Set default fulfillment mode when context changes
  useEffect(() => {
    if (fulfillmentContext.autoMode) {
      setForm(f => ({ ...f, fulfillment_mode: fulfillmentContext.autoMode }));
    } else if (fulfillmentContext.needsChoice && !form.fulfillment_mode) {
      setForm(f => ({ ...f, fulfillment_mode: fulfillmentContext.modes?.[0] || 'shipping' }));
    }
  }, [fulfillmentContext]); // eslint-disable-line react-hooks/exhaustive-deps

  // Refetch shipping options when the checkout modal opens — covers the case
  // where the merchant just configured them in another tab while the customer
  // had the landing open, so they don't have to reload manually.
  useEffect(() => {
    if (!formOpen || !slug) return;
    let mounted = true;
    publicShippingOptions.get(slug)
      .then(res => { if (mounted) setShippingOptions(res.data?.options || []); })
      .catch(() => { /* keep whatever we had from the initial load */ });
    return () => { mounted = false; };
  }, [formOpen, slug]);

  // ── Shipping computation (storefront preview mirror of the backend) ──
  //
  // The backend recomputes shipping at order-create time, so this is a
  // live preview only — never a source of truth for pricing. When the
  // backend accepts the order it trusts ONLY `shipping_option_id` and
  // computes the cost again from the DB. If the two disagree (rare race
  // with the admin editing options), the backend value wins.
  //
  // Triggers:
  //   - cart items change (recomputes physical_subtotal for threshold)
  //   - fulfillment_mode flips to/from "shipping"
  //   - shipping_option_id selection changes
  //   - shipping options list loaded / reloaded
  const hasPhysicalCart = useMemo(() => {
    const prods = catalog?.products || [];
    return selectedItems.some(it =>
      prods.find(p => p.id === it.product_id)?.item_type === 'physical'
    );
  }, [selectedItems, catalog]);

  const physicalSubtotal = useMemo(() => {
    const prods = catalog?.products || [];
    let sum = 0;
    for (const it of selectedItems) {
      const p = prods.find(pp => pp.id === it.product_id);
      if (!p || p.item_type !== 'physical' || p.price_mode === 'inquiry') continue;
      sum += Number(p.unit_price || 0) * Number(it.quantity || 0);
    }
    return Math.round(sum * 100) / 100;
  }, [selectedItems, catalog]);

  const selectedShippingOption = useMemo(() => {
    if (!form.shipping_option_id) return null;
    return shippingOptions.find(o => o.id === form.shipping_option_id) || null;
  }, [form.shipping_option_id, shippingOptions]);

  const shippingSummary = useMemo(() => {
    // Summary feeds the OrderSummary (totals row) + the "add more for free"
    // hint. `active` gates the shipping line visibility.
    if (!hasPhysicalCart) return { active: false, cost: 0, label: null, addMoreForFree: 0 };
    if (form.fulfillment_mode === 'local_pickup') {
      return { active: true, cost: 0, label: t('storefront:checkout.fulfillment.localPickup'), addMoreForFree: 0 };
    }
    if (form.fulfillment_mode !== 'shipping') return { active: false, cost: 0, label: null, addMoreForFree: 0 };
    if (!selectedShippingOption) {
      // Physical + shipping picked but no option chosen yet — OrderSummary
      // suppresses the cost but the row is "active" so the caller can use
      // this flag for button gating.
      return { active: true, cost: 0, label: null, addMoreForFree: 0 };
    }
    const base = Number(selectedShippingOption.base_price || 0);
    const threshold = selectedShippingOption.free_shipping_threshold;
    const free = threshold != null && physicalSubtotal >= Number(threshold);
    const cost = free ? 0 : base;
    const add = (!free && threshold != null) ? Math.max(0, Number(threshold) - physicalSubtotal) : 0;
    return {
      active: true,
      cost,
      label: selectedShippingOption.label,
      addMoreForFree: Math.round(add * 100) / 100,
    };
  }, [hasPhysicalCart, form.fulfillment_mode, selectedShippingOption, physicalSubtotal]);

  // Clear shipping_option_id when the mode flips away from shipping so a
  // stale id doesn't silently travel with a pickup-mode submission.
  useEffect(() => {
    if (form.fulfillment_mode !== 'shipping' && form.shipping_option_id) {
      setForm(f => ({ ...f, shipping_option_id: '' }));
    }
  }, [form.fulfillment_mode]); // eslint-disable-line react-hooks/exhaustive-deps

  // Auto-preselect when there's exactly one shipping option (no-brainer UX).
  useEffect(() => {
    if (
      hasPhysicalCart &&
      form.fulfillment_mode === 'shipping' &&
      shippingOptions.length === 1 &&
      !form.shipping_option_id
    ) {
      setForm(f => ({ ...f, shipping_option_id: shippingOptions[0].id }));
    }
  }, [hasPhysicalCart, form.fulfillment_mode, shippingOptions, form.shipping_option_id]);

  // v5.8 / Onda 4 — read commerce.checkout_stripe flag from /meta payload.
  // When false (Free plan or any plan with Stripe Connect off), we force
  // the request-mode CTA regardless of what the products' transaction_mode
  // says — the backend will downgrade direct → request anyway, so show the
  // truthful CTA upfront ("Richiedi info" instead of "Acquista").
  const { checkoutStripeEnabled } = useStoreMeta();

  // Resolve mode-aware copy from selected products' transaction_mode
  // If direct mode contains rental/event-with-capacity items, direct checkout
  // will be blocked by backend safety — soften the CTA to match reality.
  const modeCopy = useMemo(() => {
    const prods = catalog?.products || [];
    const modes = selectedItems.map(it => prods.find(p => p.id === it.product_id)?.transaction_mode);
    const mode = resolveDominantMode(modes);

    // v5.8 / Onda 4 — if the merchant's plan has checkout_stripe disabled,
    // every order becomes a contact request regardless of product config.
    // Force request copy upfront so the customer sees the right CTA.
    if (checkoutStripeEnabled === false) {
      return resolveTransactionModeCopy(t, 'request');
    }

    if (mode === 'direct') {
      // Check if any item will prevent direct checkout
      const hasRental = selectedItems.some(it => {
        const p = prods.find(pp => pp.id === it.product_id);
        return p?.item_type === 'rental';
      });
      const hasCapEvent = selectedItems.some(it => {
        const p = prods.find(pp => pp.id === it.product_id);
        return p?.item_type === 'event_ticket' && it.occurrence_id;
        // Note: we can't check capacity client-side, but events with occurrences
        // that have capacity will be caught by backend. Conservative: still show
        // direct CTA for events, backend handles the gating truthfully.
      });

      if (hasRental) {
        // Rental in direct mode → checkout won't start, use request-like copy.
        // Lives in a dedicated `rentalOverride` key so the copy can drift
        // from the generic `request` mode without leaking semantics.
        return {
          headerCta:     t('storefront:transactionMode.rentalOverride.headerCta'),
          modalTitle:    t('storefront:transactionMode.rentalOverride.modalTitle'),
          modalDesc:     t('storefront:transactionMode.rentalOverride.modalDesc'),
          submitBtn:     t('storefront:transactionMode.rentalOverride.submitBtn'),
          inquiryToggle: t('storefront:transactionMode.rentalOverride.inquiryToggle'),
        };
      }
    }

    return resolveTransactionModeCopy(t, mode);
  }, [selectedItems, catalog, t, checkoutStripeEnabled]);

  // F1 Onda 8 — which items need per-seat holder forms
  // F3 Onda 10 — aggregate per-product (selectedItems may now contain
  // multiple line items per product, one per tier). `totalQty` is the
  // sum of quantities across tiers; `seatLabels` is a per-seat
  // annotation (e.g. "Biglietto 3 — VIP") used in the dialog.
  const itemsRequiringAttendees = useMemo(() => {
    const prods = catalog?.products || [];
    const byProduct = new Map();
    for (const it of selectedItems) {
      const product = prods.find(p => p.id === it.product_id);
      if (!product || product.item_type !== 'event_ticket') continue;
      if (!product.requires_attendee_details) continue;
      const existing = byProduct.get(it.product_id);
      if (existing) {
        existing.totalQty += Number(it.quantity || 0);
      } else {
        byProduct.set(it.product_id, {
          product,
          totalQty: Number(it.quantity || 0),
        });
      }
    }
    // Build per-seat labels using getOrderedTierEntries (keeps UI in sync
    // with the actual tier-line-items that will be POSTed).
    const out = [];
    for (const { product, totalQty } of byProduct.values()) {
      const tierEntries = getOrderedTierEntries(product.id);
      const seatLabels = [];
      if (tierEntries.length > 0) {
        let n = 1;
        for (const te of tierEntries) {
          for (let i = 0; i < te.qty; i++) {
            seatLabels.push(t('storefront:checkout.attendees.seatLabelWithTier', { index: n, tier: te.label || t('storefront:checkout.attendees.tierFallback') }));
            n++;
          }
        }
      } else {
        for (let i = 0; i < totalQty; i++) {
          seatLabels.push(`Biglietto ${i + 1}`);
        }
      }
      // For backward-compat with existing consumers we still expose
      // `item` with product_id + total quantity (same shape as a plain
      // single-line cart).
      out.push({
        item: { product_id: product.id, quantity: totalQty },
        product,
        seatLabels,
      });
    }
    return out;
  }, [selectedItems, catalog, getOrderedTierEntries]);

  // Keep attendeeDetails[pid] in sync with quantity: resize array up/down,
  // preserving already-filled entries so a qty bump doesn't clear names.
  useEffect(() => {
    setAttendeeDetails(prev => {
      let changed = false;
      const next = { ...prev };
      // Ensure entries for each relevant product
      for (const { item } of itemsRequiringAttendees) {
        const pid = item.product_id;
        const cur = Array.isArray(next[pid]) ? next[pid] : [];
        const qty = Number(item.quantity) || 0;
        if (cur.length !== qty) {
          const resized = Array.from({ length: qty }, (_, i) =>
            cur[i] || { name: '', email: '', phone: '' }
          );
          next[pid] = resized;
          changed = true;
        }
      }
      // Drop entries for products that are no longer in the cart or no
      // longer require attendees (e.g. merchant toggled the policy off).
      const keep = new Set(itemsRequiringAttendees.map(({ item }) => item.product_id));
      for (const pid of Object.keys(next)) {
        if (!keep.has(pid)) { delete next[pid]; changed = true; }
      }
      return changed ? next : prev;
    });
  }, [itemsRequiringAttendees]);

  // Validation helper — are all attendee forms complete and well-formed?
  // F2 Onda 9: respect product.require_attendee_email/phone flags and
  // check that required custom fields are filled.
  const attendeesValid = useMemo(() => {
    if (itemsRequiringAttendees.length === 0) return true;
    const emailRx = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    for (const { item, product } of itemsRequiringAttendees) {
      const entries = attendeeDetails[item.product_id] || [];
      if (entries.length !== Number(item.quantity)) return false;
      const emailReq = product.require_attendee_email !== false;  // default true
      const phoneReq = !!product.require_attendee_phone;
      const requiredCustom = (product.attendee_fields || []).filter(f => f?.required);
      for (const e of entries) {
        if (!e?.name?.trim()) return false;
        if (emailReq) {
          if (!emailRx.test((e?.email || '').trim())) return false;
        } else if (e?.email && !emailRx.test(e.email.trim())) {
          // Not required, but if provided must be valid
          return false;
        }
        if (phoneReq && !(e?.phone || '').trim()) return false;
        const cf = e?.custom_fields || {};
        for (const fc of requiredCustom) {
          const v = cf[fc.id];
          const empty = (v == null) || (typeof v === 'string' && v.trim() === '');
          if (empty) return false;
        }
      }
    }
    return true;
  }, [itemsRequiringAttendees, attendeeDetails]);

  // F2 Onda 9 — order-level custom fields validation. Looks across all
  // event_ticket products in the cart and requires every field marked as
  // `required` on any of them to be non-empty.
  const orderFieldsConfig = useMemo(() => {
    const prods = catalog?.products || [];
    const seen = new Map();
    for (const it of selectedItems) {
      const p = prods.find(pp => pp.id === it.product_id);
      if (!p || p.item_type !== 'event_ticket') continue;
      for (const fc of (p.order_fields || [])) {
        if (fc?.id && !seen.has(fc.id)) seen.set(fc.id, fc);
      }
    }
    // Stable order
    return Array.from(seen.values()).sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0));
  }, [selectedItems, catalog]);

  const orderFieldsValid = useMemo(() => {
    for (const fc of orderFieldsConfig) {
      if (!fc.required) continue;
      const v = orderFieldsData[fc.id];
      const empty = (v == null) || (typeof v === 'string' && v.trim() === '');
      if (empty) return false;
    }
    return true;
  }, [orderFieldsConfig, orderFieldsData]);

  // F5 Onda 12 — list of service products in cart that need the
  // radio options picker and/or slot picker at checkout.
  const serviceItemsInCart = useMemo(() => {
    const prods = catalog?.products || [];
    const out = [];
    for (const it of selectedItems) {
      const p = prods.find(pp => pp.id === it.product_id);
      if (!p || p.item_type !== 'service') continue;
      // Already in cart — dedup by product_id
      if (out.find(x => x.product.id === p.id)) continue;
      out.push({
        item: it,
        product: p,
        options: Array.isArray(p.service_options) ? p.service_options : [],
        hasSlots: !!p.has_availability_slots,
      });
    }
    return out;
  }, [selectedItems, catalog]);

  // Fetch available slots for each service product in cart
  useEffect(() => {
    for (const { product, hasSlots } of serviceItemsInCart) {
      if (!hasSlots) continue;
      if (serviceSlotsByProduct[product.id]) continue;  // already cached
      (async () => {
        try {
          const res = await fetch(`/api/public/services/${product.id}/slots?days=30`);
          if (!res.ok) return;
          const data = await res.json();
          setServiceSlotsByProduct(prev => ({ ...prev, [product.id]: data.slots || [] }));
        } catch { /* silent */ }
      })();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [serviceItemsInCart.length]);

  // F5 Onda 12 — service flow validity: if a product has options, one
  // must be selected; if it has slots, one must be picked.
  const servicesValid = useMemo(() => {
    for (const { product, options, hasSlots } of serviceItemsInCart) {
      if (options.length > 0 && !selectedServiceOptions[product.id]) return false;
      if (hasSlots && !selectedServiceSlots[product.id]?.date) return false;
    }
    return true;
  }, [serviceItemsInCart, selectedServiceOptions, selectedServiceSlots]);

  // F4 Onda 11 — effective T&C: first product (any type) whose
  // pre-resolved terms_content is non-empty. Uniform across events and
  // services (and any future type that populates the field).
  const effectiveTerms = useMemo(() => {
    const prods = catalog?.products || [];
    for (const it of selectedItems) {
      const p = prods.find(pp => pp.id === it.product_id);
      if (p && typeof p.terms_content === 'string' && p.terms_content.trim()) {
        return p.terms_content;
      }
    }
    return null;
  }, [selectedItems, catalog]);

  const termsValid = !effectiveTerms || termsAccepted;

  // Wave GDPR-Commerce CG-5 — does this store require the new GDPR
  // consent block? True when the merchant has published their per-store
  // Privacy + Terms (CG-3 admin UI). Stays False for legacy stores so
  // the checkout flow is identical to pre-CG-5 behaviour.
  const gdprRequired = !!legalMeta && (
    legalMeta.status === 'published' || legalMeta.status === 'stale_draft'
  );
  // The two mandatory boxes must be ticked when gdprRequired AND the
  // block is actually rendered. Marketing is always optional even when
  // the block is rendered (GDPR Art. 7 granular consent).
  //
  // 2026-05-20 — Fix Bug #3: when the customer is already logged in,
  // the block is HIDDEN (CG-4 captured the snapshot at signup; the
  // re-consent modal handles version bumps before the customer can
  // even reach the checkout). For that case ``gdprValid`` is true by
  // construction — we don't have checkboxes to validate. The backend
  // mirrors this by accepting the customer_account snapshot in place
  // of the per-order payload flags for logged-in customers (Fix 3b).
  const gdprValid =
    !gdprRequired
    || isCustomerAuthenticated
    || (gdprTermsAccepted && gdprPrivacyAccepted);

  // Auto-fill first attendee from the main customer form: it's the most
  // common case (Michele buys 3 tickets, first is his own). Keeps friction
  // low; customer can still override if the first seat is for a guest.
  useEffect(() => {
    if (!form.name.trim() && !form.email.trim()) return;
    setAttendeeDetails(prev => {
      let changed = false;
      const next = { ...prev };
      for (const { item } of itemsRequiringAttendees) {
        const pid = item.product_id;
        const cur = next[pid];
        if (Array.isArray(cur) && cur.length > 0) {
          const first = cur[0] || {};
          if (!first.name && !first.email) {
            next[pid] = [
              { name: form.name.trim(), email: form.email.trim(), phone: form.phone?.trim() || '' },
              ...cur.slice(1),
            ];
            changed = true;
          }
        }
      }
      return changed ? next : prev;
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [form.name, form.email, form.phone, itemsRequiringAttendees.length]);

  const handleSubmit = async (e) => {
    // K3+ — in contesto marketplace il success attiva il Passaporto con
    // l'email dell'ordine (one-click, senza ridigitarla)
    if (mktpCheckout && form?.email) {
      try { sessionStorage.setItem('storefront:mktp_email', form.email); } catch { /* no-op */ }
    }
    e.preventDefault();
    if (!form.name.trim() || !form.email.trim() || selectedItems.length === 0) return;
    if (!attendeesValid) {
      toast.error(t('storefront:errors.fillAttendees'));
      return;
    }
    if (effectiveTerms && !termsAccepted) {
      toast.error(t('storefront:errors.termsRequired'));
      return;
    }
    // Wave GDPR-Commerce CG-5 — block submit if the store has GDPR
    // docs published and the customer hasn't ticked the mandatory
    // privacy + terms checkboxes. Marketing is optional.
    if (gdprRequired && !gdprValid) {
      toast.error(t('storefront:errors.gdprRequired', {
        defaultValue: 'Devi accettare la Privacy e i Termini del negozio per procedere.',
      }));
      return;
    }
    if (!servicesValid) {
      toast.error(t('storefront:errors.selectServiceOptionAndSlot'));
      return;
    }
    // Structured shipping address validation — runs only for mode=shipping.
    // Required fields mirror the backend Pydantic contract; soft pattern
    // check on CAP applies to IT only (other countries allow alphanumeric
    // postal codes).
    if (form.fulfillment_mode === 'shipping') {
      const a = form.shipping_address_details || {};
      const missing = [];
      if (!a.line1?.trim()) missing.push(t('storefront:checkout.address.streetField'));
      if (!a.civic?.trim()) missing.push(t('storefront:checkout.address.civicField'));
      if (!a.postal_code?.trim()) missing.push(t('storefront:checkout.address.postalCodeField'));
      if (!a.city?.trim()) missing.push(t('storefront:checkout.address.cityField'));
      if (missing.length) {
        toast.error(t('storefront:errors.completeAddress', { missing: missing.join(', ') }));
        return;
      }
      const countryIso = (a.country || 'IT').toUpperCase();
      if (countryIso === 'IT' && !/^\d{5}$/.test(a.postal_code.trim())) {
        toast.error(t('storefront:errors.invalidPostalCodeIT'));
        return;
      }
    }
    // Shipping option required when the cart contains a physical item
    // AND the customer chose mode=shipping. Backend re-validates this,
    // but surfacing the error client-side avoids a confusing round-trip.
    if (hasPhysicalCart && form.fulfillment_mode === 'shipping' && !form.shipping_option_id) {
      toast.error(t('storefront:errors.selectShippingOption'));
      return;
    }
    setSubmitting(true);
    // Fase C2: best-effort account creation BEFORE the order. By design the
    // account is created with email_verified=false — the customer will
    // confirm via email and, at first successful login, their orders on
    // this org are automatically linked by email match (backend
    // _link_account_to_existing_customers). The order itself is still
    // submitted as guest in this request; never block the order on a
    // signup hiccup.
    let registrationState = null; // null | 'created' | 'already' | 'failed' | 'auto_logged_in'
    if (wantRegister && !isCustomerAuthenticated) {
      const strength = computePasswordStrength(regPassword);
      if (!strength.ok) {
        toast.error(t('storefront:checkout.signup.passwordRequirementsToast'));
        setSubmitting(false);
        return;
      }
      if (regPassword !== regPasswordConfirm) {
        toast.error(t('storefront:checkout.signup.passwordMismatch'));
        setSubmitting(false);
        return;
      }

      // Release 4 (Courses) — when the cart contains a course we ask the
      // backend to `auto_login` so the signup response already carries a
      // Bearer token. This bypasses the email-verified gate that would
      // otherwise block a subsequent /login call (the account is freshly
      // created → email_verified=false → login 403). For non-course
      // carts the legacy fire-and-forget signup keeps working unchanged.
      const wantAutoLogin = !!requiresCustomerAccount;

      try {
        // Note: we call through the context's `signup` (not the raw
        // customerAuthAPI) so the token is persisted in localStorage +
        // React state atomically. The next `storefrontAPI.submitOrder`
        // will then attach the Bearer automatically via customerClient.
        // 2026-05-20 — Fix Bug #1 (checkout inline signup): the backend
        // CG-4 contract requires accepted_terms + accepted_privacy at
        // signup (and optionally accepted_marketing). Without these the
        // service raises "Devi accettare i Termini..." and the user sees
        // a generic "registrazione non completata". The checkout already
        // has these states (the GDPR block above forces the merchant's
        // ticked boxes before the submit) so we forward them verbatim.
        const result = await customerSignup({
          slug,
          email: form.email.trim(),
          name: form.name.trim(),
          password: regPassword,
          auto_login: wantAutoLogin,
          // CG-4 consent flags — required when merchant_legal_status is
          // "published" / "stale_draft". For stores that have NOT
          // published these are ignored server-side (backward compat).
          accepted_terms: !!gdprTermsAccepted,
          accepted_privacy: !!gdprPrivacyAccepted,
          accepted_marketing: !!gdprMarketingAccepted,
        });
        if (result && typeof result === 'object' && result.status === 'auto_logged_in') {
          registrationState = 'auto_logged_in';
        } else {
          registrationState = 'created';  // legacy verification_required flow
        }
      } catch (err) {
        const status = err?.response?.status;
        const rawDetail = err?.response?.data?.detail;
        const detail = typeof rawDetail === 'string' ? rawDetail
                       : (rawDetail?.message || rawDetail?.error || '');
        // 409 or "esiste già / already / exists" → account exists.
        // Regex widened to match Italian "esiste" (no accent needed).
        if (status === 409 || /email.*gi[aà]|already|existe?s?|esiste/i.test(String(detail))) {
          registrationState = 'already';
          if (requiresCustomerAccount) {
            toast.error(t('storefront:errors.emailAlreadyForCourse'));
            setSubmitting(false);
            return;
          }
          toast.info(t('storefront:errors.emailAlreadyInfo'));
        } else {
          registrationState = 'failed';
          if (requiresCustomerAccount) {
            // For courses we cannot proceed as guest — the server will
            // reject with course_requires_account. Stop here with a
            // clear message instead of letting the backend 400 bubble.
            toast.error(detail || t('storefront:errors.signupFailed'));
            setSubmitting(false);
            return;
          }
          toast.info(t('storefront:errors.signupNotCompleted'));
        }
      }
    }
    try {
      const payload = {
        slug,
        customer_name: form.name.trim(),
        customer_email: form.email.trim(),
        customer_phone: form.phone.trim() || null,
        items: selectedItems,
        notes: form.notes.trim() || null,
        // GT1 — il canale viaggia con l'ordine: gli ordini nati dal
        // marketplace (K1: mktp_ctx) si incassano SOLO online.
        channel: (() => {
          try { return sessionStorage.getItem('storefront:mktp_ctx') === '1' ? 'marketplace' : 'store'; }
          catch { return 'store'; }
        })(),
      };
      // F2 Onda 9 — send order-level custom fields only if we collected any
      if (orderFieldsData && Object.keys(orderFieldsData).length > 0) {
        payload.order_fields = orderFieldsData;
      }
      // F4 Onda 11 — send T&C acceptance flag (only meaningful when
      // the catalog exposed a non-empty `terms_content`)
      payload.terms_accepted = !!termsAccepted;
      // Wave GDPR-Commerce CG-5 — per-order consent flags. Always sent
      // (legacy clients omit them, defaults to False). Backend enforces
      // them ONLY when the merchant has GDPR published — otherwise
      // they're harmlessly ignored and the legacy flow proceeds.
      payload.gdpr_terms_accepted = !!gdprTermsAccepted;
      payload.gdpr_privacy_accepted = !!gdprPrivacyAccepted;
      payload.gdpr_marketing_accepted = !!gdprMarketingAccepted;
      // v10.0: fulfillment fields
      if (form.fulfillment_mode && form.fulfillment_mode !== 'manual_arrangement') {
        payload.fulfillment_mode = form.fulfillment_mode;
      }
      // Structured shipping address — only sent for mode=shipping. The
      // backend trusts this payload and synthesizes the flattened
      // `shipping_address` string server-side, so we intentionally do
      // NOT send the legacy key.
      if (form.fulfillment_mode === 'shipping') {
        const a = form.shipping_address_details || {};
        payload.shipping_address_details = {
          recipient_name: a.recipient_name?.trim() || null,
          line1: a.line1.trim(),
          civic: a.civic.trim(),
          postal_code: a.postal_code.trim(),
          city: a.city.trim(),
          province: a.province?.trim().toUpperCase() || null,
          country: (a.country || 'IT').toUpperCase(),
        };
      }
      // Shipping option id — only meaningful for mode=shipping. Backend
      // recomputes the cost from the ShippingOption doc so a malicious
      // client cannot alter the total by tampering with the payload.
      if (form.fulfillment_mode === 'shipping' && form.shipping_option_id) {
        payload.shipping_option_id = form.shipping_option_id;
      }
      if (form.fulfillment_notes?.trim()) {
        payload.fulfillment_notes = form.fulfillment_notes.trim();
      }
      if (form.coupon_code?.trim()) {
        payload.coupon_code = form.coupon_code.trim();
      }
      // customerClient injects customer_token automatically if present.
      //
      // Checkout consolidation: the API call + Stripe redirect + error
      // toast go through the shared useCheckoutSubmit hook (same path
      // used by EventLandingPage) so both pages honor
      // payment_checkout_url identically and future fixes land in one
      // place. The success branch still handles page-specific cleanup
      // (form close, password scrub, availability reload) that is
      // unique to the cart UX.
      const result = await submitCheckout(payload, {
        onSuccess: (data) => {
          setSubmitted({ ...data, registered: registrationState });
          setFormOpen(false);
          setRegPassword('');
          setRegPasswordConfirm('');
          setWantRegister(false);
          // Cart persisted in sessionStorage is now consumed — drop the
          // snapshot so a fresh visit starts clean. The in-memory state
          // reset happens when the user dismisses the success modal
          // (see the "Nuovo ordine" / reset button further down).
          // Phase 7.1: clearCartSnapshot routes through useStorefrontCart
          // so future cart-storage refactors land in one place.
          clearCartSnapshot();
          const bookingProduct = (catalog?.products || []).find(p => p.item_type === 'booking');
          if (bookingProduct) loadAvailability(bookingProduct.slot_duration_minutes || null, bookingProduct.id);
        },
        onError: (detail) => {
          toast.error(detail);
        },
      });
      // When redirected to Stripe, the return above effectively means
      // we never reach the finally block of submitting=false — the
      // browser has already left the page. Kept for parity with the
      // previous inline flow.
      if (result?.redirected) return;
    } catch (err) {
      // Same anti-crash guard as useCheckoutSubmit — the detail may be
      // a structured FastAPI object (e.g. `{error, message}` for the
      // course_requires_account gate) and React can't render it.
      const raw = err?.response?.data?.detail;
      const msg = typeof raw === 'string'
        ? raw
        : (raw && typeof raw === 'object' && (raw.message || raw.error))
          || t('storefront:errors.submitGeneric');
      toast.error(String(msg));
    } finally { setSubmitting(false); }
  };

  // ── States ──

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-2 border-gray-300 border-t-gray-800" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
        <div className="text-center">
          <p className="text-lg font-semibold text-gray-700">{error}</p>
          <p className="text-sm text-gray-500 mt-2">{t('storefront:errors.verifyUrl')}</p>
        </div>
      </div>
    );
  }

  if (submitted) {
    const hasCheckout = !!submitted.payment_checkout_url;
    const heading = hasCheckout ? t('storefront:submitted.orderReceived') : t('storefront:submitted.requestRegistered');
    const orderRef = submitted.order_id ? `#${submitted.order_id.slice(0, 8)}` : '';
    // Localized body — picked from the resolved storefront language
    // based on the backend's `transaction_mode`. The backend itself
    // returns a hardcoded Italian message in `submitted.message` for
    // legacy callers; we honor it as a fallback only when the mode is
    // unknown (defensive — should never happen with current backend).
    const bodyKeyByMode = {
      direct: 'storefront:submitted.body.direct',
      approval: 'storefront:submitted.body.approval',
      request: 'storefront:submitted.body.request',
    };
    const bodyKey = bodyKeyByMode[submitted.transaction_mode];
    const body = bodyKey ? t(bodyKey) : (submitted.message || t('storefront:submitted.body.request'));
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
        <div className="text-center max-w-md space-y-3">
          <div className="w-16 h-16 mx-auto rounded-full bg-green-100 flex items-center justify-center">
            <svg className="w-8 h-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
          </div>
          <h2 className="text-xl font-bold text-gray-900">{heading}</h2>
          <p className="text-gray-600">{body}</p>
          {orderRef && (
            <p className="text-sm text-gray-400">{t('storefront:submitted.reference', { ref: orderRef })}</p>
          )}
          <p className="text-sm text-gray-500">{t('storefront:submitted.confirmEmailSoon')}</p>

          {/* Fase C3: optional registration feedback box — only when the
              shopper opted into signup during checkout. Conveys truthful
              state without adding friction to pure-guest purchases. */}
          {submitted.registered === 'created' && (
            <div className="mx-auto max-w-sm rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-left text-sm text-emerald-900 space-y-1">
              <p className="font-semibold">{t('storefront:submitted.created.title')}</p>
              <p className="text-[13px]">
                {t('storefront:submitted.created.body')}
              </p>
              <p className="text-[12px] text-emerald-700">
                <Link to={`/account/login?slug=${encodeURIComponent(slug || '')}`} className="underline hover:no-underline">
                  {t('storefront:submitted.created.loginLink')}
                </Link>
              </p>
            </div>
          )}
          {submitted.registered === 'already' && (
            <div className="mx-auto max-w-sm rounded-lg border border-amber-200 bg-amber-50 p-3 text-left text-sm text-amber-900 space-y-1">
              <p className="font-semibold">{t('storefront:submitted.already.title')}</p>
              <p className="text-[13px]">
                {t('storefront:submitted.already.body')}
              </p>
              <p className="text-[12px]">
                <Link to={`/account/login?slug=${encodeURIComponent(slug || '')}`} className="underline hover:no-underline">
                  {t('storefront:submitted.already.loginLink')}
                </Link>
              </p>
            </div>
          )}
          {submitted.registered === 'failed' && (
            <div className="mx-auto max-w-sm rounded-lg border border-gray-200 bg-gray-50 p-3 text-left text-sm text-gray-700 space-y-1">
              <p className="text-[13px]">
                {t('storefront:submitted.failed.body')}
              </p>
            </div>
          )}

          <div className="flex justify-center gap-3 pt-2">
            {isCustomerAuthenticated && (
              <Link to={`/account?store=${slug}`} className="inline-block text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg px-4 py-2 hover:bg-gray-50 transition-colors">
                {t('storefront:submitted.myOrders')}
              </Link>
            )}
            <button
              onClick={() => {
                setSubmitted(null); setFormOpen(false);
                setQuantities({}); setSelectedOccurrences({}); setRentalDates({}); setBookingSlots({});
                setForm(f => ({
                  ...f,
                  notes: '',
                  shipping_address_details: {
                    recipient_name: '', line1: '', civic: '',
                    postal_code: '', city: '', province: '', country: 'IT',
                  },
                  fulfillment_notes: '',
                }));
              }}
              className="inline-block text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg px-4 py-2 hover:bg-gray-50 transition-colors"
            >
              {t('storefront:submitted.backToCatalog')}
            </button>
          </div>
        </div>
      </div>
    );
  }

  // `products` and `categoryDef` are computed at the top of the
  // component (alongside other hooks) — see the Phase 7.5 useMemo
  // block. Re-declared as `const` here would shadow that binding;
  // we just rely on the existing closures.

  if (products.length === 0) {
    // Empty state — still mount the full storefront chrome so the
    // visitor sees the brand, the logo, and (critically) the language
    // switcher and the category nav. Lets the visitor navigate
    // sideways into another category instead of bouncing off the page.
    //
    // Phase 7.5 — on a category page (categoryDef set) the empty copy
    // is category-specific ("Nessun servizio prenotabile" instead of
    // the generic "Nessun prodotto disponibile"). The user only hits
    // this branch via a direct URL — useAvailableCategories filters
    // empty categories out of the header, so navigation-driven visits
    // never land on an empty category.
    const emptyTitle = categoryDef
      ? t(categoryDef.emptyKey)
      : t('storefront:catalog.noProducts');
    const emptyHint = categoryDef
      ? t(categoryDef.emptyHintKey, { org: catalog?.org_name })
      : t('storefront:catalog.noProductsHint', { name: catalog?.org_name });

    return (
      // Phase 9 — designCssVars provides the resolved --sf-* tokens
      // (radius, density, font, accent, header alphas) so every
      // descendant can read them without prop-drilling.
      <div className="min-h-screen bg-gray-50"
        style={{
          ...designCssVars,
          fontFamily: 'var(--sf-font)',
          ...(catalog?.store_info?.brand_color ? {
            '--brand': catalog.store_info.brand_color,
            '--brand-text': catalog.store_info.brand_color_text || '#ffffff',
          } : {}),
        }}
      >
        <StorefrontHeader
          orgSlug={slug}
          storeInfo={catalog?.store_info}
          orgName={catalog?.org_name}
          subtitle={t('storefront:catalog.headerSubtitle')}
          supportedLanguages={catalog?.storefront_languages}
          categories={availableCategories}
          customNavLinks={catalog?.custom_nav_links}
          logoHeight={designLogo.height}
          logoFit={designLogo.fit}
          showStoreName={designLogo.showStoreName}
        />
        <div className="flex items-center justify-center px-4 py-24">
          <div className="text-center">
            <p className="text-lg font-semibold text-gray-700">{emptyTitle}</p>
            <p className="text-sm text-gray-500 mt-2">{emptyHint}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    // Phase 9 — same designCssVars injection as the empty-state branch.
    <div className="min-h-screen bg-gray-50"
      style={{
        ...designCssVars,
        fontFamily: 'var(--sf-font)',
        ...(catalog?.store_info?.brand_color ? {
          '--brand': catalog.store_info.brand_color,
          '--brand-text': catalog.store_info.brand_color_text || '#ffffff',
        } : {}),
      }}
    >
      {/* Header — shared across the storefront and the event landing.
          Logo + name link back to /s/:slug from any surface.
          Phase 7.4 — `categories` drives the secondary nav strip
          under the main bar.
          Phase 8.2 — `customNavLinks` (catalog.custom_nav_links) feeds
          the right-side cluster of the same strip. PREVIOUSLY this
          render path was missing the prop, so configured links only
          appeared on the empty-state branch — non-empty stores (the
          common case) never showed merchant-configured links. */}
      <StorefrontHeader
        orgSlug={slug}
        storeInfo={catalog?.store_info}
        orgName={catalog?.org_name}
        subtitle={t('storefront:catalog.headerSubtitle')}
        supportedLanguages={catalog?.storefront_languages}
        categories={availableCategories}
        customNavLinks={catalog?.custom_nav_links}
        logoHeight={designLogo.height}
        logoFit={designLogo.fit}
        showStoreName={designLogo.showStoreName}
        rightSlot={
          <>
            {/* Cleanup pass (post-Phase-7): the "Vai al checkout" pill
                that used to live here has been removed. The cart icon
                below is now the SINGLE entry point to the checkout
                modal — both empty (toast hint) and full (open modal)
                states are owned by it. Removing the dedicated pill
                eliminates the 3-CTA redundancy (pill + mini-cart bar +
                cart icon) the merchant complained about. */}

            {/* User icon */}
            <Link
              to={isCustomerAuthenticated
                ? `/account?store=${slug}`
                : `/account/login?store=${slug}`
              }
              className="relative p-1.5 rounded-full transition-opacity hover:opacity-80"
              aria-label={isCustomerAuthenticated ? t('storefront:header.myAccount') : t('storefront:header.loginOrSignup')}
              title={isCustomerAuthenticated ? (customer?.name || t('storefront:header.myAccount')) : t('storefront:header.loginSignupShort')}
            >
              <User className="h-5 w-5"
                style={{ color: catalog?.store_info?.brand_color_text || '#374151' }}
              />
              {isCustomerAuthenticated && (
                <span className="absolute -top-0.5 -right-0.5 h-2.5 w-2.5 rounded-full bg-emerald-500 border-2"
                  style={{ borderColor: catalog?.store_info?.brand_color || '#fff' }} />
              )}
            </Link>

            {/* Cart — SINGLE entry point to checkout.
                Two visual states:
                  · empty       : transparent icon-only button, click
                                  shows a toast hinting the cart is empty
                  · has items   : brand-inverted PILL with icon + count
                                  + shadow. Sized larger so it reads
                                  as the primary action on the bar.
                                  Subtle bump animation when count
                                  changes (key={totalQty} forces remount
                                  → CSS animation replays).
                The cleanup pass merged 3 previous CTAs (header pill,
                mini-cart bar, mobile FAB) into THIS button — making
                its visual weight explicit was the user's ask. */}
            {selectedItems.length === 0 ? (
              <button
                onClick={() => toast(t('storefront:header.emptyCartToast'))}
                className="relative p-2 rounded-full transition-opacity hover:opacity-80 hover:bg-black/5"
                aria-label={t('storefront:header.cartAria', { count: 0 })}
              >
                <ShoppingCart className="h-5 w-5"
                  style={{ color: catalog?.store_info?.brand_color_text || '#374151' }}
                />
              </button>
            ) : (
              <button
                key={totalQty}
                onClick={() => setFormOpen(true)}
                className="relative flex items-center gap-2 rounded-full px-3.5 py-2 text-sm font-semibold
                           shadow-md hover:shadow-lg transition-all
                           hover:scale-[1.03] active:scale-95
                           animate-cart-bump"
                style={{
                  // Brand-inverted: the header bar paints brand_color
                  // as background, so the cart pill flips to use the
                  // brand_color_text as ITS background — guarantees
                  // contrast on any brand palette.
                  backgroundColor: catalog?.store_info?.brand_color_text || '#1a1a1a',
                  color: catalog?.store_info?.brand_color || '#ffffff',
                }}
                aria-label={t('storefront:header.cartAria', { count: totalQty })}
              >
                <ShoppingCart className="h-4 w-4" />
                <span className="leading-none">{totalQty}</span>
              </button>
            )}
          </>
        }
      />

      {/* Cleanup pass (post-Phase-7): the mini-cart summary bar that
          used to live here (a sticky strip under the header showing
          "N articoli nel carrello", a "Vai al checkout" pill, and a
          "Dettagli/Riduci" toggle) has been removed. Reasons:
            1. It duplicated the cart icon's affordance (both opened
               the same modal) so visitors saw 3 checkout entry points
               at the same time.
            2. The CategoryNav strip from Phase 7.4 already lives
               directly under the header — adding another sticky bar
               below was visually crowded and ate vertical real estate
               on small viewports.
            3. The cart icon below has been visually strengthened to
               carry the "items in cart" signal alone (animated count,
               brand-colored pill when non-empty).
          The cart-detail review UX (remove items inline, see names)
          stays available inside the checkout modal's OrderSummary
          which already lists items + remove buttons. */}

      {/* Merchant info section — S2: sulla home duplica l'hero brand,
          quindi si mostra solo sulle pagine categoria */}
      {!isHome && !aboutMode && !isRootAbout && (() => {
        const si = catalog?.store_info;
        if (!si?.store_description && !si?.contact_email && !si?.contact_phone) return null;
        return (
          <div className="max-w-6xl mx-auto px-4 pt-4">
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              {si.store_description && (
                <p className="text-sm text-gray-600 mb-2">{si.store_description}</p>
              )}
              {(si.contact_email || si.contact_phone) && (
                <div className="flex flex-wrap gap-3 text-sm text-gray-500">
                  {si.contact_email && <a href={`mailto:${si.contact_email}`} className="hover:text-gray-700">{si.contact_email}</a>}
                  {si.contact_phone && <a href={`tel:${si.contact_phone}`} className="hover:text-gray-700">{si.contact_phone}</a>}
                </div>
              )}
            </div>
          </div>
        );
      })()}

      {/* Phase 7.5 — category page title. Renders only when the visitor
          is on `/s/:slug/c/:category` so the page has a single H1
          that mirrors the active category. On the root `/s/:slug`
          the redirect kicks in BEFORE rendering reaches here, so this
          block is reached only in two cases:
            1. category page (categoryDef set) — title shown
            2. root + empty catalog (redirect skipped) — handled by
               the empty-state branch above, never reaches this code
          The h1 lives at page level (not inside ProductGrid) because
          ProductGrid is used in both layouts and shouldn't duplicate
          headings on the legacy single-page view. */}
      {categoryDef && (
        <div className="max-w-6xl mx-auto px-4 pt-6">
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">
            {t(categoryDef.titleKey)}
          </h1>
        </div>
      )}

      {/* S3+T1 — Chi siamo nel guscio store: su /chi-siamo E sulla root
          (bio-first: la prima pagina dello store e' l'identita') */}
      {(aboutMode || isRootAbout) && (
        <div className="max-w-6xl mx-auto px-4 pt-2 pb-4">
          <StoreAbout slug={slug} />
        </div>
      )}

      {/* V1 — home vetrina: hero brand + categorie + prossimi ritiri */}
      {isHome && (
        <div className="max-w-6xl mx-auto px-4 pt-6 pb-4">
          <StoreHome
            slug={slug}
            catalog={catalog}
            availableCategories={availableCategories}
            currency={catalog?.currency}
          />
        </div>
      )}

      {/* Phase 7.3 — entire product grid extracted into ProductGrid.jsx
          so CategoryPage (Phase 7.5) can render the same sections with
          a pre-filtered product subset. The grid handles the bucketing
          + sorting + per-section headers + the inline ProductCard
          fallback. The BookingCalendarModal stays at the page level
          (below) because it's a global modal — only ONE picker is open
          at a time across all booking products. */}
      {!isHome && !aboutMode && !isRootAbout && <ProductGrid
        products={products}
        currency={catalog.currency}
        orgSlug={slug}
        // Phase 7.5 — on a category page the h1 above already labels
        // the section, so suppress the inner section headers. On the
        // legacy single-page view (categoryDef null) keep the section
        // headers visible — they group the multi-type grid.
        hideSectionTitles={!!categoryDef}
        // Cart slices for the inline ProductCard fallback (legacy
        // products without a dedicated landing page).
        quantities={quantities}
        setQuantities={setQuantities}
        selectedOccurrences={selectedOccurrences}
        setSelectedOccurrences={setSelectedOccurrences}
        rentalDates={rentalDates}
        setRentalDates={setRentalDates}
        bookingSlots={bookingSlots}
        setBookingSlots={setBookingSlots}
        availableSlots={availableSlots}
      />}


      {/* Cleanup pass (post-Phase-7): the mobile FAB carrello that
          floated bottom-right has been removed. The header is sticky
          so the cart icon stays visible on every scroll position
          regardless of viewport size — the FAB was redundant on
          mobile and doubled the affordances. */}

      {/* Footer */}
      <footer className="bg-white border-t mt-8">
        <div className="max-w-6xl mx-auto px-4 py-4">
          {/* Wave GDPR-Commerce CG-2 — legal links anchored to the
              merchant's own per-store privacy + terms (served from
              /api/legal/storefront/<slug>/{privacy,terms} in the
              display_locale chosen by the merchant). The link is
              always rendered; the page itself gracefully shows a
              "not yet configured" placeholder when the merchant has
              not published, so the storefront UX never breaks. */}
          <div className="flex flex-wrap justify-center gap-x-6 gap-y-1 text-xs text-gray-500 mb-2">
            <Link to={`/s/${slug}/privacy`} className="hover:text-gray-900 hover:underline">
              {t('legal:storefront_legal.footer_privacy', 'Privacy')}
            </Link>
            <Link to={`/s/${slug}/terms`} className="hover:text-gray-900 hover:underline">
              {t('legal:storefront_legal.footer_terms', 'Termini')}
            </Link>
          </div>
          <p className="text-xs text-gray-400 text-center">
            {/* F2.1 — ecosistema: profilo organizzatore + directory
                (solo footer: mai dentro il funnel di checkout) */}
            <a href={`/s/${slug}/chi-siamo`} className="hover:underline">
              {t('storefront:footer.operatorProfile', { defaultValue: 'Chi siamo' })}
            </a>
            <span aria-hidden className="mx-1.5">·</span>
            <a href="/ritiri" className="hover:underline">
              {t('storefront:footer.findRetreats', { defaultValue: 'Scopri altri ritiri' })}
            </a>
            <span aria-hidden className="mx-1.5">·</span>
            {t('storefront:footer.poweredBy')}
          </p>
        </div>
      </footer>

      {/* Booking slot picker modal */}
      {(() => {
        const openPid = Object.keys(bookingSlots).find(pid => bookingSlots[pid]?._pickerOpen);
        if (!openPid) return null;
        return (
          <BookingCalendarModal
            availableSlots={availableSlots}
            bookingSlot={bookingSlots[openPid]}
            onBookingSlotChange={(bs) => setBookingSlots(prev => ({ ...prev, [openPid]: bs }))}
            onQtyChange={(qty) => setQuantities(prev => ({ ...prev, [openPid]: qty }))}
          />
        );
      })()}

      {/* Order request modal */}
      {/* K1+ — sipario marketplace: in contesto mktp il visitatore non
          deve vedere la vetrina dietro il checkout (feedback founder:
          'sembra di essere da un'altra parte'). Copre TUTTA la pagina
          store; il dialog sta sopra (z-50 > z-40). */}
      {mktpCheckout && formOpen && (
        <div className="fixed inset-0 z-40 bg-gray-50">
          <div className="h-14 border-b border-gray-200 bg-white flex items-center px-4">
            <img src="/logo-aurya-128.png" alt="" aria-hidden className="h-9 w-9 mr-2.5 select-none" draggable={false} />
            <span className="font-brand font-medium uppercase tracking-[0.28em] text-lg leading-none text-[#8a7440] select-none">{BRAND_NAME}</span>
            <span className="ml-auto text-xs text-gray-500">
              {t('storefront:checkout.securePayment', { defaultValue: 'Pagamento sicuro' })}
            </span>
          </div>
        </div>
      )}
      {formOpen && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-lg font-bold">{modeCopy.modalTitle}</h2>
                <button onClick={() => setFormOpen(false)} className="text-gray-400 hover:text-gray-600 text-xl">&times;</button>
              </div>

              <p className="text-sm text-gray-500 mb-4">
                {modeCopy.modalDesc}
              </p>

              {/* Phase 7.5 bugfix — OrderSummary receives the FULL
                  product list (catalog?.products) rather than the
                  category-filtered `products` variable. The cart can
                  contain items added on any category page, so the
                  summary's product-by-id lookups (name, price_mode,
                  rental_unit, service_options) must resolve against
                  EVERY published product, not only the ones the
                  visitor is currently viewing. Pre-fix this dropped
                  the names of off-category items (e.g. a Massaggio
                  added on /c/servizi was nameless when the modal
                  opened from /c/prodotti). Same lookup-only pattern
                  the mini-cart bar already uses (line ~1734). */}
              {/* Sprint 2 W2.2 — couponDiscount + couponLabel props per
                  live breakdown discount nel OrderSummary. Stato coupon
                  validation hosted in couponValidationState (lifted up
                  via CouponInput onValidated callback). */}
              <OrderSummary
                items={selectedItems}
                products={catalog?.products || []}
                selectedOccurrences={selectedOccurrences}
                selectedTiers={selectedTiers}
                rentalDates={rentalDates}
                bookingSlots={{
                  ...bookingSlots,
                  // F5 Onda 12 — merge service slots so OrderSummary shows
                  // the selected date/time for service products too.
                  ...Object.fromEntries(
                    Object.entries(selectedServiceSlots).map(([pid, s]) => [
                      pid, { date: s.date, start: s.start_time, end: s.end_time },
                    ])
                  ),
                }}
                currency={catalog.currency}
                shipping={shippingSummary}
                onRemove={removeFromCart}
                onQtyChange={(pid, q) => setQuantities(prev => ({ ...prev, [pid]: q }))}
                couponDiscount={couponValidationState?.discountAmount || 0}
                couponLabel={couponValidationState?.code || null}
              />

              <form onSubmit={handleSubmit} className="mt-4 space-y-3">
                {/* Onda 15 — item-specific sections come FIRST (slot review,
                    event attendees) so the customer confirms what they're
                    buying before typing personal/payment data. Customer
                    info, fulfillment, coupon, T&C follow in a second
                    logical block. */}

                {/* Onda 13 — service products in cart: read-only summary.
                    Option + slot are picked on the dedicated product landing
                    (/p/:org/:slug) and arrive here via preloadCart. If the
                    customer opened the checkout without first visiting the
                    landing (unusual path), we show a link back so they can
                    complete the selection. */}
                {serviceItemsInCart.map(({ product, options, hasSlots }) => {
                  const pid = product.id;
                  const selectedOpt = (options || []).find(o => o.id === selectedServiceOptions[pid]);
                  const selectedSlot = selectedServiceSlots[pid];
                  const needsSelection = (options.length > 0 && !selectedOpt) || (hasSlots && !selectedSlot?.date);
                  const landingUrl = product.slug ? `/p/${slug}/${product.slug}` : null;
                  return (
                    <div key={`svc-${pid}`} className="rounded-lg border border-indigo-200 bg-indigo-50/30 p-3">
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-sm font-semibold text-gray-900">{product.name}</p>
                        {landingUrl && (
                          <Link
                            to={landingUrl}
                            className="text-xs text-indigo-700 hover:underline font-medium shrink-0"
                          >{t('storefront:checkout.service.editLink')}</Link>
                        )}
                      </div>
                      {selectedOpt && (
                        <p className="text-xs text-gray-700 mt-1">
                          <span className="text-gray-500">{t('storefront:checkout.service.optionPrefix')}</span> <strong>{selectedOpt.label}</strong> — {formatAmount(Number(selectedOpt.price), catalog?.currency)}
                        </p>
                      )}
                      {selectedSlot?.date && (
                        <p className="text-xs text-gray-700 mt-0.5">
                          <strong>{new Date(selectedSlot.date + 'T12:00').toLocaleDateString(i18n.language, { weekday: 'long', day: 'numeric', month: 'long' })}</strong>
                          {' · '}{selectedSlot.start_time}
                          {selectedSlot.end_time ? ` – ${selectedSlot.end_time}` : ''}
                        </p>
                      )}
                      {needsSelection && (
                        <div className="mt-2 flex items-start gap-2 rounded-md bg-amber-50 border border-amber-200 p-2 text-xs">
                          <span className="text-amber-900">
                            {t('storefront:checkout.service.selectionRequired')}
                          </span>
                          {landingUrl && (
                            <Link
                              to={landingUrl}
                              className="underline text-amber-900 font-semibold"
                            >{t('storefront:checkout.service.openProductLink')}</Link>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}

                {/* F1 Onda 8 — per-ticket holder forms for events that
                    require attendee details. One block per product; one
                    sub-form per seat. */}
                {itemsRequiringAttendees.map(({ item, product, seatLabels }) => {
                  const pid = item.product_id;
                  const entries = attendeeDetails[pid] || [];
                  return (
                    <div key={`attendees-${pid}`} className="rounded-lg border border-blue-200 bg-blue-50/30 p-3 space-y-3">
                      <div>
                        <p className="text-sm font-semibold text-gray-900">
                          {t('storefront:checkout.attendees.title', { name: product.name })}
                        </p>
                        <p className="text-xs text-gray-600 mt-0.5">
                          {t('storefront:checkout.attendees.subtitle')}
                        </p>
                      </div>
                      {entries.map((entry, idx) => {
                        // F2 Onda 9 — pull per-field flags from the product
                        const emailReq = product.require_attendee_email !== false;
                        const phoneReq = !!product.require_attendee_phone;
                        const attendeeFieldsCfg = (product.attendee_fields || [])
                          .slice().sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0));
                        const setCustomField = (fid, value) => setAttendeeDetails(prev => {
                          const next = { ...prev };
                          next[pid] = [...(next[pid] || [])];
                          const cur = next[pid][idx] || {};
                          next[pid][idx] = {
                            ...cur,
                            custom_fields: { ...(cur.custom_fields || {}), [fid]: value },
                          };
                          return next;
                        });
                        return (
                          <div key={idx} className="rounded-md bg-white border border-gray-200 p-3 space-y-2">
                            <p className="text-xs font-semibold text-gray-700">
                              {seatLabels?.[idx] || t('storefront:checkout.attendees.ticketIndex', { index: idx + 1 })}
                            </p>
                            <input
                              type="text"
                              required
                              value={entry.name}
                              onChange={e => setAttendeeDetails(prev => {
                                const next = { ...prev };
                                next[pid] = [...(next[pid] || [])];
                                next[pid][idx] = { ...next[pid][idx], name: e.target.value };
                                return next;
                              })}
                              placeholder={t('storefront:checkout.attendees.fullNamePlaceholder')}
                              className="w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:ring-1 focus:ring-gray-800 focus:border-gray-800 outline-none"
                            />
                            <input
                              type="email"
                              required={emailReq}
                              value={entry.email}
                              onChange={e => setAttendeeDetails(prev => {
                                const next = { ...prev };
                                next[pid] = [...(next[pid] || [])];
                                next[pid][idx] = { ...next[pid][idx], email: e.target.value };
                                return next;
                              })}
                              placeholder={emailReq ? t('storefront:checkout.attendees.emailRequired') : t('storefront:checkout.attendees.emailOptional')}
                              className="w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:ring-1 focus:ring-gray-800 focus:border-gray-800 outline-none"
                            />
                            <input
                              type="tel"
                              required={phoneReq}
                              value={entry.phone}
                              onChange={e => setAttendeeDetails(prev => {
                                const next = { ...prev };
                                next[pid] = [...(next[pid] || [])];
                                next[pid][idx] = { ...next[pid][idx], phone: e.target.value };
                                return next;
                              })}
                              placeholder={phoneReq ? t('storefront:checkout.attendees.phoneRequired') : t('storefront:checkout.attendees.phoneOptional')}
                              className="w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:ring-1 focus:ring-gray-800 focus:border-gray-800 outline-none"
                            />

                            {/* F2 Onda 9 — attendee custom fields */}
                            {attendeeFieldsCfg.map(fc => {
                              const v = entry.custom_fields?.[fc.id] ?? '';
                              const common = {
                                className: "w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:ring-1 focus:ring-gray-800 focus:border-gray-800 outline-none",
                                placeholder: fc.placeholder || '',
                              };
                              return (
                                <div key={fc.id}>
                                  <label className="block text-[11px] font-medium text-gray-700 mb-0.5">
                                    {fc.label}{fc.required && ' *'}
                                  </label>
                                  {fc.type === 'textarea' ? (
                                    <textarea {...common} rows={2} value={v} onChange={e => setCustomField(fc.id, e.target.value)} />
                                  ) : fc.type === 'number' ? (
                                    <input {...common} type="number" value={v} onChange={e => setCustomField(fc.id, e.target.value)} />
                                  ) : (
                                    <input {...common} type="text" value={v} onChange={e => setCustomField(fc.id, e.target.value)} />
                                  )}
                                  {fc.help_text && (
                                    <p className="text-[10px] text-gray-500 mt-0.5">{fc.help_text}</p>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        );
                      })}
                    </div>
                  );
                })}

                {/* Customer personal info — comes AFTER item-specific selections
                    so the user first confirms the what, then fills in the who. */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{t('storefront:checkout.customer.nameLabel')}</label>
                  <input
                    type="text" required value={form.name}
                    onChange={e => setForm({ ...form, name: e.target.value })}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-gray-800 focus:border-transparent outline-none"
                    placeholder={t('storefront:checkout.customer.namePlaceholder')}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{t('storefront:checkout.customer.emailLabel')}</label>
                  <input
                    type="email" required value={form.email}
                    onChange={e => setForm({ ...form, email: e.target.value })}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-gray-800 focus:border-transparent outline-none"
                    placeholder={t('storefront:checkout.customer.emailPlaceholder')}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{t('storefront:checkout.customer.phoneLabel')}</label>
                  <input
                    type="tel" value={form.phone}
                    onChange={e => setForm({ ...form, phone: e.target.value })}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-gray-800 focus:border-transparent outline-none"
                    placeholder={t('storefront:checkout.customer.phoneOptional')}
                  />
                </div>
                {/* v10.0 + Sprint 2 W2.3 — Fulfillment mode choice.
                    Supporta 3 modes (parity widget afianco-fulfillment-picker):
                    - shipping (con shipping address required)
                    - local_pickup (ritiro merchant location)
                    - pickup_at_store (ritiro punto vendita specifico
                      configurato dal merchant — gap fix W2.3) */}
                {fulfillmentContext.needsChoice && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">{t('storefront:checkout.fulfillment.label')}</label>
                    <div className="flex gap-2 flex-wrap">
                      {fulfillmentContext.modes.map(mode => {
                        const labelMap = {
                          shipping: t('storefront:checkout.fulfillment.shipping'),
                          local_pickup: t('storefront:checkout.fulfillment.localPickup'),
                          pickup_at_store: t('storefront:checkout.fulfillment.pickupAtStore', 'Ritiro in negozio'),
                        };
                        return (
                          <button
                            key={mode}
                            type="button"
                            onClick={() => setForm({ ...form, fulfillment_mode: mode })}
                            className={`flex-1 rounded-lg border px-3 py-2 text-sm font-medium transition-colors min-w-[120px] ${
                              form.fulfillment_mode === mode
                                ? 'border-[var(--sf-accent-hover,#1f2937)] bg-[var(--sf-accent,#111827)] text-[var(--sf-accent-fg,#ffffff)]'
                                : 'border-gray-300 text-gray-700 hover:border-gray-400'
                            }`}
                          >
                            {labelMap[mode] || mode}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}
                {/* Single mode hint (not a selector). Sprint 2 W2.3 — supporta
                    anche pickup_at_store con label corretta. */}
                {!fulfillmentContext.needsChoice && fulfillmentContext.autoMode && fulfillmentContext.autoMode !== 'manual_arrangement' && (
                  <div className="text-xs text-gray-500 bg-gray-50 rounded-lg px-3 py-2">
                    {(() => {
                      const labelMap = {
                        shipping: t('storefront:checkout.fulfillment.shipping'),
                        local_pickup: t('storefront:checkout.fulfillment.localPickup'),
                        pickup_at_store: t('storefront:checkout.fulfillment.pickupAtStore', 'Ritiro in negozio'),
                      };
                      return labelMap[fulfillmentContext.autoMode] || fulfillmentContext.autoMode;
                    })()}
                  </div>
                )}
                {form.fulfillment_mode === 'shipping' && (() => {
                  // Structured shipping address block. Replaces the legacy
                  // single textarea — each field is validated separately at
                  // submit. `updateAddr` is a small helper to update one
                  // field without clobbering siblings.
                  const addr = form.shipping_address_details || {};
                  const updateAddr = (patch) => setForm(f => ({
                    ...f,
                    shipping_address_details: { ...(f.shipping_address_details || {}), ...patch },
                  }));
                  const commonInput = 'w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-gray-800 focus:border-transparent outline-none';
                  return (
                    <div className="space-y-2">
                      <label className="block text-sm font-medium text-gray-700">{t('storefront:checkout.address.label')}</label>

                      <input
                        type="text"
                        value={addr.recipient_name || ''}
                        onChange={e => updateAddr({ recipient_name: e.target.value })}
                        placeholder={t('storefront:checkout.address.recipientPlaceholder')}
                        maxLength={160}
                        className={commonInput}
                      />

                      <div className="grid grid-cols-[1fr_110px] gap-2">
                        <input
                          type="text"
                          value={addr.line1 || ''}
                          onChange={e => updateAddr({ line1: e.target.value })}
                          placeholder={t('storefront:checkout.address.streetPlaceholder')}
                          maxLength={200}
                          className={commonInput}
                        />
                        <input
                          type="text"
                          value={addr.civic || ''}
                          onChange={e => updateAddr({ civic: e.target.value })}
                          placeholder={t('storefront:checkout.address.civicPlaceholder')}
                          maxLength={20}
                          className={commonInput}
                        />
                      </div>

                      <div className="grid grid-cols-[120px_1fr_90px] gap-2">
                        <input
                          type="text"
                          value={addr.postal_code || ''}
                          onChange={e => updateAddr({ postal_code: e.target.value })}
                          placeholder={t('storefront:checkout.address.postalCodePlaceholder')}
                          maxLength={16}
                          inputMode="numeric"
                          className={`${commonInput} tabular-nums`}
                        />
                        <input
                          type="text"
                          value={addr.city || ''}
                          onChange={e => updateAddr({ city: e.target.value })}
                          placeholder={t('storefront:checkout.address.cityPlaceholder')}
                          maxLength={120}
                          className={commonInput}
                        />
                        <input
                          type="text"
                          value={addr.province || ''}
                          onChange={e => updateAddr({ province: e.target.value.toUpperCase() })}
                          placeholder={t('storefront:checkout.address.provincePlaceholder')}
                          maxLength={2}
                          className={`${commonInput} uppercase tracking-wide`}
                        />
                      </div>

                      <select
                        value={addr.country || 'IT'}
                        onChange={e => updateAddr({ country: e.target.value })}
                        className={commonInput}
                      >
                        <option value="IT">{t('storefront:checkout.address.country.IT')}</option>
                        <option value="FR">{t('storefront:checkout.address.country.FR')}</option>
                        <option value="DE">{t('storefront:checkout.address.country.DE')}</option>
                        <option value="CH">{t('storefront:checkout.address.country.CH')}</option>
                        <option value="AT">{t('storefront:checkout.address.country.AT')}</option>
                        <option value="ES">{t('storefront:checkout.address.country.ES')}</option>
                        <option value="SI">{t('storefront:checkout.address.country.SI')}</option>
                        <option value="HR">{t('storefront:checkout.address.country.HR')}</option>
                      </select>
                    </div>
                  );
                })()}

                {/* Shipping option picker — visible only when the cart has
                    physical items AND the customer picked "shipping" mode.
                    Empty options list surfaces a banner so the merchant is
                    nudged to configure at least one option. */}
                {hasPhysicalCart && form.fulfillment_mode === 'shipping' && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">{t('storefront:checkout.shippingOptions.label')}</label>
                    {shippingOptions.length === 0 ? (
                      <div className="rounded-lg bg-amber-50 border border-amber-200 px-3 py-2 text-xs text-amber-900">
                        {t('storefront:checkout.shippingOptions.empty')}
                      </div>
                    ) : (
                      <div className="space-y-1.5">
                        {shippingOptions.map(opt => {
                          const base = Number(opt.base_price || 0);
                          const threshold = opt.free_shipping_threshold;
                          const free = threshold != null && physicalSubtotal >= Number(threshold);
                          const selected = form.shipping_option_id === opt.id;
                          return (
                            <label
                              key={opt.id}
                              className={`flex items-start gap-2 rounded-lg border px-3 py-2 cursor-pointer transition-colors ${
                                selected
                                  ? 'border-gray-800 bg-gray-50'
                                  : 'border-gray-300 hover:border-gray-400 bg-white'
                              }`}
                            >
                              <input
                                type="radio"
                                name="shipping_option"
                                value={opt.id}
                                checked={selected}
                                onChange={() => setForm({ ...form, shipping_option_id: opt.id })}
                                className="mt-0.5"
                              />
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center justify-between gap-2">
                                  <span className="text-sm font-medium text-gray-900">{opt.label}</span>
                                  <span className="text-sm tabular-nums">
                                    {free ? (
                                      <>
                                        <span className="line-through text-gray-400 mr-1">
                                          {fmtPrice(base, catalog.currency)}
                                        </span>
                                        <span className="text-green-700 font-semibold">{t('storefront:summary.shippingFree')}</span>
                                      </>
                                    ) : (
                                      <span className="font-semibold">{fmtPrice(base, catalog.currency)}</span>
                                    )}
                                  </span>
                                </div>
                                {opt.description && (
                                  <p className="text-[11px] text-gray-500 mt-0.5">{opt.description}</p>
                                )}
                                {threshold != null && !free && (
                                  <p className="text-[11px] text-blue-700 mt-0.5">
                                    {t('storefront:summary.addMoreForFree', { amount: fmtPrice(Math.max(0, Number(threshold) - physicalSubtotal), catalog.currency) })}
                                  </p>
                                )}
                              </div>
                            </label>
                          );
                        })}
                      </div>
                    )}
                  </div>
                )}
                {/* F2 Onda 9 — order-level custom fields, rendered inline
                    as standalone fields (F4 fix: removed "Dati ordine"
                    wrapper). Each field uses its own label as the title,
                    same style as Nome/Email/Note above. */}
                {orderFieldsConfig.map(fc => {
                  const v = orderFieldsData[fc.id] ?? '';
                  const setV = (next) => setOrderFieldsData(prev => ({ ...prev, [fc.id]: next }));
                  const common = {
                    className: "w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-gray-800 focus:border-transparent outline-none",
                    placeholder: fc.placeholder || '',
                  };
                  return (
                    <div key={fc.id}>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        {fc.label}{fc.required && ' *'}
                      </label>
                      {fc.type === 'textarea' ? (
                        <textarea {...common} rows={2} value={v} onChange={e => setV(e.target.value)} />
                      ) : fc.type === 'number' ? (
                        <input {...common} type="number" value={v} onChange={e => setV(e.target.value)} />
                      ) : (
                        <input {...common} type="text" value={v} onChange={e => setV(e.target.value)} />
                      )}
                      {fc.help_text && (
                        <p className="text-[11px] text-gray-500 mt-0.5">{fc.help_text}</p>
                      )}
                    </div>
                  );
                })}

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{t('storefront:checkout.notesLabel')}</label>
                  <textarea
                    value={form.notes}
                    onChange={e => setForm({ ...form, notes: e.target.value })}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-gray-800 focus:border-transparent outline-none"
                    rows={2} placeholder={t('storefront:checkout.notesPlaceholder')}
                  />
                </div>

                {/* Onda 15 — service slot review + event attendees blocks
                    were moved up above the customer info form so the "what"
                    comes before the "who". Keeping an empty marker here for
                    reviewer orientation. */}

                {/* F1 Onda 8 — per-ticket holder forms for events that
                    require attendee details. MOVED UP (Onda 15). */}
                {/* Attendees block moved up above customer info (Onda 15). */}

                {/* Sprint 2 W2.1 — coupon dry-run validation (parity
                    widget E4.1). CouponInput component wraps useCouponValidation
                    hook che fa debounced POST /coupons/validate/{slug}
                    con cart subtotal. Customer vede badge verde/rosso
                    live invece di scoprire al checkout. */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{t('storefront:checkout.couponLabel')}</label>
                  <CouponInput
                    slug={slug}
                    value={form.coupon_code}
                    onChange={(v) => setForm({ ...form, coupon_code: v })}
                    cartSubtotal={(() => {
                      // Subtotal = somma items * qty * rentalMult (mirror del
                      // calcolo OrderSummary). Calcolato inline per essere
                      // reattivo a cambi cart senza extra state.
                      try {
                        const prods = catalog?.products || [];
                        return (selectedItems || []).reduce((sum, it) => {
                          const p = prods.find(x => x.id === it.product_id);
                          if (!p) return sum;
                          const price = Number(p.unit_price) || 0;
                          return sum + price * (it.quantity || 1);
                        }, 0);
                      } catch {
                        return 0;
                      }
                    })()}
                    placeholder={t('storefront:checkout.couponPlaceholder')}
                  />
                </div>

                {/* F4 Onda 11 — Terms & Conditions acceptance block.
                    Renders only when the merchant has configured T&C
                    (store-level enabled, or product-level override). */}
                {effectiveTerms && (
                  <div className="rounded-lg border border-gray-300 bg-gray-50/50 p-3 space-y-2">
                    <label className="flex items-start gap-2 cursor-pointer select-none">
                      <input
                        type="checkbox"
                        checked={termsAccepted}
                        onChange={e => setTermsAccepted(e.target.checked)}
                        className="mt-0.5 shrink-0 h-4 w-4 rounded border-gray-300 text-gray-900 focus:ring-gray-900"
                        required
                      />
                      <span className="text-sm text-gray-800">
                        {t('storefront:checkout.terms.prefix')}{' '}
                        <button
                          type="button"
                          onClick={() => setTermsExpanded(v => !v)}
                          className="underline text-gray-900 hover:no-underline"
                        >
                          {t('storefront:checkout.terms.linkLabel')}
                        </button>
                        {' *'}
                      </span>
                    </label>
                    {termsExpanded && (
                      <div className="mt-2 pt-2 border-t border-gray-200 max-h-64 overflow-y-auto bg-white rounded-md p-3">
                        <MarkdownLite source={effectiveTerms} />
                      </div>
                    )}
                  </div>
                )}

                {/* Wave GDPR-Commerce CG-5 — per-order GDPR consent block.
                    Renders ONLY when the merchant has published their
                    per-store Privacy + Terms (CG-3 admin UI). Legacy
                    stores skip this entire block — backward compat.

                    2026-05-20 — Two INDEPENDENT visibility rules:
                      a. Privacy + Terms checkboxes appear ONLY for
                         guests. Logged-in customers have a fresh CG-4
                         snapshot (the re-consent modal blocks the UI
                         before they reach checkout when versions
                         change), so re-asking is redundant.
                      b. Marketing checkbox appears ONLY when the
                         customer is NOT already opted-in, regardless
                         of guest vs registered. ``useIsMarketingOptedIn``
                         resolves the state from customer.accepted_*
                         (logged-in path) or the public marketing-status
                         endpoint (guest path with debounced lookup).
                         When already opted-in we show a small info line
                         pointing to the unsubscribe link instead.

                    The two outer guards (block visibility) are now
                    OR-composed: render the container if AT LEAST one
                    of the inner sections will appear. */}
                {gdprRequired && (!isCustomerAuthenticated || !marketingStatus.isOptedIn) && (
                  <div className="rounded-lg border border-blue-200 bg-blue-50/40 p-3 space-y-2">
                    <p className="text-xs font-medium text-blue-900 uppercase tracking-wide">
                      {t('storefront:checkout.gdpr.title', { defaultValue: 'Privacy e Termini' })}
                    </p>
                    {/* Privacy + Terms — guest only (CG-4 covers registered). */}
                    {!isCustomerAuthenticated && (
                      <>
                        <label className="flex items-start gap-2 cursor-pointer select-none">
                          <input
                            type="checkbox"
                            checked={gdprPrivacyAccepted}
                            onChange={e => setGdprPrivacyAccepted(e.target.checked)}
                            className="mt-0.5 shrink-0 h-4 w-4 rounded border-gray-300 text-gray-900 focus:ring-gray-900"
                            required
                          />
                          <span className="text-sm text-gray-800">
                            {t('storefront:checkout.gdpr.privacy_prefix', { defaultValue: 'Ho letto l\u2019' })}
                            <a
                              href={`/s/${encodeURIComponent(slug || '')}/privacy`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="underline text-blue-700 hover:no-underline"
                            >
                              {t('storefront:checkout.gdpr.privacy_link', { defaultValue: 'Informativa sulla Privacy' })}
                            </a>
                            {' *'}
                          </span>
                        </label>
                        <label className="flex items-start gap-2 cursor-pointer select-none">
                          <input
                            type="checkbox"
                            checked={gdprTermsAccepted}
                            onChange={e => setGdprTermsAccepted(e.target.checked)}
                            className="mt-0.5 shrink-0 h-4 w-4 rounded border-gray-300 text-gray-900 focus:ring-gray-900"
                            required
                          />
                          <span className="text-sm text-gray-800">
                            {t('storefront:checkout.gdpr.terms_prefix', { defaultValue: 'Accetto i' })}{' '}
                            <a
                              href={`/s/${encodeURIComponent(slug || '')}/terms`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="underline text-blue-700 hover:no-underline"
                            >
                              {t('storefront:checkout.gdpr.terms_link', { defaultValue: 'Termini e Condizioni' })}
                            </a>
                            {' *'}
                          </span>
                        </label>
                      </>
                    )}
                    {/* Marketing — visible only when NOT already opted-in.
                        Replaced by a small info line otherwise. */}
                    {!marketingStatus.isOptedIn ? (
                      <label className="flex items-start gap-2 cursor-pointer select-none">
                        <input
                          type="checkbox"
                          checked={gdprMarketingAccepted}
                          onChange={e => setGdprMarketingAccepted(e.target.checked)}
                          className="mt-0.5 shrink-0 h-4 w-4 rounded border-gray-300 text-gray-900 focus:ring-gray-900"
                        />
                        <span className="text-sm text-gray-600">
                          {t('storefront:checkout.gdpr.marketing', {
                            defaultValue: 'Desidero ricevere comunicazioni promozionali (opzionale, revocabile in qualsiasi momento)'
                          })}
                        </span>
                      </label>
                    ) : (
                      <p className="text-xs text-gray-600 italic">
                        ℹ️ {t('storefront:checkout.gdpr.already_opted_in', {
                          defaultValue: 'Sei già iscritto alla newsletter. Per disiscriverti usa il link in fondo a ogni email.',
                        })}
                      </p>
                    )}
                  </div>
                )}

                {/* ── Optional ecommerce registration (Fase C1) ─────────────
                    Visible only for guest shoppers: a logged-in customer has
                    nothing to do here. Isolated from admin auth by using the
                    customer-auth endpoints (handled in Fase C2). */}
                {/* K2 — contesto marketplace: niente account del negozio;
                    il viaggiatore ha il Passaporto (post-acquisto, zero campi) */}
                {mktpCheckout && !requiresCustomerAccount && !isCustomerAuthenticated && (
                  <div className="rounded-lg border border-primary/25 bg-primary/5 p-3 flex items-start gap-2">
                    <img src="/logo-aurya-128.png" alt="" aria-hidden className="h-5 w-5 mt-0.5 select-none" draggable={false} />
                    <p className="text-xs text-gray-700">
                      {t('storefront:checkout.passportHint', { defaultValue: 'I tuoi viaggi in un posto solo: dopo l\'acquisto ricevi via email il link al tuo Passaporto — senza password.' })}
                    </p>
                  </div>
                )}
                {(!mktpCheckout || requiresCustomerAccount) && !isCustomerAuthenticated && (() => {
                  const emailOk = !!form.email && form.email.includes('@');
                  const strength = computePasswordStrength(regPassword);
                  const mismatch = wantRegister && regPassword && regPasswordConfirm && regPassword !== regPasswordConfirm;
                  return (
                    <div className={`rounded-lg border p-3 space-y-2 ${
                      requiresCustomerAccount
                        ? 'border-blue-300 bg-blue-50/60'
                        : 'border-gray-200 bg-gray-50/60'
                    }`}>
                      {/* Release 4 (Courses) — contextual banner when the cart
                          contains a course. The account is MANDATORY here:
                          the checkbox is forced-on and non-dismissable. */}
                      {requiresCustomerAccount && (
                        <div className="flex items-start gap-2 rounded-md bg-blue-100/60 border border-blue-200 px-2 py-1.5">
                          <span aria-hidden />
                          <p className="text-xs text-blue-900">
                            <strong>{t('storefront:checkout.signup.courseAlertTitle')}</strong>{' '}
                            {t('storefront:checkout.signup.courseAlertBody')}
                          </p>
                        </div>
                      )}
                      <label className={`flex items-start gap-2 select-none ${
                        requiresCustomerAccount ? 'cursor-default' : 'cursor-pointer'
                      }`}>
                        <input
                          type="checkbox"
                          checked={wantRegister || requiresCustomerAccount}
                          disabled={!emailOk || requiresCustomerAccount}
                          onChange={e => {
                            if (requiresCustomerAccount) return;   // cannot opt out
                            setWantRegister(e.target.checked);
                          }}
                          className="mt-0.5 shrink-0"
                          aria-describedby="reg-hint"
                        />
                        <span className="text-sm text-gray-800">
                          <span className="font-medium">
                            {requiresCustomerAccount ? t('storefront:checkout.signup.createAccountRequired') : t('storefront:checkout.signup.createAccount')}
                          </span>
                          <span className="text-gray-600">
                            {requiresCustomerAccount
                              ? t('storefront:checkout.signup.suffixCourse')
                              : t('storefront:checkout.signup.suffixOrders')}
                          </span>
                          {!emailOk && (
                            <span className="block text-[11px] text-gray-500 mt-0.5">
                              {t('storefront:checkout.signup.fillEmailFirst')}
                            </span>
                          )}
                        </span>
                      </label>
                      {/* Alternative path for shoppers who already have an account */}
                      <p className="text-[11px] text-gray-500 pl-6">
                        {t('storefront:checkout.signup.alreadyHaveAccount')}{' '}
                        <Link
                          to={`/account/login?slug=${encodeURIComponent(slug || '')}`}
                          className="text-gray-700 underline hover:no-underline"
                        >
                          {t('storefront:checkout.signup.loginLink')}
                        </Link>
                      </p>
                      {wantRegister && emailOk && (
                        <div id="reg-hint" className="pl-6 space-y-2">
                          <div>
                            <label className="block text-xs font-medium text-gray-700 mb-1">{t('storefront:checkout.signup.passwordLabel')}</label>
                            <div className="relative">
                              <input
                                type={showRegPassword ? 'text' : 'password'}
                                value={regPassword}
                                onChange={e => setRegPassword(e.target.value)}
                                autoComplete="new-password"
                                aria-describedby="reg-strength"
                                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-gray-800 focus:border-transparent outline-none pr-16"
                                placeholder={t('storefront:checkout.signup.passwordPlaceholder')}
                              />
                              <button
                                type="button"
                                onClick={() => setShowRegPassword(s => !s)}
                                className="absolute right-2 top-1/2 -translate-y-1/2 text-[11px] text-gray-500 hover:text-gray-700"
                                tabIndex={-1}
                              >
                                {showRegPassword ? t('storefront:checkout.signup.hidePw') : t('storefront:checkout.signup.showPw')}
                              </button>
                            </div>
                            {/* Strength meter — visual only; server re-validates */}
                            <div id="reg-strength" className="mt-1">
                              <div className="flex gap-1 h-1" aria-hidden="true">
                                {[0, 1, 2, 3].map(i => (
                                  <span
                                    key={i}
                                    className={`flex-1 rounded-full transition-colors ${
                                      i < strength.score
                                        ? strength.score >= 3 ? 'bg-emerald-500' : strength.score >= 2 ? 'bg-amber-500' : 'bg-red-400'
                                        : 'bg-gray-200'
                                    }`}
                                  />
                                ))}
                              </div>
                              {regPassword && !strength.ok && (
                                <p className="text-[11px] text-gray-500 mt-1">
                                  {strength.reasonCodes.map(c => t(`storefront:password.${c}`)).join(' · ')}
                                </p>
                              )}
                            </div>
                          </div>
                          <div>
                            <label className="block text-xs font-medium text-gray-700 mb-1">{t('storefront:checkout.signup.passwordConfirmLabel')}</label>
                            <input
                              type={showRegPassword ? 'text' : 'password'}
                              value={regPasswordConfirm}
                              onChange={e => setRegPasswordConfirm(e.target.value)}
                              autoComplete="new-password"
                              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-gray-800 focus:border-transparent outline-none"
                              placeholder={t('storefront:checkout.signup.passwordConfirmPlaceholder')}
                            />
                            {mismatch && (
                              <p className="text-[11px] text-red-500 mt-1">{t('storefront:checkout.signup.passwordMismatch')}</p>
                            )}
                          </div>
                          <p className="text-[11px] text-gray-500">
                            {t('storefront:checkout.signup.confirmEmailHint')}
                          </p>
                        </div>
                      )}
                    </div>
                  );
                })()}

                <button
                  type="submit"
                  disabled={submitting || selectedItems.length === 0 || !attendeesValid || !orderFieldsValid || !termsValid || !gdprValid || !servicesValid || (wantRegister && !isCustomerAuthenticated && (!computePasswordStrength(regPassword).ok || regPassword !== regPasswordConfirm))}
                  className="w-full py-2.5 rounded-lg text-sm font-medium disabled:opacity-50 transition-colors"
                  style={catalog?.store_info?.brand_color
                    ? { backgroundColor: catalog.store_info.brand_color, color: catalog.store_info.brand_color_text || '#fff' }
                    : { backgroundColor: '#1a1a1a', color: '#fff' }
                  }
                >
                  {submitting ? t('storefront:checkout.submittingBtn') : modeCopy.submitBtn}
                </button>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
