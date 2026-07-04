"""Fix caparra 4/7/2026 — il catalogo pubblico espone payment_plan.

Bug: il riepilogo checkout dello store mostrava "Totale 1600€" senza
menzione della caparra perché PublicProduct non aveva il campo
payment_plan (esisteva solo su PublicEventProduct della landing):
il serializer lo passava ma Pydantic lo scartava in silenzio.
La session Stripe chiedeva comunque la caparra giusta — bug di
comunicazione, non di soldi. Questi test impediscono la regressione.
"""

import os, sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")


class TestPublicProductPaymentPlan:
    def test_public_product_model_has_payment_plan_field(self):
        from routers.public import PublicProduct
        assert "payment_plan" in PublicProduct.model_fields

    def test_payment_plan_survives_model_roundtrip(self):
        from routers.public import PublicProduct
        plan = {"mode": "deposit_balance", "deposit_type": "percent",
                "deposit_value": 30, "balance_due_days_before": 30}
        p = PublicProduct(id="x", name="Ritiro", payment_plan=plan)
        assert p.model_dump()["payment_plan"]["deposit_value"] == 30

    def test_catalog_serializer_populates_payment_plan(self):
        # Il loop di enrichment del catalogo deve copiare
        # metadata.payment_plan sul doc (guard sul sorgente: il campo
        # sul modello da solo non basta se il serializer non lo popola).
        src = (BACKEND_DIR / "routers" / "public.py").read_text()
        idx = src.index("# Enrichment loop")
        end = src.index("products.append(PublicProduct(**doc))", idx)
        block = src[idx:end]
        assert 'doc["payment_plan"] = meta.get("payment_plan")' in block

    def test_event_landing_still_exposes_payment_plan(self):
        from routers.public import PublicEventProduct
        assert "payment_plan" in PublicEventProduct.model_fields
