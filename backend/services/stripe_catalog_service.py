"""
stripe_catalog_service.py
==========================
Onda 10 Step C.4 — Server-side Stripe Product + Price auto-creation.

When the system_admin creates a new commercial plan or addon via
POST /admin/catalog/plans or /admin/catalog/addons, this service can
optionally provision the matching Stripe entities in the same flow:
  · stripe.Product.create(name, description, metadata)
  · stripe.Price.create(product, unit_amount, currency, recurring)
    × monthly always
    × yearly if price_yearly is provided

Failure mode (default): NON-FATAL.
  If Stripe is unreachable, returns None for the IDs and logs a
  warning. The caller (catalog_repository.create_*) persists the
  plan/addon WITHOUT Stripe IDs — admin can complete the linkage
  later via PATCH /admin/catalog/plans/{slug}/pricing or by re-running
  this service against the orphan plan.

Idempotency:
  Each request uses a deterministic idempotency_key derived from the
  catalog slug + a fixed prefix, so retries don't create duplicate
  Stripe entities. If the operator re-runs against the same slug,
  Stripe returns the originally-created Product and Prices.

This service is INDEPENDENT from the existing services/stripe_service.py
to avoid coupling the lean catalog flow to the heavier subscription/
checkout machinery. Both share the same `stripe` Python SDK module.

Public API:
  · async ensure_stripe_for_plan(plan_doc) → dict | None
  · async ensure_stripe_for_addon(addon_doc) → dict | None

Both return:
  {
    "stripe_product_id": str,
    "stripe_price_id_monthly": str,
    "stripe_price_id_yearly": str | None,
  }
or None if Stripe is not configured / unreachable.
"""

import logging
import os
from typing import Any, Optional, Dict

logger = logging.getLogger(__name__)

# Idempotency key prefix — collisions across deployments would be
# unfortunate but harmless (Stripe enforces a 24h TTL on idempotency
# keys, then they're recycled).
_IDEMPOTENCY_PREFIX = "afianco_catalog_v1"


def _get_stripe():
    """Lazy-import + configure. Returns None if SDK or key missing."""
    try:
        import stripe
    except ImportError:
        logger.error("stripe package not installed — pip install stripe")
        return None
    api_key = os.environ.get("STRIPE_SECRET_KEY", "").strip()
    if not api_key:
        logger.warning("STRIPE_SECRET_KEY not set — skipping Stripe catalog provisioning")
        return None
    stripe.api_key = api_key
    stripe.api_version = "2024-06-20"
    return stripe


def _is_test_key() -> bool:
    """Return True iff the active key is a Stripe TEST key (sk_test_...)."""
    return os.environ.get("STRIPE_SECRET_KEY", "").startswith("sk_test")


def _euros_to_cents(amount: float) -> int:
    """Stripe expects integer minor units. €19.00 → 1900."""
    return int(round(float(amount) * 100))


async def _create_product_and_prices(
    *,
    slug: str,
    name: str,
    description: str,
    price_monthly: float,
    price_yearly: Optional[float],
    currency: str,
    is_addon: bool,
) -> Optional[Dict[str, Optional[str]]]:
    """Create Stripe Product + Price(s). Returns None on any error.

    Caller is responsible for persisting the returned IDs into the
    CommercialPlan doc (typically by passing them to
    `create_commercial_plan` / `create_addon`).
    """
    stripe = _get_stripe()
    if stripe is None:
        return None

    # Idempotency keys (deterministic by slug)
    product_idem = f"{_IDEMPOTENCY_PREFIX}:product:{slug}"
    price_m_idem = f"{_IDEMPOTENCY_PREFIX}:price_m:{slug}"
    price_y_idem = f"{_IDEMPOTENCY_PREFIX}:price_y:{slug}"

    metadata = {
        "afianco_slug": slug,
        "afianco_kind": "addon" if is_addon else "plan",
        "afianco_env": "test" if _is_test_key() else "live",
    }

    try:
        product = stripe.Product.create(
            name=name,
            description=description or None,
            metadata=metadata,
            idempotency_key=product_idem,
        )
        product_id = product.get("id") if hasattr(product, "get") else product.id
    except Exception as e:
        logger.warning("stripe_catalog: Product.create failed for slug=%r: %s", slug, e)
        return None

    # Monthly price (always)
    try:
        price_m = stripe.Price.create(
            product=product_id,
            unit_amount=_euros_to_cents(price_monthly),
            currency=(currency or "eur").lower(),
            recurring={"interval": "month"},
            metadata=metadata,
            idempotency_key=price_m_idem,
        )
        price_m_id = price_m.get("id") if hasattr(price_m, "get") else price_m.id
    except Exception as e:
        logger.warning(
            "stripe_catalog: Price.create monthly failed for slug=%r product=%s: %s",
            slug, product_id, e,
        )
        # Product was created. Return the product ID even without prices
        # so the admin can manually create prices later via dashboard.
        return {
            "stripe_product_id": product_id,
            "stripe_price_id_monthly": None,
            "stripe_price_id_yearly": None,
        }

    # Yearly price (optional)
    price_y_id: Optional[str] = None
    if price_yearly is not None and price_yearly > 0:
        try:
            price_y = stripe.Price.create(
                product=product_id,
                unit_amount=_euros_to_cents(price_yearly),
                currency=(currency or "eur").lower(),
                recurring={"interval": "year"},
                metadata=metadata,
                idempotency_key=price_y_idem,
            )
            price_y_id = price_y.get("id") if hasattr(price_y, "get") else price_y.id
        except Exception as e:
            logger.warning(
                "stripe_catalog: Price.create yearly failed for slug=%r: %s",
                slug, e,
            )

    return {
        "stripe_product_id": product_id,
        "stripe_price_id_monthly": price_m_id,
        "stripe_price_id_yearly": price_y_id,
    }


async def ensure_stripe_for_plan(plan_doc: dict) -> Optional[Dict[str, Optional[str]]]:
    """Provision Stripe Product+Prices for a newly-created plan.

    Idempotent (Stripe-side via idempotency_key). Safe to retry.

    Args:
        plan_doc: a CommercialPlan dict (with at minimum `slug`, `name`,
                  `price_monthly`, optional `price_yearly`, `currency`).

    Returns:
        Dict with stripe_product_id, stripe_price_id_monthly,
        stripe_price_id_yearly — or None if Stripe is not configured /
        unreachable. Caller logs/handles None as a non-fatal warning.
    """
    return await _create_product_and_prices(
        slug=plan_doc["slug"],
        name=plan_doc.get("name", plan_doc["slug"]),
        description=plan_doc.get("description") or plan_doc.get("tagline") or "",
        price_monthly=plan_doc.get("price_monthly", 0),
        price_yearly=plan_doc.get("price_yearly"),
        currency=plan_doc.get("currency", "eur"),
        is_addon=False,
    )


async def validate_stripe_product(stripe_product_id: Optional[str]) -> Dict[str, Any]:
    """Onda 11 Step 2 — fetch Stripe Product details for drift surfacing.

    Read-only Stripe call. Never mutates DB or Stripe state.

    Args:
        stripe_product_id: the Product ID stored on the plan
                           (CommercialPlan.stripe_product_id), or None.

    Returns a dict shaped:
      {
        "configured": bool,                # True iff stripe_product_id set
        "exists": bool | None,             # True/False/None (None=unconfigured)
        "active": bool | None,             # Stripe Product.active flag
        "name": str | None,                # Stripe Product.name
        "metadata_afianco_slug": str|None, # metadata.afianco_slug if present
        "metadata_afianco_kind": str|None, # "plan" | "addon" | None
        "metadata_afianco_env": str|None,  # "test" | "live" | None
        "error": str | None,               # transport / API error message
      }

    Designed to drive the system_admin "Stripe linking" UI (Onda 11
    Step 3) — the admin sees at-a-glance whether the linked Product
    actually exists in their Stripe account, whether it's still
    active, and whether its `afianco_slug` metadata still matches the
    plan slug (catches "wrong Product linked" mistakes).
    """
    out: Dict[str, Any] = {
        "configured": False,
        "exists": None,
        "active": None,
        "name": None,
        "metadata_afianco_slug": None,
        "metadata_afianco_kind": None,
        "metadata_afianco_env": None,
        "error": None,
    }
    if not stripe_product_id:
        return out
    out["configured"] = True

    stripe = _get_stripe()
    if stripe is None:
        out["error"] = "stripe_not_configured"
        return out

    try:
        product = stripe.Product.retrieve(stripe_product_id)
    except Exception as e:
        msg = f"{type(e).__name__}: {str(e)[:200]}"
        # Stripe SDK raises InvalidRequestError("No such product: prod_...")
        # for missing/wrong IDs. Other exceptions = transport/network.
        if "No such product" in str(e) or "resource_missing" in str(e):
            out["exists"] = False
            out["error"] = "stripe_product_not_found"
        else:
            out["error"] = msg
        return out

    getter = product.get if hasattr(product, "get") else (
        lambda k: getattr(product, k, None)
    )
    metadata = getter("metadata") or {}
    if not isinstance(metadata, dict):
        # Stripe StripeObject acts dict-like — coerce.
        try:
            metadata = dict(metadata)
        except Exception:
            metadata = {}

    out["exists"] = True
    out["active"] = bool(getter("active"))
    out["name"] = getter("name")
    out["metadata_afianco_slug"] = metadata.get("afianco_slug")
    out["metadata_afianco_kind"] = metadata.get("afianco_kind")
    out["metadata_afianco_env"] = metadata.get("afianco_env")
    return out


async def validate_stripe_pricing(plan_doc: dict) -> Dict[str, Optional[str]]:
    """Compare DB-side pricing vs LIVE Stripe Price.

    Onda 10 Step D.3 — drift detection between catalog DB and Stripe.

    Reads:
      · plan_doc.stripe_price_id_monthly
      · plan_doc.stripe_price_id_yearly  (optional)
      · plan_doc.price_monthly + price_yearly + currency

    Returns a dict with:
      {
        "configured": bool,         # at least one Stripe ID is set
        "monthly": {
            "db_price": float, "stripe_unit_amount": int|None,
            "stripe_currency": str|None, "stripe_recurring_interval": str|None,
            "stripe_active": bool|None, "drift": bool, "reason": str|None,
        } | None,
        "yearly": {...} | None,
        "errors": [str, ...]    # transport / API errors
      }

    Read-only — never mutates anything in DB or in Stripe.
    """
    out: Dict[str, Optional[str]] = {
        "configured": False,
        "monthly": None,
        "yearly": None,
        "errors": [],
    }

    stripe = _get_stripe()
    if stripe is None:
        out["errors"] = ["stripe_not_configured"]
        return out

    db_price_m = plan_doc.get("price_monthly")
    db_price_y = plan_doc.get("price_yearly")
    db_currency = (plan_doc.get("currency") or "EUR").upper()
    sp_monthly = plan_doc.get("stripe_price_id_monthly")
    sp_yearly = plan_doc.get("stripe_price_id_yearly")

    if not sp_monthly and not sp_yearly:
        return out  # configured stays False

    out["configured"] = True

    def _compare(stripe_price, expected_db_price: Optional[float], expected_interval: str):
        """Compare a Stripe Price object to expected DB value."""
        if stripe_price is None:
            return {
                "db_price": expected_db_price,
                "stripe_unit_amount": None,
                "stripe_currency": None,
                "stripe_recurring_interval": None,
                "stripe_active": None,
                "drift": True,
                "reason": "stripe_price_not_found",
            }
        # Stripe object accessor
        getter = stripe_price.get if hasattr(stripe_price, "get") else lambda k: getattr(stripe_price, k, None)
        unit_amount = getter("unit_amount")  # cents
        currency = (getter("currency") or "").upper()
        recurring = getter("recurring") or {}
        interval = recurring.get("interval") if hasattr(recurring, "get") else getattr(recurring, "interval", None)
        active = bool(getter("active"))

        result = {
            "db_price": expected_db_price,
            "stripe_unit_amount": unit_amount,
            "stripe_currency": currency,
            "stripe_recurring_interval": interval,
            "stripe_active": active,
            "drift": False,
            "reason": None,
        }
        if not active:
            result["drift"] = True
            result["reason"] = "stripe_price_inactive"
            return result
        if expected_db_price is None:
            result["drift"] = True
            result["reason"] = "db_price_missing"
            return result
        expected_cents = _euros_to_cents(expected_db_price)
        if unit_amount != expected_cents:
            result["drift"] = True
            result["reason"] = (
                f"price_mismatch: db={expected_db_price} ({expected_cents} cents) "
                f"vs stripe={unit_amount} cents"
            )
            return result
        if currency != db_currency:
            result["drift"] = True
            result["reason"] = f"currency_mismatch: db={db_currency} vs stripe={currency}"
            return result
        if interval != expected_interval:
            result["drift"] = True
            result["reason"] = f"interval_mismatch: expected={expected_interval} vs stripe={interval}"
        return result

    if sp_monthly:
        try:
            sp = stripe.Price.retrieve(sp_monthly)
            out["monthly"] = _compare(sp, db_price_m, "month")
        except Exception as e:
            out["errors"].append(f"monthly_retrieve: {type(e).__name__}: {str(e)[:200]}")
            out["monthly"] = {
                "db_price": db_price_m, "stripe_unit_amount": None,
                "stripe_currency": None, "stripe_recurring_interval": None,
                "stripe_active": None, "drift": True, "reason": "stripe_api_error",
            }

    if sp_yearly:
        try:
            sp = stripe.Price.retrieve(sp_yearly)
            out["yearly"] = _compare(sp, db_price_y, "year")
        except Exception as e:
            out["errors"].append(f"yearly_retrieve: {type(e).__name__}: {str(e)[:200]}")
            out["yearly"] = {
                "db_price": db_price_y, "stripe_unit_amount": None,
                "stripe_currency": None, "stripe_recurring_interval": None,
                "stripe_active": None, "drift": True, "reason": "stripe_api_error",
            }

    return out


async def ensure_stripe_for_addon(addon_doc: dict) -> Optional[Dict[str, Optional[str]]]:
    """Provision Stripe Product+Price for a newly-created addon.

    Addons are monthly-only by current platform design (no yearly).
    Yearly is silently ignored even if price_yearly is set on the doc.
    """
    return await _create_product_and_prices(
        slug=addon_doc["slug"],
        name=addon_doc.get("name", addon_doc["slug"]),
        description=addon_doc.get("description") or "",
        price_monthly=addon_doc.get("price_monthly", 0),
        price_yearly=None,  # addons monthly-only by design
        currency=addon_doc.get("currency", "eur"),
        is_addon=True,
    )
