"""Bootstrap ambiente dev Retreat App (Fase 1.1/1.3 del RETREAT_MASTER_PLAN).

Idempotente. Contro il DB indicato da .env (retreat_dev):
  1. Esegue i seed (pricing plans + commercial plans, inclusi retreat_*)
  2. Crea/aggiorna l'org di test "Masseria Montanari Dev" su retreat_free
  3. Provisiona i ModuleSubscription dal piano
  4. Stampa la matrice di gating per modulo (DoD kill-list: AI e cashflow
     devono risultare enabled=False; commerce/catalogo/clienti True)

Uso:  venv/bin/python scripts/bootstrap_dev_org.py
"""

import asyncio
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

DEV_ORG_ID = "org_masseria_dev"
# L'org dell'utente demo della UI (admin@demo.com) — va provisionata anche
# lei sui piani retreat, altrimenti il browser gira sul piano legacy free.
DEMO_UI_ORG_ID = "2393033b-80a8-47c9-8529-b7810c0b2123"
DEV_ORG_NAME = "Masseria Montanari Dev"


async def main() -> int:
    from database import db
    from services.seed_pricing import seed_pricing_plans_if_empty
    from services.seed_commercial_plans import seed_commercial_plans
    from services.plan_provisioning import provision_commercial_plan
    from services.module_access import get_module_entitlements

    print(f"DB: {db.name}")

    # 1. Seed cataloghi (idempotenti)
    await seed_pricing_plans_if_empty()
    await seed_commercial_plans()

    # 2. Org di test (upsert minimale — i campi runtime li aggiunge l'app)
    await db.organizations.update_one(
        {"id": DEV_ORG_ID},
        {"$setOnInsert": {
            "id": DEV_ORG_ID,
            "name": DEV_ORG_NAME,
            "plan": "free",
            "created_at": "2026-07-04T00:00:00Z",
        }},
        upsert=True,
    )

    # 3. Provisioning piano retreat_free (org script + org UI demo)
    for oid in (DEV_ORG_ID, DEMO_UI_ORG_ID):
        result = await provision_commercial_plan(
            org_id=oid,
            plan_slug="retreat_free",
            assigned_by="script:bootstrap_dev_org",
            billing_status="manual",
            notes="org dev bootstrap",
        )
        print(f"Provisioning {oid[:12]}…: {result.get('plan_slug', result)}")

    # 4. Matrice gating — la DoD della kill-list
    org_doc = await db.organizations.find_one({"id": DEV_ORG_ID})
    expected = {
        "ai_assistant": False,
        # WS-2 (decisione founder): il cashflow core è il gestionale → ON;
        # le sotto-feature (alert/fornitori/qualità) sono spente a livello
        # di feature-key nel piano cashflow_monitor_retreat.
        "cashflow_monitor": True,
        "product_catalog": True,
        "commerce": True,
        "customers_light": True,
    }
    failures = []
    print("\nModulo               enabled  piano")
    for module_key, want in expected.items():
        ent = await get_module_entitlements(DEV_ORG_ID, module_key, org_doc)
        got = ent["enabled"]
        mark = "ok" if got == want else "!! ATTESO " + str(want)
        print(f"{module_key:<20} {str(got):<8} {ent.get('plan_slug','-'):<28} {mark}")
        if got != want:
            failures.append(module_key)

    if failures:
        print(f"\nKILL-LIST NON RISPETTATA: {failures}")
        return 1
    print("\nDoD verificata: AI spento, cashflow core acceso (gestionale), vendita accesa.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
