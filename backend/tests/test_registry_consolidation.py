"""Tests for the module-registry consolidation (legacy → modern).

These tests guarantee that ``core.module_registry.get_all_for_ui()`` and
``get_all()`` produce the dataset that drives ``GET /api/modules/available``
and ``GET /api/modules/active``.

The historical equivalence test against the legacy filesystem-scanning
registry has been removed together with the legacy registry itself.
The structural invariants (``test_metadata_no_defaults``,
``test_unique_module_keys``, ``test_ui_shape_keys``) remain as
guardrails; the no-resurrection guardrails live in
``tests/test_module_registry_invariants.py``.
"""
from __future__ import annotations


def test_metadata_no_defaults():
    """Every registered module must declare description/category/icon explicitly.

    Defaults (``""``, ``"other"``, ``"activity"``) are placeholders for
    backward-compat during the migration; a real module without metadata
    would look broken in the merchant /modules page.
    """
    import modules.cashflow_monitor  # noqa: F401
    import modules.commerce  # noqa: F401
    import modules.customer_insights  # noqa: F401
    import modules.product_catalog  # noqa: F401

    from core.module_registry import get_all

    for m in get_all():
        assert m.description, f"{m.module_key} missing description"
        assert m.category and m.category != "other", (
            f"{m.module_key} has default/empty category"
        )
        assert m.icon and m.icon != "activity", (
            f"{m.module_key} has default/empty icon"
        )


def test_unique_module_keys():
    """No two modules may share a module_key."""
    import modules.cashflow_monitor  # noqa: F401
    import modules.commerce  # noqa: F401
    import modules.customer_insights  # noqa: F401
    import modules.product_catalog  # noqa: F401

    from core.module_registry import get_all

    keys = [m.module_key for m in get_all()]
    assert len(keys) == len(set(keys)), f"Duplicate module_keys: {keys}"


def test_ui_shape_keys():
    """get_all_for_ui() must produce exactly the 6 expected dict keys."""
    import modules.cashflow_monitor  # noqa: F401
    from core.module_registry import get_all_for_ui

    EXPECTED = {"key", "name", "description", "category", "icon", "is_available"}
    for d in get_all_for_ui():
        assert set(d.keys()) == EXPECTED, (
            f"Unexpected shape for {d.get('key')!r}: got keys={set(d.keys())}"
        )
