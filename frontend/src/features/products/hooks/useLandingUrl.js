/**
 * useLandingUrl — single React hook for the admin-side landing URL actions.
 *
 * Wraps GET /products/:id/landing-info and exposes an ergonomic shape to
 * Reservation / Service / Physical / Digital dashboards so they stop
 * computing the URL client-side (which historically picked a random
 * published store and produced 404 links on multi-store setups).
 *
 * Contract:
 *   const { landingPath, landingUrl, storeName, blockers, loading, refresh }
 *     = useLandingUrl(productId);
 *
 *   - landingPath:   "/r/<store_slug>/<product_slug>" | null  (internal routing)
 *   - landingUrl:    absolute URL | null                       (copy-link target)
 *   - storeName:     human name of the resolved store | null
 *   - blockers:      list of human-readable reasons the landing isn't reachable
 *   - loading:       true while the initial fetch is in flight
 *   - refresh():     re-fetch (call after publishing / updating stores)
 *
 * `productId` may be null during the initial render of the dashboard — the
 * hook degrades to { landingPath: null, blockers: [], loading: false } in
 * that case, matching what the UI did before.
 */

import { useCallback, useEffect, useState } from 'react';
import { productsAPI } from '../../../api';


// Empty default shared across renders — avoids creating a new object
// each call which would invalidate consumers' effects unnecessarily.
const EMPTY = Object.freeze({
  has_landing: false,
  landing_url_path: null,
  landing_url_absolute: null,
  store_slug: null,
  store_name: null,
  product_slug: null,
  item_type: null,
  blockers: [],
});


export default function useLandingUrl(productId) {
  const [info, setInfo] = useState(EMPTY);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    if (!productId) {
      setInfo(EMPTY);
      return;
    }
    setLoading(true);
    try {
      const res = await productsAPI.getLandingInfo(productId);
      setInfo(res.data || EMPTY);
    } catch {
      // Gracefully degrade so the button shows "Landing non disponibile"
      // rather than crashing the dashboard.
      setInfo(EMPTY);
    } finally {
      setLoading(false);
    }
  }, [productId]);

  useEffect(() => { load(); }, [load]);

  // Prefer the absolute URL for clipboard-copy targets — it survives when
  // the customer pastes it outside the webapp. Falls back to the origin
  // + path when the backend didn't have PUBLIC_APP_URL configured, so the
  // admin always gets something usable.
  const absoluteFallback = info.landing_url_path
    ? `${window.location.origin}${info.landing_url_path}`
    : null;

  return {
    landingPath: info.landing_url_path || null,
    landingUrl: info.landing_url_absolute || absoluteFallback,
    storeSlug: info.store_slug || null,
    storeName: info.store_name || null,
    productSlug: info.product_slug || null,
    itemType: info.item_type || null,
    blockers: info.blockers || [],
    hasLanding: !!info.has_landing,
    loading,
    refresh: load,
  };
}
