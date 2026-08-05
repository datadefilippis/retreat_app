"""MO — l'ordine manuale produce gli stessi effetti di quello online.

Dispositivo sotto guardia (ciclo MO, 5 ago 2026):
  1. Il path manuale passa dal validatore tipizzato: conflitto slot,
     edizione non pubblicata e sold-out BLOCCANO; «slot obbligatorio»
     e «attendees obbligatori» restano soft (il banco puo' vendere
     senza fissare l'appuntamento; il partecipante ricade sul cliente).
  2. Un servizio con slot blocca il calendario GIA' in bozza e alla
     conferma emette l'appuntamento (issued_bookings → Calendario).
  3. Un evento alloca il partecipante (issued_tickets) e decrementa
     reserved_seats; sold-out e bozze sono rifiutati alla creazione.
  4. Il PATCH ordine conserva occurrence/slot/tier (prima li cancellava).
  5. Il form offre solo edizioni pubblicate e invia slot e tier.
"""

import asyncio
import os
import sys
import uuid
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")

import pytest

FRONTEND_SRC = BACKEND_DIR.parent / "frontend" / "src"
ORDERS_PAGE = FRONTEND_SRC / "features" / "orders" / "OrdersPage.js"


class TestMo1BackendDevice:
    def test_manual_path_calls_typed_validator(self):
        src = (BACKEND_DIR / "services" / "order_service.py").read_text()
        assert 'if source != "storefront":' in src
        assert "validate_order_item" in src
        # la politica banco: questi restano soft, il resto blocca
        for soft in ("service_slot_required", "attendees_required"):
            assert soft in src, f"reason soft mancante: {soft}"

    def test_service_slots_block_calendar_in_draft(self):
        src = (BACKEND_DIR / "services" / "order_service.py").read_text()
        assert '("rental", "service")' in src, \
            "il pre-reserve dello slot deve coprire anche i servizi"

    def test_patch_preserves_occurrence_and_slot(self):
        src = (BACKEND_DIR / "services" / "order_service.py").read_text()
        i = src.index("il PATCH ricostruiva la riga")
        chunk = src[i:i + 2200]
        for f in ("occurrence_id", "booking_date", "ticket_tier_id",
                  "attendees", "item_type"):
            assert f in chunk, f"PATCH perde ancora il campo {f}"


class TestMo4CalendarTruth:
    def test_calendar_reads_the_atomic_counter(self):
        """MO4 — Calendario ed Event Dashboard devono dire lo stesso
        numero: entrambi leggono reserved_seats (il contatore atomico
        della capienza), niente ri-aggregazione sugli ordini che
        contava le righe e includeva le bozze."""
        src = (BACKEND_DIR / "routers" / "calendar.py").read_text()
        assert '"reserved_seats": 1' in src, \
            "il calendario non proietta reserved_seats"
        assert 'occ.get("reserved_seats")' in src
        assert '"items.occurrence_id": {"$in": occ_ids}' not in src, \
            "la vecchia aggregazione sulle righe ordine e' tornata"


class TestMo2FormDevice:
    def test_form_offers_only_published_occurrences(self):
        src = ORDERS_PAGE.read_text()
        assert "o.status === 'published'" in src
        assert "['draft', 'published']" not in src

    def test_form_sends_slot_and_tier(self):
        src = ORDERS_PAGE.read_text()
        for f in ("booking_date", "booking_start_time", "booking_end_time",
                  "ticket_tier_id"):
            assert f in src, f"il form non gestisce {f}"
        assert "loadSlots" in src and "loadTiers" in src

    def test_edit_mode_keeps_slot_fields(self):
        src = ORDERS_PAGE.read_text()
        i = src.index("(editing.items || []).map")
        chunk = src[i:i + 700]
        for f in ("booking_date", "ticket_tier_id"):
            assert f in chunk, f"la modifica ordine perde {f} dallo stato"


class TestMoLiveEffects:
    """Effetti reali sul DB locale: bozza che blocca, conferma che
    emette, capienza che scende, sold-out/bozza rifiutati."""

    def test_manual_order_full_circle(self):
        async def run():
            from database import db
            from models.order import OrderCreate, OrderLineCreate
            from services import order_service

            # la suite gira su test_db (conftest): l'org se la crea da
            # sola, cosi' il test e' autosufficiente e pulito
            tag = uuid.uuid4().hex[:6]
            org_id = str(uuid.uuid4())
            plan_id = str(uuid.uuid4())
            sub_id = str(uuid.uuid4())
            await db.organizations.insert_one(
                {"id": org_id, "name": f"MO Org {tag}", "currency": "EUR",
                 "is_active": True})
            # il gate moduli non e' il dispositivo sotto test: piani e
            # abbonamenti minimi (commerce + cashflow_monitor, che la
            # conferma usa per i SalesRecords) perche' l'ordine viva
            extra_ids = []
            for mk in ("commerce", "cashflow_monitor"):
                p_id, s_id = str(uuid.uuid4()), str(uuid.uuid4())
                extra_ids += [("pricing_plans", p_id),
                              ("module_subscriptions", s_id)]
                await db.pricing_plans.insert_one(
                    {"id": p_id, "slug": f"{mk}_mo_{tag}",
                     "module_key": mk, "name": "MO Test",
                     "limits": {"orders_monthly": -1, "data_rows": -1}})
                await db.module_subscriptions.insert_one(
                    {"id": s_id, "organization_id": org_id,
                     "module_key": mk, "pricing_plan_id": p_id,
                     "status": "active", "started_at": "2026-01-01"})
            oids, pids, occs = [], [], []
            cust_id = str(uuid.uuid4())
            await db.customers.insert_one(
                {"id": cust_id, "organization_id": org_id,
                 "name": f"MO Guard {tag}",
                 "email": f"mo-guard-{tag}@example.com"})
            try:
                # servizio con slot: blocco in bozza + conflitto rifiutato
                svc = str(uuid.uuid4())
                await db.products.insert_one(
                    {"id": svc, "organization_id": org_id,
                     "name": f"Svc {tag}", "item_type": "service",
                     "unit_price": 50.0, "is_active": True, "metadata": {}})
                pids.append(svc)
                o1 = await order_service.create_order(org_id, OrderCreate(
                    customer_id=cust_id,
                    items=[OrderLineCreate(product_id=svc, quantity=1,
                                           booking_date="2026-09-15",
                                           booking_start_time="09:00",
                                           booking_end_time="10:00")]))
                oids.append(o1["id"])
                assert await db.blocked_slots.find_one(
                    {"reference_id": o1["id"]}), "bozza senza blocco slot"
                with pytest.raises(ValueError):
                    await order_service.create_order(org_id, OrderCreate(
                        customer_id=cust_id,
                        items=[OrderLineCreate(product_id=svc, quantity=1,
                                               booking_date="2026-09-15",
                                               booking_start_time="09:30",
                                               booking_end_time="10:30")]))
                await order_service.confirm_order(
                    org_id, o1["id"], skip_payment_check=True)
                assert await db.issued_bookings.find_one(
                    {"order_id": o1["id"]}), "conferma senza appuntamento"

                # evento pubblicato: partecipante + capienza; poi sold-out
                ev, occ = str(uuid.uuid4()), str(uuid.uuid4())
                await db.products.insert_one(
                    {"id": ev, "organization_id": org_id,
                     "name": f"Rit {tag}", "item_type": "event_ticket",
                     "unit_price": 100.0, "is_active": True, "metadata": {}})
                pids.append(ev)
                await db.event_occurrences.insert_one(
                    {"id": occ, "organization_id": org_id, "product_id": ev,
                     "slug": f"mo-g-{tag}", "status": "published",
                     "start_at": "2026-10-05T10:00:00+00:00",
                     "capacity": 1, "reserved_seats": 0})
                occs.append(occ)
                o2 = await order_service.create_order(org_id, OrderCreate(
                    customer_id=cust_id,
                    items=[OrderLineCreate(product_id=ev, quantity=1,
                                           occurrence_id=occ)]))
                oids.append(o2["id"])
                await order_service.confirm_order(
                    org_id, o2["id"], skip_payment_check=True)
                d = await db.event_occurrences.find_one({"id": occ})
                assert d["reserved_seats"] == 1, "capienza non decrementata"
                assert await db.issued_tickets.find_one(
                    {"order_id": o2["id"]}), "nessun partecipante emesso"
                # ora e' pieno: il prossimo manuale deve essere rifiutato
                with pytest.raises(ValueError):
                    await order_service.create_order(org_id, OrderCreate(
                        customer_id=cust_id,
                        items=[OrderLineCreate(product_id=ev, quantity=1,
                                               occurrence_id=occ)]))
            finally:
                for oid in oids:
                    await db.orders.delete_one({"id": oid})
                    await db.blocked_slots.delete_many({"reference_id": oid})
                    await db.issued_bookings.delete_many({"order_id": oid})
                    await db.issued_tickets.delete_many({"order_id": oid})
                    await db.event_seat_reservations.delete_many(
                        {"order_id": oid})
                    await db.sales_records.delete_many({"order_id": oid})
                    await db.payment_schedules.delete_many({"order_id": oid})
                for pid in pids:
                    await db.products.delete_one({"id": pid})
                for x in occs:
                    await db.event_occurrences.delete_one({"id": x})
                await db.customers.delete_one({"id": cust_id})
                await db.organizations.delete_one({"id": org_id})
                for coll, xid in extra_ids:
                    await db[coll].delete_one({"id": xid})

        asyncio.run(run())
