"""Permanent guardrails against re-introducing the legacy module registry.

These tests are *failsafes*: they exist to ensure the consolidation
documented in ``docs/PRODUCTS_ARCHITECTURE.md`` (single source of truth
for module metadata in ``core.module_registry``) cannot silently
regress.  Each test corresponds to a class of bug that used to be
possible with the old dual-registry setup:

  - ``test_no_legacy_config_py_files``: prevents anyone from
    re-creating ``modules/<x>/config.py`` files.  The legacy registry
    used to discover modules by filesystem scan; a stale ``config.py``
    in a renamed folder caused customers_light to vanish from the
    merchant /modules page (the original incident).

  - ``test_no_legacy_get_registered_modules_imports``: prevents anyone
    from re-introducing ``from modules import get_registered_modules``.
    The function no longer exists; this test catches the import in CI
    before it reaches runtime.

  - ``test_modules_package_init_is_marker_only``: prevents the legacy
    ``ModuleRegistry`` class from re-appearing in ``modules/__init__.py``.

  - ``test_registered_keys_form_superset_of_co_activation_rules``:
    ensures the CO_ACTIVATE / CO_DEACTIVATE rules in ``routers/modules.py``
    only reference module keys that actually exist in the registry —
    otherwise activating a module would silently fail to cascade.
"""
from __future__ import annotations

import glob
import os
import re
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parent.parent
MODULES_DIR = BACKEND_ROOT / "modules"


def test_no_legacy_config_py_files():
    """No ``modules/<module>/config.py`` may exist.

    The legacy filesystem-scanning registry used these files; bringing
    one back would silently re-introduce the dual-source-of-truth bug.
    Module metadata now lives in the ``register(ModuleDefinition(...))``
    call inside each module's ``__init__.py``.
    """
    pattern = str(MODULES_DIR / "*" / "config.py")
    found = glob.glob(pattern)
    assert found == [], (
        f"Legacy config.py files have reappeared: {found}. "
        "Module metadata must live in __init__.py's register() call. "
        "See docs/PRODUCTS_ARCHITECTURE.md."
    )


def test_no_legacy_get_registered_modules_imports():
    """No file may import the removed ``get_registered_modules`` symbol.

    Scans the backend source tree (excluding venv, __pycache__, tests
    themselves) for any reference to the deleted symbol.  Catches typos
    and accidental restorations before they cause an ImportError at
    application boot.
    """
    pattern = re.compile(
        r"\bfrom\s+modules\s+import\s+get_registered_modules\b"
        r"|\bmodules\.get_registered_modules\b"
        r"|\bModuleRegistry\.\w+\("
    )
    offenders: list[str] = []
    skip_dirs = {"venv", "__pycache__", ".git", "node_modules"}
    skip_files = {
        # This test file itself contains the literal description of the
        # forbidden patterns and must not match its own assertion.
        os.path.basename(__file__),
    }
    # Path-based skip (relative to BACKEND_ROOT): docstrings and
    # historical-context comments inside these files legitimately
    # mention the legacy names to explain what the new registry replaces.
    skip_relative_paths = {
        "core/module_registry.py",
        "modules/__init__.py",
    }
    for root, dirs, files in os.walk(BACKEND_ROOT):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for name in files:
            if not name.endswith(".py"):
                continue
            if name in skip_files:
                continue
            path = Path(root) / name
            rel = str(path.relative_to(BACKEND_ROOT))
            if rel in skip_relative_paths:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if pattern.search(text):
                offenders.append(rel)
    assert offenders == [], (
        f"Legacy registry references found in: {offenders}. "
        "Use `from core.module_registry import get_all_for_ui` instead."
    )


def test_modules_package_init_is_marker_only():
    """``modules/__init__.py`` must not define a ModuleRegistry class.

    After the consolidation, this file is just a package marker with
    a docstring. Adding class ModuleRegistry / def get_registered_modules
    back would silently revive the dual-registry pattern.
    """
    text = (MODULES_DIR / "__init__.py").read_text(encoding="utf-8")
    forbidden = ["class ModuleRegistry", "def get_registered_modules", "def discover_modules"]
    found = [f for f in forbidden if f in text]
    assert found == [], (
        f"modules/__init__.py contains forbidden legacy definitions: {found}. "
        "Module metadata must live in core.module_registry via register()."
    )


def test_registered_keys_form_superset_of_co_activation_rules():
    """Every key in CO_ACTIVATE / CO_DEACTIVATE must be a real module.

    Stops typos in the cascading-activation rules in routers/modules.py
    from causing silent activate/deactivate no-ops.  The 'commerce'
    module's cascade lists product_catalog and customers_light — both
    must exist in the registry.
    """
    # Trigger module registration via package imports
    import modules.cashflow_monitor  # noqa: F401
    import modules.commerce  # noqa: F401
    import modules.customer_insights  # noqa: F401
    import modules.product_catalog  # noqa: F401

    from core.module_registry import get_all
    from routers.modules import CO_ACTIVATE, CO_DEACTIVATE

    registered_keys = {m.module_key for m in get_all()}
    for label, mapping in [("CO_ACTIVATE", CO_ACTIVATE), ("CO_DEACTIVATE", CO_DEACTIVATE)]:
        for parent_key, deps in mapping.items():
            assert parent_key in registered_keys, (
                f"{label} declares parent {parent_key!r} but no module is registered with that key"
            )
            for dep_key in deps:
                assert dep_key in registered_keys, (
                    f"{label}[{parent_key!r}] declares dependency {dep_key!r} "
                    f"but no module is registered with that key"
                )
