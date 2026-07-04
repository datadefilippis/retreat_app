"""
Retroactive Linker — controlled re-linking of historical records.

Scans existing records that have unresolved entity references and
attempts to link them using the same deterministic resolver logic
that runs at import time.

Two modes:
  - preview (dry_run=True):  Returns counts and sample candidates. No mutations.
  - apply   (dry_run=False): Applies exact-match links with audit metadata.

Safety principles:
  - Uses identical entity_resolver functions (exact match, ambiguity excluded)
  - Every retroactive link is tagged: metadata.retroactive_link = True
  - Batch-limited to prevent runaway updates
  - Returns detailed stats for operator review
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from services.entity_resolver import (
    build_customer_name_map,
    build_customer_external_id_map,
    build_product_sku_map,
    build_supplier_name_map,
    resolve_by_name,
    resolve_by_external_id,
    resolve_by_sku,
    normalize_entity_text,
)

logger = logging.getLogger(__name__)

MAX_SCAN_BATCH = 5000
MAX_PREVIEW_SAMPLES = 10


async def run_retroactive_linking(
    org_id: str,
    dataset_type: str = "sales",
    dry_run: bool = True,
) -> dict:
    """
    Scan unlinked records and attempt exact-match entity resolution.

    Args:
        org_id: Organization ID
        dataset_type: "sales", "purchases", or "expenses"
        dry_run: If True, return preview only. If False, apply links.

    Returns:
        Dict with stats, sample candidates (preview), and applied counts.
    """
    from database import db

    collection_name = {
        "sales": "sales_records",
        "purchases": "purchase_records",
        "expenses": "expense_records",
    }.get(dataset_type)

    if not collection_name:
        return {"error": f"Unknown dataset_type: {dataset_type}"}

    collection = db[collection_name]
    now = datetime.now(timezone.utc)

    # ── Build resolver maps ────────────────────────────────────────────────
    maps = {}
    if dataset_type == "sales":
        maps["customer_name"] = await build_customer_name_map(org_id)
        maps["customer_extid"] = await build_customer_external_id_map(org_id)
        maps["product_sku"] = await build_product_sku_map(org_id)
    elif dataset_type == "purchases":
        maps["supplier_name"] = await build_supplier_name_map(org_id)
        maps["product_sku"] = await build_product_sku_map(org_id)
    elif dataset_type == "expenses":
        maps["supplier_name"] = await build_supplier_name_map(org_id)

    map_sizes = {k: len(v) for k, v in maps.items()}
    logger.info("retroactive_linker: maps built for %s org=%s: %s", dataset_type, org_id, map_sizes)

    # ── Scan unlinked records ──────────────────────────────────────────────
    results = {
        "dataset_type": dataset_type,
        "dry_run": dry_run,
        "scanned": 0,
        "candidates_found": 0,
        "links_applied": 0,
        "by_entity": {},
        "samples": [],
        "map_sizes": map_sizes,
    }

    # Build query for records with at least one missing link
    unlinked_filter = _build_unlinked_filter(org_id, dataset_type)
    if not unlinked_filter:
        return results

    cursor = collection.find(
        unlinked_filter,
        {"_id": 0, "id": 1, "customer_id": 1, "product_id": 1, "supplier_id": 1,
         "description": 1, "category": 1, "metadata": 1, "date": 1},
    ).limit(MAX_SCAN_BATCH)

    candidates = []
    async for record in cursor:
        results["scanned"] += 1
        matched = _try_resolve(record, maps, dataset_type)
        if matched:
            candidates.append((record, matched))

    results["candidates_found"] = len(candidates)

    # Entity breakdown
    entity_counts = {}
    for _, matched in candidates:
        for entity_key in matched:
            entity_counts[entity_key] = entity_counts.get(entity_key, 0) + 1
    results["by_entity"] = entity_counts

    # Samples for preview
    for record, matched in candidates[:MAX_PREVIEW_SAMPLES]:
        results["samples"].append({
            "record_id": record["id"],
            "date": record.get("date"),
            "description": record.get("description", "")[:80],
            "links": matched,
        })

    # ── Apply if not dry run ───────────────────────────────────────────────
    if not dry_run and candidates:
        applied = 0
        for record, matched in candidates:
            update_set = {}
            for key, value in matched.items():
                update_set[key] = value

            # Audit metadata
            update_set["metadata.retroactive_link"] = True
            update_set["metadata.retroactive_linked_at"] = now.isoformat()
            update_set["metadata.retroactive_linked_fields"] = list(matched.keys())

            result = await collection.update_one(
                {"id": record["id"], "organization_id": org_id},
                {"$set": update_set},
            )
            if result.modified_count > 0:
                applied += 1

        results["links_applied"] = applied
        logger.info(
            "retroactive_linker: applied %d links (of %d candidates) for %s org=%s",
            applied, len(candidates), dataset_type, org_id,
        )

    return results


def _build_unlinked_filter(org_id: str, dataset_type: str) -> Optional[dict]:
    """Build a MongoDB query for records with at least one missing entity link."""
    base = {"organization_id": org_id}

    if dataset_type == "sales":
        # Records missing customer_id OR product_id, that have metadata hints
        return {
            **base,
            "$or": [
                {"customer_id": None},
                {"customer_id": {"$exists": False}},
                {"product_id": None},
                {"product_id": {"$exists": False}},
            ],
        }
    elif dataset_type in ("purchases", "expenses"):
        return {
            **base,
            "$or": [
                {"supplier_id": None},
                {"supplier_id": {"$exists": False}},
                {"product_id": None},
                {"product_id": {"$exists": False}},
            ],
        }
    return None


def _try_resolve(record: dict, maps: dict, dataset_type: str) -> dict:
    """
    Attempt to resolve missing entity links on a record.

    Returns dict of {field: resolved_id} for fields that can be linked.
    Returns empty dict if nothing can be resolved.
    """
    matched = {}
    meta = record.get("metadata", {}) or {}

    if dataset_type == "sales":
        # Customer resolution (if currently unlinked)
        if not record.get("customer_id"):
            cust_id = None
            # Priority 1: external_id from import metadata
            extid = meta.get("entity_linking", {}).get("unresolved", {}).get("customer_extid")
            if extid and maps.get("customer_extid"):
                cust_id = resolve_by_external_id(maps["customer_extid"], extid)
            # Priority 2: name from import metadata
            if not cust_id:
                name = meta.get("entity_linking", {}).get("unresolved", {}).get("customer_name")
                if name and maps.get("customer_name"):
                    cust_id = resolve_by_name(maps["customer_name"], name)
            # Priority 3: description field as customer name hint (conservative)
            if not cust_id and record.get("description"):
                desc = record["description"]
                if maps.get("customer_name"):
                    cust_id = resolve_by_name(maps["customer_name"], desc)
            if cust_id:
                matched["customer_id"] = cust_id

        # Product resolution (if currently unlinked)
        if not record.get("product_id"):
            prod_id = None
            sku = meta.get("entity_linking", {}).get("unresolved", {}).get("product_sku")
            if sku and maps.get("product_sku"):
                prod_id = resolve_by_sku(maps["product_sku"], sku)
            if prod_id:
                matched["product_id"] = prod_id

    elif dataset_type in ("purchases", "expenses"):
        # Supplier resolution
        if not record.get("supplier_id"):
            sup_id = None
            name = meta.get("entity_linking", {}).get("unresolved", {}).get("supplier_name")
            if name and maps.get("supplier_name"):
                sup_id = resolve_by_name(maps["supplier_name"], name)
            if not sup_id and record.get("description"):
                if maps.get("supplier_name"):
                    sup_id = resolve_by_name(maps["supplier_name"], record["description"])
            if sup_id:
                matched["supplier_id"] = sup_id

        # Product resolution (purchases only)
        if dataset_type == "purchases" and not record.get("product_id"):
            sku = meta.get("entity_linking", {}).get("unresolved", {}).get("product_sku")
            if sku and maps.get("product_sku"):
                prod_id = resolve_by_sku(maps["product_sku"], sku)
                if prod_id:
                    matched["product_id"] = prod_id

    return matched


async def get_linking_coverage(org_id: str) -> dict:
    """
    Return entity linking coverage across all dataset types.

    Provides total/linked/unlinked counts per entity per dataset type.
    """
    from database import db

    coverage = {}

    # Sales: customer_id + product_id
    sales_col = db["sales_records"]
    total_sales = await sales_col.count_documents({"organization_id": org_id})
    if total_sales > 0:
        linked_customer = await sales_col.count_documents(
            {"organization_id": org_id, "customer_id": {"$ne": None, "$exists": True}}
        )
        linked_product = await sales_col.count_documents(
            {"organization_id": org_id, "product_id": {"$ne": None, "$exists": True}}
        )
        coverage["sales"] = {
            "total": total_sales,
            "customer_id": {"linked": linked_customer, "unlinked": total_sales - linked_customer,
                           "pct": round(linked_customer / total_sales * 100, 1)},
            "product_id": {"linked": linked_product, "unlinked": total_sales - linked_product,
                          "pct": round(linked_product / total_sales * 100, 1)},
        }

    # Purchases: supplier_id + product_id
    purch_col = db["purchase_records"]
    total_purch = await purch_col.count_documents({"organization_id": org_id})
    if total_purch > 0:
        linked_supplier = await purch_col.count_documents(
            {"organization_id": org_id, "supplier_id": {"$ne": None, "$exists": True}}
        )
        linked_product_p = await purch_col.count_documents(
            {"organization_id": org_id, "product_id": {"$ne": None, "$exists": True}}
        )
        coverage["purchases"] = {
            "total": total_purch,
            "supplier_id": {"linked": linked_supplier, "unlinked": total_purch - linked_supplier,
                           "pct": round(linked_supplier / total_purch * 100, 1)},
            "product_id": {"linked": linked_product_p, "unlinked": total_purch - linked_product_p,
                          "pct": round(linked_product_p / total_purch * 100, 1)},
        }

    # Expenses: supplier_id
    exp_col = db["expense_records"]
    total_exp = await exp_col.count_documents({"organization_id": org_id})
    if total_exp > 0:
        linked_supplier_e = await exp_col.count_documents(
            {"organization_id": org_id, "supplier_id": {"$ne": None, "$exists": True}}
        )
        coverage["expenses"] = {
            "total": total_exp,
            "supplier_id": {"linked": linked_supplier_e, "unlinked": total_exp - linked_supplier_e,
                           "pct": round(linked_supplier_e / total_exp * 100, 1)},
        }

    return coverage
