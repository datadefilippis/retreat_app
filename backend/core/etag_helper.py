"""ETag helper — Sprint 3 W3.5 (Conditional GET per /embed/* hot paths).

Centralized SHA256-hex16 computation + If-None-Match comparison logic
per evitare duplicazione tra handler /init, /categories, /products.

Strategy
========
Compute ETag come SHA256-hex16 di:
  - response payload JSON-stringified canonical
  - + API version header (so bump version invalidates cache)

If client sends If-None-Match matching → 304 Not Modified (zero body).
Altrimenti 200 + ETag header set per future conditional requests.

Performance
===========
SHA256 hash su payload tipico (init ~2KB, catalog ~10KB):
  - init: ~0.01ms
  - catalog 50 prodotti: ~0.1ms
Trascurabile rispetto al DB lookup. Cache hit -> response 200ms -> 304 5ms.

Usage
=====
::

    from core.etag_helper import compute_etag, build_conditional_response

    @router.get("/init/{slug}")
    async def get_embed_init(request, response, slug):
        payload = await get_embed_init_data(slug)
        return build_conditional_response(
            request=request,
            response=response,
            payload=payload,
            max_age=300,
        )

Returns either the payload (200) or a Response with status 304.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse


def compute_etag(payload: Any, *, version_tag: str = "v1") -> str:
    """Compute a stable ETag per il payload + version.

    SHA256-hex16 (16 char hex) e' sufficiente per anti-collision practical
    (2^64 keyspace) + payload piccolo (~16 byte ETag header).

    Args:
        payload: oggetto JSON-serializable (dict, list, primitivo).
        version_tag: bumpa per breaking changes contract (es. "v1" → "v2").

    Returns:
        Stringa hex16, e.g. "8f4a3b2c1d9e5f6a"
    """
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    seed = f"{version_tag}:{canonical}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def build_conditional_response(
    *,
    request: Request,
    response: Response,
    payload: Any,
    max_age: int = 300,
    version_tag: str = "v1",
) -> Any:
    """Build response with ETag + Cache-Control, or 304 if matching.

    Args:
        request: FastAPI Request (per leggere If-None-Match header)
        response: FastAPI Response (per setting headers on 200)
        payload: dict/list/primitivo serializzabile
        max_age: TTL Cache-Control in secondi (default 300 = 5 min)
        version_tag: bumpa per invalidare cache su breaking changes

    Returns:
        - payload as-is per 200 OK (FastAPI serialize automatic)
        - JSONResponse 304 Not Modified se If-None-Match match (zero body)
    """
    etag = f'"{compute_etag(payload, version_tag=version_tag)}"'

    # Conditional GET check
    if_none_match = request.headers.get("if-none-match")
    if if_none_match and if_none_match == etag:
        # Cache hit: 304 Not Modified, no body
        return JSONResponse(
            content=None,
            status_code=status.HTTP_304_NOT_MODIFIED,
            headers={
                "ETag": etag,
                "Cache-Control": f"public, max-age={max_age}",
            },
        )

    # Cache miss: set headers su 200 response
    response.headers["ETag"] = etag
    response.headers["Cache-Control"] = f"public, max-age={max_age}"
    return payload
