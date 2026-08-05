"""DC — una verita' sola per ogni numero mostrato all'operatore.

Dispositivo sotto guardia (ciclo DC, 5 ago 2026, dall'audit di
consistenza delle dashboard):
  DC1 — Event Dashboard conta solo ordini CONFERMATI (venduto, timeline,
        confronto edizioni); la card Posti confermati esiste e legge
        reserved_seats; il filtro «Annullati» morto e' rimosso.
  DC2 — Tesoreria: at_risk non sparisce dalle viste; la data
        dell'incasso e' quando e' stato PAGATO; il conteggio ritardi
        non e' troncato; «Ordini da gestire» esclude le bozze (che
        hanno la loro riga) e legge il campo fulfillment giusto.
  DC3 — Newsletter org: i disiscritti non sono iscritti.
  DC5 — Le etichette dicono cosa contano (Venduto, sublabel incassi).
"""

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")

FRONTEND_SRC = BACKEND_DIR.parent / "frontend" / "src"


class TestDc1EventTruth:
    def test_event_pipelines_confirmed_only(self):
        src = (BACKEND_DIR / "routers" / "event_occurrences.py").read_text()
        assert src.count('"status": {"$in": ["confirmed", "completed"]}') >= 3, \
            "venduto/timeline/confronto devono contare solo confermati"

    def test_event_dashboard_shows_confirmed_seats(self):
        src = (FRONTEND_SRC / "features" / "events"
               / "EventDashboardPage.js").read_text()
        assert "seatsConfirmed" in src, "card Posti confermati mancante"
        assert "reservedSeats" in src and "capacityProgress" in src

    def test_dead_voided_filter_removed(self):
        src = (FRONTEND_SRC / "features" / "events"
               / "EventDashboardPage.js").read_text()
        assert '<option value="voided">' not in src, \
            "filtro Annullati sempre-vuoto reintrodotto"

    def test_revenue_label_says_venduto(self):
        import json
        p = json.loads((FRONTEND_SRC / "locales" / "it"
                        / "products.json").read_text())
        rev = p["dashboards"]["event"]["revenue"]
        assert rev["title"] == "Venduto"
        assert "confermat" in rev["fromTickets_other"]


class TestDc2Tesoreria:
    def test_at_risk_money_is_visible(self):
        src = (BACKEND_DIR / "routers" / "cashflow.py").read_text()
        assert '"at_risk")' in src.split("_UNPAID = ")[1][:120], \
            "le rate at_risk sono di nuovo denaro invisibile"

    def test_incasso_dated_by_payment(self):
        src = (BACKEND_DIR / "routers" / "cashflow.py").read_text()
        assert 'o.get("paid_at")' in src, \
            "la gamba ordini deve datare l'incasso al pagamento"

    def test_overdue_count_never_truncated(self):
        src = (BACKEND_DIR / "routers" / "cashflow.py").read_text()
        assert '"in_ritardo_count": overdue_count_total' in src
        home = (FRONTEND_SRC / "features" / "dashboard"
                / "OperatorHome.js").read_text()
        assert "in_ritardo_count" in home

    def test_todo_excludes_drafts_and_reads_fulfillment(self):
        src = (BACKEND_DIR / "routers" / "orders.py").read_text()
        i = src.index('agg["needs_action_count"]')
        chunk = src[i - 600:i + 300]
        assert '"fulfillment": 1' in chunk, \
            "la proiezione deve portare order.fulfillment"
        assert 'o.get("status") == "confirmed"' in chunk, \
            "le bozze hanno gia' la loro riga: niente doppio conteggio"


class TestDc3Newsletter:
    def test_unsubscribed_are_not_subscribers(self):
        src = (BACKEND_DIR / "routers" / "newsletter_forms.py").read_text()
        assert '"status": {"$ne": "unsubscribed"}' in src, \
            "i disiscritti tornano nel conteggio iscritti"


class TestDc5Labels:
    def test_incassi_cards_have_sublabels(self):
        src = (FRONTEND_SRC / "features" / "cashflow"
               / "IncassiPage.js").read_text()
        for key in ("collectedSub", "incomingSub", "overdueSub",
                    "avgTicketSub"):
            assert key in src, f"sublabel mancante: {key}"
