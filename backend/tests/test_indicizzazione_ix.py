"""Ciclo IX (5/9/2026) — le 74 pagine non indicizzate di Search Console.

Crawl di prod come Googlebot: le 131 URL della sitemap erano pulite;
i difetti stavano FUORI dalla sitemap. Dieci radici di prefisso senza
slug (/e, /p, /o, /s...) rispondevano 200 con la stessa shell vuota,
indicizzabile: per Google dieci pagine identiche («duplicata, canonica
diversa»). /index.html e /ritiri ripetevano la home, /esplora-operatori
la directory. /sound rendeva 55 caratteri, le stanze del Lab 330; le
14 categorie del Magazine erano orfane dalla shell di /blog; la home
non linkava nessun profilo.

Queste guardie tengono chiuse le porte: nel registro, in nginx, nel
renderer e nella maglia interna. Analisi in
docs/SEO_INDICIZZAZIONE_ANALISI_2026-09.md.
"""
import asyncio
import hashlib
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
REGISTRO = json.loads((BACKEND_DIR / "config" / "rotte.json").read_text())
NGINX = (REPO / "deploy" / "nginx" / "nginx.conf").read_text()


def _testo(html: str) -> str:
    b = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    b = re.sub(r"<[^>]+>", " ", b)
    return re.sub(r"\s+", " ", b).strip()


def _shell(path: str):
    try:
        r = requests.get(f"{BASE}/__seo{path}", timeout=30, allow_redirects=False)
    except Exception:
        pytest.skip("backend locale non raggiungibile")
    return r


class TestIx1LePorteChiuse:
    """Le radici senza slug fanno 404, i doppioni fanno 301."""

    def test_il_registro_dichiara_le_radici_e_i_rimandi(self):
        assert set(REGISTRO["solo_con_slug"]) == {"co", "dg", "e", "frequenze", "l", "o", "p", "ph", "r", "s"}
        # RB7 (10/9/2026): /come-funziona (guscio vuoto in fase rete) e' un 301 come /ritiri
        # RE (10/9/2026 sera): /ritiri ed /esplora-ritiri rimandano al calendario /esperienze
        assert REGISTRO["rimandi"] == {"index.html": "/", "ritiri": "/esperienze", "come-funziona": "/manifesto"}
        assert REGISTRO["rimandi_prefisso"] == {"esplora-operatori": "/operatori", "esplora-ritiri": "/esperienze"}
        for seg in REGISTRO["solo_con_slug"]:
            assert seg in REGISTRO["pubblica"], f"{seg} deve restare pubblica (con slug)"

    def test_nginx_e_generato_dal_registro(self):
        esito = subprocess.run([sys.executable, "scripts/genera_rotte_nginx.py", "--controlla"],
                               cwd=BACKEND_DIR, capture_output=True, text=True)
        assert esito.returncode == 0, esito.stdout + esito.stderr

    def test_nginx_ha_le_location_ix1_prima_del_renderer(self):
        blocco = NGINX.split("<<< ROTTE-RENDERER")[1].split("<<< FINE ROTTE-RENDERER")[0]
        assert "location ~ ^/index\\.html/?$ { return 301 /; }" in blocco
        assert "location ~ ^/ritiri/?$ { return 301 /esperienze; }" in blocco   # RE (10/9)
        assert "location ~ ^/esplora\\-ritiri(/.*)?$ { return 301 /esperienze; }" in blocco
        assert "location ~ ^/esplora\\-operatori(/.*)?$ { return 301 /operatori; }" in blocco
        radici = "location ~ ^/(co|dg|e|frequenze|l|o|p|ph|r|s)/?$ {"
        assert radici in blocco
        # PRIMA della location del renderer: fra le regex vince la prima
        assert blocco.index(radici) < blocco.index("Le pagine che hanno (o devono avere) meta server-side")
        # /ritiri/{categoria} NON e' rimandata: solo la radice esatta
        assert "^/ritiri(/.*)?$" not in blocco

    def test_il_renderer_fa_404_sulle_radici_senza_slug(self):
        from routers.seo_shell import resolve_meta
        for seg in REGISTRO["solo_con_slug"]:
            assert asyncio.run(resolve_meta(f"/{seg}")) is None, f"/{seg} deve essere un 404"

    def test_il_collaudo_delle_rotte_sa_le_regole_ix1(self):
        src = (BACKEND_DIR / "scripts" / "collauda_rotte.py").read_text()
        assert "SOLO_CON_SLUG" in src and "RIMANDI" in src
        assert "_NoRedirect" in src, "il 301 si vede, non si segue"


class TestIx2TestoVeroAiBot:
    """Niente gusci: le pagine della sitemap rendono testo vero."""

    SOGLIA = 400

    def test_le_stanze_del_lab_hanno_perche_e_azioni(self):
        from routers.seo_shell import _LAB_STANZE, _LAB_STANZE_COPIA
        assert set(_LAB_STANZE) == set(_LAB_STANZE_COPIA)
        lab = REPO / "frontend" / "src" / "features" / "frequenze" / "lab"
        for stanza, c in _LAB_STANZE_COPIA.items():
            jsx = (lab / f"Lab{stanza.capitalize()}.jsx").read_text()
            assert c["domanda"] in jsx, f"{stanza}: la domanda non e' quella del JSX"
            for azione in c["azioni"]:
                assert azione in jsx, f"{stanza}: azione non nel JSX: {azione[:40]}"
            # il perche' nel JSX ha <b> e &rsquo;: si confrontano le prime parole
            inizio = c["perche"].split(" ")[:5]
            assert " ".join(inizio) in jsx.replace("\n        ", " "), f"{stanza}: il perche' non e' quello del JSX"

    def test_la_home_di_sound_ha_la_copia_della_landing(self):
        from routers.seo_shell import _SOUND_HOME_COPIA
        jsx = (REPO / "frontend" / "src" / "features" / "frequenze" / "SoundLandingPage.js").read_text()
        piatto = re.sub(r"\s+", " ", jsx)
        for k, v in _SOUND_HOME_COPIA.items():
            assert v.split(". ")[0] in piatto, f"SoundLandingPage: manca «{v[:40]}»"

    def test_la_guida_del_renderer_combacia_con_guida_js(self):
        """I dati di /sound/impara e del glossario sono copiati da
        guida.js: se il frontend cambia una voce, qui si vede."""
        from routers.seo_shell import _GUIDA
        js = (REPO / "frontend" / "src" / "features" / "frequenze" / "content" / "guida.js").read_text()
        piatto = js.replace("\\'", "'").replace('\\"', '"')
        for t in _GUIDA["percorso"]:
            assert t in piatto, f"tappa non in guida.js: {t}"
        assert len(_GUIDA["bande"]) == 5 and sum(len(v) for _, v in _GUIDA["glossario"]) >= 17
        for fam, voci in _GUIDA["glossario"]:
            assert f"fam: '{fam}'" in js
            for termine, definizione in voci:
                assert termine in piatto, f"voce non in guida.js: {termine}"
                assert definizione[:40] in piatto, f"definizione cambiata: {termine}"
        for t, hz, d in _GUIDA["bande"]:
            assert f"t: '{t}', hz: '{hz}'" in js

    @pytest.mark.parametrize("path", ["/sound", "/sound/lab", "/sound/lab/banco", "/sound/lab/orecchio",
                                      "/sound/lab/ritratto", "/sound/lab/meraviglie", "/sound/lab/risonanze",
                                      "/sound/impara", "/sound/impara/glossario"])
    def test_le_pagine_sound_non_sono_gusci(self, path):
        r = _shell(path)
        assert r.status_code == 200
        assert len(_testo(r.text)) >= self.SOGLIA, f"{path}: {len(_testo(r.text))} caratteri"


class TestIx3LaMagliaInterna:
    def test_blog_linka_le_categorie_con_una_riga(self):
        from routers.seo_shell import _CATEGORIE_INTRO
        from models.article import ARTICLE_CATEGORIES
        assert set(_CATEGORIE_INTRO) == set(ARTICLE_CATEGORIES), "ogni categoria ha la sua riga"
        r = _shell("/blog")
        assert r.status_code == 200
        assert r.text.count('href="/blog/categoria/') >= 1
        assert "Le categorie del Magazine" in r.text

    def test_la_categoria_ha_intro_e_torna_al_magazine(self):
        r = _shell("/blog/categoria/yoga")
        if r.status_code != 200:
            pytest.skip("categoria yoga vuota in locale")
        assert "Tutte le categorie del Magazine" in r.text

    def test_l_articolo_porta_la_briciola_della_categoria(self):
        src = (BACKEND_DIR / "routers" / "seo_shell.py").read_text()
        assert "briciola = (f'<p><a href=\"/blog\">Magazine</a> › '" in src

    def test_la_home_linka_i_professionisti(self):
        src = (BACKEND_DIR / "routers" / "seo_shell.py").read_text()
        assert "Alcuni professionisti della rete" in src
        assert '"exclude_from_listings": {"$ne": True}' in src.split("Alcuni professionisti della rete")[0][-1500:], \
            "stesso perimetro della directory"


class TestIx4AntiGuscio:
    """Il guardiano: nessuna radice pubblica indicizzabile e vuota, mai
    due radici pubbliche con lo stesso testo."""

    def test_nessuna_radice_pubblica_e_un_guscio_indicizzabile(self):
        vuote, hashes = [], {}
        for seg in sorted(REGISTRO["pubblica"]):
            if seg in REGISTRO["solo_con_slug"] or seg in REGISTRO["rimandi"] or seg in REGISTRO["rimandi_prefisso"]:
                continue
            r = _shell(f"/{seg}")
            if r.status_code != 200:
                continue
            if 'content="noindex"' in r.text:
                continue
            t = _testo(r.text)
            if len(t) < 100:
                vuote.append(f"/{seg} ({len(t)})")
            hashes.setdefault(hashlib.md5(t.encode()).hexdigest(), []).append(f"/{seg}")
        doppi = [v for v in hashes.values() if len(v) > 1]
        assert not vuote, "gusci indicizzabili: " + ", ".join(vuote)
        assert not doppi, "radici pubbliche identiche: " + str(doppi)
