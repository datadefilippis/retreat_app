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
        for tid in ("ol-hero", "ol-go", "ol-studio", "ol-rete", "ol-now", "ol-prezzi", "ol-join", "ol-faq", "ol-who", "ol-form", "ol-end"):
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
        for k in ("v1k", "v6k", "reteTitle", "nowB4t", "nowCta"):
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
        assert "Trovami il mio ritiro | Ritiri ed esperienze olistiche vicino a te | Aurya" in shell
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
        assert "senza commissioni" in it["doorOpText"] and "senza commissioni" in it["prosOffer"]
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

    def test_la_pagina_esperienze_e_semplice_e_onesta(self):
        page = (FE / "features" / "storefront" / "EsperienzePage.js").read_text()
        assert "api.get('/public/retreats'" in page
        for tid in ("esp-fascia-prima-fila", "esp-tutti", "esp-vuoto",
                    "esp-cta-cerca", "esp-cta-op", "esp-prima-fila"):
            assert f'data-testid="{tid}"' in page, tid
        assert "su richiesta" in page and "prenotazione online" in page
        # RB13 (onda 3): le porte portano il parametro ?porta=esperienze
        assert 'to="/cerca-ritiro?porta=esperienze"' in page and 'to="/entra-nella-rete?porta=esperienze"' in page
        assert "senza commissioni" in page
        assert "noSearch" in page, "niente ricerca ne' mappa: quelle sono della fase marketplace"

    def test_il_gate_segue_la_fase(self):
        app = (FE / "App.js").read_text()
        i = app.index("function EsperienzeGate()")
        gate = app[i:i + 400]
        assert "sitePhase === 'network'" in gate and "<EsperienzePage />" in gate
        assert 'to="/"' in gate, "in fase marketplace la directory e' la home"

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
        blocco = shell_src[shell_src.index('"aziende": {'):shell_src.index('"esperienze": {')]
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


class TestRb8LaSequenzaDopoLaRegistrazione:
    """RB8 (10/9/2026, piano di rebranding onda 2): dopo il benvenuto
    quattro momenti con UNA azione ciascuno (g2 a Valentina, g7 profilo,
    g14 primo ritiro, g30 come va), ognuno solo nella sua finestra, mai
    due volte, mai un'urgenza."""

    def test_i_passi_partono_solo_nella_loro_finestra(self):
        sys.path.insert(0, str(BACKEND_DIR))
        from services.sequenza_operatore import passo_dovuto, PASSI, FINESTRA_GIORNI
        assert [n for n, _ in PASSI] == ["g2", "g7", "g14", "g30"] and FINESTRA_GIORNI == 7
        assert passo_dovuto(0) is None and passo_dovuto(1) is None
        assert passo_dovuto(2) == "g2" and passo_dovuto(6) == "g2"
        assert passo_dovuto(7) == "g7" and passo_dovuto(13) == "g7"
        assert passo_dovuto(14) == "g14" and passo_dovuto(20) == "g14"
        assert passo_dovuto(25) is None, "chi si e' registrato mesi fa non riceve tre email in un colpo"
        assert passo_dovuto(30) == "g30" and passo_dovuto(36) == "g30" and passo_dovuto(37) is None

    def test_si_marca_prima_di_inviare_e_il_job_esiste(self):
        src = (BACKEND_DIR / "services" / "sequenza_operatore.py").read_text()
        assert src.index('{"$set": {f"sequenza.{passo}": now.isoformat()}}') < src.index("if _manda(passo, org")
        assert '"is_sample": {"$ne": True}' in src and '"legacy_commerce": {"$ne": True}' in src
        assert "reply_to=ADMIN_EMAIL" in src, "a g30 si risponde: legge Valentina"
        for frase in ANTI_URGENZA + ("ultimi posti", "affrettati", "solo per oggi"):
            assert frase not in src.lower(), frase
        bg = (BACKEND_DIR / "services" / "background_service.py").read_text()
        assert 'name="sequenza_operatore_job"' in bg

    def test_le_email_dicono_una_azione_e_le_parole_del_piano(self):
        sys.path.insert(0, str(BACKEND_DIR))
        from services.sequenza_operatore import _contenuto
        org = {"id": "o1", "name": "Studio Prova"}
        f = {"aperto": True, "tetto": 20, "rimasti": 17, "scadenza": "2026-10-31"}
        _, c7 = _contenuto("g7", "Giulia Serra", org, {"online": False, "ritiro": False, "slug": None}, f)
        assert "Ciao Giulia," in c7 and "Completa il profilo" in c7 and c7.count('class="btn"') == 1
        _, c7b = _contenuto("g7", "", org, {"online": True, "ritiro": False, "slug": "giulia"}, f)
        assert "/o/giulia" in c7b and "senza commissioni" in c7b
        _, c14 = _contenuto("g14", "Giulia", org, {"online": True, "ritiro": False, "slug": "giulia"}, f)
        assert "gratis e senza commissioni" in c14 and "bonifico" in c14 and "/events/new" in c14
        _, c30 = _contenuto("g30", "Giulia", org, {"online": True, "ritiro": True, "slug": "giulia"}, f)
        assert "Rispondi a questa email" in c30 and "cinquanta" in c30
        assert "31/10/2026" in c30 and "Ne restano 17" in c30
        _, c30b = _contenuto("g30", "Giulia", org, {"online": True, "ritiro": True, "slug": "giulia"}, {"aperto": False})
        assert "fondatori" not in c30b, "chiuso il tetto, la parola sparisce"


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
        assert "/esperienze?porta=magazine" in page
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
        esp = (FE / "features" / "storefront" / "EsperienzePage.js").read_text()
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
        assert "reply_to=ADMIN_EMAIL" in seq and "Telegram" in seq
        for frase in ("Cordiali saluti", "affrettati", "ultimi posti"):
            assert frase not in seq
        svc = (BACKEND_DIR / "services" / "auth_service.py").read_text()
        assert "benvenuto_operatore(user.email, user.name, verification_token, user_locale)" in svc
