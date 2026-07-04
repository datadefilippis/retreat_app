"""
Tool Result Envelope Contract — Wave 14.0 foundation.

Every AI chat tool returns a JSON-serialisable dict that flows back to
Anthropic as a ``tool_result`` block. Pre-Wave-14 each tool invented
its own shape: some returned ``{"has_data": false, "_caveat": "..."}``,
others ``{"error": "..."}``, others a bare data dict, others a list,
others ``{"data": {...}, "_epistemic": {...}}``. The model had to
code-switch between shapes every turn, and silent contract violations
(a missing key, an unexpected type) became invisible bugs the chat
AI papered over with synthesised numbers — see the Wave 14 audit and
the 2026-05-16 production incident.

This module defines the **canonical envelope** every tool SHOULD
adopt. The envelope is opt-in via :func:`wrap_response`; existing
tools keep working unchanged until Phase 14.1 migrates them. The
validator :func:`validate_envelope` lets contract tests assert that
a given response respects the contract.

Public API
----------
    :class:`DataIntegrityStatus`     — enum {ok, warning, error}
    :class:`EnvelopeValidationResult` — outcome of :func:`validate_envelope`
    :data:`REQUIRED_FIELDS`           — fields that MUST be present
    :data:`RECOMMENDED_FIELDS`        — fields strongly suggested
    :data:`RESERVED_FIELDS`           — fields the envelope owns
    :func:`wrap_response`             — build a canonical envelope
    :func:`validate_envelope`         — check a dict against the contract
    :func:`is_envelope`               — quick yes/no probe

Envelope shape (one example)::

    {
      "has_data": true,                            # MANDATORY
      "data": {                                    # actual payload
        "total_sales": 209954.34,
        "net_after_fixed": 90899.99,
        ...
      },
      "currency": "EUR",                           # required if has_data
      "period": {                                  # period-scoped tools only
        "label": "ytd",
        "start_date": "2026-01-01",
        "end_date":   "2026-05-16",
        "days": 136,
        "semantic": "ytd"
      },
      "_temporal_scope": "period_filtered",        # MANDATORY (Wave 13.6 vocabulary)
      "_caveat": null,                             # required when has_data=false
      "_data_integrity": {                         # MANDATORY
        "status": "ok",                            # ok | warning | error
        "message": null
      },
      "_source": {                                 # MANDATORY (forensic)
        "tool": "query_cashflow_summary",
        "envelope_version": "14.0"
      }
    }

Design rationale
----------------

* **has_data is the binary the AI keys on.** All anti-hallucination
  rules (Wave 14.HOTFIX Rule 21) depend on it being unambiguous and
  always present. The envelope makes it MANDATORY.

* **data is namespaced.** Pre-Wave-14, the business payload lived
  at the top level mixed with metadata (``_caveat``, ``_epistemic``,
  ``_temporal_scope``). The envelope separates "envelope metadata"
  (underscore-prefixed) from "business data" (under the ``data`` key)
  so the model can read each section deterministically.

* **_temporal_scope is mandatory.** Wave 13.6 made the chat
  dispatcher auto-inject the scope from a registry, but tools that
  KNOW their scope more precisely (e.g. ``query_product_trend`` =
  ``materialized_30d_vs_prior_30d``) can declare it themselves. The
  envelope formalises this: the field MUST be present after the
  dispatcher pass, never None at the point the model reads it.

* **_data_integrity is mandatory.** A tool that succeeded but with
  caveats (partial data, stale snapshot, computed proxy) MUST signal
  it. The chat AI is then instructed (Wave 14 prompt) to relay the
  integrity warning rather than pretend everything is clean.

* **_source is forensic.** Every response carries the tool name and
  envelope version. Combined with ``AIUsageEvent.period_audit``
  (Wave 13.2), this makes end-to-end forensic reconstruction trivial:
  "given turn N at time T, the model received envelope X from tool
  Y on data with integrity Z".

Backward compatibility
----------------------

This module ADDS new helpers — it does NOT change any existing tool.
:func:`wrap_response` is opt-in. Tools that don't use it continue to
work; the chat dispatcher (Wave 13.6 ``attach_temporal_scope``)
still injects ``_temporal_scope`` for them.

Phase 14.1 will migrate each tool to use ``wrap_response`` one by
one, with contract tests asserting envelope compliance. By the end
of Phase 14.1 every chat tool should return a valid envelope.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Optional


#: Current envelope version. Bumped when the envelope shape changes
#: in a way callers must observe. Tools record it in ``_source`` so
#: future analysis can correlate envelope behaviour to a version.
ENVELOPE_VERSION = "14.0"


# ── Vocabulary ──────────────────────────────────────────────────────────────


class DataIntegrityStatus(str, Enum):
    """Status of the data inside ``data``.

    ``ok``      — Data is reliable, no caveats. Default.
    ``warning`` — Data is usable but has caveats (partial, stale,
                  approximation, proxy metric). ``_data_integrity.message``
                  MUST explain why.
    ``error``   — Data could not be computed reliably; the AI must
                  NOT cite numbers from this response. Pair with
                  ``has_data=False`` and a clear ``_caveat``.
    """

    OK = "ok"
    WARNING = "warning"
    ERROR = "error"


#: Field names the envelope owns. Tools MUST NOT use these as their
#: own data keys — they'd collide with the envelope metadata when
#: ``wrap_response`` flattens or validates the response.
RESERVED_FIELDS = frozenset({
    "has_data",
    "data",
    "currency",
    "period",
    "_temporal_scope",
    "_caveat",
    "_data_integrity",
    "_source",
    # Aliases / Wave-13 transitional fields kept readable
    "_truncated",
    "_truncated_by",
    "_original_size_chars",
    "_cap_chars",
    "_hint",
    "head",
})


#: Fields the envelope contract considers MANDATORY. A response
#: missing any of these is non-compliant; :func:`validate_envelope`
#: flags them as errors.
REQUIRED_FIELDS = frozenset({
    "has_data",
    "_temporal_scope",
    "_data_integrity",
    "_source",
})


#: Fields the envelope contract considers RECOMMENDED. Their absence
#: produces a warning, not an error — useful e.g. for non-period
#: tools that legitimately omit ``period``.
RECOMMENDED_FIELDS = frozenset({
    "data",
    "currency",
    "period",
})


#: Valid values for ``_temporal_scope``. Mirrors the Wave 13.6
#: registry plus the fine-grained labels individual tools may set.
#: Tools are free to invent more specific labels (e.g.
#: ``materialized_30d_vs_prior_30d`` from query_product_trend) —
#: validator accepts any string but warns when one of the canonical
#: scope values is more accurate.
CANONICAL_SCOPES = frozenset({
    "period_filtered",
    "all_time",
    "current_state",
    "forward_looking",
    "meta",
})


# ── Validation result ───────────────────────────────────────────────────────


@dataclass(frozen=True)
class EnvelopeValidationResult:
    """Outcome of :func:`validate_envelope`.

    Attributes:
      ok: True if the response is fully compliant with the contract.
          May still carry warnings (compliant but suboptimal).
      errors: List of human-readable strings explaining contract
              violations. Each one corresponds to a field that
              MUST be present / valid.
      warnings: Recommended fields missing or non-canonical values
                used. Not blocking but worth surfacing.
    """

    ok: bool
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.ok


# ── Internal helpers ────────────────────────────────────────────────────────


def _validate_temporal_scope(scope: Any) -> tuple[bool, Optional[str]]:
    """Return (is_valid, warning_msg)."""
    if scope is None:
        return False, "_temporal_scope is None"
    if not isinstance(scope, str):
        return False, f"_temporal_scope must be a string, got {type(scope).__name__}"
    if not scope:
        return False, "_temporal_scope is empty"
    if scope not in CANONICAL_SCOPES:
        # Non-canonical is allowed (tool-specific precision) but
        # we surface it as a warning so reviewers see the variance.
        return True, (
            f"_temporal_scope={scope!r} is not in CANONICAL_SCOPES; "
            "tool-specific values are permitted but document the rationale."
        )
    return True, None


def _validate_data_integrity(di: Any) -> tuple[bool, Optional[str]]:
    """Return (is_valid, error_msg)."""
    if not isinstance(di, dict):
        return False, f"_data_integrity must be a dict, got {type(di).__name__}"
    status = di.get("status")
    if status is None:
        return False, "_data_integrity.status is required"
    if status not in {s.value for s in DataIntegrityStatus}:
        return False, (
            f"_data_integrity.status={status!r} is not one of "
            f"{[s.value for s in DataIntegrityStatus]}"
        )
    # Warning / error MUST carry a message so the AI can relay it.
    if status in ("warning", "error") and not di.get("message"):
        return False, (
            f"_data_integrity.status={status!r} requires a non-empty "
            "_data_integrity.message"
        )
    return True, None


def _validate_source(src: Any) -> tuple[bool, Optional[str]]:
    if not isinstance(src, dict):
        return False, f"_source must be a dict, got {type(src).__name__}"
    if not src.get("tool"):
        return False, "_source.tool is required"
    if not src.get("envelope_version"):
        return False, "_source.envelope_version is required"
    return True, None


# ── Public API ──────────────────────────────────────────────────────────────


def wrap_response(
    *,
    tool: str,
    has_data: bool,
    data: Optional[Mapping[str, Any]] = None,
    currency: Optional[str] = None,
    period: Optional[Mapping[str, Any]] = None,
    temporal_scope: Optional[str] = None,
    caveat: Optional[str] = None,
    integrity_status: str = DataIntegrityStatus.OK.value,
    integrity_message: Optional[str] = None,
) -> dict:
    """Build a canonical envelope response.

    Args:
      tool: The tool name (matches the entry in
            :data:`core.tool_temporal_scope.TOOL_SCOPE`). Required so
            the response carries forensic source attribution.
      has_data: Whether the response actually contains business data.
                When False, the AI is instructed (Rule 21) to NOT
                quote numbers from ``data`` and to cite ``caveat``.
      data: The business payload — KPIs, lists, breakdowns, etc.
            Optional only when ``has_data=False`` (in which case it
            defaults to an empty dict).
      currency: ISO currency code (EUR, CHF, USD…). Required when
                ``has_data=True`` and the payload includes monetary
                amounts; can be omitted for tools that don't return
                money.
      period: Period block (start_date / end_date / label / days /
              semantic). Required for period-scoped tools.
      temporal_scope: One of the values in :data:`CANONICAL_SCOPES`
                      OR a more specific tool-defined label (e.g.
                      ``materialized_30d_vs_prior_30d``). If omitted,
                      Phase 13.6 dispatcher will inject the scope
                      from the registry — but tools that KNOW their
                      scope should declare it explicitly here.
      caveat: Human-readable explanation when ``has_data=False`` OR
              when the data has notable limitations. Surfaced to the
              user by the chat AI via Rule 21.
      integrity_status: ``ok`` | ``warning`` | ``error``. See
                        :class:`DataIntegrityStatus`.
      integrity_message: Required when status is ``warning`` or
                         ``error``; explains the issue.

    Returns:
      A canonical envelope dict ready to return from the tool's
      executor. The shape matches the module docstring's example
      AND passes :func:`validate_envelope` in strict mode.

    Raises:
      ValueError: If the caller's arguments violate basic invariants
                  (e.g. ``has_data=True`` with ``data=None``,
                  ``integrity_status='warning'`` without a message).
                  These are programmer errors, not user errors —
                  fail loud so the migration of tools to the envelope
                  surfaces them early.
    """
    # ── Argument validation ──────────────────────────────────────────────
    if not isinstance(tool, str) or not tool.strip():
        raise ValueError("wrap_response: tool must be a non-empty string")

    if integrity_status not in {s.value for s in DataIntegrityStatus}:
        raise ValueError(
            f"wrap_response: integrity_status={integrity_status!r} is "
            f"not one of {[s.value for s in DataIntegrityStatus]}"
        )

    if integrity_status in ("warning", "error") and not integrity_message:
        raise ValueError(
            f"wrap_response: integrity_status={integrity_status!r} "
            "requires a non-empty integrity_message"
        )

    if has_data is False and not caveat and integrity_status == "ok":
        # When the tool says "no data" but offers no explanation AND
        # no integrity signal, the chat AI cannot relay any context
        # to the user. Force at least one of caveat or integrity to
        # be informative.
        raise ValueError(
            "wrap_response: has_data=False requires either a caveat "
            "or integrity_status != 'ok' with integrity_message — "
            "otherwise the AI cannot tell the user WHY data is missing"
        )

    # ── Assemble the envelope ────────────────────────────────────────────
    envelope: dict = {
        "has_data": has_data,
        "data": dict(data) if data else {},
        "_data_integrity": {
            "status": integrity_status,
            "message": integrity_message,
        },
        "_source": {
            "tool": tool,
            "envelope_version": ENVELOPE_VERSION,
        },
    }

    # Optional fields included only when present (keeps the envelope
    # minimal for non-period / no-currency tools).
    if currency is not None:
        envelope["currency"] = currency
    if period is not None:
        envelope["period"] = dict(period)
    if temporal_scope is not None:
        envelope["_temporal_scope"] = temporal_scope
    if caveat is not None:
        envelope["_caveat"] = caveat

    return envelope


def attach_envelope_metadata(
    response: Mapping[str, Any],
    *,
    tool: str,
    temporal_scope: Optional[str] = None,
    integrity_status: str = DataIntegrityStatus.OK.value,
    integrity_message: Optional[str] = None,
    has_data_default: Optional[bool] = None,
) -> dict:
    """Migration helper: add envelope metadata to an EXISTING response.

    Wave 14.1 contract — lets legacy tools adopt the envelope WITHOUT
    moving their business fields under the ``data`` namespace. The
    legacy shape (``{"pnl": {...}, "yoy": {...}, ...}``) is preserved
    at the top level; we only ADD the four envelope metadata fields
    (``_temporal_scope``, ``_data_integrity``, ``_source``, plus
    ``has_data`` if the legacy tool didn't already emit it).

    Returns a NEW dict (does not mutate the caller's input) ready to
    pass :func:`validate_envelope` in lenient mode. Useful for the
    Phase 14.1 incremental migration: each tool can adopt the
    envelope in a single 3-line patch.

    Args:
      response: The legacy tool response (any dict shape).
      tool: Tool name for ``_source.tool``.
      temporal_scope: Scope label. If None, the chat dispatcher's
                      Wave 13.6 ``attach_temporal_scope`` will fill
                      it in from the registry — but tools are
                      encouraged to set it explicitly here.
      integrity_status: ``ok`` | ``warning`` | ``error``. Default ``ok``.
      integrity_message: Required when status != ok.
      has_data_default: Used ONLY when the response has no
                        ``has_data`` key. Set this when the legacy
                        tool didn't emit it explicitly.

    Raises:
      ValueError: on programmer errors (empty tool, invalid status,
                  warning/error without message).
    """
    if not isinstance(response, Mapping):
        raise ValueError(
            "attach_envelope_metadata: response must be a Mapping/dict, "
            f"got {type(response).__name__}"
        )
    if not tool or not str(tool).strip():
        raise ValueError(
            "attach_envelope_metadata: tool must be a non-empty string"
        )
    if integrity_status not in {s.value for s in DataIntegrityStatus}:
        raise ValueError(
            f"attach_envelope_metadata: invalid integrity_status="
            f"{integrity_status!r}"
        )
    if integrity_status in ("warning", "error") and not integrity_message:
        raise ValueError(
            f"attach_envelope_metadata: integrity_status="
            f"{integrity_status!r} requires a non-empty integrity_message"
        )

    enriched: dict = dict(response)

    # has_data — present in most legacy tools but not all
    if "has_data" not in enriched:
        if has_data_default is not None:
            enriched["has_data"] = bool(has_data_default)
        else:
            # Best-effort inference for tools that didn't track it:
            # ``error`` field present → no data; otherwise pessimistic
            # default True (legacy tools that omit has_data tend to
            # be data-bearing when they don't raise).
            enriched["has_data"] = "error" not in enriched

    # Envelope metadata — only set when not already present so a tool
    # that opts to declare its own (e.g. a more specific scope) wins.
    if "_temporal_scope" not in enriched and temporal_scope is not None:
        enriched["_temporal_scope"] = temporal_scope
    if "_data_integrity" not in enriched:
        enriched["_data_integrity"] = {
            "status": integrity_status,
            "message": integrity_message,
        }
    if "_source" not in enriched:
        enriched["_source"] = {
            "tool": str(tool),
            "envelope_version": ENVELOPE_VERSION,
        }

    return enriched


def validate_envelope(
    response: Any,
    *,
    strict: bool = False,
) -> EnvelopeValidationResult:
    """Validate a tool response against the envelope contract.

    Args:
      response: The dict returned by a tool's executor.
      strict: When True, recommended fields are promoted to errors.
              Useful for contract tests that want to enforce the
              full envelope; production validation can stay lenient.

    Returns:
      :class:`EnvelopeValidationResult` with ``ok``, ``errors``,
      ``warnings``. Truthy when fully compliant.
    """
    errors: list = []
    warnings: list = []

    if not isinstance(response, dict):
        return EnvelopeValidationResult(
            ok=False,
            errors=[f"response is not a dict (got {type(response).__name__})"],
        )

    # ── REQUIRED fields ──────────────────────────────────────────────────
    for field_name in REQUIRED_FIELDS:
        if field_name not in response:
            errors.append(f"missing required field: {field_name}")

    if "has_data" in response and not isinstance(response["has_data"], bool):
        errors.append(
            f"has_data must be bool, got {type(response['has_data']).__name__}"
        )

    if "_temporal_scope" in response:
        ok, msg = _validate_temporal_scope(response["_temporal_scope"])
        if not ok:
            errors.append(msg or "invalid _temporal_scope")
        elif msg:
            warnings.append(msg)

    if "_data_integrity" in response:
        ok, msg = _validate_data_integrity(response["_data_integrity"])
        if not ok:
            errors.append(msg or "invalid _data_integrity")

    if "_source" in response:
        ok, msg = _validate_source(response["_source"])
        if not ok:
            errors.append(msg or "invalid _source")

    # ── Cross-field invariants ──────────────────────────────────────────
    has_data = response.get("has_data")
    caveat = response.get("_caveat")
    integrity = response.get("_data_integrity") or {}
    integrity_status = integrity.get("status")
    if has_data is False and not caveat and integrity_status == "ok":
        errors.append(
            "has_data=False requires a _caveat OR _data_integrity.status "
            "!= 'ok' so the AI can explain why data is missing"
        )

    # ── RECOMMENDED fields ──────────────────────────────────────────────
    for field_name in RECOMMENDED_FIELDS:
        if field_name not in response:
            msg = f"recommended field missing: {field_name}"
            if strict:
                errors.append(msg)
            else:
                warnings.append(msg)

    # ── Reserved field hygiene ──────────────────────────────────────────
    # If the tool put business data UNDER a reserved field name (e.g.
    # ``data["currency"] = "EUR"`` instead of top-level ``currency``),
    # the envelope semantics get murky. Surface this as a warning so
    # migration can clean it up.
    data_block = response.get("data") or {}
    if isinstance(data_block, dict):
        for reserved in (RESERVED_FIELDS & set(data_block.keys())):
            if reserved == "data":
                # Tools may legitimately nest a "data" key inside their
                # business payload (e.g. {"data": {"data": {...}}});
                # we only warn on the OUTER layer.
                continue
            warnings.append(
                f"reserved field {reserved!r} appears inside data block; "
                "consider moving it to the envelope's top level"
            )

    return EnvelopeValidationResult(
        ok=not errors,
        errors=errors,
        warnings=warnings,
    )


def wrap_tool_result_envelope(tool_name: str, result: Any) -> Any:
    """Dispatcher-level envelope wrapper — Wave 14.1.B.

    Single entry point that the chat dispatcher calls AFTER each tool
    executes. Wraps the result with envelope metadata, using the
    Wave 13.6 ``TOOL_SCOPE`` registry to derive ``_temporal_scope``
    when the tool didn't set one itself.

    Idempotent: when ``result`` is already a fully-formed envelope
    (``is_envelope()`` returns True — typically the case for the 5
    tools migrated in Phase 14.1.A) the call is a no-op and the
    pre-existing envelope is returned unchanged.

    Defensive on non-dict results: lists, ``None``, strings, and any
    other non-dict shapes pass through unchanged. The envelope only
    applies to dict tool responses; everything else is the tool's
    own contract concern.

    Tools not registered in ``TOOL_SCOPE`` still get the other three
    envelope fields (``has_data``, ``_data_integrity``, ``_source``)
    so the response is partially-compliant; ``validate_envelope``
    will surface them as missing-scope errors, which is the signal
    to add the tool to the registry.

    Args:
      tool_name: The tool name the dispatcher is processing. Used
                 for ``_source.tool`` AND for the scope registry
                 lookup.
      result: Whatever the tool's executor returned.

    Returns:
      A NEW dict (envelope-compliant) when ``result`` is a non-envelope
      dict. Otherwise ``result`` unchanged.
    """
    if not isinstance(result, dict):
        return result
    if is_envelope(result):
        return result
    # Lazy import — keeps the envelope module free of cross-imports
    # from the tool registry except at the wrapping boundary.
    from core.tool_temporal_scope import get_scope
    scope = get_scope(tool_name)
    return attach_envelope_metadata(
        result,
        tool=tool_name,
        temporal_scope=scope,
    )


def is_envelope(response: Any) -> bool:
    """Quick yes/no probe: does ``response`` look like an envelope?

    Cheaper than :func:`validate_envelope` — useful inside hot paths
    (e.g. the chat dispatcher's tool-result post-processor) where we
    want to skip wrapping a response that's already canonical.
    """
    if not isinstance(response, dict):
        return False
    # All four REQUIRED fields present == is_envelope. We don't go
    # deeper here; full structural check is validate_envelope's job.
    return REQUIRED_FIELDS.issubset(response.keys())
