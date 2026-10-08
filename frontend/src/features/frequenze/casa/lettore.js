/**
 * lettore.js — MR3 (8/10/2026, piano refinement meditazioni): L'ASCOLTO PARTE DOVE SEI.
 *
 * Un lettore solo per la casa e per la pagina della playlist, in una barra
 * fissa in basso: si ascolta lì, senza cambiare pagina (decisione 3 del
 * founder). Usa SOLO i due file che la pagina pubblica già usa — l'anteprima
 * di 90 s per chi non è nel Cerchio e il master mp3 per chi lo è — con lo
 * stesso lettore da file (engine/continuo.lettoreDaUrl: Media Session, tempo,
 * fine). Niente sintesi dal vivo qui: una meditazione senza master si apre
 * nella pagina intera, che resta com'è (link condiviso, SEO, continuo).
 *
 * Stesse regole della pagina: il sipario di sicurezza prima del primo suono
 * (useSafetyGate), il cancello a 90 s (CancelloLettera nel foglio), gli
 * eventi di ascolto (SN0), «riprendi» e i recenti con l'account (SN3), la
 * playlist che continua da sola (SN1).
 */
import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { frequenciesAPI } from '../../../api/frequencies';
import platformApi from '../../../api/platformClient';
import { prova } from '../../../lib/cerchio';
import { lettoreDaUrl } from '../engine/continuo';
import { schermoAcceso, schermoLibero } from '../engine/veglia';
import { useSafetyGate } from '../SafetyCurtain';

export const PREVIEW_SEC = 90;
const Ctx = createContext(null);

export const sbloccato = () => {
  try { return !!prova() || !!localStorage.getItem('platform_token') || !!localStorage.getItem('token'); } catch { return false; }
};
const haAccount = () => { try { return !!localStorage.getItem('platform_token'); } catch { return false; } };

export function LettoreProvider({ children }) {
  const [traccia, setTraccia] = useState(null);       // il payload pubblico (getPublic)
  const [playlist, setPlaylist] = useState(null);     // {slug, title, tracce[]} oppure null
  const [da, setDa] = useState('casa');
  const [playing, setPlaying] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [caricamento, setCaricamento] = useState(false);
  const [cancello, setCancello] = useState(false);    // il foglio del Cerchio, dopo i 90 s
  const [unlocked, setUnlocked] = useState(sbloccato);
  const [scheda, setScheda] = useState(null);         // la meditazione aperta nel foglio di dettaglio
  const { guard, curtain, openReview } = useSafetyGate();
  const hRef = useRef(null);
  const ascoltoRef = useRef({ avviato: false, quartili: {} });
  const ultimoSalvatoRef = useRef(0);
  const tracciaRef = useRef(null);
  tracciaRef.current = traccia;

  const butta = useCallback(() => {
    if (hRef.current) { try { hRef.current.pause(); hRef.current.dispose?.(); } catch { /* niente */ } hRef.current = null; }
    schermoLibero();
    setPlaying(false);
  }, []);
  useEffect(() => () => butta(), [butta]);

  const evento = useCallback((slug, nome, secondo, playlistSlug, prov) => {
    frequenciesAPI.registraAscolto(slug, { evento: nome, secondo: Math.floor(secondo || 0), provenienza: prov, playlist: playlistSlug || null, provaToken: prova() })
      .catch(() => { /* la misura non ferma il suono */ });
    if (haAccount()) {
      if (nome === 'avvio') platformApi.post('/platform/me/sound/ascolto', { slug, secondo: 0 }).catch(() => {});
      if (nome === 'fine') platformApi.post('/platform/me/sound/ascolto', { slug, fine: true }).catch(() => {});
    }
  }, []);

  /* avvia una meditazione: item = card del catalogo o payload pubblico */
  const avviaDavvero = useCallback(async (item, opz = {}) => {
    const pl = opz.playlist !== undefined ? opz.playlist : playlist;
    const prov = opz.da || da;
    butta();
    setCancello(false);
    setElapsed(0);
    setCaricamento(true);
    ascoltoRef.current = { avviato: false, quartili: {} };
    ultimoSalvatoRef.current = 0;
    let t = item;
    try {
      if (!('anteprima_url' in (item || {})) || !('master_pronto' in (item || {}))) {
        t = (await frequenciesAPI.getPublic(item.slug)).data;
      }
    } catch { setCaricamento(false); return; }
    setTraccia(t); setPlaylist(pl); setDa(prov);
    const apertoOra = sbloccato();
    setUnlocked(apertoOra);
    const d = t.score?.duration_sec || t.duration_sec || 0;
    const meta = { titolo: t.title, autore: t.guida_nome || t.operator?.name };
    const quartili = (sec) => {
      const q = ascoltoRef.current.quartili;
      [['q25', 0.25], ['q50', 0.5], ['q75', 0.75], ['fine', 0.98]].forEach(([k, f]) => {
        if (!q[k] && d && sec >= d * f) { q[k] = true; evento(t.slug, k, sec, pl?.slug, prov); }
      });
      if (haAccount() && sec - ultimoSalvatoRef.current >= 15) {
        ultimoSalvatoRef.current = sec;
        platformApi.post('/platform/me/sound/ascolto', { slug: t.slug, secondo: Math.floor(sec) }).catch(() => {});
      }
    };
    const avvio = () => {
      if (!ascoltoRef.current.avviato) { ascoltoRef.current.avviato = true; frequenciesAPI.registerPlay(t.slug).catch(() => {}); evento(t.slug, 'avvio', 0, pl?.slug, prov); }
    };
    let src = null, durata = d, anteprima = false;
    try {
      if (apertoOra && t.master_pronto) {
        /* il pass: con la prova del Cerchio via header; con il solo account
           Aurya via il client della piattaforma (il client operatore non
           porta quel token: nella pagina intera questo caso finiva in sintesi) */
        const pass = prova()
          ? (await frequenciesAPI.masterPass(t.slug, prova())).data.pass
          : (await platformApi.get(`/frequencies/public/${t.slug}/master-pass`)).data.pass;
        src = `${process.env.REACT_APP_BACKEND_URL || ''}/api/frequencies/public/${t.slug}/master?pass=${encodeURIComponent(pass)}`;
      } else if (t.anteprima_url) {
        src = t.anteprima_url; durata = Math.min(PREVIEW_SEC, d || PREVIEW_SEC); anteprima = true;
      }
    } catch { src = null; }
    if (!src) {
      /* senza file: la pagina intera sa sintetizzare dal vivo */
      setCaricamento(false);
      window.location.href = `/frequenze/${t.slug}?da=${encodeURIComponent(prov)}${pl ? `&playlist=${encodeURIComponent(pl.slug)}` : ''}`;
      return;
    }
    const h = lettoreDaUrl(src, durata, meta, {
      onPlay: () => { setPlaying(true); schermoAcceso(); avvio(); },
      onPause: () => { setPlaying(false); schermoLibero(); },
      onEnd: () => {
        setPlaying(false); schermoLibero();
        if (anteprima) { setCancello(true); return; }
        setElapsed(0);
        prossimaRef.current?.();
      },
      onTime: (sec) => {
        setElapsed(sec); quartili(sec);
        if (anteprima && sec >= PREVIEW_SEC) { h.pause(); setCancello(true); }
      },
    });
    try {   // la copertina sullo schermo bloccato (predisposizione app)
      if (t.cover_url && navigator.mediaSession?.metadata) {
        navigator.mediaSession.metadata = new window.MediaMetadata({
          title: t.title, artist: meta.autore ? `${meta.autore} · Aurya Sound` : 'Aurya Sound',
          artwork: [{ src: t.cover_url, sizes: '1200x1200', type: 'image/webp' }],
        });
      }
    } catch { /* decorativo */ }
    hRef.current = h;
    setCaricamento(false);
    if (opz.da_secondo > 5 && opz.da_secondo < durata - 5) h.seek(opz.da_secondo);
    h.play();
  }, [butta, da, evento, playlist]);

  const avviaConSipario = useMemo(() => guard(avviaDavvero), [guard, avviaDavvero]);
  const avvia = useCallback((item, opz) => { avviaConSipario(item, opz); }, [avviaConSipario]);

  const toggle = useCallback(() => {
    const h = hRef.current;
    if (!h) { if (tracciaRef.current) avvia(tracciaRef.current, { da_secondo: elapsed }); return; }
    if (playing) h.pause(); else h.play();
  }, [avvia, elapsed, playing]);
  const seek = useCallback((sec) => {
    const h = hRef.current; if (!h) return;
    const tetto = unlocked ? Infinity : PREVIEW_SEC - 1;
    h.seek(Math.min(sec, tetto)); setElapsed(Math.min(sec, tetto));
  }, [unlocked]);

  const posizione = playlist && traccia ? (playlist.tracce || []).findIndex((x) => x.slug === traccia.slug) : -1;
  const prossimaRef = useRef(null);
  const vai = useCallback((delta) => {
    if (posizione < 0) return false;
    const t = (playlist.tracce || [])[posizione + delta];
    if (!t) return false;
    avvia(t, { playlist, da: 'playlist' });
    return true;
  }, [avvia, playlist, posizione]);
  prossimaRef.current = () => { if (!vai(1)) butta(); };

  const chiudi = useCallback(() => { butta(); setTraccia(null); setPlaylist(null); setCancello(false); }, [butta]);
  /* dopo lo sblocco dal cancello: si riparte da capo col master */
  const sbloccaERiparti = useCallback(() => {
    setUnlocked(true); setCancello(false);
    if (tracciaRef.current) avviaDavvero(tracciaRef.current, {});
  }, [avviaDavvero]);

  const valore = useMemo(() => ({
    traccia, playlist, playing, elapsed, caricamento, cancello, unlocked, posizione, scheda,
    avvia, toggle, seek, chiudi, sbloccaERiparti, prossima: () => vai(1), precedente: () => vai(-1),
    apriScheda: setScheda, chiudiScheda: () => setScheda(null), openReview, setCancello,
    /* il sipario lo disegna la pagina DENTRO il suo .fqz: fuori resterebbe senza stile */
    curtain,
  }), [traccia, playlist, playing, elapsed, caricamento, cancello, unlocked, posizione, scheda, avvia, toggle, seek, chiudi, sbloccaERiparti, vai, openReview, curtain]);

  return <Ctx.Provider value={valore}>{children}</Ctx.Provider>;
}

export function useLettore() {
  return useContext(Ctx);
}
