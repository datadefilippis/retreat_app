/**
 * Sentinel tests — AfiancoStoreKernel + page-config (Embed à-la-carte, Fase 1).
 *
 * Invariants pinned
 * =================
 *   INV-K-1  Registry: un solo kernel per slug; slug diversi → istanze diverse
 *   INV-K-2  Stato iniziale "idle"; subscribe avvia il bootstrap
 *   INV-K-3  ensureInit dedup: chiamate concorrenti → 1 sola getInit
 *   INV-K-4  init OK → status "ready" + init salvato + listener notificato
 *   INV-K-5  init KO → status "error" + messaggio
 *   INV-K-6  unsubscribe rimuove il listener
 *   INV-K-7  page-config legge data-afianco-slug / data-afianco-base-url
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

import {
  AfiancoStoreKernel,
  getStoreKernel,
  __clearStoreRegistryForTests,
} from '../src/store/kernel';
import { getPageConfig, __resetPageConfigForTests } from '../src/store/page-config';

// Fake client minimale: solo cio' che il kernel usa (embed.getInit).
function makeFakeClient(slug: string, initImpl: () => Promise<any>) {
  return {
    slug,
    baseUrl: 'http://test',
    tokenStorage: { get: () => null },
    embed: { getInit: vi.fn(initImpl) },
  } as any;
}

const OK_INIT = {
  slug: 'acme',
  storefront_languages: ['it'],
  store_info: { display_name: 'Acme' },
  currency: 'EUR',
  categories: [],
};

describe('AfiancoStoreKernel', () => {
  beforeEach(() => {
    __clearStoreRegistryForTests();
  });

  // INV-K-1
  it('registry returns one kernel per slug', () => {
    const a1 = getStoreKernel('acme', { client: makeFakeClient('acme', async () => OK_INIT) });
    const a2 = getStoreKernel('acme');
    const b = getStoreKernel('beta', { client: makeFakeClient('beta', async () => OK_INIT) });
    expect(a1).toBe(a2);
    expect(a1).not.toBe(b);
  });

  // INV-K-2
  it('starts idle and bootstraps on first subscribe', async () => {
    const client = makeFakeClient('acme', async () => OK_INIT);
    const k = new AfiancoStoreKernel('acme', { client });
    expect(k.state.status).toBe('idle');
    const unsub = k.subscribe(() => {});
    expect(client.embed.getInit).toHaveBeenCalledTimes(1);
    unsub();
  });

  // INV-K-3
  it('dedups concurrent ensureInit into a single getInit', async () => {
    const client = makeFakeClient('acme', async () => OK_INIT);
    const k = new AfiancoStoreKernel('acme', { client });
    await Promise.all([k.ensureInit(), k.ensureInit(), k.ensureInit()]);
    expect(client.embed.getInit).toHaveBeenCalledTimes(1);
    expect(k.state.status).toBe('ready');
  });

  // INV-K-4
  it('transitions to ready and notifies listeners on success', async () => {
    const client = makeFakeClient('acme', async () => OK_INIT);
    const k = new AfiancoStoreKernel('acme', { client });
    const seen: string[] = [];
    k.subscribe(() => seen.push(k.state.status));
    await k.ensureInit();
    expect(k.state.status).toBe('ready');
    expect(k.state.init).toEqual(OK_INIT);
    expect(seen).toContain('ready');
  });

  // INV-K-5
  it('transitions to error on failure', async () => {
    const client = makeFakeClient('acme', async () => {
      throw new Error('boom');
    });
    const k = new AfiancoStoreKernel('acme', { client });
    await k.ensureInit();
    expect(k.state.status).toBe('error');
    expect(k.state.error).toContain('boom');
  });

  // INV-K-6
  it('unsubscribe stops notifications', async () => {
    const client = makeFakeClient('acme', async () => OK_INIT);
    const k = new AfiancoStoreKernel('acme', { client });
    let count = 0;
    const unsub = k.subscribe(() => (count += 1));
    await k.ensureInit();
    const afterInit = count;
    unsub();
    await k.refresh(true);
    expect(count).toBe(afterInit);
  });
});

describe('page-config', () => {
  afterEach(() => {
    __resetPageConfigForTests();
    document.querySelectorAll('script[data-afianco-slug]').forEach((el) => el.remove());
  });

  // INV-K-7
  it('reads slug and base-url from the script tag', () => {
    const s = document.createElement('script');
    s.setAttribute('data-afianco-slug', 'mio-store');
    s.setAttribute('data-afianco-base-url', 'http://localhost:8000');
    document.head.appendChild(s);
    __resetPageConfigForTests();
    const cfg = getPageConfig();
    expect(cfg.slug).toBe('mio-store');
    expect(cfg.baseUrl).toBe('http://localhost:8000');
  });

  it('returns empty config when no script tag present', () => {
    __resetPageConfigForTests();
    const cfg = getPageConfig();
    expect(cfg.slug).toBeUndefined();
  });
});
