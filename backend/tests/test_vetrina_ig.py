"""
CICLO IG (3/9/2026) — il profilo mobile da vetrina (per il carosello
Instagram del founder). SOLO PELLE: nessuna logica, nessuna API,
nessun campo nuovo. Piano in docs/VETRINA_MOBILE_PLAN_2026-09.md.

Vincolo del founder: ogni operatore carica foto di dimensioni
diverse e devono vedersi bene per TUTTI — quindi mai un layout
guidato dalla proporzione della foto.
"""
from pathlib import Path

FE = Path(__file__).resolve().parents[1].parent / "frontend" / "src"
STORE = FE / "features" / "storefront"


class TestFotoRobuste:
    def test_l_avatar_e_sempre_tondo_e_ritagliato(self):
        """Qualunque proporzione la foto abbia: cerchio + object-cover
        col fuoco alto (le teste dei ritratti verticali restano)."""
        src = (STORE / "components" / "OperatorIdentityHeader.jsx").read_text()
        assert "rounded-full" in src and "object-cover" in src
        assert "object-[center_25%]" in src, \
            "senza il fuoco alto le foto verticali tagliano il volto"

    def test_la_cover_e_una_banda_ad_altezza_fissa(self):
        src = (STORE / "components" / "OperatorIdentityHeader.jsx").read_text()
        assert "h-44" in src and "object-cover" in src, \
            "la cover deve avere altezza fissa: mai il layout che balla"
        assert "identity-card" in src, "manca la card d'identita'"

    def test_via_la_fotona_a_grandezza_naturale(self):
        """Il ritratto non vive piu' nell'aside a dimensione naturale
        (era il difetto: uno screenshot = una foto). Entra in galleria."""
        src = (STORE / "OperatorProfilePage.js").read_text()
        assert "w-full h-auto max-h-96 object-contain" not in src, \
            "la fotona a proporzione naturale e' tornata nell'aside"


class TestVetrinaMockup:
    def test_la_cta_prenota_e_lo_sticky(self):
        """IG5 (founder 3/9): su mobile la porta d'azione e' UNA, la
        barra flottante (gli piaceva quella); il bottone in card resta
        solo desktop. E senza listino non esiste nessuna delle due:
        non c'e' nulla da prenotare."""
        src = (STORE / "OperatorProfilePage.js").read_text()
        assert 'data-testid="profile-cta-prenota"' in src
        assert 'data-testid="profile-cta-sticky"' in src
        assert "bookSession" in src and "#listino" in src
        i = src.index('data-testid="profile-cta-prenota"')
        assert "hidden lg:block" in src[i:i + 300], "in card = solo desktop"
        assert src.rfind("{hasListino && (", 0, i) > -1, "in card solo con listino"
        j = src.index('data-testid="profile-cta-sticky"')
        assert "{hasListino && !listinoInVista && (" in src[j - 400:j], \
            "flottante solo con listino"
        assert "pb-20 lg:pb-0" in src, "la barra flottante non deve coprire il fondo pagina"

    def test_una_casa_sola_per_ogni_informazione(self):
        """IG5: discipline e citta' nella testata (non piu' nell'aside),
        la recensione si scrive dalla sezione Recensioni, l'aside e'
        «Contatti» e su mobile scende in fondo; niente sezione ritiri
        vuota."""
        page = (STORE / "OperatorProfilePage.js").read_text()
        header = (STORE / "components" / "OperatorIdentityHeader.jsx").read_text()
        assert 'data-testid="profile-disciplines"' in header
        assert 'data-testid="profile-disciplines"' not in page
        assert "/destinazioni/" in header and "/destinazioni/" not in page
        assert page.count("reviews.writeCta") == 1, "una sola porta per la recensione"
        assert 'data-testid="profile-contacts"' in page
        assert "{hasUpcoming && (" in page and "{true && (" not in page

    def test_il_prezzo_e_in_evidenza(self):
        src = (STORE / "OperatorProfilePage.js").read_text()
        assert "text-base font-bold text-[#376254]" in src, \
            "il prezzo deve risaltare come nei mockup"

    def test_il_calendario_vive_sui_dati_esistenti(self):
        cal = (STORE / "components" / "MiniCalendario.jsx").read_text()
        assert "upcoming" in cal, "il calendario usa i dati che il profilo GIA' riceve"
        assert "if (!quadro) return null" in cal, \
            "agenda vuota = niente calendario (mai una griglia vuota)"
        # zero chiamate: e' solo disegno
        assert "fetch(" not in cal and "api." not in cal.lower()
        pagina = (STORE / "OperatorProfilePage.js").read_text()
        assert "<MiniCalendario" in pagina


DASH = FE / "features" / "dashboard"


class TestDashboardIG4:
    """IG4 (3/9/2026) — la home operatore si legge in un colpo, dall'alto:
    numeri del mese, cose da fare, agenda e andamento. Il founder ha
    scartato il saluto «Benvenuta, {nome}» («e se si tratta di un
    uomo?»): la riga di apertura e' la data, uguale per tutti. Le
    tessere sono INSIGHT del nostro sistema, non i numeri del mockup."""

    def test_nessun_saluto_con_genere(self):
        home = (DASH / "OperatorHome.js").read_text()
        assert "Benvenut" not in home and "Bentornat" not in home, \
            "un saluto declinato sbaglia genere: la riga di apertura e' la data"
        assert 'data-testid="home-oggi"' in home

    def test_i_numeri_del_mese_prima_di_tutto(self):
        home = (DASH / "OperatorHome.js").read_text()
        ordine = [home.index(k) for k in (
            'data-testid="home-panoramica"', 'data-testid="home-dafare"',
            'data-testid="home-ritiri"', 'data-testid="home-andamento"')]
        assert ordine == sorted(ordine), \
            "gerarchia: Questo mese → Da fare → Prossimi ritiri → Andamento"
        for tile in ("tile-incassato", "tile-in-arrivo", "tile-prenotazioni"):
            assert f'testid="{tile}"' in home
        # IG5 (founder): le visite al profilo NON sono una tessera ma una
        # sezione in fondo, con la quota «tramite Aurya» e i 30 giorni
        assert 'testid="tile-visite"' not in home
        assert 'data-testid="home-visite"' in home
        assert home.index('data-testid="home-andamento"') < home.index('data-testid="home-visite"')
        assert "aurya_visits" in home and "last_30d" in home

    def test_stesse_sei_fonti_nessuna_chiamata_nuova(self):
        home = (DASH / "OperatorHome.js").read_text()
        for ep in ("/event-occurrences/admin/list", "/orders/payments-overview",
                   "/analytics/cashflow", "/reviews",
                   "/organizations/current/onboarding-status", "/analytics/visibility"):
            assert ep in home
        assert home.count("api.get(") == 6, "IG4 e' pelle: nessuna chiamata in piu'"

    def test_visibilita_spenta_niente_zero_finto(self):
        """Il modulo commerce puo' essere spento (403): le tessere del
        mese spariscono, come faceva la vecchia card. Mai uno zero finto."""
        home = (DASH / "OperatorHome.js").read_text()
        assert "visRes.value.data || {}) : false" in home
        assert "visAvailable && (" in home

    def test_il_grafico_non_mostra_il_futuro_a_zero(self):
        home = (DASH / "OperatorHome.js").read_text()
        assert "months.filter((m) => m.month <= ym)" in home, \
            "i 3 secchi futuri del cashflow sembravano un crollo"

    def test_posti_come_barra_e_chiavi_italiane(self):
        import json
        home = (DASH / "OperatorHome.js").read_text()
        assert "reserved_seats" in home and "style={{ width: `${pct}%` }}" in home
        it = json.loads((FE / "locales" / "it" / "dashboard.json").read_text())["home"]
        for k in ("overview_title", "tile_collected", "tile_collected_sub", "tile_expected_sub",
                  "tile_overdue_sub", "delta_same", "delta_vs", "seats", "trend_title", "avg_ticket",
                  "visits_title", "visits_from_aurya", "visits_from_outside", "visits_30d"):
            assert k in it, f"chiave italiana mancante: {k}"


BACKEND = Path(__file__).resolve().parents[1]


class TestFlussiDalProfilo:
    """Verifica olistica 3/9/2026 (founder: «tutto deve funzionare:
    prenotazioni, recensioni ecc.»). Collaudati dal browser sul profilo
    demo: richiesta di appuntamento dal listino → ordine + cliente CRM;
    conferma dell'operatore; recensione con codice. Due verita' emerse
    e chiuse, qui guardiate."""

    def test_la_richiesta_di_appuntamento_e_da_gestire_non_un_carrello(self):
        """Il cliente invia una richiesta dal profilo: nasce come bozza
        con source «storefront», identica a un carrello abbandonato.
        Ora la regola la riconosce (needs_approval/appointment_request)
        e la home la conta tra le cose da gestire, non tra i carrelli."""
        regole = (BACKEND / "services" / "commerce_rules.py").read_text()
        i = regole.index('"reason": "appointment_request"')
        assert 'it.get("transaction_mode") == "request"' in regole[i - 400:i]
        assert regole.index('"reason": "approval_required"') < i < regole.index('"reason": "rental_availability"')
        ordini = (BACKEND / "routers" / "orders.py").read_text()
        assert "_richiesta_cliente(o)" in ordini
        import json
        it = json.loads((FE / "locales" / "it" / "orders.json").read_text())
        assert "appointment_request" in it["review"]

    def test_il_codice_recensione_si_brucia_solo_a_recensione_accettata(self):
        """Prima il codice veniva consumato PRIMA delle regole (solo chi
        ha prenotato, testo minimo): chi inciampava doveva chiederne uno
        nuovo. Ora: peek → regole → consume, in quest'ordine."""
        src = (BACKEND / "services" / "review_service.py").read_text()
        i = src.index("async def submit_review")
        corpo = src[i:]
        assert corpo.index("_peek_otp(") < corpo.index('"orders_required"') \
            < corpo.index("_consume_otp(") < corpo.index('status = "published" if verified')

    def test_il_wizard_ritiri_accetta_un_prodotto_senza_metadata(self):
        """Emerso creando il ritiro della simulazione via API: metadata
        Optional nel payload, dict obbligatorio nel Product → 400."""
        src = (BACKEND / "routers" / "event_occurrences.py").read_text()
        assert '"metadata": body.product.metadata or {}' in src

    def test_titoli_di_sezione_uniformi_con_accento(self):
        """Founder 3/9: «ottimizziamo le informazioni dei vari riquadri in
        modo che spicchino bene» → ogni titolo di sezione del profilo ha
        la stessa classe (profile-h2) con la barretta oro; «Chi sono»,
        non «Chi siamo» (e' una persona); le discipline in un riquadro
        titolato «Le mie discipline»."""
        import json
        page = (STORE / "OperatorProfilePage.js").read_text()
        cal = (STORE / "components" / "MiniCalendario.jsx").read_text()
        header = (STORE / "components" / "OperatorIdentityHeader.jsx").read_text()
        assert page.count("profile-h2") >= 6 and "profile-h2" in cal
        assert "<h2 className=\"font-heading" not in page, "un titolo senza accento"
        assert "myDisciplines" in header
        it = json.loads((FE / "locales" / "it" / "landings.json").read_text())["operator"]
        assert it["about"] == "Chi sono" and it["myDisciplines"] == "Le mie discipline"
        assert it["contacts"] == "Contatti"
