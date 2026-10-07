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
        # 6/10 sera (founder): i Prodotti escono in ANTEPRIMA finche' non da' il
        # via: interruttore in features/prodotti/stato.js (false), scheda oscurata
        # con l'anteprima in Strumenti, rotte /prodotti/* chiuse dal cancello
        stato = (FRONTEND / "features" / "prodotti" / "stato.js").read_text()
        assert "export const PRODOTTI_UI_PRONTA = false" in stato
        strumenti = (FRONTEND / "pages" / "StrumentiPage.js").read_text()
        assert "from '../features/prodotti/stato'" in strumenti and "const PRODOTTI_UI_PRONTA" not in strumenti
        assert "strumento-${s.key}-anteprima" in strumenti and "s.inArrivo ? 'opacity-" in strumenti
        assert "<ProdottiGate>" in app and 'Navigate to="/strumenti" replace' in app
        # il demo e' pilota: continua a testare in locale con l'anteprima chiusa
        assert "PILOTI_PRODOTTI = ['admin@demo.com']" in stato and "prodottiAperti(user)" in app
        assert "prodottiAperti(user)" in strumenti and "p-4 md:p-8" in strumenti
        assert app.count("<ProdottiGate>") == 4
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


# ── Consolidamento pre-live (6/10/2026 sera) ────────────────────────────────

class TestConsolidamento:
    def test_verifica_pagamento_pubblica(self):
        pub = (BACKEND / "routers" / "public.py").read_text()
        assert '@router.post("/orders/{order_id}/verifica-pagamento")' in pub
        corpo = pub[pub.index('@router.post("/orders/{order_id}/verifica-pagamento")'):pub.index('@router.get("/orders/{order_id}/status"')]
        assert "verify_commerce_order_payment(order_id, order[\"organization_id\"])" in corpo
        assert '"already_reconciled"' in corpo and '"session_not_found"' in corpo
        assert 'limiter.limit("10/minute")' in corpo
        fe = (FRONTEND / "features" / "storefront" / "CheckoutResultPage.js").read_text()
        # una sola verifica dalla pagina (prima erano 3 in concorrenza → due
        # «Nuovo ordine pagato» all'operatore); il server ha comunque il lucchetto
        assert "storefrontAPI.verifyOrderPayment(orderId)" in fe and "verifiedRef.current < 1" in fe
        assert "_VERIFICHE_IN_CORSO" in corpo and "async with lock:" in corpo
        assert 'data-testid="checkout-file-pronto"' in fe and "includes('digital')" in fe
        assert "item_types: List[str] = []" in pub and '"items.item_type": 1' in pub

    def test_riconciliazione_idempotente_sulla_stessa_session(self):
        """Stessa session due volte (verifica + webhook, o due webhook): la
        seconda e' un no-op, senza seconda conferma ne' seconda email."""
        src = (BACKEND / "services" / "payment_checkout_service.py").read_text()
        corpo = src[src.index("async def reconcile_checkout_event"):]
        assert '"action": "already_collected"' in corpo
        assert 'order.get("payment_intent") == "collected"' in corpo
        assert "stored_ref == session_id" in corpo
        # il guardiano viene PRIMA di confirm_order e di notify_merchant_new_order
        assert corpo.index('"already_collected"') < corpo.index("confirm_order(")
        assert "verifica-pagamento" in (FRONTEND / "api" / "storefront.js").read_text()

    def test_email_operatore_ordine_pagato(self):
        src = (BACKEND / "services" / "order_email_service.py").read_text()
        corpo = src[src.index("async def notify_merchant_new_order("):src.index("# ── Customer: Order Confirmed")]
        for s in ('order.get("payment_intent") == "collected"', '"order_merchant_paid_subject"', '"order_merchant_ship_to"',
                  '"order_merchant_pickup"', '"order_merchant_digital"', '"order_merchant_phone"', '"order_merchant_paid_cta"'):
            assert s in corpo, s
        assert '"order_merchant_draft_hint"' in corpo, "la variante richiesta (non pagata) resta"
        from services.email_service import EMAIL_TRANSLATIONS
        it = EMAIL_TRANSLATIONS["it"]
        assert it["order_merchant_paid_subject"] == "Nuovo ordine pagato — {customer_name}"
        assert "Non devi fare nulla" in it["order_merchant_digital"]
        assert "bozza" not in it["order_merchant_paid_body"]

    def test_email_cliente_dice_cosa_succede(self):
        src = (BACKEND / "services" / "order_email_service.py").read_text()
        corpo = src[src.index("async def notify_customer_order_confirmed("):src.index("async def notify_customer_order_cancelled(")]
        for s in ('"order_confirmed_body_digital"', '"order_confirmed_body_shipping"', '"order_confirmed_body_pickup"',
                  '"order_confirmed_cta_files"', 'tipi <= {"digital"}'):
            assert s in corpo, s
        from services.email_service import EMAIL_TRANSLATIONS
        it = EMAIL_TRANSLATIONS["it"]
        assert "I miei file" in it["order_confirmed_body_digital"]
        for k in ("order_confirmed_body_digital", "order_confirmed_body_shipping", "order_confirmed_body_pickup",
                  "order_merchant_paid_body", "order_merchant_digital", "order_merchant_pickup"):
            for proibita in ("con successo", "click", "Ti contatteremo", "storefront"):
                assert proibita not in it[k], (k, proibita)

    def test_ordini_mostrano_i_contatti(self):
        p = (FRONTEND / "features" / "orders" / "OrdersPage.js").read_text()
        assert 'data-testid="ordine-contatti"' in p and "o.customer_email" in p and "o.contact_phone" in p


# ── DP (6/10/2026 sera) — design del modulo + la pagina del prodotto ──

class TestDesignDP:
    def test_landing_pubblica_dal_public_slug(self):
        src = (BACKEND / "routers" / "public.py").read_text()
        assert '@router.get("/prodotto/{org_slug}/{slug}", response_model=PublicProdottoLanding)' in src
        corpo = src[src.index('async def get_prodotto_landing'):src.index('async def _operator_prodotti')]
        # risolve dal public_slug come il profilo, MAI dallo store legacy; campioni fuori
        assert '"public_slug": org_slug' in corpo and 'org.get("is_sample")' in corpo
        assert "stores_collection" not in corpo
        assert "org_has_public_home" in corpo
        # la stessa lista del profilo: se non e' sul profilo, non ha una pagina
        assert "righe = await _operator_prodotti(org[\"id\"])" in corpo
        assert '"altri"' in src[src.index('class PublicProdottoLanding'):src.index('async def get_prodotto_landing')] or "altri=[" in corpo

    def test_rotta_registrata_e_meta_per_i_bot(self):
        import json
        reg = json.loads((BACKEND / "config" / "rotte.json").read_text())
        assert "prodotto" in reg["pubblica"] and "prodotto" in reg["solo_con_slug"]
        shell = (BACKEND / "routers" / "seo_shell.py").read_text()
        assert 'if head == "prodotto" and len(parts) >= 3:' in shell and "async def _meta_prodotto" in shell
        corpo = shell[shell.index("async def _meta_prodotto"):shell.index("async def _meta_destination")]
        assert '"@type": "Product"' in corpo and 'f"{base}/prodotto/{org_slug}/{product_slug}"' in corpo
        seo = (BACKEND / "routers" / "seo.py").read_text()
        assert '"physical": "prodotto", "digital": "prodotto"' in seo
        nginx = (BACKEND.parent / "deploy" / "nginx" / "nginx.conf").read_text()
        assert "prodotto" in nginx
        app = (FRONTEND / "App.js").read_text()
        assert 'path="/prodotto/:org_slug/:slug"' in app and "ProdottoLandingPage" in app
        api = (FRONTEND / "api" / "storefront.js").read_text()
        assert "getProdottoLanding" in api and "/api/public/prodotto/${orgSlug}/${slug}" in api

    def test_la_pagina_del_prodotto(self):
        l = (FRONTEND / "features" / "storefront" / "ProdottoLandingPage.js").read_text()
        for t in ("prodotto-landing", "prodotto-landing-compra", "prodotto-landing-condividi", "prodotto-landing-come",
                  "prodotto-landing-acquisto", "prodotto-landing-racconto", "prodotto-landing-altri", "prodotto-landing-barra",
                  "prodotto-landing-404"):
            assert f'data-testid="{t}"' in l, t
        assert "InlineProdottoCheckout" in l and "useSeoMeta" in l
        # niente etichetta di tipo in pagina (founder): il tipo decide solo cosa si spiega
        assert "'Digitale'" not in l and "'Fisico'" not in l
        assert "navigator.share" in l

    def test_profilo_compra_e_scopri_di_piu_senza_etichetta(self):
        p = (FRONTEND / "features" / "storefront" / "OperatorProfilePage.js").read_text()
        sez = p[p.index('data-testid="profile-prodotti"'):p.index("<Gallery")]
        assert 'data-testid="prodotto-cta"' in sez and 'data-testid="prodotto-info"' in sez
        assert "Scopri di più" in sez and "'Compra'" in sez
        assert "`/prodotto/${org_slug}/${pr.slug" in sez
        assert "{pr.tipo}" not in sez, "l'etichetta Digitale/Fisico e' uscita dal profilo"
        assert 'data-testid="prodotto-inline"' in sez and 'data-testid="prodotto-card"' in sez

    def test_il_kit_del_gestionale(self):
        ui = (FRONTEND / "features" / "prodotti" / "ui.js").read_text()
        for n in ("export function Campo", "export function Scheda", "export function Bottone", "export function Ragioni",
                  "export function AnteprimaProdotto", "export function LinkPagina", "export function SceltaImmagine",
                  "export function classePasso", "export function urlPagina"):
            assert n in ui, n
        assert "/${prefisso}/${orgSlug}/${slug}" in ui and "prefisso = 'prodotto'" in ui   # AC3: lo stesso link serve i corsi
        # l'anteprima non ha l'etichetta di tipo
        ant = ui[ui.index("export function AnteprimaProdotto"):ui.index("export function urlPagina")]
        assert "Digitale" not in ant and "Fisico" not in ant
        for f in ("ProdottiPage.js", "ProdottoPage.js", "ProdottoDigitaleWizard.js", "ProdottoFisicoWizard.js"):
            src = (FRONTEND / "features" / "prodotti" / f).read_text()
            assert "from './ui'" in src, f
            assert "p-4 md:p-8" in src, f
        pag = (FRONTEND / "features" / "prodotti" / "ProdottoPage.js").read_text()
        assert 'data-testid="prodotto-racconto"' in pag and "LinkPagina" in pag and "long_description" in pag
        assert 'data-testid="dg-racconto"' in (FRONTEND / "features" / "prodotti" / "ProdottoDigitaleWizard.js").read_text()
        assert 'data-testid="pf-racconto"' in (FRONTEND / "features" / "prodotti" / "ProdottoFisicoWizard.js").read_text()
        lista = (FRONTEND / "features" / "prodotti" / "ProdottiPage.js").read_text()
        assert "copiaLink" in lista and "{p.tipo_etichetta}" not in lista

    def test_public_slug_nel_gestionale(self):
        src = (BACKEND / "routers" / "prodotti.py").read_text()
        assert '"public_slug": (org or {}).get("public_slug")' in src
        assert '"public_slug": pre.get("public_slug")' in src


# ── GL (6/10/2026 notte) — la galleria: piu' foto per prodotto ──

class TestGalleriaGL:
    def test_endpoint_e_modello(self):
        src = (BACKEND / "routers" / "prodotti.py").read_text()
        for r in ('@router.post("/{product_id}/foto")', '@router.delete("/{product_id}/foto")',
                  '@router.post("/{product_id}/foto/principale")', "GALLERIA_MAX = 8", "def _galleria(prod: dict)"):
            assert r in src, r
        # image_url = la principale, metadata.galleria = le altre; la riga del gestionale le espone tutte
        assert '"metadata.galleria": nuove[1:]' in src and '"galleria": _galleria(prod)' in src
        # le rotte fisse /foto vengono PRIMA del PATCH /{product_id}
        assert src.index('@router.post("/{product_id}/foto")') < src.index('@router.patch("/{product_id}")')
        from routers.prodotti import _galleria
        assert _galleria({"image_url": "a", "metadata": {"galleria": ["b", "a", "c"]}}) == ["a", "b", "c"]
        assert _galleria({"image_url": None, "metadata": {}}) == []
        pub = (BACKEND / "routers" / "public.py").read_text()
        assert '"metadata.galleria": 1' in pub and '"galleria": [u for u in [r.get("image_url")]' in pub
        assert '"file_size_bytes", "galleria")' in pub

    def test_gestionale_e_wizard(self):
        api = (FRONTEND / "api" / "prodotti.js").read_text()
        for n in ("aggiungiFoto", "togliFoto", "fotoPrincipale", "compressImage"):
            assert n in api, n
        ui = (FRONTEND / "features" / "prodotti" / "ui.js").read_text()
        assert "export function GestoreFoto" in ui and 'data-testid="prodotto-foto"' in ui and "multiple" in ui
        pag = (FRONTEND / "features" / "prodotti" / "ProdottoPage.js").read_text()
        assert "<GestoreFoto" in pag and "SceltaImmagine" not in pag
        for f in ("ProdottoDigitaleWizard.js", "ProdottoFisicoWizard.js"):
            w = (FRONTEND / "features" / "prodotti" / f).read_text()
            assert "coverFiles" in w and "aggiungiFoto" in w and "<SceltaImmagine multiple" in w, f

    def test_landing_sfoglia_e_profilo_proporzionato(self):
        l = (FRONTEND / "features" / "storefront" / "ProdottoLandingPage.js").read_text()
        assert "function Galleria(" in l and 'data-testid="prodotto-landing-galleria"' in l
        for t in ("galleria-prev", "galleria-next", "galleria-miniature"):
            assert f'data-testid="{t}"' in l, t
        assert "onTouchStart" in l and "ArrowRight" in l
        p = (FRONTEND / "features" / "storefront" / "OperatorProfilePage.js").read_text()
        sez = p[p.index('data-testid="profile-prodotti"'):p.index("<Gallery")]
        # la stessa misura delle card dei ritiri: h-36 e p-3
        assert 'className="block h-36 overflow-hidden' in sez and 'className="flex flex-1 flex-col p-3"' in sez
        assert 'className="h-36 bg-gray-100"' in p, "la card dei ritiri resta h-36"

