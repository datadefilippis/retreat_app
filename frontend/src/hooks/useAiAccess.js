/**
 * useAiAccess — React Context + hook for AI access status.
 *
 * Single fetch of GET /ai/access-status shared across all components.
 * Exposes: plan, aiEnabled, limits, usage, loading, refresh(), canUse(), quotaExhausted().
 */
import React, { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react';
import { useAuth } from '../context/AuthContext';

const AiAccessContext = createContext(null);

export function AiAccessProvider({ children }) {
  const { isAuthenticated } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  // SA-R (10/9/2026 sera, founder: «via la sezione AI»): il backend non
  // monta piu' nessun router /ai, e GET /ai/access-status rispondeva 404
  // a OGNI caricamento dell'app. Niente chiamata: l'AI e' spenta, i
  // consumatori (canUse, entitlements) leggono «no» come prima.
  const refresh = useCallback(async () => {
    setData(null);
    setLoading(false);
  }, [isAuthenticated]);   // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    refresh();
  }, [refresh]);

  const canUse = useCallback((feature) => {
    if (!data?.ai_enabled) return false;
    const limit = data?.limits?.[feature];
    if (limit === -1) return true; // unlimited (enterprise)
    return (data?.usage?.[feature] ?? 0) < limit;
  }, [data]);

  const quotaExhausted = useCallback((feature) => {
    if (!data?.ai_enabled) return false; // not even enabled — different state
    const limit = data?.limits?.[feature];
    if (limit === -1) return false; // unlimited
    return (data?.usage?.[feature] ?? 0) >= limit;
  }, [data]);

  const value = useMemo(() => ({
    plan: data?.plan ?? 'free',
    aiEnabled: data?.ai_enabled ?? false,
    limits: data?.limits ?? { chat: 0, digest: 0, alert_analysis: 0, health_explanation: 0 },
    usage: data?.usage ?? { chat: 0, digest: 0, alert_analysis: 0, health_explanation: 0 },
    loading,
    refresh,
    canUse,
    quotaExhausted,
  }), [data, loading, refresh, canUse, quotaExhausted]);

  return (
    <AiAccessContext.Provider value={value}>
      {children}
    </AiAccessContext.Provider>
  );
}

export function useAiAccess() {
  const ctx = useContext(AiAccessContext);
  if (!ctx) {
    throw new Error('useAiAccess must be used inside <AiAccessProvider>');
  }
  return ctx;
}
