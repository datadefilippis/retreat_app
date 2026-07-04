"""
CostSource — additive cost composition model for products (W1.S1).

Replaces the legacy single-value ``Product.cost_price`` with a richer
composition where each product has 0..N **additive components** of mixed
types. The final unit cost is the sum of all components.

Why additive components and not a single "type"
-----------------------------------------------
Real businesses mix cost types within the same product:

  - A pizza has tracked ingredients (categories with quantity)
    PLUS manual labor cost
    PLUS shared kitchen overhead (a share component).
  - A consultant has manual hourly cost PLUS manual software cost.
  - An e-commerce SKU may have one quantity-linked category PLUS
    manual packaging cost.

Forcing a single type per product would either model these poorly or
push complexity into the resolver. Additive components keep the data
model honest with the business reality.

Component types — what they mean
--------------------------------

``manual``               Direct value declared by the user. Independent
                         of purchase records. Used for services, digital
                         goods, packaging overheads, labor estimates.

``category_quantity``    Quantity-per-unit × WAC of a purchase_records
                         category. The recipe-style precise calculator:
                         "I consume 0.2 kg of Pasta per dish; the system
                         knows my WAC of Pasta this period is €1.50/kg,
                         so this component contributes €0.30."

``category_share``       Percent of the category's purchase pool. The
                         simple-mode calculator: "this product gets 35%
                         of the Cosmetics pool" — or with share_pct=None,
                         distributes the pool proportionally to revenue
                         among all products linking the same category.

``org_average``          Fallback when the user hasn't configured anything.
                         A WAC computed over a scoped subset of the org's
                         purchases (all / same item_type / same category).
                         Flagged with low confidence so the UI and the AI
                         Analyst can communicate the approximation.

Method (rolling window strategy)
--------------------------------
``method`` controls *how* the WAC is computed for category components
(and how org_average is windowed):

  ``fixed``      no time window — manual_value is the only signal,
                 category components fall back to the latest available
                 purchase data (rare; mostly for testing).
  ``latest``     last purchase record per category — most reactive,
                 most volatile.
  ``wac_30d``    weighted average cost over the last 30 days. Right for
                 high-volatility inputs (fresh food, perishables).
  ``wac_90d``    DEFAULT. Good balance for most businesses.
  ``wac_180d``   for slow-moving categories (artisanal materials).
  ``wac_365d``   for highly seasonal businesses where a full annual
                 cycle is needed to smooth out fluctuations.

Backward compatibility
----------------------
The legacy ``Product.cost_price`` field stays in the schema during the
W1 wave but is no longer the authoritative source of the cost calculation
once a ``cost_source`` is present. The migration script
``scripts/migrate_cost_price_to_components.py`` converts every
``cost_price > 0`` into a single ``manual`` component, after which
``cost_price`` can be dropped from the model (planned cleanup at the end
of Wave 1).
"""

from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
from typing import Optional, List, Literal


# ── Constants ────────────────────────────────────────────────────────────────
# Exposed as tuples so callers (validators, admin selectors, tests) get a
# single source of truth. Adding a new method or unit is a one-line change
# here plus the corresponding i18n key in product_cost.json.

COST_METHODS = (
    "fixed",      # no rolling window — manual_value frozen
    "latest",     # last purchase record per category
    "wac_30d",
    "wac_90d",    # default for new products
    "wac_180d",
    "wac_365d",
)

COST_COMPONENT_TYPES = (
    "manual",
    "category_quantity",
    "category_share",
    "org_average",
)

# Units of measure recognised for ``category_quantity`` components.
# The resolver filters purchase_records of the linked category by the same
# unit to keep the WAC mathematically sound (no kg + L mixing). Future
# Wave 4 will introduce automatic unit conversion (g↔kg, ml↔L).
COST_UNITS = ("kg", "g", "L", "ml", "pcs", "h", "m", "m2", "m3")

ORG_AVERAGE_SCOPES = ("all", "same_item_type", "same_category")


# ── Models ───────────────────────────────────────────────────────────────────


class CostComponent(BaseModel):
    """A single contribution to a product's unit cost.

    Components are summed (NOT averaged) by the resolver: ``unit_cost =
    Σ component.contribution``. Each component has a ``type`` discriminator
    that selects which other fields are meaningful — see the model-level
    validator below for the field requirements per type.

    The ``label`` is always required and is shown both in the admin UI
    (decomposition table) and persisted into the snapshot history, so the
    merchant can audit the composition even after editing.
    """

    model_config = ConfigDict(extra="ignore")

    type: Literal["manual", "category_quantity", "category_share", "org_average"]

    # Human-readable name for this contribution. Shown in the UI
    # decomposition row and in the cost_history snapshot. Required so
    # decomposition stays meaningful when audited months later.
    label: str = Field(min_length=1, max_length=100)

    # ── type="manual" ────────────────────────────────────────────────────────
    # User-declared numeric value (currency unit of the product). No
    # dependency on any other data — the resolver returns this value as-is.
    manual_value: Optional[float] = Field(default=None, ge=0)

    # ── type="category_quantity" / "category_share" ─────────────────────────
    # ``category`` is matched against ``purchase_records.category`` (exact
    # string match, case-sensitive). The UI sources the dropdown from the
    # actual set of categories used by the org's purchase records, so
    # there's no free-text drift.
    category: Optional[str] = Field(default=None, max_length=100)

    # ── type="category_quantity" only ──────────────────────────────────────
    # Quantity of the category consumed per 1 unit of the finished product.
    # Multiplied by the category's per-unit WAC at calculation time.
    qty_per_unit: Optional[float] = Field(default=None, ge=0)
    # Unit of measure for ``qty_per_unit``. Must match the unit used on
    # the corresponding purchase records (no auto-conversion in W1).
    qty_unit: Optional[str] = Field(default=None, max_length=10)

    # ── type="category_share" only ─────────────────────────────────────────
    # Percent of the category pool attributed to this product. When None,
    # the resolver distributes the pool proportionally to each linking
    # product's revenue share — the auto-balancing default.
    share_pct: Optional[float] = Field(default=None, ge=0, le=100)

    # ── type="org_average" only ────────────────────────────────────────────
    # How wide to cast the WAC net for the fallback estimate.
    scope: Optional[Literal["all", "same_item_type", "same_category"]] = None

    @field_validator("type", mode="before")
    @classmethod
    def _validate_type(cls, v):
        if v not in COST_COMPONENT_TYPES:
            raise ValueError(f"type must be one of {COST_COMPONENT_TYPES}")
        return v

    @field_validator("qty_unit", mode="before")
    @classmethod
    def _validate_qty_unit(cls, v):
        # Empty string is treated as "not specified" — many JSON clients
        # serialise unset optional strings as "" rather than null.
        if v is None or v == "":
            return None
        if v not in COST_UNITS:
            raise ValueError(f"qty_unit must be one of {COST_UNITS}")
        return v

    @model_validator(mode="after")
    def _validate_completeness(self):
        """Each component type has its own required-field set.

        Centralising the check here means the API rejects malformed
        components at parse time with a clear message, rather than the
        resolver swallowing them silently downstream.
        """
        if self.type == "manual":
            if self.manual_value is None:
                raise ValueError("manual component requires manual_value")
        elif self.type == "category_quantity":
            missing = []
            if not self.category:
                missing.append("category")
            if self.qty_per_unit is None:
                missing.append("qty_per_unit")
            if not self.qty_unit:
                missing.append("qty_unit")
            if missing:
                raise ValueError(
                    f"category_quantity component requires: {missing}"
                )
        elif self.type == "category_share":
            if not self.category:
                raise ValueError("category_share component requires category")
            # share_pct may legitimately be None — that's the auto-proportional
            # signal interpreted by the resolver.
        elif self.type == "org_average":
            if not self.scope:
                raise ValueError("org_average component requires scope")
        return self


class CostSource(BaseModel):
    """Container for a product's cost composition.

    Lives on ``Product.cost_source`` (optional). When present and
    ``components`` is non-empty, the resolver returns
    ``Σ component.contribution`` as the product's unit cost. When absent
    or empty, the product has no margin computable — the UI shows N/D
    with a CTA to configure the cost.

    ``method`` is global to the source: it selects the rolling window for
    every category-based component in the list. Manual components ignore
    the method (their value is fixed by definition).
    """

    model_config = ConfigDict(extra="ignore")

    method: Literal[
        "fixed",
        "latest",
        "wac_30d",
        "wac_90d",
        "wac_180d",
        "wac_365d",
    ] = "wac_90d"

    components: List[CostComponent] = Field(default_factory=list)

    @field_validator("method", mode="before")
    @classmethod
    def _validate_method(cls, v):
        if v and v not in COST_METHODS:
            raise ValueError(f"method must be one of {COST_METHODS}")
        # Empty / None defaults to the most balanced choice.
        return v or "wac_90d"
