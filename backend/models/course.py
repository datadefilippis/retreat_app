"""
Course — content entity for video courses (item_type="course").

Release 4 (Courses) Step 1. The Course is the content side of the
listing/content pair: a Product(item_type="course") points at a Course
via metadata.course_id, exactly the same pattern used by:

  - Event:    Product(event_ticket) → Occurrence
  - Service:  Product(service)      → ServiceOption / Availability
  - Rental:   Product(rental)       → rental_config (inline)
  - Digital:  Product(digital)      → DigitalAsset (file URL + policy)
  - Course:   Product(course)       → Course (modules + lessons)  ← here

Hierarchy: Course → CourseModule → Lesson. CourseModule (instead of plain
"Module") avoids name collision with the existing OrganizationModule in
models/module.py.

Each Lesson holds a Bunny Stream video GUID. Bunny remains the only host
for video files; AFianco never uploads or stores videos. The signed
embed URL is generated server-side at play time (see services/bunny_service.py
in Step 7).

Customer access is tracked separately by IssuedCourseAccess (see
issued_course_access.py) — emitted at order confirm.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .common import generate_id, utc_now


# ── Access policy ────────────────────────────────────────────────────────────

class CourseAccessPolicy(str, Enum):
    """How long an enrollment grants access after purchase."""
    LIFETIME = "lifetime"        # access never expires
    EXPIRING = "expiring"        # access_expiry_days from enrollment date


# ── Lesson resource (downloadable companion file or external link) ──────────

class CourseResource(BaseModel):
    """A downloadable file or external link attached to a lesson.

    Purposefully minimal in MVP: just a label + URL. The URL is
    typically a public asset hosted by the merchant (PDF, audio,
    external link). Future evolutions can add per-resource access
    control without breaking the schema (extra="ignore").
    """

    model_config = ConfigDict(extra="ignore")

    label: str = Field(min_length=1, max_length=200)
    url: str = Field(min_length=1, max_length=2048)


# ── Lesson (atomic content unit inside a module) ─────────────────────────────

class Lesson(BaseModel):
    """A single video lesson inside a CourseModule."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)
    order: int = Field(ge=0)                          # 0-indexed sort key within module
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)
    duration_seconds: int = Field(default=0, ge=0)    # 0 = unknown / placeholder
    bunny_video_guid: Optional[str] = Field(default=None, max_length=64)
    # Multi-library support (Step 2): which Bunny library hosts this
    # video. References `BunnyLibrary.id` (AFianco-side stable ID, NOT
    # Bunny's library_id). When None, the resolver falls back to the
    # org's default library at playback time. Validated against the
    # org's bunny_libraries on save (in routers/courses.py).
    bunny_library_id: Optional[str] = Field(default=None, max_length=32)
    resources: List[CourseResource] = Field(default_factory=list)
    # Future: free preview lessons (visible without enrollment).
    # Currently not surfaced in the public landing.
    is_preview: bool = False

    @field_validator("bunny_video_guid", mode="before")
    @classmethod
    def _validate_bunny_guid(cls, v):
        """Empty string → None. Validate UUID-shape if provided.

        Bunny video IDs look like "f0a4b6e7-1234-4abc-9def-abcdef012345".
        We normalize empties to None so the lesson can be saved as a
        placeholder before the merchant pastes the real GUID.
        """
        if v is None:
            return None
        v = str(v).strip()
        if v == "":
            return None
        # Loose UUID check: 36 chars, dashes at the right positions.
        if len(v) != 36 or v[8] != "-" or v[13] != "-" or v[18] != "-" or v[23] != "-":
            raise ValueError("bunny_video_guid must be a UUID string (36 chars)")
        return v


# ── Course module (group of lessons) ─────────────────────────────────────────

class CourseModule(BaseModel):
    """A group of lessons inside a Course. Named CourseModule to avoid
    clashing with OrganizationModule in models/module.py.
    """

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)
    order: int = Field(ge=0)
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)
    lessons: List[Lesson] = Field(default_factory=list)


# ── Course (full document) ───────────────────────────────────────────────────

class CourseBase(BaseModel):
    """Shared fields between Create / Update / persisted Course."""

    model_config = ConfigDict(extra="ignore")

    title: str = Field(min_length=1, max_length=255)
    # URL slug used in /co/:org_slug/:course_slug. Unique per org.
    slug: str = Field(min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=2000)
    long_description: Optional[str] = Field(default=None, max_length=20000)
    cover_image_url: Optional[str] = Field(default=None, max_length=2048)
    instructor_name: Optional[str] = Field(default=None, max_length=255)
    instructor_bio: Optional[str] = Field(default=None, max_length=4000)
    access_policy: CourseAccessPolicy = CourseAccessPolicy.LIFETIME
    # Required when access_policy = EXPIRING. Validated below.
    access_expiry_days: Optional[int] = Field(default=None, ge=1, le=3650)
    # Lifecycle: is_active=False hides the Course from new product
    # bindings (existing enrollments still play — content is immutable
    # to the customer once issued).
    is_active: bool = True

    @field_validator("slug", mode="before")
    @classmethod
    def _normalize_slug(cls, v):
        """Lowercase + strip. Validate basic slug shape."""
        if v is None:
            return v
        v = str(v).strip().lower()
        if not v:
            raise ValueError("slug cannot be empty")
        # Basic shape: alphanumeric + dashes only. Mirrors Organization.public_slug rules.
        for ch in v:
            if not (ch.isalnum() or ch == "-"):
                raise ValueError("slug may only contain lowercase letters, digits and dashes")
        if v.startswith("-") or v.endswith("-"):
            raise ValueError("slug cannot start or end with a dash")
        return v


class CourseCreate(CourseBase):
    """Payload for POST /api/courses. Modules added separately via
    nested endpoints (see Step 2)."""
    pass


class CourseUpdate(BaseModel):
    """PATCH /api/courses/{id}: all fields optional."""

    model_config = ConfigDict(extra="ignore")

    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    slug: Optional[str] = Field(default=None, min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=2000)
    long_description: Optional[str] = Field(default=None, max_length=20000)
    cover_image_url: Optional[str] = Field(default=None, max_length=2048)
    instructor_name: Optional[str] = Field(default=None, max_length=255)
    instructor_bio: Optional[str] = Field(default=None, max_length=4000)
    access_policy: Optional[CourseAccessPolicy] = None
    access_expiry_days: Optional[int] = Field(default=None, ge=1, le=3650)
    is_active: Optional[bool] = None


class Course(CourseBase):
    """Full Course document as stored in MongoDB."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)
    organization_id: str
    modules: List[CourseModule] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    def total_lessons(self) -> int:
        return sum(len(m.lessons) for m in self.modules)

    def total_duration_seconds(self) -> int:
        return sum(l.duration_seconds for m in self.modules for l in m.lessons)


class CourseResponse(CourseBase):
    """Admin-facing response shape."""

    id: str
    organization_id: str
    modules: List[CourseModule] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
