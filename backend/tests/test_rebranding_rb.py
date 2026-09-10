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
        # decisione founder 10/9: la canonica dell'operatore resta /entra-nella-rete
        assert "const OPERATORI_PATH = '/entra-nella-rete'" in src

    def test_il_copy_delle_porte_nomina_l_oggetto_e_l_offerta(self):
        it = json.loads(LOCALE.read_text())["nwHome"]
        assert "ritiro" in it["doorSeekTitle"].lower(), "la porta di chi cerca nomina l'oggetto"
        # founder 10/9 sera: i testi del primo schermo sono i suoi, parola per parola
        assert it["doorSeekCta"] == "Trova il mio ritiro"
        assert "<b>cosa cerchi e dove</b>" in it["doorSeekText"] and "esperienza giusta" in it["doorSeekText"]
        assert it["doorOpTitle"] == "Sei un operatore olistico?", "lessico: all'operatore si dice operatore olistico"
        for parola in ("profilo", "servizi", "prenotazioni", "eventi e ritiri", "<b>Gratis per sempre, senza commissioni.</b>"):
            assert parola in it["doorOpText"], f"l'offerta in chiaro nomina: {parola}"
        assert it["doorOpCta"] == "Crea il tuo spazio"
        assert it["heroP1"] == "Trova il professionista, il percorso o il ritiro giusto per te."
        assert it["heroCta"] == "Scopri gli operatori"

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
        # CP (10/9 notte): l'offerta la dice la porta dell'hero; qui
        # resta solo il patto, e UNA porta (via «Come funziona»)
        assert "nwHome.prosOffer" not in pros and "nwHome.prosFounders" in pros
        assert "hp-pros-how" not in pros
        assert "nwHome.prosP5" not in pros, "«ci piacerebbe conoscerti» non e' una ragione per iscriversi oggi"
        assert "OPERATORI_PATH" in pros and "JOIN_PATH" not in pros
        it = json.loads(LOCALE.read_text())["nwHome"]
        assert "operatori olistici" in it["prosFounders"] and "entro il" in it["prosFounders"]
        assert re.search(r"primi \w+ operatori", it["prosFounders"]), "il patto ha un tetto"

    def test_la_shell_seo_dice_quello_che_dice_la_pagina(self):
        shell = SHELL.read_text()
        for k in ("doorSeekTitle", "doorOpTitle", "doorSeekCta", "doorOpCta", "prosFounders"):
            assert f'"{k}"' in shell, f"la shell non ha {k}"
        assert '"prosOffer"' not in shell and '"pillarExpTitle"' not in shell, "la shell ripete blocchi usciti (CP)"
        html = shell[shell.index("async def _home_content_html"):shell.index("async def _home_content_html") + 3000]
        assert 'href=\\"/cerca-ritiro\\"' in html and 'href=\\"/entra-nella-rete\\"' in html
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
        # CP (10/9 notte): via ol-rete, ol-who, ol-end; il filo a /chi-siamo
        # resta in una riga dentro il modulo (ol-who-cta)
        for tid in ("ol-hero", "ol-go", "ol-studio", "ol-now", "ol-prezzi", "ol-join", "ol-faq", "ol-form", "ol-who-cta"):
            here = src.index(f'data-testid="{tid}"')
            assert here > pos, f"{tid}: fuori ordine"
            pos = here
        assert 'data-testid="ol-for"' not in src

    def test_il_copy_parla_all_operatore_olistico(self):
        op = json.loads(PRELAUNCH.read_text())["opPro"]
        assert "operatori olistici" in op["seoTitle"] and "operatrici olistiche" in op["heroEyebrow"]
        assert op["heroTitle"] == "Il tuo spazio professionale, pronto oggi."
        # RB2-bis (10/9 sera): l'offerta in una frase, la frase-marchio senza data
        for parola in ("prenotazioni", "ritiri", "un solo link"):
            assert parola in op["heroP1"] + " " + op["heroP2"], f"l'offerta in chiaro nomina: {parola}"
        assert op["heroP3"] == "Gratis per sempre, senza commissioni."
        assert "31 ottobre 2026" in op["nowP1"] and ("venti" in op["nowP1"] or "20 operatori" in op["nowP1"]), "il patto fondatori ha tetto e data"
        assert "30 giugno 2027" in op["nowB1b"] and "post al mese" not in json.dumps(op), "il Club fondatori ha una fine e niente post mensile"
        for k in ("v1k", "v6k", "nowB4t", "nowCta"):
            assert op.get(k), k
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
        # founder 10/9 sera: niente attesa di una chiamata, il gruppo Telegram
        assert "Telegram" in op["j3b"] and "Verificato Aurya" in op["j3b"]
        assert "Valentina ti scrive" not in json.dumps(op), "il processo non aspetta nessuno"
        assert "gratuito per sempre" in op["prezziP1"] and "19 €" in op["prezzi1t"]
        assert "Non serve la carta" in op["j1b"] or "Nessuna carta" in op["j1b"]

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
        assert "Gratis per sempre, senza commissioni." in shell   # RB2-bis: la frase-marchio, senza data
        from services.identita import corpo_professionisti, faq_professionisti
        corpo = corpo_professionisti()
        for frase in ("Il tuo spazio professionale, pronto oggi.", "Tutto quello che ti serve, in un unico posto.",
                      "scoperto anche su Aurya", "Perché entrare ora.", "Quanto costa.", "Come si comincia."):
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
        # CP (10/9/2026 notte, founder: «tagliamo ma mantenendo fili
        # logici»): il modulo e' montato UNA volta, nel primo schermo;
        # la chiusura e' un bottone che ci riporta (tr-end-cta)
        assert src.count("<SchedaForm") == 1 and src.count("<LeadForm") == 1, \
            "UN modulo (la scheda), montato solo nel primo schermo"
        assert 'data-testid="tr-end-cta"' in src and 'href="#racconta"' in src
        blocco = src[src.index("<LeadForm"):src.index("/>", src.index("<LeadForm"))]
        for prop in ("subscribe", "showName", "wantsExperiencesAlways", 'context="cerca-ritiro"'):
            assert prop in blocco, f"manca {prop}"
        assert "compact" not in blocco, "il modulo e' quello pieno: citta', interessi, raggio, budget"
        form = (FE / "features" / "prelaunch" / "LeadForm.jsx").read_text()
        assert "wantsExperiencesAlways = false" in form and "BASE_TO_EXP" in form
        assert "wants_experiences: experiencesOptIn ? wantsExperiences : (wantsExperiencesAlways || null)" in form

    def test_il_copy_nomina_l_oggetto_i_tre_tempi_e_nessuna_cadenza(self):
        tr = json.loads(PRELAUNCH.read_text())["tr"]
        assert tr["cta"] == "Trovami il mio ritiro" and "ritiro" in tr["title"].lower()
        assert tr["d1w"] == "Subito" and "meditazioni" in tr["d1t"].lower()
        # founder 10/9 sera: niente data («non voglio vincolarmi»); il terzo
        # tempo e' il vantaggio: ritiri ed esperienze sui suoi interessi
        assert "15 gennaio" not in json.dumps(tr), "la landing non promette piu' una data"
        assert "interessi" in tr["d3b"] and "preferenze" in tr["d3b"]
        assert tr["d2t"] == "La Lettera di Aurya"
        testo = " ".join(str(v) for v in tr.values()).lower()
        for cadenza in ("ogni due settimane", "ogni settimana", "ogni mese", "al lancio"):
            assert cadenza not in testo, f"cadenza o promessa vecchia: «{cadenza}»"
        assert "operatore olistico" in tr["switch2"]

    def test_la_shell_e_il_corpo_dicono_la_porta(self):
        shell = SHELL.read_text()
        assert "Trovami il mio ritiro | Ritiri olistici vicino a te | Aurya" in shell   # SEO-R: titolo entro ~60
        assert '"cerca-ritiro": "WebPage"' in shell
        from services.identita import CORPI, corpo_cerca_ritiro
        assert "cerca-ritiro" in CORPI
        corpo = corpo_cerca_ritiro()
        # founder 10/9 sera: niente data nel corpo, il vantaggio al suo posto
        for frase in ("C’è un ritiro che ti sta aspettando.", "Cosa succede dopo, detto prima.", "pensati per te", "Persone, non annunci."):
            assert frase in corpo, frase
        assert "al lancio" not in corpo.lower()


class TestRb6Rb7HeaderEPotature:
    """RB6: l'header dice all'operatore lo stesso gesto delle porte.
    RB7: Manifesto e Chi siamo senza «lentamente / tutto subito»,
    Meditazioni col lessico di chi cerca, /come-funziona un 301 vero."""

    def test_l_header_dice_apri_il_tuo_spazio(self):
        shell = (FE / "features" / "storefront" / "components" / "MarketplaceShell.jsx").read_text()
        assert "defaultValue: 'Apri il tuo spazio'" in shell
        it = json.loads(LOCALE.read_text())
        assert it["marketplace"]["forProfessionals"] == "Apri il tuo spazio"
        # founder 10/9 sera: la porta in home dice «Crea il tuo spazio» (testo
        # suo); l'header resta «Apri il tuo spazio» finche' non decide anche li'
        assert it["nwHome"]["doorOpCta"] == "Crea il tuo spazio"

    def test_manifesto_e_chi_siamo_senza_anti_urgenza(self):
        it = json.loads(LOCALE.read_text())
        testo = " ".join(str(v) for k in ("manifesto", "aboutPage") for v in it[k].values()).lower()
        for frase in ("lentamente", "tutto subito", "infine gli strumenti"):
            assert frase not in testo, f"tornata l'anti-urgenza: «{frase}»"
        assert it["aboutPage"]["step3"] == "Oggi ci sono gli strumenti.", "i quattro tempi sono al passato/presente"

    def test_meditazioni_parlano_di_professionisti(self):
        med = (FE / "features" / "frequenze" / "MeditazioniPage.js").read_text()
        assert "operatori della rete" not in med and "operatori di Aurya" not in med
        from services.identita import corpo_meditazioni
        assert "professionisti della rete" in corpo_meditazioni()

    def test_come_funziona_e_un_rimando_vero(self):
        reg = json.loads((BACKEND_DIR / "config" / "rotte.json").read_text())
        # come /ritiri: resta classificata (il gate SPA esiste) ma nginx fa 301
        assert "come-funziona" in reg["pubblica"] and reg["rimandi"]["come-funziona"] == "/manifesto"
        nginx = (REPO / "deploy" / "nginx" / "nginx.conf").read_text()
        assert "return 301 /manifesto" in nginx


class TestP1LeParoleSuiSoldi:
    """P1 (10/9/2026, piano di business): «Aurya non prende commissioni.
    Mai.» ovunque si parla di soldi; i piani del 2027 scritti da oggi in
    /costi (Spinta 19, Club 49, Pro 119) coi tre cancelli e la garanzia;
    la fee del Gratis a zero nel seed e sulle org (migrazione flag-gated);
    il banner «col Pro avresti risparmiato» spento a fee zero."""

    COSTI = FE / "features" / "prelaunch" / "PricingPage.js"

    def test_costi_dice_zero_commissioni_e_i_piani_del_2027(self):
        src = re.sub(r"/\*.*?\*/", "", self.COSTI.read_text(), flags=re.DOTALL)
        for frase in ("Aurya non prende commissioni. Mai.", "Gratis per sempre, senza commissioni",
                      "I prezzi dal 1° gennaio 2027", 'testid="plan-spinta"', 'testid="plan-club"',
                      "Il Club si accende quando la fila c’è.", "300 iscritti confermati", "10 ritiri", "1.000 visite",
                      "I fondatori.", "Club regalato fino al 30 giugno 2027", "La garanzia.", "E Stripe?"):
            assert frase in src, frase
        assert "5%" not in src and "sugli incassi online" not in src.split("E Stripe?")[0].replace("senza commissioni", "")

    def test_la_fee_e_zero_nel_seed_e_la_migrazione_esiste(self):
        from services.seed_commercial_plans import RETREAT_COMMERCIAL_PLANS
        for p in RETREAT_COMMERCIAL_PLANS:
            assert float(p.get("transaction_fee_percent") or 0.0) == 0.0, f"{p['slug']}: fee {p.get('transaction_fee_percent')}"
        seed = (BACKEND_DIR / "services" / "seed_pricing.py").read_text()
        assert "async def migrate_zero_commissioni_v1" in seed and '"_id": "zero_commissioni_v1"' in seed
        assert "migrate_zero_commissioni_v1()" in (BACKEND_DIR / "server.py").read_text()
        cash = (BACKEND_DIR / "routers" / "cashflow.py").read_text()
        assert "fee_saver = None if current_fee <= 0 else {" in cash

    def test_la_frase_marchio_e_nelle_porte_e_nella_landing(self):
        it = json.loads(LOCALE.read_text())["nwHome"]
        assert "senza commissioni" in it["doorOpText"]   # CP: prosOffer e' uscito dalla home
        op = json.loads(PRELAUNCH.read_text())["opPro"]
        assert "non prende commissioni" in op["faq1b1"] and "Club Fondatori regalato fino al 30 giugno 2027" in op["nowP2"]
        assert "19 €" in op["faq1b2"] and "49 €" in op["faq1b2"] and "119 €" in op["faq1b2"]   # RB2-bis: i prezzi nel secondo punto
        sett = json.loads((FE / "locales" / "it" / "settings.json").read_text())["billing"]["retreat"]
        assert "non prende commissioni" in sett["subtitle"]
        llms = (BACKEND_DIR / "assets" / "llms.txt").read_text()
        assert "senza commissioni" in llms and "commissione solo sulle prenotazioni" not in llms

    def test_nessuna_data_di_scadenza_del_gratis_nelle_porte(self):
        """«Gratis fino al 31 dicembre 2026» diceva che poi si paga: il
        Gratis e' per sempre. La data resta solo per «nessun costo di
        nessun tipo» (Spinta/Club/Pro dal 2027)."""
        it = json.loads(LOCALE.read_text())["nwHome"]
        assert "fino al 31 dicembre" not in it["doorOpText"].lower()


class TestP3MarketplaceApertoAPrimaFila:
    """P3 (10/9/2026, piano di business §3, decisione founder): «un
    marketplace vuoto non vende». Il marketplace e' GRATIS per tutti i
    ritiri pubblicati, con o senza Stripe; si paga la PROMOZIONE (la
    prima fila), non la presenza. /esperienze torna come pagina semplice
    con la fascia «In prima fila» e lo stato vuoto che porta alle porte."""

    def test_il_listing_elenca_anche_i_ritiri_su_richiesta(self):
        src = (BACKEND_DIR / "routers" / "public.py").read_text()
        i = src.index("async def list_public_retreats(")
        corpo = src[i:i + 12000]
        assert '"transaction_mode": {"$in": ["direct", "request"]}' in corpo
        assert '"transaction_mode": "direct",' not in corpo, "GT1b non filtra piu' i ritiri su richiesta"
        assert '"booking": prod.get("transaction_mode") or "direct",' in corpo
        assert '"prima_fila": bool(prod.get("prima_fila")),' in corpo
        # la prima fila sta in cima, PRIMA del conteggio e della pagina
        assert corpo.index('items.sort(key=lambda i: not i.get("prima_fila"))') < corpo.index("total = len(items)")

    def test_la_pagina_esperienze_e_il_calendario_con_le_parti_di_p3(self):
        """RE (10/9/2026 sera, founder: «riaccendiamo e implementiamo»):
        una pagina sola. Il calendario di luglio (ricerca, categorie,
        filtri, percorsi SEO) E' /esperienze, con le tre cose buone della
        pagina di P3: la fascia in prima fila, lo stato vuoto con le
        parole del founder e le due porte, la copertina. EsperienzePage
        e' stata ritirata."""
        assert not (FE / "features" / "storefront" / "EsperienzePage.js").exists()
        page = (FE / "features" / "storefront" / "RetreatsCalendarPage.js").read_text()
        assert "api.get('/public/retreats'" in page
        for tid in ("esp-fascia-prima-fila", "esp-vuoto", "esp-cta-cerca", "esp-cta-op", "esp-prima-fila", "esp-title"):
            assert f'data-testid="{tid}"' in page, tid
        assert "su richiesta" in page and "prenotazione online" in page
        assert 'to="/cerca-ritiro?porta=esperienze"' in page and 'to="/entra-nella-rete?porta=esperienze"' in page
        assert "senza commissioni" in page and "I primi ritiri stanno arrivando." in page
        # RE-bis (10/9 sera, founder): lo stile della directory dei professionisti
        # — foto ferma con velatura, barra filtri sticky, schede 16/9
        assert "HeroVideo" not in page and "aurya-hero-poster.jpg" not in page, "copertina diversa dalla home (founder)"
        assert "/media/hero-blog.webp" in page
        assert 'data-testid="esp-search-bar"' in page and "GeoSearchBar" in page and 'fluid' in page
        assert 'data-testid="esp-f-categoria"' in page and 'data-testid="esp-f-mese"' in page
        assert "const basePath = '/esperienze';" in page
        # RE-ter: nel filtro solo le categorie con ritiri, col conteggio
        pub = (BACKEND_DIR / "routers" / "public.py").read_text()
        corpo = pub[pub.index("async def list_public_retreats("):pub.index("def _haversine_km(")]
        assert '"categories": RETREAT_CATEGORIES' not in corpo and "await _categorie_con_ritiri()" in corpo
        assert "async def _categorie_con_ritiri()" in pub
        assert "info?.count ? ` (${info.count})` : ''" in page
        assert "MarketplaceValueSections" not in page, "niente sezioni ridondanti sotto l'elenco (founder)"

    def test_il_gate_e_i_rimandi(self):
        app = (FE / "App.js").read_text()
        i = app.index("function EsperienzeGate()")
        gate = app[i:i + 200]
        assert "<RetreatsCalendarPage />" in gate and "sitePhase" not in gate, "in ogni fase"
        assert 'path="/esperienze/:categoria"' in app and 'path="/esperienze/:categoria/:regione"' in app
        assert "function EsploraRitiriRedirect()" in app and "function RitiriCategoryGate()" in app
        assert 'to="/esperienze"' in app[app.index("function RitiriGate()"):][:300]

    def test_l_hint_in_admin_non_dice_piu_che_su_richiesta_resta_fuori(self):
        hint = (FE / "components" / "DirectoryListingHint.jsx").read_text()
        it = json.loads((FE / "locales" / "it" / "common.json").read_text())["directoryHint"]
        for testo in (hint, it["request"], it["stripeNote"]):
            assert "NON comparir" not in testo and "non comparir" not in testo
            assert "Ritiri ed esperienze" in testo
        assert "bonifico" in it["request"]
        prod = json.loads((FE / "locales" / "it" / "products.json").read_text())
        ragioni = prod["grids"]["event"]["directory"]["reason"]
        assert "Ritiri ed esperienze" in ragioni["mode_request"]
        assert "su richiesta" in ragioni["stripe_not_ready"]


class TestP2IlBonificoElaStradaPrincipale:
    """P2 (10/9/2026, piano di business, decisione founder): i primi
    operatori trovano Stripe complesso e preferiscono il bonifico. Il
    bonifico e' la strada principale della caparra, Stripe resta
    facoltativo e silenzioso. Tre campi sull'organizzazione, le
    istruzioni nella stessa email della richiesta, «caparra ricevuta»
    gia' esistente (settle-manual). L'IBAN non esce MAI da /public."""

    def test_i_tre_campi_esistono_e_l_iban_si_valida(self):
        sys.path.insert(0, str(BACKEND_DIR))
        from routers.organizations import OrganizationUpdate
        dto = OrganizationUpdate(bank_iban="it60 x054 2811 1010 0000 0123 456",
                                 bank_holder=" Giulia Serra ", deposit_days=7)
        assert dto.bank_iban == "IT60X0542811101000000123456"
        assert dto.bank_holder == "Giulia Serra" and dto.deposit_days == 7
        assert OrganizationUpdate(bank_iban="  ").bank_iban == ""   # svuota
        import pytest
        with pytest.raises(ValueError):
            OrganizationUpdate(bank_iban="1234")
        with pytest.raises(ValueError):
            OrganizationUpdate(deposit_days=0)
        model = (BACKEND_DIR / "models" / "organization.py").read_text()
        for campo in ("bank_iban", "bank_holder", "deposit_days"):
            assert f"    {campo}: Optional" in model, campo

    def test_le_istruzioni_partono_con_l_email_della_richiesta(self):
        src = (BACKEND_DIR / "services" / "order_email_service.py").read_text()
        assert "async def _bank_transfer_block(" in src and "async def _saldo_block(" in src
        assert "compute_deposit_minor" in src, "la caparra segue il piano del ritiro come con Stripe"
        assert 'it.get("item_type") == "event_ticket"' in src, "la caparra via email solo per i ritiri, non per un massaggio"
        assert 'f"{parola} {d[\'causale_base\']}"' in src, "causale leggibile: ritiro e cognome, non un codice"
        assert "{saldo_html}" in src and '"manual_deposit_received": True' in (BACKEND_DIR / "services" / "order_service.py").read_text()
        i = src.index("async def notify_customer_order_received(")
        corpo = src[i:i + 3000]
        assert "_bank_transfer_block(order, org_id, order_ref, locale)" in corpo
        assert "{bank_block}" in corpo
        em = (BACKEND_DIR / "services" / "email_service.py").read_text()
        for k in ("order_bank_title", "order_bank_body", "order_bank_iban",
                  "order_bank_reason", "order_bank_note"):
            assert em.count(f'"{k}"') >= 2, f"{k}: it + en"

    def test_l_iban_non_esce_dalle_risposte_pubbliche(self):
        for rel in ("routers/seo_shell.py", "routers/fondatori.py"):
            assert "bank_iban" not in (BACKEND_DIR / rel).read_text(), rel
        # public.py legge l'IBAN solo per dire «c'e' il bonifico» (bool): mai nel payload
        pub = (BACKEND_DIR / "routers" / "public.py").read_text()
        assert '"bank_iban": 1' not in pub and 'bank_iban=' not in pub
        assert pub.count("bank_iban") == pub.count('org.get("bank_iban")')

    def test_la_scheda_nelle_impostazioni_dopo_stripe(self):
        page = (FE / "features" / "settings" / "SettingsPage.js").read_text()
        assert page.index("<PaymentConnectionsCard") < page.index("<BonificoCard />")
        card = (FE / "features" / "settings" / "sections" / "BonificoCard.jsx").read_text()
        for tid in ("bonifico-card", "bonifico-iban", "bonifico-intestatario",
                    "bonifico-giorni", "bonifico-salva", "bonifico-stato"):
            assert f'data-testid="{tid}"' in card, tid
        assert "organizationsAPI.updateCurrent(" in card
        assert "caparra ricevuta" in card and "senza commissioni" in card

    def test_un_ritiro_nuovo_nasce_su_richiesta(self):
        wiz = (FE / "features" / "events" / "EventWizard.js").read_text()
        assert "transaction_mode: p.transaction_mode || (prefillRef.current?.product ? 'direct' : 'request')" in wiz


class TestP13AuryaPerLeAziendeEChiediLaRegia:
    """P13 (10/9/2026, piano di business §3.1 A e B): i servizi fanno i
    primi soldi veri. «Aurya per le aziende» e' una landing con un
    modulo (team building alla Masseria, due formati con prezzo «da»);
    «Chiedi la regia» allarga la scheda «Cerco una struttura» del
    gestionale. Le richieste finiscono tutte nel pannello, con un tipo."""

    def test_la_rotta_e_registrata_con_meta_e_in_sitemap(self):
        reg = json.loads((BACKEND_DIR / "config" / "rotte.json").read_text())
        assert "aziende" in reg["pubblica"]
        shell = (BACKEND_DIR / "routers" / "seo_shell.py").read_text()
        assert '"aziende": {' in shell and '"aziende": "WebPage"' in shell
        assert 'f"{base}/aziende"' in (BACKEND_DIR / "routers" / "seo.py").read_text()
        ident = (BACKEND_DIR / "services" / "identita.py").read_text()
        assert '"aziende": corpo_aziende' in ident and "def sezione_aziende_llms" in ident
        assert "sezione_aziende_llms(base)" in (BACKEND_DIR / "server.py").read_text()
        nginx = (REPO / "deploy" / "nginx" / "nginx.conf").read_text()
        assert "|aziende|" in nginx, "rigenera nginx: scripts/genera_rotte_nginx.py --scrivi"

    def test_la_pagina_e_su_misura_senza_prezzi_ne_formati(self):
        """Founder (10/9 sera): «non voglio sponsorizzare solo la Masseria,
        niente formati gia' fatti: non li abbiamo e vanno studiati». Il
        servizio e' on demand, il prezzo pattuito su cio' che l'azienda vuole."""
        app = (FE / "App.js").read_text()
        assert 'path="/aziende" element={<AziendePage />}' in app
        page = (FE / "features" / "network" / "AziendePage.js").read_text()
        testo = re.sub(r"/\*.*?\*/", "", page, flags=re.S)
        for tid in ("az-cosa", "az-chi-rete", "az-come", "az-form", "az-messaggio",
                    "az-invia", "az-fatto", "az-faq"):
            assert f'data-testid="{tid}"' in testo, tid
        assert "su misura" in testo and "pattuito" in testo
        assert "rete" in testo and "strutture" in testo, "la rete di operatori E di strutture"
        assert "€" not in testo and "prezzo «da»" not in testo, "nessun prezzo: non abbiamo formati"
        assert "Masseria" not in testo and "sala a volta" not in testo, "non solo la Masseria"
        assert "formato" not in testo.lower(), "niente formati pre-fatti"
        assert "/public/aziende/richiesta" in testo and "BRAND_EMAIL" in testo
        for frase in ANTI_URGENZA + ("ultimi posti", "affrettat", "solo per oggi"):
            assert frase not in testo.lower(), frase
        assert "<img" not in testo, "niente foto finche' non ci sono quelle vere"
        shell_src = (BACKEND_DIR / "routers" / "seo_shell.py").read_text()
        blocco = shell_src[shell_src.index('"aziende": {'):shell_src.index('"cerca-ritiro": {')]   # RE: /esperienze non e' piu' una pagina statica
        assert "€" not in blocco and "Masseria" not in blocco and "su misura" in blocco
        em = (BACKEND_DIR / "services" / "strutture_email.py").read_text()
        assert "Masseria" not in em and "FORMATI" not in em
        assert "formato" not in (BACKEND_DIR / "routers" / "aziende.py").read_text()
        ident = (BACKEND_DIR / "services" / "identita.py").read_text()
        corpo = ident[ident.index("def corpo_aziende"):ident.index("CORPI = {")]
        assert "€" not in corpo and "Masseria" not in corpo and "su misura" in corpo
        shell = (FE / "features" / "storefront" / "components" / "MarketplaceShell.jsx").read_text()
        assert 'data-testid="footer-nw-aziende"' in shell

    def test_il_modulo_pubblico_ha_il_limite_e_il_tipo(self):
        src = (BACKEND_DIR / "routers" / "aziende.py").read_text()
        assert 'prefix="/public/aziende"' in src and '@limiter.limit("5/hour")' in src
        assert 'dati["tipo"] = "team_building"' in src
        assert "honeypot" not in src.lower() and "website" not in src, "niente esca: l'autofill la riempiva (28/8)"
        assert "aziende_router.router" in (BACKEND_DIR / "server.py").read_text()
        rs = (BACKEND_DIR / "routers" / "strutture.py").read_text()
        assert 'tipo: Literal["struttura", "regia"] = "struttura"' in rs
        em = (BACKEND_DIR / "services" / "strutture_email.py").read_text()
        for s in ("Richiesta di regia da", "Richiesta team building da", "Richiesta struttura da",
                  "La tua richiesta di regia è arrivata", "Aurya per le aziende"):
            assert s in em, s

    def test_la_scheda_del_gestionale_chiede_anche_la_regia(self):
        events = (FE / "features" / "events" / "EventsListPage.js").read_text()
        assert 'data-testid="events-chiedi-regia"' in events and 'tipoIniziale="regia"' in events
        assert 'data-testid="events-cerca-struttura"' not in events, "founder 10/9 sera: gratis non si vende, il pulsante esce"
        dialog = (FE / "features" / "events" / "components" / "RichiestaStrutturaDialog.jsx").read_text()
        # founder 10/9 sera: solo la regia dal gestionale, niente linguette
        assert "richiesta-tab-" not in dialog and "tipoIniziale = 'regia'" in dialog
        for tid in ("richiesta-regia-intro", "richiesta-formula"):
            assert f'data-testid="{tid}"' in dialog, tid
        # founder 10/9 sera: la regia e' GIA' disponibile — niente «ti scriviamo quando parte»
        assert "quando il servizio parte" not in dialog and "entro pochi giorni" in dialog
        assert "Regia leggera, 290 €" in dialog and "Regia completa, 690 €" in dialog
        assert "40 € a partecipante oltre il sesto" in dialog
        assert "tipo, formula: tipo === 'regia' ? formula : null" in dialog
        admin = (FE / "features" / "admin" / "strutture" / "StrutturePage.js").read_text()
        assert 'data-testid="strutture-richiesta-tipo"' in admin and "team_building" in admin


class TestFv2LeSequenze:
    """RB8 (10/9/2026) → FV2 (10/9 sera, audit del funnel) → FV5 (stessa
    sera, founder): un motore solo per due pubblici (services/sequenze.py),
    passi come dati, testi in services/email_sequenze.py. Operatore:
    5/10/15 senza pagina, pagina online, primo ritiro; VIA il «come va»
    a 30 giorni. Cerchio: UNA sola email, il benvenuto, che si adatta a
    come e da dove ci si e' iscritti, e parte alla conferma. L'email a
    noi dice Telegram. Le risposte arrivano al Reply-To."""

    def test_i_passi_partono_solo_nella_loro_finestra(self):
        sys.path.insert(0, str(BACKEND_DIR))
        from services.sequenze import passi_dovuti, PASSI, passo_dovuto
        assert [p.nome for p in PASSI["operatore"]] == ["g2", "profilo_online", "np5", "np10", "np15", "r14"], \
            "via g30 (founder 10/9 sera)"
        assert [p.nome for p in PASSI["cerchio"]] == ["benvenuto_ritiri", "benvenuto_meditazioni", "benvenuto_altro"]
        nomi = lambda g, s, m={}: [p.nome for p in passi_dovuti("operatore", g, s, m)]   # noqa: E731
        spento = {"online": False, "ritiro": False}
        acceso = {"online": True, "ritiro": False}
        assert nomi(0, spento) == [] and nomi(1, spento) == []
        assert nomi(2, spento) == ["g2"] and nomi(4, spento) == ["g2"]
        assert nomi(5, spento) == ["np5"] and nomi(9, spento) == ["np5"]
        assert nomi(10, spento) == ["np10"] and nomi(15, spento) == ["np15"] and nomi(21, spento) == ["np15"]
        assert nomi(25, spento) == [] and nomi(30, spento) == [], "niente email a 30 giorni"
        assert nomi(5, acceso) == ["profilo_online"]
        assert nomi(14, acceso, {"profilo_online": "x"}) == ["r14"]
        assert nomi(14, {"online": True, "ritiro": True}, {"profilo_online": "x"}) == []
        assert nomi(7, spento, {"g7": "x"}) == [], "le marcature vecchie di RB8 valgono"
        assert passo_dovuto(2) == "g2" and passo_dovuto(30) is None

    def test_il_benvenuto_del_cerchio_sceglie_la_variante(self):
        sys.path.insert(0, str(BACKEND_DIR))
        from services.sequenze import passi_dovuti, stato_cerchio, porta_cerchio
        nomi = lambda sub, m={}: [p.nome for p in passi_dovuti("cerchio", 0, stato_cerchio(sub), m)]   # noqa: E731
        ritiri = {"source": "cerca-ritiro", "profile": {"interests": ["yoga"]}, "preferences": {}}
        flag = {"source": "home_letter", "profile": {}, "preferences": {"retreat_alert": {"enabled": True}}}
        med = {"source": "meditazioni", "profile": {}, "preferences": {}}
        cancello = {"source": "cancello:respiro", "profile": {}, "preferences": {}}
        altro = {"source": "blog_yoga", "profile": {}, "preferences": {}}
        assert nomi(ritiri) == ["benvenuto_ritiri"] and nomi(flag) == ["benvenuto_ritiri"]
        assert nomi(med) == ["benvenuto_meditazioni"] and nomi(cancello) == ["benvenuto_meditazioni"]
        assert nomi(altro) == ["benvenuto_altro"]
        assert nomi({**med, "profile": {"interests": ["suono"]}}) == ["benvenuto_ritiri"], \
            "dalle meditazioni ma con le vie scelte: parla di ritiri"
        assert nomi(ritiri, {"benvenuto_altro": "x"}) == [] and nomi(ritiri, {"c1": "x"}) == []
        assert passi_dovuti("cerchio", 2, stato_cerchio(ritiri), {}) == [], "solo appena confermati"
        assert porta_cerchio("gate_meditazione") == "meditazioni" and porta_cerchio(None) == "altro"

    def test_si_marca_prima_di_inviare_e_il_job_esiste(self):
        src = (BACKEND_DIR / "services" / "sequenze.py").read_text()
        corpo = src[src.index("async def _esegui"):src.index("async def _giro_operatore")]
        assert corpo.index("await _marca(") < corpo.index("_manda(passo, ctx)")
        assert '"is_sample": {"$ne": True}' in src and '"legacy_commerce": {"$ne": True}' in src
        assert '"status": "confirmed", "consent": True' in src, "il Cerchio scrive solo ai confermati"
        assert "saltato" in src
        bg = (BACKEND_DIR / "services" / "background_service.py").read_text()
        assert 'name="sequenze_job"' in bg and "sequenza_operatore" not in bg
        assert not (BACKEND_DIR / "services" / "sequenza_operatore.py").exists()
        subs = (BACKEND_DIR / "routers" / "subscribers.py").read_text()
        corpo = subs[subs.index("async def confirm("):subs.index("@router.", subs.index("async def confirm("))]
        assert "ReturnDocument.BEFORE" in corpo and 'await invia_subito("cerchio", email)' in corpo
        assert 'prima.get("status") != "confirmed"' in corpo

    def test_le_email_sono_scritte_e_fanno_una_cosa(self):
        sys.path.insert(0, str(BACKEND_DIR))
        from services import email_sequenze as T
        testo = (BACKEND_DIR / "services" / "email_sequenze.py").read_text().lower()
        for frase in ANTI_URGENZA + ("ultimi posti", "affrettati", "solo per oggi", "cordiali saluti"):
            assert frase not in testo, frase
        assert "whatsapp" not in testo, "a noi si dice Telegram (founder 10/9 sera)"
        assert "def op_g30" not in testo
        ctx = {"nome": "Giulia Serra", "email": "g@esempio.it", "org": {"name": "Studio"},
               "stato": {"online": False, "ritiro": False, "slug": None, "iban": False}, "fondatori": None}
        oggetti = set()
        for fn in (T.op_np5, T.op_np10, T.op_np15):
            o, c = fn(ctx)
            oggetti.add(o)
            assert "Ciao Giulia," in c and c.count('class="btn"') == 1 and "/public-profile" in c
            assert "Valentina" in c
        assert len(oggetti) == 3
        _, c15 = T.op_np15(ctx)
        assert "ultima email" in c15 and "resta aperto" in c15 and "chiamami" in c15
        ctx_on = {**ctx, "stato": {"online": True, "ritiro": False, "slug": "giulia", "iban": False}}
        _, c = T.op_profilo_online(ctx_on)
        assert "/o/giulia" in c and "Telegram" in c and "IBAN" in c
        _, c_iban = T.op_profilo_online({**ctx_on, "stato": {**ctx_on["stato"], "iban": True}})
        assert "IBAN" not in c_iban
        _, c14 = T.op_r14(ctx_on)
        assert "senza commissioni" in c14 and "bonifico" in c14 and "/events/new" in c14
        o2, c2 = T.op_g2_admin(ctx)
        assert "Telegram" in c2 and "Studio" in o2

    def test_il_benvenuto_del_cerchio_parla_solo_di_quello_che_ha_chiesto(self):
        sys.path.insert(0, str(BACKEND_DIR))
        from services import email_sequenze as T
        base = {"nome": "Giulia", "email": "g@esempio.it", "token": "tok", "citta": "", "interessi": [],
                "travel": "", "porta": "altro", "vuole_ritiri": False}
        o, c = T.benvenuto_cerchio_ritiri({**base, "citta": "Bari", "interessi": ["yoga", "suono"], "travel": "near", "vuole_ritiri": True})
        assert o == "Benvenuto nel Cerchio di Aurya" and "lo yoga e il suono" in c and "vicino a Bari" in c
        assert "te lo scriviamo" in c and "/meditazioni" in c and "dicci le tue vie" not in c
        _, c_vuoto = T.benvenuto_cerchio_ritiri({**base, "vuole_ritiri": True})
        assert "dicci le tue vie e dove vivi" in c_vuoto and "/newsletter/preferenze/tok" in c_vuoto
        o_m, c_m = T.benvenuto_cerchio_meditazioni({**base, "porta": "meditazioni"})
        assert "meditazioni" in o_m and "/meditazioni" in c_m and c_m.count('class="btn"') == 1
        assert "ritir" not in c_m.lower(), "dalle meditazioni, senza preferenze: nessuna parola sui ritiri"
        _, c_a = T.benvenuto_cerchio_generico(base)
        assert "/meditazioni" in c_a and "Lettera" in c_a and "/newsletter/preferenze/tok" in c_a
        for corpo in (c, c_m, c_a):
            assert "/newsletter/preferenze/tok" in corpo, "ci si cancella da ogni email"
        subs = (BACKEND_DIR / "routers" / "subscribers.py").read_text()
        assert "Benvenuto nel Cerchio: un clic e sei dentro" in subs

    def test_le_risposte_e_i_moduli_arrivano_alla_casella_di_aurya(self):
        """FV6 (10/9 sera, founder): Reply-To = aurya.life@gmail.com su OGNI
        email (chi risponde al noreply arriva li'), il piede lo dice, e i
        moduli verso di noi (regia, aziende, strutture, promemoria) scrivono
        alla stessa casella."""
        sys.path.insert(0, str(BACKEND_DIR))
        import importlib, os
        os.environ.pop("REPLY_TO_EMAIL", None); os.environ.pop("AURYA_INBOX_EMAIL", None)
        import services.email_service as es
        importlib.reload(es)
        assert es.CASELLA_AURYA == "aurya.life@gmail.com" and es.REPLY_TO_DEFAULT == "aurya.life@gmail.com"
        d = es._payload_brevo("a@b.it", "x", "<p>x</p>")
        assert d["replyTo"] == {"email": "aurya.life@gmail.com"}, "anche senza reply_to esplicito"
        assert es._payload_brevo("a@b.it", "x", "<p>x</p>", reply_to="op@studio.it")["replyTo"] == {"email": "op@studio.it"}
        piede = es._wrap_template("<p>ciao</p>", "it")
        assert "Per rispondere, scrivi a aurya.life@gmail.com" in piede and "non rispondere" not in piede
        seq = (BACKEND_DIR / "services" / "email_sequenze.py").read_text()
        assert "def risposte_a()" in seq and "reply_to=risposte_a()" in seq
        motore = (BACKEND_DIR / "services" / "sequenze.py").read_text()
        assert "send_email(CASELLA_AURYA, oggetto" in motore, "il promemoria a noi va alla casella"
        strutture = (BACKEND_DIR / "services" / "strutture_email.py").read_text()
        assert "send_email(CASELLA_AURYA, oggetto" in strutture, "regia, aziende e strutture scrivono alla casella"
        assert "ADMIN_EMAIL" not in strutture[strutture.index("def avvisa_piattaforma_richiesta"):strutture.index("def ricevuta_operatore")]
        assert "AURYA_INBOX_EMAIL" in (BACKEND_DIR / ".env.example").read_text()

    def test_l_iscrizione_ha_una_struttura_sola(self):
        """founder 10/9 sera: stessa struttura dell'iscrizione della landing
        principale ovunque (form della Lettera, preferenze), e l'avviso
        ritiri acceso SOLO dove un form lo chiede."""
        pref = (FE / "features" / "prelaunch" / "PreferenzeRitiri.jsx").read_text()
        assert "export const VIE" in pref
        assert "export const BASE_TO_EXP" in pref and "export const TRAVELS = ['near', 'italy', 'abroad']" in pref
        form = (FE / "features" / "prelaunch" / "LeadForm.jsx").read_text()
        # US (10/9 notte): il blocco «avvisami» e' AvvisamiRitiri (condiviso
        # coi cancelli del mondo Sound) e monta lo stesso PreferenzeRitiri,
        # col budget: quattro cose, ovunque
        assert form.count("<PreferenzeRitiri") == 1 and "<AvvisamiRitiri" in form
        avv = (FE / "features" / "prelaunch" / "AvvisamiRitiri.jsx").read_text()
        assert "<PreferenzeRitiri" in avv and "budget={budget} setBudget={setBudget}" in avv
        for morto in ("expInterests", "expCity", "expTravel", "EXP_INTERESTS"):
            assert morto not in form, f"doppione sopravvissuto: {morto}"
        pagina = (FE / "features" / "prelaunch" / "NewsletterPreferencesPage.js").read_text()
        assert "<PreferenzeRitiri" in pagina and "interests: versoBackend(interests)" in pagina
        cerchio = (FE / "lib" / "cerchio.js").read_text()
        assert "wantsExperiences = null" in cerchio and "typeof wantsExperiences === 'boolean'" in cerchio
        assert (BACKEND_DIR / "services" / "migrazioni_cerchio.py").exists()
        assert "migrate_cerchio_alert_esplicito_v1()" in (BACKEND_DIR / "server.py").read_text()

    def test_il_cliente_risponde_all_operatore_non_ad_aurya(self):
        """FV7 (10/9 sera, founder): le email che il cliente riceve a nome
        dell'operatore (richiesta, conferma, biglietto, promemoria,
        prenotazione) rispondono all'operatore anche quando non ha
        impostato un indirizzo di risposta: contatto, notifiche, account.
        Mai il default di piattaforma (aurya.life@gmail.com) su quelle."""
        oes = (BACKEND_DIR / "services" / "order_email_service.py").read_text()
        assert "async def contatto_operatore(" in oes
        assert oes.count("await contatto_operatore(") == 2, "entrambe le vie di _load_store_context"
        corpo = oes[oes.index("async def contatto_operatore"):oes.index("async def _load_store_context")]
        assert '("reply_to_email", "contact_email", "notification_email")' in corpo
        assert '"role": "admin"' in corpo, "ultima risorsa: l'account dell'operatore"
        assert "CASELLA_AURYA" not in corpo and "REPLY_TO_DEFAULT" not in corpo
        es = (BACKEND_DIR / "services" / "email_service.py").read_text()
        assert 'store.get("reply_to_email") or await contatto_operatore(org_id, store)' in es
        assert "reply_to=(customer_email or None)" in oes, "l'operatore risponde al cliente, non ad Aurya"
        # FV7-bis: l'operatore VEDE e puo' cambiare l'indirizzo, in Impostazioni
        org = (BACKEND_DIR / "routers" / "organizations.py").read_text()
        assert '@router.get("/current/risposte-clienti")' in org and '@router.put("/current/risposte-clienti")' in org
        assert org.index("async def _risposte_clienti") < org.index('@router.get("/current/cerchio-vicino")'), "mai fra decoratore e funzione"
        card = (FE / "features" / "settings" / "sections" / "RisposteCard.jsx").read_text()
        assert "risposte-clienti" in card and 'data-testid="risposte-effettivo"' in card
        assert "<RisposteCard />" in (FE / "features" / "settings" / "SettingsPage.js").read_text()
        # chi usa il contesto passa il suo reply_to (non lascia il default)
        for f in ("payment_email_service.py", "event_email_service.py"):
            src = (BACKEND_DIR / "services" / f).read_text()
            assert 'reply_to=ctx["reply_to"]' in src, f

    def test_l_anteprima_nel_pannello_e_i_numeri(self):
        ap = (BACKEND_DIR / "routers" / "admin_platform.py").read_text()
        assert '@router.get("/sequenze/anteprima")' in ap and '@router.get("/sequenze/passi")' in ap
        assert "require_system_admin" in ap[ap.index("async def sequenze_anteprima"):]
        assert '"sequenze_30g": sequenze' in ap
        # SA-R: l'anteprima e' il tab «Email automatiche» di Iscritti al Cerchio, con la prova
        tab = (FE / "features" / "admin" / "SequenzeTab.js").read_text()
        assert 'data-testid="sequenze-anteprima"' in tab and "srcDoc={reso.html}" in tab
        assert "/admin/platform/sequenze/prova" in tab and 'data-testid="seq-prova"' in tab
        assert '@router.post("/sequenze/prova")' in ap and "[PROVA]" in ap
        assert "<SequenzeTab />" in (FE / "features" / "admin" / "CerchioPage.js").read_text()
        assert "SequenzeAnteprima" not in (FE / "features" / "admin" / "PlatformOverviewTab.js").read_text()
        assert 'data-testid="numeri-lunedi-sequenze"' in (FE / "features" / "admin" / "PlatformOverviewTab.js").read_text()


class TestRb9StrisciaEFondatore:
    """RB9 (10/9/2026): la striscia-guida dice la data dei fondatori col
    contatore vero; il profilo pubblico porta il badge «Fondatore»
    (primi 20 nella rete entro il 31/10/2026, fonte routers/fondatori)."""

    def test_la_striscia_dice_la_data_col_contatore_vero(self):
        src = (FE / "features" / "onboarding" / "OnboardingStrip.js").read_text()
        assert "api.get('/public/fondatori')" in src
        assert 'data-testid="strip-fondatori"' in src and "fondatori?.aperto" in src
        assert "Club regalato fino al 30 giugno 2027" in src and "Ne restano {fondatori.rimasti}" in src

    def test_il_badge_fondatore_viene_dal_backend(self):
        fon = (BACKEND_DIR / "routers" / "fondatori.py").read_text()
        assert "async def ids_fondatori()" in fon and "naturali[:posti]" in fon   # BD: forzati + naturali
        assert "SCADENZA.isoformat()" in fon
        pub = (BACKEND_DIR / "routers" / "public.py").read_text()
        assert '"fondatore": org_id in await _ids_fondatori(),' in pub
        hdr = (FE / "features" / "storefront" / "components" / "OperatorIdentityHeader.jsx").read_text()
        assert 'data-testid="founder-badge"' in hdr and "data.fondatore" in hdr
        assert hdr.index('data-testid="verified-badge-slot"') < hdr.index('data-testid="founder-badge"'), \
            "Verificato Aurya resta il primo badge"


class TestCodaBadgeERecensioni:
    """Coda del founder (10/9 sera): i badge si governano dal pannello
    system admin (In evidenza, Fondatore forzato/escluso; Verificato
    resta la tab Interviste); le recensioni nel profilo sono un blocco
    in evidenza che al clic scorre alla sezione."""

    def test_i_badge_dal_pannello(self):
        adm = (BACKEND_DIR / "routers" / "admin.py").read_text()
        assert '"/organizations/{org_id}/badges"' in adm
        assert 'updates["directory_featured"] = bool(body["featured"])' in adm
        assert 'updates["fondatore_forzato"] = v' in adm
        assert "directory_featured=bool(doc.get(\"directory_featured\"))" in adm
        fon = (BACKEND_DIR / "routers" / "fondatori.py").read_text()
        assert 'r.get("fondatore_forzato") is True' in fon and "posti = max(0, TETTO - len(forzati))" in fon
        tab = (FE / "features" / "admin" / "OrganizationsTab.js").read_text()
        assert 'data-testid="org-toggle-featured"' in tab and 'data-testid="org-cycle-fondatore"' in tab
        assert "adminAPI.setBadges(" in tab
        assert "setBadges:" in (FE / "api" / "admin.js").read_text()

    def test_le_recensioni_sono_un_blocco_in_evidenza_che_scorre(self):
        hdr = (FE / "features" / "storefront" / "components" / "OperatorIdentityHeader.jsx").read_text()
        assert 'data-testid="reviews-cta"' in hdr
        assert "document.getElementById('recensioni')" in hdr and "scrollIntoView" in hdr
        assert "#recensioni" in hdr, "dalla pagina intervista porta al profilo"
        assert "scrivi la prima" in hdr, "anche a zero recensioni la voce c'e'"
        # founder 10/9: «piu' in evidenza, ma lean» — resta nella fila dei badge
        i = hdr.index('data-testid="reviews-cta"')
        assert "rounded-full" in hdr[i:i + 900] and "text-2xl" not in hdr[i:i + 900]
        page = (FE / "features" / "storefront" / "OperatorProfilePage.js").read_text()
        assert 'id="recensioni"' in page and "scroll-mt-20" in page


class TestOnda3LeSorgentiELaMisura:
    """Rebranding onda 3 (10/9/2026): RB12 il box di fine articolo per
    categoria porta alla porta di chi cerca; RB13 la porta viaggia
    nell'URL, finisce nella fonte dell'iscritto e negli eventi GA4;
    RB14 i numeri del lunedi' nel pannello di sistema; P6 il contatore
    del Cerchio nel wizard del ritiro (il primo innesco)."""

    def test_rb12_il_magazine_apre_la_porta_di_chi_cerca(self):
        page = (FE / "features" / "storefront" / "BlogArticlePage.js").read_text()
        assert "sitePhase === 'network' && BOOKABLE_CATS.has(article.category) ? (" in page
        assert 'data-testid="art-porta-cerca"' in page
        assert "/cerca-ritiro?tema=${article.category}&porta=magazine" in page
        assert "/esperienze?porta=magazine" not in page, "NV (10/9 sera): dal Magazine si va solo alla landing"
        assert page.count("<BlogNewsletterCTA") == 1, "la Lettera resta per le categorie editoriali"
        tl = (FE / "features" / "prelaunch" / "TravelerLandingPage.js").read_text()
        assert "initialInterests={temaIniziale()}" in tl and "TEMA_TO_CHIP" in tl

    def test_rb13_la_porta_finisce_nella_fonte_e_negli_eventi(self):
        lf = (FE / "features" / "prelaunch" / "LeadForm.jsx").read_text()
        assert "get('porta')" in lf and "source: fonte," in lf
        assert "[context || 'landing', porta].filter(Boolean).join(':')" in lf
        home = HOME.read_text()
        assert "`${CERCA_PATH}?porta=home`" in home and "`${OPERATORI_PATH}?porta=home`" in home
        assert "trackEvent('porta', { porta: 'cerca', da: 'home' })" in home
        esp = (FE / "features" / "storefront" / "RetreatsCalendarPage.js").read_text()   # RE (10/9)
        assert "/cerca-ritiro?porta=esperienze" in esp and "trackEvent('porta'" in esp

    def test_rb14_i_numeri_del_lunedi(self):
        src = (BACKEND_DIR / "routers" / "admin_platform.py").read_text()
        assert '@router.get("/lunedi")' in src
        for chiave in ('"confermati"', '"con_citta"', '"in_programma"', '"ultimi_7g"',
                       '"attivi_90g"', '"team_building"', '"ritiri_30g"', '"porte_30g"'):
            assert chiave in src, chiave
        assert "_cached(\"lunedi\")" in src, "cache 60s come la panoramica"
        tab = (FE / "features" / "admin" / "PlatformOverviewTab.js").read_text()
        assert 'data-testid="numeri-lunedi"' in tab and "api.get('/admin/platform/lunedi')" in tab
        assert tab.index('data-testid="numeri-lunedi"') < tab.index("Riga 1 — i miei soldi"), \
            "prima la fila, poi i soldi"

    def test_p6_il_contatore_del_cerchio_nel_wizard(self):
        org = (BACKEND_DIR / "routers" / "organizations.py").read_text()
        assert '@router.get("/current/cerchio-vicino")' in org
        assert '"preferences.retreat_alert.regions": slug' in org and '"soglia_lettera": 50' in org
        corpo = org[org.index("async def cerchio_vicino"):org.index('@router.get("/current/onboarding-status")')]
        assert '"email"' not in corpo and "email\": 1" not in corpo, "mai email: solo conteggi"
        wiz = (FE / "features" / "events" / "EventWizard.js").read_text()
        assert "api.get('/organizations/current/cerchio-vicino'" in wiz
        assert 'data-testid="wizard-cerchio-contatore"' in wiz
        assert "La Lettera per zona parte da" in wiz, "il cancello scritto in chiaro"


class TestP4IlCatalogoDel2027:
    """P4 (10/9/2026, founder: «impostiamoli gia' correttamente e
    consolidiamo»): il catalogo del 2027 vive nel codice da oggi — Club
    49/anno (solo annuale), Pro 119/anno o 12/mese, Club Fondatori — e
    la VENDITA si accende il 1° gennaio 2027. Il Pro da 19/190 e' ritirato."""

    def test_il_catalogo_e_la_migrazione(self):
        seed = (BACKEND_DIR / "services" / "seed_commercial_plans.py").read_text()
        assert 'VENDITA_PIANI_DAL = "2027-01-01"' in seed
        assert '"slug": "retreat_club"' in seed and '"name": "Club Fondatori"' in seed
        blocco = seed[seed.index("RETREAT_COMMERCIAL_PLANS: List[dict] = ["):]
        assert '"price_monthly": 19.0' not in blocco and '"price_yearly": 190.0' not in blocco, "il Pro di agosto e' ritirato"
        pricing = (BACKEND_DIR / "services" / "seed_pricing.py").read_text()
        assert "async def migrate_catalogo_2027_v1" in pricing
        assert 'aggiorna["stripe_price_id_monthly"] = None' in pricing, "i price id di agosto (19/190) escono"
        assert "await migrate_catalogo_2027_v1()" in (BACKEND_DIR / "server.py").read_text()
        model = (BACKEND_DIR / "models" / "commercial_plan.py").read_text()
        assert "available_from: Optional[str] = None" in model and 'intervals: List[str] = ["month", "year"]' in model

    def test_la_vendita_e_chiusa_fino_alla_data(self):
        bill = (BACKEND_DIR / "routers" / "billing.py").read_text()
        assert '"code": "non_in_vendita"' in bill and "date.today().isoformat() < dal" in bill
        assert '"code": "cadenza_non_disponibile"' in bill
        page = (FE / "pages" / "PlansPage.js").read_text()
        assert "nonAncoraInVendita(plan)" in page and "billing.available_from_label" in page
        assert "soloAnnuale" in page, "il Club e' solo annuale"
        assert "retreat_club" in (FE / "features" / "admin" / "pianiAurya.js").read_text()
        rp = (FE / "pages" / "RetreatPlansPage.js").read_text()
        assert "example_title" not in rp and "feeExample" not in rp, "founder 10/9: via gli esempi sui 100 €"
        assert 'data-testid={`plans-cta-${plan.slug}`}' in rp and "nonAncoraInVendita(plan)" in rp
        assert "md:grid-cols-3" in rp, "tre schede: Gratis, Club, Pro"

    def test_le_parole_dentro_dicono_le_stesse_del_fuori(self):
        it = json.loads((FE / "locales" / "it" / "settings.json").read_text())["billing"]
        assert "1° gennaio 2027" in it["retreat"]["subtitle"] and "gratuito per sempre" in it["retreat"]["subtitle"]
        assert "30 giugno 2027" in it["retreat"]["founding_note"]
        for k in ("retreat_club_prima_fila", "retreat_club_lettera_zona", "retreat_club_rete_lavoro",
                  "retreat_pro_racconto", "retreat_pro_whatsapp", "retreat_founding_badge"):
            assert it["features"].get(k), k
        src = (FE / "features" / "prelaunch" / "PricingPage.js").read_text()
        assert "PRICING_2027 = { spinta: 19, club: 49, pro: 119 }" in src
        pricing = (BACKEND_DIR / "services" / "seed_pricing.py").read_text()
        assert "async def migrate_stripe_prezzi_2027_v1" in pricing and 'startswith("sk_live_")' in pricing
        assert "price_1UE819RL6JKSLFw8BZRkQlLX" in pricing and "price_1UE81ZRL6JKSLFw8H0XyEHbD" in pricing


class TestP2TerEventiCoerenti:
    """Founder (10/9 sera): «l'utente e' libero di impostare un evento anche
    senza caparra? le informazioni sulla caparra appaiono? consolidiamo».
    Un ritiro puo' non avere caparra (piano «tutto in una volta», il
    default); la pagina pubblica dice SEMPRE come si prenota e come si
    paga (online con carta / bonifico dopo la conferma / da concordare)
    e nomina la caparra solo se c'e'; l'email segue le stesse regole."""

    def test_il_payload_pubblico_dice_se_c_e_il_bonifico_ma_mai_l_iban(self):
        pub = (BACKEND_DIR / "routers" / "public.py").read_text()
        assert "bank_transfer: bool = False" in pub
        assert 'bank_transfer=bool((org.get("bank_iban") or "").strip())' in pub

    def test_la_pagina_del_ritiro_dice_come_si_paga_in_ogni_caso(self):
        page = (FE / "features" / "storefront" / "EventLandingPage.js").read_text()
        assert 'data-testid="come-si-paga"' in page and "paymentPlan.methodOnline" in page
        assert "paymentPlan.methodBank" in page and "paymentPlan.methodAgree" in page
        assert "deposit.requestBank" in page and "deposit.requestAgree" in page
        assert "bankTransfer={!!data.bank_transfer}" in page
        assert page.count("product.payment_plan.mode !== 'full'") >= 2, "la caparra si nomina solo se c'e'"
        assert "faqAfterRequestA" in page and "trustRequest" in page

    def test_l_email_segue_il_piano_e_l_iban(self):
        src = (BACKEND_DIR / "services" / "order_email_service.py").read_text()
        assert 'chiave = "order_bank_body_full" if d["deposit"] >= d["total"] else "order_bank_body"' in src
        assert "async def _pagamento_concordare_block(" in src
        assert "effective_mode(plan, start_at, now) == PaymentPlanMode.FULL" in src, "l'email segue la regola last-minute della pagina e di Stripe"
        em = (BACKEND_DIR / "services" / "email_service.py").read_text()
        for k in ("order_bank_body_full", "order_agree_body", "order_agree_deposit"):
            assert em.count(f'"{k}"') >= 2, k

    def test_il_wizard_e_chiaro_sulla_caparra_e_sull_iban(self):
        it = json.loads((FE / "locales" / "it" / "products.json").read_text())["wizards"]["event"]["payments"]
        assert it["modeHeading"] == "Caparra e saldo"
        assert it["modes"]["full"]["title"].startswith("Nessuna caparra")
        assert "Solo con la prenotazione online" in it["modes"]["deposit_installments"]["desc"]
        wiz = (FE / "features" / "events" / "EventWizard.js").read_text()
        assert 'data-testid="wizard-bonifico-hint"' in wiz and "setOrgIban(res.data?.bank_iban || '')" in wiz
        assert "['full', 'deposit_balance']" in wiz, "su richiesta niente rate"


class TestFv1IlMuroDellaVerifica:
    """FV1 (10/9/2026, audit del funnel): l'operatore si registrava, leggeva
    «controlla la tua email», cliccava, e trovava un bottone «Accedi» per
    rifare il login. Ora il clic sul link di verifica FA ENTRARE (la
    risposta porta la sessione) e atterra sul benvenuto; la schermata dopo
    la registrazione dice «apri l'email» e rimanda il link da li'. La
    risposta 202 uniforme alla registrazione resta: e' l'anti-enumerazione."""

    def test_la_verifica_porta_la_sessione(self):
        m = (BACKEND_DIR / "models" / "auth.py").read_text()
        assert "access_token: Optional[str] = None" in m[m.index("class VerifyEmailResponse"):]
        r = (BACKEND_DIR / "routers" / "auth.py").read_text()
        i = r.index("async def verify_email(")
        corpo = r[i:r.index("@router.", i)]
        assert "access_token=sessione, user=utente" in corpo
        assert '"status": "verification_required"' in r, "la 202 uniforme resta"

    def test_il_clic_entra_da_solo_e_la_schermata_rimanda(self):
        pages = (FE / "pages" / "AuthPages.js").read_text()
        assert "adottaSessione(dati)" in pages and "navigate('/benvenuto', { replace: true })" in pages
        ctx = (FE / "context" / "AuthContext.js").read_text()
        assert "const adottaSessione = useCallback" in ctx
        form = (FE / "features" / "prelaunch" / "InlineSignupForm.js").read_text()
        assert 'data-testid="ol-signup-resend"' in form and "authAPI.resendVerification(email)" in form
        assert "un clic e sei dentro" in form

    def test_il_giorno_zero_e_scritto(self):
        seq = (BACKEND_DIR / "services" / "email_sequenze.py").read_text()
        assert "def benvenuto_operatore(" in seq and "Entra nel tuo spazio" in seq
        # FV5 (10/9 sera): le risposte vanno al Reply-To (REPLY_TO_EMAIL o ADMIN_EMAIL)
        assert "reply_to=risposte_a()" in seq and "Telegram" in seq
        for frase in ("Cordiali saluti", "affrettati", "ultimi posti"):
            assert frase not in seq
        svc = (BACKEND_DIR / "services" / "auth_service.py").read_text()
        assert "benvenuto_operatore(user.email, user.name, verification_token, user_locale)" in svc


class TestFv8IlPercorsoSenzaVicoliCiechi:
    """FV8 (10/9/2026 sera, founder: «verifica che iscrizione, account,
    verifica e accesso siano snelli, senza bug»). Giro fatto da utente
    vero nel browser: operatore dalla landing e da /accedi, Cerchio da
    /cerca-ritiro e dalle meditazioni, disiscrizione e re-iscrizione.
    Quattro vicoli ciechi chiusi: il link scaduto non offriva niente; il
    secondo clic diceva «link non valido»; «prima conferma la tua email»
    al login non rimandava; la schermata dopo la registrazione mostrava
    il testo vecchio (le chiavi del locale vincono sul defaultValue)."""

    def test_dal_link_scaduto_si_rimanda_e_il_secondo_clic_dice_la_verita(self):
        pages = (FE / "pages" / "AuthPages.js").read_text()
        assert 'data-testid="verify-resend"' in pages and "authAPI.resendVerification(emailRimando.trim())" in pages
        assert "setStatus('gia')" in pages and "Era già verificata" in pages
        auth = (BACKEND_DIR / "routers" / "auth.py").read_text()
        corpo = auth[auth.index("async def verify_email("):auth.index("@router.", auth.index("async def verify_email("))]
        assert '"verification_token_hash": None' in corpo, "il token resta MONOUSO (SEC S2.3)"
        assert '"verification_token_used_hash": token_hash' in corpo and '"verification_token_used_hash": token_hash, "email_verified": True' in corpo
        assert corpo.count('message="Email già verificata."') == 2, "il secondo clic si riconosce dall'hash consumato"

    def test_al_login_non_verificato_si_rimanda_da_li(self):
        login = (FE / "features" / "account" / "AccountLoginPage.js").read_text()
        assert 'data-testid="login-rimanda-verifica"' in login and "authAPI.resendVerification(email.trim())" in login
        assert "setNonVerificata(true)" in login

    def test_la_schermata_dopo_la_registrazione_dice_le_parole_nuove(self):
        import json
        auth = json.loads((FE / "locales" / "it" / "auth.json").read_text())
        assert auth["signup"]["verify_email_title"] == "Apri la tua email: un clic e sei dentro"
        assert "{{email}}" in auth["signup"]["verify_email_message"]
        assert auth["verify_email"]["error_title"] == "Questo link non vale più"

    def test_chi_torna_dopo_la_disiscrizione_riparte_da_zero(self):
        subs = (BACKEND_DIR / "routers" / "subscribers.py").read_text()
        corpo = subs[subs.index("async def subscribe("):subs.index("async def confirm(")]
        assert '"$unset": {"sequenza": "", "unsubscribed_at": "", "unsubscribed_by": ""}' in corpo

    def test_il_mondo_sound_parte_in_italiano(self):
        i18n = (FE / "i18n.js").read_text()
        for via in ("meditazioni", "frequenze", "newsletter", "entra-nella-rete", "accedi", "verify-email"):
            assert f"|{via}" in i18n, via


class TestTxUnaTassonomiaSola:
    """TX (10/9/2026 sera, founder: «le categorie dei ritiri sono complete
    come quelle del profilo? serve integrazione»). Le vie di chi cerca
    (EXPERIENCE_INTERESTS meno «misto») SONO le categorie dei ritiri;
    ogni disciplina del profilo ha una casa fra le categorie; il wizard
    legge la tassonomia vera e suggerisce quella coerente col profilo."""

    def test_le_vie_sono_le_categorie(self):
        sys.path.insert(0, str(BACKEND_DIR))
        from models.retreat_taxonomy import RETREAT_CATEGORIES, DISCIPLINA_TO_CATEGORIA, categoria_suggerita
        from routers.subscribers import EXPERIENCE_INTERESTS
        from models.disciplines import DISCIPLINES
        assert set(EXPERIENCE_INTERESTS) - {"misto"} <= set(RETREAT_CATEGORIES)
        assert "cerchi" not in EXPERIENCE_INTERESTS and "femminile" in EXPERIENCE_INTERESTS
        assert set(DISCIPLINA_TO_CATEGORIA) == set(DISCIPLINES), "ogni disciplina ha una casa"
        assert set(DISCIPLINA_TO_CATEGORIA.values()) <= set(RETREAT_CATEGORIES)
        assert categoria_suggerita(["shiatsu", "yoga"]) == "massaggio" and categoria_suggerita([]) is None

    def test_il_wizard_legge_la_tassonomia_e_suggerisce(self):
        wiz = (FE / "features" / "events" / "EventWizard.js").read_text()
        assert "api.get('/products/taxonomies')" in wiz and "month: '1900-01'" not in wiz
        assert "suggerita_event_ticket" in wiz and 'data-testid="wizard-categoria-suggerita"' in wiz
        prod = (BACKEND_DIR / "routers" / "products.py").read_text()
        assert '"suggerita_event_ticket": suggerita' in prod

    def test_i_vocabolari_del_frontend_sono_allineati(self):
        sys.path.insert(0, str(BACKEND_DIR))
        from models.retreat_taxonomy import RETREAT_CATEGORIES
        import json as _json
        pref = (FE / "features" / "prelaunch" / "PreferenzeRitiri.jsx").read_text()
        assert "women: 'femminile'" in pref and "'cerchi'" not in pref
        blog = (FE / "features" / "storefront" / "BlogArticlePage.js").read_text()
        for k in RETREAT_CATEGORIES:
            assert f"'{k}'" in blog[blog.index("const BOOKABLE_CATS"):blog.index("]);", blog.index("const BOOKABLE_CATS"))], k
        cats = _json.loads((FE / "locales" / "it" / "landings.json").read_text())["categories"]
        for k in RETREAT_CATEGORIES:
            assert k in cats, f"etichetta mancante per {k}"
        assert "migrate_vie_femminile_v1()" in (BACKEND_DIR / "server.py").read_text()


class TestSiSoloItalianoNelWizard:
    """SI (10/9/2026 sera, founder): «dalla creazione ritiri togliamo la
    possibilita' di creare un ritiro in piu' lingue: solo italiano»."""

    def test_il_wizard_non_ha_piu_lingue(self):
        wiz = (FE / "features" / "events" / "EventWizard.js").read_text()
        assert "MultiLangSection" not in wiz
        for morto in ("trName", "trDescription", "trLong"):
            assert morto not in wiz, morto
        assert "translations: (() =>" not in wiz


class TestSeoRIlConsolidamento:
    """SEO-R (10/9/2026 sera, founder): «operatori e ritiri indicizzati con
    le parole dell'olistico; quando si condivide un link deve apparire
    un'anteprima e una descrizione appropriata, non a caso»."""

    def test_il_profilo_dice_le_discipline_e_la_citta(self):
        shell = (BACKEND_DIR / "routers" / "seo_shell.py").read_text()
        corpo = shell[shell.index("async def _meta_operator("):shell.index("async def _meta_link_page")]
        assert "from models.disciplines import DISCIPLINES" in corpo
        assert 'f"{name} · {d} a {city} | Aurya"' in corpo and "ritiri a {city}" not in corpo
        assert "recensioni verificate su Aurya" in corpo
        client = (FE / "features" / "storefront" / "OperatorProfilePage.js").read_text()
        assert "`${data.name} · ${d} a ${data.city} | Aurya`" in client and "profilo professionista`" not in client

    def test_la_landing_del_ritiro_ha_descrizione_e_anteprima_vere(self):
        shell = (BACKEND_DIR / "routers" / "seo_shell.py").read_text()
        corpo = shell[shell.index("async def _meta_event("):shell.index("async def _meta_product(")]
        assert "Lo conduce {org_name}" in corpo and "public_profile.cover_url" in corpo
        assert 'f"{base}/esperienze/{cat}"' in corpo and '/ritiri/{cat}' not in corpo
        client = (FE / "features" / "storefront" / "EventLandingPage.js").read_text()
        assert "| Aurya`" in client and "· prenota online`" not in client

    def test_le_pagine_cardine_hanno_la_loro_anteprima(self):
        shell = (BACKEND_DIR / "routers" / "seo_shell.py").read_text()
        blocco = shell[shell.index("_BRAND_PAGES = {"):shell.index("def _meta_brand_page")]
        for chiave in ("newsletter", "meditazioni", "chi-siamo", "manifesto", "aziende", "costi", "cerca-ritiro", "entra-nella-rete"):
            i = blocco.index(f'    "{chiave}": {{')
            assert '"image": "/media/' in blocco[i:blocco.index("\n    },", i)], f"{chiave} senza immagine di anteprima"
        assert "Operatori olistici e professionisti del benessere in Italia | Aurya" in shell
        assert 'if head in ("strutture", "struttura"):' in shell
        seo = (BACKEND_DIR / "routers" / "seo.py").read_text()
        assert 'urls.append(_url(f"{base}/esplora-operatori"' not in seo, "un 301 non si dichiara in sitemap"
