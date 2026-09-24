"""LOTTO A · Regia operatori (24/9/2026) — docs/PIANO_ESECUZIONE_ADMIN_CERCHIO_2026-09-24.md

Il founder vuole distinguere chi si e' fermato all'account da chi ha una
pagina, vedere nome/attivita'/telefono in riga, e correggere un profilo
senza impersonare l'operatore. Tenuto fermo qui:

  A1  services/stato_profilo: quattro stati da UNA verita' (riusa
      sequenze.stato_operatore), conteggi sempre a quattro chiavi;
  A2  GET /admin/organizations: q/stato/telefono, conteggi, riga con i
      campi nuovi (solo aggiunti), proiezione esplicita; i letterali
      guardati da test_regia_operatori restano;
  A3  services/profilo_pubblico: pulisci + dopo_salvataggio estratti
      SENZA cambi di comportamento, _PUBLIC_PROFILE_FIELDS ancora in
      routers/organizations.py, la rotta dell'operatore li chiama;
  A4  PATCH /admin/organizations/{id}/public-profile: system admin,
      motivo 3-300 obbligatorio, audit PUBLIC_PROFILE_ADMIN_EDIT con
      campi/prima/dopo/motivo, risposta = payload della GET;
  A5  frontend: casella, chip di stato, «senza telefono», colonna Chi,
      coda «da rivedere», form admin con motivo, scheda 360° dal nome.

I test in-process girano sul DB del backend/.env (come il server live);
quelli HTTP si saltano da soli se il server su :8000 non e' ancora stato
riavviato col codice nuovo.
"""
import asyncio
import os
import re
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

import pytest
import requests

FE = BACKEND.parent / "frontend" / "src"
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8000")

ADMIN = (BACKEND / "routers" / "admin.py").read_text(encoding="utf-8")
ORGS = (BACKEND / "routers" / "organizations.py").read_text(encoding="utf-8")
MODELLO = (BACKEND / "models" / "admin.py").read_text(encoding="utf-8")
REPO = (BACKEND / "repositories" / "admin_repository.py").read_text(encoding="utf-8")
STATO = (BACKEND / "services" / "stato_profilo.py").read_text(encoding="utf-8")
SERVIZIO = (BACKEND / "services" / "profilo_pubblico.py").read_text(encoding="utf-8")
TAB = (FE / "features" / "admin" / "OrganizationsTab.js").read_text(encoding="utf-8")
FORM = (FE / "features" / "admin" / "OrgProfiloAdminTab.js").read_text(encoding="utf-8")
DIALOG = (FE / "features" / "admin" / "OrgBusinessProfileDialog.js").read_text(encoding="utf-8")
API = (FE / "api" / "admin.js").read_text(encoding="utf-8")


# I test che toccano il DB sono `async def`: pytest-asyncio (asyncio_mode
# = auto in conftest) li fa girare sul loop condiviso della suite, come
# tutti gli altri test DB. Un loop di modulo qui rompeva il giro completo.


def _sys_headers():
    for pwd in ("DevLocal1234!", "demo1234"):
        r = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "sysadmin@demo.com", "password": pwd}, timeout=10)
        if r.status_code == 200:
            return {"Authorization": f"Bearer {r.json()['access_token']}"}
    pytest.skip("login sysadmin non disponibile (rate limit?)")


def _lista_live(params=None):
    """GET live; skip se il server su :8000 e' ancora quello di ieri."""
    r = requests.get(f"{BASE_URL}/api/admin/organizations", headers=_sys_headers(),
                     params=params or {}, timeout=15)
    assert r.status_code == 200, r.text
    d = r.json()
    if "conteggi" not in d:
        pytest.skip("backend su :8000 non riavviato col Lotto A (manca conteggi)")
    return d


# ── A1 · stato del profilo ─────────────────────────────────────────────────

class TestA1StatoProfilo:
    def test_la_regola_pura(self):
        from services.stato_profilo import STATI, classifica
        assert STATI == ("account", "bozza", "pagina", "online")
        assert classifica(0, False, 0) == "account"
        assert classifica(0, True, 3) == "account"        # senza bio non c'e' niente
        assert classifica(120, False, 0) == "bozza"
        assert classifica(120, False, 2) == "bozza"       # servizi senza pagina: resta bozza
        assert classifica(120, True, 0) == "pagina"
        assert classifica(120, True, 1) == "online"

    def test_riusa_stato_operatore_e_non_lo_ricalcola(self):
        assert "from services.sequenze import stato_operatore" in STATO
        assert "count_documents" not in STATO and "stores_collection" not in STATO
        assert 'async def stato_profilo(org: dict)' in STATO

    def test_conteggi_sempre_a_quattro_chiavi(self):
        from services.stato_profilo import conteggi
        assert conteggi([]) == {"account": 0, "bozza": 0, "pagina": 0, "online": 0}
        c = conteggi([{"stato": "online"}, {"stato": "online"}, {"stato": "account"}, {"stato": "boh"}])
        assert c == {"account": 1, "bozza": 0, "pagina": 0, "online": 2}

    async def test_sul_db_locale_lo_stato_segue_le_sequenze(self):
        from database import organizations_collection
        from services.sequenze import stato_operatore
        from services.stato_profilo import classifica, stato_profilo

        async def go():
            try:
                docs = await organizations_collection.find(
                    {"is_sample": {"$ne": True}}, {"_id": 0, "id": 1, "public_profile": 1, "public_slug": 1}).to_list(50)
            except RuntimeError as e:          # «Event loop is closed»: client motor legato a un altro loop
                pytest.skip(f"client motor su un altro loop: {e}")
            out = []
            for d in docs:
                so = await stato_operatore(d)
                sp = await stato_profilo(d)
                out.append((so, sp, d))
            return out
        righe = await go()
        if not righe:
            pytest.skip("nessuna org nel db locale")
        for so, sp, d in righe:
            bio = len(((d.get("public_profile") or {}).get("bio") or "").strip())
            assert sp["stato"] == classifica(bio, so["pagina"], so["n_servizi"])
            assert sp["n_servizi"] == so["n_servizi"] and sp["bio_len"] == bio
            assert sp["slug"] == (so["slug"] or None)


# ── A2 · la lista della regia ──────────────────────────────────────────────

class TestA2Lista:
    def test_i_parametri_e_i_conteggi(self):
        blocco = ADMIN[ADMIN.index("async def list_organizations("):]
        blocco = blocco[:blocco.index("async def _filtro_regia_q")]
        for p in ('q: Optional[str] = Query(', 'stato: Optional[str] = Query(',
                  'telefono: Optional[str] = Query(', '"^(account|bozza|pagina|online)$"',
                  '"^(si|no)$"', "conteggi=conteggi", "list_organizations_regia(",
                  "stato_profilo(d) for d in docs", "email_verificata"):
            assert p in blocco, p
        # i conteggi si calcolano PRIMA dei filtri stato/telefono (sulla sola q)
        assert blocco.index("conteggi = _conteggi(stati)") < blocco.index("if stato and st")

    def test_la_ricerca_copre_le_cinque_cose(self):
        blocco = ADMIN[ADMIN.index("async def _filtro_regia_q"):][:2500]
        for campo in ('{"name": rx}', '{"public_profile.nome_persona": rx}', '{"public_slug": rx}',
                      '{"public_profile.public_phone": rx}', '{"email": rx', '{"slug": rx',
                      're.escape(q)', '"$options": "i"'):
            assert campo in blocco, campo

    def test_la_riga_ha_i_campi_nuovi_solo_aggiunti(self):
        for campo in ("nome_persona", "nome_pubblico", "telefono", "telefono_pubblico",
                      "stato_profilo", "n_servizi", "bio_len", "email_verificata"):
            assert f"{campo}: Optional[" in MODELLO, campo
        assert "conteggi: Dict[str, int]" in MODELLO
        # i letterali di ieri (test_regia_operatori) restano
        for campo in ("directory_listed", "profile_published", "admin_email", "profile_slug"):
            assert campo in MODELLO
        for lit in ("slug_pubblico", "pubblicate = set(slug_pubblico)", "email_titolare", '"is_published": True'):
            assert lit in ADMIN, lit
        from routers.admin import _org_summary
        s = _org_summary({"id": "o1", "name": "Org", "created_at": "2026-07-10T00:00:00+00:00"})
        assert s.stato_profilo is None and s.nome_pubblico == "Org"

    def test_la_proiezione_e_esplicita(self):
        blocco = REPO[REPO.index("PROIEZIONE_REGIA = {"):REPO.index("async def list_organizations_regia")]
        for campo in ('"public_profile.nome_persona": 1', '"public_profile.public_phone": 1',
                      '"public_profile.show_contacts": 1', '"public_profile.bio": 1',
                      '"exclude_from_listings": 1', '"public_slug": 1',
                      '"store_settings.is_storefront_published": 1'):
            assert campo in blocco, campo
        assert '"public_profile.photos"' not in blocco and '"public_profile.link_page"' not in blocco
        assert '"is_sample": {"$ne": True}' in REPO

    def test_filtri_e_conteggi_dal_vivo(self):
        """Prima girava in-process (motor + loop condiviso: fragile nel giro
        completo); ora contro il server vivo, che e' la cosa vera."""
        tutti = _lista_live({"limit": 200})
        online = _lista_live({"limit": 200, "stato": "online"})
        senza = _lista_live({"limit": 200, "telefono": "no"})
        assert set(tutti["conteggi"]) == {"account", "bozza", "pagina", "online"}
        assert sum(tutti["conteggi"].values()) == tutti["total"] == len(tutti["items"])
        assert online["total"] == tutti["conteggi"]["online"] and all(i["stato_profilo"] == "online" for i in online["items"])
        assert online["conteggi"] == tutti["conteggi"]          # i conteggi non seguono il filtro di stato
        assert all(not i["telefono"] for i in senza["items"])
        if tutti["items"]:
            riga = tutti["items"][0]
            if riga.get("admin_email"):
                per_email = _lista_live({"limit": 200, "q": riga["admin_email"]})
                assert any(i["id"] == riga["id"] for i in per_email["items"])
            per_nome = _lista_live({"limit": 200, "q": riga["name"][:6].upper()})
            assert any(i["id"] == riga["id"] for i in per_nome["items"])

    def test_live_http(self):
        d = _lista_live({"limit": 200})
        assert set(d["conteggi"]) == {"account", "bozza", "pagina", "online"}
        assert {"items", "total", "skip", "limit"} <= set(d)
        for row in d["items"]:
            assert row["stato_profilo"] in ("account", "bozza", "pagina", "online")
            for k in ("nome_pubblico", "telefono", "telefono_pubblico", "n_servizi", "bio_len", "email_verificata"):
                assert k in row, k
        online = _lista_live({"limit": 200, "stato": "online"})
        assert all(r["stato_profilo"] == "online" for r in online["items"])
        assert online["total"] == d["conteggi"]["online"]
        r = requests.get(f"{BASE_URL}/api/admin/organizations", headers=_sys_headers(),
                         params={"stato": "boh"}, timeout=10)
        assert r.status_code == 422


# ── A3 · l'estrazione del pulitore ─────────────────────────────────────────

class TestA3Estrazione:
    def test_la_whitelist_resta_nel_router_e_la_rotta_usa_il_servizio(self):
        assert "_PUBLIC_PROFILE_FIELDS = {" in ORGS and '"bio": 1000' in ORGS and '"nome_persona": 80' in ORGS
        rotta = ORGS[ORGS.index('@router.patch("/current/public-profile")'):][:2200]
        assert "from services.profilo_pubblico import dopo_salvataggio, pulisci" in rotta
        assert "updates = pulisci(body)" in rotta
        assert 'await dopo_salvataggio(current_user["organization_id"], updates)' in rotta
        # la logica inline e' USCITA dalla rotta (vive una volta sola)
        assert "for field, max_len in _PUBLIC_PROFILE_FIELDS.items()" not in rotta
        assert "NORMALIZZATORI" not in rotta and "clean_disciplines" not in rotta
        assert 'raise HTTPException(status_code=400, detail="Nessun campo valido")' in rotta
        # e nel servizio c'e' tutta, nello stesso ordine
        for passo in ("_PUBLIC_PROFILE_FIELDS.items()", "public_profile.nome_persona", "NORMALIZZATORI",
                      "show_contacts", "_clean_link_page", 'updates["name"]', "_PP_PHOTOS_MAX", "_PP_LANGS",
                      "clean_disciplines", "translations", "public_profile.geo", "normalizza_sedi"):
            assert passo in SERVIZIO, passo
        for effetto in ("_geocode_profile_if_needed", "_allinea_sedi_dagli_specchi", "_ensure_public_surface",
                        "_invalidate_resolve_org_cache", "_ping_operator_indexnow"):
            assert effetto in SERVIZIO, effetto

    def test_pulisci_stesso_comportamento(self):
        from services.profilo_pubblico import pulisci
        u = pulisci({"bio": "  ciao  ", "tagline": "", "city": None, "boh": "x", "nome_persona": "  Anna   Bianchi ",
                     "name": "   ", "show_contacts": 1, "instagram": "@anna.b", "website": "esempio.it",
                     "disciplines": ["yoga", "yoga", "non-esiste"], "languages": ["it", "xx", "en"],
                     "photos": ["https://a/1.jpg", "", 3], "latitude": "40.5", "longitude": "17.2",
                     "translations": {"en": {"bio": " b ", "tagline": ""}, "zz": {"bio": "x"}}})
        assert u["public_profile.bio"] == "ciao" and u["public_profile.tagline"] is None
        assert u["public_profile.city"] is None and "public_profile.boh" not in u and "boh" not in u
        assert u["public_profile.nome_persona"] == "Anna Bianchi"
        assert "name" not in u                                     # il vuoto NON cancella
        assert u["public_profile.show_contacts"] is True
        assert u["public_profile.instagram"] == "https://instagram.com/anna.b"
        assert u["public_profile.website"].startswith("https://")
        assert u["public_profile.disciplines"] == ["yoga"]
        assert u["public_profile.languages"] == ["it", "en"]
        assert u["public_profile.photos"] == ["https://a/1.jpg"]
        assert u["public_profile.latitude"] == 40.5 and u["public_profile.geo"]["coordinates"] == [17.2, 40.5]
        assert u["public_profile.translations"] == {"en": {"bio": "b"}}
        assert pulisci({"interview": [{"q": "x"}]}) == {}
        assert pulisci({"name": "Studio Zen "})["name"] == "Studio Zen"
        s = pulisci({"sedi": [{"citta": "Lecce", "regione": "Puglia", "lat": 40.35, "lng": 18.17}]})
        assert s["public_profile.city"] == "Lecce" and s["public_profile.region"] == "Puglia"
        assert s["public_profile.geo"]["type"] == "MultiPoint" and len(s["public_profile.sedi"]) == 1


# ── A4 · la rotta admin ────────────────────────────────────────────────────

class TestA4RottaAdmin:
    def test_esiste_ed_e_del_system_admin_con_motivo_e_audit(self):
        assert ADMIN.count('"/organizations/{org_id}/public-profile"') == 2   # GET + PATCH
        blocco = ADMIN[ADMIN.index("async def admin_update_public_profile"):][:3500]
        assert "require_system_admin" in blocco
        assert "_MOTIVO_MIN, _MOTIVO_MAX = 3, 300" in ADMIN
        assert "from services.profilo_pubblico import dopo_salvataggio, pulisci" in blocco
        assert '"action": "PUBLIC_PROFILE_ADMIN_EDIT"' in blocco
        assert '"target_type": "organization"' in blocco
        for k in ('"campi":', '"prima":', '"dopo":', '"motivo":', '"actor_role": "system_admin"', '"expire_at": now_dt'):
            assert k in blocco, k
        assert "_VALORE_BREVE = 120" in ADMIN
        assert "send_email" not in blocco                # nessuna email all'operatore
        assert "return await _profilo_pubblico_payload(org_id)" in blocco

    def test_valori_brevi(self):
        from routers.admin import _valore_breve
        assert _valore_breve("x" * 500) == "x" * 120
        assert _valore_breve(None) is None and _valore_breve(True) is True
        assert len(_valore_breve(["a" * 200])) == 120

    def test_patch_dal_vivo_scrive_audit_e_ripristina(self):
        """Contro il server vivo: 422 senza motivo, 400 senza campi, poi una
        modifica vera con riga di audit (prima/dopo/motivo) e ripristino."""
        h = _sys_headers()
        d = _lista_live({"limit": 5, "q": "admin@demo.com"})
        if not d["items"]:
            pytest.skip("org demo assente nel db locale")
        org_id = d["items"][0]["id"]
        url = f"{BASE_URL}/api/admin/organizations/{org_id}/public-profile"
        prima = requests.get(url, headers=h, timeout=10)
        if prima.status_code == 404:
            pytest.skip("backend su :8000 non riavviato col Lotto A")
        assert prima.status_code == 200, prima.text
        prima = prima.json()
        assert requests.patch(url, json={"tagline": "x"}, headers=h, timeout=10).status_code == 422
        assert requests.patch(url, json={"motivo": "prova", "boh": 1}, headers=h, timeout=10).status_code == 400
        marker = "Guardia SA4"
        r = requests.patch(url, json={"tagline": marker, "motivo": "  test   guardia SA4  "}, headers=h, timeout=10)
        assert r.status_code == 200, r.text
        dopo = r.json()
        assert dopo["tagline"] == marker and set(prima) == set(dopo)
        logs = requests.get(f"{BASE_URL}/api/admin/audit-logs", headers=h,
                            params={"limit": 20}, timeout=10).json()
        righe = logs.get("items") or logs.get("logs") or (logs if isinstance(logs, list) else [])
        riga = next((x for x in righe if x.get("action") == "PUBLIC_PROFILE_ADMIN_EDIT"
                     and x.get("target_id") == org_id), None)
        # ripristino PRIMA delle asserzioni, cosi' un rosso non lascia il marker
        rr = requests.patch(url, json={"tagline": prima.get("tagline") or "", "motivo": "ripristino guardia SA4"},
                            headers=h, timeout=10)
        assert riga, "manca la riga di audit"
        assert riga["metadata"]["campi"] == ["public_profile.tagline"]
        assert riga["metadata"]["prima"] == {"public_profile.tagline": prima.get("tagline")}
        assert riga["metadata"]["dopo"] == {"public_profile.tagline": marker}
        assert riga["metadata"]["motivo"] == "test guardia SA4"
        assert rr.status_code in (200, 400)      # 400 = tagline vuota, niente da cambiare

    def test_live_http_chiuso_ai_non_admin(self):
        r = requests.patch(f"{BASE_URL}/api/admin/organizations/x/public-profile",
                           json={"motivo": "prova", "tagline": "x"}, timeout=10)
        assert r.status_code in (401, 403, 404, 405)     # 404/405 = server non riavviato


# ── A5 · frontend ──────────────────────────────────────────────────────────

class TestA5Frontend:
    def test_la_regia_sopra_la_tabella(self):
        for tid in ("org-cerca", "org-senza-telefono", "org-da-rivedere", "org-chi", "org-regia"):
            assert f'data-testid="{tid}"' in TAB, tid
        assert "data-testid={`org-stato-${s}`}" in TAB
        assert "const STATI_PROFILO = ['account', 'bozza', 'pagina', 'online'];" in TAB
        assert "extra.q = qServer" in TAB and "extra.stato = statoFiltro" in TAB and "extra.telefono = 'no'" in TAB
        assert "setConteggi(res.data.conteggi || {})" in TAB
        # coda «da rivedere»: i quattro motivi
        blocco = TAB[TAB.index("function motiviDaRivedere"):][:700]
        for m in ("bio breve", "solo marchio", "senza telefono", "pagina senza listino"):
            assert m in blocco, m
        assert "const BIO_BUONA = 300;" in TAB

    def test_la_colonna_chi_e_la_scheda_dal_nome(self):
        assert "org.nome_pubblico || org.name" in TAB
        assert "org.telefono_pubblico" in TAB and "org.email_verificata" in TAB
        assert "import OrgBusinessProfileDialog from './OrgBusinessProfileDialog';" in TAB
        assert "onClick={() => apriScheda(org.id)}" in TAB
        assert "foglioIniziale={schedaFoglio}" in TAB
        # i letterali di ieri restano (test_regia_operatori)
        for lit in ("handleToggleDirectory", "setDirectoryListed", "'✓ Directory' : 'Directory'",
                    "org.admin_email", "non pubblicato", "LO SPECCHIETTO"):
            assert lit in TAB, lit
        assert "/o/${org.profile_slug}" in TAB.replace("`", "")

    def test_l_api_e_il_form_admin(self):
        assert "listOrganizations: (skip = 0, limit = 100, extra = {}) =>" in API
        assert "getOrgPublicProfile:" in API and "setOrgPublicProfile:" in API
        assert "api.patch(`/admin/organizations/${orgId}/public-profile`, body)" in API
        for tid in ("admin-profilo-form", "admin-profilo-motivo", "admin-profilo-salva",
                    "admin-profilo-bio", "admin-profilo-telefono", "admin-profilo-anteprima"):
            assert f'data-testid="{tid}"' in FORM, tid
        assert "<SelettoreDiscipline" in FORM and "<LocationAutocomplete" in FORM
        assert "nomePubblico(form.nome_persona, form.name)" in FORM
        assert "adminAPI.setOrgPublicProfile(orgId, { ...modifiche, motivo: pulito(motivo) })" in FORM
        assert "const BIO_MAX = 1000;" in FORM and "const BIO_BUONA = 300;" in FORM
        assert "MOTIVO_MIN = 3" in FORM and "MOTIVO_MAX = 300" in FORM
        assert "useTranslation('settings')" in FORM and "useTranslation('settings')" in TAB
        # niente chiavi nuove sotto publicProfile.* (guardia OP4) e niente «organizzatori»
        assert not re.search(r"publicProfile\.", FORM)
        for src in (FORM, TAB, DIALOG):
            assert "organizzator" not in src.lower()

    def test_la_scheda_360_ha_il_foglio_profilo(self):
        assert "import OrgProfiloAdminTab from './OrgProfiloAdminTab';" in DIALOG
        assert 'data-testid="business-fogli"' in DIALOG and "data-testid={`business-foglio-${k}`}" in DIALOG
        assert "<OrgProfiloAdminTab orgId={orgId}" in DIALOG
        # i letterali di ieri (P3, SA4, SA6)
        for lit in ('data-testid="business-recapito"', "business-profile", "pro_breakeven_reached", "trial-history"):
            assert lit in DIALOG, lit
