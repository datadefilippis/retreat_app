# Re-export all models for backwards compatibility
# Usage: from models import User, Organization, etc.

from .common import generate_id, utc_now

from .user import (
    UserRole,
    UserBase,
    UserCreate,
    UserLogin,
    User,
    UserResponse,
    UserInvite,
    UserInviteResponse,
)

from .organization import (
    OrganizationBase,
    OrganizationCreate,
    Organization
)

from .dataset import (
    DatasetType,
    DatasetBase,
    DatasetCreate,
    Dataset,
    DatasetResponse,
    UploadResponse,
    SalesRecord,
    SalesRecordCreate,
    SalesRecordUpdate,
    ExpenseRecord,
    ExpenseRecordCreate,
    ExpenseRecordUpdate,
    # PurchaseRecord: canonical version imported from .financial_record below
    PurchaseRecordCreate,
    FixedCostFrequency,
    FixedCostCategory,
    # FixedCost: canonical version imported from .financial_record below
    FixedCostCreate
)

from .module import (
    ModuleMetadata,
    OrganizationModule
)

from .alert import (
    AlertSeverity,
    AlertStatus,
    AlertBase,
    Alert,
    AlertUpdate
)

from .insight import (
    InsightBase,
    Insight
)

from .analytics import (
    DailyAggregate,
    KPIData,
    ChartDataPoint
)

from .audit import AuditLog

from .auth import (
    TokenResponse,
    ChangePasswordRequest,
    ChangePasswordResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
    VerifyEmailRequest,
    VerifyEmailResponse,
    ResendVerificationRequest,
    ResendVerificationResponse,
)

# ── Phase-1 new models ────────────────────────────────────────────────────────
from .customer import Customer, CustomerCreate, CustomerResponse

from .supplier import Supplier, SupplierCreate, SupplierResponse

from .product import Product, ProductCreate, ProductResponse

from .financial_record import (
    PaymentStatus,
    PurchaseRecord,
    PurchaseRecordResponse,
    CostFrequency,
    FixedCost,
    FixedCostResponse,
)

from .kpi_snapshot import KPISnapshot, KPISnapshotBase, KPISnapshotResponse

from .column_mapping import (
    ColumnMapping,
    ColumnMappingBase,
    ColumnMappingResponse,
    ColumnStat,
    DatasetColumnProfile,
    DatasetColumnProfileResponse,
)

from .data_validation_rule import (
    ValidationRuleType,
    DataValidationRuleBase,
    DataValidationRule,
    DataValidationRuleResponse,
    DataValidationRuleUpdate,
)

from .module_config import ModuleConfig, ModuleConfigBase, ModuleConfigResponse

from .schema_version import SchemaVersion, SchemaVersionResponse

from .digest import Digest

from .ai_usage import AIUsageEvent

from .pricing_plan import PricingPlan

from .subscription import ModuleSubscription
from .addon_subscription import AddonSubscription
from .org_quota_notice import OrgQuotaNotice

# ── Controlled Access (v6.0) ─────────────────────────────────────────────────
from .platform_settings import PlatformSettings, RegistrationMode

# ── Sales Core: Orders (v7.0) ─────────────────────────────────────────────────
from .order import (
    OrderStatus,
    OrderPaymentStatus,
    OrderLineBase,
    OrderLineCreate,
    OrderCreate,
    OrderUpdate,
    Order,
    OrderResponse,
)

from .invite import (
    InviteStatus,
    InviteCreate,
    Invite,
    InviteResponse,
    InviteListResponse,
)


__all__ = [
    # Common
    'generate_id',
    'utc_now',
    # User
    'UserRole',
    'UserBase',
    'UserCreate',
    'UserLogin',
    'User',
    'UserResponse',
    'UserInvite',
    'UserInviteResponse',
    # Organization
    'OrganizationBase',
    'OrganizationCreate',
    'Organization',
    # Dataset
    'DatasetType',
    'DatasetBase',
    'DatasetCreate',
    'Dataset',
    'DatasetResponse',
    'UploadResponse',
    'SalesRecord',
    'ExpenseRecord',
    'PurchaseRecord',
    'PurchaseRecordCreate',
    'FixedCostFrequency',
    'FixedCostCategory',
    'FixedCost',
    'FixedCostCreate',
    'SalesRecordCreate',
    'SalesRecordUpdate',
    'ExpenseRecordCreate',
    'ExpenseRecordUpdate',
    # Module
    'ModuleMetadata',
    'OrganizationModule',
    # Alert
    'AlertSeverity',
    'AlertStatus',
    'AlertBase',
    'Alert',
    'AlertUpdate',
    # Insight
    'InsightBase',
    'Insight',
    # Analytics
    'DailyAggregate',
    'KPIData',
    'ChartDataPoint',
    # Audit
    'AuditLog',
    # Auth
    'TokenResponse',
    'ChangePasswordRequest',
    'ChangePasswordResponse',
    'ForgotPasswordRequest',
    'ForgotPasswordResponse',
    'ResetPasswordRequest',
    'ResetPasswordResponse',
    'VerifyEmailRequest',
    'VerifyEmailResponse',
    'ResendVerificationRequest',
    'ResendVerificationResponse',
    # ── Phase-1 ──
    'Customer',
    'CustomerCreate',
    'CustomerResponse',
    'Supplier',
    'SupplierCreate',
    'SupplierResponse',
    'Product',
    'ProductCreate',
    'ProductResponse',
    'PaymentStatus',
    'PurchaseRecord',
    'PurchaseRecordResponse',
    'CostFrequency',
    'FixedCost',
    'FixedCostResponse',
    'KPISnapshot',
    'KPISnapshotBase',
    'KPISnapshotResponse',
    'ColumnMapping',
    'ColumnMappingBase',
    'ColumnMappingResponse',
    'ColumnStat',
    'DatasetColumnProfile',
    'DatasetColumnProfileResponse',
    'ValidationRuleType',
    'DataValidationRuleBase',
    'DataValidationRule',
    'DataValidationRuleResponse',
    'DataValidationRuleUpdate',
    'ModuleConfig',
    'ModuleConfigBase',
    'ModuleConfigResponse',
    'SchemaVersion',
    'SchemaVersionResponse',
    # Digest
    'Digest',
    # AI Usage
    'AIUsageEvent',
    # Modular Subscriptions (v4.0)
    'PricingPlan',
    'ModuleSubscription',
    # Add-on subscriptions (v5.8 / Onda 3)
    'AddonSubscription',
    # Quota warning notices (v5.8 / Onda 6)
    'OrgQuotaNotice',
    # Controlled Access (v6.0)
    'PlatformSettings',
    'RegistrationMode',
    'InviteStatus',
    'InviteCreate',
    'Invite',
    'InviteResponse',
    'InviteListResponse',
    # Sales Core: Orders (v7.0)
    'OrderStatus',
    'OrderPaymentStatus',
    'OrderLineBase',
    'OrderLineCreate',
    'OrderCreate',
    'OrderUpdate',
    'Order',
    'OrderResponse',
]
