/**
 * Sentinel tests for <afianco-cart-drawer> — Phase 1 Step 25.
 *
 * Strategia: stessa di product-grid → inject ctx + chiamare le public
 * API direttamente per testare business logic. La rendering visuale
 * dello slide-in è coperta da Playwright E2E (Phase F).
 *
 * Invariants pinned
 * =================
 *  INV-CD-1   Registered in customElements
 *  INV-CD-2   Document listener afianco:add-to-cart attached on connect
 *  INV-CD-3   addItem() crea cart al primo add via client.cart.create
 *  INV-CD-4   addItem() su existing cart usa cart.update + merge by product_id
 *  INV-CD-5   updateItemQuantity(0) rimuove l'item
 *  INV-CD-6   cart_id persisted in localStorage chiavato per slug
 *  INV-CD-7   cart_id loaded from localStorage at init (re-hydrate)
 *  INV-CD-8   open/close state + custom events afianco:cart-opened/closed
 *  INV-CD-9   Checkout CTA dispatcha afianco:checkout-requested
 *  INV-CD-10  afianco:cart-updated dispatched ad ogni mutazione
 *  INV-CD-11  Shadow DOM presente
 *  INV-CD-12  auto-open attribute apre il drawer dopo primo add
 *  INV-CD-13  Stale cart_id (404) viene rimosso da localStorage
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { AfiancoCartDrawer } from '../src/components/afianco-cart-drawer.js';
import type {
  AfiancoClient,
  CartResponse,
  CartUpdate,
  EmbedProductCard,
} from '@afianco/api-client';
import type { StorefrontContext } from '../src/context.js';

function makeCart(overrides: Partial<CartResponse> = {}): CartResponse {
  return {
    id: 'cart_test_1',
    organization_id: 'org-1',
    items: [],
    item_count: 0,
    subtotal_snapshot: 0,
    currency_snapshot: 'EUR',
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    expires_at: '2026-03-01T00:00:00Z',
    source: 'embed',
    ...overrides,
  };
}

function makeProduct(overrides: Partial<EmbedProductCard> = {}): EmbedProductCard {
  return {
    id: 'p-test',
    name: 'Test Product',
    currency: 'EUR',
    unit_price: 10,
    description: 'Test',
    image_url: null,
    category: null,
    category_slug: null,
    item_type: 'physical',
    price_mode: 'fixed',
    transaction_mode: 'direct',
    ...overrides,
  };
}

interface MockClientState {
  /** Last cart returned from create/update (mutates between calls). */
  cart: CartResponse | null;
  /** Calls made to cart.create */
  createCalls: number;
  /** Calls made to cart.update (cart_id, body) */
  updateCalls: { cartId: string; body: CartUpdate }[];
  /** Calls to cart.get */
  getCalls: string[];
  /** If true, cart.get throws (simulate stale cart_id) */
  getThrows: boolean;
}

function makeMockClient(opts: { slug?: string; getThrows?: boolean } = {}): {
  client: AfiancoClient;
  state: MockClientState;
} {
  const state: MockClientState = {
    cart: null,
    createCalls: 0,
    updateCalls: [],
    getCalls: [],
    getThrows: opts.getThrows ?? false,
  };
  const client = {
    slug: opts.slug ?? 'demo',
    embed: {
      cart: {
        create: async () => {
          state.createCalls += 1;
          state.cart = makeCart({ id: `cart_${state.createCalls}` });
          return state.cart;
        },
        get: async (id: string) => {
          state.getCalls.push(id);
          if (state.getThrows) {
            const err = new Error('Cart not found');
            (err as Error & { status?: number }).status = 404;
            throw err;
          }
          // Return whatever current state we have
          return state.cart ?? makeCart({ id });
        },
        update: async (cartId: string, body: CartUpdate) => {
          state.updateCalls.push({ cartId, body });
          // Build a new cart matching the body items shape
          const items = (body.items ?? []).map((i) => ({
            product_id: i.product_id,
            quantity: i.quantity,
            occurrence_id: i.occurrence_id ?? null,
            ticket_tier_id: i.ticket_tier_id ?? null,
            rental_date_from: i.rental_date_from ?? null,
            rental_date_to: i.rental_date_to ?? null,
            rental_notes: i.rental_notes ?? null,
            booking_date: i.booking_date ?? null,
            booking_start_time: i.booking_start_time ?? null,
            booking_end_time: i.booking_end_time ?? null,
            booking_end_date: i.booking_end_date ?? null,
            attendees: i.attendees ?? null,
            service_option_id: i.service_option_id ?? null,
            service_custom_request: i.service_custom_request ?? false,
            extra_selections: i.extra_selections ?? null,
            product_name_snapshot: 'Test Product',
            unit_price_snapshot: 10,
            currency_snapshot: 'EUR',
          }));
          state.cart = makeCart({
            id: cartId,
            items,
            item_count: items.reduce((acc, x) => acc + x.quantity, 0),
            subtotal_snapshot: items.reduce(
              (acc, x) => acc + (x.unit_price_snapshot ?? 0) * x.quantity,
              0,
            ),
          });
          return state.cart;
        },
      },
    },
  } as unknown as AfiancoClient;
  return { client, state };
}

function readyContext(
  client: AfiancoClient,
  initSlug = 'demo',
): StorefrontContext {
  return {
    client,
    init: {
      slug: initSlug,
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

async function mountDrawer(ctx: StorefrontContext): Promise<AfiancoCartDrawer> {
  const el = document.createElement('afianco-cart-drawer') as AfiancoCartDrawer;
  el.ctx = ctx;
  document.body.appendChild(el);
  await el.updateComplete;
  // Allow init load promise
  await new Promise((r) => setTimeout(r, 0));
  await el.updateComplete;
  return el;
}

const STORAGE_PREFIX = 'afianco_cart_id_';

describe('<afianco-cart-drawer>', () => {
  beforeEach(() => {
    try {
      Object.keys(localStorage)
        .filter((k) => k.startsWith(STORAGE_PREFIX))
        .forEach((k) => localStorage.removeItem(k));
    } catch {
      // happy-dom may not have full localStorage
    }
  });

  afterEach(() => {
    // Cleanup all drawer instances
    document.querySelectorAll('afianco-cart-drawer').forEach((el) => el.remove());
  });

  it('INV-CD-1 — registered in customElements', () => {
    expect(customElements.get('afianco-cart-drawer')).toBe(AfiancoCartDrawer);
  });

  it('INV-CD-11 — uses Shadow DOM', async () => {
    const { client } = makeMockClient();
    const el = await mountDrawer(readyContext(client));
    expect(el.shadowRoot).not.toBeNull();
  });

  it('public API: addItem / updateItemQuantity / toggle / setOpen', () => {
    const el = document.createElement('afianco-cart-drawer') as AfiancoCartDrawer;
    expect(typeof el.addItem).toBe('function');
    expect(typeof el.updateItemQuantity).toBe('function');
    expect(typeof el.toggle).toBe('function');
    expect(typeof el.setOpen).toBe('function');
  });

  it('INV-CD-3 — addItem() creates cart on first add via cart.create', async () => {
    const { client, state } = makeMockClient();
    const el = await mountDrawer(readyContext(client));
    await el.addItem({ product: makeProduct({ id: 'p1' }), quantity: 2 });
    expect(state.createCalls).toBe(1);
    expect(state.updateCalls.length).toBe(1);
    expect(state.updateCalls[0]?.body.items?.[0]).toMatchObject({
      product_id: 'p1',
      quantity: 2,
    });
  });

  it('INV-CD-4 — addItem() su existing cart NON ricrea, merge by product_id', async () => {
    const { client, state } = makeMockClient();
    const el = await mountDrawer(readyContext(client));
    // First add → create
    await el.addItem({ product: makeProduct({ id: 'p1' }), quantity: 2 });
    // Second add stesso product → merge qty
    await el.addItem({ product: makeProduct({ id: 'p1' }), quantity: 3 });
    expect(state.createCalls).toBe(1);
    expect(state.updateCalls.length).toBe(2);
    // Last update should have qty = 2 + 3 = 5
    const lastBody = state.updateCalls[state.updateCalls.length - 1]?.body;
    expect(lastBody?.items?.length).toBe(1);
    expect(lastBody?.items?.[0]?.quantity).toBe(5);
  });

  it('INV-CD-4 — addItem() distinct product appends', async () => {
    const { client, state } = makeMockClient();
    const el = await mountDrawer(readyContext(client));
    await el.addItem({ product: makeProduct({ id: 'p1' }), quantity: 1 });
    await el.addItem({ product: makeProduct({ id: 'p2' }), quantity: 2 });
    const last = state.updateCalls[state.updateCalls.length - 1]?.body;
    expect(last?.items?.length).toBe(2);
    expect(last?.items?.find((i) => i.product_id === 'p2')?.quantity).toBe(2);
  });

  it('INV-CD-5 — updateItemQuantity(0) removes the item', async () => {
    const { client, state } = makeMockClient();
    const el = await mountDrawer(readyContext(client));
    await el.addItem({ product: makeProduct({ id: 'p1' }), quantity: 2 });
    await el.addItem({ product: makeProduct({ id: 'p2' }), quantity: 1 });
    const p1 = (el as any).cart.items.find((i: any) => i.product_id === 'p1');
    await el.updateItemQuantity((el as any).buildItemSignature(p1), 0);
    const last = state.updateCalls[state.updateCalls.length - 1]?.body;
    expect(last?.items?.length).toBe(1);
    expect(last?.items?.[0]?.product_id).toBe('p2');
  });

  it('INV-CD-5b — B4: update per-riga non collassa righe stesso prodotto', async () => {
    const { client, state } = makeMockClient();
    const el = await mountDrawer(readyContext(client));
    // due righe stesso prodotto, occurrence (slot) diversi
    await el.addItem({ product: makeProduct({ id: 'p1' }), quantity: 1, extras: { occurrence_id: 'o1' } });
    await el.addItem({ product: makeProduct({ id: 'p1' }), quantity: 1, extras: { occurrence_id: 'o2' } });
    const items = (el as any).cart.items;
    expect(items.length).toBe(2); // NON fuse
    // rimuovo solo la riga occurrence o1
    const lineO1 = items.find((i: any) => i.occurrence_id === 'o1');
    await el.updateItemQuantity((el as any).buildItemSignature(lineO1), 0);
    const last = state.updateCalls[state.updateCalls.length - 1]?.body;
    expect(last?.items?.length).toBe(1);
    expect(last?.items?.[0]?.occurrence_id).toBe('o2'); // resta l'altra riga
  });

  it('INV-CD-5d — R2: addItem propaga extra_selections nel body PATCH', async () => {
    const { client, state } = makeMockClient();
    const el = await mountDrawer(readyContext(client));
    await el.addItem({
      product: makeProduct({ id: 'p1' }),
      quantity: 1,
      extras: { extra_selections: { optional_ids: ['e1'], radio_picks: { size: 'L' } } },
    });
    const body = state.updateCalls[state.updateCalls.length - 1]?.body;
    expect(body?.items?.[0]?.extra_selections).toEqual({
      optional_ids: ['e1'],
      radio_picks: { size: 'L' },
    });
  });

  it('INV-CD-5e — R4: addItem propaga service_custom_request + booking nel body PATCH', async () => {
    const { client, state } = makeMockClient();
    const el = await mountDrawer(readyContext(client));
    await el.addItem({
      product: makeProduct({ id: 'p1' }),
      quantity: 1,
      extras: {
        service_custom_request: true,
        booking_date: '2099-06-01',
        booking_start_time: '10:00',
        booking_end_time: '11:00',
        rental_notes: 'Pomeriggio se possibile',
      },
    });
    const item = state.updateCalls[state.updateCalls.length - 1]?.body?.items?.[0];
    expect(item?.service_custom_request).toBe(true);
    expect(item?.booking_date).toBe('2099-06-01');
    expect(item?.booking_start_time).toBe('10:00');
    expect(item?.rental_notes).toBe('Pomeriggio se possibile');
  });

  it('INV-CD-5f — R4: richiesta custom è riga distinta da slot standard', async () => {
    const { client, state } = makeMockClient();
    const el = await mountDrawer(readyContext(client));
    // Slot standard (no custom request) e richiesta custom stesso prodotto/orario:
    // signature diversa → due righe, non un merge.
    await el.addItem({
      product: makeProduct({ id: 'p1' }),
      quantity: 1,
      extras: { booking_date: '2099-06-01', booking_start_time: '10:00', booking_end_time: '11:00' },
    });
    await el.addItem({
      product: makeProduct({ id: 'p1' }),
      quantity: 1,
      extras: {
        service_custom_request: true,
        booking_date: '2099-06-01',
        booking_start_time: '10:00',
        booking_end_time: '11:00',
      },
    });
    const items = state.updateCalls[state.updateCalls.length - 1]?.body?.items ?? [];
    expect(items.length).toBe(2);
  });

  it('INV-CD-5c — B5: segnale storage da altra tab → refetch del cart', async () => {
    const { client, state } = makeMockClient();
    const el = await mountDrawer(readyContext(client));
    await el.addItem({ product: makeProduct({ id: 'p1' }), quantity: 1 });
    const before = state.getCalls.length;
    // un'altra tab (stesso slug 'demo') ha mutato il cart → segnale storage
    window.dispatchEvent(
      new StorageEvent('storage', { key: 'afianco_cart_touch_demo', newValue: '999' }),
    );
    await new Promise((r) => setTimeout(r, 0));
    expect(state.getCalls.length).toBeGreaterThan(before); // ha rifetchato
  });

  it('INV-CD-6 — cart_id persisted in localStorage per slug', async () => {
    const { client } = makeMockClient({ slug: 'mybiz' });
    const ctx = readyContext(client, 'mybiz');
    const el = await mountDrawer(ctx);
    await el.addItem({ product: makeProduct({ id: 'p1' }), quantity: 1 });
    expect(localStorage.getItem(`${STORAGE_PREFIX}mybiz`)).toBe('cart_1');
  });

  it('INV-CD-7 — cart_id loaded from localStorage at init (re-hydrate)', async () => {
    localStorage.setItem(`${STORAGE_PREFIX}demo`, 'cart_existing_123');
    const { client, state } = makeMockClient();
    // Pre-populate state cart for the GET to return real data
    state.cart = makeCart({ id: 'cart_existing_123', item_count: 2 });
    const el = await mountDrawer(readyContext(client));
    // Wait for the async loadPersistedCart
    await new Promise((r) => setTimeout(r, 0));
    await el.updateComplete;
    expect(state.getCalls).toContain('cart_existing_123');
  });

  it('INV-CD-13 — stale cart_id (404) viene rimosso da localStorage', async () => {
    localStorage.setItem(`${STORAGE_PREFIX}demo`, 'cart_stale');
    const { client } = makeMockClient({ getThrows: true });
    const el = await mountDrawer(readyContext(client));
    await new Promise((r) => setTimeout(r, 0));
    await el.updateComplete;
    expect(localStorage.getItem(`${STORAGE_PREFIX}demo`)).toBeNull();
  });

  it('INV-CD-8 — open/close state + custom events', async () => {
    const { client } = makeMockClient();
    const el = await mountDrawer(readyContext(client));
    let openedFired = false;
    let closedFired = false;
    el.addEventListener('afianco:cart-opened', () => {
      openedFired = true;
    });
    el.addEventListener('afianco:cart-closed', () => {
      closedFired = true;
    });
    el.setOpen(true);
    expect(el.open).toBe(true);
    expect(openedFired).toBe(true);
    el.setOpen(false);
    expect(el.open).toBe(false);
    expect(closedFired).toBe(true);
  });

  it('INV-CD-8 — toggle() switches state', async () => {
    const { client } = makeMockClient();
    const el = await mountDrawer(readyContext(client));
    expect(el.open).toBe(false);
    el.toggle();
    expect(el.open).toBe(true);
    el.toggle();
    expect(el.open).toBe(false);
  });

  it('INV-CD-9 — Checkout CTA dispatcha afianco:checkout-requested with cart payload', async () => {
    const { client } = makeMockClient();
    const el = await mountDrawer(readyContext(client));
    await el.addItem({ product: makeProduct({ id: 'p1' }), quantity: 1 });

    let detail: { cart_id: string } | null = null;
    el.addEventListener('afianco:checkout-requested', (e) => {
      detail = (e as CustomEvent<{ cart_id: string }>).detail;
    });

    el.setOpen(true);
    await el.updateComplete;
    const cta = el.shadowRoot?.querySelector('.checkout-cta') as HTMLButtonElement;
    expect(cta).toBeTruthy();
    cta.click();
    expect(detail).toBeTruthy();
    expect(detail!.cart_id).toBe('cart_1');
  });

  it('INV-CD-10 — afianco:cart-updated dispatched ad ogni mutazione', async () => {
    const { client } = makeMockClient();
    const el = await mountDrawer(readyContext(client));
    let count = 0;
    el.addEventListener('afianco:cart-updated', () => {
      count += 1;
    });
    await el.addItem({ product: makeProduct({ id: 'p1' }), quantity: 1 });
    expect(count).toBe(1);
    await el.addItem({ product: makeProduct({ id: 'p2' }), quantity: 2 });
    expect(count).toBe(2);
  });

  it('INV-CD-12 — auto-open opens drawer dopo primo add', async () => {
    const { client } = makeMockClient();
    const el = await mountDrawer(readyContext(client));
    el.autoOpen = true;
    expect(el.open).toBe(false);
    await el.addItem({ product: makeProduct(), quantity: 1 });
    expect(el.open).toBe(true);
  });

  it('autoOpen=false NON apre il drawer', async () => {
    const { client } = makeMockClient();
    const el = await mountDrawer(readyContext(client));
    el.autoOpen = false;
    await el.addItem({ product: makeProduct(), quantity: 1 });
    expect(el.open).toBe(false);
  });

  it('INV-CD-2 — document listener afianco:add-to-cart triggers addItem', async () => {
    const { client, state } = makeMockClient();
    const el = await mountDrawer(readyContext(client));
    // Simulate event from anywhere in document
    document.dispatchEvent(
      new CustomEvent('afianco:add-to-cart', {
        bubbles: true,
        composed: true,
        detail: {
          product: makeProduct({ id: 'pdoc' }),
          quantity: 4,
        },
      }),
    );
    // wait for async
    await new Promise((r) => setTimeout(r, 0));
    await el.updateComplete;
    expect(state.updateCalls.length).toBeGreaterThan(0);
    expect(state.updateCalls[0]?.body.items?.[0]).toMatchObject({
      product_id: 'pdoc',
      quantity: 4,
    });
  });

  it('removes the document listener on disconnect (no leak)', async () => {
    const { client, state } = makeMockClient();
    const el = await mountDrawer(readyContext(client));
    document.body.removeChild(el);
    // After disconnect, event should not trigger handler
    document.dispatchEvent(
      new CustomEvent('afianco:add-to-cart', {
        bubbles: true,
        composed: true,
        detail: {
          product: makeProduct({ id: 'p-leak' }),
          quantity: 1,
        },
      }),
    );
    await new Promise((r) => setTimeout(r, 0));
    expect(state.updateCalls.length).toBe(0);
  });
});
