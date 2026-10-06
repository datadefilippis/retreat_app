"""P0 (6/10/2026) — FONDAMENTA dei prodotti: la commissione la decide la
riga, il modulo «prodotti» nel registro, i tier, l'interruttore, il patto,
il volume dei file, la scheda negli Strumenti.

Promessa stampata: ritiri e servizi senza commissioni, sempre. Guardie:

  PF1  fee per riga: solo ritiri → 0 (identico a oggi); misto (ritiro +
       libro + guida) → solo le righe prodotto; sconto coupon ripartito;
       snapshot «physical» su un prodotto che OGGI e' service → 0; quota
       proporzionale per caparra/rate; percentuale effettiva
  PF2  mappa: dal campo org, altrimenti dal piano; pulita (solo tipi
       ammessi, 0..100)
  PF3  provider: l'importo per riga vince sulla percentuale, con tetto al
       netto; senza importo il ramo storico resta
  PF4  checkout: entrambe le session passano application_fee_minor e il
       metadata (importo, scomposizione, percentuale effettiva)
  PF5  ledger: fee_minor esplicito, percentuale effettiva dal metadata,
       rimborso con la percentuale dell'incasso
  PF6  piani: Gratis 15/15, abbonamenti 0/0, modulo prodotti nei tier, il
       provisioning propaga la mappa, migrazione d'avvio presente
  PF7  modulo: registrato, ownership, interruttore prodotti_spento noto e
       rispettato da require_module, patto DPA sui prodotti
  PF8  infrastruttura: volume private_uploads nel compose; scheda Prodotti
       negli Strumenti letta dal registro
"""
from __future__ import annotations

import os
import sys
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("JWT_SECRET_KEY", "test")
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_dummy")

BACKEND = Path(__file__).resolve().parents[1]
ROOT = BACKEND.parent
FRONTEND = ROOT / "frontend" / "src"
sys.path.insert(0, str(BACKEND))

from services import fee_per_riga as F  # noqa: E402

MAPPA = {"physical": 15, "digital": 15}
RITIRO = {"items": [{"product_id": "r", "item_type": "event_ticket", "line_total": 300.0, "occurrence_id": "o1"}],
          "discount_total": 0, "total": 300}
MISTO = {"items": [{"product_id": "r", "item_type": "event_ticket", "line_total": 300.0},
                   {"product_id": "l", "item_type": "physical", "line_total": 20.0},
                   {"product_id": "d", "item_type": "digital", "line_total": 10.0}],
         "discount_total": 0, "total": 330}


# ── PF1 ─────────────────────────────────────────────────────────────────

class TestPF1FeePerRiga:
    def test_solo_ritiri_zero(self):
        assert F.scomponi_fee(RITIRO, MAPPA) == (0, {})
        assert F.scomponi_fee(RITIRO, {}) == (0, {})

    def test_misto_solo_righe_prodotto(self):
        assert F.scomponi_fee(MISTO, MAPPA) == (450, {"physical": 300, "digital": 150})

    def test_sconto_ripartito(self):
        # 33 di sconto su 330 = 10% su ogni riga → fee su 18 + 9
        assert F.scomponi_fee(MISTO, MAPPA, discount_major=33) == (405, {"physical": 270, "digital": 135})

    def test_tipo_vero_del_prodotto_vince_sullo_snapshot(self):
        ordine = {"items": [{"product_id": "s", "item_type": "physical", "line_total": 50}]}
        assert F.scomponi_fee(ordine, MAPPA, {"s": "service"}) == (0, {})
        assert F.scomponi_fee(ordine, MAPPA, {"s": "physical"}) == (750, {"physical": 750})

    def test_pro_zero(self):
        assert F.scomponi_fee(MISTO, {"physical": 0, "digital": 0}) == (0, {})

    def test_quota_e_percentuale(self):
        assert F.quota_fee(450, 9900, 33000) == 135
        assert F.quota_fee(0, 9900, 33000) == 0 and F.quota_fee(450, 9900, 0) == 0
        assert F.quota_fee(450, 33000, 33000) == 450
        assert F.percentuale_effettiva(450, 9900) == 4.5455
        assert F.percentuale_effettiva(0, 9900) == 0.0

    def test_metadata_stringhe(self):
        m = F.metadata_fee(450, {"physical": 300, "digital": 150}, 33000)
        assert m["application_fee_minor"] == "450"
        assert m["fee_by_type"] == '{"physical":300,"digital":150}'
        assert m["application_fee_effective_percent"] == "1.3636"
        assert F.metadata_fee(0, {}, 1000) == {"application_fee_minor": "0", "application_fee_effective_percent": "0.0"}


# ── PF2 ─────────────────────────────────────────────────────────────────

class TestPF2Mappa:
    def test_pulita(self):
        assert F.mappa_pulita({"physical": "15", "service": 5, "digital": 200, "x": 1}) == {"physical": 15.0, "digital": 100.0}
        assert F.mappa_pulita(None) == {} and F.mappa_pulita("15") == {}

    @pytest.mark.asyncio
    async def test_dal_campo_org_poi_dal_piano(self):
        assert await F.mappa_fee_org({"application_fee_by_type": {"physical": 15}}) == {"physical": 15.0}
        assert await F.mappa_fee_org({"application_fee_by_type": {}}) == {}
        repo = MagicMock()
        repo.get_commercial_plan = AsyncMock(return_value={"transaction_fee_by_type": {"physical": 15, "digital": 15}})
        with patch("repositories.billing_repository.get_commercial_plan", repo.get_commercial_plan):
            assert await F.mappa_fee_org({"commercial_plan_slug": "retreat_free"}) == {"physical": 15.0, "digital": 15.0}
        assert await F.mappa_fee_org({}) == {} and await F.mappa_fee_org(None) == {}


# ── PF3 ─────────────────────────────────────────────────────────────────

class TestPF3Provider:
    def test_importo_vince_e_ramo_storico_resta(self):
        src = (BACKEND / "payment_providers" / "stripe" / "provider.py").read_text()
        assert "if request.application_fee_minor is not None:" in src
        assert "fee_minor = min(max(0, int(request.application_fee_minor)), net_minor)" in src
        assert "elif request.application_fee_percent and request.application_fee_percent > 0:" in src
        from payment_providers.models import CheckoutSessionRequest
        r = CheckoutSessionRequest(org_id="o", order_id="x", currency="EUR", line_items=(),
                                   success_url="s", cancel_url="c")
        assert r.application_fee_minor is None and r.application_fee_percent == Decimal("0")


# ── PF4 ─────────────────────────────────────────────────────────────────

class TestPF4Checkout:
    def test_entrambe_le_session(self):
        src = (BACKEND / "services" / "payment_checkout_service.py").read_text()
        a = src[src.index("async def create_checkout_session("):src.index("async def _resolve_org_doc_for_provider(")]
        b = src[src.index("async def create_row_checkout_session("):src.index("async def reconcile_checkout_event(")]
        for corpo in (a, b):
            assert "application_fee_minor=fee_session_minor" in corpo
            assert "metadata_fee(fee_session_minor" in corpo
            assert "await fee_per_ordine(" in corpo and "org_doc_for_provider, order" in corpo
            assert '"application_fee_percent": str(application_fee_percent)' in corpo, "il ramo storico resta"
        assert "quota_fee(fee_ordine_minor, int(deposit_row[\"amount_minor\"])" in a, "la caparra porta la quota"
        assert "quota_fee(_fee_tot, int(row[\"amount_minor\"])" in b


# ── PF5 ─────────────────────────────────────────────────────────────────

class TestPF5Ledger:
    @pytest.mark.asyncio
    async def test_percentuale_effettiva_dal_metadata(self):
        from services import platform_fee_ledger as L
        assert await L.resolve_fee_percent({"metadata": {"application_fee_effective_percent": "1.3636",
                                                          "application_fee_percent": "0"}}, "org") == 1.3636
        assert await L.resolve_fee_percent({"metadata": {"application_fee_percent": "5"}}, "org") == 5.0

    @pytest.mark.asyncio
    async def test_record_from_session_passa_importo_e_scomposizione(self):
        from services import platform_fee_ledger as L
        chiamate = []

        async def finto(**kw):
            chiamate.append(kw)
        with patch.object(L, "record_platform_fee", finto):
            await L.record_from_session(
                {"id": "cs_1", "amount_total": 33000, "currency": "eur",
                 "metadata": {"application_fee_minor": "450", "fee_by_type": '{"physical":300,"digital":150}',
                              "application_fee_effective_percent": "1.3636"}},
                organization_id="org", order_id="ord", kind="checkout")
        assert chiamate[0]["fee_minor"] == 450
        assert chiamate[0]["fee_by_type"] == {"physical": 300, "digital": 150}
        assert chiamate[0]["fee_percent"] == 1.3636

    @pytest.mark.asyncio
    async def test_fee_minor_esplicito_nel_documento(self):
        from services import platform_fee_ledger as L
        coll = MagicMock()
        coll.update_one = AsyncMock()
        db = MagicMock()
        db.platform_fee_ledger = coll
        with patch("database.db", db):
            await L.record_platform_fee(entry_key="k", organization_id="o", order_id="x", kind="checkout",
                                        amount_minor=33000, fee_percent=1.3636, currency="eur",
                                        fee_minor=450, fee_by_type={"physical": 300})
            doc = coll.update_one.call_args.args[1]["$setOnInsert"]
            assert doc["fee_minor"] == 450 and doc["fee_by_type"] == {"physical": 300}
            await L.record_platform_fee(entry_key="k2", organization_id="o", order_id="x", kind="checkout",
                                        amount_minor=10000, fee_percent=5, currency="eur")
            doc = coll.update_one.call_args.args[1]["$setOnInsert"]
            assert doc["fee_minor"] == 500 and doc["fee_by_type"] is None, "senza importo: dalla percentuale, come prima"

    def test_rimborso_usa_la_percentuale_dell_incasso(self):
        src = (BACKEND / "services" / "payment_refund_service.py").read_text()
        assert "resolve_fee_percent_for_order(order_id, org_id)" in src
        assert "resolve_fee_percent({}, org_id)" not in src


# ── PF6 ─────────────────────────────────────────────────────────────────

class TestPF6Piani:
    def test_mappa_nei_piani(self):
        from services.seed_commercial_plans import RETREAT_COMMERCIAL_PLANS
        per_slug = {p["slug"]: p for p in RETREAT_COMMERCIAL_PLANS}
        assert per_slug["retreat_free"]["transaction_fee_by_type"] == {"physical": 15.0, "digital": 15.0}
        for slug in ("retreat_club", "retreat_pro", "retreat_founding", "retreat_partner"):
            assert per_slug[slug]["transaction_fee_by_type"] == {"physical": 0.0, "digital": 0.0}, slug
            assert per_slug[slug]["transaction_fee_percent"] == 0.0
        assert per_slug["retreat_free"]["transaction_fee_percent"] == 0.0, "ritiri e servizi: zero, sempre"
        assert per_slug["retreat_free"]["module_plans"]["prodotti"] == "prodotti_retreat_free"
        assert per_slug["retreat_pro"]["module_plans"]["prodotti"] == "prodotti_retreat_pro"
        from models.commercial_plan import CommercialPlan
        assert CommercialPlan(**per_slug["retreat_free"]).transaction_fee_by_type == {"physical": 15.0, "digital": 15.0}

    def test_tier_del_modulo(self):
        from services.seed_pricing import PRODOTTI_PLANS
        tiers = {p["slug"]: p["limits"] for p in PRODOTTI_PLANS}
        assert tiers["prodotti_retreat_free"] == {"vendita": -1, "products_max": 20, "max_file_mb": 100}
        assert tiers["prodotti_retreat_pro"] == {"vendita": -1, "products_max": 200, "max_file_mb": 500}
        src = (BACKEND / "services" / "seed_pricing.py").read_text()
        assert '_seed_module_plans("prodotti", PRODOTTI_PLANS)' in src
        assert "+ CUSTOMERS_LIGHT_PLANS + PRODOTTI_PLANS" in src
        assert "async def migrate_prodotti_p0_v1" in src
        assert 'await migrate_prodotti_p0_v1()' in (BACKEND / "server.py").read_text()

    def test_provisioning_propaga_e_org_la_porta(self):
        src = (BACKEND / "services" / "plan_provisioning.py").read_text()
        assert 'org_fields["application_fee_by_type"] = mappa_pulita(plan.get("transaction_fee_by_type"))' in src
        from models.organization import Organization
        assert "application_fee_by_type" in Organization.model_fields
        assert Organization.model_fields["application_fee_percent"].metadata  # ge/le presenti


# ── PF7 ─────────────────────────────────────────────────────────────────

class TestPF7Modulo:
    def test_registrato_e_ownership(self):
        import importlib
        importlib.import_module("modules.prodotti")
        from core import module_registry
        m = module_registry.get("prodotti")
        assert m and m.module_name == "Prodotti" and m.is_available
        from services.module_access import MODULE_OWNERSHIP, KILL_SWITCH_FLAGS
        assert MODULE_OWNERSHIP["prodotti"] == "prodotti"
        assert KILL_SWITCH_FLAGS["prodotti"] == "prodotti_spento"
        from services.feature_flag_service import KNOWN_FLAGS, FLAG_PRODOTTI_SPENTO
        assert FLAG_PRODOTTI_SPENTO in KNOWN_FLAGS
        assert 'import_module("modules.prodotti")' in (BACKEND / "server.py").read_text()

    @pytest.mark.asyncio
    async def test_interruttore_rispettato(self):
        from fastapi import HTTPException
        from services.module_access import require_module
        gate = require_module("prodotti")
        coll = MagicMock()
        coll.find_one = AsyncMock(return_value={"_id": 1})
        with patch("database.organization_modules_collection", coll), \
             patch("services.feature_flag_service.is_enabled", AsyncMock(return_value=True)):
            with pytest.raises(HTTPException) as e:
                await gate(current_user={"organization_id": "org"})
            assert e.value.status_code == 403 and "spento" in e.value.detail["message"]
        with patch("database.organization_modules_collection", coll), \
             patch("services.feature_flag_service.is_enabled", AsyncMock(return_value=False)):
            assert (await gate(current_user={"organization_id": "org"}))["organization_id"] == "org"

    def test_patto_sui_prodotti(self):
        from services.dpa_guard import SELLABLE_ITEM_TYPES
        assert set(SELLABLE_ITEM_TYPES) == {"service", "event_ticket", "physical", "digital"}


# ── PF8 ─────────────────────────────────────────────────────────────────

class TestPF8Infrastruttura:
    def test_volume_private_uploads(self):
        c = (ROOT / "docker-compose.prod.yml").read_text()
        assert "- backend_private_uploads:/app/private_uploads" in c
        assert "name: ms-backend-private-uploads" in c
        assert "- backend_uploads:/app/uploads" in c, "il volume storico resta"

    def test_scheda_strumenti_dal_registro(self):
        s = (FRONTEND / "pages" / "StrumentiPage.js").read_text()
        assert "modulesAPI.listActive()" in s and "m.module_key === 'prodotti'" in s
        assert "paymentConnectionsAPI.getStatus()" in s
        # 6/10 sera (founder): in arrivo NESSUN pulsante («incassi collegati non
        # significa nulla»), solo l'etichetta in evidenza e l'anteprima
        assert "key: 'prodotti'" in s and "strumenti-collega-incassi" not in s
        assert "strumento-${s.key}-anteprima" in s and "In arrivo: è già previsto nel tuo piano." in s
        assert "'In arrivo'" in s
        assert "user?.sound_crea" in s, "lo Studio resta com'era"
