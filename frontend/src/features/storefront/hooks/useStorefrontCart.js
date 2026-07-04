/**
 * useStorefrontCart — single source of truth for the storefront cart.
 *
 * Why this hook exists
 * --------------------
 * Phase 7 of the storefront redesign introduces per-category pages
 * (/s/:slug/c/:category). Each category page needs the SAME cart
 * behaviour as the legacy single-page storefront:
 *
 *   - 10 product-scoped state slices (quantities, occurrences, tiers,
 *     rental dates, booking slots, attendee details, order fields,
 *     service options, service slots, extra selections)
 *   - sessionStorage persistence keyed by store slug (survives the
 *     SPA route remount when navigating between categories or to a
 *     product landing page)
 *   - rehydrate on mount so a returning visitor finds their bag intact
 *   - dispatch `storefront:cart:change` CustomEvent so landing-page
 *     cart badges (useCartCount) stay in sync without polling
 *   - 5-second undo window on remove (toast action button)
 *
 * Without this hook, every page that renders products would need to
 * duplicate ~150 lines of identical state plumbing. A drift between
 * StorefrontPage and CategoryPage would silently break cart continuity
 * across navigation (the bug the sessionStorage layer was originally
 * built to prevent — see useCartStorage.js).
 *
 * Contract (what callers should know)
 * -----------------------------------
 * The hook returns a single bundle containing:
 *
 *   { quantities, setQuantities,
 *     selectedOccurrences, setSelectedOccurrences,
 *     selectedTiers, setSelectedTiers,
 *     rentalDates, setRentalDates,
 *     bookingSlots, setBookingSlots,
 *     attendeeDetails, setAttendeeDetails,
 *     orderFieldsData, setOrderFieldsData,
 *     selectedServiceOptions, setSelectedServiceOptions,
 *     selectedServiceSlots, setSelectedServiceSlots,
 *     selectedExtraSelections, setSelectedExtraSelections,
 *     // helpers
 *     removeFromCart,           // (productId) => void  — 5s undo toast
 *     undoRemoveFromCart,       // (productId) => void  — restore snapshot
 *     clearCartSnapshot,        // () => void           — wipe sessionStorage
 *   }
 *
 * Callers pass:
 *   - `slug`            store slug (drives the sessionStorage key)
 *   - `t`               i18next t() function for toast strings
 *   - `productsLookup`  array of catalog products (used by removeFromCart
 *                       to resolve a name for the "Annulla" toast). May
 *                       be empty during catalog load — toast falls back
 *                       to a generic name.
 *
 * Why a hook and not a Context provider?
 * --------------------------------------
 * Each storefront page owns its own cart instance — Context provider
 * would require wrapping the entire route tree, complicating SSR/init
 * for landing pages that don't need write access (they just read
 * count via useCartCount). Hook is local, testable in isolation, and
 * matches the existing `useStorefrontLocaleSync` pattern.
 *
 * Note on identity
 * ----------------
 * The 10 setters are returned BY REFERENCE from useState — same setter
 * identity across renders — so callers can put them in useCallback /
 * useMemo deps without infinite-render loops.
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { toast } from 'sonner';
import { hydrateCart, persistCart, clearCart } from './useCartStorage';
// Phase 0 Step 4b (2026-05-28) — sidecar dual-write to server-side cart.
// Inactive when feature flag REACT_APP_PERSISTENT_CART_ENABLED is false
// (default). Zero impact on sessionStorage-based behavior when off.
import { usePersistentCartSync } from './usePersistentCartSync';


export default function useStorefrontCart({ slug, t, productsLookup }) {
  // ── 10 product-scoped state slices ─────────────────────────────────────
  // Identical shapes to the legacy StorefrontPage state. Documented
  // inline so this file stays self-describing for future readers.

  // { productId: qty } — primary "is-this-in-the-cart" signal.
  const [quantities, setQuantities] = useState({});

  // { productId: occurrence } — event_ticket: which date the customer picked.
  const [selectedOccurrences, setSelectedOccurrences] = useState({});

  // { productId: { tierId: qty } } — event_ticket multi-tier cart.
  const [selectedTiers, setSelectedTiers] = useState({});

  // { productId: { from, to, notes } } — rental product date range.
  const [rentalDates, setRentalDates] = useState({});

  // { productId: { date, start, end } } — legacy booking slot.
  const [bookingSlots, setBookingSlots] = useState({});

  // { productId: [{ name, email, phone, custom_fields }] } — per-ticket forms.
  const [attendeeDetails, setAttendeeDetails] = useState({});

  // { fieldId: value } — order-level custom fields (merged across products).
  const [orderFieldsData, setOrderFieldsData] = useState({});

  // { productId: optionId } — service product option choice.
  const [selectedServiceOptions, setSelectedServiceOptions] = useState({});

  // { productId: { date, start_time, end_time } } — service slot choice.
  const [selectedServiceSlots, setSelectedServiceSlots] = useState({});

  // { productId: { optional_ids: [], radio_picks: {} } } — reservation extras.
  const [selectedExtraSelections, setSelectedExtraSelections] = useState({});

  // ── 1. Rehydrate on mount ──────────────────────────────────────────────
  //
  // Runs once per slug. The page-level preloadCart effect (handed off
  // from a landing page) mounts AFTER this effect (React effect ordering)
  // and merges its values via the same spread setters, so the hydrate
  // doesn't fight the merge.
  useEffect(() => {
    if (!slug) return;
    const restored = hydrateCart(slug);
    if (!restored) return;
    // Only apply slices that have actual content — never clobber the
    // existing default `{}` with another empty `{}` (avoids extra renders).
    if (restored.quantities && Object.keys(restored.quantities).length > 0)
      setQuantities(restored.quantities);
    if (restored.selectedOccurrences && Object.keys(restored.selectedOccurrences).length > 0)
      setSelectedOccurrences(restored.selectedOccurrences);
    if (restored.selectedTiers && Object.keys(restored.selectedTiers).length > 0)
      setSelectedTiers(restored.selectedTiers);
    if (restored.rentalDates && Object.keys(restored.rentalDates).length > 0)
      setRentalDates(restored.rentalDates);
    if (restored.bookingSlots && Object.keys(restored.bookingSlots).length > 0)
      setBookingSlots(restored.bookingSlots);
    if (restored.attendeeDetails && Object.keys(restored.attendeeDetails).length > 0)
      setAttendeeDetails(restored.attendeeDetails);
    if (restored.orderFieldsData && Object.keys(restored.orderFieldsData).length > 0)
      setOrderFieldsData(restored.orderFieldsData);
    if (restored.selectedServiceOptions && Object.keys(restored.selectedServiceOptions).length > 0)
      setSelectedServiceOptions(restored.selectedServiceOptions);
    if (restored.selectedServiceSlots && Object.keys(restored.selectedServiceSlots).length > 0)
      setSelectedServiceSlots(restored.selectedServiceSlots);
    if (restored.selectedExtraSelections && Object.keys(restored.selectedExtraSelections).length > 0)
      setSelectedExtraSelections(restored.selectedExtraSelections);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slug]);

  // ── 2. Persist on every change ─────────────────────────────────────────
  //
  // React batches multiple synchronous setState calls so the effect
  // fires once per render, not per slice. sessionStorage writes are ~μs
  // so this stays cheap even with rapid qty +/- clicks.
  useEffect(() => {
    if (!slug) return;
    const snap = {
      quantities, selectedOccurrences, selectedTiers,
      rentalDates, bookingSlots, attendeeDetails,
      orderFieldsData, selectedServiceOptions,
      selectedServiceSlots, selectedExtraSelections,
    };
    const hasAny = Object.values(snap).some(
      v => v && typeof v === 'object' && Object.keys(v).length > 0
    );
    if (hasAny) persistCart(slug, snap);
    else clearCart(slug);

    // Notify same-tab listeners (landing pages' useCartCount) so the
    // back-link badge updates immediately. The CustomEvent constructor
    // can throw on very old Safari — degrade silently.
    try {
      window.dispatchEvent(new CustomEvent('storefront:cart:change', { detail: { slug } }));
    } catch {
      /* old Safari */
    }
  }, [
    slug,
    quantities, selectedOccurrences, selectedTiers,
    rentalDates, bookingSlots, attendeeDetails,
    orderFieldsData, selectedServiceOptions,
    selectedServiceSlots, selectedExtraSelections,
  ]);

  // ── 3. Cart removal with 5s undo window ────────────────────────────────
  //
  // Snapshots live in a ref (not state) so undo doesn't trigger a
  // re-render during the countdown. React batching keeps the 9 setState
  // calls atomic — the persist effect catches up once.
  const undoSnapshotsRef = useRef({});   // { [productId]: {qty, occurrence, tiers, ...} }
  const undoTimersRef = useRef({});      // { [productId]: timeoutId }

  const undoRemoveFromCart = useCallback((productId) => {
    const snap = undoSnapshotsRef.current[productId];
    if (!snap) return;
    // Restore only the slices that were populated before removal. Using
    // `!= null` on qty to include 0 (defensive — 0 shouldn't appear but
    // if it does we preserve exactly what was there).
    if (snap.qty != null)         setQuantities(prev => ({ ...prev, [productId]: snap.qty }));
    if (snap.occurrence)          setSelectedOccurrences(prev => ({ ...prev, [productId]: snap.occurrence }));
    if (snap.tiers)               setSelectedTiers(prev => ({ ...prev, [productId]: snap.tiers }));
    if (snap.rentalDate)          setRentalDates(prev => ({ ...prev, [productId]: snap.rentalDate }));
    if (snap.bookingSlot)         setBookingSlots(prev => ({ ...prev, [productId]: snap.bookingSlot }));
    if (snap.attendees)           setAttendeeDetails(prev => ({ ...prev, [productId]: snap.attendees }));
    if (snap.serviceOption)       setSelectedServiceOptions(prev => ({ ...prev, [productId]: snap.serviceOption }));
    if (snap.serviceSlot)         setSelectedServiceSlots(prev => ({ ...prev, [productId]: snap.serviceSlot }));
    if (snap.extras)              setSelectedExtraSelections(prev => ({ ...prev, [productId]: snap.extras }));

    delete undoSnapshotsRef.current[productId];
    if (undoTimersRef.current[productId]) {
      clearTimeout(undoTimersRef.current[productId]);
      delete undoTimersRef.current[productId];
    }
    toast.success(t('storefront:cart.restoredToast'));
  }, [t]);

  const removeFromCart = useCallback((productId) => {
    if (!productId) return;

    // Capture full snapshot BEFORE mutating so undo can restore exactly
    // the same slot/date/extras/attendees the customer had configured.
    const snapshot = {
      qty: quantities[productId],
      occurrence: selectedOccurrences[productId],
      tiers: selectedTiers[productId],
      rentalDate: rentalDates[productId],
      bookingSlot: bookingSlots[productId],
      attendees: attendeeDetails[productId],
      serviceOption: selectedServiceOptions[productId],
      serviceSlot: selectedServiceSlots[productId],
      extras: selectedExtraSelections[productId],
    };
    // If the product isn't actually in the cart, no-op (defensive — UI
    // shouldn't even show the button in that case).
    if (snapshot.qty == null && !snapshot.tiers && !snapshot.rentalDate && !snapshot.bookingSlot) return;
    undoSnapshotsRef.current[productId] = snapshot;

    // Wipe all 9 slices. React batches synchronous setState calls into
    // one render, so the persist effect fires once with the clean state.
    const dropKey = (setter) => setter(prev => {
      if (!prev || prev[productId] === undefined) return prev;
      const next = { ...prev };
      delete next[productId];
      return next;
    });
    dropKey(setQuantities);
    dropKey(setSelectedOccurrences);
    dropKey(setSelectedTiers);
    dropKey(setRentalDates);
    dropKey(setBookingSlots);
    dropKey(setAttendeeDetails);
    dropKey(setSelectedServiceOptions);
    dropKey(setSelectedServiceSlots);
    dropKey(setSelectedExtraSelections);

    // Reset any existing undo timer for this product (e.g. rapid re-remove).
    if (undoTimersRef.current[productId]) {
      clearTimeout(undoTimersRef.current[productId]);
    }
    undoTimersRef.current[productId] = setTimeout(() => {
      delete undoSnapshotsRef.current[productId];
      delete undoTimersRef.current[productId];
    }, 5000);

    const productName =
      (productsLookup || []).find(p => p.id === productId)?.name
      || t('storefront:summary.removeFallbackName');
    toast(t('storefront:cart.removedToast', { name: productName }), {
      action: {
        label: t('storefront:cart.undoAction'),
        onClick: () => undoRemoveFromCart(productId),
      },
      duration: 5000,
    });
  }, [
    t, productsLookup, undoRemoveFromCart,
    quantities, selectedOccurrences, selectedTiers, rentalDates, bookingSlots,
    attendeeDetails, selectedServiceOptions, selectedServiceSlots,
    selectedExtraSelections,
  ]);

  // ── 4. Cleanup undo timers on unmount ──────────────────────────────────
  //
  // Avoids leaking a 5s pending setTimeout if the user navigates away
  // mid-countdown (e.g. closes the tab).
  useEffect(() => {
    return () => {
      Object.values(undoTimersRef.current).forEach(clearTimeout);
      undoTimersRef.current = {};
      undoSnapshotsRef.current = {};
    };
  }, []);

  // ── 5. Explicit clear (called after successful order submission) ───────
  //
  // The post-order flow needs to drop the sessionStorage snapshot AND
  // the in-memory state. The persist effect would also wipe storage
  // when all slices are empty, but providing an explicit method makes
  // the post-checkout intent self-documenting.
  const clearCartSnapshot = useCallback(() => {
    if (slug) {
      try { clearCart(slug); } catch { /* noop */ }
    }
  }, [slug]);

  // ── Phase 0 Step 4b — sidecar dual-write to server cart ─────────────
  // Pushes the 10 state slices to /api/public/cart/* in background.
  // sessionStorage remains the source of truth in Step 4b (60-day soak).
  // Switching authority to server-side happens in Step 4c after observability
  // confirms zero drift between client and server cart state.
  //
  // The sidecar is a no-op when REACT_APP_PERSISTENT_CART_ENABLED=false
  // (default in production today). Zero impact on existing cart UX.
  usePersistentCartSync({
    slug,
    snapshot: {
      quantities,
      selectedOccurrences,
      selectedTiers,
      rentalDates,
      bookingSlots,
      attendeeDetails,
      orderFieldsData,
      selectedServiceOptions,
      selectedServiceSlots,
      selectedExtraSelections,
    },
  });

  return {
    // State slices (read-only access by callers)
    quantities,
    selectedOccurrences,
    selectedTiers,
    rentalDates,
    bookingSlots,
    attendeeDetails,
    orderFieldsData,
    selectedServiceOptions,
    selectedServiceSlots,
    selectedExtraSelections,
    // Setters (passed to ProductCard / ProductGrid / checkout)
    setQuantities,
    setSelectedOccurrences,
    setSelectedTiers,
    setRentalDates,
    setBookingSlots,
    setAttendeeDetails,
    setOrderFieldsData,
    setSelectedServiceOptions,
    setSelectedServiceSlots,
    setSelectedExtraSelections,
    // Helpers
    removeFromCart,
    undoRemoveFromCart,
    clearCartSnapshot,
  };
}
