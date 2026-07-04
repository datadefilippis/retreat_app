/**
 * Sentinel tests for <afianco-signup> — Phase 1 Step 27.
 *
 * Invariants pinned
 * =================
 *  INV-SU-1   Registered in customElements
 *  INV-SU-2   Form fields name + email + password + gdpr*
 *  INV-SU-3   Validation: missing name, invalid email, short password,
 *             missing gdpr → errors
 *  INV-SU-4   submit() calls client.customerAuth.signup con payload corretto
 *  INV-SU-5   Success → dispatches afianco:customer-signed-up + success view
 *  INV-SU-6   Error → afianco:customer-auth-error dispatched
 *  INV-SU-7   Login link → afianco:auth-action {action: show-login}
 *  INV-SU-8   Shadow DOM
 *  INV-SU-9   Password cleared dopo success
 */

import { describe, it, expect, afterEach } from 'vitest';
import { AfiancoSignup } from '../src/components/afianco-signup.js';
import {
  AfiancoValidationError,
  type AfiancoClient,
  type CustomerSignupRequest,
} from '@afianco/api-client';
import type { StorefrontContext } from '../src/context.js';

function makeMockClient(opts: {
  throws?: Error;
  signupResponse?: unknown;
} = {}): { client: AfiancoClient; calls: CustomerSignupRequest[] } {
  const calls: CustomerSignupRequest[] = [];
  const client = {
    slug: 'demo',
    customerAuth: {
      signup: async (body: CustomerSignupRequest) => {
        calls.push(body);
        if (opts.throws) throw opts.throws;
        return opts.signupResponse ?? { status: 'verification_required' };
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

async function mountSignup(ctx: StorefrontContext): Promise<AfiancoSignup> {
  const el = document.createElement('afianco-signup') as AfiancoSignup;
  el.ctx = ctx;
  document.body.appendChild(el);
  await el.updateComplete;
  return el;
}

function fillValidForm(el: AfiancoSignup): void {
  (el as unknown as { name: string }).name = 'Mario Test';
  (el as unknown as { email: string }).email = 'mario.test@example.com';
  (el as unknown as { password: string }).password = 'StrongPass!2026';
  (el as unknown as { gdprPrivacy: boolean }).gdprPrivacy = true;
  (el as unknown as { gdprTerms: boolean }).gdprTerms = true;
}

describe('<afianco-signup>', () => {
  afterEach(() => {
    document.querySelectorAll('afianco-signup').forEach((e) => e.remove());
  });

  it('INV-SU-1 — registered in customElements', () => {
    expect(customElements.get('afianco-signup')).toBe(AfiancoSignup);
  });

  it('INV-SU-8 — uses Shadow DOM', async () => {
    const { client } = makeMockClient();
    const el = await mountSignup(readyContext(client));
    expect(el.shadowRoot).not.toBeNull();
  });

  it('INV-SU-2 — renders name + email + password + 3 gdpr fields', async () => {
    const { client } = makeMockClient();
    const el = await mountSignup(readyContext(client));
    expect(el.shadowRoot?.querySelector('#afianco-signup-name')).toBeTruthy();
    expect(el.shadowRoot?.querySelector('#afianco-signup-email')).toBeTruthy();
    expect(el.shadowRoot?.querySelector('#afianco-signup-password')).toBeTruthy();
    expect(el.shadowRoot?.querySelector('#afianco-signup-privacy')).toBeTruthy();
    expect(el.shadowRoot?.querySelector('#afianco-signup-terms')).toBeTruthy();
    expect(el.shadowRoot?.querySelector('#afianco-signup-marketing')).toBeTruthy();
  });

  it('INV-SU-3 — missing name → error, no API call', async () => {
    const { client, calls } = makeMockClient();
    const el = await mountSignup(readyContext(client));
    await el.submit();
    expect(calls.length).toBe(0);
    expect(el.shadowRoot?.textContent ?? '').toMatch(/nome/i);
  });

  it('INV-SU-3 — invalid email → error', async () => {
    const { client, calls } = makeMockClient();
    const el = await mountSignup(readyContext(client));
    (el as unknown as { name: string }).name = 'Mario';
    (el as unknown as { email: string }).email = 'not-an-email';
    await el.submit();
    expect(calls.length).toBe(0);
    expect(el.shadowRoot?.textContent ?? '').toMatch(/email/i);
  });

  it('INV-SU-3 — short password → error', async () => {
    const { client, calls } = makeMockClient();
    const el = await mountSignup(readyContext(client));
    (el as unknown as { name: string }).name = 'Mario';
    (el as unknown as { email: string }).email = 'mario@example.com';
    (el as unknown as { password: string }).password = 'short';
    await el.submit();
    expect(calls.length).toBe(0);
    expect(el.shadowRoot?.textContent ?? '').toMatch(/8/);
  });

  it('INV-SU-3 — missing GDPR → error', async () => {
    const { client, calls } = makeMockClient();
    const el = await mountSignup(readyContext(client));
    (el as unknown as { name: string }).name = 'Mario';
    (el as unknown as { email: string }).email = 'mario@example.com';
    (el as unknown as { password: string }).password = 'StrongPass!';
    await el.submit();
    expect(calls.length).toBe(0);
    expect(el.shadowRoot?.textContent ?? '').toMatch(/Privacy|Termini/);
  });

  it('INV-SU-4 — submit calls signup con payload corretto', async () => {
    const { client, calls } = makeMockClient();
    const el = await mountSignup(readyContext(client));
    fillValidForm(el);
    (el as unknown as { gdprMarketing: boolean }).gdprMarketing = true;
    await el.submit();
    expect(calls.length).toBe(1);
    expect(calls[0]).toMatchObject({
      slug: 'demo',
      name: 'Mario Test',
      email: 'mario.test@example.com',
      password: 'StrongPass!2026',
      accepted_terms: true,
      accepted_privacy: true,
      accepted_marketing: true,
    });
  });

  it('INV-SU-5 — success → afianco:customer-signed-up event + success view', async () => {
    const { client } = makeMockClient();
    const el = await mountSignup(readyContext(client));
    let detail: { email: string } | null = null;
    el.addEventListener('afianco:customer-signed-up', (e) => {
      detail = (e as CustomEvent<{ email: string }>).detail;
    });
    fillValidForm(el);
    await el.submit();
    expect(detail).toBeTruthy();
    expect(detail!.email).toBe('mario.test@example.com');
    await el.updateComplete;
    const text = el.shadowRoot?.textContent ?? '';
    expect(text).toContain('mario.test@example.com');
    expect(text.toLowerCase()).toContain('verifica');
  });

  it('INV-SU-6 — backend error → error banner + auth-error event', async () => {
    const validationError = new AfiancoValidationError('signup_failed', {
      detail: 'Email già registrata',
    });
    const { client } = makeMockClient({ throws: validationError });
    const el = await mountSignup(readyContext(client));
    let errMsg: string | null = null;
    el.addEventListener('afianco:customer-auth-error', (e) => {
      errMsg = (e as CustomEvent<{ message: string }>).detail.message;
    });
    fillValidForm(el);
    await el.submit();
    expect(errMsg).toBeTruthy();
    expect(el.shadowRoot?.textContent ?? '').toContain('Email già registrata');
  });

  it('INV-SU-7 — login link dispatcha afianco:auth-action {show-login}', async () => {
    const { client } = makeMockClient();
    const el = await mountSignup(readyContext(client));
    let actionDetail: { action: string } | null = null;
    el.addEventListener('afianco:auth-action', (e) => {
      actionDetail = (e as CustomEvent<{ action: string }>).detail;
    });
    const link = el.shadowRoot?.querySelector('.login-link a') as HTMLAnchorElement;
    expect(link).toBeTruthy();
    link.click();
    expect(actionDetail).toMatchObject({ action: 'show-login' });
  });

  it('INV-SU-9 — password cleared after successful signup', async () => {
    const { client } = makeMockClient();
    const el = await mountSignup(readyContext(client));
    fillValidForm(el);
    await el.submit();
    expect((el as unknown as { password: string }).password).toBe('');
  });

  it('show-login-link=false hides login link', async () => {
    const { client } = makeMockClient();
    const el = document.createElement('afianco-signup') as AfiancoSignup;
    el.ctx = readyContext(client);
    el.showLoginLink = false;
    document.body.appendChild(el);
    await el.updateComplete;
    expect(el.shadowRoot?.querySelector('.login-link')).toBeFalsy();
  });
});
