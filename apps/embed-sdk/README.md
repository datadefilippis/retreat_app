# @afianco/embed-sdk

Web Components SDK per cross-origin merchant embed (Stream A).

Status: **Phase 0 Step 11 — scaffolding** (2026-05-28). Solo
`<afianco-test-card>` per validare la pipeline. Componenti reali
(product browser, cart, checkout) iniziano in Stream A.

## Architecture

| Concern | Choice | Rationale |
|---|---|---|
| Bundler | Vite | Velocità dev, tree-shaking superiore a CRA |
| Component lib | Lit 3 | Web Components nativi, Shadow DOM, ~5KB |
| Language | TypeScript strict | Type safety + autocompletion |
| Test runner | Vitest + happy-dom | Stack omogenea Vite, DOM emulato veloce |
| Bundle target | ES2017 | Safari 11+, IE-free, async nativo |
| Output formats | ESM + UMD | Modern + legacy WP fallback |
| Bundle size budget | ~80 KB gzip | Sotto la soglia mobile-friendly |

## Commands

Tutti i comandi vanno invocati dalla root del monorepo:

```bash
# Dev server con HMR
pnpm --filter @afianco/embed-sdk dev

# Build produzione (ESM + UMD in dist/)
pnpm --filter @afianco/embed-sdk build

# Type-check
pnpm --filter @afianco/embed-sdk typecheck

# Unit tests
pnpm --filter @afianco/embed-sdk test
```

## Usage (futuro, post-CDN deploy)

```html
<!-- Cross-origin merchant include -->
<script
  type="module"
  src="https://cdn.afianco.app/embed/v0/afianco-embed.es.js">
</script>

<!-- Use components like native HTML tags -->
<afianco-test-card store="my-store" message="Welcome"></afianco-test-card>
```

## Components

| Tag | Status | Description |
|---|---|---|
| `<afianco-test-card>` | ✅ Step 11 | Validation card. No API call. |
| `<afianco-product-card>` | 🚧 Stream A | Single product display + add-to-cart |
| `<afianco-cart>` | 🚧 Stream A | Mini cart drawer |
| `<afianco-checkout>` | 🚧 Stream A | Inline checkout flow |

## Security

- Shadow DOM su tutti i componenti → no CSS leakage merchant ↔ widget
- Tutti gli endpoint API che chiameremo passeranno via
  `/api/public/embed/{slug}/*` → coperti da DynamicCORSMiddleware
  (Phase 0 Step 7) e Idempotency Middleware (Phase 0 Step 8)
- Nessuna credenziale embedded nel bundle — solo public ``store`` slug
