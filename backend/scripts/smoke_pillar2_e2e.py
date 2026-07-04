"""
Pillar 2 end-to-end smoke test — "Pasticceria Dolce Vita SRL".

Builds a SMALL, REALISTIC test organisation whose data is hand-crafted to
exercise each Pillar 2 fix in isolation, runs the live alert engine
(``run_alert_engine``), forwards HIGH-severity alerts through the actual
notification pipeline (``notify_high_severity_batch``), and writes a
weekly digest PDF to ``/tmp/`` for visual inspection.

What the seeded scenarios verify
--------------------------------
1. **A3 month_closed_loss — severe-narrative variant (P2.4b)**
   Last completed month: revenue €500, outflows €5500 → loss_pct = 1000%.
   The new logic switches to ``summary_severe`` template so the merchant
   sees "per €1 di ricavi, €11 di costi" instead of the unparseable
   "perdita pari al 1000% dei ricavi". HIGH severity.

2. **A4 revenue_concentration — UUID humanise + 100% cap (P2.4c/d)**
   "Caffè Centrale Snc" = 65% of last-30d revenue, with a real
   customer_name (NOT a UUID). The pct value is capped at 100 via
   ``cap_share_pct`` even if upstream aggregation drifted. HIGH severity.

3. **C2 high_risk_invoice — UUID humanise on customer (P2.4c)**
   "Hotel Splendid Milano" invoice €3000, 45 days overdue, 60% of
   monthly revenue. We seed a real customer_name; humanize_entity_name
   would substitute "Cliente sconosciuto" if the name were UUID-shaped.
   HIGH severity.

4. **E1 supplier_concentration — UUID humanise on supplier (P2.4c)**
   "Farina & Co" = 72% of purchases. Real supplier_name. HIGH severity.

5. **B4 category_expense_trend — bimonthly NON-trigger (P2.2a)**
   Electricity is a bimonthly bill: €48 alternating with €680.
   ``detect_payment_frequency`` should classify as "bimonthly" and the
   median-ratio baseline shouldn't false-fire as it did in v14.1
   ("+1000% Elettricità"). We assert ZERO category_expense_trend alerts
   for category="Elettricità".

6. **Anti-redundancy (P2.3)** — verified in a separate pass:
   resolve the generated alerts → re-run the engine → those alert_types
   must NOT fire again for 60 days.

Usage
-----
    cd backend
    set -a; source .env; set +a

    # Default: seed + run engine + verify expectations, but DO NOT send
    # any email. This avoids the "3 duplicate emails" trap when iterating
    # on the script.
    ./venv/bin/python -m scripts.smoke_pillar2_e2e

    # To actually ship the email + digest PDF (e.g. final E2E verification):
    SMOKE_SEND_EMAIL=1 ./venv/bin/python -m scripts.smoke_pillar2_e2e

    # Hard-skip everything downstream of seed+engine (e.g. checking only
    # that alerts generation logic still works):
    SMOKE_DRY_RUN=1 ./venv/bin/python -m scripts.smoke_pillar2_e2e

    # Skip digest PDF generation specifically:
    SMOKE_SKIP_PDF=1 ./venv/bin/python -m scripts.smoke_pillar2_e2e

Idempotent
----------
Every document this script writes is tagged with
``metadata.smoke_seed = "smoke_pillar2_v1"`` (or the equivalent
``source_label`` for sales_records). Re-running deletes ONLY documents
matching that tag — production / other-org data is never touched.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import List, Tuple

_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))

# ── Stable identifiers ──────────────────────────────────────────────────────
# Hard-coded so repeated runs target the same documents (idempotency).

ORG_ID         = "smoke-pillar2-org-00000000000000000001"
ORG_NAME       = "Pasticceria Dolce Vita SRL"
ORG_SLUG       = "dolce-vita-smoke"
ADMIN_USER_ID  = "smoke-pillar2-admin-0000000000000001"
# Use a gmail +alias so we don't collide with the real user's email
# (which already exists in the dev DB with a unique index). The "+smoke"
# tag is preserved in the To: header and Gmail routes it to the main
# inbox — you'll see "davidedefilippis94+smoke@gmail.com" in the From/To
# but it lands exactly where the unaliased one would.
_BASE_EMAIL = os.environ.get("BACKUP_ALERT_EMAIL", "davidedefilippis94@gmail.com")
if "+smoke" not in _BASE_EMAIL:
    _local, _domain = _BASE_EMAIL.split("@", 1)
    ADMIN_EMAIL = f"{_local}+smoke@{_domain}"
else:
    ADMIN_EMAIL = _BASE_EMAIL
ADMIN_NAME     = "Davide De Filippis (smoke-test)"
DATASET_SALES  = "smoke-pillar2-dataset-sales-001"
DATASET_EXP    = "smoke-pillar2-dataset-exp-001"
DATASET_PURCH  = "smoke-pillar2-dataset-purch-001"

SEED_TAG          = "smoke_pillar2_v1"
SALES_SRC_LABEL   = "demo_seed_smoke_pillar2_v1"

# Customer / supplier names (real strings — NOT UUIDs, so we can verify
# that humanize_entity_name doesn't false-positive on real data)
CUSTOMER_TOP      = "Caffè Centrale Snc"
CUSTOMER_OVERDUE  = "Hotel Splendid Milano"
CUSTOMER_OTHER_1  = "Bar Stella"
CUSTOMER_OTHER_2  = "Ristorante Bella Italia"
CUSTOMER_OTHER_3  = "Pasticceria del Corso"
CUSTOMER_OTHER_4  = "Trattoria San Marco"
CUSTOMER_OTHER_5  = "Caffetteria Verdi"
SUPPLIER_TOP      = "Farina & Co"
SUPPLIER_OTHER    = "Latticini Pugliesi"
SUPPLIER_OTHER_2  = "Zucchero Italiano Srl"
SUPPLIER_OTHER_3  = "Imballaggi Moderni"


def _today() -> date:
    """Use real today (UTC) — we want the engine to see fresh dates."""
    return datetime.now(timezone.utc).date()


def _iso(d: date) -> str:
    return d.isoformat()


# ─────────────────────────────────────────────────────────────────────────────
# DB cleanup — only documents tagged smoke_pillar2_v1
# ─────────────────────────────────────────────────────────────────────────────

async def _wipe_smoke_data():
    """Delete every smoke-tagged document. Idempotent."""
    from database import (
        organizations_collection, users_collection,
        organization_modules_collection, datasets_collection,
        sales_records_collection, expense_records_collection,
        purchase_records_collection, customers_collection,
        suppliers_collection, alerts_collection,
        module_configs_collection, fixed_costs_collection,
    )

    deletions = {}
    for name, coll, filt in [
        ("organizations",    organizations_collection,        {"id": ORG_ID}),
        ("users",            users_collection,                {"id": ADMIN_USER_ID}),
        ("module_configs",   module_configs_collection,       {"organization_id": ORG_ID}),
        ("org_modules",      organization_modules_collection, {"organization_id": ORG_ID}),
        ("datasets",         datasets_collection,             {"organization_id": ORG_ID}),
        ("sales_records",    sales_records_collection,        {"organization_id": ORG_ID}),
        ("expense_records",  expense_records_collection,      {"organization_id": ORG_ID}),
        ("purchase_records", purchase_records_collection,     {"organization_id": ORG_ID}),
        ("customers",        customers_collection,            {"organization_id": ORG_ID}),
        ("suppliers",        suppliers_collection,            {"organization_id": ORG_ID}),
        ("alerts",           alerts_collection,               {"organization_id": ORG_ID}),
        ("fixed_costs",      fixed_costs_collection,          {"organization_id": ORG_ID}),
    ]:
        r = await coll.delete_many(filt)
        deletions[name] = r.deleted_count
    return deletions


# ─────────────────────────────────────────────────────────────────────────────
# Seed: organisation + admin user
# ─────────────────────────────────────────────────────────────────────────────

async def _seed_org_and_admin():
    """Create the smoke org, its admin user (= email recipient), and grant
    the cashflow_monitor module access at the highest plan tier so the
    notification pipeline's plan-gate passes."""
    from database import (
        organizations_collection, users_collection,
        organization_modules_collection, module_configs_collection,
    )
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    now = datetime.now(timezone.utc)

    # Organisation
    await organizations_collection.insert_one({
        "id": ORG_ID,
        "name": ORG_NAME,
        "slug": ORG_SLUG,
        "industry": "Food & Beverage",
        "subscription_plan": "enterprise",  # most permissive
        "created_at": now,
        "updated_at": now,
        "is_active": True,
        "smoke_seed": SEED_TAG,
        "locale": "it",
    })

    # Admin user — recipient of notify_high_severity_batch
    await users_collection.insert_one({
        "id": ADMIN_USER_ID,
        "email": ADMIN_EMAIL,
        "name": ADMIN_NAME,
        "role": "admin",
        "organization_id": ORG_ID,
        "password_hash": pwd_context.hash("smoke-pillar2-throwaway"),
        "created_at": now,
        "updated_at": now,
        "is_active": True,
        "is_verified": True,
        "locale": "it",
        "smoke_seed": SEED_TAG,
    })

    # Enable cashflow_monitor module + ensure email_high_alerts True and
    # rate-limit cleared so the notification pipeline actually sends.
    await organization_modules_collection.insert_one({
        "organization_id": ORG_ID,
        "module_key": "cashflow_monitor",
        "enabled": True,
        "enabled_at": now,
        "smoke_seed": SEED_TAG,
    })
    await module_configs_collection.insert_one({
        "organization_id": ORG_ID,
        "module_key": "cashflow_monitor",
        "settings": {
            "email_high_alerts": True,
            "email_weekly_digest": True,
            # NOTE: NO _last_high_email_at → rate limit is fresh
        },
        "smoke_seed": SEED_TAG,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Seed: customers + suppliers (real names, so humanize_entity_name returns
# them as-is. UUID-shape detection is unit-tested elsewhere.)
# ─────────────────────────────────────────────────────────────────────────────

async def _seed_customers_suppliers():
    from database import customers_collection, suppliers_collection

    now = datetime.now(timezone.utc)
    # Need ≥4 customers in the last-30d aggregate so A4 revenue_concentration
    # bypasses its "<=3 customers → structural" smart suppression. Same
    # logic for E1 supplier_concentration (<=2 suppliers → suppressed).
    customers = [
        {"id": str(uuid.uuid4()), "name": CUSTOMER_TOP,
         "email": "ordini@caffecentrale.test", "organization_id": ORG_ID,
         "created_at": now, "smoke_seed": SEED_TAG},
        {"id": str(uuid.uuid4()), "name": CUSTOMER_OVERDUE,
         "email": "amministrazione@hotel-splendid.test", "organization_id": ORG_ID,
         "created_at": now, "smoke_seed": SEED_TAG},
        {"id": str(uuid.uuid4()), "name": CUSTOMER_OTHER_1,
         "organization_id": ORG_ID, "created_at": now, "smoke_seed": SEED_TAG},
        {"id": str(uuid.uuid4()), "name": CUSTOMER_OTHER_2,
         "organization_id": ORG_ID, "created_at": now, "smoke_seed": SEED_TAG},
        {"id": str(uuid.uuid4()), "name": CUSTOMER_OTHER_3,
         "organization_id": ORG_ID, "created_at": now, "smoke_seed": SEED_TAG},
        {"id": str(uuid.uuid4()), "name": CUSTOMER_OTHER_4,
         "organization_id": ORG_ID, "created_at": now, "smoke_seed": SEED_TAG},
        {"id": str(uuid.uuid4()), "name": CUSTOMER_OTHER_5,
         "organization_id": ORG_ID, "created_at": now, "smoke_seed": SEED_TAG},
    ]
    await customers_collection.insert_many(customers)

    suppliers = [
        {"id": str(uuid.uuid4()), "name": SUPPLIER_TOP,
         "organization_id": ORG_ID, "created_at": now, "smoke_seed": SEED_TAG},
        {"id": str(uuid.uuid4()), "name": SUPPLIER_OTHER,
         "organization_id": ORG_ID, "created_at": now, "smoke_seed": SEED_TAG},
        {"id": str(uuid.uuid4()), "name": SUPPLIER_OTHER_2,
         "organization_id": ORG_ID, "created_at": now, "smoke_seed": SEED_TAG},
        {"id": str(uuid.uuid4()), "name": SUPPLIER_OTHER_3,
         "organization_id": ORG_ID, "created_at": now, "smoke_seed": SEED_TAG},
    ]
    await suppliers_collection.insert_many(suppliers)

    # Map name → id so sales_records can carry customer_id correctly.
    return (
        {c["name"]: c["id"] for c in customers},
        {s["name"]: s["id"] for s in suppliers},
    )


# ─────────────────────────────────────────────────────────────────────────────
# Seed: 14 months of sales with the exact patterns Pillar 2 should react to
# ─────────────────────────────────────────────────────────────────────────────

async def _seed_sales_records(customer_ids: dict):
    """Build the sales timeline that triggers A3 + A4 + C2."""
    from database import sales_records_collection, datasets_collection

    today = _today()
    now = datetime.now(timezone.utc)

    # Create the dataset row first (FK from sales_records)
    await datasets_collection.insert_one({
        "id": DATASET_SALES,
        "name": "Smoke Pillar2 — vendite",
        "organization_id": ORG_ID,
        "source": "smoke_seed",
        "created_at": now,
        "smoke_seed": SEED_TAG,
    })

    records: list = []

    def _push(d: date, amount: float, customer_name: str, customer_id: str,
              category: str = "Vendita banco", due_date: date = None,
              payment_status: str = "paid"):
        # Default due_date: invoice payable 30d from sale date. We need
        # ≥30% coverage of due_dates so the C1 (dso_worsening) and C2
        # (high_risk_invoice) @requires_data gate passes its
        # min_field_coverage check.
        if due_date is None:
            due_date = d + timedelta(days=30)
        records.append({
            "id": str(uuid.uuid4()),
            "organization_id": ORG_ID,
            "dataset_id": DATASET_SALES,
            "date": _iso(d),
            "amount": round(amount, 2),
            "category": category,
            "customer_id": customer_id,
            "customer_name": customer_name,
            "payment_status": payment_status,
            "due_date": _iso(due_date),
            "source_label": SALES_SRC_LABEL,
        })

    # ── 1. Historical 12 months (baseline ≈ €4500/mo, mostly small B2B) ───
    # We need at least 14 calendar months of history so the @requires_data
    # gate passes (min_days_of_data ≥ 120 in some rules) and the YoY/B1
    # snapshot logic has enough material. We use 13 months back to
    # 30 days ago, plus the "current" partial month.
    history_start = today - timedelta(days=420)  # ~14 months ago
    # Spread €4500/month over ~22 working days, split among 3 minor customers
    for month_offset in range(13, 1, -1):
        # Stop ~30 days before today so "last completed month" is special
        month_anchor = today - timedelta(days=30 * month_offset)
        for day_of_month in range(1, 23):
            d = month_anchor + timedelta(days=day_of_month)
            if d > today - timedelta(days=35):
                break
            # Round-robin among non-dominant customers
            cust_name = [CUSTOMER_OTHER_1, CUSTOMER_OTHER_2][day_of_month % 2]
            _push(d, 200.0 + (day_of_month % 5) * 10,
                  cust_name, customer_ids[cust_name],
                  category="Vendita banco")

    # ── 2. LAST COMPLETED MONTH — only €500 revenue (severe loss trigger) ─
    # The check_month_closed_loss rule reads from monthly_snapshots which
    # itself derives from sales_by_date_365d. We need just a handful of
    # tiny records in the previous calendar month.
    last_month_end = today.replace(day=1) - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)
    # ~5 small invoices totaling €500
    for i, amount in enumerate([110, 90, 130, 80, 90]):
        d = last_month_start + timedelta(days=i * 5)
        if d > last_month_end:
            d = last_month_end
        _push(d, amount, CUSTOMER_OTHER_1, customer_ids[CUSTOMER_OTHER_1],
              category="Vendita banco")

    # ── 3. LAST 30 DAYS — concentration on Caffè Centrale (65%) ───────────
    # A4 revenue_concentration triggers at ≥40% (warning) / ≥60% (critical).
    # We need >60% concentration AND:
    #   - ≥4 customers in the aggregate (else A4 smart-suppression kills it)
    #   - ≥20 sales records in last-30d (else A3's @requires_data gate fails:
    #     min_samples_30d=20). So we dense-pack the 30-day window with
    #     ~28 records, with Caffè Centrale holding €2600 of ~€4000 (65%).
    for i in range(14):  # 14 × ≈€185 = €2590 ≈ 65% of €4000
        d = today - timedelta(days=2 + i * 2)
        _push(d, 185.0,
              CUSTOMER_TOP, customer_ids[CUSTOMER_TOP],
              category="Vendita banco")
    # Distribute the remaining €1400 across 4 minor customers so the
    # aggregate returns ≥5 customers and the smart-suppression at
    # `len(customers_by_revenue) <= 3` is bypassed. 14 × €100 = €1400.
    minor_customers = [CUSTOMER_OTHER_1, CUSTOMER_OTHER_2,
                       CUSTOMER_OTHER_3, CUSTOMER_OTHER_4]
    for i in range(14):
        d = today - timedelta(days=3 + i * 2)
        cust = minor_customers[i % len(minor_customers)]
        _push(d, 100.0,
              cust, customer_ids[cust],
              category="Vendita banco")

    # ── 4. OVERDUE INVOICE — Hotel Splendid €3000, 75d overdue ────────────
    # check_high_risk_invoice reads from ctx.overdue_invoices, which is
    # built by _extract_overdue_invoices() in alert_engine.py. That
    # extraction only considers buckets named "61-90" or "90+" as
    # "significantly overdue" — anything in "31-60" gets filtered out.
    # So we set due_date to 75d ago (→ bucket 61-90) instead of 45d.
    overdue_date = today - timedelta(days=100)       # invoiced 100d ago
    due_date     = today - timedelta(days=75)        # due 75d ago → overdue 75d
    _push(overdue_date, 3000.0, CUSTOMER_OVERDUE,
          customer_ids[CUSTOMER_OVERDUE],
          category="Banchetti", due_date=due_date,
          payment_status="overdue")

    await sales_records_collection.insert_many(records)
    return len(records)


# ─────────────────────────────────────────────────────────────────────────────
# Seed: expenses — including bimonthly electricity (B4 non-trigger test)
# ─────────────────────────────────────────────────────────────────────────────

async def _seed_expense_records():
    """Build the expense timeline that triggers A3 (severe loss) and
    proves B4 does NOT false-fire on bimonthly bills."""
    from database import expense_records_collection, datasets_collection

    today = _today()
    now = datetime.now(timezone.utc)

    await datasets_collection.insert_one({
        "id": DATASET_EXP,
        "name": "Smoke Pillar2 — spese",
        "organization_id": ORG_ID,
        "source": "smoke_seed",
        "created_at": now,
        "smoke_seed": SEED_TAG,
    })

    records: list = []

    def _push(d: date, amount: float, category: str, supplier: str = None,
              description: str = ""):
        records.append({
            "id": str(uuid.uuid4()),
            "organization_id": ORG_ID,
            "dataset_id": DATASET_EXP,
            "date": _iso(d),
            "amount": round(amount, 2),
            "category": category,
            "supplier": supplier,
            "description": description,
            "source_label": SALES_SRC_LABEL,
        })

    # ── BIMONTHLY ELECTRICITY (B4 false-positive test) ────────────────────
    # 14 months of bills: ~€48 in "small" months (partial period), ~€680
    # in "full" months. detect_payment_frequency should label "bimonthly"
    # and the median ratio shouldn't false-fire on the alternation.
    elec_pattern = [48, 680, 52, 700, 50, 670, 48, 690, 52, 680, 49, 700, 51, 680]
    # Most recent at end, oldest at start. Walk back 14 months in monthly anchors.
    for month_offset, amount in enumerate(reversed(elec_pattern)):
        d = today.replace(day=15) - timedelta(days=30 * month_offset)
        _push(d, float(amount), "Elettricità", supplier="Enel Energia")

    # ── LAST COMPLETED MONTH — heavy expenses to drive severe loss ────────
    # We need outflows ≈ €5500 vs revenue €500 in last month (loss_pct = 1000%).
    last_month_end = today.replace(day=1) - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)
    # Big chunks: rent €2000, salary €1500, food cost €1500, misc €500
    _push(last_month_start + timedelta(days=2),  2000.0, "Affitto",   "Imm. Brera",  "Affitto locale")
    _push(last_month_start + timedelta(days=5),  1500.0, "Stipendi",  None,           "Salario dipendente")
    _push(last_month_start + timedelta(days=8),  1500.0, "Materie prime", SUPPLIER_TOP, "Acquisto urgente")
    _push(last_month_start + timedelta(days=14),  500.0, "Varie",      None,           "Manutenzione forno")

    # ── Historic expenses — baseline so partials don't false-fire ─────────
    for month_offset in range(13, 0, -1):
        month_anchor = today - timedelta(days=30 * month_offset)
        _push(month_anchor + timedelta(days=5),  2000.0, "Affitto",  "Imm. Brera")
        _push(month_anchor + timedelta(days=10), 1500.0, "Stipendi", None)
        _push(month_anchor + timedelta(days=18),  300.0, "Pulizia",   None)

    await expense_records_collection.insert_many(records)
    return len(records)


# ─────────────────────────────────────────────────────────────────────────────
# Seed: purchases — supplier_concentration trigger (E1)
# ─────────────────────────────────────────────────────────────────────────────

async def _seed_purchase_records(supplier_ids: dict):
    """Build last-30d purchases where Farina & Co dominates (72%)."""
    from database import purchase_records_collection, datasets_collection

    today = _today()
    now = datetime.now(timezone.utc)

    await datasets_collection.insert_one({
        "id": DATASET_PURCH,
        "name": "Smoke Pillar2 — acquisti",
        "organization_id": ORG_ID,
        "source": "smoke_seed",
        "created_at": now,
        "smoke_seed": SEED_TAG,
    })

    records: list = []

    def _push(d: date, total: float, supplier_name: str,
              category: str = "Materie prime", quantity: float = 10,
              unit: str = "kg"):
        records.append({
            "id": str(uuid.uuid4()),
            "organization_id": ORG_ID,
            "dataset_id": DATASET_PURCH,
            "date": _iso(d),
            "supplier_name": supplier_name,
            "supplier_id": supplier_ids.get(supplier_name),
            "quantity": quantity,
            "unit": unit,
            "unit_price": round(total / max(quantity, 1), 2),
            "total_price": round(total, 2),
            "total_with_iva": round(total * 1.10, 2),
            "category": category,
            "source_label": SALES_SRC_LABEL,
        })

    # Last 30d: ~€7200 from Farina & Co dominant, ~€2800 split across 3
    # other suppliers (so we have 4 suppliers total → E1 smart-suppression
    # at `len(suppliers_by_amount) <= 2` is bypassed; Farina & Co still
    # holds 72% to trigger critical severity).
    for i in range(6):
        d = today - timedelta(days=2 + i * 4)
        _push(d, 1200.0, SUPPLIER_TOP, quantity=50, unit="kg")
    minor_suppliers = [
        (SUPPLIER_OTHER, "Latticini"),
        (SUPPLIER_OTHER_2, "Zucchero/Cacao"),
        (SUPPLIER_OTHER_3, "Imballaggi"),
    ]
    for i in range(6):
        d = today - timedelta(days=5 + i * 4)
        supp, cat = minor_suppliers[i % len(minor_suppliers)]
        _push(d, 470.0, supp, quantity=20, unit="kg", category=cat)

    # Older 30d: baseline so the partial-month signal isn't dominant
    for month_offset in range(2, 13):
        month_anchor = today - timedelta(days=30 * month_offset)
        _push(month_anchor + timedelta(days=5),  900.0, SUPPLIER_TOP)
        _push(month_anchor + timedelta(days=15), 400.0, SUPPLIER_OTHER,
              category="Latticini")
        _push(month_anchor + timedelta(days=22), 250.0, SUPPLIER_OTHER_2,
              category="Zucchero/Cacao")

    await purchase_records_collection.insert_many(records)
    return len(records)


# ─────────────────────────────────────────────────────────────────────────────
# Seed: fixed costs (so total_fixed_costs_30d > 0 and break-even rules can fire)
# ─────────────────────────────────────────────────────────────────────────────

async def _seed_fixed_costs():
    from database import fixed_costs_collection

    today = _today()
    now = datetime.now(timezone.utc)

    docs = [
        {"id": str(uuid.uuid4()), "organization_id": ORG_ID,
         "name": "Affitto locale", "amount": 2000.0,
         "frequency": "monthly", "category": "Affitto",
         "active_from": _iso(today - timedelta(days=400)),
         "created_at": now, "smoke_seed": SEED_TAG},
        {"id": str(uuid.uuid4()), "organization_id": ORG_ID,
         "name": "Stipendio dipendente", "amount": 1500.0,
         "frequency": "monthly", "category": "Stipendi",
         "active_from": _iso(today - timedelta(days=400)),
         "created_at": now, "smoke_seed": SEED_TAG},
    ]
    await fixed_costs_collection.insert_many(docs)
    return len(docs)


# ─────────────────────────────────────────────────────────────────────────────
# Direct-send fallback — mirrors the renderer in notify_high_severity_batch
# but bypasses the plan / preferences / rate-limit gate. Used only by this
# smoke script; production never calls this path.
# ─────────────────────────────────────────────────────────────────────────────

async def _smoke_direct_send(alerts: list) -> None:
    """Render the HIGH-severity batch email using the exact same template
    as notify_high_severity_batch and ship it via send_email."""
    from services.email_service import send_email, _t, APP_URL
    from services.alert_notification_service import _render_alert_footer

    high_alerts = [a for a in alerts if a.severity.value == "high"]
    if not high_alerts:
        print("    ⚠️  no HIGH alerts to send")
        return

    n = len(high_alerts)
    locale = "it"
    cat_tpl = _t("cashflow_alert_category_label", locale, category="__CAT__")
    heading_key = ("cashflow_alert_high_heading_one" if n == 1
                   else "cashflow_alert_high_heading_other")
    heading = _t(heading_key, locale, count=n)

    alert_rows = ""
    for a in high_alerts[:5]:
        title = a.title
        summary = (a.summary or "")[:300]
        suggestion = a.suggested_action or ""
        cat = getattr(a, "alert_category", "") or ""
        cat_label = cat_tpl.replace("__CAT__", cat) if cat else ""
        cat_html = (
            f'<span style="color:#9CA3AF; font-size:11px;"> ({cat_label})</span>'
            if cat_label else ""
        )
        alert_rows += f"""
        <tr>
            <td style="padding:12px; border-bottom:1px solid #eee;">
                <strong style="color:#DC2626;">&#x1F534; {title}</strong>{cat_html}<br>
                <span style="color:#666; font-size:14px;">{summary}</span>
                {"<br><em style='color:#2563EB; font-size:13px;'>&#x2192; " + suggestion + "</em>" if suggestion else ""}
            </td>
        </tr>"""

    view_cta = _t("cashflow_alert_view_all_cta", locale)
    alerts_url = f"{APP_URL}/cashflow?tab=alerts"
    try:
        footer = _render_alert_footer(locale)
    except Exception:
        footer = ""

    html = f"""
    <div style="font-family:Arial,sans-serif; max-width:600px; margin:0 auto;">
        <div style="background:#FEF2F2; padding:8px 16px; border-radius:6px;
                    border:1px solid #FCA5A5; margin-bottom:16px;">
            <strong>🧪 SMOKE TEST</strong> — Pillar 2 E2E
            (org: {ORG_NAME})
        </div>
        <h2 style="color:#DC2626;">&#x26A0;&#xFE0F; {heading}</h2>
        <table style="width:100%; border-collapse:collapse;">
            {alert_rows}
        </table>
        <p style="margin-top:20px;">
            <a href="{alerts_url}"
               style="background:#2563EB; color:#fff; padding:10px 20px;
                      text-decoration:none; border-radius:6px; display:inline-block;">
                {view_cta}
            </a>
        </p>
        {footer}
    </div>
    """

    subject = f"[SMOKE PILLAR2] {n} allerte HIGH per {ORG_NAME}"
    ok = send_email(
        to_email=ADMIN_EMAIL,
        subject=subject,
        html_body=html,
        bypass_gate=True,  # skip email_gate (bounce list) — this is a test
    )
    if ok:
        print(f"    ✅ direct email sent to {ADMIN_EMAIL}")
        print(f"       (subject: {subject!r})")
    else:
        print(f"    ❌ direct send_email returned False — check logs above")


# ─────────────────────────────────────────────────────────────────────────────
# Main orchestration
# ─────────────────────────────────────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--keep-data", action="store_true",
                        help="Skip the wipe at the end; useful for manual inspection")
    args = parser.parse_args()

    print("=" * 72)
    print("  Pillar 2 E2E smoke — Pasticceria Dolce Vita SRL")
    print("=" * 72)
    print(f"  Org ID         : {ORG_ID}")
    print(f"  Admin email    : {ADMIN_EMAIL}")
    print(f"  Today (UTC)    : {_today()}")
    print(f"  Dry-run mode   : {os.environ.get('SMOKE_DRY_RUN', '0')}")
    print(f"  Skip PDF       : {os.environ.get('SMOKE_SKIP_PDF', '0')}")
    print("-" * 72)

    # 1. Clean slate
    print("\n[1/6] Wiping previous smoke data...")
    deletions = await _wipe_smoke_data()
    for k, v in deletions.items():
        if v:
            print(f"    - deleted {v} from {k}")

    # 2. Seed
    print("\n[2/6] Seeding org + admin + customers/suppliers...")
    await _seed_org_and_admin()
    customer_ids, supplier_ids = await _seed_customers_suppliers()
    print(f"    - org={ORG_ID[:20]}... admin={ADMIN_EMAIL}")

    print("\n[3/6] Seeding transactional data (14 months)...")
    n_sales = await _seed_sales_records(customer_ids)
    n_exp   = await _seed_expense_records()
    n_purch = await _seed_purchase_records(supplier_ids)
    n_fixed = await _seed_fixed_costs()
    print(f"    - sales_records   : {n_sales}")
    print(f"    - expense_records : {n_exp}")
    print(f"    - purchase_records: {n_purch}")
    print(f"    - fixed_costs     : {n_fixed}")

    # 3. Run engine
    print("\n[4/6] Running alert_engine.run_alert_engine(org_id, locale='it')...")
    from modules.cashflow_monitor.alert_engine import run_alert_engine
    from repositories import alert_repository
    new_alerts = await run_alert_engine(ORG_ID, locale="it")
    # Persist (alert_engine returns objects but doesn't save — alert_service does that.
    # We mimic alert_service.generate_and_save_alerts() flow for the smoke.)
    if new_alerts:
        await alert_repository.create_many(new_alerts)
    print(f"    - alerts generated: {len(new_alerts)}")
    for a in new_alerts:
        atype = getattr(a, "metric_payload", {}).get("alert_type", "?")
        print(f"      • [{a.severity.value.upper():6}] {atype:30} — {a.title[:60]}")

    # ── Assertions on expected outcomes ────────────────────────────────────
    print("\n[5/6] Verifying Pillar 2 expectations...")
    seen_types = {a.metric_payload.get("alert_type") for a in new_alerts}
    expected = {
        "month_closed_loss",
        "revenue_concentration",
        "high_risk_invoice",
        "supplier_concentration",
    }
    forbidden = {
        "category_expense_trend",  # Elettricità bimonthly MUST NOT trigger
    }
    missing = expected - seen_types
    leaked  = forbidden & seen_types
    if not missing and not leaked:
        print("    ✅ All expected alerts fired, no forbidden false-positives")
    else:
        if missing:
            print(f"    ⚠️  Missing expected alerts: {missing}")
        if leaked:
            print(f"    ❌ FORBIDDEN alerts fired (B4 false-positive regressed?): {leaked}")

    # Inspect month_closed_loss summary for the new severe-narrative
    for a in new_alerts:
        atype = a.metric_payload.get("alert_type", "")
        if atype == "month_closed_loss":
            payload = a.metric_payload or {}
            cpr = payload.get("cost_per_revenue")
            loss_pct = payload.get("loss_pct")
            print(f"    - A3 summary excerpt    : {a.summary[:120]}...")
            print(f"      loss_pct={loss_pct}, cost_per_revenue={cpr}")
            if "per €1 di ricavi" in a.summary or "per ogni" in a.summary.lower():
                print("      ✅ severe-narrative variant active")
            else:
                print("      ℹ️  using default summary (loss_pct might be <100)")

    # 4. Send the actual email — DEFAULT IS NOW DRY-RUN to avoid the
    # 3-duplicates problem we ran into during the first live test
    # (re-running the smoke after a script edit re-sends the email).
    # To actually ship the email + PDF, set SMOKE_SEND_EMAIL=1 explicitly.
    # SMOKE_DRY_RUN=1 still works as a stronger no-op (skips everything
    # downstream).
    dry_run = os.environ.get("SMOKE_DRY_RUN", "0") == "1"
    send_real = os.environ.get("SMOKE_SEND_EMAIL", "0") == "1"
    if dry_run or not send_real:
        action = "(DRY RUN — set SMOKE_SEND_EMAIL=1 to actually send) skipping"
    else:
        action = "Sending"
    print(f"\n[6/6] {action} HIGH-severity email...")
    # Treat "not send_real" the same as dry_run for the rest of the function.
    if not send_real:
        dry_run = True
    if not dry_run and new_alerts:
        from services.alert_notification_service import notify_high_severity_batch
        n_sent = await notify_high_severity_batch(new_alerts, ORG_ID, locale="it")
        print(f"    - emails sent via real pipeline: {n_sent}")
        if n_sent == 0:
            # The real pipeline gate-blocked us (most likely the plan-feature
            # gate: enterprise plan in our seed doesn't bundle "email_alerts"
            # by default — that requires entitlement seeding which is
            # complex to fake locally). Fall back to a direct send_email
            # call that reuses the SAME rendering logic used by the live
            # pipeline. This still exercises:
            #   - the Pillar 2 narrative (severe-loss variant, humanise,
            #     cap_share_pct, severity tiers) which lives in a.title /
            #     a.summary / a.suggested_action
            #   - real Brevo delivery
            # It skips: plan-gate, email_high_alerts preference, rate
            # limit, structural suppression — all orthogonal to Pillar 2.
            print("    ⏭  real pipeline gated. Fallback: direct send_email "
                  "(bypasses plan gate, exercises rendering + Brevo)")
            await _smoke_direct_send(new_alerts)

    # PDF digest — exercises the EXACT production flow:
    #   1. module.digest_builder() → pdf_bytes + sections (as background_service does)
    #   2. send_digest_report_email() → ships email with PDF attached
    #
    # We bypass only the plan gate (can_use_module) — that's orthogonal to
    # the Pillar 2 narrative/template changes we're testing. The rest of
    # the pipeline runs as in production: preference check, admin lookup,
    # HTML rendering with health/sales/outflows/margin, PDF attachment via
    # send_email_with_attachment to Brevo.
    skip_pdf = os.environ.get("SMOKE_SKIP_PDF", "0") == "1"
    if not skip_pdf and not dry_run:
        print("\n  Generating digest + sending PDF email (real pipeline)...")
        try:
            from core.module_registry import get_all as registry_get_all
            digest_modules = [m for m in registry_get_all()
                              if getattr(m, "digest_builder", None) is not None]
            if not digest_modules:
                print("    ⚠️  no digest module registered")
            else:
                # ── 1. Build digest (real call) ─────────────────────────────
                result = await digest_modules[0].digest_builder(
                    org_id=ORG_ID, period_days=30, digest_type="weekly",
                    locale="it", format="report", include_ai=False,
                )
                pdf_bytes = result.get("pdf_bytes") if isinstance(result, dict) else None
                if pdf_bytes:
                    pdf_path = "/tmp/smoke_pillar2_digest.pdf"
                    with open(pdf_path, "wb") as f:
                        f.write(pdf_bytes)
                    print(f"    - PDF written: {pdf_path} ({len(pdf_bytes)} bytes)")

                    # ── 2. Send email with PDF attached (real pipeline) ─────
                    # Monkey-patch can_use_module locally so the plan gate
                    # doesn't block us. The seed org has subscription_plan
                    # = "enterprise" but the pricing catalogue's
                    # cashflow_monitor.email_digest entitlement requires
                    # specific seeded plans which is out of scope for a
                    # rule-narrative smoke. Everything else (preference
                    # check, admin lookup, HTML render, PDF attachment,
                    # Brevo delivery) runs unmodified.
                    # send_digest_report_email does `from services.module_access
                    # import can_use_module` INSIDE the function body, so we
                    # must patch the source module, not alert_notification_service.
                    import services.module_access as mod_access
                    from services.alert_notification_service import send_digest_report_email
                    async def _bypass_can(*args, **kwargs):
                        return True
                    _orig_can = mod_access.can_use_module
                    mod_access.can_use_module = _bypass_can
                    try:
                        period_label = (f"{result.get('period_start', '')} — "
                                        f"{result.get('period_end', '')}")
                        n = await send_digest_report_email(
                            org_id=ORG_ID, pdf_bytes=pdf_bytes,
                            sections=result.get("sections", {}),
                            digest_type="weekly",
                            period_label=period_label,
                            locale="it",
                        )
                    finally:
                        mod_access.can_use_module = _orig_can
                    if n:
                        print(f"    ✅ digest report email sent ({n} recipient)")
                        print(f"       PDF attached: {pdf_path}")
                    else:
                        print("    ⚠️  send_digest_report_email returned 0 — "
                              "check email_weekly_digest preference / admin lookup")
                else:
                    keys = list(result.keys()) if isinstance(result, dict) else "<not dict>"
                    print(f"    ⚠️  digest_builder returned no pdf_bytes (keys: {keys})")
        except Exception as e:
            import traceback
            print(f"    ⚠️  digest PDF skipped: {type(e).__name__}: {e}")
            traceback.print_exc()
    elif skip_pdf:
        print("\n  (SMOKE_SKIP_PDF=1) digest PDF skipped")

    # ─────────────────────────────────────────────────────────────────────
    # [7/7] P2.3 cooldown verification — opt-in via SMOKE_TEST_COOLDOWN=1
    # so the smoke stays fast for the common iteration loop.
    #
    # Mechanics:
    #   1. Mark 3 alerts as RESOLVED in the alerts collection (mimics what
    #      the merchant does in the UI: "I know, fix shipped").
    #   2. Re-run run_alert_engine on the same data.
    #   3. Assert: those 3 alert_types are MISSING from the new run
    #      (recently_resolved_alert_types cooldown active for 60 days),
    #      AND the other alert_types ARE still present (cooldown is
    #      alert_type-scoped, not a global mute).
    # ─────────────────────────────────────────────────────────────────────
    if os.environ.get("SMOKE_TEST_COOLDOWN", "0") == "1":
        print("\n[7/7] P2.3 cooldown verification...")
        from database import alerts_collection
        from datetime import datetime as _dt, timezone as _tz

        to_resolve = {
            "month_closed_loss",
            "revenue_concentration",
            "supplier_concentration",
        }
        now_iso = _dt.now(_tz.utc).isoformat()
        result = await alerts_collection.update_many(
            {
                "organization_id": ORG_ID,
                "metric_payload.alert_type": {"$in": list(to_resolve)},
                "status": "new",
            },
            {"$set": {
                "status": "resolved",
                "resolved_at": now_iso,
                "resolution_note": "smoke-test resolve to verify cooldown",
            }},
        )
        print(f"    - resolved {result.modified_count} alerts "
              f"({sorted(to_resolve)})")

        # Re-run engine on the same data
        print("    - re-running alert_engine...")
        # Cancello solo gli alert NEW residui (per evitare dedup-su-self)
        # ma LASCIO i risolti (devono restare per recently_resolved logic)
        await alerts_collection.delete_many(
            {"organization_id": ORG_ID, "status": "new"}
        )
        rerun_alerts = await run_alert_engine(ORG_ID, locale="it")
        seen_types_rerun = {
            a.metric_payload.get("alert_type") for a in rerun_alerts
        }
        print(f"    - rerun produced {len(rerun_alerts)} alerts:")
        for a in rerun_alerts:
            atype = a.metric_payload.get("alert_type", "?")
            print(f"      • [{a.severity.value:6}] {atype}")

        # Assertions
        leaked_resolved = to_resolve & seen_types_rerun
        if leaked_resolved:
            print(f"    ❌ COOLDOWN FAILED: these alert_types fired again "
                  f"after being resolved: {leaked_resolved}")
        else:
            print(f"    ✅ cooldown active: none of {sorted(to_resolve)} "
                  f"fired in the re-run")

        # Sanity check: the non-resolved types should still be there
        not_resolved_baseline = {
            "cash_runway_critical",
            "high_risk_invoice",
            "unit_cost_increase",
        }
        # Note: persistent_negative_cashflow is MEDIUM and depends on
        # daily-cashflow detection — it may or may not re-fire depending
        # on streak state; we don't assert on it.
        still_alive = not_resolved_baseline & seen_types_rerun
        missing = not_resolved_baseline - seen_types_rerun
        if missing:
            print(f"    ⚠️  these non-resolved types DIDN'T re-fire "
                  f"(could be legit dedup by entity_key, but worth a look): "
                  f"{missing}")
        if still_alive:
            print(f"    ✅ non-resolved types correctly re-fired: "
                  f"{sorted(still_alive)} (cooldown is alert_type-scoped, "
                  f"not a global mute)")
    else:
        print("\n[7/7] P2.3 cooldown check skipped "
              "(set SMOKE_TEST_COOLDOWN=1 to enable)")

    print("\n" + "=" * 72)
    print("Smoke complete.")
    if not args.keep_data:
        print("Run with --keep-data to preserve the smoke org for manual inspection.")
        print("Re-running this script wipes only smoke-tagged docs (other data is safe).")
    print("=" * 72)


if __name__ == "__main__":
    asyncio.run(main())
