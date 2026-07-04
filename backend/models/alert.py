from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum
from .common import generate_id, utc_now


class AlertSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AlertStatus(str, Enum):
    NEW = "new"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class AlertBase(BaseModel):
    module_key: str
    severity: AlertSeverity
    title: str
    summary: str
    date_reference: str
    metric_payload: Dict[str, Any] = {}

    # ── Wave 13.4 additions (Period Integrity for alerts) ────────────────────
    #
    # The analysis window used to compute this alert. Optional + all None
    # by default → zero schema migration, zero breaking change for existing
    # alerts (pre-Wave-13.4 documents simply have these fields absent / None
    # and the chat layer treats them as "unknown window" gracefully).
    #
    # Why they matter (Wave 13 audit BUG #3):
    #   An alert generated 30 days ago for "calo ricavi nelle ultime 4
    #   settimane" was computed on the 2026-03-16 → 2026-04-15 window.
    #   If the user later asks the chat "spiega questo alert", the chat
    #   needs the ORIGINAL window — not "current 30 days" — to give a
    #   coherent explanation that does not contradict the alert's own
    #   premise. Pre-13.4 the window was nowhere to be found in the
    #   document; chat fell back to "current data" and produced
    #   self-contradicting analyses.
    #
    #   ``period_start`` / ``period_end``  Inclusive ISO YYYY-MM-DD window
    #                                       used to compute the metric that
    #                                       triggered the alert.
    #   ``window_label``                    Short human / audit label
    #                                       ("30d", "90d", "ytd", "custom")
    #                                       describing the window. Lets the
    #                                       AI quote "negli ultimi 30 giorni"
    #                                       precisely without parsing dates.
    #
    # Default population is performed in ``alert_engine.run_alert_engine``
    # — any alert without an explicit window inherits the engine's default
    # 30-day-from-today window (the one used by the majority of rules).
    # Rules that operate on a different window (90d, 365d) can override
    # by setting these fields directly on the Alert.
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    window_label: Optional[str] = None


class Alert(AlertBase):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=generate_id)
    organization_id: str
    status: AlertStatus = AlertStatus.NEW
    created_at: datetime = Field(default_factory=utc_now)
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    # ── Phase-1 additions (all Optional → zero breaking change) ──────────────
    schema_version: Optional[str] = None
    auto_resolved: Optional[bool] = None      # True if resolved by the system automatically
    resolution_note: Optional[str] = None     # free-text note on resolution
    ai_analysis: Optional[str] = None         # AI root-cause analysis text

    # ── v3.0 additions (alert system redesign) ────────────────────────────────
    alert_category: Optional[str] = None      # "A"|"B"|"C"|"D"|"E" — alert family
    entity_key: Optional[str] = None          # dedup identity for business object
    suggested_action: Optional[str] = None    # localized actionable suggestion


class AlertUpdate(BaseModel):
    status: AlertStatus
