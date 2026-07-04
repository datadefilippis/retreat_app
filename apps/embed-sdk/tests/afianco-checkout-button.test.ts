/**
 * Sentinel tests for <afianco-checkout-button> — Phase 1 Step 26.
 *
 * Invariants pinned
 * =================
 *  INV-CB-1   Registered in customElements
 *  INV-CB-2   Public API: openWithCart / closeModal / submit
 *  INV-CB-3   Document listener afianco:checkout-requested attached/detached
 *  INV-CB-4   Form fields: name, email, phone, gdpr*, create_account, password
 *  INV-CB-5   Validation: missing name → error, no email → error, no gdpr → error
 *  INV-CB-6   Validation: create_account=true + short password → error
 *  INV-CB-7   submit() calls client.embed.checkout.start con payload corretto
 *  INV-CB-8   Direct mode (payment_checkout_url present) → opens window.open
 *  INV-CB-9   Request mode (no payment_url) → dispatches afianco:order-completed immediately
 *  INV-CB-10  postMessage afianco-embed source → dispatch afianco:order-completed
 *  INV-CB-11  postMessage from wrong origin → ignored
 *  INV-CB-12  On order-completed → cart_id rimosso da localStorage
 *  INV-CB-13  Shadow DOM presente
 *  INV-CB-14  Inline signup includes password in body
 *  INV-CB-15  return-url attribute overrides default window.location
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { AfiancoCheckoutButton } from '../src/components/afianco-checkout-button.js';
import type {
  AfiancoClient,
  CartResponse,
  EmbedCheckoutStartRequest,
  EmbedCheckoutStartResponse,
} from '@afianco/api-client';
import type { StorefrontContext } from '../src/context.js';

function makeCart(overrides: Partial<CartResponse> = {}): CartResponse {
  return {
    id: 'cart_co_1',
    organization_id: 'org-1',
    items: [],
    item_count: 1,
    subtotal_snapshot: 10,
    currency_snapshot: 'EUR',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    expires_at: '2026-03-01T00:00:00Z',
    source: 'embed',
    ...overrides,
  };
}

interface MockState {
  startCalls: EmbedCheckoutStartRequest[];
  response: EmbedCheckoutStartResponse;
}

function makeMockClient(
  resp: Partial<EmbedCheckoutStartResponse> = {},
): { client: AfiancoClient; state: MockState } {
  const state: MockState = {
    startCalls: [],
    response: {
      order_id: 'ord_test_1',
      transaction_mode: 'direct',
      order_status: 'draft',
      message: 'ok',
      embed_return_url: 'http://test/return',
      account_created: false,
      ...resp,
    },
  };
  const client = {
    slug: 'demo',
    baseUrl: 'http://test-backend',
    embed: {
      checkout: {
        start: async (body: EmbedCheckoutStartRequest) => {
          state.startCalls.push(body);
          return state.response;
        },
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

async function mountCheckout(ctx: StorefrontContext): Promise<AfiancoCheckoutButton> {
  const el = document.createElement('afianco-checkout-button') as AfiancoCheckoutButton;
  el.ctx = ctx;
  document.body.appendChild(el);
  await el.updateComplete;
  return el;
}

const STORAGE_PREFIX = 'afianco_cart_id_';

describe('<afianco-checkout-button>', () => {
  beforeEach(() => {
    try {
      Object.keys(localStorage)
        .filter((k) => k.startsWith(STORAGE_PREFIX))
        .forEach((k) => localStorage.removeItem(k));
    } catch {
      // ignore
    }
  });

  afterEach(() => {
    document
      .querySelectorAll('afianco-checkout-button')
      .forEach((el) => el.remove());
  });

  it('INV-CB-1 — registered in customElements', () => {
    expect(customElements.get('afianco-checkout-button')).toBe(AfiancoCheckoutButton);
  });

  it('INV-CB-13 — uses Shadow DOM', async () => {
    const { client } = makeMockClient();
    const el = await mountCheckout(readyContext(client));
    expect(el.shadowRoot).not.toBeNull();
  });

  it('INV-CB-2 — public API: openWithCart / closeModal / submit', () => {
    const el = document.createElement('afianco-checkout-button') as AfiancoCheckoutButton;
    expect(typeof el.openWithCart).toBe('function');
    expect(typeof el.closeModal).toBe('function');
    expect(typeof el.submit).toBe('function');
  });

  it('renders nothing until openWithCart is called', async () => {
    const { client } = makeMockClient();
    const el = await mountCheckout(readyContext(client));
    const innerHTML = el.shadowRoot?.innerHTML ?? '';
    expect(innerHTML.includes('Completa')).toBe(false);
    el.openWithCart(makeCart());
    await el.updateComplete;
    expect(el.shadowRoot?.textContent ?? '').toContain('Completa');
  });

  it('INV-CB-4 — form has name, email, phone, gdpr*, password fields when create_account=true', async () => {
    const { client } = makeMockClient();
    const el = await mountCheckout(readyContext(client));
    el.openWithCart(makeCart());
    await el.updateComplete;
    expect(el.shadowRoot?.querySelector('#afianco-name')).toBeTruthy();
    expect(el.shadowRoot?.querySelector('#afianco-email')).toBeTruthy();
    expect(el.shadowRoot?.querySelector('#afianco-phone')).toBeTruthy();
    expect(el.shadowRoot?.querySelector('#afianco-gdpr-privacy')).toBeTruthy();
    expect(el.shadowRoot?.querySelector('#afianco-gdpr-terms')).toBeTruthy();
    expect(el.shadowRoot?.querySelector('#afianco-gdpr-marketing')).toBeTruthy();
    // password not rendered until createAccount=true
    expect(el.shadowRoot?.querySelector('#afianco-password')).toBeFalsy();
    (el as unknown as { createAccount: boolean }).createAccount = true;
    await el.updateComplete;
    expect(el.shadowRoot?.querySelector('#afianco-password')).toBeTruthy();
  });

  it('INV-CB-5 — validation: empty name → error', async () => {
    const { client, state } = makeMockClient();
    const el = await mountCheckout(readyContext(client));
    el.openWithCart(makeCart());
    await el.submit();
    expect(state.startCalls.length).toBe(0);
    const text = el.shadowRoot?.textContent ?? '';
    expect(text).toMatch(/nome/i);
  });

  it('INV-CB-5 — validation: invalid email → error', async () => {
    const { client, state } = makeMockClient();
    const el = await mountCheckout(readyContext(client));
    el.openWithCart(makeCart());
    (el as unknown as { name: string }).name = 'Mario';
    (el as unknown as { email: string }).email = 'not-an-email';
    (el as unknown as { gdprPrivacy: boolean }).gdprPrivacy = true;
    (el as unknown as { gdprTerms: boolean }).gdprTerms = true;
    await el.submit();
    expect(state.startCalls.length).toBe(0);
    const text = el.shadowRoot?.textContent ?? '';
    expect(text).toMatch(/email/i);
  });

  it('INV-CB-5 — validation: missing gdpr → error', async () => {
    const { client, state } = makeMockClient();
    const el = await mountCheckout(readyContext(client));
    el.openWithCart(makeCart());
    (el as unknown as { name: string }).name = 'Mario';
    (el as unknown as { email: string }).email = 'mario@example.com';
    // No gdpr
    await el.submit();
    expect(state.startCalls.length).toBe(0);
    const text = el.shadowRoot?.textContent ?? '';
    expect(text).toMatch(/Privacy/i);
  });

  it('INV-CB-6 — validation: create_account + short password → error', async () => {
    const { client, state } = makeMockClient();
    const el = await mountCheckout(readyContext(client));
    el.openWithCart(makeCart());
    (el as unknown as { name: string }).name = 'Mario';
    (el as unknown as { email: string }).email = 'mario@example.com';
    (el as unknown as { gdprPrivacy: boolean }).gdprPrivacy = true;
    (el as unknown as { gdprTerms: boolean }).gdprTerms = true;
    (el as unknown as { createAccount: boolean }).createAccount = true;
    (el as unknown as { password: string }).password = 'short';
    await el.submit();
    expect(state.startCalls.length).toBe(0);
    const text = el.shadowRoot?.textContent ?? '';
    expect(text).toMatch(/8/);
  });

  it('INV-CB-7 — submit() calls client.embed.checkout.start con payload corretto', async () => {
    const { client, state } = makeMockClient();
    const el = await mountCheckout(readyContext(client));
    el.openWithCart(makeCart({ id: 'cart_abc' }));
    (el as unknown as { name: string }).name = 'Mario';
    (el as unknown as { email: string }).email = 'mario@example.com';
    (el as unknown as { phone: string }).phone = '+390000000000';
    (el as unknown as { gdprPrivacy: boolean }).gdprPrivacy = true;
    (el as unknown as { gdprTerms: boolean }).gdprTerms = true;
    (el as unknown as { gdprMarketing: boolean }).gdprMarketing = true;
    // Replace window.open to avoid popup pollution
    const origOpen = window.open;
    window.open = (() => ({ closed: false, close: () => {} })) as unknown as typeof window.open;
    await el.submit();
    window.open = origOpen;
    expect(state.startCalls.length).toBe(1);
    const body = state.startCalls[0]!;
    expect(body.cart_id).toBe('cart_abc');
    expect(body.customer_name).toBe('Mario');
    expect(body.customer_email).toBe('mario@example.com');
    expect(body.customer_phone).toBe('+390000000000');
    expect(body.gdpr_privacy_accepted).toBe(true);
    expect(body.gdpr_terms_accepted).toBe(true);
    expect(body.gdpr_marketing_accepted).toBe(true);
    expect(body.terms_accepted).toBe(true);
    expect(body.create_account).toBeUndefined();
  });

  it('INV-CB-14 — inline signup: body has create_account + account_password', async () => {
    const { client, state } = makeMockClient();
    const el = await mountCheckout(readyContext(client));
    el.openWithCart(makeCart());
    (el as unknown as { name: string }).name = 'Mario';
    (el as unknown as { email: string }).email = 'mario@example.com';
    (el as unknown as { gdprPrivacy: boolean }).gdprPrivacy = true;
    (el as unknown as { gdprTerms: boolean }).gdprTerms = true;
    (el as unknown as { createAccount: boolean }).createAccount = true;
    (el as unknown as { password: string }).password = 'StrongPass!2026';
    const origOpen = window.open;
    window.open = (() => ({ closed: false, close: () => {} })) as unknown as typeof window.open;
    await el.submit();
    window.open = origOpen;
    expect(state.startCalls.length).toBe(1);
    const body = state.startCalls[0]!;
    expect(body.create_account).toBe(true);
    expect(body.account_password).toBe('StrongPass!2026');
    expect(body.account_locale).toBe('it');
  });

  it('INV-CB-8 — direct mode: opens window.open with payment_checkout_url', async () => {
    const { client } = makeMockClient({
      transaction_mode: 'direct',
      payment_checkout_url: 'https://checkout.stripe.com/c/abc',
    });
    const el = await mountCheckout(readyContext(client));
    el.openWithCart(makeCart());
    (el as unknown as { name: string }).name = 'Mario';
    (el as unknown as { email: string }).email = 'mario@example.com';
    (el as unknown as { gdprPrivacy: boolean }).gdprPrivacy = true;
    (el as unknown as { gdprTerms: boolean }).gdprTerms = true;
    let openedUrl: string | URL | undefined;
    const origOpen = window.open;
    window.open = ((url?: string | URL) => {
      openedUrl = url;
      return { closed: false, close: () => {} } as unknown as Window;
    }) as unknown as typeof window.open;
    await el.submit();
    window.open = origOpen;
    expect(openedUrl).toBe('https://checkout.stripe.com/c/abc');
  });

  it('INV-CB-9 — request mode (no payment_url) → afianco:order-completed immediately', async () => {
    const { client } = makeMockClient({
      transaction_mode: 'request',
      payment_checkout_url: null,
      order_id: 'ord_req_1',
    });
    const el = await mountCheckout(readyContext(client));
    let completedDetail: { order_id: string } | null = null;
    el.addEventListener('afianco:order-completed', (e) => {
      completedDetail = (e as CustomEvent<{ order_id: string }>).detail;
    });
    el.openWithCart(makeCart());
    (el as unknown as { name: string }).name = 'Mario';
    (el as unknown as { email: string }).email = 'mario@example.com';
    (el as unknown as { gdprPrivacy: boolean }).gdprPrivacy = true;
    (el as unknown as { gdprTerms: boolean }).gdprTerms = true;
    await el.submit();
    expect(completedDetail).toBeTruthy();
    expect(completedDetail!.order_id).toBe('ord_req_1');
  });

  it('INV-CB-10 — postMessage afianco-embed source dispatcha afianco:order-completed', async () => {
    const { client } = makeMockClient();
    const el = await mountCheckout(readyContext(client));
    let detail: { order_id: string; order_status: string } | null = null;
    el.addEventListener('afianco:order-completed', (e) => {
      detail = (e as CustomEvent<{ order_id: string; order_status: string }>).detail;
    });
    // Backend origin matching our mock (test-backend)
    window.dispatchEvent(
      new MessageEvent('message', {
        data: {
          source: 'afianco-embed',
          type: 'checkout_complete',
          order_id: 'ord_pm_1',
          order_status: 'confirmed',
          payment_status: 'collected',
        },
        origin: 'http://test-backend',
      }),
    );
    await el.updateComplete;
    expect(detail).toBeTruthy();
    expect(detail!.order_id).toBe('ord_pm_1');
    expect(detail!.order_status).toBe('confirmed');
  });

  it('INV-CB-11 — postMessage from wrong origin → ignored', async () => {
    const { client } = makeMockClient();
    const el = await mountCheckout(readyContext(client));
    let fired = false;
    el.addEventListener('afianco:order-completed', () => {
      fired = true;
    });
    window.dispatchEvent(
      new MessageEvent('message', {
        data: {
          source: 'afianco-embed',
          type: 'checkout_complete',
          order_id: 'malicious',
          order_status: 'confirmed',
          payment_status: 'collected',
        },
        origin: 'https://evil.example.com',
      }),
    );
    await el.updateComplete;
    expect(fired).toBe(false);
  });

  it('INV-CB-12 — order-completed → cart_id rimosso da localStorage', async () => {
    localStorage.setItem(`${STORAGE_PREFIX}demo`, 'cart_to_clear');
    const { client } = makeMockClient();
    const el = await mountCheckout(readyContext(client));
    window.dispatchEvent(
      new MessageEvent('message', {
        data: {
          source: 'afianco-embed',
          type: 'checkout_complete',
          order_id: 'ord_x',
          order_status: 'confirmed',
          payment_status: 'collected',
        },
        origin: 'http://test-backend',
      }),
    );
    await el.updateComplete;
    expect(localStorage.getItem(`${STORAGE_PREFIX}demo`)).toBeNull();
  });

  it('INV-CB-15 — return-url attribute overrides default', async () => {
    const { client, state } = makeMockClient();
    const el = await mountCheckout(readyContext(client));
    el.returnUrl = 'https://merchant.com/order-done';
    el.openWithCart(makeCart());
    (el as unknown as { name: string }).name = 'Mario';
    (el as unknown as { email: string }).email = 'mario@example.com';
    (el as unknown as { gdprPrivacy: boolean }).gdprPrivacy = true;
    (el as unknown as { gdprTerms: boolean }).gdprTerms = true;
    const origOpen = window.open;
    window.open = (() => ({ closed: false, close: () => {} })) as unknown as typeof window.open;
    await el.submit();
    window.open = origOpen;
    expect(state.startCalls[0]?.embed_return_url).toBe('https://merchant.com/order-done');
  });

  it('INV-CB-3 — document listener attaches afianco:checkout-requested', async () => {
    const { client } = makeMockClient();
    const el = await mountCheckout(readyContext(client));
    // Simulate event
    document.dispatchEvent(
      new CustomEvent('afianco:checkout-requested', {
        detail: { cart_id: 'cart_x', cart: makeCart({ id: 'cart_x' }) },
        bubbles: true,
        composed: true,
      }),
    );
    await el.updateComplete;
    expect(el.shadowRoot?.textContent ?? '').toContain('Completa');
  });

  it('removes document listener on disconnect', async () => {
    const { client } = makeMockClient();
    const el = await mountCheckout(readyContext(client));
    // Verify listener attached at mount
    expect((el as unknown as { _checkoutListenerAttached: boolean })._checkoutListenerAttached).toBe(true);
    // Detach via disconnect
    document.body.removeChild(el);
    expect((el as unknown as { _checkoutListenerAttached: boolean })._checkoutListenerAttached).toBe(false);
  });
});
