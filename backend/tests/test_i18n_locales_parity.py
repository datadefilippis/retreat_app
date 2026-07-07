"""Locale parity guard for the frontend i18n JSON files.

Why this lives in the Python test suite even though it inspects JSON
files under ``frontend/src/locales/``:

  * Keeps i18n validation under the same CI hook the backend pytest run
    already uses — no extra Jest/Vitest infra needed for what is
    fundamentally a JSON-shape check.
  * Catches the silent-fallback bug class: the React component calls
    ``t('foo.bar', 'Italian default')``. If ``foo.bar`` is missing
    from a locale, the user sees the Italian default instead of an
    error — a polish issue invisible until a Swiss-German merchant
    reports it.

Scope: every locale must expose the SAME key set. Translations may
differ in copy length, but the key TOPOLOGY must match across
``it / en / de / fr`` so a future ``t(key)`` call resolves in all
four UIs the moment it lands in the JSX.

Currently audited namespaces:
  * settings.paymentMethods   (Sub-stream 2.4 — CH compliance v1)

Add more namespaces below as the i18n sweep extends.
"""

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
LOCALES_DIR = REPO_ROOT / "frontend" / "src" / "locales"
LOCALES = ("it", "en", "de", "fr")


def _flatten(obj, prefix=""):
    """Return the set of dot-paths that lead to leaf (non-dict) values."""
    if not isinstance(obj, dict):
        return {prefix.rstrip(".")}
    keys = set()
    for k, v in obj.items():
        keys |= _flatten(v, f"{prefix}{k}.")
    return keys


def _read(locale: str, namespace: str) -> dict:
    f = LOCALES_DIR / locale / f"{namespace}.json"
    return json.loads(f.read_text())


# ── Discovered topology snapshot ─────────────────────────────────────────
# Built from the IT file at audit time. We assert the exact SAME set of
# leaf keys exists in each of the other 3 locales. When an i18n sweep
# adds new keys we update IT and re-run; if the others lag we get a
# diff — much faster than a Swiss merchant reporting "this string is
# in Italian for me".


@pytest.mark.parametrize("namespace,subpath", [
    ("settings", "paymentMethods"),
    ("customerInsights", ""),
    ("common", "reviews"),      # PR5 — plancia recensioni back-office
    ("landings", "reviews"),    # PR5 — flusso recensioni pubblico
    ("common", "charts"),          # CF1 — kit grafico
    ("common", "outreachShared"),  # CF2 — ContactActions
    ("common", "cashflow"),        # CF3 — pagina Incassi
    ("customerInsights", "essential"),  # CF6 — clienti essenziale
    ("newsletter", "stats"),       # CF7 — mini-stats newsletter
    ("products", "salesStats"),         # CG3 — mini-stats per anima
    ("customerInsights", "crossSell"),  # CG4 — cross-sell
    ("customerInsights", "anime"),      # CG4 — badge anime
])
def test_locales_have_identical_key_topology(namespace, subpath):
    """All locales expose the same dot-path key set under ``subpath``."""
    locales_keys = {}
    for loc in LOCALES:
        data = _read(loc, namespace)
        section = data
        if subpath:
            for part in subpath.split("."):
                section = section.get(part, {})
        locales_keys[loc] = _flatten(section)

    reference = locales_keys["it"]
    assert reference, (
        f"IT locale missing keys under '{namespace}.{subpath}'. "
        f"Reference is empty → cannot validate parity."
    )

    diffs = []
    for loc in LOCALES:
        if loc == "it":
            continue
        missing = reference - locales_keys[loc]
        extra = locales_keys[loc] - reference
        if missing or extra:
            diffs.append(f"  {loc}: missing={sorted(missing)} extra={sorted(extra)}")

    assert not diffs, (
        f"Locale key drift under '{namespace}.{subpath}':\n" + "\n".join(diffs)
    )


@pytest.mark.parametrize("namespace,subpath", [
    ("settings", "paymentMethods"),
    ("customerInsights", ""),
    ("common", "reviews"),
    ("landings", "reviews"),
    ("common", "charts"),
    ("common", "outreachShared"),
    ("common", "cashflow"),
    ("customerInsights", "essential"),
    ("newsletter", "stats"),
    ("products", "salesStats"),
    ("customerInsights", "crossSell"),
    ("customerInsights", "anime"),
])
def test_locales_have_no_empty_string_translations(namespace, subpath):
    """An empty string slips through silently in the UI (renders blank).
    Catch it here so a copy-paste mistake doesn't make it to prod.
    """
    offenders = []
    for loc in LOCALES:
        data = _read(loc, namespace)
        section = data
        if subpath:
            for part in subpath.split("."):
                section = section.get(part, {})

        def walk(obj, prefix=""):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    walk(v, f"{prefix}{k}.")
            elif isinstance(obj, str) and not obj.strip():
                offenders.append(f"{loc}.{prefix.rstrip('.')}")

        walk(section)

    assert not offenders, (
        f"Empty translation strings under '{namespace}.{subpath}':\n" +
        "\n".join(f"  {o}" for o in offenders)
    )


# ── Specific spot-checks for paymentMethods (Sub-stream 2.4) ──────────────


def test_payment_methods_translates_twint_cta_to_each_locale():
    """The TWINT CTA banner is the most prominent CHF-specific copy.
    Spot-check that it actually translates rather than echoing the
    Italian default.
    """
    italian = _read("it", "settings")["paymentMethods"]["twintCta"]["title"]
    for loc in ("en", "de", "fr"):
        translated = _read(loc, "settings")["paymentMethods"]["twintCta"]["title"]
        assert translated != italian, (
            f"{loc}.paymentMethods.twintCta.title is identical to IT — "
            f"likely a missed translation."
        )


# ── PR5 — le chiavi recensioni usate nel JSX esistono nei locales ────────


def _keys_used_in(component_path: str, pattern: str) -> set:
    """Extract i18n keys referenced by a component via ``t('<pattern>...')``."""
    import re
    src = (REPO_ROOT / "frontend" / "src" / component_path).read_text()
    return set(re.findall(pattern, src))


def _resolves(section: dict, key: str) -> bool:
    """A key resolves if present as-is or via plural forms (_one/_other)."""
    return key in section or (
        f"{key}_one" in section and f"{key}_other" in section)


def test_reviews_admin_page_keys_exist_in_common_locales():
    """Every ``t('reviews.X')`` in ReviewsAdminPage must resolve in all 4
    common.json files — otherwise the UI silently falls back to the
    Italian defaultValue for non-IT operators."""
    used = _keys_used_in("features/reviews/ReviewsAdminPage.js",
                         r"t\('reviews\.([a-zA-Z]+)'")
    assert used, "no reviews.* keys found — component moved? update the guard"
    missing = []
    for loc in LOCALES:
        section = _read(loc, "common").get("reviews", {})
        missing += [f"{loc}.reviews.{k}" for k in sorted(used)
                    if not _resolves(section, k)]
    assert not missing, "reviews keys missing in common.json:\n" + \
        "\n".join(f"  {m}" for m in missing)


def test_public_reviews_flow_keys_exist_in_landings_locales():
    """Same guard for the public flow on OperatorProfilePage
    (``landings:reviews.*``)."""
    used = _keys_used_in("features/storefront/OperatorProfilePage.js",
                         r"'landings:reviews\.([a-zA-Z]+)'")
    assert used, "no landings:reviews.* keys found — update the guard"
    missing = []
    for loc in LOCALES:
        section = _read(loc, "landings").get("reviews", {})
        missing += [f"{loc}.reviews.{k}" for k in sorted(used)
                    if not _resolves(section, k)]
    assert not missing, "reviews keys missing in landings.json:\n" + \
        "\n".join(f"  {m}" for m in missing)


def test_payment_methods_active_badge_is_short_word():
    """The 'Active' badge is rendered inside a small chip — long
    translations would wrap awkwardly. Pin to ≤ 12 chars.
    """
    for loc in LOCALES:
        badge = _read(loc, "settings")["paymentMethods"]["activeBadge"]
        assert len(badge) <= 12, (
            f"{loc}.paymentMethods.activeBadge='{badge}' is {len(badge)} chars; "
            f"must be ≤ 12 to fit the badge UI"
        )


def test_retreat_billing_feature_keys_exist_in_all_locales():
    """MD4 — ogni voce features_display dei piani retreat ha la sua
    copy in TUTTE le lingue (settings.json → billing.features.*)."""
    import sys
    backend = Path(__file__).resolve().parent.parent
    if str(backend) not in sys.path:
        sys.path.insert(0, str(backend))
    from services.seed_commercial_plans import RETREAT_COMMERCIAL_PLANS
    keys = set()
    for plan in RETREAT_COMMERCIAL_PLANS:
        keys |= set(plan.get("features_display", []))
    missing = []
    for loc in LOCALES:
        feats = _read(loc, "settings").get("billing", {}).get("features", {})
        for key in sorted(keys):
            short = key.split("billing.features.")[-1]
            if short not in feats:
                missing.append(f"{loc}: {short}")
            # GT5 — ogni voce ha anche il dettaglio "_info" (info circle):
            # i piani si spiegano, non sono una lista della spesa
            if f"{short}_info" not in feats:
                missing.append(f"{loc}: {short}_info")
    assert not missing, "Copy mancante per voci di pricing:\n" + "\n".join(missing)
