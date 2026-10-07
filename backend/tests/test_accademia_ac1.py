"""AC1 (7/10/2026) — L'operatore: Bunny gestito da Aurya, webhook, /accademia.

Le funzioni pure si provano con vettori fissi (firma TUS, HMAC del webhook,
stati); il router e i modelli con pin e con i modelli Pydantic; il flusso
end-to-end senza chiave Bunny (503 chiaro) e' provato dal vivo in locale.
"""
import hashlib
import hmac
import json
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
FRONTEND = BACKEND.parent / "frontend" / "src"


class TestBunnyGestito:
    def test_firma_tus_come_documentata(self):
        """Bunny: SHA256(library_id + api_key + expiration_time + video_id)."""
        from services.bunny.gestito import firma_tus, credenziali_tus, TUS_ENDPOINT
        atteso = hashlib.sha256(b"123456" + b"chiave" + b"1700000000" + b"guid-1").hexdigest()
        assert firma_tus("123456", "chiave", 1700000000, "guid-1") == atteso
        cred = credenziali_tus({"library_id": "123456", "api_key": "chiave"}, "guid-1", ttl=60)
        assert cred["tus_endpoint"] == TUS_ENDPOINT == "https://video.bunnycdn.com/tusupload"
        h = cred["headers"]
        assert set(h) == {"AuthorizationSignature", "AuthorizationExpire", "VideoId", "LibraryId"}
        assert h["VideoId"] == "guid-1" and h["LibraryId"] == "123456"
        # la chiave API NON viaggia
        assert "chiave" not in json.dumps(cred)
        assert h["AuthorizationSignature"] == firma_tus("123456", "chiave", int(h["AuthorizationExpire"]), "guid-1")

    def test_firma_webhook_hmac_sha256_tempo_costante(self):
        from services.bunny.gestito import firma_webhook_valida
        corpo = b'{"VideoLibraryId":1,"VideoGuid":"g","Status":3}'
        buona = hmac.new(b"ro-key", corpo, hashlib.sha256).hexdigest()
        assert firma_webhook_valida(corpo, buona, "ro-key")
        assert firma_webhook_valida(corpo, buona.upper(), "ro-key")
        assert not firma_webhook_valida(corpo, buona, "altra")
        assert not firma_webhook_valida(corpo, None, "ro-key")
        assert not firma_webhook_valida(corpo, buona, None)

    def test_stati_e_impostazioni_di_costo(self):
        from services.bunny.gestito import stato_da_bunny, IMPOSTAZIONI_LIBRERIA, RISOLUZIONI, attivo, chiave_account
        assert stato_da_bunny(3) == "pronto" and stato_da_bunny(4) == "pronto"
        assert stato_da_bunny(5) == "errore" and stato_da_bunny(8) == "errore"
        assert stato_da_bunny(0) == "codifica" and stato_da_bunny("x") == "codifica" and stato_da_bunny(6) == "caricamento"
        # l'OGGETTO video ha un altro vocabolario: 4 = finito, 3 = transcodifica (provato il 7/10)
        from services.bunny.gestito import stato_da_oggetto_video
        assert stato_da_oggetto_video(4) == "pronto" and stato_da_oggetto_video(3) == "codifica"
        assert stato_da_oggetto_video(2) == "codifica" and stato_da_oggetto_video(5) == "errore" and stato_da_oggetto_video(6) == "errore"
        acc = (BACKEND / "routers" / "accademia.py").read_text()
        assert 'gestito.stato_da_oggetto_video(remoto.get("status"))' in acc
        # le leve sui costi: niente 240p/1440p/2160p, niente originali, niente copie extra
        assert RISOLUZIONI == "360p,720p,1080p"
        assert IMPOSTAZIONI_LIBRERIA["EnabledResolutions"] == RISOLUZIONI
        assert IMPOSTAZIONI_LIBRERIA["KeepOriginalFiles"] is False
        assert IMPOSTAZIONI_LIBRERIA["EnableMP4Fallback"] is False
        assert IMPOSTAZIONI_LIBRERIA["AllowDirectPlay"] is False
        # sicurezza: token auth acceso, referrer nostri
        assert IMPOSTAZIONI_LIBRERIA["PlayerTokenAuthenticationEnabled"] is True
        assert "aurya.life" in IMPOSTAZIONI_LIBRERIA["AllowedReferrers"]
        # senza chiave in env l'upload e' spento
        import os
        os.environ.pop("BUNNY_ACCOUNT_API_KEY", None)
        assert chiave_account() is None and attivo() is False

    def test_client_esteso(self):
        src = (BACKEND / "services" / "bunny" / "client.py").read_text()
        for n in ("async def create_video", "async def get_video", "async def delete_video",
                  "class BunnyAccountClient", "async def create_library", "async def update_library", "async def get_pullzone"):
            assert n in src, n
        assert '_ACCOUNT_BASE_URL = "https://api.bunny.net"' in src
        assert 'self._client.post(f"/library/{library_id}/videos"' in src
        assert "async def add_allowed_referrer" in src and "async def list_libraries" in src
        g = (BACKEND / "services" / "bunny" / "gestito.py").read_text()
        # un salvataggio fallito non lascia orfani: si adotta la libreria con lo stesso nome
        assert "await acc.list_libraries()" in g and "adotto la libreria" in g
        # org nate con integrations null: $set dell'oggetto intero, non $push
        assert '{"$set": {"integrations": {"bunny_libraries": [lib]}}}' in g
        assert "await acc.add_allowed_referrer(library_id, dominio)" in g

    def test_modelli_additivi(self):
        from models.course import Lesson, VideoLezione
        from models.organization import BunnyLibrary
        l = Lesson(order=0, title="Lezione", tipo="testo", testo="ciao")
        assert l.video is None and l.tipo == "testo"
        v = VideoLezione(guid="a" * 36, stato="codifica", size_bytes=10)
        assert Lesson(order=0, title="L", video=v).video.stato == "codifica"
        lib = BunnyLibrary(alias="Aurya", library_id="1", api_key="k", managed=True, created_by="aurya",
                           read_only_api_key="ro", quota={"video_bytes": 5, "video_count": 1})
        assert lib.managed and lib.quota["video_bytes"] == 5
        # il legacy resta leggibile: nessun campo nuovo obbligatorio
        assert BunnyLibrary(alias="x", library_id="1", api_key="k").managed is False


class TestWebhook:
    def test_router_montato_e_verifica(self):
        src = (BACKEND / "routers" / "webhooks_bunny.py").read_text()
        assert 'router = APIRouter(prefix="/webhooks/bunny"' in src
        assert 'request.headers.get("X-BunnyStream-Signature")' in src
        assert "firma_webhook_valida(corpo, firma, lib.get(\"read_only_api_key\"))" in src
        assert "HTTP_401_UNAUTHORIZED" in src and "HTTP_404_NOT_FOUND" in src
        # quando e' pronto legge durata/dimensione/miniatura e allinea i campi del legacy
        assert 'l["bunny_video_guid"] = video_guid' in src and 'l["duration_seconds"] = dettagli["duration_seconds"]' in src
        server = (BACKEND / "server.py").read_text()
        assert 'app.include_router(webhooks_bunny_router.router, prefix="/api")' in server
        assert 'app.include_router(accademia_router.router, prefix="/api")' in server


class TestRouterAccademia:
    def test_rotte_e_cancello(self):
        src = (BACKEND / "routers" / "accademia.py").read_text()
        assert '_gate = require_module("accademia")' in src
        for r in ('@router.get("")', '@router.post("", status_code=status.HTTP_201_CREATED)', '@router.get("/{course_id}")',
                  '@router.patch("/{course_id}")', '@router.post("/{course_id}/copertina")', '@router.post("/{course_id}/pubblica")',
                  '@router.post("/{course_id}/ritira")', '@router.delete("/{course_id}")',
                  '@router.post("/{course_id}/moduli", status_code=status.HTTP_201_CREATED)',
                  '@router.post("/{course_id}/lezioni", status_code=status.HTTP_201_CREATED)',
                  '@router.put("/{course_id}/ordine")', '@router.post("/{course_id}/lezioni/{lesson_id}/video")',
                  '@router.get("/{course_id}/lezioni/{lesson_id}/video")', '@router.delete("/{course_id}/lezioni/{lesson_id}/video")',
                  '@router.get("/{course_id}/studenti")', '@router.post("/{course_id}/studenti/{enrollment_id}/revoca")'):
            assert r in src, r
        # ogni rotta ha il cancello del modulo
        assert src.count("_=Depends(_gate)") >= 16
        # la chiave API non viaggia mai: al browser vanno le credenziali TUS
        assert "return gestito.credenziali_tus(lib, guid)" in src
        # quota PRIMA di creare il video; patto DPA alla creazione; prodotto gemello riusato
        assert src.index('"code": "quota_video"') < src.index("assicura_libreria(org_id)")
        assert "await require_dpa_acknowledged(org_id)" in src and "from routers.courses import _ensure_linked_product" in src

    def test_ragioni_di_pubblicazione(self):
        from routers.accademia import _ragioni_pubblicazione
        pre = {"stripe_pronto": True, "patto": True, "pagina_pubblica": True}
        corso = {"modules": [{"id": "m", "lessons": [
            {"id": "a", "tipo": "testo", "testo": "ciao"},
            {"id": "b", "tipo": "video", "video": {"stato": "codifica"}},
            {"id": "c", "tipo": "video", "video": None},
        ]}]}
        r = _ragioni_pubblicazione(corso, {"unit_price": 10}, pre)
        assert any("in lavorazione" in x for x in r) and any("senza contenuto" in x for x in r)
        assert not any("almeno una lezione" in x for x in r)
        ok = {"modules": [{"id": "m", "lessons": [{"id": "b", "tipo": "video", "video": {"stato": "pronto"}}]}]}
        assert _ragioni_pubblicazione(ok, {"unit_price": 10}, pre) == []
        assert any("prezzo" in x for x in _ragioni_pubblicazione(ok, {"unit_price": 0}, pre))
        assert any("Stripe" in x for x in _ragioni_pubblicazione(ok, {"unit_price": 10}, {**pre, "stripe_pronto": False}))

    def test_slug(self):
        from routers.accademia import _slugify
        assert _slugify("Respiro consapevole in 5 giorni!") == "respiro-consapevole-in-5-giorni"
        assert _slugify("   ") == "corso"
