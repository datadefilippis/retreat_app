"""
Inbound webhook handlers for AFianco.

Each external service we integrate with that pushes events back to us
gets its own router file under this package. Conventions:

  - URL prefix: /api/webhooks/<service>
  - Verification: HMAC (Stripe) or shared secret in custom header (Brevo).
  - Idempotent: re-sending the same event must produce the same DB state
    (callers retry on transient failures).
  - Defensive: never raises 5xx for parseable but unknown event types
    (silently ignore so the provider does not retry endlessly).

Currently:
  - brevo.py  → bounce / complaint / blocked / unsubscribed (Phase 1 Step B2)

Future:
  - stripe.py would belong here too (currently still under routers/billing.py
    for historical reasons — refactor candidate).
"""
