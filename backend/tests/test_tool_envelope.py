"""Tests for Wave 14.0 — Tool Result Envelope Contract.

The envelope is the canonical shape every chat AI tool should return.
This file is the contract: any change to the envelope semantics that
breaks these tests is a deliberate, breaking change requiring a wave
version bump and migration of all tools.

Sections:
  1. wrap_response — happy path + argument validation
  2. validate_envelope — strict + lenient modes
  3. is_envelope probe
  4. End-to-end shape examples (mirrors module docstring)
"""

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


from core.tool_envelope import (
    CANONICAL_SCOPES,
    DataIntegrityStatus,
    ENVELOPE_VERSION,
    EnvelopeValidationResult,
    RECOMMENDED_FIELDS,
    REQUIRED_FIELDS,
    RESERVED_FIELDS,
    attach_envelope_metadata,
    is_envelope,
    validate_envelope,
    wrap_response,
)


# ── 1. wrap_response — happy path ───────────────────────────────────────────


class TestWrapResponseHappyPath:
    def test_minimal_period_filtered_response(self):
        """Most common shape: period-scoped tool with data."""
        env = wrap_response(
            tool="query_cashflow_summary",
            has_data=True,
            data={"total_sales": 209954.34},
            currency="EUR",
            period={
                "label": "ytd",
                "start_date": "2026-01-01",
                "end_date": "2026-05-16",
                "days": 136,
                "semantic": "ytd",
            },
            temporal_scope="period_filtered",
        )

        # Required envelope fields all present
        assert env["has_data"] is True
        assert env["data"]["total_sales"] == 209954.34
        assert env["currency"] == "EUR"
        assert env["_temporal_scope"] == "period_filtered"
        assert env["_data_integrity"]["status"] == "ok"
        assert env["_data_integrity"]["message"] is None
        assert env["_source"]["tool"] == "query_cashflow_summary"
        assert env["_source"]["envelope_version"] == ENVELOPE_VERSION
        # Period block preserved
        assert env["period"]["semantic"] == "ytd"

    def test_no_data_response(self):
        """When has_data=False, must carry a caveat."""
        env = wrap_response(
            tool="query_cashflow_summary",
            has_data=False,
            caveat="Insufficient transactions in the requested period.",
        )

        assert env["has_data"] is False
        # Empty data dict (not None) — keeps the shape stable
        assert env["data"] == {}
        assert env["_caveat"].startswith("Insufficient")
        # Integrity defaults to ok (the tool ran fine; just no data)
        assert env["_data_integrity"]["status"] == "ok"

    def test_snapshot_tool_omits_period(self):
        """All-time snapshot tools (e.g. top customers) don't carry a
        period block. The envelope tolerates omission of optional
        recommended fields."""
        env = wrap_response(
            tool="query_top_customers",
            has_data=True,
            data={"customers": [{"name": "ACME", "total_revenue": 50000}]},
            temporal_scope="all_time",
        )
        assert "period" not in env
        assert env["_temporal_scope"] == "all_time"

    def test_warning_integrity_with_message(self):
        """Status warning requires a non-empty message."""
        env = wrap_response(
            tool="query_top_customers",
            has_data=True,
            data={"customers": []},
            temporal_scope="all_time",
            integrity_status="warning",
            integrity_message="customer_metrics last refreshed 9 days ago",
        )
        assert env["_data_integrity"]["status"] == "warning"
        assert env["_data_integrity"]["message"] == \
               "customer_metrics last refreshed 9 days ago"

    def test_error_integrity_with_message(self):
        env = wrap_response(
            tool="query_smart_brief",
            has_data=False,
            caveat="Smart brief failed; call query_cashflow_summary instead.",
            temporal_scope="period_filtered",
            integrity_status="error",
            integrity_message="risk_focus list/dict mismatch (pre-Wave-14 bug)",
        )
        assert env["_data_integrity"]["status"] == "error"


# ── 2. wrap_response — argument validation ─────────────────────────────────


class TestWrapResponseValidation:
    def test_empty_tool_name_raises(self):
        with pytest.raises(ValueError, match="tool must be a non-empty string"):
            wrap_response(tool="", has_data=True, data={})

    def test_invalid_integrity_status_raises(self):
        with pytest.raises(ValueError, match="integrity_status="):
            wrap_response(
                tool="x", has_data=True, data={},
                integrity_status="bogus",
            )

    def test_warning_without_message_raises(self):
        with pytest.raises(ValueError, match="requires a non-empty integrity_message"):
            wrap_response(
                tool="x", has_data=True, data={},
                integrity_status="warning",
            )

    def test_error_without_message_raises(self):
        with pytest.raises(ValueError, match="requires a non-empty integrity_message"):
            wrap_response(
                tool="x", has_data=False, caveat="...",
                integrity_status="error",
            )

    def test_no_data_without_caveat_or_integrity_raises(self):
        """When has_data=False, the user MUST be told why. Either a
        caveat or an integrity warning/error is required."""
        with pytest.raises(ValueError, match="requires either a caveat"):
            wrap_response(tool="x", has_data=False)


# ── 3. validate_envelope — strict + lenient modes ──────────────────────────


class TestValidateEnvelopeRequiredFields:
    def test_well_formed_envelope_passes(self):
        env = wrap_response(
            tool="query_cashflow_summary",
            has_data=True,
            data={"x": 1},
            currency="EUR",
            period={"label": "30d"},
            temporal_scope="period_filtered",
        )
        result = validate_envelope(env)
        assert result.ok is True
        assert result.errors == []

    def test_missing_has_data_is_error(self):
        result = validate_envelope({
            "data": {},
            "_temporal_scope": "period_filtered",
            "_data_integrity": {"status": "ok", "message": None},
            "_source": {"tool": "x", "envelope_version": ENVELOPE_VERSION},
        })
        assert result.ok is False
        assert any("has_data" in e for e in result.errors)

    def test_missing_temporal_scope_is_error(self):
        result = validate_envelope({
            "has_data": True,
            "data": {},
            "_data_integrity": {"status": "ok", "message": None},
            "_source": {"tool": "x", "envelope_version": ENVELOPE_VERSION},
        })
        assert result.ok is False
        assert any("_temporal_scope" in e for e in result.errors)

    def test_missing_data_integrity_is_error(self):
        result = validate_envelope({
            "has_data": True,
            "data": {},
            "_temporal_scope": "period_filtered",
            "_source": {"tool": "x", "envelope_version": ENVELOPE_VERSION},
        })
        assert result.ok is False
        assert any("_data_integrity" in e for e in result.errors)

    def test_missing_source_is_error(self):
        result = validate_envelope({
            "has_data": True,
            "data": {},
            "_temporal_scope": "period_filtered",
            "_data_integrity": {"status": "ok", "message": None},
        })
        assert result.ok is False
        assert any("_source" in e for e in result.errors)


class TestValidateEnvelopeFieldShapes:
    def test_has_data_must_be_bool(self):
        result = validate_envelope({
            "has_data": "yes",  # ← string, should be bool
            "_temporal_scope": "period_filtered",
            "_data_integrity": {"status": "ok", "message": None},
            "_source": {"tool": "x", "envelope_version": ENVELOPE_VERSION},
        })
        assert result.ok is False
        assert any("has_data must be bool" in e for e in result.errors)

    def test_temporal_scope_canonical_passes_clean(self):
        for scope in CANONICAL_SCOPES:
            env = wrap_response(
                tool="x", has_data=True, data={},
                temporal_scope=scope,
            )
            result = validate_envelope(env)
            assert result.ok, f"scope={scope} should be valid"

    def test_temporal_scope_custom_label_warns(self):
        env = wrap_response(
            tool="query_product_trend",
            has_data=True, data={},
            temporal_scope="materialized_30d_vs_prior_30d",
        )
        result = validate_envelope(env)
        # Tool-specific scope is allowed but flagged as a warning
        assert result.ok is True
        assert any("not in CANONICAL_SCOPES" in w for w in result.warnings)

    def test_temporal_scope_empty_string_is_error(self):
        result = validate_envelope({
            "has_data": True,
            "_temporal_scope": "",
            "_data_integrity": {"status": "ok", "message": None},
            "_source": {"tool": "x", "envelope_version": ENVELOPE_VERSION},
        })
        assert not result.ok
        assert any("_temporal_scope" in e for e in result.errors)

    def test_data_integrity_warning_without_message_is_error(self):
        result = validate_envelope({
            "has_data": True,
            "_temporal_scope": "period_filtered",
            "_data_integrity": {"status": "warning", "message": None},
            "_source": {"tool": "x", "envelope_version": ENVELOPE_VERSION},
        })
        assert not result.ok
        assert any("requires a non-empty" in e for e in result.errors)

    def test_source_missing_tool_is_error(self):
        result = validate_envelope({
            "has_data": True,
            "_temporal_scope": "period_filtered",
            "_data_integrity": {"status": "ok", "message": None},
            "_source": {"envelope_version": ENVELOPE_VERSION},
        })
        assert not result.ok
        assert any("_source.tool" in e for e in result.errors)

    def test_source_missing_envelope_version_is_error(self):
        result = validate_envelope({
            "has_data": True,
            "_temporal_scope": "period_filtered",
            "_data_integrity": {"status": "ok", "message": None},
            "_source": {"tool": "x"},
        })
        assert not result.ok
        assert any("envelope_version" in e for e in result.errors)


class TestValidateEnvelopeCrossFieldInvariants:
    def test_has_data_false_without_caveat_or_warning_is_error(self):
        result = validate_envelope({
            "has_data": False,
            "_temporal_scope": "period_filtered",
            "_data_integrity": {"status": "ok", "message": None},
            "_source": {"tool": "x", "envelope_version": ENVELOPE_VERSION},
        })
        assert not result.ok
        assert any("requires a _caveat" in e for e in result.errors)

    def test_has_data_false_with_caveat_passes(self):
        env = wrap_response(
            tool="x", has_data=False,
            caveat="No transactions in period.",
            temporal_scope="period_filtered",
        )
        result = validate_envelope(env)
        assert result.ok

    def test_has_data_false_with_integrity_warning_passes(self):
        env = wrap_response(
            tool="x", has_data=False,
            caveat="See integrity.",
            temporal_scope="period_filtered",
            integrity_status="warning",
            integrity_message="Partial data only",
        )
        result = validate_envelope(env)
        assert result.ok


class TestValidateEnvelopeStrictMode:
    def test_recommended_fields_are_warnings_when_lenient(self):
        """In lenient mode, missing recommended fields are warnings."""
        env = wrap_response(
            tool="query_data_quality_audit",
            has_data=True,
            data={"quality_score": 87},
            temporal_scope="current_state",
            # no currency, no period — both recommended-but-missing
        )
        result = validate_envelope(env)
        assert result.ok is True
        # Both 'currency' and 'period' missing → warnings
        assert any("currency" in w for w in result.warnings)
        assert any("period" in w for w in result.warnings)

    def test_recommended_fields_promote_to_errors_when_strict(self):
        env = wrap_response(
            tool="query_x",
            has_data=True,
            data={"x": 1},
            temporal_scope="period_filtered",
        )
        result = validate_envelope(env, strict=True)
        assert not result.ok
        # Errors include the recommended-but-missing
        assert any("currency" in e for e in result.errors)
        assert any("period" in e for e in result.errors)


class TestValidateEnvelopeReservedFieldHygiene:
    def test_currency_inside_data_warns(self):
        env = wrap_response(
            tool="x", has_data=True,
            data={"currency": "EUR", "total": 100},  # ← currency inside data
            temporal_scope="period_filtered",
        )
        result = validate_envelope(env)
        # Reserved field inside data → warning
        assert any("currency" in w and "data block" in w for w in result.warnings)


# ── 4. is_envelope probe ───────────────────────────────────────────────────


class TestIsEnvelopeProbe:
    def test_canonical_envelope_recognised(self):
        env = wrap_response(
            tool="x", has_data=True, data={},
            temporal_scope="period_filtered",
        )
        assert is_envelope(env) is True

    def test_non_dict_not_envelope(self):
        assert is_envelope(None) is False
        assert is_envelope([]) is False
        assert is_envelope("string") is False
        assert is_envelope(42) is False

    def test_incomplete_dict_not_envelope(self):
        assert is_envelope({"has_data": True}) is False
        assert is_envelope({"has_data": True, "_temporal_scope": "x"}) is False

    def test_legacy_tool_response_not_envelope(self):
        """A pre-Wave-14 tool result lacks the envelope fields."""
        legacy = {
            "total": 1000.0,
            "currency": "EUR",
            "_caveat": None,
            "by_date": {"2026-05-01": 100.0},
        }
        assert is_envelope(legacy) is False


# ── 5. End-to-end shape examples ───────────────────────────────────────────


class TestEnvelopeShapeExamples:
    def test_query_cashflow_summary_shape(self):
        """The canonical cashflow summary shape from the module
        docstring. Pinning this ensures the envelope structure stays
        stable across waves."""
        env = wrap_response(
            tool="query_cashflow_summary",
            has_data=True,
            data={
                "total_sales": 209954.34,
                "net_after_fixed": 90899.99,
                "operating_margin_pct": 44.6,
            },
            currency="EUR",
            period={
                "label": "ytd",
                "start_date": "2026-01-01",
                "end_date":   "2026-05-16",
                "days": 136,
                "semantic": "ytd",
            },
            temporal_scope="period_filtered",
        )
        # Spec compliance
        assert validate_envelope(env).ok
        # Specific keys for downstream consumers
        assert env["data"]["total_sales"] == 209954.34
        assert env["period"]["semantic"] == "ytd"
        assert env["_temporal_scope"] == "period_filtered"
        assert env["_source"]["tool"] == "query_cashflow_summary"
        assert env["_source"]["envelope_version"] == "14.0"

    def test_query_top_customers_shape(self):
        """All-time snapshot tool: no period block."""
        env = wrap_response(
            tool="query_top_customers",
            has_data=True,
            data={"customers": [{"name": "ACME", "total_revenue": 50000}]},
            temporal_scope="all_time",
        )
        assert validate_envelope(env).ok
        assert env["_temporal_scope"] == "all_time"
        assert "period" not in env

    def test_failed_tool_shape(self):
        """A tool that hit an internal error returns has_data=False
        with integrity=error so the chat AI escalates (Rule 20)."""
        env = wrap_response(
            tool="query_smart_brief",
            has_data=False,
            caveat=(
                "Smart brief failed on the cashflow section; call "
                "query_cashflow_summary directly with the same period."
            ),
            temporal_scope="period_filtered",
            integrity_status="error",
            integrity_message=(
                "risk_focus list/dict shape mismatch — pre-Wave-14 bug "
                "fixed in 14.HOTFIX #1; this branch should not fire."
            ),
        )
        assert validate_envelope(env).ok
        assert env["has_data"] is False
        assert env["_data_integrity"]["status"] == "error"


# ── 6. Reserved-fields contract sentinel ──────────────────────────────────


class TestReservedFieldsContract:
    """Reserved fields must stay stable — adding/removing any here
    breaks the envelope contract for tools that adopt it."""

    def test_envelope_required_fields_stable(self):
        assert REQUIRED_FIELDS == frozenset({
            "has_data",
            "_temporal_scope",
            "_data_integrity",
            "_source",
        })

    def test_envelope_recommended_fields_stable(self):
        assert RECOMMENDED_FIELDS == frozenset({
            "data",
            "currency",
            "period",
        })

    def test_canonical_scopes_match_wave_13_6_registry(self):
        from core.tool_temporal_scope import VALID_SCOPES
        # Envelope canonical scopes must be a subset of (or equal to)
        # the Wave 13.6 registry scopes so tools using either source
        # produce compatible values.
        assert CANONICAL_SCOPES == VALID_SCOPES


# ── 7. attach_envelope_metadata — migration helper ────────────────────────


class TestAttachEnvelopeMetadata:
    """Migration helper that adds envelope metadata to an existing
    legacy tool response without moving business fields around."""

    def test_adds_metadata_to_legacy_response(self):
        legacy = {
            "has_data": True,
            "total": 209954.34,
            "currency": "EUR",
            "period": {"start_date": "2026-01-01", "end_date": "2026-05-16"},
            "by_date": {"2026-01-15": 1000.0},
            "_caveat": None,
        }
        enriched = attach_envelope_metadata(
            legacy,
            tool="query_revenue",
            temporal_scope="period_filtered",
        )

        # Legacy fields preserved verbatim at the top level
        assert enriched["total"] == 209954.34
        assert enriched["currency"] == "EUR"
        assert enriched["by_date"] == {"2026-01-15": 1000.0}

        # Envelope metadata added
        assert enriched["_temporal_scope"] == "period_filtered"
        assert enriched["_data_integrity"]["status"] == "ok"
        assert enriched["_source"]["tool"] == "query_revenue"
        assert enriched["_source"]["envelope_version"] == ENVELOPE_VERSION

        # Validates lenient (no data namespace, warning only)
        result = validate_envelope(enriched)
        assert result.ok

    def test_does_not_mutate_input(self):
        legacy = {"has_data": True, "x": 1}
        original_keys = set(legacy.keys())
        attach_envelope_metadata(legacy, tool="x", temporal_scope="all_time")
        # Input untouched
        assert set(legacy.keys()) == original_keys

    def test_preserves_pre_existing_envelope_fields(self):
        """Tools that already set _temporal_scope (e.g. product_trend)
        keep their more-precise label — the helper does not overwrite."""
        response = {
            "has_data": True,
            "_temporal_scope": "materialized_30d_vs_prior_30d",
        }
        enriched = attach_envelope_metadata(
            response,
            tool="query_product_trend",
            temporal_scope="all_time",  # registry value would be this
        )
        # The pre-existing more-precise scope wins
        assert enriched["_temporal_scope"] == "materialized_30d_vs_prior_30d"

    def test_infers_has_data_when_missing(self):
        # Tool didn't emit has_data → inferred from absence of "error"
        enriched = attach_envelope_metadata(
            {"total": 100},
            tool="x",
            temporal_scope="period_filtered",
        )
        assert enriched["has_data"] is True

    def test_infers_has_data_false_when_error_present(self):
        enriched = attach_envelope_metadata(
            {"error": "boom"},
            tool="x",
            temporal_scope="period_filtered",
        )
        assert enriched["has_data"] is False

    def test_explicit_has_data_default_used_when_missing(self):
        enriched = attach_envelope_metadata(
            {"total": 0},
            tool="x",
            temporal_scope="period_filtered",
            has_data_default=False,
        )
        assert enriched["has_data"] is False

    def test_warning_integrity_with_message(self):
        enriched = attach_envelope_metadata(
            {"has_data": True, "total": 100},
            tool="x",
            temporal_scope="period_filtered",
            integrity_status="warning",
            integrity_message="customer_metrics last refreshed 9 days ago",
        )
        assert enriched["_data_integrity"]["status"] == "warning"
        assert enriched["_data_integrity"]["message"].startswith("customer_metrics")

    def test_warning_without_message_raises(self):
        with pytest.raises(ValueError, match="requires a non-empty integrity_message"):
            attach_envelope_metadata(
                {"has_data": True},
                tool="x",
                integrity_status="warning",
            )

    def test_non_dict_input_raises(self):
        with pytest.raises(ValueError, match="must be a Mapping"):
            attach_envelope_metadata([1, 2, 3], tool="x")

    def test_empty_tool_name_raises(self):
        with pytest.raises(ValueError, match="tool must be a non-empty"):
            attach_envelope_metadata({"has_data": True}, tool="")


# ── 8. Data integrity status vocabulary ───────────────────────────────────


class TestDataIntegrityStatusEnum:
    def test_three_canonical_values(self):
        assert DataIntegrityStatus.OK.value == "ok"
        assert DataIntegrityStatus.WARNING.value == "warning"
        assert DataIntegrityStatus.ERROR.value == "error"

    def test_enum_is_string_subclass(self):
        # str-Enum so JSON serialisation works without special casing.
        assert isinstance(DataIntegrityStatus.OK, str)
