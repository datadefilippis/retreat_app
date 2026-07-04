"""Sentinel — F4: lead/iscritti senza acquisti visibili in Customer Insights.

build_customer_list nasce da customer_metrics (acquisti). Un iscritto via form
newsletter senza ordini non ha riga metriche → invisibile. F4 lo aggiunge come
"lead" (zero metriche) coi filtri coerenti. Mockiamo le due fonti
(repository.find_metrics_by_org + customer_repository.find_by_org); i lead non
hanno account → nessuna query customer_accounts (no DB).

INV-F4-1  un cliente CRM senza metriche compare come lead (segment='lead', tx=0)
INV-F4-2  lo stato marketing del lead è derivato dal CRM (opted-in via newsletter)
INV-F4-3  filtro marketing_opted_in=true include i lead opted-in
INV-F4-4  filtro segment='top' NON include i lead; segment='lead' include solo i lead
INV-F4-5  un acquirente esistente resta invariato (non duplicato)
"""

import os
import sys
from pathlib import Path

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-real")

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import pytest

ORG = "org_f4"


def _buyer_metric():
    return {
        "customer_id": "buyer1", "customer_name": "Buyer", "segment": "top",
        "customer_status": "healthy", "total_revenue": 100.0, "transaction_count": 2,
        "avg_transaction_value": 50.0, "last_purchase_date": "2026-05-01",
        "days_since_last_purchase": 30, "churn_risk_score": 0.1, "trend_direction": "up",
    }


@pytest.fixture
def patched_sources(monkeypatch):
    """Mocka le due fonti di build_customer_list. Ritorna un setter."""
    from models.customer import Customer
    import modules.customer_insights.repository as repo_mod
    import repositories.customer_repository as cr_mod

    state = {"metrics": [], "customers": []}

    async def fake_metrics(org_id, *, segment=None, limit=5000):
        # Replica il filtro segment del repo reale.
        if segment:
            return [m for m in state["metrics"] if m.get("segment") == segment]
        return list(state["metrics"])

    async def fake_customers(org_id, *, active_only=False, limit=5000):
        return list(state["customers"])

    async def fake_metric_ids(org_id):
        # Set globale degli acquirenti (ignora il filtro segment).
        return {m["customer_id"] for m in state["metrics"]}

    monkeypatch.setattr(repo_mod, "find_metrics_by_org", fake_metrics)
    monkeypatch.setattr(repo_mod, "find_metric_customer_ids", fake_metric_ids)
    monkeypatch.setattr(cr_mod, "find_by_org", fake_customers)
    return state, Customer


async def test_inv_f4_1_2_3_lead_visible_and_opted_in(patched_sources):
    from modules.customer_insights.service import build_customer_list
    state, Customer = patched_sources

    state["metrics"] = [_buyer_metric()]
    state["customers"] = [
        Customer(id="buyer1", organization_id=ORG, name="Buyer", email="b@x.com"),
        # Iscritto newsletter senza acquisti, opted-in via CRM.
        Customer(
            id="lead1", organization_id=ORG, name="Lead Mario", email="l@x.com",
            accepted_marketing_at="2026-06-01T00:00:00+00:00", marketing_revoked_at=None,
        ),
    ]

    res = await build_customer_list(ORG, page=1, page_size=50)
    by_id = {r["customer_id"]: r for r in res["rows"]}

    # INV-F4-1 — il lead compare
    assert "lead1" in by_id
    lead = by_id["lead1"]
    assert lead["segment"] == "lead"
    assert lead["transaction_count"] == 0
    assert lead["total_revenue"] == 0
    # INV-F4-2 — stato marketing dal CRM
    assert lead["marketing_opted_in"] is True
    assert lead["has_account"] is False
    # INV-F4-5 — acquirente invariato, non duplicato
    assert sum(1 for r in res["rows"] if r["customer_id"] == "buyer1") == 1
    assert by_id["buyer1"]["segment"] == "top"


async def test_inv_f4_3_marketing_filter_includes_leads(patched_sources):
    from modules.customer_insights.service import build_customer_list
    state, Customer = patched_sources
    state["metrics"] = []
    state["customers"] = [
        Customer(id="lead_in", organization_id=ORG, name="In", email="i@x.com",
                 accepted_marketing_at="2026-06-01T00:00:00+00:00"),
        Customer(id="lead_out", organization_id=ORG, name="Out", email="o@x.com"),
    ]
    res = await build_customer_list(ORG, marketing_opted_in=True, page=1, page_size=50)
    ids = {r["customer_id"] for r in res["rows"]}
    assert "lead_in" in ids
    assert "lead_out" not in ids  # non opted-in → escluso dal filtro


async def test_inv_f4_4_segment_filter_semantics(patched_sources):
    from modules.customer_insights.service import build_customer_list
    state, Customer = patched_sources
    state["metrics"] = [_buyer_metric()]
    state["customers"] = [
        Customer(id="buyer1", organization_id=ORG, name="Buyer", email="b@x.com"),
        Customer(id="lead1", organization_id=ORG, name="Lead", email="l@x.com",
                 accepted_marketing_at="2026-06-01T00:00:00+00:00"),
    ]
    # segment='top' → solo acquirente, niente lead
    top = await build_customer_list(ORG, segment="top", page=1, page_size=50)
    top_ids = {r["customer_id"] for r in top["rows"]}
    assert "buyer1" in top_ids and "lead1" not in top_ids
    # segment='lead' → solo lead
    leads = await build_customer_list(ORG, segment="lead", page=1, page_size=50)
    lead_ids = {r["customer_id"] for r in leads["rows"]}
    assert "lead1" in lead_ids and "buyer1" not in lead_ids
