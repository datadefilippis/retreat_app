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
        """I due momenti LM1 esistono nella riga espansa e 'Tutte le
        impostazioni' resta il percorso avanzato."""
        page = self.PAGE.read_text()
        assert "Opzioni e varianti" in page
        assert "Prenotazione e incasso" in page
        assert "Tutte le impostazioni" in page
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
        # entrambe le strade di login arricchiscono la risposta
        assert router.count("**await newsletter_status(account[\"email\"])") == 2
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
