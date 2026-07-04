/**
 * AfiancoClient — typed fetch wrapper per il widget Stream A.
 */

import type {
  EmbedInitResponse,
  EmbedCategoriesResponse,
  EmbedProductsResponse,
  EmbedProductsQuery,
  EmbedProductDetail,
  EmbedAvailabilityResponse,
  EmbedAvailabilityQuery,
  EmbedPricePreviewRequest,
  EmbedPricePreviewResponse,
  EmbedCouponValidateRequest,
  EmbedCouponValidateResponse,
  EmbedShippingOptionsResponse,
  CartCreate,
  CartUpdate,
  CartResponse,
  CartMergeRequest,
  EmbedCheckoutStartRequest,
  EmbedCheckoutStartResponse,
  CustomerSignupRequest,
  CustomerLoginRequest,
  CustomerTokenResponse,
  CustomerProfile,
  CustomerProfileUpdate,
  CustomerOrderSummary,
  ForgotPasswordRequest,
  ResetPasswordRequest,
  VerifyEmailRequest,
  // Track E Step 2.4.6 — customer assets
  CustomerDownloadsResponse,
  CustomerBookingsResponse,
  CustomerReservationsResponse,
  CustomerCoursesResponse,
  CustomerCourseDetail,
  CustomerCoursePlayUrlResponse,
  CustomerCourseProgressUpdate,
} from '@afianco/shared-types';

import {
  AfiancoApiError,
  AfiancoAuthError,
  AfiancoLockedError,
  AfiancoRateLimitError,
  AfiancoValidationError,
} from './errors.js';

import {
  LocalStorageTokenStorage,
  type TokenStorage,
} from './token-storage.js';

// ── UUID v4 lightweight (no deps) ──────────────────────────────────────

/**
 * Generate a RFC 4122 v4 UUID. Uses crypto.randomUUID() if available
 * (modern browsers + Node 14.17+), falls back to Math.random based gen
 * (sufficient for Idempotency-Key entropy — non per security tokens).
 */
function uuidv4(): string {
  // Prefer cryptographic implementation
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  // Fallback: less random but still unique enough for idempotency keys
  let r: number;
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

// ── Options ─────────────────────────────────────────────────────────────

export interface AfiancoClientOptions {
  /** Store slug (merchant identifier). Required. */
  slug: string;
  /**
   * Base URL del backend afianco. Default: https://api.afianco.app
   * Per dev locale: 'http://localhost:8000'
   */
  baseUrl?: string;
  /**
   * Pluggable token storage. Default: LocalStorageTokenStorage con key
   * `afianco_token_<slug>`. Pass MemoryTokenStorage per volatile-only.
   */
  tokenStorage?: TokenStorage;
  /**
   * Max retry attempts su 429/5xx. Default: 3 (con exponential backoff
   * 500ms / 1s / 2s).
   */
  maxRetries?: number;
  /**
   * Optional custom fetch (testing, custom user-agent, ecc.).
   * Default: global fetch.
   */
  fetchFn?: typeof fetch;
  /**
   * Token preview READ-ONLY (Fase 5). Quando presente, viene allegato
   * come header `X-Afianco-Preview-Token` + query `preview_token` (per il
   * preflight) → il backend autorizza le GET embed (init/products/categories)
   * dall'origin dell'admin senza che sia negli allowed_origins pubblici.
   * Usato SOLO dall'anteprima live nella dashboard.
   */
  previewToken?: string;
}

// ── Internal request helper ────────────────────────────────────────────

type HttpMethod = 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE';

interface RequestOpts {
  method: HttpMethod;
  path: string;
  query?: Record<string, string | number | boolean | undefined | null>;
  body?: unknown;
  /**
   * When true, the client adds `Authorization: Bearer <token>` if a
   * token is stored. When false, the request is always anonymous.
   * Default false (most embed endpoints accept Bearer as optional).
   */
  withAuth?: boolean;
  /**
   * Optional explicit Idempotency-Key override. By default the client
   * generates a fresh uuidv4() for every non-GET request. Passing this
   * lets callers replay a deterministic key — useful for explicit retry
   * flows where the network reply was lost mid-flight (Sprint 1 W1.3).
   *
   * Backend caches the response for 24h keyed on (key, path, body
   * digest) so replay is safe.
   */
  idempotencyKey?: string;
}

// ── Public client class ────────────────────────────────────────────────

export class AfiancoClient {
  readonly slug: string;
  readonly baseUrl: string;
  readonly tokenStorage: TokenStorage;
  private readonly maxRetries: number;
  private readonly fetchFn: typeof fetch;
  private readonly previewToken?: string;

  constructor(opts: AfiancoClientOptions) {
    if (!opts.slug) {
      throw new Error('AfiancoClient: `slug` is required');
    }
    this.slug = opts.slug;
    this.baseUrl = (opts.baseUrl ?? 'https://api.afianco.app').replace(/\/+$/, '');
    this.tokenStorage =
      opts.tokenStorage ?? new LocalStorageTokenStorage(`afianco_token_${opts.slug}`);
    this.maxRetries = Math.max(0, opts.maxRetries ?? 3);
    this.fetchFn = opts.fetchFn ?? fetch.bind(globalThis);
    this.previewToken = opts.previewToken;
  }

  // ── Core request ─────────────────────────────────────────────────────

  /**
   * Path patterns where the slug is ALREADY visible in the URL path,
   * so we don't need to also add `?slug=...` query param (would be
   * redundant + clutter). Routes outside these patterns get the slug
   * injected as query param to ensure the backend DynamicCORSMiddleware
   * can read it on the browser preflight OPTIONS (where custom headers
   * are NOT sent — preflight-safe slug visibility).
   *
   * Track E Step 2.4.3 — closing the preflight CORS gap.
   */
  private static readonly _SLUG_IN_PATH_RE = new RegExp(
    String.raw`^/api/public/(embed|ai-site)/(init|categories|products)/`,
  );

  private async request<T>(opts: RequestOpts): Promise<T> {
    // Inject `slug` query param for preflight CORS visibility unless the
    // slug is already in the URL path (init/categories/products routes).
    // Browser preflight OPTIONS doesn't send custom headers, so the slug
    // MUST be in the URL for the middleware to authorize the request.
    const needsSlugInQuery =
      !AfiancoClient._SLUG_IN_PATH_RE.test(opts.path) &&
      !(opts.query && 'slug' in opts.query);
    let effectiveQuery = needsSlugInQuery
      ? { ...(opts.query ?? {}), slug: this.slug }
      : opts.query;

    // Fase 5 — preview token in query per la visibilita' sul preflight
    // OPTIONS (i custom header non sono inviati sul preflight).
    if (this.previewToken) {
      effectiveQuery = { ...(effectiveQuery ?? {}), preview_token: this.previewToken };
    }

    const url = this.buildUrl(opts.path, effectiveQuery);
    const headers: Record<string, string> = {
      'Accept': 'application/json',
      'X-Afianco-Store-Slug': this.slug,
    };

    // Fase 5 — preview token anche come header sulla richiesta reale.
    if (this.previewToken) {
      headers['X-Afianco-Preview-Token'] = this.previewToken;
    }

    if (opts.body !== undefined) {
      headers['Content-Type'] = 'application/json';
    }

    // Idempotency-Key per le mutazioni (anti-doppio-ordine middleware
    // Phase 0 Step 8 + Sprint 1 W1.3 — pinned by sentinel
    // TestSEC_E_8_3_SDKIdempotencyKeys). Caller puo' passare
    // opts.idempotencyKey per replay esplicito (es. retry su network
    // failure mid-flight): backend cache 24h su (key, path, body digest).
    if (opts.method !== 'GET') {
      headers['Idempotency-Key'] = opts.idempotencyKey ?? uuidv4();
    }

    // Optional Bearer
    if (opts.withAuth) {
      const token = this.tokenStorage.get();
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
    }

    return this.requestWithRetry<T>(url, opts.method, headers, opts.body, 0);
  }

  private async requestWithRetry<T>(
    url: string,
    method: HttpMethod,
    headers: Record<string, string>,
    body: unknown,
    attempt: number,
  ): Promise<T> {
    const init: RequestInit = {
      method,
      headers,
      // credentials: 'omit' di default → no cookie cross-origin (widget
      // usa Bearer JWT in header, niente cookie SameSite issues).
      credentials: 'omit',
      // mode 'cors' implicit per cross-origin fetch
    };
    if (body !== undefined) {
      init.body = JSON.stringify(body);
    }

    let response: Response;
    try {
      response = await this.fetchFn(url, init);
    } catch (e) {
      // Network error → optional retry
      if (attempt < this.maxRetries) {
        await this.backoff(attempt);
        return this.requestWithRetry<T>(url, method, headers, body, attempt + 1);
      }
      throw new AfiancoApiError(0, e, `network error: ${(e as Error)?.message ?? e}`);
    }

    // Retry on 429 / 5xx
    if (
      (response.status === 429 || (response.status >= 500 && response.status < 600)) &&
      attempt < this.maxRetries
    ) {
      // Honor Retry-After header if present
      const retryAfter = parseRetryAfter(response.headers.get('retry-after'));
      await this.backoff(attempt, retryAfter);
      return this.requestWithRetry<T>(url, method, headers, body, attempt + 1);
    }

    return this.parseResponse<T>(response);
  }

  private async parseResponse<T>(response: Response): Promise<T> {
    // 204 No Content
    if (response.status === 204) {
      return undefined as T;
    }

    let payload: unknown = null;
    const contentType = response.headers.get('content-type') ?? '';

    if (contentType.includes('application/json')) {
      try {
        payload = await response.json();
      } catch {
        payload = null;
      }
    } else {
      payload = await response.text().catch(() => null);
    }

    if (response.ok) {
      return payload as T;
    }

    // Error mapping
    const status = response.status;
    if (status === 401 || status === 403) {
      throw new AfiancoAuthError(status, payload);
    }
    // Sprint 3 W3.2 — 423 Locked (account lockout Onda 29)
    if (status === 423) {
      let unlockAt: string | null = null;
      const det = (payload as Record<string, unknown> | null)?.detail;
      if (det && typeof det === 'object' && 'unlock_at' in det) {
        const v = (det as Record<string, unknown>).unlock_at;
        if (typeof v === 'string') unlockAt = v;
      }
      throw new AfiancoLockedError(unlockAt, payload);
    }
    if (status === 429) {
      const ra = parseRetryAfter(response.headers.get('retry-after'));
      throw new AfiancoRateLimitError(ra, payload);
    }
    if (status === 400) {
      // Extract error code if backend returned {detail: {error: "..."}}
      let code: string | null = null;
      const det = (payload as Record<string, unknown> | null)?.detail;
      if (det && typeof det === 'object' && 'error' in det) {
        const v = (det as Record<string, unknown>).error;
        if (typeof v === 'string') code = v;
      }
      throw new AfiancoValidationError(code, payload);
    }

    throw new AfiancoApiError(status, payload);
  }

  private buildUrl(
    path: string,
    query?: Record<string, string | number | boolean | undefined | null>,
  ): string {
    const url = new URL(this.baseUrl + path);
    if (query) {
      for (const [k, v] of Object.entries(query)) {
        if (v === undefined || v === null) continue;
        url.searchParams.set(k, String(v));
      }
    }
    return url.toString();
  }

  private async backoff(attempt: number, retryAfterSec?: number | null): Promise<void> {
    let waitMs: number;
    if (retryAfterSec != null && retryAfterSec > 0) {
      waitMs = retryAfterSec * 1000;
    } else {
      // Exponential 500ms / 1s / 2s
      waitMs = 500 * Math.pow(2, attempt);
    }
    await new Promise((r) => setTimeout(r, waitMs));
  }

  // ── EMBED PUBLIC API ─────────────────────────────────────────────────

  readonly embed = {
    /**
     * GET /api/public/embed/init/{slug}
     *
     * Sprint 4 W4.5 — `bypassCache` opt forza cache-bust via timestamp
     * query param `?_v=<ms>`. Il backend ignora il param ma il browser
     * lo vede come URL diversa -> bypassa cache locale + intermediary
     * proxies -> backend cache check via ETag (304 se nessun cambio).
     * Usato dal widget re-fetch periodico (polling 90s) per pickup
     * cambi merchant (lingua, brand_color, custom_nav_links).
     */
    getInit: async (opts: { bypassCache?: boolean } = {}): Promise<EmbedInitResponse> =>
      this.request<EmbedInitResponse>({
        method: 'GET',
        path: `/api/public/embed/init/${encodeURIComponent(this.slug)}`,
        query: opts.bypassCache ? { _v: String(Date.now()) } : undefined,
      }),

    /** GET /api/public/embed/categories/{slug} */
    getCategories: async (
      opts: { withThumbnail?: boolean; includeEmpty?: boolean } = {},
    ): Promise<EmbedCategoriesResponse> =>
      this.request<EmbedCategoriesResponse>({
        method: 'GET',
        path: `/api/public/embed/categories/${encodeURIComponent(this.slug)}`,
        query: {
          with_thumbnail: opts.withThumbnail,
          include_empty: opts.includeEmpty,
        },
      }),

    /** GET /api/public/embed/products/{slug} */
    getProducts: async (query: EmbedProductsQuery = {}): Promise<EmbedProductsResponse> =>
      this.request<EmbedProductsResponse>({
        method: 'GET',
        path: `/api/public/embed/products/${encodeURIComponent(this.slug)}`,
        query: {
          category: query.category,
          type: query.type,
          sort: query.sort,
          limit: query.limit,
          offset: query.offset,
          // Track E Step 5.1 — full-text search query (?q=...)
          q: query.q,
        },
      }),

    /**
     * GET /api/public/embed/products/{slug}/{product_id}
     *
     * Track E Step 2.4.5 → 2.4.6 — product detail TYPE-AWARE per il drawer
     * landing. Restituisce shape enriched in base a item_type:
     *   - service: service_options, has_availability_slots, service_duration_minutes
     *   - event_ticket: occurrences (con tier embeddati), attendee_fields
     *   - rental: extras, reservation_flavor, rental_unit
     *   - course: course_lessons_count, course_duration_seconds, access_policy
     */
    getProduct: async (productId: string): Promise<EmbedProductDetail> =>
      this.request<EmbedProductDetail>({
        method: 'GET',
        path: `/api/public/embed/products/${encodeURIComponent(this.slug)}/${encodeURIComponent(productId)}`,
      }),

    /**
     * GET /api/public/embed/products/{slug}/{product_id}/availability
     *
     * Track E Step 2.4.6 — slot disponibili per service products (calendar
     * widget). Max 30 days range. Default oggi → +30g.
     *
     * Args:
     *   productId: service product UUID (deve avere has_availability_slots=true)
     *   query.date_from/date_to: YYYY-MM-DD (default: today → +30d)
     *   query.duration: override durata slot in minuti (default: product service_duration_minutes)
     */
    getProductAvailability: async (
      productId: string,
      query: EmbedAvailabilityQuery = {},
    ): Promise<EmbedAvailabilityResponse> =>
      this.request<EmbedAvailabilityResponse>({
        method: 'GET',
        path: `/api/public/embed/products/${encodeURIComponent(this.slug)}/${encodeURIComponent(productId)}/availability`,
        query: {
          date_from: query.date_from,
          date_to: query.date_to,
          duration: query.duration,
        },
      }),

    /**
     * GET /api/public/embed/products/{slug}/{product_id}/blocked-dates  (R3)
     * Date occupate per un prodotto rental (advisory UX, parità storefront).
     */
    getRentalBlockedDates: async (
      productId: string,
      query: { from: string; to: string },
    ): Promise<{ blocked_dates: string[] }> =>
      this.request<{ blocked_dates: string[] }>({
        method: 'GET',
        path: `/api/public/embed/products/${encodeURIComponent(this.slug)}/${encodeURIComponent(productId)}/blocked-dates`,
        query: { from: query.from, to: query.to },
      }),

    /**
     * GET /api/public/embed/products/{slug}/{product_id}/availability-windows (R3)
     * Finestre [start,end) per rental+flavor=slot. Parità storefront.
     */
    getRentalAvailabilityWindows: async (
      productId: string,
      query: { days?: number } = {},
    ): Promise<Record<string, unknown>> =>
      this.request<Record<string, unknown>>({
        method: 'GET',
        path: `/api/public/embed/products/${encodeURIComponent(this.slug)}/${encodeURIComponent(productId)}/availability-windows`,
        query: { days: query.days },
      }),

    /**
     * POST /api/public/embed/price-preview/{slug}
     *
     * Track E Step 2.4.10 — live price preview (stateless, no order created).
     * Usato dal componente Lit <afianco-price-preview> con debounce 300ms
     * on qty/slot/date/extras change. Rate-limited 60/min per (IP, slug).
     */
    pricePreview: async (
      body: EmbedPricePreviewRequest,
    ): Promise<EmbedPricePreviewResponse> =>
      this.request<EmbedPricePreviewResponse>({
        method: 'POST',
        path: `/api/public/embed/price-preview/${encodeURIComponent(this.slug)}`,
        body,
      }),

    /**
     * POST /api/public/embed/coupons/validate/{slug}
     *
     * Track E Step 4.1 — Coupon dry-run validation per widget checkout.
     * Stateless, no usage increment. Per applicare lo sconto al checkout,
     * passa il `coupon_code` nel EmbedCheckoutStartRequest del checkout.start
     * (backend rivaliderebbe atomicamente con increment).
     */
    validateCoupon: async (
      body: EmbedCouponValidateRequest,
    ): Promise<EmbedCouponValidateResponse> =>
      this.request<EmbedCouponValidateResponse>({
        method: 'POST',
        path: `/api/public/embed/coupons/validate/${encodeURIComponent(this.slug)}`,
        body,
      }),

    /**
     * GET /api/public/embed/shipping-options/{slug}
     *
     * Track E Step 4.2 — Lista shipping options del store per il radio
     * picker nel checkout. Cache 300s lato backend (options cambiano
     * raramente, no atomic state).
     */
    getShippingOptions: async (): Promise<EmbedShippingOptionsResponse> =>
      this.request<EmbedShippingOptionsResponse>({
        method: 'GET',
        path: `/api/public/embed/shipping-options/${encodeURIComponent(this.slug)}`,
      }),

    cart: {
      /** POST /api/public/embed/cart */
      create: async (body: Partial<CartCreate> = {}): Promise<CartResponse> =>
        this.request<CartResponse>({
          method: 'POST',
          path: `/api/public/embed/cart`,
          body: { slug: this.slug, ...body },
        }),

      /** GET /api/public/embed/cart/{cart_id} */
      get: async (cartId: string): Promise<CartResponse> =>
        this.request<CartResponse>({
          method: 'GET',
          path: `/api/public/embed/cart/${encodeURIComponent(cartId)}`,
          query: { slug: this.slug },
        }),

      /** PATCH /api/public/embed/cart/{cart_id} */
      update: async (cartId: string, body: CartUpdate): Promise<CartResponse> =>
        this.request<CartResponse>({
          method: 'PATCH',
          path: `/api/public/embed/cart/${encodeURIComponent(cartId)}`,
          query: { slug: this.slug },
          body,
        }),

      /** DELETE /api/public/embed/cart/{cart_id} */
      clear: async (cartId: string, opts: { hard?: boolean } = {}): Promise<unknown> =>
        this.request({
          method: 'DELETE',
          path: `/api/public/embed/cart/${encodeURIComponent(cartId)}`,
          query: { slug: this.slug, hard: opts.hard },
        }),

      /** POST /api/public/embed/cart/{cart_id}/merge — requires Bearer customer JWT */
      merge: async (cartId: string, body: CartMergeRequest): Promise<CartResponse> =>
        this.request<CartResponse>({
          method: 'POST',
          path: `/api/public/embed/cart/${encodeURIComponent(cartId)}/merge`,
          query: { slug: this.slug },
          body,
          withAuth: true,
        }),
    },

    checkout: {
      /**
       * POST /api/public/embed/checkout/start
       *
       * Supporta i 3 modi auth (guest / authenticated / signup-inline).
       * Quando body.create_account=true e response.customer_access_token
       * arriva, salva automaticamente il token nel TokenStorage.
       */
      start: async (
        body: EmbedCheckoutStartRequest,
      ): Promise<EmbedCheckoutStartResponse> => {
        const resp = await this.request<EmbedCheckoutStartResponse>({
          method: 'POST',
          path: `/api/public/embed/checkout/start`,
          body,
          withAuth: true,
        });
        if (resp.customer_access_token) {
          this.tokenStorage.set(resp.customer_access_token);
        }
        return resp;
      },

      /**
       * GET /api/public/embed/checkout/complete?order_id=...
       *
       * Generally NOT called by JS — il backend serve direttamente l'HTML
       * bridge come redirect target dal Stripe Checkout popup. Helper
       * comodo per build URL del bridge.
       */
      completeUrl: (orderId: string): string =>
        this.buildUrl(`/api/public/embed/checkout/complete`, { order_id: orderId }),
    },
  } as const;

  // ── CUSTOMER AUTH API (Phase 1 F3 embed-ready) ───────────────────────

  readonly customerAuth = {
    /** POST /api/customer-auth/signup */
    signup: async (body: CustomerSignupRequest): Promise<unknown> =>
      this.request({
        method: 'POST',
        path: `/api/customer-auth/signup`,
        body,
      }),

    /** POST /api/customer-auth/login — also stores the token. */
    login: async (body: CustomerLoginRequest): Promise<CustomerTokenResponse> => {
      const resp = await this.request<CustomerTokenResponse>({
        method: 'POST',
        path: `/api/customer-auth/login`,
        body,
      });
      if (resp.access_token) {
        this.tokenStorage.set(resp.access_token);
      }
      return resp;
    },

    /** Logout client-side (drop token). Server token expires on its own. */
    logout: (): void => {
      this.tokenStorage.clear();
    },

    /** POST /api/customer-auth/forgot-password */
    forgotPassword: async (body: ForgotPasswordRequest): Promise<unknown> =>
      this.request({
        method: 'POST',
        path: `/api/customer-auth/forgot-password`,
        body,
      }),

    /** POST /api/customer-auth/reset-password */
    resetPassword: async (body: ResetPasswordRequest): Promise<unknown> =>
      this.request({
        method: 'POST',
        path: `/api/customer-auth/reset-password`,
        body,
      }),

    /** POST /api/customer-auth/verify-email */
    verifyEmail: async (body: VerifyEmailRequest): Promise<unknown> =>
      this.request({
        method: 'POST',
        path: `/api/customer-auth/verify-email`,
        body,
      }),
  } as const;

  // ── CUSTOMER PORTAL API (auth required) ──────────────────────────────

  readonly customer = {
    /** GET /api/customer/me */
    me: async (): Promise<CustomerProfile> =>
      this.request<CustomerProfile>({
        method: 'GET',
        path: `/api/customer/me`,
        withAuth: true,
      }),

    /** PATCH /api/customer/me */
    updateMe: async (body: CustomerProfileUpdate): Promise<CustomerProfile> =>
      this.request<CustomerProfile>({
        method: 'PATCH',
        path: `/api/customer/me`,
        body,
        withAuth: true,
      }),

    /**
     * POST /api/customer/change-password
     * Track E Step 4.4 — change password authenticated.
     * Body: { current_password, new_password }
     */
    changePassword: async (body: {
      current_password: string;
      new_password: string;
    }): Promise<{ message: string }> =>
      this.request<{ message: string }>({
        method: 'POST',
        path: `/api/customer/change-password`,
        body,
        withAuth: true,
      }),

    /**
     * POST /api/customer/me/request-erasure
     * Track E Step 4.4 — GDPR Art. 17 right-to-erasure request.
     * Backend logs the request + notifies ops + replies with SLA (30gg).
     * Body: { reason?: string }
     */
    requestErasure: async (
      body: { reason?: string | null } = {},
    ): Promise<{
      status: string;
      message: string;
      request_id: string;
      estimated_completion_days: number;
    }> =>
      this.request({
        method: 'POST',
        path: `/api/customer/me/request-erasure`,
        body,
        withAuth: true,
      }),

    /**
     * GET /api/customer/orders/{order_id}/receipt
     * Track E Step 4.4 — order receipt PDF download (binary stream).
     * Returns the absolute URL del PDF — il widget naviga (window.open)
     * con Authorization header NON applicabile a download diretti.
     * Workaround: blob fetch + download.
     *
     * Helper urlOnly=true ritorna l'URL stringa per costruire link
     * <a href> (client-side il customer deve essere loggato per scaricare).
     */
    orderReceiptUrl: (orderId: string): string =>
      `${this.baseUrl}/api/customer/orders/${encodeURIComponent(orderId)}/receipt`,

    /** GET /api/customer/orders */
    orders: async (): Promise<CustomerOrderSummary[]> =>
      this.request<CustomerOrderSummary[]>({
        method: 'GET',
        path: `/api/customer/orders`,
        withAuth: true,
      }),

    // ── Track E Step 2.4.6 — Customer assets (downloads/bookings/reservations) ──

    /** GET /api/customer/downloads — file digitali acquistati. */
    downloads: async (): Promise<CustomerDownloadsResponse> =>
      this.request<CustomerDownloadsResponse>({
        method: 'GET',
        path: `/api/customer/downloads`,
        withAuth: true,
      }),

    /** GET /api/customer/bookings — prenotazioni servizi con slot. */
    bookings: async (): Promise<CustomerBookingsResponse> =>
      this.request<CustomerBookingsResponse>({
        method: 'GET',
        path: `/api/customer/bookings`,
        withAuth: true,
      }),

    /**
     * POST /api/customer/bookings/{booking_id}/cancel
     * Track E Step 5.5 — customer cancela una sua prenotazione service.
     * Status idempotent (already-cancelled = 200 no-op).
     */
    cancelBooking: async (bookingId: string): Promise<{ message: string; status: string }> =>
      this.request({
        method: 'POST',
        path: `/api/customer/bookings/${encodeURIComponent(bookingId)}/cancel`,
        withAuth: true,
      }),

    /** GET /api/customer/reservations — noleggi rental. */
    reservations: async (): Promise<CustomerReservationsResponse> =>
      this.request<CustomerReservationsResponse>({
        method: 'GET',
        path: `/api/customer/reservations`,
        withAuth: true,
      }),

    // ── Track E Step 2.4.6 — Course player (Release 4 R-4 endpoints) ──

    /** GET /api/customer/courses — videocorsi acquistati con progress stats. */
    courses: async (): Promise<CustomerCoursesResponse> =>
      this.request<CustomerCoursesResponse>({
        method: 'GET',
        path: `/api/customer/courses`,
        withAuth: true,
      }),

    /** GET /api/customer/courses/{enrollment_id} — corso detail + lessons. */
    course: async (enrollmentId: string): Promise<CustomerCourseDetail> =>
      this.request<CustomerCourseDetail>({
        method: 'GET',
        path: `/api/customer/courses/${encodeURIComponent(enrollmentId)}`,
        withAuth: true,
      }),

    /**
     * POST /api/customer/courses/{enrollment_id}/lessons/{lesson_id}/play-url
     *
     * Bunny Stream signed URL per video player iframe. TTL short (~15min).
     * Restituisce {play_url, expires_at, watermark_text?}.
     */
    coursePlayUrl: async (
      enrollmentId: string,
      lessonId: string,
    ): Promise<CustomerCoursePlayUrlResponse> =>
      this.request<CustomerCoursePlayUrlResponse>({
        method: 'POST',
        path: `/api/customer/courses/${encodeURIComponent(enrollmentId)}/lessons/${encodeURIComponent(lessonId)}/play-url`,
        withAuth: true,
      }),

    /**
     * POST /api/customer/courses/{enrollment_id}/progress
     *
     * Heartbeat per progress tracking (watched_seconds atomico $max,
     * completed_at sticky). Da chiamare ogni 10-30 sec durante playback.
     */
    updateCourseProgress: async (
      enrollmentId: string,
      body: CustomerCourseProgressUpdate,
    ): Promise<unknown> =>
      this.request({
        method: 'POST',
        path: `/api/customer/courses/${encodeURIComponent(enrollmentId)}/progress`,
        body,
        withAuth: true,
      }),
  } as const;
}

// ── Factory ────────────────────────────────────────────────────────────

/**
 * Build a new AfiancoClient. Preferred over `new AfiancoClient(...)`
 * for the JSDoc auto-import: `createAfiancoClient` is more discoverable.
 */
export function createAfiancoClient(opts: AfiancoClientOptions): AfiancoClient {
  return new AfiancoClient(opts);
}

// ── Helpers ────────────────────────────────────────────────────────────

function parseRetryAfter(header: string | null): number | null {
  if (!header) return null;
  // RFC 7231: integer seconds OR HTTP-date
  const asNum = Number.parseInt(header, 10);
  if (!Number.isNaN(asNum) && asNum >= 0) return asNum;
  const asDate = Date.parse(header);
  if (!Number.isNaN(asDate)) {
    const delta = Math.ceil((asDate - Date.now()) / 1000);
    return delta > 0 ? delta : 0;
  }
  return null;
}
