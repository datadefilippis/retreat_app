"""Commercial Plan -- the user-facing plan catalog.

A CommercialPlan represents a purchasable bundle (Free / Core / Pro / Enterprise).
Each plan maps to a set of per-module pricing plans (module_plans dict).

When an org subscribes to a commercial plan, the plan_provisioning service
creates one ModuleSubscription per module in module_plans.

Design rules:
  - CommercialPlan is the ONLY model the user sees.
  - PricingPlan remains the per-module entitlement definition (internal).
  - module_access.py reads from ModuleSubscription/PricingPlan (unchanged).
  - Stripe fields are stored here for mapping, but Stripe is NOT the
    source of truth for access -- internal DB state is.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from models.common import generate_id


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CommercialPlan(BaseModel):
    """A purchasable plan bundle shown to users."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)

    # -- Identity ---------------------------------------------------------------
    slug: str                                  # "free", "core", "pro", "enterprise"
    name: str                                  # Display name: "AFianco Core"
    description: str = ""                      # Short tagline for pricing page
    tagline: str = ""                          # One-line value prop

    # -- Pricing ----------------------------------------------------------------
    price_monthly: float = 0.0                 # EUR/month (0 = free tier)
    price_yearly: Optional[float] = None       # EUR/year (discounted annual)
    currency: str = "EUR"                      # ISO 4217

    # -- Commercial flags -------------------------------------------------------
    trial_days: int = 0                        # 14 for paid self-serve, 0 for free
    is_public: bool = True                     # Show on pricing page
    is_self_serve: bool = True                 # True = Stripe Checkout, False = contact sales
    sort_order: int = 0                        # Display ordering (0 = first)

    # -- Stripe mapping (set after Stripe Products/Prices are created) ----------
    stripe_product_id: Optional[str] = None
    stripe_price_id_monthly: Optional[str] = None
    stripe_price_id_yearly: Optional[str] = None

    # -- Module -> PricingPlan slug mapping -------------------------------------
    # When org subscribes to this commercial plan, create one ModuleSubscription
    # per entry: { "cashflow_monitor": "cashflow_monitor_pro", ... }
    module_plans: Dict[str, str] = {}

    # -- Human-readable features for pricing UI ---------------------------------
    # Translation keys or plain strings. Frontend renders these as bullet points.
    features_display: List[str] = []

    # -- Add-on extension (v5.8 / Onda 3) ---------------------------------------
    # An "add-on" is a CommercialPlan with `is_addon=True` that does NOT replace
    # the main plan: it adds a Stripe subscription_item on top, contributing
    # extra quota to specific feature_keys (defined in `addon_provides`).
    #
    # Backward-compat: existing plans never set these fields → all default to
    # safe "non-addon" values, so the catalog continues to behave exactly as
    # today for `free`/`starter`/`core`/`pro`/`enterprise`.
    is_addon: bool = False

    # When `is_addon=True`, this dict declares which feature_keys the add-on
    # extends and by how much per unit. Shape:
    #   { module_key: { feature_key: quantity_provided } }
    # Example for "+50 AI chat": {"ai_assistant": {"chat": 50}}
    # Quantity is multiplied by AddonSubscription.quantity at access-check time.
    # `module_access.get_effective_limit()` (Onda 3+) sums base limit + Σ addons.
    # When -1 is provided, the feature becomes unlimited regardless of base.
    addon_provides: Optional[Dict[str, Dict[str, int]]] = None

    # When `is_addon=True`, restricts which main commercial_plan slugs can buy
    # this add-on. Empty list = compatible with ANY non-free plan. The free
    # plan is always excluded by default (Free orgs cannot buy add-ons).
    # Example: ["core", "pro"] for a Pro-only addon like extra_store.
    compatible_plans: List[str] = []

    # When `is_addon=True`, max number of times the same add-on can be stacked
    # on a single subscription (e.g. 5 = customer can buy up to 5x +50 chat
    # packs for a total of +250 chat). 1 = single-use add-on.
    max_quantity: int = 1

    # -- Retreat fork: fee transazionale legata al piano -------------------------
    # Percentuale di application_fee applicata ai pagamenti Connect degli
    # operatori su questo piano (Gratis=5, Pro/Founding=2). None = il piano
    # non governa la fee (piani legacy AFianco: resta il valore manuale su
    # org). Al provisioning (plan_provisioning, entry point canonico di OGNI
    # cambio piano) il valore viene sincronizzato su
    # organization.application_fee_percent — che resta l'unico punto letto
    # dal checkout a runtime. La fee piattaforma è SEPARATA dalle commissioni
    # di processing Stripe (che Stripe applica per conto suo sull'account
    # connesso): la UI le dichiara distinte.
    transaction_fee_percent: Optional[float] = None

    # -- Governance (Phase 2a) --------------------------------------------------
    is_archived: bool = False                  # Archived plans: not available for new subs
    admin_modified_at: Optional[datetime] = None  # Set when admin edits via catalog UI

    # -- Addon CTAs override (Onda 10 Step B.4) ---------------------------------
    # Per-plan override of the "which add-on to suggest when this metric is
    # exhausted" mapping. Falls back to services/quota_email_service.py:
    # METRIC_TO_ADDON_OFFER if a metric_key is not present here.
    #
    # Shape: { metric_key: addon_slug }
    # Example: {"orders_monthly": "addon_orders_pack_solo"}  (custom for Solo)
    #
    # Useful for plan-specific bundling: e.g. Solo plan suggests a smaller
    # orders pack (€10/100 ord) while Pro suggests the larger one (€25/500).
    addon_ctas: Optional[Dict[str, str]] = None

    # -- Platform-wide limits (Onda 10 Step B.1) --------------------------------
    # Limits that aren't tied to a specific module's PricingPlan tier. These
    # are values that historically lived hardcoded in routers/services
    # (e.g. _TEAM_LIMITS, chat_session_ttl_days, hard_abuse_caps). Migrating
    # them here makes them admin-editable through the catalog UI without
    # any redeploy.
    #
    # Convention: integer values, with the same -1/0/N semantics as
    # PricingPlan.limits — `-1`=unlimited, `0`=disabled, `>0`=quota.
    #
    # Currently defined keys:
    #   · "team_members" (Step B.1)         — max active users in org
    #   · "chat_session_ttl_days" (B.2)     — chat history retention
    #   · "stores_max_abuse_cap" (B.5)      — defence-in-depth above stores_max
    #
    # Backwards compat: when None or empty, callers fall back to the legacy
    # hardcoded `_TEAM_LIMITS`/`_PLAN_TTL_DAYS` dicts so no behaviour change
    # before the migration runs.
    platform_limits: Optional[Dict[str, int]] = None

    # -- Timestamps -------------------------------------------------------------
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)


class BillingEvent(BaseModel):
    """Idempotent record of a processed Stripe webhook event.

    Before processing any webhook, check if stripe_event_id already exists.
    If yes, skip processing (idempotent). If no, process and record.
    """

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)
    stripe_event_id: str                       # Stripe event ID (evt_xxx) -- unique
    event_type: str                            # e.g. "checkout.session.completed"
    organization_id: Optional[str] = None      # Resolved org, if applicable
    payload_summary: Dict[str, Any] = {}       # Key fields from the event payload
    processed: bool = True
    error: Optional[str] = None                # Error message if processing failed
    created_at: datetime = Field(default_factory=_utc_now)
