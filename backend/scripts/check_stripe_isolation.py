#!/usr/bin/env python3
"""
Lint rule: ``import stripe`` is allowed only in a controlled set of files.

Why this exists
===============
Sub-stream 2 introduced a provider abstraction (``payment_providers/``)
specifically so the Stripe SDK is a swap-out detail rather than a
load-bearing dependency. Without this check, a routine PR could
re-introduce a ``import stripe`` in ``services/order_*.py`` or
``modules/cashflow_monitor/*`` and undo the isolation work — silently,
because nothing would break in tests.

Scope (deliberate)
==================
We DO NOT ban ``import stripe`` globally — that would force a same-day
rewrite of the AFianco-platform subscription path
(``services/billing_lifecycle.py``, ``services/stripe_service.py``,
``services/plan_provisioning.py``, ``services/stripe_*``,
``services/stripe_connect_express.py``, the admin scripts), all of
which are *out of scope* for the multi-currency / merchant-checkout
work and are always denominated in EUR by business design.

Banned
------
``import stripe`` MUST NOT appear in:
  * ``backend/routers/**``           — routers route, they don't talk to SDKs
  * ``backend/services/order_*.py``  — order email/PDF/import are SDK-free
  * ``backend/services/event_*.py``  — event ticketing same
  * ``backend/services/booking_*.py``— booking flow same
  * ``backend/modules/**``           — cashflow / customers analytics

Allowed
-------
``import stripe`` MAY appear in:
  * ``backend/payment_providers/stripe/**``  (the only blessed home)
  * ``backend/services/payment_checkout_service.py``
        — legacy verify/refund/dispute paths still use ``_get_stripe()``;
          will be migrated into the provider in a future iteration.
  * ``backend/services/billing_lifecycle.py``,
    ``services/plan_provisioning.py``,
    ``services/stripe_service.py``,
    ``services/stripe_connect_express.py``,
    ``services/stripe_catalog_service.py``
        — AFianco SaaS subscription (CommercialPlan), always EUR,
          orthogonal to the merchant checkout flow.
  * ``backend/scripts/**``  — admin one-shots.

Exit code 0 if clean, 1 if any banned location contains the import.

Usage
-----
    cd backend
    python -m scripts.check_stripe_isolation

Wired into pre-commit / CI when v1.5 lands; for now it's a manual
canary the team runs before merging payment-provider PRs.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


_ROOT = Path(__file__).resolve().parent.parent  # → backend/

# Files that may legitimately import the Stripe SDK.
#
# Two buckets:
#   1. Merchant commerce flow (multi-currency / TWINT-aware) —
#      ``payment_checkout_service.py`` keeps a thin SDK touchpoint
#      while the verify/refund/dispute paths complete migration.
#   2. AFianco platform SaaS billing — orthogonal to the merchant
#      flow, always EUR by business design. Lives in routers/billing,
#      routers/auth, routers/admin* (subscription cancel), and the
#      background subscription-audit jobs. Listed here so the rule is
#      strict on commerce paths without forcing a same-day rewrite of
#      the SaaS subscription stack.
_ALLOW_FILES = {
    # Merchant commerce flow
    _ROOT / "services" / "payment_checkout_service.py",
    # AFianco SaaS subscription
    _ROOT / "services" / "billing_lifecycle.py",
    _ROOT / "services" / "plan_provisioning.py",
    _ROOT / "services" / "stripe_service.py",
    _ROOT / "services" / "stripe_connect_express.py",
    _ROOT / "services" / "stripe_catalog_service.py",
    _ROOT / "services" / "background_service.py",
    _ROOT / "routers" / "auth.py",
    _ROOT / "routers" / "billing.py",
    _ROOT / "routers" / "admin.py",
    _ROOT / "routers" / "admin_catalog.py",
}

# Whole subtrees where the import is allowed.
_ALLOW_PREFIXES = (
    _ROOT / "payment_providers" / "stripe",
    _ROOT / "scripts",
)

# Subtrees the rule actively polices. Keeping the scope narrow means
# we catch real isolation violations without false positives in the
# parts of the codebase that legitimately need Stripe.
_POLICE_PREFIXES = (
    _ROOT / "routers",
    _ROOT / "modules",
)
# Plus any single file in services/ that doesn't appear in _ALLOW_FILES.
_POLICE_SERVICES_GLOB = _ROOT / "services"

_IMPORT_RE = re.compile(
    r"^\s*(?:import\s+stripe\b|from\s+stripe(?:\.\w+)*\s+import)",
    re.MULTILINE,
)


def _is_allowed(path: Path) -> bool:
    if path in _ALLOW_FILES:
        return True
    return any(path.is_relative_to(prefix) for prefix in _ALLOW_PREFIXES)


def _is_policed(path: Path) -> bool:
    if path.is_relative_to(_POLICE_SERVICES_GLOB):
        # services/ is policed *unless* explicitly allow-listed.
        return path not in _ALLOW_FILES
    return any(path.is_relative_to(prefix) for prefix in _POLICE_PREFIXES)


def _scan() -> list[tuple[Path, int, str]]:
    """Return (path, line_number, line_text) tuples for every violation."""
    violations: list[tuple[Path, int, str]] = []
    for path in _ROOT.rglob("*.py"):
        if not _is_policed(path):
            continue
        if _is_allowed(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for match in _IMPORT_RE.finditer(text):
            line_no = text.count("\n", 0, match.start()) + 1
            line_text = text.splitlines()[line_no - 1].strip()
            violations.append((path, line_no, line_text))
    return violations


def main() -> int:
    violations = _scan()
    if not violations:
        print("✓ Stripe isolation: no banned imports found.")
        return 0

    print("✗ Stripe isolation: forbidden imports detected.")
    print("")
    print("The following files import the Stripe SDK directly. They must")
    print("instead go through ``payment_providers`` (PaymentProviderRegistry).")
    print("")
    for path, line_no, line_text in violations:
        rel = path.relative_to(_ROOT)
        print(f"  {rel}:{line_no}: {line_text}")
    print("")
    print(f"Total: {len(violations)} violation(s). See header docstring "
          f"of {Path(__file__).name} for the rationale.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
