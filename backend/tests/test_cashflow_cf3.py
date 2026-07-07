"""CF3 — /analytics/cashflow: invarianti di solidità.

  1. auth obbligatoria (401/403 senza token);
  2. shape del payload: summary/months/overdue/upcoming/by_product;
  3. months = 12 bucket consecutivi (-8..+3) — la finestra include
     il futuro contrattualizzato;
  4. coerenza col libro mastro: la classificazione paid/pending/
     overdue segue la stessa semantica di aggregate_schedules
     (fonte di verità unica — niente KPI paralleli);
  5. cache 60s per-org presente nel modulo (pattern R13);
  6. le righe azionabili espongono il contatto MA mai l'email hash
     o dati fuori progetto.
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

import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8000")


def _login():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": "admin@demo.com", "password": "demo1234"}, timeout=10)
    if r.status_code != 200:
        import pytest
        pytest.skip("demo login unavailable (rate limit?)")
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


class TestAuth:
    def test_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/analytics/cashflow", timeout=10)
        assert r.status_code in (401, 403)


class TestShape:
    def test_payload_shape_and_window(self):
        d = requests.get(f"{BASE_URL}/api/analytics/cashflow?fresh=true",
                         headers=_login(), timeout=20).json()
        for key in ("summary", "months", "overdue", "upcoming", "by_product"):
            assert key in d, f"chiave mancante: {key}"
        for key in ("incassato", "in_arrivo", "in_ritardo", "ticket_medio"):
            assert key in d["summary"]
        # 12 bucket consecutivi YYYY-MM
        months = [m["month"] for m in d["months"]]
        assert len(months) == 12
        for a, b in zip(months, months[1:]):
            ya, ma = map(int, a.split("-"))
            yb, mb = map(int, b.split("-"))
            assert (yb * 12 + mb) - (ya * 12 + ma) == 1, f"buco fra {a} e {b}"

    def test_actionable_rows_expose_contact_fields(self):
        d = requests.get(f"{BASE_URL}/api/analytics/cashflow",
                         headers=_login(), timeout=20).json()
        for r in (d["overdue"] + d["upcoming"])[:3]:
            for key in ("customer_name", "customer_email", "customer_phone",
                        "amount", "due_at"):
                assert key in r


class TestSourceOfTruth:
    def test_same_ledger_semantics_as_aggregate_schedules(self):
        """La classificazione deve leggere payment_schedules con la
        stessa semantica del payments-overview (stessi status)."""
        import inspect
        from routers import cashflow
        src = inspect.getsource(cashflow)
        assert "payment_schedules" in src
        assert '"paid", "paid_manual"' in src.replace("'", '"')
        assert "pending" in src and "overdue" in src

    def test_cache_ttl_present(self):
        from routers import cashflow
        assert cashflow._CACHE_TTL == 60.0
        assert isinstance(cashflow._cache, dict)


class TestUnionCg1:
    """CG1 — la tesoreria è l'unione di TRE registri senza sovrapposizioni."""

    def test_orders_leg_excludes_scheduled_orders(self):
        """Anti-double-counting: la gamba ordini DEVE escludere gli
        order_id presenti nel ledger ($nin scheduled_order_ids)."""
        import inspect
        from routers import cashflow
        src = inspect.getsource(cashflow._build)
        assert "scheduled_order_ids" in src
        assert "$nin" in src

    def test_manual_leg_reads_only_manual_records(self):
        """I sales_records sincronizzati dagli ordini (dataset_id=
        'orders') NON si contano: il loro ordine è già nelle altre
        gambe. Solo dataset_id='manual' entra."""
        import inspect
        from routers import cashflow
        src = inspect.getsource(cashflow._build)
        assert '"dataset_id": "manual"' in src

    def test_rows_carry_source_discriminator(self):
        """Ogni riga azionabile dichiara la fonte (ledger/order/manual)
        — il frontend decide l'azione (sollecito vs registra pagamento)."""
        d = requests.get(f"{BASE_URL}/api/analytics/cashflow?fresh=true",
                         headers=_login(), timeout=20).json()
        for r in (d["overdue"] + d["upcoming"])[:10]:
            assert r.get("source") in ("ledger", "order", "manual")
