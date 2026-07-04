"""
Course repository — Motor/MongoDB persistence for Course documents.

Release 4 (Courses) Step 2. Mirrors the shape of product_repository.py
to keep the codebase consistent. Org-scoped on every query; callers
extract `organization_id` from the admin JWT and pass it in.

Soft delete: `is_active=False` (pattern used across the codebase). A
hard DELETE is offered too (used by the admin router when the course
is NOT referenced by any Product), but it only runs after an explicit
integrity check in the router layer.
"""

from __future__ import annotations

from typing import List, Optional
from datetime import datetime, timezone

from database import courses_collection
from models.course import Course, CourseCreate


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def create(organization_id: str, data: CourseCreate) -> Course:
    """Insert a brand-new Course document. Caller must enforce slug
    uniqueness per-org (see check_slug_available).
    """
    course = Course(organization_id=organization_id, **data.model_dump())
    doc = course.model_dump()
    # Persist timestamps as ISO strings to match the rest of the codebase.
    doc["created_at"] = doc["created_at"].isoformat()
    doc["updated_at"] = doc["updated_at"].isoformat()
    await courses_collection.insert_one(doc)
    return course


async def find_by_id(course_id: str, organization_id: str) -> Optional[Course]:
    doc = await courses_collection.find_one(
        {"id": course_id, "organization_id": organization_id}
    )
    return Course(**doc) if doc else None


async def find_by_slug(slug: str, organization_id: str) -> Optional[Course]:
    """Lookup by org-scoped slug. Used by landing resolver (Step 3) and
    by the create/update endpoints to detect conflicts."""
    doc = await courses_collection.find_one(
        {"slug": slug, "organization_id": organization_id}
    )
    return Course(**doc) if doc else None


async def find_by_org(
    organization_id: str,
    active_only: bool = True,
    limit: int = 500,
) -> List[Course]:
    query: dict = {"organization_id": organization_id}
    if active_only:
        query["is_active"] = True
    cursor = courses_collection.find(query).sort("title", 1).limit(limit)
    return [Course(**doc) async for doc in cursor]


async def check_slug_available(
    organization_id: str,
    slug: str,
    exclude_course_id: Optional[str] = None,
) -> bool:
    """Return True when the given slug is not used by any other course of
    this org. `exclude_course_id` lets the update handler rename a course
    to the same slug without a false conflict with itself.
    """
    query: dict = {"organization_id": organization_id, "slug": slug}
    if exclude_course_id:
        query["id"] = {"$ne": exclude_course_id}
    existing = await courses_collection.find_one(query, {"_id": 0, "id": 1})
    return existing is None


async def update(
    course_id: str,
    organization_id: str,
    updates: dict,
) -> Optional[Course]:
    """Shallow $set update. Nested modules/lessons mutation has dedicated
    helpers (update_modules, add_module, etc.) to keep payloads small and
    to avoid accidental clobbering of nested state."""
    updates["updated_at"] = _now().isoformat()
    result = await courses_collection.update_one(
        {"id": course_id, "organization_id": organization_id},
        {"$set": updates},
    )
    if result.matched_count == 0:
        return None
    return await find_by_id(course_id, organization_id)


async def update_modules(
    course_id: str,
    organization_id: str,
    modules: List[dict],
) -> Optional[Course]:
    """Replace the full modules[] array. Used by module/lesson CRUD
    endpoints (they fetch → mutate → call this). Atomic single-document
    write — Mongo guarantees no partial state is ever observable.
    """
    result = await courses_collection.update_one(
        {"id": course_id, "organization_id": organization_id},
        {"$set": {"modules": modules, "updated_at": _now().isoformat()}},
    )
    if result.matched_count == 0:
        return None
    return await find_by_id(course_id, organization_id)


async def deactivate(course_id: str, organization_id: str) -> bool:
    """Soft-delete: set is_active=False. Does NOT cascade to
    IssuedCourseAccess (existing enrollments keep playing); the admin
    UI surfaces the soft state so the merchant can re-activate later.
    """
    result = await courses_collection.update_one(
        {"id": course_id, "organization_id": organization_id},
        {"$set": {"is_active": False, "updated_at": _now().isoformat()}},
    )
    return result.modified_count > 0


async def hard_delete(course_id: str, organization_id: str) -> bool:
    """Remove the document permanently. Only the router layer may call
    this, and only after confirming no Product references this course
    (via Product.metadata.course_id). Useful to let the merchant retire
    a never-sold test course without leaving a zombie row.
    """
    result = await courses_collection.delete_one(
        {"id": course_id, "organization_id": organization_id}
    )
    return result.deleted_count > 0
