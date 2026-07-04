"""Fase 2 S2 (2.7) — aggregazione dashboard incassi (funzione pura)."""

import os, sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

from services.payment_schedule_service import aggregate_schedules

NOW = "2026-07-04T12:00:00+00:00"


def sched(state, rows):
    return {"payment_state": state, "rows": rows}


def row(status, amount, due="2026-09-01T00:00:00+00:00", refund=None):
    r = {"status": status, "amount_minor": amount, "due_at": due}
    if refund:
        r["refund"] = {"amount_minor": refund}
    return r


class TestAggregate:
    def test_empty(self):
        agg = aggregate_schedules([], now_iso=NOW)
        assert agg["orders_count"] == 0 and agg["incassato_minor"] == 0

    def test_mixed_states(self):
        docs = [
            sched("deposit_paid", [row("paid", 24000), row("pending", 56000)]),
            sched("fully_paid", [row("paid", 30000), row("paid_manual", 70000)]),
            sched("deposit_paid", [row("paid", 10000),
                                   row("pending", 40000, due="2026-06-01T00:00:00+00:00")]),
            sched("deposit_paid", [row("paid", 5000), row("at_risk", 15000)]),
        ]
        agg = aggregate_schedules(docs, now_iso=NOW)
        assert agg["orders_count"] == 4
        assert agg["incassato_minor"] == 24000 + 30000 + 70000 + 10000 + 5000
        assert agg["in_arrivo_minor"] == 56000
        assert agg["in_ritardo_minor"] == 40000    # pending scaduta
        assert agg["a_rischio_minor"] == 15000
        assert agg["fully_paid_orders"] == 1
        assert agg["deposit_paid_orders"] == 3

    def test_overdue_and_processing(self):
        docs = [sched("deposit_paid", [
            row("overdue", 20000, due="2026-06-01T00:00:00+00:00"),
            row("processing", 30000, due="2026-08-01T00:00:00+00:00"),
        ])]
        agg = aggregate_schedules(docs, now_iso=NOW)
        assert agg["in_ritardo_minor"] == 20000
        assert agg["in_arrivo_minor"] == 30000

    def test_refunds_and_cancelled_ignored_in_income(self):
        docs = [sched("none", [
            {"status": "refunded", "amount_minor": 24000,
             "due_at": "2026-06-01T00:00:00+00:00", "paid_at": "x",
             "refund": {"amount_minor": 24000}},
            {"status": "cancelled", "amount_minor": 56000,
             "due_at": "2026-09-01T00:00:00+00:00"},
        ])]
        agg = aggregate_schedules(docs, now_iso=NOW)
        assert agg["rimborsato_minor"] == 24000
        assert agg["in_arrivo_minor"] == 0 and agg["in_ritardo_minor"] == 0
