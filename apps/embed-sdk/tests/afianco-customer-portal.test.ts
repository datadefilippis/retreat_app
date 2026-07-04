/**
 * Sentinel tests for <afianco-customer-portal> — Phase 1 Step 28.
 *
 * Invariants pinned
 * =================
 *  INV-CP-1   Registered in customElements
 *  INV-CP-2   Shadow DOM isolated
 *  INV-CP-3   No token → auth-required event + auth prompt rendered
 *  INV-CP-4   With token → fetchProfile chiamato + profile rendered
 *  INV-CP-5   Profile tab shows name, email, locale, created_at
 *  INV-CP-6   email_verified flag → badge "verificata" vs "non verificata"
 *  INV-CP-7   Orders tab → fetchOrders chiamato lazy al primo click
 *  INV-CP-8   Empty orders → empty-state messaggio
 *  INV-CP-9   Orders renderizzano numero ordine + total + status
 *  INV-CP-10  initial-tab="orders" → orders tab attivo al mount
 *  INV-CP-11  Logout → token cleared + afianco:portal-logout event
 *  INV-CP-12  AfiancoAuthError on me() → token cleared + auth-required
 *  INV-CP-13  show-logout=false nasconde il bottone Esci
 *  INV-CP-14  afianco:portal-loaded event dispatched dopo profile fetch
 *  INV-CP-15  Auth-prompt CTA dispatcha auth-action {show-login}
 */

import { describe, it, expect, afterEach, vi } from 'vitest';
import { AfiancoCustomerPortal } from '../src/components/afianco-customer-portal.js';
import {
  AfiancoAuthError,
  type AfiancoClient,
  type CustomerProfile,
  type CustomerOrderSummary,
} from '@afianco/api-client';
import type { StorefrontContext } from '../src/context.js';

interface MockState {
  token: string | null;
  meCallCount: number;
  ordersCallCount: number;
  logoutCallCount: number;
}

interface MockOpts {
  initialToken?: string | null;
  profile?: CustomerProfile;
  orders?: CustomerOrderSummary[];
  meThrows?: Error;
  ordersThrows?: Error;
}

function mockProfile(overrides: Partial<CustomerProfile> = {}): CustomerProfile {
  return {
    id: 'cust_1',
    email: 'mario@example.com',
    name: 'Mario Rossi',
    locale: 'it',
    email_verified: true,
    phone: null,
    accepted_marketing: false,
    created_at: '2026-01-15T10:30:00Z',
    ...overrides,
  };
}

function mockOrder(overrides: Partial<CustomerOrderSummary> = {}): CustomerOrderSummary {
  return {
    id: 'ord_abc12345',
    order_number: 'A-001',
    order_status: 'confirmed',
    payment_intent: 'collected',
    total: 42.5,
    currency: 'EUR',
    created_at: '2026-02-10T14:00:00Z',
    ...overrides,
  };
}

function makeMockClient(opts: MockOpts = {}): {
  client: AfiancoClient;
  state: MockState;
} {
  const state: MockState = {
    token: opts.initialToken ?? null,
    meCallCount: 0,
    ordersCallCount: 0,
    logoutCallCount: 0,
  };
  const client = {
    slug: 'demo',
    tokenStorage: {
      get: () => state.token,
      set: (t: string) => {
        state.token = t;
      },
      clear: () => {
        state.token = null;
      },
    },
    customer: {
      me: async () => {
        state.meCallCount += 1;
        if (opts.meThrows) throw opts.meThrows;
        return opts.profile ?? mockProfile();
      },
      orders: async () => {
        state.ordersCallCount += 1;
        if (opts.ordersThrows) throw opts.ordersThrows;
        return opts.orders ?? [];
      },
    },
    customerAuth: {
      logout: () => {
        state.logoutCallCount += 1;
        state.token = null;
      },
    },
  } as unknown as AfiancoClient;
  return { client, state };
}

function readyContext(client: AfiancoClient): StorefrontContext {
  return {
    client,
    init: {
      slug: 'demo',
      org_name: 'Demo',
      currency: 'EUR',
      storefront_languages: ['it'],
      available_product_types: ['physical'],
      categories: [],
      capabilities: {
        checkout_stripe_enabled: true,
        cart_enabled: true,
        customer_auth_enabled: true,
      },
      fulfillment_modes: ['shipping'],
    },
    status: 'ready',
    error: null,
  };
}

async function mountPortal(
  ctx: StorefrontContext,
  attrs: Record<string, string | boolean> = {},
): Promise<AfiancoCustomerPortal> {
  const el = document.createElement('afianco-customer-portal') as AfiancoCustomerPortal;
  el.ctx = ctx;
  for (const [k, v] of Object.entries(attrs)) {
    if (typeof v === 'boolean') {
      if (v) el.setAttribute(k, '');
    } else {
      el.setAttribute(k, v);
    }
  }
  document.body.appendChild(el);
  await el.updateComplete;
  // Wait one microtask flush for bootstrap()
  await new Promise((r) => setTimeout(r, 0));
  await el.updateComplete;
  return el;
}

describe('<afianco-customer-portal>', () => {
  afterEach(() => {
    document.querySelectorAll('afianco-customer-portal').forEach((e) => e.remove());
    vi.restoreAllMocks();
  });

  it('INV-CP-1 — registered in customElements', () => {
    expect(customElements.get('afianco-customer-portal')).toBe(AfiancoCustomerPortal);
  });

  it('INV-CP-2 — uses Shadow DOM', async () => {
    const { client } = makeMockClient({ initialToken: 'tok' });
    const el = await mountPortal(readyContext(client));
    expect(el.shadowRoot).not.toBeNull();
  });

  it('INV-CP-3 — no token → auth-required event + prompt rendered', async () => {
    const { client, state } = makeMockClient({ initialToken: null });
    let fired = false;
    const ctx = readyContext(client);
    const el = document.createElement('afianco-customer-portal') as AfiancoCustomerPortal;
    el.ctx = ctx;
    el.addEventListener('afianco:auth-required', () => {
      fired = true;
    });
    document.body.appendChild(el);
    await el.updateComplete;
    await new Promise((r) => setTimeout(r, 0));
    await el.updateComplete;
    expect(fired).toBe(true);
    expect(state.meCallCount).toBe(0);
    const text = el.shadowRoot?.textContent ?? '';
    expect(text).toMatch(/accedi/i);
  });

  it('INV-CP-4 — with token → fetchProfile called + profile rendered', async () => {
    const { client, state } = makeMockClient({
      initialToken: 'tok',
      profile: mockProfile({ name: 'Anna Bianchi' }),
    });
    const el = await mountPortal(readyContext(client));
    expect(state.meCallCount).toBe(1);
    expect(el.shadowRoot?.textContent ?? '').toMatch(/Anna Bianchi/);
  });

  it('INV-CP-5 — profile tab shows name, email, locale, created_at', async () => {
    const { client } = makeMockClient({
      initialToken: 'tok',
      profile: mockProfile({
        name: 'Test User',
        email: 'test@x.it',
        locale: 'it',
        created_at: '2026-03-01T00:00:00Z',
      }),
    });
    const el = await mountPortal(readyContext(client));
    const text = el.shadowRoot?.textContent ?? '';
    expect(text).toMatch(/Test User/);
    expect(text).toMatch(/test@x\.it/);
    // Verify both row labels are rendered. La formattazione data dipende
    // dalla ICU disponibile nel runtime (happy-dom puo' essere minimal).
    expect(text).toMatch(/Lingua/);
    expect(text).toMatch(/Iscritto dal/);
  });

  it('INV-CP-6 — email_verified=true → badge "verificata"', async () => {
    const { client } = makeMockClient({
      initialToken: 'tok',
      profile: mockProfile({ email_verified: true }),
    });
    const el = await mountPortal(readyContext(client));
    expect(el.shadowRoot?.textContent ?? '').toMatch(/verificata/);
    expect(el.shadowRoot?.textContent ?? '').not.toMatch(/non verificata/);
  });

  it('INV-CP-6b — email_verified=false → badge "non verificata"', async () => {
    const { client } = makeMockClient({
      initialToken: 'tok',
      profile: mockProfile({ email_verified: false }),
    });
    const el = await mountPortal(readyContext(client));
    expect(el.shadowRoot?.textContent ?? '').toMatch(/non verificata/);
  });

  it('INV-CP-7 — orders tab lazy-fetches on first click', async () => {
    const { client, state } = makeMockClient({
      initialToken: 'tok',
      orders: [mockOrder()],
    });
    const el = await mountPortal(readyContext(client));
    // At mount default tab is "profile" → orders not fetched
    expect(state.ordersCallCount).toBe(0);
    // Click orders tab
    el.selectTab('orders');
    await el.updateComplete;
    await new Promise((r) => setTimeout(r, 0));
    await el.updateComplete;
    expect(state.ordersCallCount).toBe(1);
  });

  it('INV-CP-8 — empty orders → empty-state messaggio', async () => {
    const { client } = makeMockClient({
      initialToken: 'tok',
      orders: [],
    });
    const el = await mountPortal(readyContext(client));
    el.selectTab('orders');
    await el.updateComplete;
    await new Promise((r) => setTimeout(r, 0));
    await el.updateComplete;
    expect(el.shadowRoot?.textContent ?? '').toMatch(/non hai ancora effettuato ordini/i);
  });

  it('INV-CP-9 — orders render: numero ordine + total + status', async () => {
    const { client } = makeMockClient({
      initialToken: 'tok',
      orders: [
        mockOrder({
          order_number: 'A-042',
          total: 99.99,
          currency: 'EUR',
          order_status: 'fulfilled',
        }),
      ],
    });
    const el = await mountPortal(readyContext(client));
    el.selectTab('orders');
    await el.updateComplete;
    await new Promise((r) => setTimeout(r, 0));
    await el.updateComplete;
    const text = el.shadowRoot?.textContent ?? '';
    expect(text).toMatch(/A-042/);
    expect(text).toMatch(/99[,.]99/);
    expect(text).toMatch(/fulfilled/);
  });

  it('INV-CP-10 — initial-tab="orders" → orders attivo al mount', async () => {
    const { client, state } = makeMockClient({
      initialToken: 'tok',
      orders: [mockOrder()],
    });
    const el = await mountPortal(readyContext(client), { 'initial-tab': 'orders' });
    expect(state.ordersCallCount).toBeGreaterThanOrEqual(1);
    const activeTab = el.shadowRoot?.querySelector('button[aria-selected="true"]');
    expect(activeTab?.textContent?.trim()).toBe('Ordini');
  });

  it('INV-CP-11 — logout → token cleared + portal-logout event', async () => {
    const { client, state } = makeMockClient({
      initialToken: 'tok',
      profile: mockProfile({ id: 'cust_xyz' }),
    });
    const el = await mountPortal(readyContext(client));
    let detail: { customer_id: string | null } | null = null;
    el.addEventListener('afianco:portal-logout', (e) => {
      detail = (e as CustomEvent<{ customer_id: string | null }>).detail;
    });
    el.logout();
    await el.updateComplete;
    expect(state.logoutCallCount).toBe(1);
    expect(state.token).toBeNull();
    expect(detail).toMatchObject({ customer_id: 'cust_xyz' });
    // Render dovrebbe ora mostrare il prompt auth
    expect(el.shadowRoot?.textContent ?? '').toMatch(/accedi/i);
  });

  it('INV-CP-12 — AuthError on me() → token cleared + auth-required', async () => {
    const { client, state } = makeMockClient({
      initialToken: 'expired_tok',
      meThrows: new AfiancoAuthError(401, { detail: 'expired' }),
    });
    let fired = false;
    const ctx = readyContext(client);
    const el = document.createElement('afianco-customer-portal') as AfiancoCustomerPortal;
    el.ctx = ctx;
    el.addEventListener('afianco:auth-required', () => {
      fired = true;
    });
    document.body.appendChild(el);
    await el.updateComplete;
    await new Promise((r) => setTimeout(r, 0));
    await el.updateComplete;
    expect(state.logoutCallCount).toBe(1);
    expect(state.token).toBeNull();
    expect(fired).toBe(true);
  });

  it('INV-CP-13 — show-logout=false nasconde il bottone Esci', async () => {
    const { client } = makeMockClient({ initialToken: 'tok' });
    const el = document.createElement('afianco-customer-portal') as AfiancoCustomerPortal;
    el.ctx = readyContext(client);
    el.showLogout = false;
    document.body.appendChild(el);
    await el.updateComplete;
    await new Promise((r) => setTimeout(r, 0));
    await el.updateComplete;
    const logoutBtn = el.shadowRoot?.querySelector('.logout-btn');
    expect(logoutBtn).toBeFalsy();
  });

  it('INV-CP-14 — afianco:portal-loaded event dopo profile fetch', async () => {
    const { client } = makeMockClient({
      initialToken: 'tok',
      profile: mockProfile({ id: 'cust_loaded' }),
    });
    let detail: { profile: CustomerProfile; ordersCount: number | null } | null = null;
    const ctx = readyContext(client);
    const el = document.createElement('afianco-customer-portal') as AfiancoCustomerPortal;
    el.ctx = ctx;
    el.addEventListener('afianco:portal-loaded', (e) => {
      detail = (e as CustomEvent<{
        profile: CustomerProfile;
        ordersCount: number | null;
      }>).detail;
    });
    document.body.appendChild(el);
    await el.updateComplete;
    await new Promise((r) => setTimeout(r, 0));
    await el.updateComplete;
    expect(detail).toBeTruthy();
    expect(detail!.profile.id).toBe('cust_loaded');
    expect(detail!.ordersCount).toBeNull();
  });

  it('INV-CP-15 — auth-prompt CTA dispatcha auth-action {show-login}', async () => {
    const { client } = makeMockClient({ initialToken: null });
    const el = await mountPortal(readyContext(client));
    let actionDetail: { action: string } | null = null;
    el.addEventListener('afianco:auth-action', (e) => {
      actionDetail = (e as CustomEvent<{ action: string }>).detail;
    });
    const btn = el.shadowRoot?.querySelector('.auth-btn') as HTMLButtonElement | null;
    expect(btn).toBeTruthy();
    btn!.click();
    expect(actionDetail).toMatchObject({ action: 'show-login' });
  });
});
