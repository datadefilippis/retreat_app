"""Helper di parsing file (R4, estratti da dataset_service prima della potatura).

Il vecchio dataset_service (upload BI: vendite/spese/acquisti) e' stato
rimosso col modulo cashflow; questi helper PURI restano perche' li usa
l'import ordini da CSV/Excel (services/order_import_service.py), una
feature commerce viva. Nessuna dipendenza da DB o modelli.
"""

import io
import logging
import re
import unicodedata
from datetime import datetime, date
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = [".csv", ".xlsx", ".xls"]


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
