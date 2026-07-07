"""
Payment Checkout Service — Stripe Connect commerce checkout lifecycle.

Model: Direct Charges on Standard Connected Accounts.
Sessions are created on the merchant's connected account via stripe_account param.

Lifecycle:
  1. create_checkout_session(org_id, order) → creates session on connected account
  2. Stripe webhook → reconcile_checkout_event(event) → validates + confirms order
  3. Order: payment_intent=collected → confirm_order() → SalesRecords

Reconciliation strategy:
  - Metadata on checkout session: org_id, order_id, source=afianco, flow_version
  - event.account identifies the connected account
  - Order lookup validates org_id + order_id + payment_checkout.reference match
  - Idempotency: payment_intent=collected check + processed_events list

Failure semantics:
  - Payment collected but confirm fails: payment_intent=collected, order stays draft
    Logged as CRITICAL. Operator can confirm manually. Truthful state preserved.
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

FLOW_VERSION = "connect_v1"

# Hard gate: Stripe rejects Checkout Sessions below a per-currency minimum
# (~0.50 in major currencies). Gating client-side keeps us from creating an
# order with a useless payment_checkout_url and surfaces a clean reason to
# the customer instead of a silent Session.create() failure.
# See https://stripe.com/docs/currencies#minimum-and-maximum-charge-amounts
#
# CH compliance v1: the minimum is now resolved per-currency via
# ``core.checkout_minimums.get_minimum(currency)``. The legacy
# ``MIN_CHECKOUT_AMOUNT_EUR`` symbol is preserved as an EUR-bound alias for
# backward compatibility — ``routers/public.py`` imports it directly to
# render a localized "below minimum" message. New call sites should use
# :func:`backend.core.checkout_minimums.get_minimum` with the order's
# currency instead.
from core.checkout_minimums import get_minimum as _get_minimum_for_currency

MIN_CHECKOUT_AMOUNT_EUR = float(_get_minimum_for_currency("EUR"))


def _get_stripe():
    import stripe
    stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
    return stripe


def _get_frontend_url() -> str:
    return os.environ.get("FRONTEND_URL", "https://afianco.app")


# ── Order Eligibility ─────────────────────────────────────────────────────

def check_order_eligibility(order: dict) -> tuple[bool, str]:
    """Check if an order's data is eligible for checkout (price, items).

    Does NOT check provider readiness — that's the resolution service's job.

    The minimum is resolved per the order's currency (CH compliance v1):
    a CHF order is gated by the CHF minimum, an EUR order by the EUR
    minimum. Orders without a currency snapshot fall back to EUR via
    :func:`services.currency_service.get_currency_for_order`, preserving
    legacy behaviour exactly.

    Reason codes:
      - payment_intent_not_required: order is not in a state that needs checkout
      - zero_total: total is 0 or negative
      - zero_price_line: at least one line has quantity > 0 but no price
      - below_minimum_amount: total is below the Stripe minimum charge floor
    """
    if order.get("payment_intent") != "required":
        return False, "payment_intent_not_required"
    total = order.get("total") or 0
    if total <= 0:
        return False, "zero_total"

    from services.currency_service import get_currency_for_order
    order_currency = get_currency_for_order(order)
    minimum = float(_get_minimum_for_currency(order_currency))

    if total < minimum:
        # Stripe would reject Session.create with amount_too_small; fail fast
        # so the frontend can show a specific, actionable message instead of a
        # generic "checkout unavailable" that hides the real reason.
        return False, "below_minimum_amount"
    for item in order.get("items", []):
        if item.get("line_total", 0) <= 0 and item.get("quantity", 0) > 0:
            return False, "zero_price_line"
    return True, "eligible"


# ── R1: line items che nettano a order["total"] ───────────────────────────

def _build_checkout_lines(order: dict):
    """Costruisce i CheckoutLineItem + l'importo sconto, garantendo
    ``Σ(line_items) − discount == order['total']``.

    - una riga per ogni item dell'ordine usando ``line_total`` (che include
      extras + rental multiplier + discount_pct), con quantity=1 (l'eventuale
      quantità è nel nome) → la somma = subtotal;
    - una riga "Spedizione" se ``fulfillment.shipping_cost > 0``;
    - lo sconto coupon (``discount_total``) restituito a parte → applicato come
      Stripe discount nel provider (Stripe non ammette line item negativi).

    Ritorna ``(tuple[CheckoutLineItem], discount_major: Decimal)``.
    """
    from decimal import Decimal as _D
    from payment_providers import CheckoutLineItem

    lines: list = []
    for item in order.get("items", []):
        qty = int(item.get("quantity") or 1)
        amount = item.get("line_total")
        if amount is None:
            amount = float(item.get("unit_price") or 0) * float(item.get("quantity") or 0)
        name = item.get("product_name") or "Articolo"
        if qty and qty != 1:
            name = f"{name} × {qty}"
        lines.append(CheckoutLineItem(name=name, quantity=1, unit_amount=_D(str(amount))))

    shipping = float((order.get("fulfillment") or {}).get("shipping_cost") or 0)
    if shipping > 0:
        lines.append(CheckoutLineItem(name="Spedizione", quantity=1, unit_amount=_D(str(shipping))))

    discount = _D(str(order.get("discount_total") or 0))

    # Guardia difensiva: se per qualunque drift Σ(lines) − discount ≠ total,
    # logghiamo (il test sentinella pinna l'uguaglianza nei casi normali).
    try:
        gross = sum((li.unit_amount for li in lines), _D("0"))
        net = gross - discount
        total = _D(str(order.get("total") or 0))
        if abs(net - total) >= _D("0.01"):
            logger.warning(
                "checkout lines mismatch order=%s net=%s total=%s",
                order.get("id"), net, total,
            )
    except Exception:
        pass

    return tuple(lines), discount


# ── Checkout Session Creation (Connected Account) ─────────────────────────

async def create_checkout_session(org_id: str, order: dict) -> Optional[dict]:
    """Create a Stripe Checkout Session on the merchant's connected account.

    Two-layer check:
      1. Order eligibility (price, items)
      2. Org payment readiness (resolution service)

    Returns {url, session_id, provider, connected_account} or None.
    """
    from services.payment_resolution import resolve_org_payment_readiness

    # Layer 1: Order data eligibility (price, items)
    eligible, reason = check_order_eligibility(order)
    if not eligible:
        logger.info("payment_checkout: order %s not eligible — %s", order.get("id"), reason)
        return None

    # Layer 2: Availability safety — is direct payment safe for these items?
    from services.commerce_rules import is_direct_checkout_safe_async
    safe, safety_reason = await is_direct_checkout_safe_async(order, org_id)
    if not safe:
        logger.info("payment_checkout: order %s not safe for direct checkout — %s", order.get("id"), safety_reason)
        return None

    # Layer 3: Org payment provider readiness
    readiness = await resolve_org_payment_readiness(org_id)
    if not readiness.checkout_available:
        logger.info("payment_checkout: org %s not ready — %s", org_id, readiness.reason_code)
        return None

    # Resolve the connected account ID
    connected_account_id = await _get_connected_account_id(org_id)
    if not connected_account_id:
        logger.warning("payment_checkout: org %s has no connected account ID", org_id)
        return None

    frontend_url = _get_frontend_url()
    order_id = order["id"]

    # CH compliance v1: derive the Stripe Session currency from the order's
    # snapshot (with org / EUR fallbacks). Stripe expects lowercase ISO 4217.
    from services.currency_service import get_currency_for_order
    order_currency = get_currency_for_order(order)

    if not order.get("items"):
        return None

    # Fase 7a: pass customer_email so Stripe dedupes the guest Customer across
    # repeat purchases by the same buyer on this connected account. Without
    # this, each checkout creates a brand-new "guest" Customer, cluttering the
    # merchant's Stripe Customers list and breaking repeat-customer analytics.
    # Best-effort: a missing email never blocks the checkout.
    customer_email = await _lookup_customer_email(order.get("customer_id"), org_id)

    # Sub-stream 2.3: route the actual SDK call through the provider
    # abstraction so future Datatrans/PostFinance integrations are a
    # localized addition rather than a 30-day refactor. Behaviour is
    # bit-for-bit identical to the previous direct-stripe path: same
    # metadata keys, same line_items shape, same persisted document.
    from decimal import Decimal as _Decimal
    from payment_providers import (
        CheckoutLineItem,
        CheckoutSessionRequest,
        PaymentProviderRegistry,
        ProviderError,
    )

    org_doc_for_provider = await _resolve_org_doc_for_provider(org_id)
    provider = PaymentProviderRegistry.get_for_org(org_doc_for_provider)

    # Sub-stream 2.6: read the platform application fee off the org
    # doc. v1 default is 0.0 — the first 10 founding clients pay no
    # platform cut on top of Stripe's transaction fee. When monetization
    # turns on, flipping this field per-org is a DB write — no code
    # change. Defensive coercion below tolerates legacy docs where the
    # field is absent or stored as int/string.
    application_fee_percent = _Decimal(str(
        (org_doc_for_provider or {}).get("application_fee_percent", 0) or 0
    ))

    # R1 — line_items che NETTANO a order["total"]: per ogni riga si usa
    # ``line_total`` (che INCLUDE extras + rental mult + discount_pct), non
    # ``unit_price×qty`` (che li ignorava). Si aggiunge la riga Spedizione e si
    # passa lo sconto coupon a parte (applicato come Stripe discount nel
    # provider). Invariante: Σ(line_items) − discount == order["total"].
    line_item_models, discount_amount = _build_checkout_lines(order)

    # Sub-stream 2.5: a deterministic idempotency key prevents Stripe
    # from creating a second Session if afianco retries the request
    # within Stripe's 24h idempotency window. Same input (order_id) →
    # same Session (Stripe returns the cached response).
    #
    # We DO NOT include retry counters in the key — that would defeat
    # the goal: a network blip on the second attempt would otherwise
    # create a new Session under a different key. Letting Stripe
    # collapse them is precisely what idempotency keys are for.
    idempotency_key = f"checkout:{order_id}"

    # ── Fase 2 S2 (retreat) — checkout schedule-aware ──────────────────────
    # Se l'ordine ha un PaymentSchedule con riga caparra addebitabile, la
    # session incassa SOLO la caparra: una riga "Caparra — {ritiro}", niente
    # discount separato (il coupon è già dentro il totale su cui la caparra
    # è stata calcolata alla generazione dello schedule). Il saldo viaggerà
    # su session dedicate generate dallo scheduler (S3). Metadata estesa con
    # schedule_row_seq così il webhook fa la transizione della riga giusta.
    from services.payment_schedule_service import (
        get_schedule_for_order,
        pending_charge_row,
    )
    # Solo gli ordini-ritiro (riga evento con data) possono avere una caparra:
    # per tutto il resto niente lookup — zero costo e zero deviazioni sul
    # flusso storico.
    has_event_line = any(
        (it or {}).get("occurrence_id") for it in (order.get("items") or [])
    )
    schedule_doc = await get_schedule_for_order(order_id, org_id) if has_event_line else None
    deposit_row = pending_charge_row(schedule_doc)
    schedule_metadata = {}
    if deposit_row is not None:
        deposit_eur = _Decimal(deposit_row["amount_minor"]) / _Decimal(100)
        first_item_name = (order.get("items") or [{}])[0].get("product_name") or "ritiro"
        line_item_models = [CheckoutLineItem(
            name=f"Caparra — {first_item_name}",
            quantity=1,
            unit_amount=deposit_eur,
        )]
        discount_amount = _Decimal("0")
        idempotency_key = f"checkout:{order_id}:row:{deposit_row['seq']}"
        schedule_metadata = {
            "schedule_id": schedule_doc["id"],
            "schedule_row_seq": str(deposit_row["seq"]),
        }
        logger.info(
            "payment_checkout: deposit mode for order %s — charging row %s (%s minor)",
            order_id, deposit_row["seq"], deposit_row["amount_minor"],
        )

    request = CheckoutSessionRequest(
        org_id=org_id,
        order_id=order_id,
        currency=order_currency,
        line_items=line_item_models,
        success_url=f"{frontend_url}/s/checkout-success?order_id={order_id}",
        cancel_url=f"{frontend_url}/s/checkout-cancel?order_id={order_id}",
        customer_email=customer_email,
        idempotency_key=idempotency_key,
        application_fee_percent=application_fee_percent,
        discount_amount=discount_amount,  # R1
        metadata={
            "checkout_type": "commerce",
            "order_id": order_id,
            "org_id": org_id,
            "source": "afianco",
            "flow_version": FLOW_VERSION,
            # Carrier — provider strips this from outgoing Stripe metadata.
            "connected_account_id": connected_account_id,
            # SA1 — la percentuale viaggia con la session: al webhook la
            # fee si timbra con il valore VERO della creazione, immune
            # ai cambi piano avvenuti nel frattempo.
            "application_fee_percent": str(application_fee_percent),
            # Fase 2 S2 — presente solo per session-caparra (vuoto = full).
            **schedule_metadata,
        },
    )

    try:
        result = await provider.create_checkout_session(request)

        now = datetime.now(timezone.utc).isoformat()

        # Persist checkout handoff on the order
        from database import orders_collection
        await orders_collection.update_one(
            {"id": order_id, "organization_id": org_id},
            {"$set": {
                "payment_checkout": {
                    "url": result.url,
                    "provider": result.provider,
                    "reference": result.session_id,
                    "connected_account_id": result.connected_account or connected_account_id,
                    "flow_version": FLOW_VERSION,
                    "created_at": now,
                },
                "updated_at": now,
            }},
        )

        logger.info(
            "payment_checkout: created session %s on account %s for order %s org=%s (provider=%s methods=%s)",
            result.session_id, connected_account_id, order_id, org_id,
            result.provider, ",".join(result.payment_method_types) or "default",
        )

        # Fase 2 S2 — riga caparra → processing (session emessa, esito non
        # noto). Evita session duplicate applicative; best-effort: un fallo
        # qui non blocca il checkout (la guardia vera è l'idempotency key).
        if deposit_row is not None:
            try:
                from models.payment_schedule import RowStatus
                from services.payment_schedule_service import apply_row_transition
                if deposit_row.get("status") == RowStatus.PENDING.value:
                    await apply_row_transition(
                        schedule_doc, deposit_row["seq"], RowStatus.PROCESSING,
                        actor="system:checkout",
                        action="row_session_created",
                        row_updates={"stripe_session_id": result.session_id},
                        detail={"session_id": result.session_id},
                    )
            except Exception as exc_row:
                logger.warning(
                    "payment_checkout: row processing mark failed for order %s: %s",
                    order_id, exc_row,
                )

        # Sub-stream 2.7: audit trail. Best-effort write to the
        # ``audit_logs`` collection so customer-support and finance can
        # reconstruct exactly which provider + payment methods + fee
        # were offered for any order, even years later. Failures here
        # MUST NOT block the checkout flow — the merchant has already
        # built a session URL and the customer is about to click it.
        try:
            from repositories import audit_repository
            from models import AuditLog
            await audit_repository.create(AuditLog(
                organization_id=org_id,
                user_id="system",
                action="payment.checkout.created",
                resource_type="order",
                resource_id=order_id,
                details={
                    "provider": result.provider,
                    "session_id": result.session_id,
                    "connected_account_id": result.connected_account or connected_account_id,
                    "currency": order_currency,
                    "payment_method_types": list(result.payment_method_types),
                    "application_fee_percent": float(application_fee_percent),
                    "flow_version": FLOW_VERSION,
                },
            ))
        except Exception as audit_err:
            logger.warning(
                "payment_checkout: audit log write failed for order %s: %s",
                order_id, audit_err,
            )

        return {
            "url": result.url,
            "session_id": result.session_id,
            "provider": result.provider,
            "connected_account": result.connected_account or connected_account_id,
        }

    except ProviderError as exc:
        # Provider explicitly raised — code/provider attributes already
        # carry the diagnostic context. Caller treats None as "checkout
        # not available right now" and surfaces a clean UX message.
        logger.error(
            "payment_checkout: provider %s rejected session for order %s: code=%s msg=%s",
            getattr(exc, "provider", "?"), order_id,
            getattr(exc, "code", "?"), exc,
        )
        return None
    except Exception as exc:
        logger.error("payment_checkout: session creation failed for order %s: %s", order_id, exc)
        return None


async def _resolve_org_doc_for_provider(org_id: str) -> Optional[dict]:
    """Fetch the bare minimum from the org doc that the provider
    registry needs to pick the right :class:`PaymentProvider`.

    We only read ``payment_provider`` (defaults to "stripe" inside
    the registry). Keeping the projection narrow avoids loading the
    full org document for what is, today, a one-field decision.
    """
    from repositories import organization_repository
    try:
        return await organization_repository.find_by_id(org_id)
    except Exception:
        # Defensive: registry handles a None org gracefully (falls
        # back to the default "stripe" provider) so a transient DB
        # hiccup must not block checkout.
        return None


async def _get_connected_account_id(org_id: str) -> Optional[str]:
    """Get the connected Stripe account ID for an org."""
    from database import payment_connections_collection
    conn = await payment_connections_collection.find_one(
        {"organization_id": org_id, "provider": "stripe", "is_default": True,
         "status": "active", "runtime_status": "ready"},
        {"_id": 0, "external_account_id": 1},
    )
    return conn.get("external_account_id") if conn else None


async def _lookup_customer_email(customer_id: Optional[str], org_id: str) -> Optional[str]:
    """Resolve the customer's email for the Stripe Customer dedup hint.

    Returns None if no customer_id, no matching customer, or no email on file
    — callers must treat a None return as "best-effort, skip the prefill".
    """
    if not customer_id:
        return None
    try:
        from database import customers_collection
        cust = await customers_collection.find_one(
            {"id": customer_id, "organization_id": org_id},
            {"_id": 0, "email": 1},
        )
    except Exception as exc:
        logger.warning(
            "payment_checkout: customer lookup failed for %s (org=%s): %s",
            customer_id, org_id, exc,
        )
        return None
    email = (cust or {}).get("email")
    # Very light sanity check: Stripe rejects obviously malformed emails;
    # defer to them for the full validation rather than duplicating it here.
    if not email or "@" not in email:
        return None
    return email


# ── Pull-based Verification (manual safety net for webhook failures) ──────

async def verify_commerce_order_payment(order_id: str, org_id: str) -> dict:
    """Ask Stripe directly whether a commerce order's checkout session was paid.

    Purpose:
      The webhook path is the primary reconciliation channel. Occasionally
      events fail permanently (endpoint misconfig, Stripe delivery issue,
      extended downtime) and orders get stuck in draft even though the
      customer paid. This function is the admin-triggered safety net.

    Flow:
      1. Load order, validate org ownership + that a Stripe session exists.
      2. stripe.checkout.Session.retrieve against the connected account,
         normalized to dict (Fase 5a — v15 compat).
      3. If payment_status == "paid", construct a synthetic event and feed
         it to reconcile_checkout_event — reusing the canonical path so
         side effects (order confirm, alerts, emails) are identical to a
         real webhook arrival. The synthetic event_id is prefixed so a
         later real webhook is not double-counted (reconcile's internal
         idempotency on processed_events handles the rest).
      4. If payment_status is anything else (unpaid/no_payment_required),
         report truthfully without mutating the order.

    Returns a dict with a `status` key:
      - "reconciled":       payment was paid and we just confirmed the order
      - "already_reconciled": order was already collected; idempotent no-op
      - "still_unpaid":     Stripe says the session is not paid
      - "session_not_found": order has no stored session reference
      - "error":            Stripe API error or internal problem

    Never raises — callers are admin endpoints, they deserve structured
    responses instead of 500s.
    """
    from database import orders_collection

    order = await orders_collection.find_one(
        {"id": order_id, "organization_id": org_id},
        {"_id": 0},
    )
    if not order:
        return {"status": "error", "reason": "order_not_found", "order_id": order_id}

    # Already reconciled — nothing to do
    if order.get("payment_intent") == "collected":
        return {
            "status": "already_reconciled",
            "order_id": order_id,
            "order_number": order.get("order_number"),
        }

    pc = order.get("payment_checkout") or {}
    session_id = pc.get("reference")
    connected_account_id = pc.get("connected_account_id")

    if not session_id:
        return {"status": "session_not_found", "order_id": order_id}

    # Retrieve the Session directly from Stripe on the connected account.
    stripe = _get_stripe()
    try:
        if connected_account_id:
            raw_session = await asyncio.to_thread(
                stripe.checkout.Session.retrieve,
                session_id,
                stripe_account=connected_account_id,
            )
        else:
            # Legacy path: some early sessions may lack connected_account_id;
            # fall back to the platform account (Standard charges).
            raw_session = await asyncio.to_thread(
                stripe.checkout.Session.retrieve, session_id,
            )
    except Exception as exc:
        logger.warning(
            "verify_commerce: Session.retrieve failed for order=%s session=%s: %s",
            order_id, session_id, exc,
        )
        return {
            "status": "error",
            "reason": "stripe_retrieve_failed",
            "error": str(exc)[:300],
            "order_id": order_id,
        }

    # Normalize to dict (v15 compat) so downstream .get() calls are safe
    from services.stripe_service import _normalize_stripe_object
    session = _normalize_stripe_object(raw_session)

    payment_status = session.get("payment_status")
    logger.info(
        "verify_commerce: order=%s session=%s payment_status=%s",
        order_id, session_id, payment_status,
    )

    if payment_status != "paid":
        return {
            "status": "still_unpaid",
            "order_id": order_id,
            "payment_status": payment_status,
            "session_status": session.get("status"),
        }

    # Synthesize an event-shaped dict and delegate to the canonical reconciler.
    # The "verify_" prefix on the event_id makes it distinguishable from real
    # Stripe events; reconcile's processed_events idempotency prevents any
    # double-effect if a real webhook lands afterwards.
    synthetic_event = {
        "id": f"verify_{order_id}_{session_id}",
        "type": "checkout.session.completed",
        "account": connected_account_id,
        "data": {"object": session},
    }
    result = await reconcile_checkout_event(synthetic_event)

    # Translate reconcile's action vocabulary into the verify API's vocabulary
    action = result.get("action")
    if action == "confirmed":
        return {
            "status": "reconciled",
            "order_id": order_id,
            "order_number": result.get("order_number"),
            "stripe_payment_intent": result.get("stripe_payment_intent"),
        }
    if action in ("skipped",) and result.get("reason") in ("already_collected", "event_already_processed"):
        return {
            "status": "already_reconciled",
            "order_id": order_id,
            "order_number": order.get("order_number"),
        }
    if action == "payment_collected_confirm_failed":
        return {
            "status": "error",
            "reason": "confirm_failed",
            "error": result.get("error"),
            "order_id": order_id,
        }
    # Any other reconcile outcome — bubble it up so the caller has context
    return {
        "status": "error",
        "reason": "reconcile_unexpected",
        "action": action,
        "order_id": order_id,
    }


# ── Webhook Reconciliation ─────────────────────────────────────────────────

async def create_row_checkout_session(
    org_id: str, order: dict, schedule_doc: dict, row: dict,
) -> Optional[dict]:
    """Checkout Session per UNA riga dello schedule (saldo/rata) — S3.

    Usata dalla pagina pubblica /pay/{token} e dal job promemoria: genera
    la session FRESCA al momento del bisogno (le session scadono in 24h,
    per questo nelle email viaggia il token, mai l'URL Stripe).

    Differenze dal checkout-ordine:
      · line item = la sola riga (label + prodotto), fee piattaforma sul
        suo importo;
      · la session id NON sovrascrive payment_checkout.reference (che
        appartiene alla session-caparra): finisce sulla riga e in
        payment_checkout.row_sessions — il reconcile valida contro quelli.
    """
    from decimal import Decimal as _Decimal
    from payment_providers import (
        CheckoutLineItem, CheckoutSessionRequest,
        PaymentProviderRegistry, ProviderError,
    )
    from models.payment_schedule import RowStatus
    from services.payment_schedule_service import (
        PAYABLE_STATES, apply_row_transition, refresh_row_session_id,
    )

    if row.get("status") not in PAYABLE_STATES:
        return None
    if order.get("status") == "draft" and row.get("seq", 0) != 0:
        # saldo/rate esistono solo su ordini confermati (caparra pagata)
        return None

    connected_account_id = await _get_connected_account_id(org_id)
    if not connected_account_id:
        return None
    org_doc_for_provider = await _resolve_org_doc_for_provider(org_id)
    provider = PaymentProviderRegistry.get_for_org(org_doc_for_provider)
    application_fee_percent = _Decimal(str(
        (org_doc_for_provider or {}).get("application_fee_percent", 0) or 0))

    from services.currency_service import get_currency_for_order
    order_id = order["id"]
    row_seq = row["seq"]
    first_item_name = (order.get("items") or [{}])[0].get("product_name") or "ritiro"
    amount_eur = _Decimal(row["amount_minor"]) / _Decimal(100)
    frontend_url = _get_frontend_url()

    request = CheckoutSessionRequest(
        org_id=org_id,
        order_id=order_id,
        currency=get_currency_for_order(order),
        line_items=[CheckoutLineItem(
            name=f"{row.get('label', 'Pagamento')} — {first_item_name}",
            quantity=1, unit_amount=amount_eur,
        )],
        success_url=f"{frontend_url}/s/checkout-success?order_id={order_id}",
        cancel_url=f"{frontend_url}/s/checkout-cancel?order_id={order_id}",
        customer_email=await _lookup_customer_email(order.get("customer_id"), org_id),
        # chiave per-riga: dopo le 24h Stripe la considera nuova (come la
        # session scaduta) — il link /pay resta quindi sempre vivo
        idempotency_key=f"checkout:{order_id}:row:{row_seq}",
        application_fee_percent=application_fee_percent,
        discount_amount=_Decimal("0"),
        metadata={
            "checkout_type": "commerce",
            "order_id": order_id,
            "org_id": org_id,
            "source": "afianco",
            "flow_version": FLOW_VERSION,
            "connected_account_id": connected_account_id,
            # SA1 — vedi checkout principale: fee timbrata alla creazione
            "application_fee_percent": str(application_fee_percent),
            "schedule_id": schedule_doc["id"],
            "schedule_row_seq": str(row_seq),
        },
    )
    try:
        result = await provider.create_checkout_session(request)
    except ProviderError as exc:
        logger.error("row checkout: provider rejected order=%s row=%s: %s",
                     order_id, row_seq, exc)
        return None

    # traccia la session: sulla riga + nel set noto all'ordine (reconcile)
    from database import orders_collection
    from models.common import utc_now as _now
    await orders_collection.update_one(
        {"id": order_id, "organization_id": org_id},
        {"$addToSet": {"payment_checkout.row_sessions": result.session_id},
         "$set": {"updated_at": _now()}},
    )
    try:
        if row.get("status") == RowStatus.PENDING.value or row.get("status") in (
                RowStatus.OVERDUE.value, RowStatus.AT_RISK.value):
            await apply_row_transition(
                schedule_doc, row_seq, RowStatus.PROCESSING,
                actor="system:pay-link",
                action="row_session_created",
                row_updates={"stripe_session_id": result.session_id},
                detail={"session_id": result.session_id},
            )
        else:  # già processing: session precedente scaduta, refresh id
            await refresh_row_session_id(
                schedule_doc, row_seq, result.session_id, actor="system:pay-link")
    except Exception as exc:
        logger.warning("row checkout: row mark failed order=%s row=%s: %s",
                       order_id, row_seq, exc)

    return {"url": result.url, "session_id": result.session_id,
            "connected_account": result.connected_account or connected_account_id}


async def reconcile_checkout_event(event: dict) -> dict:
    """Central reconciliation entry point for commerce checkout webhooks.

    Validates, resolves, and processes a checkout.session.completed event.

    Uses multiple identification layers:
      1. event.account → connected Stripe account
      2. session.metadata.org_id → AFianco organization
      3. session.metadata.order_id → AFianco order
      4. order.payment_checkout.reference → must match session.id

    Returns structured result with action taken.
    """
    session = event["data"]["object"]
    event_id = event.get("id", "unknown")
    event_account = event.get("account")  # connected account that owns this event

    session_id = session.get("id")
    metadata = session.get("metadata", {})
    order_id = metadata.get("order_id")
    org_id = metadata.get("org_id")
    source = metadata.get("source")
    payment_status = session.get("payment_status")

    logger.info(
        "payment_reconcile: event=%s session=%s account=%s org=%s order=%s payment=%s",
        event_id, session_id, event_account, org_id, order_id, payment_status,
    )

    # ── Validate metadata ──────────────────────────────────────────────────
    if source != "afianco":
        logger.warning("payment_reconcile: session %s missing afianco source marker — skipping", session_id)
        return {"action": "skipped", "reason": "not_afianco_session"}

    if not order_id or not org_id:
        raise ValueError(f"Missing order_id or org_id in session metadata: session={session_id}")

    if payment_status != "paid":
        logger.info("payment_reconcile: session %s payment_status=%s — skipping", session_id, payment_status)
        return {"action": "skipped", "reason": f"payment_status={payment_status}"}

    # ── Resolve and validate order ─────────────────────────────────────────
    from database import orders_collection
    order = await orders_collection.find_one(
        {"id": order_id, "organization_id": org_id},
        {"_id": 0},
    )

    if not order:
        raise ValueError(f"Order {order_id} not found for org {org_id}")

    # Validate session reference matches what we stored.
    # S3: oltre alla session-ordine (caparra/unico) esistono session
    # PER-RIGA (saldo/rate via /pay/{token}) tracciate in row_sessions —
    # una session nota in quel set è altrettanto legittima.
    stored_ref = (order.get("payment_checkout") or {}).get("reference")
    known_row_sessions = set((order.get("payment_checkout") or {}).get("row_sessions") or [])
    if stored_ref and stored_ref != session_id and session_id not in known_row_sessions:
        logger.warning(
            "payment_reconcile: session mismatch — stored=%s received=%s for order %s",
            stored_ref, session_id, order_id,
        )
        raise ValueError(f"Session reference mismatch: stored={stored_ref} received={session_id}")

    # Validate connected account matches if available
    stored_account = (order.get("payment_checkout") or {}).get("connected_account_id")
    if stored_account and event_account and stored_account != event_account:
        logger.warning(
            "payment_reconcile: account mismatch — stored=%s event=%s for order %s",
            stored_account, event_account, order_id,
        )
        raise ValueError(f"Connected account mismatch: stored={stored_account} event={event_account}")

    # CH compliance v1: validate currency snapshot matches what Stripe charged.
    # A mismatch is a tampering signal (or a release-time bug) and must NOT be
    # silently reconciled — refusing here keeps the audit trail honest and
    # prevents booking a CHF charge against an EUR order or vice versa.
    session_currency_raw = session.get("currency")
    if session_currency_raw:
        from services.currency_service import get_currency_for_order
        order_currency = get_currency_for_order(order).upper()
        session_currency = str(session_currency_raw).upper()
        if session_currency != order_currency:
            logger.error(
                "payment_reconcile: currency mismatch — order=%s expected=%s got=%s session=%s",
                order_id, order_currency, session_currency, session_id,
            )
            raise ValueError(
                f"Currency mismatch: order={order_currency} session={session_currency}"
            )

    # ── Idempotency: already processed? ────────────────────────────────────
    processed_events = order.get("payment_checkout", {}).get("processed_events", [])
    if event_id in processed_events:
        logger.info("payment_reconcile: event %s already processed for order %s", event_id, order_id)
        return {"action": "skipped", "reason": "event_already_processed", "order_id": order_id}

    if order.get("payment_intent") == "collected":
        # S3 — l'ordine è già incassato (caparra) ma QUESTA session può
        # essere il pagamento di una riga successiva (saldo/rata): la
        # transizione della riga va applicata comunque, altrimenti il
        # saldo pagato non verrebbe mai registrato a libro.
        row_seq_raw = metadata.get("schedule_row_seq")
        if row_seq_raw is not None:
            try:
                from services.payment_schedule_service import (
                    apply_stripe_payment_to_schedule,
                )
                updated_schedule = await apply_stripe_payment_to_schedule(
                    order_id, org_id, int(row_seq_raw),
                    stripe_payment_intent=session.get("payment_intent"),
                    stripe_session_id=session_id,
                )
                if updated_schedule:
                    await orders_collection.update_one(
                        {"id": order_id, "organization_id": org_id},
                        {"$set": {"payment_state": updated_schedule.get("payment_state")}},
                    )
                    logger.info(
                        "payment_reconcile: row %s paid on collected order %s (state=%s)",
                        row_seq_raw, order_id, updated_schedule.get("payment_state"),
                    )
            except Exception as exc_sched:
                logger.error(
                    "payment_reconcile: row transition on collected order %s failed: %s",
                    order_id, exc_sched,
                )
        # SA1 — anche il saldo/rata pagato online è transato fee-bearing:
        # una riga di ledger per QUESTA session (idempotente su session_id)
        if row_seq_raw is not None:
            from services.platform_fee_ledger import record_from_session
            await record_from_session(
                session, organization_id=org_id, order_id=order_id,
                kind="schedule_row", row_seq=int(row_seq_raw))
        logger.info("payment_reconcile: order %s already collected — recording event only", order_id)
        await _record_event(orders_collection, order_id, org_id, event_id, session_id)
        return {"action": "skipped", "reason": "already_collected", "order_id": order_id,
                "row_seq": row_seq_raw}

    # ── Apply payment ──────────────────────────────────────────────────────
    from models.common import utc_now
    now = utc_now()

    # Extract Stripe payment intent ID for audit trail
    stripe_pi = session.get("payment_intent")

    await orders_collection.update_one(
        {"id": order_id, "organization_id": org_id},
        {"$set": {
            "payment_intent": "collected",
            "payment_checkout.payment_status": "paid",
            "payment_checkout.completed_at": now.isoformat(),
            "payment_checkout.stripe_payment_intent_id": stripe_pi,
            "payment_checkout.event_account": event_account,
            "updated_at": now,
        },
        "$push": {
            "payment_checkout.processed_events": event_id,
        }},
    )

    # SA1 — il primo incasso online timbra il ledger fee: transato +
    # percentuale (dal metadata della session) + fee piattaforma.
    from services.platform_fee_ledger import record_from_session
    row_seq_meta = (session.get("metadata") or {}).get("schedule_row_seq")
    await record_from_session(
        session, organization_id=org_id, order_id=order_id,
        kind="schedule_row" if row_seq_meta is not None else "checkout",
        row_seq=int(row_seq_meta) if row_seq_meta is not None else None)

    logger.info("payment_reconcile: payment_intent=collected for order %s (pi=%s)", order_id, stripe_pi)

    # ── Fase 2 S2 — transizione riga schedule (caparra o pagamento unico) ──
    # La session porta schedule_row_seq quando è una session-caparra; per i
    # piani full la riga 0 è comunque il pagamento intero. Il ledger passa a
    # paid QUI, nel punto in cui il denaro è certo. Idempotente: il webhook
    # doppio perde sulla guardia ottimistica e non tocca nulla.
    try:
        from services.payment_schedule_service import (
            apply_stripe_payment_to_schedule,
            get_schedule_for_order,
        )
        row_seq_raw = metadata.get("schedule_row_seq")
        target_seq = int(row_seq_raw) if row_seq_raw is not None else 0
        updated_schedule = await apply_stripe_payment_to_schedule(
            order_id, org_id, target_seq,
            stripe_payment_intent=stripe_pi,
            stripe_session_id=session_id,
        )
        if updated_schedule:
            # Mirror denormalizzato per le liste admin: la fonte di verità
            # resta lo schedule; l'ordine espone lo stato derivato.
            await orders_collection.update_one(
                {"id": order_id, "organization_id": org_id},
                {"$set": {"payment_state": updated_schedule.get("payment_state")}},
            )
    except Exception as exc_sched:
        # Il ledger non deve MAI bloccare la conferma di un pagamento reale;
        # l'evento resta ricostruibile da Stripe + audit. Log severo.
        logger.error(
            "payment_reconcile: schedule transition failed for order %s: %s",
            order_id, exc_sched,
        )

    # ── Confirm order ──────────────────────────────────────────────────────
    from services.order_service import confirm_order

    try:
        confirmed = await confirm_order(org_id, order_id, skip_payment_check=True)
        order_number = confirmed.get("order_number")
        logger.info("payment_reconcile: order %s confirmed (number=%s)", order_id, order_number)

        # The "new order arrived" merchant email is part of the request-mode
        # flow (sent from POST /order-request immediately on submission).
        # For direct-mode orders we deliberately deferred it to here, after
        # the customer has actually paid: see the guard in routers/public.py
        # around the notify_customer_order_received block. Without this
        # call the merchant would never know a paid direct-mode order
        # arrived (the customer-side `notify_customer_order_confirmed` in
        # confirm_order does not loop back to the merchant).
        try:
            from services.order_email_service import notify_merchant_new_order
            await notify_merchant_new_order(confirmed, org_id)
        except Exception as exc_email:
            logger.warning(
                "payment_reconcile: merchant new-order email failed for %s: %s",
                order_id, exc_email,
            )

        # P2 Passaporto Ritiri — al primo pagamento riuscito, invito il
        # cliente a reclamare il suo account unico ("Gestisci le tue
        # prenotazioni", magic link). Idempotente: solo account non
        # verificati, cooldown 24h. Best-effort: mai bloccare l'incasso.
        try:
            from services.platform_account_service import (
                send_claim_email_if_needed,
            )
            await send_claim_email_if_needed(confirmed)
        except Exception as exc_claim:
            logger.warning(
                "payment_reconcile: claim email piattaforma fallita per %s: %s",
                order_id, exc_claim,
            )

        return {
            "action": "confirmed",
            "order_id": order_id,
            "org_id": org_id,
            "order_number": order_number,
            "event_id": event_id,
            "stripe_payment_intent": stripe_pi,
        }

    except Exception as exc:
        # CRITICAL: Payment collected but business confirmation failed.
        # State is truthful: payment_intent=collected, status=draft.
        # Operator can confirm manually. No data corruption.
        logger.error(
            "payment_reconcile: CRITICAL — payment collected for order %s but confirm failed: %s",
            order_id, exc,
        )

        # Record the failure for audit
        await orders_collection.update_one(
            {"id": order_id, "organization_id": org_id},
            {"$set": {
                "payment_checkout.confirm_error": str(exc)[:300],
                "payment_checkout.confirm_failed_at": now.isoformat(),
            }},
        )

        # Fase 5d: persist alert + notify admins + ops (best-effort, never raises).
        # Customer has been charged; staff must see this surfaced somewhere other
        # than raw application logs.
        try:
            from services.critical_alert_service import emit_payment_confirm_failed
            # Pull customer email from order if available for inclusion in the alert
            _customer_email = None
            try:
                from database import customers_collection
                _cust = await customers_collection.find_one(
                    {"id": order.get("customer_id"), "organization_id": org_id},
                    {"_id": 0, "email": 1},
                )
                if _cust:
                    _customer_email = _cust.get("email")
            except Exception:
                pass
            await emit_payment_confirm_failed(
                org_id=org_id,
                order_id=order_id,
                order_number=order.get("order_number"),
                event_id=event_id,
                error_detail=str(exc)[:500],
                stripe_payment_intent_id=stripe_pi,
                customer_email=_customer_email,
                total=order.get("total"),
                currency=order.get("currency", "EUR"),
            )
        except Exception as alert_err:
            # Alerting failure must never prevent the reconcile loop from returning
            # the truthful action code to Stripe (so retries stop spamming).
            logger.error(
                "payment_reconcile: alert dispatch failed for order %s: %s",
                order_id, alert_err,
            )

        return {
            "action": "payment_collected_confirm_failed",
            "order_id": order_id,
            "org_id": org_id,
            "error": str(exc),
            "event_id": event_id,
        }


async def _record_event(collection, order_id: str, org_id: str, event_id: str, session_id: str):
    """Record a processed event ID on the order for idempotency."""
    await collection.update_one(
        {"id": order_id, "organization_id": org_id},
        {"$addToSet": {"payment_checkout.processed_events": event_id}},
    )


# ── Post-charge events: refund + dispute (Fase 7c) ────────────────────────

async def _find_order_by_payment_intent(stripe_payment_intent_id: str) -> Optional[dict]:
    """Look up a commerce order by its stored Stripe Payment Intent ID.

    Returns the full order dict (sans _id) or None. Intended for webhook
    handlers that receive a charge object and need to correlate back.
    """
    if not stripe_payment_intent_id:
        return None
    from database import orders_collection
    return await orders_collection.find_one(
        {"payment_checkout.stripe_payment_intent_id": stripe_payment_intent_id},
        {"_id": 0},
    )


async def handle_charge_refunded(event: dict) -> dict:
    """Webhook handler: merchant (or admin) issued a refund on a commerce charge.

    Stripe sends `charge.refunded` whenever a Charge on a connected account
    receives a refund. We map it back to an AFianco order via the stored
    payment_intent id and mark payment_intent=refunded. Idempotent per event_id.

    Returns structured dict for the dispatcher. Never raises.
    """
    charge = event["data"]["object"]
    event_id = event.get("id", "unknown")
    pi = charge.get("payment_intent")
    amount_refunded = charge.get("amount_refunded") or 0
    from services.currency_service import DEFAULT_CURRENCY
    currency = (charge.get("currency") or DEFAULT_CURRENCY).upper()
    refunded_fully = bool(charge.get("refunded"))

    order = await _find_order_by_payment_intent(pi)
    if not order:
        logger.info(
            "charge.refunded: no matching order for payment_intent=%s event=%s",
            pi, event_id,
        )
        return {"status": "ignored", "reason": "no_matching_order", "event_id": event_id}

    order_id = order["id"]
    org_id = order["organization_id"]

    # Idempotency: skip if we've already processed this event.
    processed_events = (order.get("payment_checkout") or {}).get("processed_events") or []
    if event_id in processed_events:
        logger.info(
            "charge.refunded: event %s already processed for order %s",
            event_id, order_id,
        )
        return {"status": "skipped", "reason": "event_already_processed", "order_id": order_id}

    from database import orders_collection
    from models.common import utc_now
    now = utc_now()

    amount_refunded_major = amount_refunded / 100.0
    new_intent = "refunded" if refunded_fully else "partially_refunded"

    await orders_collection.update_one(
        {"id": order_id, "organization_id": org_id},
        {"$set": {
            "payment_intent": new_intent,
            "payment_checkout.refunded_at": now.isoformat(),
            "payment_checkout.refund_amount": amount_refunded_major,
            "payment_checkout.refund_currency": currency,
            "updated_at": now,
        },
        "$push": {"payment_checkout.processed_events": event_id}},
    )

    logger.info(
        "charge.refunded: order %s → payment_intent=%s (refunded=%s %s)",
        order_id, new_intent, amount_refunded_major, currency,
    )

    return {
        "action": "refund_recorded",
        "order_id": order_id,
        "org_id": org_id,
        "new_intent": new_intent,
        "refund_amount": amount_refunded_major,
        "currency": currency,
        "event_id": event_id,
    }


async def handle_charge_dispute_created(event: dict) -> dict:
    """Webhook handler: a customer opened a dispute on a commerce charge.

    Marks the order payment_intent="disputed" and fires a critical alert
    (emit_charge_disputed) so admins learn about it immediately. Disputes
    have a hard Stripe deadline (typically 7 days) to submit evidence.
    Idempotent per event_id.
    """
    dispute = event["data"]["object"]
    event_id = event.get("id", "unknown")
    pi = dispute.get("payment_intent")
    reason = dispute.get("reason")
    amount = dispute.get("amount") or 0
    from services.currency_service import DEFAULT_CURRENCY
    currency = (dispute.get("currency") or DEFAULT_CURRENCY).upper()

    order = await _find_order_by_payment_intent(pi)
    if not order:
        logger.info(
            "charge.dispute.created: no matching order for payment_intent=%s event=%s",
            pi, event_id,
        )
        return {"status": "ignored", "reason": "no_matching_order", "event_id": event_id}

    order_id = order["id"]
    org_id = order["organization_id"]

    # Idempotency
    processed_events = (order.get("payment_checkout") or {}).get("processed_events") or []
    if event_id in processed_events:
        return {"status": "skipped", "reason": "event_already_processed", "order_id": order_id}

    from database import orders_collection
    from models.common import utc_now
    now = utc_now()
    amount_major = amount / 100.0

    await orders_collection.update_one(
        {"id": order_id, "organization_id": org_id},
        {"$set": {
            "payment_intent": "disputed",
            "payment_checkout.dispute_opened_at": now.isoformat(),
            "payment_checkout.dispute_reason": reason,
            "payment_checkout.dispute_amount": amount_major,
            "payment_checkout.dispute_currency": currency,
            "updated_at": now,
        },
        "$push": {"payment_checkout.processed_events": event_id}},
    )

    logger.warning(
        "charge.dispute.created: order %s disputed (reason=%s amount=%s %s)",
        order_id, reason, amount_major, currency,
    )

    # Fire critical alert (best-effort; never raises)
    try:
        # Best-effort customer email pull for the notification
        _customer_email = None
        try:
            from database import customers_collection
            _cust = await customers_collection.find_one(
                {"id": order.get("customer_id"), "organization_id": org_id},
                {"_id": 0, "email": 1},
            )
            if _cust:
                _customer_email = _cust.get("email")
        except Exception:
            pass

        from services.critical_alert_service import emit_charge_disputed
        await emit_charge_disputed(
            org_id=org_id,
            order_id=order_id,
            order_number=order.get("order_number"),
            event_id=event_id,
            dispute_reason=reason,
            dispute_amount=amount_major,
            currency=currency,
            stripe_payment_intent_id=pi,
            customer_email=_customer_email,
        )
    except Exception as alert_err:
        logger.error(
            "charge.dispute.created: alert dispatch failed for order %s: %s",
            order_id, alert_err,
        )

    return {
        "action": "dispute_recorded",
        "order_id": order_id,
        "org_id": org_id,
        "reason": reason,
        "amount": amount_major,
        "currency": currency,
        "event_id": event_id,
    }
