"""Seed the commercial plan catalog.

Called once at startup.  Idempotent: upserts by slug.

Commercial plans define the user-facing bundles (Free / Core / Pro / Enterprise).
Each plan maps module_key -> PricingPlan slug.  When an org subscribes,
plan_provisioning creates one ModuleSubscription per mapping.

Pricing (EUR):
  Free:        0/mo  --  free tier, 200 rows, 3 AI chat, no email
  Starter:    19/mo  --  cashflow_monitor_starter, no AI, email alerts/digest
  Core:       39/mo  --  cashflow_monitor_pro + ai_assistant_starter + email
  Pro:        79/mo  --  all modules pro + ai_assistant_pro + email
  Enterprise: 199/mo --  admin-only, not public (contact sales)
"""

import logging
from typing import List

from models.commercial_plan import CommercialPlan
from repositories import billing_repository

logger = logging.getLogger(__name__)


# v5.8 / Onda 5 — Plan rebrand
#
# Slugs unchanged (free/starter/core/pro/enterprise) so existing Stripe
# subscriptions, BillingEvent records, and Organization.commercial_plan_slug
# continue working unchanged. ONLY display fields + commerce module_plan
# are updated:
#
#   slug=free       → Free               commerce_free       (30 ord, no Stripe)
#   slug=starter    → Solo               commerce_disabled   (no shop)
#   slug=core       → Commerce Starter   commerce_starter    (200 ord, Stripe)
#   slug=pro        → Commerce Pro       commerce_pro        (1000 ord, 3 stores)
#   slug=enterprise → Custom             commerce_unlimited  (custom override)
#
# Notes for the rebrand migration:
#  · upsert_commercial_plan PROTECTS admin-editable fields (name, tagline,
#    description, price_monthly, price_yearly, features_display) on subsequent
#    startups. So this seed file is the source of truth ONLY for fresh DBs.
#  · For existing DBs, `migrate_plan_relaunch_v5()` (in seed_pricing.py) is
#    the one-shot script that rewrites the protected fields to the new
#    rebrand values + flips the legacy_pricing_lock on every org with an
#    active Stripe subscription.

COMMERCIAL_PLANS: List[dict] = [
    {
        "slug": "free",
        "name": "Free",
        # v5.8 / Onda 9.N — Cashflow-first repositioning. Free was previously
        # ambiguous ("cashflow + tiny shop demo"), creating an incoherent
        # value ladder where Solo (€19) actually LOST commerce features
        # versus Free. Production data confirmed all current users are
        # cashflow-only, so the strategic decision is to make Free a pure
        # cashflow demo and reserve commerce for Commerce Starter+.
        # Migration risk = ~zero (no production commerce users yet).
        "description": "Prova gratis il monitoraggio cashflow.",
        "tagline": "Cashflow demo, gratis per sempre",
        "price_monthly": 0.0,
        "price_yearly": None,
        "currency": "EUR",
        "trial_days": 0,
        "is_public": True,
        "is_self_serve": False,  # Free is a baseline/fallback, not a checkout target
        "sort_order": 0,
        "module_plans": {
            "cashflow_monitor": "cashflow_monitor_free",
            "ai_assistant": "ai_assistant_free",
            # 9.N: was product_catalog_free (50 products) → no commerce, no catalog
            "product_catalog": "product_catalog_disabled",
            # 9.N: was commerce_free (30 contact requests) → cashflow-only positioning
            "commerce": "commerce_disabled",
            "customers_light": "customers_light_free",
        },
        "features_display": [
            "billing.features.cashflow_basic",
            "billing.features.data_rows_200",
            "billing.features.basic_analytics",
            "billing.features.ai_chat_3",
            # 9.N: rimosso commerce_30_contact_requests + products_50 (Free non ha più commerce)
        ],
    },
    {
        "slug": "starter",
        "name": "Solo",
        # v5.8 / Onda 9.N — Re-positioned as the FULL CASHFLOW plan (the
        # production sweet spot today). Removed "no_shop" from the feature
        # list (negative framing) and changed `product_catalog_free` to
        # `product_catalog_disabled` for consistency with Free post-rebrand
        # — Solo and Free now both have ZERO commerce surface, the entire
        # commerce upsell happens at Commerce Starter (€39).
        "description": "Cashflow completo + analytics avanzate per la tua attivita.",
        "tagline": "Cashflow completo per la tua attivita",
        "price_monthly": 19.0,         # protected on existing DBs; migrate_plan_relaunch_v5 changes to €15 if desired
        "price_yearly": 190.0,
        "currency": "EUR",
        "trial_days": 14,
        "is_public": True,
        "is_self_serve": True,
        "sort_order": 1,
        "module_plans": {
            "cashflow_monitor": "cashflow_monitor_starter",
            "ai_assistant": "ai_assistant_starter_lite",
            # 9.N: was product_catalog_free (50 prod) → catalog disabled too
            "product_catalog": "product_catalog_disabled",
            "commerce": "commerce_disabled",
            "customers_light": "customers_light_free",
        },
        "features_display": [
            "billing.features.cashflow_full",
            "billing.features.data_rows_1000",
            "billing.features.ai_chat_20",
            "billing.features.email_alerts",
            "billing.features.email_digest_kpi",
            "billing.features.alert_config",
            "billing.features.export",
            "billing.features.team_2",
            # 9.N: rimosso "no_shop" (negative framing). Il plan parla solo
            # di cosa OTTIENE l'utente, non di cosa gli manca.
        ],
    },
    {
        "slug": "core",
        "name": "Commerce Starter",
        "description": "Cashflow completo + storefront con Stripe Connect.",
        "tagline": "Per chi vende online ed esce dalla sandbox",
        # v5.8 / Onda 9.V — price bump 39→49 (Stripe new product + price IDs).
        # Existing customers (none in prod yet) would be grandfathered via
        # legacy_pricing_lock if needed; new signups pay €49 from day one.
        "price_monthly": 49.0,
        "price_yearly": 490.0,
        "currency": "EUR",
        "trial_days": 14,
        "is_public": True,
        "is_self_serve": True,
        "sort_order": 2,
        "module_plans": {
            "cashflow_monitor": "cashflow_monitor_pro",
            "ai_assistant": "ai_assistant_starter",
            "product_catalog": "product_catalog_starter",
            "commerce": "commerce_starter",      # NEW: 200 ord, 1 store, Stripe
            "customers_light": "customers_light_pro",
        },
        "features_display": [
            "billing.features.cashflow_full",
            "billing.features.data_rows_unlimited",
            "billing.features.ai_chat_80",
            "billing.features.ai_digest_4",
            "billing.features.ai_alerts",
            "billing.features.ai_health",
            "billing.features.commerce_200_orders",
            "billing.features.products_200",
            "billing.features.stripe_connect",
            "billing.features.team_5",
            "billing.features.email_support",
        ],
    },
    {
        "slug": "pro",
        "name": "Commerce Pro",
        "description": "Multi-store + AI illimitata + AI digest unlimited.",
        "tagline": "Per chi scala su più canali",
        # v5.8 / Onda 9.V — price bump 79→89 (Stripe new product + price IDs).
        "price_monthly": 89.0,
        "price_yearly": 890.0,
        "currency": "EUR",
        "trial_days": 14,
        "is_public": True,
        "is_self_serve": True,
        "sort_order": 3,
        "module_plans": {
            "cashflow_monitor": "cashflow_monitor_pro",
            "ai_assistant": "ai_assistant_pro",
            "product_catalog": "product_catalog_pro",
            "commerce": "commerce_pro",          # NEW: 1000 ord, 3 stores, Stripe
            "customers_light": "customers_light_pro",
        },
        "features_display": [
            "billing.features.everything_in_commerce_starter",
            "billing.features.ai_chat_200",
            "billing.features.ai_digest_unlimited",
            "billing.features.commerce_1000_orders",
            "billing.features.products_unlimited",
            "billing.features.stores_3",
            "billing.features.team_15",
            "billing.features.priority_support",
        ],
    },
    {
        "slug": "enterprise",
        "name": "Custom",
        "description": "Configurazione su misura — system_admin only.",
        "tagline": "Casi speciali / partner / consulenti",
        "price_monthly": 199.0,
        "price_yearly": None,  # Custom pricing
        "currency": "EUR",
        "trial_days": 0,
        "is_public": False,            # NEW: hidden from public pricing page
        "is_self_serve": False,
        "sort_order": 4,
        "module_plans": {
            "cashflow_monitor": "cashflow_monitor_pro",
            "ai_assistant": "ai_assistant_enterprise",
            "product_catalog": "product_catalog_pro",
            "commerce": "commerce_unlimited",    # NEW: -1 / -1 / Stripe
            "customers_light": "customers_light_pro",
        },
        "features_display": [
            "billing.features.everything_in_commerce_pro",
            "billing.features.ai_unlimited",
            "billing.features.dedicated_support",
            "billing.features.custom_integrations",
            "billing.features.sla",
        ],
    },
]


# ── Add-on plans (v5.8 / Onda 3) ─────────────────────────────────────────────
#
# Each entry is a CommercialPlan with `is_addon=True`. They sit alongside the
# main bundle plans (free/starter/core/pro/enterprise) in the same collection,
# but are NEVER assigned via `commercial_plan_slug` on Organization. Instead:
#
#   1. Customer (or admin UI) calls POST /api/billing/add-addon with addon_slug
#   2. stripe_service.modify_subscription appends a Stripe subscription_item
#   3. Webhook handler upserts an AddonSubscription row
#   4. module_access.get_effective_limit(org, module, feature) sums:
#        base_plan_limit + Σ(addon.quantity * addon_provides[module][feature])
#
# Stripe IDs (`stripe_product_id`, `stripe_price_id_monthly`) are NOT seeded
# here — they must be created manually in Stripe Dashboard (test mode first,
# then live) and wired in via `PUT /api/admin/commercial-plans/{slug}` or
# directly in MongoDB. This keeps the seed file environment-agnostic and
# avoids accidental Stripe API calls at startup.
#
# Compatibility rules:
#   · Free plan is NEVER compatible with any add-on (enforced at endpoint level)
#   · Each add-on declares `compatible_plans` — empty list means "any non-free
#     paid plan", non-empty restricts to listed slugs (e.g. extra_store: pro only)
#   · `max_quantity` caps stacking (most are 5x, extra_store is 7x)

ADDON_PLANS: List[dict] = [
    {
        "slug": "addon_ai_chat_pack",
        "name": "+50 AI chat",
        "description": "50 chat AI extra al mese, cumulabile fino a 5×.",
        "tagline": "Per chi usa l'AI per le decisioni",
        "price_monthly": 9.0,
        "price_yearly": None,        # add-ons are monthly-only at v5.8
        "currency": "EUR",
        "trial_days": 0,
        "is_public": True,
        "is_self_serve": True,
        "is_addon": True,
        "addon_provides": {"ai_assistant": {"chat": 50}},
        "compatible_plans": ["starter", "core", "pro"],
        "max_quantity": 5,
        "sort_order": 100,
        "module_plans": {},          # add-ons don't bundle modules
        "features_display": [
            "billing.addons.ai_chat_pack.feat_50",
            "billing.addons.ai_chat_pack.feat_stack",
        ],
    },
    {
        "slug": "addon_ai_chat_pro",
        "name": "+200 AI chat",
        "description": "200 chat AI extra al mese, cumulabile fino a 3×.",
        "tagline": "Per power user dell'AI",
        "price_monthly": 29.0,
        "price_yearly": None,
        "currency": "EUR",
        "trial_days": 0,
        "is_public": True,
        "is_self_serve": True,
        "is_addon": True,
        "addon_provides": {"ai_assistant": {"chat": 200}},
        "compatible_plans": ["core", "pro"],
        "max_quantity": 3,
        "sort_order": 101,
        "module_plans": {},
        "features_display": [
            "billing.addons.ai_chat_pro.feat_200",
            "billing.addons.ai_chat_pro.feat_stack",
        ],
    },
    {
        "slug": "addon_orders_pack",
        "name": "+200 ordini",
        "description": "200 ordini ecommerce extra al mese, cumulabile fino a 5×.",
        "tagline": "Per chi vende molto",
        "price_monthly": 15.0,
        "price_yearly": None,
        "currency": "EUR",
        "trial_days": 0,
        "is_public": True,
        "is_self_serve": True,
        "is_addon": True,
        "addon_provides": {"commerce": {"orders_monthly": 200}},
        "compatible_plans": ["core", "pro"],   # only commerce-active plans
        "max_quantity": 5,
        "sort_order": 102,
        "module_plans": {},
        "features_display": [
            "billing.addons.orders_pack.feat_200",
            "billing.addons.orders_pack.feat_stack",
        ],
    },
    {
        "slug": "addon_extra_store",
        "name": "+1 store",
        "description": "Aggiungi 1 storefront in più al tuo piano, cumulabile fino a 7×.",
        "tagline": "Per multi-brand",
        "price_monthly": 19.0,
        "price_yearly": None,
        "currency": "EUR",
        "trial_days": 0,
        "is_public": True,
        "is_self_serve": True,
        "is_addon": True,
        "addon_provides": {"commerce": {"stores_max": 1}},
        "compatible_plans": ["pro"],   # only Pro can multi-store
        "max_quantity": 7,
        "sort_order": 103,
        "module_plans": {},
        "features_display": [
            "billing.addons.extra_store.feat_1",
            "billing.addons.extra_store.feat_stack",
        ],
    },
]


# ── Retreat fork (Fase 1.3 — kill-list) ─────────────────────────────────────
#
# I due piani della piattaforma ritiri. Modello di business (vedi
# docs/BUSINESS_CONCEPT_RITIRI_2026-07.md §6, rivisto 16/7/2026): il piano
# Gratis include TUTTO il funzionale (pubblicazione, prenotazioni, caparre,
# partecipanti) ed è monetizzato con la fee transazionale
# (application_fee_percent=5); il Pro a 29€/mese AZZERA la fee (decisione
# founder 16/7/2026: chi paga il canone tiene tutto il transato) e aggiunge
# evidenza/limiti estesi.
#
# I moduli AFianco non pertinenti (AI, cashflow) puntano ai pricing plan
# *_disabled (tutti i limiti a 0 → moduli invisibili nella UI). I piani
# legacy (free/starter/core/pro/enterprise) restano nel catalogo per
# compatibilità con fallback e test; la loro rimozione dalla pagina pricing
# è pianificata in Fase 6.2 del RETREAT_MASTER_PLAN.

RETREAT_COMMERCIAL_PLANS: List[dict] = [
    {
        "slug": "retreat_free",
        "name": "Gratis",
        "description": "Tutto per pubblicare e incassare i tuoi ritiri. Paghi solo quando incassi.",
        "tagline": "Tutto incluso, paghi solo quando incassi",
        "price_monthly": 0.0,
        "price_yearly": None,
        "currency": "EUR",
        "trial_days": 0,
        "is_public": True,
        "is_self_serve": False,   # baseline al signup, non un target di checkout
        "sort_order": 10,
        "transaction_fee_percent": 5.0,
        "platform_limits": {"team_members": 2},
        "module_plans": {
            "cashflow_monitor": "cashflow_monitor_retreat",
            "ai_assistant": "ai_assistant_disabled",
            "product_catalog": "product_catalog_retreat_free",
            "commerce": "commerce_retreat",
            "customers_light": "customers_light_free",
        },
        # Inventario olistico funzionalita' (4/7/2026, richiesta founder):
        # TUTTO cio' che il piano include, senza omissioni fuorvianti —
        # incluso l'e-commerce, che prima non era menzionato.
        "features_display": [
            "billing.features.retreat_unlimited_listings",
            "billing.features.retreat_ecommerce",
            "billing.features.retreat_product_types",
            "billing.features.retreat_public_page",
            "billing.features.retreat_deposits_payments",
            "billing.features.retreat_payment_reminders",
            "billing.features.retreat_participants",
            "billing.features.retreat_comms",
            "billing.features.retreat_newsletter",
            "billing.features.retreat_cashflow",
            "billing.features.retreat_customers",
            "billing.features.retreat_coupons",
            "billing.features.retreat_catalog_100",
            "billing.features.retreat_stores_1",
            "billing.features.retreat_team_2",
        ],
    },
    {
        "slug": "retreat_pro",
        "name": "Pro",
        "description": "Zero commissioni sul transato, evidenza nel calendario pubblico e limiti estesi.",
        "tagline": "Per chi organizza più ritiri l'anno",
        "price_monthly": 29.0,
        "price_yearly": 290.0,
        "currency": "EUR",
        "trial_days": 0,
        "is_public": True,
        "is_self_serve": True,
        "sort_order": 11,
        "transaction_fee_percent": 0.0,
        "platform_limits": {"team_members": 5},
        "module_plans": {
            "cashflow_monitor": "cashflow_monitor_retreat",
            "ai_assistant": "ai_assistant_disabled",
            "product_catalog": "product_catalog_retreat_pro",
            "commerce": "commerce_retreat_pro",
            "customers_light": "customers_light_pro",
        },
        "features_display": [
            "billing.features.retreat_everything_free",
            "billing.features.retreat_zero_fee",
            "billing.features.retreat_featured",
            "billing.features.retreat_catalog_unlimited",
            "billing.features.retreat_stores_3",
            "billing.features.retreat_team_5",
            "billing.features.retreat_priority_support",
        ],
    },
    # Founding — piano DEDICATO per i primi organizzatori (decisione founder
    # 4/7/2026: niente coupon, piano a sé). Tutto Pro a 0€, assegnato solo
    # dall'admin (non pubblico, non self-serve); la scadenza dei 3 mesi si
    # gestisce con trial_ends_at/notes al momento dell'assegnazione admin.
    {
        "slug": "retreat_founding",
        "name": "Founding",
        "description": "Piano riservato ai primi organizzatori: tutto Pro, gratis per 3 mesi.",
        "tagline": "Per chi costruisce la piattaforma con noi",
        "price_monthly": 0.0,
        "price_yearly": None,
        "currency": "EUR",
        "trial_days": 0,
        "is_public": False,
        "is_self_serve": False,
        "sort_order": 12,
        "transaction_fee_percent": 0.0,   # trattamento Pro (zero fee)
        "platform_limits": {"team_members": 5},
        "module_plans": {
            "cashflow_monitor": "cashflow_monitor_retreat",
            "ai_assistant": "ai_assistant_disabled",
            "product_catalog": "product_catalog_retreat_pro",
            "commerce": "commerce_retreat_pro",
            "customers_light": "customers_light_pro",
        },
        "features_display": [
            "billing.features.retreat_everything_pro",
            "billing.features.retreat_founding_free",
            "billing.features.retreat_founding_feedback",
        ],
    },
    # Partner — piano 0% fee (richiesta founder 5/7/2026): NASCOSTO dal
    # pricing pubblico e assegnabile SOLO dal system admin, on demand
    # (org proprie come la Masseria, partnership strategiche). Tutto Pro,
    # nessuna fee piattaforma: il provider Stripe omette
    # application_fee_amount quando la fee e' 0 (gia' gestito, testato).
    {
        "slug": "retreat_partner",
        "name": "Partner",
        "description": "Piano riservato assegnato dall'admin: tutto Pro, 0% di fee piattaforma.",
        "tagline": "Per le strutture partner della piattaforma",
        "price_monthly": 0.0,
        "price_yearly": None,
        "currency": "EUR",
        "trial_days": 0,
        "is_public": False,
        "is_self_serve": False,
        "sort_order": 13,
        "transaction_fee_percent": 0.0,
        "platform_limits": {"team_members": 5},
        "module_plans": {
            "cashflow_monitor": "cashflow_monitor_retreat",
            "ai_assistant": "ai_assistant_disabled",
            "product_catalog": "product_catalog_retreat_pro",
            "commerce": "commerce_retreat_pro",
            "customers_light": "customers_light_pro",
        },
        "features_display": [
            "billing.features.retreat_everything_pro",
            "billing.features.retreat_zero_fee",
            "billing.features.retreat_no_monthly",
        ],
    },
]


async def seed_commercial_plans() -> None:
    """Seed the commercial plan catalog.  Idempotent (upsert by slug).

    Safe to call on every startup.  Updates existing plans if seed data changes.
    Main bundle plans (free/starter/core/pro/enterprise), add-on plans
    (addon_*) and retreat fork plans (retreat_*) are upserted in one pass.

    Stripe IDs are deliberately NOT seeded — see ADDON_PLANS docstring.
    """
    # 16/7/2026 (consolidamento AU) — il catalogo di Aurya sono SOLO i
    # piani retreat_*: i piani AFianco (main + addon) non vengono piu'
    # seminati. Le costanti COMMERCIAL_PLANS/ADDON_PLANS restano nel
    # modulo per i test del catalogo legacy, ma non toccano il DB.
    all_plans = RETREAT_COMMERCIAL_PLANS
    for plan_data in all_plans:
        plan = CommercialPlan(**plan_data)
        doc = plan.model_dump()
        # Serialize datetimes for MongoDB
        doc["created_at"] = doc["created_at"].isoformat()
        doc["updated_at"] = doc["updated_at"].isoformat()
        await billing_repository.upsert_commercial_plan(doc)

    # Purga dei piani legacy AFianco dal DB (16/7/2026, consolidamento
    # AU): il pannello admin deve mostrare SOLO il catalogo Aurya.
    # Guardia di sicurezza: un piano ancora referenziato da una org o
    # da un addon attivo NON viene toccato (e viene loggato) — mai
    # orfanare un abbonamento vivo.
    from database import (commercial_plans_collection,
                          organizations_collection,
                          addon_subscriptions_collection)
    legacy_slugs = ([p["slug"] for p in COMMERCIAL_PLANS]
                    + [p["slug"] for p in ADDON_PLANS])
    still_used = set(await organizations_collection.distinct(
        "commercial_plan_slug", {"commercial_plan_slug": {"$in": legacy_slugs}}))
    still_used |= set(await addon_subscriptions_collection.distinct(
        "addon_slug", {"addon_slug": {"$in": legacy_slugs},
                       "status": "active"}))
    removable = [s for s in legacy_slugs if s not in still_used]
    if removable:
        result = await commercial_plans_collection.delete_many(
            {"slug": {"$in": removable}})
        if result.deleted_count:
            logger.info("Catalogo Aurya-only: rimossi %d piani legacy AFianco (%s)",
                        result.deleted_count, ", ".join(removable))
    if still_used:
        logger.warning("Piani legacy ANCORA referenziati, non rimossi: %s",
                       ", ".join(sorted(still_used)))

    logger.info("Seeded %d commercial plans (upsert) — catalogo Aurya (retreat_*).",
                len(all_plans))
