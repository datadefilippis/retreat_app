/**
 * Sentinel tests for <afianco-storefront-init> — Phase 1 Step 22.
 *
 * Bootstrap component che chiama /embed/init e provvede contesto Lit
 * ai child components.
 *
 * Invariants pinned
 * =================
 *  INV-SI-1   Registered in customElements registry
 *  INV-SI-2   Missing slug → status=error
 *  INV-SI-3   Loading skeleton mostrato prima del fetch
 *  INV-SI-4   Successful init → status=ready + contextValue popolato
 *  INV-SI-5   Failed init → status=error + custom event afianco:init-error
 *  INV-SI-6   Brand colors da init.store_info applicati come CSS vars
 *  INV-SI-7   Custom event afianco:init-ready fired on success
 *  INV-SI-8   noAutoInit attribute → init() non chiamato in firstUpdated
 *  INV-SI-9   Shadow DOM presente (CSS isolation)
 */

import { describe, it, expect, beforeAll, vi, type Mock } from 'vitest';
import { AfiancoStorefrontInit } from '../src/components/afianco-storefront-init.js';
import { STOREFRONT_INITIAL } from '../src/context.js';

beforeAll(() => {
  // Patch global fetch — mocked per test
  if (!('fetch' in globalThis)) {
    (globalThis as Record<string, unknown>).fetch = () => Promise.reject(new Error('no fetch'));
  }
});

function mockSuccessfulInit(): void {
  (globalThis as Record<string, unknown>).fetch = vi.fn(async () => {
    return new Response(
      JSON.stringify({
        slug: 'demo',
        org_name: 'Demo Store',
        currency: 'EUR',
        storefront_languages: ['it'],
        available_product_types: ['physical', 'service'],
        categories: [{ name: 'A', slug: 'a', count: 1 }],
        capabilities: {
          checkout_stripe_enabled: true,
          cart_enabled: true,
          customer_auth_enabled: true,
        },
        fulfillment_modes: ['shipping'],
        store_info: {
          display_name: 'Demo',
          brand_color: '#ff5500',
          brand_color_text: '#ffffff',
        },
      }),
      { status: 200, headers: { 'content-type': 'application/json' } },
    );
  });
}

function mockFailingInit(status: number, body = 'oops'): void {
  (globalThis as Record<string, unknown>).fetch = vi.fn(async () => {
    return new Response(JSON.stringify({ detail: body }), {
      status,
      headers: { 'content-type': 'application/json' },
    });
  });
}

describe('<afianco-storefront-init>', () => {
  it('INV-SI-1 — is registered in customElements', () => {
    const ctor = customElements.get('afianco-storefront-init');
    expect(ctor).toBeDefined();
    expect(ctor).toBe(AfiancoStorefrontInit);
  });

  it('createElement returns AfiancoStorefrontInit instance', () => {
    const el = document.createElement('afianco-storefront-init');
    expect(el).toBeInstanceOf(AfiancoStorefrontInit);
  });

  it('INV-SI-9 — uses Shadow DOM for isolation', async () => {
    const el = document.createElement('afianco-storefront-init') as AfiancoStorefrontInit;
    el.noAutoInit = true;
    el.slug = 'demo';
    document.body.appendChild(el);
    await el.updateComplete;
    expect(el.shadowRoot).not.toBeNull();
    document.body.removeChild(el);
  });

  it('INV-SI-3 — shows loading skeleton initially', async () => {
    const el = document.createElement('afianco-storefront-init') as AfiancoStorefrontInit;
    el.noAutoInit = true;
    el.slug = 'demo';
    document.body.appendChild(el);
    await el.updateComplete;
    const text = el.shadowRoot?.textContent ?? '';
    expect(text.toLowerCase()).toContain('loading');
    document.body.removeChild(el);
  });

  it('INV-SI-2 — missing slug → status=error + init-error event', async () => {
    const el = document.createElement('afianco-storefront-init') as AfiancoStorefrontInit;
    el.noAutoInit = true; // skip auto, we call init manually
    document.body.appendChild(el);
    await el.updateComplete;

    let errorMsg: string | null = null;
    el.addEventListener('afianco:init-error', (e) => {
      errorMsg = (e as CustomEvent<{ message: string }>).detail.message;
    });

    await el.init();
    await el.updateComplete;

    expect(el.contextValue.status).toBe('error');
    expect(errorMsg).toBeTruthy();
    document.body.removeChild(el);
  });

  it('INV-SI-4 + INV-SI-7 — successful init → ready + event', async () => {
    mockSuccessfulInit();

    const el = document.createElement('afianco-storefront-init') as AfiancoStorefrontInit;
    el.noAutoInit = true;
    el.slug = 'demo';
    el.baseUrl = 'http://test';
    document.body.appendChild(el);
    await el.updateComplete;

    let receivedDetail: unknown = null;
    el.addEventListener('afianco:init-ready', (e) => {
      receivedDetail = (e as CustomEvent).detail;
    });

    await el.init();
    await el.updateComplete;

    expect(el.contextValue.status).toBe('ready');
    expect(el.contextValue.init).toBeTruthy();
    expect(el.contextValue.init?.org_name).toBe('Demo Store');
    expect(el.contextValue.client).not.toBeNull();
    expect(receivedDetail).toBeTruthy();
    expect((receivedDetail as { org_name: string }).org_name).toBe('Demo Store');

    document.body.removeChild(el);
  });

  it('INV-SI-6 — brand colors applied as CSS variables on host', async () => {
    mockSuccessfulInit();

    const el = document.createElement('afianco-storefront-init') as AfiancoStorefrontInit;
    el.noAutoInit = true;
    el.slug = 'demo';
    el.baseUrl = 'http://test';
    document.body.appendChild(el);
    await el.init();
    await el.updateComplete;

    expect(el.style.getPropertyValue('--afianco-color-primary')).toBe('#ff5500');
    expect(el.style.getPropertyValue('--afianco-color-primary-text')).toBe('#ffffff');

    document.body.removeChild(el);
  });

  it('INV-SI-5 — failing init → status=error + init-error event', async () => {
    mockFailingInit(500, 'server down');

    const el = document.createElement('afianco-storefront-init') as AfiancoStorefrontInit;
    el.noAutoInit = true;
    el.slug = 'demo';
    el.baseUrl = 'http://test';
    document.body.appendChild(el);

    let errorReceived = false;
    el.addEventListener('afianco:init-error', () => {
      errorReceived = true;
    });

    await el.init();
    await el.updateComplete;

    expect(el.contextValue.status).toBe('error');
    expect(errorReceived).toBe(true);

    document.body.removeChild(el);
  });

  it('INV-SI-8 — noAutoInit prevents auto-init in firstUpdated', async () => {
    let fetchCalled = false;
    (globalThis as Record<string, unknown>).fetch = vi.fn(async () => {
      fetchCalled = true;
      return new Response('{}', { status: 200, headers: { 'content-type': 'application/json' } });
    });

    const el = document.createElement('afianco-storefront-init') as AfiancoStorefrontInit;
    el.noAutoInit = true;
    el.slug = 'demo';
    document.body.appendChild(el);
    await el.updateComplete;

    expect(fetchCalled).toBe(false);
    document.body.removeChild(el);
  });

  it('STOREFRONT_INITIAL has loading status', () => {
    expect(STOREFRONT_INITIAL.status).toBe('loading');
    expect(STOREFRONT_INITIAL.client).toBeNull();
    expect(STOREFRONT_INITIAL.init).toBeNull();
  });

  it('exports the context handle', async () => {
    const mod = await import('../src/index.js');
    expect(mod.storefrontContext).toBeDefined();
  });
});
