/**
 * useDesignTokens — resolve design tokens from the catalog response,
 * apply sensible defaults, and emit a CSS-variables object the parent
 * page can pour onto its root `<div style={cssVars}>`.
 *
 * Phase 9 of the pre-launch refinement. The merchant configures up
 * to 6 tokens from the admin UI:
 *
 *   accent_color    hex (optional)       → --sf-accent
 *   font_family     manrope|inter|serif|system → --sf-font
 *   border_radius   sharp|standard|soft|pill   → --sf-radius
 *   density         compact|standard|spacious  → --sf-density-gap
 *                                              → --sf-density-pad
 *   header_style    solid|translucent|minimal  → --sf-header-bg-alpha
 *                                              → --sf-header-blur
 *   card_style      shadow|flat|outlined        → --sf-card-shadow
 *                                              → --sf-card-border
 *
 * Why CSS variables (not Tailwind classes)
 * ----------------------------------------
 * Tailwind classes have to be present at build time (JIT scanning).
 * Switching the radius based on a runtime token would require us to
 * write a switch on `if (radius === 'soft') return 'rounded-2xl' else …`
 * for every consumer — fragile and verbose. CSS variables let the
 * consumer write a SINGLE class (e.g. `rounded-[var(--sf-radius)]`)
 * and the value swaps server-side.
 *
 * Architecture note: this hook is parallel to useDesignTokens for
 * the LANDING pages (Phase 12 will wire those). For now only the
 * main storefront index applies the tokens — landings keep their
 * current Tailwind classes until Phase 12 polish.
 *
 * Returns
 * -------
 * {
 *   tokens:  { accent_color, font_family, border_radius, density,
 *              header_style, card_style }      // resolved + defaults
 *   cssVars: { '--sf-accent': '#FF5500', ... } // ready for inline style
 * }
 *
 * Memoized on `catalog?.design_tokens` reference. Re-renders
 * triggered by unrelated state (cart change, etc.) DON'T recompute.
 */

import { useMemo } from 'react';


// Default token set.
//
// Important: these defaults match the pre-Phase-9 visual baseline
// (Phase 8.3's modernized header + the legacy CommerceCard styling).
// A regression caught during smoke: an earlier draft used "solid"
// header_style as default, which DROPPED the Phase 8.3 frosted glass.
// header_style: 'translucent' restores the visual continuity.
//
// accent_color stays null so consumers can fall back to brand_color
// when not configured.
const DEFAULT_TOKENS = Object.freeze({
  accent_color: null,
  font_family: 'manrope',
  border_radius: 'standard',
  density: 'standard',
  // 'translucent' = backdrop-blur 12px + alpha 0.8.
  // Matches the Phase 8.3 modernization. Merchants who want a
  // traditional opaque bar pick 'solid' explicitly.
  header_style: 'translucent',
  card_style: 'shadow',
  // ── Logo display defaults (logo flexibility refinement) ──────────
  // md height (40px) matches the pre-refinement w-10 h-10. 'contain'
  // (new default) respects aspect ratio so wide/vertical logos
  // render undistorted; 'cover' is the legacy opt-in. The toggle
  // for the store name defaults to TRUE so non-customized stores
  // keep their current look.
  logo_height: 'md',
  logo_fit: 'contain',
  show_store_name: true,
});


// ── Token → CSS value mappings ─────────────────────────────────────────────


// Border radius scale. The 'standard' value (16px = Tailwind
// rounded-2xl) matches the pre-Phase-9 CommerceCard radius — keeps
// the visual continuity for stores that haven't customized.
// Smaller / larger options are explicit opt-ins.
const RADIUS_PX = Object.freeze({
  sharp: '6px',       // ≈ rounded-md
  standard: '16px',   // = rounded-2xl (matches pre-Phase-9 cards)
  soft: '24px',       // ≈ rounded-3xl
  pill: '9999px',     // pill
});


// Density translates to TWO CSS variables: grid `gap` and section
// vertical padding. Components opt into either based on their
// concern (grid layout vs. card internal spacing).
const DENSITY_VARS = Object.freeze({
  compact:   { gap: '0.5rem',  pad: '0.5rem'  },
  standard:  { gap: '1rem',    pad: '1rem'    },
  spacious:  { gap: '1.5rem',  pad: '1.5rem'  },
});


// Header style maps to a background-alpha + backdrop-blur pair.
// The 'translucent' default (Phase 9 fix) uses 12px blur to match
// Tailwind's `backdrop-blur-md` which Phase 8.3 originally used.
const HEADER_STYLE_VARS = Object.freeze({
  solid:        { alpha: '1',    blur: '0px'  },  // opaque (opt-in)
  translucent:  { alpha: '0.8',  blur: '12px' },  // frosted glass — default
  minimal:      { alpha: '0.55', blur: '16px' },  // very transparent + strong blur
});


// Card style produces a resting shadow + hover shadow + border
// alpha. The pre-Phase-9 cards used Tailwind shadow-sm with
// hover:shadow-md — these defaults reproduce that exactly so the
// 'shadow' default keeps the original look. 'flat' and 'outlined'
// are explicit opt-ins.
const CARD_STYLE_VARS = Object.freeze({
  shadow: {
    shadow:      '0 1px 2px 0 rgb(0 0 0 / 0.05)',   // Tailwind shadow-sm
    shadowHover: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',  // shadow-md
    border:      'transparent',
  },
  flat: {
    shadow:      'none',
    shadowHover: 'none',
    border:      'transparent',
  },
  outlined: {
    shadow:      'none',
    shadowHover: '0 1px 3px rgba(0,0,0,0.06)',
    border:      'rgba(0,0,0,0.10)',
  },
});


// Font family — maps to a CSS font-family stack. The Manrope /
// Public Sans / JetBrains Mono stacks come from the existing
// tailwind.config.js (theme.extend.fontFamily); we just pick the
// right one per token.
const FONT_FAMILY = Object.freeze({
  manrope: '"Manrope", system-ui, sans-serif',
  inter:   '"Inter", system-ui, sans-serif',
  serif:   '"Georgia", "Times New Roman", serif',
  system:  'system-ui, -apple-system, sans-serif',
});


// Logo height preset → CSS pixel value. Three steps are enough:
// finer granularity invited inconsistent header heights across
// stores and gave admins decision fatigue. 32px works for compact
// nav layouts; 40px is the legacy default; 56px is "brand-forward"
// for stores where the logo IS the brand identity (no name text).
const LOGO_HEIGHT_PX = Object.freeze({
  sm: '32px',
  md: '40px',
  lg: '56px',
});


// Logo object-fit. 'contain' (NEW default) lets wide / vertical
// logos render at their natural aspect ratio inside the height
// box. 'cover' (legacy) crops to a square at the configured height
// — preserved for merchants who already designed around it.
const LOGO_FIT = Object.freeze({
  contain: 'contain',
  cover: 'cover',
});


/**
 * Resolve a candidate token value: if it's in the allowed enum
 * return it, otherwise return the default. Pure helper, no React.
 */
function _resolveEnum(value, allowed, fallback) {
  if (typeof value !== 'string') return fallback;
  if (Object.prototype.hasOwnProperty.call(allowed, value)) return value;
  return fallback;
}


// ── Accent color computation helpers ───────────────────────────────────────


/**
 * Parse a `#RGB` / `#RRGGBB` hex color into [r, g, b] ints (0-255).
 * Returns null when the input isn't a valid hex string — callers
 * fall back to the static gray-900 default.
 */
function _parseHex(hex) {
  if (typeof hex !== 'string' || !hex.startsWith('#')) return null;
  const body = hex.slice(1);
  if (body.length === 3) {
    // #RGB → #RRGGBB shorthand expansion
    const r = parseInt(body[0] + body[0], 16);
    const g = parseInt(body[1] + body[1], 16);
    const b = parseInt(body[2] + body[2], 16);
    return Number.isNaN(r + g + b) ? null : [r, g, b];
  }
  if (body.length === 6 || body.length === 8) {
    const r = parseInt(body.slice(0, 2), 16);
    const g = parseInt(body.slice(2, 4), 16);
    const b = parseInt(body.slice(4, 6), 16);
    return Number.isNaN(r + g + b) ? null : [r, g, b];
  }
  return null;
}


/**
 * Convert [r,g,b] (0-255) back to a #RRGGBB hex string.
 */
function _hexFromRgb([r, g, b]) {
  const clamp = (v) => Math.max(0, Math.min(255, Math.round(v)));
  const toH = (v) => clamp(v).toString(16).padStart(2, '0');
  return `#${toH(r)}${toH(g)}${toH(b)}`;
}


/**
 * Darken a hex color by `pct` (0 to 1). Used to compute the
 * `--sf-accent-hover` variant from the merchant's accent color.
 *
 * Implementation: multiplies each RGB channel by (1 - pct). Linear
 * darkening is good enough for hover states; a proper HSL shift
 * would preserve hue better but adds 30+ lines of conversion code
 * for marginal visual gain on small saturation changes.
 *
 * Returns null if the input isn't a valid hex.
 */
function _darkenHex(hex, pct = 0.1) {
  const rgb = _parseHex(hex);
  if (!rgb) return null;
  const factor = 1 - Math.max(0, Math.min(1, pct));
  return _hexFromRgb(rgb.map((c) => c * factor));
}


/**
 * Pick a foreground color (black or white) that contrasts the
 * given accent hex. Uses the YIQ formula — the same heuristic
 * Material Design + most a11y libraries use for this.
 *
 * Threshold 128 (the midpoint) keeps the choice deterministic:
 * accent luminance ≥ 128 → text BLACK, else WHITE. Guarantees
 * WCAG AA contrast on most accent choices (some borderline
 * yellows / cyans may need manual override, but the common case
 * — brand reds / blues / greens / pinks — works correctly).
 */
function _contrastForeground(hex) {
  const rgb = _parseHex(hex);
  if (!rgb) return null;
  const [r, g, b] = rgb;
  // ITU-R BT.601 luma coefficients (YIQ formula).
  const yiq = (r * 299 + g * 587 + b * 114) / 1000;
  // Use a near-black instead of #000 so the text doesn't feel
  // harsh against light accents.
  return yiq >= 128 ? '#111827' : '#FFFFFF';
}


/**
 * Build the final CSS variables dict from resolved tokens. The
 * variable names are namespaced with `--sf-` (storefront) to avoid
 * collisions with shadcn / Tailwind's existing CSS vars.
 */
function _buildCssVars({
  accent_color,
  font_family,
  border_radius,
  density,
  header_style,
  card_style,
}, storeBrandFallback) {
  const accent = accent_color || storeBrandFallback || null;
  const densityVars = DENSITY_VARS[density] || DENSITY_VARS.standard;
  const headerVars = HEADER_STYLE_VARS[header_style] || HEADER_STYLE_VARS.solid;
  const cardVars = CARD_STYLE_VARS[card_style] || CARD_STYLE_VARS.shadow;

  // Only emit `--sf-accent` when we actually have a value — the
  // consumer's CSS uses `var(--sf-accent, fallback)` so omitting the
  // variable lets the fallback win without "" cascade weirdness.
  const out = {
    '--sf-font':              FONT_FAMILY[font_family] || FONT_FAMILY.manrope,
    '--sf-radius':            RADIUS_PX[border_radius] || RADIUS_PX.standard,
    '--sf-density-gap':       densityVars.gap,
    '--sf-density-pad':       densityVars.pad,
    '--sf-header-bg-alpha':   headerVars.alpha,
    '--sf-header-blur':       headerVars.blur,
    '--sf-card-shadow':       cardVars.shadow,
    '--sf-card-shadow-hover': cardVars.shadowHover,
    '--sf-card-border':       cardVars.border,
  };

  // Accent color triple — resting / hover / foreground.
  //
  // Emit the 3 vars ONLY when `accent` is a valid hex. When not,
  // consumer CSS falls back to its hardcoded default via the
  // arbitrary-value syntax `var(--sf-accent, #111827)` — so
  // stores without an accent set keep the gray-900 look from
  // pre-refinement.
  //
  // Hover: 10% linear darkening (good enough for the small range
  // typical of CTA hover transitions).
  // Foreground: YIQ formula picks black (#111827) for light accents,
  // white (#FFFFFF) for dark accents — guarantees readability on
  // any reasonable accent choice.
  if (accent) {
    const hoverHex = _darkenHex(accent, 0.1);
    const fgHex = _contrastForeground(accent);
    out['--sf-accent'] = accent;
    if (hoverHex) out['--sf-accent-hover'] = hoverHex;
    if (fgHex) out['--sf-accent-fg'] = fgHex;
  }
  return out;
}


/**
 * Resolve logo display tokens from the catalog response.
 * Separate from the main token resolver because the header
 * consumes these as direct props (height in px, fit string, bool
 * for show-name) rather than CSS variables — the bool can't be
 * a CSS var, and inline px values render simpler than reading
 * a var inside a Tailwind className.
 */
function _resolveLogoTokens(raw) {
  return {
    height:     LOGO_HEIGHT_PX[
      typeof raw?.logo_height === 'string' && LOGO_HEIGHT_PX[raw.logo_height]
        ? raw.logo_height
        : 'md'
    ],
    fit: typeof raw?.logo_fit === 'string' && LOGO_FIT[raw.logo_fit]
      ? raw.logo_fit
      : 'contain',
    // Bool default true; admin must explicitly set false to hide
    // the store name. Treat undefined/null/missing as default true.
    showStoreName: raw?.show_store_name !== false,
  };
}


/**
 * @param {{
 *   design_tokens?: { [key: string]: any },
 *   store_info?: { brand_color?: string },
 * } | null | undefined} catalog
 * @returns {{
 *   tokens: typeof DEFAULT_TOKENS,
 *   cssVars: Record<string, string>,
 * }}
 */
export default function useDesignTokens(catalog) {
  return useMemo(() => {
    const raw = catalog?.design_tokens || {};

    // Resolve every token through its enum / default chain.
    const tokens = {
      ...DEFAULT_TOKENS,
      accent_color: typeof raw.accent_color === 'string' ? raw.accent_color : null,
      font_family:   _resolveEnum(raw.font_family,   FONT_FAMILY,        DEFAULT_TOKENS.font_family),
      border_radius: _resolveEnum(raw.border_radius, RADIUS_PX,           DEFAULT_TOKENS.border_radius),
      density:       _resolveEnum(raw.density,       DENSITY_VARS,        DEFAULT_TOKENS.density),
      header_style:  _resolveEnum(raw.header_style,  HEADER_STYLE_VARS,   DEFAULT_TOKENS.header_style),
      card_style:    _resolveEnum(raw.card_style,    CARD_STYLE_VARS,     DEFAULT_TOKENS.card_style),
    };

    const cssVars = _buildCssVars(tokens, catalog?.store_info?.brand_color);

    // Logo display tokens — exposed as a typed object next to cssVars
    // so consumers (StorefrontHeader) can read them without parsing
    // CSS vars. The bool `showStoreName` in particular can't live in
    // a CSS variable; pixel height could but cleaner inline.
    const logo = _resolveLogoTokens(raw);

    return { tokens, cssVars, logo };
  // Memo deps: only the raw token dict reference + the brand fallback.
  // Any unrelated catalog change (products, store_info text fields,
  // cart-induced re-render) skips recompute.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [catalog?.design_tokens, catalog?.store_info?.brand_color]);
}


// Re-export the constant maps so callers (admin UI, tests, future
// landing-page polish) can inspect the allowed values without
// duplicating the lookup tables.
export const DESIGN_TOKEN_OPTIONS = Object.freeze({
  font_family:   Object.keys(FONT_FAMILY),
  border_radius: Object.keys(RADIUS_PX),
  density:       Object.keys(DENSITY_VARS),
  header_style:  Object.keys(HEADER_STYLE_VARS),
  card_style:    Object.keys(CARD_STYLE_VARS),
  logo_height:   Object.keys(LOGO_HEIGHT_PX),
  logo_fit:      Object.keys(LOGO_FIT),
});
