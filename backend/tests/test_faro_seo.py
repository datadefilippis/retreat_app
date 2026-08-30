"""
FA7 (piano FARO, 30/8/2026) — il motore SEO: da 1 pagina a ~37.

Le ~36 schede della biblioteca (contenuto editoriale vero, con grado
di evidenza) vivevano TUTTE dentro /sound/esplora: per Google una
pagina sola. Ora ogni scheda ha il suo indirizzo /sound/esplora/{slug}
— pagina client + shell SSR col testo INTERO + JSON-LD + sitemap —
e il motore e' guidato dai dati: scheda nuova in biblioteca.js →
si rilancia l'esportatore e tutto nasce da solo (queste guardie
fanno rosso finche' non lo fai).
"""
import json
import re
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
FRONTEND = BACKEND.parent / "frontend"
JSON_SEO = BACKEND / "config" / "biblioteca_seo.json"
BIB_JS = (FRONTEND / "src" / "features" / "frequenze"
          / "content" / "biblioteca.js")


def _slug(titolo: str) -> str:
    """La STESSA regola di content/slugScheda.js, replicata per la
    parita' (cambiarla la' senza cambiarla qui = rosso, giusto cosi':
    gli slug sono URL pubblici)."""
    t = titolo.lower()
    for a, b in (("à", "a"), ("è", "e"), ("é", "e"), ("ì", "i"),
                 ("ò", "o"), ("ù", "u")):
        t = t.replace(a, b)
    t = re.sub(r"[^a-z0-9]+", "-", t)
    return t.strip("-")


def _titoli_biblioteca():
    src = BIB_JS.read_text()
    return [m.group(1).replace("\\'", "'")
            for m in re.finditer(r"\{t:'((?:[^'\\\\]|\\\\.)*)'", src)]


class TestParitaBiblioteca:
    def test_ogni_scheda_ha_la_sua_pagina(self):
        dati = json.loads(JSON_SEO.read_text())
        titoli = _titoli_biblioteca()
        assert len(titoli) >= 30, "la biblioteca si e' svuotata?"
        mancanti = [t for t in titoli if _slug(t) not in dati]
        assert not mancanti, (
            f"schede senza pagina SEO: {mancanti} — rilancia "
            "`node frontend/scripts/esporta_biblioteca.mjs`")

    def test_il_json_porta_il_testo_intero(self):
        dati = json.loads(JSON_SEO.read_text())
        for slug, sc in dati.items():
            assert sc.get("full") or sc.get("body"), f"{slug}: scheda vuota"
            assert sc.get("categoria") and sc.get("g")


class TestShellScheda:
    def test_la_shell_serve_il_contenuto_intero(self):
        src = (BACKEND / "routers" / "seo_shell.py").read_text()
        assert "_biblioteca_seo" in src
        assert 'sub == "esplora" and len(parts) == 2' in src
        assert "application/ld+json" in src, "manca il JSON-LD"
        assert "BreadcrumbList" in src
        assert "Provala dal vivo" in src, \
            "il ponte biblioteca→Lab e' l'interlink che conta"

    def test_lo_slug_ignoto_fa_404(self):
        src = (BACKEND / "routers" / "seo_shell.py").read_text()
        blocco = src[src.index('sub == "esplora" and len(parts) == 2'):]
        assert "return None" in blocco[:400], "slug ignoto = 404 onesto"

    def test_la_sitemap_dichiara_le_schede(self):
        src = (BACKEND / "routers" / "seo.py").read_text()
        assert "biblioteca_seo" in src and "sound/esplora/{slug}" in src


class TestPaginaScheda:
    def test_la_rotta_vive_prima_del_catchall(self):
        app = (FRONTEND / "src" / "App.js").read_text()
        i_scheda = app.index('path="/sound/esplora/:slug"')
        i_catch = app.index('path="/sound/lab"')
        assert i_scheda < i_catch

    def test_le_card_linkano_la_pagina(self):
        src = (FRONTEND / "src" / "features" / "frequenze"
               / "FrequenzePage.js").read_text()
        assert "fqz-approfondisci-link" in src
        assert "sluggifica(entry.t)" in src

    def test_la_pagina_ha_briciole_lab_e_sorelle(self):
        src = (FRONTEND / "src" / "features" / "frequenze"
               / "SchedaBibliotecaPage.jsx").read_text()
        for tid in ("scheda-briciole", "scheda-testo", "scheda-lab",
                    "scheda-sorelle", "scheda-ascolta"):
            assert f'data-testid="{tid}"' in src
        assert "risonanz" in src, "il ponte al Lab sceglie la stanza giusta"

    def test_l_esportatore_esiste(self):
        assert (FRONTEND / "scripts" / "esporta_biblioteca.mjs").exists()
        assert (FRONTEND / "src" / "features" / "frequenze" / "content"
                / "slugScheda.js").exists()


class TestFa8InvitoSound:
    """FA8 (FARO) — l'invito unico del mondo gratuito, con la REGOLA
    DEL SILENZIO nel contratto: chi ha la prova della Lettera, un
    account o un login operatore non vede nulla — il controllo sta
    PRIMA del render. Collaudato nel pane: visibile da anonimo su
    scheda e stanza, ASSENTE con la prova in tasca."""

    def test_la_regola_del_silenzio_e_nel_contratto(self):
        src = (FRONTEND / "src" / "features" / "frequenze"
               / "InvitoSound.jsx").read_text()
        assert "if (servito()) return null;" in src
        blocco = src[src.index("const servito"):src.index("export default")]
        assert "prova()" in blocco and "PLATFORM_TOKEN_KEY" in blocco \
            and "'token'" in blocco, \
            "le TRE prove (Lettera, account, operatore) spengono l'invito"

    def test_ogni_montaggio_porta_la_fonte(self):
        scheda = (FRONTEND / "src" / "features" / "frequenze"
                  / "SchedaBibliotecaPage.jsx").read_text()
        assert "sound:esplora:${slug}" in scheda.replace("`", "")
        stanza = (FRONTEND / "src" / "features" / "frequenze"
                  / "lab" / "Stanza.jsx").read_text()
        assert "sound:lab:${slug}" in stanza.replace("`", "")

    def test_l_invito_non_e_un_cancello(self):
        src = (FRONTEND / "src" / "features" / "frequenze"
               / "InvitoSound.jsx").read_text()
        assert "gratuito" in src and "iscriviESblocca" in src
        assert "riservat" not in src, \
            "l'invito offre di piu', non toglie: mai copy da cancello"
