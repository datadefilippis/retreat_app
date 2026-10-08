/**
 * preferite.js — MR2 (8/10/2026, piano refinement meditazioni): IL CUORE, UNO.
 *
 * Un solo posto che sa cosa hai salvato (meditazioni e playlist), con una
 * cache di sessione condivisa fra la casa, la pagina playlist e il player:
 * ogni pagina la legge una volta, il toggle e' ottimistico e si ritira se il
 * server dice di no. Senza account il cuore apre l'invito (chiediAccount).
 */
import { useCallback, useEffect, useState } from 'react';
import platformApi, { PLATFORM_TOKEN_KEY } from '../../../api/platformClient';

const cache = { caricata: false, promessa: null, slugs: new Set(), playlists: new Set(), ascoltatori: new Set() };

const avvisa = () => cache.ascoltatori.forEach((fn) => { try { fn(); } catch { /* niente */ } });

export const haAccount = () => { try { return !!localStorage.getItem(PLATFORM_TOKEN_KEY); } catch { return false; } };

export async function caricaPreferite(forza = false) {
  if (!haAccount()) return;
  if (cache.caricata && !forza) return;
  if (cache.promessa && !forza) return cache.promessa;
  cache.promessa = platformApi.get('/frequencies/favorites')
    .then((r) => {
      cache.slugs = new Set(r.data.slugs || []);
      cache.playlists = new Set(r.data.playlists || []);
      cache.caricata = true;
      avvisa();
    })
    .catch(() => { /* non bloccante: il cuore resta vuoto */ })
    .finally(() => { cache.promessa = null; });
  return cache.promessa;
}

async function toggla(set, slug, via) {
  const era = set.has(slug);
  if (era) set.delete(slug); else set.add(slug);
  avvisa();
  try {
    if (era) await platformApi.delete(via); else await platformApi.put(via);
  } catch {
    if (era) set.add(slug); else set.delete(slug);   // si ritira
    avvisa();
  }
}

/** lo stato delle preferite + i gesti; `chiediAccount` si alza quando serve l'account */
export function usePreferite() {
  const [, forza] = useState(0);
  const [chiediAccount, setChiediAccount] = useState(false);
  useEffect(() => {
    const fn = () => forza((n) => n + 1);
    cache.ascoltatori.add(fn);
    caricaPreferite();
    return () => { cache.ascoltatori.delete(fn); };
  }, []);
  const conto = haAccount();
  const isFav = useCallback((slug) => cache.slugs.has(slug), []);
  const isFavPlaylist = useCallback((slug) => cache.playlists.has(slug), []);
  const toggle = useCallback((slug) => {
    if (!conto) { setChiediAccount(true); return; }
    toggla(cache.slugs, slug, `/frequencies/favorites/${encodeURIComponent(slug)}`);
  }, [conto]);
  const togglePlaylist = useCallback((slug) => {
    if (!conto) { setChiediAccount(true); return; }
    toggla(cache.playlists, slug, `/frequencies/favorites/playlist/${encodeURIComponent(slug)}`);
  }, [conto]);
  return {
    hasAccount: conto, isFav, isFavPlaylist, toggle, togglePlaylist,
    slugs: cache.slugs, playlists: cache.playlists,
    chiediAccount, setChiediAccount, ricarica: () => caricaPreferite(true),
  };
}
