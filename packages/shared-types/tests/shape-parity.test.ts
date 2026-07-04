/**
 * Sentinel tests — Phase 1 Step 19 (Track B).
 *
 * Verifica che ogni TS interface esportata di @afianco/shared-types
 * abbia le proprietà attese (subset minimo). Pin del contract:
 * rimuovere un campo = breaking change widget downstream.
 *
 * NOTA: questi test verificano lo SHAPE TypeScript via runtime check su
 * "object literal" che soddisfano l'interface. TypeScript stesso garantisce
 * il typing al compile-time (`pnpm typecheck`), questi test garantiscono
 * che almeno un oggetto valido esista — utile come smoke level zero.
 */

import { describe, it, expect } from 'vitest';
import type {
  EmbedInitResponse,
  EmbedCategorySummary,
  EmbedCapabilities,
  EmbedCategoriesResponse,
  EmbedCategoryItem,
  EmbedProductCard,
  EmbedProductsResponse,
  EmbedPagination,
  CartResponse,
  CartCreate,
  CartUpdate,
  CartItemInput,
  CartMergeRequest,
  EmbedCheckoutStartRequest,
  EmbedCheckoutStartResponse,
  EmbedPostMessage,
  CustomerSignupRequest,
  CustomerLoginRequest,
  CustomerTokenResponse,
  CustomerProfile,
  ProductType,
  TransactionMode,
  PriceMode,
  EmbedProductSortMode,
  StoreInfo,
} from '../src/index.js';

describe('@afianco/shared-types — shape parity', () => {
  it('EmbedInitResponse — minimal valid sample', () => {
    const sample: EmbedInitResponse = {
      slug: 'bottega-demo',
      org_name: 'Bottega Demo',
      currency: 'EUR',
      storefront_languages: ['it'],
      available_product_types: ['physical', 'service'],
      categories: [],
      capabilities: {
        checkout_stripe_enabled: true,
        cart_enabled: true,
        customer_auth_enabled: true,
      },
      fulfillment_modes: ['shipping', 'local_pickup'],
    };
    expect(sample.slug).toBe('bottega-demo');
    expect(sample.capabilities.cart_enabled).toBe(true);
  });

  it('EmbedCategorySummary + EmbedCategoryItem', () => {
    const summary: EmbedCategorySummary = {
      name: 'Catering',
      slug: 'catering',
      count: 3,
    };
    expect(summary.slug).toBe('catering');

    const item: EmbedCategoryItem = {
      ...summary,
      thumbnail_url: '/uploads/x.jpg',
    };
    expect(item.thumbnail_url).toBe('/uploads/x.jpg');
  });

  it('EmbedCategoriesResponse', () => {
    const resp: EmbedCategoriesResponse = {
      slug: 'bottega-demo',
      categories: [
        { name: 'A', slug: 'a', count: 1, thumbnail_url: null },
      ],
    };
    expect(resp.categories.length).toBe(1);
  });

  it('EmbedProductCard + EmbedProductsResponse', () => {
    const card: EmbedProductCard = {
      id: 'p1',
      name: 'Product',
      currency: 'EUR',
      item_type: 'physical',
      price_mode: 'fixed',
      transaction_mode: 'direct',
    };
    const resp: EmbedProductsResponse = {
      slug: 's',
      currency: 'EUR',
      items: [card],
      pagination: { total: 1, limit: 20, offset: 0, has_more: false },
    };
    expect(resp.items[0]!.id).toBe('p1');
  });

  it('EmbedPagination', () => {
    const p: EmbedPagination = { total: 0, limit: 20, offset: 0, has_more: false };
    expect(p.total).toBe(0);
  });

  it('CartCreate + CartResponse + CartUpdate + CartItemInput', () => {
    const c: CartCreate = { slug: 's' };
    const u: CartUpdate = {
      items: [{ product_id: 'p', quantity: 1 } as CartItemInput],
    };
    const r: CartResponse = {
      id: 'cart_1',
      organization_id: 'org-1',
      items: [],
      item_count: 0,
      subtotal_snapshot: 0,
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
      expires_at: '2026-03-01T00:00:00Z',
      source: 'embed',
    };
    expect(c.slug).toBe('s');
    expect(u.items?.length).toBe(1);
    expect(r.source).toBe('embed');
  });

  it('CartMergeRequest', () => {
    const m: CartMergeRequest = { customer_account_id: 'acc_1' };
    expect(m.customer_account_id).toBe('acc_1');
  });

  it('EmbedCheckoutStartRequest with all auth modes', () => {
    // Mode 1 — guest
    const guest: EmbedCheckoutStartRequest = {
      slug: 's',
      cart_id: 'cart_1',
      customer_name: 'X',
      customer_email: 'x@y.com',
      embed_return_url: 'https://merchant.com/done',
      gdpr_terms_accepted: true,
      gdpr_privacy_accepted: true,
      gdpr_marketing_accepted: false,
      terms_accepted: true,
    };
    expect(guest.cart_id).toBe('cart_1');

    // Mode 3 — signup inline
    const signup: EmbedCheckoutStartRequest = {
      ...guest,
      create_account: true,
      account_password: 'StrongPass!2026',
      account_locale: 'it',
    };
    expect(signup.create_account).toBe(true);
  });

  it('EmbedCheckoutStartResponse', () => {
    const resp: EmbedCheckoutStartResponse = {
      order_id: 'ord_1',
      transaction_mode: 'request',
      order_status: 'draft',
      message: 'ok',
      embed_return_url: 'https://merchant.com/done',
      account_created: false,
    };
    expect(resp.order_id).toBe('ord_1');
  });

  it('EmbedPostMessage', () => {
    const m: EmbedPostMessage = {
      source: 'afianco-embed',
      type: 'checkout_complete',
      order_id: 'ord_1',
      order_status: 'draft',
      payment_status: 'collected',
    };
    expect(m.source).toBe('afianco-embed');
  });

  it('CustomerSignupRequest', () => {
    const r: CustomerSignupRequest = {
      slug: 's',
      email: 'x@y.com',
      name: 'Mario',
      password: 'StrongPass!2026',
      accepted_terms: true,
      accepted_privacy: true,
    };
    expect(r.accepted_privacy).toBe(true);
  });

  it('CustomerLoginRequest + CustomerTokenResponse + CustomerProfile', () => {
    const login: CustomerLoginRequest = { slug: 's', email: 'x@y.com', password: 'p' };
    const profile: CustomerProfile = {
      id: 'acc_1',
      email: 'x@y.com',
      name: 'Mario',
      locale: 'it',
      email_verified: false,
      created_at: '2026-01-01T00:00:00Z',
    };
    const tok: CustomerTokenResponse = {
      access_token: 'eyJ...',
      token_type: 'bearer',
      customer: profile,
    };
    expect(login.slug).toBe('s');
    expect(tok.customer.email).toBe('x@y.com');
  });

  it('Discriminated unions: ProductType / TransactionMode / PriceMode', () => {
    const t: ProductType = 'event_ticket';
    const tm: TransactionMode = 'direct';
    const pm: PriceMode = 'fixed';
    const sort: EmbedProductSortMode = 'price_asc';
    expect(t).toBe('event_ticket');
    expect(tm).toBe('direct');
    expect(pm).toBe('fixed');
    expect(sort).toBe('price_asc');
  });

  it('StoreInfo — all nullable fields', () => {
    const si: StoreInfo = {
      display_name: null,
      contact_email: null,
    };
    expect(si.display_name).toBeNull();
  });
});
