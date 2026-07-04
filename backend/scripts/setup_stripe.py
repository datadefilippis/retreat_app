#!/usr/bin/env python3
"""
Automated Stripe Setup — Creates Products, Prices, Webhook, Portal config
and writes Stripe IDs to MongoDB.  Zero manual dashboard clicks needed.

Usage:
  # From backend/ directory:
  python scripts/setup_stripe.py --mode test --webhook-url https://YOUR_DOMAIN/api/billing/webhooks
  python scripts/setup_stripe.py --mode test --webhook-url https://YOUR_DOMAIN/api/billing/webhooks --dry-run

  # Local dev with Stripe CLI (no webhook URL needed):
  python scripts/setup_stripe.py --mode test --skip-webhook

  # Production (live mode):
  python scripts/setup_stripe.py --mode live --webhook-url https://app.afianco.it/api/billing/webhooks

Requirements:
  - STRIPE_SECRET_KEY must be set in backend/.env (or as env var)
  - MongoDB must be running and accessible (MONGO_URL in .env)
  - stripe Python package installed (pip install stripe)

What it does:
  1. Creates Stripe Products for Core and Pro plans (idempotent via metadata lookup)
  2. Creates Stripe Prices for each product (monthly + yearly)
  3. Creates a Webhook endpoint with the 5 required events
  4. Configures the Customer Portal (cancel at period end, update payment, invoices)
  5. Writes stripe_product_id, stripe_price_id_monthly, stripe_price_id_yearly to MongoDB
  6. Prints a summary with all IDs and env vars to set
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Ensure backend/ is on sys.path so we can import database.py
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# Load .env before anything else
from dotenv import load_dotenv
load_dotenv(BACKEND_DIR / ".env", override=True)

import stripe

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("setup_stripe")


# ══════════════════════════════════════════════════════════════════════════════
# Plan definitions — single source of truth (mirrors seed_commercial_plans.py)
# ══════════════════════════════════════════════════════════════════════════════

STRIPE_PLANS = [
    {
        "slug": "core",
        "product_name": "AFianco Core",
        "product_description": "Monitoraggio completo del cashflow e AI base",
        "price_monthly_eur": 3900,   # cents
        "price_yearly_eur": 39000,   # cents
    },
    {
        "slug": "pro",
        "product_name": "AFianco Pro",
        "product_description": "Analisi avanzata con AI illimitata",
        "price_monthly_eur": 7900,   # cents
        "price_yearly_eur": 79000,   # cents
    },
]

# Events our webhook handler knows about
WEBHOOK_EVENTS = [
    "checkout.session.completed",
    "customer.subscription.updated",
    "customer.subscription.deleted",
    "invoice.paid",
    "invoice.payment_failed",
]

STRIPE_API_VERSION = "2024-06-20"


# ══════════════════════════════════════════════════════════════════════════════
# Stripe helpers (idempotent)
# ══════════════════════════════════════════════════════════════════════════════

def find_existing_product(slug: str) -> Optional[Dict[str, Any]]:
    """Search for an existing Stripe Product by our metadata tag."""
    products = stripe.Product.search(
        query=f'metadata["afianco_plan_slug"]:"{slug}"',
        limit=1,
    )
    if products.data:
        return products.data[0]
    return None


def find_existing_prices(product_id: str) -> Dict[str, Any]:
    """List active prices for a product, keyed by interval."""
    prices = stripe.Price.list(product=product_id, active=True, limit=10)
    result = {}
    for p in prices.data:
        interval = p.recurring.interval if p.recurring else None
        if interval == "month":
            result["monthly"] = p
        elif interval == "year":
            result["yearly"] = p
    return result


def create_or_get_product(plan: dict, dry_run: bool) -> Dict[str, Any]:
    """Create a Stripe Product or return existing one (idempotent)."""
    slug = plan["slug"]
    existing = find_existing_product(slug)

    if existing:
        logger.info("  ✓ Product '%s' already exists: %s", slug, existing.id)
        return existing

    if dry_run:
        logger.info("  [DRY RUN] Would create Product '%s'", slug)
        return {"id": f"prod_DRYRUN_{slug}", "name": plan["product_name"]}

    product = stripe.Product.create(
        name=plan["product_name"],
        description=plan["product_description"],
        metadata={"afianco_plan_slug": slug, "platform": "afianco"},
    )
    logger.info("  ✓ Created Product '%s': %s", slug, product.id)
    return product


def create_or_get_price(
    product_id: str,
    amount_cents: int,
    interval: str,  # "month" or "year"
    existing_prices: Dict[str, Any],
    plan_slug: str,
    dry_run: bool,
) -> Dict[str, Any]:
    """Create a Stripe Price or return existing one (idempotent)."""
    key = "monthly" if interval == "month" else "yearly"

    if key in existing_prices:
        existing = existing_prices[key]
        # Verify amount matches
        if existing.unit_amount == amount_cents:
            logger.info("    ✓ Price %s (%s) already exists: %s", key, interval, existing.id)
            return existing
        else:
            logger.warning(
                "    ⚠ Price %s exists but amount mismatch: Stripe=%d vs expected=%d. "
                "You may need to archive the old price and create a new one manually.",
                key, existing.unit_amount, amount_cents,
            )
            return existing

    if dry_run:
        logger.info("    [DRY RUN] Would create Price: €%.2f/%s", amount_cents / 100, interval)
        return {"id": f"price_DRYRUN_{plan_slug}_{key}"}

    price = stripe.Price.create(
        product=product_id,
        unit_amount=amount_cents,
        currency="eur",
        recurring={"interval": interval},
        metadata={"afianco_plan_slug": plan_slug, "interval": key},
    )
    logger.info("    ✓ Created Price %s (€%.2f/%s): %s", key, amount_cents / 100, interval, price.id)
    return price


def find_existing_webhook(url: str) -> Optional[Dict[str, Any]]:
    """Search for an existing webhook endpoint by URL."""
    endpoints = stripe.WebhookEndpoint.list(limit=50)
    for ep in endpoints.data:
        if ep.url == url and ep.status != "disabled":
            return ep
    return None


def create_or_get_webhook(url: str, dry_run: bool) -> Dict[str, Any]:
    """Create a Webhook endpoint or return existing one (idempotent)."""
    existing = find_existing_webhook(url)

    if existing:
        # Check if events match
        missing_events = set(WEBHOOK_EVENTS) - set(existing.enabled_events)
        if missing_events:
            if not dry_run:
                updated = stripe.WebhookEndpoint.modify(
                    existing.id,
                    enabled_events=WEBHOOK_EVENTS,
                )
                logger.info("  ✓ Updated Webhook %s: added missing events %s", existing.id, missing_events)
                return updated
            else:
                logger.info("  [DRY RUN] Would update Webhook %s: add events %s", existing.id, missing_events)
        else:
            logger.info("  ✓ Webhook already exists: %s", existing.id)
        return existing

    if dry_run:
        logger.info("  [DRY RUN] Would create Webhook for %s", url)
        return {"id": "we_DRYRUN", "secret": "whsec_DRYRUN"}

    webhook = stripe.WebhookEndpoint.create(
        url=url,
        enabled_events=WEBHOOK_EVENTS,
        api_version=STRIPE_API_VERSION,
        description="AFianco Billing — automated setup",
        metadata={"platform": "afianco"},
    )
    logger.info("  ✓ Created Webhook: %s", webhook.id)
    logger.info("  🔑 Webhook Secret: %s", webhook.secret)
    return webhook


def setup_customer_portal(product_prices: Dict[str, Dict[str, str]], dry_run: bool) -> Optional[str]:
    """Configure the Stripe Customer Portal.

    Enables: subscription cancellation (at period end), payment method updates,
    invoice history, and plan switching between Core and Pro.
    """
    if dry_run:
        logger.info("  [DRY RUN] Would configure Customer Portal")
        return None

    # Build the list of switchable prices for portal
    portal_products = []
    for slug, prices in product_prices.items():
        price_list = []
        if prices.get("monthly"):
            price_list.append(prices["monthly"])
        if prices.get("yearly"):
            price_list.append(prices["yearly"])
        if price_list:
            portal_products.append({"product": prices["product_id"], "prices": price_list})

    config_params = {
        "business_profile": {
            "headline": "Gestisci il tuo abbonamento AFianco",
        },
        "features": {
            "customer_update": {
                "enabled": True,
                "allowed_updates": ["email", "tax_id"],
            },
            "payment_method_update": {
                "enabled": True,
            },
            "invoice_history": {
                "enabled": True,
            },
            "subscription_cancel": {
                "enabled": True,
                "mode": "at_period_end",  # Key: cancel at period end, not immediately
                "proration_behavior": "none",
            },
        },
        "default_return_url": os.environ.get("FRONTEND_URL", "https://afianco.app") + "/settings",
        "metadata": {"platform": "afianco"},
    }

    # Add plan switching if we have multiple products
    if len(portal_products) >= 2:
        config_params["features"]["subscription_update"] = {
            "enabled": True,
            "default_allowed_updates": ["price"],
            "proration_behavior": "create_prorations",
            "products": portal_products,
        }

    try:
        config = stripe.billing_portal.Configuration.create(**config_params)
        logger.info("  ✓ Created Customer Portal configuration: %s", config.id)
        return config.id
    except stripe.InvalidRequestError as e:
        logger.warning("  ⚠ Portal config creation failed: %s", e)
        logger.info("    This may happen if a portal config already exists. Check the Stripe Dashboard.")
        return None


# ══════════════════════════════════════════════════════════════════════════════
# MongoDB update
# ══════════════════════════════════════════════════════════════════════════════

async def update_mongodb(plan_stripe_ids: Dict[str, Dict[str, str]], dry_run: bool):
    """Write Stripe IDs to the commercial_plans collection in MongoDB."""
    from database import commercial_plans_collection

    for slug, ids in plan_stripe_ids.items():
        update_fields = {}
        if ids.get("product_id"):
            update_fields["stripe_product_id"] = ids["product_id"]
        if ids.get("monthly"):
            update_fields["stripe_price_id_monthly"] = ids["monthly"]
        if ids.get("yearly"):
            update_fields["stripe_price_id_yearly"] = ids["yearly"]

        if not update_fields:
            continue

        if dry_run:
            logger.info("  [DRY RUN] Would update plan '%s' in MongoDB: %s", slug, update_fields)
            continue

        result = await commercial_plans_collection.update_one(
            {"slug": slug},
            {"$set": update_fields},
        )

        if result.matched_count == 0:
            logger.warning("  ⚠ Plan '%s' NOT FOUND in MongoDB — run the app once first to seed plans.", slug)
        elif result.modified_count > 0:
            logger.info("  ✓ Updated plan '%s' in MongoDB: %s", slug, update_fields)
        else:
            logger.info("  ✓ Plan '%s' already up-to-date in MongoDB", slug)

    # Verification: read back
    if not dry_run:
        logger.info("\n  📋 Verification — Stripe IDs in MongoDB:")
        for slug in plan_stripe_ids:
            doc = await commercial_plans_collection.find_one(
                {"slug": slug},
                {"_id": 0, "slug": 1, "stripe_product_id": 1,
                 "stripe_price_id_monthly": 1, "stripe_price_id_yearly": 1},
            )
            if doc:
                logger.info("    %s: product=%s  monthly=%s  yearly=%s",
                    doc.get("slug"),
                    doc.get("stripe_product_id", "❌ MISSING"),
                    doc.get("stripe_price_id_monthly", "❌ MISSING"),
                    doc.get("stripe_price_id_yearly", "❌ MISSING"),
                )


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════

async def main():
    parser = argparse.ArgumentParser(
        description="Automated Stripe setup for AFianco billing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test mode with production webhook URL:
  python scripts/setup_stripe.py --mode test --webhook-url https://app.afianco.it/api/billing/webhooks

  # Test mode, skip webhook (use Stripe CLI locally):
  python scripts/setup_stripe.py --mode test --skip-webhook

  # Dry run (no changes made):
  python scripts/setup_stripe.py --mode test --webhook-url https://example.com/api/billing/webhooks --dry-run

  # Live mode:
  python scripts/setup_stripe.py --mode live --webhook-url https://app.afianco.it/api/billing/webhooks
        """,
    )
    parser.add_argument(
        "--mode", choices=["test", "live"], required=True,
        help="Stripe mode: 'test' for test keys, 'live' for production",
    )
    parser.add_argument(
        "--webhook-url",
        help="Public URL for the webhook endpoint (e.g., https://app.afianco.it/api/billing/webhooks)",
    )
    parser.add_argument(
        "--skip-webhook", action="store_true",
        help="Skip webhook creation (use when testing locally with Stripe CLI)",
    )
    parser.add_argument(
        "--skip-portal", action="store_true",
        help="Skip Customer Portal configuration",
    )
    parser.add_argument(
        "--skip-mongodb", action="store_true",
        help="Skip writing Stripe IDs to MongoDB (Stripe-only setup)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print what would be done without making any changes",
    )

    args = parser.parse_args()

    # ── Validate ──────────────────────────────────────────────────────────────
    secret_key = os.environ.get("STRIPE_SECRET_KEY", "")
    if not secret_key:
        logger.error("❌ STRIPE_SECRET_KEY not set. Add it to backend/.env or export it.")
        sys.exit(1)

    if args.mode == "test" and not secret_key.startswith("sk_test_"):
        logger.error("❌ --mode test but STRIPE_SECRET_KEY doesn't start with 'sk_test_'. "
                      "You're using a LIVE key! Aborting for safety.")
        sys.exit(1)

    if args.mode == "live" and not secret_key.startswith("sk_live_"):
        logger.error("❌ --mode live but STRIPE_SECRET_KEY doesn't start with 'sk_live_'. "
                      "You're using a TEST key!")
        sys.exit(1)

    if not args.skip_webhook and not args.webhook_url:
        logger.error("❌ --webhook-url is required unless --skip-webhook is used.")
        sys.exit(1)

    # ── Configure Stripe ──────────────────────────────────────────────────────
    stripe.api_key = secret_key
    stripe.api_version = STRIPE_API_VERSION

    mode_label = "TEST" if args.mode == "test" else "🔴 LIVE"
    dry_label = " [DRY RUN]" if args.dry_run else ""

    logger.info("=" * 70)
    logger.info("  AFianco Stripe Setup — %s MODE%s", mode_label, dry_label)
    logger.info("=" * 70)

    # Verify API key works
    try:
        account = stripe.Account.retrieve()
        logger.info("  Connected to Stripe account: %s (%s)", account.get("business_profile", {}).get("name", "N/A"), account.id)
    except stripe.AuthenticationError:
        logger.error("❌ Stripe authentication failed. Check your STRIPE_SECRET_KEY.")
        sys.exit(1)

    # ══════════════════════════════════════════════════════════════════════════
    # Step 1: Create Products + Prices
    # ══════════════════════════════════════════════════════════════════════════
    logger.info("\n📦 Step 1: Products & Prices")
    logger.info("-" * 40)

    plan_stripe_ids: Dict[str, Dict[str, str]] = {}
    product_prices: Dict[str, Dict[str, str]] = {}  # For portal config

    for plan in STRIPE_PLANS:
        slug = plan["slug"]
        logger.info("\n  Plan: %s", slug.upper())

        # Product
        product = create_or_get_product(plan, args.dry_run)
        product_id = product.id if hasattr(product, "id") else product["id"]

        # Find existing prices
        existing_prices = {} if args.dry_run else find_existing_prices(product_id)

        # Monthly price
        monthly = create_or_get_price(
            product_id, plan["price_monthly_eur"], "month",
            existing_prices, slug, args.dry_run,
        )
        monthly_id = monthly.id if hasattr(monthly, "id") else monthly["id"]

        # Yearly price
        yearly = create_or_get_price(
            product_id, plan["price_yearly_eur"], "year",
            existing_prices, slug, args.dry_run,
        )
        yearly_id = yearly.id if hasattr(yearly, "id") else yearly["id"]

        plan_stripe_ids[slug] = {
            "product_id": product_id,
            "monthly": monthly_id,
            "yearly": yearly_id,
        }

        product_prices[slug] = {
            "product_id": product_id,
            "monthly": monthly_id,
            "yearly": yearly_id,
        }

    # ══════════════════════════════════════════════════════════════════════════
    # Step 2: Webhook Endpoint
    # ══════════════════════════════════════════════════════════════════════════
    webhook_secret = None

    if args.skip_webhook:
        logger.info("\n🔗 Step 2: Webhook — SKIPPED (use Stripe CLI for local testing)")
        logger.info("  Run: stripe listen --forward-to http://localhost:8000/api/billing/webhooks")
    else:
        logger.info("\n🔗 Step 2: Webhook Endpoint")
        logger.info("-" * 40)
        webhook = create_or_get_webhook(args.webhook_url, args.dry_run)
        # Secret is only available on creation, not on retrieval
        webhook_secret = getattr(webhook, "secret", None) or (webhook.get("secret") if isinstance(webhook, dict) else None)
        if webhook_secret:
            logger.info("\n  ⚠️  SAVE THIS — Webhook secret is only shown once:")
            logger.info("  STRIPE_WEBHOOK_SECRET=%s", webhook_secret)

    # ══════════════════════════════════════════════════════════════════════════
    # Step 3: Customer Portal
    # ══════════════════════════════════════════════════════════════════════════
    if args.skip_portal:
        logger.info("\n🎛️  Step 3: Customer Portal — SKIPPED")
    else:
        logger.info("\n🎛️  Step 3: Customer Portal Configuration")
        logger.info("-" * 40)
        setup_customer_portal(product_prices, args.dry_run)

    # ══════════════════════════════════════════════════════════════════════════
    # Step 4: MongoDB Update
    # ══════════════════════════════════════════════════════════════════════════
    if args.skip_mongodb:
        logger.info("\n🗄️  Step 4: MongoDB Update — SKIPPED")
    else:
        logger.info("\n🗄️  Step 4: Write Stripe IDs to MongoDB")
        logger.info("-" * 40)
        await update_mongodb(plan_stripe_ids, args.dry_run)

    # ══════════════════════════════════════════════════════════════════════════
    # Summary
    # ══════════════════════════════════════════════════════════════════════════
    logger.info("\n" + "=" * 70)
    logger.info("  ✅ SETUP COMPLETE%s", dry_label)
    logger.info("=" * 70)

    logger.info("\n📋 Stripe IDs created:")
    for slug, ids in plan_stripe_ids.items():
        logger.info("  %s:", slug.upper())
        logger.info("    product_id:           %s", ids["product_id"])
        logger.info("    price_id_monthly:     %s", ids["monthly"])
        logger.info("    price_id_yearly:      %s", ids["yearly"])

    # Print env vars to set
    publishable_key = os.environ.get("STRIPE_PUBLISHABLE_KEY", "")
    logger.info("\n📝 Environment variables for .env.production:")
    logger.info("-" * 40)
    logger.info("  STRIPE_SECRET_KEY=%s", secret_key[:12] + "..." + secret_key[-4:])
    if publishable_key:
        logger.info("  STRIPE_PUBLISHABLE_KEY=%s", publishable_key)
    else:
        logger.info("  STRIPE_PUBLISHABLE_KEY=<get from Stripe Dashboard → API Keys>")
    if webhook_secret:
        logger.info("  STRIPE_WEBHOOK_SECRET=%s", webhook_secret)
    else:
        logger.info("  STRIPE_WEBHOOK_SECRET=<already set or use 'stripe listen' output>")
    logger.info("  FRONTEND_URL=%s", os.environ.get("FRONTEND_URL", "https://YOUR_DOMAIN"))

    if not args.skip_webhook:
        logger.info("\n🧪 Test the webhook:")
        logger.info("  stripe trigger checkout.session.completed")

    logger.info("")


if __name__ == "__main__":
    asyncio.run(main())
