#!/usr/bin/env python3
"""
Block 6 pre-flight — refuse to proceed with Standard Connect removal if any
active Standard connection exists.

Hard gate. Run before Fases 10b / 10c / 10d. Exit 0 means safe to proceed.
Exit non-zero means an active Standard merchant exists and the removal
would break their payment rail — STOP and investigate.

This script is strictly READ-ONLY. Zero writes to any collection.
"""

import asyncio
import sys
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))


async def main() -> int:
    from database import payment_connections_collection

    print("[preflight] Counting active Standard connections...")

    # Hard filter: connect_type="standard" AND status="active"
    # Anything else (disconnected, pending, never-migrated) is safe.
    active_standard = await payment_connections_collection.count_documents({
        "connect_type": "standard",
        "status": "active",
    })

    total_standard = await payment_connections_collection.count_documents({
        "connect_type": "standard",
    })

    total_express = await payment_connections_collection.count_documents({
        "connect_type": "express",
    })

    print(f"  active Standard  : {active_standard}")
    print(f"  total Standard   : {total_standard}  (incl. disconnected / pending)")
    print(f"  total Express    : {total_express}")

    if active_standard > 0:
        print()
        print("❌ ABORT: at least one merchant has an ACTIVE Standard connection.")
        print("   Block 6 removal would break their checkout flow. Aborting.")
        print("   To proceed, those merchants must first migrate to Express.")
        return 1

    # Sanity check: we expect some Express connections, otherwise this looks
    # like an empty / misconfigured database. Warn but do not abort — it's a
    # legitimate early-stage state.
    if total_express == 0:
        print()
        print("⚠️  WARNING: no Express connections either. Is this the right DB?")
        print("    (Not blocking — empty environments are legitimate.)")

    print()
    print("✅ pre-flight PASSED — safe to proceed with Block 6 removal phases")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
