/**
 * Design token canonical names. Esportati come constants TS oltre che
 * come CSS variables — il widget puo' fare riferimento ai nomi via
 * `tokens.COLOR_PRIMARY` invece di stringare a mano `var(--afianco-...)`.
 *
 * Naming convention:
 *   --afianco-<category>-<name>[-<variant>]
 */

export const tokens = {
  // ── Color palette ────────────────────────────────────────────────────
  COLOR_PRIMARY: '--afianco-color-primary',
  COLOR_PRIMARY_TEXT: '--afianco-color-primary-text',
  COLOR_ACCENT: '--afianco-color-accent',
  COLOR_BG: '--afianco-color-bg',
  COLOR_SURFACE: '--afianco-color-surface',
  COLOR_BORDER: '--afianco-color-border',
  COLOR_TEXT_PRIMARY: '--afianco-color-text-primary',
  COLOR_TEXT_SECONDARY: '--afianco-color-text-secondary',
  COLOR_TEXT_MUTED: '--afianco-color-text-muted',
  COLOR_DANGER: '--afianco-color-danger',
  COLOR_SUCCESS: '--afianco-color-success',
  COLOR_WARNING: '--afianco-color-warning',

  // ── Spacing scale (4px base) ────────────────────────────────────────
  SPACING_XS: '--afianco-spacing-xs', // 4px
  SPACING_SM: '--afianco-spacing-sm', // 8px
  SPACING_MD: '--afianco-spacing-md', // 12px
  SPACING_LG: '--afianco-spacing-lg', // 16px
  SPACING_XL: '--afianco-spacing-xl', // 24px
  SPACING_XXL: '--afianco-spacing-xxl', // 32px

  // ── Radius ──────────────────────────────────────────────────────────
  RADIUS_SM: '--afianco-radius-sm',
  RADIUS_MD: '--afianco-radius-md',
  RADIUS_LG: '--afianco-radius-lg',
  RADIUS_PILL: '--afianco-radius-pill',

  // ── Typography ──────────────────────────────────────────────────────
  FONT_FAMILY: '--afianco-font-family',
  FONT_SIZE_XS: '--afianco-font-size-xs',
  FONT_SIZE_SM: '--afianco-font-size-sm',
  FONT_SIZE_MD: '--afianco-font-size-md',
  FONT_SIZE_LG: '--afianco-font-size-lg',
  FONT_SIZE_XL: '--afianco-font-size-xl',
  FONT_WEIGHT_REGULAR: '--afianco-font-weight-regular',
  FONT_WEIGHT_MEDIUM: '--afianco-font-weight-medium',
  FONT_WEIGHT_BOLD: '--afianco-font-weight-bold',
  LINE_HEIGHT_TIGHT: '--afianco-line-height-tight',
  LINE_HEIGHT_NORMAL: '--afianco-line-height-normal',

  // ── Shadows / elevation ─────────────────────────────────────────────
  SHADOW_SM: '--afianco-shadow-sm',
  SHADOW_MD: '--afianco-shadow-md',
  SHADOW_LG: '--afianco-shadow-lg',

  // ── Z-index scale ───────────────────────────────────────────────────
  Z_BASE: '--afianco-z-base',
  Z_DROPDOWN: '--afianco-z-dropdown',
  Z_MODAL: '--afianco-z-modal',
  Z_TOAST: '--afianco-z-toast',

  // ── Motion ──────────────────────────────────────────────────────────
  DURATION_FAST: '--afianco-duration-fast', // 120ms
  DURATION_NORMAL: '--afianco-duration-normal', // 200ms
  DURATION_SLOW: '--afianco-duration-slow', // 320ms
  EASING_STANDARD: '--afianco-easing-standard',
} as const;

export type TokenName = (typeof tokens)[keyof typeof tokens];

/**
 * Helper per riferire un token CSS in template strings:
 *   `background: ${cssVar(tokens.COLOR_PRIMARY)};`  → `background: var(--afianco-color-primary);`
 *   `padding: ${cssVar(tokens.SPACING_MD, '12px')};` → `padding: var(--afianco-spacing-md, 12px);`
 */
export function cssVar(name: TokenName, fallback?: string): string {
  return fallback != null ? `var(${name}, ${fallback})` : `var(${name})`;
}
