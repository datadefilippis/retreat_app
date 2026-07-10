/**
 * SiteConfigContext — config pubblica runtime (PL1, cache PL17).
 *
 * Legge GET /api/public/site-config al boot ed espone il flag
 * `prelaunch`. Runtime, non build-time: al lancio si spegne la env sul
 * backend e il frontend lo riflette senza rebuild.
 *
 * PL17 — stale-while-revalidate: il flag viene ricordato in
 * localStorage e usato SUBITO al boot (loading=false), poi la rete
 * conferma o corregge in background. Risultato: niente schermo bianco
 * in attesa del round-trip — la home dipinge al primo frame. Il primo
 * visitatore in assoluto (nessuna cache) aspetta la rete come prima:
 * default prudente prelaunch=false, mai flash di "in preparazione" su
 * un sito già aperto.
 */
import React, { createContext, useContext, useEffect, useState } from 'react';
import api from '../api/client';

const CACHE_KEY = 'aurya_site_config';

function readCache() {
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (typeof parsed?.prelaunch !== 'boolean') return null;
    return parsed;
  } catch { return null; }
}

const SiteConfigContext = createContext({ prelaunch: false, loading: true });

export function SiteConfigProvider({ children }) {
  const [config, setConfig] = useState(() => {
    const cached = readCache();
    return cached
      ? { prelaunch: cached.prelaunch, loading: false }   // primo frame utile
      : { prelaunch: false, loading: true };
  });

  useEffect(() => {
    let mounted = true;
    api.get('/public/site-config')
      .then((res) => {
        const prelaunch = Boolean(res.data?.prelaunch);
        try { localStorage.setItem(CACHE_KEY, JSON.stringify({ prelaunch })); } catch { /* storage pieno/negato */ }
        if (mounted) setConfig({ prelaunch, loading: false });
      })
      .catch(() => { if (mounted) setConfig((c) => ({ ...c, loading: false })); });
    return () => { mounted = false; };
  }, []);

  return (
    <SiteConfigContext.Provider value={config}>
      {children}
    </SiteConfigContext.Provider>
  );
}

export function useSiteConfig() {
  return useContext(SiteConfigContext);
}
