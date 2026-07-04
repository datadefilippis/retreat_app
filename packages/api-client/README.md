# @afianco/api-client

Typed fetch wrapper per il widget embed cross-origin (Stream A).

## Features

- ✅ **Type-safe** — re-exports `@afianco/shared-types` (single import)
- ✅ **Auto-headers** — `X-Afianco-Store-Slug` + `Idempotency-Key` (UUID v4)
- ✅ **Pluggable token storage** — `LocalStorageTokenStorage` (default) o `MemoryTokenStorage`
- ✅ **Auto-retry** — 429 + 5xx con exponential backoff + Retry-After parsing
- ✅ **Error mapping** — `AfiancoAuthError` / `AfiancoRateLimitError` / `AfiancoValidationError`
- ✅ **Zero deps** — solo `@afianco/shared-types` come workspace dep
- ✅ **No cookies** — `credentials: 'omit'`, Bearer JWT in header

## Usage

```ts
import { createAfiancoClient } from '@afianco/api-client';

const client = createAfiancoClient({
  slug: 'bottega-demo',
  // baseUrl: 'http://localhost:8000', // dev
});

// Bootstrap (1 round-trip)
const init = await client.embed.getInit();
console.log(init.org_name, init.categories);

// Catalog filterable
const products = await client.embed.getProducts({
  category: 'catering',
  sort: 'price_asc',
  limit: 20,
});

// Cart CRUD
const cart = await client.embed.cart.create();
await client.embed.cart.update(cart.id, {
  items: [{ product_id: 'p1', quantity: 2 }],
});

// Checkout (3 modes)
//   Guest:
const guest = await client.embed.checkout.start({ /* ... */ });

//   Signup inline (token salvato automaticamente):
const signed = await client.embed.checkout.start({
  /* ... */ create_account: true, account_password: 'StrongPass!2026',
});

//   Authenticated (Bearer presa da tokenStorage):
await client.customerAuth.login({ slug: 'bottega-demo', email, password });
const authd = await client.embed.checkout.start({ /* ... */ });

// Customer portal
const me = await client.customer.me();
const orders = await client.customer.orders();
```

## Token Storage

Per dafault il client usa `localStorage` con key `afianco_token_<slug>`.
Merchant con stricter security puo' override:

```ts
import { createAfiancoClient, MemoryTokenStorage } from '@afianco/api-client';

const client = createAfiancoClient({
  slug: 'demo',
  tokenStorage: new MemoryTokenStorage(), // volatile, lost on reload
});
```

## Error Handling

```ts
try {
  await client.embed.checkout.start(/* ... */);
} catch (e) {
  if (e instanceof AfiancoValidationError) {
    // 400 con error code (return_url_rejected, cart_empty, ...)
    console.error('Validation:', e.errorCode, e.detail);
  } else if (e instanceof AfiancoAuthError) {
    // 401 / 403 — token expired or cross-tenant
    client.customerAuth.logout();
  } else if (e instanceof AfiancoRateLimitError) {
    // 429 — server-suggested wait
    setTimeout(retry, (e.retryAfterSeconds ?? 5) * 1000);
  }
}
```

## Build

```bash
pnpm --filter @afianco/api-client build       # tsup → ESM + CJS + d.ts
pnpm --filter @afianco/api-client typecheck   # tsc --noEmit
pnpm --filter @afianco/api-client test        # vitest run
```
