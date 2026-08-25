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

// MT (26/8/2026) — LE NOSTRE VISITE NON SI CONTANO. Misurato: 86
// «visitatori» in 38 giorni, e dentro c'eravamo anche noi due, a ogni
// prova e a ogni deploy. L'impronta giornaliera salata rende
// impossibile riconoscerci a posteriori: va impedito ALLA FONTE.
// Due cinture:
//   1. chi ha un token di lavoro nel browser (operatore o admin) non
//      viene tracciato — copre noi nei browser di lavoro, e copre
//      anche l'operatore che guarda il proprio profilo e si contava
//      da solo come visitatore;
//   2. il patto del telefono: aprire UNA volta ?siamo-noi marca il
//      browser per sempre (chiave locale) e il ping tace — per i
//      nostri telefoni, dove non siamo sempre loggati.
const CHIAVE_NOI = 'aurya_siamo_noi';

export function isNoi() {
  try {
    if (new URLSearchParams(window.location.search).has('siamo-noi')) {
      localStorage.setItem(CHIAVE_NOI, '1');
    }
    return (
      localStorage.getItem(CHIAVE_NOI) === '1'
      || !!localStorage.getItem('token')
      || !!localStorage.getItem('platform_token')
    );
  } catch {
    return false;   // storage negato (incognito duro): meglio contare
  }
}

export default function useTrackView(surface, slug) {
  useEffect(() => {
    if (!surface || !slug) return undefined;
    if (isNoi()) return undefined;   // MT — mai contarci da soli
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
