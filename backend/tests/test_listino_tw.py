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
        dentro Stores. (PS5: l'editor legale custom non e' piu' qui —
        vedi TestPotaturaPs5 — ma la politica di cancellazione resta.)"""
        card = (FRONTEND_SRC / "features" / "settings" / "sections"
                / "SalesConditionsCard.jsx").read_text()
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
        # PN2 — il JSX del checkout e' estratto da StorefrontPage.js in
        # components/checkout/ + hooks/useCheckoutForm.js: l'invariante
        # vale sull'unione dei sorgenti del checkout, non su un file solo.
        storefront = FRONTEND_SRC / "features" / "storefront"
        sf = "\n".join(p.read_text() for p in [
            storefront / "StorefrontPage.js",
            storefront / "components" / "checkout" / "CheckoutForm.jsx",
            storefront / "components" / "checkout" / "OrderSummary.jsx",
            storefront / "hooks" / "useCheckoutForm.js",
        ])
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


class TestClientiRS4:
    """RS4 — Clienti e newsletter tornano nel mondo snello: il consenso
    raccolto (RS3) deve essere VISIBILE e azionabile dall'operatore."""

    def test_customers_in_lean_menu(self):
        layout = (FRONTEND_SRC / "components" / "Layout.js").read_text()
        lean = layout.split("!legacyCommerce")[1][:1400]
        assert "customers-light" in lean

    def test_insights_links_newsletter_forms(self):
        page = (FRONTEND_SRC / "features" / "customer-insights"
                / "CustomerInsightsPage.jsx").read_text()
        assert "newsletter-forms-link" in page
        assert "'/newsletter-forms'" in page or '"/newsletter-forms"' in page

    def test_insights_endpoints_declare_module(self):
        """Coerenza MD2: la vista Clienti era protetta solo dal menu,
        ora il backend dichiara il modulo customers_light."""
        ma = (BACKEND_DIR / "services" / "module_access.py").read_text()
        assert '"customer_insights": "customers_light"' in ma
        router = (BACKEND_DIR / "modules" / "customer_insights"
                  / "router.py").read_text()
        assert "_require_insights_module" in router
        # tutte le route autenticate portano il gate
        assert router.count("_require_insights_module()") >= 6

    def test_insights_still_open_for_active_module(self):
        """MD1 attiva tutto di default: il gate non deve chiudere fuori
        le org esistenti (403 solo a modulo spento)."""
        r = requests.get(f"{BASE_URL}/api/customer-insights/overview",
                         timeout=10)
        # senza auth: 401/403 auth, NON un 500 da dependency rotta
        assert r.status_code in (401, 403)


class TestFunnelRS5:
    """RS5 — integrita' del funnel: fonte unica del consenso, Passaporto
    onesto, audit senza doppioni, promessa sull'email."""

    def test_magic_link_on_request_confirm(self):
        """Il magic link parte anche alla CONFERMA di una richiesta,
        non solo al pagamento (prima l'account restava pending e
        irraggiungibile)."""
        src = (BACKEND_DIR / "routers" / "orders.py").read_text()
        assert "send_claim_email_if_needed" in src

    def test_doc_audit_only_on_real_click(self):
        """Niente doppioni: l'audit dei documenti si scrive solo su
        click reale (il loggato ha gia' il record CG-4 dal signup)."""
        ocs = (BACKEND_DIR / "services"
               / "order_creation_service.py").read_text()
        assert "_clicked_docs" in ocs

    def test_newsletter_stats_include_checkout_optins(self):
        """Fonte unica: la vista newsletter conta anche i consensi
        dal checkout (email distinte, revoche escluse, unione onesta)."""
        nf = (BACKEND_DIR / "routers" / "newsletter_forms.py").read_text()
        assert "checkout_optins" in nf and "reachable_total" in nf
        page = (FRONTEND_SRC / "features" / "newsletter"
                / "NewsletterPage.js").read_text()
        assert "checkout-optins-line" in page
        assert "customers-light" in page  # il link 'Vedile in Clienti'

    def test_checkout_email_promise(self):
        # PN2 — la promessa email vive nel form estratto (CheckoutForm).
        sf = (FRONTEND_SRC / "features" / "storefront" / "components"
              / "checkout" / "CheckoutForm.jsx").read_text()
        assert "email-promise" in sf


class TestProfiloNegozioPN0:
    """PN0 (docs/PROFILO_NEGOZIO_PIANO_2026-07.md) — condizioni
    trovabili, ritiri sempre sul profilo, zero 'store' nei percorsi
    snelli."""

    def test_profile_shows_retreats_in_every_phase(self):
        prof = (FRONTEND_SRC / "features" / "storefront"
                / "OperatorProfilePage.js").read_text()
        # la sezione ritiri non e' piu' gated dalla fase del sito
        i = prof.index('id="ritiri"')
        assert "sitePhase !== 'network' && (" not in prof[max(0, i - 400):i]
        # e il bottone 'Visita il negozio' non esiste piu'
        assert "visitStore" not in prof

    def test_no_store_copy_in_retreat_path(self):
        hint = (FRONTEND_SRC / "components"
                / "DirectoryListingHint.jsx").read_text()
        assert "dal tuo store" not in hint
        assert "profilo pubblico" in hint
        import json as _json
        prod = _json.loads((FRONTEND_SRC / "locales" / "it"
                            / "products.json").read_text())
        flat = _json.dumps(prod, ensure_ascii=False)
        assert "pubblica lo store" not in flat.lower()
        assert "Pubblica uno store" not in flat
        dash = (FRONTEND_SRC / "locales" / "it"
                / "dashboard.json").read_text()
        assert "appare sul tuo profilo" in dash

    def test_conditions_discoverable(self):
        """La card Condizioni sta in alto in Impostazioni e ha rimandi
        da Profilo pubblico e da /inizia."""
        settings = (FRONTEND_SRC / "features" / "settings"
                    / "SettingsPage.js").read_text()
        assert (settings.index("<SalesConditionsCard />")
                < settings.index("<LanguageSelector />"))
        pub = (FRONTEND_SRC / "features" / "settings"
               / "PublicProfilePage.js").read_text()
        assert "conditions-shortcut" in pub
        inizia = (FRONTEND_SRC / "features" / "onboarding"
                  / "IniziaPage.js").read_text()
        assert "lean_profile_conditions" in inizia

    def test_pn1_listino_rows_ready_for_inline(self):
        """PN1 — la riga di listino pubblica porta cio' che serve
        all'acquisto inline: product_id, flag slot, opzioni."""
        r = requests.get(f"{BASE_URL}/api/public/operator/masseria-demo",
                         timeout=10)
        row = r.json()["listino"][0]
        for field in ("product_id", "has_availability_slots",
                      "service_options", "allow_custom_request"):
            assert field in row, field


class TestInlineCheckoutPN3:
    """PN3 — compra dal profilo, tutto in pagina: la riga di listino si
    espande su un harness (InlineServiceCheckout) che RIUSA il checkout
    dello storefront. La landing /p/ resta viva come link secondario."""

    def test_profile_primary_cta_expands_inline(self):
        """Il CTA primario della riga e' un bottone che espande in
        pagina (niente navigazione a /p/); il link /p/ resta come
        'Vedi dettagli' secondario."""
        prof = (FRONTEND_SRC / "features" / "storefront"
                / "OperatorProfilePage.js").read_text()
        assert "InlineServiceCheckout" in prof
        assert 'data-testid="listino-cta"' in prof
        # il bottone primario espande (aria-expanded), non naviga
        i = prof.index('data-testid="listino-cta"')
        assert "aria-expanded" in prof[i - 200:i + 200]
        # la landing /p/ sopravvive come link secondario sulla riga
        assert "/p/${org_slug}/${row.slug}" in prof
        assert "Vedi dettagli" in prof

    def test_inline_checkout_reuses_shared_form(self):
        """Un solo checkout nel codice (I2/I3): l'harness monta
        CheckoutForm/OrderSummary/useCheckoutForm dello storefront e
        NON reimplementa submit/consensi."""
        inline = (FRONTEND_SRC / "features" / "storefront" / "components"
                  / "checkout" / "InlineServiceCheckout.jsx").read_text()
        assert "import CheckoutForm from './CheckoutForm'" in inline
        assert "import OrderSummary from './OrderSummary'" in inline
        assert "useCheckoutForm" in inline
        assert "useStorefrontCart" in inline
        # zero secondo submit: l'ordine parte SOLO dal form condiviso
        assert "submitOrder" not in inline
        assert "order-request" not in inline
        # slot reali dallo stesso endpoint pubblico della landing /p/
        assert "getServiceSlots" in inline
        assert "AvailabilityCalendarSlotPicker" in inline

    def test_p_landing_still_alive(self):
        """La landing /p/ resta viva (SEO + link esterni): route nel
        router e payload pubblico che risponde."""
        app = (FRONTEND_SRC / "App.js").read_text()
        assert '/p/:orgSlug' in app or 'path="/p/' in app
        r = requests.get(
            f"{BASE_URL}/api/public/products/masseria-demo/seduta-di-reiki",
            timeout=10)
        assert r.status_code == 200
        assert r.json()["product"]["name"]


class TestRitiroSenzaStorePN4:
    """PN4/PN5 — il ritiro si compra senza mai vedere lo store: in
    contesto marketplace il CTA della landing /e/ apre il checkout
    CONDIVISO in pagina (InlineEventCheckout); l'handoff a /s/ resta
    SOLO per il guscio store (?store=1, org legacy_commerce)."""

    def _landing_src(self):
        return (FRONTEND_SRC / "features" / "storefront"
                / "EventLandingPage.js").read_text()

    def test_marketplace_checkout_opens_inline_not_on_s(self):
        """(a) niente piu' navigazione a /s/ per il checkout
        marketplace: il vecchio handoff openCheckout/mktp e' sparito,
        il ramo !fromStore apre l'overlay inline e basta."""
        src = self._landing_src()
        assert "InlineEventCheckout" in src
        # il vecchio handoff marketplace non esiste piu'
        assert "preloadCart.openCheckout" not in src
        assert "preloadCart.mktp" not in src
        # dentro handleProceed: prima il gate marketplace (inline),
        # POI l'unica navigate a /s/ (ramo store)
        i = src.index("const handleProceed")
        block = src[i:i + 1600]
        j = block.index("if (!fromStore)")
        inline_branch = block[j:block.index("}", j)]
        assert "setInlineOpen(true)" in inline_branch
        assert "navigate(" not in inline_branch
        assert j < block.index("navigate(`/s/${orgSlug}`")

    def test_inline_event_checkout_reuses_shared_form(self):
        """(b) un solo checkout nel codice (I2/I3): l'harness monta
        CheckoutForm/OrderSummary/useCheckoutForm dello storefront e
        NON reimplementa submit/consensi."""
        inline = (FRONTEND_SRC / "features" / "storefront" / "components"
                  / "checkout" / "InlineEventCheckout.jsx").read_text()
        assert "import CheckoutForm from './CheckoutForm'" in inline
        assert "import OrderSummary from './OrderSummary'" in inline
        assert "useCheckoutForm" in inline
        # zero secondo submit: l'ordine parte SOLO dal form condiviso
        assert "submitOrder" not in inline
        assert "order-request" not in inline
        # il payload evento resta quello dello store (fan-out F3)
        assert "ticket_tier_id" in inline
        assert "occurrence_id" in inline

    def test_no_store_copy_in_marketplace_path(self):
        """PN5 — copy pass: niente 'negozio' nel percorso marketplace
        (harness inline + chiave gdprRequired neutralizzata)."""
        inline = (FRONTEND_SRC / "features" / "storefront" / "components"
                  / "checkout" / "InlineEventCheckout.jsx").read_text()
        # (il nome del piano PROFILO_NEGOZIO nei commenti non conta)
        assert "negozio" not in inline.lower().replace(
            "profilo_negozio_piano", "")
        import json as _json
        sf = _json.loads((FRONTEND_SRC / "locales" / "it"
                          / "storefront.json").read_text())
        assert "negozio" not in sf["errors"]["gdprRequired"].lower()

    def test_i1_event_landing_still_alive(self):
        """(c) invariante I1: la landing /e/ risponde 200 anche col
        checkout inline a bordo."""
        r = requests.get(f"{BASE_URL}/__seo/e/masseria-demo/"
                         "ritiro-yoga-test-s1-2026-10-02", timeout=10)
        assert r.status_code == 200


class TestListinoUnPassoLM1:
    """LM1 (docs/LISTINO_MARKETPLACE_PIANO_2026-07.md) — la voce di
    listino si configura in un passo: base sempre visibile + due
    accordion progressivi sulla riga espansa (solo righe salvate)."""

    PAGE = FRONTEND_SRC / "features" / "listino" / "ListinoPage.js"

    def test_accordion_progressivi_nella_riga(self):
        """I due momenti LM1 esistono nella riga espansa e 'Impostazioni
        avanzate' (label PS2) resta il percorso avanzato."""
        page = self.PAGE.read_text()
        assert "Opzioni e varianti" in page
        assert "Prenotazione e incasso" in page
        assert "Impostazioni avanzate" in page
        # progressione: una sezione aperta alla volta, mai tutte
        assert "openSection" in page

    def test_riuso_editor_opzioni_senza_copia(self):
        """ServiceOptionsEditor e StripeRequiredAlert sono riusati
        as-is: import dai moduli originali, nessuna copia locale."""
        page = self.PAGE.read_text()
        assert "from '../services/components/ServiceOptionsEditor'" in page
        assert "from '../../components/StripeRequiredAlert'" in page
        assert "serviceOptionsAPI" in page
        listino_dir = FRONTEND_SRC / "features" / "listino"
        copie = [f.name for f in listino_dir.iterdir()
                 if "Options" in f.name or "Stripe" in f.name]
        assert copie == [], f"copie locali vietate: {copie}"

    def test_salvataggio_conserva_metadata(self):
        """use_default_schedule e transaction_mode si salvano dalla
        riga SENZA perdere gli altri campi metadata (merge su rawMeta);
        i default snelli di saveNew restano intatti (vedi anche
        test_listino_defaults_are_lean)."""
        page = self.PAGE.read_text()
        assert "use_default_schedule: !!edit.useDefaultSchedule" in page
        assert "...edit.rawMeta" in page
        assert "transaction_mode: edit.transactionMode" in page
        # payloadFromRow resta il payload base identico di TW1
        assert "payloadFromRow(draft)" in page
        assert "payloadFromRow(edit)" in page


class TestCardOperatoreLM2:
    """LM2 (docs/LISTINO_MARKETPLACE_PIANO_2026-07.md) — card operatore
    ricca: rating + aggregato listino + anteprima su /public/operators,
    vista rapida in card, footer con 'Esplora operatori' in entrambe
    le fasi."""

    def test_operators_endpoint_exposes_card_fields(self):
        """rating / services_count / price_from / listino_preview
        viaggiano sugli item, derivati dalla stessa query prodotti
        (niente N+1 per pagina)."""
        src = (BACKEND_DIR / "routers" / "public.py").read_text()
        blocco = src.split("async def public_operators_index")[1]
        blocco = blocco.split("async def _operator_listino")[0]
        for campo in ('"rating"', '"services_count"', '"price_from"',
                      '"listino_preview"'):
            assert campo in blocco, f"campo mancante sull'item: {campo}"
        # una sola query prodotti per tutte le org della pagina
        assert "svc_by_org" in blocco
        assert "_operator_listino(" not in blocco, "niente N+1 in loop"
        r = requests.get(f"{BASE_URL}/api/public/operators", timeout=10)
        assert r.status_code == 200
        # quando la fase corrente mostra operatori, i campi ci sono
        for item in r.json()["items"][:1]:
            for campo in ("rating", "services_count", "price_from",
                          "listino_preview"):
                assert campo in item, f"campo mancante live: {campo}"

    def test_card_vista_rapida_in_pagina(self):
        """La card espande l'anteprima IN CARD (bottone aria-expanded,
        pattern PN3): niente navigazione, il profilo resta la CTA."""
        page = (FRONTEND_SRC / "features" / "storefront"
                / "OperatorsIndexPage.js").read_text()
        assert "Vista rapida" in page
        assert "operator-quick-view" in page
        assert "aria-expanded={quickOpen}" in page
        assert "listino_preview" in page
        assert "Vai al profilo" in page
        # fiducia e prezzo di partenza sulla card
        assert "op.rating" in page
        assert "da {{price}} euro" in page

    def test_footer_esplora_operatori_entrambe_le_fasi(self):
        """La voce 'Esplora operatori' → /operatori non e' dietro
        isNetwork ne' prelaunch: vive in rete E in marketplace."""
        shell = (FRONTEND_SRC / "features" / "storefront" / "components"
                 / "MarketplaceShell.jsx").read_text()
        righe = [l for l in shell.splitlines()
                 if "Esplora operatori" in l and "/operatori" in l]
        assert righe, "voce footer 'Esplora operatori' assente"
        assert all("isNetwork" not in l and "prelaunch" not in l
                   for l in righe)


class TestRicercaLM3:
    """LM3 (docs/LISTINO_MARKETPLACE_PIANO_2026-07.md) — ricerca stile
    Treatwell su /operatori: barra sticky Dove/Cosa/Ordina, geo via
    indice 2dsphere ($geoNear) e nuovi parametri API."""

    def _blocco_endpoint(self):
        src = (BACKEND_DIR / "routers" / "public.py").read_text()
        blocco = src.split("async def public_operators_index")[1]
        return blocco.split("async def _operator_listino")[0]

    def test_endpoint_accetta_sort_e_service_category(self):
        """sort=distance|rating|price e service_category (categorie
        delle righe di listino) esistono e rispondono live; sort
        sconosciuto degrada al default (rating senza geo)."""
        blocco = self._blocco_endpoint()
        assert "service_category" in blocco
        assert '("distance", "rating", "price")' in blocco
        # default sensato: distance se geo attivo, rating altrimenti
        assert '"distance" if _geo_active else "rating"' in blocco
        r = requests.get(f"{BASE_URL}/api/public/operators",
                         params={"sort": "rating"}, timeout=10)
        assert r.status_code == 200
        assert r.json().get("sort") == "rating"
        r2 = requests.get(f"{BASE_URL}/api/public/operators",
                          params={"service_category": "consulenze",
                                  "sort": "boh"}, timeout=10)
        assert r2.status_code == 200
        assert r2.json().get("sort") == "rating"

    def test_geo_via_indice_2dsphere_con_fallback(self):
        """La distanza arriva da $geoNear sull'indice an3_org_geo
        (public_profile.geo); l'haversine resta SOLO come fallback
        per-item per i doc con lat/lng senza campo geo."""
        blocco = self._blocco_endpoint()
        assert "$geoNear" in blocco
        assert '"key": "public_profile.geo"' in blocco
        assert "maxDistance" in blocco
        # fallback dichiarato: doc legacy fuori dall'indice sparse
        assert "_haversine_km" in blocco
        assert "distance_km" in blocco
        # niente piu' ciclo haversine post-lista su tutti gli item
        assert 'i["distance_km"] = (round(_haversine_km' not in blocco

    def test_barra_sticky_dove_cosa_ordina(self):
        """La barra unica sticky vive in testa a /operatori: Dove
        (GeoSearchBar fluida), Cosa (select categorie), Ordina per
        (?ordina= in URL) e il toggle Mappa dentro la barra."""
        page = (FRONTEND_SRC / "features" / "storefront"
                / "OperatorsIndexPage.js").read_text()
        assert 'data-testid="operators-search-bar"' in page
        assert "sticky top-14" in page
        # URL fonte di verita': ?ordina= + categoria come path segment
        assert "SORT_PARAM" in page
        assert "params.get('ordina')" in page
        # 28992cf — la stessa pagina risponde anche su /esplora-operatori:
        # la categoria resta path segment ma sul basePath dinamico
        assert "${basePath}/${next}" in page
        assert "'/esplora-operatori'" in page
        # Dove dentro la barra, in versione fluida
        assert "<GeoSearchBar value={geoValue} onChange={setGeo} fluid />" in page
        # Distanza offerta solo con geo attivo (come il backend)
        assert '{geoValue && (' in page
        geobar = (FRONTEND_SRC / "features" / "storefront" / "components"
                  / "GeoSearchBar.jsx").read_text()
        assert "fluid = false" in geobar


class TestQuandoLM4:
    """LM4 (docs/LISTINO_MARKETPLACE_PIANO_2026-07.md) — filtro Quando
    cross-operatore su indice denormalizzato availability_index.
    INVARIANTE ASSOLUTA: l'indice serve SOLO alla ricerca; checkout e
    slot veri restano sul motore esistente (slot_generator)."""

    SERVICE = BACKEND_DIR / "services" / "availability_index_service.py"

    def _blocco_endpoint(self):
        src = (BACKEND_DIR / "routers" / "public.py").read_text()
        blocco = src.split("async def public_operators_index")[1]
        return blocco.split("async def _operator_listino")[0]

    def test_servizio_indice_riusa_il_motore_slot(self):
        """Il servizio esiste e materializza l'indice CHIAMANDO
        generate_available_slots (scope agenda, stessa chiamata di
        GET /public/services/{id}/slots) — zero regole duplicate:
        niente letture dirette di availability_rules/blocked_slots,
        niente ciclo su day_of_week."""
        src = self.SERVICE.read_text()
        assert "from services.slot_generator import generate_available_slots" in src
        assert 'scope="agenda"' in src
        assert "rebuild_for_product" in src and "rebuild_for_org" in src
        # il motore non si duplica: il servizio non rilegge le regole
        assert "availability_rules_collection" not in src
        assert "blocked_slots_collection" not in src
        assert "day_of_week" not in src

    def test_endpoint_quando_con_date_filter_ready(self):
        """/public/operators accetta date (+ time_from/to), espone
        date_filter_ready (feature flag implicito: indice vuoto → il
        frontend nasconde il campo) e next_available sugli item."""
        blocco = self._blocco_endpoint()
        assert "date_filter_ready" in blocco
        assert '"next_available"' in blocco
        assert "availability_index_collection" in blocco
        from datetime import date as _d, timedelta as _td
        domani = (_d.today() + _td(days=1)).isoformat()
        r = requests.get(f"{BASE_URL}/api/public/operators",
                         params={"date": domani}, timeout=10)
        assert r.status_code == 200
        body = r.json()
        assert "date_filter_ready" in body
        # indice vuoto → lista vuota, MAI un errore
        if not body["date_filter_ready"]:
            assert body["items"] == []
        # data malformata → 400 esplicito, non 500
        r2 = requests.get(f"{BASE_URL}/api/public/operators",
                          params={"date": "31-12-2026"}, timeout=10)
        assert r2.status_code == 400

    def test_hook_best_effort_nei_punti_di_scrittura(self):
        """Chi cambia la disponibilita' riallinea l'indice in
        background: regole/blocchi (routers/availability.py), slot
        consumato da prenotazione e rilascio (booking_availability),
        annullamento ordine (order_service). Sempre best-effort:
        import dentro try, mai nel percorso critico."""
        hook = "from services.availability_index_service import schedule_rebuild"
        av = (BACKEND_DIR / "routers" / "availability.py").read_text()
        # regole (create+delete) e blocchi (create/delete/batch/group)
        assert av.count("schedule_rebuild(") >= 6
        assert hook in av
        ba = (BACKEND_DIR / "services" / "booking_availability.py").read_text()
        assert hook in ba and "schedule_rebuild(org_id)" in ba
        osrc = (BACKEND_DIR / "services" / "order_service.py").read_text()
        assert hook in osrc
        # best-effort dichiarato: ogni import dell'hook vive dentro un
        # try (un rebuild rotto non deve MAI rompere il flusso primario)
        for src in (av, ba, osrc):
            for prima in src.split(hook)[:-1]:
                coda = "\n".join(prima.rstrip().splitlines()[-3:])
                assert "try:" in coda, "hook schedule_rebuild fuori da un try"

    def test_invariante_indice_solo_ricerca(self):
        """Il motore slot e il checkout NON sanno che l'indice esiste:
        slot_generator intoccato (nessun riferimento all'indice) e
        nessuna lettura di availability_index nei percorsi d'acquisto.
        L'unico lettore e' la ricerca /public/operators."""
        sg = (BACKEND_DIR / "services" / "slot_generator.py").read_text()
        assert "availability_index" not in sg
        for nome in ("order_creation_service.py", "product_type_validators.py",
                     "payment_checkout_service.py", "cart_service.py"):
            src = (BACKEND_DIR / "services" / nome).read_text()
            assert "availability_index" not in src, f"checkout legge l'indice: {nome}"
        # lo slot picker pubblico resta sul motore vero
        pub = (BACKEND_DIR / "routers" / "public.py").read_text()
        picker = pub.split("async def get_service_slots")[1].split("@router.get")[0]
        assert "generate_available_slots" in picker
        assert "availability_index" not in picker


class TestAnteprimaMarketplace:
    """PN (richiesta founder 29/7) — anteprima VERA del marketplace su
    rotte non linkate (/esplora-operatori, /esplora-ritiri): preview=1
    bypassa il filtro solo-campioni della fase (PL8) SOLO per quella
    risposta; il default resta identico (le guardie PL8 non cambiano)."""

    def test_preview_1_mostra_org_vere(self):
        """preview=1 → comportamento marketplace: operatori/ritiri VERI,
        mai marcati sample, identita' non redatta (PL9 non serve: i
        campioni escono dal perimetro)."""
        src = (BACKEND_DIR / "routers" / "public.py").read_text()
        op = src.split("async def public_operators_index")[1] \
                .split("async def _operator_listino")[0]
        assert "_prelaunch = prelaunch_mode() and not preview" in op
        rt = src.split("async def list_public_retreats")[1] \
                .split("def _haversine_km")[0]
        assert "if prelaunch_mode() and not preview:" in rt
        r = requests.get(f"{BASE_URL}/api/public/operators",
                         params={"preview": 1}, timeout=10)
        assert r.status_code == 200
        for it in r.json()["items"]:
            assert it["sample"] is False
            assert it["name"], "identita' redatta con preview=1"
        r2 = requests.get(f"{BASE_URL}/api/public/retreats",
                          params={"preview": 1}, timeout=10)
        assert r2.status_code == 200
        for it in r2.json()["items"]:
            assert it["sample"] is False
            assert it["org_name"], "org_name redatto con preview=1"

    def test_default_resta_campioni(self):
        """Senza preview NULLA cambia: in fase non-marketplace i listing
        mostrano solo campioni (sample=True) e le guardie PL8 restano
        scritte come prima."""
        src = (BACKEND_DIR / "routers" / "public.py").read_text()
        # le guardie PL8 esistenti (test_prelaunch_pl) restano intatte
        assert "pay_ready = set(sample_orgs)" in src
        assert "if _is_sample != _prelaunch:" in src
        cfg = requests.get(f"{BASE_URL}/api/public/site-config",
                           timeout=10).json()
        prelaunch = bool(cfg.get("prelaunch"))
        for ep in ("operators", "retreats"):
            r = requests.get(f"{BASE_URL}/api/public/{ep}", timeout=10)
            assert r.status_code == 200
            for it in r.json()["items"]:
                # fase spenta: solo campioni; marketplace: solo veri
                assert it["sample"] is prelaunch, \
                    f"default cambiato su /{ep} (fase prelaunch={prelaunch})"

    def test_rotte_esplora_presenti_e_noindex(self):
        """Le rotte /esplora-* montano le pagine marketplace in OGNI
        fase, chiedono preview=1 e si marcano noindex; nessuna voce di
        menu/footer le linka (restano raggiungibili solo via URL)."""
        app = (FRONTEND_SRC / "App.js").read_text()
        assert 'path="/esplora-ritiri"' in app
        assert 'path="/esplora-ritiri/:categoria"' in app
        assert 'path="/esplora-ritiri/:categoria/:regione"' in app
        assert 'path="/esplora-operatori"' in app
        cal = (FRONTEND_SRC / "features" / "storefront"
               / "RetreatsCalendarPage.js").read_text()
        assert "'/esplora-ritiri'" in cal
        assert "q.preview = 1" in cal
        assert "noindex: isPreview" in cal
        assert "${basePath}/${category}" in cal   # navigazione interna
        ops = (FRONTEND_SRC / "features" / "storefront"
               / "OperatorsIndexPage.js").read_text()
        assert "q.preview = 1" in ops
        assert "noindex: isPreview ||" in ops
        # nessun link di menu/footer verso le rotte anteprima
        shell = (FRONTEND_SRC / "features" / "storefront" / "components"
                 / "MarketplaceShell.jsx").read_text()
        assert "/esplora-ritiri" not in shell
        assert "/esplora-operatori" not in shell


class TestPolishLM5:
    """LM5 (docs/LISTINO_MARKETPLACE_PIANO_2026-07.md) — polish visivo
    stile Treatwell su /operatori: skeleton al posto dei flash vuoti,
    empty state onesto con il suggerimento giusto per il filtro attivo."""

    def test_skeleton_cards_durante_il_caricamento(self):
        """Il loading usa il pattern Skeleton di components/ui con la
        STESSA geometria della card (cover 16/9): niente flash vuoti
        e niente salto di layout a fetch finito."""
        page = (FRONTEND_SRC / "features" / "storefront"
                / "OperatorsIndexPage.js").read_text()
        assert "from '../../components/ui/skeleton'" in page
        assert "OperatorCardSkeleton" in page
        assert 'data-testid="operator-card-skeleton"' in page
        # la cover skeleton condivide il ratio della cover vera
        assert page.count("aspect-[16/9]") >= 2, \
            "cover della card e dello skeleton con lo stesso ratio 16/9"

    def test_empty_state_con_suggerimento(self):
        """Zero risultati = messaggio onesto + gesto suggerito legato
        al filtro attivo: togli la data, allarga il raggio, tutti i
        servizi. Mai un vuoto muto."""
        page = (FRONTEND_SRC / "features" / "storefront"
                / "OperatorsIndexPage.js").read_text()
        assert 'data-testid="operators-empty"' in page
        assert "Togli la data" in page
        assert "Allarga il raggio" in page
        # i suggerimenti sono azioni vere sui filtri, non solo testo
        assert "onClick={() => setQuando('')}" in page
        assert "setGeo({ ...geoValue, radius: 250 })" in page


class TestAccountAp0:
    """AP0 (docs/ACCOUNT_UNICO_PIANO_2026-07.md) — il signup cliente
    funziona anche con legal autogenerato (coerenza RS3): snapshot
    consensi 'autogen:v0' come gia' fanno gli ordini; il 400 resta
    SOLO se lo store non esiste; il catch del checkout dice il motivo
    vero invece del generico 'registrazione non completata'."""

    @staticmethod
    def _signup_patches(store_doc, captured_account, captured_audit):
        from unittest.mock import AsyncMock, patch

        async def _create(doc):
            captured_account.update(doc)
            return doc

        async def _record(**kw):
            captured_audit.append(kw)

        return [
            patch("services.customer_auth_service."
                  "customer_account_repository.find_by_email",
                  new=AsyncMock(return_value=None)),
            patch("services.customer_auth_service."
                  "customer_account_repository.create", new=_create),
            patch("services.customer_auth_service."
                  "_link_account_to_existing_customers", new=AsyncMock()),
            patch("database.stores_collection.find_one",
                  new=AsyncMock(return_value=store_doc)),
            patch("repositories.consent_audit_repository.record_consent",
                  new=_record),
            patch("services.customer_auth_service._load_email_context",
                  new=AsyncMock(return_value={
                      "sender_name": "", "reply_to": "", "store_name": "",
                  })),
            patch("services.customer_auth_service.resolve_slug_for_org",
                  new=AsyncMock(return_value="acme")),
            patch("services.customer_auth_service.send_customer_welcome",
                  new=lambda *a, **kw: None),
        ]

    async def test_ap0_signup_ok_con_store_autogen(self):
        """Store esistente ma legal not_configured: il signup PASSA e
        lo snapshot CG-4 e' 'autogen:v0' (stessa sentinella degli
        ordini RS3), audit con tag 'autogen' + hash 'v0'."""
        from contextlib import ExitStack
        from services import customer_auth_service

        store = {
            "id": "store-ap0", "organization_id": "org-ap0",
            "slug": "acme", "name": "Acme",
            "storefront_languages": ["it"],
            # nessun merchant_*_content → merchant_legal_status
            # = not_configured
        }
        account, audit = {}, []
        with ExitStack() as stack:
            for p in self._signup_patches(store, account, audit):
                stack.enter_context(p)
            result = await customer_auth_service.customer_signup(
                org_id="org-ap0", email="ap0@example.com", name="Ap0",
                password="StrongPass12", signup_slug="acme",
                accepted_terms=True, accepted_privacy=True,
            )

        assert result["status"] == "verification_required"
        assert account["accepted_store_terms_version"] == "autogen:v0"
        assert account["accepted_store_privacy_version"] == "autogen:v0"
        assert account["accepted_store_terms_locale"] == "it"
        assert [r["version_tag"] for r in audit] == ["autogen", "autogen"]
        assert [r["version_hash"] for r in audit] == ["v0", "v0"]

    async def test_ap0_400_solo_se_store_inesistente(self):
        """L'unico rifiuto legale rimasto: lo store NON esiste (niente
        documenti serviti, nemmeno autogenerati → nulla a cui legare
        il consenso)."""
        import pytest
        from contextlib import ExitStack
        from services import customer_auth_service

        account, audit = {}, []
        with ExitStack() as stack:
            for p in self._signup_patches(None, account, audit):
                stack.enter_context(p)
            with pytest.raises(ValueError, match="configurazione"):
                await customer_auth_service.customer_signup(
                    org_id="org-ap0", email="ap0b@example.com", name="B",
                    password="StrongPass12", signup_slug="ghost",
                    accepted_terms=True, accepted_privacy=True,
                )
        assert not account and not audit

    def test_ap0_catch_onesto_nel_checkout(self):
        """Il ramo else del catch signup mostra il motivo vero quando
        il backend fornisce `detail` (chiave i18n con {{reason}}); il
        generico resta solo come fallback. Per i corsi il flusso resta
        bloccante com'era."""
        hook = (FRONTEND_SRC / "features" / "storefront" / "hooks"
                / "useCheckoutForm.js").read_text()
        assert "signupNotCompletedReason" in hook
        assert "reason: String(detail)" in hook
        # fallback generico ancora presente per errori senza detail
        assert "storefront:errors.signupNotCompleted'" in hook
        # corsi: sempre bloccanti (return dopo il toast.error)
        assert "toast.error(detail || t('storefront:errors.signupFailed'))" in hook
        # la chiave esiste in tutte e 4 le lingue, con {{reason}}
        import json
        for lang in ("it", "en", "de", "fr"):
            data = json.loads((FRONTEND_SRC / "locales" / lang
                               / "storefront.json").read_text())
            msg = data["errors"]["signupNotCompletedReason"]
            assert "{{reason}}" in msg


class TestCheckoutAuryaAp1:
    """AP1 (docs/ACCOUNT_UNICO_PIANO_2026-07.md) — il checkout parla
    solo Aurya: la registrazione con password e' gated ai soli corsi,
    i guest vedono l'hint Passaporto, e chi ha gia' un account entra
    inline con gli endpoint passwordless della piattaforma."""

    CHECKOUT_DIR = ("features", "storefront", "components", "checkout")

    def _checkout_file(self, name):
        p = FRONTEND_SRC
        for part in self.CHECKOUT_DIR:
            p = p / part
        return (p / name).read_text()

    def test_ap1_password_gated_ai_soli_corsi(self):
        """La sezione 'crea account' con password NON e' piu' una scelta:
        appare SOLO quando il carrello contiene un corso (dove resta
        obbligatoria e invariata). R1: il codice wantRegister resta nel
        hook, la condizione e' riallargabile."""
        form = self._checkout_file("CheckoutForm.jsx")
        # gate: solo corsi (requiresCustomerAccount), mai scelta libera
        assert ("{requiresCustomerAccount && !isCustomerAuthenticated"
                " && (() => {") in form
        assert "(!mktpCheckout || requiresCustomerAccount)" not in form
        # dentro il blocco la registrazione resta forzata e invariata
        assert "checked={wantRegister || requiresCustomerAccount}" in form
        assert "disabled={!emailOk || requiresCustomerAccount}" in form
        # R1 — la logica signup del hook NON e' stata eliminata
        hook = (FRONTEND_SRC / "features" / "storefront" / "hooks"
                / "useCheckoutForm.js").read_text()
        assert "wantRegister" in hook
        assert "customerSignup({" in hook

    def test_ap1_hint_passport_per_guest(self):
        """Al posto della scelta account, i guest (senza corso) vedono
        il blocco informativo Passaporto — su OGNI superficie del
        checkout, non solo marketplace. Copy in 4 lingue, senza
        'negozio' e senza trattini lunghi."""
        form = self._checkout_file("CheckoutForm.jsx")
        assert 'data-testid="aurya-passport-hint"' in form
        assert ("{!requiresCustomerAccount && !isCustomerAuthenticated"
                " && (") in form
        import json
        for lang in ("it", "en", "de", "fr"):
            data = json.loads((FRONTEND_SRC / "locales" / lang
                               / "storefront.json").read_text())
            msg = data["checkout"]["auryaPassportHint"]
            assert "Aurya" in msg, lang
            assert "—" not in msg, lang       # niente em dash
            assert "negozio" not in msg.lower(), lang

    def test_ap1_pannello_accesso_endpoint_platform(self):
        """L'accesso rapido inline riusa ESATTAMENTE il passwordless
        della piattaforma (stessi endpoint di AccountLoginPage) e il
        token in localStorage; il profilo per il prefill arriva da
        GET /platform/me."""
        panel = self._checkout_file("AuryaQuickLogin.jsx")
        assert "'/platform/auth/magic-link'" in panel
        assert "'/platform/auth/code/verify'" in panel
        assert "'/platform/me'" in panel
        assert "PLATFORM_TOKEN_KEY" in panel
        # montato nel form del checkout, solo per i guest
        form = self._checkout_file("CheckoutForm.jsx")
        assert "AuryaQuickLogin" in form
        assert "{!isCustomerAuthenticated && (\n                  <AuryaQuickLogin" in form


class TestHubAccountAp2:
    """AP2 (docs/ACCOUNT_UNICO_PIANO_2026-07.md, adattata) — l'hub
    /account racconta lo stato vero di richieste e ritiri e apre le
    guide della lettera di Aurya agli iscritti confermati."""

    def test_ap2_orders_espongono_stato_e_slot(self):
        """La proiezione /platform/me/orders porta status +
        transaction_mode dominante + l'appuntamento scelto al checkout
        servizi (service_slot dai booking_* della riga) e NON nasconde
        piu' gli ordini annullati (badge 'Annullato')."""
        src = (BACKEND_DIR / "routers" / "platform_accounts.py").read_text()
        assert '"items.booking_date": 1' in src
        assert '"items.transaction_mode": 1' in src
        assert '"service_slot"' in src
        assert '"transaction_mode": (modes.pop() if len(modes) == 1' in src
        # gli annullati ora si vedono (prima erano filtrati via)
        assert '{"$ne": "cancelled"}' not in src

    def test_ap2_login_emette_token_newsletter_solo_confirmed(self):
        """Il login Passaporto (magic link E codice) risponde con
        newsletter_subscriber e, SOLO per iscrizioni aurya_subscribers
        confermate, col subscriber_token (riuso core/subscriber_token,
        la stessa chiave che sblocca le guide BN3)."""
        svc = (BACKEND_DIR / "services"
               / "platform_account_service.py").read_text()
        assert "async def newsletter_status" in svc
        assert 'doc.get("status") == "confirmed"' in svc
        assert "generate_subscriber_token" in svc
        # il token si firma DENTRO il ramo confirmed, mai fuori
        confirmed_branch = svc.split('doc.get("status") == "confirmed"')[1]
        assert "generate_subscriber_token" in confirmed_branch
        router = (BACKEND_DIR / "routers" / "platform_accounts.py").read_text()
        # TUTTE le strade di login arricchiscono la risposta (magic link,
        # OTP e — da AP1b — anche il login password)
        assert router.count("**await newsletter_status(account[\"email\"])") == 3
        # /platform/me espone il booleano per il render (senza token)
        assert "with_token=False" in router

    def test_ap2_sezione_guide_frontend(self):
        """/account ha la sezione Guide e materiale: lista delle guide
        riservate (endpoint pubblico del blog) per gli iscritti, invito
        a /newsletter per gli altri; i login salvano aurya_nl_token
        solo se il backend lo ha emesso. Copy in 4 lingue, senza
        trattini lunghi e senza 'negozio'."""
        page = (FRONTEND_SRC / "features" / "account"
                / "AccountPage.js").read_text()
        assert 'data-testid="account-guides"' in page
        assert "newsletter_subscriber" in page
        assert "'/public/articles'" in page
        assert 'to="/newsletter"' in page
        assert ".filter(a => a.gated)" in page
        login = (FRONTEND_SRC / "features" / "account"
                 / "AccountLoginPage.js").read_text()
        assert "aurya_nl_token" in login
        assert "subscriber_token" in login
        quick = (FRONTEND_SRC / "features" / "storefront" / "components"
                 / "checkout" / "AuryaQuickLogin.jsx").read_text()
        assert "aurya_nl_token" in quick
        import json
        for lang in ("it", "en", "de", "fr"):
            data = json.loads((FRONTEND_SRC / "locales" / lang
                               / "landings.json").read_text())
            acc = data["account"]
            for key in ("statusRequestSent", "statusConfirmed",
                        "statusCompleted", "statusCancelled",
                        "appointment", "guidesTitle", "guidesInvite",
                        "guidesCta"):
                msg = acc[key]
                assert "—" not in msg, (lang, key)
                assert "negozio" not in msg.lower(), (lang, key)


class TestAccountAp1b:
    """AP1b (docs/ACCOUNT_UNICO_PIANO_2026-07.md, revisione founder) —
    email+password sull'account Aurya: signup con verifica email,
    login password con lockout, reset che vale anche come "imposta
    password" per gli account nati passwordless. Il passwordless resta
    identico come alternativa."""

    PASSWORD = "StrongPass12"

    class _MemAccounts:
        """platform_accounts in memoria: il minimo che serve al service
        (find_one per uguaglianza, insert_one, update_one con $set)."""

        def __init__(self):
            self.docs = {}

        async def find_one(self, q, proj=None):
            for d in self.docs.values():
                if all(d.get(k) == v for k, v in q.items()):
                    return dict(d)
            return None

        async def insert_one(self, doc):
            self.docs[doc["id"]] = dict(doc)

        async def update_one(self, q, u):
            for d in self.docs.values():
                if all(d.get(k) == v for k, v in q.items()):
                    for k, v in u.get("$set", {}).items():
                        d[k] = v
                    return

    def _ctx(self, fake, sent):
        """Patch comuni: collection in memoria, email catturate (il token
        in chiaro viaggia SOLO li'), claim e rate-limit neutralizzati."""
        from unittest.mock import AsyncMock, patch
        from services import platform_account_service as svc

        return [
            patch("database.platform_accounts_collection", fake),
            patch.object(svc, "_send_verify_email",
                         lambda e, t, n, locale="it": sent.update(
                             {"verify_email": e, "verify_token": t})),
            patch.object(svc, "_send_reset_email",
                         lambda e, t, n, locale="it": sent.update(
                             {"reset_email": e, "reset_token": t})),
            patch.object(svc, "retroactive_claim", AsyncMock()),
            patch("core.rate_limiting.check_email_rate",
                  new=lambda *a, **kw: True),
        ]

    async def test_ap1b_signup_verifica_login_felice(self):
        """Signup → email di verifica (token in chiaro solo li', a DB
        l'hash) → verify → login password: sessione e contatori ok."""
        from contextlib import ExitStack
        from services import platform_account_service as svc

        fake, sent = self._MemAccounts(), {}
        with ExitStack() as stack:
            for p in self._ctx(fake, sent):
                stack.enter_context(p)

            out = await svc.password_signup(
                name="Anna", email="Anna@Ap1b.it", password=self.PASSWORD)
            assert out == {"status": "verification_required"}
            acc = list(fake.docs.values())[0]
            assert acc["email"] == "anna@ap1b.it"          # normalizzata
            assert acc["email_verified"] is False
            assert acc["password_hash"].startswith("$2")   # bcrypt
            token = sent["verify_token"]
            assert token and token not in str(acc)         # MAI in chiaro a DB
            assert acc["verification_token_hash"] == svc._hash_token(token)

            out = await svc.verify_signup_email(token)
            assert out == {"status": "verified"}
            acc = list(fake.docs.values())[0]
            assert acc["email_verified"] is True
            assert acc["verification_token_hash"] is None  # one-shot

            logged = await svc.password_login("anna@ap1b.it", self.PASSWORD)
            assert logged["id"] == acc["id"]
            assert logged["last_login_at"]
            assert logged["failed_login_attempts"] == 0

    async def test_ap1b_login_prima_della_verifica_rifiutato(self):
        """Password giusta ma email non verificata: EMAIL_NOT_VERIFIED
        (il router lo traduce in 403). Prima della password giusta,
        invece, SOLO 401 generico: niente enumeration."""
        import pytest
        from contextlib import ExitStack
        from services import platform_account_service as svc

        fake, sent = self._MemAccounts(), {}
        with ExitStack() as stack:
            for p in self._ctx(fake, sent):
                stack.enter_context(p)
            await svc.password_signup(
                name="B", email="b@ap1b.it", password=self.PASSWORD)
            with pytest.raises(ValueError, match="EMAIL_NOT_VERIFIED"):
                await svc.password_login("b@ap1b.it", self.PASSWORD)
            # password sbagliata su account non verificato: 401 generico,
            # mai lo stato dell'account
            with pytest.raises(ValueError, match="INVALID_CREDENTIALS"):
                await svc.password_login("b@ap1b.it", "WrongPass1234")

    async def test_ap1b_email_gia_registrata_409(self):
        """Account gia' verificato (o con password) → EMAIL_EXISTS, che
        il router mappa su un 409 onesto. ECCEZIONE voluta: il guscio
        passwordless pending nato da un acquisto guest viene ADOTTATO
        dal signup (la proprieta' resta provata dal link di verifica)."""
        import pytest
        from contextlib import ExitStack
        from services import platform_account_service as svc

        fake, sent = self._MemAccounts(), {}
        with ExitStack() as stack:
            for p in self._ctx(fake, sent):
                stack.enter_context(p)
            await svc.password_signup(
                name="C", email="c@ap1b.it", password=self.PASSWORD)
            await svc.verify_signup_email(sent["verify_token"])
            with pytest.raises(ValueError, match="EMAIL_EXISTS"):
                await svc.password_signup(
                    name="C2", email="C@AP1B.IT", password=self.PASSWORD)

            # guscio pending (claim acquisto): il signup lo adotta
            fake.docs["shell-1"] = {"id": "shell-1", "email": "guest@ap1b.it",
                                    "email_verified": False,
                                    "password_hash": None}
            out = await svc.password_signup(
                name="Guest", email="guest@ap1b.it", password=self.PASSWORD)
            assert out == {"status": "verification_required"}
            shell = fake.docs["shell-1"]
            assert shell["password_hash"].startswith("$2")
            assert shell["email_verified"] is False        # verifica ancora dovuta

        # il router mappa EMAIL_EXISTS su 409
        router = (BACKEND_DIR / "routers" / "platform_accounts.py").read_text()
        block = router.split('"/auth/signup"')[1]
        assert "HTTP_409_CONFLICT" in block.split("@router.post")[0]

    async def test_ap1b_lockout_dopo_n_tentativi(self):
        """Stesse soglie dei customer (core/security_config): dopo
        LOCKOUT_THRESHOLD password sbagliate l'account si blocca e
        ANCHE la password giusta risponde ACCOUNT_LOCKED (recupero via
        reset)."""
        import pytest
        from contextlib import ExitStack
        from core.security_config import LOCKOUT_ERROR_CODE, LOCKOUT_THRESHOLD
        from services import platform_account_service as svc

        fake, sent = self._MemAccounts(), {}
        with ExitStack() as stack:
            for p in self._ctx(fake, sent):
                stack.enter_context(p)
            await svc.password_signup(
                name="D", email="d@ap1b.it", password=self.PASSWORD)
            await svc.verify_signup_email(sent["verify_token"])

            for _ in range(LOCKOUT_THRESHOLD):
                with pytest.raises(ValueError, match="INVALID_CREDENTIALS"):
                    await svc.password_login("d@ap1b.it", "WrongPass1234")

            acc = list(fake.docs.values())[0]
            assert acc["locked_until"]                     # lockout scattato
            with pytest.raises(ValueError,
                               match=f"^{LOCKOUT_ERROR_CODE}:"):
                await svc.password_login("d@ap1b.it", self.PASSWORD)

    async def test_ap1b_reset_imposta_password_su_passwordless(self):
        """Il reset e' anche il flusso "imposta la password" per gli
        account nati passwordless (claim acquisto): password_hash None →
        scritto; il link usato prova la casella → email_verified True;
        token one-shot."""
        import pytest
        from contextlib import ExitStack
        from services import platform_account_service as svc

        fake, sent = self._MemAccounts(), {}
        fake.docs["pl-1"] = {"id": "pl-1", "email": "senza@ap1b.it",
                             "email_verified": False, "password_hash": None,
                             "language": "it"}
        with ExitStack() as stack:
            for p in self._ctx(fake, sent):
                stack.enter_context(p)
            await svc.request_password_reset("senza@ap1b.it")
            token = sent["reset_token"]
            assert token not in str(fake.docs["pl-1"])     # a DB solo l'hash

            out = await svc.confirm_password_reset(token, self.PASSWORD)
            assert out == {"status": "ok"}
            acc = fake.docs["pl-1"]
            assert acc["password_hash"].startswith("$2")
            assert acc["email_verified"] is True           # casella provata
            assert acc["reset_token_hash"] is None         # one-shot

            logged = await svc.password_login("senza@ap1b.it", self.PASSWORD)
            assert logged["id"] == "pl-1"

            # secondo uso dello stesso token: rifiutato
            with pytest.raises(ValueError, match="INVALID_TOKEN"):
                await svc.confirm_password_reset(token, self.PASSWORD)

    async def test_ap1b_reset_request_neutra_se_email_ignota(self):
        """Nessun account per l'email → nessuna email inviata, nessun
        errore: il router risponde comunque 200 (enumeration-safe)."""
        from contextlib import ExitStack
        from services import platform_account_service as svc

        fake, sent = self._MemAccounts(), {}
        with ExitStack() as stack:
            for p in self._ctx(fake, sent):
                stack.enter_context(p)
            await svc.request_password_reset("ignota@ap1b.it")
        assert "reset_token" not in sent

    def test_ap1b_risposta_login_password_con_newsletter(self):
        """La risposta del login password ha lo STESSO shape delle altre
        strade: access_token + account + newsletter_status AP2 (le guide
        si sbloccano anche col login password)."""
        router = (BACKEND_DIR / "routers" / "platform_accounts.py").read_text()
        block = router.split('"/auth/login"')[1].split("@router.post")[0]
        assert "_login_response(account)" in block
        assert '**await newsletter_status(account["email"])' in block
        # errori: 423 lockout, 403 non verificata, 401 generico
        assert "HTTP_423_LOCKED" in block
        assert "HTTP_403_FORBIDDEN" in block
        assert "HTTP_401_UNAUTHORIZED" in block

    def test_ap1b_frontend_percorsi_e_copy(self):
        """AccountLoginPage: password primaria + link secondari (OTP e
        reset) + signup; pagine verify/nuova-password instradate; il
        checkout inline ha il toggle password. Copy x4 lingue: mai
        'Passaporto', mai trattini lunghi."""
        login = (FRONTEND_SRC / "features" / "account"
                 / "AccountLoginPage.js").read_text()
        assert "'/platform/auth/login'" in login
        assert "'/platform/auth/signup'" in login
        assert "'/platform/auth/password-reset'" in login
        assert 'data-testid="login-no-password"' in login
        assert 'data-testid="login-forgot"' in login
        assert 'data-testid="login-to-signup"' in login

        verify = (FRONTEND_SRC / "features" / "account"
                  / "AccountVerifyEmailPage.js").read_text()
        assert "'/platform/auth/verify-email'" in verify
        reset = (FRONTEND_SRC / "features" / "account"
                 / "AccountResetPasswordPage.js").read_text()
        assert "'/platform/auth/password-reset/confirm'" in reset

        app = (FRONTEND_SRC / "App.js").read_text()
        assert 'path="/account/verifica"' in app
        assert 'path="/account/nuova-password"' in app

        quick = (FRONTEND_SRC / "features" / "storefront" / "components"
                 / "checkout" / "AuryaQuickLogin.jsx").read_text()
        assert "'/platform/auth/login'" in quick
        assert 'data-testid="aurya-login-have-password"' in quick
        assert "PLATFORM_TOKEN_KEY" in quick

        import json
        new_account_keys = (
            "passwordLoginBody", "passwordPlaceholder", "otpLink",
            "forgotLink", "signupLink", "signupTitle", "signupSentBody",
            "signupExists", "resetTitle", "resetBody", "resetSentBody",
            "passwordHint", "verifyOkBody", "verifyFailBody",
            "newPasswordTitle", "newPasswordOkBody", "newPasswordFailBody",
            "goToLogin", "backToLogin",
        )
        for lang in ("it", "en", "de", "fr"):
            acc = json.loads((FRONTEND_SRC / "locales" / lang
                              / "landings.json").read_text())["account"]
            for key in new_account_keys:
                msg = acc[key]
                assert "—" not in msg, (lang, key)         # niente em dash
                assert "assaporto" not in msg, (lang, key)  # mai Passaporto
            store = json.loads((FRONTEND_SRC / "locales" / lang
                                / "storefront.json").read_text())
            aq = store["checkout"]["auryaLogin"]
            for key in ("havePassword", "passwordHint", "passwordPlaceholder",
                        "noPassword", "passwordError", "passwordNotVerified",
                        "passwordLocked"):
                msg = aq[key]
                assert "—" not in msg, (lang, key)
                assert "assaporto" not in msg, (lang, key)

    def test_ap1b_email_transazionali_x4(self):
        """Le email di verifica e reset esistono nelle 4 lingue, dentro
        lo stesso sistema template (EMAIL_TRANSLATIONS + _wrap_template),
        senza la parola Passaporto nei testi nuovi."""
        from services.email_service import EMAIL_TRANSLATIONS

        keys = ("aurya_verify_subject", "aurya_verify_body",
                "aurya_verify_cta", "aurya_verify_footer",
                "aurya_reset_subject", "aurya_reset_body",
                "aurya_reset_cta", "aurya_reset_footer")
        for lang in ("it", "en", "de", "fr"):
            for key in keys:
                msg = EMAIL_TRANSLATIONS[lang][key]
                assert msg, (lang, key)
                assert "—" not in msg, (lang, key)
                assert "assaporto" not in msg, (lang, key)
        svc_src = (BACKEND_DIR / "services"
                   / "platform_account_service.py").read_text()
        assert "_wrap_template" in svc_src.split("def _send_verify_email")[1]
        assert "/account/verifica?token=" in svc_src
        assert "/account/nuova-password?token=" in svc_src


class TestAccountApL:
    """AP-L (docs/ACCOUNT_UNICO_PIANO_2026-07.md, revisione founder) —
    legal a due livelli gestito da Aurya: consenso Aurya timbrato
    sull'account alla creazione (aurya_legal + audit immutabile),
    checkout con atto primario Aurya (guest checkbox / loggato coperto
    dall'account) e checkbox DINAMICA delle condizioni dell'operatore
    solo se compilate; l'ordine timbra lo snapshot di TUTTO."""

    PASSWORD = "StrongPass12"

    # ── infrastruttura live (stesso server dei test RS/PN/LM) ────────

    _admin_token_cache = None

    @classmethod
    def _admin_headers(cls):
        import pytest
        if cls._admin_token_cache:
            return {"Authorization": f"Bearer {cls._admin_token_cache}"}
        r = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@demo.com", "password": "demo1234"}, timeout=10)
        if r.status_code != 200:
            pytest.skip("demo login unavailable (rate limit?)")
        cls._admin_token_cache = r.json()["access_token"]
        return {"Authorization": f"Bearer {cls._admin_token_cache}"}

    @staticmethod
    def _db():
        """DB del server live (backend/.env), NON il test_db di default."""
        import re
        import pymongo
        env = (BACKEND_DIR / ".env").read_text()
        mongo = re.search(r'MONGO_URL="?([^"\n]+?)"?\n', env).group(1)
        name = re.search(r'DB_NAME="?([^"\n]+?)"?\n', env).group(1)
        return pymongo.MongoClient(mongo)[name]

    @classmethod
    def _cleanup_email(cls, email):
        """Ripulisce TUTTE le tracce dei dati di guardia per email."""
        db = cls._db()
        email = email.lower()
        pa_ids = [a["id"] for a in
                  db.platform_accounts.find({"email": email}, {"id": 1})]
        cust_ids = [c["id"] for c in
                    db.customers.find({"email": email}, {"id": 1})]
        db.orders.delete_many({"$or": [
            {"customer_id": {"$in": cust_ids}},
            {"platform_account_id": {"$in": pa_ids}},
        ]})
        db.customers.delete_many({"email": email})
        db.customer_accounts.delete_many({"email": email})
        db.platform_magic_tokens.delete_many({"account_id": {"$in": pa_ids}})
        db.platform_accounts.delete_many({"email": email})
        db.consent_audit.delete_many({"customer_email": email})

    def _make_service(self, headers, name, metadata=None):
        r = requests.post(f"{BASE_URL}/api/products", headers=headers, json={
            "name": name, "item_type": "service",
            "transaction_mode": "request", "is_published": True,
            "unit_price": 30, "price_mode": "fixed",
            "metadata": metadata or {},
        }, timeout=10)
        assert r.status_code in (200, 201), r.text
        return r.json()

    def _delete_product(self, headers, product_id):
        requests.delete(f"{BASE_URL}/api/products/{product_id}",
                        headers=headers, timeout=10)
        # l'API fa soft-delete (is_active=False): il doc di guardia si
        # rimuove del tutto, cosi' i run ripetuti non accumulano residui
        try:
            self._db().products.delete_one({"id": product_id})
        except Exception:
            pass

    # ── 1. signup con consenso timbrato + audit (unit, in memoria) ───

    async def test_apl_signup_consenso_timbrato_e_audit(self):
        """password_signup con accepted_terms=True timbra aurya_legal
        (versioni correnti, source signup) sull'account e scrive
        l'audit immutabile (privacy_terms, platform_signup). Senza
        accepted_terms (chiamanti legacy): nessun timbro, nessun
        audit — il router pero' rende la spunta obbligatoria (400)."""
        from contextlib import ExitStack
        from unittest.mock import patch

        from core.legal_versions import (CURRENT_VERSION_TAG,
                                         current_version_string)
        from services import platform_account_service as svc

        # riuso dell'infrastruttura in-memory di AP1b (stesso modulo)
        Ap1b = TestAccountAp1b
        fake, sent, audit = Ap1b._MemAccounts(), {}, []

        async def _record(**kw):
            audit.append(kw)

        with ExitStack() as stack:
            for p in Ap1b()._ctx(fake, sent):
                stack.enter_context(p)
            stack.enter_context(
                patch("repositories.consent_audit_repository.record_consent",
                      new=_record))

            out = await svc.password_signup(
                name="Apl", email="apl-signup@example.com",
                password=self.PASSWORD, language="it",
                accepted_terms=True, request_ip="10.0.0.1",
                user_agent="guardia-apl")
            assert out == {"status": "verification_required"}
            acc = list(fake.docs.values())[0]
            legal = acc["aurya_legal"]
            assert legal["terms_version"] == current_version_string()
            assert legal["privacy_version"] == current_version_string()
            assert legal["source"] == "signup"
            assert legal["locale"] == "it"
            assert legal["accepted_at"]
            assert len(audit) == 1
            rec = audit[0]
            assert rec["document_type"] == "privacy_terms"
            assert rec["source"] == "platform_signup"
            assert rec["version_tag"] == CURRENT_VERSION_TAG
            assert rec["user_id"] == acc["id"]
            assert rec["customer_email"] == "apl-signup@example.com"
            assert rec["ip_address"] == "10.0.0.1"

            # chiamante legacy senza consenso: nessun timbro, nessun audit
            await svc.password_signup(
                name="NoLegal", email="apl-nolegal@example.com",
                password=self.PASSWORD)
            acc2 = [d for d in fake.docs.values()
                    if d["email"] == "apl-nolegal@example.com"][0]
            assert "aurya_legal" not in acc2
            assert len(audit) == 1

        # il router impone la checkbox: 400 senza accepted_terms, e
        # inoltra accepted_terms=True + ip/ua al service
        router = (BACKEND_DIR / "routers" / "platform_accounts.py").read_text()
        block = router.split('"/auth/signup"')[1].split("@router.post")[0]
        assert "accepted_terms" in block
        assert "HTTP_400_BAD_REQUEST" in block
        assert "accepted_terms=True" in block

    # ── 2. ordine GUEST: snapshot Aurya + operatore sull'ordine ──────

    def test_apl_ordine_guest_snapshot_aurya_e_operatore(self):
        """Ordine guest con checkbox Aurya spuntata e condizioni
        dell'operatore accettate: l'ordine timbra aurya_* (versioni
        correnti, source checkout), terms_content_snapshot (RS3
        esteso) e i gdpr_* merchant; l'account piattaforma nato
        dall'acquisto porta aurya_legal (source checkout) e l'audit
        immutabile ha il record platform_checkout con order_id."""
        from core.legal_versions import current_version_string

        email = "apl-guest@example.com"
        headers = self._admin_headers()
        self._cleanup_email(email)
        prod = self._make_service(
            headers, "Guardia AP-L guest",
            metadata={"terms_content": "Requisiti guardia AP-L: nessuna "
                                       "controindicazione medica."})
        try:
            r = requests.post(f"{BASE_URL}/api/public/order-request", json={
                "slug": "masseria-demo",
                "customer_name": "Guardia Apl",
                "customer_email": email,
                "items": [{"product_id": prod["id"], "quantity": 1}],
                "terms_accepted": True,
                "gdpr_terms_accepted": True,
                "gdpr_privacy_accepted": True,
                "gdpr_marketing_accepted": False,
                "aurya_terms_accepted": True,
                "locale": "it",
                "channel": "store",
            }, timeout=15)
            assert r.status_code == 200, r.text
            order_id = r.json()["order_id"]

            db = self._db()
            order = db.orders.find_one({"id": order_id})
            assert order["aurya_terms_version"] == current_version_string()
            assert order["aurya_privacy_version"] == current_version_string()
            assert order["aurya_source"] == "checkout"
            assert order["aurya_locale"] == "it"
            assert order["aurya_accepted_at"]
            # RS3 esteso: i requisiti accettati restano timbrati
            assert "controindicazione" in order["terms_content_snapshot"]
            assert order["terms_accepted_at"]
            # macchina merchant CG-5 intatta (autogen fallback)
            assert order["gdpr_terms_version"]

            account = db.platform_accounts.find_one({"email": email})
            assert account and account.get("aurya_legal")
            assert account["aurya_legal"]["source"] == "checkout"
            assert (account["aurya_legal"]["terms_version"]
                    == current_version_string())

            recs = list(db.consent_audit.find(
                {"customer_email": email, "source": "platform_checkout"}))
            assert len(recs) == 1
            assert recs[0]["order_id"] == order_id
            assert recs[0]["document_type"] == "privacy_terms"
        finally:
            self._delete_product(headers, prod["id"])
            self._cleanup_email(email)

    # ── 3. ordine da LOGGATO: niente ri-accettazione Aurya ───────────

    def test_apl_ordine_loggato_snapshot_da_account(self):
        """Compratore con account Aurya e consenso gia' timbrato: ordina
        SENZA flag aurya/gdpr (la checkbox non compare) accettando solo
        le condizioni dell'operatore: l'ordine eredita lo snapshot
        aurya_* dall'account (source account, stesso accepted_at) e
        NESSUN nuovo audit platform_checkout viene scritto."""
        import uuid
        from datetime import datetime, timezone

        from core.legal_versions import current_version_string

        email = "apl-logged@example.com"
        headers = self._admin_headers()
        self._cleanup_email(email)
        accepted_at = datetime.now(timezone.utc).isoformat()
        db = self._db()
        db.platform_accounts.insert_one({
            "id": str(uuid.uuid4()), "email": email, "name": "Apl Loggata",
            "language": "it", "email_verified": True, "is_active": True,
            "failed_login_attempts": 0, "lockout_count_today": 0,
            "created_at": accepted_at,
            "aurya_legal": {
                "terms_version": current_version_string(),
                "privacy_version": current_version_string(),
                "accepted_at": accepted_at,
                "source": "signup", "locale": "it",
            },
        })
        prod = self._make_service(
            headers, "Guardia AP-L loggato",
            metadata={"terms_content": "Condizioni operatore guardia."})
        try:
            r = requests.post(f"{BASE_URL}/api/public/order-request", json={
                "slug": "masseria-demo",
                "customer_name": "Apl Loggata",
                "customer_email": email,
                "items": [{"product_id": prod["id"], "quantity": 1}],
                "terms_accepted": True,          # condizioni operatore: si'
                "gdpr_terms_accepted": False,    # niente checkbox Aurya
                "gdpr_privacy_accepted": False,
                "aurya_terms_accepted": False,
                "locale": "it",
                "channel": "store",
            }, timeout=15)
            assert r.status_code == 200, r.text
            order = db.orders.find_one({"id": r.json()["order_id"]})
            assert order["aurya_source"] == "account"
            assert order["aurya_accepted_at"] == accepted_at
            assert order["aurya_terms_version"] == current_version_string()
            assert "operatore" in order["terms_content_snapshot"]
            # nessun nuovo audit piattaforma: il record vive dal signup
            assert db.consent_audit.count_documents(
                {"customer_email": email, "source": "platform_checkout"}) == 0
        finally:
            self._delete_product(headers, prod["id"])
            self._cleanup_email(email)

    # ── 4. senza condizioni operatore: nessuna checkbox, nessun gate ─

    def test_apl_senza_condizioni_niente_checkbox_operatore(self):
        """Servizio SENZA terms_content ne' policy: il catalogo pubblico
        espone terms_content nullo (la checkbox dinamica non esiste) e
        l'ordine passa senza terms_accepted, senza snapshot condizioni."""
        email = "apl-nocond@example.com"
        headers = self._admin_headers()
        self._cleanup_email(email)
        prod = self._make_service(headers, "Guardia AP-L senza condizioni")
        try:
            cat = requests.get(
                f"{BASE_URL}/api/public/catalog/masseria-demo",
                timeout=10).json()
            entry = next(p for p in cat["products"] if p["id"] == prod["id"])
            assert not entry.get("terms_content")
            assert not (entry.get("payment_plan") or {}).get(
                "cancellation_policy")

            r = requests.post(f"{BASE_URL}/api/public/order-request", json={
                "slug": "masseria-demo",
                "customer_name": "Apl NoCond",
                "customer_email": email,
                "items": [{"product_id": prod["id"], "quantity": 1}],
                "terms_accepted": False,
                "gdpr_terms_accepted": True,
                "gdpr_privacy_accepted": True,
                "aurya_terms_accepted": True,
                "locale": "it",
                "channel": "store",
            }, timeout=15)
            assert r.status_code == 200, r.text
            order = self._db().orders.find_one({"id": r.json()["order_id"]})
            assert "terms_content_snapshot" not in order
            assert order["aurya_source"] == "checkout"   # livello Aurya c'e'
        finally:
            self._delete_product(headers, prod["id"])
            self._cleanup_email(email)

        # frontend: la checkbox operatore e' gated dalle condizioni reali
        sf_dir = FRONTEND_SRC / "features" / "storefront"
        form = (sf_dir / "components" / "checkout"
                / "CheckoutForm.jsx").read_text()
        assert "{hasOperatorConditions && (" in form
        assert 'data-testid="operator-terms-checkbox"' in form
        hook = (sf_dir / "hooks" / "useCheckoutForm.js").read_text()
        assert ("const hasOperatorConditions = "
                "!!(effectiveTerms || cartCancellationPolicy)") in hook

    # ── 5. i requisiti dal listino arrivano al checkout ──────────────

    def test_apl_requisiti_dal_listino_al_checkout(self):
        """Il campo promosso nel listino (metadata.terms_content) esce
        risolto sul catalogo pubblico che alimenta il checkout
        condiviso (F4/terms_resolver): stessa strada del wizard."""
        headers = self._admin_headers()
        prod = self._make_service(headers, "Guardia AP-L listino")
        try:
            # stesso salvataggio della riga listino: merge del metadata
            r = requests.patch(
                f"{BASE_URL}/api/products/{prod['id']}", headers=headers,
                json={"metadata": {**(prod.get("metadata") or {}),
                                   "terms_content": "Requisiti dal listino."}},
                timeout=10)
            assert r.status_code == 200, r.text
            cat = requests.get(
                f"{BASE_URL}/api/public/catalog/masseria-demo",
                timeout=10).json()
            entry = next(p for p in cat["products"] if p["id"] == prod["id"])
            assert entry["terms_content"] == "Requisiti dal listino."
        finally:
            self._delete_product(headers, prod["id"])

        # superfici admin: textarea nel listino e nel passo Regole del
        # wizard ritiro (non piu' sepolta nel passo publish)
        listino = (FRONTEND_SRC / "features" / "listino"
                   / "ListinoPage.js").read_text()
        assert 'data-testid="listino-requisiti"' in listino
        assert "terms_content: edit.termsContent?.trim() || null" in listino
        assert "Requisiti e condizioni del servizio" in listino
        wiz = (FRONTEND_SRC / "features" / "events"
               / "EventWizard.js").read_text()
        assert 'data-testid="wizard-requisiti"' in wiz
        assert "wizards.event.regole.requisitiTitle" in wiz
        assert "wizards.event.publish.termsTitle')" not in wiz

    # ── 6. cablaggio a due livelli del checkout condiviso ────────────

    def test_apl_checkout_due_livelli_frontend(self):
        """CheckoutForm: checkbox Aurya per i guest (link /termini e
        /privacy), riga discreta per i loggati piattaforma, payload col
        flag aurya_terms_accepted; il merchant legal in Impostazioni e'
        ridimensionato a 'Condizioni dell'operatore' (custom = opzione
        avanzata, dialog esistente NON rimosso)."""
        sf_dir = FRONTEND_SRC / "features" / "storefront"
        form = (sf_dir / "components" / "checkout"
                / "CheckoutForm.jsx").read_text()
        assert 'data-testid="aurya-terms-checkbox"' in form
        assert 'data-testid="aurya-terms-already"' in form
        assert 'href="/termini"' in form and 'href="/privacy"' in form
        assert "{platformLoggedIn ? (" in form
        # niente doppia coppia di checkbox merchant: l'atto primario e' Aurya
        assert "checked={gdprPrivacyAccepted}" not in form
        assert "checked={gdprTermsAccepted}" not in form

        hook = (sf_dir / "hooks" / "useCheckoutForm.js").read_text()
        assert "payload.aurya_terms_accepted = !!auryaAccepted" in hook
        assert "PLATFORM_TOKEN_KEY" in hook
        assert "setAuryaConsent" in hook
        # loggato Aurya: gdprValid senza checkbox
        assert "|| platformLoggedIn" in hook

        # signup Aurya: riga consenso con link, obbligatoria
        login = (FRONTEND_SRC / "features" / "account"
                 / "AccountLoginPage.js").read_text()
        assert 'data-testid="signup-consent"' in login
        assert "accepted_terms: !!signupConsent" in login

        card = (FRONTEND_SRC / "features" / "settings" / "sections"
                / "SalesConditionsCard.jsx").read_text()
        assert "Condizioni dell'operatore" in card
        # PS5: l'editor legale custom e' congelato fuori dal mondo
        # snello (vive solo in /stores e /newsletter-forms); al suo
        # posto il mini-form titolare (vedi TestPotaturaPs5)
        assert 'data-testid="owner-data-form"' in card
        assert 'data-testid="service-requirements-hint"' in card

    # ── 7. testi Aurya estesi (bozza) + versioning coerente ──────────

    def test_apl_testi_aurya_v23_bozza_marcata(self):
        """I testi x4 lingue hanno le sezioni nuove (due livelli, art.
        28), il marcatore bozza vive SOLO come commento nei sorgenti e
        NON arriva all'utente finale; la versione corrente e' v2.3 e
        l'hash corrisponde al bundle IT su disco."""
        import hashlib

        from core.legal_versions import (CURRENT_VERSION_HASH,
                                         CURRENT_VERSION_TAG,
                                         get_legal_document)

        legal_dir = BACKEND_DIR / "legal"
        for lang in ("it", "en", "de", "fr"):
            for doc in ("privacy", "terms"):
                src = (legal_dir / f"{doc}_{lang}.md").read_text()
                assert "BOZZA IN ATTESA DI REVISIONE LEGALE" in src, (doc, lang)
                served = get_legal_document(doc, lang)["content"]
                assert "BOZZA" not in served, (doc, lang)
                assert "<!--" not in served, (doc, lang)
            # sezioni nuove servite (marker per lingua)
            assert "2.3" in get_legal_document("privacy", lang)["content"]

        assert CURRENT_VERSION_TAG == "v2.3"
        priv = (legal_dir / "privacy_it.md").read_text()
        terms = (legal_dir / "terms_it.md").read_text()
        digest = hashlib.sha256(
            (priv + "\n\n--- TERMS BUNDLE ---\n\n" + terms).encode()
        ).hexdigest()[:16]
        assert digest == CURRENT_VERSION_HASH

        # l'audit accetta le nuove source piattaforma
        from repositories.consent_audit_repository import _VALID_SOURCES
        assert "platform_signup" in _VALID_SOURCES
        assert "platform_checkout" in _VALID_SOURCES


class TestAccountAp4:
    """AP4 (docs/ACCOUNT_UNICO_PIANO_2026-07.md, revisione founder) —
    il concetto 'Passaporto' e' eliminato dall'esperienza utente:
    l'account e' uno, classico, 'il tuo account Aurya'. Queste guardie
    scansionano i VALORI (le stringhe che l'utente legge) e diventano
    rosse se il vecchio nome ricompare in una qualsiasi lingua.

    Esclusioni motivate:
    - NOMI INTERNI (chiavi i18n 'auryaPassportHint'/'passportLink'/
      'activatePassport', chiavi email 'passport_*', testid
      'aurya-passport-hint', commenti): rinominarli costerebbe
      regressioni su guardie e template senza alcun effetto visibile.
      Si scansionano solo i valori, mai le chiavi.
    - backend/legal/*.md: i testi legali definiscono ancora l'account
      'Passaporto Ritiri' e sono blindati dall'hash consensi v2.3
      (test_consent_version_bumped_and_hash_matches_files): la loro
      riscrittura passa dal legale con bump versione + re-consent
      (AP-L / pre-lancio), non da un copy pass.
    """

    import re as _re
    # copre Passaporto/Passaporti (it), Passport (en/de), Passeport (fr)
    PATTERN = _re.compile(r"pass[ae]?port", _re.IGNORECASE)

    def _iter_strings(self, node):
        if isinstance(node, dict):
            for value in node.values():
                yield from self._iter_strings(value)
        elif isinstance(node, list):
            for value in node:
                yield from self._iter_strings(value)
        elif isinstance(node, str):
            yield node

    def test_ap4_locales_senza_passaporto(self):
        """Tutti i namespace i18n, tutte e 4 le lingue: nessuna stringa
        user-facing contiene piu' Passaporto/Passport/Passeport."""
        import json
        offenders = []
        for lang in ("it", "en", "de", "fr"):
            for path in sorted((FRONTEND_SRC / "locales" / lang).glob("*.json")):
                data = json.loads(path.read_text())
                for text in self._iter_strings(data):
                    if self.PATTERN.search(text):
                        offenders.append((lang, path.name, text[:80]))
        assert not offenders, offenders

    def test_ap4_email_transazionali_senza_passaporto(self):
        """EMAIL_TRANSLATIONS (4 lingue): i testi delle email non
        nominano mai il Passaporto (le chiavi passport_* restano come
        nomi interni)."""
        from services.email_service import EMAIL_TRANSLATIONS
        offenders = []
        for lang, table in EMAIL_TRANSLATIONS.items():
            for key, msg in table.items():
                if isinstance(msg, str) and self.PATTERN.search(msg):
                    offenders.append((lang, key, msg[:80]))
        assert not offenders, offenders

    def test_ap4_claim_email_invita_alla_password(self):
        """La claim post-acquisto ora parla dell'account Aurya e invita
        a impostare la password (assetto password-first AP1b)."""
        from services.email_service import EMAIL_TRANSLATIONS
        expectations = {
            "it": ("account Aurya", "password"),
            "en": ("Aurya account", "password"),
            "de": ("Aurya Konto", "Passwort"),
            "fr": ("compte Aurya", "mot de passe"),
        }
        for lang, (brand, pwd) in expectations.items():
            blob = " ".join(
                EMAIL_TRANSLATIONS[lang][key] for key in
                ("passport_claim_subject", "passport_claim_body",
                 "passport_claim_cta", "passport_claim_footer"))
            assert brand in blob, lang
            assert pwd in blob, lang
            assert "—" not in blob, lang        # mai trattini lunghi


class TestAccountAp5:
    """AP5 (docs/ACCOUNT_UNICO_PIANO_2026-07.md) — chiusura del ciclo
    Account Unico: guardie SOLO per i buchi della matrice E2E. Il resto
    della matrice e' gia' coperto (censimento 29/7):

      1. guest da profilo  → TestAccountApL.test_apl_ordine_guest_* (consensi
         due livelli + account pending + audit); QUI: marketing nel CRM e
         claim email alla conferma della richiesta.
      2. acquisto diretto  → QUI: viaggio live ordine→session→webhook
         simulato→claim→hub (i pezzi unitari vivono in
         test_payment_checkout_integration e TestP2ClaimEmail).
      3. login tre vie     → TestLoginCode/TestMagicLinkService/AP1b; QUI:
         le TRE strade live sullo STESSO account, stessa identita'.
      4. guide/newsletter  → TestHubAccountAp2 + test_f1/f2 newsletter; QUI
         (dentro il login tre vie): newsletter_subscriber coerente.
      5. password lifecycle→ TestAccountAp1b; QUI: il reset su account
         passwordless AGGANCIA lo storico (retroactive_claim).
      6. errori onesti     → AP1b (409/403/401/423, reset one-shot) +
         TestLoginCode (OTP); QUI: token verifica/reset SCADUTI.
      7. GDPR              → TestP4Gdpr (unit); QUI: export+delete live via
         HTTP col nuovo assetto, ordini operatore intatti.
      8. isolamento        → TestP2OrderLinking (unit); QUI: due org VERE,
         un account, /me/orders con entrambi, customer per-org separati.
      9. regressione       → TestInvariants, CG2/CG4, TW/RS/PN/LM: gia'
         tutte guardie vive nella suite (nessun doppione qui).
    """

    PASSWORD = "StrongPass12"

    # ── riuso infrastruttura live AP-L ──────────────────────────────────
    @classmethod
    def _admin_headers(cls):
        return TestAccountApL._admin_headers()

    @staticmethod
    def _db():
        return TestAccountApL._db()

    @classmethod
    def _cleanup_email(cls, email):
        """AP-L cleanup + artefatti della conferma (sales, schedule,
        ledger, ticket) che gli ordini AP5 confermati generano."""
        db = cls._db()
        email = email.lower()
        pa_ids = [a["id"] for a in
                  db.platform_accounts.find({"email": email}, {"id": 1})]
        cust_ids = [c["id"] for c in
                    db.customers.find({"email": email}, {"id": 1})]
        order_ids = [o["id"] for o in db.orders.find({"$or": [
            {"customer_id": {"$in": cust_ids}},
            {"platform_account_id": {"$in": pa_ids}},
        ]}, {"id": 1})]
        if order_ids:
            db.sales_records.delete_many(
                {"metadata.order_id": {"$in": order_ids}})
            db.payment_schedules.delete_many({"order_id": {"$in": order_ids}})
            db.platform_fee_ledger.delete_many({"order_id": {"$in": order_ids}})
            db.issued_tickets.delete_many({"order_id": {"$in": order_ids}})
            db.issued_bookings.delete_many({"order_id": {"$in": order_ids}})
            db.orders.delete_many({"id": {"$in": order_ids}})
        TestAccountApL._cleanup_email(email)
        db.aurya_subscribers.delete_many({"email": email})

    @classmethod
    def _insert_magic_token(cls, account_id):
        """Token magic con hash noto (la via del browser/dei test live:
        il chiaro non e' mai recuperabile dal DB)."""
        import hashlib
        import secrets
        import uuid
        from datetime import datetime, timedelta, timezone

        token = secrets.token_urlsafe(24)
        code = f"{secrets.randbelow(1_000_000):06d}"
        cls._db().platform_magic_tokens.insert_one({
            "id": str(uuid.uuid4()),
            "account_id": account_id,
            "token_hash": hashlib.sha256(token.encode()).hexdigest(),
            "code_hash": hashlib.sha256(code.encode()).hexdigest(),
            "code_attempts": 0,
            "used_at": None,
            "expires_at": (datetime.now(timezone.utc)
                           + timedelta(minutes=10)).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        return token, code

    @classmethod
    def _platform_login(cls, account_id):
        token, _ = cls._insert_magic_token(account_id)
        r = requests.post(f"{BASE_URL}/api/platform/auth/magic-link/verify",
                          json={"token": token}, timeout=10)
        assert r.status_code == 200, r.text
        body = r.json()
        return {"Authorization": f"Bearer {body['access_token']}"}, body

    @staticmethod
    def _order_request(email, product_id, *, slug="masseria-demo",
                       name="Guardia Ap5", marketing=False):
        r = requests.post(f"{BASE_URL}/api/public/order-request", json={
            "slug": slug, "customer_name": name, "customer_email": email,
            "items": [{"product_id": product_id, "quantity": 1}],
            "terms_accepted": False,
            "gdpr_terms_accepted": True, "gdpr_privacy_accepted": True,
            "gdpr_marketing_accepted": bool(marketing),
            "aurya_terms_accepted": True,
            "locale": "it", "channel": "store",
        }, timeout=30)
        assert r.status_code == 200, r.text
        return r.json()

    # ── 1. guest da profilo: marketing nel CRM + claim alla conferma ────

    def test_ap5_richiesta_guest_marketing_e_claim_su_conferma(self):
        """Richiesta servizio da guest con opt-in marketing: il CRM
        timbra accepted_marketing_at + audit merchant_marketing; la
        CONFERMA della richiesta (RS5) fa partire la claim email
        dell'account Aurya pending (timestamp + token magic emesso)."""
        email = "ap5-guest@example.com"
        headers = self._admin_headers()
        self._cleanup_email(email)
        apl = TestAccountApL()
        prod = apl._make_service(headers, "Guardia AP5 guest marketing")
        try:
            out = self._order_request(email, prod["id"], marketing=True)
            order_id = out["order_id"]
            db = self._db()

            cust = db.customers.find_one({"email": email})
            assert cust and cust.get("accepted_marketing_at")
            assert not cust.get("marketing_revoked_at")
            mk = list(db.consent_audit.find(
                {"customer_email": email,
                 "document_type": "merchant_marketing"}))
            assert len(mk) == 1
            assert mk[0]["source"] == "customer_marketing_optin"

            account = db.platform_accounts.find_one({"email": email})
            assert account and not account.get("email_verified")   # pending
            assert not account.get("claim_last_sent_at")           # non ancora

            r = requests.post(f"{BASE_URL}/api/orders/{order_id}/confirm",
                              headers=headers, timeout=15)
            assert r.status_code == 200, r.text

            account = db.platform_accounts.find_one({"email": email})
            assert account.get("claim_last_sent_at")               # claim inviata
            assert db.platform_magic_tokens.count_documents(
                {"account_id": account["id"]}) >= 1                # link emesso
        finally:
            apl._delete_product(headers, prod["id"])
            self._cleanup_email(email)

    # ── 2. acquisto diretto: session → webhook simulato → claim → hub ───

    def test_ap5_acquisto_diretto_webhook_claim_e_hub(self):
        """Ordine direct: session Stripe creata (fin dove il dev arriva),
        webhook checkout.session.completed SIMULATO col reconciler vero
        (stesso pattern verify_/synthetic della suite) → ordine
        confermato, incasso registrato, claim email partita, ordine
        visibile in /account via /platform/me/orders."""
        import json as _json
        import os as _os
        import subprocess

        email = "ap5-direct@example.com"
        headers = self._admin_headers()
        self._cleanup_email(email)
        apl = TestAccountApL()
        r = requests.post(f"{BASE_URL}/api/products", headers=headers, json={
            "name": "Guardia AP5 direct", "item_type": "service",
            "transaction_mode": "direct", "is_published": True,
            "unit_price": 40, "price_mode": "fixed"}, timeout=10)
        assert r.status_code in (200, 201), r.text
        prod = r.json()
        try:
            out = self._order_request(email, prod["id"])
            assert out["transaction_mode"] == "direct"
            order_id = out["order_id"]
            db = self._db()
            order = db.orders.find_one({"id": order_id})
            assert order["payment_intent"] == "required"
            # fin dove il dev consente: la session test viene creata e
            # l'URL di redirect e' quello di Stripe Checkout (se la rete
            # verso Stripe manca, il reconcile sotto resta comunque valido)
            if out.get("payment_checkout_url"):
                assert out["payment_checkout_url"].startswith(
                    "https://checkout.stripe.com/")

            # webhook simulato: evento sintetico sul reconciler canonico,
            # eseguito nel venv del backend contro il DB del server live
            ref = (order.get("payment_checkout") or {}).get("reference")
            script = f"""
import asyncio, json
async def main():
    from services.payment_checkout_service import reconcile_checkout_event
    event = {{
        "id": "evt_ap5_guard_{order_id[:8]}",
        "type": "checkout.session.completed",
        "account": None,
        "data": {{"object": {{
            "id": {ref!r} or "cs_test_ap5_guard",
            "payment_status": "paid",
            "payment_intent": "pi_ap5_guard",
            "currency": "eur",
            "metadata": {{"source": "afianco",
                          "org_id": {order["organization_id"]!r},
                          "order_id": {order_id!r},
                          "schedule_row_seq": "0"}},
            "amount_total": 4000,
        }}}},
    }}
    print(json.dumps(await reconcile_checkout_event(event)))
asyncio.run(main())
"""
            env = {k: v for k, v in _os.environ.items()
                   if k not in ("MONGO_URL", "DB_NAME")}
            proc = subprocess.run(
                [str(BACKEND_DIR / "venv" / "bin" / "python"), "-"],
                input=script, capture_output=True, text=True,
                cwd=BACKEND_DIR, env=env, timeout=120)
            assert proc.returncode == 0, proc.stderr[-2000:]
            result = _json.loads(proc.stdout.strip().splitlines()[-1])
            assert result["action"] == "confirmed", result

            order = db.orders.find_one({"id": order_id})
            assert order["status"] == "confirmed"
            assert order["payment_intent"] == "collected"

            # claim email al pagamento riuscito (account ancora pending)
            account = db.platform_accounts.find_one({"email": email})
            assert account.get("claim_last_sent_at")

            # l'ordine e' nel suo /account
            ph, _ = self._platform_login(account["id"])
            r = requests.get(f"{BASE_URL}/api/platform/me/orders",
                             headers=ph, timeout=10)
            assert r.status_code == 200, r.text
            rows = [o for o in r.json()["orders"] if o["id"] == order_id]
            assert rows and rows[0]["status"] == "confirmed"
            assert rows[0]["transaction_mode"] == "direct"
        finally:
            apl._delete_product(headers, prod["id"])
            self._cleanup_email(email)

    # ── 3+4. login tre vie sullo stesso account + newsletter coerente ───

    def test_ap5_login_tre_vie_stesso_account(self):
        """Password, OTP e magic link entrano tutte nello STESSO account
        (stessa identita', stesso shape di risposta) e il flag
        newsletter_subscriber e' coerente: False da non iscritto, True +
        subscriber_token appena l'iscrizione e' confermata."""
        import uuid
        from datetime import datetime, timezone

        from auth import get_password_hash

        email = "ap5-tre-vie@example.com"
        self._cleanup_email(email)
        db = self._db()
        account_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        db.platform_accounts.insert_one({
            "id": account_id, "email": email, "name": "Tre Vie",
            "language": "it", "email_verified": True, "is_active": True,
            "password_hash": get_password_hash(self.PASSWORD),
            "failed_login_attempts": 0, "lockout_count_today": 0,
            "locked_until": None, "sessions_invalidated_at": None,
            "created_at": now,
        })
        try:
            # 1. password
            r = requests.post(f"{BASE_URL}/api/platform/auth/login", json={
                "email": email, "password": self.PASSWORD}, timeout=10)
            assert r.status_code == 200, r.text
            pw = r.json()
            assert pw["account"]["id"] == account_id
            assert pw["newsletter_subscriber"] is False
            assert "subscriber_token" not in pw

            # 2. OTP (codice a 6 cifre)
            _, code = self._insert_magic_token(account_id)
            r = requests.post(f"{BASE_URL}/api/platform/auth/code/verify",
                              json={"email": email, "code": code}, timeout=10)
            assert r.status_code == 200, r.text
            otp = r.json()
            assert otp["account"]["id"] == account_id

            # 3. magic link
            token, _ = self._insert_magic_token(account_id)
            r = requests.post(
                f"{BASE_URL}/api/platform/auth/magic-link/verify",
                json={"token": token}, timeout=10)
            assert r.status_code == 200, r.text
            ml = r.json()
            assert ml["account"]["id"] == account_id
            # stesso shape su tutte le strade
            for body in (pw, otp, ml):
                assert set(body) >= {"access_token", "token_type",
                                     "account", "newsletter_subscriber"}

            # iscrizione confermata → il login porta il token guide
            db.aurya_subscribers.insert_one({
                "id": str(uuid.uuid4()), "email": email,
                "status": "confirmed", "created_at": now})
            r = requests.post(f"{BASE_URL}/api/platform/auth/login", json={
                "email": email, "password": self.PASSWORD}, timeout=10)
            assert r.status_code == 200, r.text
            assert r.json()["newsletter_subscriber"] is True
            assert r.json()["subscriber_token"]
        finally:
            self._cleanup_email(email)

    # ── 5+6. reset aggancia lo storico + token scaduti rifiutati ────────

    async def test_ap5_reset_aggancia_storico_e_token_scaduti(self):
        """(a) confirm_password_reset su account nato passwordless chiama
        retroactive_claim (lo storico ordini si aggancia); (b) token di
        verifica e di reset SCADUTI → INVALID_TOKEN (con l'hash ancora a
        DB: il rifiuto e' sulla scadenza, non sull'assenza)."""
        from contextlib import ExitStack
        from datetime import timedelta
        from unittest.mock import AsyncMock, patch

        import pytest
        from models.common import utc_now
        from services import platform_account_service as svc

        Ap1b = TestAccountAp1b
        fake, sent = Ap1b._MemAccounts(), {}
        claim = AsyncMock()
        with ExitStack() as stack:
            for p in Ap1b()._ctx(fake, sent):
                stack.enter_context(p)
            stack.enter_context(patch.object(svc, "retroactive_claim", claim))

            # (a) account passwordless da acquisto guest: reset = imposta
            # password + claim retroattivo dello storico
            fake.docs["g1"] = {"id": "g1", "email": "ap5-claim@x.it",
                               "email_verified": False, "password_hash": None,
                               "language": "it"}
            await svc.request_password_reset("ap5-claim@x.it")
            await svc.confirm_password_reset(sent["reset_token"],
                                             self.PASSWORD)
            assert claim.await_count == 1          # storico agganciato
            assert claim.await_args[0][0]["id"] == "g1"

            # (b) verifica scaduta: hash presente ma oltre il TTL
            await svc.password_signup(name="S", email="ap5-scad@x.it",
                                      password=self.PASSWORD)
            acc = [d for d in fake.docs.values()
                   if d["email"] == "ap5-scad@x.it"][0]
            acc["verification_token_expires"] = (
                utc_now() - timedelta(hours=1)).isoformat()
            with pytest.raises(ValueError, match="INVALID_TOKEN"):
                await svc.verify_signup_email(sent["verify_token"])

            # (b) reset scaduto: stesso rifiuto
            await svc.request_password_reset("ap5-scad@x.it")
            acc["reset_token_expires"] = (
                utc_now() - timedelta(minutes=5)).isoformat()
            with pytest.raises(ValueError, match="INVALID_TOKEN"):
                await svc.confirm_password_reset(sent["reset_token"],
                                                 self.PASSWORD)

    # ── 7. GDPR live: export + delete col nuovo assetto ─────────────────

    def test_ap5_gdpr_export_delete_live(self):
        """Export via HTTP porta identita' + ordini (vista cliente);
        DELETE /platform/me cancella l'identita' e i token ma NON tocca
        l'ordine ne' il CRM dell'operatore (solo unlink dello stamp)."""
        email = "ap5-gdpr@example.com"
        headers = self._admin_headers()
        self._cleanup_email(email)
        apl = TestAccountApL()
        prod = apl._make_service(headers, "Guardia AP5 gdpr")
        try:
            out = self._order_request(email, prod["id"])
            order_id = out["order_id"]
            db = self._db()
            account = db.platform_accounts.find_one({"email": email})
            ph, _ = self._platform_login(account["id"])

            r = requests.get(f"{BASE_URL}/api/platform/me/export",
                             headers=ph, timeout=10)
            assert r.status_code == 200, r.text
            exp = r.json()
            assert exp["account"]["email"] == email
            assert [o["id"] for o in exp["orders"]] == [order_id]
            blob = str(exp)
            for banned in ("cost_price", "application_fee", "notes"):
                assert banned not in blob

            r = requests.delete(f"{BASE_URL}/api/platform/me",
                                headers=ph, timeout=10)
            assert r.status_code == 200, r.text
            assert r.json()["status"] == "deleted"

            # identita' e token VIA; dati operatore INTATTI, solo unlink
            assert not db.platform_accounts.find_one({"email": email})
            assert db.platform_magic_tokens.count_documents(
                {"account_id": account["id"]}) == 0
            order = db.orders.find_one({"id": order_id})
            assert order and "platform_account_id" not in order
            assert db.customers.find_one({"email": email})   # CRM operatore
        finally:
            apl._delete_product(headers, prod["id"])
            self._cleanup_email(email)

    # ── 8. isolamento: due org vere, UN account, dati mai mescolati ─────

    def test_ap5_isolamento_due_org_live(self):
        """Stessa email compra su masseria-demo E borgo-sereno: nasce UN
        solo platform account, /me/orders mostra entrambi gli ordini coi
        nomi dei DUE operatori, il CRM resta un record per org."""
        import uuid

        email = "ap5-iso@example.com"
        headers = self._admin_headers()
        self._cleanup_email(email)
        apl = TestAccountApL()
        prod_a = apl._make_service(headers, "Guardia AP5 iso masseria")
        db = self._db()
        # per l'org borgo non abbiamo credenziali admin nei test: il
        # prodotto di guardia nasce come CLONE dello schema del prodotto
        # vero (stessa forma dati), con org e id propri
        borgo_org = "afca4458-6b11-44d1-811a-60e79df8a928"
        prod_b = dict(db.products.find_one({"id": prod_a["id"]}, {"_id": 0}))
        prod_b.update({"id": str(uuid.uuid4()),
                       "organization_id": borgo_org,
                       "name": "Guardia AP5 iso borgo", "slug": None})
        db.products.insert_one(dict(prod_b))
        try:
            out_a = self._order_request(email, prod_a["id"],
                                        slug="masseria-demo")
            out_b = self._order_request(email, prod_b["id"],
                                        slug="borgo-sereno")

            accounts = list(db.platform_accounts.find({"email": email}))
            assert len(accounts) == 1                     # UNA identita'
            aid = accounts[0]["id"]
            for oid in (out_a["order_id"], out_b["order_id"]):
                assert db.orders.find_one({"id": oid})[
                    "platform_account_id"] == aid

            custs = list(db.customers.find({"email": email}))
            assert len(custs) == 2                        # CRM per-org separati
            assert ({c["organization_id"] for c in custs}
                    == {"2393033b-80a8-47c9-8529-b7810c0b2123", borgo_org})

            ph, _ = self._platform_login(aid)
            r = requests.get(f"{BASE_URL}/api/platform/me/orders",
                             headers=ph, timeout=10)
            assert r.status_code == 200, r.text
            rows = {o["id"]: o for o in r.json()["orders"]}
            assert {out_a["order_id"], out_b["order_id"]} <= set(rows)
            names = {rows[out_a["order_id"]]["operator_name"],
                     rows[out_b["order_id"]]["operator_name"]}
            assert len(names) == 2                        # due operatori veri
        finally:
            apl._delete_product(headers, prod_a["id"])
            db.products.delete_many({"id": prod_b["id"]})
            self._cleanup_email(email)


class TestPotaturaPs1:
    """PS1 (30/7/2026) — back onesti: le dashboard raggiungibili dal
    mondo snello non riportano MAI alla ProductsPage legacy.

    ServiceDashboardPage (da /listino "Impostazioni avanzate") torna a
    /listino in tutti e tre i punti (hero back + due stati di errore);
    EventDashboardPage not-found e CheckInPage tornano a /events. La
    ProductsPage resta viva SOLO per le org legacy_commerce (voce di
    menu dietro flag, Layout.js): qui si vieta solo la strada dal
    mondo snello.
    """

    def test_ps1_service_dashboard_torna_al_listino(self):
        page = (FRONTEND_SRC / "features" / "services"
                / "ServiceDashboardPage.js").read_text()
        assert 'to="/products' not in page \
            and "navigate('/products" not in page, \
            "ServiceDashboardPage non deve piu' linkare la ProductsPage legacy"
        assert page.count("'/listino'") + page.count('"/listino"') >= 3, \
            "attesi 3 ritorni a /listino (hero + not_found + wrong_type)"

    def test_ps1_ecosistema_ritiri_torna_ai_ritiri(self):
        for rel in (("features", "events", "EventDashboardPage.js"),
                    ("features", "events", "CheckInPage.js")):
            src = FRONTEND_SRC.joinpath(*rel).read_text()
            assert 'to="/products"' not in src and "navigate('/products')" not in src, \
                f"{rel[-1]} non deve riportare alla ProductsPage legacy"


class TestPotaturaPs2:
    """PS2 (30/7/2026) — /services/:id ridotta a editor AVANZATO onesto
    (docs/POTATURA_STORE_PIANO_2026-07.md). Restano SOLO le sezioni che
    non hanno altra casa: descrizione estesa + copertina landing (con
    multilingua), traduzioni di nome/nota, regole orari per-giorno,
    campi ordine custom, anteprima/copia link/duplica. Tutto cio' che
    duplicava la riga espansa del listino (LM1) e la sezione morta
    Distribuzione sono stati potati. Il salvataggio manda un payload
    PARZIALE (exclude_unset lato API) con merge del metadata esistente:
    i campi del listino non possono essere azzerati da qui."""

    PAGE = (FRONTEND_SRC / "features" / "services"
            / "ServiceDashboardPage.js")
    LISTINO = FRONTEND_SRC / "features" / "listino" / "ListinoPage.js"

    def test_ps2_sezioni_duplicate_potate(self):
        page = self.PAGE.read_text()
        assert "ProductSalesStats" not in page      # Incassi/Ordini coprono
        assert "ServiceOptionsEditor" not in page   # opzioni: nel listino
        assert "distribu" not in page.lower()       # sezione morta
        assert "quickTogglePublish" not in page \
            and "statusTitle" not in page           # stato: toggle Eye listino
        assert "terms_content" not in page          # requisiti: nel listino
        assert "transaction_mode" not in page       # incasso: nel listino
        assert "unit_price" not in page             # prezzo: nel listino
        assert "is_published" not in page           # stato: nel listino
        assert "upcomingTitle" not in page          # agenda: nel Calendario

    def test_ps2_sezioni_superstiti(self):
        page = self.PAGE.read_text()
        assert "AvailabilityRulesEditor" in page    # regole orari per-giorno
        assert "use_default_schedule" in page       # toggle calendario ufficiale
        assert "long_description" in page           # descrizione estesa landing
        assert "cover_image_url" in page            # copertina landing
        assert "FieldEditorList" in page            # campi ordine custom
        assert "MultiLangSection" in page           # traduzioni
        assert "service_allow_custom_request" in page
        assert "handleDuplicate" in page and "copyLandingUrl" in page
        assert "Impostazioni avanzate del servizio" in page  # titolo onesto

    def test_ps2_payload_parziale_con_merge_metadata(self):
        """Nessun campo del listino nel payload di update: il metadata
        fa merge sull'esistente, il resto viaggia via exclude_unset."""
        page = self.PAGE.read_text()
        assert "...existingMeta" in page
        assert "translations: buildTranslationsPayload()" in page
        # le due strade di salvataggio: saveProduct + flag immediati
        assert page.count("productsAPI.update(") == 2

    def test_ps2_label_listino_impostazioni_avanzate(self):
        listino = self.LISTINO.read_text()
        assert "Tutte le impostazioni" not in listino
        assert "Impostazioni avanzate" in listino
        assert "impostazioni avanzate" in listino   # link regole orari

    def test_ps2_niente_store_nel_copy_pagina(self):
        page = self.PAGE.read_text()
        assert "store" not in page.lower()
        assert "negozio" not in page.lower()

    def test_ps2_i18n_x4(self):
        """Chiavi nuove presenti e chiavi morte assenti nei 4 locales."""
        import json as _json
        for lang in ("it", "en", "de", "fr"):
            loc = _json.loads((FRONTEND_SRC / "locales" / lang
                               / "products.json").read_text())
            svc = loc["dashboards"]["service"]
            for key in ("pageTitle", "baseHint", "translationsTitle",
                        "translationsSave", "coverLabel",
                        "allowCustomTitle", "orderFieldsSave"):
                assert key in svc, f"{lang}: manca {key}"
            for key in ("statusTitle", "product", "orderFieldsHint",
                        "distributionDesc", "optionsTitle", "termsTitle",
                        "upcomingTitle"):
                assert key not in svc, f"{lang}: chiave morta {key}"
            assert "advancedSettings" in loc.get("listino", {}), \
                f"{lang}: manca listino.advancedSettings"


class TestPotaturaPs3:
    """PS3 (30/7/2026) — bonifica olistica di "store" e vecchia pagina
    prodotti dalle superfici raggiungibili da un operatore snello
    (docs/POTATURA_STORE_PIANO_2026-07.md, onda PS3).

    Il wizard ritiri garantisce lo store tecnico in silenzio
    (ensureDefault, stesso pattern del Listino) e non mostra mai banner
    o CTA verso /stores; la sezione Distribuzione (wizard + dashboard
    prodotto superstiti) esiste SOLO nel mondo multi-store legacy
    (>1 store); le Impostazioni parlano di profilo pubblico /o/, non di
    catalogo /s/; il copy piani parla di profilo pubblico, non di
    negozio online; /store-settings redirige a /settings. Le scansioni
    sono ancorate a file e sezioni intere, mai a offset di riga.
    """

    WIZARD = FRONTEND_SRC / "features" / "events" / "EventWizard.js"
    SETTINGS = FRONTEND_SRC / "features" / "settings" / "SettingsPage.js"
    APP = FRONTEND_SRC / "App.js"

    def test_ps3_wizard_senza_cta_stores_con_ensure_default(self):
        src = self.WIZARD.read_text()
        assert 'href="/stores"' not in src and "storeRequired" not in src, \
            "il passo Pubblica non deve mai chiedere di creare uno store"
        assert "storesAPI.ensureDefault()" in src, \
            "lo store tecnico va garantito in silenzio (pattern Listino)"

    def test_ps3_wizard_distribuzione_solo_multi_store(self):
        src = self.WIZARD.read_text()
        assert "availableStores.length > 1 && (" in src, \
            "la Distribuzione appare solo col multi-store legacy"
        # il ramo <=1 ("Visibile automaticamente in: <store>") e' potato
        assert "visibleAutoPrefix" not in src
        assert "distributionDesc" not in src

    def test_ps3_dashboard_distribuzione_solo_multi_store(self):
        for rel in (("features", "physicals", "PhysicalDashboardPage.js"),
                    ("features", "digitals", "DigitalDashboardPage.js"),
                    ("features", "reservations",
                     "ReservationDashboardPage.js")):
            src = FRONTEND_SRC.joinpath(*rel).read_text()
            assert "stores.length > 1 && (" in src, \
                f"{rel[-1]}: sezione Distribuzione senza gate multi-store"
        event = (FRONTEND_SRC / "features" / "events"
                 / "EventDashboardPage.js").read_text()
        assert "availableStores.length > 1 && (" in event
        assert "availableStores.length > 0 && (" not in event

    def test_ps3_settings_indirizzo_in_chiave_profilo(self):
        src = self.SETTINGS.read_text()
        assert "/s/" not in src, "niente prefisso storefront legacy"
        assert "negozio" not in src.lower() \
            and "catalogo" not in src.lower(), \
            "la sezione indirizzo parla di profilo, non di commerce"
        assert "/o/" in src and "Indirizzo pubblico del tuo profilo" in src
        # lo slug del profilo e dello store tecnico restano allineati
        # (il sync vive in handleSave, solo se erano gia' allineati)
        assert "storesAPI.list()" in src and "storesAPI.update(" in src

    def test_ps3_rotta_store_settings_redirect(self):
        app = self.APP.read_text()
        assert "StoreSettingsPage" not in app, \
            "la pagina StoreSettingsPage non deve piu' essere importata"
        assert ('path="/store-settings" '
                'element={<Navigate to="/settings" replace />}') in app

    def test_ps3_nav_store_settings_rimossa_x4(self):
        import json as _json
        for lang in ("it", "en", "de", "fr"):
            nav = _json.loads((FRONTEND_SRC / "locales" / lang
                               / "common.json").read_text())["nav"]
            assert "store_settings" not in nav, f"{lang}: label morta"

    def test_ps3_copy_piani_profilo_pubblico_x4(self):
        """Le feature dei piani parlano di profilo pubblico, mai di
        negozio online (IT) o equivalenti nelle altre lingue."""
        import json as _json

        def _find_parent(node, key):
            if isinstance(node, dict):
                if key in node:
                    return node
                for v in node.values():
                    r = _find_parent(v, key)
                    if r is not None:
                        return r
            elif isinstance(node, list):
                for v in node:
                    r = _find_parent(v, key)
                    if r is not None:
                        return r
            return None

        forbidden = {"it": ("negozio",),
                     "en": ("online store",),
                     "de": ("online-shop",),
                     "fr": ("boutique en ligne",)}
        for lang, bads in forbidden.items():
            loc = _json.loads((FRONTEND_SRC / "locales" / lang
                               / "settings.json").read_text())
            feats = _find_parent(loc, "retreat_ecommerce")
            assert feats is not None, f"{lang}: piani retreat_* spariti?"
            for key, val in feats.items():
                if not key.startswith("retreat_"):
                    continue
                for bad in bads:
                    assert bad not in val.lower(), f"{lang}:{key}: {val}"
            # il profilo pubblico e' entrato nel copy della feature clou
            assert "profil" in feats["retreat_ecommerce"].lower(), \
                f"{lang}: retreat_ecommerce non parla di profilo"

    def test_ps3_inizia_lean_vetrina_non_negozio(self):
        src = (FRONTEND_SRC / "features" / "onboarding"
               / "IniziaPage.js").read_text()
        assert "la tua vetrina insieme" in src
        assert "il tuo negozio insieme" not in src
        # gli step legacy ("Crea il tuo store") restano SOLO nel ramo
        # LEGACY_STEPS, selezionato dallo shape dello status backend
        # (org.legacy_commerce): il mondo lean usa LEAN_STEPS
        assert "lean ? LEAN_STEPS : LEGACY_STEPS" in src

    def test_ps3_legal_dialog_senza_link_stores(self):
        src = (FRONTEND_SRC / "features" / "stores" / "components"
               / "MerchantLegalDialog.js").read_text()
        assert 'href="/stores"' not in src, \
            "il dialog si apre anche dal mondo snello: CTA neutra"
        assert "active_locale_link_text" not in src

    def test_ps3_layout_codice_morto_potato(self):
        src = (FRONTEND_SRC / "components" / "Layout.js").read_text()
        assert "const operationsNav" not in src \
            and "const moduleNavMap" not in src, \
            "nav morta con /stores: va rimossa, non lasciata dormiente"
        # la voce Store resta SOLO dietro il flag legacy_commerce
        assert "legacyCommerce" in src


class TestPotaturaPs4:
    """PS4 (30/7/2026) — icona account utente nell'header pubblico +
    UN SOLO login utente (docs/POTATURA_STORE_PIANO_2026-07.md, onda
    PS4). L'omino CircleUserRound e' l'entry point universale (tutti i
    breakpoint, tutte le fasi, network inclusa: decisione founder); il
    token piattaforma si legge in modo sincrono da localStorage; senza
    token si atterra su /account/accedi, con token su /account. Del
    portale clienti legacy restano vive SOLO le rotte strutturali del
    player corsi; signup/ordini/profilo legacy redirigono ad Aurya.
    """

    SHELL = (FRONTEND_SRC / "features" / "storefront" / "components"
             / "MarketplaceShell.jsx")
    APP = FRONTEND_SRC / "App.js"

    def test_ps4_icona_account_nello_shell(self):
        src = self.SHELL.read_text()
        assert "CircleUserRound" in src, \
            "l'omino account deve vivere nell'header marketplace"
        assert "PLATFORM_TOKEN_KEY" in src, \
            "lo stato loggato si legge dal token piattaforma (sincrono)"
        assert "'/account'" in src and "'/account/accedi'" in src, \
            "href: /account con token, /account/accedi senza"
        assert "marketplace.accountAria" in src, \
            "aria-label i18n dell'icona account"
        # l'icona non e' nascosta dietro breakpoint: nessun hidden
        # sulla riga del Link icona (il pill myTrips resta hidden sm)
        icon_at = src.index("CircleUserRound className")
        link_open = src.rindex("<Link", 0, icon_at)
        assert "hidden" not in src[link_open:icon_at], \
            "l'icona account deve essere visibile a TUTTI i breakpoint"

    def test_ps4_icona_anche_in_fase_network(self):
        """Il Link dell'icona NON sta dentro un ramo !isNetwork."""
        src = self.SHELL.read_text()
        icon_at = src.index("CircleUserRound className")
        link_open = src.rindex("<Link", 0, icon_at)
        # nessun gate di fase tra l'apertura del Link icona e l'icona
        assert "isNetwork" not in src[link_open:icon_at], \
            "l'icona account non deve essere gated dalla fase network"
        # il ramo condizionale della pill myTrips si CHIUDE prima
        # dell'apertura del Link icona (l'icona sta fuori dal ramo)
        pill_close = src.index("</Link>", src.index("marketplace.myTrips"))
        assert ")}" in src[pill_close:link_open], \
            "il ramo !isNetwork della pill deve chiudersi prima dell'icona"
        # accanto all'hamburger: il bottone menu mobile segue l'icona
        assert src.index("setMobileNavOpen((o) => !o)") > icon_at

    def test_ps4_i18n_x4_senza_passaporto(self):
        import json as _json
        for lang in ("it", "en", "de", "fr"):
            loc = _json.loads((FRONTEND_SRC / "locales" / lang
                               / "landings.json").read_text())
            val = loc["marketplace"].get("accountAria", "")
            assert val, f"{lang}: manca marketplace.accountAria"
            assert "Passaporto" not in val and "—" not in val \
                and "–" not in val, f"{lang}: copy vietato"

    def test_ps4_una_sola_rotta_account_attiva(self):
        app = self.APP.read_text()
        assert app.count('path="/account"') == 1, \
            "/account deve essere registrato UNA volta (AccountPage)"
        assert 'path="/account" element={<AccountPage />}' in app
        # le rotte Aurya continuano a vincere (registrate e distinte)
        for p in ("/account/accedi", "/account/verifica",
                  "/account/nuova-password"):
            assert f'path="{p}"' in app, f"manca la rotta {p}"

    def test_ps4_legacy_redirette_e_player_vivo(self):
        app = self.APP.read_text()
        # redirette alle rotte Aurya
        assert ('path="/account/signup" '
                'element={<Navigate to="/account/accedi" replace />}') in app
        for p in ("/account/orders", "/account/orders/:orderId",
                  "/account/profile"):
            assert (f'path="{p}" '
                    'element={<Navigate to="/account" replace />}') in app, \
                f"{p}: attesa redirect all'account Aurya"
        # strutturali del player corsi legacy: restano vive
        assert 'path="/account/login" element={<CustomerLoginPage />}' in app
        assert "CustomerCoursePlayerPage" in app \
            and 'path="/account/courses/:enrollment_id"' in app
        assert 'path="/account/forgot-password"' in app \
            and 'path="/account/reset-password"' in app \
            and 'path="/account/verify-email"' in app
        # il vecchio portale ordini/profilo non e' piu' importato
        for dead in ("CustomerOrdersPage", "CustomerOrderDetailPageNew",
                     "CustomerProfilePage", "CustomerSignupPage"):
            assert dead not in app, f"import morto: {dead}"

    def test_ps4_nessun_nuovo_passaporto(self):
        shell = self.SHELL.read_text()
        assert "Passaporto" not in shell
        # App.js: resta solo il commento storico P3 (nessuna new entry)
        assert self.APP.read_text().count("Passaporto") <= 1


class TestPotaturaPs5:
    """PS5 (30/7/2026) — consolidamento GDPR operatore
    (docs/POTATURA_STORE_PIANO_2026-07.md, onda PS5).

    L'operatore NON scrive privacy: documenti Aurya + informativa
    autogenerata multilingua + le sue condizioni. L'editor custom
    (MerchantLegalDialog) resta raggiungibile SOLO dal mondo legacy
    (/stores, /newsletter-forms); gli endpoint storefront legal
    accettano ?lang= e espongono binding_locale; i dati anagrafici
    correnti dello store vincono sui template_vars stantii; il DPA
    art. 28 e' in superficie in SalesConditionsCard.
    """

    CARD = (FRONTEND_SRC / "features" / "settings" / "sections"
            / "SalesConditionsCard.jsx")

    def test_ps5_storefront_privacy_multilingua(self):
        """masseria-demo (org demo, nessun legal custom PUBBLICATO,
        binding EN da storefront_languages) risponde nella lingua
        richiesta: autogen x4."""
        base = f"{BASE_URL}/api/legal/storefront/masseria-demo/privacy"
        r_en = requests.get(base, params={"lang": "en"}, timeout=10)
        assert r_en.status_code == 200
        d_en = r_en.json()
        assert d_en["display_locale"] == "en"
        assert "Data Controller" in d_en["content"]
        r_it = requests.get(base, params={"lang": "it"}, timeout=10)
        d_it = r_it.json()
        assert d_it["display_locale"] == "it"
        assert "Titolare del trattamento" in d_it["content"]
        # binding_locale sempre presente e uguale nelle due risposte
        assert d_en["binding_locale"] == d_it["binding_locale"]
        assert d_it["binding_locale"] in ("it", "en", "de", "fr")
        # lang invalido → default (comportamento pre-PS5)
        r_bad = requests.get(base, params={"lang": "xx"}, timeout=10)
        d_bad = r_bad.json()
        assert d_bad["locale_requested"] is None
        assert d_bad["display_locale"] == d_bad["binding_locale"]

    def test_ps5_dati_titolare_correnti_vincono(self):
        """La precedenza e' invertita SOLO sui campi identitari: i dati
        correnti dello store doc battono i template_vars stantii; i
        flag di raccolta restano dai template_vars."""
        from routers.legal import _build_autogen_template_vars
        store = {
            "name": "Store Vero",
            "contact_email": "vero@example.com",
            "country": "Italia",
            "fulfillment_modes": [],
            "merchant_legal_template_vars": {
                "merchant_name": "test",
                "merchant_email": "dav@gmail.com",
                "merchant_country": "iitallia",
                "store_name": "test",
                "store_country": "iitallia",
                "collects_phone": True,
                "platform_name": "afianco",
                "platform_controller_email": "davide@afianco.ch",
            },
        }
        v = _build_autogen_template_vars(store)
        assert v.merchant_name == "Store Vero"
        assert v.merchant_email == "vero@example.com"
        assert v.merchant_country == "Italia"
        assert v.store_name == "Store Vero"
        assert v.store_country == "Italia"
        # i flag non identitari restano dai template_vars salvati
        assert v.collects_phone is True
        # platform_*: sempre il brand corrente, mai i valori salvati
        assert "afianco" not in v.platform_name.lower()
        assert "afianco" not in v.platform_controller_email.lower()
        # fallback: campo corrente vuoto → template_vars come riserva
        store_no_email = {**store, "contact_email": None}
        assert _build_autogen_template_vars(
            store_no_email).merchant_email == "dav@gmail.com"

    def test_ps5_template_vars_default_senza_afianco(self):
        """I default piattaforma leggono core/brand.py (Aurya)."""
        from services.merchant_legal_template_service import TemplateVars
        dump = TemplateVars().model_dump()
        for key, val in dump.items():
            assert "afianco" not in str(val).lower(), f"{key}: {val}"
        assert dump["platform_name"] == "Aurya"

    def test_ps5_templates_senza_boilerplate_lingua(self):
        """Niente 'fa fede la versione italiana' hardcoded nei
        template: la lingua di riferimento e' binding_locale dinamico
        (riga renderizzata da StorefrontLegalPage)."""
        from services.merchant_legal_template_service import (
            list_template_files,
        )
        files = list_template_files()
        assert len(files) == 8, "matrice template 2 doc x 4 lingue"
        for path in files:
            text = path.read_text(encoding="utf-8").lower()
            for bad in ("legally binding", "verbindliche",
                        "prévaut", "legalmente vincolante",
                        "afianco"):
                assert bad not in text, f"{path.name}: '{bad}'"

    def test_ps5_card_senza_editor_custom(self):
        """SalesConditionsCard: editor custom congelato (resta solo nel
        mondo legacy /stores e /newsletter-forms), informativa autogen
        come riga semplice, mini-form titolare, riga DPA."""
        card = self.CARD.read_text()
        assert "MerchantLegalDialog" not in card, \
            "l'editor custom non deve essere raggiungibile da Impostazioni"
        assert "owner-data-form" in card and "save-owner-data" in card
        assert "generata automaticamente" in card       # riga informativa
        assert "/privacy" in card                        # link autogen
        assert "dpa-row" in card and "/settings/legal/dpa" in card
        # il mini-form scrive sullo store doc (autogen coerente)
        assert "storesAPI.update(" in card
        assert "contact_email" in card and "country" in card
        # il dialog resta vivo SOLO nel mondo legacy
        for legacy in (("features", "stores", "StoresPage.js"),
                       ("features", "newsletter", "NewsletterPage.js")):
            src = FRONTEND_SRC.joinpath(*legacy).read_text()
            assert "MerchantLegalDialog" in src, \
                f"{legacy[-1]}: il mondo legacy tiene l'editor custom"

    def test_ps5_dpa_raggiungibile(self):
        """Rotta /settings/legal/dpa registrata + endpoint status vivo
        (auth-gated: 401/403 senza token)."""
        app = (FRONTEND_SRC / "App.js").read_text()
        assert 'path="/settings/legal/dpa"' in app
        r = requests.get(f"{BASE_URL}/api/legal/dpa/status", timeout=10)
        assert r.status_code in (401, 403)

    def test_ps5_pagina_legale_lingua_utente(self):
        """StorefrontLegalPage chiede la lingua utente e mostra la riga
        'fa fede' quando la lingua servita differisce dal binding."""
        page = (FRONTEND_SRC / "pages"
                / "StorefrontLegalPage.js").read_text()
        assert "fetcher(slug, userLang || undefined)" in page
        assert "binding_note" in page and "binding-locale-note" in page
        svc = (FRONTEND_SRC / "services" / "legalService.js").read_text()
        assert "fetchStorefrontPrivacy(slug, locale)" in svc
        assert "fetchStorefrontTerms(slug, locale)" in svc


class TestPotaturaPs6:
    """PS6 (30/7/2026) — funnel checkout pertinenti alla superficie di
    partenza (docs/POTATURA_STORE_PIANO_2026-07.md, onda PS6).

    ROTTI: latch del consenso checkout in StoreToProfileRedirect (il
    param ?checkout=1 viene strippato DOPO il mount, la guardia non deve
    rivalutare); recupero lingua nel handoff /p/ → /s/ (catalogo senza
    filtro lingua + toast onesto se manca davvero); /pay/{token} in
    stati non pagabili REINDIRIZZA a una pagina umana, mai piu' JSON
    nudo nelle email. FUORVIANTI: canale ordine dalla superficie reale
    (prop channel, decontaminazione mktp in InlineServiceCheckout,
    timbro condizionato in InlineEventCheckout); cancel/success/
    breadcrumb con copy e CTA oneste.
    """

    APP = FRONTEND_SRC / "App.js"
    SF = FRONTEND_SRC / "features" / "storefront"

    # ── 1. latch: /s/:slug?checkout=1 non rimbalza piu' al profilo ──

    def test_ps6_latch_store_to_profile_redirect(self):
        src = self.APP.read_text()
        assert "function StoreToProfileRedirect" in src
        seg = src.split("function StoreToProfileRedirect")[1][:700]
        # il consenso e' LATCHATO al mount con lo useState-initializer:
        # lo strip del param/state non fa piu' rimbalzare al profilo
        assert "React.useState(() =>" in seg, \
            "manca il latch useState(() => wantsCheckout) nel redirect"
        assert "has('checkout')" in seg and "preloadCart" in seg

    # ── 2. handoff /p/ → /s/: recupero lingua + toast onesto ─────────

    def test_ps6_preload_recupero_lingua(self):
        page = (self.SF / "StorefrontPage.js").read_text()
        # niente piu' bail silenzioso: refetch senza filtro lingua...
        assert "preloadRecoveryRef" in page
        assert "storefrontAPI.getCatalog(slug)" in page
        # ...e toast onesto quando il prodotto manca davvero
        assert "preloadUnavailableInLanguage" in page

    # ── 3. pay-token: mai JSON nudo, sempre redirect umano ───────────

    def test_ps6_pay_token_ignoto_redirect(self):
        r = requests.get(
            f"{BASE_URL}/api/public/pay/token-inesistente-1234567890",
            allow_redirects=False, timeout=10)
        assert r.status_code in (303, 307), r.text
        assert "/s/pay-non-disponibile" in r.headers.get("Location", "")

    def test_ps6_pay_token_non_pagabile_redirect(self):
        """HTTP reale: ordine+schedule fixture con riga in stato non
        pagabile → redirect alla pagina onesta CON lo slug operatore."""
        import uuid as _uuid
        db = self._db()
        store = db.stores.find_one({"slug": "masseria-demo"},
                                   {"id": 1, "organization_id": 1})
        assert store, "store demo masseria-demo assente"
        token = "ps6-guard-" + _uuid.uuid4().hex
        order_id = "ps6-guard-order-" + _uuid.uuid4().hex[:8]
        sched_id = "ps6-guard-sched-" + _uuid.uuid4().hex[:8]
        try:
            db.orders.insert_one({
                "id": order_id,
                "organization_id": store["organization_id"],
                "store_id": store["id"],
                "status": "draft", "total": 10.0,
            })
            db.payment_schedules.insert_one({
                "id": sched_id, "order_id": order_id,
                "organization_id": store["organization_id"],
                "rows": [{"seq": 1, "kind": "balance",
                          "amount_minor": 1000,
                          "status": "suspended",   # fuori da PAYABLE e da paid
                          "pay_token": token}],
            })
            r = requests.get(f"{BASE_URL}/api/public/pay/{token}",
                             allow_redirects=False, timeout=10)
            assert r.status_code in (303, 307), r.text
            loc = r.headers.get("Location", "")
            assert "/s/pay-non-disponibile" in loc
            assert "slug=masseria-demo" in loc, \
                "l'org e' nota: la pagina deve poter offrire 'Torna all'operatore'"
        finally:
            db.payment_schedules.delete_one({"id": sched_id})
            db.orders.delete_one({"id": order_id})

    def test_ps6_pay_page_frontend_registrata(self):
        app = self.APP.read_text()
        assert '"/s/pay-non-disponibile"' in app.replace("'", '"')
        crp = (self.SF / "CheckoutResultPage.js").read_text()
        assert "PayLinkUnavailablePage" in crp
        assert 'to="/account"' in crp        # CTA "Vai al tuo account"
        assert "/o/${slug}" in crp           # CTA "Torna all'operatore"

    # ── 4. canale = superficie reale + decontaminazione mktp ─────────

    def test_ps6_inline_service_decontaminazione(self):
        src = (self.SF / "components" / "checkout"
               / "InlineServiceCheckout.jsx").read_text()
        assert "removeItem('storefront:mktp_ctx')" in src
        assert "removeItem('storefront:mktp_return')" in src
        assert "channel: 'store'" in src

    def test_ps6_channel_prop_in_use_checkout_form(self):
        src = (self.SF / "hooks" / "useCheckoutForm.js").read_text()
        assert "  channel,\n}) {" in src, "il hook accetta la prop channel"
        # prop esplicita vince, fallback legacy al flag di sessione
        assert "channel: channel ||" in src
        assert "storefront:mktp_ctx" in src

    def test_ps6_inline_event_timbro_condizionato(self):
        src = (self.SF / "components" / "checkout"
               / "InlineEventCheckout.jsx").read_text()
        # niente piu' timbro incondizionato: solo in vero contesto mktp
        assert "mktpContext" in src
        assert "if (!mktpContext) return;" in src
        assert "channel: mktpContext ? 'marketplace' : 'store'" in src
        # la landing calcola la provenienza reale e passa la prop
        elp = (self.SF / "EventLandingPage.js").read_text()
        assert "computeMktpContext" in elp
        assert "aurya:nav:prev" in elp
        assert "mktpContext={mktpCtx}" in elp

    # ── 5. cancel page: funnel + copy onesta + niente importo ────────

    def test_ps6_cancel_page_funnel(self):
        crp = (self.SF / "CheckoutResultPage.js").read_text()
        cancel = crp.split("export function CheckoutCancelPage")[1]
        assert "mktp_return" in cancel       # CTA "Riprova: torna al ritiro"
        assert "cancelRetryRetreat" in cancel
        assert "hideAmount" in cancel        # niente totale-ordine spacciato per caparra

    def test_ps6_cancel_copy_onesta_x4(self):
        import json as _json
        for lang in ("it", "en", "de", "fr"):
            loc = _json.loads((FRONTEND_SRC / "locales" / lang
                               / "storefront.json").read_text())
            cr = loc["checkoutResult"]
            desc = cr["cancelDesc"]
            # la vecchia promessa "sarai contattato per procedere" e' via
            assert "contattato" not in desc and "contacted" not in desc \
                and "kontaktiert" not in desc and "contacté" not in desc, \
                f"{lang}: la cancel page non deve promettere ricontatti su un draft"
            for key in ("cancelRetryRetreat", "backToRetreat", "backToHome"):
                assert key in cr, f"{lang}: manca checkoutResult.{key}"
            for key in ("title", "body", "tempTitle", "tempBody",
                        "ctaAccount", "ctaOperator"):
                assert key in cr["payUnavailable"], \
                    f"{lang}: manca payUnavailable.{key}"

    # ── 6. success + breadcrumb: mai label bugiarde ──────────────────

    def test_ps6_success_ritorno_onesto(self):
        crp = (self.SF / "CheckoutResultPage.js").read_text()
        success = crp.split("export function CheckoutSuccessPage")[1] \
                     .split("export function")[0]
        # mktp_return quando esiste, label neutra "Torna alla home" altrimenti
        assert "mktp_return" in success
        assert "backToHome" in success and "backToRetreat" in success

    def test_ps6_breadcrumb_landing_onesto(self):
        elp = (self.SF / "EventLandingPage.js").read_text()
        # fase network: crumb "Aurya" → home, o /esplora-ritiri se anteprima
        assert "sitePhase === 'network'" in elp
        assert "/esplora-ritiri" in elp
        assert "breadcrumbRetreats" in elp

    # ── 9/10. attriti: avviso doppio via, ?checkout=1 con carrello vuoto ──

    def test_ps6_avviso_doppio_pannello_servizio(self):
        form = (self.SF / "components" / "checkout"
                / "CheckoutForm.jsx").read_text()
        assert "inlineServiceSelection" in form
        assert "needsSelection && !inlineServiceSelection" in form
        inline = (self.SF / "components" / "checkout"
                  / "InlineServiceCheckout.jsx").read_text()
        assert "inlineServiceSelection" in inline

    def test_ps6_checkout_param_carrello_vuoto(self):
        page = (self.SF / "StorefrontPage.js").read_text()
        assert "checkoutEmptyCart" in page
        # il param viene strippato anche nel ramo vuoto (stripParam)
        assert "stripParam" in page

    @staticmethod
    def _db():
        """DB del server live (backend/.env), NON il test_db di default."""
        import re as _re
        import pymongo
        env = (BACKEND_DIR / ".env").read_text()
        mongo = _re.search(r'MONGO_URL="?([^"\n]+?)"?\n', env).group(1)
        name = _re.search(r'DB_NAME="?([^"\n]+?)"?\n', env).group(1)
        return pymongo.MongoClient(mongo)[name]


class TestProfiloPv1:
    """PV1 (PROFILO_VERIFICATO_PIANO_2026-07) — foto solide.

    Guardie: MIME map canonica nei chiamanti, filename NON deterministico
    per cover/ritratto/logo (sostituzione mai in cache) + cleanup dei
    vecchi file, HEIC accettato e convertito WebP, limite 2MB ancora
    attivo, helper compressImage presente nelle superfici frontend.
    """

    UPLOADS = BACKEND_DIR / "uploads"

    # ── infrastruttura live (stessi helper dei cicli TW/RS/PN/LM) ────

    _admin_token_cache = None

    @classmethod
    def _admin_headers(cls):
        import pytest
        if cls._admin_token_cache:
            return {"Authorization": f"Bearer {cls._admin_token_cache}"}
        r = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@demo.com", "password": "demo1234"}, timeout=10)
        if r.status_code != 200:
            pytest.skip("demo login unavailable (rate limit?)")
        cls._admin_token_cache = r.json()["access_token"]
        return {"Authorization": f"Bearer {cls._admin_token_cache}"}

    @staticmethod
    def _db():
        import re as _re
        import pymongo
        env = (BACKEND_DIR / ".env").read_text()
        mongo = _re.search(r'MONGO_URL="?([^"\n]+?)"?\n', env).group(1)
        name = _re.search(r'DB_NAME="?([^"\n]+?)"?\n', env).group(1)
        return pymongo.MongoClient(mongo)[name]

    @classmethod
    def _org_id(cls):
        r = requests.get(f"{BASE_URL}/api/organizations/current",
                         headers=cls._admin_headers(), timeout=10)
        assert r.status_code == 200
        return r.json()["id"]

    @staticmethod
    def _png_bytes(size=(900, 500), color=(60, 120, 90)):
        import io
        from PIL import Image
        buf = io.BytesIO()
        Image.new("RGB", size, color).save(buf, format="PNG")
        return buf.getvalue()

    @classmethod
    def _snapshot_local(cls, url):
        """(path, bytes) del file locale dietro un URL /uploads/*, o None."""
        if not url or not str(url).startswith("/uploads/"):
            return None
        path = cls.UPLOADS / str(url)[len("/uploads/"):]
        if path.is_file():
            return path, path.read_bytes()
        return None

    # ── 1. MIME map canonica (il bug "image/jpg") ────────────────────

    def test_mime_map_no_fstring_ext(self):
        """Nessun chiamante costruisce più il MIME con f"image/{ext}"
        (produceva "image/jpg" → ottimizzazione WebP saltata)."""
        routers = BACKEND_DIR / "routers"
        offenders = []
        for p in routers.glob("*.py"):
            if 'f"image/{ext' in p.read_text():
                offenders.append(p.name)
        assert offenders == [], f"MIME da estensione grezza in: {offenders}"

    def test_mime_map_helper_used(self):
        storage = (BACKEND_DIR / "services" / "object_storage.py").read_text()
        assert "def content_type_for_ext" in storage
        assert '".jpg": "image/jpeg"' in storage
        for router in ("organizations.py", "products.py",
                       "event_occurrences.py"):
            src = (BACKEND_DIR / "routers" / router).read_text()
            assert "content_type_for_ext" in src, router

    # ── 2. filename non deterministico + cleanup (bug sostituzione) ──

    def test_random_suffix_in_source(self):
        """Cover, ritratto e logo org usano il pattern gallery
        {org_id}-{uuid4[:10]}{ext}: URL nuovo a ogni upload."""
        src = (BACKEND_DIR / "routers" / "organizations.py").read_text()
        occurrences = src.count('-{uuid.uuid4().hex[:10]}{ext}')
        assert occurrences >= 4, occurrences  # logo, cover, ritratto, gallery
        storage = (BACKEND_DIR / "services" / "object_storage.py").read_text()
        assert "def delete_public_uploads" in storage
        assert "delete_objects" in storage  # simmetria S3 del cleanup

    def test_cover_replacement_new_url_old_file_gone(self):
        """Due upload cover consecutivi → URL DIVERSI e il vecchio file
        rimosso da uploads/ (riproduzione HTTP del bug sostituzione)."""
        import pytest
        headers = self._admin_headers()
        org_id = self._org_id()
        db = self._db()
        org = db.organizations.find_one({"id": org_id},
                                        {"public_profile.cover_url": 1})
        original_url = ((org or {}).get("public_profile")
                        or {}).get("cover_url")
        original_file = self._snapshot_local(original_url)
        try:
            urls = []
            for color in ((200, 30, 30), (30, 30, 200)):
                r = requests.post(
                    f"{BASE_URL}/api/organizations/current/public-profile/cover",
                    headers=headers, timeout=20,
                    files={"file": ("guardia-pv1.png",
                                    self._png_bytes(color=color),
                                    "image/png")})
                if r.status_code == 429:
                    pytest.skip("rate limit cover raggiunto (rerun <1min)")
                assert r.status_code == 200, r.text
                urls.append(r.json()["cover_url"])
            first, second = urls
            assert first != second, "URL cover identico: sostituzione in cache"
            assert f"{org_id}-" in first.rsplit("/", 1)[-1]
            first_local = self.UPLOADS / first[len("/uploads/"):]
            second_local = self.UPLOADS / second[len("/uploads/"):]
            assert not first_local.exists(), "vecchio file cover non rimosso"
            assert second_local.exists(), "nuovo file cover mancante"
        finally:
            # ripristino com'era: file originale (se locale) + puntatore DB
            for p in (self.UPLOADS / "profile-covers").glob(f"{org_id}*"):
                try:
                    p.unlink()
                except OSError:
                    pass
            if original_file:
                path, data = original_file
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            db.organizations.update_one(
                {"id": org_id},
                {"$set": {"public_profile.cover_url": original_url}})

    # ── 3. HEIC accettato e convertito WebP ──────────────────────────

    def test_heic_upload_converted_to_webp(self):
        import io
        import pytest
        from PIL import Image
        heif = pytest.importorskip("pillow_heif")
        heif.register_heif_opener()
        headers = self._admin_headers()
        org_id = self._org_id()
        db = self._db()
        org = db.organizations.find_one({"id": org_id},
                                        {"public_profile.portrait_url": 1})
        original_url = ((org or {}).get("public_profile")
                        or {}).get("portrait_url")
        original_file = self._snapshot_local(original_url)
        buf = io.BytesIO()
        Image.new("RGB", (2200, 1300), (90, 60, 120)).save(buf, format="HEIF")
        try:
            r = requests.post(
                f"{BASE_URL}/api/organizations/current/public-profile/portrait",
                headers=headers, timeout=20,
                files={"file": ("iphone-pv1.heic", buf.getvalue(),
                                "image/heic")})
            if r.status_code == 429:
                pytest.skip("rate limit portrait raggiunto (rerun <1min)")
            assert r.status_code == 200, r.text
            url = r.json()["portrait_url"]
            assert url.endswith(".webp"), url  # convertito, mai .heic servito
            saved = self.UPLOADS / url[len("/uploads/"):]
            assert saved.is_file()
            img = Image.open(io.BytesIO(saved.read_bytes()))
            assert img.format == "WEBP"
            assert max(img.size) <= 1600  # resize S6 applicato
        finally:
            for p in (self.UPLOADS / "profile-portraits").glob(f"{org_id}*"):
                try:
                    p.unlink()
                except OSError:
                    pass
            if original_file:
                path, data = original_file
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            db.organizations.update_one(
                {"id": org_id},
                {"$set": {"public_profile.portrait_url": original_url}})

    def test_heic_in_whitelists(self):
        for router in ("organizations.py", "products.py",
                       "event_occurrences.py"):
            src = (BACKEND_DIR / "routers" / router).read_text()
            assert '".heic"' in src, router
            assert "image/heic" in src, router
        req = (BACKEND_DIR / "requirements.txt").read_text()
        assert "pillow-heif" in req
        storage = (BACKEND_DIR / "services" / "object_storage.py").read_text()
        assert "register_heif_opener" in storage
        assert "image/heic" in storage  # in _OPTIMIZE_TYPES
        assert "_FORCE_CONVERT_TYPES" in storage  # heic mai servito com'è

    # ── 4. cintura 2MB ancora attiva ─────────────────────────────────

    def test_oversize_still_rejected(self):
        import pytest
        headers = self._admin_headers()
        blob = b"\x00" * (2 * 1024 * 1024 + 1)
        r = requests.post(
            f"{BASE_URL}/api/organizations/current/public-profile/cover",
            headers=headers, timeout=20,
            files={"file": ("troppo-grande.png", blob, "image/png")})
        if r.status_code == 429:
            pytest.skip("rate limit cover raggiunto (rerun <1min)")
        assert r.status_code == 400
        assert "2MB" in r.json()["detail"]

    # ── 5. messaggio 429 leggibile ───────────────────────────────────

    def test_429_has_detail_key(self):
        """L'handler slowapi custom risponde con detail E error, così
        il toast del frontend mostra il messaggio vero."""
        server = (BACKEND_DIR / "server.py").read_text()
        assert "_rate_limit_handler" in server
        assert '"detail": msg' in server
        assert '"error": msg' in server

    # ── 6. helper compressImage nelle superfici frontend ─────────────

    def test_compress_helper_exists(self):
        helper = (FRONTEND_SRC / "lib" / "compressImage.js").read_text()
        assert "createImageBitmap" in helper
        assert "imageOrientation" in helper           # EXIF from-image
        assert "'image/webp'" in helper
        assert "'image/jpeg'" in helper               # fallback Safari
        assert "return file" in helper                # fail-safe: mai bloccare

    def test_compress_helper_wired_in_api_wrappers(self):
        """La compressione avviene PRIMA della FormData in TUTTI i
        wrapper API di upload immagine (quindi in ogni superficie)."""
        for api_file in ("products.js", "orgBranding.js", "stores.js",
                         "storeSettings.js", "eventOccurrences.js"):
            src = (FRONTEND_SRC / "api" / api_file).read_text()
            assert "compressImage" in src, api_file
            assert "await compressImage(file)" in src, api_file

    def test_profile_page_compresses_and_resets(self):
        page = (FRONTEND_SRC / "features" / "settings"
                / "PublicProfilePage.js").read_text()
        assert "compressImage" in page
        assert page.count("e.target.value = ''") >= 3  # cover+ritratto+gallery
        assert 'accept="image/*"' in page
        assert "max 2MB" not in page                   # copy percepito rimosso
        assert "optimizing" in page                    # stato "Ottimizzo la foto"

    def test_image_inputs_accept_any_image(self):
        surfaces = (
            "features/settings/PublicProfilePage.js",
            "features/stores/components/OrgBrandingDialog.jsx",
            "features/stores/StoresPage.js",
            "features/services/ServiceWizard.js",
            "features/listino/ListinoPage.js",
            "features/physicals/PhysicalWizard.js",
            "features/digitals/DigitalWizard.js",
            "features/reservations/ReservationWizard.js",
            "features/events/EventWizard.js",
            "features/events/EventDashboardPage.js",
        )
        for rel in surfaces:
            src = (FRONTEND_SRC / Path(rel)).read_text()
            assert 'accept="image/*"' in src, rel
            assert 'accept=".jpg' not in src, rel


class TestProfiloPv2:
    """PV2 (PROFILO_VERIFICATO_PIANO_2026-07) — intervista al system admin.

    Guardie: PUT admin (bozza → pubblica → verified_at timbrato UNA volta
    → spubblica → azzerato), 403 per non-sysadmin, video YouTube
    normalizzato all'URL canonico (422 per host estranei), PATCH
    self-service che IGNORA interview, pubblico che espone l'intervista
    SOLO se pubblicata (has_interview coerente), interview_status in
    _org_summary, editor operatore sostituito dal pannello informativo.
    """

    _sys_token_cache = None
    _op_token_cache = None

    # ── infrastruttura live (stessi helper di TestProfiloPv1) ────────

    @classmethod
    def _sys_headers(cls):
        import pytest
        if cls._sys_token_cache:
            return {"Authorization": f"Bearer {cls._sys_token_cache}"}
        for pwd in ("DevLocal1234!", "demo1234"):
            r = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": "sysadmin@demo.com", "password": pwd}, timeout=10)
            if r.status_code == 200:
                cls._sys_token_cache = r.json()["access_token"]
                return {"Authorization": f"Bearer {cls._sys_token_cache}"}
        pytest.skip("sysadmin login unavailable (rate limit?)")

    @classmethod
    def _op_headers(cls):
        import pytest
        if cls._op_token_cache:
            return {"Authorization": f"Bearer {cls._op_token_cache}"}
        r = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@demo.com", "password": "demo1234"}, timeout=10)
        if r.status_code != 200:
            pytest.skip("demo login unavailable (rate limit?)")
        cls._op_token_cache = r.json()["access_token"]
        return {"Authorization": f"Bearer {cls._op_token_cache}"}

    @staticmethod
    def _db():
        import re as _re
        import pymongo
        env = (BACKEND_DIR / ".env").read_text()
        mongo = _re.search(r'MONGO_URL="?([^"\n]+?)"?\n', env).group(1)
        name = _re.search(r'DB_NAME="?([^"\n]+?)"?\n', env).group(1)
        return pymongo.MongoClient(mongo)[name]

    @classmethod
    def _org_id(cls):
        r = requests.get(f"{BASE_URL}/api/organizations/current",
                         headers=cls._op_headers(), timeout=10)
        assert r.status_code == 200
        return r.json()["id"]

    _IV_FIELDS = ("interview", "interview_video_url",
                  "interview_published", "interview_verified_at")

    @classmethod
    def _snapshot_interview(cls, db, org_id):
        """{campo: valore} SOLO dei campi presenti (assenti → da $unset)."""
        org = db.organizations.find_one({"id": org_id},
                                        {"public_profile": 1}) or {}
        pp = org.get("public_profile") or {}
        return {f: pp[f] for f in cls._IV_FIELDS if f in pp}

    @classmethod
    def _restore_interview(cls, db, org_id, snap):
        ops = {}
        sets = {f"public_profile.{f}": v for f, v in snap.items()}
        unsets = {f"public_profile.{f}": ""
                  for f in cls._IV_FIELDS if f not in snap}
        if sets:
            ops["$set"] = sets
        if unsets:
            ops["$unset"] = unsets
        if ops:
            db.organizations.update_one({"id": org_id}, ops)

    UA = {"User-Agent": "Mozilla/5.0 (Macintosh) Chrome/126 Safari/537.36"}

    def _public_profile(self):
        r = requests.get(f"{BASE_URL}/api/public/operator/masseria-demo",
                         headers=self.UA, timeout=10)
        assert r.status_code == 200, r.text
        return r.json()

    def _member_row(self):
        r = requests.get(f"{BASE_URL}/api/public/network/members",
                         headers=self.UA, timeout=10)
        assert r.status_code == 200
        rows = [m for m in r.json()["items"] if m["slug"] == "masseria-demo"]
        return rows[0] if rows else None

    def _summary_row(self, org_id):
        r = requests.get(f"{BASE_URL}/api/admin/organizations",
                         headers=self._sys_headers(),
                         params={"limit": 200}, timeout=10)
        assert r.status_code == 200
        rows = [o for o in r.json()["items"] if o["id"] == org_id]
        assert rows, "org demo assente dalla lista admin"
        return rows[0]

    # ── 1. ciclo di vita completo: bozza → pubblica → spubblica ─────

    def test_admin_put_full_lifecycle(self):
        sys_h = self._sys_headers()
        org_id = self._org_id()
        db = self._db()
        snap = self._snapshot_interview(db, org_id)
        url = f"{BASE_URL}/api/admin/organizations/{org_id}/interview"
        body = {"items": [{"question": "Guardia PV2?",
                           "answer": "Risposta integrale PV2."}],
                "video_url": "https://youtu.be/dQw4w9WgXcQ",
                "published": False}
        try:
            # BOZZA: salvata ma invisibile al pubblico
            r = requests.put(url, headers=sys_h, json=body, timeout=10)
            assert r.status_code == 200, r.text
            assert r.json()["verified_at"] is None
            pub = self._public_profile()
            assert pub["interview"] == []
            assert pub["interview_video_url"] is None
            assert pub["interview_verified_at"] is None
            assert self._summary_row(org_id)["interview_status"] == "draft"
            member = self._member_row()
            if member:
                assert member["has_interview"] is False

            # GET admin: l'editor ricarica lo stato (bozza inclusa)
            r = requests.get(url, headers=sys_h, timeout=10)
            assert r.status_code == 200
            state = r.json()
            assert state["items"][0]["question"] == "Guardia PV2?"
            assert state["published"] is False

            # PUBBLICA: verified_at timbrato
            body["published"] = True
            r = requests.put(url, headers=sys_h, json=body, timeout=10)
            assert r.status_code == 200, r.text
            first_stamp = r.json()["verified_at"]
            assert first_stamp

            # ri-salvataggio da pubblicata: il timbro NON cambia
            r = requests.put(url, headers=sys_h, json=body, timeout=10)
            assert r.json()["verified_at"] == first_stamp

            # pubblico: intervista + video canonico + timbro
            pub = self._public_profile()
            assert pub["interview"][0]["question"] == "Guardia PV2?"
            assert (pub["interview_video_url"]
                    == "https://www.youtube.com/watch?v=dQw4w9WgXcQ")
            assert pub["interview_verified_at"] == first_stamp
            assert self._summary_row(org_id)["interview_status"] == "published"
            member = self._member_row()
            if member:
                assert member["has_interview"] is True

            # SPUBBLICA: timbro azzerato, pubblico ripulito
            body["published"] = False
            r = requests.put(url, headers=sys_h, json=body, timeout=10)
            assert r.status_code == 200
            assert r.json()["verified_at"] is None
            pub = self._public_profile()
            assert pub["interview"] == []
            assert pub["interview_verified_at"] is None
            member = self._member_row()
            if member:
                assert member["has_interview"] is False

            # RIMUOVI: items vuoti → stato none in lista
            r = requests.put(url, headers=sys_h, timeout=10,
                             json={"items": [], "video_url": None,
                                   "published": False})
            assert r.status_code == 200
            assert self._summary_row(org_id)["interview_status"] == "none"
        finally:
            self._restore_interview(db, org_id, snap)

    # ── 2. solo il system admin ──────────────────────────────────────

    def test_put_requires_system_admin(self):
        op_h = self._op_headers()
        org_id = self._org_id()
        url = f"{BASE_URL}/api/admin/organizations/{org_id}/interview"
        r = requests.put(url, headers=op_h, timeout=10,
                         json={"items": [], "published": False})
        assert r.status_code == 403
        r = requests.get(url, headers=op_h, timeout=10)
        assert r.status_code == 403

    # ── 3. video: normalizzazione YouTube + rifiuto host estranei ────

    def test_video_url_normalized_and_rejected(self):
        sys_h = self._sys_headers()
        org_id = self._org_id()
        db = self._db()
        snap = self._snapshot_interview(db, org_id)
        url = f"{BASE_URL}/api/admin/organizations/{org_id}/interview"
        canonical = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        accepted = (
            "https://youtu.be/dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ?t=42",
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ&ab_channel=x",
            "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://www.youtube.com/shorts/dQw4w9WgXcQ",
        )
        rejected = (
            "https://vimeo.com/123456789",
            "https://example.com/watch?v=dQw4w9WgXcQ",
            "https://youtube.com.evil.io/watch?v=dQw4w9WgXcQ",
            "non-un-url",
        )
        try:
            for raw in accepted:
                r = requests.put(url, headers=sys_h, timeout=10,
                                 json={"items": [], "video_url": raw,
                                       "published": False})
                assert r.status_code == 200, (raw, r.text)
                assert r.json()["video_url"] == canonical, raw
            for raw in rejected:
                r = requests.put(url, headers=sys_h, timeout=10,
                                 json={"items": [], "video_url": raw,
                                       "published": False})
                assert r.status_code == 422, (raw, r.status_code)
        finally:
            self._restore_interview(db, org_id, snap)

    # ── 4. regole di validazione ereditate dal vecchio PATCH ─────────

    def test_items_rules_max12_lengths_empty_dropped(self):
        sys_h = self._sys_headers()
        org_id = self._org_id()
        db = self._db()
        snap = self._snapshot_interview(db, org_id)
        url = f"{BASE_URL}/api/admin/organizations/{org_id}/interview"
        items = [{"question": f"D{i}? " + "q" * 300,
                  "answer": "a" * 3000} for i in range(15)]
        items.append({"question": "Solo domanda", "answer": "  "})
        try:
            r = requests.put(url, headers=sys_h, timeout=10,
                             json={"items": items, "published": False})
            assert r.status_code == 200, r.text
            saved = r.json()["items"]
            assert len(saved) == 12                      # max 12, vuote fuori
            assert all(len(qa["question"]) <= 200 for qa in saved)
            assert all(len(qa["answer"]) <= 2500 for qa in saved)
        finally:
            self._restore_interview(db, org_id, snap)

    # ── 5. il self-service è chiuso (retrocompat: ignorato, no errore) ─

    def test_patch_self_service_ignores_interview(self):
        op_h = self._op_headers()
        org_id = self._org_id()
        db = self._db()
        snap = self._snapshot_interview(db, org_id)
        before = snap.get("interview")
        # payload con SOLO interview: il caso peggiore del client vecchio
        r = requests.patch(
            f"{BASE_URL}/api/organizations/current/public-profile",
            headers=op_h, timeout=15,
            json={"interview": [{"question": "INTRUSO",
                                 "answer": "Self-service chiuso."}]})
        assert r.status_code == 200, r.text          # niente 4xx: ignorato
        org = db.organizations.find_one({"id": org_id}, {"public_profile": 1})
        after = (org.get("public_profile") or {}).get("interview")
        assert after == before, "il PATCH self-service ha scritto interview"

    def test_patch_source_no_longer_writes_interview(self):
        src = (BACKEND_DIR / "routers" / "organizations.py").read_text()
        assert 'updates["public_profile.interview"]' not in src

    # ── 6. superfici frontend: editor via, pannello invito al suo posto ─

    def test_operator_editor_replaced_by_invite_panel(self):
        page = (FRONTEND_SRC / "features" / "settings"
                / "PublicProfilePage.js").read_text()
        assert "payload.interview" not in page        # non si invia più
        assert "interview-invite-panel" in page       # pannello informativo
        assert "interviewInviteTitle" in page
        assert "mailto:info@aurya.life" in page       # CTA contatto
        assert "set('interview'" not in page          # niente campi compilabili

    def test_admin_tab_registered(self):
        tab = (FRONTEND_SRC / "features" / "admin"
               / "InterviewsTab.js").read_text()
        assert "getOrgInterview" in tab
        assert "setOrgInterview" in tab
        assert "ytVideoId" in tab                     # anteprima ID video
        admin_page = (FRONTEND_SRC / "features" / "admin"
                      / "AdminPage.js").read_text()
        assert "InterviewsTab" in admin_page
        assert 'value="interviews"' in admin_page

    def test_invite_panel_i18n_x4(self):
        import json
        for lang in ("it", "en", "de", "fr"):
            data = json.loads(
                (FRONTEND_SRC / "locales" / lang / "settings.json")
                .read_text())
            pp = data.get("publicProfile") or {}
            for key in ("interviewInviteTitle", "interviewInviteBody",
                        "interviewInviteCta"):
                assert pp.get(key), f"{lang}: publicProfile.{key} mancante"
            # le chiavi del vecchio editor self-service sono sparite
            assert "interviewAdd" not in pp, lang

    # ── 7. interview_status esposto dalla lista admin ────────────────

    def test_org_summary_has_interview_status(self):
        r = requests.get(f"{BASE_URL}/api/admin/organizations",
                         headers=self._sys_headers(),
                         params={"limit": 50}, timeout=10)
        assert r.status_code == 200
        items = r.json()["items"]
        assert items
        for row in items:
            assert row["interview_status"] in ("none", "draft", "published")
            assert "interview_verified_at" in row


class TestProfiloPv3:
    """PV3 (PROFILO_VERIFICATO_PIANO_2026-07) — pagina intervista pubblica.

    Guardie: rotta /o/:slug/intervista registrata, embed SOLO
    youtube-nocookie (mai youtube.com/embed in tutto il frontend),
    redirect al profilo quando l'intervista non è pubblicata, testata
    identitaria CONDIVISA col profilo (stesso componente, slot badge
    PV4 previsto), blocco compatto con bottone sul profilo, link nuovo
    dalla pagina rete, fascia "Continua a scoprire", i18n x4.
    """

    PAGE = FRONTEND_SRC / "features" / "storefront" / "OperatorInterviewPage.js"
    PROFILE = FRONTEND_SRC / "features" / "storefront" / "OperatorProfilePage.js"
    HEADER = (FRONTEND_SRC / "features" / "storefront" / "components"
              / "OperatorIdentityHeader.jsx")

    # ── 1. rotta registrata dentro le rotte /o/ ──────────────────────

    def test_route_registered(self):
        app = (FRONTEND_SRC / "App.js").read_text()
        assert 'path="/o/:org_slug/intervista"' in app
        assert "OperatorInterviewPage" in app

    # ── 2. embed: youtube-nocookie e MAI youtube.com/embed diretto ───

    def test_embed_nocookie_only(self):
        page = self.PAGE.read_text()
        assert "youtube-nocookie.com/embed" in page
        for f in FRONTEND_SRC.rglob("*.js"):
            src = f.read_text()
            assert "www.youtube.com/embed" not in src, f
            assert "//youtube.com/embed" not in src, f

    def test_video_lazy_titled_with_poster(self):
        page = self.PAGE.read_text()
        assert 'loading="lazy"' in page
        assert "interviewVideoTitle" in page        # title accessibile
        assert "i.ytimg.com/vi/" in page            # poster/facade pre-play

    # ── 3. non pubblicata → redirect al profilo, nessun 404 crudo ────

    def test_redirect_when_not_published(self):
        page = self.PAGE.read_text()
        assert "if (notFound || !data || !published)" in page
        assert "Navigate" in page and "replace" in page
        assert "data.interview.length > 0" in page   # pubblicata = lista piena

    # ── 4. continuità: testata identitaria condivisa + slot badge PV4 ─

    def test_identity_header_shared(self):
        assert "OperatorIdentityHeader" in self.PAGE.read_text()
        assert "OperatorIdentityHeader" in self.PROFILE.read_text()
        header = self.HEADER.read_text()
        assert "verified-badge-slot" in header       # slot badge PV4 previsto
        assert "bg-black/45" in header               # stesso overlay cover

    def test_back_to_profile_always_visible(self):
        page = self.PAGE.read_text()
        assert "back-to-profile" in page
        assert "sticky" in page

    def test_continue_band_links_profile_anchors(self):
        page = self.PAGE.read_text()
        assert "continue-band" in page
        for anchor in ("#ritiri", "#listino", "#recensioni"):
            assert anchor in page, anchor

    # ── 5. profilo: blocco compatto con anteprima e bottone ──────────

    def test_profile_compact_block(self):
        profile = self.PROFILE.read_text()
        assert "interview-teaser" in profile
        assert "read-interview-cta" in profile
        assert "line-clamp-3" in profile             # anteprima con ellissi
        assert "data.interview[0].question" in profile
        assert "data.interview.map" not in profile   # niente Q&A integrali inline

    # ── 6. la pagina rete linka la pagina nuova ──────────────────────

    def test_network_page_links_interview_page(self):
        page = (FRONTEND_SRC / "features" / "network"
                / "NetworkOperatorsPage.js").read_text()
        assert "/intervista" in page

    # ── 7. i18n x4 ───────────────────────────────────────────────────

    def test_i18n_x4(self):
        import json
        for lang in ("it", "en", "de", "fr"):
            data = json.loads(
                (FRONTEND_SRC / "locales" / lang / "landings.json")
                .read_text())
            op = data.get("operator") or {}
            for key in ("interviewReadCta", "interviewBackToProfile",
                        "interviewByAurya", "interviewContinueTitle",
                        "interviewSeoTitle", "interviewVideoTitle"):
                assert op.get(key), f"{lang}: operator.{key} mancante"

    # ── 8. il prerender crawler risponde 200 anche sul path nuovo ────

    def test_seo_shell_serves_interview_path(self):
        r = requests.get(f"{BASE_URL}/__seo/o/masseria-demo/intervista",
                         timeout=10)
        assert r.status_code == 200


class TestProfiloPv4:
    """PV4 (PROFILO_VERIFICATO_PIANO_2026-07) — badge "Verificato Aurya".

    Guardie: /public/operators espone verified (bool, additivo) coerente
    con interview_verified_at (pubblica → True, spubblica → False, mai
    per i campioni), /network/members idem; componente VerifiedAuryaBadge
    con le due varianti (on-photo blur / on-light ori brand) e il glifo
    del logo esistente; montato e CONDIZIONATO nei 3 posti (hero
    condiviso profilo+intervista, card marketplace + quick view, card
    rete); ordine Verificato PRIMA di In evidenza; tooltip i18n x4.
    """

    UA = {"User-Agent": "Mozilla/5.0 (Macintosh) Chrome/126 Safari/537.36"}

    BADGE = FRONTEND_SRC / "components" / "VerifiedAuryaBadge.jsx"
    HEADER = (FRONTEND_SRC / "features" / "storefront" / "components"
              / "OperatorIdentityHeader.jsx")
    INDEX = FRONTEND_SRC / "features" / "storefront" / "OperatorsIndexPage.js"
    NETWORK = FRONTEND_SRC / "features" / "network" / "NetworkOperatorsPage.js"

    # ── helper: le due liste pubbliche, con verified sempre bool ─────

    def _operators_items(self):
        # preview=1: in pre-lancio la vetrina mostra i campioni (PL8),
        # l'anteprima /esplora-operatori mostra gli operatori VERI
        r = requests.get(f"{BASE_URL}/api/public/operators",
                         params={"preview": 1}, headers=self.UA, timeout=10)
        assert r.status_code == 200, r.text
        items = r.json()["items"]
        for i in items:
            assert isinstance(i.get("verified"), bool), i.get("org_slug")
        return items

    def _members_items(self):
        r = requests.get(f"{BASE_URL}/api/public/network/members",
                         headers=self.UA, timeout=10)
        assert r.status_code == 200, r.text
        items = r.json()["items"]
        for i in items:
            assert isinstance(i.get("verified"), bool), i.get("slug")
        return items

    def _demo_rows(self, org_name):
        ops = [i for i in self._operators_items() if i["name"] == org_name]
        mem = [i for i in self._members_items()
               if i["slug"] == "masseria-demo"]
        return (ops[0] if ops else None), (mem[0] if mem else None)

    # ── 1. HTTP: verified segue pubblica/spubblica dell'intervista ───

    def test_verified_follows_interview_publication(self):
        P = TestProfiloPv2
        sys_h = P._sys_headers()
        org_id = P._org_id()
        r = requests.get(f"{BASE_URL}/api/organizations/current",
                         headers=P._op_headers(), timeout=10)
        assert r.status_code == 200
        org_name = r.json()["name"]
        db = P._db()
        snap = P._snapshot_interview(db, org_id)
        url = f"{BASE_URL}/api/admin/organizations/{org_id}/interview"
        body = {"items": [{"question": "Guardia PV4?",
                           "answer": "Il badge segue il timbro."}],
                "published": True}
        try:
            # PUBBLICA → verified True su entrambe le liste
            r = requests.put(url, headers=sys_h, json=body, timeout=10)
            assert r.status_code == 200, r.text
            assert r.json()["verified_at"]
            op_row, mem_row = self._demo_rows(org_name)
            assert op_row is not None, "org demo assente da /public/operators"
            assert op_row["verified"] is True
            # nessun campione porta mai il sigillo (identita' redatta)
            for i in self._operators_items():
                if i.get("sample"):
                    assert i["verified"] is False
            if mem_row:
                assert mem_row["verified"] is True

            # SPUBBLICA → timbro azzerato, verified False ovunque
            body["published"] = False
            r = requests.put(url, headers=sys_h, json=body, timeout=10)
            assert r.status_code == 200
            assert r.json()["verified_at"] is None
            op_row, mem_row = self._demo_rows(org_name)
            assert op_row is not None
            assert op_row["verified"] is False
            if mem_row:
                assert mem_row["verified"] is False
        finally:
            P._restore_interview(db, org_id, snap)

    # ── 2. componente: varianti, glifo del logo, accessibilita' ─────

    def test_badge_component_variants_and_glyph(self):
        comp = self.BADGE.read_text()
        assert "on-photo" in comp and "on-light" in comp
        assert "backdrop-blur" in comp                # variante su foto
        assert "#8a7440" in comp and "#cbb578" in comp  # ori brand
        assert "logo-aurya" in comp                   # glifo dal logo, no asset nuovi
        assert "aria-label" in comp and "title=" in comp
        assert "verifiedBadge.tooltip" in comp

    # ── 3. montato e CONDIZIONATO nei 3 posti ────────────────────────

    def test_badge_mounted_and_gated_everywhere(self):
        header = self.HEADER.read_text()
        assert "VerifiedAuryaBadge" in header
        assert "data.interview_verified_at &&" in header   # mai incondizionato
        assert "verified-badge-slot" in header

        index = self.INDEX.read_text()
        assert "VerifiedAuryaBadge" in index
        assert "op.verified &&" in index
        # anche nella vista rapida (due montaggi nella card)
        assert index.count("<VerifiedAuryaBadge") >= 2

        network = self.NETWORK.read_text()
        assert "VerifiedAuryaBadge" in network
        assert "m.verified &&" in network

    # ── 4. ordine: Verificato PRIMA di In evidenza (hero e card) ─────

    def test_verified_before_featured(self):
        header = self.HEADER.read_text()
        assert (header.index("VerifiedAuryaBadge", header.index("return"))
                < header.index("calendar.featured"))
        index = self.INDEX.read_text()
        card = index[index.index("function OperatorCard"):]
        assert card.index("<VerifiedAuryaBadge") < card.index("calendar.featured")

    # ── 5. tooltip e testi i18n x4 ───────────────────────────────────

    def test_badge_i18n_x4(self):
        import json
        for lang in ("it", "en", "de", "fr"):
            data = json.loads(
                (FRONTEND_SRC / "locales" / lang / "landings.json")
                .read_text())
            vb = data.get("verifiedBadge") or {}
            for key in ("label", "short", "tooltip"):
                assert vb.get(key), f"{lang}: verifiedBadge.{key} mancante"


class TestProfiloPv5:
    """PV5 (PROFILO_VERIFICATO_PIANO_2026-07) — la landing /p/ "esiste"
    solo se ha contenuto; nessun servizio rimanda mai al vecchio store.

    Guardie: has_landing nel listino pubblico coerente col contenuto
    (racconto lungo o cover dedicata → True, senza → False, additivo);
    legacy_commerce (bool, additivo) sul payload landing /p/; gate del
    link "Vedi dettagli" su has_landing (OperatorProfilePage + link
    gemello in InlineServiceCheckout); landing servizi nel mondo snello
    dentro il guscio del profilo (MarketplaceShell, breadcrumb, back a
    /o/, niente StorefrontHeader/banner carrello store); CTA acquisto →
    checkout inline del profilo (persistCart + navigate /o/ con state
    expandService, consumato da OperatorProfilePage); handoff legacy
    /p/→/s/ INTATTO dietro il ramo profileWorld; i18n x4.
    """

    UA = {"User-Agent": "Mozilla/5.0 (Macintosh) Chrome/126 Safari/537.36"}

    PROFILE = FRONTEND_SRC / "features" / "storefront" / "OperatorProfilePage.js"
    LANDING = FRONTEND_SRC / "features" / "storefront" / "ProductLandingPage.js"
    INLINE = (FRONTEND_SRC / "features" / "storefront" / "components"
              / "checkout" / "InlineServiceCheckout.jsx")

    # ── helper: riga di listino pubblica del servizio demo ───────────

    def _listino_row(self, slug="seduta-di-reiki"):
        r = requests.get(f"{BASE_URL}/api/public/operator/masseria-demo",
                         headers=self.UA, timeout=10)
        assert r.status_code == 200, r.text
        rows = [x for x in r.json().get("listino", []) if x.get("slug") == slug]
        assert rows, f"servizio {slug} assente dal listino demo"
        return rows[0]

    def _demo_service(self, headers, slug="seduta-di-reiki"):
        r = requests.get(f"{BASE_URL}/api/products", headers=headers,
                         params={"limit": 200}, timeout=10)
        assert r.status_code == 200, r.text
        prods = r.json()
        rows = [p for p in prods if p.get("slug") == slug]
        assert rows, f"prodotto {slug} non trovato"
        return rows[0]

    def _patch_meta(self, headers, product, **fields):
        meta = {**(product.get("metadata") or {}), **fields}
        r = requests.patch(f"{BASE_URL}/api/products/{product['id']}",
                           headers=headers, json={"metadata": meta}, timeout=10)
        assert r.status_code == 200, r.text

    # ── 1. HTTP: has_landing segue il contenuto della landing ────────

    def test_has_landing_follows_content(self):
        op_h = TestProfiloPv2._op_headers()
        prod = self._demo_service(op_h)
        orig_meta = prod.get("metadata") or {}
        snap = {"long_description": orig_meta.get("long_description"),
                "cover_image_url": orig_meta.get("cover_image_url")}
        try:
            # senza contenuto → False (baseline demo)
            self._patch_meta(op_h, prod, long_description=None,
                             cover_image_url=None)
            assert self._listino_row()["has_landing"] is False
            # racconto lungo → True
            self._patch_meta(op_h, prod,
                             long_description="Racconto PV5", cover_image_url=None)
            assert self._listino_row()["has_landing"] is True
            # solo cover dedicata → True
            self._patch_meta(op_h, prod, long_description=None,
                             cover_image_url="/uploads/x.webp")
            assert self._listino_row()["has_landing"] is True
            # spazi bianchi non contano come contenuto
            self._patch_meta(op_h, prod, long_description="   ",
                             cover_image_url=None)
            assert self._listino_row()["has_landing"] is False
        finally:
            self._patch_meta(op_h, prod, **snap)

    def test_has_landing_bool_on_every_row(self):
        r = requests.get(f"{BASE_URL}/api/public/operator/masseria-demo",
                         headers=self.UA, timeout=10)
        assert r.status_code == 200
        for row in r.json().get("listino", []):
            assert isinstance(row.get("has_landing"), bool), row.get("slug")

    # ── 2. HTTP: la landing /p/ dichiara il mondo dell'org ───────────

    def test_landing_payload_exposes_legacy_commerce(self):
        r = requests.get(
            f"{BASE_URL}/api/public/products/masseria-demo/seduta-di-reiki",
            headers=self.UA, timeout=10)
        assert r.status_code == 200, r.text
        body = r.json()
        assert isinstance(body.get("legacy_commerce"), bool)
        # l'org demo e' nel mondo snello: il guscio profilo deve valere
        assert body["legacy_commerce"] is False

    # ── 3. scan: gate del bottone "Vedi dettagli" ────────────────────

    def test_view_details_gated_by_has_landing(self):
        page = self.PROFILE.read_text()
        assert "row.slug && row.has_landing && (" in page, \
            "il link Vedi dettagli deve essere condizionato a has_landing"
        inline = self.INLINE.read_text()
        assert "row.slug && row.has_landing && (" in inline, \
            "il link gemello nel pannello inline deve avere lo stesso gate"

    # ── 4. scan: landing servizi nel mondo snello senza varchi /s/ ───

    def test_service_landing_lives_in_profile_world(self):
        page = self.LANDING.read_text()
        # il mondo decide il guscio: flag org + tipo servizio
        assert "!data.legacy_commerce" in page
        assert "item_type === 'service'" in page
        # guscio profilo: shell marketplace + breadcrumb + back a /o/
        assert "MarketplaceShell" in page
        assert 'data-testid="landing-profile-breadcrumb"' in page
        assert "/o/${orgSlug}#listino" in page
        # niente header store né banner carrello store nel mondo snello
        assert "{!profileWorld && (\n        <StorefrontHeader" in page
        assert "{!profileWorld && cartCount > 0 && (" in page
        # il not-found riporta al profilo, non alla vetrina
        assert 'to={`/o/${orgSlug}`}' in page

    # ── 5. scan: CTA acquisto → checkout inline del profilo ──────────

    def test_cta_deep_links_profile_inline_checkout(self):
        page = self.LANDING.read_text()
        # la selezione persiste nello snapshot che idrata il profilo
        assert "persistCart(orgSlug, next)" in page
        assert ("navigate(`/o/${orgSlug}`, { state: { expandService: "
                "product.id } })") in page
        # il profilo consuma lo state: riga espansa + scroll all'ancora
        profile = self.PROFILE.read_text()
        assert "navState?.expandService" in profile
        assert "setExpandedService(row.product_id || row.slug || row.name)" \
            in profile
        assert 'id={`servizio-${row.slug || row.product_id}`}' in profile

    # ── 6. scan: handoff legacy /p/→/s/ intatto dietro il ramo ───────

    def test_legacy_handoff_intact_behind_flag(self):
        page = self.LANDING.read_text()
        # il ramo profileWorld esce PRIMA dell'handoff storico
        idx_guard = page.find("if (profileWorld) {")
        idx_handoff = page.find("navigate(`/s/${orgSlug}`, { state: { preloadCart } })")
        assert idx_guard != -1 and idx_handoff != -1
        assert idx_guard < idx_handoff, \
            "l'handoff legacy deve restare, gato dal ramo profileWorld"
        # il toast legacy col deep-link ?checkout=1 resta per lo store
        assert "navigate(`/s/${orgSlug}?checkout=1`)" in page

    # ── 7. i18n x4 ───────────────────────────────────────────────────

    def test_pv5_i18n_x4(self):
        import json as _json
        for lang in ("it", "en", "de", "fr"):
            data = _json.loads(
                (FRONTEND_SRC / "locales" / lang / "landings.json")
                .read_text())
            assert (data.get("operator") or {}).get("viewDetails"), \
                f"{lang}: operator.viewDetails mancante"
            assert (data.get("product") or {}).get("backToProfile"), \
                f"{lang}: product.backToProfile mancante"
