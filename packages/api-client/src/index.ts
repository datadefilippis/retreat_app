/**
 * @afianco/api-client — Phase 1 Step 20 (Track B).
 *
 * Typed fetch wrapper per il widget embed Stream A. Centralizza:
 *   - base URL configurabile (default: https://api.afianco.app)
 *   - X-Afianco-Store-Slug header automatico per ogni richiesta
 *   - Idempotency-Key UUID v4 generato per mutazioni (POST/PATCH/DELETE)
 *   - Customer JWT storage abstraction (localStorage-backed di default,
 *     plug-in custom per merchant con stricter security requirements)
 *   - Retry su 429 + 5xx con exponential backoff
 *   - Typed responses via @afianco/shared-types
 *
 * Public API:
 *   `createAfiancoClient({ slug, baseUrl?, tokenStorage? })`
 *
 * Esempio:
 *   const client = createAfiancoClient({ slug: 'bottega-demo' });
 *   const init = await client.embed.getInit();   // EmbedInitResponse
 *   const cart = await client.embed.cart.create();
 *   await client.embed.cart.update(cart.id, {
 *     items: [{ product_id: 'p1', quantity: 2 }],
 *   });
 */

export * from './client.js';
export * from './errors.js';
export * from './token-storage.js';

// Re-export types for downstream convenience (Lit widget importa solo
// '@afianco/api-client' senza dover anche dichiarare '@afianco/shared-types').
export type * from '@afianco/shared-types';
