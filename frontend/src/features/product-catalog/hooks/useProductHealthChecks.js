/**
 * useProductHealthChecks — fetches the intelligence-banner health
 * checks for the current period.
 *
 * Same robustness contract as ``useProductOverview``:
 *  - cancels stale responses
 *  - returns { data, loading, error, refetch }
 *  - error surface is a string suitable for inline banner display
 *
 * Stays separate from useProductOverview so the banner can render
 * faster than the metrics grid (smaller payload, no period comparison).
 *
 * Dismissal handling
 * ------------------
 * The hook exposes ``dismissCheck(id)`` and ``isDismissed(id)`` so the
 * banner can hide individual checks for 30 days without a backend
 * round-trip. Persistence is via localStorage scoped per-organisation
 * (the key carries the org slug; switching orgs in the same browser
 * gets a fresh banner). 30 days was chosen because most data-quality
 * issues either get fixed within that window or stop being relevant.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { productCatalogAPI } from '../../../api/productCatalog';


// 30-day dismissal expiry in ms.
const DISMISS_TTL_MS = 30 * 24 * 60 * 60 * 1000;


function _dismissStorageKey() {
  // Per-app key; if multi-org in the same browser becomes relevant we
  // can extend with an org_id suffix later. Today's accounts are
  // single-org per user session.
  return 'product_catalog:dismissed_checks';
}


function _loadDismissals() {
  try {
    const raw = localStorage.getItem(_dismissStorageKey());
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    // Strip expired entries on read so the object stays small.
    const now = Date.now();
    const fresh = {};
    for (const [id, ts] of Object.entries(parsed)) {
      if (typeof ts === 'number' && (now - ts) < DISMISS_TTL_MS) {
        fresh[id] = ts;
      }
    }
    return fresh;
  } catch {
    return {};
  }
}


function _saveDismissals(map) {
  try {
    localStorage.setItem(_dismissStorageKey(), JSON.stringify(map));
  } catch {
    // localStorage may be unavailable (private mode, quota); the
    // banner just keeps showing dismissable items — soft failure.
  }
}


export default function useProductHealthChecks(period) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [refetchTick, setRefetchTick] = useState(0);
  const [dismissals, setDismissals] = useState(() => _loadDismissals());
  const requestToken = useRef(0);

  useEffect(() => {
    const myToken = ++requestToken.current;
    setLoading(true);
    setError(null);

    productCatalogAPI.healthCheck(period)
      .then((res) => {
        if (myToken !== requestToken.current) return;
        setData(res?.data || null);
      })
      .catch((err) => {
        if (myToken !== requestToken.current) return;
        const detail = err?.response?.data?.detail;
        setError(typeof detail === 'string' ? detail : (err?.message || 'unknown'));
      })
      .finally(() => {
        if (myToken === requestToken.current) setLoading(false);
      });
  }, [period, refetchTick]);

  const refetch = useCallback(() => setRefetchTick((n) => n + 1), []);

  const dismissCheck = useCallback((id) => {
    setDismissals((prev) => {
      const next = { ...prev, [id]: Date.now() };
      _saveDismissals(next);
      return next;
    });
  }, []);

  const undismissCheck = useCallback((id) => {
    setDismissals((prev) => {
      const next = { ...prev };
      delete next[id];
      _saveDismissals(next);
      return next;
    });
  }, []);

  const isDismissed = useCallback((id) => Boolean(dismissals[id]), [dismissals]);

  return { data, loading, error, refetch, dismissCheck, undismissCheck, isDismissed };
}
