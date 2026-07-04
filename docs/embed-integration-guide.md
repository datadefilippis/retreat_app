# AFianco Embed Integration Guide

> Guida per integrare il widget e-commerce AFianco sul proprio sito.
> **Track E Step 1.6** — Sub-Track E1 contract consolidation (closing).
>
> **Audience:** sviluppatori merchant + integrator partner.
> **Status:** v1 (single-major contract, stable).
> **Last updated:** 2026-06-02.

---

## TL;DR — 60 seconds to working embed

```html
<!-- 1. Carica lo script embed-SDK (CDN o self-host) -->
<script type="module" src="https://cdn.afianco.ch/embed/v1/afianco-embed.es.js"></script>

<!-- 2. Posiziona il web component dove vuoi che appaia lo store -->
<afianco-storefront-init slug="il-tuo-slug-merchant">
  <afianco-product-grid></afianco-product-grid>
  <afianco-cart-drawer></afianco-cart-drawer>
  <afianco-checkout-button></afianco-checkout-button>
</afianco-storefront-init>
```

That's it. Lo widget contatta `https://api.afianco.ch/api/public/embed/init/<slug>`,
carica meta + categorie + capabilities, e renderizza autonomamente.

---

## Pre-requisiti

1. **Account merchant attivo** su [app.afianco.ch](https://app.afianco.ch)
2. **Store pubblicato** (vedi Setup Wizard nella dashboard merchant)
3. **`allowed_origins` configurato** per il tuo dominio:
   - Login dashboard → Store settings → Embed → Add allowed origin
   - Esempio: `https://www.mioshop.com` (NO wildcard, exact match)
4. **TLS / HTTPS attivo** sul tuo sito (richiesto da CORS browser-level)

---

## API versioning protocol

### Header request (opzionale)

Client SDK manda esplicitamente:

```
X-API-Version: 1
```

Se assente, server assume **current stable** (v1 oggi).

### Header response (sempre presente)

Server SEMPRE risponde con:

```
X-API-Version: 1
```

Indica al client quale contratto e' stato applicato. Client SDK puo'
verificare consistency.

### Versioni supportate

| Versione | Status | Deprecation date | Removal date |
|---|---|---|---|
| **1** | ✅ Stable (current) | TBD | TBD |

Future v2 (breaking changes): annunciata 6+ mesi in anticipo via:
- Email a contact merchant registrato
- `Deprecation` header su risposte v1
- Update di questa pagina + changelog finale

### Error: unsupported version

Se mandi `X-API-Version: 999`:

```
HTTP 400 Bad Request
Content-Type: application/json

{
  "detail": {
    "code": "UNSUPPORTED_API_VERSION",
    "message": "X-API-Version=999 not supported. Use one of: [1]. Current stable: 1.",
    "supported_versions": [1],
    "current": 1
  }
}
```

Se mandi `X-API-Version: abc`:

```
HTTP 400
{
  "detail": {
    "code": "INVALID_API_VERSION",
    "message": "X-API-Version header must be a positive integer, got 'abc'.",
    "supported_versions": [1],
    "current": 1
  }
}
```

---

## Endpoint catalog

Tutti gli endpoint sotto il prefisso **`/api/public/embed/`** del backend
AFianco. Production base URL: `https://api.afianco.ch` (TBD esempio).

| Endpoint | Method | Rate limit | Purpose |
|---|---|---|---|
| `/init/{slug}` | GET | 60/min | Bootstrap: meta + categories + capabilities |
| `/categories/{slug}` | GET | 60/min | Categories list (con thumbnail opzionale) |
| `/products/{slug}` | GET | 60/min | Products list + filter + sort + **search (E1.3)** |
| `/products/{slug}/{id}` | GET | 60/min | **Product detail enriched type-aware (E2.4.5/6)** |
| `/products/{slug}/{id}/availability` | GET | 30/min | **Service/rental slot availability (E2.4.6)** |
| `/price-preview/{slug}` | POST | 60/min | **Live total preview server-computed (E2.4.10)** |
| `/cart` | POST | 30/min | Create empty cart |
| `/cart/{cart_id}` | GET | 60/min | Read cart by id |
| `/cart/{cart_id}` | PATCH | 30/min | Update cart items + **inventory check (E1.2)** |
| `/cart/{cart_id}` | DELETE | 30/min | Clear cart (default) or hard delete |
| `/cart/{cart_id}/merge` | POST | 10/min | Bind anonymous cart to authenticated customer |
| `/checkout/start` | POST | 10/min | Convert cart to order + Stripe checkout URL |
| `/checkout/complete` | GET | 60/min | postMessage bridge (popup return) |

Inoltre il widget consuma **endpoint customer-portal** (autenticati) coperti dal middleware DynamicCORS:

| Endpoint | Method | Auth | Purpose |
|---|---|---|---|
| `/api/customer/me` | GET | Bearer JWT | Customer profile |
| `/api/customer/orders` | GET | Bearer JWT | Order history |
| `/api/customer/courses` | GET | Bearer JWT | **Videocorsi acquistati (E2.4.6/8)** |
| `/api/customer/courses/{id}` | GET | Bearer JWT | Course detail con lessons |
| `/api/customer/courses/{id}/lessons/{lid}/play-url` | POST | Bearer JWT | Bunny signed URL (TTL ~15min) |
| `/api/customer/courses/{id}/progress` | POST | Bearer JWT | Progress heartbeat ($max sticky) |
| `/api/customer/downloads` | GET | Bearer JWT | **File digitali acquistati (E2.4.6)** |
| `/api/customer/bookings` | GET | Bearer JWT | **Prenotazioni servizi (E2.4.6)** |
| `/api/customer/reservations` | GET | Bearer JWT | **Noleggi rental (E2.4.6)** |

### Rate limits — per-merchant isolation (E1.4)

I rate limit sono per-(IP, merchant slug). Esempio:

- Customer X visita merchant A: bucket `(IP=X, slug=A)` = 60/min su /products
- Customer X visita merchant B SUL TUO STESSO browser/IP:
  bucket separato `(IP=X, slug=B)` = altri 60/min indipendenti
- Merchant A satura il proprio bucket NON impatta merchant B

Quando hit il limit:

```
HTTP 429 Too Many Requests
Retry-After: <seconds>
```

---

## Cart & inventory

### Inventory check on add (E1.2)

PATCH `/cart/{cart_id}` con qty > stock disponibile:

```
HTTP 409 Conflict
{
  "detail": {
    "code": "STOCK_INSUFFICIENT",
    "message": "Quantita' richiesta (10) supera la disponibilita' (3).",
    "product_id": "p_abc123",
    "requested": 10,
    "available": 3
  }
}
```

### Quali prodotti hanno inventory tracking

| Item type | Inventory tracked? | Reason |
|---|---|---|
| `physical` | ✅ (se `stock_quantity` settato) | Stock finito |
| `digital` | ✅ (se `stock_quantity` settato) | License cap opzionale |
| `service` | ❌ | Capacity offline-managed |
| `rental` | ❌ | Calendar availability |
| `event_ticket` | ❌ | Per-occurrence capacity (separato) |
| `course` | ❌ | Nominative licenses |

Prodotti senza `stock_quantity` settato = unlimited (legacy backward compat).

### Race condition note

Inventory check at cart add e' **best-effort**:
- 2 customer simultanei aggiungono ultima unita' → ENTRAMBI passano cart check
- Atomic guarantee al checkout finale (`/checkout/start` consuma stock via Mongo `find_one_and_update`)
- Customer "secondo" vede error solo al checkout finale (acceptable industry standard, vedi Shopify/WooCommerce)

---

## Search (E1.3)

GET `/products/{slug}?q=pizza`

Mongo `$text` operator con stemmer italiano. Supporta:

- **Match singolo**: `?q=pizza` → match "pizza", "pizze", "pizzaiolo"
- **Phrase**: `?q="farina 00"` → match esatto frase
- **Exclusion**: `?q=pasta -glutine` → "pasta" SI, "glutine" NO
- **Max length**: 200 char (>200 → 422 da FastAPI Query validator)
- **Empty/whitespace**: silent ignored (no filter)

Weights:
- `name` field: weight 3 (3x piu' importante)
- `description` field: weight 1

Sort default quando q presente: `relevance` (score DESC).
Sort explicit `?sort=name` override.

---

## Customer authentication (embed-inline signup)

Vedi `/api/customer-auth/*` endpoint (separato dal embed router):

- `POST /customer-auth/signup` (5/15min per IP+email)
- `POST /customer-auth/login` (10/min per IP)
- `POST /customer-auth/forgot-password` (5/min per IP + 10/h per email)
- `POST /customer-auth/verify-email`

Customer authenticated puo' fare `POST /embed/cart/{id}/merge` per bind
guest cart al proprio account (Bearer JWT richiesto).

---

## CORS setup (browser-level)

Il backend AFianco usa `DynamicCORSMiddleware` che:

1. Legge `Origin` header dal browser
2. Lookup `stores_collection.find_one({slug, allowed_origins: origin})`
3. Se match → CORS headers + 200/304
4. Se NO match → **403 Forbidden** (no CORS headers)

### Configurazione

Dashboard merchant → Store settings → Embed → Allowed origins:

```
https://www.mioshop.com
https://shop.mioshop.com
https://staging.mioshop.com
```

NB:
- **NO wildcard** (`*` rejected)
- **NO http://** in produzione (TLS only)
- **Path NON parte del match** (`https://mioshop.com/path` viene
  ignorato al `/path` — match e' origin only)

### Errore origin rifiutato

```
HTTP 403 Forbidden
{
  "detail": "Origin not allowed for this store"
}
```

NESSUN header CORS → browser blocca lato client con CORS error in console.

---

## Error code catalog

Reference completo: vedi `embed-error-codes.md`.

Quick table:

| Status | Code | Endpoint | Cause |
|---|---|---|---|
| 400 | `INVALID_API_VERSION` | tutti | Header X-API-Version non integer |
| 400 | `UNSUPPORTED_API_VERSION` | tutti | Header X-API-Version non in supported set |
| 400 | (string) | tutti | Body validation Pydantic fail |
| 403 | (string) | tutti | CORS origin not allowed |
| 404 | (string) | tutti | Slug store / cart_id / order_id not found |
| 409 | `STOCK_INSUFFICIENT` | PATCH /cart, POST /cart | Inventory check fail (E1.2) |
| 422 | (string) | tutti | Query param out of bounds (es. q >200 char) |
| 429 | (Retry-After) | tutti | Rate limit per-(IP, slug) exceeded |
| 500 | (generic) | tutti | Server error — captured in Sentry (E1.5) |

---

## Observability & monitoring

### Sentry surface tagging (E1.5)

Tutti gli errori embed in produzione sono auto-tagged in Sentry con:

```
surface: embed
```

Filterable in Sentry inbox per triage rapido. Alert rule
**[P2] Embed-SDK error spike** (>50/h) notifica `davide@afianco.ch`.

### Metrics

Counters Prometheus pubblicati su `/metrics` endpoint (admin auth):

- `embed_init_requests_total{slug, cache_result}`
- `embed_category_lookups_total{slug, with_thumbnail}`
- `embed_product_searches_total{slug, has_filter}`
- `embed_checkout_started_total{slug, outcome}`
- `embed_postmessage_bridges_total{slug, status}`
- `cart_operations_total{operation, status, source}`
  - `status="stock_rejected"` quando E1.2 inventory check blocca

---

## Idempotency-Key requirement

Tutte le mutations (POST/PATCH/DELETE) richiedono header:

```
Idempotency-Key: <unique-string>
```

Best practice client SDK:
- UUID v4 per ogni operazione utente (es. "add to cart" click)
- TTL cache 24h server-side
- Replay con stesso key → same response (cached)
- Missing header → 400 Bad Request

---

## Performance / caching

GET endpoints (init, categories, products) ritornano:

```
Cache-Control: public, max-age=300
ETag: "<sha1-deterministic>"
```

Conditional GET via `If-None-Match` → 304 Not Modified (zero body).

CDN edge cache OK (TTL 5 min). Cache busting via query param `?_v=<sha>`
se merchant cambia config + vuole propagation immediata.

---

## Versioning policy & deprecation

### Additive changes (no version bump)

- Nuovo OPTIONAL field nel response
- Nuovo OPTIONAL query param
- Nuovo endpoint embed (es. /products/{slug}/{id} dettaglio)
- Nuovo valore enum in field esistente (es. nuovo sort mode)

**Backward compat:** client SDK old continua a funzionare invariato.

### Breaking changes (REQUIRE version bump)

- Rename field nel response
- Remove field
- Change semantica di un field esistente
- Change error code structure
- Reduction di limit (es. max_length 200 → 100)

**Policy:**
1. New version (v2) announced 6+ mesi in advance
2. Both v1 + v2 supported during transition
3. `Deprecation` header su response v1 con sunset date
4. v1 removed solo dopo 6+ mesi soak
5. Embed-SDK auto-detects e propone upgrade al merchant

---

## Web Components catalog (Track E Step 2.4)

Il bundle SDK espone **17 custom elements** registrati globalmente. Lo
snippet canonical generato da `embed_distribution.generate_embed_snippet()`
ne usa 6, ma il merchant può embedare anche sub-component standalone
(es. solo il calendar picker per integrazioni custom).

### Core layout (6 nel snippet default)

```html
<script type="module" src="https://app.afianco.ch/embed/v1/afianco-embed.es.js"></script>
<afianco-storefront-init slug="{store-slug}">
  <afianco-header></afianco-header>                       <!-- navbar sticky -->
  <afianco-account hide-trigger></afianco-account>        <!-- drawer login/signup/portal -->
  <afianco-product-grid></afianco-product-grid>           <!-- catalog grid -->
  <afianco-product-detail></afianco-product-detail>       <!-- landing drawer type-aware -->
  <afianco-cart-drawer hide-trigger></afianco-cart-drawer><!-- cart slide-in -->
  <afianco-checkout-button></afianco-checkout-button>     <!-- Stripe checkout -->
</afianco-storefront-init>
```

### Sub-component standalone (esposti per compositions custom)

| Tag | Scopo |
|---|---|
| `<afianco-service-options-picker>` | Radio cards opzioni servizio |
| `<afianco-availability-picker>` | Date carousel + slot grid (service) |
| `<afianco-occurrence-picker>` | Date evento + remaining capacity |
| `<afianco-tier-picker>` | Tier biglietti + qty stepper |
| `<afianco-date-range-picker>` | Date from/to (rental flavor=range) |
| `<afianco-course-preview>` | Info corso (lessons count + access policy) |
| `<afianco-extras-picker>` | Mandatory/optional/radio variant extras |
| `<afianco-price-preview>` | Live total server-computed (debounced) |
| `<afianco-customer-portal>` | Area personale (5 tab) |
| `<afianco-my-courses>` | Grid corsi acquistati con progress |
| `<afianco-course-player>` | iframe Bunny + heartbeat progress |
| `<afianco-my-downloads>` | Lista signed download URLs |
| `<afianco-my-bookings>` | Timeline bookings + reservations |
| `<afianco-login>`, `<afianco-signup>` | Standalone auth forms |

### Event bus (loose coupling)

I componenti comunicano via document-level CustomEvents (no direct
reference):

| Event | Producer | Consumer |
|---|---|---|
| `afianco:open-account` | header | account |
| `afianco:open-cart` | header | cart-drawer |
| `afianco:product-view-requested` | product-card | product-detail |
| `afianco:add-to-cart` | product-detail | cart-drawer |
| `afianco:slot-selected` | availability-picker | product-detail |
| `afianco:occurrence-selected` | occurrence-picker | product-detail |
| `afianco:tier-changed` | tier-picker | product-detail |
| `afianco:date-range-selected` | date-range-picker | product-detail |
| `afianco:extras-changed` | extras-picker | product-detail |
| `afianco:price-updated` | price-preview | merchant listener (optional) |
| `afianco:course-selected` | my-courses | customer-portal |
| `afianco:lesson-completed` | course-player | merchant listener (optional) |

---

## Type-aware buy flow (Track E Step 2.4.7)

Quando il customer clicca una card prodotto, il drawer landing si apre
type-aware:

| `item_type` | UI nel drawer |
|---|---|
| `physical` | Qty stepper + extras |
| `digital` | Qty stepper + extras + download info |
| `service` | Service options (radio) + availability calendar (slot grid) + extras |
| `event_ticket` | Occurrence picker + tier picker (qty integrato) |
| `rental` | Date range picker (flavor=range) + extras (per_day moltiplicatore) |
| `course` | Preview lessons + access policy (acquisto → portal area) |

Il **price preview** (server-computed, debounced 300ms) si aggiorna
ad ogni cambio di selezione. La CTA "Aggiungi al carrello" è disabled
finché i required fields non sono popolati (es. slot scelto per service,
occurrence per event).

---

## v1.5 additions — Conversion completeness + UX parity (E4 + E5)

### New endpoints

| Endpoint | Method | Rate limit | Purpose |
|---|---|---|---|
| `/coupons/validate/{slug}` | POST | 30/min | **Dry-run coupon validation (E4.1)** — no usage increment |
| `/shipping-options/{slug}` | GET | 60/min | **Lista opzioni shipping (E4.2)** — base_price + free threshold |
| `/customer/bookings/{id}/cancel` | POST | 5/min | **Self-service cancel booking (E5.2)** — customer ownership check |
| `/customer/orders/{id}/receipt` | GET | 30/min | **PDF receipt download (E5.2)** — signed URL |

### New `EmbedInitResponse` fields

```typescript
interface EmbedInitResponse {
  // ... existing fields
  design_tokens?: {           // E4.3
    accent_color?: string;
    font_family?: 'inter' | 'system' | 'serif' | 'mono';
    border_radius?: 'sharp' | 'soft' | 'pill';
    density?: 'compact' | 'cozy' | 'spacious';
    header_style?: 'minimal' | 'banner';
    card_style?: 'flat' | 'elevated';
  };
  custom_nav_links?: {        // E4.3
    label: string;
    url: string;
    external?: boolean;
  }[];
  supported_locales?: string[]; // E4.5
}
```

Backend espone gli stessi `design_tokens` field sia su EmbedInitResponse
sia su CatalogResponse (storefront classic) — single source, applied
locally al proprio namespace.

### New Web Components (E4-E5)

| Tag | Scope | Default in snippet? |
|---|---|---|
| `<afianco-fulfillment-picker>` | Radio shipping / pickup_at_store / local_pickup | Auto-mounted in checkout |
| `<afianco-shipping-options-picker>` | Radio cards shipping options with free threshold | Auto-mounted in checkout |
| `<afianco-profile-editor>` | Accordion: edit profile + change password + GDPR erasure | Inside `afianco-customer-portal` |
| `<afianco-language-switcher>` | Dropdown lingua (variant=compact / full) | Auto-mounted in header se >1 locale |
| `<afianco-analytics-bridge>` | Opt-in bridge eventi → GTM/GA4 | NO (opt-in via merchant snippet) |

### Updated canonical snippet

```html
<script type="module" src="https://app.afianco.ch/embed/v1/afianco-embed.es.js"></script>
<afianco-storefront-init slug="{store-slug}">
  <afianco-header></afianco-header>
  <afianco-account hide-trigger></afianco-account>
  <afianco-product-grid show-search></afianco-product-grid>   <!-- E5.1: search bar -->
  <afianco-product-detail></afianco-product-detail>
  <afianco-cart-drawer hide-trigger></afianco-cart-drawer>
  <afianco-checkout-button></afianco-checkout-button>
  <!-- opt-in optional bridge -->
  <afianco-analytics-bridge gtm gtag></afianco-analytics-bridge>
</afianco-storefront-init>
```

### New custom events (E4-E5)

| Event | Producer | Consumer |
|---|---|---|
| `afianco:coupon-applied` | checkout-button | analytics-bridge |
| `afianco:fulfillment-mode-changed` | fulfillment-picker | checkout-button |
| `afianco:shipping-option-selected` | shipping-options-picker | checkout-button |
| `afianco:locale-changed` | language-switcher (document) | all components (re-render) |
| `afianco:profile-updated` | profile-editor | customer-portal |
| `afianco:password-changed` | profile-editor | customer-portal |
| `afianco:erasure-requested` | profile-editor | customer-portal |
| `afianco:booking-cancelled` | my-bookings | customer-portal |
| `afianco:view-item` | product-detail | analytics-bridge |
| `afianco:begin-checkout` | checkout-button | analytics-bridge |
| `afianco:purchase` | postmessage bridge | analytics-bridge |
| `afianco:login`, `afianco:sign-up` | account | analytics-bridge |

### i18n contract (E4.5)

Locale auto-detect priority:
1. URL query `?lang=en` (forced)
2. `<afianco-storefront-init lang="en">` attribute
3. `localStorage[afianco_lang_{slug}]`
4. `navigator.language` mapped to supported_locales
5. Fallback `it` (base)

Persistence: `localStorage[afianco_lang_{slug}]` (scoped per slug for
multi-merchant isolation on same origin).

Document event broadcast `afianco:locale-changed` → tutti i componenti
si re-renderizzano automaticamente.

### Search bar contract (E5.1)

`<afianco-product-grid show-search>` espone search input nel header
del grid:
- Debounced 350ms keystroke → query `?q=`
- Esc / X clear → re-fetch full catalog
- Mobile-friendly (full width su <480px)
- i18n labels (placeholder + clear button)

Backend usa Mongo `$text` con stemmer italiano (vedi sezione Search E1.3).

### Analytics privacy contract (E5.4)

`<afianco-analytics-bridge>` emette **zero PII**:
- ✅ product_id, qty, value, currency
- ❌ NEVER: email, name, address, IP, phone

Eventi mappati:

| Widget event | GA4 event | GTM dataLayer |
|---|---|---|
| `afianco:view-item` | `view_item` | `{ event: 'view_item', items: [...] }` |
| `afianco:add-to-cart` | `add_to_cart` | `{ event: 'add_to_cart', ... }` |
| `afianco:begin-checkout` | `begin_checkout` | `{ event: 'begin_checkout', ... }` |
| `afianco:purchase` | `purchase` | `{ event: 'purchase', transaction_id, ... }` |
| `afianco:login` | `login` | `{ event: 'login', method }` |
| `afianco:sign-up` | `sign_up` | `{ event: 'sign_up', method }` |

Attributi attivazione (entrambi opzionali, additive):
- `gtm` → push a `window.dataLayer`
- `gtag` → call a `window.gtag('event', name, params)`

Se nessun attributo settato → no-op silenzioso.

### Cart auto-close UX fix (E3.1)

`<afianco-cart-drawer>` ora chiude automaticamente quando il customer
clicca "Procedi al checkout":
- `setTimeout(setOpen(false), 50)` per evitare z-index war
- Defense-in-depth: scrim modal usa `z-index: calc(var(--afianco-z-modal) + 10)`
- Comportamento documentato in `embed-ux-symmetry-audit.md` (UX area #1)

### GDPR Art.17 erasure (E4.4)

Customer puo' richiedere cancellazione account dal portale widget:
- Portal → Profilo → "Cancella account" (accordion section)
- Conferma checkbox + email re-inserita per safety
- Backend marca `deletion_requested_at` + invia email
- Cancellazione effettiva entro 30 giorni (window reversibile customer support)

Endpoint backend: `POST /api/customer/erasure-request` (Bearer JWT).

---

## Changelog

| Version | Date | Status | Notes |
|---|---|---|---|
| **v1** | 2026-06-02 | Stable (current) | Initial public contract. Track E1 consolidation. |
| **v1.4.x** | 2026-06-02 | Additive | Track E Step 2.4.x: type-aware product-detail drawer, unified navbar header, customer portal tabs (corsi/downloads/bookings), extras picker, live price preview. **Snippet ora include 6 componenti** (era 4). |
| **v1.5.x** | 2026-06-02 | Additive | **Track E Step 4-5**: coupon dry-run, shipping options endpoint, design_tokens + custom_nav_links in init, profile editor + GDPR erasure, i18n IT+EN, search bar product-grid, analytics bridge GTM/GA4, ICS calendar link, map URL on occurrences, booking self-cancel, order receipt download. **No breaking changes** — tutti i field nuovi sono OPTIONAL. |

---

## Support & contact

- **Email:** davide@afianco.ch
- **Docs:** `https://docs.afianco.ch` (TBD)
- **Bug reports:** include `X-Request-ID` header del response in
  questione + curl reproduction se possibile
- **Discord/community:** TBD post-pilot launch

---

## Related documents

- `docs/embed-error-codes.md` — error code reference catalog completo
- `docs/embed-onboarding-merchant.md` — **5-min onboarding merchant (NEW E7.2)**
- `docs/embed-troubleshooting.md` — **diagnostics step-by-step (NEW E7.2)**
- `docs/embed-ux-symmetry-audit.md` — **storefront vs widget audit (NEW E6)**
- `docs/operations/sentry-alert-rules.md` — alert rules ops (internal)
- `docs/operations/uptime-monitoring.md` — uptime monitor (internal)
- `docs/architecture/system-invariants.md` — contract invariants
- README.md — overview prodotto

---

**Document version:** 1.5 (Track E Steps 1-7 — pilot launch ready)
**Next review:** post-pilot launch (~30 giorni)
