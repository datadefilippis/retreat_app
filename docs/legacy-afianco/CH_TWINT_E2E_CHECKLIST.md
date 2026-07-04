# CH compliance v1 — TWINT End-to-End Manual Test Checklist

This document is the **manual smoke test** for the TWINT-via-Stripe
flow before onboarding the first Swiss merchant. The unit suite
(``tests/test_stripe_provider.py``, ``test_payment_provider_interface.py``,
``test_checkout_idempotency.py``, ``test_application_fee.py``) covers
the wire-level contract with the Stripe SDK mocked. This checklist
covers the **real** Stripe test-mode round-trip, end-to-end, that
mocks can't simulate.

Run before:
* Onboarding the first CH merchant in production.
* Releasing any change that touches ``payment_providers/stripe/`` or
  ``services/payment_checkout_service.py``.

## Prerequisites (one-time)

1. **Stripe test-mode account with TWINT enabled.**
   * Create / log in at https://dashboard.stripe.com/test/dashboard
   * Settings → Payment Methods → enable **TWINT**.
   * Country must be set to Switzerland (``CH``) on the test account.
   * Note the Stripe test API key (``sk_test_...``); set it as
     ``STRIPE_SECRET_KEY`` in the local backend ``.env``.

2. **Local AFianco environment running**
   * Backend on ``localhost:8001`` (or whichever port your
     worktree-isolated dev server uses).
   * Frontend on ``localhost:3003``.

3. **Test org with currency=CHF**
   * Either reuse an existing CHF org or create one via signup +
     Settings → Organization → Valuta = CHF.

4. **Stripe Connect connection on the test org**
   * Settings → Payment connections → connect Stripe.
   * Confirm connected account ID is visible in
     ``Settings → Metodi di pagamento → Account collegato``.

## Checklist

### A. Capabilities preflight (Settings UI)

- [ ] Login as the CHF test merchant.
- [ ] Navigate to ``/settings``.
- [ ] Scroll to **"Metodi di pagamento"** card. Confirm:
  - [ ] **Carte di credito**: ``Attivo`` badge.
  - [ ] **TWINT**: ``Attivo`` badge.
  - [ ] No yellow CTA banner ("Attiva TWINT su Stripe…") is shown.
- [ ] In a separate browser tab, disable TWINT on the Stripe
      dashboard (Settings → Payment methods → toggle TWINT off).
- [ ] Click the refresh button (↻) on the AFianco card.
- [ ] Confirm:
  - [ ] **TWINT** row now shows the warning icon and "Attiva su
        Stripe →" link.
  - [ ] Yellow CTA banner appears at the top of the card with the
        deep link to ``dashboard.stripe.com/settings/payment_methods``.
- [ ] Re-enable TWINT on Stripe; refresh; confirm both rows are
      green again.

### B. Checkout creation — TWINT visible

- [ ] Create a draft order with a single CHF line item ≥ 1.00 CHF.
- [ ] From the storefront, complete checkout to land on the Stripe
      hosted checkout URL.
- [ ] On the hosted page, confirm:
  - [ ] **TWINT** is offered alongside Credit Card.
  - [ ] The amount and currency display as ``CHF`` (e.g. ``CHF 49.50``).
- [ ] Pay with the Stripe TWINT test flow (use a 10-digit test phone
      number; Stripe simulates the TWINT QR confirmation).
- [ ] Wait for the redirect to ``/s/checkout-success?order_id=…``.

### C. Idempotency (key collapse)

- [ ] Note the Session ID (``cs_test_…``) on the success URL or in
      the Stripe dashboard.
- [ ] Trigger a second checkout for the **same** order (e.g. by
      clicking a "Pay now" link a second time before the first one
      completes).
- [ ] Confirm via Stripe dashboard that **no second Session was
      created** — the same ``cs_test_…`` is reused.
  * If a second session appears, the idempotency key is missing or
    being mutated; bisect via
    ``test_checkout_idempotency.py``.

### D. Webhook signature + currency match

- [ ] In Stripe dashboard → Developers → Webhooks, confirm the
      checkout event was delivered to the local endpoint.
- [ ] Confirm the order document has:
  - [ ] ``payment_intent: collected``
  - [ ] ``payment_checkout.payment_status: paid``
  - [ ] ``payment_checkout.processed_events`` includes the event id.
- [ ] In Stripe dashboard, manually replay the same event from the
      Webhooks page. Confirm the order is **not** double-processed
      (idempotent reconcile).
- [ ] (Tampering check) Send a POST to the webhook URL with an
      invalid ``Stripe-Signature`` header. Confirm the response is
      **400 Bad Request** and the order is unchanged.

### E. Audit log (Sub-stream 2.7)

- [ ] In MongoDB, query the ``audit_logs`` collection:
  ```js
  db.audit_logs.find({
    organization_id: "<org_id>",
    action: "payment.checkout.created"
  }).sort({_id: -1}).limit(1)
  ```
- [ ] Confirm the most recent entry has:
  - [ ] ``details.provider == "stripe"``
  - [ ] ``details.currency == "CHF"``
  - [ ] ``details.payment_method_types`` includes ``"twint"``
  - [ ] ``details.application_fee_percent == 0`` (founding clients)
  - [ ] ``details.session_id`` matches the Stripe session.

### F. Application fee (when monetization turns on)

> Skip this section while ``application_fee_percent`` is 0 across all
> orgs. Run it the first time you flip a non-zero fee on a test org.

- [ ] In MongoDB, set ``application_fee_percent: 1.5`` on the test
      org.
- [ ] Trigger a checkout for an EUR or CHF amount of 100.00.
- [ ] In Stripe dashboard, open the resulting Payment Intent.
- [ ] Confirm ``application_fee_amount`` is **150** (1.5 % of
      10 000 minor units).
- [ ] Reset the field to 0 when the test is done.

### G. EUR fallback

- [ ] Create a sibling org with ``currency=EUR``.
- [ ] Open Settings → Metodi di pagamento.
- [ ] Confirm:
  - [ ] Card row visible.
  - [ ] **No TWINT row** (TWINT is CHF-only).
  - [ ] No CHF-related banner.
- [ ] Run a checkout. Confirm the hosted page offers Card only and
      the amount is in ``€``.

## Non-test conditions to confirm separately

Some flows can't be exercised in test mode:

* **Live TWINT app integration.** Stripe's test mode simulates the
  TWINT flow without contacting the real TWINT app. Real-world
  validation requires a beta merchant.
* **Cross-currency fraud detection.** Stripe applies its own risk
  rules in test mode that differ from production; do not assume the
  same flag set will appear live.

## Sign-off

When every checkbox above is green, attach the Stripe dashboard
event IDs and the audit_logs entry ``_id`` to the release ticket and
mark the merchant ready for production.
