/**
 * Section — la battuta editoriale (HP1, ritoccata in HP3).
 *
 * Una sezione = una battuta. Il respiro nasce dall'alternanza dei
 * fondi e dal ritmo verticale, non dal padding a caso: qui il ritmo
 * e' UNO SOLO, deciso dal prop `rhythm`.
 *
 * tone   cream (fondo dominante) | sand (un gradino piu' caldo, per
 *        far galleggiare le schede bianche) | paper (bianco pieno,
 *        la vetrina) | sage (l'ancora verde, testo chiaro)
 * rhythm hero    → l'apertura: poco sopra, molto sotto
 *        screen  → la battuta piena
 *        flow    → altezza dal contenuto (sezioni con immagini)
 *        none    → il padding lo mette il contenuto (fasce a tutta
 *                  larghezza, dove il fondo arriva ai bordi)
 *
 * HP3 — via il `min-h-[82vh] flex items-center` del ritmo `screen`.
 * Era lui il responsabile del "troppo bianco" segnalato dal founder:
 * su desktop una sezione di tre righe veniva stirata a una schermata
 * intera e centrata, lasciando due vuoti enormi sopra e sotto. Ora il
 * respiro sta nel padding: tanto FRA le sezioni (i padding si sommano
 * al confine), meno DENTRO.
 */
import React from 'react';
import useReveal from './useReveal';

const TONES = {
  cream: 'bg-background text-foreground',
  sand: 'bg-[#f2ece0] text-foreground',
  paper: 'bg-white text-foreground',
  sage: 'bg-[#2f5749] text-[#f6f2e8]',
};

const RHYTHM = {
  hero: 'pt-8 pb-14 sm:pt-14 sm:pb-24 lg:pt-16 lg:pb-28',
  screen: 'py-20 sm:py-28 lg:py-32',
  flow: 'py-16 sm:py-24 lg:py-28',
  none: '',
};

export default function Section({
  tone = 'cream',
  rhythm = 'screen',
  as: Tag = 'section',
  width = 'max-w-5xl',
  gutter = true,
  labelledBy,
  className = '',
  innerClassName = '',
  children,
  ...rest
}) {
  const reveal = useReveal();
  return (
    <Tag
      aria-labelledby={labelledBy}
      className={`${TONES[tone] || TONES.cream} ${RHYTHM[rhythm] ?? RHYTHM.flow} ${className}`}
      {...rest}
    >
      <div
        ref={reveal.ref}
        className={`${reveal.className} ${width} mx-auto w-full ${gutter ? 'px-6 sm:px-8' : ''} ${innerClassName}`}
      >
        {children}
      </div>
    </Tag>
  );
}
