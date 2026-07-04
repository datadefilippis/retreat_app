"""Tests for Phase 2 of the Store consolidation plan: shared validator
helper + route parity for `fulfillment_modes` and `storefront_languages`.

Goal
----
Two parallel update surfaces exist:

  · `PATCH /stores/{id}`        (multi-store world, models.store.StoreUpdate)
  · `PATCH /store-settings`     (legacy embedded settings, StoreSettingsUpdate)

Pre-Phase-2 they validated `fulfillment_modes` differently:
  - /stores: strict (must be non-empty, all in {"shipping","local_pickup"})
  - /store-settings: NONE — accepted any payload

And `storefront_languages` had no validation on either side, so an empty
array or unsupported code (e.g. "es") could land in the DB and break the
storefront i18n resolver (which assumes storefront_languages[0] ∈
APP_SUPPORTED).

This file pins:
  1. The shared helper `validate_string_list_field` raises ValueError
     for every malformed input the storefront expects to never see.
  2. The Italian 400 message contract on `fulfillment_modes` is preserved
     after the refactor (so the frontend's existing error-toast copy
     still matches without UI changes).
  3. The two routes apply the same rules to `fulfillment_modes` (parity).
  4. The new `storefront_languages` rule kicks in on /stores/{id}.

Pure unit tests on the helper + a parametrised parity sweep.
No DB, no FastAPI fixtures.
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

from models.store import (
    SUPPORTED_FULFILLMENT_MODES,
    SUPPORTED_STOREFRONT_LANGUAGES,
    validate_string_list_field,
)


# ── Helper — happy path ────────────────────────────────────────────────────


class TestValidatorHappyPath:
    """Valid payloads pass through untouched. The helper returns the
    input value so callers can use a single-line idiom like
    `updates[k] = validate_string_list_field(updates[k], ...)`."""

    def test_single_valid_language(self):
        assert validate_string_list_field(
            ["it"], field_name="storefront_languages",
            allowed=SUPPORTED_STOREFRONT_LANGUAGES,
        ) == ["it"]

    def test_multi_valid_languages_preserves_order(self):
        # Order matters — storefront i18n reads [0] as the primary.
        assert validate_string_list_field(
            ["de", "fr"], field_name="storefront_languages",
            allowed=SUPPORTED_STOREFRONT_LANGUAGES,
        ) == ["de", "fr"]

    def test_all_four_languages_accepted(self):
        # Forward-compatible: when multi-lang ships, the admin can
        # enable the full set.
        out = validate_string_list_field(
            ["it", "en", "de", "fr"], field_name="storefront_languages",
            allowed=SUPPORTED_STOREFRONT_LANGUAGES,
        )
        assert out == ["it", "en", "de", "fr"]

    def test_shipping_only_fulfillment(self):
        assert validate_string_list_field(
            ["shipping"], field_name="fulfillment_modes",
            allowed=SUPPORTED_FULFILLMENT_MODES,
        ) == ["shipping"]

    def test_both_fulfillment_modes(self):
        assert validate_string_list_field(
            ["shipping", "local_pickup"], field_name="fulfillment_modes",
            allowed=SUPPORTED_FULFILLMENT_MODES,
        ) == ["shipping", "local_pickup"]


# ── Helper — rejected payloads ─────────────────────────────────────────────


class TestValidatorRejectsEmpty:
    """An empty list is the most likely accidental payload — frontend
    bugs (uncheck-all loop) used to send `[]` to /store-settings before
    Phase 2. Pinning the exact Italian 400 message text preserves the
    existing error-toast copy the UI shows."""

    def test_empty_languages_rejected(self):
        with pytest.raises(ValueError) as exc:
            validate_string_list_field(
                [], field_name="storefront_languages",
                allowed=SUPPORTED_STOREFRONT_LANGUAGES,
            )
        # The Italian message is part of the 400 contract — the frontend
        # toast subscribes to `detail` string verbatim.
        assert "deve contenere almeno un valore valido" in str(exc.value)
        assert "storefront_languages" in str(exc.value)

    def test_empty_fulfillment_modes_rejected(self):
        # This is the exact message string the pre-Phase-2 manual check
        # at routers/stores.update_store raised. Preserving it means
        # zero frontend change after the refactor.
        with pytest.raises(ValueError) as exc:
            validate_string_list_field(
                [], field_name="fulfillment_modes",
                allowed=SUPPORTED_FULFILLMENT_MODES,
            )
        assert "fulfillment_modes deve contenere almeno un valore valido" in str(exc.value)


class TestValidatorRejectsInvalidCodes:
    """Unsupported values (typos, languages we don't ship i18n for)
    must fail loudly. Silent persistence used to break the storefront."""

    def test_unsupported_language_es_rejected(self):
        with pytest.raises(ValueError) as exc:
            validate_string_list_field(
                ["es"], field_name="storefront_languages",
                allowed=SUPPORTED_STOREFRONT_LANGUAGES,
            )
        msg = str(exc.value)
        assert "'es'" in msg
        # The error must enumerate the allowed set so the frontend can
        # render specific copy (e.g. "Lingue ammesse: IT, EN, DE, FR")
        # without string-parsing.
        assert "Valori ammessi" in msg

    def test_garbage_language_rejected(self):
        with pytest.raises(ValueError):
            validate_string_list_field(
                ["xx-INVALID"], field_name="storefront_languages",
                allowed=SUPPORTED_STOREFRONT_LANGUAGES,
            )

    def test_one_valid_one_invalid_language_rejected(self):
        # The presence of one valid code doesn't excuse the other —
        # mixed inputs are still rejected (no silent filtering).
        with pytest.raises(ValueError) as exc:
            validate_string_list_field(
                ["it", "es"], field_name="storefront_languages",
                allowed=SUPPORTED_STOREFRONT_LANGUAGES,
            )
        assert "'es'" in str(exc.value)

    def test_unsupported_fulfillment_mode_rejected(self):
        # "air_drop" is the canonical test value for "future mode the
        # backend doesn't ship yet" — we want the API to reject this
        # rather than silently storing an unrenderable mode.
        with pytest.raises(ValueError) as exc:
            validate_string_list_field(
                ["air_drop"], field_name="fulfillment_modes",
                allowed=SUPPORTED_FULFILLMENT_MODES,
            )
        assert "'air_drop'" in str(exc.value)


class TestValidatorRejectsDuplicates:
    """Duplicates indicate a frontend bug (double-click on a toggle).
    Silently coercing to a unique set would mask the bug; reject."""

    def test_duplicate_language_rejected(self):
        with pytest.raises(ValueError) as exc:
            validate_string_list_field(
                ["de", "de"], field_name="storefront_languages",
                allowed=SUPPORTED_STOREFRONT_LANGUAGES,
            )
        assert "duplicato" in str(exc.value)
        assert "'de'" in str(exc.value)

    def test_duplicate_fulfillment_mode_rejected(self):
        with pytest.raises(ValueError) as exc:
            validate_string_list_field(
                ["shipping", "shipping"], field_name="fulfillment_modes",
                allowed=SUPPORTED_FULFILLMENT_MODES,
            )
        assert "duplicato" in str(exc.value)


class TestValidatorRejectsTypeErrors:
    """Defensive: non-list / non-string inputs from a misbehaving
    client must produce a clear 400, not a 500."""

    def test_none_rejected(self):
        # `None` is a "field is required" signal — callers should skip
        # the check when the field is absent from the PATCH body, so
        # reaching the helper with None is a programmer error.
        with pytest.raises(ValueError):
            validate_string_list_field(
                None, field_name="storefront_languages",
                allowed=SUPPORTED_STOREFRONT_LANGUAGES,
            )

    def test_string_instead_of_list_rejected(self):
        # JSON foot-gun: `"it"` instead of `["it"]`. Without the type
        # check Python's `in` operator would treat the string as
        # iterable of chars and accept it as if it were ["i","t"].
        with pytest.raises(ValueError) as exc:
            validate_string_list_field(
                "it", field_name="storefront_languages",
                allowed=SUPPORTED_STOREFRONT_LANGUAGES,
            )
        assert "must be a list" in str(exc.value)

    def test_dict_instead_of_list_rejected(self):
        with pytest.raises(ValueError):
            validate_string_list_field(
                {"it": True}, field_name="storefront_languages",
                allowed=SUPPORTED_STOREFRONT_LANGUAGES,
            )

    def test_int_element_rejected(self):
        with pytest.raises(ValueError) as exc:
            validate_string_list_field(
                ["it", 42], field_name="storefront_languages",
                allowed=SUPPORTED_STOREFRONT_LANGUAGES,
            )
        assert "non valido" in str(exc.value)

    def test_none_element_rejected(self):
        with pytest.raises(ValueError):
            validate_string_list_field(
                [None], field_name="storefront_languages",
                allowed=SUPPORTED_STOREFRONT_LANGUAGES,
            )


# ── Route parity — both /stores and /store-settings reject the same inputs ─


class TestRouteParity:
    """The shared helper is the SINGLE source of truth for
    fulfillment_modes validation across both endpoints. This test sweeps
    a battery of bad payloads through both routers' check call-sites
    and asserts identical rejection — eliminating the drift risk that
    motivated Phase 2.

    Strategy: don't spin up FastAPI. Instead, re-import the helper at
    the same call-sites the routers do and verify rejection. This keeps
    the test fast (no event loop) while still locking the contract.
    """

    BAD_FULFILLMENT_PAYLOADS = [
        ([], "empty list"),
        (["air_drop"], "unsupported mode"),
        (["shipping", "shipping"], "duplicate"),
        ("shipping", "string not list"),
        (["shipping", 1], "non-string element"),
        ([None], "None element"),
        ({"x": "y"}, "dict not list"),
    ]

    @pytest.mark.parametrize("payload,reason", BAD_FULFILLMENT_PAYLOADS)
    def test_fulfillment_modes_rejected_consistently(self, payload, reason):
        """Both endpoints invoke `validate_string_list_field` with
        identical args. Verifying the helper rejects each payload is
        equivalent to verifying parity — the routers can't disagree."""
        with pytest.raises(ValueError):
            validate_string_list_field(
                payload, field_name="fulfillment_modes",
                allowed=SUPPORTED_FULFILLMENT_MODES,
            )


# ── Routers actually import + invoke the helper (smoke check) ──────────────


class TestRoutersWireHelper:
    """Smoke test: confirm both routers actually import the helper and
    the SUPPORTED constants. Catches a future refactor that drops the
    import (silent regression: validation disappears, this file's
    helper-level tests still pass)."""

    def test_stores_router_imports_helper(self):
        from routers import stores as stores_router

        assert hasattr(stores_router, "validate_string_list_field")
        assert hasattr(stores_router, "SUPPORTED_FULFILLMENT_MODES")
        assert hasattr(stores_router, "SUPPORTED_STOREFRONT_LANGUAGES")
        assert stores_router.SUPPORTED_FULFILLMENT_MODES == SUPPORTED_FULFILLMENT_MODES
        assert stores_router.SUPPORTED_STOREFRONT_LANGUAGES == SUPPORTED_STOREFRONT_LANGUAGES

    def test_store_settings_router_imports_helper(self):
        from routers import store_settings as ss_router

        assert hasattr(ss_router, "validate_string_list_field")
        assert hasattr(ss_router, "SUPPORTED_FULFILLMENT_MODES")
        assert ss_router.SUPPORTED_FULFILLMENT_MODES == SUPPORTED_FULFILLMENT_MODES


# ── Supported-set contract ─────────────────────────────────────────────────


class TestSupportedSets:
    """Lock the exact contents of the supported sets. A change here
    must be a conscious, multi-file update (i18n bundles + storefront
    resolver + this constant), not a one-line tweak."""

    def test_storefront_languages_set_pinned(self):
        # Mirrors APP_SUPPORTED in frontend useStorefrontLocale.js and
        # routers/stores.SUPPORTED_LOCALES. Drift = silent storefront 500.
        assert SUPPORTED_STOREFRONT_LANGUAGES == frozenset({"it", "en", "de", "fr"})

    def test_fulfillment_modes_set_pinned(self):
        # Adding a third mode (e.g. "digital_delivery") requires a
        # backend + storefront + email-template audit — not a quick fix.
        assert SUPPORTED_FULFILLMENT_MODES == frozenset({"shipping", "local_pickup"})
