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
        assert "/operatori/${next}" in page
        # Dove dentro la barra, in versione fluida
        assert "<GeoSearchBar value={geoValue} onChange={setGeo} fluid />" in page
        # Distanza offerta solo con geo attivo (come il backend)
        assert '{geoValue && (' in page
        geobar = (FRONTEND_SRC / "features" / "storefront" / "components"
                  / "GeoSearchBar.jsx").read_text()
        assert "fluid = false" in geobar
