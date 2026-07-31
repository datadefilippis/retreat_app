import React from 'react';
import { useTranslation } from 'react-i18next';
import { BRAND_NAME, BRAND_PAYOFF } from '../config/brand';

/**
 * BrandLogo — il marchio Aurya (loto + sole nel cerchio dorato) con
 * wordmark tipografico.
 *
 * Il logo è un PNG statico in /public (deciso dal founder 13/7/2026,
 * sostituisce sia il glifo provvisorio 🌿 sia i vecchi SVG AFianco che
 * vivevano in /public/brand/). Il wordmark è testo: niente asset da
 * rigenerare quando cambia la tipografia.
 *
 * Usato su:
 *   · pagine auth (login, signup, reset) → size="md"
 *   · header sidebar dell'app → size="xs" variant="light"
 *
 * Props
 * -----
 *   size       'xs' | 'sm' | 'md' (default 'md')
 *   variant    'dark' | 'light' (default 'dark') — colore del wordmark:
 *              dark su sfondi chiari, light (bianco) su sfondi scuri.
 *   className  classi extra per il wrapper
 */
export function BrandLogo({ size = 'md', variant = 'dark', className = '' }) {
  const { t } = useTranslation('landings');
  // Wordmark in capitali romane (Cinzel, stile Trajan) molto spaziate +
  // payoff sotto, come da direzione visiva del founder (13/7/2026).
  // Il payoff compare da 'sm' in su: nella sidebar (xs) non ci sta.
  const SIZE_MAP = {
    xs: { icon: 'h-[42px]', word: 'text-lg',  motto: null },          // sidebar
    sm: { icon: 'h-[52px]', word: 'text-2xl', motto: 'text-[9px]' },
    md: { icon: 'h-[64px]', word: 'text-3xl', motto: 'text-[11px]' }, // pagine auth
  };
  const { icon: iconHeight, word: wordSize, motto: mottoSize } = SIZE_MAP[size] || SIZE_MAP.md;

  // Oro del wordmark: profondo su sfondi chiari, chiaro su sfondi scuri.
  const gold = variant === 'light' ? 'text-[#cbb578]' : 'text-[#8a7440]';
  const goldSoft = variant === 'light' ? 'text-[#cbb578]/80' : 'text-[#8a7440]/80';

  // Nitidezza su mobile (composite-layer rasterisation, vedi storia del
  // file): il PNG 512px scala bene, i due hint restano innocui altrove.
  const crispImg = {
    transform: 'translateZ(0)',
    WebkitTransform: 'translateZ(0)',
    imageRendering: '-webkit-optimize-contrast',
  };

  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <img
        src="/logo-aurya-512.png"
        alt=""
        aria-hidden="true"
        className={`${iconHeight} w-auto select-none`}
        style={crispImg}
        draggable={false}
      />
      <span className="flex flex-col select-none">
        <span className={`font-brand font-medium uppercase leading-none tracking-[0.3em] ${wordSize} ${gold}`}>
          {BRAND_NAME}
        </span>
        {mottoSize && (
          /* HP1 — il payoff e' una frase: tracking calmo e niente
             maiuscolo, cosi' resta leggibile sotto il wordmark */
          <span className={`font-brand tracking-[0.06em] leading-snug mt-1.5 max-w-[22ch] ${mottoSize} ${goldSoft}`}>
            {t('marketplace.payoff', { defaultValue: BRAND_PAYOFF })}
          </span>
        )}
      </span>
    </div>
  );
}

export default BrandLogo;
