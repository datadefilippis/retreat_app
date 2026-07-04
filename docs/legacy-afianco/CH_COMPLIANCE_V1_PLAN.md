# CH Compliance v1 — Implementation Plan

Status: in-progress (Sub-stream 1 — Step 1.4 done, scope holistically extended for Step 1.5)
Owner: AFianco core team
Target: enable Switzerland (CHF + TWINT + VAT 8.1%) for first 5–10 micro-merchants in Ticino, with a multi-currency foundation that scales to USD/GBP and beyond.

## 0. Scope evolution

The original Step 1.5 ("refactor 9 EUR fallbacks") was uncovered to be a small subset of the real surface area. A holistic audit (see Section 3.5) found 19 critical gaps across customer-facing, merchant-facing, storage and Stripe layers. Step 1.5 has therefore been re-architected as a **multi-currency foundation** with four independently mergeable priority levels (A → D, ~11 dev days total). All other sub-streams (payment provider abstraction, VAT, manual onboarding) remain as planned.

## 1. Objective

Make AFianco usable by a Swiss micro-merchant (under VAT registration threshold of CHF 100k/year) without breaking any existing EUR/IT merchant flow, AND lay a multi-currency architecture solid enough to support USD/GBP/etc with no rewrite.

Success criteria:
- An organization with `currency=CHF` can complete checkout end-to-end with TWINT
- The PDF receipt shows `CHF 49.50` and VAT 8.1% (when enabled)
- An organization with `currency=EUR` continues to work identically (zero regression)
- A merchant cannot change currency once orders exist
- All existing tests pass

Out of scope for v1:
- QR-bill ISO 20022 generation
- Multi-currency per organization
- Per-product VAT rate override
- Datatrans / PostFinance / TWINT direct
- Setup wizard self-service UI
- Apple Pay / Google Pay

## 2. Architecture

### 2.1 Single-currency per organization

Each organization picks ONE currency at setup. Once any order exists for that organization, the currency becomes immutable. Validator enforced at the model layer; UI disables the selector after first order.

### 2.2 Provider-agnostic payment layer

Even though only Stripe is implemented in v1, all checkout logic goes through a `PaymentProvider` abstract interface. No `import stripe` outside `backend/payment_providers/stripe/`. This makes adding Datatrans (v1.5) a 5-day job instead of a 15-day refactor.

### 2.3 Immutable fiscal snapshots

Orders carry a `tax_breakdown` snapshot at creation. Changes to org-level VAT rate never propagate to existing orders. Audit-friendly.

### 2.4 Feature flag

```python
class OrganizationBetaFeatures(BaseModel):
    ch_compliance: bool = False
```

Default `False`. CH UI/logic only activates when flag is on. Reversible: turning the flag off returns the org to legacy EUR behavior. Existing CHF orders keep their snapshots.

## 3. Sub-streams

### Sub-stream 1 — Currency abstraction (3 days)

**New files**:
- `backend/core/checkout_minimums.py` — per-currency Stripe minimums
- `backend/core/currency_format.py` — server-side formatter (PDF/email)
- `backend/services/currency_service.py` — `is_change_allowed(org_id)`, `get_currency_for_org(org)`
- `frontend/src/utils/currency.js` — `formatAmount(amount, currency, locale)` via `Intl.NumberFormat`
- `frontend/src/constants/currencies.js` — supported currencies list
- `frontend/src/components/forms/CurrencySelector.jsx` — disabled after first order

**Edits (additive)**:
- `backend/models/organization.py:246` — `Optional[str] = None` → `Literal["EUR","CHF"] = "EUR"` + validator
- `backend/models/order.py:226` — default removed, currency always propagated from org
- `backend/routers/public.py` — 9 EUR fallback sites (lines 166, 214, 363, 843, 1006, 2741, 2746, 2965, 2994) made currency-aware
- `backend/services/payment_checkout_service.py:39, 70` — `MIN_CHECKOUT_AMOUNT_EUR` becomes `get_minimum(currency)` lookup
- `backend/routers/me.py` — new `GET /api/me/can-change-currency` endpoint

**Migration script**: `scripts/migrate_currency_default.py` sets `currency="EUR"` on all orgs where `currency is None`. Idempotent + reversible (dry-run mode).

**Tests**:
- `backend/tests/test_currency_immutability.py`
- `backend/tests/test_currency_propagation.py`
- `backend/tests/test_currency_format.py`

### Sub-stream 2 — Payment provider abstraction + Stripe TWINT (3 days)

**New module structure**:
```
backend/payment_providers/
├── __init__.py
├── base.py           # PaymentProvider abstract class
├── registry.py       # PaymentProviderRegistry singleton
├── exceptions.py     # ProviderError, AccountNotConfigured
├── models.py         # CheckoutSessionRequest/Response (provider-agnostic)
└── stripe/
    ├── __init__.py
    ├── provider.py
    ├── webhook.py    # signature validation + event parsing
    └── capabilities.py  # preflight: which payment methods active
```

**Edit**: `backend/services/payment_checkout_service.py` extracts `stripe.checkout.Session.create(...)` into `StripeProvider`. Service calls `provider.create_checkout_session(...)`.

**Logic**: when `currency=CHF` and Stripe account capabilities include `twint` active, `payment_method_types=["card","twint"]`. Otherwise card-only with dashboard warning.

**Application fee** (preparation for monetization): new field `Organization.application_fee_percent: Decimal = 0`. v1 always 0 for first 10 clients.

**Security**:
- Webhook signature validation always on
- Idempotency keys on every Stripe call
- No silent fallback if TWINT capability missing
- Audit log on every checkout/payment event
- Rate limit on preflight endpoint (12 calls/min/org, 5-min Redis cache)

**Tests**:
- `backend/tests/test_stripe_provider.py`
- `backend/tests/test_payment_provider_interface.py`
- `backend/tests/test_webhook_signature.py`
- `backend/tests/test_idempotency.py`
- Manual Stripe test mode TWINT transaction

### Sub-stream 3 — VAT configurable (3 days)

**New models**:
```python
class TaxSettings(BaseModel):       # embedded in Organization
    enabled: bool = False
    country: Literal["CH","IT","DE","FR"] = "IT"
    default_rate_percent: Decimal = Decimal("0")
    vat_id: Optional[str] = None
    include_in_price: bool = True

class TaxBreakdown(BaseModel):      # embedded in Order, immutable
    rate_percent: Decimal
    taxable_amount: Decimal
    tax_amount: Decimal
    total_with_tax: Decimal
    included_in_price: bool
    snapshot_at: datetime
```

**New service**: `backend/services/tax_service.py` — `calculate(order, org) -> TaxBreakdown`.

**Edits**:
- `backend/models/organization.py` — add `tax_settings: TaxSettings = TaxSettings()`
- `backend/models/order.py` — add `tax_breakdown: Optional[TaxBreakdown] = None`
- `backend/services/order_service.py` — at checkout call `tax_service.calculate()` and set `tax_breakdown`
- `backend/services/order_pdf_service.py` — conditional render: with VAT line if `tax_breakdown` present, simple receipt if absent

**Tests**:
- `backend/tests/test_tax_calculation.py` — included vs added, edge cases 0/2.6/8.1/22%
- `backend/tests/test_tax_immutability.py`
- `backend/tests/test_pdf_render_with_tax.py` — snapshot 3 scenarios
- `backend/tests/test_no_regression_orders_without_tax.py`

### Sub-stream 4 — Manual onboarding (1 day)

**New files**:
- `scripts/onboard_ch_merchant.py` — idempotent CLI with `--rollback`
- `docs/onboarding/CH_MERCHANT_CHECKLIST.md` — 10-step setup guide
- `docs/onboarding/EMAIL_WELCOME_CH.md` — post-signup email copy

**No UI changes**. Setup wizard remains in stand-by. First 10 merchants onboarded via 30-min 1:1 call.

## 4. Execution sequence

```
day 1-3   Sub-stream 1 (Currency)
day 4-6   Sub-stream 2 (Payment)
day 7-9   Sub-stream 3 (VAT)
day 10    Sub-stream 4 (Onboarding)
day 11    Internal beta (1 EUR org + 1 CHF org)
day 12    Merge → main
```

Sub-stream 1 must precede 2 and 3 (both depend on `currency_service`).

## 5. Test plan

| Layer | Test | When |
|---|---|---|
| Unit | currency_service, tax_service, stripe_provider | Continuous |
| Integration | Webhook flow, idempotency, immutability | Pre-merge per sub-stream |
| E2E | 1 EUR order (legacy) + 1 CHF+TWINT order | Pre-merge global |
| Snapshot | PDF receipt × 3 scenarios | Pre-merge sub-stream 3 |
| Regression | All existing tests green | Gate every sub-stream |
| Manual | Stripe test mode TWINT transaction | Pre-merge sub-stream 2 |

Coverage target: ≥80% on new files, 0 regressions on edited files.

## 6. Definition of Done (merge gate)

- [ ] All existing tests pass
- [ ] New tests pass with coverage ≥80% on new modules
- [ ] Type hints complete, `mypy --strict` clean on new files
- [ ] Linter rule active: `import stripe` forbidden outside `payment_providers/stripe/`
- [ ] Documentation updated (`CH_COMPLIANCE_V1_PLAN.md`, `CH_MERCHANT_CHECKLIST.md`, payment provider design)
- [ ] Internal beta 24h on test EUR + test CHF org, zero error logs
- [ ] Manual e2e Stripe test mode TWINT verified
- [ ] PR with reversible migration script (dry-run tested)
- [ ] Audit log writes new events correctly
- [ ] Feature flag `ch_compliance` defaults to `False` in main

## 7. Decisions taken

1. Single-currency per org in v1 (not multi-currency)
2. VAT included in price by default for CH (B2C standard), configurable
3. Stripe-only payment methods: `card + twint` for CHF, `card` for EUR
4. VAT only at org level in v1 (per-product override deferred to v1.5)
5. Manual onboarding for first 10 clients (setup wizard stays parked)
6. Application fee = 0% for first 10 clients (field exists for future monetization)

## 8. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Currency change after orders exist | Pydantic validator + service-level guard + UI disabled selector |
| TWINT request without Stripe account capability | Preflight check + UI warning + checkout block (no silent fallback) |
| VAT change retroactive | `tax_breakdown` is immutable snapshot |
| Stripe webhook spoofing | Signature validation always on |
| Currency mismatch order vs org | Validator at order creation |
| Migration breaks existing orgs | Idempotent script with dry-run + reversible |
| Existing flow regression | Feature flag default OFF + full regression gate |

## 9. Out of scope (v1.5 candidates)

- QR-bill ISO 20022
- Datatrans / PostFinance Checkout integration
- Per-product VAT override
- Multi-currency for same org
- Apple Pay / Google Pay
- Setup wizard self-service UI
- Cookie banner / LPD UI
- TWINT direct contract
