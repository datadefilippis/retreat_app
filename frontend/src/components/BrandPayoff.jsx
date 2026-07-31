/**
 * BrandPayoff — l'occhiello di brand delle superfici pubbliche.
 *
 * HP1: il payoff e' diventato una FRASE ("Ci si fida di qualcuno, non
 * di qualcosa."), non tre parole. Il vecchio trattamento (maiuscolo
 * con tracking 0.35em) su una frase lunga andava a capo male e
 * sfondava i 375px. Qui il tracking e' calmo, il maiuscolo resta solo
 * sui corpi minuscoli, e la frase puo' andare a capo senza rompere
 * nulla. Un componente solo = un solo posto da cambiare.
 *
 * tone  cream → oro scuro su fondo chiaro
 *       deep  → oro chiaro su fondo salvia scuro
 *       hero  → oro chiaro su foto (con ombra di leggibilita')
 * size  xs | sm | hero
 * rules → i due fili d'oro ai lati (solo hero del calendario)
 */
import React from 'react';
import { useTranslation } from 'react-i18next';
import { BRAND_PAYOFF } from '../config/brand';

const TONES = {
  cream: 'text-[#7d6836]',
  deep: 'text-[#d6c49a]',
  hero: 'text-[#ecd9a8] text-hero-shadow',
};

const SIZES = {
  xs: 'text-[11px] tracking-[0.16em] uppercase',
  sm: 'text-xs sm:text-sm tracking-[0.14em] uppercase',
  hero: 'text-sm sm:text-lg md:text-xl tracking-[0.08em]',
};

export default function BrandPayoff({
  tone = 'cream',
  size = 'xs',
  rules = false,
  className = '',
}) {
  const { t } = useTranslation('landings');
  const text = t('marketplace.payoff', { defaultValue: BRAND_PAYOFF });
  const rule = 'hidden sm:block h-px w-10 md:w-16 shrink-0 bg-current opacity-40';

  return (
    <p
      data-brand-payoff
      className={`font-brand ${TONES[tone] || TONES.cream} ${SIZES[size] || SIZES.xs}
                  ${rules ? 'flex items-center justify-center gap-4' : ''} ${className}`}
    >
      {rules && <span aria-hidden className={rule} />}
      <span className="max-w-full">{text}</span>
      {rules && <span aria-hidden className={rule} />}
    </p>
  );
}
