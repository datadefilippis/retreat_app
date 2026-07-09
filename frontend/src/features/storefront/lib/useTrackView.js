// VT2 — ping visita first-party (specchietto Visibilità operatore).
//
// Contratto col backend (POST /api/public/track, sempre 204):
// - parte SOLO dopo 3s sulla pagina: i bounce istantanei e i crawler
//   senza JS non contano; sendBeacon sopravvive alla chiusura tab
// - nessun cookie, nessun localStorage: il dedup visitatori è
//   server-side (visitor_hash giornaliero, IP mai salvato)
// - best-effort assoluto: qualsiasi errore qui muore in silenzio
import { useEffect } from 'react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';

const SEARCH_RE = /(^|\.)(google|bing|duckduckgo|yahoo|ecosia|qwant)\./;
const SOCIAL_RE = /(^|\.)(instagram|facebook|fb|tiktok|youtube|linkedin|pinterest|twitter|x|t)\.(com?|co|it|me)/;

// Attribuzione dei 5 canali (docs/VISIBILITA_OPERATORE_PIANO.md §2).
// Esportata pura per i test. `hostname` SENZA porta da entrambi i
// lati (URL.hostname vs location.host col :3000 non matcherebbe mai
// in dev e il referrer interno finirebbe in `direct`).
export function resolveChannel(surface, search, referrer, hostname) {
  if (surface === 'store') return 'store';
  if (surface === 'event' && /[?&]store=1(&|$)/.test(search || '')) {
    return 'store';
  }
  if (!referrer) return 'direct';
  let refHost = '';
  try {
    refHost = new URL(referrer).hostname.toLowerCase();
  } catch {
    return 'direct';
  }
  if (refHost === (hostname || '').toLowerCase()) return 'directory';
  if (SEARCH_RE.test(refHost)) return 'search';
  if (SOCIAL_RE.test(refHost)) return 'social';
  return 'direct';
}

function send(payload) {
  try {
    const url = `${BACKEND_URL}/api/public/track`;
    const body = JSON.stringify(payload);
    if (navigator.sendBeacon) {
      navigator.sendBeacon(url, new Blob([body], { type: 'application/json' }));
    } else {
      fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body,
        keepalive: true,
      }).catch(() => {});
    }
  } catch {
    /* mai rompere la pagina per un ping */
  }
}

export default function useTrackView(surface, slug) {
  useEffect(() => {
    if (!surface || !slug) return undefined;
    const timer = setTimeout(() => {
      const referrer = document.referrer || '';
      const channel = resolveChannel(
        surface, window.location.search, referrer, window.location.hostname);
      let referrerHost = null;
      try {
        const h = referrer ? new URL(referrer).hostname : '';
        // solo hostname ESTERNI: il path non parte mai (no PII)
        if (h && h !== window.location.hostname) referrerHost = h.slice(0, 100);
      } catch {
        referrerHost = null;
      }
      send({
        surface,
        slug,
        channel,
        referrer_host: referrerHost,
        lang: (document.documentElement.lang || 'it').slice(0, 2),
      });
    }, 3000);
    return () => clearTimeout(timer);
  }, [surface, slug]);
}
