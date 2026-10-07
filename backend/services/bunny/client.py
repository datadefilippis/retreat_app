"""
Async HTTP client for the Bunny Stream Video API.

Thin wrapper over `httpx.AsyncClient` that:
  - sets the AccessKey header automatically
  - uses a sensible default timeout (5s) so admin PATCHes never hang
  - exposes only the endpoints we actually use (GET library, list videos)

Architectural note: this is the ONLY place in the codebase that talks
HTTP to Bunny. Everything else (signing, verification, future video
listing) sits on top. Keep it small and stable.

Why httpx and not requests/aiohttp:
  - FastAPI is async; using `requests` would block the event loop
  - httpx is already in the venv (verified pre-Step 1)
  - Native async/await + context manager makes the verifier code clean

Why a class instead of standalone functions:
  - Reuses the underlying connection pool across calls in the same flow
    (e.g. step 3 may verify-then-list-videos in one admin action)
  - Encapsulates the AccessKey so callers can't forget to set it
"""

from typing import Any, Dict, Optional
import httpx


# Bunny Stream Video API base URL. Distinct from the iframe embed host
# (https://iframe.mediadelivery.net) which is for player rendering, NOT
# management. Documented at https://docs.bunny.net/reference/api-overview
_BASE_URL = "https://video.bunnycdn.com"

# Default timeout — generous enough that a slow Bunny region doesn't
# false-positive a network_error, tight enough that the admin doesn't
# stare at a spinner if Bunny is genuinely down. Override per-call when
# needed (e.g. listing 1000 videos).
_DEFAULT_TIMEOUT = 5.0


class BunnyClient:
    """Async HTTP client for one Bunny library.

    Use as an async context manager so the underlying httpx client is
    closed deterministically:

        async with BunnyClient(api_key="...") as client:
            lib = await client.get_library("644527")

    The api_key is captured at construction; you can't accidentally hit
    one library with another's key (each instance is bound to a single
    AccessKey).
    """

    def __init__(self, api_key: str, timeout: float = _DEFAULT_TIMEOUT):
        # Stripped to defend against a user who pasted the key with
        # trailing whitespace from a copy-paste.
        self._api_key = (api_key or "").strip()
        self._client = httpx.AsyncClient(
            base_url=_BASE_URL,
            headers={
                "AccessKey": self._api_key,
                "accept": "application/json",
            },
            timeout=timeout,
        )

    async def __aenter__(self) -> "BunnyClient":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self._client.aclose()

    async def get_library(self, library_id: str) -> Dict[str, Any]:
        """Fetch metadata for a single library.

        Bunny endpoint: GET /library/{library_id}

        Returns the parsed JSON response on 200. Bunny's library object
        includes (relevant fields): `Id`, `Name`, `VideoCount`, `Bitrate*`,
        `EnabledResolutions`, ...

        Raises `httpx.HTTPStatusError` on 4xx/5xx — the verifier maps
        those to BunnyStatus values. Raises `httpx.TimeoutException` /
        `httpx.NetworkError` on transport failures.
        """
        # `library_id` is supposed to be a numeric string ("644527"). We
        # don't strip-validate here because the verifier's NOT_CONFIGURED
        # path already handles empty/null cases before reaching this
        # method. A non-numeric id will simply 404 from Bunny — which
        # maps cleanly to LIBRARY_NOT_FOUND.
        response = await self._client.get(f"/library/{library_id}")
        response.raise_for_status()
        return response.json()

    async def list_videos(
        self,
        library_id: str,
        page: int = 1,
        items_per_page: int = 10,
        order_by: str = "date",
    ) -> Dict[str, Any]:
        """List videos in a library, paginated.

        Reserved for Step 8 (post-MVP video picker). Implemented now so
        the client surface is stable; not yet wired to any UI.

        Bunny endpoint: GET /library/{library_id}/videos
        Query params: page, itemsPerPage, orderBy

        Returns the parsed JSON: `{ "totalItems": int, "items": [{ "guid", "title", ... }] }`.
        """
        response = await self._client.get(
            f"/library/{library_id}/videos",
            params={
                "page": page,
                "itemsPerPage": items_per_page,
                "orderBy": order_by,
            },
        )
        response.raise_for_status()
        return response.json()

    # ── AC1 (7/10/2026) — il video: crea, leggi, cancella ──────────────────
    # Documentazione Bunny Stream: POST /library/{id}/videos {title} → {guid};
    # GET /library/{id}/videos/{guid} → length (secondi), status, storageSize,
    # thumbnailFileName, availableResolutions; DELETE /library/{id}/videos/{guid}.

    async def create_video(self, library_id: str, title: str, collection_id: Optional[str] = None) -> Dict[str, Any]:
        """Il video nasce DENTRO la collezione del corso (Bunny: cartella nella
        libreria): libreria = operatore, collezione = corso, video = lezione."""
        body: Dict[str, Any] = {"title": title[:255]}
        if collection_id:
            body["collectionId"] = collection_id
        response = await self._client.post(f"/library/{library_id}/videos", json=body)
        response.raise_for_status()
        return response.json()

    async def update_video(self, library_id: str, video_guid: str, **campi: Any) -> None:
        """POST /library/{id}/videos/{guid} con title e/o collectionId."""
        response = await self._client.post(f"/library/{library_id}/videos/{video_guid}", json=campi)
        response.raise_for_status()

    # ── collezioni: una cartella per corso ──
    async def create_collection(self, library_id: str, name: str) -> Dict[str, Any]:
        response = await self._client.post(f"/library/{library_id}/collections", json={"name": name[:255]})
        response.raise_for_status()
        return response.json()

    async def update_collection(self, library_id: str, collection_id: str, name: str) -> None:
        response = await self._client.post(f"/library/{library_id}/collections/{collection_id}", json={"name": name[:255]})
        response.raise_for_status()

    async def delete_collection(self, library_id: str, collection_id: str) -> None:
        response = await self._client.delete(f"/library/{library_id}/collections/{collection_id}")
        if response.status_code != 404:
            response.raise_for_status()

    async def get_video(self, library_id: str, video_guid: str) -> Dict[str, Any]:
        response = await self._client.get(f"/library/{library_id}/videos/{video_guid}")
        response.raise_for_status()
        return response.json()

    async def delete_video(self, library_id: str, video_guid: str) -> None:
        response = await self._client.delete(f"/library/{library_id}/videos/{video_guid}")
        if response.status_code != 404:
            response.raise_for_status()


_ACCOUNT_BASE_URL = "https://api.bunny.net"


class BunnyAccountClient:
    """AC1 (7/10/2026) — il client dell'ACCOUNT Aurya (chiave di account,
    solo in env): crea e configura le librerie Stream degli operatori e
    legge il pull zone. Mai usato con chiavi di libreria."""

    def __init__(self, account_key: str, timeout: float = 15.0):
        self._client = httpx.AsyncClient(
            base_url=_ACCOUNT_BASE_URL,
            headers={"AccessKey": (account_key or "").strip(), "accept": "application/json",
                     "content-type": "application/json"},
            timeout=timeout,
        )

    async def __aenter__(self) -> "BunnyAccountClient":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self._client.aclose()

    async def create_library(self, name: str, replication_regions: Optional[list] = None) -> Dict[str, Any]:
        """POST /videolibrary {Name, ReplicationRegions} → {Id, ApiKey, ReadOnlyApiKey, PullZoneId, ...}.
        Nessuna replica: una regione basta (costi)."""
        body: Dict[str, Any] = {"Name": name[:100]}
        if replication_regions:
            body["ReplicationRegions"] = replication_regions
        response = await self._client.post("/videolibrary", json=body)
        response.raise_for_status()
        return response.json()

    async def list_libraries(self, per_page: int = 100) -> list:
        """GET /videolibrary → le librerie dell'account (per adottare una
        libreria gia' creata con lo stesso nome, se un salvataggio e' fallito)."""
        response = await self._client.get("/videolibrary", params={"page": 1, "perPage": per_page})
        response.raise_for_status()
        d = response.json()
        return d.get("Items", d if isinstance(d, list) else [])

    async def get_library(self, library_id: str) -> Dict[str, Any]:
        """GET /videolibrary/{id} → con ApiKey e ReadOnlyApiKey."""
        response = await self._client.get(f"/videolibrary/{library_id}")
        response.raise_for_status()
        return response.json()

    async def update_library(self, library_id: str, settings: Dict[str, Any]) -> Dict[str, Any]:
        """POST /videolibrary/{id} con le impostazioni (risoluzioni, originali,
        token auth, referrer, webhook...)."""
        response = await self._client.post(f"/videolibrary/{library_id}", json=settings)
        response.raise_for_status()
        return response.json() if response.content else {}

    async def add_allowed_referrer(self, library_id: str, hostname: str) -> None:
        """POST /videolibrary/{id}/addAllowedReferrer {Hostname}: il campo
        AllowedReferrers nell'update viene ignorato da Bunny (provato il 7/10),
        l'endpoint dedicato no."""
        response = await self._client.post(f"/videolibrary/{library_id}/addAllowedReferrer", json={"Hostname": hostname})
        response.raise_for_status()

    async def get_pullzone(self, pullzone_id: str) -> Dict[str, Any]:
        response = await self._client.get(f"/pullzone/{pullzone_id}")
        response.raise_for_status()
        return response.json()

    async def update_pullzone(self, pullzone_id: str, settings: Dict[str, Any]) -> None:
        """POST /pullzone/{id}: qui si accende la VERA protezione a token del
        CDN (ZoneSecurityEnabled) — provato il 7/10: il flag della libreria
        (PlayerTokenAuthenticationEnabled) da solo non blocca la playlist."""
        response = await self._client.post(f"/pullzone/{pullzone_id}", json=settings)
        response.raise_for_status()
