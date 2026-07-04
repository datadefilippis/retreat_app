/**
 * Legal docs service — Wave GDPR-Admin Phase C (2026-05-16).
 *
 * Thin fetch wrapper for the public legal endpoints. No auth, no
 * tokens — these endpoints are public by design (users must read
 * the legal docs before signing up).
 *
 * Browser-cache friendly: backend sets Cache-Control: public,
 * max-age=300, so repeated views during a single signup flow are
 * served from cache.
 */

import axios from 'axios';

const API_BASE =
  process.env.REACT_APP_BACKEND_URL ||
  process.env.REACT_APP_API_URL ||
  '';

/**
 * Fetch a legal document.
 * @param {"privacy"|"terms"} docType
 * @param {"it"|"en"|"de"|"fr"} locale - falls back to "it" if unknown
 * @returns {Promise<{content: string, locale_actual: string, locale_requested: string,
 *                   doc_type: string, is_draft: boolean, version_tag: string,
 *                   available_locales: string[]}>}
 */
export async function fetchLegalDocument(docType, locale) {
  if (!['privacy', 'terms'].includes(docType)) {
    throw new Error(`Invalid docType: ${docType}`);
  }
  const params = locale ? `?lang=${encodeURIComponent(locale)}` : '';
  const url = `${API_BASE}/api/legal/${docType}${params}`;
  const res = await axios.get(url, {
    // No Authorization header — public endpoints
    headers: { Accept: 'application/json' },
  });
  return res.data;
}

/**
 * Fetch current legal version metadata.
 * Used by signup to display "Accept terms v1.0:abc123 (in IT)".
 */
export async function fetchLegalVersions() {
  const url = `${API_BASE}/api/legal/versions`;
  const res = await axios.get(url, {
    headers: { Accept: 'application/json' },
  });
  return res.data;
}

// ─── Wave GDPR-Commerce Phase CG-2 ─────────────────────────────────────
//
// Per-store merchant legal docs (the merchant is the Data Controller
// toward end customers; afianco is Data Processor). These endpoints
// are PUBLIC, locale is NOT a query param — the merchant chose ONE
// display_locale in admin and that is what all customers see.

/**
 * Fetch the merchant's published Privacy Policy for a storefront.
 *
 * Returned envelope (always 200 when slug is valid):
 *   {
 *     content: string,                  // markdown ("" when not yet published)
 *     display_locale: "it"|"en"|"de"|"fr"|null,
 *     status: "not_configured"|"draft"|"published"|"stale_draft",
 *     version_tag: string|null,
 *     version_hash: string|null,
 *     version_string: string|null,
 *     doc_type: "privacy",
 *     merchant_email: string|null,
 *     store_name: string,
 *     published_at: string|null
 *   }
 *
 * @param {string} slug — storefront slug
 */
export async function fetchStorefrontPrivacy(slug) {
  if (!slug) throw new Error('fetchStorefrontPrivacy: slug required');
  const url = `${API_BASE}/api/legal/storefront/${encodeURIComponent(slug)}/privacy`;
  const res = await axios.get(url, { headers: { Accept: 'application/json' } });
  return res.data;
}

/**
 * Fetch the merchant's published Terms of Service for a storefront.
 * Same envelope shape as fetchStorefrontPrivacy with doc_type="terms".
 */
export async function fetchStorefrontTerms(slug) {
  if (!slug) throw new Error('fetchStorefrontTerms: slug required');
  const url = `${API_BASE}/api/legal/storefront/${encodeURIComponent(slug)}/terms`;
  const res = await axios.get(url, { headers: { Accept: 'application/json' } });
  return res.data;
}

/**
 * Fetch the per-store legal version metadata (no content body).
 *
 * Used by:
 *   - The storefront signup form to stamp accepted_terms_version on
 *     the new customer record at the live published snapshot.
 *   - The customer portal to detect a stale accepted_terms_version
 *     and trigger the re-consent modal (CG-4).
 */
export async function fetchStorefrontLegalMetadata(slug) {
  if (!slug) throw new Error('fetchStorefrontLegalMetadata: slug required');
  const url = `${API_BASE}/api/legal/storefront/${encodeURIComponent(slug)}/metadata`;
  const res = await axios.get(url, { headers: { Accept: 'application/json' } });
  return res.data;
}


/**
 * Wave GDPR-Admin Phase E — fetch the locale-aware sub-processor registry.
 *
 * Returned shape:
 *   {
 *     locale_actual: string, locale_requested: string,
 *     version_tag: string, version_string: string,
 *     binding_locale: "it",
 *     controller: { name, city, country, email },
 *     sub_processors: [
 *       { id, name, country_code, is_eu_eea, url,
 *         purpose, data, safeguard }
 *     ]
 *   }
 *
 * @param {"it"|"en"|"de"|"fr"} locale
 */
export async function fetchSubProcessors(locale) {
  const params = locale ? `?lang=${encodeURIComponent(locale)}` : '';
  const url = `${API_BASE}/api/legal/sub-processors${params}`;
  const res = await axios.get(url, {
    headers: { Accept: 'application/json' },
  });
  return res.data;
}


// ─── Wave GDPR-Commerce Piece 1b (2026-05-19) ───────────────────────────
//
// Tokenised marketing-consent revocation. Public, no auth — the
// token IS the credential. Mirrors the GDPR Art. 7(3) symmetry
// requirement: the customer (guest or registered) can opt out with
// one click via a link the merchant embeds in newsletter footers.

/**
 * Preview an unsubscribe link.
 *
 * Two-step UX: the email client (and aggressive spam scanners) sometimes
 * pre-fetches links — issuing the actual revocation on GET would lead
 * to accidental opt-outs. So the GET only VALIDATES + returns the masked
 * email + idempotency hint; the user clicks "Confirm" → POST to act.
 *
 * @param {string} token - JWT from the URL path /u/<token>
 * @returns {Promise<{valid: true, email_masked: string,
 *                    organization_name: string|null,
 *                    already_unsubscribed: boolean}>}
 *
 * On 401/410 axios throws; the page distinguishes via err.response.status
 * + err.response.data.detail.error_code ("invalid_token" / "expired_token").
 */
export async function previewMarketingUnsubscribe(token) {
  if (!token || typeof token !== 'string') {
    throw new Error('previewMarketingUnsubscribe: token required');
  }
  const url = `${API_BASE}/api/marketing-consent/unsubscribe/${encodeURIComponent(token)}`;
  const res = await axios.get(url, {
    headers: { Accept: 'application/json' },
  });
  return res.data;
}

/**
 * Execute the unsubscribe action. Idempotent on the server side — the
 * UI can safely retry, the customer's intent is recorded each time.
 *
 * @param {string} token
 * @returns {Promise<{success: true, applied_to_account: boolean}>}
 */
export async function confirmMarketingUnsubscribe(token) {
  if (!token || typeof token !== 'string') {
    throw new Error('confirmMarketingUnsubscribe: token required');
  }
  const url = `${API_BASE}/api/marketing-consent/unsubscribe/${encodeURIComponent(token)}/confirm`;
  const res = await axios.post(url, null, {
    headers: { Accept: 'application/json' },
  });
  return res.data;
}
