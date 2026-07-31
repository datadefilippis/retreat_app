/**
 * Section — la battuta editoriale (HP1).
 *
 * Una sezione = una schermata, un pensiero. Il respiro nasce
 * dall'alternanza prova/pensiero e dal fondo, non dal padding a caso:
 * qui il ritmo verticale e' UNO SOLO, deciso dal prop `rhythm`.
 *
 * tone   crema (fondo dominante) | carta (un gradino piu' chiaro,
 *        per staccare la prova dal pensiero) | salvia (il picco)
 * rhythm screen  → circa una schermata su desktop, contenuto centrato
 *        flow    → altezza dal contenuto (sezioni con immagini)
 */
import React from 'react';
import useReveal from './useReveal';

const TONES = {
  cream: 'bg-background text-foreground',
  paper: 'bg-white text-foreground',
  sage: 'bg-[#2f5749] text-[#f6f2e8]',
};

const RHYTHM = {
  screen: 'py-20 sm:py-28 lg:min-h-[82vh] lg:py-32 flex items-center',
  flow: 'py-20 sm:py-24 lg:py-28',
};

export default function Section({
  tone = 'cream',
  rhythm = 'screen',
  as: Tag = 'section',
  width = 'max-w-5xl',
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
      className={`${TONES[tone] || TONES.cream} ${RHYTHM[rhythm] || RHYTHM.flow} ${className}`}
      {...rest}
    >
      <div
        ref={reveal.ref}
        className={`${reveal.className} ${width} mx-auto w-full px-6 sm:px-8 ${innerClassName}`}
      >
        {children}
      </div>
    </Tag>
  );
}
