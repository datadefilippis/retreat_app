"""
Hard-delete service — permanently removes ALL data for a deactivated organization.

Called by the background cleanup job after the 30-day grace period expires.
Idempotent: running twice on the same org_id is safe (delete_many on
already-deleted records returns deleted_count=0).

Order: derived data → core data → file cleanup → users → audit (anonymize) → org (last).
"""

import logging
import os
from pathlib import Path
from typing import Dict

from database import (
    chat_sessions_collection,
    ai_usage_events_collection,
    digests_collection,
    customer_metrics_collection,
    kpi_snapshots_collection,
    data_validation_rules_collection,
    dataset_column_profiles_collection,
    column_mappings_collection,
    module_configs_collection,
    module_subscriptions_collection,
    billing_events_collection,
    alerts_collection,
    insights_collection,
    organization_modules_collection,
    customers_collection,
    suppliers_collection,
    products_collection,
    purchase_records_collection,
    fixed_costs_collection,
    sales_records_collection,
    expense_records_collection,
    temp_uploads_collection,
    datasets_collection,
    users_collection,
    audit_logs_collection,
    organizations_collection,
)

logger = logging.getLogger(__name__)

# Ordered list of collections to hard-delete (org-scoped data).
# Derived/ephemeral data first, core data last.
_ORG_SCOPED_COLLECTIONS = [
    ("chat_sessions", chat_sessions_collection),
    ("ai_usage_events", ai_usage_events_collection),
    ("digests", digests_collection),
    ("customer_metrics", customer_metrics_collection),
    ("kpi_snapshots", kpi_snapshots_collection),
    ("data_validation_rules", data_validation_rules_collection),
    ("dataset_column_profiles", dataset_column_profiles_collection),
    ("column_mappings", column_mappings_collection),
    ("module_configs", module_configs_collection),
    ("module_subscriptions", module_subscriptions_collection),
    ("billing_events", billing_events_collection),
    ("alerts", alerts_collection),
    ("insights", insights_collection),
    ("organization_modules", organization_modules_collection),
    ("customers", customers_collection),
    ("suppliers", suppliers_collection),
    ("products", products_collection),
    ("purchase_records", purchase_records_collection),
    ("fixed_costs", fixed_costs_collection),
    ("sales_records", sales_records_collection),
    ("expense_records", expense_records_collection),
    ("temp_uploads", temp_uploads_collection),
]


async def cascade_hard_delete(org_id: str) -> Dict[str, int]:
    """Permanently delete ALL data for an organization.

    Returns a dict mapping collection name → number of deleted documents.
    The organization document itself is deleted last.
    """
    counts: Dict[str, int] = {}
    f = {"organization_id": org_id}

    # 1. Collect dataset file paths BEFORE deleting datasets
    file_keys = []
    try:
        cursor = datasets_collection.find(f, {"_id": 0, "file_key": 1, "file_path": 1})
        async for doc in cursor:
            if doc.get("file_key"):
                file_keys.append(doc["file_key"])
            if doc.get("file_path"):
                file_keys.append(doc["file_path"])
    except Exception as e:
        logger.warning("hard_delete: failed to collect file keys for org %s: %s", org_id, e)

    # 2. Delete all org-scoped collections
    for name, collection in _ORG_SCOPED_COLLECTIONS:
        try:
            result = await collection.delete_many(f)
            counts[name] = result.deleted_count
        except Exception as e:
            logger.error("hard_delete: failed on collection %s for org %s: %s", name, org_id, e)
            counts[name] = -1  # signal error

    # 3. Delete local upload files
    uploads_dir = Path(__file__).parent.parent / "uploads"
    files_deleted = 0
    for key in file_keys:
        try:
            file_path = uploads_dir / key
            if file_path.exists():
                file_path.unlink()
                files_deleted += 1
        except Exception as e:
            logger.warning("hard_delete: failed to delete local file %s: %s", key, e)
    counts["local_files"] = files_deleted

    # 4. Delete S3 files (if configured)
    s3_bucket = os.environ.get("S3_BUCKET_NAME", "")
    if s3_bucket and file_keys:
        try:
            import boto3
            s3 = boto3.client(
                "s3",
                aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID", ""),
                aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY", ""),
                region_name=os.environ.get("AWS_REGION", "eu-central-1"),
            )
            # S3 delete_objects accepts max 1000 keys per call
            for i in range(0, len(file_keys), 1000):
                batch = file_keys[i : i + 1000]
                s3.delete_objects(
                    Bucket=s3_bucket,
                    Delete={"Objects": [{"Key": k} for k in batch]},
                )
            counts["s3_files"] = len(file_keys)
            logger.info("hard_delete: deleted %d S3 objects for org %s", len(file_keys), org_id)
        except Exception as e:
            logger.error("hard_delete: S3 cleanup failed for org %s: %s", org_id, e)
            counts["s3_files"] = -1

    # 5. Delete datasets (after files are cleaned up)
    try:
        result = await datasets_collection.delete_many(f)
        counts["datasets"] = result.deleted_count
    except Exception as e:
        logger.error("hard_delete: failed on datasets for org %s: %s", org_id, e)
        counts["datasets"] = -1

    # 6. Delete users
    try:
        result = await users_collection.delete_many(f)
        counts["users"] = result.deleted_count
    except Exception as e:
        logger.error("hard_delete: failed on users for org %s: %s", org_id, e)
        counts["users"] = -1

    # 7. Anonymize audit logs (preserve structure for compliance)
    try:
        result = await audit_logs_collection.update_many(
            {"organization_id": org_id},
            {"$set": {
                "user_id": "deleted",
                "details": {},
                "organization_id": "deleted",
            }},
        )
        counts["audit_logs_anonymized"] = result.modified_count
    except Exception as e:
        logger.error("hard_delete: failed to anonymize audit logs for org %s: %s", org_id, e)
        counts["audit_logs_anonymized"] = -1

    # 8. Delete the organization document (LAST)
    try:
        result = await organizations_collection.delete_one({"id": org_id})
        counts["organization"] = result.deleted_count
    except Exception as e:
        logger.error("hard_delete: failed to delete org %s: %s", org_id, e)
        counts["organization"] = -1

    total = sum(v for v in counts.values() if v > 0)
    logger.info(
        "hard_delete: org=%s completed — %d records deleted across %d collections",
        org_id, total, len(counts),
    )

    return counts
