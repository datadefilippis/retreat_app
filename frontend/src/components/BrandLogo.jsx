import React from 'react';

/**
 * BrandLogo — official AFianco brand mark (3D ring icon + wordmark).
 *
 * Renders the 2026 visual identity. Used on:
 *   · auth pages (login, signup, forgot password, reset password) →
 *     variant="dark", size="md"
 *   · main app sidebar header (over the navy gradient) →
 *     variant="light", size="xs"
 *
 * Replaces the legacy <TrendingUp/> + "AFianco" text combo wherever
 * it appeared.
 *
 * The SVGs ship as static assets in /public/brand/ so the bundler
 * doesn't inline them — keeps the JS bundle small and lets the browser
 * cache them aggressively across sessions.
 *
 * Props
 * -----
 *   size       'xs' | 'sm' | 'md' (default 'md')
 *              - xs: icon 36px, wordmark 24px — sidebar header
 *              - sm: icon 58px, wordmark 36px
 *              - md: icon 72px, wordmark 44px — auth pages (1.8x)
 *   variant    'dark' | 'light' (default 'dark')
 *              - dark: dark-colored wordmark (wordmark.svg), use on
 *                light backgrounds (auth pages)
 *              - light: white wordmark (wordmark-light.svg), use on
 *                dark backgrounds (sidebar, dark hero sections)
 *   className  optional Tailwind classes for the wrapper
 *
 * Accessibility
 * -------------
 * The icon is decorative (aria-hidden) — the wordmark carries the
 * brand name in its rendered text and an alt attribute. Screen readers
 * announce "afianco" once, not twice.
 */
export function BrandLogo({ size = 'md', variant = 'dark', className = '' }) {
  // 2026-05-22 — three sizes covering every usage in the app.
  // Using Tailwind arbitrary values for exact pixel sizes; preset
  // spacing-scale gaps (h-16 vs h-20 would be 1.6x vs 2.0x) don't
  // give a clean 1.8x ratio for the auth screens.
  const SIZE_MAP = {
    // 2026-05-22 — sidebar size bumped +40% (icon 36→50px, wordmark
    // 24→34px). Still fits inside the h-16 (64px) sidebar header with
    // breathing room top/bottom (~7px each side).
    xs: { icon: 'h-[50px]',  word: 'h-[34px]'  }, // sidebar
    sm: { icon: 'h-[58px]',  word: 'h-9'       },
    md: { icon: 'h-[72px]',  word: 'h-[44px]'  }, // auth pages, 1.8x
  };
  const { icon: iconHeight, word: wordHeight } = SIZE_MAP[size] || SIZE_MAP.md;

  // Wordmark variant: dark for light backgrounds (default), light
  // (white text) for dark backgrounds. The icon SVG renders well on
  // both — the rings carry their own gradients.
  const wordmarkSrc = variant === 'light'
    ? '/brand/wordmark-light.svg'
    : '/brand/wordmark.svg';

  // 2026-05-22 mobile crispness fix.
  //
  // Symptom: on iOS Safari (and to a lesser extent Android Chrome) the
  // logo + wordmark rendered blurry inside the auth layout. Two
  // independent causes contribute:
  //
  //   1. Composite-layer rasterisation. When an <img src=*.svg> sits
  //      inside a parent that uses ``backdrop-filter`` (or any layer
  //      that promotes its children to a composited bitmap), the SVG
  //      is rasterised at the resolution of the COMPOSITE LAYER, not
  //      the device pixel ratio. ``translateZ(0)`` (a.k.a. the GPU-hack)
  //      forces the <img> onto its own GPU layer at native DPR, so the
  //      SVG paints at the device's full resolution. We include the
  //      -webkit- prefix variant for Safari ≤ 15.
  //
  //   2. Bilinear scaling. Mobile browsers default to ``auto`` for
  //      ``image-rendering``, which bilinear-resamples bitmaps. SVGs
  //      are vector but become bitmaps once rasterised (see 1). The
  //      ``-webkit-optimize-contrast`` hint instructs Safari to prefer
  //      a sharper resampling kernel — Safari is the only browser that
  //      respects this exact value.
  //
  // The two settings are cheap (style attribute only) and harmless
  // outside the bug surface: desktop browsers ignore the hint, the
  // translateZ is a no-op when the element wasn't going to composite
  // anyway. We attach them inline rather than in a global stylesheet
  // because BrandLogo is the only component that paints these
  // specific SVGs in a backdrop-filter context, and a global
  // ``img { transform: translateZ(0) }`` would over-promote layers.
  const crispImg = {
    transform: 'translateZ(0)',
    WebkitTransform: 'translateZ(0)',
    imageRendering: '-webkit-optimize-contrast',
  };

  return (
    <div className={`flex items-center gap-2.5 ${className}`}>
      <img
        src="/brand/logo.svg"
        alt=""
        aria-hidden="true"
        className={`${iconHeight} w-auto select-none`}
        style={crispImg}
        draggable={false}
      />
      <img
        src={wordmarkSrc}
        alt="afianco"
        className={`${wordHeight} w-auto select-none`}
        style={crispImg}
        draggable={false}
      />
    </div>
  );
}

export default BrandLogo;
