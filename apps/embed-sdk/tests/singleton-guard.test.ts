/**
 * Sentinel tests — SingletonController (Embed à-la-carte, refinement Fase 5).
 *
 * Invariants pinned
 * =================
 *   INV-SG-1  Primo connesso = attivo; successivi = passivi
 *   INV-SG-2  Disconnessione dell'attivo → promuove il successivo
 *   INV-SG-3  Chiavi indipendenti per nome diverso
 *   INV-SG-4  Chiavi indipendenti per slug diverso (attr `store`)
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';

import {
  SingletonController,
  __clearSingletonRegistryForTests,
} from '../src/store/singleton-guard';

function fakeHost(attrs: Record<string, string> = {}) {
  return {
    addController: vi.fn(),
    requestUpdate: vi.fn(),
    getAttribute: (k: string) => attrs[k] ?? null,
  } as any;
}

function mount(name: string, attrs: Record<string, string> = {}) {
  const c = new SingletonController(fakeHost(attrs), name);
  c.hostConnected();
  return c;
}

describe('SingletonController', () => {
  beforeEach(() => __clearSingletonRegistryForTests());

  // INV-SG-1
  it('first is active, subsequent are passive', () => {
    const a = mount('cart-drawer');
    const b = mount('cart-drawer');
    const c = mount('cart-drawer');
    expect(a.active).toBe(true);
    expect(b.active).toBe(false);
    expect(c.active).toBe(false);
  });

  // INV-SG-2
  it('promotes the next when the active disconnects', () => {
    const a = mount('cart-drawer');
    const b = mount('cart-drawer');
    a.hostDisconnected();
    expect(b.active).toBe(true);
  });

  it('non-active disconnect does not change the active', () => {
    const a = mount('cart-drawer');
    const b = mount('cart-drawer');
    b.hostDisconnected();
    expect(a.active).toBe(true);
  });

  // INV-SG-3
  it('different names are independent singletons', () => {
    const cart = mount('cart-drawer');
    const account = mount('account');
    expect(cart.active).toBe(true);
    expect(account.active).toBe(true);
  });

  // INV-SG-4
  it('different slugs are independent singletons', () => {
    const a = mount('cart-drawer', { store: 'shop-a' });
    const b = mount('cart-drawer', { store: 'shop-b' });
    expect(a.active).toBe(true);
    expect(b.active).toBe(true); // slug diverso → entrambi attivi
  });

  // INV-SG-5 — B6: la chiave usa lo slug del provider full-store (closest)
  it('keys by provider slug from closest(afianco-storefront-init)', () => {
    const providerHost = (slug: string) => {
      const provider = { getAttribute: (k: string) => (k === 'slug' ? slug : null) };
      return {
        addController: vi.fn(),
        requestUpdate: vi.fn(),
        getAttribute: () => null, // niente attributo `store`
        closest: (sel: string) => (sel === 'afianco-storefront-init' ? provider : null),
      } as any;
    };
    // due singleton full-store con slug provider DIVERSI → entrambi attivi
    const x = new SingletonController(providerHost('store-X'), 'cart-drawer');
    x.hostConnected();
    const y = new SingletonController(providerHost('store-Y'), 'cart-drawer');
    y.hostConnected();
    expect(x.active).toBe(true);
    expect(y.active).toBe(true);
    // un terzo con provider slug == X → collide con X → passivo
    const x2 = new SingletonController(providerHost('store-X'), 'cart-drawer');
    x2.hostConnected();
    expect(x2.active).toBe(false);
  });
});
