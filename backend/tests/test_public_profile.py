"""F2.0 — profilo pubblico operatore: whitelist, opt-in contatti."""

import os, sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")


class TestPublicProfileGuards:
    def _src(self, fname):
        return open(os.path.join(os.path.dirname(__file__), "..", fname)).read()

    def test_patch_is_whitelisted(self):
        # Il PATCH deve iterare SOLO i campi della whitelist: nessun
        # campo arbitrario puo' entrare nel documento org.
        src = self._src("routers/organizations.py")
        i = src.index("async def update_public_profile")
        block = src[i:i + 1500]
        assert "_PUBLIC_PROFILE_FIELDS.items()" in block
        assert "body.items()" not in block          # mai iterare il body

    def test_field_limits_defined(self):
        from routers.organizations import _PUBLIC_PROFILE_FIELDS
        assert _PUBLIC_PROFILE_FIELDS["bio"] <= 1000
        assert set(_PUBLIC_PROFILE_FIELDS) >= {
            "bio", "city", "region", "cover_url",
            "instagram", "website", "facebook"}

    def test_contacts_are_opt_in(self):
        # /public/operator espone i contatti SOLO con show_contacts.
        src = self._src("routers/public.py")
        i = src.index('if pp.get("show_contacts"):')
        block = src[i:i + 300]
        assert "public_email" in block and "public_phone" in block

    def test_cover_upload_rejects_svg(self):
        # niente svg per le cover (XSS via svg inline)
        src = self._src("routers/organizations.py")
        i = src.index("async def upload_profile_cover")
        block = src[i:i + 1200]
        assert '".svg"' not in block.split("allowed = ")[1].split("\n")[0]
