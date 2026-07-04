"""
Track O Step E1.1 — Embed API versioning canonical helper.

Versioning model: integer major-only (v1, v2, v3...). NO semver semantic
piu' fine perche':
  - Embed SDK gira nei browser dei merchant — vogliamo signal
    chiarissimo "breaking" vs "additive"
  - Additive changes (new optional field nel response) NON bumpano
    version: rimangono backward-compat su qualsiasi versione
  - Breaking changes (rename field, remove field, change semantics)
    bumpano major + mantieni vecchia versione 6+ mesi minimum
  - Patch/minor distinction non utile lato client (browser cache busting
    e' gestito differently via ETag + Cache-Control)

Protocol
========

Request:
  Client manda header:
    X-API-Version: 1
  Se assente → server assume current version (latest stable).
  Se invalido (non-numeric) o non supportato (es. "999") → 400 con
  detail JSON {code, message, supported_versions, current}.

Response:
  Server SEMPRE manda header:
    X-API-Version: <int>
  Indica quale contratto e' stato applicato. Client SDK puo' verificare
  che il server abbia onorato la versione richiesta.

Body:
  NO version field nel body — il header e' la fonte di verita'.
  Aggiungere body field creerebbe doppia source of truth + ETag noise.

Backward compat policy
======================

Quando bumpiamo a v2:
  - Aggiungiamo "2" a EMBED_API_SUPPORTED_VERSIONS
  - Bumpiamo EMBED_API_CURRENT_VERSION = 2
  - Manteniamo support per "1" per minimum 6 mesi (3 cicli SDK release)
  - Dopo 6 mesi: remove "1" da supported set; embed SDK old riceve 400
    "Versione 1 deprecata, upgrade SDK"
  - Documentiamo deprecation timeline in CHANGELOG + integration guide

Anti-pattern catturati
======================

- Server SEMPRE manda header anche se request non specifica versione.
  Pin sentinel: response.headers contains X-API-Version.
- Versione invalida → 400, NON silent fallback a default. Client deve
  sapere che ha mandato richiesta wrong (versione SDK upgrade needed).
- NO version nel URL path (es. /v1/products). Pin sentinel: URL pattern
  inalterato. Razionale: URL versioning rompe ALL SDK callers ad ogni
  release, header e' opt-in.

Public API
==========

    EMBED_API_CURRENT_VERSION: int (= 1)
    EMBED_API_SUPPORTED_VERSIONS: frozenset[int] (= {1})
    EMBED_API_VERSION_HEADER: str (= "X-API-Version")

    apply_api_version(request, response) -> int
        - Reads request X-API-Version (default = current)
        - Validates against supported set
        - Sets response X-API-Version header (mandatory)
        - Returns resolved version int (callers can branch behavior)
        - Raises HTTPException 400 on invalid/unsupported
"""

from typing import Optional

from fastapi import HTTPException, Request, Response, status


# Pin del nome del header — coordinated con embed-SDK client + integration
# docs. Sentinel verifica match.
EMBED_API_VERSION_HEADER = "X-API-Version"

# Current stable version. Bumpare SOLO quando introduciamo breaking change.
# Bump procedure documentata in module docstring.
EMBED_API_CURRENT_VERSION = 1

# Set di versioni supportate. Future: {1, 2} durante migration window.
# Sentinel valida che current sia sempre in set.
EMBED_API_SUPPORTED_VERSIONS: frozenset[int] = frozenset({1})


def _parse_requested_version(header_value: Optional[str]) -> Optional[int]:
    """Parse incoming X-API-Version header value to int.

    Returns:
        - None if header absent/empty (caller defaults to current)
        - int if header is valid integer
    Raises:
        - HTTPException 400 if header is present but non-numeric/non-positive
    """
    if header_value is None:
        return None
    stripped = header_value.strip()
    if not stripped:
        return None
    try:
        v = int(stripped)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_API_VERSION",
                "message": (
                    f"X-API-Version header must be a positive integer, "
                    f"got {header_value!r}."
                ),
                "supported_versions": sorted(EMBED_API_SUPPORTED_VERSIONS),
                "current": EMBED_API_CURRENT_VERSION,
            },
        )
    if v <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_API_VERSION",
                "message": (
                    f"X-API-Version must be positive, got {v}."
                ),
                "supported_versions": sorted(EMBED_API_SUPPORTED_VERSIONS),
                "current": EMBED_API_CURRENT_VERSION,
            },
        )
    return v


def apply_api_version(request: Request, response: Response) -> int:
    """Resolve + validate + apply API version for an embed endpoint.

    Pattern di uso (in ogni endpoint embed):

        async def get_embed_init(request: Request, response: Response, ...):
            _v = apply_api_version(request, response)
            # _v is the resolved version (default = current)
            # response.headers["X-API-Version"] e' gia' settato
            # branch su _v se logica diverge per versione
            ...

    Behavior:
        - Header request assente o vuoto → versione = current
        - Header valid integer in supported set → versione = quel valore
        - Header invalid (non-int o non-supported) → HTTPException 400
        - Response header X-API-Version SEMPRE settato (resolved version)

    Args:
        request: Starlette/FastAPI Request — letto X-API-Version header
        response: Starlette/FastAPI Response — settato X-API-Version header

    Returns:
        Resolved version int (1 today; future versions documented in module).

    Raises:
        HTTPException 400 if requested version is invalid or unsupported.
    """
    requested = _parse_requested_version(
        request.headers.get(EMBED_API_VERSION_HEADER)
    )

    if requested is None:
        resolved = EMBED_API_CURRENT_VERSION
    else:
        if requested not in EMBED_API_SUPPORTED_VERSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "UNSUPPORTED_API_VERSION",
                    "message": (
                        f"X-API-Version={requested} not supported. "
                        f"Use one of: {sorted(EMBED_API_SUPPORTED_VERSIONS)}. "
                        f"Current stable: {EMBED_API_CURRENT_VERSION}."
                    ),
                    "supported_versions": sorted(EMBED_API_SUPPORTED_VERSIONS),
                    "current": EMBED_API_CURRENT_VERSION,
                },
            )
        resolved = requested

    # MANDATORY: response always carries X-API-Version (signal a client SDK
    # quale contratto e' stato applicato). Pin sentinel verifica.
    response.headers[EMBED_API_VERSION_HEADER] = str(resolved)

    return resolved


__all__ = [
    "EMBED_API_CURRENT_VERSION",
    "EMBED_API_SUPPORTED_VERSIONS",
    "EMBED_API_VERSION_HEADER",
    "apply_api_version",
]
