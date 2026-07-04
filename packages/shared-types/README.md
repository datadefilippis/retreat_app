# @afianco/shared-types

TypeScript interfaces mirroring the Pydantic models of the embed public API
(Stream A). Single source of truth for the widget Lit (`apps/embed-sdk`)
and the api-client (`@afianco/api-client`).

## Status

Phase 1 Step 19 (2026-05-28) — **manual** TS interfaces for V1. Pydantic
schemas → TS via `pydantic2ts` is deferred to V2 once stability of the
shape contract is proven.

## Coverage

| Backend Pydantic model | TS interface |
|---|---|
| `EmbedInitResponse` | ✅ |
| `EmbedCapabilities` | ✅ |
| `EmbedCategorySummary` / `EmbedCategoryItem` | ✅ |
| `EmbedCategoriesResponse` | ✅ |
| `EmbedProductCard` / `EmbedProductsResponse` | ✅ |
| `EmbedPagination` | ✅ |
| `CartItem` / `CartItemInput` | ✅ |
| `CartCreate` / `CartUpdate` / `CartResponse` / `CartMergeRequest` | ✅ |
| `EmbedCheckoutStartRequest` / `EmbedCheckoutStartResponse` | ✅ |
| `EmbedPostMessage` (Step 17 bridge payload) | ✅ |
| `CustomerSignupRequest` / `CustomerLoginRequest` | ✅ |
| `CustomerTokenResponse` / `CustomerProfile` | ✅ |
| `CustomerOrderSummary` | ✅ |
| `ForgotPasswordRequest` / `ResetPasswordRequest` / `VerifyEmailRequest` | ✅ |
| `StoreInfo` | ✅ |
| `ProductType` / `TransactionMode` / `PriceMode` / `EmbedProductSortMode` | ✅ |

## Usage

```ts
import type {
  EmbedInitResponse,
  EmbedProductCard,
  CartResponse,
} from '@afianco/shared-types';

async function bootstrap(slug: string): Promise<EmbedInitResponse> {
  const r = await fetch(`/api/public/embed/init/${slug}`, {
    headers: { 'X-Afianco-Store-Slug': slug },
  });
  return r.json();
}
```

## Build

```bash
pnpm --filter @afianco/shared-types build       # tsup → ESM + CJS + d.ts
pnpm --filter @afianco/shared-types typecheck   # tsc --noEmit
pnpm --filter @afianco/shared-types test        # vitest run
```

## Convention

Updating the backend Pydantic models REQUIRES updating this package
in the same commit. Sentinel test enforced by the consumer
`@afianco/api-client` will catch missing fields.
