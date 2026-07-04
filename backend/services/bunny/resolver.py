"""
Bunny library resolver — single source of truth for "given a lesson and
its org, which Bunny config should sign the playback URL?".

Pure function, no I/O. Centralizes the priority chain so every consumer
(customer playback hot path, admin previews, future debug tooling)
makes the same decision. Adding a new fallback layer is a single
change here.

Priority chain (top wins):

  1. Lesson explicitly references a library_id that exists in
     `org.integrations.bunny_libraries` → use it. The lesson author
     has been explicit; honor it.

  2. Lesson references a library_id that does NOT exist (orphan
     reference, e.g. the library was deleted) → fall through to
     priority 3. We do NOT return None here — better to play the
     video from the org default than to break playback because of
     a stale reference.

  3. The org has a library marked `is_default=true` in
     `bunny_libraries` → use it. Common case for orgs that have
     migrated to multi-library.

  4. The org has at least one library in `bunny_libraries` but none
     marked default → use the first one. Defensive: shouldn't happen
     because the admin endpoints maintain the "exactly one default"
     invariant, but legacy data or partial migrations could land us
     here.

  5. Fall back to the legacy single-library `integrations.bunny`
     field. This keeps orgs that haven't migrated working unchanged.

  6. Nothing matches → return None. The caller (typically the play-url
     endpoint in customer_portal.py) is expected to surface a 503
     "bunny_not_configured" error to the customer.

The function is intentionally tolerant of partially-formed inputs
(None lesson, None org, missing keys, etc.) — never raises. That
makes it safe to call from middleware and from tests.
"""

from typing import Any, Dict, Optional


def resolve_library_config(
    lesson: Optional[Dict[str, Any]],
    org: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Pick the Bunny config dict for a lesson.

    Args:
        lesson: lesson document (the one with `bunny_video_guid` and
                optionally `bunny_library_id`). May be None when called
                in non-playback contexts (e.g. admin "test default
                library" flows).
        org:    organization document with the integrations bag.

    Returns:
        The chosen Bunny config dict (compatible with
        `signer.generate_signed_embed_url` and
        `verifier.verify_credentials`), or None when no config is
        configured at any level.
    """
    if not org:
        return None

    integrations = (org.get("integrations") or {})
    libraries = integrations.get("bunny_libraries") or []

    # 1. Explicit lesson reference, when it points to a real library.
    explicit_id: Optional[str] = None
    if lesson:
        explicit_id = lesson.get("bunny_library_id")
    if explicit_id:
        for lib in libraries:
            if lib.get("id") == explicit_id:
                return lib
        # 2. Orphan reference — fall through to default rather than
        # breaking playback. The admin will see broken-reference
        # warnings elsewhere (Step 5 DELETE protection) and can fix.

    # 3. Default library
    for lib in libraries:
        if lib.get("is_default"):
            return lib

    # 4. First library when no default is marked
    if libraries:
        return libraries[0]

    # 5. Legacy single-library fallback
    legacy = integrations.get("bunny")
    if legacy:
        return legacy

    # 6. Nothing
    return None
