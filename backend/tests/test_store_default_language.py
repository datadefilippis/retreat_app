"""Tests for the storefront default-language resolution.

Phase 1 of the Store consolidation plan pins the contract that:

  the admin's account locale at store-creation time becomes the
  store's default storefront language, falling back to "it" only when
  the locale is missing or outside the i18n-supported set.

Why these tests exist
---------------------
The `storefront_languages` array on a Store drives:
  · which i18n bundles the public storefront loads,
  · the primary landing language for guest visitors
    (see useStorefrontLocale.js → 'storeDefault' branch),
  · the language picker shown to logged-in customers.

Three real-world ways a wrong default leaks in:
  1. A new merchant signs up in German, creates a store, sees an
     Italian storefront. Friction; they don't realize a picker exists.
  2. A future refactor adds a new entry point that constructs Store()
     directly (script / fixture / fixed-point seeder) and the
     model-level default `["it"]` quietly overrides whatever the
     creator's locale was.
  3. The `_resolve_default_storefront_locale` helper normalizes
     BCP-47 forms (`en-US` → `en`); breaking this normalization would
     silently route every English-locale user to `"it"` via the
     fallback branch.

We test (1) and (3) directly with unit-level coverage of the resolver,
and pin (2) by asserting the Pydantic model default stays `["it"]`
(so any change to it shows up here, not in production).

Pure tests — no DB, no I/O, no FastAPI fixtures.
"""

import os
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

from models.store import Store
from routers.stores import (
    SUPPORTED_LOCALES,
    _resolve_default_storefront_locale,
)


# ── _resolve_default_storefront_locale — happy path ────────────────────────


class TestResolverSupportedLocales:
    """The resolver returns the user's locale verbatim when it's a
    short app-supported code. This is the dominant runtime path —
    every admin who completed signup has a locale set."""

    def test_italian_locale_returns_it(self):
        assert _resolve_default_storefront_locale({"locale": "it"}) == "it"

    def test_english_locale_returns_en(self):
        assert _resolve_default_storefront_locale({"locale": "en"}) == "en"

    def test_german_locale_returns_de(self):
        # Pins the wellness-case-study scenario: Swiss merchant in
        # German UI must land on a German storefront default.
        assert _resolve_default_storefront_locale({"locale": "de"}) == "de"

    def test_french_locale_returns_fr(self):
        assert _resolve_default_storefront_locale({"locale": "fr"}) == "fr"


# ── _resolve_default_storefront_locale — normalisation ─────────────────────


class TestResolverNormalisation:
    """BCP-47 inputs (`en-US`, `de-CH`) must collapse to the short
    code before the supported-set check. Uppercase variants likewise.
    Tied to the parallel `_normalize()` in useStorefrontLocale.js — if
    these two drift, the storefront and the seed value diverge."""

    def test_bcp47_en_us_returns_en(self):
        assert _resolve_default_storefront_locale({"locale": "en-US"}) == "en"

    def test_bcp47_de_ch_returns_de(self):
        # Real-world: Swiss admins typically get `de-CH` from
        # OS-locale propagation through OAuth providers.
        assert _resolve_default_storefront_locale({"locale": "de-CH"}) == "de"

    def test_uppercase_de_returns_de(self):
        assert _resolve_default_storefront_locale({"locale": "DE"}) == "de"

    def test_mixed_case_bcp47_returns_short_code(self):
        assert _resolve_default_storefront_locale({"locale": "Fr-CA"}) == "fr"


# ── _resolve_default_storefront_locale — fallback to "it" ──────────────────


class TestResolverFallback:
    """The "it" fallback is a defensive last resort. It fires only when
    the user's locale is unset, empty, or outside the four-language app
    support set. Pinning the exact fallback value prevents an
    inadvertent flip (e.g. someone changes to "en" globally would
    silently re-language every legacy store-creation path)."""

    def test_none_user_returns_it_fallback(self):
        # Path: a helper called from a non-HTTP context (e.g. legacy
        # migration where current_user is unknown). The docstring of
        # the resolver explicitly promises "it" here.
        assert _resolve_default_storefront_locale(None) == "it"

    def test_user_without_locale_returns_it(self):
        assert _resolve_default_storefront_locale({}) == "it"

    def test_user_with_empty_locale_returns_it(self):
        assert _resolve_default_storefront_locale({"locale": ""}) == "it"

    def test_user_with_none_locale_returns_it(self):
        assert _resolve_default_storefront_locale({"locale": None}) == "it"

    def test_unsupported_locale_returns_it(self):
        # Spanish isn't in the i18n stack yet — fallback applies even
        # if the user's account claims `es-MX`.
        assert _resolve_default_storefront_locale({"locale": "es"}) == "it"

    def test_garbage_locale_returns_it(self):
        assert _resolve_default_storefront_locale({"locale": "xx-INVALID"}) == "it"


# ── Resolver output ⊂ supported set (invariant) ────────────────────────────


class TestResolverInvariant:
    """The resolver's return value is always one of the four
    app-supported locales. The frontend i18n bundle list mirrors this
    set — a return value outside it would 500 the storefront on
    /catalog/{slug}.

    This is an architectural invariant we want to lock independently of
    the specific test cases above so adding a 5th locale (e.g. "es")
    later requires conscious update of BOTH this set and the i18n stack.
    """

    @pytest.mark.parametrize(
        "user_locale",
        ["it", "en", "de", "fr", "en-US", "de-CH", "fr-CA", "DE", None, "", "xx", "es"],
    )
    def test_output_always_in_supported_set(self, user_locale):
        user = None if user_locale is None else {"locale": user_locale}
        result = _resolve_default_storefront_locale(user)
        assert result in SUPPORTED_LOCALES, (
            f"Resolver returned `{result}` for input `{user_locale}` — "
            f"not in SUPPORTED_LOCALES={SUPPORTED_LOCALES}. Storefront i18n would 500."
        )


# ── Model-level default — defensive fallback contract ──────────────────────


class TestStoreModelDefault:
    """The Pydantic default `storefront_languages=["it"]` is a defensive
    fallback for paths that instantiate Store() WITHOUT providing the
    field (tests, scripts, fixtures). The HTTP create paths always
    override it via `_resolve_default_storefront_locale(current_user)`,
    so production traffic never hits this branch.

    We assert the value stays `["it"]` (not `[]` or `["en"]`) because:
      - An empty list breaks the storefront's "storeDefault" branch
        in useStorefrontLocale.js (which assumes length >= 1).
      - Any non-"it" universal default would silently re-language every
        script-created store across all merchants on next deploy.

    If a future Phase 2 validator forbids `[]` we keep this fallback
    as the canonical "the system has no other signal" value.
    """

    def test_default_is_italian_singleton(self):
        # No explicit value → fallback fires.
        s = Store(organization_id="org_test", name="Test Store")
        assert s.storefront_languages == ["it"]

    def test_explicit_value_overrides_default(self):
        # Real-world create path: HTTP layer computes the list from
        # user.locale and passes it explicitly. The default must not
        # leak through.
        s = Store(
            organization_id="org_test",
            name="Test Store",
            storefront_languages=["de"],
        )
        assert s.storefront_languages == ["de"]

    def test_multi_language_value_preserved(self):
        # Forward-compatible: when the multi-lang toggle ships, the
        # admin sends a 2+ element array. The model must round-trip
        # without truncation.
        s = Store(
            organization_id="org_test",
            name="Test Store",
            storefront_languages=["de", "fr"],
        )
        assert s.storefront_languages == ["de", "fr"]
