"""BS (2/10/2026) — la segmentazione solida in Brevo.

Il registro ATTRIBUTI_BREVO e' la verita': _attributes() produce esattamente
quelle chiavi (le date solo se valorizzate), AURYA_INVIABILE e' vero solo
per i confermati col consenso, lo script crea/riallinea/verifica e NON puo'
mandare email (solo API contatti).
"""
from datetime import datetime, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
SCRIPT = (BACKEND / "scripts" / "brevo_segmentazione.py").read_text(encoding="utf-8")
SYNC = (BACKEND / "services" / "subscriber_brevo_sync.py").read_text(encoding="utf-8")

PIENO = {
    "name": "  Maria   Rossi ", "status": "confirmed", "consent": True, "source": "cerca-ritiro",
    "language": "it", "created_at": datetime(2026, 10, 1, 13, 41, tzinfo=timezone.utc),
    "confirmed_at": "2026-10-01T13:43:25", "verificato_at": datetime(2026, 10, 1, 13, 43, tzinfo=timezone.utc),
    "consenso": {"versione": "cerchio-v3"},
    "provenienza": {"canale": "sito", "superficie": "cerca-ritiro"},
    "preferences": {"topics": ["yoga"], "format": "all", "retreat_alert": {"enabled": True, "scope": "regions", "regions": ["puglia"]}},
    "profile": {"interests": ["yoga", "suono"], "city": "Bari", "travel": "near", "budget": "500to1000", "eta": "45-59"},
}


class TestRegistro:
    def test_le_chiavi_sono_esattamente_il_registro(self):
        from services.subscriber_brevo_sync import ATTRIBUTI_BREVO, _attributes
        got = _attributes(PIENO)
        assert set(got) == set(ATTRIBUTI_BREVO)
        assert got["NOME"] == "Maria Rossi" and got["AURYA_INTERESTS"] == "yoga,suono" and got["AURYA_ETA"] == "45-59"
        assert got["AURYA_ISCRITTO_IL"] == "2026-10-01" and got["AURYA_CONFERMATO_IL"] == "2026-10-01"
        assert got["AURYA_VERIFICATO"] is True and got["AURYA_INVIABILE"] is True
        assert got["AURYA_PORTA"] == "altro" and got["AURYA_SUPERFICIE"] == "cerca-ritiro" and got["AURYA_CANALE"] == "sito"
        assert got["AURYA_CONSENSO_VERSIONE"] == "cerchio-v3" and got["AURYA_ALERT"] == "puglia"
        for k, t in ATTRIBUTI_BREVO.items():
            assert t in ("text", "date", "boolean"), k
            if t == "boolean":
                assert isinstance(got[k], bool), k

    def test_pending_senza_date_e_senza_consenso(self, monkeypatch):
        monkeypatch.delenv("CERCHIO_SINGOLO_OPTIN", raising=False)      # doppio opt-in: come oggi
        from services.subscriber_brevo_sync import _attributes
        got = _attributes({"status": "pending", "source": "meditazioni-cancello", "created_at": "2026-09-30T10:00:00"})
        assert got["AURYA_INVIABILE"] is False and got["AURYA_VERIFICATO"] is False
        assert _attributes({"status": "pending", "consent": True})["AURYA_INVIABILE"] is False   # pending col consenso: no, a interruttore spento
        assert "AURYA_CONFERMATO_IL" not in got          # data vuota = omessa (Brevo rifiuterebbe l'upsert)
        assert got["AURYA_ISCRITTO_IL"] == "2026-09-30" and got["AURYA_PORTA"] == "meditazioni"
        assert got["NOME"] == "" and got["AURYA_ETA"] == ""
        # confermato ma senza consenso registrato: NON inviabile (regola del Cerchio)
        assert _attributes({"status": "confirmed"})["AURYA_INVIABILE"] is False
        assert _attributes({"status": "unsubscribed", "consent": True})["AURYA_INVIABILE"] is False

    def test_inviabile_segue_l_interruttore_del_singolo_optin(self, monkeypatch):
        """SO (3/10): Brevo e il motore del Cerchio dicono la stessa cosa.
        Acceso: il consenso basta (il clic resta la prova di qualita');
        i sospesi e chi non ha consenso restano fuori. Spento: come prima."""
        from services.subscriber_brevo_sync import inviabile, _attributes
        from services.sequenze import filtro_sub
        monkeypatch.setenv("CERCHIO_SINGOLO_OPTIN", "1")
        assert inviabile({"status": "pending", "consent": True}) is True
        assert inviabile({"status": "confirmed", "consent": True}) is True
        assert inviabile({"status": "pending", "consent": True, "sospeso_at": "2026-10-01"}) is False
        assert inviabile({"status": "pending"}) is False
        assert inviabile({"status": "unsubscribed", "consent": True}) is False
        assert _attributes({"status": "pending", "consent": True})["AURYA_INVIABILE"] is True
        assert filtro_sub()["status"] == {"$in": ["pending", "confirmed"]}      # la stessa regola del motore
        monkeypatch.delenv("CERCHIO_SINGOLO_OPTIN", raising=False)
        assert inviabile({"status": "pending", "consent": True}) is False
        assert filtro_sub()["status"] == "confirmed"

    def test_proiezione_unica_e_push_che_risponde(self):
        from services.subscriber_brevo_sync import _PROIEZIONE_SYNC
        for k in ("profile", "provenienza", "name", "created_at", "confirmed_at", "verificato_at", "consent", "consenso",
                  "sospeso_at"):
            assert _PROIEZIONE_SYNC.get(k) == 1, k
        assert "find_one({\"email\": email}, _PROIEZIONE_SYNC)" in SYNC
        assert "def _push_to_brevo(email: str, attributes: dict, blacklisted: bool) -> bool:" in SYNC
        assert "return False\n    return True" in SYNC


class TestScript:
    def test_tre_gesti_e_mai_una_email(self):
        for g in ("--attributi", "--backfill", "--verifica"):
            assert f'"{g}"' in SCRIPT, g
        assert "/contacts/attributes/normal/" in SCRIPT and "(200, 201, 204, 409)" in SCRIPT   # idempotente
        assert "_PROIEZIONE_SYNC" in SCRIPT and "_push_to_brevo" in SCRIPT
        assert 'd.get("status") == "unsubscribed"' in SCRIPT                                    # blacklist come la sync
        for vietato in ("smtp", "sendTransacEmail", "emailCampaigns", "/smtp/email", "listIds", "sendEmail"):
            assert vietato not in SCRIPT, vietato
        assert "AURYA_INVIABILE" in SCRIPT
