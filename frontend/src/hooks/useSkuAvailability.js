/**
 * useSkuAvailability — debounced live-check of product SKU uniqueness.
 *
 * 2026-05-20 — Background: the wizards validated SKU uniqueness only at
 * submit. The user filled 5 steps, clicked "Crea prodotto", waited for
 * the response, discovered the SKU was already taken, scrolled back to
 * step 1 to change it. Modern UX is a 400ms debounced GET /products/
 * check-sku?sku=X with an icon next to the field:
 *
 *   · ⏳ checking
 *   · ✅ available
 *   · ❌ taken
 *
 * The backend endpoint is org-scoped and soft-fails on database errors
 * (returns ``available: true, degraded: true``) so this hook NEVER
 * blocks the form on network glitches — it only enhances UX.
 *
 * Usage:
 *
 *   const { state, conflictingId, degraded } = useSkuAvailability(sku, {
 *     excludeProductId: editingProduct?.id,  // optional, edit-mode only
 *     minLength: 2,
 *   });
 *
 *   // state ∈ "idle" | "checking" | "available" | "taken" | "error"
 *
 * Returned state machine:
 *
 *   sku === "" / shorter than minLength    → "idle"
 *   request in flight                       → "checking"
 *   response received, available=true       → "available"
 *   response received, available=false      → "taken"
 *   network error (degraded=true on resp)   → "available" (soft-fail UX:
 *                                              don't block the user)
 *   axios threw                              → "error" (rare; we log)
 *
 * The hook auto-cancels the previous request when ``sku`` changes — no
 * race condition where an older response overwrites a newer one.
 */

import { useEffect, useRef, useState } from 'react';

import { productsAPI } from '../api/products';


const DEFAULT_DEBOUNCE_MS = 400;
const DEFAULT_MIN_LENGTH = 2;


export function useSkuAvailability(sku, opts = {}) {
  const {
    excludeProductId = null,
    minLength = DEFAULT_MIN_LENGTH,
    debounceMs = DEFAULT_DEBOUNCE_MS,
    enabled = true,
  } = opts;

  const [state, setState] = useState('idle');
  const [conflictingId, setConflictingId] = useState(null);
  const [degraded, setDegraded] = useState(false);

  // Refs to coordinate debounce + cancellation across re-renders.
  const debounceRef = useRef(null);
  const controllerRef = useRef(null);

  useEffect(() => {
    if (!enabled) {
      setState('idle');
      return undefined;
    }
    const trimmed = (sku || '').trim();
    if (trimmed.length < minLength) {
      setState('idle');
      setConflictingId(null);
      setDegraded(false);
      return undefined;
    }

    // Cancel any in-flight request — the SKU just changed.
    if (controllerRef.current) {
      try { controllerRef.current.abort(); } catch { /* ignore */ }
      controllerRef.current = null;
    }
    if (debounceRef.current) clearTimeout(debounceRef.current);

    setState('checking');
    setConflictingId(null);
    setDegraded(false);

    debounceRef.current = setTimeout(async () => {
      const controller = new AbortController();
      controllerRef.current = controller;
      try {
        const res = await productsAPI.checkSkuAvailability(trimmed, {
          excludeProductId,
          signal: controller.signal,
        });
        if (controller.signal.aborted) return;
        const data = res?.data || {};
        setDegraded(!!data.degraded);
        if (data.available) {
          setState('available');
          setConflictingId(null);
        } else {
          setState('taken');
          setConflictingId(data.conflicting_product_id || null);
        }
      } catch (err) {
        if (controller.signal.aborted) return;
        const code = err?.code || err?.name;
        if (code === 'ERR_CANCELED' || code === 'CanceledError' || code === 'AbortError') {
          return;
        }
        // Soft-fail UX: treat any error as "available" so the user is
        // never blocked by a flaky endpoint. The hard uniqueness check
        // at create-time on the backend remains authoritative.
        setState('available');
        setDegraded(true);
        // eslint-disable-next-line no-console
        if (typeof console !== 'undefined' && console.warn) {
          console.warn('useSkuAvailability: probe failed:', err?.message || err);
        }
      } finally {
        if (controllerRef.current === controller) {
          controllerRef.current = null;
        }
      }
    }, debounceMs);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      if (controllerRef.current) {
        try { controllerRef.current.abort(); } catch { /* ignore */ }
        controllerRef.current = null;
      }
    };
  }, [sku, excludeProductId, minLength, debounceMs, enabled]);

  return { state, conflictingId, degraded };
}


export default useSkuAvailability;
