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


class TestModuleOwnershipMd2:
    """MD2 — ogni feature post-fork dichiara il suo modulo."""

    def test_registry_covers_orphan_features(self):
        from services.module_access import MODULE_OWNERSHIP
        assert MODULE_OWNERSHIP == {
            "reviews": "commerce",
            "newsletter": "commerce",
            "outreach": "customers_light",
            "cashflow_analytics": "cashflow_monitor",
            "sales_stats": "product_catalog",
            "cross_sell": "customers_light",
        }

    def test_gates_wired_on_orphan_routers(self):
        """I router (o le route) delle feature orfane montano il gate."""
        import inspect
        from routers import outreach, cashflow, newsletter_forms, reviews, products
        for mod, feature in [(outreach, "outreach"),
                             (cashflow, "cashflow_analytics"),
                             (newsletter_forms, "newsletter")]:
            assert f'require_module("{feature}")' in inspect.getsource(mod)
        assert inspect.getsource(reviews).count('require_module("reviews")') >= 5
        assert 'require_module("sales_stats")' in inspect.getsource(products)
        ci_src = (BACKEND_DIR / "modules" / "customer_insights" / "router.py").read_text()
        assert 'require_module("cross_sell")' in ci_src

    def test_public_review_endpoints_not_gated(self):
        """Il flusso recensioni PUBBLICO (OTP/submit/lista) resta libero:
        il gate vale solo per la plancia admin."""
        import inspect
        from routers import reviews
        src = inspect.getsource(reviews)
        # le route pubbliche non hanno il gate nella loro firma
        public_block = src.split("# ── Pubblico")[1].split("# admin")[0] if "# admin" in src else src.split('@router.get("/reviews"')[0]
        # euristica: il gate compare solo insieme a require_admin
        for line_pair in zip(src.splitlines(), src.splitlines()[1:]):
            if 'require_module("reviews")' in line_pair[1]:
                assert "require_admin" in line_pair[0]
