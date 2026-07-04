"""
Data Validation Rule repository — full CRUD.

Used by:
  • dataset_service.py (read-only, non-blocking) — find_active_by_org_and_type()
  • routers/validation_rules.py (management API) — full CRUD
"""
from datetime import datetime, timezone
from typing import List, Optional

from database import data_validation_rules_collection
from models.data_validation_rule import DataValidationRule, DataValidationRuleBase


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Read ──────────────────────────────────────────────────────────────────────

async def find_active_by_org_and_type(
    organization_id: str, dataset_type: str
) -> List[DataValidationRule]:
    """Return all active validation rules for (org, dataset_type).

    Used by the upload pipeline.  Results sorted by field_name for deterministic
    evaluation order.  Malformed documents are silently skipped.
    Never raises — returns [] on any database error.
    """
    try:
        cursor = data_validation_rules_collection.find(
            {
                "organization_id": organization_id,
                "dataset_type": dataset_type,
                "is_active": True,
            },
            sort=[("field_name", 1)],
        )
        rules: List[DataValidationRule] = []
        async for doc in cursor:
            try:
                rules.append(DataValidationRule(**doc))
            except Exception:
                pass  # skip malformed rule documents
        return rules
    except Exception:
        return []


async def find_by_org(
    organization_id: str,
    dataset_type: Optional[str] = None,
) -> List[DataValidationRule]:
    """Return all validation rules for an org, optionally filtered by dataset_type.

    Used by the management API.  Includes both active and inactive rules.
    Sorted by (dataset_type, field_name).
    """
    query: dict = {"organization_id": organization_id}
    if dataset_type:
        query["dataset_type"] = dataset_type

    cursor = data_validation_rules_collection.find(
        query,
        sort=[("dataset_type", 1), ("field_name", 1)],
    )
    rules: List[DataValidationRule] = []
    async for doc in cursor:
        try:
            rules.append(DataValidationRule(**doc))
        except Exception:
            pass
    return rules


async def find_by_id(
    rule_id: str, organization_id: str
) -> Optional[DataValidationRule]:
    """Return a single rule by id, scoped to the org. Returns None if not found."""
    doc = await data_validation_rules_collection.find_one(
        {"id": rule_id, "organization_id": organization_id}
    )
    return DataValidationRule(**doc) if doc else None


# ── Write ─────────────────────────────────────────────────────────────────────

async def create_rule(
    organization_id: str, data: DataValidationRuleBase
) -> DataValidationRule:
    """Insert a new validation rule and return the created object."""
    rule = DataValidationRule(organization_id=organization_id, **data.model_dump())
    doc = rule.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    doc["updated_at"] = doc["updated_at"].isoformat()
    await data_validation_rules_collection.insert_one(doc)
    return rule


async def update_rule(
    rule_id: str, organization_id: str, updates: dict
) -> Optional[DataValidationRule]:
    """Apply a partial update to a rule.  Returns the updated rule or None if not found.

    The caller is responsible for passing only safe fields in `updates`.
    `updated_at` is always refreshed automatically.
    """
    updates["updated_at"] = _now()
    await data_validation_rules_collection.update_one(
        {"id": rule_id, "organization_id": organization_id},
        {"$set": updates},
    )
    return await find_by_id(rule_id, organization_id)


async def delete_rule(rule_id: str, organization_id: str) -> bool:
    """Hard-delete a validation rule.  Returns True if a document was removed."""
    result = await data_validation_rules_collection.delete_one(
        {"id": rule_id, "organization_id": organization_id}
    )
    return result.deleted_count > 0
