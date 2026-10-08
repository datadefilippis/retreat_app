/**
 * preferite.js — MR2 (8/10/2026, piano refinement meditazioni): IL CUORE, UNO.
 *
 * Un solo posto che sa cosa hai salvato (meditazioni e playlist), con una
 * cache di sessione condivisa fra la casa, la pagina playlist e il player:
 * ogni pagina la legge una volta, il toggle e' ottimistico e si ritira se il
 * server dice di no. Senza account il cuore apre l'invito (chiediAccount).
 *
 * 8/10 sera (founder: «per i preferiti senza account aggiungiamo
 * l'accettazione»): il cuore toccato senza account resta IN ATTESA
 * (localStorage) e l'invito contiene la porta dell'account (PortaAurya, con
 * la casella legale). Appena la persona e' dentro — subito, o dopo il clic
 * nell'email se la sessione immediata e' spenta — il cuore in attesa si salva
 * da solo alla prima lettura delle preferite.
 */
import { useCallback, useEffect, useState } from 'react';
import platformApi, { PLATFORM_TOKEN_KEY } from '../../../api/platformClient';

const cache = { caricata: false, promessa: null, slugs: new Set(), playlists: new Set(), ascoltatori: new Set() };
const IN_ATTESA_KEY = 'fqz_cuore_in_attesa';

const avvisa = () => cache.ascoltatori.forEach((fn) => { try { fn(); } catch { /* niente */ } });

export const haAccount = () => { try { return !!localStorage.getItem(PLATFORM_TOKEN_KEY); } catch { return false; } };

const viaDi = (tipo, slug) => (tipo === 'playlist'
  ? `/frequencies/favorites/playlist/${encodeURIComponent(slug)}`
  : `/frequencies/favorites/${encodeURIComponent(slug)}`);

/** il cuore toccato senza account: si ricorda, si salva appena c'e' l'account */
export function ricordaInAttesa(tipo, slug) {
  try { localStorage.setItem(IN_ATTESA_KEY, JSON.stringify({ tipo, slug })); } catch { /* private mode */ }
}
export function inAttesa() {
  try { return JSON.parse(localStorage.getItem(IN_ATTESA_KEY) || 'null'); } catch { return null; }
}
export function scordaInAttesa() {
  try { localStorage.removeItem(IN_ATTESA_KEY); } catch { /* niente */ }
}

async function applicaInAttesa() {
  const a = inAttesa();
  if (!a || !a.slug) return;
  scordaInAttesa();
  const set = a.tipo === 'playlist' ? cache.playlists : cache.slugs;
  if (set.has(a.slug)) return;
  await toggla(set, a.slug, viaDi(a.tipo, a.slug));
}

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
      return applicaInAttesa();
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
    if (!conto) { ricordaInAttesa('slug', slug); setChiediAccount(true); return; }
    toggla(cache.slugs, slug, viaDi('slug', slug));
  }, [conto]);
  const togglePlaylist = useCallback((slug) => {
    if (!conto) { ricordaInAttesa('playlist', slug); setChiediAccount(true); return; }
    toggla(cache.playlists, slug, viaDi('playlist', slug));
  }, [conto]);
  /* la persona e' appena entrata dall'invito: si chiude, si legge, si salva il cuore in attesa */
  const dopoAccount = useCallback(async () => {
    setChiediAccount(false);
    await caricaPreferite(true);
    avvisa();
  }, []);
  return {
    hasAccount: conto, isFav, isFavPlaylist, toggle, togglePlaylist,
    slugs: cache.slugs, playlists: cache.playlists,
    chiediAccount, setChiediAccount, dopoAccount, ricarica: () => caricaPreferite(true),
  };
}
