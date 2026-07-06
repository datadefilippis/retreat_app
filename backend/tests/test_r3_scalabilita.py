"""R3 — bloccanti di scalabilita' (docs/PRODUCTION_PLAN.md, audit 10/7)."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class TestObjectStorage:
    def test_disabilitato_senza_env(self, monkeypatch):
        from services import object_storage as osvc
        for v in osvc._S3_VARS:
            monkeypatch.delenv(v, raising=False)
        assert osvc.is_s3_enabled() is False

    def test_abilitato_solo_con_tutte_le_env(self, monkeypatch):
        from services import object_storage as osvc
        vals = {"S3_BUCKET": "b", "S3_ENDPOINT": "https://e", "S3_ACCESS_KEY": "k",
                "S3_SECRET_KEY": "s", "S3_PUBLIC_URL": "https://cdn"}
        for k, v in vals.items():
            monkeypatch.setenv(k, v)
        assert osvc.is_s3_enabled() is True
        monkeypatch.delenv("S3_PUBLIC_URL")
        assert osvc.is_s3_enabled() is False   # parziale = spento (mai a meta')

    def test_fallback_locale_scrive_e_ritorna_path_storico(self, monkeypatch, tmp_path):
        from services import object_storage as osvc
        for v in osvc._S3_VARS:
            monkeypatch.delenv(v, raising=False)
        monkeypatch.setattr(osvc, "_UPLOADS_ROOT", tmp_path)
        url = osvc.save_public_upload("products", "x.png", b"IMG", content_type="image/png")
        assert url == "/uploads/products/x.png"     # contratto storico intatto
        assert (tmp_path / "products" / "x.png").read_bytes() == b"IMG"

    def test_s3_put_e_url_pubblica(self, monkeypatch):
        from services import object_storage as osvc
        from unittest.mock import MagicMock
        vals = {"S3_BUCKET": "aurya", "S3_ENDPOINT": "https://e", "S3_ACCESS_KEY": "k",
                "S3_SECRET_KEY": "s", "S3_PUBLIC_URL": "https://cdn.aurya.life/"}
        for k, v in vals.items():
            monkeypatch.setenv(k, v)
        fake = MagicMock()
        monkeypatch.setattr(osvc, "_client", lambda: fake)
        url = osvc.save_public_upload("logos", "s1.webp", b"IMG", content_type="image/webp")
        assert url == "https://cdn.aurya.life/uploads/logos/s1.webp"
        kw = fake.put_object.call_args.kwargs
        assert kw["Bucket"] == "aurya" and kw["Key"] == "uploads/logos/s1.webp"
        assert kw["ACL"] == "public-read" and kw["ContentType"] == "image/webp"
        assert "immutable" in kw["CacheControl"]


class TestNoUnboundedEndpoints:
    """Guard: niente to_list(None) nei ROUTER (i services per-ordine sono
    naturalmente limitati dalla dimensione dell'ordine e restano fuori)."""

    def test_routers_senza_to_list_none(self):
        routers_dir = Path(__file__).resolve().parents[1] / "routers"
        offenders = []
        for f in routers_dir.glob("*.py"):
            if "to_list(None)" in f.read_text():
                offenders.append(f.name)
        assert offenders == [], f"to_list(None) reintrodotto in: {offenders}"


class TestR3Indexes:
    def test_indici_dichiarati_in_create_indexes(self):
        src = (Path(__file__).resolve().parents[1] / "database.py").read_text()
        assert "r3_rules_org_product" in src
        assert "r3_blocks_org_product_date" in src
