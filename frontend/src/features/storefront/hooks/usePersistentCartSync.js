/**
 * usePersistentCartSync — sidecar hook for server-side cart dual-write.
 *
 * Phase 0 Step 4b della roadmap di evoluzione e-commerce (ADR-001).
 *
 * Ruolo
 * =====
 * Hook DI BACKGROUND che mantiene una copia server-side del cart in sync
 * con il sessionStorage cart gestito da useStorefrontCart. Funziona come
 * sidecar — non modifica il comportamento di useStorefrontCart, ne è
 * triggered come effetto collaterale.
 *
 * Contract di sicurezza
 * ====================
 * 1. SessionStorage rimane SOURCE OF TRUTH (Step 4b conservative).
 *    Lo switch a server-side autoritativo arriverà in Step 4c, una
 *    volta che 60 giorni di dual-write hanno validato il path server.
 *
 * 2. Tutte le failure server (network, 404, 500) sono SILENT — solo
 *    console.warn, mai toast.error o UI breakage. Cart UX continua a
 *    funzionare dal sessionStorage.
 *
 * 3. Feature flag client-side ``REACT_APP_PERSISTENT_CART_ENABLED``
 *    gate l'attivazione. Default false. Va attivato solo quando il
 *    backend è deployato + i sentinel sono verdi in prod.
 *
 * 4. cart_id storage:
 *    - HttpOnly cookie ``afianco_cart_id`` (set dal backend) — usato
 *      automatically dal browser per request successive (vedi cookie
 *      anti-CSRF behavior via SameSite=Lax)
 *    - localStorage ``afianco_cart_id_<slug>`` — necessario perché
 *      l'HttpOnly cookie NON è leggibile da JS, ma il frontend deve
 *      conoscere il cart_id per chiamare PATCH/DELETE
 *
 * Strategia di sync
 * =================
 * 1. Mount: check localStorage. Se cart_id presente → SKIP POST, vai a 3.
 *    Se assente → POST /cart (server set cookie + ritorna id, salviamo
 *    in localStorage).
 * 2. Ogni cambio di snapshot (10 slice) → debounce 500ms → PATCH /cart/{id}
 *    con items collapsed dal snapshot.
 * 3. Se PATCH ritorna 404 (cart expired/non trovato): re-crea con POST,
 *    update localStorage, retry PATCH.
 *
 * Effort: l'hook è ~150 righe, isolato, copre il dual-write completo
 * per lo storefront classic. Stream A/B futuri useranno lo stesso pattern.
 */

import { useEffect, useRef, useCallback } from 'react';
import cartAPI from '../../../api/cart';


// ── Feature flag ─────────────────────────────────────────────────────────


/**
 * Read the persistent-cart client-side feature flag.
 *
 * Default OFF — la attivazione richiede:
 *   1. Backend deployato + endpoint cart green in prod
 *   2. REACT_APP_PERSISTENT_CART_ENABLED=true al build frontend
 *   3. Soak su staging per minimo 7 giorni
 *
 * Quando la flag è OFF, l'hook è completamente inattivo: zero network
 * calls, zero impact sul comportamento esistente.
 */
export function isPersistentCartEnabled() {
  const val = process.env.REACT_APP_PERSISTENT_CART_ENABLED;
  if (val == null) return false;
  return ['true', '1', 'yes', 'on'].includes(String(val).trim().toLowerCase());
}


// ── Storage key per cart_id mirror ──────────────────────────────────────


// R1 rebrand — prefisso nuovo; il vecchio viene letto in fallback una
// volta (migrazione dolce, niente carrelli persi) e riscritto col nuovo.
const CART_ID_LOCALSTORAGE_PREFIX = 'aurya_cart_id:';
const LEGACY_CART_ID_PREFIX = 'afianco_cart_id:';

function _readCartId(slug) {
  if (!slug) return null;
  try {
    return sessionStorage.getItem(CART_ID_LOCALSTORAGE_PREFIX + slug)
      || sessionStorage.getItem(LEGACY_CART_ID_PREFIX + slug)   // migrazione R1
      || null;
  } catch {
    return null;
  }
}

function _writeCartId(slug, cartId) {
  if (!slug) return;
  try {
    if (cartId) {
      sessionStorage.setItem(CART_ID_LOCALSTORAGE_PREFIX + slug, cartId);
    } else {
      sessionStorage.removeItem(CART_ID_LOCALSTORAGE_PREFIX + slug);
    }
  } catch { /* sessionStorage quota / disabled */ }
}


// ── Snapshot → Cart items collapse ──────────────────────────────────────


/**
 * Convert le 10 slice di useStorefrontCart in una lista compatta di
 * CartItem (shape compatibile con OrderRequestItem).
 *
 * Iteriamo per ogni productId in `quantities` e per ognuno sintetizziamo
 * un item con i type-specific fields presi dalle altre slice.
 *
 * NOTA: ticket_tier_id richiederebbe espansione (1 line per tier) ma
 * questa è una conversione lossy in v1 — il source of truth resta
 * sessionStorage. Quando server diventa autoritativo (Step 4c)
 * convertiremo le slice in maniera fedele al modello multi-tier.
 */
export function collapseSnapshotToItems(snap) {
  if (!snap || typeof snap !== 'object') return [];
  const quantities = snap.quantities || {};
  const items = [];

  for (const [productId, qty] of Object.entries(quantities)) {
    if (!productId || !qty || qty <= 0) continue;

    const item = {
      product_id: productId,
      quantity: qty,
    };

    // Optional type-specific fields, only if non-null on the snapshot.
    const occ = (snap.selectedOccurrences || {})[productId];
    if (occ && occ.id) item.occurrence_id = occ.id;

    // For multi-tier: collapse first tier (lossy in v1)
    const tiers = (snap.selectedTiers || {})[productId];
    if (tiers && typeof tiers === 'object') {
      const tierIds = Object.keys(tiers);
      if (tierIds.length === 1) item.ticket_tier_id = tierIds[0];
    }

    const rental = (snap.rentalDates || {})[productId];
    if (rental) {
      if (rental.from) item.rental_date_from = rental.from;
      if (rental.to) item.rental_date_to = rental.to;
      if (rental.notes) item.rental_notes = rental.notes;
    }

    const booking = (snap.bookingSlots || {})[productId];
    if (booking) {
      if (booking.date) item.booking_date = booking.date;
      if (booking.start) item.booking_start_time = booking.start;
      if (booking.end) item.booking_end_time = booking.end;
      if (booking.end_date) item.booking_end_date = booking.end_date;
    }

    const attendees = (snap.attendeeDetails || {})[productId];
    if (Array.isArray(attendees) && attendees.length > 0) {
      item.attendees = attendees;
    }

    const serviceOpt = (snap.selectedServiceOptions || {})[productId];
    if (serviceOpt) item.service_option_id = serviceOpt;

    items.push(item);
  }
  return items;
}


// ── Main hook ────────────────────────────────────────────────────────────


/**
 * Sidecar hook che pushes il cart snapshot al server quando feature flag ON.
 *
 * Usage (in StorefrontPage o equivalente):
 * ```js
 *   const cart = useStorefrontCart({ slug, t, productsLookup });
 *   usePersistentCartSync({ slug, snapshot: cart });
 * ```
 *
 * NESSUN return value — pure side effect.
 */
export function usePersistentCartSync({ slug, snapshot, enabled }) {
  const effectiveEnabled = enabled !== undefined ? enabled : isPersistentCartEnabled();
  const debounceTimerRef = useRef(null);
  const inFlightRef = useRef(false);
  const cartIdRef = useRef(null);

  // ── 1. On mount: ensure we have a server-side cart_id ──
  // Crea cart vuoto al server solo SE feature flag ON. Cookie + localStorage
  // sincronizzati.
  useEffect(() => {
    if (!effectiveEnabled || !slug) return;
    let cancelled = false;

    const existing = _readCartId(slug);
    if (existing) {
      cartIdRef.current = existing;
      return;
    }

    (async () => {
      try {
        const res = await cartAPI.create({ slug, source: 'storefront_classic' });
        if (cancelled) return;
        const cartId = res?.data?.id;
        if (cartId) {
          cartIdRef.current = cartId;
          _writeCartId(slug, cartId);
        }
      } catch (err) {
        // Silent fail — sessionStorage is source of truth in Step 4b.
        // Don't log noisy stack — just a hint per debugging.
        // eslint-disable-next-line no-console
        console.warn('[cart-sync] failed to init server cart:', err?.message || err);
      }
    })();

    return () => { cancelled = true; };
  }, [effectiveEnabled, slug]);

  // ── 2. Debounced PATCH on snapshot change ──
  // Snapshot is the full bundle returned by useStorefrontCart. We only
  // sync the 10 cart-relevant slices; setters and helpers are not included.
  useEffect(() => {
    if (!effectiveEnabled || !slug || !snapshot) return;

    // Extract just the 10 cart slices (avoid syncing setters identity changes)
    const items = collapseSnapshotToItems({
      quantities: snapshot.quantities,
      selectedOccurrences: snapshot.selectedOccurrences,
      selectedTiers: snapshot.selectedTiers,
      rentalDates: snapshot.rentalDates,
      bookingSlots: snapshot.bookingSlots,
      attendeeDetails: snapshot.attendeeDetails,
      selectedServiceOptions: snapshot.selectedServiceOptions,
    });

    // Debounce 500ms — utente che clicca rapidamente +/- non spamma server
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }
    debounceTimerRef.current = setTimeout(async () => {
      if (inFlightRef.current) return;  // skip overlapping calls
      let cartId = cartIdRef.current || _readCartId(slug);
      if (!cartId) return;  // POST not yet completed (mount race)

      inFlightRef.current = true;
      try {
        await cartAPI.update({
          cartId,
          slug,
          body: { items },
        });
      } catch (err) {
        // 404 = cart expired or not found. Try to re-create + retry once.
        const status = err?.response?.status;
        if (status === 404) {
          try {
            const recreate = await cartAPI.create({ slug, source: 'storefront_classic' });
            cartId = recreate?.data?.id;
            if (cartId) {
              cartIdRef.current = cartId;
              _writeCartId(slug, cartId);
              await cartAPI.update({ cartId, slug, body: { items } });
            }
          } catch (retryErr) {
            // eslint-disable-next-line no-console
            console.warn('[cart-sync] recreate-after-404 failed:', retryErr?.message);
          }
        } else {
          // eslint-disable-next-line no-console
          console.warn('[cart-sync] update failed:', status || err?.message);
        }
      } finally {
        inFlightRef.current = false;
      }
    }, 500);

    return () => {
      if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current);
    };
  }, [
    effectiveEnabled, slug,
    // 10 slice — sufficienti per detect ogni change rilevante
    snapshot?.quantities,
    snapshot?.selectedOccurrences,
    snapshot?.selectedTiers,
    snapshot?.rentalDates,
    snapshot?.bookingSlots,
    snapshot?.attendeeDetails,
    snapshot?.orderFieldsData,
    snapshot?.selectedServiceOptions,
    snapshot?.selectedServiceSlots,
    snapshot?.selectedExtraSelections,
  ]);

  // ── 3. Cleanup ──
  useEffect(() => {
    return () => {
      if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current);
    };
  }, []);

  // Expose a manual clear for explicit cleanup post-order.
  const clearServerCart = useCallback(async () => {
    if (!effectiveEnabled || !slug) return;
    const cartId = cartIdRef.current || _readCartId(slug);
    if (!cartId) return;
    try {
      await cartAPI.remove({ cartId, slug, hard: true });
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn('[cart-sync] clear failed:', err?.message);
    } finally {
      _writeCartId(slug, null);
      cartIdRef.current = null;
    }
  }, [effectiveEnabled, slug]);

  return { clearServerCart };
}

export default usePersistentCartSync;
