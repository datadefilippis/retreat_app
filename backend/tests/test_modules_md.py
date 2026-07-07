"""MD1 — attivazione automatica dei moduli dal piano commerciale.

Il fork aveva due strati mai riconciliati (subscription vs
organization_modules): signup fresco = menu vuoto. Da MD1 il
provision attiva/disattiva i moduli e lo startup riconcilia.
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


def test_provision_calls_module_activation_sync():
    """Il punto canonico dei cambi piano DEVE sincronizzare anche
    l'attivazione — non solo le subscription."""
    import inspect
    from services import plan_provisioning as pp
    src = inspect.getsource(pp.provision_commercial_plan)
    assert "sync_module_activation" in src


def test_sync_rule_disabled_suffix():
    """La regola: pricing plan `*_disabled` → modulo spento, tutto il
    resto acceso (default 'tutto attivo' del verticale)."""
    import inspect
    from services import plan_provisioning as pp
    src = inspect.getsource(pp.sync_module_activation)
    assert '_disabled' in src
    assert "upsert=True" in src


def test_startup_reconciles_existing_orgs():
    """Le org nate prima di MD1 vengono riallineate a ogni startup
    (idempotente, self-healing)."""
    src = (BACKEND_DIR / "server.py").read_text()
    assert "reconcile_all_module_activations" in src


def test_retreat_free_plan_enables_four_modules():
    """Il piano baseline attiva commerce/product_catalog/customers_light/
    cashflow_monitor e spegne ai_assistant (disabled)."""
    from services.seed_commercial_plans import RETREAT_COMMERCIAL_PLANS
    plan = next(p for p in RETREAT_COMMERCIAL_PLANS if p["slug"] == "retreat_free")
    mp = plan["module_plans"]
    enabled = {k for k, v in mp.items() if not str(v).endswith("_disabled")}
    disabled = {k for k, v in mp.items() if str(v).endswith("_disabled")}
    assert enabled == {"commerce", "product_catalog", "customers_light", "cashflow_monitor"}
    assert disabled == {"ai_assistant"}


class TestModuleOwnershipMd2:
    """MD2 — ogni feature post-fork dichiara il suo modulo."""

    def test_registry_covers_orphan_features(self):
        from services.module_access import MODULE_OWNERSHIP
        assert MODULE_OWNERSHIP == {
            "reviews": "commerce",
            "newsletter": "commerce",
            "outreach": "customers_light",
            "cashflow_analytics": "cashflow_monitor",
            "sales_stats": "product_catalog",
            "cross_sell": "customers_light",
        }

    def test_gates_wired_on_orphan_routers(self):
        """I router (o le route) delle feature orfane montano il gate."""
        import inspect
        from routers import outreach, cashflow, newsletter_forms, reviews, products
        for mod, feature in [(outreach, "outreach"),
                             (cashflow, "cashflow_analytics"),
                             (newsletter_forms, "newsletter")]:
            assert f'require_module("{feature}")' in inspect.getsource(mod)
        assert inspect.getsource(reviews).count('require_module("reviews")') >= 5
        assert 'require_module("sales_stats")' in inspect.getsource(products)
        ci_src = (BACKEND_DIR / "modules" / "customer_insights" / "router.py").read_text()
        assert 'require_module("cross_sell")' in ci_src

    def test_public_review_endpoints_not_gated(self):
        """Il flusso recensioni PUBBLICO (OTP/submit/lista) resta libero:
        il gate vale solo per la plancia admin."""
        import inspect
        from routers import reviews
        src = inspect.getsource(reviews)
        # le route pubbliche non hanno il gate nella loro firma
        public_block = src.split("# ── Pubblico")[1].split("# admin")[0] if "# admin" in src else src.split('@router.get("/reviews"')[0]
        # euristica: il gate compare solo insieme a require_admin
        for line_pair in zip(src.splitlines(), src.splitlines()[1:]):
            if 'require_module("reviews")' in line_pair[1]:
                assert "require_admin" in line_pair[0]


# ── MD4 — mai più promesse vuote nel pricing ────────────────────────────────
# Ogni chiave di features_display dei piani retreat DEVE dichiarare qui il
# suo enforcement. Una voce nuova senza enforcement rompe la CI: è il
# contratto fra ciò che vendiamo e ciò che il codice consegna.
#
# Tipi di enforcement:
#   ("limit", plan_slug, limit_key, expected)  → verificato sui seed pricing
#   ("platform", key, expected)                → platform_limits del piano
#   ("code", "puntatore")                      → funzionalità verificata da
#                                                altri test di questa suite
#   ("process", motivo)                        → impegno umano, non software

PROMISE_ENFORCEMENT = {
    # ── retreat_free ──
    "billing.features.retreat_unlimited_listings": ("limit", "commerce_retreat", "orders_monthly", -1),
    "billing.features.retreat_ecommerce":          ("limit", "commerce_retreat", "checkout_stripe", -1),
    "billing.features.retreat_product_types":      ("code", "models.product_types ITEM_TYPES (6 anime)"),
    "billing.features.retreat_public_page":        ("code", "routers.public /operator/{slug} + profilo PR1"),
    "billing.features.retreat_deposits_payments":  ("code", "payment_schedules ledger (caparra/saldo)"),
    "billing.features.retreat_payment_reminders":  ("code", "outreach payment_reminder + dunning"),
    "billing.features.retreat_participants":       ("code", "issued_tickets + Event Dashboard"),
    "billing.features.retreat_comms":              ("code", "ContactActions/outreach CF2"),
    "billing.features.retreat_newsletter":         ("code", "newsletter_forms + embed"),
    "billing.features.retreat_cashflow":           ("code", "/incassi + pagina Dati (cashflow_monitor)"),
    "billing.features.retreat_customers":          ("code", "customers_light CRM"),
    "billing.features.retreat_coupons":            ("code", "coupon_code sul checkout"),
    "billing.features.retreat_catalog_100":        ("limit", "product_catalog_retreat_free", "products", 100),
    "billing.features.retreat_stores_1":           ("limit", "commerce_retreat", "stores_max", 1),
    "billing.features.retreat_team_2":             ("platform", "team_members", 2),
    # ── retreat_pro ──
    "billing.features.retreat_everything_free":    ("code", "module_plans superset del free"),
    "billing.features.retreat_featured":           ("code", "MD3: directory_featured + boost/badge /public/retreats"),
    "billing.features.retreat_catalog_unlimited":  ("limit", "product_catalog_retreat_pro", "products", -1),
    "billing.features.retreat_stores_3":           ("limit", "commerce_retreat_pro", "stores_max", 3),
    "billing.features.retreat_team_5":             ("platform", "team_members", 5),
    "billing.features.retreat_priority_support":   ("process", "canale supporto dedicato"),
    # ── founding / partner ──
    "billing.features.retreat_everything_pro":     ("code", "module_plans identici al pro"),
    "billing.features.retreat_founding_free":      ("code", "price_monthly 0 + assegnazione admin"),
    "billing.features.retreat_founding_feedback":  ("process", "canale feedback founder"),
    "billing.features.retreat_zero_fee":           ("code", "transaction_fee_percent 0 (Stripe omette application_fee)"),
    "billing.features.retreat_no_monthly":         ("code", "price_monthly 0 sul piano partner"),
}


class TestPromiseEnforcementMd4:
    def _retreat_plans(self):
        from services.seed_commercial_plans import RETREAT_COMMERCIAL_PLANS
        return RETREAT_COMMERCIAL_PLANS

    def test_every_displayed_promise_has_enforcement(self):
        """La guardia centrale: voce nel pricing senza enforcement
        dichiarato = CI rossa. (È cosi' che retreat_customers_pro e
        retreat_featured 'solo testo' non succederanno piu'.)"""
        missing = []
        for plan in self._retreat_plans():
            for key in plan.get("features_display", []):
                if key not in PROMISE_ENFORCEMENT:
                    missing.append(f"{plan['slug']}: {key}")
        assert not missing, "Promesse senza enforcement dichiarato:\n" + "\n".join(missing)

    def test_limit_promises_match_seed_pricing(self):
        """Le promesse quantitative devono combaciare coi limiti REALI
        dei pricing plan seed (catalogo 100, store 3, ecc.)."""
        from services.seed_pricing import _TARGET_LIMITS
        errors = []
        for key, enf in PROMISE_ENFORCEMENT.items():
            if enf[0] != "limit":
                continue
            _, plan_slug, limit_key, expected = enf
            entry = _TARGET_LIMITS.get(plan_slug)
            if not entry:
                errors.append(f"{key}: pricing plan '{plan_slug}' inesistente")
                continue
            actual = entry[1].get(limit_key)
            if actual != expected:
                errors.append(f"{key}: {plan_slug}.{limit_key}={actual} != {expected}")
        assert not errors, "\n".join(errors)

    def test_platform_promises_match_plans(self):
        errors = []
        plans = {p["slug"]: p for p in self._retreat_plans()}
        checks = [("billing.features.retreat_team_2", "retreat_free", 2),
                  ("billing.features.retreat_team_5", "retreat_pro", 5)]
        for key, slug, expected in checks:
            actual = (plans[slug].get("platform_limits") or {}).get("team_members")
            if actual != expected:
                errors.append(f"{key}: {slug} team_members={actual} != {expected}")
        assert not errors, "\n".join(errors)

    def test_featured_promise_is_enforced_in_code(self):
        """retreat_featured non è piu' solo testo: FEATURED_PLAN_SLUGS
        esiste, il provision denormalizza, la directory usa il flag."""
        from services.plan_provisioning import FEATURED_PLAN_SLUGS
        assert FEATURED_PLAN_SLUGS == {"retreat_pro", "retreat_founding", "retreat_partner"}
        import inspect
        from services import plan_provisioning as pp
        assert "directory_featured" in inspect.getsource(pp.provision_commercial_plan)
        pub_src = (BACKEND_DIR / "routers" / "public.py").read_text()
        assert "directory_featured" in pub_src and '"featured"' in pub_src

    def test_empty_customers_pro_promise_stays_removed(self):
        """La voce 'Insight clienti avanzati' era vuota (limiti identici
        free/pro): non deve tornare nel seed."""
        for plan in self._retreat_plans():
            assert "billing.features.retreat_customers_pro" not in plan.get("features_display", []), plan["slug"]


class TestMarketplaceChannelGt1:
    """GT1 — il canale marketplace si incassa SOLO online (founder)."""

    def test_payload_accepts_channel(self):
        from routers.public import OrderRequestPayload
        assert "channel" in OrderRequestPayload.model_fields

    def test_order_stamped_with_sales_channel(self):
        import inspect
        from services import order_creation_service as ocs
        src = inspect.getsource(ocs.submit_order_from_storefront)
        assert "sales_channel" in src

    def test_mark_paid_blocked_for_marketplace_orders(self):
        """Il gestionale resta libero (store/manuale/POS), ma un ordine
        marketplace non si chiude con mark-paid: link di pagamento."""
        import inspect
        from services import order_service as osvc
        src = inspect.getsource(osvc.mark_order_paid)
        assert "marketplace_online_only" in src
        assert '"marketplace"' in src


class TestCalendarListingGt1b:
    """GT1b — nel calendario pubblico entrano SOLO ritiri prenotabili
    online all'istante: transaction_mode=direct E org con Stripe
    attivo e pronto. Il flusso 'richiesta prima' resta sullo store
    proprio dell'operatore."""

    PUB_SRC = (BACKEND_DIR / "routers" / "public.py").read_text()

    def test_listing_query_filters_direct_mode(self):
        """La query prodotti del listing pretende transaction_mode=direct."""
        assert '"transaction_mode": "direct"' in self.PUB_SRC

    def test_listing_gated_on_payment_readiness(self):
        """Le org senza payment connection attiva+pronta spariscono dal
        calendario (stessa condizione del checkout: mai un vicolo
        cieco di pagamento)."""
        assert "pay_ready" in self.PUB_SRC
        assert '"status": "active", "runtime_status": "ready"' in self.PUB_SRC

    def test_operator_home_warns_when_calendar_blocked(self):
        """L'operatore con ritiri pubblicati ma Stripe non collegato vede
        il banner che spiega perche' non compare nel calendario."""
        home = (BACKEND_DIR.parent / "frontend" / "src" / "features"
                / "dashboard" / "OperatorHome.js").read_text()
        assert "retreat_published" in home
        assert "stripe_connected" in home
        assert "calendar_blocked" in home

    def test_calendar_blocked_copy_in_four_languages(self):
        import json
        locales_dir = BACKEND_DIR.parent / "frontend" / "src" / "locales"
        for lang in ("it", "en", "de", "fr"):
            data = json.loads((locales_dir / lang / "dashboard.json").read_text())
            home = data.get("home") or {}
            for key in ("calendar_blocked_title", "calendar_blocked_body",
                        "calendar_blocked_cta"):
                assert home.get(key), f"{lang}: home.{key} mancante"


class TestFeeSaverGt2:
    """GT2 — il Pro si vende da solo quando conviene DAVVERO: banner
    in /incassi col transato Stripe del mese e il risparmio calcolato
    lato server. Mai sotto soglia, mai fuori dal piano Gratis."""

    CF_SRC = (BACKEND_DIR / "routers" / "cashflow.py").read_text()

    def test_fee_saver_in_cashflow_payload(self):
        assert '"fee_saver"' in self.CF_SRC

    def test_only_free_plan_and_real_numbers(self):
        """Solo sul Gratis, coi numeri del piano Pro presi dal SEED
        (non hardcoded doppi) e visibile solo a risparmio positivo."""
        assert '"retreat_free"' in self.CF_SRC
        assert "RETREAT_COMMERCIAL_PLANS" in self.CF_SRC
        assert "saving > 0" in self.CF_SRC

    def test_online_volume_excludes_manual_income(self):
        """Il transato conta SOLO Stripe: righe ledger 'paid' (il
        mark-paid manuale scrive 'paid_manual') e ordini col
        payment_intent 'collected' (lo stampa solo il checkout)."""
        assert 'status == "paid"' in self.CF_SRC
        assert '"collected"' in self.CF_SRC

    def test_banner_wired_in_incassi_page(self):
        page = (BACKEND_DIR.parent / "frontend" / "src" / "features"
                / "cashflow" / "IncassiPage.js").read_text()
        assert "fee_saver" in page
        assert "feeSaver?.show" in page or "feeSaver.show" in page
        assert "UpgradeDialog" in page

    def test_fee_saver_copy_in_four_languages(self):
        import json
        locales_dir = BACKEND_DIR.parent / "frontend" / "src" / "locales"
        for lang in ("it", "en", "de", "fr"):
            data = json.loads((locales_dir / lang / "common.json").read_text())
            cf = data.get("cashflow") or {}
            for key in ("feeSaverTitle", "feeSaverBody", "feeSaverCta"):
                assert cf.get(key), f"{lang}: cashflow.{key} mancante"


class TestFeaturedBoostGt3:
    """GT3 — la promessa Pro "In evidenza" diventa percepibile:
    strip in testa alla directory, priorita' nell'aggregatore
    operatori, badge sul profilo pubblico."""

    PUB_SRC = (BACKEND_DIR / "routers" / "public.py").read_text()
    FRONT = BACKEND_DIR.parent / "frontend" / "src" / "features" / "storefront"

    def test_featured_is_badge_not_duplicate_section(self):
        """Scelta founder: NIENTE sezione In evidenza separata (creava
        doppioni) — il featured e' il badge ✦ sulla card in lista."""
        assert '"featured_items"' not in self.PUB_SRC
        page = (self.FRONT / "RetreatsCalendarPage.js").read_text()
        assert "featured_items" not in page
        assert "item.featured" in page   # il badge MD3 resta

    def test_operators_index_prioritizes_featured(self):
        """L'aggregatore ordina i featured per primi e li marca."""
        assert 'not x["featured"]' in self.PUB_SRC
        page = (self.FRONT / "OperatorsIndexPage.js").read_text()
        assert "op.featured" in page

    def test_operator_profile_shows_badge(self):
        """Il payload del profilo espone il flag e la pagina lo mostra."""
        # il flag e' nel payload di public_operator_profile (dopo reviews_open)
        idx = self.PUB_SRC.index('"reviews_open"')
        assert '"featured"' in self.PUB_SRC[idx:idx + 400]
        page = (self.FRONT / "OperatorProfilePage.js").read_text()
        assert "data.featured" in page


class TestReviewNudgeGt4:
    """GT4 — recensioni-moat: ogni mark-paid manuale ricorda che gli
    incassi fuori piattaforma non generano recensioni verificate."""

    SRC_DIR = BACKEND_DIR.parent / "frontend" / "src"

    def test_nudge_on_all_manual_paid_sites(self):
        sites = [
            "features/cashflow/IncassiPage.js",
            "features/orders/OrdersPage.js",
            "features/events/EventDashboardPage.js",
        ]
        for rel in sites:
            src = (self.SRC_DIR / rel).read_text()
            assert "reviewNudge" in src, f"{rel}: nudge mancante"

    def test_nudge_copy_in_four_languages(self):
        import json
        for lang in ("it", "en", "de", "fr"):
            data = json.loads(
                (self.SRC_DIR / "locales" / lang / "common.json").read_text())
            assert (data.get("cashflow") or {}).get("reviewNudge"), \
                f"{lang}: cashflow.reviewNudge mancante"


class TestProfileFirstGt6:
    """GT6 — la scala del valore parte dalla vetrina: il profilo con
    bio accende /o/{slug} senza store, e /inizia lo mette al gradino 0."""

    ORG_SRC = (BACKEND_DIR / "routers" / "organizations.py").read_text()
    SRC_DIR = BACKEND_DIR.parent / "frontend" / "src"

    def test_profile_save_provisions_public_surface(self):
        """Salvare il profilo (con bio) assegna public_slug + flag
        published legacy: la vetrina esiste senza store."""
        assert "_ensure_public_surface" in self.ORG_SRC
        idx = self.ORG_SRC.index("async def _ensure_public_surface")
        block = self.ORG_SRC[idx:idx + 2500]
        assert "public_slug" in block
        assert "is_storefront_published" in block

    def test_onboarding_store_step_means_real_store(self):
        """Il gradino 0 NON deve spuntare 'store creato': lo step
        legge lo store vero, non il fallback public_slug."""
        idx = self.ORG_SRC.index('"store_created"')
        line = self.ORG_SRC[idx:idx + 60]
        assert "bool(store)" in line

    def test_inizia_checklist_is_profile_first(self):
        page = (self.SRC_DIR / "features" / "onboarding" / "IniziaPage.js").read_text()
        first = page.index("'profile_completed'")
        assert first < page.index("'stripe_connected'")
        assert first < page.index("'store_created'")

    def test_gt7_admin_sees_directory_eligibility(self):
        """GT7 — l'operatore vede in admin perche' un ritiro non e' nel
        calendario: admin/list calcola directory_listed + reasons con
        le STESSE condizioni del gate GT1b."""
        src = (BACKEND_DIR / "routers" / "event_occurrences.py").read_text()
        assert '"directory_listed"' in src
        for code in ("mode_request", "stripe_not_ready",
                     "product_not_published", "occurrence_not_published",
                     "no_public_page"):
            assert f'"{code}"' in src, f"reason {code} mancante"
        # stessa condizione Stripe del checkout/listing
        assert '"status": "active", "runtime_status": "ready"' in src

    def test_gt7_wizard_and_grid_show_directory_status(self):
        base = BACKEND_DIR.parent / "frontend" / "src"
        hint = (base / "components" / "DirectoryListingHint.jsx").read_text()
        assert "request" in hint and "useStripeReadiness" in hint
        for rel in ("features/events/EventWizard.js",
                    "features/events/EventDashboardPage.js"):
            assert "DirectoryListingHint" in (base / rel).read_text(), rel
        grid = (base / "features" / "events" / "components" / "EventsGrid.js").read_text()
        assert "directory_listed" in grid and "directory_reasons" in grid

    def test_gt7_copy_in_four_languages(self):
        import json
        base = BACKEND_DIR.parent / "frontend" / "src" / "locales"
        for lang in ("it", "en", "de", "fr"):
            common = json.loads((base / lang / "common.json").read_text())
            dh = common.get("directoryHint") or {}
            assert dh.get("request") and dh.get("stripeNote"), f"{lang}: directoryHint"
            products = json.loads((base / lang / "products.json").read_text())
            d = ((products.get("grids") or {}).get("event") or {}).get("directory") or {}
            assert d.get("notListed"), f"{lang}: notListed"
            for code in ("mode_request", "stripe_not_ready",
                         "product_not_published", "occurrence_not_published",
                         "no_public_page"):
                assert (d.get("reason") or {}).get(code), f"{lang}: reason.{code}"

    def test_onboarding_copy_in_four_languages(self):
        """de/fr non avevano AFFATTO la sezione onboarding (fallback
        italiano silenzioso) — mai piu': parita' chiave per chiave."""
        import json
        blocks = {}
        for lang in ("it", "en", "de", "fr"):
            data = json.loads(
                (self.SRC_DIR / "locales" / lang / "dashboard.json").read_text())
            blocks[lang] = data.get("onboarding") or {}
        base = set(blocks["it"])
        assert base, "sezione onboarding mancante in it"
        for lang in ("en", "de", "fr"):
            missing = base - set(blocks[lang])
            assert not missing, f"{lang}: chiavi onboarding mancanti {sorted(missing)}"
