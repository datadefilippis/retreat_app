"""Repository for platform-level settings (registration mode, etc.)."""

from datetime import datetime, timezone
from database import platform_settings_collection


async def get_registration_mode() -> str:
    """Return current registration mode ('open' or 'invite_only').

    Returns 'open' when no settings document exists — backward-compatible default.
    """
    doc = await platform_settings_collection.find_one(
        {"key": "registration"}, {"_id": 0}
    )
    if not doc:
        return "open"
    return doc.get("registration_mode", "open")


async def set_registration_mode(mode: str, updated_by: str) -> bool:
    """Upsert the registration mode setting.

    Args:
        mode: 'open' or 'invite_only'
        updated_by: user_id of the system admin

    Returns:
        True on success
    """
    result = await platform_settings_collection.update_one(
        {"key": "registration"},
        {"$set": {
            "key": "registration",
            "registration_mode": mode,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": updated_by,
        }},
        upsert=True,
    )
    return result.acknowledged
