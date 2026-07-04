/**
 * Lit base styles + reset CSS per i Web Components afianco-*.
 *
 * Tutti i componenti devono importare `afiancoBaseStyles` come prima
 * voce di `static styles = [...]` per:
 *   1. ricevere i default dei token CSS (override-abili dal merchant)
 *   2. ereditare il reset Shadow DOM-isolation friendly
 */

import { css, type CSSResultGroup } from 'lit';

/**
 * Default token values + reset minimale. Tutti i custom property
 * sono definiti su `:host` cosi' il merchant può override sul wrapper:
 *
 *   afianco-product-card { --afianco-color-primary: #ff5500; }
 */
export const afiancoBaseStyles: CSSResultGroup = css`
  :host {
    /* ── Color palette ── */
    --afianco-color-primary: #2563eb;
    --afianco-color-primary-text: #ffffff;
    --afianco-color-accent: #0ea5e9;
    --afianco-color-bg: #ffffff;
    --afianco-color-surface: #f8fafc;
    --afianco-color-border: #e2e8f0;
    --afianco-color-text-primary: #0f172a;
    --afianco-color-text-secondary: #475569;
    --afianco-color-text-muted: #94a3b8;
    --afianco-color-danger: #dc2626;
    --afianco-color-success: #16a34a;
    --afianco-color-warning: #d97706;

    /* ── Spacing scale (4px base) ── */
    --afianco-spacing-xs: 4px;
    --afianco-spacing-sm: 8px;
    --afianco-spacing-md: 12px;
    --afianco-spacing-lg: 16px;
    --afianco-spacing-xl: 24px;
    --afianco-spacing-xxl: 32px;

    /* ── Radius ── */
    --afianco-radius-sm: 4px;
    --afianco-radius-md: 8px;
    --afianco-radius-lg: 12px;
    --afianco-radius-pill: 999px;

    /* ── Typography ── */
    --afianco-font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI',
      Roboto, 'Helvetica Neue', sans-serif;
    --afianco-font-size-xs: 11px;
    --afianco-font-size-sm: 13px;
    --afianco-font-size-md: 14px;
    --afianco-font-size-lg: 16px;
    --afianco-font-size-xl: 20px;
    --afianco-font-weight-regular: 400;
    --afianco-font-weight-medium: 500;
    --afianco-font-weight-bold: 600;
    --afianco-line-height-tight: 1.3;
    --afianco-line-height-normal: 1.55;

    /* ── Shadows ── */
    --afianco-shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
    --afianco-shadow-md: 0 2px 6px rgba(0, 0, 0, 0.08);
    --afianco-shadow-lg: 0 8px 24px rgba(0, 0, 0, 0.12);

    /* ── Z-index ── */
    --afianco-z-base: 1;
    --afianco-z-dropdown: 1000;
    --afianco-z-modal: 2000;
    --afianco-z-toast: 3000;

    /* ── Motion ── */
    --afianco-duration-fast: 120ms;
    --afianco-duration-normal: 200ms;
    --afianco-duration-slow: 320ms;
    --afianco-easing-standard: cubic-bezier(0.4, 0, 0.2, 1);

    /* ── Reset ── */
    font-family: var(--afianco-font-family);
    font-size: var(--afianco-font-size-md);
    line-height: var(--afianco-line-height-normal);
    color: var(--afianco-color-text-primary);
    box-sizing: border-box;
  }

  :host *,
  :host *::before,
  :host *::after {
    box-sizing: inherit;
  }

  /* Accessible focus ring for keyboard navigation */
  :host(:focus-visible),
  :host *:focus-visible {
    outline: 2px solid var(--afianco-color-primary);
    outline-offset: 2px;
  }
`;
