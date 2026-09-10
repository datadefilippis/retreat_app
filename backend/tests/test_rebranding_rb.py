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
        assert it["doorSeekCta"] == "Trovami il mio ritiro"
        assert "meditazioni" in it["doorSeekText"], "la ricompensa immediata e' detta"
        assert it["doorOpTitle"] == "Sei un operatore olistico?", "lessico: all'operatore si dice operatore olistico"
        for parola in ("prenotazioni", "ritiri", "caparra", "senza commissioni"):   # P1: zero commissioni
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
        assert "31 dicembre 2026" in op["heroP3"] and "senza commissioni" in op["heroP3"], "il prezzo ha una data e la frase-marchio"
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


class TestRb6Rb7HeaderEPotature:
    """RB6: l'header dice all'operatore lo stesso gesto delle porte.
    RB7: Manifesto e Chi siamo senza «lentamente / tutto subito»,
    Meditazioni col lessico di chi cerca, /come-funziona un 301 vero."""

    def test_l_header_dice_apri_il_tuo_spazio(self):
        shell = (FE / "features" / "storefront" / "components" / "MarketplaceShell.jsx").read_text()
        assert "defaultValue: 'Apri il tuo spazio'" in shell
        it = json.loads(LOCALE.read_text())
        assert it["marketplace"]["forProfessionals"] == "Apri il tuo spazio"
        assert it["nwHome"]["doorOpCta"] == it["marketplace"]["forProfessionals"], "header e porta dicono lo stesso gesto"

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
                      "I fondatori.", "Club regalato per tutto il 2027", "La garanzia.", "E Stripe?"):
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
        assert "non prende commissioni" in op["faq1b1"] and "Club regalato per tutto il 2027" in op["nowP2"]
        assert "19 €" in op["faq1b3"] and "49 €" in op["faq1b3"] and "119 €" in op["faq1b3"]
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
        assert 'to="/cerca-ritiro"' in page and 'to="/entra-nella-rete"' in page
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
        assert "async def _bank_transfer_block(" in src
        assert "compute_deposit_minor" in src, "la caparra segue il piano del ritiro come con Stripe"
        i = src.index("async def notify_customer_order_received(")
        corpo = src[i:i + 3000]
        assert "_bank_transfer_block(order, org_id, order_ref, locale)" in corpo
        assert "{bank_block}" in corpo
        em = (BACKEND_DIR / "services" / "email_service.py").read_text()
        for k in ("order_bank_title", "order_bank_body", "order_bank_iban",
                  "order_bank_reason", "order_bank_note"):
            assert em.count(f'"{k}"') >= 2, f"{k}: it + en"

    def test_l_iban_non_esce_dalle_risposte_pubbliche(self):
        for rel in ("routers/public.py", "routers/seo_shell.py",
                    "routers/fondatori.py"):
            assert "bank_iban" not in (BACKEND_DIR / rel).read_text(), rel

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
        assert 'data-testid="events-chiedi-regia"' in events and "tipoIniziale={strutturaTipo}" in events
        dialog = (FE / "features" / "events" / "components" / "RichiestaStrutturaDialog.jsx").read_text()
        for tid in ("richiesta-tab-struttura", "richiesta-tab-regia", "richiesta-regia-intro", "richiesta-formula"):
            assert f'data-testid="{tid}"' in dialog or f"data-testid={{`richiesta-tab-" in dialog, tid
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
        assert "Club regalato per tutto il 2027" in src and "Ne restano {fondatori.rimasti}" in src

    def test_il_badge_fondatore_viene_dal_backend(self):
        fon = (BACKEND_DIR / "routers" / "fondatori.py").read_text()
        assert "async def ids_fondatori()" in fon and "righe[:TETTO]" in fon
        assert "SCADENZA.isoformat()" in fon
        pub = (BACKEND_DIR / "routers" / "public.py").read_text()
        assert '"fondatore": org_id in await _ids_fondatori(),' in pub
        hdr = (FE / "features" / "storefront" / "components" / "OperatorIdentityHeader.jsx").read_text()
        assert 'data-testid="founder-badge"' in hdr and "data.fondatore" in hdr
        assert hdr.index('data-testid="verified-badge-slot"') < hdr.index('data-testid="founder-badge"'), \
            "Verificato Aurya resta il primo badge"
