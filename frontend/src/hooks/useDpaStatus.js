/**
 * useDpaStatus — PV7 (docs/PROFILO_VERIFICATO_PIANO_2026-07.md).
 *
 * Stato condiviso dell'acknowledgement del DPA art. 28 (il "patto di
 * responsabilita'" che l'operatore firma prima di vendere).
 *
 * GET /api/legal/dpa/status si chiama UNA volta per sessione SPA:
 * cache leggera a livello di modulo + set di listener, cosi' banner
 * (Listino, Ritiri) e gate di creazione condividono lo stesso stato
 * senza richiamare l'endpoint a ogni render/navigazione.
 *
 * La cache e' un'ottimizzazione, MAI la fonte di verita': il gate vero
 * vive sul server (409 DPA_REQUIRED alla creazione). Se la cache fosse
 * stantia (cambio org nella stessa sessione, status 403 per ruoli non
 * admin), la creazione risponde comunque 409 e la UI apre il dialog
 * dal catch — nessun buco.
 */
import { useEffect, useState } from 'react';
import { dpaAPI } from '../api/auth';

let cache = null;       // ultimo payload di /dpa/status ({acknowledged, ...})
let inflight = null;    // promise della fetch in corso (dedupe)
const listeners = new Set();

function notify() {
  listeners.forEach((l) => {
    try { l(cache); } catch { /* listener smontato a meta' — ignora */ }
  });
}

/** Carica lo status (deduplicato). force=true per rileggere dal server. */
export function primeDpaStatus(force = false) {
  if (cache && !force) return Promise.resolve(cache);
  if (inflight && !force) return inflight;
  inflight = dpaAPI.status()
    .then((s) => { cache = s; notify(); return s; })
    .catch(() => {
      // 403 (ruolo non admin) o rete giu': niente banner, il gate
      // server resta l'ultima difesa. Non cache-iamo il fallimento.
      inflight = null;
      return cache;
    });
  return inflight;
}

/** Dopo un acknowledge riuscito: aggiorna la cache e tutti i listener. */
export function markDpaAcknowledged(partial) {
  cache = { ...(cache || {}), acknowledged: true, ...(partial || {}) };
  notify();
}

/** Reset (es. logout/cambio org). La prossima lettura rifetcha. */
export function resetDpaStatusCache() {
  cache = null;
  inflight = null;
}

export default function useDpaStatus() {
  const [status, setStatus] = useState(cache);

  useEffect(() => {
    const listener = (s) => setStatus(s ? { ...s } : s);
    listeners.add(listener);
    primeDpaStatus().then((s) => {
      // primo mount: la promise puo' risolvere dopo la subscribe
      if (s && listeners.has(listener)) listener(s);
    });
    return () => listeners.delete(listener);
  }, []);

  return {
    status,                               // payload grezzo o null
    known: status != null,                // status caricato con successo
    acknowledged: !!status?.acknowledged, // il patto e' gia' firmato?
    acknowledgedAt: status?.acknowledged_at || null,
  };
}
