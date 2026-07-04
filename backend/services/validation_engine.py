"""
Validation Engine — v2.2.

Applies org-defined DataValidationRule objects to a single cleaned row dict.
Pure functions — no I/O, no async.  Designed to be called inside the
dataset_service upload pipeline after process_dataframe() has already
normalised dates, amounts, and text.

Public interface:
    apply_validation_rules(row, rules) -> list[str]
        Returns a list of violation messages (empty list = row passes all rules).
        Any rule that raises an exception is silently skipped so that a
        malformed rule never blocks a legitimate row.

Supported rule types:
    REQUIRED            field must be non-null / non-empty string
    MIN_VALUE           numeric field >= rule_value
    MAX_VALUE           numeric field <= rule_value
    DATE_RANGE          date field within {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}
    CATEGORY_WHITELIST  category field must be in the supplied list (case-insensitive)
    REGEX               not yet implemented — silently skipped (returns None)

Future-readiness:
    The function signature and violation list format are designed so that a
    future endpoint can call apply_validation_rules() on preview rows and
    return structured warnings to the frontend without changing this file.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional

from models.data_validation_rule import ValidationRuleType


# ── Public entry point ────────────────────────────────────────────────────────

def apply_validation_rules(row: dict, rules: list) -> List[str]:
    """Check all active rules against a single cleaned row dict.

    Args:
        row:   Cleaned record dict from process_dataframe() — fields include
               ``date`` (str "YYYY-MM-DD"), ``amount`` (float), ``category``
               (str | None), ``description`` (str | None), etc.
        rules: List of DataValidationRule objects loaded from the database.

    Returns:
        A (possibly empty) list of human-readable Italian violation messages.
        Empty list means the row passed all rules and should be inserted.
    """
    violations: List[str] = []
    for rule in rules:
        try:
            msg = _check_single_rule(row, rule)
            if msg:
                violations.append(msg)
        except Exception:
            # Malformed or unexpected rule — skip silently, never crash.
            pass
    return violations


# ── Rule checker ─────────────────────────────────────────────────────────────

def _check_single_rule(row: dict, rule) -> Optional[str]:
    """Return a violation message if the row violates the rule, else None.

    Each rule type is handled in an isolated branch.  Type-conversion errors
    (e.g. rule_value is None when MIN_VALUE expects a number) are caught at the
    caller level (apply_validation_rules), so this function may raise freely.
    """
    field: str = rule.field_name
    rtype: ValidationRuleType = rule.rule_type
    rvalue: Any = rule.rule_value
    custom_msg: Optional[str] = rule.error_message

    value = row.get(field)

    # ── REQUIRED ─────────────────────────────────────────────────────────────
    if rtype == ValidationRuleType.REQUIRED:
        if value is None or (isinstance(value, str) and not value.strip()):
            return custom_msg or f"Il campo '{field}' è obbligatorio"
        return None

    # ── MIN_VALUE ─────────────────────────────────────────────────────────────
    if rtype == ValidationRuleType.MIN_VALUE:
        if value is None:
            return None  # REQUIRED handles missing values; MIN_VALUE does not
        try:
            if float(value) < float(rvalue):
                return custom_msg or (
                    f"'{field}' ({value}) è inferiore al minimo consentito ({rvalue})"
                )
        except (TypeError, ValueError):
            pass  # non-numeric field or rule_value — skip rule
        return None

    # ── MAX_VALUE ─────────────────────────────────────────────────────────────
    if rtype == ValidationRuleType.MAX_VALUE:
        if value is None:
            return None
        try:
            if float(value) > float(rvalue):
                return custom_msg or (
                    f"'{field}' ({value}) supera il massimo consentito ({rvalue})"
                )
        except (TypeError, ValueError):
            pass
        return None

    # ── DATE_RANGE ────────────────────────────────────────────────────────────
    if rtype == ValidationRuleType.DATE_RANGE:
        if value is None:
            return None
        try:
            date_val = (
                datetime.strptime(str(value), "%Y-%m-%d").date()
                if isinstance(value, str)
                else value
            )
            bounds = rvalue or {}
            start_str = bounds.get("start")
            end_str = bounds.get("end")
            if start_str:
                start = datetime.strptime(str(start_str), "%Y-%m-%d").date()
                if date_val < start:
                    return custom_msg or (
                        f"Data {value} è precedente alla data minima consentita ({start_str})"
                    )
            if end_str:
                end = datetime.strptime(str(end_str), "%Y-%m-%d").date()
                if date_val > end:
                    return custom_msg or (
                        f"Data {value} è successiva alla data massima consentita ({end_str})"
                    )
        except (TypeError, ValueError, AttributeError):
            pass
        return None

    # ── CATEGORY_WHITELIST ────────────────────────────────────────────────────
    if rtype == ValidationRuleType.CATEGORY_WHITELIST:
        if value is None:
            return None  # missing category is not a whitelist violation
        try:
            whitelist = [str(v).lower().strip() for v in (rvalue or []) if v is not None]
            if whitelist and str(value).lower().strip() not in whitelist:
                return custom_msg or f"Categoria '{value}' non è nella lista consentita"
        except (TypeError, ValueError):
            pass
        return None

    # ── REGEX and future types ────────────────────────────────────────────────
    # Not yet implemented.  Return None so unrecognised rule types never block rows.
    return None
