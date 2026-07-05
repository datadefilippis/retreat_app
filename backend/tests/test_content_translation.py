"""F5 — traduzione automatica contenuti: hash, struttura, sicurezza."""

import asyncio
import os, sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

from services import content_translation_service as svc

OCC = {"long_description": "## Il ritiro\nTre giorni di pratica.",
       "agenda": [{"time": "07:30", "title": "Meditazione", "description": ""}],
       "included": ["Pasti bio"], "excluded": [], "faq": [{"q": "Domanda?", "a": "Risposta."}]}
PROD = {"description": "Un ritiro yoga tra gli ulivi."}


class TestSourceHash:
    def test_hash_stable(self):
        f = svc.build_source_fields(OCC, PROD)
        assert svc.source_hash(f) == svc.source_hash(svc.build_source_fields(OCC, PROD))

    def test_hash_changes_when_content_changes(self):
        f1 = svc.build_source_fields(OCC, PROD)
        f2 = svc.build_source_fields({**OCC, "long_description": "cambiato"}, PROD)
        assert svc.source_hash(f1) != svc.source_hash(f2)

    def test_name_is_never_translated(self):
        # il nome e' il brand dell'operatore: NON deve stare nei campi
        f = svc.build_source_fields({**OCC, "name": "Ritiro X"}, {**PROD, "name": "Ritiro X"})
        assert "name" not in f


class TestTranslateGuards:
    def _fake_llm(self, response):
        return patch("services.claude_client.send_message",
                     AsyncMock(return_value=response))

    def test_valid_translation_accepted(self):
        import json
        f = svc.build_source_fields(OCC, PROD)
        translated = {**f, "description": "A yoga retreat among olive trees."}
        with self._fake_llm(json.dumps(translated)):
            out = asyncio.run(svc.translate_fields(f, "en"))
        assert out["description"].startswith("A yoga")

    def test_divergent_keys_rejected(self):
        with self._fake_llm('{"description": "x", "malicious": "y"}'):
            out = asyncio.run(svc.translate_fields(
                svc.build_source_fields(OCC, PROD), "en"))
        assert out is None

    def test_divergent_cardinality_rejected(self):
        import json
        f = svc.build_source_fields(OCC, PROD)
        bad = {**f, "faq": []}   # LLM ha "perso" una FAQ → scarto
        with self._fake_llm(json.dumps(bad)):
            out = asyncio.run(svc.translate_fields(f, "en"))
        assert out is None

    def test_non_json_rejected(self):
        with self._fake_llm("Ecco la traduzione: ..."):
            out = asyncio.run(svc.translate_fields(
                svc.build_source_fields(OCC, PROD), "en"))
        assert out is None


class TestScanSafety:
    def test_noop_when_llm_unavailable(self):
        with patch("services.claude_client.is_available", lambda: False):
            out = asyncio.run(svc.run_translation_scan())
        assert out == {"scanned": 0, "translated": 0, "skipped": 0, "errors": 0}

    def test_flag_off_is_noop(self):
        os.environ["CONTENT_TRANSLATIONS_ENABLED"] = "false"
        try:
            out = asyncio.run(svc.run_translation_scan())
            assert out["translated"] == 0
        finally:
            os.environ.pop("CONTENT_TRANSLATIONS_ENABLED", None)

    def test_run_cap_exists(self):
        assert svc.MAX_TRANSLATIONS_PER_RUN <= 50   # mai run illimitati
