# AFianco Embed — Error Code Reference

> Catalog completo degli error code emessi dai endpoint `/api/public/embed/*`.
> **Track E Step 1.6** — single source of truth per SDK client error handling.
>
> **Audience:** sviluppatori SDK client + integrator partner.
> **Last updated:** 2026-06-02.

---

## Response shape canonical

Tutti gli error response usano questo shape:

### Structured detail (preferito)

```json
{
  "detail": {
    "code": "ERROR_CODE_CONSTANT",
    "message": "Human-readable description in Italian",
    "...extra fields...": "..."
  }
}
```

### Simple string detail (legacy)

```json
{
  "detail": "Error description string"
}
```

**Status code** = HTTP status (400/403/404/409/422/429/500).

Client SDK deve gestire ENTRAMBI i shapes (`detail` puo' essere dict
OR string).

---

## Error code catalog

### 400 INVALID_API_VERSION

**Endpoint:** all embed paths
**Trigger:** header `X-API-Version` presente ma non numerico positivo
**Detail shape:**

```json
{
  "code": "INVALID_API_VERSION",
  "message": "X-API-Version header must be a positive integer, got 'abc'.",
  "supported_versions": [1],
  "current": 1
}
```

**SDK recovery:**
- Rimuovi header X-API-Version (server usa default)
- OR usa valore corretto da `supported_versions`

---

### 400 UNSUPPORTED_API_VERSION

**Endpoint:** all embed paths
**Trigger:** header `X-API-Version` integer valido ma NON in supported set
**Detail shape:** identico a INVALID_API_VERSION (medesimi field)

**SDK recovery:**
- Upgrade SDK se SDK old hardcoded vecchia versione
- Fallback a versione corrente (rimuovendo header)

---

### 400 (generic Pydantic validation)

**Endpoint:** all
**Trigger:** body o query param fallisce validation Pydantic
**Detail shape:** Pydantic ValidationError serialized (list of errors)

```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "input": "not-an-email"
    }
  ]
}
```

**SDK recovery:** fix payload, retry.

---

### 403 origin_not_allowed (CORS)

**Endpoint:** all (DynamicCORSMiddleware level)
**Trigger:** request Origin header NON in `store.allowed_origins[]`
**Detail shape:** string

```json
{
  "detail": "Origin not allowed for this store"
}
```

**SDK recovery:**
- Verifica che il merchant abbia aggiunto il tuo domain
- Dashboard merchant → Store settings → Embed → Allowed origins

---

### 404 store_not_found

**Endpoint:** all che accettano `slug`
**Trigger:** slug NON risolve a store pubblicato + attivo
**Detail shape:** string

```json
{
  "detail": "Store not found"
}
```

**SDK recovery:**
- Verifica che lo store sia pubblicato (dashboard merchant)
- Verifica spelling slug

---

### 404 cart_not_found

**Endpoint:** GET/PATCH/DELETE `/cart/{cart_id}`
**Trigger:** cart_id non esiste OR scaduto (TTL ~24h) OR cross-tenant
**Detail shape:** string

```json
{
  "detail": "Cart non trovato o scaduto."
}
```

**SDK recovery:**
- Crea nuovo cart via `POST /cart`
- TTL cart e' 24h dall'ultimo update

---

### 409 STOCK_INSUFFICIENT

**Endpoint:** PATCH `/cart/{cart_id}`, POST `/cart` (con items)
**Trigger:** quantity richiesta > product.stock_quantity disponibile
**Detail shape:**

```json
{
  "code": "STOCK_INSUFFICIENT",
  "message": "Quantita' richiesta (10) supera la disponibilita' (3).",
  "product_id": "p_abc123",
  "requested": 10,
  "available": 3
}
```

**SDK recovery:**
- Riduci quantity a `available`
- OR rimuovi item dal cart
- OR aspetta restock (merchant aggiorna inventory)

**Note:** check e' eager (al cart add). Atomic guarantee finale al
checkout (`POST /checkout/start`). 

---

### 422 query_param_out_of_bounds

**Endpoint:** GET endpoints con query params validated
**Trigger:** Query param fuori dai range FastAPI (es. `q` > 200 char,
`limit` > 100, `offset` > 10000)
**Detail shape:** Pydantic ValidationError

```json
{
  "detail": [
    {
      "type": "string_too_long",
      "loc": ["query", "q"],
      "msg": "String should have at most 200 characters",
      "input": "..."
    }
  ]
}
```

**SDK recovery:** rispetta i limit documentati.

---

### 429 rate_limit_exceeded

**Endpoint:** all (slowapi level)
**Trigger:** per-(IP, slug) rate limit superato
**Detail shape:** string

```json
{
  "detail": "Rate limit exceeded"
}
```

**Response headers:**

```
Retry-After: 60   (seconds until reset)
```

**SDK recovery:**
- Wait `Retry-After` seconds
- Exponential backoff su retries
- Reduce request frequency

**Rate limit per endpoint:**
| Endpoint | Limit |
|---|---|
| GET endpoints (init, products, cart) | 60/min |
| POST /cart, PATCH /cart, DELETE /cart | 30/min |
| POST /cart/merge, POST /checkout/start | 10/min |

---

### 500 server_error

**Endpoint:** all
**Trigger:** unhandled exception server-side
**Detail shape:** generic

```json
{
  "detail": "Internal Server Error"
}
```

**SDK recovery:**
- Retry con exponential backoff (max 3 retry)
- Se persiste: contatta `davide@afianco.ch` con `X-Request-ID` del response

**Server-side:** capturato in Sentry con tag `surface=embed` (E1.5)
per triage operatore.

---

## Idempotency contract

POST/PATCH/DELETE endpoints richiedono header:

```
Idempotency-Key: <unique-string-per-operation>
```

### 400 (missing key)

```json
{
  "detail": "Idempotency-Key header required"
}
```

### Replay behavior

Same key + same path → same cached response (TTL 24h server-side).
Permette safe retry on network failure.

---

## Customer auth errors (related)

Endpoint sotto `/api/customer-auth/*` (separato da embed). Vedi
`docs/operations/sentry-alert-rules.md` per error code customer-auth.

Embed che usa customer JWT (es. `/cart/{id}/merge`):

- **401 invalid_token** — JWT scaduto / malformato
- **401 token_type_mismatch** — JWT type != "customer"
- **403 cross_tenant_token** — JWT org_id != store org_id
- **401 session_invalidated** — JWT iat < tokens_invalidated_at
  (logout-all-sessions O4.3)

---

## Recovery flow examples

### Customer adds item, stock changes mid-session

```
1. POST /cart → cart_id=c_abc
2. PATCH /cart/c_abc {items: [{p1, qty: 10}]} → 409 STOCK_INSUFFICIENT
   {requested: 10, available: 3}
3. SDK UI: "Solo 3 disponibili. Vuoi aggiungere 3?"
4. PATCH /cart/c_abc {items: [{p1, qty: 3}]} → 200 OK
5. POST /checkout/start → 200 OK + stripe checkout URL
```

### Rate limit hit during burst

```
1. ... rapid 60 GET /products in 60s ...
2. 61° GET /products → 429 Retry-After: 30
3. SDK pause 30s
4. Retry → 200 OK
```

### API version unsupported (SDK old)

```
1. Old SDK sends X-API-Version: 99
2. 400 UNSUPPORTED_API_VERSION {supported: [1]}
3. SDK detects → log warning + retry without header
4. Server uses default current = v1 → 200 OK
5. SDK upgrade notification to merchant developer
```

---

## Sentinel-pinned codes

Per stabilita' contract i seguenti error code sono **sentinel-pinned**
in `backend/tests/test_invariants_security.py`:

- `INVALID_API_VERSION` (E1.1, TestSEC_E_1_1)
- `UNSUPPORTED_API_VERSION` (E1.1)
- `STOCK_INSUFFICIENT` (E1.2, TestSEC_E_1_2)

Rinominare uno di questi = CI fail. Cambio richiede version bump
(v1 → v2 con migration window).

---

## Document version

| Version | Date | Notes |
|---|---|---|
| 1.0 | 2026-06-02 | Initial catalog (Track E Step 1.6) |

---

**Related docs:**
- `embed-integration-guide.md` — endpoint catalog + integration guide
- `operations/sentry-alert-rules.md` — server-side alert rules (internal)
