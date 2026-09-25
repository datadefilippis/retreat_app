"""SA6 (25/9/2026 sera, founder: «certi utenti pubblicano foto profilo o
copertina completamente fuori luogo: da system admin voglio poterle
cancellare o sostituirgliele»).

  - POST   /admin/organizations/{id}/public-profile/immagine (multipart:
           tipo cover|portrait|photo, file, motivo, sostituisci) — stesse
           difese dell'operatore (_read_profile_image), via i vecchi file,
           URL sempre nuovo, effetti post-salvataggio, audit;
  - DELETE /admin/organizations/{id}/public-profile/immagine?tipo&url&motivo;
  - audit PUBLIC_PROFILE_ADMIN_IMAGE con tipo, azione, prima/dopo, motivo;
  - la tab Profilo della regia ha la sezione «Foto» con sostituisci/rimuovi
    per copertina, ritratto e ogni foto della galleria; senza motivo si va
    a scriverlo, la rimozione chiede conferma.
"""
import io
import os
from pathlib import Path

import pytest
import requests

RADICE = Path(__file__).resolve().parents[2]
BACKEND = RADICE / "backend"
FE = RADICE / "frontend" / "src"
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8000")

ADMIN = (BACKEND / "routers" / "admin.py").read_text(encoding="utf-8")
TAB = (FE / "features" / "admin" / "OrgProfiloAdminTab.js").read_text(encoding="utf-8")
API = (FE / "api" / "admin.js").read_text(encoding="utf-8")


class TestRotte:
    def test_esistono_e_sono_del_system_admin_con_motivo_e_audit(self):
        assert ADMIN.count('"/organizations/{org_id}/public-profile/immagine"') == 2   # POST + DELETE
        up = ADMIN[ADMIN.index("async def admin_upload_public_profile_image"):][:4200]
        de = ADMIN[ADMIN.index("async def admin_delete_public_profile_image"):][:2600]
        for blocco in (up, de):
            assert "require_system_admin" in blocco
            assert "_motivo_pulito(motivo)" in blocco
            assert "await dopo_salvataggio(org_id)" in blocco       # cache slug→org, IndexNow
            assert "await _audit_immagine(" in blocco
            assert "send_email" not in blocco                          # nessuna email all'operatore
            assert "return await _profilo_pubblico_payload(org_id)" in blocco
        # le stesse difese dell'operatore e la stessa igiene dei file
        assert "from routers.organizations import _PP_PHOTOS_MAX, _read_profile_image" in up
        assert 'delete_public_uploads(category, f"{org_id}")' in up and 'delete_public_uploads(category, f"{org_id}")' in de
        # la galleria NON si spazza a prefisso org: via SOLO il file toccato
        assert "delete_public_uploads(category, _nome_file_da_url(vecchio))" in up
        assert "delete_public_uploads(category, _nome_file_da_url(url))" in de
        assert '"action": "PUBLIC_PROFILE_ADMIN_IMAGE"' in ADMIN
        for k in ('"tipo": tipo, "azione": azione', '"prima": _valore_breve(prima)', '"motivo": motivo'):
            assert k in ADMIN, k
        # la rotta storica del PATCH non e' stata toccata (GET + PATCH)
        assert ADMIN.count('"/organizations/{org_id}/public-profile"') == 2

    def test_nome_file_da_url(self):
        from routers.admin import _nome_file_da_url, _IMMAGINI_PROFILO
        assert _nome_file_da_url("/uploads/profile-photos/org1-ab12cd34ef.webp") == "org1-ab12cd34ef"
        assert _nome_file_da_url("https://cdn.x/uploads/profile-photos/org1-ab12cd34ef.jpg?v=2") == "org1-ab12cd34ef"
        assert set(_IMMAGINI_PROFILO) == {"cover", "portrait", "photo"}
        assert _IMMAGINI_PROFILO["photo"] == ("public_profile.photos", "profile-photos")

    def test_motivo_pulito(self):
        from fastapi import HTTPException
        from routers.admin import _motivo_pulito
        assert _motivo_pulito("  foto   fuori luogo ") == "foto fuori luogo"
        for cattivo in ("", "ab", "x" * 301):
            with pytest.raises(HTTPException) as e:
                _motivo_pulito(cattivo)
            assert e.value.status_code == 422


def _png() -> bytes:
    PIL = pytest.importorskip("PIL.Image")
    buf = io.BytesIO()
    PIL.new("RGB", (64, 40), (200, 120, 80)).save(buf, format="PNG")
    return buf.getvalue()


def _sys_headers():
    for pwd in ("demo1234", "Demo1234!"):
        r = requests.post(f"{BASE_URL}/api/auth/login",
                          json={"email": "sysadmin@demo.com", "password": pwd}, timeout=10)
        if r.status_code == 200:
            return {"Authorization": f"Bearer {r.json()['access_token']}"}
    pytest.skip("login sysadmin non disponibile (rate limit?)")


class TestDalVivo:
    def test_galleria_aggiungi_sostituisci_rimuovi_con_audit(self):
        h = _sys_headers()
        d = requests.get(f"{BASE_URL}/api/admin/organizations", headers=h,
                         params={"limit": 5, "q": "admin@demo.com"}, timeout=10).json()
        if not d.get("items"):
            pytest.skip("org demo assente nel db locale")
        org_id = d["items"][0]["id"]
        base = f"{BASE_URL}/api/admin/organizations/{org_id}/public-profile"
        prima = requests.get(base, headers=h, timeout=10)
        if prima.status_code == 404:
            pytest.skip("backend su :8000 non riavviato con SA6")
        n0 = len(prima.json().get("photos") or [])
        if n0 >= 8:
            pytest.skip("galleria demo piena")
        png = _png()
        # senza motivo → 422; tipo sconosciuto → 400; non admin → 401/403
        r = requests.post(f"{base}/immagine", headers=h, timeout=20,
                          files={"file": ("x.png", png, "image/png")}, data={"tipo": "photo"})
        assert r.status_code == 422, r.text
        r = requests.post(f"{base}/immagine", headers=h, timeout=20,
                          files={"file": ("x.png", png, "image/png")}, data={"tipo": "boh", "motivo": "guardia SA6"})
        assert r.status_code == 400, r.text
        assert requests.delete(f"{base}/immagine", params={"tipo": "cover", "motivo": "x"}, timeout=10).status_code in (401, 403)
        # aggiungi
        r = requests.post(f"{base}/immagine", headers=h, timeout=20,
                          files={"file": ("guardia.png", png, "image/png")},
                          data={"tipo": "photo", "motivo": "  guardia   SA6 aggiungi "})
        assert r.status_code == 200, r.text
        photos = r.json()["photos"]
        assert len(photos) == n0 + 1
        nuova = photos[-1]
        try:
            # sostituisci quella appena messa: stessa posizione, URL diverso
            r = requests.post(f"{base}/immagine", headers=h, timeout=20,
                              files={"file": ("guardia2.png", png, "image/png")},
                              data={"tipo": "photo", "motivo": "guardia SA6 sostituisci", "sostituisci": nuova})
            assert r.status_code == 200, r.text
            photos2 = r.json()["photos"]
            assert len(photos2) == n0 + 1 and photos2[-1] != nuova and nuova not in photos2
            nuova = photos2[-1]
            # sostituire un URL che non c'e' → 404
            r = requests.post(f"{base}/immagine", headers=h, timeout=20,
                              files={"file": ("g3.png", png, "image/png")},
                              data={"tipo": "photo", "motivo": "guardia SA6", "sostituisci": "/uploads/profile-photos/nope.webp"})
            assert r.status_code == 404
        finally:
            # rimuovi (ripristino) — anche se un'asserzione sopra e' rossa
            r = requests.delete(f"{base}/immagine", headers=h, timeout=20,
                                params={"tipo": "photo", "url": nuova, "motivo": "guardia SA6 rimuovi"})
        assert r.status_code == 200, r.text
        assert nuova not in r.json()["photos"] and len(r.json()["photos"]) == n0
        # rimuovere due volte → 404
        r = requests.delete(f"{base}/immagine", headers=h, timeout=20,
                            params={"tipo": "photo", "url": nuova, "motivo": "guardia SA6 rimuovi"})
        assert r.status_code == 404
        # l'audit racconta i tre gesti
        logs = requests.get(f"{BASE_URL}/api/admin/audit-logs", headers=h,
                            params={"limit": 30, "action": "PUBLIC_PROFILE_ADMIN_IMAGE"}, timeout=10).json()
        righe = logs.get("items") or logs.get("logs") or (logs if isinstance(logs, list) else [])
        mie = [x for x in righe if x.get("action") == "PUBLIC_PROFILE_ADMIN_IMAGE" and x.get("organization_id") == org_id]   # la lista espone organization_id, non target_id
        mie.sort(key=lambda x: x.get("created_at") or "", reverse=True)
        azioni = [x["metadata"]["azione"] for x in mie[:3]]
        assert set(azioni) >= {"rimuovi", "sostituisci", "aggiungi"}, azioni
        agg = next(x for x in mie if x["metadata"]["azione"] == "aggiungi")
        assert agg["metadata"]["tipo"] == "photo" and agg["metadata"]["motivo"] == "guardia SA6 aggiungi"
        assert agg["metadata"]["prima"] is None and agg["metadata"]["dopo"]
        rim = next(x for x in mie if x["metadata"]["azione"] == "rimuovi")
        assert rim["metadata"]["prima"] == nuova and rim["metadata"]["dopo"] is None

    def test_cover_senza_immagine_da_rimuovere_dice_400(self):
        h = _sys_headers()
        d = requests.get(f"{BASE_URL}/api/admin/organizations", headers=h,
                         params={"limit": 50}, timeout=10).json()
        senza = next((o for o in d.get("items", [])
                      if o.get("stato_profilo") in ("account", "bozza")), None)
        if not senza:
            pytest.skip("nessuna org senza profilo nel db locale")
        r = requests.delete(f"{BASE_URL}/api/admin/organizations/{senza['id']}/public-profile/immagine",
                            headers=h, params={"tipo": "cover", "motivo": "guardia SA6"}, timeout=10)
        assert r.status_code in (400, 404), r.text


class TestFrontend:
    def test_api_e_sezione_foto(self):
        assert "api.post(`/admin/organizations/${orgId}/public-profile/immagine`, fd" in API
        assert "api.delete(`/admin/organizations/${orgId}/public-profile/immagine`" in API
        for tid in ("admin-foto", "admin-foto-file", "admin-foto-cover", "admin-foto-cover-sostituisci", "admin-foto-cover-rimuovi",
                    "admin-foto-portrait", "admin-foto-portrait-sostituisci", "admin-foto-portrait-rimuovi",
                    "admin-foto-galleria", "admin-foto-photo", "admin-foto-photo-aggiungi"):
            assert f'data-testid="{tid}"' in TAB, tid
        # la galleria ha sostituisci E rimuovi per ogni foto
        assert "scegliFile('photo', url)" in TAB and "rimuoviImmagine('photo', url)" in TAB
        # senza motivo si va a scriverlo; la rimozione chiede conferma; la foto si comprime come per l'operatore
        assert "if (!chiediMotivo()) return;" in TAB and "window.confirm(" in TAB
        assert "compressImage(file)" in TAB
        assert "ref={motivoRef}" in TAB
        # il diff del form non tocca le immagini: restano gesti immediati
        assert "cover_url" not in TAB.split("function daPayload")[1].split("}")[0]
