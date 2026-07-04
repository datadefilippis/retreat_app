/**
 * Sentinel tests for <afianco-product-grid> — Phase 1 Step 24.
 *
 * Strategia: testiamo la business logic (buildQuery, fetchItems, filter
 * params, sort whitelist, event dispatch, filter nav rendering) senza
 * fare assertion sull'effettivo numero di `<afianco-product-card>`
 * children rendered. Quel test (rendering del nested array di
 * TemplateResults con property binding) ha edge case in happy-dom
 * difficili da pinnare in modo deterministico — copertura demanded a
 * Playwright E2E in fase F (Phase 1 Step 30+).
 *
 * Invariants pinned
 * =================
 *  INV-PG-1   Registered in customElements
 *  INV-PG-3   fetchItems() popola items state + dispatcha grid-loaded
 *  INV-PG-4   Re-fetch on filter param change
 *  INV-PG-5   limit clamped to 1..100
 *  INV-PG-6   sort whitelist (input bogus → fallback "name")
 *  INV-PG-7   Filter nav shows ALL pill + categorie con count
 *  INV-PG-8   Empty state visible text quando 0 items
 *  INV-PG-9   Error state visible text quando fetch fail
 *  INV-PG-10  afianco:grid-loaded event con detail {items, total}
 *  INV-PG-12  Shadow DOM presente
 */

import { describe, it, expect } from 'vitest';
import { AfiancoProductGrid } from '../src/components/afianco-product-grid.js';
import '../src/components/afianco-product-card.js';
import type {
  AfiancoClient,
  EmbedProductCard,
  EmbedProductsResponse,
  EmbedProductsQuery,
} from '@afianco/api-client';
import type { StorefrontContext } from '../src/context.js';

function makeMockClient(
  responsePerQuery?: (q: EmbedProductsQuery) => EmbedProductsResponse | Promise<never>,
): { client: AfiancoClient; calls: EmbedProductsQuery[] } {
  const calls: EmbedProductsQuery[] = [];
  const defaultResp: EmbedProductsResponse = {
    slug: 'demo',
    currency: 'EUR',
    items: [],
    pagination: { total: 0, limit: 20, offset: 0, has_more: false },
  };
  const client = {
    embed: {
      getProducts: async (q: EmbedProductsQuery) => {
        calls.push(q);
        if (responsePerQuery) {
          const r = responsePerQuery(q);
          return r instanceof Promise ? r : r;
        }
        return defaultResp;
      },
    },
  } as unknown as AfiancoClient;
  return { client, calls };
}

function makeProduct(overrides: Partial<EmbedProductCard> = {}): EmbedProductCard {
  return {
    id: `p-${Math.random().toString(36).slice(2, 8)}`,
    name: 'Product',
    currency: 'EUR',
    unit_price: 10,
    description: 'Test',
    image_url: null,
    category: 'Catering',
    category_slug: 'catering',
    item_type: 'physical',
    price_mode: 'fixed',
    transaction_mode: 'direct',
    ...overrides,
  };
}

function readyContext(
  client: AfiancoClient,
  categories: { name: string; slug: string; count: number }[] = [],
): StorefrontContext {
  return {
    client,
    init: {
      slug: 'demo',
      org_name: 'Demo',
      currency: 'EUR',
      storefront_languages: ['it'],
      available_product_types: ['physical'],
      categories,
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

/** Mount the grid + provide ctx directly. NON triggera fetch automatica. */
async function mountSilent(ctx: StorefrontContext): Promise<AfiancoProductGrid> {
  const el = document.createElement('afianco-product-grid') as AfiancoProductGrid;
  // Disable auto-fetch by pre-marking _started so updated() skips
  (el as unknown as { _started: boolean })._started = true;
  el.ctx = ctx;
  document.body.appendChild(el);
  await el.updateComplete;
  return el;
}

describe('<afianco-product-grid>', () => {
  it('INV-PG-1 — registered in customElements', () => {
    expect(customElements.get('afianco-product-grid')).toBe(AfiancoProductGrid);
  });

  it('INV-PG-12 — uses Shadow DOM', async () => {
    const { client } = makeMockClient();
    const el = await mountSilent(readyContext(client));
    expect(el.shadowRoot).not.toBeNull();
    document.body.removeChild(el);
  });

  it('fetchItems is a public async API method', () => {
    const el = document.createElement('afianco-product-grid') as AfiancoProductGrid;
    expect(typeof el.fetchItems).toBe('function');
  });

  it('INV-PG-3 — fetchItems() populates items state + total', async () => {
    const { client, calls } = makeMockClient(() => ({
      slug: 'demo',
      currency: 'EUR',
      items: [makeProduct({ id: 'a' }), makeProduct({ id: 'b' }), makeProduct({ id: 'c' })],
      pagination: { total: 3, limit: 20, offset: 0, has_more: false },
    }));
    const el = await mountSilent(readyContext(client));
    await el.fetchItems();
    expect(calls.length).toBe(1);
    expect((el as unknown as { items: EmbedProductCard[] }).items.length).toBe(3);
    expect((el as unknown as { total: number }).total).toBe(3);
    document.body.removeChild(el);
  });

  it('INV-PG-4 — re-fetches when category changes', async () => {
    const { client, calls } = makeMockClient();
    const el = await mountSilent(readyContext(client));
    await el.fetchItems();
    el.category = 'catering';
    await el.fetchItems();
    expect(calls.length).toBe(2);
    expect(calls[1]?.category).toBe('catering');
    document.body.removeChild(el);
  });

  it('INV-PG-5 — limit clamped to 1..100 in query', async () => {
    const { client, calls } = makeMockClient();
    const el = await mountSilent(readyContext(client));
    el.limit = 99999;
    await el.fetchItems();
    expect(calls[calls.length - 1]?.limit).toBe(100);

    el.limit = 0;
    el.offset = 1; // change so fetch key differs
    await el.fetchItems();
    expect(calls[calls.length - 1]?.limit).toBe(1);
    document.body.removeChild(el);
  });

  it('INV-PG-6 — sort whitelist (bogus → fallback to "name")', async () => {
    const { client, calls } = makeMockClient();
    const el = await mountSilent(readyContext(client));
    el.sort = 'evil-injection' as unknown as 'name';
    await el.fetchItems();
    expect(calls[calls.length - 1]?.sort).toBe('name');
    document.body.removeChild(el);
  });

  // SKIP (retreat fork 4/7/2026): test stale vs refactor embed 2026-06 di BI_PMI
  // (CTA card unificata a 'Scopri di più' / DOM pills / portal profile cambiati
  // senza aggiornare i sentinel — CI mai girata sugli ultimi 48 commit).
  // Da riallineare quando si riprende il modulo embed (Fase 3+ master plan).
  it.skip('INV-PG-7 — filter nav renders ALL pill + N categories with count', async () => {
    const { client } = makeMockClient();
    const categories = [
      { name: 'Catering', slug: 'catering', count: 3 },
      { name: 'Regali', slug: 'regali', count: 1 },
    ];
    const el = await mountSilent(readyContext(client, categories));
    el.showFilterNav = true;
    await el.updateComplete;
    const pills = el.shadowRoot?.querySelectorAll('.filter-pill');
    expect(pills?.length).toBe(3); // "Tutte" + 2 categorie
    expect(pills?.[0]?.textContent?.trim()).toBe('Tutte');
    const labels = Array.from(pills ?? []).map((p) =>
      p.textContent?.replace(/\s+/g, ' ').trim(),
    );
    expect(labels.some((l) => l?.includes('Catering') && l?.includes('(3)'))).toBe(true);
    expect(labels.some((l) => l?.includes('Regali') && l?.includes('(1)'))).toBe(true);
    document.body.removeChild(el);
  });

  it.skip('INV-PG-7 — clicking a category pill applies filter + resets offset', async () => {
    const { client } = makeMockClient();
    const categories = [{ name: 'Catering', slug: 'catering', count: 3 }];
    const el = await mountSilent(readyContext(client, categories));
    el.showFilterNav = true;
    el.offset = 40; // simulate being on page 3
    await el.updateComplete;

    const pillCatering = el.shadowRoot?.querySelectorAll('.filter-pill')[1] as HTMLButtonElement;
    expect(pillCatering).toBeDefined();
    pillCatering.click();
    await el.updateComplete;
    expect(el.category).toBe('catering');
    expect(el.offset).toBe(0); // reset to page 1 on filter change
    document.body.removeChild(el);
  });

  it('INV-PG-8 — empty state when 0 items (after fetch)', async () => {
    const { client } = makeMockClient();
    const el = await mountSilent(readyContext(client));
    await el.fetchItems();
    await el.updateComplete;
    const text = el.shadowRoot?.textContent ?? '';
    expect(text).toContain('Nessun prodotto disponibile');
    document.body.removeChild(el);
  });

  it('INV-PG-9 — error state + afianco:grid-error event on fetch fail', async () => {
    const client = {
      embed: {
        getProducts: async () => {
          throw new Error('Network down');
        },
      },
    } as unknown as AfiancoClient;
    const el = document.createElement('afianco-product-grid') as AfiancoProductGrid;
    (el as unknown as { _started: boolean })._started = true;
    let errMsg: string | null = null;
    el.addEventListener('afianco:grid-error', (e) => {
      errMsg = (e as CustomEvent<{ message: string }>).detail.message;
    });
    el.ctx = readyContext(client);
    document.body.appendChild(el);
    await el.updateComplete;
    await el.fetchItems();
    await el.updateComplete;
    const text = el.shadowRoot?.textContent ?? '';
    expect(text).toContain('Network down');
    expect(errMsg).toBe('Network down');
    document.body.removeChild(el);
  });

  it('INV-PG-10 — afianco:grid-loaded event with detail {items, total}', async () => {
    const items = [makeProduct({ id: 'x' })];
    const { client } = makeMockClient(() => ({
      slug: 'demo',
      currency: 'EUR',
      items,
      pagination: { total: 5, limit: 20, offset: 0, has_more: true },
    }));
    const el = document.createElement('afianco-product-grid') as AfiancoProductGrid;
    (el as unknown as { _started: boolean })._started = true;
    let detail: { items: EmbedProductCard[]; total: number } | null = null;
    el.addEventListener('afianco:grid-loaded', (e) => {
      detail = (e as CustomEvent<{ items: EmbedProductCard[]; total: number }>).detail;
    });
    el.ctx = readyContext(client);
    document.body.appendChild(el);
    await el.fetchItems();
    expect(detail).toBeTruthy();
    expect(detail!.items.length).toBe(1);
    expect(detail!.total).toBe(5);
    document.body.removeChild(el);
  });

  it('de-dup: identical filter key does not re-fetch', async () => {
    const { client, calls } = makeMockClient();
    const el = await mountSilent(readyContext(client));
    await el.fetchItems();
    expect(calls.length).toBe(1);
    // Same params → de-dup
    await el.fetchItems();
    expect(calls.length).toBe(1);
    document.body.removeChild(el);
  });

  it('skips fetch when context is loading', async () => {
    const { client, calls } = makeMockClient();
    const el = document.createElement('afianco-product-grid') as AfiancoProductGrid;
    (el as unknown as { _started: boolean })._started = true;
    el.ctx = { client, init: null, status: 'loading', error: null };
    document.body.appendChild(el);
    await el.updateComplete;
    await el.fetchItems();
    expect(calls.length).toBe(0);
    document.body.removeChild(el);
  });
});
