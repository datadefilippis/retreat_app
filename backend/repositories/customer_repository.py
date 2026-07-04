"""
Customer repository.

Follows the same async Motor pattern used by all existing repositories.
"""
from typing import Optional, List, Tuple
from datetime import datetime, timezone

from database import customers_collection
from models.common import generate_id, utc_now as _utc_now
from models.customer import Customer, CustomerCreate


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _normalise_email(email: Optional[str]) -> Optional[str]:
    """Single source of truth for email normalisation in this repo.

    Storefront checkout (public.py) historically called `.strip().lower()`
    inline; POS order creation (orders.py) did the same. Both now route
    through this function so a future tweak (e.g. unicode NFKC, Gmail's
    "+suffix" canonicalisation, IDN handling) lands in one place.

    Returns None when input is None/empty so the partial unique index
    (`partialFilterExpression: {email: {$type: "string"}}`) correctly
    bypasses null-email customers — POS sales without an email are
    allowed to coexist without colliding on the uniqueness constraint.
    """
    if not email:
        return None
    cleaned = email.strip().lower()
    return cleaned or None


async def create(organization_id: str, data: CustomerCreate) -> Customer:
    customer = Customer(organization_id=organization_id, **data.model_dump())
    doc = customer.model_dump()
    # Phase 4 — normalise email at the repo boundary so admin-created
    # customers (CRM panel via POST /customers) end up byte-equal to
    # storefront-created ones. Without this, a customer email entered
    # as "Alice@Foo.COM" in admin and "alice@foo.com" by the storefront
    # would create two rows that the new unique index (org_id, email)
    # can't catch — the index only compares bytes.
    doc["email"] = _normalise_email(doc.get("email"))
    doc["created_at"] = doc["created_at"].isoformat()
    doc["updated_at"] = doc["updated_at"].isoformat()
    await customers_collection.insert_one(doc)
    return customer


async def upsert_by_email(
    organization_id: str,
    *,
    name: str,
    email: str,
    phone: Optional[str] = None,
    customer_account_id: Optional[str] = None,
    source: str = "storefront",
) -> Tuple[str, bool]:
    """Atomically find-or-create a customer keyed by (org_id, email).

    Returns: (customer_id, was_created)
      `was_created` is True when this call inserted a new row,
      False when an existing customer was found (and possibly updated).

    Race-safety
    -----------
    Pre-Phase-4 the storefront and POS code paths both did:

        existing = find_one({org_id, email})
        if existing: return existing.id
        insert_one(new_doc)

    Two concurrent storefront orders from the same email could each
    observe `existing=None` and both insert — producing duplicate
    customer rows in the same org. The new unique index on
    (organization_id, email) would now reject the second insert with
    DuplicateKey, but the application code would still bubble a 500.

    This helper uses `find_one_and_update(upsert=True)` which Mongo
    guarantees is atomic at the document level:
      · If a doc matches the filter → it's updated in place.
      · If no doc matches → a new doc is inserted using `$setOnInsert`.
    Two concurrent calls deterministically converge on a single row.

    Update semantics for existing customers (preserved from pre-Phase-4
    behaviour in routers/public._find_or_create_customer):
      · `name` always overwritten (latest visitor name wins)
      · `phone` set only if currently null (we don't clobber explicit data)
      · `customer_account_id` linked only if currently null
      · `updated_at` bumped

    For NEW customers (the $setOnInsert branch):
      · `id` generated fresh
      · `is_active=True`, `tags=[]`, `metadata={source: <source>}`
      · `created_at` set
    """
    normalised = _normalise_email(email)
    if not normalised:
        # Caller must ensure email is non-empty — this helper is keyed
        # on email by definition.
        raise ValueError("upsert_by_email requires a non-empty email")

    now = _utc_now()

    # Pre-generate the candidate id. If the upsert inserts a new doc,
    # this id ends up in the result. If it matches an existing doc,
    # the existing id is preserved and our candidate is discarded.
    # We then compare returned id to candidate to detect insert vs
    # update — more reliable than timestamp comparison (no race on
    # clock granularity, no FP-equality concerns).
    candidate_id = generate_id()

    # $set runs on BOTH insert and update. We intentionally set ONLY
    # `name` and `updated_at` here — fields the caller explicitly wants
    # to refresh on every storefront/POS encounter (latest typed name
    # wins).
    set_fields = {
        "name": name,
        "updated_at": now,
    }

    # $setOnInsert runs only when no match — establishes a brand-new doc.
    # Includes ALL system fields so a fresh row passes validation.
    set_on_insert = {
        "id": candidate_id,
        "organization_id": organization_id,
        "email": normalised,
        "is_active": True,
        "tags": [],
        "metadata": {"source": source},
        "created_at": now,
        "phone": phone,
        "customer_account_id": customer_account_id,
    }

    # The atomic core: match-or-insert in a single round-trip.
    # ReturnDocument.AFTER gives back the post-write doc so we can read
    # the canonical `id` (either the existing one or our candidate).
    from pymongo import ReturnDocument

    result = await customers_collection.find_one_and_update(
        {"organization_id": organization_id, "email": normalised},
        {"$set": set_fields, "$setOnInsert": set_on_insert},
        upsert=True,
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0, "id": 1, "customer_account_id": 1, "phone": 1},
    )

    # Reliable insert-vs-update detection: if Mongo inserted our doc,
    # the returned id is our candidate_id. If it matched an existing
    # doc, the returned id is whatever was already there. No clock or
    # timestamp comparison needed.
    was_created = result["id"] == candidate_id

    # Post-upsert: if we matched an existing customer and the caller
    # provided a customer_account_id they didn't have, attach it. This
    # is the only operation that can't fit in the single
    # find_one_and_update call because $setOnInsert is one-shot.
    #
    # Phone is intentionally NOT updated on existing rows — the
    # storefront name field gets overwritten (visitors expect their
    # latest typed name in confirmation emails) but phone is treated
    # as a stable contact preference. Admin can change phone explicitly
    # via PATCH /customers/{id}.
    if not was_created:
        if customer_account_id and not result.get("customer_account_id"):
            await customers_collection.update_one(
                {"id": result["id"], "organization_id": organization_id},
                {"$set": {
                    "customer_account_id": customer_account_id,
                    "updated_at": _utc_now(),
                }},
            )

    return result["id"], was_created


async def find_by_id(customer_id: str, organization_id: str) -> Optional[Customer]:
    doc = await customers_collection.find_one(
        {"id": customer_id, "organization_id": organization_id}
    )
    if not doc:
        return None
    return Customer(**doc)


async def find_by_org(
    organization_id: str,
    active_only: bool = True,
    limit: int = 200,
) -> List[Customer]:
    query: dict = {"organization_id": organization_id}
    if active_only:
        query["is_active"] = True
    cursor = customers_collection.find(query).sort("name", 1).limit(limit)
    return [Customer(**doc) async for doc in cursor]


async def update(
    customer_id: str,
    organization_id: str,
    updates: dict,
) -> Optional[Customer]:
    updates["updated_at"] = _now().isoformat()
    result = await customers_collection.update_one(
        {"id": customer_id, "organization_id": organization_id},
        {"$set": updates},
    )
    if result.matched_count == 0:
        return None
    return await find_by_id(customer_id, organization_id)


async def deactivate(customer_id: str, organization_id: str) -> bool:
    result = await customers_collection.update_one(
        {"id": customer_id, "organization_id": organization_id},
        {"$set": {"is_active": False, "updated_at": _now().isoformat()}},
    )
    return result.modified_count > 0
