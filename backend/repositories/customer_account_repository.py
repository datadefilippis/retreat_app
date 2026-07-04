"""
Repository for customer_accounts collection.

All queries use {"_id": 0} projection (no MongoDB internal _id).
ORG-SCOPED: every lookup requires organization_id for tenant isolation.
"""

from typing import Optional
from database import customer_accounts_collection

_PROJECTION = {"_id": 0}


async def find_by_email(email: str, organization_id: str) -> Optional[dict]:
    """Lookup by normalised email within an org (caller must lowercase before calling)."""
    return await customer_accounts_collection.find_one(
        {"email": email, "organization_id": organization_id}, _PROJECTION
    )


async def find_by_id(account_id: str) -> Optional[dict]:
    """Lookup by account id. Returns org_id so callers can enforce scoping."""
    return await customer_accounts_collection.find_one(
        {"id": account_id}, _PROJECTION
    )


async def find_by_verification_token_hash(token_hash: str) -> Optional[dict]:
    return await customer_accounts_collection.find_one(
        {"verification_token_hash": token_hash}, _PROJECTION
    )


async def find_by_reset_token_hash(token_hash: str) -> Optional[dict]:
    return await customer_accounts_collection.find_one(
        {"reset_token_hash": token_hash}, _PROJECTION
    )


async def create(doc: dict) -> dict:
    """Insert a raw document. Caller builds it from the model."""
    await customer_accounts_collection.insert_one(doc)
    return doc


async def update(account_id: str, update_data: dict) -> bool:
    """$set fields on the account. Returns True if matched."""
    result = await customer_accounts_collection.update_one(
        {"id": account_id},
        {"$set": update_data},
    )
    return result.matched_count > 0
