import React from 'react';
import { BRAND_NAME } from '../config/brand';

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
  const SIZE_MAP = {
    xs: { icon: 'h-[42px]', word: 'text-xl' },   // sidebar
    sm: { icon: 'h-[52px]', word: 'text-2xl' },
    md: { icon: 'h-[64px]', word: 'text-3xl' },  // pagine auth
  };
  const { icon: iconHeight, word: wordSize } = SIZE_MAP[size] || SIZE_MAP.md;

  const wordColor = variant === 'light' ? 'text-white' : 'text-foreground';

  // Nitidezza su mobile (composite-layer rasterisation, vedi storia del
  // file): il PNG 512px scala bene, i due hint restano innocui altrove.
  const crispImg = {
    transform: 'translateZ(0)',
    WebkitTransform: 'translateZ(0)',
    imageRendering: '-webkit-optimize-contrast',
  };

  return (
    <div className={`flex items-center gap-2.5 ${className}`}>
      <img
        src="/logo-aurya-512.png"
        alt=""
        aria-hidden="true"
        className={`${iconHeight} w-auto select-none`}
        style={crispImg}
        draggable={false}
      />
      <span className={`${wordSize} ${wordColor} font-bold tracking-tight select-none`}>
        {BRAND_NAME}
      </span>
    </div>
  );
}

export default BrandLogo;
