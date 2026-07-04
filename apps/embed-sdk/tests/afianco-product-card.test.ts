/**
 * Sentinel tests for <afianco-product-card> — Phase 1 Step 23.
 *
 * Invariants pinned
 * =================
 *  INV-PC-1   Registered in customElements
 *  INV-PC-2   Renders product injected via .product property (no fetch)
 *  INV-PC-3   CTA label type-aware (price_mode=inquiry vs transaction_mode)
 *  INV-PC-4   Click CTA → dispatch afianco:add-to-cart with product+quantity
 *  INV-PC-5   stock_quantity=0 → CTA disabled + "Esaurito" hint
 *  INV-PC-6   Price formatted via Intl.NumberFormat (currency-aware)
 *  INV-PC-7   No image_url → "No image" placeholder
 *  INV-PC-8   No product/no product-id → error state
 *  INV-PC-9   Shadow DOM presente (CSS isolation)
 */

import { describe, it, expect } from 'vitest';
import {
  AfiancoProductCard,
} from '../src/components/afianco-product-card.js';
import type { EmbedProductCard } from '@afianco/api-client';

function makeProduct(overrides: Partial<EmbedProductCard> = {}): EmbedProductCard {
  return {
    id: 'p-test',
    name: 'Test Product',
    currency: 'EUR',
    unit_price: 9.5,
    description: 'A nice product.',
    image_url: '/uploads/x.jpg',
    category: 'Catering',
    category_slug: 'catering',
    item_type: 'physical',
    price_mode: 'fixed',
    transaction_mode: 'direct',
    ...overrides,
  };
}

async function mountWithProduct(p: EmbedProductCard | null): Promise<AfiancoProductCard> {
  const el = document.createElement('afianco-product-card') as AfiancoProductCard;
  el.product = p;
  document.body.appendChild(el);
  await el.updateComplete;
  return el;
}

describe('<afianco-product-card>', () => {
  it('INV-PC-1 — registered in customElements', () => {
    expect(customElements.get('afianco-product-card')).toBe(AfiancoProductCard);
  });

  it('INV-PC-9 — uses Shadow DOM', async () => {
    const el = await mountWithProduct(makeProduct());
    expect(el.shadowRoot).not.toBeNull();
    document.body.removeChild(el);
  });

  it('INV-PC-2 — renders product injected via property without fetching', async () => {
    const el = await mountWithProduct(makeProduct({ name: 'Pizza Margherita' }));
    const text = el.shadowRoot?.textContent ?? '';
    expect(text).toContain('Pizza Margherita');
    expect(text).toContain('Catering'); // category badge
    expect(text).toContain('A nice product.');
    document.body.removeChild(el);
  });

  it('INV-PC-6 — price formatted via Intl.NumberFormat', async () => {
    const el = await mountWithProduct(makeProduct({ unit_price: 1234.5, currency: 'EUR' }));
    const text = el.shadowRoot?.textContent ?? '';
    // Intl varies by locale but should include amount + currency symbol
    expect(text).toMatch(/1[.,]234[.,]50/);
    document.body.removeChild(el);
  });

  it('INV-PC-3 — CTA label "Aggiungi al carrello" for direct/physical', async () => {
    const el = await mountWithProduct(
      makeProduct({ item_type: 'physical', transaction_mode: 'direct' }),
    );
    const btn = el.shadowRoot?.querySelector('button.cta');
    expect(btn?.textContent?.trim()).toBe('Aggiungi al carrello');
    document.body.removeChild(el);
  });

  it('INV-PC-3 — CTA "Richiedi info" for request mode', async () => {
    const el = await mountWithProduct(
      makeProduct({ transaction_mode: 'request' }),
    );
    const btn = el.shadowRoot?.querySelector('button.cta');
    expect(btn?.textContent?.trim()).toBe('Richiedi info');
    document.body.removeChild(el);
  });

  it('INV-PC-3 — CTA "Acquista biglietto" for event_ticket+direct', async () => {
    const el = await mountWithProduct(
      makeProduct({ item_type: 'event_ticket', transaction_mode: 'direct' }),
    );
    const btn = el.shadowRoot?.querySelector('button.cta');
    expect(btn?.textContent?.trim()).toBe('Acquista biglietto');
    document.body.removeChild(el);
  });

  it('INV-PC-3 — CTA "Iscriviti" for course+direct', async () => {
    const el = await mountWithProduct(
      makeProduct({ item_type: 'course', transaction_mode: 'direct' }),
    );
    const btn = el.shadowRoot?.querySelector('button.cta');
    expect(btn?.textContent?.trim()).toBe('Iscriviti');
    document.body.removeChild(el);
  });

  it('INV-PC-3 — CTA "Richiedi preventivo" for inquiry price_mode', async () => {
    const el = await mountWithProduct(
      makeProduct({ price_mode: 'inquiry', transaction_mode: 'request' }),
    );
    const btn = el.shadowRoot?.querySelector('button.cta');
    expect(btn?.textContent?.trim()).toBe('Richiedi preventivo');
    // Inquiry → "Su richiesta" instead of price
    const text = el.shadowRoot?.textContent ?? '';
    expect(text).toContain('Su richiesta');
    document.body.removeChild(el);
  });

  it('INV-PC-3 — CTA "Richiedi noleggio" for rental+approval', async () => {
    const el = await mountWithProduct(
      makeProduct({ item_type: 'rental', transaction_mode: 'approval' }),
    );
    const btn = el.shadowRoot?.querySelector('button.cta');
    expect(btn?.textContent?.trim()).toBe('Richiedi noleggio');
    document.body.removeChild(el);
  });

  it('INV-PC-4 — click CTA dispatches afianco:add-to-cart with product+quantity', async () => {
    const product = makeProduct({ id: 'p-evt' });
    const el = await mountWithProduct(product);
    el.quantity = 3;
    await el.updateComplete;

    let received: { product: EmbedProductCard; quantity: number } | null = null;
    el.addEventListener('afianco:add-to-cart', (e) => {
      received = (e as CustomEvent<{ product: EmbedProductCard; quantity: number }>).detail;
    });

    const btn = el.shadowRoot?.querySelector('button.cta') as HTMLButtonElement;
    btn.click();

    expect(received).toBeTruthy();
    expect(received!.product.id).toBe('p-evt');
    expect(received!.quantity).toBe(3);
    document.body.removeChild(el);
  });

  it('INV-PC-4 — quantity clamped to min 1 (no zero or negative)', async () => {
    const el = await mountWithProduct(makeProduct());
    el.quantity = 0;
    await el.updateComplete;

    let qty = -1;
    el.addEventListener('afianco:add-to-cart', (e) => {
      qty = (e as CustomEvent<{ quantity: number }>).detail.quantity;
    });
    const btn = el.shadowRoot?.querySelector('button.cta') as HTMLButtonElement;
    btn.click();
    expect(qty).toBe(1);
    document.body.removeChild(el);
  });

  it('INV-PC-5 — stock_quantity=0 → button disabled + "Esaurito" hint', async () => {
    const el = await mountWithProduct(makeProduct({ stock_quantity: 0 }));
    const btn = el.shadowRoot?.querySelector('button.cta') as HTMLButtonElement;
    expect(btn.disabled).toBe(true);
    const text = el.shadowRoot?.textContent ?? '';
    expect(text).toContain('Esaurito');
    document.body.removeChild(el);
  });

  it('INV-PC-5 — stock_quantity<=3 → low stock warning, button still active', async () => {
    const el = await mountWithProduct(makeProduct({ stock_quantity: 2 }));
    const btn = el.shadowRoot?.querySelector('button.cta') as HTMLButtonElement;
    expect(btn.disabled).toBe(false);
    const text = el.shadowRoot?.textContent ?? '';
    expect(text).toContain('Solo 2 disponibili');
    document.body.removeChild(el);
  });

  it('INV-PC-5 — disabled button does NOT dispatch event on click', async () => {
    const el = await mountWithProduct(makeProduct({ stock_quantity: 0 }));
    let dispatched = false;
    el.addEventListener('afianco:add-to-cart', () => {
      dispatched = true;
    });
    const btn = el.shadowRoot?.querySelector('button.cta') as HTMLButtonElement;
    btn.click();
    expect(dispatched).toBe(false);
    document.body.removeChild(el);
  });

  it('INV-PC-7 — no image_url → placeholder text', async () => {
    const el = await mountWithProduct(makeProduct({ image_url: null }));
    const text = el.shadowRoot?.textContent ?? '';
    expect(text).toContain('No image');
    document.body.removeChild(el);
  });

  it('INV-PC-7 — image_url set → <img> rendered with alt', async () => {
    const el = await mountWithProduct(makeProduct({ image_url: '/x.jpg', name: 'Test X' }));
    const img = el.shadowRoot?.querySelector('img');
    expect(img).not.toBeNull();
    expect(img?.getAttribute('src')).toBe('/x.jpg');
    expect(img?.getAttribute('alt')).toBe('Test X');
    document.body.removeChild(el);
  });

  it('INV-PC-8 — no product + no product-id → error state', async () => {
    const el = document.createElement('afianco-product-card') as AfiancoProductCard;
    // Provide a 'ready' context so the loading state passes
    el.ctx = { client: null, init: null, status: 'ready', error: null };
    document.body.appendChild(el);
    await el.updateComplete;
    const text = el.shadowRoot?.textContent ?? '';
    expect(text.toLowerCase()).toContain('missing');
    document.body.removeChild(el);
  });

  it('reactive: re-renders on product property change', async () => {
    const el = await mountWithProduct(makeProduct({ name: 'First' }));
    expect(el.shadowRoot?.textContent).toContain('First');

    el.product = makeProduct({ name: 'Second', id: 'p-2' });
    await el.updateComplete;
    expect(el.shadowRoot?.textContent).toContain('Second');
    expect(el.shadowRoot?.textContent).not.toContain('First');

    document.body.removeChild(el);
  });
});
