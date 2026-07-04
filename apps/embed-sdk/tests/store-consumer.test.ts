/**
 * Sentinel tests — StoreConsumerController + componenti à-la-carte (Fase 2).
 *
 * Invariants pinned
 * =================
 *   INV-SC-1  Componente con `store="slug"` SENZA provider → si aggancia al
 *             kernel e il suo ctx diventa "ready" (cuore dell'à-la-carte)
 *   INV-SC-2  Componente SENZA slug e SENZA provider → nessun take-over
 *             (ctx resta initial: preserva il comportamento esistente)
 *   INV-SC-3  Nuovi tag registrati: cart-button, account-button, product
 *   INV-SC-4  cart-button: click → dispatch document `afianco:open-cart`
 *   INV-SC-5  cart-button: `afianco:cart-updated` → badge count aggiornato
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

import { getStoreKernel, __clearStoreRegistryForTests } from '../src/store/kernel';
import { __resetPageConfigForTests } from '../src/store/page-config';

// Import side-effect: registra i nuovi custom element.
import { AfiancoCartButton } from '../src/components/afianco-cart-button';
import { AfiancoAccountButton } from '../src/components/afianco-account-button';
import { AfiancoProduct } from '../src/components/afianco-product';

const OK_INIT = {
  slug: 'acme',
  storefront_languages: ['it'],
  store_info: { display_name: 'Acme' },
  currency: 'EUR',
  categories: [],
};

function fakeClient(slug: string) {
  return {
    slug,
    baseUrl: 'http://test',
    tokenStorage: { get: () => null },
    embed: { getInit: vi.fn(async () => OK_INIT) },
  } as any;
}

const tick = () => new Promise((r) => setTimeout(r, 0));

describe('StoreConsumerController (à-la-carte binding)', () => {
  beforeEach(() => {
    __clearStoreRegistryForTests();
    __resetPageConfigForTests();
    document.body.innerHTML = '';
  });
  afterEach(() => {
    document.body.innerHTML = '';
  });

  // INV-SC-1
  it('binds a standalone component (store attr, no provider) to the kernel → ready', async () => {
    getStoreKernel('acme', { client: fakeClient('acme') }); // seed: no network
    const el = document.createElement('afianco-cart-button') as AfiancoCartButton;
    el.setAttribute('store', 'acme');
    document.body.appendChild(el);
    await (el as any).updateComplete;
    await tick();
    expect((el as any).ctx?.status).toBe('ready');
    expect((el as any).ctx?.init?.slug).toBe('acme');
  });

  // INV-SC-2
  it('does NOT take over when there is no slug and no provider', async () => {
    const el = document.createElement('afianco-cart-button') as AfiancoCartButton;
    document.body.appendChild(el);
    await (el as any).updateComplete;
    await tick();
    // ctx resta undefined/initial (nessun provider, nessuno slug)
    expect((el as any).ctx?.status).not.toBe('ready');
  });

  // INV-SC-3
  it('registers the new à-la-carte tags', () => {
    expect(customElements.get('afianco-cart-button')).toBe(AfiancoCartButton);
    expect(customElements.get('afianco-account-button')).toBe(AfiancoAccountButton);
    expect(customElements.get('afianco-product')).toBe(AfiancoProduct);
  });

  // INV-SC-4
  it('cart-button dispatches afianco:open-cart on click', async () => {
    const el = document.createElement('afianco-cart-button') as AfiancoCartButton;
    document.body.appendChild(el);
    await (el as any).updateComplete;
    const spy = vi.fn();
    document.addEventListener('afianco:open-cart', spy);
    const btn = el.shadowRoot?.querySelector('button');
    btn?.dispatchEvent(new MouseEvent('click', { bubbles: true, composed: true }));
    expect(spy).toHaveBeenCalledTimes(1);
    document.removeEventListener('afianco:open-cart', spy);
  });

  // INV-SC-5
  it('cart-button updates badge on afianco:cart-updated', async () => {
    const el = document.createElement('afianco-cart-button') as AfiancoCartButton;
    document.body.appendChild(el);
    await (el as any).updateComplete;
    document.dispatchEvent(
      new CustomEvent('afianco:cart-updated', { detail: { item_count: 3 }, bubbles: true }),
    );
    await (el as any).updateComplete;
    const badge = el.shadowRoot?.querySelector('.badge');
    expect(badge?.textContent?.trim()).toBe('3');
  });
});
