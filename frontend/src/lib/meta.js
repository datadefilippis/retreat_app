/**
 * MP2 (5/10/2026) — Meta Pixel, solo col consenso «marketing».
 *
 * Regole della casa:
 *  - L'ID arriva da /public/site-config (env META_PIXEL_ID sul backend):
 *    runtime, non build-time. Vuoto = questo modulo non fa nulla.
 *  - Lo script fbevents.js NON e' nel bundle e NON si carica finche' la
 *    persona non accetta il marketing nel banner (lib/consenso.js): prima
 *    non parte nessuna richiesta verso Meta. Alla revoca: consent revoke,
 *    niente piu' eventi, cookie _fbp/_fbc cancellati.
 *  - Ogni evento che conta porta un eventID: lo stesso che il form manda
 *    al server (campo `tracciamento`), cosi' la Conversions API dice a Meta
 *    la stessa cosa UNA volta sola (deduplicazione).
 *  - Le funzioni evento sono no-op senza pixel o senza consenso: chi le
 *    chiama non deve sapere niente dello stato.
 */
import { consensoMarketing, onCambio } from './consenso';

let pixelId = null;
let caricato = false;     // fbevents.js iniettato
let attivo = false;       // consenso marketing vero adesso
let ascoltoRegistrato = false;

function fbq(...args) {
  if (typeof window === 'undefined' || typeof window.fbq !== 'function') return;
  window.fbq(...args);
}

function inietta() {
  if (caricato || typeof document === 'undefined' || !pixelId) return;
  /* lo stub ufficiale di Meta, senza il PageView automatico: lo mandiamo
     noi sui cambi rotta, come per GA */
  const w = window;
  if (!w.fbq) {
    const n = function () { n.callMethod ? n.callMethod.apply(n, arguments) : n.queue.push(arguments); };
    w.fbq = n; w._fbq = n; n.push = n; n.loaded = true; n.version = '2.0'; n.queue = [];
    const s = document.createElement('script');
    s.async = true;
    s.src = 'https://connect.facebook.net/en_US/fbevents.js';
    const primo = document.getElementsByTagName('script')[0];
    if (primo && primo.parentNode) primo.parentNode.insertBefore(s, primo);
    else document.head.appendChild(s);
  }
  fbq('consent', 'grant');
  fbq('init', pixelId);
  caricato = true;
}

function cancellaCookieMeta() {
  if (typeof document === 'undefined') return;
  const host = window.location.hostname.replace(/^www\./, '');
  for (const nome of ['_fbp', '_fbc']) {
    for (const dom of ['', `; domain=${host}`, `; domain=.${host}`]) {
      document.cookie = `${nome}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/${dom}`;
    }
  }
}

function applicaConsenso(marketing) {
  if (marketing) {
    attivo = true;
    inietta();
    fbq('consent', 'grant');
    // la pagina corrente conta da subito (prima era invisibile)
    if (typeof window !== 'undefined') fbq('track', 'PageView');
  } else {
    attivo = false;
    fbq('consent', 'revoke');
    cancellaCookieMeta();
  }
}

/** Dal SiteConfigContext, con l'ID runtime. Idempotente. */
export function initMeta(id) {
  if (!id || typeof window === 'undefined') return;
  pixelId = String(id);
  if (!ascoltoRegistrato) {
    onCambio((scelta) => applicaConsenso(scelta.marketing === true));
    ascoltoRegistrato = true;
  }
  if (consensoMarketing()) applicaConsenso(true);
}

export const metaAttivo = () => Boolean(pixelId && attivo && caricato);

/** PageView sui cambi rotta della SPA (App.js, accanto a trackPageView). */
export function metaPageView() {
  if (!metaAttivo()) return;
  fbq('track', 'PageView');
}

function leggiCookie(nome) {
  if (typeof document === 'undefined') return null;
  const m = document.cookie.match(new RegExp('(?:^|; )' + nome + '=([^;]*)'));
  return m ? decodeURIComponent(m[1]) : null;
}

/** Un identificativo evento condiviso fra pixel e Conversions API. */
export function idEvento(prefisso = 'ev') {
  let casuale = '';
  try {
    const b = new Uint8Array(12);
    window.crypto.getRandomValues(b);
    casuale = Array.from(b, (x) => x.toString(16).padStart(2, '0')).join('');
  } catch {
    casuale = Math.random().toString(16).slice(2, 14) + Date.now().toString(16);
  }
  return `${prefisso}_${casuale}`.slice(0, 64);
}

/**
 * Il blocco `tracciamento` che i form mandano al server. Con consenso
 * marketing: event_id + cookie _fbp/_fbc (se gia' presenti). Senza: solo
 * {marketing: false}, nessun identificativo lascia il browser.
 */
export function datiTracciamento(prefisso = 'ev') {
  if (!consensoMarketing()) return { marketing: false };
  const out = { marketing: true, event_id: idEvento(prefisso) };
  const fbp = leggiCookie('_fbp');
  const fbc = leggiCookie('_fbc');
  if (fbp) out.fbp = fbp;
  if (fbc) out.fbc = fbc;
  return out;
}

function traccia(nome, dati = {}, eventID = null) {
  if (!metaAttivo()) return false;
  const pulito = Object.fromEntries(Object.entries(dati).filter(([, v]) => v !== undefined && v !== null && v !== ''));
  if (eventID) fbq('track', nome, pulito, { eventID });
  else fbq('track', nome, pulito);
  return true;
}

/** Iscrizione al Cerchio riuscita (tutte le porte). */
export const metaLead = ({ eventID, porta, superficie } = {}) =>
  traccia('Lead', { content_name: superficie || porta || 'cerchio', content_category: 'cerchio' }, eventID);

/** Registrazione riuscita: tipo = 'operatore' | 'account'. */
export const metaCompleteRegistration = ({ eventID, tipo } = {}) =>
  traccia('CompleteRegistration', { content_name: tipo || 'account', status: true }, eventID);

/** Contatti di un operatore sbloccati. */
export const metaContact = ({ eventID, slug } = {}) =>
  traccia('Contact', { content_name: slug || 'operatore' }, eventID);

/** Ordine pagato: value e currency come li vuole Meta. */
export const metaPurchase = ({ eventID, value, currency = 'EUR', tipo } = {}) =>
  traccia('Purchase', { value: Number(value) || 0, currency, content_type: tipo || 'product' }, eventID);
