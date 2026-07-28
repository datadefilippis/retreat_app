"""TW1 — il Listino (docs/LISTINO_PIANO_2026-07.md) + INVARIANTI.

Il listino e' un'interfaccia NUOVA sopra il motore VECCHIO: queste
guardie assicurano che resti cosi'. TestInvariants e' il contratto
anti-sfascio della Parte 0 del piano: se un'onda TW lo rompe, si
torna indietro.
"""

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8000")
FRONTEND_SRC = BACKEND_DIR.parent / "frontend" / "src"


class TestInvariants:
    """Parte 0 del piano: cio' che il Listino NON deve mai toccare."""

    def test_i1_event_landing_alive(self):
        # la landing evento resta la pagina di vendita completa
        r = requests.get(f"{BASE_URL}/__seo/e/masseria-demo/"
                         "ritiro-yoga-test-s1-2026-10-02", timeout=10)
        assert r.status_code == 200

    def test_i1_service_landing_alive(self):
        # /p/ resta vivo (retrocompatibilita' + slot picker)
        app = (FRONTEND_SRC / "App.js").read_text()
        assert '/p/:orgSlug' in app or 'path="/p/' in app

    def test_i2_i3_checkout_untouched(self):
        """Il listino non riscrive il checkout: le firme chiave del
        motore ordini/booking restano al loro posto."""
        occ = (BACKEND_DIR / "services" / "order_creation_service.py").read_text()
        assert "dominant_mode" in occ
        bs = (BACKEND_DIR / "services" / "booking_service.py").read_text()
        assert "issue_bookings_for_order" in bs

    def test_i4_slot_engine_untouched(self):
        sg = (BACKEND_DIR / "services" / "slot_generator.py").read_text()
        assert "generate_available_slots" in sg

    def test_i8_no_new_collection(self):
        """Una riga di listino E' un Product service: la pagina usa la
        API products, nessuna collection nuova."""
        page = (FRONTEND_SRC / "features" / "listino"
                / "ListinoPage.js").read_text()
        assert "productsAPI.create" in page
        assert "productsAPI.update" in page
        assert "item_type: 'service'" in page

    def test_store_guard_source_unchanged(self):
        """Il gate store-first NON e' stato ammorbidito: il listino lo
        soddisfa creando lo store tecnico, non aggirandolo."""
        sg = (BACKEND_DIR / "services" / "store_guard.py").read_text()
        assert "store_required" in sg
        assert "require_public_home" in sg


class TestListinoTW1:
    def test_ensure_default_endpoint_exists(self):
        src = (BACKEND_DIR / "routers" / "stores.py").read_text()
        assert '"/ensure-default"' in src
        assert "_ensure_default_store(org_id, current_user)" in src

    def test_ensure_default_requires_auth(self):
        r = requests.post(f"{BASE_URL}/api/stores/ensure-default", timeout=10)
        assert r.status_code in (401, 403)

    def test_listino_defaults_are_lean(self):
        """Default snelli: richiesta (niente Stripe richiesto), agenda
        ufficiale (nessuna regola custom), pubblicato subito."""
        page = (FRONTEND_SRC / "features" / "listino"
                / "ListinoPage.js").read_text()
        assert "transaction_mode: 'request'" in page
        assert "is_published: true" in page
        # lo store tecnico si garantisce PRIMA di pubblicare
        assert "storesAPI.ensureDefault()" in page

    def test_services_new_redirects_to_listino(self):
        app = (FRONTEND_SRC / "App.js").read_text()
        assert 'path="/listino"' in app
        block = app.split('path="/services/new"')[1][:120]
        assert 'Navigate to="/listino"' in block
        # il wizard resta l'editor avanzato su /services/:id
        assert 'path="/services/:product_id"' in app

    def test_nav_has_listino(self):
        layout = (FRONTEND_SRC / "components" / "Layout.js").read_text()
        assert "'/listino'" in layout


class TestProfileListinoTW2:
    """TW2 — il profilo E' il negozio: listino sull'endpoint pubblico,
    card rete con da-X-euro, OfferCatalog nella shell. I bottoni
    portano alla landing /p/ esistente (zero nuovo checkout: I3)."""

    def test_operator_endpoint_exposes_listino(self):
        r = requests.get(f"{BASE_URL}/api/public/operator/masseria-demo",
                         timeout=10)
        assert r.status_code == 200
        listino = r.json().get("listino")
        assert isinstance(listino, list) and len(listino) >= 1
        row = listino[0]
        for field in ("name", "slug", "price", "on_request",
                      "transaction_mode", "service_mode"):
            assert field in row

    def test_network_members_have_price_from(self):
        r = requests.get(f"{BASE_URL}/api/public/network/members", timeout=10)
        assert r.status_code == 200
        m = r.json()["items"][0]
        assert "services_count" in m and "price_from" in m

    def test_shell_has_offer_catalog(self):
        r = requests.get(f"{BASE_URL}/__seo/o/masseria-demo", timeout=10)
        assert r.status_code == 200
        assert '"@type": "OfferCatalog"' in r.text
        assert '"@type": "Service"' in r.text

    def test_profile_buttons_link_to_existing_landing(self):
        page = (FRONTEND_SRC / "features" / "storefront"
                / "OperatorProfilePage.js").read_text()
        assert "profile-listino" in page
        # il bottone usa la landing /p/ esistente, non un checkout nuovo
        assert "/p/${org_slug}/${row.slug}" in page
        assert "Richiedi appuntamento" in page and "Prenota" in page


class TestPotaturaTW3:
    """TW3 — potatura REVERSIBILE: mondo snello di default, commerce
    legacy dietro flag per-org. Codice mai eliminato (R1), ritorno in
    un click senza deploy (R2, R5)."""

    def test_flag_defaults_off(self):
        """Il flag vive sul modello Organization, default False."""
        src = (BACKEND_DIR / "models" / "organization.py").read_text()
        assert "legacy_commerce: bool = False" in src

    def test_admin_toggle_endpoint(self):
        """R2: il system admin riaccende il legacy senza deploy."""
        src = (BACKEND_DIR / "routers" / "admin.py").read_text()
        assert "legacy-commerce" in src
        r = requests.put(
            f"{BASE_URL}/api/admin/organizations/x/legacy-commerce",
            json={"enabled": True}, timeout=10)
        assert r.status_code in (401, 403)

    def test_lean_menu_gated_in_layout(self):
        """Mondo snello: le voci legacy (store, prodotti, corsi) e il
        menu entita' compaiono SOLO con legacyCommerce acceso."""
        layout = (FRONTEND_SRC / "components" / "Layout.js").read_text()
        assert "legacyCommerce" in layout
        assert "!legacyCommerce" in layout
        # il mondo snello contiene le 5 voci operative
        lean = layout.split("!legacyCommerce")[1]
        for href in ("'/listino'", "'/events'", "'/calendar'",
                     "'/orders'", "'/public-profile'"):
            assert href in lean[:900]

    def test_r5_legacy_menu_still_in_source(self):
        """R5: il menu legacy NON e' stato eliminato, e' solo dietro
        flag — con legacyCommerce true torna tutto."""
        layout = (FRONTEND_SRC / "components" / "Layout.js").read_text()
        assert "&& legacyCommerce" in layout
        for legacy_href in ("'/stores'", "'/products'", "'/courses'"):
            assert legacy_href in layout

    def test_storefront_redirects_to_profile(self):
        """I6: /s/ vetrina non muore, redirige al profilo /o/."""
        app = (FRONTEND_SRC / "App.js").read_text()
        assert "StoreToProfileRedirect" in app
        # legal e checkout RESTANO vivi (servono a Stripe e GDPR: I2, I7)
        assert 'path="/s/:slug/privacy"' in app
        assert 'path="/s/:slug/terms"' in app
        assert "checkout-success" in app

    def test_shell_storefront_serves_operator_meta(self):
        """La shell SEO di /s/{slug} risponde col profilo operatore."""
        r = requests.get(f"{BASE_URL}/__seo/s/masseria-demo", timeout=10)
        assert r.status_code == 200
        assert '/o/masseria-demo"' in r.text

    def test_store_guard_now_self_heals(self):
        """Profile-first: il gate store auto-crea lo store tecnico
        invece di fermare l'operatore (il 409 resta ultima difesa)."""
        sg = (BACKEND_DIR / "services" / "store_guard.py").read_text()
        assert "_ensure_default_store" in sg


class TestOnboardingTW4:
    """TW4 — onboarding a 3 passi: Presentati → Listino → Online.
    Il ritiro e' un suggerimento DOPO, non un gradino. Le org legacy
    tengono i 5 passi storici (coerenza con R5)."""

    def test_endpoint_has_lean_and_legacy_paths(self):
        src = (BACKEND_DIR / "routers" / "organizations.py").read_text()
        # ramo snello sui 3 passi...
        assert '"listino_filled"' in src
        assert '"online"' in src
        # ...gated dal flag TW3, col ramo legacy intatto
        assert 'legacy_commerce' in src
        assert '"retreat_published"' in src

    def test_lean_status_exposes_signals(self):
        """La dashboard (GT1b) legge stripe/ritiri anche nel mondo
        snello: vivono in `signals`, fuori dalla checklist."""
        src = (BACKEND_DIR / "routers" / "organizations.py").read_text()
        assert '"signals"' in src
        home = (FRONTEND_SRC / "features" / "dashboard"
                / "OperatorHome.js").read_text()
        assert "signals" in home

    def test_inizia_page_is_lean_first(self):
        page = (FRONTEND_SRC / "features" / "onboarding"
                / "IniziaPage.js").read_text()
        # i 3 passi snelli puntano a profilo e listino
        assert "'/public-profile'" in page and "'/listino'" in page
        assert "listino_filled" in page and "'online' in s" in page
        # il ritiro e' il suggerimento post-onboarding
        assert "inizia-next-retreat" in page
        assert "'/events/new'" in page
        # il percorso legacy a 5 passi resta nel sorgente (R5)
        assert "store_created" in page and "retreat_published" in page

    def test_ga4_first_service_online(self):
        page = (FRONTEND_SRC / "features" / "listino"
                / "ListinoPage.js").read_text()
        assert "trackEvent('first_service_online')" in page

    def test_deploy_runbook_exists(self):
        doc = (BACKEND_DIR.parent / "docs"
               / "RUNBOOK_DEPLOY_LISTINO.md").read_text()
        assert "legacy_commerce" in doc and "Rollback" in doc


class TestRitiriRS:
    """Ciclo Ritiri (docs/RITIRI_INTEGRITA_PIANO_2026-07.md).
    RS0: /listino dentro la shell dell'app. RS1: /events e' una
    pagina di soli ritiri, non un redirect all'hub prodotti."""

    def test_rs0_listino_in_app_shell(self):
        page = (FRONTEND_SRC / "features" / "listino"
                / "ListinoPage.js").read_text()
        assert "<AppLayout>" in page and "<Header" in page

    def test_rs1_events_is_dedicated_page(self):
        app = (FRONTEND_SRC / "App.js").read_text()
        # /events monta la pagina ritiri, non il redirect all'hub
        block = app.split('path="/events"')[1][:160]
        assert "EventsListPage" in block
        assert 'Navigate to="/products?type=event_ticket"' not in app

    def test_rs1_events_page_speaks_ritiri(self):
        page = (FRONTEND_SRC / "features" / "events"
                / "EventsListPage.js").read_text()
        assert "<AppLayout>" in page
        assert "EventsGrid" in page
        # niente vocabolario e-commerce nella casa dei ritiri
        assert "prodott" not in page.lower().replace(
            "hub multi-tipo: productspage", "")

    def test_rs1_products_hub_still_alive_for_legacy(self):
        """R1/R5: l'hub multi-tipo resta raggiungibile su /products."""
        app = (FRONTEND_SRC / "App.js").read_text()
        assert 'path="/products"' in app
        assert (FRONTEND_SRC / "features" / "products"
                / "ProductsPage.js").exists()


class TestWizardRS2:
    """RS2 — il wizard del ritiro: 4 passi, linguaggio esplicativo,
    stesso motore (payload e endpoint INTATTI: I1-I3)."""

    def _src(self):
        return (FRONTEND_SRC / "features" / "events"
                / "EventWizard.js").read_text()

    def test_four_steps_only(self):
        src = self._src()
        i = src.index("const TABS = [")
        block = src[i:i + 400]
        for key in ("'ritiro'", "'prezzo'", "'regole'", "'publish'"):
            assert key in block
        for gone in ("'base'", "'where'", "'tickets'", "'program'",
                     "'payments'"):
            assert gone not in block

    def test_payload_engine_untouched(self):
        """Il submit parla ancora la stessa lingua del backend: nessun
        campo del payload wizard e' stato perso nella riorganizzazione."""
        src = self._src()
        for field in ("payment_plan", "transaction_mode", "store_ids",
                      "cost_source: costSource", "wizardCreate",
                      "cancellation_policy", "attendee_fields"):
            assert field in src, field

    def test_explicative_language(self):
        src = self._src()
        # come si prenota, spiegato; preset di cancellazione; opzioni
        assert "Come si prenota" in src
        assert "policy-presets" in src and "CANCELLATION_PRESETS" in src
        assert "tiers-toggle" in src
        assert "Opzioni di partecipazione" in src
        # il percorso ritiri non manda piu' all'hub prodotti
        assert "/products?type=event_ticket" not in src

    def test_deep_link_i18n_loaded(self):
        """Fix bug preesistente: al deep-link su /events/new i bundle
        i18n admin non erano caricati (li portava solo Layout)."""
        assert "import '../../i18n-admin'" in self._src()

    def test_dashboard_back_goes_to_events(self):
        dash = (FRONTEND_SRC / "features" / "events"
                / "EventDashboardPage.js").read_text()
        assert '"/products?type=event_ticket"' not in dash


class TestPattiChiariRS3:
    """RS3 — le condizioni dell'operatore: un posto per scriverle
    (Impostazioni), un blocco solo per accettarle (checkout), sempre
    presenti (fallback autogenerato), timbrate sull'ordine."""

    def test_org_default_policy_endpoint(self):
        """La policy org-level si salva via PUT /organizations/current
        con validazione degli scaglioni."""
        src = (BACKEND_DIR / "routers" / "organizations.py").read_text()
        assert "default_cancellation_policy" in src
        assert "giorni decrescenti e rimborsi non crescenti" in src

    def test_conditions_card_in_settings(self):
        """Raggiungibile nel mondo snello: vive in Impostazioni, non
        dentro Stores."""
        card = (FRONTEND_SRC / "features" / "settings" / "sections"
                / "SalesConditionsCard.jsx").read_text()
        assert "MerchantLegalDialog" in card
        assert "default_cancellation_policy" in card
        settings = (FRONTEND_SRC / "features" / "settings"
                    / "SettingsPage.js").read_text()
        assert "SalesConditionsCard" in settings

    def test_wizard_inherits_org_policy(self):
        wiz = (FRONTEND_SRC / "features" / "events"
               / "EventWizard.js").read_text()
        assert "default_cancellation_policy" in wiz
        assert "Le mie condizioni" in wiz

    def test_checkout_single_consent_block(self):
        """Un solo blocco consensi: niente checkbox T&C legacy separata,
        blocco GDPR visibile anche senza legal pubblicati."""
        sf = (FRONTEND_SRC / "features" / "storefront"
              / "StorefrontPage.js").read_text()
        # la checkbox legacy F4 standalone non esiste piu'
        assert "checked={termsAccepted}" not in sf
        # le condizioni specifiche vivono DENTRO il blocco unico
        assert "condizioni specifiche" in sf
        # il blocco non e' piu' gated da gdprRequired
        assert ("{gdprRequired && (!isCustomerAuthenticated"
                not in sf)

    def test_consents_stamped_even_without_published_legal(self):
        """Il backend timbra i consensi espressi anche con legal
        autogenerati (versione autogen:v0); l'enforcement resta gated."""
        ocs = (BACKEND_DIR / "services"
               / "order_creation_service.py").read_text()
        assert "gdpr_flags_given" in ocs
        assert '"autogen:v0"' in ocs
        # RS3 — la policy di cancellazione resta timbrata sull'ordine
        assert "cancellation_policy_snapshot" in ocs

    def test_checkout_handoff_survives_redirect(self):
        """Fix regressione TW3: /s/x?checkout=1 e il preloadCart delle
        landing NON redirigono al profilo (il motore di acquisto
        resta intatto: I2, I3)."""
        app = (FRONTEND_SRC / "App.js").read_text()
        assert "wantsCheckout" in app
        assert "preloadCart" in app

    def test_conditions_links_on_public_pages(self):
        prof = (FRONTEND_SRC / "features" / "storefront"
                / "OperatorProfilePage.js").read_text()
        assert "profile-conditions" in prof
        for page in ("ProductLandingPage.js", "ReservationLandingPage.js"):
            src = (FRONTEND_SRC / "features" / "storefront" / page).read_text()
            assert "landing-conditions" in src, page
