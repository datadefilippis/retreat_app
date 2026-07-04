# @afianco/design-tokens

CSS variables + Lit base styles per i Web Components `<afianco-*>`.

## Usage in a Lit Web Component

```ts
import { LitElement, css, html } from 'lit';
import { customElement } from 'lit/decorators.js';
import { afiancoBaseStyles, tokens, cssVar } from '@afianco/design-tokens';

@customElement('afianco-button')
export class AfiancoButton extends LitElement {
  static styles = [
    afiancoBaseStyles,
    css`
      button {
        background: ${cssVar(tokens.COLOR_PRIMARY)};
        color: ${cssVar(tokens.COLOR_PRIMARY_TEXT)};
        padding: ${cssVar(tokens.SPACING_MD)} ${cssVar(tokens.SPACING_LG)};
        border-radius: ${cssVar(tokens.RADIUS_MD)};
        border: none;
        cursor: pointer;
        font-weight: ${cssVar(tokens.FONT_WEIGHT_MEDIUM)};
        transition: opacity ${cssVar(tokens.DURATION_FAST)} ${cssVar(tokens.EASING_STANDARD)};
      }
      button:hover { opacity: 0.9; }
    `,
  ];

  render() {
    return html`<button><slot></slot></button>`;
  }
}
```

## Merchant override

I CSS variable sono definite su `:host` di ogni componente — il merchant
può override con CSS standard:

```html
<style>
  afianco-button,
  afianco-product-card,
  afianco-cart-drawer {
    --afianco-color-primary: #ff5500;
    --afianco-color-primary-text: #ffffff;
    --afianco-radius-md: 4px;
    --afianco-font-family: 'Custom Font', sans-serif;
  }
</style>
```

I default usano una palette neutra (blue/grey) che funziona su 90% dei
brand merchant senza modifiche.

## Token reference

| Categoria | Token | Default |
|---|---|---|
| Color | `--afianco-color-primary` | `#2563eb` |
|  | `--afianco-color-bg` | `#ffffff` |
|  | `--afianco-color-text-primary` | `#0f172a` |
| Spacing | `--afianco-spacing-md` | `12px` |
|  | `--afianco-spacing-lg` | `16px` |
| Radius | `--afianco-radius-md` | `8px` |
| Typography | `--afianco-font-size-md` | `14px` |
| Shadow | `--afianco-shadow-md` | `0 2px 6px rgba(0,0,0,.08)` |
| Motion | `--afianco-duration-normal` | `200ms` |

Vedi `src/lit-styles.ts` per la lista completa.

## Build

```bash
pnpm --filter @afianco/design-tokens build
pnpm --filter @afianco/design-tokens typecheck
pnpm --filter @afianco/design-tokens test
```
