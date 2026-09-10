"""Ciclo LX (5/9/2026) — Aurya letta dalle AI.

Verificato sul vivo: i crawler AI vedono lo stesso HTML di Google e
nessuno e' bloccato, ma l'Organization diceva ancora «la casa dei
ritiri: trova e prenota», /llms.txt conosceva solo Magazine e rete, e
le pagine cardine erano gusci per i bot. Queste guardie tengono
l'identita' in UN posto (services/identita.py), la copia italiana del
renderer uguale al frontend (assets/copia_it), e ogni pilastro
nominato in /llms.txt. Piano in docs/LLM_VISIBILITA_PIANO_2026-09.md.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
import requests

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
BASE = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8000")


def _testo(html: str) -> str:
    b = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    b = re.sub(r"<[^>]+>", " ", b)
    return re.sub(r"\s+", " ", b).strip()


def _get(path: str):
    try:
        return requests.get(f"{BASE}{path}", timeout=30, allow_redirects=False)
    except Exception:
        pytest.skip("backend locale non raggiungibile")


def _jsonld(html: str):
    out = []
    for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
        d = json.loads(m)
        out += d if isinstance(d, list) else [d]
    return out


class TestLx2LIdentitaInUnPostoSolo:
    def test_la_descrizione_e_quella_di_oggi(self):
        from services.identita import IDENTITA, organization_jsonld
        d = IDENTITA["description"]
        for parola in ("professionisti", "Magazine", "Aurya Sound", "meditazioni", "Cerchio", "ritiri"):
            assert parola in d, f"la descrizione non nomina «{parola}»"
        assert "trova e prenota" not in d, "il posizionamento marketplace e' spento"
        org = organization_jsonld("https://aurya.life")
        assert org["description"] == d and org["sameAs"] and org["knowsAbout"]
        assert org["slogan"] == IDENTITA["tagline"]

    def test_la_home_porta_organization_e_website_dall_identita(self):
        src = (BACKEND_DIR / "routers" / "seo_shell.py").read_text()
        assert "_identita.website_jsonld(base)" in src
        assert "_identita.organization_jsonld(base)" in src
        assert "La casa dei ritiri olistici italiani" not in src.split("_meta_home")[1][:3000]
        r = _get("/__seo/")
        tipi = [d.get("@type") for d in _jsonld(r.text)]
        assert "Organization" in tipi and "WebSite" in tipi
        org = next(d for d in _jsonld(r.text) if d.get("@type") == "Organization")
        assert "Aurya Sound" in org["description"]


class TestLx3LaCopiaVeraAiBot:
    def test_la_copia_italiana_combacia_col_frontend(self):
        esito = subprocess.run([sys.executable, "scripts/copia_locales.py", "--controlla"],
                               cwd=BACKEND_DIR, capture_output=True, text=True)
        assert esito.returncode == 0, esito.stdout + esito.stderr

    def test_i_corpi_usano_la_copia(self):
        from services.identita import CORPI, corpo_chi_siamo, corpo_manifesto, corpo_professionisti
        assert set(CORPI) >= {"chi-siamo", "manifesto", "entra-nella-rete", "newsletter", "meditazioni"}
        land = json.loads((REPO / "frontend/src/locales/it/landings.json").read_text())
        assert land["aboutPage"]["pathsTitle"] in corpo_chi_siamo()
        assert land["manifesto"]["p1Title"] in corpo_manifesto()
        pre = json.loads((REPO / "frontend/src/locales/it/prelaunch.json").read_text())
        assert pre["opPro"]["faq2q"] in corpo_professionisti()

    def test_le_meditazioni_dicono_le_frasi_della_pagina_viva(self):
        from services.identita import corpo_meditazioni
        jsx = re.sub(r"\s+", " ", (REPO / "frontend/src/features/frequenze/MeditazioniPage.js").read_text())
        for frase in ("sessioni vibrazionali composte dai professionisti della rete",   # RB7: lessico per chi cerca
                      "entrare è gratis, e ti apre anche i ritiri in anteprima"):
            assert frase in jsx and frase in corpo_meditazioni()

    @pytest.mark.parametrize("path,minimo", [("/chi-siamo", 1500), ("/manifesto", 2000),
                                             ("/entra-nella-rete", 3000), ("/newsletter", 800),
                                             ("/meditazioni", 600), ("/operatori", 600)])   # /operatori: in locale pochi profili
    def test_le_pagine_cardine_non_sono_gusci(self, path, minimo):
        r = _get(f"/__seo{path}")
        assert r.status_code == 200
        n = len(_testo(r.text))
        assert n >= minimo, f"{path}: {n} caratteri (minimo {minimo})"


class TestLx4IDatiStrutturati:
    @pytest.mark.parametrize("path,tipo", [("/chi-siamo", "AboutPage"), ("/manifesto", "Article"),
                                           ("/entra-nella-rete", "FAQPage"), ("/sound", "CollectionPage"),
                                           ("/sound/calm", "CreativeWork"), ("/meditazioni", "CollectionPage")])
    def test_il_tipo_giusto_per_pagina(self, path, tipo):
        r = _get(f"/__seo{path}")
        assert r.status_code == 200
        tipi = [d.get("@type") for d in _jsonld(r.text)]
        assert tipo in tipi, f"{path}: {tipi}"

    def test_operatori_e_una_lista(self):
        r = _get("/__seo/operatori")
        tipi = [d.get("@type") for d in _jsonld(r.text)]
        if "ItemList" not in tipi:
            pytest.skip("nessun professionista pubblicato in locale")
        lista = next(d for d in _jsonld(r.text) if d.get("@type") == "ItemList")
        assert lista["itemListElement"][0]["url"].split("/")[-2] == "o"

    def test_le_faq_dei_professionisti_sono_quelle_della_landing(self):
        from services.identita import faq_professionisti
        coppie = faq_professionisti()
        # RB2 (10/9/2026): sei domande — la sesta e' «Posso uscire quando
        # voglio?», e le risposte riscritte vivono su chiavi nuove
        assert len(coppie) == 6
        assert coppie[0][0] == "Quanto costa?" and "gratuito" in coppie[0][1]
        assert coppie[5][0].startswith("Posso smettere di usare Aurya")   # founder 10/9 sera


class TestLx1LlmsTxt:
    def test_ogni_pilastro_e_nominato(self):
        r = _get("/llms.txt")
        assert r.status_code == 200
        t = r.text
        for sezione in ("## Cos'è Aurya, in dieci righe", "## La rete dei professionisti",
                        "## Aurya Sound", "### La biblioteca delle frequenze",
                        "### Il Laboratorio del suono", "## Le meditazioni e il Cerchio di Aurya",
                        "## Ritiri ed esperienze", "## Magazine"):
            assert sezione in t, f"manca la sezione «{sezione}»"
        for parola in ("frequenze", "biblioteca", "meditazioni", "Lab", "Crea Studio", "Cerchio", "ritiri"):
            assert parola in t, f"llms.txt non nomina «{parola}»"
        assert t.count("/sound/esplora/") >= 30, "la biblioteca deve elencare le schede"
        assert "trova e prenota" not in t

    def test_llms_full_apre_con_le_pagine_cardine(self):
        r = _get("/llms-full.txt")
        assert r.status_code == 200
        t = r.text
        for titolo in ("## Il Manifesto", "## Chi siamo", "## Per i professionisti",
                       "## Il Cerchio di Aurya", "## Le meditazioni"):
            assert titolo in t, titolo
        assert t.index("## Il Manifesto") < t.index("Articoli inclusi") + 100000
