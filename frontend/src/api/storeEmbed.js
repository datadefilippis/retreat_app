/**
 * Store Embed API client — Track E Step 2.3.
 *
 * Wraps the 2 endpoints exposed by routers/store_embed.py:
 *   - GET   /api/stores/{store_id}/embed-info
 *   - PATCH /api/stores/{store_id}/allowed-origins
 *
 * Uses the shared admin client (api/client.js) — same Bearer JWT auth
 * + 401 retry logic + Sentry tagging as the rest of the admin app.
 *
 * Modular design: separato da api/stores.js per coerenza con il backend
 * router separation (single responsibility "embed config").
 */

import api from './client';

export const storeEmbedAPI = {
  /**
   * GET embed config info for one store.
   *
   * Returns:
   *   {
   *     store_id, store_slug, store_name, is_published,
   *     bundle_url, hosted_url, snippet,
   *     allowed_origins: [...], embed_status,
   *   }
   *
   * embed_status: "active" | "no_origins" | "store_unpublished"
   *
   * Errors:
   *   - 401 if not authenticated
   *   - 403 if user.organization_id !== store.organization_id
   *   - 404 if store_id not found (or cross-org access — anti-enumeration)
   */
  getEmbedInfo: (storeId) =>
    api.get(`/api/stores/${storeId}/embed-info`),

  /**
   * PATCH allowed_origins for one store (REPLACES the full list).
   *
   * Args:
   *   storeId: string
   *   allowedOrigins: array of strings (max 10, https:// required, no
   *                   wildcard, max 200 char each)
   *
   * Returns: same shape as getEmbedInfo (post-update).
   *
   * Errors:
   *   - 422 if validation fails (Pydantic _validate_allowed_origins)
   *   - 401/403/404 same as getEmbedInfo
   *
   * Semantica REPLACE: pass the EXACT list desired. For append/remove:
   * GET first, modify the array client-side, PATCH the updated list.
   */
  updateAllowedOrigins: (storeId, allowedOrigins) =>
    api.patch(`/api/stores/${storeId}/allowed-origins`, {
      allowed_origins: allowedOrigins,
    }),

  /**
   * POST compose embed à-la-carte snippet (Fase 3/4).
   *
   * Lo slug e' derivato server-side dallo store (non si passa). Si invia
   * solo la selezione di blocchi + la loro config.
   *
   * Args:
   *   storeId: string
   *   blocks: array di id blocco (es. ['cart-button','categories'])
   *   config: { [blockId]: { [fieldKey]: value } }
   *
   * Returns: { head, elements:[{id,label,html}], singletons:[...], snippet }
   * Errors: 422 se blocco sconosciuto o config invalida; 401/403/404 come sopra.
   */
  composeSnippet: (storeId, blocks, config = {}) =>
    api.post(`/api/stores/${storeId}/embed-snippet`, { blocks, config }),

  /**
   * GET preview token (read-only, breve durata) per l'anteprima live in
   * dashboard. Returns: { token, expires_in, bundle_url, slug }.
   */
  getPreviewToken: (storeId) =>
    api.get(`/api/stores/${storeId}/embed-preview-token`),
};

export default storeEmbedAPI;
