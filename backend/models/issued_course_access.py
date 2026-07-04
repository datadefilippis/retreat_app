"""
IssuedCourseAccess — one fulfilled course enrollment.

Release 4 (Courses) Step 1. Analog of IssuedDownload (digital) /
IssuedReservation (rental) / IssuedBooking (service) / IssuedTicket
(event_ticket) for item_type="course".

One IssuedCourseAccess row per (order_id, order_line_index). A single
order line with quantity > 1 still produces ONE enrollment — a course is
licensed nominatively per customer, not per seat. (Future evolution:
"gift seats" feature could spawn multiple enrollments.)

Status lifecycle (implicit, derived from timestamp fields):
  active     — revoked_at IS NULL AND (expires_at IS NULL OR expires_at > now)
  expired    — expires_at <= now
  revoked    — revoked_at IS NOT NULL  (manual admin revoke or order cancel)

Uniqueness:
  - access_token: globally unique (URL-safe, secrets.token_urlsafe(24))
  - (order_id, order_line_index): unique compound — confirm_order retries
    cannot duplicate the enrollment.

Per-customer indexing:
  - (customer_account_id, organization_id) for "my courses" list query.

Anti-link-sharing: the access_token is used only to identify the
enrollment internally. The customer-facing URL
(/account/courses/{enrollment_id}) requires a valid customer JWT — the
token alone never grants access without an authenticated session.
"""

from __future__ import annotations

from typing import Dict, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from .common import generate_id, utc_now


# ── Per-lesson progress (stored as a dict keyed by lesson_id) ────────────────

class LessonProgress(BaseModel):
    """Progress snapshot for a single lesson within an enrollment.

    `watched_seconds` is monotonically increasing (idempotent updates
    use max(existing, new)). `completed_at` is set once the customer
    explicitly marks the lesson complete OR Bunny reports the `ended`
    event — whichever fires first.
    """

    model_config = ConfigDict(extra="ignore")

    watched_seconds: int = Field(default=0, ge=0)
    completed_at: Optional[datetime] = None


# ── IssuedCourseAccess (full enrollment document) ────────────────────────────

class IssuedCourseAccessBase(BaseModel):
    """Shared fields persisted to Mongo + surfaced by APIs."""

    model_config = ConfigDict(extra="ignore")

    order_id: str
    # Position of the source OrderLine inside Order.items. Together with
    # order_id this is the idempotency key (unique compound index).
    order_line_index: int = Field(ge=0)

    # Snapshot of the course at issuance time. The customer's enrollment
    # remains stable even if the merchant later renames or reorganises
    # the course — playback always resolves the live course doc, but
    # the title shown in lists / emails uses this snapshot.
    course_id: str
    course_title_snapshot: str = Field(max_length=255)

    # Customer identity. customer_account_id is MANDATORY (unlike other
    # Issued* artifacts that can be guest-emitted): courses require a
    # logged-in customer end-to-end.
    customer_account_id: str
    customer_id: Optional[str] = None  # bridge to legacy Customer record if linked

    # Customer-visible enrollment fingerprint. URL-safe 32 chars.
    # Generated via secrets.token_urlsafe(24) at issuance.
    access_token: str = Field(min_length=10, max_length=64)

    enrolled_at: datetime
    # null = lifetime access. Otherwise computed as
    # enrolled_at + Course.access_expiry_days at issuance.
    expires_at: Optional[datetime] = None

    # Set by manual admin revoke or cancel_order. Once set, the enrollment
    # disappears from /account/courses listings and the player endpoint
    # rejects play-url requests.
    revoked_at: Optional[datetime] = None
    revoked_reason: Optional[str] = Field(default=None, max_length=500)

    # Per-lesson progress, keyed by lesson_id. Empty dict for fresh
    # enrollments. Idempotent merge updates (max() on watched_seconds,
    # set-once on completed_at).
    progress: Dict[str, LessonProgress] = Field(default_factory=dict)

    # Updated on every play-url request and progress heartbeat. Used to
    # sort the "my courses" list by recency.
    last_accessed_at: Optional[datetime] = None


class IssuedCourseAccess(IssuedCourseAccessBase):
    """Full IssuedCourseAccess document as stored in MongoDB."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)
    organization_id: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class IssuedCourseAccessResponse(IssuedCourseAccessBase):
    """Response shape for admin / customer endpoints.

    Note: customer-facing endpoints in Step 6/7 will project a leaner
    shape (no revoked_reason, no internal access_token in some
    contexts). This base response is for admin use.
    """

    id: str
    organization_id: str
    created_at: datetime
    updated_at: datetime
