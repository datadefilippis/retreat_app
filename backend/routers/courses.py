"""
Courses admin router.

Release 4 (Courses) Step 2. CRUD on Course documents plus nested
sub-resource endpoints for modules and lessons. All endpoints are
org-scoped via `get_current_user` — an admin of org A can never touch
courses of org B (matching the pattern used by products / product_extras).

Endpoint shape:
  GET    /api/courses                              — list
  POST   /api/courses                              — create
  GET    /api/courses/{course_id}                  — detail
  PATCH  /api/courses/{course_id}                  — update top-level fields
  DELETE /api/courses/{course_id}                  — soft delete (is_active=False)

  POST   /api/courses/{course_id}/modules          — add module
  PATCH  /api/courses/{course_id}/modules/{mod_id} — update module
  DELETE /api/courses/{course_id}/modules/{mod_id} — remove module

  POST   /api/courses/{course_id}/modules/{mod_id}/lessons           — add lesson
  PATCH  /api/courses/{course_id}/modules/{mod_id}/lessons/{lid}     — update lesson
  DELETE /api/courses/{course_id}/modules/{mod_id}/lessons/{lid}     — remove lesson

Nested write pattern: fetch the course, mutate the in-memory modules
list, call repo.update_modules(). Keeps the code simple and atomic at
the single-document level. Concurrent writes on the same course from
the same admin are extremely rare in the editor UX, so optimistic
concurrency is sufficient for MVP.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from auth import get_current_user, get_verified_user, get_verified_user
from database import products_collection
from models.common import generate_id
from models.course import (
    CourseAccessPolicy, CourseCreate, CourseModule, CourseResource,
    CourseResponse, CourseUpdate, Lesson,
)
from repositories import course_repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/courses", tags=["Courses"])


# ── Permissions helper ──────────────────────────────────────────────────────

def _require_admin(current_user: dict) -> None:
    """Mirror the pattern used by product_extras_router — write ops are
    restricted to admins (role: admin or system_admin). Reads are open
    to any authenticated org user."""
    role = current_user.get("role")
    if role not in ("admin", "system_admin"):
        raise HTTPException(status_code=403, detail="Forbidden")


# ── Course-level CRUD ───────────────────────────────────────────────────────

@router.get("", response_model=List[CourseResponse])
async def list_courses(
    active_only: bool = True,
    limit: int = 500,
    current_user: dict = Depends(get_verified_user),
):
    """List courses of the current org, sorted by title."""
    org_id = current_user["organization_id"]
    courses = await course_repository.find_by_org(org_id, active_only=active_only, limit=limit)
    return [CourseResponse(**c.model_dump()) for c in courses]


async def _ensure_linked_product(
    org_id: str,
    course,
) -> dict:
    """Create (or return existing) Product with item_type='course' linked
    to a Course via metadata.course_id.

    Idempotent: a course can have many products pointing at it (future
    scenario: cross-sell bundles) but we keep exactly ONE "primary"
    product per course — the one auto-created at course birth. The
    `metadata.course_id` index would be nice but isn't critical for
    lookup performance at our scale.

    Product defaults (aligned with the Release 4 plan):
      - item_type = "course"
      - transaction_mode = "direct"  (course purchases are finalized at checkout)
      - is_published = False         (admin must publish explicitly)
      - unit_price = None            (admin picks the price)
      - slug = course.slug           (same slug for consistency with landing URL)
    """
    from database import products_collection
    from models.common import utc_now

    # Already linked? Reuse.
    existing = await products_collection.find_one(
        {
            "organization_id": org_id,
            "item_type": "course",
            "metadata.course_id": course.id,
        },
        {"_id": 0},
    )
    if existing:
        return existing

    # v5.8 / Onda 9.L — Course creation creates a Product row; same catalog
    # quota gate as POST /products. Only enforced when we're actually about
    # to insert a NEW product (the early-return above for existing products
    # is intentionally before this check).
    from services.module_access import enforce_count_quota
    current_count = await products_collection.count_documents({"organization_id": org_id})
    await enforce_count_quota(
        org_id, "product_catalog", "products",
        current_count=current_count,
        message_template=(
            "Hai raggiunto il limite di {limit} prodotti a catalogo del tuo piano. "
            "Aggiorna il piano per pubblicare altri corsi."
        ),
        hard_abuse_cap=10000,
    )

    now = utc_now()
    product_doc = {
        "id": generate_id(),
        "organization_id": org_id,
        "name": course.title,
        "description": course.description,
        "slug": course.slug,
        "item_type": "course",
        "price_mode": "fixed",
        "transaction_mode": "direct",
        "currency": "EUR",
        "unit_price": None,
        "is_active": True,
        "is_published": False,
        "stock_quantity": None,          # courses are unlimited licenses
        "store_ids": [],
        "image_url": course.cover_image_url,
        "metadata": {
            "course_id": course.id,
            "cover_image_url": course.cover_image_url,
            "long_description": course.long_description,
        },
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    await products_collection.insert_one(product_doc)
    product_doc.pop("_id", None)
    return product_doc


@router.post("", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
async def create_course(
    data: CourseCreate,
    current_user: dict = Depends(get_verified_user),
):
    """Create a new course + auto-create the paired Product(item_type='course').

    The Product is created unpublished (admin must publish from the
    Sales card) with default `transaction_mode='direct'` and no price.
    Slug uniqueness is enforced on both the Course and the Product —
    they share the slug for consistency with the landing URL.
    """
    _require_admin(current_user)
    org_id = current_user["organization_id"]

    if data.access_policy == CourseAccessPolicy.EXPIRING and not data.access_expiry_days:
        raise HTTPException(
            status_code=400,
            detail="access_expiry_days is required when access_policy='expiring'",
        )

    if not await course_repository.check_slug_available(org_id, data.slug):
        raise HTTPException(
            status_code=409,
            detail=f"A course with slug '{data.slug}' already exists",
        )

    course = await course_repository.create(org_id, data)

    # Auto-create the paired Product. Best-effort: if the write fails we
    # log and return the course anyway — the admin can recover from the
    # Sales card which fetches-or-creates on demand (see /product below).
    try:
        await _ensure_linked_product(org_id, course)
    except Exception as exc:
        logger.warning(
            "courses: auto-create Product failed for course=%s: %s",
            course.id, exc,
        )

    return CourseResponse(**course.model_dump())


@router.get("/{course_id}/product")
async def get_linked_product(
    course_id: str,
    current_user: dict = Depends(get_verified_user),
):
    """Return the Product(item_type='course') linked to this Course.

    Fetch-or-create semantics: courses created before this endpoint
    existed (or whose auto-create failed) get their Product minted here
    on first read. This keeps the Sales card always populated.
    """
    org_id = current_user["organization_id"]
    course = await course_repository.find_by_id(course_id, org_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    product = await _ensure_linked_product(org_id, course)
    return product


class ProductUpdatePayload(BaseModel):
    """Subset of Product fields the Sales card can edit. Narrowly scoped
    so the admin can't accidentally switch item_type or break the
    course_id link."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    slug: Optional[str] = Field(default=None, min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=2000)
    unit_price: Optional[float] = Field(default=None, ge=0)
    currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    transaction_mode: Optional[str] = Field(default=None)  # request|direct|approval
    is_published: Optional[bool] = None
    store_ids: Optional[List[str]] = None
    image_url: Optional[str] = Field(default=None, max_length=2048)


@router.patch("/{course_id}/product")
async def update_linked_product(
    course_id: str,
    payload: ProductUpdatePayload,
    current_user: dict = Depends(get_verified_user),
):
    """Update the Sales-level fields of the paired Product.

    Scoped so the admin UI never touches item_type / metadata.course_id
    (those are immutable identity of the link). `slug` changes are
    synchronized with the Course slug — keep the landing URL pattern
    consistent across both entities.
    """
    _require_admin(current_user)
    org_id = current_user["organization_id"]

    course = await course_repository.find_by_id(course_id, org_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    from database import products_collection
    from models.common import utc_now

    # Ensure the Product exists (idempotent; creates if missing).
    product = await _ensure_linked_product(org_id, course)

    updates = payload.model_dump(exclude_none=True)
    if not updates:
        return product

    if "transaction_mode" in updates and updates["transaction_mode"] not in (
        "request", "direct", "approval",
    ):
        raise HTTPException(
            status_code=400,
            detail="transaction_mode must be one of request|direct|approval",
        )

    # Slug sync: when the admin renames the course-side slug via this
    # endpoint, propagate to the Course row too (landing URL matches).
    if "slug" in updates and updates["slug"] != course.slug:
        if not await course_repository.check_slug_available(
            org_id, updates["slug"], exclude_course_id=course_id,
        ):
            raise HTTPException(
                status_code=409,
                detail=f"Slug '{updates['slug']}' already in use",
            )
        await course_repository.update(course_id, org_id, {"slug": updates["slug"]})

    updates["updated_at"] = utc_now().isoformat()
    await products_collection.update_one(
        {"id": product["id"], "organization_id": org_id},
        {"$set": updates},
    )
    fresh = await products_collection.find_one(
        {"id": product["id"], "organization_id": org_id}, {"_id": 0},
    )
    return fresh


@router.get("/{course_id}", response_model=CourseResponse)
async def get_course(
    course_id: str,
    current_user: dict = Depends(get_verified_user),
):
    org_id = current_user["organization_id"]
    course = await course_repository.find_by_id(course_id, org_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return CourseResponse(**course.model_dump())


@router.patch("/{course_id}", response_model=CourseResponse)
async def update_course(
    course_id: str,
    data: CourseUpdate,
    current_user: dict = Depends(get_verified_user),
):
    _require_admin(current_user)
    org_id = current_user["organization_id"]

    # Ensure the course exists for this org before touching anything.
    existing = await course_repository.find_by_id(course_id, org_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Course not found")

    updates = data.model_dump(exclude_none=True)

    # Slug change: re-validate uniqueness (excluding ourselves).
    if "slug" in updates and updates["slug"] != existing.slug:
        if not await course_repository.check_slug_available(
            org_id, updates["slug"], exclude_course_id=course_id
        ):
            raise HTTPException(
                status_code=409,
                detail=f"A course with slug '{updates['slug']}' already exists",
            )

    # Policy change: when switching to EXPIRING, require expiry days.
    new_policy = updates.get("access_policy", existing.access_policy)
    new_expiry = updates.get("access_expiry_days", existing.access_expiry_days)
    if new_policy == CourseAccessPolicy.EXPIRING and not new_expiry:
        raise HTTPException(
            status_code=400,
            detail="access_expiry_days is required when access_policy='expiring'",
        )

    # Enum → string for $set.
    if "access_policy" in updates:
        updates["access_policy"] = (
            updates["access_policy"].value
            if hasattr(updates["access_policy"], "value")
            else updates["access_policy"]
        )

    updated = await course_repository.update(course_id, org_id, updates)
    if not updated:
        raise HTTPException(status_code=404, detail="Course not found")
    return CourseResponse(**updated.model_dump())


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(
    course_id: str,
    current_user: dict = Depends(get_verified_user),
):
    """Soft-delete (is_active=False). Refuses to soft-delete when the
    course is referenced by an active Product (prevents orphaning a
    listing that customers might purchase). Hard delete is not exposed:
    merchants can keep a retired course around without harm.
    """
    _require_admin(current_user)
    org_id = current_user["organization_id"]

    existing = await course_repository.find_by_id(course_id, org_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Course not found")

    # Integrity check: refuse if still referenced by an active Product.
    referencing = await products_collection.find_one(
        {
            "organization_id": org_id,
            "item_type": "course",
            "is_active": True,
            "metadata.course_id": course_id,
        },
        {"_id": 0, "id": 1, "name": 1},
    )
    if referencing:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Course is linked to active product '{referencing.get('name')}'. "
                "Unlink or deactivate that product first."
            ),
        )

    ok = await course_repository.deactivate(course_id, org_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Course not found")


# ── Nested: modules ─────────────────────────────────────────────────────────

class ModuleCreatePayload(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)


class ModuleUpdatePayload(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)
    order: Optional[int] = Field(default=None, ge=0)


async def _load_course_or_404(course_id: str, org_id: str):
    """Helper to DRY the common fetch-or-404 dance for nested endpoints."""
    course = await course_repository.find_by_id(course_id, org_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


def _find_module_index(course, mod_id: str) -> int:
    """Locate a module by id inside course.modules or raise 404."""
    for i, m in enumerate(course.modules):
        if m.id == mod_id:
            return i
    raise HTTPException(status_code=404, detail="Module not found")


def _find_lesson_index(module_obj, lesson_id: str) -> int:
    for i, l in enumerate(module_obj.lessons):
        if l.id == lesson_id:
            return i
    raise HTTPException(status_code=404, detail="Lesson not found")


@router.post("/{course_id}/modules", response_model=CourseResponse, status_code=201)
async def add_module(
    course_id: str,
    payload: ModuleCreatePayload,
    current_user: dict = Depends(get_verified_user),
):
    _require_admin(current_user)
    org_id = current_user["organization_id"]
    course = await _load_course_or_404(course_id, org_id)

    next_order = max((m.order for m in course.modules), default=-1) + 1
    new_module = CourseModule(
        id=generate_id(),
        order=next_order,
        title=payload.title,
        description=payload.description,
        lessons=[],
    )
    modules_as_dicts = [m.model_dump() for m in course.modules] + [new_module.model_dump()]

    updated = await course_repository.update_modules(course_id, org_id, modules_as_dicts)
    if not updated:
        raise HTTPException(status_code=404, detail="Course not found")
    return CourseResponse(**updated.model_dump())


@router.patch("/{course_id}/modules/{mod_id}", response_model=CourseResponse)
async def update_module(
    course_id: str,
    mod_id: str,
    payload: ModuleUpdatePayload,
    current_user: dict = Depends(get_verified_user),
):
    _require_admin(current_user)
    org_id = current_user["organization_id"]
    course = await _load_course_or_404(course_id, org_id)

    idx = _find_module_index(course, mod_id)
    target = course.modules[idx]
    updates = payload.model_dump(exclude_none=True)

    for k, v in updates.items():
        setattr(target, k, v)

    # If `order` changed, re-sort the list so the response reflects the
    # new order (admin UI can rely on position = order index).
    modules = list(course.modules)
    if "order" in updates:
        modules.sort(key=lambda m: m.order)

    modules_as_dicts = [m.model_dump() for m in modules]
    updated = await course_repository.update_modules(course_id, org_id, modules_as_dicts)
    if not updated:
        raise HTTPException(status_code=404, detail="Course not found")
    return CourseResponse(**updated.model_dump())


@router.delete("/{course_id}/modules/{mod_id}", response_model=CourseResponse)
async def delete_module(
    course_id: str,
    mod_id: str,
    current_user: dict = Depends(get_verified_user),
):
    _require_admin(current_user)
    org_id = current_user["organization_id"]
    course = await _load_course_or_404(course_id, org_id)

    idx = _find_module_index(course, mod_id)
    modules = [m for i, m in enumerate(course.modules) if i != idx]
    # Re-pack orders 0..N-1 so the client doesn't have to worry about gaps.
    for i, m in enumerate(modules):
        m.order = i

    modules_as_dicts = [m.model_dump() for m in modules]
    updated = await course_repository.update_modules(course_id, org_id, modules_as_dicts)
    if not updated:
        raise HTTPException(status_code=404, detail="Course not found")
    return CourseResponse(**updated.model_dump())


# ── Nested: lessons ─────────────────────────────────────────────────────────

class LessonCreatePayload(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)
    duration_seconds: int = Field(default=0, ge=0)
    bunny_video_guid: Optional[str] = Field(default=None, max_length=64)
    # Multi-library Step 2: which Bunny library hosts this video.
    # None = use org default at playback time. Validated against
    # the org's bunny_libraries on save.
    bunny_library_id: Optional[str] = Field(default=None, max_length=32)
    is_preview: bool = False
    resources: List[CourseResource] = Field(default_factory=list)


class LessonUpdatePayload(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)
    duration_seconds: Optional[int] = Field(default=None, ge=0)
    bunny_video_guid: Optional[str] = Field(default=None, max_length=64)
    bunny_library_id: Optional[str] = Field(default=None, max_length=32)
    is_preview: Optional[bool] = None
    order: Optional[int] = Field(default=None, ge=0)
    resources: Optional[List[CourseResource]] = None


async def _validate_lesson_library_ref(
    org_id: str, library_id: Optional[str],
) -> None:
    """Verify the lesson's bunny_library_id matches a library on the org.

    Multi-library Step 2 helper. Empty/None is always valid (resolver
    falls back to default at playback). A non-empty value MUST match
    one of `org.integrations.bunny_libraries[*].id`. Raises 400 with
    a friendly message when the reference is dangling.

    Pulled out of the route handlers because both add_lesson and
    update_lesson need the same check, and the legacy `bunny` field
    (singular) is NOT a valid target for explicit references — only
    entries in `bunny_libraries` are.
    """
    if not library_id:
        return  # None/empty: fall through to default at resolve time
    from repositories import organization_repository
    org_doc = await organization_repository.find_by_id(org_id)
    libs = ((org_doc or {}).get("integrations") or {}).get("bunny_libraries") or []
    if not any(lib.get("id") == library_id for lib in libs):
        raise HTTPException(
            status_code=400,
            detail=(
                f"bunny_library_id '{library_id}' non corrisponde a nessuna "
                "libreria Bunny configurata su questa organizzazione."
            ),
        )


@router.post(
    "/{course_id}/modules/{mod_id}/lessons",
    response_model=CourseResponse,
    status_code=201,
)
async def add_lesson(
    course_id: str,
    mod_id: str,
    payload: LessonCreatePayload,
    current_user: dict = Depends(get_verified_user),
):
    _require_admin(current_user)
    org_id = current_user["organization_id"]
    course = await _load_course_or_404(course_id, org_id)

    idx = _find_module_index(course, mod_id)
    target = course.modules[idx]

    # Multi-library: validate the bunny_library_id against the org's
    # configured libraries before persisting. None = OK (default fallback).
    await _validate_lesson_library_ref(org_id, payload.bunny_library_id)

    next_order = max((l.order for l in target.lessons), default=-1) + 1
    new_lesson = Lesson(
        id=generate_id(),
        order=next_order,
        title=payload.title,
        description=payload.description,
        duration_seconds=payload.duration_seconds,
        bunny_video_guid=payload.bunny_video_guid,  # validation via Lesson validator
        bunny_library_id=payload.bunny_library_id,  # validated above
        is_preview=payload.is_preview,
        resources=payload.resources,
    )
    target.lessons.append(new_lesson)

    modules_as_dicts = [m.model_dump() for m in course.modules]
    updated = await course_repository.update_modules(course_id, org_id, modules_as_dicts)
    if not updated:
        raise HTTPException(status_code=404, detail="Course not found")
    return CourseResponse(**updated.model_dump())


@router.patch(
    "/{course_id}/modules/{mod_id}/lessons/{lesson_id}",
    response_model=CourseResponse,
)
async def update_lesson(
    course_id: str,
    mod_id: str,
    lesson_id: str,
    payload: LessonUpdatePayload,
    current_user: dict = Depends(get_verified_user),
):
    _require_admin(current_user)
    org_id = current_user["organization_id"]
    course = await _load_course_or_404(course_id, org_id)

    m_idx = _find_module_index(course, mod_id)
    target_module = course.modules[m_idx]
    l_idx = _find_lesson_index(target_module, lesson_id)
    target_lesson = target_module.lessons[l_idx]

    updates = payload.model_dump(exclude_none=True)

    # Re-validate bunny_video_guid via the Lesson model (ValueError → 400).
    if "bunny_video_guid" in updates:
        try:
            # Cheap way to trigger the validator: rebuild the lesson.
            temp = Lesson(
                id=target_lesson.id,
                order=target_lesson.order,
                title=target_lesson.title,
                bunny_video_guid=updates["bunny_video_guid"],
            )
            updates["bunny_video_guid"] = temp.bunny_video_guid
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    # Multi-library: validate the bunny_library_id against the org's
    # configured libraries when changing. Skipping when not in payload
    # leaves the existing reference untouched.
    if "bunny_library_id" in updates:
        await _validate_lesson_library_ref(org_id, updates["bunny_library_id"])

    for k, v in updates.items():
        setattr(target_lesson, k, v)

    lessons = list(target_module.lessons)
    if "order" in updates:
        lessons.sort(key=lambda l: l.order)
    target_module.lessons = lessons

    modules_as_dicts = [m.model_dump() for m in course.modules]
    updated = await course_repository.update_modules(course_id, org_id, modules_as_dicts)
    if not updated:
        raise HTTPException(status_code=404, detail="Course not found")
    return CourseResponse(**updated.model_dump())


# ── Admin: enrollments listing + revoke (Release 4 Step 8) ──────────────────
#
# Used by the CourseEditor "Iscritti" tab. The admin sees who is enrolled
# on one of their courses and can revoke access with a documented reason
# (shown in audit log + email if we add it in a future phase). Revoke is
# idempotent + best-effort at the service level (issued_course_access_service).


class RevokePayload(BaseModel):
    reason: str = Field(
        default="admin_revoked", min_length=1, max_length=500,
        description="Human-readable reason stored on the enrollment and "
                    "surfaced in audit logs. Never shown to the customer.",
    )


@router.get("/{course_id}/enrollments")
async def list_course_enrollments(
    course_id: str,
    include_revoked: bool = False,
    limit: int = 500,
    current_user: dict = Depends(get_verified_user),
):
    """Admin view of everyone enrolled in a course.

    Scoped by org_id — admin of org A cannot see enrollments of org B.
    Projects a lean shape (no access_token, no progress dict details)
    so the table stays light and the token never leaks into admin
    responses. For now access_token is stripped out defensively, even
    though admin are privileged — principle of least exposure.
    """
    org_id = current_user["organization_id"]

    # Ensure the course belongs to this org (404 semantics identical to
    # the other admin endpoints).
    course = await course_repository.find_by_id(course_id, org_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    from database import (
        issued_course_accesses_collection,
        customer_accounts_collection,
    )
    query: dict = {"organization_id": org_id, "course_id": course_id}
    if not include_revoked:
        query["revoked_at"] = None

    cursor = issued_course_accesses_collection.find(
        query,
        {
            "_id": 0,
            "id": 1, "order_id": 1, "customer_account_id": 1, "customer_id": 1,
            "course_title_snapshot": 1,
            "enrolled_at": 1, "expires_at": 1, "last_accessed_at": 1,
            "revoked_at": 1, "revoked_reason": 1, "progress": 1,
        },
    ).sort("enrolled_at", -1).limit(limit)
    enrollments = await cursor.to_list(limit)

    # Bulk-fetch customer accounts to attach email/name. Keeps the
    # admin table readable without N+1 queries.
    account_ids = list({e["customer_account_id"] for e in enrollments if e.get("customer_account_id")})
    accounts_map: dict[str, dict] = {}
    if account_ids:
        async for a in customer_accounts_collection.find(
            {"id": {"$in": account_ids}},
            {"_id": 0, "id": 1, "email": 1, "name": 1},
        ):
            accounts_map[a["id"]] = a

    # Lesson count per course for computing progress percentage on the fly.
    total_lessons = sum(
        len(m.lessons or []) for m in (course.modules or [])
    )

    items = []
    for e in enrollments:
        progress = e.get("progress") or {}
        completed_count = sum(1 for v in progress.values() if v.get("completed_at"))
        percentage = (
            int(round(100 * completed_count / total_lessons)) if total_lessons else 0
        )
        account = accounts_map.get(e.get("customer_account_id")) or {}
        items.append({
            "id": e.get("id"),
            "order_id": e.get("order_id"),
            "customer_account_id": e.get("customer_account_id"),
            "customer_email": account.get("email"),
            "customer_name": account.get("name"),
            "enrolled_at": e.get("enrolled_at"),
            "expires_at": e.get("expires_at"),
            "last_accessed_at": e.get("last_accessed_at"),
            "revoked_at": e.get("revoked_at"),
            "revoked_reason": e.get("revoked_reason"),
            "progress_stats": {
                "lessons_completed": completed_count,
                "total_lessons": total_lessons,
                "percentage": percentage,
            },
        })

    return {"enrollments": items, "total": len(items)}


@router.post("/enrollments/{enrollment_id}/revoke")
async def revoke_enrollment(
    enrollment_id: str,
    payload: RevokePayload,
    current_user: dict = Depends(get_verified_user),
):
    """Revoke a single enrollment (e.g. after a manual refund).

    Admin-only. Scoped by org_id. Idempotent: revoking an already-revoked
    enrollment returns the existing state without re-setting the timestamp.
    Once revoked, the customer player endpoint responds 403 on the next
    request and the enrollment drops from "My courses".
    """
    _require_admin(current_user)
    org_id = current_user["organization_id"]

    from database import issued_course_accesses_collection
    from models.common import utc_now

    enr = await issued_course_accesses_collection.find_one(
        {"id": enrollment_id, "organization_id": org_id},
        {"_id": 0},
    )
    if not enr:
        raise HTTPException(status_code=404, detail="Enrollment not found")

    if enr.get("revoked_at"):
        # Already revoked — return the existing state (idempotent).
        return {
            "id": enr["id"],
            "revoked_at": enr.get("revoked_at"),
            "revoked_reason": enr.get("revoked_reason"),
            "already_revoked": True,
        }

    now = utc_now()
    await issued_course_accesses_collection.update_one(
        {"id": enrollment_id, "organization_id": org_id},
        {"$set": {
            "revoked_at": now,
            "revoked_reason": payload.reason,
            "updated_at": now,
        }},
    )
    logger.info(
        "courses: enrollment %s revoked by admin %s reason=%r",
        enrollment_id, current_user.get("user_id"), payload.reason,
    )
    return {
        "id": enrollment_id,
        "revoked_at": now.isoformat(),
        "revoked_reason": payload.reason,
        "already_revoked": False,
    }


@router.delete(
    "/{course_id}/modules/{mod_id}/lessons/{lesson_id}",
    response_model=CourseResponse,
)
async def delete_lesson(
    course_id: str,
    mod_id: str,
    lesson_id: str,
    current_user: dict = Depends(get_verified_user),
):
    _require_admin(current_user)
    org_id = current_user["organization_id"]
    course = await _load_course_or_404(course_id, org_id)

    m_idx = _find_module_index(course, mod_id)
    target_module = course.modules[m_idx]
    l_idx = _find_lesson_index(target_module, lesson_id)

    remaining = [l for i, l in enumerate(target_module.lessons) if i != l_idx]
    for i, l in enumerate(remaining):
        l.order = i
    target_module.lessons = remaining

    modules_as_dicts = [m.model_dump() for m in course.modules]
    updated = await course_repository.update_modules(course_id, org_id, modules_as_dicts)
    if not updated:
        raise HTTPException(status_code=404, detail="Course not found")
    return CourseResponse(**updated.model_dump())
