from typing import Optional, List
from datetime import datetime
from database import digests_collection
from models.digest import Digest


def doc_to_digest(doc: dict) -> Digest:
    """Convert a raw MongoDB document to a Digest model."""
    created_at = doc["created_at"]
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at)
    return Digest(
        id=doc["id"],
        organization_id=doc["organization_id"],
        digest_type=doc["digest_type"],
        content=doc["content"],
        period_start=doc["period_start"],
        period_end=doc["period_end"],
        kpis_summary=doc.get("kpis_summary", {}),
        alerts_count=doc.get("alerts_count", 0),
        model_version=doc.get("model_version"),
        created_at=created_at,
    )


async def create(digest: Digest) -> dict:
    """Create a new digest."""
    doc = digest.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    await digests_collection.insert_one(doc)
    doc.pop("_id", None)
    return doc


async def find_by_id(digest_id: str, org_id: str) -> Optional[dict]:
    """Find digest by ID."""
    return await digests_collection.find_one(
        {"id": digest_id, "organization_id": org_id},
        {"_id": 0},
    )


async def find_by_org(
    org_id: str,
    digest_type: Optional[str] = None,
    limit: int = 20,
    *,
    include_pdf: bool = False,
) -> List[dict]:
    """Find digests for an organization, optionally filtered by type.

    Wave 14 perf (2026-05-16) — by default the projection now EXCLUDES
    ``pdf_b64`` from every doc. Pre-fix the list endpoint transferred
    ~300 KB of base64-encoded PDF PER digest, so a 20-doc list response
    was 6 MB even though the frontend never renders the PDF in the list
    view (it calls ``GET /digests/{id}/pdf`` only when the user clicks
    "Scarica PDF"). The result was 3-5 seconds of TTFB on the Digest tab
    over a typical SOHO connection.

    Callers that genuinely need the PDF bytes embedded should set
    ``include_pdf=True``; everyone else gets the lightweight shape
    (text fields + kpis_summary + sections, ~6 KB per doc).
    """
    query = {"organization_id": org_id}
    if digest_type:
        query["digest_type"] = digest_type
    projection: dict = {"_id": 0}
    if not include_pdf:
        projection["pdf_b64"] = 0
    cursor = (
        digests_collection.find(query, projection)
        .sort("created_at", -1)
        .limit(limit)
    )
    return await cursor.to_list(limit)


async def find_latest(
    org_id: str,
    digest_type: str = "weekly",
    *,
    period_start: Optional[str] = None,
    period_end: Optional[str] = None,
    include_pdf: bool = False,
) -> Optional[dict]:
    """Find the most recent digest of a given type.

    Wave 13.7 — optional ``period_start`` / ``period_end`` arguments
    let the caller scope the lookup to a SPECIFIC window. Without them
    the function behaves exactly as before (most recent of digest_type
    regardless of window). With them, the dedup check in
    ``background_service`` and the featured-digest selector in the UI
    can correctly distinguish two same-type digests covering DIFFERENT
    windows (e.g. a monthly digest for Mar 1-31 vs Apr 1-30).

    Pre-Wave-13.7 the function matched only on (org_id, digest_type),
    which conflated cron-driven recurring digests with manually-
    triggered ones for arbitrary windows. Backward compat preserved
    because both new kwargs default to None and short-circuit when
    not supplied.
    """
    query = {"organization_id": org_id, "digest_type": digest_type}
    if period_start is not None:
        query["period_start"] = period_start
    if period_end is not None:
        query["period_end"] = period_end
    # Wave 14 perf — exclude pdf_b64 by default (300 KB / doc). Callers
    # that need the bytes embedded set include_pdf=True; the dedicated
    # ``get_pdf(id)`` function is the canonical way.
    projection: dict = {"_id": 0}
    if not include_pdf:
        projection["pdf_b64"] = 0
    cursor = (
        digests_collection.find(query, projection)
        .sort("created_at", -1)
        .limit(1)
    )
    results = await cursor.to_list(1)
    return results[0] if results else None


async def delete(digest_id: str, org_id: str) -> bool:
    """Delete digest by ID."""
    result = await digests_collection.delete_one(
        {"id": digest_id, "organization_id": org_id}
    )
    return result.deleted_count > 0


# ── v2: PDF storage ─────────────────────────────────────────────────────────

async def store_pdf(digest_id: str, org_id: str, pdf_bytes: bytes) -> bool:
    """Store PDF bytes for a digest (as base64 in the digest document)."""
    import base64
    encoded = base64.b64encode(pdf_bytes).decode("ascii")
    result = await digests_collection.update_one(
        {"id": digest_id, "organization_id": org_id},
        {"$set": {"pdf_b64": encoded}},
    )
    return result.modified_count > 0


async def get_pdf(digest_id: str, org_id: str) -> Optional[bytes]:
    """Retrieve PDF bytes for a digest."""
    import base64
    doc = await digests_collection.find_one(
        {"id": digest_id, "organization_id": org_id},
        {"_id": 0, "pdf_b64": 1},
    )
    if not doc or not doc.get("pdf_b64"):
        return None
    return base64.b64decode(doc["pdf_b64"])
