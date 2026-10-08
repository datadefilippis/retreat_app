/**
 * anteprima.js — ES1 (8/10/2026): L'ASCOLTO DI UNA SCHEDA, UNA ALLA VOLTA.
 *
 * Decisione del founder: per il pubblico un suono alla volta; il «combinare»
 * resta in Crea. Lo stesso motore delle anteprime del compositore
 * (engine/synth.startCardLive: il cfg intero, f0 → f1 con la sua curva),
 * lo stesso sipario prima del primo suono (useSafetyGate), un tetto di
 * 60 secondi: una scheda si assaggia, non si subisce.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { startCardLive } from '../engine/synth';
import { useSafetyGate } from '../SafetyCurtain';

export const ANTEPRIMA_SEC = 60;
let _ctx = null;
const audioCtx = () => {
  if (!_ctx) { const AC = window.AudioContext || window.webkitAudioContext; _ctx = new AC(); }
  return _ctx;
};

export function useAnteprimaFrequenza() {
  const [scheda, setScheda] = useState(null);      // la scheda che suona
  const [secondi, setSecondi] = useState(0);
  const hRef = useRef(null);
  const timerRef = useRef(null);
  const { guard, curtain, openReview } = useSafetyGate();

  const ferma = useCallback(() => {
    if (hRef.current) { try { hRef.current.stop(); } catch { /* niente */ } hRef.current = null; }
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null; }
    setScheda(null); setSecondi(0);
  }, []);
  useEffect(() => () => ferma(), [ferma]);

  const suonaDavvero = useCallback(async (s) => {
    ferma();
    try {
      const ctx = audioCtx();
      await ctx.resume();
      const cfg = s.cfg || {};
      const fval = cfg.method === 'tone' ? (cfg.carrier ?? 432) : (cfg.f0 ?? 10);
      hRef.current = startCardLive(ctx, cfg, cfg.gain ?? 0.25, fval);
      setScheda(s); setSecondi(0);
      const t0 = Date.now();
      timerRef.current = setInterval(() => {
        const sec = (Date.now() - t0) / 1000;
        setSecondi(sec);
        if (sec >= ANTEPRIMA_SEC) ferma();
      }, 250);
    } catch { ferma(); }
  }, [ferma]);
  const suona = useMemo(() => guard(suonaDavvero), [guard, suonaDavvero]);
  const toggle = useCallback((s) => { if (scheda && scheda.t === s.t) ferma(); else suona(s); }, [scheda, suona, ferma]);

  return { scheda, secondi, suona, ferma, toggle, curtain, openReview, inAscolto: (s) => !!scheda && scheda.t === s.t };
}
