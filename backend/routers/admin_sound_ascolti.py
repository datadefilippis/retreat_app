"""ADMIN · SOUND · ASCOLTI — la regia degli ascolti (CS4, 8/10/2026).

Solo system admin. Legge e riassume `sound_ascolti` (services/ascolti_regia):
  GET /admin/sound/ascolti/panoramica?periodo=7|30|90|tutto
  GET /admin/sound/ascolti/meditazioni?periodo=
  GET /admin/sound/ascolti/meditazioni/{slug}?periodo=
  GET /admin/sound/ascolti/persone?periodo=
  GET /admin/sound/ascolti/persone/{account_id}
  GET /admin/sound/ascolti/export.csv?vista=meditazioni|persone&periodo=
Lo score «seguito» (0–100) e le sue cinque parti sono nel servizio, pinzati.
"""
import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from auth import require_system_admin
from services import ascolti_regia as R

router = APIRouter(prefix="/admin/sound/ascolti", tags=["Admin Sound"])


def _periodo(p: str) -> str:
    return p if p in R.PERIODI else "30"


@router.get("/panoramica")
async def panoramica(periodo: str = Query("30"), _: dict = Depends(require_system_admin)) -> dict:
    return await R.panoramica(_periodo(periodo))


@router.get("/meditazioni")
async def meditazioni(periodo: str = Query("30"), _: dict = Depends(require_system_admin)) -> dict:
    return {"periodo": _periodo(periodo), "items": await R.per_meditazione(_periodo(periodo))}


@router.get("/meditazioni/{slug}")
async def meditazione(slug: str, periodo: str = Query("30"), _: dict = Depends(require_system_admin)) -> dict:
    return await R.dettaglio_meditazione(slug, _periodo(periodo))


@router.get("/persone")
async def persone(periodo: str = Query("30"), _: dict = Depends(require_system_admin)) -> dict:
    return {"periodo": _periodo(periodo), "pesi": R.PESI_SEGUITO, "items": await R.per_persona(_periodo(periodo))}


@router.get("/persone/{account_id}")
async def persona(account_id: str, _: dict = Depends(require_system_admin)) -> dict:
    d = await R.dettaglio_persona(account_id)
    if not d.get("linea") and not d.get("email"):
        raise HTTPException(status_code=404, detail="Nessun ascolto per questa persona.")
    return d


@router.get("/export.csv")
async def export_csv(vista: str = Query("meditazioni"), periodo: str = Query("30"), _: dict = Depends(require_system_admin)):
    p = _periodo(periodo)
    if vista == "persone":
        righe = await R.per_persona(p)
        campi = ["nome", "email", "primo_ascolto", "ultimo_ascolto", "ascolti", "minuti", "completati", "titoli_diversi",
                 "preferite", "fascia_abituale", "giorni_attivi_30", "settimane_consecutive", "score"]
    else:
        righe = await R.per_meditazione(p)
        campi = ["titolo", "slug", "stato", "categoria", "ascolti", "persone", "anonimi", "minuti", "completamento",
                 "abbandono_medio", "preferiti", "momento_punta"]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=campi, extrasaction="ignore")
    w.writeheader()
    for r in righe:
        w.writerow({k: r.get(k, "") for k in campi})
    buf.seek(0)
    nome = f"aurya-ascolti-{vista}-{p}.csv"
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="{nome}"'})
