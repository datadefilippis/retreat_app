"""SA2/SA3 — /api/admin/platform/* : il business di piattaforma.

Panoramica (SA2) e plancia directory (SA3) per il system admin.
Stesso perimetro degli altri router admin: 100% require_system_admin,
sole letture, cache in-process breve (i numeri non cambiano al
secondo e la pagina si apre spesso).
"""

import time
from typing import Any, Dict

from fastapi import APIRouter, Depends

from auth import require_system_admin

router = APIRouter(prefix="/admin/platform", tags=["Admin Platform"])

_CACHE_TTL = 60.0
_cache: Dict[str, "tuple[float, dict]"] = {}


def _cached(key: str):
    hit = _cache.get(key)
    if hit and (time.monotonic() - hit[0]) < _CACHE_TTL:
        return hit[1]
    return None


@router.get("/overview")
async def platform_overview(
    current_user: dict = Depends(require_system_admin),
) -> Dict[str, Any]:
    """SA2 — la panoramica: i miei soldi (fee dal ledger SA1) + il
    marketplace (GMV per mese/canale/anima) + lo stato directory.
    L'MRR resta sul suo endpoint dedicato (/admin/billing-overview/mrr):
    il frontend compone i due."""
    cached = _cached("overview")
    if cached:
        return cached

    from services.platform_insights import (fee_totals, gmv_aggregates,
                                            directory_snapshot)
    from models.common import utc_now

    fees = await fee_totals()
    gmv = await gmv_aggregates()
    directory = await directory_snapshot()

    fee_by_month = fees["by_month"]
    months = [{
        **m,
        "online": round(
            (fee_by_month.get(m["month"], {}).get("amount_minor", 0)) / 100.0, 2),
        "fees": round(
            (fee_by_month.get(m["month"], {}).get("fee_minor", 0)) / 100.0, 2),
    } for m in gmv["months"]]

    t = fees["totals"]
    payload = {
        "money": {
            "fees_month": t["fee_month_minor"] / 100.0,
            "fees_12m": t["fee_12m_minor"] / 100.0,
            "online_month": t["online_month_minor"] / 100.0,
            "online_12m": t["online_12m_minor"] / 100.0,
        },
        "months": months,
        "by_channel_30d": gmv["by_channel_30d"],
        "by_type_12m": gmv["by_type_12m"],
        "directory": directory["counters"],
        "generated_at": utc_now().isoformat(),
    }
    _cache["overview"] = (time.monotonic(), payload)
    return payload


@router.get("/directory")
async def platform_directory(
    current_user: dict = Depends(require_system_admin),
) -> Dict[str, Any]:
    """SA3 — la plancia directory: una riga per org con lo stato di
    listing (stesse condizioni GT1b), i ritiri dentro/fuori e i
    motivi. La stessa fotografia dei contatori della panoramica."""
    cached = _cached("directory")
    if cached:
        return cached

    from services.platform_insights import directory_snapshot
    from models.common import utc_now

    snap = await directory_snapshot()
    payload = {**snap, "generated_at": utc_now().isoformat()}
    _cache["directory"] = (time.monotonic(), payload)
    return payload
