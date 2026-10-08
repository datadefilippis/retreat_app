/**
 * AudioPlayer — L'MP3 di una lezione (AU, 8/10/2026). Un <audio> nativo con
 * la copertina del corso: il src e' il play-url col pass a tempo (studente)
 * o l'anteprima pubblica. Manda il tempo ascoltato (onTime, ogni ~15 s) e
 * la fine (onEnded) a chi lo monta; su telefono i controlli sono quelli di
 * sistema, che la gente conosce.
 */
import React, { useEffect, useRef } from 'react';
import { Music } from 'lucide-react';

export default function AudioPlayer({ src, titolo, copertina, onTime, onEnded, compatto = false }) {
  const ref = useRef(null);
  const ultimoRef = useRef(0);
  useEffect(() => { ultimoRef.current = 0; }, [src]);
  const tempo = () => {
    const a = ref.current;
    if (!a || !onTime) return;
    const t = Math.floor(a.currentTime || 0);
    if (t - ultimoRef.current >= 15) { ultimoRef.current = t; onTime(t); }
  };
  return (
    <div className={`relative overflow-hidden rounded-2xl bg-gray-900 text-white ${compatto ? 'aspect-video' : ''}`} data-testid="audio-player">
      {copertina
        ? <img src={copertina} alt="" className="absolute inset-0 h-full w-full object-cover opacity-50" />
        : <div className="absolute inset-0 bg-gradient-to-br from-[#1f3a30] to-[#2f5749]" />}
      <div className={`relative flex h-full flex-col justify-end gap-3 ${compatto ? 'p-4' : 'p-5 sm:p-7'}`}>
        {!compatto && <span className="flex h-12 w-12 items-center justify-center rounded-full bg-white/15"><Music className="h-6 w-6" aria-hidden /></span>}
        <div className="min-w-0">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-white/70">Lezione audio</p>
          <h3 className="truncate font-display text-xl">{titolo}</h3>
        </div>
        <audio ref={ref} src={src || undefined} controls controlsList="nodownload" preload="metadata" className="w-full"
               onTimeUpdate={tempo} onEnded={() => onEnded?.()} data-testid="audio-element" />
      </div>
    </div>
  );
}
