"""
Dataset Service — v2.1.

Changes vs Phase 2 (all backward-compatible):
  1. [Phase 2] S3 dual-write: files are uploaded to S3 when AWS env vars are present.
     Local disk write is always performed as fallback.  s3_key stored on dataset.
  2. [Phase 2] Column mapping hook: org-specific mappings in column_mappings collection
     are applied before the hardcoded standardization table.
  3. [Phase 2] KPI snapshot trigger: after every successful upload,
     kpi_snapshot_service.compute_all_granularities() is called fire-and-forget.
  4. [Phase 2] schema_version="2.0" + source_type="file_upload" stamped on every new document.
  5. [Phase 2] DatasetColumnProfile saved per dataset for future UI hints.
  6. [v2.1] Extra CSV columns preserved in record metadata instead of being discarded.
  7. [v2.1] source_record_id populated from the DataFrame row index on every record.
  8. [v2.1] Non-blocking supplier name → supplier_id auto-match for expense uploads.
  9. [v2.1] Dataset-scoped replace strategy: old active dataset records deleted by
     dataset_id instead of org-wide bulk delete, with safe fallback to legacy behaviour.
 10. [v2.2] Active DataValidationRules evaluated after row cleaning; invalid rows are
     skipped (not inserted) and reported in the audit log.  Non-blocking: engine
     failures and missing rules never interrupt the upload.

Public interface unchanged — parse_and_save_dataset() signature is identical.
"""
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

import io
import re
import unicodedata
import pandas as pd
import numpy as np

from models import Dataset, DatasetType, SalesRecord, ExpenseRecord, AuditLog, PurchaseRecord, FixedCost
from models.column_mapping import DatasetColumnProfile, ColumnStat
from repositories import dataset_repository, audit_repository
from repositories.column_mapping_repository import (
    find_mappings_by_org_and_type,
    upsert_profile,
)

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────
UPLOAD_DIR = Path(__file__).parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

SUPPORTED_EXTENSIONS = [".csv", ".xlsx", ".xls"]

_SCHEMA_VERSION = "2.0"

# ── Canonical field sets (v2.1) ───────────────────────────────────────────────
# Columns that map to named model fields.  Everything else goes into metadata.
_CANONICAL_SALES_FIELDS: frozenset = frozenset({
    "date", "amount", "category", "description", "channel",
})
_CANONICAL_EXPENSE_FIELDS: frozenset = frozenset({
    "date", "amount", "category", "description", "supplier",
})


# ── Hardcoded column alias table (legacy fallback) ────────────────────────────
_HARDCODED_ALIASES = {
    "data": "date", "fecha": "date", "datum": "date", "giorno": "date",
    "importo": "amount", "valore": "amount", "value": "amount",
    "price": "amount", "total": "amount", "totale": "amount",
    "sum": "amount", "somma": "amount",
    "categoria": "category", "cat": "category", "tipo": "category", "type": "category",
    "descrizione": "description", "desc": "description", "note": "description", "notes": "description",
    "canale": "channel",
    "fornitore": "supplier", "vendor": "supplier", "provider": "supplier",
    "data_scadenza": "due_date", "scadenza": "due_date", "payment_due": "due_date",
    "stato_pagamento": "payment_status", "pagato": "is_paid",
    # ── Entity linking lookup columns (v7.0) ──────────────────────────────
    # Virtual columns consumed by entity resolution and stripped before insert.
    "cliente": "customer_name_lookup",
    "customer": "customer_name_lookup",
    "customer_name": "customer_name_lookup",
    "nome_cliente": "customer_name_lookup",
    "codice_cliente": "customer_extid_lookup",
    "customer_code": "customer_extid_lookup",
    "codice_prodotto": "product_sku_lookup",
    "product_code": "product_sku_lookup",
    "sku": "product_sku_lookup",
}


# ── Column helpers ────────────────────────────────────────────────────────────

def _normalize_col(col: str) -> str:
    """Normalize raw column name to lowercase snake_case, remove special chars.

    Accented characters (à, è, ù …) are transliterated to their ASCII
    equivalent so that Italian headers like "Quantità" become "quantita"
    instead of being stripped to "quantit".
    """
    if not col:
        return ""
    col = str(col).lower().strip()
    # Transliterate accented chars → ASCII (e.g. à→a, è→e, ü→u)
    col = unicodedata.normalize("NFKD", col)
    col = col.encode("ascii", "ignore").decode("ascii")
    col = re.sub(r"[\s\-_]+", "_", col)
    col = re.sub(r"[^a-z0-9_]", "", col)
    return col


def standardize_column_name(col: str) -> str:
    """Apply hardcoded alias table (unchanged legacy entry point)."""
    normalized = _normalize_col(col)
    return _HARDCODED_ALIASES.get(normalized, normalized)


async def _build_column_map(org_id: str, dataset_type: DatasetType) -> dict:
    """Build a {raw_normalized → target_field} dict merging DB mappings + hardcoded aliases.

    DB mappings take precedence over hardcoded ones.
    """
    mapping = dict(_HARDCODED_ALIASES)  # start with hardcoded defaults

    # Add type-specific aliases only when relevant to avoid conflicts
    # (e.g. 'importo' → 'amount' for sales but 'total_price' for purchases)
    if dataset_type == DatasetType.PURCHASES:
        mapping.update({
            'nome_fornitore': 'supplier_name',
            'fornitore': 'supplier_name',
            'supplier': 'supplier_name',
            'quantita': 'quantity',
            'qty': 'quantity',
            'prezzo_unitario': 'unit_price',
            'prezzo': 'unit_price',
            'unita': 'unit',
            'unita_di_misura': 'unit',
            'um': 'unit',
            'prezzo_totale': 'total_price',
            'totale': 'total_price',
            'importo': 'total_price',
            'costo': 'total_price',
            'total': 'total_price',
            'amount': 'total_price',
            # VAT aliases (Wave A)
            'iva': 'iva',
            'aliquota_iva': 'iva',
            'aliquota': 'iva',
            'vat': 'iva',
            'vat_rate': 'iva',
            'iva_%': 'iva',
            'totale_con_iva': 'total_with_iva',
            'totale_iva': 'total_with_iva',
            'totale_lordo': 'total_with_iva',
            'gross_total': 'total_with_iva',
            # Prodotto aliases (category = product in purchase context)
            'prodotto': 'category',
            'product': 'category',
            'articolo': 'category',
            # Categoria (macro) aliases (Wave A.1)
            'categoria_macro': 'category_macro',
            'macro_categoria': 'category_macro',
            'category_macro': 'category_macro',
            'macro_category': 'category_macro',
            'macro': 'category_macro',
            'gruppo': 'category_macro',
            # Due date / invoice / payment status aliases
            'data_scadenza': 'due_date',
            'scadenza': 'due_date',
            'payment_due': 'due_date',
            'numero_fattura': 'invoice_number',
            'fattura': 'invoice_number',
            'invoice': 'invoice_number',
            'stato_pagamento': 'payment_status',
            'stato': 'payment_status',
            'payment_status': 'payment_status',
        })
    elif dataset_type == DatasetType.FIXED_COSTS:
        mapping.update({
            'nome': 'name',
            'nome_costo': 'name',
            'voce': 'name',
            'frequenza': 'frequency',
            'ricorrenza': 'frequency',
            'data_inizio': 'start_date',
            'inizio': 'start_date',
            'data_fine': 'end_date',
            'fine': 'end_date',
        })

    try:
        db_mappings = await find_mappings_by_org_and_type(org_id, dataset_type.value)
        for m in db_mappings:
            key = _normalize_col(m.source_column)
            mapping[key] = m.target_field
    except Exception as exc:
        logger.warning("_build_column_map: could not load DB mappings: %s", exc)

    return mapping


async def _build_supplier_name_map(org_id: str) -> dict:
    """Return {lowercase_name → supplier_id} for all active suppliers in the org.

    v2.1 addition — used for non-blocking auto-match during expense ingestion.
    Never raises: returns {} on any error so ingestion is never interrupted.
    Matching is case-insensitive exact (lowercase + strip on both sides).
    """
    try:
        from repositories.supplier_repository import find_by_org as find_suppliers
        suppliers = await find_suppliers(org_id, active_only=True)
        return {s.name.lower().strip(): s.id for s in suppliers if s.name}
    except Exception as exc:
        logger.warning("_build_supplier_name_map: could not load suppliers: %s", exc)
        return {}


async def _run_post_upload_hooks(org_id: str) -> None:
    """Run post-upload hooks for all modules registered in core.module_registry.

    Each hook is isolated: a failure in one does not prevent others from
    running and never interrupts the upload response.  This replaces the
    previous hardcoded call to kpi_snapshot_service.compute_all_granularities()
    (step 10) with a registry-driven dispatch that automatically handles
    any future module registrations without modifying this file.

    Hooks are executed in parallel via asyncio.gather (each module is
    independent).  return_exceptions=True ensures a failure in one hook
    does not cancel others.
    """
    import asyncio
    from core.module_registry import get_all as registry_get_all

    async def _safe_hook(hook, org_id: str):
        try:
            await hook(org_id)
        except Exception as exc:
            logger.warning(
                "Post-upload hook %s failed for org %s: %s",
                getattr(hook, "__name__", repr(hook)), org_id, exc,
            )

    tasks = []
    for module in registry_get_all():
        for hook in module.post_upload_hooks:
            tasks.append(_safe_hook(hook, org_id))

    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


async def _load_validation_rules(org_id: str, dataset_type: str) -> list:
    """Fetch active DataValidationRules for (org, dataset_type).

    Non-blocking: returns an empty list on any database or import error so the
    upload pipeline is never interrupted when rules cannot be loaded.
    Lazy import avoids circular-import risk at module load time.
    """
    try:
        from repositories.data_validation_rule_repository import find_active_by_org_and_type
        return await find_active_by_org_and_type(org_id, dataset_type)
    except Exception as exc:
        logger.warning("_load_validation_rules: could not load rules: %s", exc)
        return []


# ── Amount / date / text cleaners (unchanged) ─────────────────────────────────

def clean_amount(value) -> Optional[float]:
    """Locale-tolerant numeric parser — delegates to core.numeric.

    Handles European (1.234,56), US (1,234.56), and bare formats.
    Returns None on failure.  See core/numeric.py for full rule set.
    """
    if pd.isna(value):
        return None
    from core.numeric import parse_locale_number
    return parse_locale_number(value)


def clean_date(value) -> Optional[str]:
    """Parse a raw date value into ISO "YYYY-MM-DD" format.

    Handles:
    - datetime / pd.Timestamp / datetime.date objects (returned directly)
    - Excel timestamp strings like "2026-03-12 00:00:00"
    - Italian month names ("12 marzo 2026" → "12 March 2026")
    - European DD/MM/YYYY formats (always tried before American MM/DD/YYYY)

    American formats (%m/%d/%Y, %m-%d-%Y) are kept at the END of the list so
    that an ambiguous value like "12/03/2026" is always read as 12 March, not
    3 December.
    """
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    # datetime / Timestamp / date objects ─────────────────────────────────────
    if isinstance(value, (datetime, pd.Timestamp)):
        return value.strftime("%Y-%m-%d")
    if hasattr(value, "strftime"):           # catches datetime.date
        return value.strftime("%Y-%m-%d")

    val_str = str(value).strip()
    if not val_str or val_str.lower() in ("nat", "nan", "none", "n/a", ""):
        return None

    # Italian month names → English so strptime can match ────────────────────
    _ITALIAN_MONTHS = {
        "gennaio": "January", "febbraio": "February", "marzo": "March",
        "aprile": "April",    "maggio": "May",        "giugno": "June",
        "luglio": "July",     "agosto": "August",     "settembre": "September",
        "ottobre": "October", "novembre": "November", "dicembre": "December",
        "gen": "Jan", "feb": "Feb", "mar": "Mar", "apr": "Apr",
        "mag": "May", "giu": "Jun", "lug": "Jul", "ago": "Aug",
        "set": "Sep", "ott": "Oct", "nov": "Nov", "dic": "Dec",
    }
    val_lower = val_str.lower()
    for ita, eng in _ITALIAN_MONTHS.items():
        if ita in val_lower:
            val_str = val_str.lower().replace(ita, eng)
            break

    # Format priority: European-first.  American formats are last resort. ─────
    date_formats = [
        "%Y-%m-%d",           # ISO:             2026-03-12
        "%Y-%m-%d %H:%M:%S",  # ISO + time:      2026-03-12 00:00:00 (Excel/pandas)
        "%Y-%m-%dT%H:%M:%S",  # ISO 8601:        2026-03-12T00:00:00
        "%d/%m/%Y",           # European slash:  12/03/2026
        "%d-%m-%Y",           # European dash:   12-03-2026
        "%d.%m.%Y",           # European dot:    12.03.2026
        "%Y/%m/%d",           # Year-first:      2026/03/12
        "%d %b %Y",           # Short month:     12 Mar 2026
        "%d %B %Y",           # Full month:      12 March 2026
        "%b %d, %Y",          # Short American:  Mar 12, 2026
        "%B %d, %Y",          # Full American:   March 12, 2026
        "%Y%m%d",             # Compact:         20260312
        "%m/%d/%Y",           # American slash (last resort): 03/12/2026
        "%m-%d-%Y",           # American dash  (last resort): 03-12-2026
    ]
    for fmt in date_formats:
        try:
            return datetime.strptime(val_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    try:
        return pd.to_datetime(val_str, dayfirst=True).strftime("%Y-%m-%d")
    except Exception:
        pass
    return None


def clean_text(value) -> Optional[str]:
    if pd.isna(value) or value is None:
        return None
    val_str = str(value).strip()
    if not val_str or val_str.lower() in ["nan", "null", "none", "n/a", "na", "-"]:
        return None
    return re.sub(r"\s+", " ", val_str)


# ── File parsing (unchanged) ──────────────────────────────────────────────────

def parse_file_to_dataframe(content: bytes, filename: str) -> pd.DataFrame:
    ext = Path(filename).suffix.lower()
    if ext == ".csv":
        for encoding in ["utf-8", "latin-1", "iso-8859-1", "cp1252"]:
            for sep in [",", ";", "\t", "|"]:
                try:
                    df = pd.read_csv(
                        io.BytesIO(content), encoding=encoding, sep=sep, dtype=str,
                        na_values=["", "NA", "N/A", "null", "NULL", "None", "NaN"],
                    )
                    if len(df.columns) > 1 or (len(df.columns) == 1 and sep == ","):
                        return df
                except Exception:
                    continue
        raise ValueError("Impossibile leggere il file CSV. Verifica codifica e separatore.")
    elif ext == ".xlsx":
        try:
            return pd.read_excel(io.BytesIO(content), engine="openpyxl", dtype=str,
                                  na_values=["", "NA", "N/A", "null", "NULL", "None", "NaN"])
        except Exception as exc:
            raise ValueError(f"Impossibile leggere il file XLSX: {exc}")
    elif ext == ".xls":
        try:
            return pd.read_excel(io.BytesIO(content), engine="xlrd", dtype=str,
                                  na_values=["", "NA", "N/A", "null", "NULL", "None", "NaN"])
        except Exception as exc:
            raise ValueError(f"Impossibile leggere il file XLS: {exc}")
    else:
        raise ValueError(f"Formato file non supportato: {ext}. Formati accettati: {', '.join(SUPPORTED_EXTENSIONS)}")


# ── DataFrame safety helpers ──────────────────────────────────────────────────
# Shared across all dataset processing functions (purchases, sales, expenses,
# fixed costs). Protect against duplicate column names after alias renaming.


def _deduplicate_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Remove duplicate columns after alias renaming.

    When multiple source columns map to the same target (e.g., "Totale" and
    "Importo" both → "amount"), pandas creates a DataFrame with duplicate
    column names. row.get() on such a DataFrame returns a Series instead
    of a scalar, which crashes any truthiness/comparison check.

    This function keeps only the first occurrence of each column name.
    """
    if df.columns.duplicated().any():
        seen = set()
        keep = []
        for i, col in enumerate(df.columns):
            if col not in seen:
                seen.add(col)
                keep.append(i)
        df = df.iloc[:, keep]
    return df


def _safe_row_get(row, col):
    """Safely get a scalar value from a DataFrame row.

    If row.get() returns a Series (due to residual duplicate columns),
    extracts the first element. This is a defense-in-depth measure
    alongside _deduplicate_columns().
    """
    val = row.get(col)
    if isinstance(val, pd.Series):
        return val.iloc[0] if len(val) > 0 else None
    return val


# ── DataFrame processing (extended with column_map param) ─────────────────────

def _process_purchases_df(
    df: pd.DataFrame,
    column_map: Optional[dict] = None,
) -> Tuple[List[dict], List[str]]:
    """Process purchases DataFrame with explicit precedence rules.

    Supports three import modes:
      Mode A — detailed: quantity + unit_price (+ optional total_price, iva, total_with_iva)
      Mode B — row total: total_price (+ optional iva, total_with_iva, no quantity/unit_price)
      Mode C — minimal: date + supplier + total_price

    Precedence rules:
      1. If file provides total_price → use it as the base total (file wins).
      2. If total_price absent but quantity + unit_price present → compute total_price.
      3. If file provides total_with_iva → use it as the gross total (file wins).
      4. If total_with_iva absent but iva present → compute from total_price + iva.
      5. IVA must be a percentage (0-100). Values > 100 trigger a warning and are ignored.

    Required columns: date + supplier_name + (total_price OR (quantity AND unit_price))
    """
    # Use module-level _safe_row_get instead of local _scalar
    def _scalar(val):
        """Backward-compat wrapper — delegates to _safe_row_get logic."""
        if isinstance(val, pd.Series):
            return val.iloc[0] if len(val) > 0 else None
        return val

    rows = []
    errors = []
    if column_map:
        df.columns = [column_map.get(_normalize_col(col), _normalize_col(col)) for col in df.columns]
    else:
        df.columns = [standardize_column_name(col) for col in df.columns]

    # Deduplicate columns (shared helper — protects against Series crash)
    df = _deduplicate_columns(df)

    # Flexible required columns: date + supplier_name + at least one amount source
    has_total_col = 'total_price' in df.columns
    has_qty_price = 'quantity' in df.columns and 'unit_price' in df.columns

    if 'date' not in df.columns:
        return [], [f"Colonna obbligatoria mancante: 'date'. Colonne trovate: {', '.join(df.columns)}"]
    if 'supplier_name' not in df.columns:
        return [], [f"Colonna obbligatoria mancante: 'supplier_name'. Colonne trovate: {', '.join(df.columns)}"]
    if not has_total_col and not has_qty_price:
        return [], [
            f"Serve almeno una fonte importo: colonna 'total_price' (Totale) "
            f"oppure 'quantity' + 'unit_price' (Quantità + Prezzo Unitario). "
            f"Colonne trovate: {', '.join(df.columns)}"
        ]

    # IVA validation heuristic: detect suspicious values that look like amounts
    iva_suspicious = False
    if 'iva' in df.columns:
        iva_values = df['iva'].dropna().apply(lambda v: clean_amount(str(v)) if v is not None else None).dropna()
        if len(iva_values) > 0:
            over_100_count = sum(1 for v in iva_values if v > 100)
            if over_100_count > len(iva_values) * 0.5:
                iva_suspicious = True
                errors.append(
                    "⚠ La colonna mappata come 'IVA %' contiene valori superiori a 100 "
                    "nella maggioranza delle righe. Verifica che questa colonna contenga "
                    "aliquote IVA (es. 22, 10, 4) e non importi monetari. "
                    "Se contiene importi lordi, mappala come 'Totale con IVA'."
                )

    for idx, row in df.iterrows():
        row_num = idx + 2
        try:
            date_val = clean_date(_scalar(row.get('date')))
            if not date_val:
                errors.append(f"Riga {row_num}: Data non valida o mancante")
                continue

            # ── Step 1: Resolve total_price with precedence ──────────────
            file_total = clean_amount(_scalar(row.get('total_price')))
            quantity = clean_amount(_scalar(row.get('quantity')))
            unit_price = clean_amount(_scalar(row.get('unit_price')))
            computed_total = None
            if quantity is not None and unit_price is not None:
                computed_total = round(quantity * unit_price, 2)

            # Precedence: file total_price wins over computed
            if file_total is not None:
                total_price = round(file_total, 2)
            elif computed_total is not None:
                total_price = computed_total
            else:
                errors.append(f"Riga {row_num}: Nessun importo disponibile (serve Totale oppure Quantità + Prezzo)")
                continue

            # Default quantity/unit_price if not provided (Mode B/C)
            if quantity is None:
                quantity = 1.0
            if unit_price is None:
                unit_price = total_price  # single unit = total

            # ── Step 2: Resolve IVA ──────────────────────────────────────
            iva_val = clean_amount(_scalar(row.get('iva'))) if not iva_suspicious else None
            if iva_val is not None and not (0 <= iva_val <= 100):
                iva_val = None  # invalid range, ignore

            # ── Step 3: Resolve total_with_iva with precedence ───────────
            total_with_iva = None
            file_twi = clean_amount(_scalar(row.get('total_with_iva')))

            if file_twi is not None:
                # File-provided gross total wins
                total_with_iva = round(file_twi, 2)
            elif iva_val is not None:
                # Compute from total_price + IVA
                total_with_iva = round(total_price * (1 + iva_val / 100), 2)

            # ── Step 4: Resolve optional metadata fields ────────────
            due_date_val = clean_date(_scalar(row.get('due_date'))) if 'due_date' in df.columns else None
            invoice_number_val = clean_text(_scalar(row.get('invoice_number'))) if 'invoice_number' in df.columns else None

            raw_ps = clean_text(_scalar(row.get('payment_status'))) if 'payment_status' in df.columns else None
            payment_status_val = None
            if raw_ps:
                ps_lower = raw_ps.lower().strip()
                _PS_MAP = {'pending': 'pending', 'in attesa': 'pending',
                           'paid': 'paid', 'pagato': 'paid',
                           'overdue': 'overdue', 'scaduto': 'overdue',
                           'cancelled': 'cancelled', 'annullato': 'cancelled'}
                payment_status_val = _PS_MAP.get(ps_lower)

            rows.append({
                'date': date_val,
                'supplier_name': clean_text(_scalar(row.get('supplier_name'))) or 'Unknown',
                'quantity': round(quantity, 2),
                'unit': clean_text(_scalar(row.get('unit'))) or 'kg',
                'unit_price': round(unit_price, 2),
                'total_price': total_price,
                'iva': iva_val,
                'total_with_iva': total_with_iva,
                'category': clean_text(_scalar(row.get('category'))),
                'category_macro': clean_text(_scalar(row.get('category_macro'))),
                'description': clean_text(_scalar(row.get('description'))),
                'invoice_number': invoice_number_val,
                'due_date': due_date_val,
                'payment_status': payment_status_val,
                'source_record_id': str(idx),
            })
        except Exception as e:
            errors.append(f"Riga {row_num}: {str(e)}")
    return rows, errors


def _process_fixed_costs_df(
    df: pd.DataFrame,
    column_map: Optional[dict] = None,
) -> Tuple[List[dict], List[str]]:
    """Process fixed costs DataFrame"""
    rows = []
    errors = []
    if column_map:
        df.columns = [column_map.get(_normalize_col(col), _normalize_col(col)) for col in df.columns]
    else:
        df.columns = [standardize_column_name(col) for col in df.columns]

    # Deduplicate columns (shared helper — protects against Series crash)
    df = _deduplicate_columns(df)

    required = ['name', 'amount', 'frequency', 'start_date']
    missing = [h for h in required if h not in df.columns]
    if missing:
        return [], [f"Colonne obbligatorie mancanti: {', '.join(missing)}. Colonne trovate: {', '.join(df.columns)}"]

    valid_frequencies = {'mensile', 'settimanale', 'trimestrale', 'annuale'}
    valid_categories = {'affitto', 'stipendio', 'finanziamento', 'leasing', 'abbonamento', 'altro'}

    for idx, row in df.iterrows():
        row_num = idx + 2
        try:
            name = clean_text(_safe_row_get(row, 'name'))
            if not name:
                errors.append(f"Riga {row_num}: Nome mancante")
                continue
            amount = clean_amount(_safe_row_get(row, 'amount'))
            if amount is None:
                errors.append(f"Riga {row_num}: Importo non valido")
                continue
            freq = clean_text(_safe_row_get(row, 'frequency')) or 'mensile'
            freq = freq.lower()
            if freq not in valid_frequencies:
                freq = 'mensile'
            cat = clean_text(_safe_row_get(row, 'category')) or 'altro'
            cat = cat.lower()
            if cat not in valid_categories:
                cat = 'altro'
            start_date = clean_date(_safe_row_get(row, 'start_date'))
            if not start_date:
                errors.append(f"Riga {row_num}: Data inizio non valida")
                continue
            end_date = clean_date(_safe_row_get(row, 'end_date'))
            rows.append({
                'name': name,
                'category': cat,
                'amount': round(amount, 2),
                'frequency': freq,
                'start_date': start_date,
                'end_date': end_date,
                'description': clean_text(_safe_row_get(row, 'description')) if 'description' in df.columns else None,
                'source_record_id': str(idx),
            })
        except Exception as e:
            errors.append(f"Riga {row_num}: {str(e)}")
    return rows, errors


def process_dataframe(
    df: pd.DataFrame,
    dataset_type: DatasetType,
    column_map: Optional[dict] = None,
) -> Tuple[List[dict], List[str]]:
    """Process DataFrame and return (clean_rows, errors).

    column_map: merged {raw_normalized → target_field} dict.
    Falls back to hardcoded standardize_column_name() when None.

    Dispatches to specialized processors for PURCHASES and FIXED_COSTS.

    v2.1 additions (backward-compatible):
    - source_record_id populated from str(idx) on every record.
    - Extra columns (not in canonical field set) collected into record["_extra"].
      This internal key is consumed by parse_and_save_dataset() to build the
      MongoDB metadata field.  It is stripped before passing to Pydantic models.
    """
    # Dispatch to specialized processors for new types
    if dataset_type == DatasetType.PURCHASES:
        return _process_purchases_df(df, column_map=column_map)
    elif dataset_type == DatasetType.FIXED_COSTS:
        return _process_fixed_costs_df(df, column_map=column_map)

    rows, errors = [], []

    if column_map:
        df.columns = [column_map.get(_normalize_col(col), _normalize_col(col)) for col in df.columns]
    else:
        df.columns = [standardize_column_name(col) for col in df.columns]

    # Deduplicate columns (shared helper — protects against Series crash)
    df = _deduplicate_columns(df)

    required = ["date", "amount"]
    missing = [h for h in required if h not in df.columns]

    if missing:
        for col in df.columns:
            if "date" in col or "data" in col or "time" in col:
                df = df.rename(columns={col: "date"})
            if "amount" in col or "value" in col or "price" in col or "total" in col:
                df = df.rename(columns={col: "amount"})
        # Re-deduplicate after fuzzy rename (may create new duplicates)
        df = _deduplicate_columns(df)
        missing = [h for h in required if h not in df.columns]
        if missing:
            return [], [f"Colonne obbligatorie mancanti: {', '.join(missing)}. Colonne trovate: {', '.join(df.columns)}"]

    # v2.1: determine which post-rename columns are extra (not canonical model fields)
    canonical = _CANONICAL_SALES_FIELDS if dataset_type == DatasetType.SALES else _CANONICAL_EXPENSE_FIELDS
    extra_cols = [c for c in df.columns if c not in canonical]

    for idx, row in df.iterrows():
        row_num = idx + 2
        try:
            date_val = clean_date(_safe_row_get(row, "date"))
            if not date_val:
                errors.append(f"Riga {row_num}: Data non valida o mancante")
                continue
            amount_val = clean_amount(_safe_row_get(row, "amount"))
            if amount_val is None:
                errors.append(f"Riga {row_num}: Importo non valido o mancante")
                continue
            record = {
                "date": date_val,
                "amount": round(amount_val, 2),
                "category": clean_text(_safe_row_get(row, "category")),
                "description": clean_text(_safe_row_get(row, "description")),
                # v2.1: row index as source_record_id for traceability
                "source_record_id": str(idx),
            }
            if dataset_type == DatasetType.SALES:
                record["channel"] = clean_text(_safe_row_get(row, "channel"))
            else:
                record["supplier"] = clean_text(_safe_row_get(row, "supplier"))

            # v3.1: extract due_date and payment_status (shared by sales & expenses)
            if 'due_date' in df.columns:
                record["due_date"] = clean_date(_safe_row_get(row, "due_date"))
            raw_ps = clean_text(_safe_row_get(row, "payment_status")) if 'payment_status' in df.columns else None
            if raw_ps:
                ps_lower = raw_ps.lower().strip()
                _PS_MAP = {'pending': 'pending', 'in attesa': 'pending',
                           'paid': 'paid', 'pagato': 'paid',
                           'overdue': 'overdue', 'scaduto': 'overdue'}
                record["payment_status"] = _PS_MAP.get(ps_lower)
            if dataset_type == DatasetType.EXPENSES and 'is_paid' in df.columns:
                raw_ip = clean_text(_safe_row_get(row, "is_paid"))
                if raw_ip:
                    record["is_paid"] = raw_ip.lower().strip() in ('true', 'si', 'sì', '1', 'yes', 'pagato')

            # v2.1: preserve extra columns instead of discarding them.
            # Stored under the internal key "_extra" which parse_and_save_dataset()
            # strips before the Pydantic constructor and writes as MongoDB "metadata".
            if extra_cols:
                extra: dict = {}
                for col in extra_cols:
                    val = clean_text(_safe_row_get(row, col))
                    if val is not None:
                        extra[col] = val
                if extra:
                    record["_extra"] = extra

            rows.append(record)
        except Exception as exc:
            errors.append(f"Row {row_num}: {exc}")

    return rows, errors


# ── S3 upload helper ──────────────────────────────────────────────────────────

def _s3_enabled() -> bool:
    return bool(
        os.environ.get("AWS_ACCESS_KEY_ID")
        and os.environ.get("AWS_SECRET_ACCESS_KEY")
        and os.environ.get("S3_BUCKET_NAME")
    )


async def _try_s3_upload(content: bytes, s3_key: str) -> bool:
    """Upload file bytes to S3.  Returns True on success, False on any error.

    Never raises — caller's flow must not be interrupted by S3 failures.
    """
    if not _s3_enabled():
        return False
    try:
        import boto3
        bucket = os.environ["S3_BUCKET_NAME"]
        region = os.environ.get("AWS_REGION", "eu-west-1")
        s3 = boto3.client(
            "s3",
            region_name=region,
            aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
        )
        s3.put_object(Bucket=bucket, Key=s3_key, Body=content)
        logger.info("S3 upload OK: s3://%s/%s", bucket, s3_key)
        return True
    except Exception as exc:
        logger.warning("S3 upload failed (local file still saved): %s", exc)
        return False


# ── Column profile builder ────────────────────────────────────────────────────

def _build_column_profile(
    df: pd.DataFrame,
    dataset_id: str,
    org_id: str,
    total_rows: int,
    error_rows: int,
) -> DatasetColumnProfile:
    """Build a lightweight statistical profile of the DataFrame columns."""
    stats: List[ColumnStat] = []
    for col in df.columns:
        series = df[col].dropna()
        unique_vals = series.unique()[:5].tolist()  # up to 5 sample values

        # Detect type heuristically
        if col in ("date",) or "date" in col:
            detected_type = "date"
        elif col in ("amount", "price", "total", "value"):
            detected_type = "amount"
        elif series.str.match(r"^-?[\d.,]+$", na=False).mean() > 0.8:
            detected_type = "number"
        else:
            detected_type = "text"

        # Suggest canonical mapping
        suggested = _HARDCODED_ALIASES.get(_normalize_col(col))

        stats.append(
            ColumnStat(
                column_name=col,
                detected_type=detected_type,
                non_null_count=int(series.count()),
                null_count=int(df[col].isna().sum()),
                unique_count=int(df[col].nunique()),
                sample_values=[str(v) for v in unique_vals],
                suggested_mapping=suggested,
            )
        )

    return DatasetColumnProfile(
        organization_id=org_id,
        dataset_id=dataset_id,
        columns=stats,
        total_rows=total_rows,
        error_rows=error_rows,
    )


# ── Row-level duplicate detection ────────────────────────────────────────

# Key fields used to build fingerprints for duplicate row detection.
# Only these fields are compared — extra columns are ignored.
_DUPLICATE_KEY_FIELDS = {
    DatasetType.SALES: ["date", "amount"],
    DatasetType.EXPENSES: ["date", "amount"],
    DatasetType.PURCHASES: ["date", "supplier_name"],
    DatasetType.FIXED_COSTS: ["name", "amount"],
}


async def check_row_duplicates(
    content: bytes,
    filename: str,
    dataset_type: DatasetType,
    org_id: str,
    user_column_mapping: Optional[dict] = None,
    column_map: Optional[dict] = None,
) -> dict:
    """Check for row-level duplicates between a new file and existing data.

    Efficient approach:
      1. Parse file → DataFrame (fast, sub-second for PMI files)
      2. Build column map + apply to standardize column names
      3. Extract key-field fingerprints from new rows (with cleaning)
      4. Query existing records filtered by date range (one MongoDB query)
      5. Build fingerprints from existing records, set-intersect in memory

    Total cost: ~200-500ms for typical PMI datasets (1K-50K rows).
    Non-blocking: any error → returns zero duplicates.

    user_column_mapping: optional {file_column → target_field} dict from
    the interactive mapping dialog (passed from /upload-with-mapping).

    column_map: optional pre-built column map from analyze_columns_for_mapping.
    When provided, skips the DB query to _build_column_map (performance).

    Returns:
        {
            "duplicate_row_count": int,
            "total_new_rows": int,
            "sample_duplicates": [{"date": ..., "amount": ...}, ...],  # up to 5
        }
    """
    empty_result = {"duplicate_row_count": 0, "total_new_rows": 0, "sample_duplicates": []}

    try:
        df = parse_file_to_dataframe(content, filename)
    except Exception:
        return empty_result

    total_rows = len(df)
    key_fields = _DUPLICATE_KEY_FIELDS.get(dataset_type)
    if not key_fields:
        return {**empty_result, "total_new_rows": total_rows}

    # Reuse pre-built column map if available; otherwise build from DB
    if column_map is None:
        column_map = await _build_column_map(org_id, dataset_type)
    else:
        column_map = dict(column_map)  # defensive copy
    # Merge user-supplied column mapping (highest precedence)
    if user_column_mapping:
        for file_col, target_field in user_column_mapping.items():
            norm = _normalize_col(file_col)
            column_map[norm] = target_field
    df.columns = [column_map.get(_normalize_col(c), _normalize_col(c)) for c in df.columns]

    # Verify all key fields are present in the mapped DataFrame
    if not all(k in df.columns for k in key_fields):
        logger.debug(
            "check_row_duplicates: key fields %s not found in columns %s (org=%s, type=%s)",
            key_fields, list(df.columns), org_id, dataset_type.value,
        )
        return {**empty_result, "total_new_rows": total_rows}

    # ── Build fingerprints from NEW rows ────────────────────────────────
    new_fps: dict = {}  # fingerprint_string → sample row dict
    for _, row in df.iterrows():
        fp_parts = []
        sample = {}
        valid = True
        for k in key_fields:
            raw = row.get(k, "")
            if k == "date":
                cleaned = clean_date(raw)
                if not cleaned:
                    valid = False
                    break
                fp_parts.append(cleaned)
                sample[k] = cleaned
            elif k in ("amount", "unit_price", "quantity"):
                cleaned = clean_amount(raw)
                if cleaned is None:
                    valid = False
                    break
                fp_parts.append(f"{cleaned:.2f}")
                sample[k] = cleaned
            else:
                cleaned = clean_text(raw) or ""
                fp_parts.append(cleaned.lower())
                sample[k] = cleaned
        if valid:
            fp = "|".join(fp_parts)
            if fp not in new_fps:
                new_fps[fp] = sample

    if not new_fps:
        return {**empty_result, "total_new_rows": total_rows}

    # ── Query EXISTING records (date-range filtered) ────────────────────
    from database import (
        sales_records_collection,
        expense_records_collection,
        purchase_records_collection,
        fixed_costs_collection,
    )
    coll_map = {
        DatasetType.SALES: sales_records_collection,
        DatasetType.EXPENSES: expense_records_collection,
        DatasetType.PURCHASES: purchase_records_collection,
        DatasetType.FIXED_COSTS: fixed_costs_collection,
    }
    collection = coll_map[dataset_type]

    query: dict = {"organization_id": org_id}
    # Use date range filter for efficient querying
    if "date" in key_fields and "date" in df.columns:
        dates = df["date"].apply(clean_date).dropna()
        if len(dates) > 0:
            query["date"] = {"$gte": str(dates.min()), "$lte": str(dates.max())}

    projection = {"_id": 0}
    for k in key_fields:
        projection[k] = 1

    try:
        existing = await collection.find(query, projection).to_list(100_000)
    except Exception:
        return {**empty_result, "total_new_rows": total_rows}

    # ── Build fingerprints from existing records ────────────────────────
    existing_fps: set = set()
    for rec in existing:
        fp_parts = []
        for k in key_fields:
            val = rec.get(k, "")
            if k in ("amount", "unit_price", "quantity"):
                if isinstance(val, (int, float)):
                    fp_parts.append(f"{val:.2f}")
                else:
                    c = clean_amount(val)
                    fp_parts.append(f"{c:.2f}" if c is not None else str(val))
            elif k == "date":
                fp_parts.append(str(val))
            else:
                fp_parts.append(str(val).lower().strip())
        existing_fps.add("|".join(fp_parts))

    # ── Set intersection → matched fingerprints ─────────────────────────
    matched = set(new_fps.keys()) & existing_fps

    samples = [new_fps[fp] for fp in list(matched)[:5]]

    return {
        "duplicate_row_count": len(matched),
        "total_new_rows": total_rows,
        "sample_duplicates": samples,
    }


async def filter_duplicate_rows(
    rows: list,
    dataset_type: DatasetType,
    org_id: str,
) -> Tuple[list, int]:
    """Remove rows that already exist in the database.

    Called on already-cleaned rows (output of process_dataframe).  Uses the
    same fingerprint logic as check_row_duplicates but operates on dicts
    instead of raw file content.

    Returns:
        (filtered_rows, skipped_count)
    """
    key_fields = _DUPLICATE_KEY_FIELDS.get(dataset_type)
    if not key_fields or not rows:
        return rows, 0

    # ── Build fingerprints from the NEW rows ──────────────────────────
    indexed: list[tuple[str, dict]] = []  # (fingerprint, row)
    for row in rows:
        fp_parts = []
        valid = True
        for k in key_fields:
            val = row.get(k, "")
            if k in ("amount", "unit_price", "quantity"):
                if isinstance(val, (int, float)):
                    fp_parts.append(f"{val:.2f}")
                else:
                    c = clean_amount(val)
                    if c is None:
                        valid = False
                        break
                    fp_parts.append(f"{c:.2f}")
            elif k == "date":
                fp_parts.append(str(val))
            else:
                fp_parts.append(str(val).lower().strip())
        if valid:
            indexed.append(("|".join(fp_parts), row))
        else:
            # Row with un-parseable key → keep it (don't skip)
            indexed.append((None, row))

    if not indexed:
        return rows, 0

    # ── Query existing records (date-range filtered) ──────────────────
    from database import (
        sales_records_collection,
        expense_records_collection,
        purchase_records_collection,
        fixed_costs_collection,
    )
    coll_map = {
        DatasetType.SALES: sales_records_collection,
        DatasetType.EXPENSES: expense_records_collection,
        DatasetType.PURCHASES: purchase_records_collection,
        DatasetType.FIXED_COSTS: fixed_costs_collection,
    }
    collection = coll_map[dataset_type]

    query: dict = {"organization_id": org_id}
    if "date" in key_fields:
        dates = [r.get("date") for _, r in indexed if _ is not None and r.get("date")]
        if dates:
            query["date"] = {"$gte": min(dates), "$lte": max(dates)}

    projection = {"_id": 0}
    for k in key_fields:
        projection[k] = 1

    try:
        existing = await collection.find(query, projection).to_list(100_000)
    except Exception:
        return rows, 0

    # ── Build existing fingerprint set ────────────────────────────────
    existing_fps: set = set()
    for rec in existing:
        fp_parts = []
        for k in key_fields:
            val = rec.get(k, "")
            if k in ("amount", "unit_price", "quantity"):
                if isinstance(val, (int, float)):
                    fp_parts.append(f"{val:.2f}")
                else:
                    c = clean_amount(val)
                    fp_parts.append(f"{c:.2f}" if c is not None else str(val))
            elif k == "date":
                fp_parts.append(str(val))
            else:
                fp_parts.append(str(val).lower().strip())
        existing_fps.add("|".join(fp_parts))

    if not existing_fps:
        return rows, 0

    # ── Filter out matching rows ──────────────────────────────────────
    filtered = []
    skipped = 0
    for fp, row in indexed:
        if fp is not None and fp in existing_fps:
            skipped += 1
        else:
            filtered.append(row)

    logger.info(
        "filter_duplicate_rows: kept %d rows, skipped %d duplicates (org=%s, type=%s)",
        len(filtered), skipped, org_id, dataset_type.value,
    )
    return filtered, skipped


# ── Target field definitions per dataset type ────────────────────────────

_TARGET_FIELDS = {
    DatasetType.SALES: {
        "date": {"label": "Data", "required": True},
        "amount": {"label": "Importo", "required": True},
        "category": {"label": "Categoria", "required": False},
        "description": {"label": "Descrizione", "required": False},
        "channel": {"label": "Canale", "required": False},
        "due_date": {"label": "Data Scadenza", "required": False, "help": "Data di scadenza del pagamento"},
        "payment_status": {"label": "Stato Pagamento", "required": False, "help": "pending, paid, overdue"},
    },
    DatasetType.EXPENSES: {
        "date": {"label": "Data", "required": True},
        "amount": {"label": "Importo", "required": True},
        "category": {"label": "Categoria", "required": False},
        "description": {"label": "Descrizione", "required": False},
        "supplier": {"label": "Fornitore", "required": False},
        "due_date": {"label": "Data Scadenza", "required": False, "help": "Data di scadenza del pagamento"},
        "payment_status": {"label": "Stato Pagamento", "required": False, "help": "pending, paid, overdue"},
        "is_paid": {"label": "Pagato", "required": False, "help": "true/false — se il pagamento è stato effettuato"},
    },
    DatasetType.PURCHASES: {
        "date": {"label": "Data", "required": True, "help": "Data dell'acquisto (obbligatorio)"},
        "supplier_name": {"label": "Nome Fornitore", "required": True, "help": "Nome del fornitore (obbligatorio)"},
        "total_price": {"label": "Totale", "required": False, "help": "Importo netto dell'acquisto. Se presente, ha priorità su Quantità × Prezzo."},
        "quantity": {"label": "Quantità", "required": False, "help": "Quantità acquistata. Necessaria con Prezzo Unitario se manca il Totale."},
        "unit_price": {"label": "Prezzo Unitario", "required": False, "help": "Prezzo per unità. Necessario con Quantità se manca il Totale."},
        "unit": {"label": "Unità di Misura", "required": False, "help": "es. kg, pezzi, litri"},
        "iva": {"label": "IVA %", "required": False, "help": "Aliquota IVA in percentuale (es. 22, 10, 4). NON importi monetari."},
        "total_with_iva": {"label": "Totale con IVA", "required": False, "help": "Importo lordo finale (IVA inclusa). Se presente, ha priorità sul calcolo."},
        "category": {"label": "Prodotto", "required": False, "help": "Prodotto specifico (es. mele, pomodori)"},
        "category_macro": {"label": "Categoria", "required": False, "help": "Raggruppamento prodotti (es. frutta, verdura)"},
        "description": {"label": "Descrizione", "required": False},
        "invoice_number": {"label": "Numero Fattura", "required": False, "help": "Riferimento fattura fornitore"},
        "due_date": {"label": "Data Scadenza", "required": False, "help": "Data di scadenza del pagamento"},
        "payment_status": {"label": "Stato Pagamento", "required": False, "help": "pending, paid, overdue, cancelled"},
    },
    DatasetType.FIXED_COSTS: {
        "name": {"label": "Nome Costo", "required": True},
        "amount": {"label": "Importo", "required": True},
        "frequency": {"label": "Frequenza", "required": True},
        "start_date": {"label": "Data Inizio", "required": True},
        "end_date": {"label": "Data Fine", "required": False},
        "category": {"label": "Categoria", "required": False},
        "description": {"label": "Descrizione", "required": False},
    },
}


async def analyze_columns_for_mapping(
    content: bytes,
    filename: str,
    dataset_type: DatasetType,
    org_id: str,
) -> dict:
    """Analyze a file's columns and determine if interactive mapping is needed.

    Returns a dict with:
      - status: "auto_mapped" | "needs_column_mapping"
      - recognized_columns: {file_col: target_field} for auto-mapped columns
      - unmapped_columns: [file_col, ...] columns that couldn't be mapped
      - missing_required: [target_field, ...] required fields not yet covered
      - target_fields: {field: {label, required}} for the dataset type
      - preview_rows: first 3 rows of data for display in the mapping dialog
    """
    file_ext = Path(filename).suffix.lower()
    if file_ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Formato file non supportato. Formati accettati: {', '.join(SUPPORTED_EXTENSIONS)}")

    df = parse_file_to_dataframe(content, filename)

    # Build the column map (org DB mappings + hardcoded aliases)
    column_map = await _build_column_map(org_id, dataset_type)

    # Map each file column to its target
    recognized = {}   # {original_col_name: target_field}
    unmapped = []     # [original_col_name, ...]
    mapped_targets = set()

    for col in df.columns:
        norm = _normalize_col(col)
        target = column_map.get(norm, norm)
        target_fields = _TARGET_FIELDS.get(dataset_type, {})

        if target in target_fields:
            recognized[str(col)] = target
            mapped_targets.add(target)
        elif norm in target_fields:
            recognized[str(col)] = norm
            mapped_targets.add(norm)
        else:
            unmapped.append(str(col))

    # Check which required fields are missing
    target_fields_def = _TARGET_FIELDS.get(dataset_type, {})
    missing_required = [
        field for field, meta in target_fields_def.items()
        if meta["required"] and field not in mapped_targets
    ]

    # Purchase-specific conditional requirement:
    # At least one amount source must be mapped: total_price OR (quantity + unit_price)
    if dataset_type == DatasetType.PURCHASES:
        has_total = "total_price" in mapped_targets
        has_qty_price = "quantity" in mapped_targets and "unit_price" in mapped_targets
        if not has_total and not has_qty_price:
            # Add a synthetic missing_required entry to block the confirm button
            if "total_price" not in missing_required:
                missing_required.append("total_price")

    # Preview rows (first 3)
    preview_df = df.head(3).fillna("")
    preview_rows = []
    for _, row in preview_df.iterrows():
        preview_rows.append({str(col): str(row[col]) for col in df.columns})

    # Show mapping dialog if:
    # 1. Required fields are missing, OR
    # 2. There are unmapped columns (user should verify the mapping)
    # This ensures the popup acts as a double-check for the user.
    status = "auto_mapped" if (not missing_required and not unmapped) else "needs_column_mapping"

    return {
        "status": status,
        "recognized_columns": recognized,
        "unmapped_columns": unmapped,
        "missing_required": missing_required,
        "target_fields": {
            k: v for k, v in target_fields_def.items()
        },
        "preview_rows": preview_rows,
        "all_file_columns": [str(c) for c in df.columns],
        # Internal: pre-built column map for reuse downstream (avoids re-query).
        # Not serialized to the frontend (router picks it up before raising 422).
        "_column_map": column_map,
    }


# ── Main entry point ──────────────────────────────────────────────────────────

async def parse_and_save_dataset(
    content: bytes,
    filename: str,
    name: str,
    dataset_type: DatasetType,
    org_id: str,
    user_id: str,
    user_column_mapping: Optional[dict] = None,
    skip_duplicate_rows: bool = False,
    column_map: Optional[dict] = None,
) -> dict:
    """Parse uploaded file and save dataset with records.

    user_column_mapping: optional {file_column → target_field} dict from
    the interactive mapping dialog.  When present, these mappings take
    precedence over DB and hardcoded aliases.

    skip_duplicate_rows: when True, rows that already exist in the DB
    (based on key-field fingerprints) are silently removed before insert.

    column_map: optional pre-built column map from analyze_columns_for_mapping.
    When provided, skips the DB query to _build_column_map (performance).
    """
    file_ext = Path(filename).suffix.lower()
    if file_ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Formato file non supportato. Formati accettati: {', '.join(SUPPORTED_EXTENSIONS)}")

    # 1. Parse raw file
    df = parse_file_to_dataframe(content, filename)

    # 2. Load org-specific column mappings — reuse if already built upstream
    if column_map is None:
        column_map = await _build_column_map(org_id, dataset_type)
    else:
        column_map = dict(column_map)  # defensive copy

    # 2.5. Merge user-supplied column mapping (from interactive dialog)
    #      User mappings take highest precedence over DB and hardcoded aliases.
    if user_column_mapping:
        for file_col, target_field in user_column_mapping.items():
            norm = _normalize_col(file_col)
            column_map[norm] = target_field

    # 3. Process rows using merged column map
    rows, errors = process_dataframe(df, dataset_type, column_map=column_map)

    if errors and not rows:
        raise ValueError(f"Errore nel parsing del file: {'; '.join(errors[:5])}")

    # 3.5. Load org-specific validation rules (non-blocking, returns [] on any failure).
    validation_rules = await _load_validation_rules(org_id, dataset_type.value)

    # 3.6. Apply validation rules to each already-cleaned row.
    #      Invalid rows are skipped and their violations appended to `errors`.
    #      The entire block is guarded by a broad try/except: if the engine
    #      itself has a bug, all rows pass and the upload continues normally.
    validation_rows_skipped = 0
    if validation_rules:
        try:
            from services.validation_engine import apply_validation_rules
            valid_rows: list = []
            for row in rows:
                violations = apply_validation_rules(row, validation_rules)
                if violations:
                    row_num = int(row.get("source_record_id", 0)) + 2
                    for v in violations:
                        errors.append(f"Row {row_num} [validation]: {v}")
                    validation_rows_skipped += 1
                else:
                    valid_rows.append(row)
            rows = valid_rows
            if validation_rows_skipped:
                logger.info(
                    "dataset_service: validation filtered %d row(s) for org=%s "
                    "type=%s (%d rule(s) active)",
                    validation_rows_skipped, org_id, dataset_type.value, len(validation_rules),
                )
        except Exception as exc:
            # Engine failure is non-fatal: all rows pass unchanged.
            logger.warning("dataset_service: validation engine error (skipping): %s", exc)
            validation_rows_skipped = 0

    # 3.7. Optionally filter out rows that already exist in the database.
    #      This runs AFTER validation so that only valid rows are fingerprinted.
    duplicate_rows_skipped = 0
    if skip_duplicate_rows and rows:
        try:
            rows, duplicate_rows_skipped = await filter_duplicate_rows(
                rows, dataset_type, org_id,
            )
        except Exception as exc:
            logger.warning("dataset_service: filter_duplicate_rows error (skipping): %s", exc)
            duplicate_rows_skipped = 0

    # 4. Save to local disk (always)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    saved_ext = file_ext if file_ext in [".xlsx", ".xls"] else ".csv"
    file_name = f"{org_id}_{dataset_type.value}_{timestamp}{saved_ext}"
    file_path = UPLOAD_DIR / file_name
    with open(file_path, "wb") as f:
        f.write(content)

    # 5. Try S3 upload (Phase 2 dual-write; non-fatal on failure)
    s3_key = f"uploads/{org_id}/{file_name}"
    s3_ok = await _try_s3_upload(content, s3_key)

    # 6. Create dataset record with Phase-2 fields
    dataset = Dataset(
        name=name,
        dataset_type=dataset_type,
        row_count=len(rows),
        organization_id=org_id,
        file_path=str(file_path),
        uploaded_by=user_id,
        # Phase-2 additions
        schema_version=_SCHEMA_VERSION,
        source_type="file_upload",
        original_filename=filename,
        s3_key=s3_key if s3_ok else None,
    )

    dataset_doc = dataset.model_dump()
    dataset_doc["created_at"] = dataset_doc["created_at"].isoformat()

    from database import datasets_collection
    await datasets_collection.insert_one(dataset_doc)

    # 7. ACCUMULATIVE MODE (v3.0): no replacement.
    #
    # Old datasets remain active. Their records are NOT deleted.
    # Users manage datasets individually via DatasetsPage (delete cascades records).
    # The deactivate_by_type() call is removed intentionally.
    #
    # Duplicate detection (advisory, non-blocking):
    duplicate_warning = None
    try:
        existing_same_file = await datasets_collection.find_one({
            "organization_id": org_id,
            "dataset_type": dataset_type.value,
            "original_filename": filename,
            "row_count": len(rows),
            "id": {"$ne": dataset.id},
        })
        if existing_same_file:
            created = existing_same_file.get("created_at", "data sconosciuta")
            duplicate_warning = (
                f"Un file con lo stesso nome ({filename}) e lo stesso numero "
                f"di righe ({len(rows)}) è già stato caricato il {created}. "
                f"I dati sono stati comunque aggiunti."
            )
    except Exception:
        pass  # non-blocking

    # 7.5. Entity linking maps — build once per upload, reuse per row (v7.0)
    # Generalises the v2.1 supplier auto-match to all entity types.
    from services.entity_resolver import (
        build_customer_name_map, build_customer_external_id_map,
        build_supplier_name_map as _resolver_build_supplier_name_map,
        build_product_name_map, build_product_sku_map,
        resolve_by_name, resolve_by_external_id, resolve_by_sku,
    )

    _el_maps: dict = {}  # keyed by map type for this upload
    _el_stats = {
        "customers_linked": 0, "customers_unresolved": 0,
        "suppliers_linked": 0, "suppliers_unresolved": 0,
        "products_linked": 0, "products_unresolved": 0,
    }

    if dataset_type == DatasetType.SALES:
        _el_maps["customer_name"] = await build_customer_name_map(org_id)
        _el_maps["customer_extid"] = await build_customer_external_id_map(org_id)
        _el_maps["product_sku"] = await build_product_sku_map(org_id)
    elif dataset_type == DatasetType.EXPENSES:
        _el_maps["supplier_name"] = await _resolver_build_supplier_name_map(org_id)
    elif dataset_type == DatasetType.PURCHASES:
        _el_maps["supplier_name"] = await _resolver_build_supplier_name_map(org_id)
        _el_maps["product_sku"] = await build_product_sku_map(org_id)

    _any_maps = any(_el_maps.values())
    if _any_maps:
        logger.debug(
            "dataset_service: entity linking maps loaded for org=%s: %s",
            org_id, {k: len(v) for k, v in _el_maps.items() if v},
        )

    # Backward compat: supplier_name_map used by the existing expenses inline code path
    supplier_name_map = _el_maps.get("supplier_name", {})

    # 7.5.1. Batch pre-create unresolved suppliers (avoids N+1 per-row upserts).
    #   Collect all unique supplier names from rows that don't match the name map,
    #   create them in one pass, and update supplier_name_map before the row loop.
    if rows and dataset_type in (DatasetType.PURCHASES, DatasetType.EXPENSES):
        _supplier_field = "supplier_name" if dataset_type == DatasetType.PURCHASES else "supplier"
        _unresolved_names = set()
        for row in rows:
            _sn = row.get(_supplier_field)
            if _sn and not resolve_by_name(supplier_name_map, _sn):
                _unresolved_names.add(_sn.strip())
        if _unresolved_names:
            from repositories import supplier_repository
            for _name in _unresolved_names:
                try:
                    _new = await supplier_repository.get_or_create_by_name(org_id, _name)
                    supplier_name_map[_name.lower().strip()] = _new.id
                    _el_stats["suppliers_auto_created"] = _el_stats.get("suppliers_auto_created", 0) + 1
                except Exception:
                    pass  # will be counted as unresolved in the row loop
            logger.info(
                "dataset_service: pre-created %d/%d unresolved suppliers for org=%s",
                _el_stats.get("suppliers_auto_created", 0), len(_unresolved_names), org_id,
            )

    # 7.6. Pre-check data_rows quota before inserting
    if rows:
        from services.module_access import check_module_access
        await check_module_access(org_id, "cashflow_monitor", "data_rows", pending_quantity=len(rows))

    # 8. Insert new records (schema_version + metadata + resolved FKs)
    matched_suppliers = 0
    rows_with_extra = 0
    if rows:
        records = []

        if dataset_type in (DatasetType.PURCHASES, DatasetType.FIXED_COSTS):
            # Specialized types: build docs directly without the _extra/schema_version wrapping
            for row in rows:
                extra_data = row.pop("_extra", None) or {}

                if dataset_type == DatasetType.PURCHASES:
                    # v7.0: entity linking for purchases
                    _unresolved = {}

                    # Supplier: resolve by name, auto-create if not found
                    _supp_name = row.get("supplier_name")
                    if _supp_name:
                        _supp_id = resolve_by_name(supplier_name_map, _supp_name) if supplier_name_map else None
                        if _supp_id:
                            row["supplier_id"] = _supp_id
                            _el_stats["suppliers_linked"] += 1
                        else:
                            try:
                                from repositories import supplier_repository
                                _new_supp = await supplier_repository.get_or_create_by_name(org_id, _supp_name)
                                row["supplier_id"] = _new_supp.id
                                supplier_name_map[_supp_name.lower().strip()] = _new_supp.id
                                _el_stats["suppliers_linked"] += 1
                                _el_stats["suppliers_auto_created"] = _el_stats.get("suppliers_auto_created", 0) + 1
                            except Exception:
                                _el_stats["suppliers_unresolved"] += 1

                    # Product: resolve by SKU from lookup column
                    _prod_sku_raw = extra_data.pop("product_sku_lookup", None)
                    if _prod_sku_raw:
                        _prod_id = resolve_by_sku(_el_maps.get("product_sku", {}), _prod_sku_raw)
                        if _prod_id:
                            row["product_id"] = _prod_id
                            _el_stats["products_linked"] += 1
                        else:
                            _unresolved["product_sku"] = _prod_sku_raw
                            _el_stats["products_unresolved"] += 1

                    # Build metadata with unresolved if any
                    _meta = {}
                    if _unresolved:
                        _meta["entity_linking"] = {"unresolved": _unresolved}

                    rec = PurchaseRecord(
                        organization_id=org_id,
                        dataset_id=dataset.id,
                        source_label=name,
                        **row,
                    ).model_dump()
                    if _meta:
                        rec["metadata"] = _meta
                    records.append(rec)
                else:
                    records.append(
                        FixedCost(
                            organization_id=org_id,
                            dataset_id=dataset.id,
                            source_label=name,
                            **row,
                        ).model_dump()
                    )

            if dataset_type == DatasetType.PURCHASES:
                await dataset_repository.insert_purchase_records(records)
            else:
                await dataset_repository.insert_fixed_cost_records(records)

        else:
            # SALES / EXPENSES path (original v2.1 logic with schema_version + metadata)
            for row in rows:
                # Pop internal _extra key before passing to Pydantic (extra="ignore" would
                # also silently drop it, but explicit pop is cleaner and avoids any edge cases).
                extra_metadata: dict = row.pop("_extra", None) or {}
                if extra_metadata:
                    rows_with_extra += 1

                if dataset_type == DatasetType.SALES:
                    # v7.0: entity linking — resolve customer and product FKs
                    _unresolved = {}

                    # Customer: external_id takes priority over name
                    _cust_extid_raw = extra_metadata.pop("customer_extid_lookup", None)
                    _cust_name_raw = extra_metadata.pop("customer_name_lookup", None)
                    _cust_id = None
                    if _cust_extid_raw:
                        _cust_id = resolve_by_external_id(_el_maps.get("customer_extid", {}), _cust_extid_raw)
                    if not _cust_id and _cust_name_raw:
                        _cust_id = resolve_by_name(_el_maps.get("customer_name", {}), _cust_name_raw)
                    if _cust_id:
                        row["customer_id"] = _cust_id
                        _el_stats["customers_linked"] += 1
                    elif _cust_name_raw or _cust_extid_raw:
                        if _cust_name_raw:
                            _unresolved["customer_name"] = _cust_name_raw
                        if _cust_extid_raw:
                            _unresolved["customer_extid"] = _cust_extid_raw
                        _el_stats["customers_unresolved"] += 1

                    # Product: SKU only (no category fallback)
                    _prod_sku_raw = extra_metadata.pop("product_sku_lookup", None)
                    if _prod_sku_raw:
                        _prod_id = resolve_by_sku(_el_maps.get("product_sku", {}), _prod_sku_raw)
                        if _prod_id:
                            row["product_id"] = _prod_id
                            _el_stats["products_linked"] += 1
                        else:
                            _unresolved["product_sku"] = _prod_sku_raw
                            _el_stats["products_unresolved"] += 1

                    if _unresolved:
                        extra_metadata.setdefault("entity_linking", {})["unresolved"] = _unresolved

                    rec_doc = {
                        **SalesRecord(organization_id=org_id, dataset_id=dataset.id, source_label=name, **row).model_dump(),
                        "schema_version": _SCHEMA_VERSION,
                        "metadata": extra_metadata,
                    }
                else:
                    # EXPENSES: resolve supplier FK via name, auto-create if not found
                    supplier_text = row.get("supplier")
                    if supplier_text:
                        matched_id = resolve_by_name(supplier_name_map, supplier_text) if supplier_name_map else None
                        if matched_id:
                            row["supplier_id"] = matched_id
                            matched_suppliers += 1
                            _el_stats["suppliers_linked"] += 1
                        else:
                            try:
                                from repositories import supplier_repository
                                _new_supp = await supplier_repository.get_or_create_by_name(org_id, supplier_text)
                                row["supplier_id"] = _new_supp.id
                                supplier_name_map[supplier_text.lower().strip()] = _new_supp.id
                                matched_suppliers += 1
                                _el_stats["suppliers_linked"] += 1
                                _el_stats["suppliers_auto_created"] = _el_stats.get("suppliers_auto_created", 0) + 1
                            except Exception:
                                _el_stats["suppliers_unresolved"] += 1

                    rec_doc = {
                        **ExpenseRecord(organization_id=org_id, dataset_id=dataset.id, source_label=name, **row).model_dump(),
                        "schema_version": _SCHEMA_VERSION,
                        "metadata": extra_metadata,
                    }

                records.append(rec_doc)

            if dataset_type == DatasetType.SALES:
                await dataset_repository.insert_sales_records(records)
            elif dataset_type == DatasetType.EXPENSES:
                await dataset_repository.insert_expense_records(records)

        logger.info(
            "dataset_service: inserted %d records for dataset %s "
            "(rows_with_extra_cols=%d, supplier_ids_matched=%d)",
            len(records), dataset.id, rows_with_extra, matched_suppliers,
        )

        # Record data_rows usage after successful insert
        from services.module_access import record_module_usage
        await record_module_usage(org_id, "cashflow_monitor", "data_rows", quantity=len(records))

    # 9. Save column profile (fire-and-forget)
    try:
        profile = _build_column_profile(df, dataset.id, org_id, len(rows), len(errors))
        await upsert_profile(profile)
    except Exception as exc:
        logger.warning("Could not save column profile for dataset %s: %s", dataset.id, exc)

    # 10. Trigger post-upload hooks for all registered modules (fire-and-forget)
    await _run_post_upload_hooks(org_id)

    # 11. Audit log
    audit = AuditLog(
        organization_id=org_id,
        user_id=user_id,
        action="upload_dataset",
        resource_type="dataset",
        resource_id=dataset.id,
        details={
            "name": name,
            "type": dataset_type.value,
            "rows": len(rows),
            "errors": len(errors),
            "s3_stored": s3_ok,
            "schema_version": _SCHEMA_VERSION,
            # v2.1 additions
            "rows_with_extra_cols": rows_with_extra,
            "supplier_ids_matched": matched_suppliers,
            # v2.2 additions
            "validation_rules_active": len(validation_rules),
            "validation_rows_skipped": validation_rows_skipped,
            # v3.1 additions
            "duplicate_rows_skipped": duplicate_rows_skipped,
        },
    )
    await audit_repository.create(audit)

    return {
        "id": dataset.id,
        "name": dataset.name,
        "dataset_type": dataset.dataset_type,
        "row_count": dataset.row_count,
        "organization_id": dataset.organization_id,
        "uploaded_by": dataset.uploaded_by,
        "created_at": dataset.created_at,
        "is_active": dataset.is_active,
        # ── v2.2 reporting fields ─────────────────────────────────────────────
        "errors": errors[:10] if errors else [],
        "validation_rows_skipped": validation_rows_skipped,
        "validation_rules_active": len(validation_rules),
        # ── v3.0 accumulative mode ────────────────────────────────────────────
        "duplicate_warning": duplicate_warning,
        # ── v3.1 skip duplicate rows ─────────────────────────────────────────
        "duplicate_rows_skipped": duplicate_rows_skipped,
        # total rows attempted = valid (saved) + skipped by validation + skipped duplicates
        "total_rows_attempted": dataset.row_count + validation_rows_skipped + duplicate_rows_skipped,
        # ── v7.0 entity linking stats ────────────────────────────────────────
        "entity_linking_stats": {k: v for k, v in _el_stats.items() if v > 0} or None,
    }
