"""P4 «formato» (6/10/2026, founder: «formazione non sostituisce la
disciplina yoga, meditazione… ci dovrebbe essere un campo nuovo che indica
una seconda categoria: evento, ritiro, formazione»).

Il secondo asse delle esperienze con una data, ORTOGONALE alla disciplina:
product.metadata.formato ∈ {ritiro, evento, formazione}, facoltativo.
Vincolo del founder: gli eventi sono live e funzionano → ogni tocco e'
additivo. Le guardie qui sotto lo tengono vero:

  FM1  schema: le 15 discipline identiche; formato assente accettato;
       fuori lista rifiutato dallo schema; validate_metadata conserva le
       chiavi del wizard (payment_plan ecc.) e il formato
  FM2  wizard: payload SENZA formato → creato come prima (niente formato
       in archivio); con formato → salvato; fuori lista → 422 e nessuna
       riga lasciata a meta'
  FM3  PATCH prodotto: formato fuori lista → 422 (validate_metadata da
       solo l'avrebbe conservato); valido → scritto; il duplica lo porta
  FM4  /public/retreats: `formato` sulle card (None sulle righe vecchie),
       filtro ?formato=, conteggi `formati` solo con edizioni, un formato
       sconosciuto = lista vuota (mai 500); senza filtro le righe senza
       formato restano in lista
  FM5  superfici: tre carte nel wizard, selettore nel pannello, filtro
       «Tipo» ed etichetta su /esperienze, script di mappatura, landing
"""
from __future__ import annotations

import asyncio
import os
import sys
import uuid
from pathlib import Path

import pytest

os.environ.setdefault("JWT_SECRET_KEY", "test")
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_dummy")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_database")

BACKEND = Path(__file__).resolve().parents[1]
FRONTEND = BACKEND.parent / "frontend" / "src"
sys.path.insert(0, str(BACKEND))

# UN solo event loop per modulo, creato PRIMA di importare database: il
# client Mongo si lega al loop corrente e un asyncio.run() per test lo
# lascerebbe su un loop chiuso («Event loop is closed»).
_LOOP = asyncio.new_event_loop()
asyncio.set_event_loop(_LOOP)

from database import (  # noqa: E402
    event_occurrences_collection, event_ticket_tiers_collection,
    organizations_collection, products_collection, stores_collection,
)

PREFIX = "test_fm_"
ORG = PREFIX + "org"


def _run(coro):
    """Il client motor memorizza il PRIMO loop che lo usa (core.io_loop):
    nella suite intera quel loop e' di un altro modulo e a quel punto e'
    chiuso («Event loop is closed»). Per la durata della coroutine il
    client lavora sul loop di questo modulo, poi si rimette com'era."""
    import database as _db
    prima = getattr(_db.client, "_io_loop", None)
    _db.client._io_loop = _LOOP
    try:
        return _LOOP.run_until_complete(coro)
    finally:
        _db.client._io_loop = prima


async def _pulisci():
    for c in (event_occurrences_collection, event_ticket_tiers_collection,
              products_collection, stores_collection):
        await c.delete_many({"organization_id": {"$regex": f"^{PREFIX}"}})
    await organizations_collection.delete_many({"id": {"$regex": f"^{PREFIX}"}})


def _user():
    return {"organization_id": ORG, "id": "u1", "email": "fm@example.com"}


def _body(metadata=None, start="2027-10-24T09:00:00", end="2027-10-24T18:00:00", name="Corso Reiki I livello"):
    return {
        "product": {"name": name, "category": "reiki", "unit_price": 150.0,
                    "price_mode": "fixed", "transaction_mode": "request",
                    "is_published": True,
                    **({"metadata": metadata} if metadata is not None else {})},
        "occurrence": {"start_at": start, "end_at": end, "capacity": 12,
                       "venue_name": "Sala", "city": "Bari", "country": "IT",
                       "status": "draft"},
        "tiers": [],
    }


async def _wizard(body):
    from routers.event_occurrences import create_event_wizard, EventWizardPayload
    import services.dpa_guard as dpa
    # il limitatore (slowapi) pretende una Request vera: si chiama la funzione nuda
    nuda = getattr(create_event_wizard, "__wrapped__", create_event_wizard)
    # il patto DPA (PV7) e' un cancello a parte, provato altrove: qui si apre
    vero = dpa.require_dpa_acknowledged

    async def aperto(_org):
        return None
    dpa.require_dpa_acknowledged = aperto
    try:
        return await nuda(None, EventWizardPayload(**body), current_user=_user())
    finally:
        dpa.require_dpa_acknowledged = vero


async def _lista(**kw):
    """Chiamata diretta all'endpoint: i default Query(...) sono FieldInfo,
    non None, quindi si passano TUTTI i parametri espliciti."""
    from routers.public import list_public_retreats
    base = dict(request=None, category=None, formato=None, region=None, lat=None, lng=None,
                radius_km=100, country=None, month=None, price_max=None, limit=60,
                offset=0, lang=None, preview=1)
    base.update(kw)
    return await list_public_retreats(**base)


# ── FM1 ─────────────────────────────────────────────────────────────────

class TestFM1Schema:
    def test_le_quindici_discipline_non_cambiano(self):
        from models.retreat_taxonomy import RETREAT_CATEGORIES, FORMATI_ESPERIENZA
        assert list(RETREAT_CATEGORIES) == [
            "yoga", "meditazione", "breathwork", "suono", "reiki", "costellazioni",
            "astrologia", "ayurveda", "tantra", "detox", "cammini", "femminile",
            "crescita", "massaggio", "aziendale"]
        assert "formazione" not in RETREAT_CATEGORIES, "il formato NON e' una disciplina"
        assert list(FORMATI_ESPERIENZA) == ["ritiro", "evento", "formazione"]

    def test_schema_facoltativo_e_stretto(self):
        from models.product_metadata import EventTicketMetadata, validate_metadata_for_type
        assert EventTicketMetadata().model_dump(exclude_none=True) == {}
        assert EventTicketMetadata(formato="formazione").formato == "formazione"
        with pytest.raises(Exception):
            EventTicketMetadata(formato="corso")
        # il wizard passa payment_plan e campi partecipante come extra: restano
        out = validate_metadata_for_type("event_ticket", {
            "payment_plan": {"mode": "full"}, "requires_attendee_details": True, "formato": "ritiro"})
        assert out["payment_plan"] == {"mode": "full"} and out["requires_attendee_details"] is True
        assert out["formato"] == "ritiro"

    def test_helper_errore_e_suggerimento(self):
        from models.retreat_taxonomy import errore_formato, formato_suggerito
        assert errore_formato(None) is None and errore_formato({}) is None
        assert errore_formato({"formato": None}) is None
        assert "Formato non valido" in errore_formato({"formato": "corso"})
        assert formato_suggerito("2026-11-27T10:00", "2026-11-29T16:00") == "ritiro"
        assert formato_suggerito("2026-10-25T09:00", "2026-10-25T18:00") == "evento"
        assert formato_suggerito("2026-10-25T09:00", None) == "evento"


# ── FM2 wizard ──────────────────────────────────────────────────────────

class TestFM2Wizard:
    def test_senza_formato_come_prima(self):
        async def go():
            await _pulisci()
            res = await _wizard(_body())
            prod = await products_collection.find_one({"id": res["product_id"]}, {"_id": 0})
            assert prod["category"] == "reiki"
            assert "formato" not in (prod.get("metadata") or {})
            await _pulisci()
        _run(go())

    def test_con_formato_salvato(self):
        async def go():
            await _pulisci()
            res = await _wizard(_body({"formato": "formazione", "requires_attendee_details": False}))
            prod = await products_collection.find_one({"id": res["product_id"]}, {"_id": 0})
            assert prod["metadata"]["formato"] == "formazione"
            assert prod["metadata"]["requires_attendee_details"] is False
            await _pulisci()
        _run(go())

    def test_fuori_lista_422_senza_righe(self):
        from fastapi import HTTPException

        async def go():
            await _pulisci()
            with pytest.raises(HTTPException) as e:
                await _wizard(_body({"formato": "corso"}))
            assert e.value.status_code == 422
            assert await products_collection.count_documents({"organization_id": ORG}) == 0
            assert await event_occurrences_collection.count_documents({"organization_id": ORG}) == 0
            await _pulisci()
        _run(go())

    def test_il_duplica_porta_il_formato(self):
        src = (BACKEND / "routers" / "event_occurrences.py").read_text()
        i = src.index("product_clean = {")
        assert '"formato"' in src[i:i + 1600]


# ── FM3 PATCH prodotto ──────────────────────────────────────────────────

class TestFM3Patch:
    def test_patch_valida_e_rifiuta(self):
        from fastapi import HTTPException, Response
        from routers.products import update_product
        from models.product import ProductUpdate

        async def go():
            await _pulisci()
            res = await _wizard(_body())
            pid = res["product_id"]
            with pytest.raises(HTTPException) as e:
                await update_product(pid, ProductUpdate(metadata={"formato": "corso"}),
                                     Response(), current_user=_user())
            assert e.value.status_code == 422
            prod = await products_collection.find_one({"id": pid}, {"_id": 0})
            assert "formato" not in (prod.get("metadata") or {}), "niente valore inventato in archivio"
            await update_product(pid, ProductUpdate(metadata={"formato": "evento", "terms_content": None}),
                                 Response(), current_user=_user())
            prod = await products_collection.find_one({"id": pid}, {"_id": 0})
            assert prod["metadata"]["formato"] == "evento"
            await _pulisci()
        _run(go())


# ── FM4 listing pubblico ────────────────────────────────────────────────

async def _semina_listing():
    """Un'org con store pubblico e tre esperienze future su richiesta:
    una «formazione», una «ritiro», una SENZA formato (nata prima)."""
    await _pulisci()
    await organizations_collection.insert_one({
        "id": ORG, "name": "Studio FM", "is_active": True, "is_sample": False,
        "exclude_from_listings": False, "store_settings": {}})
    await stores_collection.insert_one({
        "id": PREFIX + "store", "organization_id": ORG, "slug": "studio-fm",
        "is_published": True, "is_active": True, "visibility": "public"})
    righe = [("formazione", "Corso Reiki", "2027-10-24T09:00:00", "2027-10-24T18:00:00"),
             ("ritiro", "Ritorno alle origini", "2027-11-27T10:00:00", "2027-11-29T16:00:00"),
             (None, "Serata di meditazione", "2027-10-30T20:00:00", "2027-10-30T22:00:00")]
    for fmt, nome, s, e in righe:
        pid = PREFIX + uuid.uuid4().hex[:8]
        await products_collection.insert_one({
            "id": pid, "organization_id": ORG, "item_type": "event_ticket", "name": nome,
            "category": "reiki" if fmt == "formazione" else "meditazione",
            "unit_price": 100, "is_active": True, "is_published": True,
            "transaction_mode": "request", "price_mode": "fixed",
            "metadata": ({"formato": fmt} if fmt else {})})
        await event_occurrences_collection.insert_one({
            "id": PREFIX + uuid.uuid4().hex[:8], "organization_id": ORG, "product_id": pid,
            "product_name": nome, "slug": nome.lower().replace(" ", "-"),
            "status": "published", "start_at": s, "end_at": e, "city": "Bari", "country": "IT"})


class TestFM4Listing:
    def test_card_filtro_e_conteggi(self):
        async def go():
            await _semina_listing()
            tutti = await _lista()
            miei = [i for i in tutti["items"] if i["org_slug"] == "studio-fm"]
            assert len(miei) == 3, "senza filtro le righe senza formato restano in lista"
            per_titolo = {i["title"]: i["formato"] for i in miei}
            assert per_titolo == {"Corso Reiki": "formazione", "Ritorno alle origini": "ritiro",
                                  "Serata di meditazione": None}
            assert tutti["formati"]["formazione"]["count"] >= 1
            assert tutti["formati"]["ritiro"]["count"] >= 1
            assert tutti["formati"]["formazione"]["label"] == "Formazione"
            assert "categories" in tutti  # la chiave storica resta
            solo_f = await _lista(formato="formazione")
            miei_f = [i for i in solo_f["items"] if i["org_slug"] == "studio-fm"]
            assert [i["title"] for i in miei_f] == ["Corso Reiki"]
            assert all(i["formato"] == "formazione" for i in solo_f["items"])
            ignoto = await _lista(formato="corso")
            assert ignoto["items"] == [] and "formati" in ignoto
            await _pulisci()
        _run(go())

    def test_conteggi_formati_solo_con_edizioni(self):
        from routers.public import _conteggi_esperienze, _categorie_con_ritiri

        async def go():
            await _semina_listing()
            c = await _conteggi_esperienze(1)
            assert set(c) == {"categories", "formati"}
            assert "evento" not in c["formati"] or c["formati"]["evento"]["count"] > 0
            assert c["categories"] == await _categorie_con_ritiri(1)
            await _pulisci()
        _run(go())


# ── FM5 superfici ───────────────────────────────────────────────────────

class TestFM5Superfici:
    def test_wizard_tre_carte_e_suggerimento(self):
        w = (FRONTEND / "features" / "events" / "EventWizard.js").read_text()
        for s in ("wizard-formato", "suggerisciFormato(where.start_at, where.end_at)",
                  "formato: base.formato || null", "errors.formato", "formati_esperienza",
                  "get('formato')"):
            assert s in w, s
        # la disciplina resta obbligatoria e separata
        assert "errors.category" in w and "category: base.category" in w

    def test_pannello_evento(self):
        d = (FRONTEND / "features" / "events" / "EventDashboardPage.js").read_text()
        assert "dash-formato-select" in d
        assert "formato: occ.product_metadata?.formato || ''" in d
        assert "...(productForm.formato ? { formato: productForm.formato } : {})" in d

    def test_esperienze_filtro_tipo_ed_etichetta(self):
        p = (FRONTEND / "features" / "storefront" / "RetreatsCalendarPage.js").read_text()
        assert 'data-testid="esp-f-tipo"' in p
        assert "params.get('tipo')" in p and "q.formato = formato" in p
        assert 'data-testid="esp-card-formato"' in p
        assert 'data-testid="esp-f-categoria"' in p, "il filtro disciplina resta"
        import json
        loc = json.loads((FRONTEND / "locales" / "it" / "landings.json").read_text())
        assert loc["calendar"]["allFormats"] == "Tutti i tipi"
        assert loc["calendar"]["formato"] == {"ritiro": "Ritiro", "evento": "Evento", "formazione": "Formazione"}

    def test_landing_e_tassonomie_espongono_il_formato(self):
        pub = (BACKEND / "routers" / "public.py").read_text()
        assert "formato: Optional[str] = None" in pub[pub.index("class PublicEventProduct("):][:1200]
        prod = (BACKEND / "routers" / "products.py").read_text()
        assert '"formati_esperienza": FORMATI_ESPERIENZA' in prod

    def test_script_di_mappatura(self):
        s = (BACKEND / "scripts" / "formato_esperienze.py").read_text()
        for frag in ("--lista", "--imposta", "--scrivi", "metadata.formato", "FORMATI_ESPERIENZA"):
            assert frag in s
