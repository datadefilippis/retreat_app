/**
 * @afianco/design-tokens — Phase 1 Step 21 (Track B).
 *
 * Design system tokens + Lit base styles per i Web Components afianco-*.
 * Esposti come CSS custom properties (--afianco-*) così che il merchant
 * possa override-arli con il proprio CSS, mantenendo la coerenza interna.
 *
 * Esempio override merchant:
 *   <style>
 *     afianco-product-card,
 *     afianco-cart-drawer {
 *       --afianco-color-primary: #ff5500;
 *       --afianco-color-primary-text: #ffffff;
 *       --afianco-radius-md: 4px;
 *     }
 *   </style>
 */

export * from './tokens.js';
export * from './lit-styles.js';
