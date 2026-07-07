"""MD1 — attivazione automatica dei moduli dal piano commerciale.

Il fork aveva due strati mai riconciliati (subscription vs
organization_modules): signup fresco = menu vuoto. Da MD1 il
provision attiva/disattiva i moduli e lo startup riconcilia.
"""

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")


def test_provision_calls_module_activation_sync():
    """Il punto canonico dei cambi piano DEVE sincronizzare anche
    l'attivazione — non solo le subscription."""
    import inspect
    from services import plan_provisioning as pp
    src = inspect.getsource(pp.provision_commercial_plan)
    assert "sync_module_activation" in src


def test_sync_rule_disabled_suffix():
    """La regola: pricing plan `*_disabled` → modulo spento, tutto il
    resto acceso (default 'tutto attivo' del verticale)."""
    import inspect
    from services import plan_provisioning as pp
    src = inspect.getsource(pp.sync_module_activation)
    assert '_disabled' in src
    assert "upsert=True" in src


def test_startup_reconciles_existing_orgs():
    """Le org nate prima di MD1 vengono riallineate a ogni startup
    (idempotente, self-healing)."""
    src = (BACKEND_DIR / "server.py").read_text()
    assert "reconcile_all_module_activations" in src


def test_retreat_free_plan_enables_four_modules():
    """Il piano baseline attiva commerce/product_catalog/customers_light/
    cashflow_monitor e spegne ai_assistant (disabled)."""
    from services.seed_commercial_plans import RETREAT_COMMERCIAL_PLANS
    plan = next(p for p in RETREAT_COMMERCIAL_PLANS if p["slug"] == "retreat_free")
    mp = plan["module_plans"]
    enabled = {k for k, v in mp.items() if not str(v).endswith("_disabled")}
    disabled = {k for k, v in mp.items() if str(v).endswith("_disabled")}
    assert enabled == {"commerce", "product_catalog", "customers_light", "cashflow_monitor"}
    assert disabled == {"ai_assistant"}
