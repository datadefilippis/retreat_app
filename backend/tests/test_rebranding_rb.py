"""Ciclo RB — il rebranding delle due porte (10/9/2026).

Piano: docs/REBRANDING_STRATEGIA_2026-09.md. Diagnosi:
docs/COMUNICAZIONE_ANALISI_2026-09.md. La landing a due porte di
luglio, con zero contenuti, convertiva piu' del sito intero: dal 4/8
zero contatti «cerco un ritiro» (la porta non esisteva piu'),
operatori che si registrano ma non pubblicano. Il sito torna a fare
tre cose nel primo schermo: nominare l'oggetto del desiderio (il
ritiro), chiedere «chi sei?» (due porte) e dare una ragione per farlo
oggi (fondatori con tetto e data, selezione datata).

Queste guardie tengono le decisioni che si perdono per prime: le due
porte nell'ordine (prima chi cerca, poi chi opera), gli indirizzi
canonici, il lessico («operatore olistico» quando si parla
ALL'operatore), la shell SEO che dice quello che dice la pagina, e
l'anti-urgenza («con calma», «lentamente», «candidatura») fuori dal
funnel dell'operatore.
"""
import json
import re
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
FE = REPO / "frontend" / "src"
HOME = FE / "features" / "network" / "NetworkHomePage.js"
LOCALE = FE / "locales" / "it" / "landings.json"
SHELL = BACKEND_DIR / "routers" / "seo_shell.py"

# le parole che dicevano «prendetevela comoda» nel funnel dell'operatore
ANTI_URGENZA = ("con calma", "lentamente", "candidatura", "se c'è sintonia",
                "se c’è sintonia", "non fa per te")


class TestRb1LeDuePorteInHome:

    def test_le_due_porte_stanno_nel_primo_schermo_nell_ordine(self):
        src = HOME.read_text()
        hero = src[src.index('data-testid="hp-hero"'):src.index('data-testid="hp-pillars"')]
        assert 'data-testid="hp-doors"' in hero
        i_seek = hero.index('data-testid="hp-door-seek"')
        i_op = hero.index('data-testid="hp-door-op"')
        assert i_seek < i_op, "prima chi cerca, poi chi opera"
        # ogni porta: una domanda, l'oggetto, UN bottone pieno
        seek = hero[i_seek:i_op]
        op = hero[i_op:hero.index("nwHome.heroOr")]
        for porta, chiave, path in ((seek, "doorSeek", "CERCA_PATH"), (op, "doorOp", "OPERATORI_PATH")):
            assert f"nwHome.{chiave}Title" in porta and f"nwHome.{chiave}Text" in porta and f"nwHome.{chiave}Cta" in porta
            assert porta.count("<EditorialCta") == 1 and 'variant="solid"' in porta
            assert path in porta
        assert "const CERCA_PATH = '/cerca-ritiro'" in src
        assert "const OPERATORI_PATH = '/per-operatori'" in src

    def test_il_copy_delle_porte_nomina_l_oggetto_e_l_offerta(self):
        it = json.loads(LOCALE.read_text())["nwHome"]
        assert "ritiro" in it["doorSeekTitle"].lower(), "la porta di chi cerca nomina l'oggetto"
        assert it["doorSeekCta"] == "Trovami il mio ritiro"
        assert "meditazioni" in it["doorSeekText"], "la ricompensa immediata e' detta"
        assert it["doorOpTitle"] == "Sei un operatore olistico?", "lessico: all'operatore si dice operatore olistico"
        for parola in ("prenotazioni", "ritiri", "caparra", "Gratis fino al 31 dicembre 2026"):
            assert parola in it["doorOpText"], f"l'offerta in chiaro nomina: {parola}"
        assert it["doorOpCta"] == "Apri il tuo spazio"

    def test_l_hero_non_descrive_piu_un_processo(self):
        src = HOME.read_text()
        hero = src[src.index('data-testid="hp-hero"'):src.index('data-testid="hp-pillars"')]
        for vecchio in ("nwHome.heroP2", "nwHome.heroP3", "orientarsi", "consapevolezza"):
            assert vecchio not in hero, f"tornato il processo nell'hero: {vecchio}"
        # la constatazione del founder resta
        assert "nwHome.heroP1" in hero

    def test_la_sezione_operatori_dice_offerta_e_patto(self):
        src = HOME.read_text()
        pros = src[src.index('data-testid="hp-pros"'):src.index('data-testid="hp-letter"')]
        assert "nwHome.prosOffer" in pros and "nwHome.prosFounders" in pros
        assert "nwHome.prosP5" not in pros, "«ci piacerebbe conoscerti» non e' una ragione per iscriversi oggi"
        assert "OPERATORI_PATH" in pros and "JOIN_PATH" not in pros
        it = json.loads(LOCALE.read_text())["nwHome"]
        assert "operatori olistici" in it["prosFounders"] and "entro il" in it["prosFounders"]
        assert re.search(r"primi \w+ operatori", it["prosFounders"]), "il patto ha un tetto"

    def test_la_shell_seo_dice_quello_che_dice_la_pagina(self):
        shell = SHELL.read_text()
        for k in ("doorSeekTitle", "doorOpTitle", "doorSeekCta", "doorOpCta", "prosOffer", "prosFounders"):
            assert f'"{k}"' in shell, f"la shell non ha {k}"
        html = shell[shell.index("async def _home_content_html"):shell.index("async def _home_content_html") + 3000]
        assert 'href=\\"/cerca-ritiro\\"' in html and 'href=\\"/per-operatori\\"' in html
        assert "c['heroP2']" not in html and "c['heroP3']" not in html
        # la copia del backend segue il locale (copia_locales.py --scrivi)
        copia = json.loads((BACKEND_DIR / "assets" / "copia_it" / "landings.json").read_text())["nwHome"]
        locale = json.loads(LOCALE.read_text())["nwHome"]
        for k in ("doorSeekTitle", "doorOpTitle", "prosFounders"):
            assert copia[k] == locale[k], f"copia_it non allineata su {k}: lancia copia_locales.py --scrivi"

    def test_niente_anti_urgenza_nel_funnel_dell_operatore_in_home(self):
        it = json.loads(LOCALE.read_text())["nwHome"]
        testo = " ".join(str(v) for v in it.values()).lower()
        for frase in ANTI_URGENZA:
            assert frase not in testo, f"la home dice all'operatore di prendersela comoda: «{frase}»"


LANDING = FE / "features" / "prelaunch" / "OperatorLandingPage.js"
PRELAUNCH = FE / "locales" / "it" / "prelaunch.json"
BASE = __import__("os").environ.get("REACT_APP_BACKEND_URL", "http://localhost:8000")


class TestRb2LaLandingDellOperatore:
    """/entra-nella-rete segue il trittico: cosa hai, perche' ora, come si
    entra. Concreto, con la data e il contatore vero. Niente candidatura,
    niente «con calma», niente «non fa per te»."""

    def test_il_trittico_nell_ordine(self):
        src = LANDING.read_text()
        pos = -1
        for tid in ("ol-hero", "ol-go", "ol-now", "ol-join", "ol-faq", "ol-who", "ol-form", "ol-end"):
            here = src.index(f'data-testid="{tid}"')
            assert here > pos, f"{tid}: fuori ordine"
            pos = here
        assert 'data-testid="ol-for"' not in src

    def test_il_copy_parla_all_operatore_olistico(self):
        op = json.loads(PRELAUNCH.read_text())["opPro"]
        assert "operatori olistici" in op["seoTitle"] and "operatrici olistiche" in op["heroEyebrow"]
        assert op["heroTitle"] == "Il tuo spazio professionale, pronto oggi."
        for parola in ("prenotazione", "ritiri", "caparra", "Instagram"):
            assert parola in op["heroP1"], f"l'offerta in chiaro nomina: {parola}"
        assert "31 dicembre 2026" in op["heroP3"], "il prezzo ha una data"
        assert "31 ottobre 2026" in op["nowP1"] and "venti" in op["nowP1"], "il patto fondatori ha tetto e data"
        assert op["ctaOpen"] == "Apri il tuo spazio"
        testo = " ".join(str(v) for v in op.values()).lower()
        for frase in ANTI_URGENZA:
            assert frase not in testo, f"la landing dice all'operatore di prendersela comoda: «{frase}»"
        assert "professionisti del benessere" not in op["heroEyebrow"].lower()

    def test_l_intervista_e_un_premio_dopo_non_un_cancello_prima(self):
        # si giudica il copy che il lettore vede, non le note di lavoro
        src = re.sub(r"/\*.*?\*/", "", LANDING.read_text(), flags=re.DOTALL)
        src = re.sub(r"^\s*//.*$", "", src, flags=re.MULTILINE)
        for vecchio in ("Compila il modulo", "candidatura", "Non è una selezione", "non fa per te", "Stiamo iniziando con calma"):
            assert vecchio not in src, f"tornato il cancello: {vecchio}"
        op = json.loads(PRELAUNCH.read_text())["opPro"]
        assert "Valentina ti scrive" in op["j3t"] and "Verificato Aurya" in op["j3b"]
        assert "Nessuna carta" in op["j1b"]

    def test_il_contatore_dei_fondatori_e_vero(self):
        src = LANDING.read_text()
        assert "api.get('/public/fondatori')" in src and 'data-testid="ol-fondatori-contatore"' in src
        assert "nowCountFallback" in src, "senza rete la frase resta senza numero, mai un numero inventato"
        import requests
        try:
            r = requests.get(f"{BASE}/api/public/fondatori", timeout=10)
        except Exception:
            import pytest
            pytest.skip("backend locale non raggiungibile")
        assert r.status_code == 200
        j = r.json()
        assert j["tetto"] == 20 and j["scadenza"] == "2026-10-31"
        assert 0 <= j["rimasti"] <= 20 and j["presi"] + j["rimasti"] == 20

    def test_la_shell_e_il_corpo_dicono_la_stessa_landing(self):
        shell = SHELL.read_text()
        assert "Per operatori olistici: il tuo spazio professionale, pronto oggi | Aurya" in shell
        assert "il racconto del tuo lavoro lo scriviamo insieme" in shell
        from services.identita import corpo_professionisti, faq_professionisti
        corpo = corpo_professionisti()
        for frase in ("Il tuo spazio professionale, pronto oggi.", "Cosa hai da subito.", "Perché ora.", "Come si entra."):
            assert frase in corpo
        assert "non fa per te" not in corpo and "con calma" not in corpo
        assert len(faq_professionisti()) == 6


class TestRb4LaPortaDiChiCerca:
    """/cerca-ritiro torna viva: si chiama con l'oggetto («Trovami il mio
    ritiro»), il modulo di luglio iscrive al Cerchio con i ritiri accesi,
    e cosa succede dopo e' detto prima (subito, quando vale la pena, il
    15 gennaio 2027). Mai una cadenza dichiarata (regola del founder)."""

    TR = FE / "features" / "prelaunch" / "TravelerLandingPage.js"

    def test_la_rotta_e_viva_e_la_porta_di_casa_la_usa(self):
        app = (FE / "App.js").read_text()
        assert 'path="/cerca-ritiro" element={<TravelerLandingPage />}' in app
        assert 'path="/cerca-ritiro" element={<Navigate' not in app
        assert "const CERCA_PATH = '/cerca-ritiro'" in HOME.read_text()

    def test_il_modulo_di_luglio_iscrive_al_cerchio_coi_ritiri_accesi(self):
        src = self.TR.read_text()
        assert src.count("<SchedaForm") == 2 and src.count("<LeadForm") == 1, \
            "UN modulo (la scheda), montato nel primo schermo e in fondo"
        blocco = src[src.index("<LeadForm"):src.index("/>", src.index("<LeadForm"))]
        for prop in ("subscribe", "showName", "wantsExperiencesAlways", "context={context === 'hero' ? 'cerca-ritiro'"):
            assert prop in blocco, f"manca {prop}"
        assert "compact" not in blocco, "il modulo e' quello pieno: citta', interessi, raggio, budget"
        form = (FE / "features" / "prelaunch" / "LeadForm.jsx").read_text()
        assert "wantsExperiencesAlways = false" in form and "BASE_TO_EXP" in form
        assert "wants_experiences: experiencesOptIn ? wantsExperiences : (wantsExperiencesAlways || null)" in form

    def test_il_copy_nomina_l_oggetto_i_tre_tempi_e_nessuna_cadenza(self):
        tr = json.loads(PRELAUNCH.read_text())["tr"]
        assert tr["cta"] == "Trovami il mio ritiro" and "ritiro" in tr["title"].lower()
        assert tr["d1w"] == "Subito" and "meditazioni" in tr["d1t"].lower()
        assert "15 gennaio 2027" in tr["d3w"] and "primavera 2027" in tr["d3t"]
        testo = " ".join(str(v) for v in tr.values()).lower()
        for cadenza in ("ogni due settimane", "ogni settimana", "ogni mese", "al lancio"):
            assert cadenza not in testo, f"cadenza o promessa vecchia: «{cadenza}»"
        assert "operatore olistico" in tr["switch2"]

    def test_la_shell_e_il_corpo_dicono_la_porta(self):
        shell = SHELL.read_text()
        assert "Trovami il mio ritiro | Ritiri ed esperienze olistiche vicino a te | Aurya" in shell
        assert '"cerca-ritiro": "WebPage"' in shell
        from services.identita import CORPI, corpo_cerca_ritiro
        assert "cerca-ritiro" in CORPI
        corpo = corpo_cerca_ritiro()
        for frase in ("C’è un ritiro che ti sta aspettando.", "Cosa succede dopo, detto prima.", "15 gennaio 2027", "Persone, non annunci."):
            assert frase in corpo, frase
        assert "al lancio" not in corpo.lower()
