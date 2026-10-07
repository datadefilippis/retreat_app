/**
 * SuonoPlayer — LA TRACCIA AURYA SOUND dentro un corso (AU, 8/10/2026).
 *
 * Riusa il player condiviso delle esperienze (frequenze/esperienze/ascolto:
 * creaAscolto = motore + ponte + veglia + avviso cuffie) e il sipario delle
 * controindicazioni (SafetyCurtain) come su /frequenze/:slug. Niente file:
 * la ricetta arriva dal play-url (studente) o dall'anteprima (pubblico).
 *
 * Props: traccia {title, score, duration_sec}, onTic(sec), onFine(),
 * compatto (per la copertina della landing).
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Play, Square, Headphones, Waves } from 'lucide-react';
import { creaAscolto } from '../../frequenze/esperienze/ascolto';
import { useSafetyGate, SafetyLine } from '../../frequenze/SafetyCurtain';

const fmt = (s) => { const n = Math.max(0, Math.floor(s || 0)); return `${Math.floor(n / 60)}:${String(n % 60).padStart(2, '0')}`; };

export default function SuonoPlayer({ traccia, onTic, onFine, compatto = false }) {
  const [inAscolto, setInAscolto] = useState(false);
  const [trascorso, setTrascorso] = useState(0);
  const [perso, setPerso] = useState(false);
  const ascoltoRef = useRef(null);
  const { guard, curtain, openReview } = useSafetyGate();
  const durata = traccia?.duration_sec || traccia?.score?.duration_sec || 0;

  useEffect(() => () => { ascoltoRef.current?.ferma?.(); ascoltoRef.current = null; }, []);
  useEffect(() => { ascoltoRef.current?.ferma?.(); ascoltoRef.current = null; setInAscolto(false); setTrascorso(0); }, [traccia?.id]);

  const avvia = useCallback(guard(async () => {
    if (!traccia?.score) return;
    if (!ascoltoRef.current) {
      ascoltoRef.current = creaAscolto(traccia.score, {
        onTic: (t) => { setTrascorso(t); onTic?.(t); },
        onFine: () => { setInAscolto(false); setTrascorso(durata); onFine?.(); },
        onPerso: () => { setInAscolto(false); setPerso(true); },
      });
    }
    setPerso(false);
    await ascoltoRef.current.avvia();
    setInAscolto(true);
  }), [guard, traccia, durata, onTic, onFine]);

  const ferma = () => { ascoltoRef.current?.ferma?.(); setInAscolto(false); };
  const avviso = ascoltoRef.current?.avviso;

  return (
    <div className={`relative overflow-hidden rounded-2xl bg-gradient-to-br from-[#1f3a30] to-[#2f5749] text-white ${compatto ? 'aspect-video' : 'p-5 sm:p-7'}`} data-testid="suono-player">
      {curtain}
      <div className={`flex h-full flex-col justify-between ${compatto ? 'p-4 pt-12' : ''}`}>
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="inline-flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-white/70"><Waves className="h-3.5 w-3.5" aria-hidden /> Aurya Sound</p>
            <h3 className="mt-0.5 truncate font-display text-xl">{traccia?.title}</h3>
          </div>
          <span className="flex-none text-sm tabular-nums text-white/80">{fmt(trascorso)} / {fmt(durata)}</span>
        </div>
        <div className={`flex items-center gap-4 ${compatto ? 'mt-3' : 'mt-6'}`}>
          <button type="button" onClick={inAscolto ? ferma : avvia} data-testid="suono-play"
                  className="flex h-14 w-14 flex-none items-center justify-center rounded-full bg-white text-[#2f5749] shadow-lg transition hover:scale-105">
            {inAscolto ? <Square className="h-5 w-5 fill-current" aria-hidden /> : <Play className="ml-0.5 h-6 w-6 fill-current" aria-hidden />}
          </button>
          <div className="min-w-0 flex-1">
            {/* niente seek: la traccia suona dal vivo, dall'inizio; la barra dice solo dove sei */}
            <div className="h-2 w-full overflow-hidden rounded-full bg-white/20" role="progressbar" aria-valuemin={0} aria-valuemax={durata || 0} aria-valuenow={Math.floor(trascorso)} data-testid="suono-barra">
              <div className="h-full rounded-full bg-white transition-[width] duration-300" style={{ width: `${durata ? Math.min(100, (100 * trascorso) / durata) : 0}%` }} />
            </div>
            <p className="mt-1 inline-flex items-center gap-1 text-[11px] text-white/70">
              <Headphones className="h-3 w-3" aria-hidden /> {avviso ? 'Meglio con le cuffie' : 'Cuffie consigliate'} · si ascolta dal vivo, senza scaricare nulla
            </p>
          </div>
        </div>
        {perso && <p className="mt-2 text-xs text-amber-200">L'ascolto si è interrotto (schermo bloccato o scheda in pausa): tocca di nuovo play.</p>}
        {!compatto && <div className="mt-3 text-[11px] leading-relaxed text-white/70 [&_button]:ml-1 [&_button]:underline"><SafetyLine onOpen={openReview} /></div>}
      </div>
    </div>
  );
}
