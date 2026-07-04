/**
 * Sentinel tests for @afianco/api-client — Phase 1 Step 20.
 *
 * Verifica:
 *  - Headers automatici (X-Afianco-Store-Slug + Idempotency-Key + Bearer)
 *  - URL building (path + query)
 *  - Error mapping (401/403/429/400/5xx)
 *  - Retry su 429/5xx con backoff
 *  - Token storage abstraction
 *  - Auth flow (login → store token → me)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  createAfiancoClient,
  AfiancoApiError,
  AfiancoAuthError,
  AfiancoRateLimitError,
  AfiancoValidationError,
  MemoryTokenStorage,
} from '../src/index.js';

/** Build a mock fetch that returns a sequence of responses. */
function mockFetchSequence(
  responses: Array<{ status: number; body?: unknown; headers?: Record<string, string> }>,
): { fetchFn: typeof fetch; calls: Array<{ url: string; init: RequestInit }> } {
  const calls: Array<{ url: string; init: RequestInit }> = [];
  let index = 0;
  const fetchFn = (async (input: RequestInfo | URL, init?: RequestInit) => {
    calls.push({ url: String(input), init: init ?? {} });
    const r = responses[index++] ?? responses[responses.length - 1];
    if (!r) throw new Error('mockFetchSequence: out of responses');
    const headers = new Headers({
      'content-type': 'application/json',
      ...(r.headers ?? {}),
    });
    return new Response(r.body !== undefined ? JSON.stringify(r.body) : null, {
      status: r.status,
      headers,
    });
  }) as unknown as typeof fetch;
  return { fetchFn, calls };
}

describe('@afianco/api-client — construction', () => {
  it('throws if slug missing', () => {
    expect(() => createAfiancoClient({ slug: '' })).toThrow(/slug/);
  });

  it('uses default base URL', () => {
    const c = createAfiancoClient({ slug: 'demo' });
    expect(c.baseUrl).toBe('https://api.afianco.app');
  });

  it('normalizes trailing slash on baseUrl', () => {
    const c = createAfiancoClient({ slug: 'demo', baseUrl: 'http://localhost:8000///' });
    expect(c.baseUrl).toBe('http://localhost:8000');
  });

  it('exposes the embed namespace', () => {
    const c = createAfiancoClient({ slug: 'demo' });
    expect(typeof c.embed.getInit).toBe('function');
    expect(typeof c.embed.cart.create).toBe('function');
    expect(typeof c.embed.cart.merge).toBe('function');
    expect(typeof c.embed.checkout.start).toBe('function');
    expect(typeof c.embed.checkout.completeUrl).toBe('function');
  });

  it('exposes customerAuth + customer namespace', () => {
    const c = createAfiancoClient({ slug: 'demo' });
    expect(typeof c.customerAuth.login).toBe('function');
    expect(typeof c.customerAuth.signup).toBe('function');
    expect(typeof c.customerAuth.logout).toBe('function');
    expect(typeof c.customer.me).toBe('function');
    expect(typeof c.customer.orders).toBe('function');
  });
});

describe('@afianco/api-client — headers', () => {
  it('adds X-Afianco-Store-Slug on every request', async () => {
    const { fetchFn, calls } = mockFetchSequence([
      { status: 200, body: { slug: 'demo', org_name: 'X' } },
    ]);
    const c = createAfiancoClient({ slug: 'demo', baseUrl: 'http://t', fetchFn });
    await c.embed.getInit();
    const headers = calls[0]!.init.headers as Record<string, string>;
    expect(headers['X-Afianco-Store-Slug']).toBe('demo');
  });

  it('adds Idempotency-Key on POST/PATCH/DELETE', async () => {
    const { fetchFn, calls } = mockFetchSequence([
      { status: 200, body: { id: 'cart_1', organization_id: 'o', items: [], item_count: 0, subtotal_snapshot: 0, created_at: 'x', updated_at: 'x', expires_at: 'x', source: 'embed' } },
    ]);
    const c = createAfiancoClient({ slug: 'demo', baseUrl: 'http://t', fetchFn });
    await c.embed.cart.create();
    const headers = calls[0]!.init.headers as Record<string, string>;
    expect(headers['Idempotency-Key']).toBeTruthy();
    expect(headers['Idempotency-Key'].length).toBeGreaterThan(30);
  });

  it('does NOT add Idempotency-Key on GET', async () => {
    const { fetchFn, calls } = mockFetchSequence([
      { status: 200, body: { slug: 'demo', org_name: 'X' } },
    ]);
    const c = createAfiancoClient({ slug: 'demo', baseUrl: 'http://t', fetchFn });
    await c.embed.getInit();
    const headers = calls[0]!.init.headers as Record<string, string>;
    expect(headers['Idempotency-Key']).toBeUndefined();
  });

  it('adds Bearer token when withAuth=true and storage has token', async () => {
    const storage = new MemoryTokenStorage();
    storage.set('test-jwt');
    const { fetchFn, calls } = mockFetchSequence([
      { status: 200, body: { id: 'a', email: 'x@y.com', name: 'X', locale: 'it', email_verified: true, created_at: 'x' } },
    ]);
    const c = createAfiancoClient({ slug: 'demo', baseUrl: 'http://t', fetchFn, tokenStorage: storage });
    await c.customer.me();
    const headers = calls[0]!.init.headers as Record<string, string>;
    expect(headers['Authorization']).toBe('Bearer test-jwt');
  });

  it('omits Bearer when no token in storage', async () => {
    const { fetchFn, calls } = mockFetchSequence([
      { status: 200, body: { id: 'a', email: 'x@y.com', name: 'X', locale: 'it', email_verified: true, created_at: 'x' } },
    ]);
    const c = createAfiancoClient({
      slug: 'demo',
      baseUrl: 'http://t',
      fetchFn,
      tokenStorage: new MemoryTokenStorage(),
    });
    await c.customer.me();
    const headers = calls[0]!.init.headers as Record<string, string>;
    expect(headers['Authorization']).toBeUndefined();
  });
});

describe('@afianco/api-client — URL building', () => {
  it('encodes slug in path', async () => {
    const { fetchFn, calls } = mockFetchSequence([
      { status: 200, body: { slug: 'my store', org_name: 'X' } },
    ]);
    const c = createAfiancoClient({ slug: 'my store', baseUrl: 'http://t', fetchFn });
    await c.embed.getInit();
    expect(calls[0]!.url).toContain('my%20store');
  });

  it('serializes query params correctly', async () => {
    const { fetchFn, calls } = mockFetchSequence([
      { status: 200, body: { slug: 'demo', currency: 'EUR', items: [], pagination: { total: 0, limit: 20, offset: 0, has_more: false } } },
    ]);
    const c = createAfiancoClient({ slug: 'demo', baseUrl: 'http://t', fetchFn });
    await c.embed.getProducts({ category: 'catering', sort: 'price_asc', limit: 5 });
    const url = new URL(calls[0]!.url);
    expect(url.searchParams.get('category')).toBe('catering');
    expect(url.searchParams.get('sort')).toBe('price_asc');
    expect(url.searchParams.get('limit')).toBe('5');
  });

  it('skips null/undefined query params', async () => {
    const { fetchFn, calls } = mockFetchSequence([
      { status: 200, body: { slug: 'demo', categories: [] } },
    ]);
    const c = createAfiancoClient({ slug: 'demo', baseUrl: 'http://t', fetchFn });
    await c.embed.getCategories({ withThumbnail: undefined });
    const url = new URL(calls[0]!.url);
    expect(url.searchParams.has('with_thumbnail')).toBe(false);
  });

  it('completeUrl helper builds correct query string', () => {
    const c = createAfiancoClient({ slug: 'demo', baseUrl: 'http://t' });
    const url = c.embed.checkout.completeUrl('ord_abc');
    expect(url).toBe('http://t/api/public/embed/checkout/complete?order_id=ord_abc');
  });
});

// ─── E2.4.3 — Preflight-safe slug query injection ────────────────────────
//
// Track E Step 2.4.3 — il backend DynamicCORSMiddleware deve poter leggere
// lo slug sul preflight OPTIONS. I browser NON inviano custom headers
// sui preflight, quindi X-Afianco-Store-Slug e' invisible. La soluzione e':
// il SDK inietta SEMPRE ?slug=... come query parameter (eccetto per i
// routes dove lo slug e' gia' nella path: init/categories/products).
//
// Senza questa garanzia, /cart, /checkout/start, /customer-auth/*,
// /customer/* falliscono al preflight con 403/400 → widget non funziona.

describe('@afianco/api-client — preflight-safe slug query injection (E2.4.3)', () => {
  it('does NOT inject ?slug= for /init/{slug} (already in path)', async () => {
    const { fetchFn, calls } = mockFetchSequence([
      { status: 200, body: { slug: 'demo', org_name: 'X' } },
    ]);
    const c = createAfiancoClient({ slug: 'demo', baseUrl: 'http://t', fetchFn });
    await c.embed.getInit();
    const url = new URL(calls[0]!.url);
    expect(url.searchParams.has('slug')).toBe(false);
    expect(url.pathname).toContain('/init/demo');
  });

  it('does NOT inject ?slug= for /categories/{slug}', async () => {
    const { fetchFn, calls } = mockFetchSequence([
      { status: 200, body: { slug: 'demo', categories: [] } },
    ]);
    const c = createAfiancoClient({ slug: 'demo', baseUrl: 'http://t', fetchFn });
    await c.embed.getCategories();
    const url = new URL(calls[0]!.url);
    expect(url.searchParams.has('slug')).toBe(false);
  });

  it('does NOT inject ?slug= for /products/{slug}', async () => {
    const { fetchFn, calls } = mockFetchSequence([
      { status: 200, body: { slug: 'demo', currency: 'EUR', items: [], pagination: { total: 0, limit: 20, offset: 0, has_more: false } } },
    ]);
    const c = createAfiancoClient({ slug: 'demo', baseUrl: 'http://t', fetchFn });
    await c.embed.getProducts();
    const url = new URL(calls[0]!.url);
    expect(url.searchParams.has('slug')).toBe(false);
  });

  it('INJECTS ?slug= for /cart POST (slug NOT in path)', async () => {
    const { fetchFn, calls } = mockFetchSequence([
      { status: 200, body: { id: 'c1', organization_id: 'o', items: [], item_count: 0, subtotal_snapshot: 0, created_at: 'x', updated_at: 'x', expires_at: 'x', source: 'embed' } },
    ]);
    const c = createAfiancoClient({ slug: 'acme', baseUrl: 'http://t', fetchFn });
    await c.embed.cart.create();
    const url = new URL(calls[0]!.url);
    expect(url.searchParams.get('slug')).toBe('acme');
  });

  it('INJECTS ?slug= for /checkout/start POST', async () => {
    const { fetchFn, calls } = mockFetchSequence([
      { status: 200, body: { checkout_url: 'https://stripe.com/x', session_id: 's1' } },
    ]);
    const c = createAfiancoClient({ slug: 'acme', baseUrl: 'http://t', fetchFn });
    await c.embed.checkout.start({ cart_id: 'c1', success_url: 'http://x', cancel_url: 'http://y' } as never);
    const url = new URL(calls[0]!.url);
    expect(url.searchParams.get('slug')).toBe('acme');
  });

  it('INJECTS ?slug= for /customer-auth/login', async () => {
    const { fetchFn, calls } = mockFetchSequence([
      { status: 200, body: { access_token: 'jwt', token_type: 'Bearer', expires_in: 3600 } },
    ]);
    const c = createAfiancoClient({ slug: 'acme', baseUrl: 'http://t', fetchFn });
    await c.customerAuth.login({ email: 'x@y.com', password: 'pw' } as never);
    const url = new URL(calls[0]!.url);
    expect(url.searchParams.get('slug')).toBe('acme');
  });

  it('INJECTS ?slug= for /customer-auth/signup', async () => {
    const { fetchFn, calls } = mockFetchSequence([
      { status: 201, body: { id: 'a', email: 'x@y.com' } },
    ]);
    const c = createAfiancoClient({ slug: 'acme', baseUrl: 'http://t', fetchFn });
    await c.customerAuth.signup({ email: 'x@y.com', password: 'pw', name: 'X' } as never);
    const url = new URL(calls[0]!.url);
    expect(url.searchParams.get('slug')).toBe('acme');
  });

  it('INJECTS ?slug= for /customer/me', async () => {
    const storage = new MemoryTokenStorage();
    storage.set('jwt');
    const { fetchFn, calls } = mockFetchSequence([
      { status: 200, body: { id: 'a', email: 'x@y.com', name: 'X', locale: 'it', email_verified: true, created_at: 'x' } },
    ]);
    const c = createAfiancoClient({ slug: 'acme', baseUrl: 'http://t', fetchFn, tokenStorage: storage });
    await c.customer.me();
    const url = new URL(calls[0]!.url);
    expect(url.searchParams.get('slug')).toBe('acme');
  });

  it('preserves user-provided query when injecting slug', async () => {
    // /cart/{cart_id} already passes query.slug → SDK should NOT duplicate
    const { fetchFn, calls } = mockFetchSequence([
      { status: 200, body: { id: 'c1', organization_id: 'o', items: [], item_count: 0, subtotal_snapshot: 0, created_at: 'x', updated_at: 'x', expires_at: 'x', source: 'embed' } },
    ]);
    const c = createAfiancoClient({ slug: 'acme', baseUrl: 'http://t', fetchFn });
    await c.embed.cart.get('cart_abc');
    const url = new URL(calls[0]!.url);
    // slug must be present exactly once (no double-append)
    expect(url.searchParams.getAll('slug')).toEqual(['acme']);
  });
});

describe('@afianco/api-client — error mapping', () => {
  it('maps 401 → AfiancoAuthError', async () => {
    const { fetchFn } = mockFetchSequence([{ status: 401, body: { detail: 'unauthorized' } }]);
    const c = createAfiancoClient({ slug: 'demo', baseUrl: 'http://t', fetchFn });
    await expect(c.customer.me()).rejects.toBeInstanceOf(AfiancoAuthError);
  });

  it('maps 403 → AfiancoAuthError', async () => {
    const { fetchFn } = mockFetchSequence([{ status: 403, body: { detail: 'forbidden' } }]);
    const c = createAfiancoClient({ slug: 'demo', baseUrl: 'http://t', fetchFn });
    await expect(c.customer.me()).rejects.toBeInstanceOf(AfiancoAuthError);
  });

  it('maps 400 with error code → AfiancoValidationError', async () => {
    const { fetchFn } = mockFetchSequence([
      { status: 400, body: { detail: { error: 'return_url_rejected', message: 'x' } } },
    ]);
    const c = createAfiancoClient({
      slug: 'demo',
      baseUrl: 'http://t',
      fetchFn,
      maxRetries: 0,
    });
    try {
      await c.embed.checkout.start({
        slug: 'demo',
        cart_id: 'c',
        customer_name: 'X',
        customer_email: 'x@y.com',
        embed_return_url: 'https://bad',
        gdpr_terms_accepted: true,
        gdpr_privacy_accepted: true,
        gdpr_marketing_accepted: false,
        terms_accepted: true,
      });
      expect.fail('should have thrown');
    } catch (e) {
      expect(e).toBeInstanceOf(AfiancoValidationError);
      expect((e as AfiancoValidationError).errorCode).toBe('return_url_rejected');
    }
  });

  it('maps 429 → AfiancoRateLimitError with Retry-After parsing', async () => {
    // Provide enough 429 responses so all retry attempts also see 429.
    const { fetchFn } = mockFetchSequence([
      { status: 429, body: { detail: 'rate limited' }, headers: { 'retry-after': '5' } },
      { status: 429, body: { detail: 'rate limited' }, headers: { 'retry-after': '5' } },
      { status: 429, body: { detail: 'rate limited' }, headers: { 'retry-after': '5' } },
      { status: 429, body: { detail: 'rate limited' }, headers: { 'retry-after': '5' } },
    ]);
    const c = createAfiancoClient({
      slug: 'demo',
      baseUrl: 'http://t',
      fetchFn,
      maxRetries: 0, // no retry per testare il throw immediato
    });
    try {
      await c.embed.getInit();
      expect.fail('should have thrown');
    } catch (e) {
      expect(e).toBeInstanceOf(AfiancoRateLimitError);
      expect((e as AfiancoRateLimitError).retryAfterSeconds).toBe(5);
    }
  });

  it('maps generic 5xx → AfiancoApiError', async () => {
    const { fetchFn } = mockFetchSequence([{ status: 500, body: { detail: 'oops' } }]);
    const c = createAfiancoClient({ slug: 'demo', baseUrl: 'http://t', fetchFn, maxRetries: 0 });
    try {
      await c.embed.getInit();
      expect.fail('should have thrown');
    } catch (e) {
      expect(e).toBeInstanceOf(AfiancoApiError);
      expect((e as AfiancoApiError).status).toBe(500);
    }
  });
});

describe('@afianco/api-client — retry behavior', () => {
  it('retries on 429 up to maxRetries then succeeds', async () => {
    // 2 × 429 followed by 200 success
    const { fetchFn, calls } = mockFetchSequence([
      { status: 429, body: { detail: 'rate' } },
      { status: 429, body: { detail: 'rate' } },
      { status: 200, body: { slug: 'demo', org_name: 'X' } },
    ]);
    const c = createAfiancoClient({
      slug: 'demo',
      baseUrl: 'http://t',
      fetchFn,
      maxRetries: 3,
    });
    // Speed up: replace backoff to 0
    const orig = (c as unknown as { backoff: () => Promise<void> }).backoff;
    (c as unknown as { backoff: () => Promise<void> }).backoff = () => Promise.resolve();
    try {
      const r = await c.embed.getInit();
      expect(r).toBeTruthy();
      expect(calls.length).toBe(3);
    } finally {
      (c as unknown as { backoff: typeof orig }).backoff = orig;
    }
  });
});

describe('@afianco/api-client — auth flows', () => {
  it('login stores the token in storage', async () => {
    const storage = new MemoryTokenStorage();
    const { fetchFn } = mockFetchSequence([
      {
        status: 200,
        body: {
          access_token: 'token-xyz',
          token_type: 'bearer',
          customer: {
            id: 'a', email: 'x@y.com', name: 'X',
            locale: 'it', email_verified: false, created_at: 'x',
          },
        },
      },
    ]);
    const c = createAfiancoClient({
      slug: 'demo',
      baseUrl: 'http://t',
      fetchFn,
      tokenStorage: storage,
    });
    await c.customerAuth.login({ slug: 'demo', email: 'x@y.com', password: 'p' });
    expect(storage.get()).toBe('token-xyz');
  });

  it('logout clears the token', async () => {
    const storage = new MemoryTokenStorage();
    storage.set('test-jwt');
    const c = createAfiancoClient({
      slug: 'demo',
      baseUrl: 'http://t',
      tokenStorage: storage,
    });
    c.customerAuth.logout();
    expect(storage.get()).toBeNull();
  });

  it('checkout.start with inline signup stores returned token', async () => {
    const storage = new MemoryTokenStorage();
    const { fetchFn } = mockFetchSequence([
      {
        status: 200,
        body: {
          order_id: 'ord_1',
          transaction_mode: 'request',
          order_status: 'draft',
          message: 'ok',
          embed_return_url: 'https://merchant.com/done',
          customer_access_token: 'new-token-after-signup',
          account_created: true,
        },
      },
    ]);
    const c = createAfiancoClient({
      slug: 'demo',
      baseUrl: 'http://t',
      fetchFn,
      tokenStorage: storage,
    });
    const resp = await c.embed.checkout.start({
      slug: 'demo',
      cart_id: 'cart_1',
      customer_name: 'X',
      customer_email: 'x@y.com',
      embed_return_url: 'https://merchant.com/done',
      gdpr_terms_accepted: true,
      gdpr_privacy_accepted: true,
      gdpr_marketing_accepted: false,
      terms_accepted: true,
      create_account: true,
      account_password: 'StrongPass!2026',
    });
    expect(resp.account_created).toBe(true);
    expect(storage.get()).toBe('new-token-after-signup');
  });

  it('cart.merge sends Authorization header', async () => {
    const storage = new MemoryTokenStorage();
    storage.set('cust-jwt');
    const { fetchFn, calls } = mockFetchSequence([
      {
        status: 200,
        body: {
          id: 'cart_1',
          organization_id: 'o',
          items: [],
          item_count: 0,
          subtotal_snapshot: 0,
          created_at: 'x',
          updated_at: 'x',
          expires_at: 'x',
          source: 'embed',
        },
      },
    ]);
    const c = createAfiancoClient({
      slug: 'demo',
      baseUrl: 'http://t',
      fetchFn,
      tokenStorage: storage,
    });
    await c.embed.cart.merge('cart_1', { customer_account_id: 'acc-1' });
    const headers = calls[0]!.init.headers as Record<string, string>;
    expect(headers['Authorization']).toBe('Bearer cust-jwt');
  });
});

describe('@afianco/api-client — credentials policy', () => {
  it('sets credentials: omit (no cookies cross-origin)', async () => {
    const { fetchFn, calls } = mockFetchSequence([
      { status: 200, body: { slug: 'demo', org_name: 'X' } },
    ]);
    const c = createAfiancoClient({ slug: 'demo', baseUrl: 'http://t', fetchFn });
    await c.embed.getInit();
    expect(calls[0]!.init.credentials).toBe('omit');
  });
});
