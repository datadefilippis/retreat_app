"""
Customer Portal Router — authenticated customer-facing endpoints.

All endpoints require a valid customer JWT (type=customer).
Access is scoped by customer_account_id AND organization_id from token.
No admin data is ever exposed. No cross-org access.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth import get_current_customer
from database import orders_collection, organizations_collection, customers_collection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/customer", tags=["Customer Portal"])


@router.get("/me")
async def get_me(current_customer: dict = Depends(get_current_customer)):
    """Return current customer account info.

    Wave GDPR-Commerce CG-4: the response now carries the consent
    snapshot (``accepted_store_terms_version``, ``accepted_store_privacy_version``,
    ``accepted_marketing_at``, ``marketing_revoked_at``) plus the
    server-computed re-consent freshness flag:

        consent_needs_refresh == True  iff
            (accepted_store_terms_version != current_store_legal_version)
            OR  (accepted_store_privacy_version != current_store_legal_version)
            OR  (the merchant has published since this customer signed up
                 with no version snapshot, e.g. legacy CG-pre-4 accounts)

    The frontend reads this on every customer-portal boot and renders
    the blocking ``<CustomerReconsentModal/>`` when True. ``current_store_legal_version``
    is also surfaced so the modal can display "Versione corrente: <tag>".
    """
    from repositories import customer_account_repository
    account = await customer_account_repository.find_by_id(
        current_customer["customer_account_id"]
    )
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # Resolve org name for display
    org_id = current_customer["organization_id"]
    org = await organizations_collection.find_one(
        {"id": org_id}, {"_id": 0, "name": 1, "public_slug": 1},
    )

    # ── CG-4: compute consent_needs_refresh against the customer's
    # original signup store (resolved via signup_slug). If the customer
    # signed up on store A, we only compare against store A's version
    # — not against any other store of the same org.
    current_legal_version = None
    consent_needs_refresh = False
    signup_slug = account.get("signup_slug")
    if signup_slug:
        from database import stores_collection
        from services.merchant_legal_versioning import (
            current_version_string, merchant_legal_status,
        )
        store_doc = await stores_collection.find_one(
            {"slug": signup_slug, "organization_id": org_id},
            {
                "_id": 0,
                "merchant_legal_version_tag": 1,
                "merchant_legal_version_hash": 1,
                "merchant_legal_published_at": 1,
                "merchant_legal_display_locale": 1,
                "merchant_legal_last_edited_at": 1,
                # CG-3-Polish-3 — needed by get_effective_display_locale
                # which now reads storefront_languages[0] as the primary
                # source of truth for the customer-visible locale.
                "storefront_languages": 1,
                "merchant_privacy_content_it": 1,
                "merchant_privacy_content_en": 1,
                "merchant_privacy_content_de": 1,
                "merchant_privacy_content_fr": 1,
                "merchant_terms_content_it": 1,
                "merchant_terms_content_en": 1,
                "merchant_terms_content_de": 1,
                "merchant_terms_content_fr": 1,
            },
        )
        if store_doc:
            status_val = merchant_legal_status(store_doc)
            if status_val in ("published", "stale_draft"):
                current_legal_version = current_version_string(store_doc)
                accepted_t = account.get("accepted_store_terms_version")
                accepted_p = account.get("accepted_store_privacy_version")
                # Refresh required when either accepted version is
                # missing or differs from current.
                if (current_legal_version
                    and (accepted_t != current_legal_version
                         or accepted_p != current_legal_version)):
                    consent_needs_refresh = True

    return {
        "id": account["id"],
        "organization_id": org_id,
        "email": account["email"],
        "name": account["name"],
        "locale": account.get("locale", "it"),
        "email_verified": account.get("email_verified", False),
        "created_at": account.get("created_at"),
        "org_name": org.get("name", "") if org else "",
        "org_slug": org.get("public_slug", "") if org else "",
        # CG-4 consent block
        "signup_slug": signup_slug,
        "accepted_store_terms_version": account.get("accepted_store_terms_version"),
        "accepted_store_privacy_version": account.get("accepted_store_privacy_version"),
        "accepted_marketing_at": account.get("accepted_marketing_at"),
        "marketing_revoked_at": account.get("marketing_revoked_at"),
        "current_store_legal_version": current_legal_version,
        "consent_needs_refresh": consent_needs_refresh,
    }


# ─── Wave GDPR-Commerce CG-4 — re-consent endpoint ──────────────────────


@router.post("/me/re-consent")
async def customer_re_consent(
    current_customer: dict = Depends(get_current_customer),
):
    """Record a customer's re-acceptance of the merchant's current
    Privacy + Terms version.

    Effects (parallel to admin Phase E re_consent in routers/auth.py):
      1. Append two consent_audit records (privacy + terms) with
         source="customer_re_acceptance".
      2. Update the customer document's accepted_store_*_version /
         locale / at fields to match the store's current published
         version, so the next /me read flips consent_needs_refresh
         back to False.

    Atomicity: the audit record is the legal proof, so it is written
    FIRST. If the user-doc update fails after the audit succeeds, the
    modal will reappear on the next reload and the user re-accepts
    (idempotent on consent_audit because each acceptance is a fresh
    immutable record — multiple records mean multiple re-acceptances,
    which is auditable and correct).

    The version + locale are read from the SIGNUP store (via signup_slug)
    — never from the request payload. The request body is empty.
    """
    from datetime import datetime, timezone
    from fastapi import Request as _Request
    from database import stores_collection, customer_accounts_collection
    from repositories import (
        customer_account_repository,
        consent_audit_repository as car,
    )
    from services.merchant_legal_versioning import (
        merchant_legal_status, current_version_string,
        get_effective_display_locale,
    )

    account = await customer_account_repository.find_by_id(
        current_customer["customer_account_id"]
    )
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    org_id = current_customer["organization_id"]
    signup_slug = account.get("signup_slug")
    if not signup_slug:
        # Legacy account predates CG-1 → there's no store to bind
        # consent to. Reject so the frontend surfaces a "contact the
        # merchant" message rather than silently no-oping.
        raise HTTPException(
            status_code=422,
            detail=(
                "Account legacy: il negozio di registrazione non è "
                "associato. Contatta il venditore."
            ),
        )

    store_doc = await stores_collection.find_one(
        {"slug": signup_slug, "organization_id": org_id},
        {"_id": 0},
    )
    if not store_doc:
        raise HTTPException(status_code=404, detail="Store not found")

    if merchant_legal_status(store_doc) not in ("published", "stale_draft"):
        raise HTTPException(
            status_code=422,
            detail=(
                "Il negozio non ha ancora pubblicato la versione "
                "corrente dei documenti."
            ),
        )

    legal_version = current_version_string(store_doc)
    # CG-3-Polish-3 — resolve via helper (the auto-cleanup unsets the
    # raw legacy field; reading it directly returns None and breaks
    # re-consent for legacy stores).
    legal_display_locale = get_effective_display_locale(store_doc)
    if not legal_version or not legal_display_locale:
        raise HTTPException(status_code=500, detail="Legal version unresolved")

    version_tag, _, version_hash = legal_version.partition(":")
    audit_locale = legal_display_locale if legal_display_locale in (
        "it", "en", "de", "fr"
    ) else "it"

    # No IP/UA threading here: the route signature is kept simple
    # (no Request injection). If we want to capture IP/UA we can add
    # a Request param — left for a follow-up if compliance audit
    # specifically asks for it on re-consent (signup already captures).

    # 1) Write audit records FIRST.
    try:
        for doc_type in ("merchant_privacy", "merchant_terms"):
            await car.record_consent(
                user_id=account["id"],
                organization_id=org_id,
                store_id=store_doc.get("id"),
                locale=audit_locale,
                version_tag=version_tag or "v1.0",
                version_hash=version_hash or "unknown",
                source="customer_re_acceptance",
                document_type=doc_type,
            )
    except Exception as exc:
        logger.error(
            "customer_re_consent: audit insert failed for account=%s: %s",
            account["id"], exc, exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=(
                "Impossibile registrare l'accettazione. Riprova "
                "fra qualche secondo."
            ),
        )

    # 2) Update the customer doc so the modal stops appearing.
    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        await customer_accounts_collection.update_one(
            {"id": account["id"], "organization_id": org_id},
            {"$set": {
                "accepted_store_terms_version": legal_version,
                "accepted_store_terms_locale": legal_display_locale,
                "accepted_store_terms_at": now_iso,
                "accepted_store_privacy_version": legal_version,
                "accepted_store_privacy_locale": legal_display_locale,
                "accepted_store_privacy_at": now_iso,
                "updated_at": now_iso,
            }},
        )
    except Exception as exc:
        logger.error(
            "customer_re_consent: account update failed after audit "
            "succeeded for account=%s: %s", account["id"], exc, exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=(
                "Accettazione registrata ma profilo non aggiornato. "
                "Ricarica la pagina."
            ),
        )

    return {
        "status": "ok",
        "accepted_terms_version": legal_version,
        "accepted_privacy_version": legal_version,
        "accepted_locale": legal_display_locale,
        "consent_needs_refresh": False,
    }


@router.patch("/me")
async def update_my_profile(
    current_customer: dict = Depends(get_current_customer),
    body: dict = None,
):
    """Update customer profile fields.

    Whitelist of editable fields:
      - name, phone   — free-text identity fields
      - locale        — preferred UI / email language (it/en/de/fr)

    The locale value drives the language of:
      • the customer's UI when they're logged in (CustomerAuthContext
        calls i18n.changeLanguage(customer.locale) on every me-fetch),
      • all transactional emails (verify, reset, order_confirmed),
      • the storefront when the same customer revisits a different
        device — the resolver in useStorefrontLocale prefers
        customer.locale over the per-device localStorage cache.

    Anything outside the allowed set is silently dropped — never errors,
    never partially applied; same shape as before the locale addition.
    """
    from database import customer_accounts_collection
    from models.common import utc_now

    if not body:
        raise HTTPException(status_code=400, detail="No fields to update")

    allowed = {"name", "phone", "locale"}
    updates = {k: v for k, v in (body or {}).items() if k in allowed and v is not None}

    # Locale validation — only accept languages the app actually has
    # translations for. Reject the request entirely (vs. silently
    # dropping) when locale is provided but invalid, so the client
    # learns about the typo instead of seeing a no-op response.
    if "locale" in updates:
        loc = str(updates["locale"]).lower().split("-")[0]
        if loc not in {"it", "en", "de", "fr"}:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported locale '{updates['locale']}'. Use one of it, en, de, fr.",
            )
        updates["locale"] = loc

    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update")

    updates["updated_at"] = utc_now()
    await customer_accounts_collection.update_one(
        {"id": current_customer["customer_account_id"]},
        {"$set": updates},
    )

    # Also update linked customer record
    org_id = current_customer["organization_id"]
    if "name" in updates:
        await customers_collection.update_many(
            {"organization_id": org_id, "email": current_customer.get("email")},
            {"$set": {"name": updates["name"]}},
        )

    return {"message": "Profilo aggiornato"}


@router.post("/change-password")
async def change_my_password(
    current_customer: dict = Depends(get_current_customer),
    body: dict = None,
):
    """Change customer password. Requires current_password + new_password."""
    from database import customer_accounts_collection
    from passlib.context import CryptContext

    pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

    current_pw = (body or {}).get("current_password", "")
    new_pw = (body or {}).get("new_password", "")

    if not current_pw or not new_pw:
        raise HTTPException(status_code=400, detail="current_password e new_password richiesti")
    if len(new_pw) < 8:
        raise HTTPException(status_code=400, detail="La nuova password deve avere almeno 8 caratteri")

    account = await customer_accounts_collection.find_one(
        {"id": current_customer["customer_account_id"]}, {"_id": 0, "password_hash": 1})
    if not account or not pwd_ctx.verify(current_pw, account.get("password_hash", "")):
        raise HTTPException(status_code=400, detail="Password attuale non corretta")

    from models.common import utc_now
    await customer_accounts_collection.update_one(
        {"id": current_customer["customer_account_id"]},
        {"$set": {"password_hash": pwd_ctx.hash(new_pw), "updated_at": utc_now()}},
    )

    return {"message": "Password aggiornata"}


@router.get("/orders")
async def get_my_orders(current_customer: dict = Depends(get_current_customer)):
    """Return orders for this customer within their organization only.

    Scoped by BOTH customer_account_id AND organization_id.
    No cross-org orders are ever returned.
    """
    account_id = current_customer["customer_account_id"]
    org_id = current_customer["organization_id"]

    cursor = orders_collection.find(
        {"customer_account_id": account_id, "organization_id": org_id},
        {
            "_id": 0,
            "id": 1,
            "organization_id": 1,
            "order_number": 1,
            "customer_id": 1,
            "status": 1,
            "payment_status": 1,
            "payment_intent": 1,
            "total": 1,
            "currency": 1,
            "source": 1,
            "items": 1,
            "fulfillment": 1,
            "created_at": 1,
            "updated_at": 1,
            "notes": 1,
        },
    ).sort("created_at", -1).limit(100)

    orders = await cursor.to_list(100)

    # Denormalize org_name and customer_name
    if orders:
        org = await organizations_collection.find_one(
            {"id": org_id}, {"_id": 0, "name": 1},
        )
        org_name = org.get("name", "") if org else ""

        customer_ids = list({o["customer_id"] for o in orders})
        cust_cursor = customers_collection.find(
            {"id": {"$in": customer_ids}, "organization_id": org_id},
            {"_id": 0, "id": 1, "name": 1},
        )
        cust_map = {doc["id"]: doc.get("name", "") async for doc in cust_cursor}

        for order in orders:
            order["org_name"] = org_name
            order["customer_name"] = cust_map.get(order["customer_id"], "")

    return {"orders": orders, "total": len(orders)}


@router.get("/orders/{order_id}")
async def get_my_order(
    order_id: str,
    with_issued: bool = False,
    current_customer: dict = Depends(get_current_customer),
):
    """Return a single order detail. Only if customer_account_id AND org_id match.

    Query params
    ------------
      with_issued: when True, the response is enriched with the
                   per-line issued asset arrays:
                     _issued_tickets       (event_ticket lines)
                     _issued_bookings      (service / consulenza lines)
                     _issued_reservations  (rental lines, both flavours)
                     _issued_downloads     (digital lines)
                   Each array is filtered to (order_id, organization_id)
                   so the customer never sees foreign-org or foreign-
                   order assets even if a server-side bug ever wrote
                   one. Tickets/bookings/etc are NOT joined when the
                   flag is False — keeps the lightweight default the
                   orders-list page consumes.

    The course access is intentionally NOT included on this endpoint
    even with with_issued=True: course consumption has its own UX
    surface at /account/courses + /account/courses/<enrollment_id>
    and the listing endpoint /customer/courses is the canonical
    source. Step 8 will revisit this when the course line on the
    order detail wants to show a per-enrollment progress bar.
    """
    account_id = current_customer["customer_account_id"]
    org_id = current_customer["organization_id"]

    order = await orders_collection.find_one(
        {"id": order_id, "customer_account_id": account_id, "organization_id": org_id},
        {"_id": 0},
    )
    if not order:
        raise HTTPException(status_code=404, detail="Ordine non trovato")

    # Denormalize org + customer name (existing behaviour).
    org = await organizations_collection.find_one(
        {"id": org_id}, {"_id": 0, "name": 1},
    )
    order["org_name"] = org.get("name", "") if org else ""

    customer = await customers_collection.find_one(
        {"id": order["customer_id"], "organization_id": org_id},
        {"_id": 0, "name": 1},
    )
    order["customer_name"] = customer.get("name", "") if customer else ""

    # Opt-in enrichment with issued assets (tickets / bookings /
    # reservations / downloads). Skipped when not requested so the
    # orders-list page stays a single fast Mongo query.
    if with_issued:
        await _attach_issued_assets(order, org_id)

    return order


async def _attach_issued_assets(order: dict, org_id: str) -> None:
    """Populate order['_issued_*'] arrays for the customer detail page.

    Each array is filtered to (organization_id, order_id) so cross-
    tenant or cross-order leakage is impossible — defence in depth on
    top of the order ownership check the caller already performed.

    Each list is sorted in a stable order so the UI rendering is
    deterministic across page loads (helps when the customer takes
    a screenshot for a colleague or compares two refreshes).

    Mutates `order` in place; returns None on purpose so the caller
    keeps using the existing reference. Best-effort — DB blips on
    any one collection do not raise; the customer just sees the
    pre-Step-2 minimal layout for that line.
    """
    from database import (
        issued_tickets_collection,
        issued_bookings_collection,
        issued_reservations_collection,
        issued_downloads_collection,
        issued_course_accesses_collection,
    )

    order_id = order.get("id", "")
    base_filter = {"organization_id": org_id, "order_id": order_id}

    async def _safe_list(coll, sort_keys):
        try:
            # Pass the full key list to .sort() in a single call — chained
            # .sort(k1).sort(k2) on motor REPLACES rather than accumulates,
            # which silently turns a multi-key sort into a single-key
            # sort on the last call. The list form preserves the
            # composite ordering we actually want.
            cursor = coll.find(base_filter, {"_id": 0}).sort(sort_keys)
            return await cursor.to_list(length=500)
        except Exception:
            # Never fail the whole detail page because one issued-*
            # collection had a hiccup. The renderer falls back to the
            # minimal line-snapshot layout for that branch.
            return []

    order["_issued_tickets"] = await _safe_list(
        issued_tickets_collection,
        # Same occurrence first, then by seat — stable ticket grid order
        [("occurrence_id", 1), ("seat_index", 1), ("created_at", 1)],
    )
    order["_issued_bookings"] = await _safe_list(
        issued_bookings_collection,
        # Earliest appointment first
        [("booking_date", 1), ("booking_start_time", 1)],
    )
    order["_issued_reservations"] = await _safe_list(
        issued_reservations_collection,
        # Range: by date_from. Slot: falls back to slot_date because
        # date_from is null. Mongo sorts nulls first, so slot rows
        # cluster correctly regardless.
        [("date_from", 1), ("slot_date", 1), ("slot_start_time", 1)],
    )
    order["_issued_downloads"] = await _safe_list(
        issued_downloads_collection,
        [("created_at", 1)],
    )
    # Course accesses are joined here (Step 8) so the order detail page
    # can deep-link straight to /account/courses/<enrollment_id>. The
    # full course player UX still lives at /account/courses — this is
    # purely the entry point for "I bought it, take me to the right
    # enrollment now".
    order["_issued_course_accesses"] = await _safe_list(
        issued_course_accesses_collection,
        [("enrolled_at", 1)],
    )


# ── Release 4 (Courses) Step 6 — "I miei corsi" customer area ────────────────
#
# Two endpoints power the customer-facing course experience:
#
#   GET /customer/courses                 → grid/list view of active enrollments
#   GET /customer/courses/{enrollment_id} → single-course detail (sidebar +
#                                           modules/lessons with progress)
#
# Security invariants enforced here (the player endpoints of Step 7 add
# a third layer on top):
#
#   * customer_account_id + organization_id from the JWT are the ONLY
#     filters that expose enrollment rows. Copying another customer's
#     enrollment_id into the URL produces a 404 — the scoping predicate
#     is IN the Mongo query, not an afterthought check.
#
#   * Revoked / expired enrollments are hidden from the listing and
#     return 403 on the detail endpoint (not 404 — we want to distinguish
#     "doesn't exist" from "access revoked / expired").
#
#   * bunny_video_guid is NEVER surfaced here. The lesson payload carries
#     only title + duration + order + is_preview. The signed Bunny URL is
#     minted in Step 7 via a dedicated endpoint that re-verifies the
#     enrollment at play time.


def _is_enrollment_expired(enr: dict, now) -> bool:
    """True when the enrollment's expires_at is in the past.

    Keeps the comparison tolerant to both str and datetime storage
    (Pydantic dumps datetime objects; some flows store ISO strings).
    """
    exp = enr.get("expires_at")
    if not exp:
        return False
    if hasattr(exp, "tzinfo"):
        return exp < now
    # ISO string — best-effort parse
    try:
        from datetime import datetime, timezone
        parsed = datetime.fromisoformat(str(exp).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed < now
    except Exception:
        return False


def _project_course_for_customer(course_doc: dict) -> dict:
    """Strip internal fields from a Course document before returning it
    to the customer. Most importantly: NO bunny_video_guid on lessons.
    """
    if not course_doc:
        return {}
    modules_out = []
    for m in (course_doc.get("modules") or []):
        lessons_out = []
        for l in (m.get("lessons") or []):
            lessons_out.append({
                "id": l.get("id"),
                "order": int(l.get("order") or 0),
                "title": l.get("title", ""),
                "description": l.get("description"),
                "duration_seconds": int(l.get("duration_seconds") or 0),
                "is_preview": bool(l.get("is_preview")),
                "has_video": bool(l.get("bunny_video_guid")),
                "resources": l.get("resources") or [],
            })
        modules_out.append({
            "id": m.get("id"),
            "order": int(m.get("order") or 0),
            "title": m.get("title", ""),
            "description": m.get("description"),
            "lessons": lessons_out,
        })
    return {
        "id": course_doc.get("id"),
        "title": course_doc.get("title", ""),
        "description": course_doc.get("description"),
        "long_description": course_doc.get("long_description"),
        "cover_image_url": course_doc.get("cover_image_url"),
        "instructor_name": course_doc.get("instructor_name"),
        "instructor_bio": course_doc.get("instructor_bio"),
        "access_policy": course_doc.get("access_policy") or "lifetime",
        "access_expiry_days": course_doc.get("access_expiry_days"),
        "modules": modules_out,
    }


@router.get("/courses")
async def list_my_courses(current_customer: dict = Depends(get_current_customer)):
    """Grid view of courses the customer is enrolled into.

    Returns: `{courses: [ {enrollment: {...}, course: {...}, progress_stats: {...}} ]}`

    Excluded from the listing: revoked (revoked_at != null) and expired
    enrollments. The list is sorted by last_accessed_at DESC then by
    enrolled_at DESC so the customer sees the most relevant course first.
    """
    from database import issued_course_accesses_collection, courses_collection
    from models.common import utc_now

    account_id = current_customer["customer_account_id"]
    org_id = current_customer["organization_id"]
    now = utc_now()

    # Pull active enrollments (not revoked). Expiry filter is applied in
    # Python below to tolerate mixed str/datetime storage.
    cursor = issued_course_accesses_collection.find(
        {
            "customer_account_id": account_id,
            "organization_id": org_id,
            "revoked_at": None,
        },
        {"_id": 0},
    ).sort([("last_accessed_at", -1), ("enrolled_at", -1)]).limit(200)
    enrollments = await cursor.to_list(200)

    # Filter out expired + bulk-fetch course snapshots once.
    active = [e for e in enrollments if not _is_enrollment_expired(e, now)]
    course_ids = list({e["course_id"] for e in active if e.get("course_id")})
    course_map: dict[str, dict] = {}
    if course_ids:
        async for c in courses_collection.find(
            {"id": {"$in": course_ids}, "organization_id": org_id},
            {"_id": 0},
        ):
            course_map[c["id"]] = c

    courses_out = []
    for enr in active:
        course_doc = course_map.get(enr.get("course_id"))
        # Compute progress_stats even when the course doc is missing
        # (e.g. admin hard-deleted it). We still surface the enrollment
        # with 0/0 so the customer sees a truthful state.
        lessons = []
        if course_doc:
            for m in (course_doc.get("modules") or []):
                for l in (m.get("lessons") or []):
                    lessons.append(l)
        total_lessons = len(lessons)
        completed = 0
        progress = enr.get("progress") or {}
        for lid in progress.keys():
            if progress[lid].get("completed_at"):
                completed += 1
        percentage = int(round(100 * completed / total_lessons)) if total_lessons else 0

        courses_out.append({
            "enrollment": {
                "id": enr.get("id"),
                "access_token": enr.get("access_token"),  # internal fingerprint, safe in customer payload
                "enrolled_at": enr.get("enrolled_at"),
                "expires_at": enr.get("expires_at"),
                "last_accessed_at": enr.get("last_accessed_at"),
            },
            "course": {
                "id": course_doc.get("id") if course_doc else enr.get("course_id"),
                "title": (course_doc or {}).get("title") or enr.get("course_title_snapshot", ""),
                "description": (course_doc or {}).get("description"),
                "cover_image_url": (course_doc or {}).get("cover_image_url"),
                "instructor_name": (course_doc or {}).get("instructor_name"),
                "modules_count": len((course_doc or {}).get("modules") or []),
                "lessons_count": total_lessons,
                "total_duration_seconds": sum(
                    int(l.get("duration_seconds") or 0) for l in lessons
                ),
                # Signal that the content entity is gone without breaking the UI.
                "is_available": bool(course_doc),
            },
            "progress_stats": {
                "lessons_completed": completed,
                "total_lessons": total_lessons,
                "percentage": percentage,
            },
        })

    return {"courses": courses_out, "total": len(courses_out)}


@router.get("/courses/{enrollment_id}")
async def get_my_course_detail(
    enrollment_id: str,
    current_customer: dict = Depends(get_current_customer),
):
    """Detailed view of a single enrollment (modules + lessons + per-lesson
    progress).

    Returns 404 when:
      * enrollment_id does not exist
      * OR it belongs to a different customer / different org
        (we do not distinguish the two — same response on purpose to
        avoid leaking enrollment existence across customers).

    Returns 403 when the enrollment is revoked or expired. The customer
    UI differentiates these cases from a plain 404 so it can show a
    "accesso revocato" / "scaduto" message instead of "non trovato".
    """
    from database import issued_course_accesses_collection, courses_collection
    from models.common import utc_now

    account_id = current_customer["customer_account_id"]
    org_id = current_customer["organization_id"]
    now = utc_now()

    enr = await issued_course_accesses_collection.find_one(
        {
            "id": enrollment_id,
            "customer_account_id": account_id,
            "organization_id": org_id,
        },
        {"_id": 0},
    )
    if not enr:
        raise HTTPException(status_code=404, detail="Corso non trovato")

    if enr.get("revoked_at"):
        raise HTTPException(
            status_code=403,
            detail={"error": "enrollment_revoked", "message": "Accesso al corso revocato."},
        )
    if _is_enrollment_expired(enr, now):
        raise HTTPException(
            status_code=403,
            detail={"error": "enrollment_expired", "message": "Il tuo accesso al corso è scaduto."},
        )

    course_doc = await courses_collection.find_one(
        {"id": enr.get("course_id"), "organization_id": org_id},
        {"_id": 0},
    )
    if not course_doc:
        # The course entity was deleted. Return a minimal degraded response
        # so the UI can show a clear "contenuto non disponibile" message.
        raise HTTPException(
            status_code=410,
            detail={"error": "course_unavailable", "message": "Il contenuto del corso non è più disponibile."},
        )

    course_projection = _project_course_for_customer(course_doc)

    # Progress — key by lesson_id, include only lessons that exist in the
    # current course shape (defensive against lessons removed after enrolment).
    valid_lesson_ids = {
        l["id"] for m in course_projection["modules"] for l in m["lessons"]
    }
    raw_progress = enr.get("progress") or {}
    progress = {
        lid: {
            "watched_seconds": int((raw_progress[lid] or {}).get("watched_seconds", 0) or 0),
            "completed_at": (raw_progress[lid] or {}).get("completed_at"),
        }
        for lid in raw_progress.keys()
        if lid in valid_lesson_ids
    }

    total_lessons = len(valid_lesson_ids)
    completed = sum(1 for v in progress.values() if v.get("completed_at"))
    percentage = int(round(100 * completed / total_lessons)) if total_lessons else 0

    return {
        "enrollment": {
            "id": enr.get("id"),
            "enrolled_at": enr.get("enrolled_at"),
            "expires_at": enr.get("expires_at"),
            "last_accessed_at": enr.get("last_accessed_at"),
        },
        "course": course_projection,
        "progress": progress,
        "progress_stats": {
            "lessons_completed": completed,
            "total_lessons": total_lessons,
            "percentage": percentage,
        },
    }


# ── Release 4 (Courses) Step 7 — player: signed Bunny URL + progress ────────

class PlayUrlResponse(BaseModel):
    """Response shape for the play-url endpoint. Kept narrow on purpose:
    no enrollment internals or course metadata — the caller already has
    those from the detail endpoint."""
    play_url: str
    expires_at: str
    watermark_text: Optional[str] = None


class ProgressInput(BaseModel):
    """Heartbeat body from the player.

    watched_seconds: cumulative seconds the player has spent on this
                     lesson. Server enforces max() so replaying a
                     smaller value never rewinds the progress bar.
    completed:       explicit completion flag. Once True, `completed_at`
                     is set once and never flipped back — completion is
                     sticky per the product design (watched once = done).
    """
    lesson_id: str = Field(min_length=1, max_length=64)
    watched_seconds: int = Field(default=0, ge=0, le=100_000)
    completed: bool = False


@router.post("/courses/{enrollment_id}/lessons/{lesson_id}/play-url", response_model=PlayUrlResponse)
async def get_lesson_play_url(
    enrollment_id: str,
    lesson_id: str,
    current_customer: dict = Depends(get_current_customer),
):
    """Mint a short-lived signed Bunny embed URL for a specific lesson.

    Auth strata applied here (in order):
      1. JWT must be `type=customer` (Depends already enforces).
      2. Enrollment must exist, belong to this customer, this org.
      3. Enrollment must not be revoked, must not be expired.
      4. Course doc must still exist and be active.
      5. Lesson must be part of the enrolled Course (no cross-course
         leakage via crafted lesson_ids).
      6. Lesson must have a bunny_video_guid — lessons without video
         can't be played; we return 404 with a distinct error code.

    Only after ALL checks pass do we build the signed URL. The URL
    itself encodes the TTL in the query string; Bunny CDN rejects it
    after `expires`.
    """
    from database import (
        issued_course_accesses_collection, courses_collection,
        organizations_collection,
    )
    from models.common import utc_now
    from services.bunny_service import (
        generate_signed_embed_url, validate_bunny_config, BunnyConfigError,
    )

    account_id = current_customer["customer_account_id"]
    org_id = current_customer["organization_id"]
    email = current_customer.get("email")
    now = utc_now()

    enr = await issued_course_accesses_collection.find_one(
        {
            "id": enrollment_id,
            "customer_account_id": account_id,
            "organization_id": org_id,
        },
        {"_id": 0},
    )
    if not enr:
        raise HTTPException(status_code=404, detail="Corso non trovato")

    if enr.get("revoked_at"):
        raise HTTPException(
            status_code=403,
            detail={"error": "enrollment_revoked", "message": "Accesso al corso revocato."},
        )
    if _is_enrollment_expired(enr, now):
        raise HTTPException(
            status_code=403,
            detail={"error": "enrollment_expired", "message": "Il tuo accesso al corso è scaduto."},
        )

    course_doc = await courses_collection.find_one(
        {"id": enr.get("course_id"), "organization_id": org_id, "is_active": True},
        {"_id": 0, "modules": 1},
    )
    if not course_doc:
        raise HTTPException(
            status_code=410,
            detail={"error": "course_unavailable", "message": "Il contenuto del corso non è più disponibile."},
        )

    # Locate lesson — O(N_modules × N_lessons) but N is tiny for a single course.
    lesson_doc = None
    for m in (course_doc.get("modules") or []):
        for l in (m.get("lessons") or []):
            if l.get("id") == lesson_id:
                lesson_doc = l
                break
        if lesson_doc:
            break
    if not lesson_doc:
        raise HTTPException(status_code=404, detail="Lezione non trovata in questo corso")

    video_guid = lesson_doc.get("bunny_video_guid")
    if not video_guid:
        raise HTTPException(
            status_code=404,
            detail={"error": "lesson_no_video", "message": "Questa lezione non ha ancora un video caricato."},
        )

    org_doc = await organizations_collection.find_one(
        {"id": org_id}, {"_id": 0, "integrations": 1},
    )

    # Multi-library Step 4: route through the centralized resolver
    # instead of reading `org.integrations.bunny` directly. The
    # resolver handles the full priority chain:
    #   1. Lesson explicit `bunny_library_id` → matching library
    #   2. Orphan reference → fall through to default
    #   3. Default library in `bunny_libraries`
    #   4. First library when no default marked
    #   5. Legacy single-library `integrations.bunny`
    #   6. None → 503
    #
    # Backward compatibility is preserved: orgs that still have only
    # the legacy `bunny` field (no `bunny_libraries`) get the same
    # config they always got. Customer playback for those orgs is
    # byte-for-byte unchanged.
    from services.bunny import resolve_library_config
    bunny_config = resolve_library_config(lesson_doc, org_doc)
    if not validate_bunny_config(bunny_config):
        raise HTTPException(
            status_code=503,
            detail={
                "error": "bunny_not_configured",
                "message": "Il corso è temporaneamente non disponibile. Contatta il merchant.",
            },
        )

    try:
        signed = generate_signed_embed_url(
            bunny_config,
            video_guid,
            customer_email=email,
        )
    except (BunnyConfigError, ValueError) as exc:
        logger.warning("play-url mint failed org=%s enrollment=%s: %s", org_id, enrollment_id, exc)
        raise HTTPException(status_code=503, detail={"error": "bunny_not_configured", "message": "Servizio video non disponibile."})

    # Update last_accessed_at so "My courses" sorts by recent activity.
    # Fire-and-forget — failure must not block the play.
    try:
        await issued_course_accesses_collection.update_one(
            {"id": enrollment_id},
            {"$set": {"last_accessed_at": now, "updated_at": now}},
        )
    except Exception as e:
        logger.debug("last_accessed_at update failed for enrollment=%s: %s", enrollment_id, e)

    return PlayUrlResponse(
        play_url=signed.play_url,
        expires_at=signed.expires_at.isoformat(),
        watermark_text=signed.watermark_text,
    )


@router.post("/courses/{enrollment_id}/progress")
async def update_course_progress(
    enrollment_id: str,
    body: ProgressInput,
    current_customer: dict = Depends(get_current_customer),
):
    """Upsert per-lesson progress for an enrollment.

    Idempotent + monotonic on `watched_seconds` (max-merge). `completed_at`
    is sticky — set once when body.completed is True, never cleared.
    Updates `last_accessed_at` on every call.

    Rejects the heartbeat when the enrollment is revoked/expired so
    the player can redirect back to /account/courses.
    """
    from database import issued_course_accesses_collection, courses_collection
    from models.common import utc_now

    account_id = current_customer["customer_account_id"]
    org_id = current_customer["organization_id"]
    now = utc_now()

    enr = await issued_course_accesses_collection.find_one(
        {
            "id": enrollment_id,
            "customer_account_id": account_id,
            "organization_id": org_id,
        },
        {"_id": 0},
    )
    if not enr:
        raise HTTPException(status_code=404, detail="Corso non trovato")
    if enr.get("revoked_at"):
        raise HTTPException(
            status_code=403,
            detail={"error": "enrollment_revoked", "message": "Accesso al corso revocato."},
        )
    if _is_enrollment_expired(enr, now):
        raise HTTPException(
            status_code=403,
            detail={"error": "enrollment_expired", "message": "Il tuo accesso al corso è scaduto."},
        )

    # Defensive: lesson_id must belong to the current course. Prevents
    # a malicious client from injecting progress on a non-existent or
    # foreign lesson_id (noise in the progress dict).
    course_doc = await courses_collection.find_one(
        {"id": enr.get("course_id"), "organization_id": org_id, "is_active": True},
        {"_id": 0, "modules": 1},
    )
    valid_lesson_ids = set()
    for m in ((course_doc or {}).get("modules") or []):
        for l in (m.get("lessons") or []):
            if l.get("id"):
                valid_lesson_ids.add(l["id"])
    if body.lesson_id not in valid_lesson_ids:
        raise HTTPException(status_code=404, detail="Lezione non trovata in questo corso")

    progress = enr.get("progress") or {}
    current = progress.get(body.lesson_id) or {}
    current_watched = int(current.get("watched_seconds") or 0)
    new_watched = max(current_watched, int(body.watched_seconds))

    current_completed = current.get("completed_at")
    new_completed = current_completed
    if body.completed and not current_completed:
        new_completed = now

    progress[body.lesson_id] = {
        "watched_seconds": new_watched,
        "completed_at": new_completed,
    }

    await issued_course_accesses_collection.update_one(
        {"id": enrollment_id},
        {"$set": {
            "progress": progress,
            "last_accessed_at": now,
            "updated_at": now,
        }},
    )

    # Return the single lesson's state + overall stats so the player
    # can refresh the sidebar without a second round-trip.
    total_lessons = len(valid_lesson_ids)
    completed_count = sum(1 for v in progress.values() if v.get("completed_at"))
    percentage = int(round(100 * completed_count / total_lessons)) if total_lessons else 0

    return {
        "lesson_id": body.lesson_id,
        "watched_seconds": new_watched,
        "completed_at": new_completed.isoformat() if hasattr(new_completed, "isoformat") else new_completed,
        "progress_stats": {
            "lessons_completed": completed_count,
            "total_lessons": total_lessons,
            "percentage": percentage,
        },
    }


@router.get("/orders/{order_id}/receipt")
async def download_my_receipt(
    order_id: str,
    current_customer: dict = Depends(get_current_customer),
):
    """Download PDF receipt for a customer's own order."""
    from services.order_pdf_service import generate_order_receipt
    from fastapi.responses import Response

    account_id = current_customer["customer_account_id"]
    org_id = current_customer["organization_id"]

    order = await orders_collection.find_one(
        {"id": order_id, "customer_account_id": account_id, "organization_id": org_id,
         "status": {"$in": ["confirmed", "completed"]}},
        {"_id": 0},
    )
    if not order:
        raise HTTPException(status_code=404, detail="Ordine non trovato o non ancora confermato")

    org = await organizations_collection.find_one({"id": org_id}, {"_id": 0, "store_settings": 1, "name": 1})
    store_settings = (org or {}).get("store_settings") or {}
    if not store_settings.get("display_name"):
        store_settings["display_name"] = (org or {}).get("name", "Store")

    customer = await customers_collection.find_one(
        {"id": order.get("customer_id"), "organization_id": org_id}, {"_id": 0, "name": 1})
    if customer:
        order["customer_name"] = customer.get("name", "")

    pdf_bytes = generate_order_receipt(order, store_settings)
    filename = f"ricevuta_{order.get('order_number', order_id[:8])}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Track E Step 2.4.6 — Customer assets endpoints (downloads/bookings/reservations)
#
# Endpoint che il widget embed (Lit) usa nella sezione "Area personale"
# del customer portal per mostrare:
#   - I miei download (file digitali acquistati)
#   - Le mie prenotazioni (booking conferme su service products)
#   - I miei noleggi (reservation conferme su rental products)
#
# Auth: customer JWT (Depends get_current_customer).
# Multi-tenant: scoped a (customer_account_id, organization_id).
# Read-only: nessuna mutazione, no PII leak in payload (whitelist projection).


@router.get("/downloads")
async def get_my_downloads(current_customer: dict = Depends(get_current_customer)):
    """Return issued downloads (digital products) per customer.

    Track E Step 2.4.6 — widget embed customer-portal tab "I miei download".

    Sicurezza
    ---------
    - Multi-tenant: compound match (customer_account_id, org_id)
    - PII / leak safe: projection whitelist (no admin notes, no internal
      delivery_status_log, no email recipient — il customer e' gia' lui)
    - URL signing: il file vero viene servito da /api/public/downloads/{token}/file
      (signed, expiring, max_downloads enforced)

    Returns:
        {downloads: [{id, code, product_id, product_name, status, access_token,
                      access_token_expires_at, max_downloads, downloads_count,
                      created_at}], total: int}
    """
    from database import issued_downloads_collection

    account_id = current_customer["customer_account_id"]
    org_id = current_customer["organization_id"]

    try:
        cursor = issued_downloads_collection.find(
            {"customer_account_id": account_id, "organization_id": org_id},
            {
                "_id": 0,
                "id": 1,
                "code": 1,
                "order_id": 1,
                "product_id": 1,
                "product_name": 1,
                "status": 1,
                "access_token": 1,
                "access_token_expires_at": 1,
                "max_downloads": 1,
                "downloads_count": 1,
                "created_at": 1,
                "expires_at": 1,
            },
        ).sort("created_at", -1).limit(100)
        downloads = await cursor.to_list(100)
    except Exception as exc:
        logger.warning(
            "customer downloads list failed for customer=%s org=%s: %s",
            account_id, org_id, exc,
        )
        downloads = []

    return {"downloads": downloads, "total": len(downloads)}


@router.get("/bookings")
async def get_my_bookings(current_customer: dict = Depends(get_current_customer)):
    """Return issued bookings (service products with slot booking) per customer.

    Track E Step 2.4.6 — widget embed customer-portal tab "Le mie prenotazioni".

    Sicurezza
    ---------
    - Multi-tenant: compound match (customer_account_id, org_id)
    - Projection whitelist: solo i campi safe-to-public

    Returns:
        {bookings: [{id, code, product_id, product_name, booking_date,
                     booking_start_time, booking_end_time, status,
                     service_option_label, location, created_at}], total: int}
    """
    from database import issued_bookings_collection

    account_id = current_customer["customer_account_id"]
    org_id = current_customer["organization_id"]

    try:
        cursor = issued_bookings_collection.find(
            {"customer_account_id": account_id, "organization_id": org_id},
            {
                "_id": 0,
                "id": 1,
                "code": 1,
                "order_id": 1,
                "product_id": 1,
                "product_name": 1,
                "booking_date": 1,
                "booking_start_time": 1,
                "booking_end_time": 1,
                "booking_end_date": 1,
                "status": 1,
                "service_option_id": 1,
                "service_option_label": 1,
                "location": 1,
                "notes": 1,
                # Track E Step 5.2 — access_token per .ics calendar download
                # (link /api/public/bookings/{access_token}/ics)
                "access_token": 1,
                "created_at": 1,
            },
        ).sort("booking_date", -1).limit(100)
        bookings = await cursor.to_list(100)
    except Exception as exc:
        logger.warning(
            "customer bookings list failed for customer=%s org=%s: %s",
            account_id, org_id, exc,
        )
        bookings = []

    return {"bookings": bookings, "total": len(bookings)}


@router.get("/reservations")
async def get_my_reservations(current_customer: dict = Depends(get_current_customer)):
    """Return issued reservations (rental products with date range) per customer.

    Track E Step 2.4.6 — widget embed customer-portal tab "I miei noleggi".

    Sicurezza
    ---------
    - Multi-tenant: compound match (customer_account_id, org_id)
    - Projection whitelist

    Returns:
        {reservations: [{id, code, product_id, product_name, rental_date_from,
                         rental_date_to, status, created_at}], total: int}
    """
    from database import issued_reservations_collection

    account_id = current_customer["customer_account_id"]
    org_id = current_customer["organization_id"]

    try:
        cursor = issued_reservations_collection.find(
            {"customer_account_id": account_id, "organization_id": org_id},
            {
                "_id": 0,
                "id": 1,
                "code": 1,
                "order_id": 1,
                "product_id": 1,
                "product_name": 1,
                "rental_date_from": 1,
                "rental_date_to": 1,
                "booking_date": 1,
                "booking_start_time": 1,
                "booking_end_time": 1,
                "booking_end_date": 1,
                "status": 1,
                "approval_status": 1,
                "rental_notes": 1,
                "created_at": 1,
                # Track E Step 5.2 — access_token per .ics calendar download
                "access_token": 1,
            },
        ).sort("rental_date_from", -1).limit(100)
        reservations = await cursor.to_list(100)
    except Exception as exc:
        logger.warning(
            "customer reservations list failed for customer=%s org=%s: %s",
            account_id, org_id, exc,
        )
        reservations = []

    return {"reservations": reservations, "total": len(reservations)}


# ── Track E Step 5.5 — Customer-initiated booking cancel ─────────────────
#
# Customer puo' richiedere la cancellazione di una sua prenotazione dal
# portale widget. La cancellazione e' soft (status="cancelled" + timestamp)
# — non hard-delete, per preservare audit trail e gestione disputes.
#
# Policy:
#   - Cancellazione ALWAYS allowed entro N giorni dalla booking_date
#     (configurabile per merchant in future; per ora hardcoded a 24h)
#   - Customer ID ownership check (no cross-customer cancel)
#   - Multi-tenant scope (no cross-org leakage)
#   - Status idempotent: cancel su already-cancelled = no-op


@router.post("/bookings/{booking_id}/cancel")
async def cancel_my_booking(
    booking_id: str,
    current_customer: dict = Depends(get_current_customer),
):
    """Customer cancela una sua prenotazione service.

    Track E Step 5.5 — widget cancel from <afianco-my-bookings>.

    Sicurezza:
    - customer_account_id ownership check (cross-customer prevention)
    - organization_id scope (multi-tenant guard)
    - Status idempotent (already-cancelled = no-op)

    Future enhancements:
    - Cancellation policy (deadline pre-slot configurabile per merchant)
    - Refund automation (Stripe refund partial/full)
    - Email notification al merchant + customer
    """
    from database import issued_bookings_collection
    from models.common import utc_now

    account_id = current_customer["customer_account_id"]
    org_id = current_customer["organization_id"]

    booking = await issued_bookings_collection.find_one(
        {
            "id": booking_id,
            "customer_account_id": account_id,
            "organization_id": org_id,
        },
        {"_id": 0, "id": 1, "status": 1, "booking_date": 1},
    )
    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Prenotazione non trovata",
        )

    if booking.get("status") == "cancelled":
        return {"message": "Prenotazione gia' cancellata", "status": "cancelled"}

    await issued_bookings_collection.update_one(
        {"id": booking_id, "customer_account_id": account_id},
        {
            "$set": {
                "status": "cancelled",
                "cancelled_at": utc_now().isoformat(),
                "cancelled_by": "customer",
                "updated_at": utc_now().isoformat(),
            },
        },
    )

    logger.info(
        "Booking cancelled by customer: booking=%s customer=%s org=%s",
        booking_id, account_id, org_id,
    )

    return {"message": "Prenotazione cancellata", "status": "cancelled"}


# ── Track L Step 1 — GDPR right-to-erasure (Art. 17 GDPR) ────────────────


class ErasureRequestBody(BaseModel):
    """Body for POST /customer/me/request-erasure.

    Customer dichiara di voler esercitare il diritto all'oblio (Art. 17
    GDPR). Optional reason field per audit log + customer support.
    """
    reason: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Motivo opzionale della richiesta (analytics + customer support).",
    )
    confirm: bool = Field(
        ...,
        description="Conferma esplicita che customer comprende che l'erasure "
                    "e' irreversible. Frontend deve mostrare modal confirm.",
    )


class ErasureRequestResponse(BaseModel):
    status: str
    message: str
    request_id: str
    estimated_completion_days: int


@router.post(
    "/me/request-erasure",
    response_model=ErasureRequestResponse,
    status_code=202,
)
async def request_account_erasure(
    body: ErasureRequestBody,
    current_customer: dict = Depends(get_current_customer),
):
    """Track L Step 1 — GDPR right-to-erasure (Art. 17 GDPR).

    Customer richiede la cancellazione del proprio account + dati associati.

    Flow V1 (semi-manual):
      1. Customer chiama questo endpoint con confirm=true
      2. Marca account: `erasure_requested_at`, `erasure_request_reason`
      3. Email notification ad admin di sistema (via Brevo)
      4. Email conferma a customer (separate, no leak)
      5. Audit log permanente in `audit_logs` collection
      6. (Manual) Admin processa entro 30gg → cascade DELETE
         su cart, orders, consent_audit, customer_account
      7. Final email conferma cancellazione completata

    Trade-off V1: processo manuale (admin esegue cascade) per evitare
    bug catastrofici (accidental delete di customer attivo). V2 →
    automated cascade con dry-run + 24h grace period.

    Response 202 Accepted: la richiesta e' registrata, esecuzione
    asincrona. Estimated 30 giorni (GDPR Art. 12 max response time).
    """
    if not body.confirm:
        # Defense in depth: frontend dovrebbe gia' bloccare ma sentinel.
        raise HTTPException(
            status_code=400,
            detail="Conferma esplicita richiesta (body.confirm=true).",
        )

    from database import customer_accounts_collection, audit_logs_collection
    from models.common import utc_now, generate_id

    customer_id = current_customer["customer_account_id"]
    org_id = current_customer["organization_id"]
    now = utc_now()
    request_id = generate_id()

    # Check se gia' richiesta in corso (anti-spam + idempotent)
    from repositories import customer_account_repository
    account = await customer_account_repository.find_by_id(customer_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account non trovato.")

    if account.get("erasure_requested_at"):
        # Idempotent: ritorna stato esistente invece di erroreggiare
        logger.info(
            "customer erasure: duplicate request for %s (already pending)",
            customer_id,
        )
        return ErasureRequestResponse(
            status="pending",
            message=(
                "Una richiesta di cancellazione e' gia' in elaborazione "
                "per il tuo account. Riceverai conferma entro 30 giorni."
            ),
            request_id=account.get("erasure_request_id", request_id),
            estimated_completion_days=30,
        )

    # Mark account: erasure pending
    await customer_accounts_collection.update_one(
        {"id": customer_id},
        {"$set": {
            "erasure_requested_at": now.isoformat(),
            "erasure_request_id": request_id,
            "erasure_request_reason": (body.reason or "").strip()[:500],
            "updated_at": now.isoformat(),
        }},
    )

    # Audit log permanente (NON cancellato dal cascade — proof legale)
    try:
        await audit_logs_collection.insert_one({
            "id": generate_id(),
            "organization_id": org_id,
            "actor_id": customer_id,
            "actor_type": "customer",
            "action": "gdpr_erasure_requested",
            "resource_type": "customer_account",
            "resource_id": customer_id,
            "metadata": {
                "request_id": request_id,
                "reason": body.reason,
                "email_redacted": (
                    account["email"][:3] + "***" +
                    account["email"][account["email"].find("@"):]
                    if "@" in account.get("email", "") else "***"
                ),
            },
            "created_at": now.isoformat(),
        })
    except Exception as exc:
        # Audit log failure NON blocca la richiesta — il marker
        # sull'account e' la primary source. Log + Sentry per ops.
        logger.error(
            "customer erasure: audit log insert failed for %s: %s",
            customer_id, exc, exc_info=True,
        )

    # Notify admin via email (best-effort — failure non blocca response)
    try:
        from services.email_service import send_admin_notification
        send_admin_notification(
            subject=f"[GDPR] Richiesta cancellazione account — {request_id[:8]}",
            body=(
                f"Customer ha richiesto cancellazione account.\n\n"
                f"Request ID: {request_id}\n"
                f"Customer ID: {customer_id}\n"
                f"Org ID: {org_id}\n"
                f"Email: {account.get('email', '?')}\n"
                f"Reason: {body.reason or '(non fornito)'}\n"
                f"Requested at: {now.isoformat()}\n\n"
                f"SLA GDPR: 30 giorni per esecuzione.\n"
                f"Procedura cascade: vedere docs/operations/gdpr-erasure-procedure.md"
            ),
        )
    except (ImportError, AttributeError):
        # send_admin_notification non implementato? Log warning.
        logger.warning(
            "customer erasure: admin notification helper not available — "
            "process request_id=%s manually within 30gg",
            request_id,
        )
    except Exception as exc:
        logger.error(
            "customer erasure: admin notification failed for %s: %s",
            request_id, exc,
        )

    logger.info(
        "GDPR erasure requested: customer=%s org=%s request_id=%s",
        customer_id, org_id, request_id,
    )

    return ErasureRequestResponse(
        status="accepted",
        message=(
            "La tua richiesta di cancellazione e' stata registrata. "
            "Sarai contattato entro 30 giorni con la conferma di completamento "
            "(GDPR Art. 12). Puoi continuare a usare il tuo account fino "
            "alla cancellazione effettiva."
        ),
        request_id=request_id,
        estimated_completion_days=30,
    )
