"""
Canonical locale-tolerant numeric parser.

Handles European (1.234,56), US (1,234.56), Swiss (1'234.56), French
space-separated (1 234,56), and bare (1234.56 / 1234,56) formats.

Extracted from dataset_service.clean_amount() to serve as the single
source of truth for numeric coercion across:
  - CSV/XLSX import pipeline  (dataset_service.py → clean_amount)
  - Pydantic BeforeValidators (manual-entry models)
  - Any future API clients sending locale-formatted strings

Public API:
    parse_locale_number(value) → Optional[float]   # None on failure
    coerce_locale_number(value) → Optional[float]   # raises ValueError on failure
"""

import re
from typing import Optional, Union


def parse_locale_number(value: Union[str, int, float, None]) -> Optional[float]:
    """Parse a locale-formatted numeric string into a Python float.

    Rules:
      1. None / empty → None
      2. int / float  → passthrough as float
      3. Strip currency symbols ($€£¥₹) and whitespace
      4. If both , and . present:
         - rightmost separator is the decimal separator
         - "1.234,56" → 1234.56   "1,234.56" → 1234.56
      5. If only comma present:
         - ≤ 2 digits after comma → decimal  ("12,5" → 12.5)
         - 3+ digits after comma  → thousands ("1,000" → 1000)
      6. Strip any remaining non-numeric chars (except dot and minus)
      7. Convert to float; return None on failure
    """
    if value is None:
        return None

    # Passthrough for already-numeric types
    if isinstance(value, (int, float)):
        return float(value)

    val_str = str(value).strip()
    if not val_str:
        return None

    # Strip currency symbols and all whitespace (incl. non-breaking space)
    val_str = re.sub(r"[$€£¥₹\s\u00a0]", "", val_str)

    # ── Both comma and dot present → rightmost is decimal separator ──
    if "," in val_str and "." in val_str:
        if val_str.rfind(",") > val_str.rfind("."):
            # European: "1.234,56" → comma is decimal
            val_str = val_str.replace(".", "").replace(",", ".")
        else:
            # US: "1,234.56" → dot is decimal
            val_str = val_str.replace(",", "")

    elif "," in val_str:
        # ── Only comma present → heuristic ───────────────────────────
        parts = val_str.split(",")
        if len(parts) == 2 and len(parts[1]) <= 2:
            # Single comma with ≤2 decimal digits → decimal separator
            val_str = val_str.replace(",", ".")
        else:
            # Thousands separator ("1,000" or "1,000,000")
            val_str = val_str.replace(",", "")

    # Strip Swiss apostrophe thousands separator and any other junk
    val_str = re.sub(r"[^\d.\-]", "", val_str)

    try:
        return float(val_str)
    except ValueError:
        return None


def coerce_locale_number(value: Union[str, int, float, None]) -> Optional[float]:
    """Pydantic BeforeValidator wrapper.

    Same as parse_locale_number but raises ValueError (instead of returning
    None) when the input is a non-empty string that cannot be parsed.
    This gives Pydantic proper validation error messages.
    """
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    result = parse_locale_number(value)
    if result is None and str(value).strip():
        raise ValueError(
            f"Valore numerico non valido: '{value}'. "
            "Formati accettati: 1234.56, 1234,56, 1.234,56, 1,234.56"
        )
    return result
