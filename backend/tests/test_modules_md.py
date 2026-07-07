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
