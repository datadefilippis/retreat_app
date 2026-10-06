"""AC0 (6/10/2026) — le fondamenta dell'Accademia (docs/PIANO_ACCADEMIA_2026-10-06.md).

Niente si vende ancora: il modulo e' nel registro, i tier nei piani, la
fee `course` nel motore per riga, le iscrizioni sull'account Aurya, la
scheda «In arrivo» in Strumenti. Le rotte arrivano con AC1/AC2.
"""
import json
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
FRONTEND = BACKEND.parent / "frontend" / "src"


class TestModuloNelRegistro:
    def test_registrato_con_ownership_e_interruttore(self):
        import importlib
        importlib.import_module("modules.accademia")
        from core.module_registry import get as get_module
        d = get_module("accademia")
        assert d is not None and d.module_name == "Accademia" and d.is_available
        from services.module_access import MODULE_OWNERSHIP, KILL_SWITCH_FLAGS
        assert MODULE_OWNERSHIP["accademia"] == "accademia"
        assert KILL_SWITCH_FLAGS["accademia"] == "accademia_spento"
        from services.feature_flag_service import KNOWN_FLAGS, FLAG_ACCADEMIA_SPENTO
        assert FLAG_ACCADEMIA_SPENTO == "accademia_spento" and FLAG_ACCADEMIA_SPENTO in KNOWN_FLAGS
        src = (BACKEND / "server.py").read_text()
        assert '_il.import_module("modules.accademia")' in src
        assert "await migrate_accademia_a0_v1()" in src

    def test_tier_nei_piani(self):
        from services.seed_commercial_plans import RETREAT_COMMERCIAL_PLANS, _TIERS_BASE, _TIERS_PRO
        from services.seed_pricing import ACCADEMIA_PLANS
        assert _TIERS_BASE["accademia"] == "accademia_retreat_free"
        assert _TIERS_PRO["accademia"] == "accademia_retreat_pro"
        per_slug = {p["slug"]: p for p in RETREAT_COMMERCIAL_PLANS}
        assert per_slug["retreat_free"]["module_plans"]["accademia"] == "accademia_retreat_free"
        assert per_slug["retreat_pro"]["module_plans"]["accademia"] == "accademia_retreat_pro"
        tiers = {p["slug"]: p["limits"] for p in ACCADEMIA_PLANS}
        assert tiers["accademia_retreat_free"] == {"vendita": -1, "corsi_max": 2, "lezioni_max": 30, "video_gb": 2}
        assert tiers["accademia_retreat_pro"] == {"vendita": -1, "corsi_max": 30, "lezioni_max": 500, "video_gb": 50}
        assert all(p["module_key"] == "accademia" for p in ACCADEMIA_PLANS)

    def test_patto_dpa_copre_i_corsi(self):
        from services.dpa_guard import SELLABLE_ITEM_TYPES
        assert "course" in SELLABLE_ITEM_TYPES


class TestFeePerRigaCourse:
    def test_course_nella_mappa_e_nei_piani(self):
        from services.fee_per_riga import TIPI_CON_FEE, mappa_pulita
        assert "course" in TIPI_CON_FEE
        assert mappa_pulita({"physical": 15, "digital": 15, "course": 15, "service": 99}) == \
            {"physical": 15.0, "digital": 15.0, "course": 15.0}
        from services.seed_commercial_plans import FEE_PRODOTTI_GRATIS, FEE_PRODOTTI_ABBONATO, RETREAT_COMMERCIAL_PLANS
        assert FEE_PRODOTTI_GRATIS["course"] == 15.0 and FEE_PRODOTTI_ABBONATO["course"] == 0.0
        per_slug = {p["slug"]: p for p in RETREAT_COMMERCIAL_PLANS}
        assert per_slug["retreat_free"]["transaction_fee_by_type"]["course"] == 15.0
        for slug in ("retreat_pro", "retreat_club", "retreat_founding", "retreat_partner"):
            assert per_slug[slug]["transaction_fee_by_type"]["course"] == 0.0

    def test_scomposizione_con_una_riga_corso(self):
        """Ordine misto: un ritiro (0), un corso (15%), spedizione fuori."""
        from services.fee_per_riga import scomponi_fee
        order = {"items": [
            {"product_id": "r", "item_type": "event_ticket", "unit_price": 100, "quantity": 1},
            {"product_id": "c", "item_type": "course", "unit_price": 40, "quantity": 1},
        ], "shipping_cost": 6}
        fee, per_tipo = scomponi_fee(order, {"course": 15.0, "physical": 15.0}, {"r": "event_ticket", "c": "course"})
        assert fee == 600 and per_tipo == {"course": 600}
        fee0, _ = scomponi_fee(order, {"course": 0.0}, {"r": "event_ticket", "c": "course"})
        assert fee0 == 0

    def test_migrazione_definita_e_idempotente_nel_codice(self):
        src = (BACKEND / "services" / "seed_pricing.py").read_text()
        corpo = src[src.index("async def migrate_accademia_a0_v1"):src.index("async def migrate_zero_commissioni_v1")]
        assert '{"_id": "accademia_a0_v1"}' in corpo
        # tocca SOLO la chiave course della mappa dell'org, mai le altre
        assert '"application_fee_by_type.course": mappa_piano["course"]' in corpo
        assert '"module_key": "accademia"' in corpo and "accademia_retreat_free" in corpo


class TestIscrizioneSullAccountAurya:
    def test_modello(self):
        from models.issued_course_access import IssuedCourseAccess
        from datetime import datetime, timezone
        doc = IssuedCourseAccess(
            organization_id="o", order_id="ord", order_line_index=0, course_id="c",
            course_title_snapshot="Corso", platform_account_id="acc", access_token="t" * 32,
            enrolled_at=datetime.now(timezone.utc))
        assert doc.platform_account_id == "acc" and doc.customer_account_id is None
        assert doc.source == "order" and doc.completed_at is None
        # il legacy resta leggibile
        legacy = IssuedCourseAccess(
            organization_id="o", order_id="ord", order_line_index=1, course_id="c",
            course_title_snapshot="Corso", customer_account_id="cust", access_token="t" * 32,
            enrolled_at=datetime.now(timezone.utc))
        assert legacy.platform_account_id is None and legacy.customer_account_id == "cust"

    def test_emissione_usa_l_account_aurya(self):
        from datetime import datetime, timezone
        from services.issued_course_access_service import _build_enrollment_doc
        now = datetime.now(timezone.utc)
        base = dict(org_id="o", line_index=0, line={"product_id": "p", "product_name": "Corso"},
                    product_doc={"id": "p"}, course_doc={"id": "c", "title": "Corso"}, now=now)
        con_account = _build_enrollment_doc(order={"id": "ord", "platform_account_id": "acc"}, **base)
        assert con_account and con_account["platform_account_id"] == "acc" and con_account["source"] == "order"
        legacy = _build_enrollment_doc(order={"id": "ord", "customer_account_id": "cust"}, **base)
        assert legacy and legacy["customer_account_id"] == "cust" and legacy["platform_account_id"] is None
        assert _build_enrollment_doc(order={"id": "ord"}, **base) is None

    def test_guardia_all_ordine_e_indice(self):
        src = (BACKEND / "services" / "order_creation_service.py").read_text()
        assert "if has_course_item and not (platform_account_id or customer_account_id):" in src
        assert "Per comprare un corso serve il tuo account Aurya" in src
        db = (BACKEND / "database.py").read_text()
        assert '[("platform_account_id", 1), ("revoked_at", 1)]' in db


class TestStrumentiInArrivo:
    def test_scheda_e_stato(self):
        s = (FRONTEND / "pages" / "StrumentiPage.js").read_text()
        assert "key: 'accademia'" in s and "m.module_key === 'accademia'" in s
        blocco = s[s.index("key: 'accademia'"):]
        assert "inArrivo: true" in blocco and "azioni: []" in blocco
        assert "'In arrivo: è già previsto nel tuo piano.'" in blocco
        stato = (FRONTEND / "features" / "accademia" / "stato.js").read_text()
        assert "export const ACCADEMIA_UI_PRONTA = false" in stato
        assert "PILOTI_ACCADEMIA = ['admin@demo.com']" in stato
