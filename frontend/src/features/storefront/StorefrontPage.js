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
import { storefrontAPI } from '../../api/storefront';
import { customerAuthAPI } from '../../api/customerAuth';
import { publicShippingOptions } from '../../api/shippingOptions';
import { useStorefrontLocaleSync } from './hooks/useStorefrontLocaleSync';
import useStorefrontCart from './hooks/useStorefrontCart';
// PS6.10 — lettura diretta dello snapshot carrello per il feedback
// "?checkout=1 con carrello vuoto" (la fonte di verita' della persistenza).
import { hydrateCart } from './hooks/useCartStorage';
import useAvailableCategories from './hooks/useAvailableCategories';
import useDesignTokens from './hooks/useDesignTokens';
import { CATEGORY_BY_SLUG, isKnownCategorySlug } from './categories';
import StorefrontHeader from './components/StorefrontHeader';
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
// PN2 (PROFILO_NEGOZIO_PIANO_2026-07) — il checkout e' estratto in
// componenti/hook dedicati: OrderSummary + CheckoutForm (JSX spostato
// tale e quale) e useCheckoutForm (stati + validazioni + handleSubmit).
// Comportamento invariato: solo codice spostato.
import OrderSummary from './components/checkout/OrderSummary';
import CheckoutForm from './components/checkout/CheckoutForm';
import useCheckoutForm from './hooks/useCheckoutForm';
import { BookingCalendarModal } from './components/StorefrontCards';
import { useCustomerAuth } from '../../context/CustomerAuthContext';
import { User, ShoppingCart } from 'lucide-react';
import { toast } from 'sonner';
import { BRAND_NAME } from '../../config/brand';


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


  const [availableSlots, setAvailableSlots] = useState(null); // null | [{date, day_name, slots}]


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

  // PS6.2 — stato del recupero preload per prodotto ('pending' |
  // 'done' | 'failed'): un solo refetch per prodotto, niente loop.
  const preloadRecoveryRef = useRef({});
  // PS6.10 — feedback "carrello vuoto" mostrato al massimo una volta.
  const emptyCheckoutNoticeRef = useRef(false);

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
    if (!product) {
      // PS6.2 — il catalogo in lingua non contiene il prodotto del
      // handoff /p/ → /s/ (traduzione mancante: il filtro lingua del
      // catalogo lo esclude, la landing /p/ invece serve il fallback
      // italiano). Recupero a basso rischio: UN refetch del catalogo
      // SENZA filtro lingua (lingua sorgente IT, sempre completa); se
      // il prodotto c'e', lo si innesta nel catalogo corrente (il
      // resto della vetrina resta nella lingua scelta) e l'effetto
      // ri-gira idratando il carrello. Se manca anche li' (spublicato)
      // → toast onesto, niente vetrina muta col toast "Aggiunto".
      const pid = preload.productId;
      const mergeRecovered = (recovered) => setCatalog(prev => {
        if (!prev) return prev;
        if ((prev.products || []).some(p => p.id === pid)) return prev;
        return { ...prev, products: [...(prev.products || []), recovered] };
      });
      const attempt = preloadRecoveryRef.current[pid];
      if (attempt?.status === 'done') {
        // Un refetch concorrente del catalogo (strict-mode/cambio lingua)
        // ha sovrascritto il merge: si re-innesta dal prodotto gia'
        // recuperato, senza nuove chiamate (idempotente, niente loop).
        mergeRecovered(attempt.product);
        return;
      }
      if (!attempt) {
        preloadRecoveryRef.current[pid] = { status: 'pending' };
        (async () => {
          let found = null;
          try {
            const res = await storefrontAPI.getCatalog(slug);
            found = (res.data?.products || []).find(p => p.id === pid) || null;
          } catch { /* rete giu': si cade nel ramo onesto */ }
          if (found) {
            preloadRecoveryRef.current[pid] = { status: 'done', product: found };
            mergeRecovered(found);
            return;
          }
          preloadRecoveryRef.current[pid] = { status: 'failed' };
          toast.error(t('storefront:errors.preloadUnavailableInLanguage', {
            defaultValue: 'Questo servizio non è disponibile nella lingua della vetrina.',
          }));
          // Router state via: un refresh non deve ritentare l'idratazione.
          window.history.replaceState(
            { ...(window.history.state || {}), usr: undefined },
            '', window.location.pathname + window.location.search,
          );
        })();
      }
      return;
    }
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

  // PN2 — stati checkout + validazioni + handleSubmit impacchettati in
  // useCheckoutForm (vedi hooks/useCheckoutForm.js). La pagina resta
  // l'unica fonte del comportamento attuale: qui si destruttura solo
  // cio' che gli effetti/JSX di pagina continuano a usare.
  const checkout = useCheckoutForm({
    slug,
    catalog,
    selectedItems,
    getOrderedTierEntries,
    customer,
    isCustomerAuthenticated,
    customerSignup,
    attendeeDetails,
    setAttendeeDetails,
    orderFieldsData,
    selectedServiceOptions,
    selectedServiceSlots,
    clearCartSnapshot,
    loadAvailability,
    t,
  });
  const {
    setForm,
    formOpen, setFormOpen,
    submitted, setSubmitted,
    mktpCheckout, setMktpCheckout,
    setShippingOptions,
    shippingSummary,
    couponValidationState,
    modeCopy,
  } = checkout;

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
    const stripParam = () => {
      params.delete('checkout');
      const newSearch = params.toString();
      navigate(
        location.pathname + (newSearch ? `?${newSearch}` : '') + location.hash,
        { replace: true },
      );
    };
    // Only open if there is something to check out; otherwise wait for the
    // cart to hydrate (selectedItems.length will change, re-triggering).
    if (selectedItems.length === 0) {
      // PS6.10 — carrello DAVVERO vuoto (nessuno snapshot in sessione e
      // nessun preload in arrivo): il param non deve restare appeso
      // nell'URL senza alcun feedback. Un colpo solo per pagina.
      if (catalog && !location.state?.preloadCart && !emptyCheckoutNoticeRef.current) {
        let snapshotHasItems = false;
        try {
          const snap = hydrateCart(slug);
          snapshotHasItems = !!snap && Object.values(snap.quantities || {}).some(q => q > 0);
        } catch { /* storage inaccessibile */ }
        if (!snapshotHasItems) {
          emptyCheckoutNoticeRef.current = true;
          toast.info(t('storefront:errors.checkoutEmptyCart', {
            defaultValue: 'Il tuo carrello è vuoto: aggiungi un servizio o un ritiro per procedere.',
          }));
          stripParam();
        }
      }
      return;
    }
    setFormOpen(true);
    stripParam();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.search, location.pathname, location.hash, selectedItems.length, navigate, catalog]);

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
            {/* F2.1 — ecosistema: profilo professionista + directory
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

              <CheckoutForm
                checkout={checkout}
                slug={slug}
                catalog={catalog}
                selectedItems={selectedItems}
                isCustomerAuthenticated={isCustomerAuthenticated}
                attendeeDetails={attendeeDetails}
                setAttendeeDetails={setAttendeeDetails}
                orderFieldsData={orderFieldsData}
                setOrderFieldsData={setOrderFieldsData}
                selectedServiceOptions={selectedServiceOptions}
                selectedServiceSlots={selectedServiceSlots}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
