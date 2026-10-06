"""P1 (6/10/2026) — PRODOTTI DIGITALI: API /prodotti, lucchetti alla
pubblicazione, account obbligatorio per comprare, «I miei file», profilo.

  PD1  ragioni di pubblicazione: Stripe, patto, pagina, prezzo, file
  PD2  modelli: crea solo digital|physical, prezzo >= 0, policy nei limiti
  PD3  ordine: righe prodotto senza account Aurya → 400 prodotto_richiede_account;
       con account → l'ordine porta l'id vero (sorgente)
  PD4  rotte: /prodotti sotto require_module, /me/file, header X-Aurya-Account
  PD5  profilo pubblico: prodotti pubblicati con file, mai un digitale senza file
  PD6  upload: limite del piano letto dai tier
  PD7  frontend: pagine, wizard in tre gesti, inline checkout con account
       obbligatorio, sezione sul profilo, I miei file, scheda Strumenti attiva
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("JWT_SECRET_KEY", "test")
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_dummy")

BACKEND = Path(__file__).resolve().parents[1]
FRONTEND = BACKEND.parent / "frontend" / "src"
sys.path.insert(0, str(BACKEND))


class TestPD1Ragioni:
    def test_tutti_i_lucchetti(self):
        from routers.prodotti import _ragioni_pubblicazione
        pre_ok = {"stripe_pronto": True, "patto": True, "pagina_pubblica": True}
        dig = {"item_type": "digital", "unit_price": 12, "metadata": {"download_filename": "g.pdf"}}
        assert _ragioni_pubblicazione(dig, pre_ok) == []
        r = _ragioni_pubblicazione({"item_type": "digital", "unit_price": 0, "metadata": {}},
                                   {"stripe_pronto": False, "patto": False, "pagina_pubblica": False})
        assert len(r) == 5
        assert any("Stripe" in x for x in r) and any("patto" in x for x in r)
        assert any("prezzo" in x for x in r) and any("file" in x for x in r)
        fis = {"item_type": "physical", "unit_price": 20, "metadata": {}}
        assert _ragioni_pubblicazione(fis, pre_ok) == [], "il fisico non ha bisogno del file"

    def test_riga(self):
        from routers.prodotti import _riga
        p = {"id": "p1", "name": "Guida", "item_type": "digital", "unit_price": 12,
             "metadata": {"download_filename": "g.pdf", "download_size_bytes": 10, "max_downloads_per_delivery": 5}}
        r = _riga(p, {"p1": 3}, {"stripe_pronto": True, "patto": True, "pagina_pubblica": True})
        assert r["file"]["filename"] == "g.pdf" and r["venduti_30gg"] == 3 and r["tipo_etichetta"] == "Digitale"
        assert r["max_downloads_per_delivery"] == 5 and r["ragioni_pubblicazione"] == []


class TestPD2Modelli:
    def test_create(self):
        from routers.prodotti import ProdottoCreate
        assert ProdottoCreate(item_type="digital", name="G", unit_price=12).item_type == "digital"
        with pytest.raises(Exception):
            ProdottoCreate(item_type="service", name="G", unit_price=12)
        with pytest.raises(Exception):
            ProdottoCreate(item_type="digital", name="G", unit_price=-1)
        with pytest.raises(Exception):
            ProdottoCreate(item_type="digital", name="G", unit_price=1, max_downloads_per_delivery=0)

    def test_router_sotto_modulo(self):
        src = (BACKEND / "routers" / "prodotti.py").read_text()
        assert '_gate = require_module("prodotti")' in src
        for rotta in ('@router.get("")', '@router.post("", status_code=status.HTTP_201_CREATED)',
                      '@router.post("/{product_id}/pubblica")', '@router.post("/{product_id}/ritira")',
                      '@router.delete("/{product_id}"', '@router.get("/{product_id}/vendite")'):
            assert rotta in src, rotta
        assert src.count("_=Depends(_gate)") >= 7
        assert 'transaction_mode="direct"' in src and 'price_mode="fixed"' in src and "is_published=False" in src
        assert 'app.include_router(prodotti_router.router, prefix="/api")' in (BACKEND / "server.py").read_text()


class TestPD3Ordine:
    def test_gate_e_timbro(self):
        src = (BACKEND / "services" / "order_creation_service.py").read_text()
        assert "platform_account_id: Optional[str] = None," in src
        assert '"error": "prodotto_richiede_account"' in src
        assert 'in ("digital", "physical")' in src
        assert '{"$set": {"platform_account_id": platform_account_id}}' in src
        assert "if order and not order.get(\"platform_account_id\"):" in src, "il link per email resta per gli ospiti"
        pub = (BACKEND / "routers" / "public.py").read_text()
        assert 'request.headers.get("x-aurya-account", "")' in pub
        assert '_pl.get("type") == "platform"' in pub
        assert "platform_account_id=platform_account_id" in pub


class TestPD4Account:
    def test_me_file(self):
        src = (BACKEND / "routers" / "platform_accounts.py").read_text()
        assert '@router.get("/me/file")' in src
        corpo = src[src.index('@router.get("/me/file")'):src.index('@router.get("/me/export")')]
        assert '{"platform_account_id": account["id"]}' in corpo
        assert '"status": {"$ne": "cancelled"}' in corpo
        assert 'f"/d/{r[\'access_token\']}"' in corpo
        for riservato in ("fee", "cost", "notes"):
            assert riservato not in corpo.replace("download_count", ""), riservato


class TestPD5Profilo:
    @pytest.mark.asyncio
    async def test_prodotti_del_profilo(self):
        from routers.public import _operator_prodotti
        righe = [
            {"id": "a", "name": "Guida", "slug": "guida", "item_type": "digital", "unit_price": 12,
             "metadata": {"download_filename": "guida.pdf", "download_size_bytes": 10}},
            {"id": "b", "name": "Senza file", "slug": "sf", "item_type": "digital", "unit_price": 5, "metadata": {}},
            {"id": "c", "name": "Kit", "slug": "kit", "item_type": "physical", "unit_price": 30, "stock_quantity": 0},
            {"id": "d", "name": "Libro", "slug": "libro", "item_type": "physical", "unit_price": 20, "stock_quantity": None},
            {"id": "e", "name": "Su richiesta", "slug": "sr", "item_type": "physical", "unit_price": 9, "transaction_mode": "request"},
        ]
        cursor = MagicMock()
        cursor.sort.return_value = cursor
        cursor.to_list = AsyncMock(return_value=righe)
        coll = MagicMock()
        coll.find.return_value = cursor
        with patch("database.products_collection", coll):
            out = await _operator_prodotti("org1")
        assert [r["product_id"] for r in out] == ["a", "d"], "niente digitali senza file, niente fisici esauriti"
        assert out[0]["tipo"] == "Digitale" and out[0]["file_ext"] == "pdf"
        assert out[1]["tipo"] == "Fisico"
        q = coll.find.call_args.args[0]
        assert q["is_published"] is True and "transaction_mode" not in q, "il filtro direct e' in Python (guardia Gt1b)"
        assert q["item_type"] == {"$in": ["digital", "physical"]}
        pub = (BACKEND / "routers" / "public.py").read_text()
        assert '"prodotti": await _operator_prodotti(org_id),' in pub


class TestPD6Upload:
    def test_limite_del_piano(self):
        src = (BACKEND / "routers" / "products.py").read_text()
        corpo = src[src.index("async def upload_digital_file("):src.index("_SALES_STATS_CACHE")]
        assert 'get_module_entitlements(org_id, "prodotti")' in corpo
        assert '.get("max_file_mb")' in corpo
        assert "digital_storage.delete_digital_file(org_id, product_id)" in corpo


class TestPD7Frontend:
    def test_pagine_e_rotte(self):
        app = (FRONTEND / "App.js").read_text()
        for r in ('path="/prodotti"', 'path="/prodotti/nuovo/digitale"', 'path="/prodotti/:id"'):
            assert r in app, r
        assert (FRONTEND / "features" / "prodotti" / "ProdottiPage.js").exists()
        w = (FRONTEND / "features" / "prodotti" / "ProdottoDigitaleWizard.js").read_text()
        for s in ("data-testid={`passo-${p.key}`}", "{ key: 'cosa'", "{ key: 'file'", "{ key: 'pubblica'",
                  "DpaPactDialog", "non_pubblicabile", "onUploadProgress"):
            assert s in w, s
        assert "const PRODOTTI_UI_PRONTA = true" in (FRONTEND / "pages" / "StrumentiPage.js").read_text()
        assert "'digital'" in (FRONTEND / "constants" / "itemTypes.js").read_text()

    def test_acquisto_con_account(self):
        c = (FRONTEND / "features" / "storefront" / "components" / "checkout" / "CheckoutForm.jsx").read_text()
        assert "richiedeAccount = false" in c
        assert "(richiedeAccount && !platformLoggedIn)" in c
        assert 'data-testid="prodotto-serve-account"' in c
        i = (FRONTEND / "features" / "storefront" / "components" / "checkout" / "InlineProdottoCheckout.jsx").read_text()
        assert "richiedeAccount" in i and "useCheckoutForm({" in i and "channel: 'store'" in i
        s = (FRONTEND / "api" / "storefront.js").read_text()
        assert "'X-Aurya-Account': `Bearer ${tk}`" in s
        p = (FRONTEND / "features" / "storefront" / "OperatorProfilePage.js").read_text()
        assert 'data-testid="profile-prodotti"' in p and "InlineProdottoCheckout" in p
        assert 'data-testid="profile-listino"' in p, "il listino resta"
        a = (FRONTEND / "features" / "account" / "AccountPage.js").read_text()
        assert "/platform/me/file" in a and 'data-testid="account-file"' in a


# ── P2 (6/10/2026 sera) — fisici: consegna, commissione in chiaro, niente formazione qui ──

class TestP2Fisici:
    def test_consegna_e_commissione_nel_router(self):
        src = (BACKEND / "routers" / "prodotti.py").read_text()
        assert '@router.get("/consegna")' in src and '@router.put("/consegna")' in src
        # le rotte fisse vengono PRIMA di /{product_id}: altrimenti «consegna» sarebbe un id
        assert src.index('@router.get("/consegna")') < src.index('@router.get("/{product_id}")')
        assert "Scegli almeno un modo" in src
        assert "update_store_settings(StoreSettingsUpdate(fulfillment_modes=modi)" in src
        assert '"label": "Spedizione"' in src
        assert '"commissione": await _commissione(org_id)' in src and '"consegna": await _consegna(org_id)' in src

    def test_modello_consegna(self):
        from routers.prodotti import ConsegnaUpdate
        c = ConsegnaUpdate(ritiro=True, spedizione=True, costo_spedizione=6, soglia_gratis=50)
        assert c.costo_spedizione == 6 and c.soglia_gratis == 50
        with pytest.raises(Exception):
            ConsegnaUpdate(spedizione=True, costo_spedizione=-1)

    def test_pagina_prodotti_senza_formazione_e_con_commissione(self):
        p = (FRONTEND / "features" / "prodotti" / "ProdottiPage.js").read_text()
        assert 'data-testid="tipologia-fisico"' in p and "/prodotti/nuovo/fisico" in p
        assert 'data-testid="tipologia-formazione"' not in p, "la formazione in presenza non e' un prodotto"
        assert 'data-testid="prodotti-nota-formazione"' in p and "events/new?formato=formazione" in p
        assert 'data-testid="prodotti-commissione"' in p
        assert "GraduationCap" not in p
        app = (FRONTEND / "App.js").read_text()
        assert 'path="/prodotti/nuovo/fisico"' in app
        w = (FRONTEND / "features" / "prodotti" / "ProdottoFisicoWizard.js").read_text()
        for s in ("{ key: 'arriva'", "pf-ritiro", "pf-spedizione", "salvaConsegna", "stock_quantity", "DpaPactDialog"):
            assert s in w, s

    def test_termini_a_principio_i_numeri_su_costi(self):
        for lang in ("it", "en", "de", "fr"):
            t = (BACKEND / "legal" / f"terms_{lang}.md").read_text()
            assert "https://aurya.life/costi" in t
            assert "15%" not in t and "15 %" not in t, f"terms_{lang}: i numeri della commissione vivono solo su /costi"
