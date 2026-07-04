/**
 * Sentinel tests for @afianco/design-tokens — Phase 1 Step 21.
 *
 * Verify:
 *  - All canonical token names are exported (no accidental rename)
 *  - cssVar() helper produces valid CSS syntax
 *  - afiancoBaseStyles defines :host with all token defaults
 *  - Token values are non-empty strings (sane defaults)
 */

import { describe, it, expect } from 'vitest';
import { tokens, cssVar, afiancoBaseStyles } from '../src/index.js';

describe('@afianco/design-tokens — tokens map', () => {
  it('exports canonical color tokens', () => {
    expect(tokens.COLOR_PRIMARY).toBe('--afianco-color-primary');
    expect(tokens.COLOR_PRIMARY_TEXT).toBe('--afianco-color-primary-text');
    expect(tokens.COLOR_BG).toBe('--afianco-color-bg');
  });

  it('exports spacing tokens', () => {
    for (const k of ['SPACING_XS', 'SPACING_SM', 'SPACING_MD', 'SPACING_LG', 'SPACING_XL', 'SPACING_XXL']) {
      expect(tokens[k as keyof typeof tokens]).toMatch(/^--afianco-spacing-/);
    }
  });

  it('exports radius tokens', () => {
    expect(tokens.RADIUS_SM).toBe('--afianco-radius-sm');
    expect(tokens.RADIUS_PILL).toBe('--afianco-radius-pill');
  });

  it('exports typography tokens', () => {
    expect(tokens.FONT_FAMILY).toBe('--afianco-font-family');
    expect(tokens.FONT_SIZE_LG).toBe('--afianco-font-size-lg');
    expect(tokens.FONT_WEIGHT_BOLD).toBe('--afianco-font-weight-bold');
  });

  it('exports shadow + z-index + motion tokens', () => {
    expect(tokens.SHADOW_LG).toBe('--afianco-shadow-lg');
    expect(tokens.Z_MODAL).toBe('--afianco-z-modal');
    expect(tokens.DURATION_NORMAL).toBe('--afianco-duration-normal');
    expect(tokens.EASING_STANDARD).toBe('--afianco-easing-standard');
  });

  it('all token names follow --afianco-* convention', () => {
    for (const [k, v] of Object.entries(tokens)) {
      expect(v, `${k}=${v}`).toMatch(/^--afianco-/);
    }
  });
});

describe('@afianco/design-tokens — cssVar helper', () => {
  it('builds var() without fallback', () => {
    expect(cssVar(tokens.COLOR_PRIMARY)).toBe('var(--afianco-color-primary)');
  });

  it('builds var() with fallback', () => {
    expect(cssVar(tokens.RADIUS_MD, '8px')).toBe('var(--afianco-radius-md, 8px)');
  });
});

describe('@afianco/design-tokens — afiancoBaseStyles', () => {
  it('is a Lit CSSResultGroup', () => {
    expect(afiancoBaseStyles).toBeDefined();
    // Lit's css`` produces an object with `.cssText` getter
    const cssText = (afiancoBaseStyles as { cssText?: string }).cssText;
    expect(typeof cssText).toBe('string');
  });

  it('defines all token defaults', () => {
    const cssText = (afiancoBaseStyles as { cssText: string }).cssText;
    // Spot-check the most critical tokens
    expect(cssText).toContain('--afianco-color-primary:');
    expect(cssText).toContain('--afianco-spacing-md:');
    expect(cssText).toContain('--afianco-radius-md:');
    expect(cssText).toContain('--afianco-font-family:');
    expect(cssText).toContain('--afianco-shadow-md:');
    expect(cssText).toContain('--afianco-duration-normal:');
  });

  it('includes :host selector + box-sizing reset', () => {
    const cssText = (afiancoBaseStyles as { cssText: string }).cssText;
    expect(cssText).toContain(':host');
    expect(cssText).toContain('box-sizing');
  });

  it('includes accessibility focus-visible style', () => {
    const cssText = (afiancoBaseStyles as { cssText: string }).cssText;
    expect(cssText).toContain(':focus-visible');
  });
});
