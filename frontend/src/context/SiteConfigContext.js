/**
 * SiteConfigContext — config pubblica runtime (PL1).
 *
 * Legge GET /api/public/site-config una volta al boot ed espone il flag
 * `prelaunch`. Runtime, non build-time: al lancio si spegne la env sul
 * backend e il frontend lo riflette senza rebuild.
 *
 * Default prudente: finché non risponde, prelaunch=false (mostra il
 * marketplace normale, non lo splash) — mai flash di "in preparazione"
 * su un sito già aperto.
 */
import React, { createContext, useContext, useEffect, useState } from 'react';
import api from '../api/client';

const SiteConfigContext = createContext({ prelaunch: false, loading: true });

export function SiteConfigProvider({ children }) {
  const [config, setConfig] = useState({ prelaunch: false, loading: true });

  useEffect(() => {
    let mounted = true;
    api.get('/public/site-config')
      .then((res) => {
        if (mounted) setConfig({ prelaunch: Boolean(res.data?.prelaunch), loading: false });
      })
      .catch(() => { if (mounted) setConfig({ prelaunch: false, loading: false }); });
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
