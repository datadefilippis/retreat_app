#!/usr/bin/env python3
"""
create_system_admin.py
======================
Bootstrap the AFianco platform system administrator.

This script MUST NOT be exposed via any API endpoint.
Run it directly on the server from the backend/ directory:

    cd backend
    python scripts/create_system_admin.py --email admin@company.com

If --password is omitted you will be prompted securely (no echo).

Constraints enforced:
  - Only ONE system admin is allowed.  The script exits if one already exists.
  - Password must meet the centralized complexity policy (see auth.py).
  - The email must not already be registered to any other account.
  - The user is created with organization_id=None (not scoped to any org).
  - Role is always "system_admin" — cannot be changed by this script.

To reset/replace a system admin, modify the document directly in MongoDB and
re-run this script (after removing the existing system_admin document).
"""

import argparse
import asyncio
import getpass
import sys
from pathlib import Path

# ── Add backend/ to sys.path so we can import project modules ────────────────
# This script lives in backend/scripts/ — one level below backend/.
_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))

# ── Project imports (after sys.path fix) ─────────────────────────────────────
from database import users_collection  # noqa: E402
from auth import get_password_hash, validate_password_strength  # noqa: E402
from models.common import generate_id, utc_now  # noqa: E402

_SCHEMA_VERSION = "2.8"


async def _create(email: str, password: str) -> None:
    """Core async logic — check constraints and insert the system admin user."""

    # ── Guard 1: only one system admin allowed ────────────────────────────────
    existing_sa = await users_collection.find_one(
        {"role": "system_admin"},
        {"_id": 0, "email": 1, "is_active": 1},
    )
    if existing_sa:
        active_label = "active" if existing_sa.get("is_active", True) else "INACTIVE"
        print(
            f"\nERROR: A system admin already exists.\n"
            f"  Email:  {existing_sa['email']}\n"
            f"  Status: {active_label}\n\n"
            "Only one system admin is allowed per platform instance.\n"
            "To replace it, remove the existing document from MongoDB first:\n"
            "  db.users.deleteOne({role: 'system_admin'})\n"
        )
        sys.exit(1)

    # ── Guard 2: email must not already be in use ─────────────────────────────
    email_conflict = await users_collection.find_one(
        {"email": email},
        {"_id": 0, "id": 1},
    )
    if email_conflict:
        print(
            f"\nERROR: The email '{email}' is already registered to another account.\n"
            "Choose a different email address for the system admin.\n"
        )
        sys.exit(1)

    # ── Create the document ───────────────────────────────────────────────────
    now_iso = utc_now().isoformat()
    user_doc = {
        "id":              generate_id(),
        "email":           email,
        "name":            "Platform Admin",
        "role":            "system_admin",
        "organization_id": None,           # system admin is not scoped to any org
        "password_hash":   get_password_hash(password),
        "is_active":       True,
        "created_at":      now_iso,
        "updated_at":      now_iso,
        "last_login_at":   None,
        "preferences":     None,
        "mfa_enabled":     None,
        "schema_version":  _SCHEMA_VERSION,
    }

    await users_collection.insert_one(user_doc)

    print(
        f"\n✓ System admin created successfully\n"
        f"  ID:    {user_doc['id']}\n"
        f"  Email: {email}\n"
        f"  Role:  system_admin\n"
        f"  Org:   None (platform-level — not scoped to any organization)\n\n"
        "You can now log in at POST /api/auth/login with these credentials.\n"
        "Use the system admin token on /api/admin/* routes (coming in next step).\n"
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bootstrap the AFianco platform system admin user.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python scripts/create_system_admin.py --email ops@company.com\n"
            "  python scripts/create_system_admin.py --email ops@company.com --password 'S3cur3P@ss!'\n"
        ),
    )
    parser.add_argument(
        "--email",
        required=True,
        help="Email address for the platform system admin.",
    )
    parser.add_argument(
        "--password",
        required=False,
        default=None,
        help=(
            "Password (min 12 chars, upper+lower+digit). "
            "If omitted, you will be prompted securely."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    # ── Resolve password ──────────────────────────────────────────────────────
    password = args.password
    if not password:
        password = getpass.getpass("Password for system admin: ")
        confirm  = getpass.getpass("Confirm password:          ")
        if password != confirm:
            print("\nERROR: Passwords do not match.\n")
            sys.exit(1)

    try:
        validate_password_strength(password)
    except ValueError as e:
        print(f"\nERROR: {e}\n")
        sys.exit(1)

    # ── Run ───────────────────────────────────────────────────────────────────
    asyncio.run(_create(args.email, password))


if __name__ == "__main__":
    main()
