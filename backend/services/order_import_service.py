"""
Order Import Service — CSV/XLSX bulk import for orders.

Parses an uploaded file, maps columns, resolves/creates customers,
groups rows by (customer + date) into orders, auto-confirms each order
(generating SalesRecords for the cashflow), and returns import stats.

Reuses parsing infrastructure from dataset_service (parse_file_to_dataframe,
clean_date, clean_amount, clean_text, _normalize_col) and entity resolution
from entity_resolver (build_customer_name_map).

Design:
  - Isolated: does NOT modify dataset_service or order_service logic.
  - Non-blocking: entity resolution, customer creation, and post-hooks
    fail gracefully — never interrupt the import.
  - Modular: follows the same column-mapping + 422/409 pattern as datasets.
"""

import logging
import base64
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

from services.file_parsing import (
    parse_file_to_dataframe,
    clean_date,
    clean_amount,
    clean_text,
    _normalize_col,
    SUPPORTED_EXTENSIONS,
    _deduplicate_columns,
)
from services.entity_resolver import (
    build_customer_name_map,
    normalize_entity_text,
    resolve_by_name,
)
from models.dataset import SalesRecord

logger = logging.getLogger(__name__)

_MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB

# ── Target fields for order import ────────────────────────────────────────────

ORDER_TARGET_FIELDS = {
    "customer_name":  {"label": "Cliente",           "required": True,  "help": "Nome del cliente"},
    "customer_email": {"label": "Email Cliente",     "required": False, "help": "Email del cliente — usata per creare/aggiornare l'anagrafica"},
    "date":           {"label": "Data Ordine",       "required": True,  "help": "Data dell'ordine"},
    "product_name":   {"label": "Prodotto",          "required": True,  "help": "Nome del prodotto / servizio"},
    "quantity":       {"label": "Quantità",          "required": False, "help": "Quantità (default: 1)"},
    "unit_price":     {"label": "Prezzo Unitario",   "required": True,  "help": "Prezzo per unità"},
    "discount_pct":   {"label": "Sconto %",          "required": False, "help": "Sconto percentuale (0-100)"},
    "category":       {"label": "Categoria",         "required": False},
    "sku":            {"label": "Codice Prodotto",   "required": False},
    "notes":          {"label": "Note",              "required": False},
    "due_date":       {"label": "Data Scadenza",     "required": False, "help": "Scadenza pagamento"},
    "payment_status": {"label": "Stato Pagamento",   "required": False, "help": "pending, paid, overdue"},
}

# ── Hardcoded column aliases for order import ─────────────────────────────────

_ORDER_ALIASES = {
    # customer_name
    "cliente": "customer_name",
    "customer": "customer_name",
    "customer_name": "customer_name",
    "nome_cliente": "customer_name",
    "ragione_sociale": "customer_name",
    # customer_email
    "email": "customer_email",
    "email_cliente": "customer_email",
    "customer_email": "customer_email",
    "mail": "customer_email",
    "e_mail": "customer_email",
    "posta_elettronica": "customer_email",
    # date
    "data": "date",
    "data_ordine": "date",
    "order_date": "date",
    "fecha": "date",
    "datum": "date",
    # product_name
    "prodotto": "product_name",
    "product": "product_name",
    "product_name": "product_name",
    "nome_prodotto": "product_name",
    "descrizione_prodotto": "product_name",
    "articolo": "product_name",
    # quantity
    "quantita": "quantity",
    "quantity": "quantity",
    "qty": "quantity",
    # unit_price
    "prezzo": "unit_price",
    "prezzo_unitario": "unit_price",
    "unit_price": "unit_price",
    "importo": "unit_price",
    "price": "unit_price",
    # discount_pct
    "sconto": "discount_pct",
    "sconto_percentuale": "discount_pct",
    "discount": "discount_pct",
    "discount_pct": "discount_pct",
    # category
    "categoria": "category",
    "category": "category",
    # sku
    "codice_prodotto": "sku",
    "codice": "sku",
    "sku": "sku",
    "product_code": "sku",
    # notes
    "note": "notes",
    "notes": "notes",
    "commenti": "notes",
    "descrizione": "notes",
    # due_date
    "scadenza": "due_date",
    "data_scadenza": "due_date",
    "payment_due": "due_date",
    "due_date": "due_date",
    # payment_status
    "stato_pagamento": "payment_status",
    "payment_status": "payment_status",
    "pagato": "payment_status",
}


# ── Column analysis (reuses dataset_service pattern) ─────────────────────────

async def analyze_order_import(
    content: bytes,
    filename: str,
    org_id: str,
) -> dict:
    """Analyze file columns and determine if interactive mapping is needed.

    Returns dict with status, recognized/unmapped columns, target_fields, preview.
    """
    file_ext = Path(filename).suffix.lower()
    if file_ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Formato file non supportato. Formati accettati: {', '.join(SUPPORTED_EXTENSIONS)}")

    df = parse_file_to_dataframe(content, filename)

    recognized = {}
    unmapped = []
    mapped_targets = set()

    for col in df.columns:
        norm = _normalize_col(col)
        target = _ORDER_ALIASES.get(norm, norm)
        if target in ORDER_TARGET_FIELDS:
            recognized[str(col)] = target
            mapped_targets.add(target)
        elif norm in ORDER_TARGET_FIELDS:
            recognized[str(col)] = norm
            mapped_targets.add(norm)
        else:
            unmapped.append(str(col))

    missing_required = [
        field for field, meta in ORDER_TARGET_FIELDS.items()
        if meta["required"] and field not in mapped_targets
    ]

    preview_df = df.head(3).fillna("")
    preview_rows = []
    for _, row in preview_df.iterrows():
        preview_rows.append({str(col): str(row[col]) for col in df.columns})

    status = "auto_mapped" if (not missing_required and not unmapped) else "needs_column_mapping"

    return {
        "status": status,
        "recognized_columns": recognized,
        "unmapped_columns": unmapped,
        "missing_required": missing_required,
        "target_fields": dict(ORDER_TARGET_FIELDS),
        "preview_rows": preview_rows,
        "all_file_columns": [str(c) for c in df.columns],
    }


# ── Row processing ───────────────────────────────────────────────────────────

def _process_order_rows(df, column_map: dict):
    """Clean and validate each row, returning (rows, errors).

    Each row dict has: customer_name, date, product_name, quantity,
    unit_price, discount_pct, line_total, category, sku, notes,
    due_date, payment_status.
    """
    import pandas as pd

    # Apply column mapping
    df.columns = [column_map.get(_normalize_col(col), _normalize_col(col)) for col in df.columns]
    df = _deduplicate_columns(df)

    rows = []
    errors = []

    for idx, raw_row in df.iterrows():
        row_num = idx + 2  # 1-indexed + header

        # Required: customer_name
        cust_raw = raw_row.get("customer_name")
        if pd.isna(cust_raw) if hasattr(pd, 'isna') else cust_raw is None:
            cust_raw = None
        customer_name = clean_text(cust_raw)
        if not customer_name:
            errors.append(f"Riga {row_num}: cliente mancante")
            continue

        # Required: date
        date_val = clean_date(raw_row.get("date"))
        if not date_val:
            errors.append(f"Riga {row_num}: data mancante o non valida")
            continue

        # Required: product_name
        product_name = clean_text(raw_row.get("product_name"))
        if not product_name:
            errors.append(f"Riga {row_num}: prodotto mancante")
            continue

        # Required: unit_price
        unit_price = clean_amount(raw_row.get("unit_price"))
        if unit_price is None:
            errors.append(f"Riga {row_num}: prezzo unitario mancante o non valido")
            continue

        # Optional: quantity (default 1)
        quantity = clean_amount(raw_row.get("quantity"))
        if quantity is None or quantity <= 0:
            quantity = 1.0

        # Optional: discount_pct (default 0)
        discount_pct = clean_amount(raw_row.get("discount_pct"))
        if discount_pct is None or discount_pct < 0 or discount_pct > 100:
            discount_pct = 0.0

        line_total = round(unit_price * quantity * (1 - discount_pct / 100), 2)

        # Optional fields
        category = clean_text(raw_row.get("category"))
        sku = clean_text(raw_row.get("sku"))
        notes = clean_text(raw_row.get("notes"))
        due_date = clean_date(raw_row.get("due_date"))
        payment_status = clean_text(raw_row.get("payment_status"))
        if payment_status and payment_status.lower() in ("paid", "pagato", "si", "sì", "yes", "true"):
            payment_status = "paid"
        elif payment_status and payment_status.lower() in ("overdue", "scaduto"):
            payment_status = "overdue"
        else:
            payment_status = "pending"

        # Optional: customer_email (for customer entity enrichment)
        customer_email = clean_text(raw_row.get("customer_email"))
        # Basic email validation — must contain @
        if customer_email and "@" not in customer_email:
            customer_email = None

        rows.append({
            "customer_name": customer_name,
            "customer_email": customer_email,
            "date": date_val,
            "product_name": product_name,
            "quantity": quantity,
            "unit_price": unit_price,
            "discount_pct": discount_pct,
            "line_total": line_total,
            "category": category,
            "sku": sku,
            "notes": notes,
            "due_date": due_date,
            "payment_status": payment_status,
        })

    return rows, errors


# ── Main import execution ────────────────────────────────────────────────────

async def execute_order_import(
    content: bytes,
    filename: str,
    org_id: str,
    user_id: str,
    user_column_mapping: Optional[dict] = None,
) -> dict:
    """Parse file, resolve/create customers, group into orders, auto-confirm.

    Performance-optimised pipeline:
      - File parsed once (caller passes content, no re-parse)
      - Customer resolution: 1 bulk query + targeted creates/updates
      - Customer name cache built from resolution (no extra find_by_id)
      - Orders inserted via batch insert_many (1 DB call)
      - SalesRecords inserted via batch insert_many (1 DB call)
      - Module hooks fired once at the end (not per order)
      - No email, calendar, stock ops (not needed for historical import)

    v5.8 / Onda 9.Y.0 — Billing-gated. Two pre-flight checks fire BEFORE
    any DB writes:
      · commerce.orders_monthly  (one event per imported order group)
      · cashflow_monitor.data_rows (one event per generated SalesRecord)
    Each check raises 429 QUOTA_EXCEEDED if the import would push the
    org past its plan limits. After successful insert, both counters are
    incremented with the actual quantity processed.

    Closes Bug A — bulk import was previously the largest data_rows
    bypass: a Free org could shovel arbitrary CSVs and never trip the
    quota because the import path skipped record_module_usage entirely.
    """
    from repositories import customer_repository, order_repository
    from repositories import sales_repository
    from database import orders_collection
    from models.customer import CustomerCreate
    from models.order import Order, OrderLineBase, OrderStatus, OrderPaymentStatus
    from models.common import generate_id, utc_now
    from services.order_service import derive_fulfillment
    from services.module_access import check_module_access, record_module_usage
    from services.currency_service import get_currency_for_org
    from repositories import organization_repository

    # CH compliance v1: imported orders inherit the org's currency. Without
    # this, every imported order silently fell back to the legacy ``"EUR"``
    # default on Order, which would silently mis-currency a CHF merchant's
    # historical archive.
    org_doc = await organization_repository.find_by_id(org_id)
    import_currency = get_currency_for_org(org_doc or {})

    # 1. Parse file (once)
    df = parse_file_to_dataframe(content, filename)

    # 2. Build column map
    column_map = dict(_ORDER_ALIASES)
    if user_column_mapping:
        for file_col, target_field in user_column_mapping.items():
            norm = _normalize_col(file_col)
            column_map[norm] = target_field

    # 3. Process rows (pure CPU, no DB)
    rows, errors = _process_order_rows(df, column_map)

    if not rows:
        raise ValueError(
            f"Nessuna riga valida trovata. Errori: {'; '.join(errors[:5])}"
        )

    # 3b. Onda 9.Y.0 — Pre-flight quota check.
    # We can't know the exact orders count until grouping (step 6), but
    # we can upper-bound it by len(rows) — one row → at most one order.
    # data_rows is exactly len(rows) (one SalesRecord per valid row).
    # Both checks fire before any DB write so a Free user at quota gets
    # 429 with no side effects.
    pending_data_rows = len(rows)
    pending_orders_upper_bound = len(rows)
    await check_module_access(
        org_id, "cashflow_monitor", "data_rows",
        pending_quantity=pending_data_rows,
    )
    await check_module_access(
        org_id, "commerce", "orders_monthly",
        pending_quantity=pending_orders_upper_bound,
    )

    # 4. Customer resolution — 1 bulk query + targeted creates/updates
    #    build_customer_name_map does 1 query (find_by_org with limit=10000).
    #    We reuse the loaded data for name cache too (no extra find_by_id).
    customer_name_map = await build_customer_name_map(org_id)
    customers_created = 0
    customers_updated = 0

    # Collect best email per customer name (first non-null from rows)
    name_to_email = {}
    for r in rows:
        key = normalize_entity_text(r["customer_name"])
        if r.get("customer_email") and key not in name_to_email:
            name_to_email[key] = r["customer_email"]

    # Resolve all unique customer names — build name→(id, display_name) map
    unique_names = set(r["customer_name"] for r in rows)
    name_to_id = {}          # norm_key → customer_id
    cust_name_cache = {}     # customer_id → display_name

    for name in unique_names:
        norm_key = normalize_entity_text(name)
        email = name_to_email.get(norm_key)
        cid = resolve_by_name(customer_name_map, name)
        if cid:
            name_to_id[norm_key] = cid
            cust_name_cache[cid] = name  # use CSV name as display (avoid find_by_id)
            # Enrich existing customer with email if they don't have one
            if email:
                try:
                    existing = await customer_repository.find_by_id(cid, org_id)
                    if existing and not existing.email:
                        await customer_repository.update(cid, org_id, {"email": email})
                        customers_updated += 1
                    if existing:
                        cust_name_cache[cid] = existing.name  # use DB name (authoritative)
                except Exception as e:
                    logger.warning("order_import: failed to enrich customer '%s': %s", name, e)
        else:
            # Auto-create customer with email — 1 insert
            try:
                new_customer = await customer_repository.create(
                    org_id, CustomerCreate(name=name, email=email),
                )
                name_to_id[norm_key] = new_customer.id
                cust_name_cache[new_customer.id] = new_customer.name
                customers_created += 1
            except Exception as e:
                logger.warning("order_import: failed to create customer '%s': %s", name, e)
                errors.append(f"Impossibile creare cliente '{name}': {e}")

    # 5. Assign customer_id to each row
    for row in rows:
        row["customer_id"] = name_to_id.get(normalize_entity_text(row["customer_name"]))

    valid_rows = [r for r in rows if r.get("customer_id")]
    skipped_no_customer = len(rows) - len(valid_rows)
    if skipped_no_customer > 0:
        errors.append(f"{skipped_no_customer} righe skippate: cliente non risolvibile")

    # 6. Group by (customer_id, date) → one order per group
    groups = defaultdict(list)
    for row in valid_rows:
        groups[(row["customer_id"], row["date"])].append(row)

    # 7. Build all order docs + SalesRecord docs in memory (no DB yet)
    #    1 query for next order number, then pure CPU loop.
    base_order_number = await order_repository.get_next_order_number(org_id)
    next_num = int(base_order_number.split("-", 1)[1])

    all_order_docs = []
    all_sales_docs = []

    for (customer_id, order_date), group_rows in groups.items():
        try:
            all_notes = list(dict.fromkeys(
                r["notes"] for r in group_rows if r.get("notes")
            ))
            order_notes = "; ".join(all_notes) if all_notes else None
            due_date = next((r["due_date"] for r in group_rows if r.get("due_date")), None)

            all_paid = all(r["payment_status"] == "paid" for r in group_rows)
            any_overdue = any(r["payment_status"] == "overdue" for r in group_rows)
            order_payment = "paid" if all_paid else ("overdue" if any_overdue else "pending")

            lines = [
                OrderLineBase(
                    product_id="__import__",
                    product_name=r["product_name"],
                    sku=r.get("sku"),
                    category=r.get("category"),
                    item_type="physical",
                    transaction_mode="direct",
                    quantity=r["quantity"],
                    unit_price=r["unit_price"],
                    discount_pct=r["discount_pct"],
                    line_total=r["line_total"],
                )
                for r in group_rows
            ]

            subtotal = round(sum(l.line_total for l in lines), 2)
            order_number = f"ORD-{next_num:04d}"
            next_num += 1

            order = Order(
                organization_id=org_id,
                customer_id=customer_id,
                currency=import_currency,
                order_date=order_date,
                due_date=due_date,
                notes=order_notes,
                items=lines,
                subtotal=subtotal,
                total=subtotal,
                status=OrderStatus.CONFIRMED,
                payment_status=OrderPaymentStatus(order_payment),
                source="import",
            )

            doc = order.model_dump(mode="json")
            doc["customer_name"] = cust_name_cache.get(customer_id, group_rows[0]["customer_name"])
            doc["order_number"] = order_number
            doc["fulfillment"] = derive_fulfillment(lines)
            all_order_docs.append(doc)

            for line in lines:
                sale = SalesRecord(
                    organization_id=org_id,
                    dataset_id="orders",
                    date=order_date,
                    amount=round(line.line_total, 2),
                    category=line.category,
                    description=f"Ordine {order_number}: {line.product_name} x {line.quantity}",
                    customer_id=customer_id,
                    product_id=line.product_id,
                    payment_status=order_payment,
                    due_date=due_date,
                    source_label="Ordini",
                )
                sale_doc = sale.model_dump()
                sale_doc["metadata"] = {"order_id": order.id, "order_number": order_number}
                all_sales_docs.append(sale_doc)

        except Exception as e:
            logger.warning("order_import: failed to build order for (%s, %s): %s",
                           customer_id[:8] if customer_id else "?", order_date, e)
            errors.append(f"Errore creazione ordine ({group_rows[0]['customer_name']}, {order_date}): {e}")

    # 8. Batch-insert orders (1 DB call)
    orders_created = 0
    if all_order_docs:
        try:
            await orders_collection.insert_many(all_order_docs)
            orders_created = len(all_order_docs)
            # Clean _id from docs (not JSON-serializable)
            for doc in all_order_docs:
                doc.pop("_id", None)
        except Exception as e:
            logger.error("order_import: orders batch insert failed: %s", e)
            errors.append(f"Errore inserimento ordini: {e}")

    # 9. Batch-insert SalesRecords (1 DB call)
    sales_records_generated = 0
    if all_sales_docs:
        try:
            count = await sales_repository.insert_many(all_sales_docs)
            sales_records_generated = count
        except Exception as e:
            logger.warning("order_import: SalesRecords batch insert failed: %s", e)
            errors.append(f"Errore inserimento SalesRecords: {e}")

    # 9b. Onda 9.Y.0 — Record actual usage post-insert.
    # We post-record (not pre-record) so a partial failure during the
    # batch insert doesn't bill the user for rows that didn't land.
    # Idempotency note: ai_usage_events is append-only, so a retry of
    # this whole import would double-count. Order_import is not
    # idempotent at the API layer (no idempotency-key header), so this
    # matches existing semantics — retries are the caller's problem.
    if orders_created > 0:
        try:
            await record_module_usage(
                org_id, "commerce", "orders_monthly", quantity=orders_created,
            )
        except Exception as e:
            logger.warning("order_import: failed to record orders_monthly usage: %s", e)
    if sales_records_generated > 0:
        try:
            await record_module_usage(
                org_id, "cashflow_monitor", "data_rows", quantity=sales_records_generated,
            )
        except Exception as e:
            logger.warning("order_import: failed to record data_rows usage: %s", e)

    # 10. Trigger module hooks ONCE — fire-and-forget in background
    #     These hooks (KPI snapshots, alert generation, customer/product metrics)
    #     are heavy DB operations. Running them in background avoids blocking
    #     the import response.
    import asyncio
    async def _run_hooks_background():
        try:
            from services.order_service import _trigger_module_hooks
            await _trigger_module_hooks(org_id)
        except Exception as e:
            logger.warning("order_import: background hooks failed: %s", e)
    asyncio.create_task(_run_hooks_background())

    logger.info(
        "order_import: org=%s — %d orders, %d customers, %d SalesRecords in 2 batch inserts",
        org_id, orders_created, customers_created, sales_records_generated,
    )

    return {
        "orders_created": orders_created,
        "customers_created": customers_created,
        "customers_updated": customers_updated,
        "sales_records_generated": sales_records_generated,
        "rows_processed": len(valid_rows),
        "rows_skipped": len(rows) - len(valid_rows) + (df.shape[0] - len(rows)),
        "errors": errors[:20],
    }
