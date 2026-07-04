/**
 * Sentinel tests for <afianco-login> — Phase 1 Step 27.
 *
 * Invariants pinned
 * =================
 *  INV-LO-1   Registered in customElements
 *  INV-LO-2   Form fields email + password rendered
 *  INV-LO-3   Validation: missing email → error, missing password → error
 *  INV-LO-4   submit() calls client.customerAuth.login con payload corretto
 *  INV-LO-5   Success → dispatches afianco:customer-logged-in with detail
 *  INV-LO-6   Error → afianco:customer-auth-error dispatched
 *  INV-LO-7   Forgot password link → afianco:auth-action {action: forgot-password}
 *  INV-LO-8   Signup link → afianco:auth-action {action: show-signup}
 *  INV-LO-9   Shadow DOM
 *  INV-LO-10  Password cleared dopo success (no leak in DOM)
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { AfiancoLogin } from '../src/components/afianco-login.js';
import {
  AfiancoAuthError,
  type AfiancoClient,
  type CustomerLoginRequest,
  type CustomerTokenResponse,
} from '@afianco/api-client';
import type { StorefrontContext } from '../src/context.js';

function makeMockClient(opts: {
  loginResponse?: CustomerTokenResponse;
  throws?: Error;
} = {}): { client: AfiancoClient; calls: CustomerLoginRequest[] } {
  const calls: CustomerLoginRequest[] = [];
  const client = {
    slug: 'demo',
    customerAuth: {
      login: async (body: CustomerLoginRequest) => {
        calls.push(body);
        if (opts.throws) throw opts.throws;
        return (
          opts.loginResponse ?? {
            access_token: 'tok_test',
            token_type: 'bearer',
            customer: {
              id: 'cust_1',
              email: body.email,
              name: 'Mario',
              locale: 'it',
              email_verified: true,
              created_at: '2026-01-01T00:00:00Z',
            },
          }
        );
      },
    },
  } as unknown as AfiancoClient;
  return { client, calls };
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

async function mountLogin(ctx: StorefrontContext): Promise<AfiancoLogin> {
  const el = document.createElement('afianco-login') as AfiancoLogin;
  el.ctx = ctx;
  document.body.appendChild(el);
  await el.updateComplete;
  return el;
}

describe('<afianco-login>', () => {
  afterEach(() => {
    document.querySelectorAll('afianco-login').forEach((e) => e.remove());
  });

  it('INV-LO-1 — registered in customElements', () => {
    expect(customElements.get('afianco-login')).toBe(AfiancoLogin);
  });

  it('INV-LO-9 — uses Shadow DOM', async () => {
    const { client } = makeMockClient();
    const el = await mountLogin(readyContext(client));
    expect(el.shadowRoot).not.toBeNull();
  });

  it('INV-LO-2 — renders email + password form fields', async () => {
    const { client } = makeMockClient();
    const el = await mountLogin(readyContext(client));
    expect(el.shadowRoot?.querySelector('#afianco-login-email')).toBeTruthy();
    expect(el.shadowRoot?.querySelector('#afianco-login-password')).toBeTruthy();
  });

  it('INV-LO-3 — validation: invalid email → error, no API call', async () => {
    const { client, calls } = makeMockClient();
    const el = await mountLogin(readyContext(client));
    (el as unknown as { email: string }).email = 'not-an-email';
    (el as unknown as { password: string }).password = 'whatever';
    await el.submit();
    expect(calls.length).toBe(0);
    expect(el.shadowRoot?.textContent ?? '').toMatch(/email/i);
  });

  it('INV-LO-3 — validation: empty password → error, no API call', async () => {
    const { client, calls } = makeMockClient();
    const el = await mountLogin(readyContext(client));
    (el as unknown as { email: string }).email = 'mario@example.com';
    (el as unknown as { password: string }).password = '';
    await el.submit();
    expect(calls.length).toBe(0);
    expect(el.shadowRoot?.textContent ?? '').toMatch(/password/i);
  });

  it('INV-LO-4 + INV-LO-5 — submit calls login + dispatches customer-logged-in', async () => {
    const { client, calls } = makeMockClient();
    const el = await mountLogin(readyContext(client));
    let detail: { customer: { id: string }; access_token: string } | null = null;
    el.addEventListener('afianco:customer-logged-in', (e) => {
      detail = (e as CustomEvent<{ customer: { id: string }; access_token: string }>).detail;
    });
    (el as unknown as { email: string }).email = 'mario@example.com';
    (el as unknown as { password: string }).password = 'StrongPass!';
    await el.submit();
    expect(calls.length).toBe(1);
    expect(calls[0]).toMatchObject({
      slug: 'demo',
      email: 'mario@example.com',
      password: 'StrongPass!',
    });
    expect(detail).toBeTruthy();
    expect(detail!.access_token).toBe('tok_test');
    expect(detail!.customer.id).toBe('cust_1');
  });

  it('INV-LO-6 — AfiancoAuthError → "credenziali non valide" + auth-error event', async () => {
    const { client } = makeMockClient({
      throws: new AfiancoAuthError(401, { detail: 'unauthorized' }),
    });
    const el = await mountLogin(readyContext(client));
    let errMsg: string | null = null;
    el.addEventListener('afianco:customer-auth-error', (e) => {
      errMsg = (e as CustomEvent<{ message: string }>).detail.message;
    });
    (el as unknown as { email: string }).email = 'mario@example.com';
    (el as unknown as { password: string }).password = 'wrong';
    await el.submit();
    expect(el.shadowRoot?.textContent ?? '').toMatch(/credenziali|account/i);
    expect(errMsg).toBeTruthy();
  });

  it('INV-LO-7 — click "Password dimenticata" dispatcha afianco:auth-action', async () => {
    const { client } = makeMockClient();
    const el = await mountLogin(readyContext(client));
    let actionDetail: { action: string } | null = null;
    el.addEventListener('afianco:auth-action', (e) => {
      actionDetail = (e as CustomEvent<{ action: string }>).detail;
    });
    const links = el.shadowRoot?.querySelectorAll('.links a');
    const forgot = Array.from(links ?? []).find((a) =>
      a.textContent?.includes('Password'),
    ) as HTMLAnchorElement | undefined;
    expect(forgot).toBeTruthy();
    forgot!.click();
    expect(actionDetail).toMatchObject({ action: 'forgot-password' });
  });

  it('INV-LO-8 — click "Crea un account" dispatcha show-signup', async () => {
    const { client } = makeMockClient();
    const el = await mountLogin(readyContext(client));
    let actionDetail: { action: string } | null = null;
    el.addEventListener('afianco:auth-action', (e) => {
      actionDetail = (e as CustomEvent<{ action: string }>).detail;
    });
    const links = el.shadowRoot?.querySelectorAll('.links a');
    const signup = Array.from(links ?? []).find((a) =>
      a.textContent?.includes('Crea'),
    ) as HTMLAnchorElement | undefined;
    expect(signup).toBeTruthy();
    signup!.click();
    expect(actionDetail).toMatchObject({ action: 'show-signup' });
  });

  it('INV-LO-10 — password cleared after successful login (no DOM leak)', async () => {
    const { client } = makeMockClient();
    const el = await mountLogin(readyContext(client));
    (el as unknown as { email: string }).email = 'mario@example.com';
    (el as unknown as { password: string }).password = 'SecretPass!';
    await el.submit();
    expect((el as unknown as { password: string }).password).toBe('');
  });

  it('show-forgot=false hides forgot password link', async () => {
    const { client } = makeMockClient();
    const el = document.createElement('afianco-login') as AfiancoLogin;
    el.ctx = readyContext(client);
    el.showForgot = false;
    document.body.appendChild(el);
    await el.updateComplete;
    const text = el.shadowRoot?.textContent ?? '';
    expect(text.includes('Password dimenticata')).toBe(false);
  });
});
