"""Ciclo SR, fase 0 (8/9/2026) — le strutture ricettive per i ritiri.

Un solo modello con due porte (oggi il pannello di sistema, in fase 1
l'area della struttura), tutto ISOLATO dal mondo dei professionisti:
file nuovi, collezione propria, router proprio, rotte riservate nel
registro. Piano: docs/STRUTTURE_FASE0_PIANO_2026-09.md.
"""
import json
import os
import re
import sys
from pathlib import Path

import pytest
import requests

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
BASE = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8000")
FE = REPO / "frontend" / "src"


def _login(email):
    try:
        r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": "demo1234"}, timeout=10)
    except Exception:
        pytest.skip("backend locale non raggiungibile")
    if r.status_code != 200:
        pytest.skip(f"login {email} non disponibile ({r.status_code}: rate limit?)")
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


class TestIsolamento:
    """Il mondo delle strutture non tocca quello dei professionisti."""

    def test_nessun_file_dei_professionisti_importa_le_strutture(self):
        vietati = ["struttura_repository", "models.struttura", "admin_strutture", "strutture_email"]
        for f in (BACKEND_DIR / "routers").glob("*.py"):
            if f.name in ("admin_strutture.py", "strutture.py"):
                continue
            src = f.read_text()
            for v in vietati:
                assert v not in src, f"{f.name} importa {v}: il mondo strutture deve restare isolato"
        assert "strutture" not in (BACKEND_DIR / "models" / "organization.py").read_text()

    def test_il_menu_dei_professionisti_non_sa_delle_strutture(self):
        layout = (FE / "components" / "Layout.js").read_text()
        assert "struttur" not in layout.lower()

    def test_in_fase_0_non_esiste_una_pagina_pubblica(self):
        """Niente /strutture ne' /struttura finche' App.js non ha le rotte
        (fase 1): il registro non apre porte su stanze vuote, l'ignoto fa
        404. La prenotazione vive nella nota del registro."""
        reg = json.loads((BACKEND_DIR / "config" / "rotte.json").read_text())
        for cat in ("pubblica", "servizio", "app"):
            assert "struttura" not in reg[cat] and "strutture" not in reg[cat]
        assert "struttura/strutture" in reg["_note_sui_casi_strani"]
        app = (FE / "App.js").read_text()
        assert not re.search(r'<Route\s+path="/strutt', app)
        nginx = (REPO / "deploy" / "nginx" / "nginx.conf").read_text()
        assert "|struttura|" not in nginx and "|strutture|" not in nginx

    def test_solo_il_system_admin_entra_nel_pannello(self):
        h_op = _login("admin@demo.com")
        assert requests.get(f"{BASE}/api/admin/strutture", headers=h_op, timeout=10).status_code == 403
        assert requests.get(f"{BASE}/api/admin/strutture/schema", headers=h_op, timeout=10).status_code == 403


class TestModello:
    def test_le_liste_chiuse_sono_una_fonte_sola(self):
        from models.struttura import SCHEMA_LISTE, REGIONI, schema_per_frontend, SEZIONI
        s = schema_per_frontend()
        assert set(s["liste"]) == set(SCHEMA_LISTE) and len(s["regioni"]) == 20 == len(REGIONI)
        assert tuple(s["sezioni"]) == SEZIONI and len(SEZIONI) == 11
        for nome, lista in SCHEMA_LISTE.items():
            valori = [v for v, _ in lista]
            assert len(valori) == len(set(valori)), f"{nome}: valori doppi"
            assert all(e for _, e in lista), f"{nome}: etichetta vuota"

    def test_i_derivati_seguono_le_sezioni(self):
        from models.struttura import calcola_derivati
        d = calcola_derivati({
            "identita": {"tipo": "masseria"}, "luogo": {"regione": "Puglia"},
            "ricettivita": {"camere": [{"tipologia": "doppia", "quantita": 6, "letti": 2},
                                       {"tipologia": "camerata", "quantita": 1, "letti": 8}]},
            "spazi": {"sale": [{"mq": 90}, {"mq": 40}], "spazi_esterni": [{"tipo": "uliveto"}]},
            "comfort": {"piscina": "esterna", "aria_condizionata": "nessuna"},
            "prezzi": {"stagioni": [{"tariffe": [{"base": "persona_notte", "prezzo": 130},
                                                 {"base": "persona_notte", "prezzo": 95},
                                                 {"base": "camera_notte", "prezzo": 40},
                                                 {"base": "persona_notte", "prezzo": None}]}]},
            "adatta": {"adatta_a": ["yoga"]}, "redazione": {},
        })
        assert d["posti_letto_totali"] == 20 and d["prezzo_da"] == 95
        assert d["ha_sala"] and d["sala_mq_max"] == 90 and d["ha_piscina"] and not d["ha_aria"]
        assert d["ha_spazi_esterni"] and d["stato_pipeline"] == "da_contattare"
        # i posti dichiarati vincono sul calcolo
        d2 = calcola_derivati({"ricettivita": {"camere": [{"quantita": 1, "letti": 2}], "posti_letto_dichiarati": 30}})
        assert d2["posti_letto_totali"] == 30

    def test_le_liste_chiuse_si_fanno_rispettare(self):
        from models.struttura import errori_liste
        assert errori_liste("luogo", {"regione": "Marte"})
        assert errori_liste("cucina", {"regimi": ["vegano", "marziano"]})
        assert errori_liste("ricettivita", {"camere": [{"tipologia": "igloo", "quantita": 1, "letti": 1}]})
        assert not errori_liste("cucina", {"regimi": ["vegano"], "cucina": "struttura"})

    def test_lo_slug_e_pulito(self):
        from models.struttura import slugify
        assert slugify("Masseria Montanari — Sala a volta!") == "masseria-montanari-sala-a-volta"
        assert slugify("Èremo d'Ùmbria") == "eremo-d-umbria"


class TestFlussoLive:
    """Crea, salva per sezione, filtra, chiedi da operatore, decidi: pulito alla fine."""

    def test_dal_pannello_alla_richiesta(self):
        h = _login("sysadmin@demo.com")
        h_op = _login("admin@demo.com")
        ids, rid = [], None
        try:
            r = requests.post(f"{BASE}/api/admin/strutture", headers=h,
                              json={"nome": "Guardia SR", "regione": "Puglia", "tipo": "masseria"}, timeout=10)
            assert r.status_code == 201, r.text
            sid = r.json()["id"]; ids.append(sid)
            assert r.json()["slug"] == "guardia-sr" and r.json()["organization_id"] is None
            r = requests.patch(f"{BASE}/api/admin/strutture/{sid}", headers=h, json={
                "ricettivita": {"camere": [{"tipologia": "doppia", "quantita": 5, "letti": 2}]},
                "spazi": {"sale": [{"nome": "Sala", "mq": 60}]},
                "comfort": {"piscina": "esterna"},
                "prezzi": {"stagioni": [{"nome": "alta", "tariffe": [{"base": "persona_notte", "prezzo": 88}]}]},
                "adatta": {"adatta_a": ["yoga", "silenzio"]},
                "redazione": {"stato_pipeline": "in_lista"}}, timeout=10)
            assert r.status_code == 200, r.text
            d = r.json()["derivati"]
            assert d["posti_letto_totali"] == 10 and d["prezzo_da"] == 88 and d["ha_sala"] and d["ha_piscina"]
            # una sezione salvata NON cancella le altre
            r = requests.patch(f"{BASE}/api/admin/strutture/{sid}", headers=h, json={"cucina": {"cucina": "struttura", "regimi": ["vegano"]}}, timeout=10)
            assert r.status_code == 200 and r.json()["ricettivita"]["camere"][0]["quantita"] == 5
            # lista chiusa violata → 400 col campo nominato
            r = requests.patch(f"{BASE}/api/admin/strutture/{sid}", headers=h, json={"luogo": {"regione": "Marte"}}, timeout=10)
            assert r.status_code == 400 and "luogo.regione" in r.text
            # filtri combinati (parametri ripetuti) + facet
            r = requests.get(f"{BASE}/api/admin/strutture", headers=h, timeout=10,
                             params={"regione": ["Puglia"], "posti_letto_min": 8, "sala": "true",
                                     "piscina": "true", "prezzo_max": 90, "adatta_a": ["yoga", "silenzio"], "q": "guardia"})
            assert r.status_code == 200 and any(x["id"] == sid for x in r.json()["righe"])
            assert any(f["valore"] == "Puglia" for f in r.json()["facet"]["regione"])
            r = requests.get(f"{BASE}/api/admin/strutture", headers=h, params={"prezzo_max": 50, "q": "guardia"}, timeout=10)
            assert not any(x["id"] == sid for x in r.json()["righe"])
            # storia dei contatti
            r = requests.post(f"{BASE}/api/admin/strutture/{sid}/storia", headers=h, json={"nota": "prima chiamata"}, timeout=10)
            assert r.status_code == 200 and r.json()["storia"][0]["nota"] == "prima chiamata"
            # la richiesta dell'operatore e la decisione
            r = requests.post(f"{BASE}/api/strutture/richieste", headers=h_op, timeout=10,
                              json={"zona": "Puglia", "periodo": "ottobre", "persone": 12, "esigenze": "sala coperta"})
            assert r.status_code == 201, r.text
            rid = r.json()["id"]
            r = requests.get(f"{BASE}/api/admin/strutture/richieste/tutte", headers=h, timeout=10)
            assert any(x["id"] == rid for x in r.json()["righe"])
            r = requests.patch(f"{BASE}/api/admin/strutture/richieste/{rid}", headers=h,
                               json={"stato": "proposta", "strutture_proposte": [sid], "nota_interna": "solo noi"}, timeout=10)
            assert r.status_code == 200 and r.json()["stato"] == "proposta"
            r = requests.get(f"{BASE}/api/strutture/richieste/mie", headers=h_op, timeout=10)
            mia = next(x for x in r.json()["righe"] if x["id"] == rid)
            assert mia["stato"] == "proposta" and "nota_interna" not in mia
            # l'operatore non vede le strutture
            assert requests.get(f"{BASE}/api/admin/strutture/{sid}", headers=h_op, timeout=10).status_code == 403
        finally:
            for sid in ids:
                requests.delete(f"{BASE}/api/admin/strutture/{sid}", headers=h, timeout=10)
            if rid:
                from pymongo import MongoClient
                db = MongoClient(os.environ["MONGO_URL"])[os.environ.get("DB_NAME", "retreat_db")]
                db.richieste_struttura.delete_many({"id": rid})


class TestPannello:
    def test_il_tab_e_la_scheda_esistono(self):
        page = (FE / "features" / "admin" / "AdminPage.js").read_text()
        assert 'value="strutture"' in page and "StruttureTab" in page
        app = (FE / "App.js").read_text()
        assert 'path="/admin/strutture/:id"' in app and "SystemAdminRoute" in app.split('path="/admin/strutture/:id"')[1][:200]
        scheda = (FE / "features" / "admin" / "strutture" / "StrutturaScheda.js").read_text()
        for n in range(1, 12):
            assert f'titolo="{n} ·' in scheda, f"manca la sezione {n}"
        assert scheda.count("onSalva={() => salvaSezione(") == 11, "ogni sezione ha il suo Salva"
        assert 'data-testid={`${testid}-salva`}' in scheda
        api = (FE / "features" / "admin" / "strutture" / "api.js").read_text()
        assert "URLSearchParams" in api and "p.append(k, x)" in api, "le liste vanno come parametri ripetuti"

    def test_il_gestionale_ha_solo_il_pulsante_della_richiesta(self):
        events = (FE / "features" / "events" / "EventsListPage.js").read_text()
        assert 'data-testid="events-cerca-struttura"' in events and "RichiestaStrutturaDialog" in events
        dialog = (FE / "features" / "events" / "components" / "RichiestaStrutturaDialog.jsx").read_text()
        assert "/strutture/richieste" in dialog and "/admin/strutture" not in dialog
