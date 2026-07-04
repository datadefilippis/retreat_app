# packages/

Shared TypeScript libraries usate da uno o più workspace in ``apps/*``.

## Roadmap pacchetti

| Package | Scope | Status |
|---|---|---|
| `@afianco/shared-types` | TS types condivisi backend ↔ frontend (generati da Pydantic) | Step 6 |
| `@afianco/design-tokens` | Brand colors, typography, design system tokens | Step 6 |
| `@afianco/api-client` | Axios client + types per public API (storefront + embed) | Step 11 |
| `@afianco/slot-elements` | Web Components Lit (afianco-product-card, afianco-cart, ecc.) | Stream A |
| `@afianco/embed-runtime` | Logica condivisa embed-sdk + ai-site-renderer | Stream A |

## Convenzioni

- Ogni package ha `package.json` con `name: "@afianco/<name>"`, `version: "0.0.0"`, `private: true`
- Linguaggio: TypeScript strict mode
- Build: `tsup` per ESM + CJS output
- Test: Vitest + happy-dom (per Web Components)
- Consumer via pnpm workspaces: `import { foo } from '@afianco/shared-types'`
