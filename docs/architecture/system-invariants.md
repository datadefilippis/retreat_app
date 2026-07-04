# System Invariants — afianco

**Status:** Living document
**Last update:** 2026-05-28
**Owner:** core team

---

## Purpose

Documento di riferimento per tutti gli **invarianti del sistema afianco** —
le promesse che il sistema fa oggi e che ogni refactor/feature DEVE preservare.

Ogni invariante ha:
- ID univoco (INV-N per business invariants, CTR-N per contract invariants, SEC-N per security)
- Descrizione formale
- File:line dove è enforced oggi
- Sentinel test che la pinna
- Severità (Critical / High / Medium / Low)

Le invarianti sono ordinate per severità. Critical = se viola l'invariante,
il sistema produce bug visibili al merchant entro pochi ordini.

---

## INV — Business invariants

### INV-1 — Customer atomic upsert per (organization_id, email)

**Severità:** 🔴 Critical

**Descrizione:** ogni email customer è unica all'interno di una organization.
La creazione/lookup di customer durante checkout deve essere atomic per
prevenire duplicati in caso di concurrent requests.

**Enforcement:**
- Funzione: ``customer_repository.upsert_by_email``
- File: ``apps/backend/repositories/customer_repository.py:53-178``
- Mongo: unique partial index su ``(organization_id, email)``
- Method: ``find_one_and_update(upsert=True)`` (atomic at document level)

**Sentinel test:**
- ``apps/backend/tests/test_invariants_public_flow.py::TestINV1_CustomerAtomicUpsert``

**Violation impact:** customer duplicati, audit GDPR rotto, marketing
opt-in count duplicato, CRM tier calculation incorretto.

---

### INV-2 — Order number canonical format ``ORD-{N:04d}``

**Severità:** 🔴 Critical

**Descrizione:** ogni order_number assegnato deve seguire il formato
``ORD-{N:04d}`` (es. ORD-0042). Il parser per calcolare il prossimo numero
estrae l'ultima sequenza di cifre dal numero corrente.

**Enforcement:**
- Funzione: ``order_repository.get_next_order_number``
- File: ``apps/backend/repositories/order_repository.py:97-158``
- Parser: ``_ORDER_NUMBER_TAIL_DIGITS = re.compile(r"(\d+)\s*$")``
- Mongo: unique partial index su ``(organization_id, order_number)``

**Sentinel test:**
- ``apps/backend/tests/test_invariants_public_flow.py::TestINV2_OrderNumberCanonical``

**Violation impact:** parser fallisce → assegnazione fallback ``ORD-0001`` →
collision con ordini esistenti → 3 retry → eccezione → ordine non confirmed.

---

### INV-3 — Marketing opt-in triple-write

**Severità:** 🟠 High

**Descrizione:** quando un customer accetta marketing opt-in durante checkout,
si devono produrre 3 write atomiche su collection diverse:
1. ``consent_audit_collection.insert`` (immutable proof legal)
2. ``customer_accounts_collection.update`` (se logged-in)
3. ``customers_collection.update`` (sempre, per CRM denorm)

**Enforcement:**
- File: ``apps/backend/routers/public.py:3070-3165``
- Non transazionale (MongoDB single-document atomicity)
- Soft-fail allowed sui write 2-3 con audit immutable preservato

**Sentinel test:**
- ``apps/backend/tests/test_invariants_public_flow.py::TestINV3_ConsentTripleWrite``

**Violation impact:** GDPR audit incompleto, CRM dashboard mostra customer
non-opted-in ma marketing automation li include. Drift legale.

---

### INV-4 — GDPR snapshot on Order at checkout

**Severità:** 🟠 High

**Descrizione:** ogni Order al checkout deve catturare uno snapshot dei
termini legali accettati: ``gdpr_terms_version``, ``gdpr_privacy_version``,
``gdpr_locale``, ``gdpr_accepted_at``, ``gdpr_marketing_accepted``.

**Enforcement:**
- File: ``apps/backend/routers/public.py:3023-3029``

**Sentinel test:**
- ``apps/backend/tests/test_invariants_public_flow.py::TestINV4_GDPRSnapshotOnOrder``

**Violation impact:** prova legale incompleta in caso di contestazione.

---

### INV-5 — Stripe webhook idempotency via event_id lock

**Severità:** 🔴 Critical

**Descrizione:** ogni Stripe webhook event ha un ``event_id`` univoco. Il
sistema acquisisce un lock atomic prima del processing; se l'event è già
stato processato, skippa silenziosamente. ``processed_events[]`` array su
Order traccia gli event applicati.

**Enforcement:**
- ``stripe_service.py:1394-1407`` (lock acquisition)
- ``payment_checkout_service.py:615-628`` (per-order event log)
- ``billing_repository.try_acquire_event_lock``

**Sentinel test:**
- ``apps/backend/tests/test_invariants_public_flow.py::TestINV5_StripeWebhookIdempotency``

**Violation impact:** stesso webhook event applicato 2 volte → SalesRecords
duplicati → cashflow KPI doppiati → margini errati → decisioni di business
sbagliate.

---

### INV-6 — Rental slot atomic pre-reservation

**Severità:** 🔴 Critical

**Descrizione:** per prodotti rental con slot temporali, la prenotazione
dello slot deve essere atomic PRIMA dell'insert dell'order (e rollback se
order insert fallisce) per prevenire double-booking concorrente.

**Enforcement:**
- ``order_service.py:406-428``
- Mongo: unique index su blocked_slots ``(product_id, slot_start, slot_end)``

**Sentinel test:**
- ``apps/backend/tests/test_invariants_public_flow.py::TestINV6_RentalSlotAtomic``

**Violation impact:** stesso slot venduto a 2 clienti → conflitto fisico,
refund obbligatorio, danno reputazionale.

---

### INV-7 — Customer metrics refresh after confirmed order

**Severità:** 🟡 Medium

**Descrizione:** dopo ogni ordine in stato ``confirmed`` con
``payment_intent=collected``, il sistema deve triggerare un refresh delle
``customer_metrics`` (best-effort, fire-and-forget).

**Enforcement:**
- ``order_service.py:584``
- ``modules.customer_insights.refresh.refresh_customer_metrics``

**Sentinel test:**
- ``apps/backend/tests/test_invariants_public_flow.py::TestINV7_CustomerMetricsRefresh``

**Violation impact:** CRM dashboard mostra tier stale per ~24h. Non critico
(metric refresh job giornaliero recupera).

---

### INV-8 — SalesRecords 1:1 con order lines

**Severità:** 🟠 High

**Descrizione:** ogni order line al ``confirm`` deve produrre esattamente
1 SalesRecord con ``source_label="Ordini"``, ``dataset_id="orders"``,
``customer_id``, ``product_id`` preservati.

**Enforcement:**
- ``order_service.py:1300-1419`` (``_generate_sales_records``)

**Sentinel test:**
- ``apps/backend/tests/test_invariants_public_flow.py::TestINV8_SalesRecordsGeneration``

**Violation impact:** cashflow KPI non riflettono ordini reali. Margini
prodotto incorretti. Reporting falso.

---

### INV-9 — Order status state machine

**Severità:** 🟠 High

**Descrizione:** order status transizioni valide:
- ``draft → confirmed`` (al payment collection)
- ``draft → cancelled`` (rifiuto manuale)
- ``confirmed → cancelled`` (refund)
- NO skip (es. ``draft → completed`` direttamente)
- NO reverse (es. ``confirmed → draft``)

**Enforcement:**
- ``order_service.py`` (confirm_order, cancel_order)

**Sentinel test:**
- ``apps/backend/tests/test_invariants_public_flow.py::TestINV9_OrderStateMachine``

**Violation impact:** state inconsistente, analytics aggregati errati,
KPI history corrotta.

---

### INV-10 — Payment intent transitions only via webhook

**Severità:** 🔴 Critical

**Descrizione:** il campo ``Order.payment_intent`` cambia stato (none →
required → collected) ESCLUSIVAMENTE via webhook handler Stripe, mai via
manual API call.

**Enforcement:**
- ``payment_checkout_service.py:615`` (webhook updater)
- No setter pubblico esposto in REST API

**Sentinel test:**
- ``apps/backend/tests/test_invariants_public_flow.py::TestINV10_PaymentIntentTransitions``

**Violation impact:** payment status race condition, ordini "paid" mai
realmente collected, fraud risk.

---

## CTR — Contract invariants

### CTR-1 — POST /api/public/order-request response shape

**Severità:** 🔴 Critical

**Descrizione:** la response di ``POST /api/public/order-request`` deve
sempre includere:
- ``success: bool`` (sempre presente)
- ``message: str`` (sempre presente)
- ``order_id: str`` (sempre presente)
- ``transaction_mode: str`` ("request" | "direct" | "approval")
- ``order_status: str`` (sempre "draft" al submit)
- ``payment_checkout_url: Optional[str]`` (presente SOLO se ``transaction_mode="direct"``)
- ``payment_reason: Optional[str]``

**Enforcement:**
- Pydantic model: ``apps/backend/routers/public.py:379-387``

**Sentinel test:**
- ``apps/backend/tests/test_invariants_public_flow.py::TestCTR1_OrderRequestResponseShape``

**Violation impact:** frontend client (storefront + future embed + AI site)
non riesce più a parsare la response → checkout flow rotto.

---

### CTR-2 — Storefront catalog payload shape

**Severità:** 🟠 High

**Descrizione:** ``GET /api/public/storefront/{slug}`` deve sempre ritornare
struttura completa: ``store_info``, ``products[]``, ``design_tokens``,
``custom_nav_links``, ``storefront_languages``.

**Enforcement:**
- ``apps/backend/routers/public.py:417+``

**Sentinel test:**
- ``apps/backend/tests/test_invariants_public_flow.py::TestCTR2_StorefrontCatalogShape``

**Violation impact:** storefront non renderizza, landing pages rotte.

---

### CTR-3 — Storefront meta endpoint cached 60s

**Severità:** 🟡 Medium

**Descrizione:** ``GET /api/public/storefront/{slug}/meta`` deve avere
cache-control 60s server-side.

**Enforcement:**
- ``apps/backend/routers/public.py:512``

---

## SEC — Security invariants

### SEC-1 — CSP no unsafe-inline scripts

**Severità:** 🔴 Critical

**Descrizione:** Content Security Policy deve impedire ``script-src
'unsafe-inline'``. (``unsafe-eval`` accettato per recharts runtime).

**Enforcement:**
- ``deploy/nginx/nginx.conf:117``

---

### SEC-2 — HSTS preload 1 year

**Severità:** 🟠 High

**Descrizione:** HSTS header ``max-age=31536000; includeSubDomains; preload``.

**Enforcement:**
- ``deploy/nginx/nginx.conf:51``

---

### SEC-3 — X-Frame-Options DENY

**Severità:** 🟠 High

**Descrizione:** clickjacking protection via ``X-Frame-Options: DENY`` per
afianco.app principale. (Endpoint embed avranno policy diversa con
``frame-ancestors`` whitelist.)

**Enforcement:**
- ``deploy/nginx/nginx.conf:56``

---

### SEC-4 — CORS allow_credentials con whitelist esplicita

**Severità:** 🔴 Critical

**Descrizione:** ``CORSMiddleware`` con ``allow_credentials=True`` accoppiato
a ``allow_origins`` esplicita (mai wildcard ``*``).

**Enforcement:**
- ``apps/backend/server.py:617-623``

**Note:** Phase 0 introdurrà ``DynamicCORSMiddleware`` per
``/api/public/embed/*`` con whitelist per-store, mantenendo lo stesso
principio.

---

### SEC-5 — Rate limiting per endpoint pubblico

**Severità:** 🟠 High

**Descrizione:** ogni endpoint pubblico ha rate limit specifico via slowapi:
- ``/storefront/{slug}/meta``: 60/min
- ``/storefront/{slug}``: 30/min
- ``/order-request``: 30/min
- ``/marketing-status``: 10/min

**Enforcement:**
- ``apps/backend/routers/auth.py:limiter``
- ``apps/backend/routers/public.py`` decorators

---

## Review

Ogni nuovo invariante introdotto deve:
1. Avere ID univoco assegnato
2. Avere sentinel test in ``apps/backend/tests/test_invariants_*.py``
3. Essere documentato qui PRIMA del merge della feature relativa
4. Avere severità classificata
5. Avere "Violation impact" descritto

Invariant deprecation richiede approval esplicito del lead architect.
