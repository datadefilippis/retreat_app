from . import user_repository
from . import organization_repository
from . import dataset_repository
from . import alert_repository
from . import insight_repository
from . import module_repository
from . import analytics_repository
from . import audit_repository
from . import purchase_repository
from . import fixed_cost_repository
from . import sales_repository
from . import expenses_repository

# ── Phase-1 new repositories ──────────────────────────────────────────────────
from . import customer_repository
from . import supplier_repository
from . import product_repository
from . import kpi_snapshot_repository
from . import column_mapping_repository

__all__ = [
    # Legacy
    'user_repository',
    'organization_repository',
    'dataset_repository',
    'alert_repository',
    'insight_repository',
    'module_repository',
    'analytics_repository',
    'audit_repository',
    'purchase_repository',
    'fixed_cost_repository',
    'sales_repository',
    'expenses_repository',
    # Phase-1
    'customer_repository',
    'supplier_repository',
    'product_repository',
    'kpi_snapshot_repository',
    'column_mapping_repository',
]

# ── Commerce (Orders) ─────────────────────────────────────────────────────────
from . import order_repository

# ── Phase-3 new repositories ──────────────────────────────────────────────────
from . import purchase_record_repository
from . import fixed_cost_repository

# ── Phase-4 new repositories ──────────────────────────────────────────────────
from . import data_validation_rule_repository

# ── System Admin repositories (v2.9) ──────────────────────────────────────────
# Cross-org queries. Import ONLY from routes protected by require_system_admin.
from . import admin_repository

# ── Modular Subscriptions (v4.0) ─────────────────────────────────────────────
from . import subscription_repository

# ── Module-agnostic usage facade (v4.0) ──────────────────────────────────────
# Generic read/write path for usage tracking.  All callers use this.
from . import usage_repository

# ── AI Chat Session persistence ──────────────────────────────────────────────
from . import chat_session_repository

# ── Controlled Access (v6.0) ─────────────────────────────────────────────────
from . import platform_settings_repository
from . import invite_repository

# ── Release 4 (Courses) ──────────────────────────────────────────────────────
from . import course_repository
