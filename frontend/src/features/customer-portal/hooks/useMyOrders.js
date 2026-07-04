/**
 * useMyOrders — single source of truth for fetching the logged-in
 * customer's orders.
 *
 * Encapsulates the patterns the inline implementation in
 * CustomerPortalPages.js had to bake in:
 *   - Auto-retry once after 1.5s on the first failure → handles the
 *     "token in flight" race after an inline auto_login signup.
 *   - 401 silent (the global axios interceptor takes care of logout).
 *   - Inline error state with a `retry()` callback instead of a
 *     transient toast that disappears.
 *
 * Returns:
 *   { orders, loading, error, retry, reload }
 *
 * `retry()` and `reload()` are aliases — the former is exposed so
 * the consumer can wire it to a "Riprova" button without renaming.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { customerAuthAPI } from '../../../api/customerAuth';


const RETRY_DELAY_MS = 1500;


export default function useMyOrders() {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  // Internal: protect against double-mount in StrictMode + against
  // setState after unmount.
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);

  const load = useCallback(async ({ retryCount = 0 } = {}) => {
    if (!mountedRef.current) return;
    setLoading(true);
    setError(null);
    try {
      const res = await customerAuthAPI.getMyOrders();
      if (!mountedRef.current) return;
      setOrders(res.data?.orders || []);
    } catch (err) {
      if (!mountedRef.current) return;
      const status = err?.response?.status;
      if (status === 401) {
        // Global axios interceptor handles the redirect — locally we
        // just stop with empty orders and no error banner.
        setOrders([]);
        return;
      }
      if (retryCount < 1) {
        // Single auto-retry: most common failure is the token
        // propagation race right after auto_login.
        setTimeout(() => load({ retryCount: retryCount + 1 }), RETRY_DELAY_MS);
        return;
      }
      setError('Impossibile caricare i tuoi ordini. Verifica la connessione e riprova.');
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const retry = useCallback(() => load(), [load]);

  return {
    orders,
    loading,
    error,
    retry,
    reload: retry,
  };
}
