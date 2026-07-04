"""Export router — CSV export for cashflow data, gated by feature_key 'export'."""

import csv
import io
import logging
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from auth import get_current_user, get_verified_user, get_verified_user
from repositories import organization_repository
from services.module_access import check_module_access
from database import (
    sales_records_collection,
    expense_records_collection,
    purchase_records_collection,
    fixed_costs_collection,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/export", tags=["Export"])

# ── Column definitions per data type ────────────────────────────────────────

_COLUMNS = {
    "sales": [
        ("date", "Data"),
        ("amount", "Importo"),
        ("currency", "Valuta"),
        ("category", "Categoria"),
        ("description", "Descrizione"),
        ("channel", "Canale"),
        ("payment_status", "Stato Pagamento"),
        ("due_date", "Scadenza"),
    ],
    "expenses": [
        ("date", "Data"),
        ("amount", "Importo"),
        ("currency", "Valuta"),
        ("category", "Categoria"),
        ("description", "Descrizione"),
        ("supplier", "Fornitore"),
        ("is_fixed", "Costo Fisso"),
        ("is_paid", "Pagato"),
    ],
    "purchases": [
        ("date", "Data"),
        ("supplier_name", "Fornitore"),
        ("category", "Categoria"),
        ("description", "Descrizione"),
        ("quantity", "Quantita"),
        ("unit_price", "Prezzo Unitario"),
        ("total_price", "Totale"),
        ("currency", "Valuta"),
        ("payment_status", "Stato Pagamento"),
    ],
    "fixed_costs": [
        ("name", "Nome"),
        ("amount", "Importo"),
        ("currency", "Valuta"),
        ("category", "Categoria"),
        ("frequency", "Frequenza"),
        ("description", "Descrizione"),
        ("start_date", "Data Inizio"),
        ("end_date", "Data Fine"),
        ("is_active", "Attivo"),
    ],
}

_COLLECTIONS = {
    "sales": sales_records_collection,
    "expenses": expense_records_collection,
    "purchases": purchase_records_collection,
    "fixed_costs": fixed_costs_collection,
}

_FILENAMES = {
    "sales": "vendite",
    "expenses": "spese",
    "purchases": "acquisti",
    "fixed_costs": "costi_fissi",
}


def _period_filter(period: str) -> dict:
    """Build a MongoDB date filter from period string."""
    if period == "all":
        return {}
    days_map = {"30d": 30, "90d": 90, "12m": 365}
    days = days_map.get(period)
    if not days:
        return {}
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    return {"date": {"$gte": cutoff}}


@router.get("/cashflow")
async def export_cashflow(
    type: str = Query(..., regex="^(sales|expenses|purchases|fixed_costs)$"),
    period: str = Query(default="all", regex="^(30d|90d|12m|all)$"),
    current_user: dict = Depends(get_verified_user),
):
    """Export cashflow data as CSV. Requires 'export' feature (pro plan)."""
    org_id = current_user["organization_id"]

    # Gate: export feature
    org_doc = await organization_repository.find_by_id(org_id)
    if not org_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organizzazione non trovata.")
    await check_module_access(org_id, "cashflow_monitor", "export", org_doc=org_doc)

    # Query records
    collection = _COLLECTIONS[type]
    query = {"organization_id": org_id}

    # Date filter (fixed_costs use start_date, not date)
    if type == "fixed_costs":
        if period != "all":
            days_map = {"30d": 30, "90d": 90, "12m": 365}
            days = days_map.get(period, 0)
            if days:
                cutoff = (date.today() - timedelta(days=days)).isoformat()
                query["start_date"] = {"$gte": cutoff}
    else:
        date_filter = _period_filter(period)
        query.update(date_filter)

    cursor = collection.find(query).sort("date" if type != "fixed_costs" else "name", 1)
    docs = await cursor.to_list(length=50000)

    # CH compliance v1: every monetary export row carries an explicit
    # "Valuta" column so a CHF merchant opening the file in Excel never
    # has to guess. The collections themselves don't store a per-row
    # currency yet (the org has a single currency), so we read once from
    # the org doc and stamp it on every row.
    from services.currency_service import get_currency_for_org
    org_currency = get_currency_for_org(org_doc)

    # Build CSV
    columns = _COLUMNS[type]
    output = io.StringIO()
    writer = csv.writer(output)

    # Header row (Italian labels)
    writer.writerow([label for _, label in columns])

    # Data rows
    for doc in docs:
        row = []
        for field, _ in columns:
            if field == "currency":
                val = doc.get("currency") or org_currency
            else:
                val = doc.get(field, "")
            if val is None:
                val = ""
            elif isinstance(val, bool):
                val = "Si" if val else "No"
            row.append(val)
        writer.writerow(row)

    output.seek(0)

    filename = f"{_FILENAMES[type]}_{date.today().isoformat()}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
