"""
GDPR Data Export Service (art. 20 — Data Portability).

Builds a ZIP file containing all organization data as human-readable JSON files.
Each entity uses a strict WHITELIST of fields — no sensitive/technical data is included.

Memory-efficient: processes one collection at a time, writes to ZIP, then releases.
"""

import io
import json
import logging
import zipfile
from datetime import datetime, timezone

from database import (
    users_collection,
    organizations_collection,
    sales_records_collection,
    purchase_records_collection,
    expense_records_collection,
    fixed_costs_collection,
    customers_collection,
    suppliers_collection,
    products_collection,
    chat_sessions_collection,
    alerts_collection,
    audit_logs_collection,
)

logger = logging.getLogger(__name__)

_MAX_RECORDS = 100_000  # Hard cap per collection


# ── Whitelist field definitions ───────────────────────────────────────────────

_USER_FIELDS = [
    "name", "email", "role", "locale", "created_at",
    "last_login_at", "email_verified", "accepted_terms_at",
]

_ORG_FIELDS = [
    "name", "industry", "timezone", "currency", "plan",
    "commercial_plan_slug", "created_at",
]

_TEAM_MEMBER_FIELDS = [
    "name", "email", "role", "locale", "created_at",
    "last_login_at", "is_active",
]

_SALES_FIELDS = [
    "date", "amount", "category", "description", "channel",
    "payment_status", "payment_date", "due_date", "tags", "created_at",
]

_PURCHASE_FIELDS = [
    "date", "supplier_name", "quantity", "unit", "unit_price",
    "total_price", "iva", "total_with_iva", "category", "category_macro",
    "description", "invoice_number", "payment_status", "due_date",
    "tags", "created_at",
]

_EXPENSE_FIELDS = [
    "date", "amount", "category", "description", "supplier",
    "is_fixed", "is_paid", "payment_date", "tags", "created_at",
]

_FIXED_COST_FIELDS = [
    "name", "amount", "frequency", "category", "description",
    "start_date", "end_date", "is_active", "tags", "created_at",
]

_CUSTOMER_FIELDS = [
    "name", "email", "phone", "address", "tags",
    "is_active", "created_at",
]

_SUPPLIER_FIELDS = [
    "name", "email", "phone", "address", "category",
    "tags", "is_active", "created_at",
]

_PRODUCT_FIELDS = [
    "name", "sku", "category", "unit_price", "unit",
    "tags", "is_active", "created_at",
]

_CHAT_FIELDS = [
    "session_id", "title", "messages", "created_at", "updated_at",
]

_ALERT_FIELDS = [
    "module_key", "severity", "status", "title", "summary",
    "date_reference", "created_at", "resolved_at",
]

_AUDIT_FIELDS = [
    "action", "resource_type", "resource_id", "details", "created_at",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _pick(doc: dict, fields: list) -> dict:
    """Extract only whitelisted fields from a MongoDB document."""
    return {f: doc.get(f) for f in fields if f in doc}


def _to_json(data) -> str:
    """Serialize data to pretty JSON string (UTF-8, ISO dates)."""
    return json.dumps(data, ensure_ascii=False, indent=2, default=str)


# ── Main export function ─────────────────────────────────────────────────────

async def build_gdpr_export_zip(org_id: str, user_id: str) -> bytes:
    """Build a ZIP file containing all organization data as JSON.

    Processes one collection at a time to limit memory usage.
    Returns the ZIP file as bytes.
    """
    buf = io.BytesIO()
    now_iso = datetime.now(timezone.utc).isoformat()

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:

        # ── 1. account.json ───────────────────────────────────────────────
        user_doc = await users_collection.find_one(
            {"id": user_id}, {"_id": 0}
        )
        org_doc = await organizations_collection.find_one(
            {"id": org_id}, {"_id": 0}
        )
        account = {
            "user": _pick(user_doc, _USER_FIELDS) if user_doc else {},
            "organization": _pick(org_doc, _ORG_FIELDS) if org_doc else {},
            "export_date": now_iso,
            "export_format_version": "1.0",
        }
        zf.writestr("account.json", _to_json(account))
        del account

        # ── 2. team_members.json ──────────────────────────────────────────
        cursor = users_collection.find(
            {"organization_id": org_id}, {"_id": 0, "password_hash": 0}
        )
        members = await cursor.to_list(_MAX_RECORDS)
        team = [_pick(m, _TEAM_MEMBER_FIELDS) for m in members]

        # Build user_id → email lookup for audit log enrichment
        user_email_map = {}
        for m in members:
            uid = m.get("id")
            if uid:
                user_email_map[uid] = m.get("email", "unknown")
        del members

        zf.writestr("team_members.json", _to_json(team))
        del team

        # ── 3. sales.json ─────────────────────────────────────────────────
        cursor = sales_records_collection.find(
            {"organization_id": org_id}, {"_id": 0}
        ).sort("date", 1)
        records = await cursor.to_list(_MAX_RECORDS)
        zf.writestr("sales.json", _to_json([_pick(r, _SALES_FIELDS) for r in records]))
        del records

        # ── 4. purchases.json ─────────────────────────────────────────────
        cursor = purchase_records_collection.find(
            {"organization_id": org_id}, {"_id": 0}
        ).sort("date", 1)
        records = await cursor.to_list(_MAX_RECORDS)
        zf.writestr("purchases.json", _to_json([_pick(r, _PURCHASE_FIELDS) for r in records]))
        del records

        # ── 5. expenses.json ──────────────────────────────────────────────
        cursor = expense_records_collection.find(
            {"organization_id": org_id}, {"_id": 0}
        ).sort("date", 1)
        records = await cursor.to_list(_MAX_RECORDS)
        zf.writestr("expenses.json", _to_json([_pick(r, _EXPENSE_FIELDS) for r in records]))
        del records

        # ── 6. fixed_costs.json ───────────────────────────────────────────
        cursor = fixed_costs_collection.find(
            {"organization_id": org_id}, {"_id": 0}
        ).sort("name", 1)
        records = await cursor.to_list(_MAX_RECORDS)
        zf.writestr("fixed_costs.json", _to_json([_pick(r, _FIXED_COST_FIELDS) for r in records]))
        del records

        # ── 7. customers.json ─────────────────────────────────────────────
        cursor = customers_collection.find(
            {"organization_id": org_id}, {"_id": 0}
        ).sort("name", 1)
        records = await cursor.to_list(_MAX_RECORDS)
        zf.writestr("customers.json", _to_json([_pick(r, _CUSTOMER_FIELDS) for r in records]))
        del records

        # ── 8. suppliers.json ─────────────────────────────────────────────
        cursor = suppliers_collection.find(
            {"organization_id": org_id}, {"_id": 0}
        ).sort("name", 1)
        records = await cursor.to_list(_MAX_RECORDS)
        zf.writestr("suppliers.json", _to_json([_pick(r, _SUPPLIER_FIELDS) for r in records]))
        del records

        # ── 9. products.json ──────────────────────────────────────────────
        cursor = products_collection.find(
            {"organization_id": org_id}, {"_id": 0}
        ).sort("name", 1)
        records = await cursor.to_list(_MAX_RECORDS)
        zf.writestr("products.json", _to_json([_pick(r, _PRODUCT_FIELDS) for r in records]))
        del records

        # ── 10. chat_history.json ─────────────────────────────────────────
        cursor = chat_sessions_collection.find(
            {"organization_id": org_id}, {"_id": 0}
        ).sort("created_at", -1)
        records = await cursor.to_list(_MAX_RECORDS)
        zf.writestr("chat_history.json", _to_json([_pick(r, _CHAT_FIELDS) for r in records]))
        del records

        # ── 11. alerts.json ───────────────────────────────────────────────
        cursor = alerts_collection.find(
            {"organization_id": org_id}, {"_id": 0}
        ).sort("created_at", -1)
        records = await cursor.to_list(_MAX_RECORDS)
        zf.writestr("alerts.json", _to_json([_pick(r, _ALERT_FIELDS) for r in records]))
        del records

        # ── 12. audit_log.json (with user_email lookup) ──────────────────
        cursor = audit_logs_collection.find(
            {"organization_id": org_id}, {"_id": 0}
        ).sort("created_at", -1)
        records = await cursor.to_list(_MAX_RECORDS)
        audit_entries = []
        for r in records:
            entry = _pick(r, _AUDIT_FIELDS)
            uid = r.get("user_id", "")
            entry["user_email"] = user_email_map.get(uid, "deleted")
            audit_entries.append(entry)
        zf.writestr("audit_log.json", _to_json(audit_entries))
        del records, audit_entries

    result = buf.getvalue()
    buf.close()

    logger.info(
        "gdpr_export: built ZIP for org=%s user=%s — %d bytes",
        org_id, user_id, len(result),
    )

    return result
