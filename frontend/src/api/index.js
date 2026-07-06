// Re-export all API modules for convenience
import api from './client';
import { authAPI } from './auth';
import { analyticsAPI, analyticsSnapshotAPI } from './analytics';
import { datasetsAPI } from './datasets';
import { modulesAPI } from './modules';
import { insightsAPI } from './insights';
import { organizationsAPI } from './organizations';
import { purchasesAPI } from './purchases';
import { fixedCostsAPI } from './fixedCosts';
import { salesAPI } from './sales';
import { expensesAPI } from './expenses';

// ── Phase-3 new API clients ───────────────────────────────────────────────────
import { customersAPI } from './customers';
import { suppliersAPI } from './suppliers';
import { productsAPI } from './products';
import { purchaseRecordsAPI } from './purchaseRecords';
import { columnMappingsAPI } from './columnMappings';

// ── Customers Light module API ────────────────────────────────────────────────
import { customersLightAPI } from './customersLight';

// ── Product Catalog module API ───────────────────────────────────────────────
import { productCatalogAPI } from './productCatalog';

// ── Phase-4 new API clients ───────────────────────────────────────────────────
import { validationRulesAPI } from './validationRules';

// ── User Preferences API ──────────────────────────────────────────────────────

// ── AI Chat API (v2.5) ──────────────────────────────────────────────────────
import { aiAPI } from './ai';

// ── AI Digest API (v2.5) ────────────────────────────────────────────────────
import { digestsAPI } from './digests';

// ── Export API (Blocco 1) ────────────────────────────────────────────────────
import { exportAPI } from './export';

// ── Billing API (v5.0) ───────────────────────────────────────────────────────
import { billingAPI } from './billing';

// ── System Admin API (v3.0) ───────────────────────────────────────────────────
// Only callable with a system_admin JWT — backend enforces 403 for all others.
import { adminAPI } from './admin';

// ── Sales Core: Orders (v7.0) ────────────────────────────────────────────────
import { ordersAPI } from './orders';

// ── Store Settings (v8.0) ───────────────────────────────────────────────────
import { storeSettingsAPI } from './storeSettings';

// ── Multi-Store (v12.0) ─────────────────────────────────────────────────────
import { storesAPI } from './stores';

// ── Availability (v12.0) ────────────────────────────────────────────────────
import { availabilityAPI } from './availability';

// ── Coupons (v13.0) ────────────────────────────────────────────────────────
import { couponsAPI } from './coupons';

// ── Org-level branding (olistic settings) ──────────────────────────────────
// Defaults that cascade to every store of the org. Per-store branding
// in storesAPI overrides these values when set. See backend resolver
// in services/branding_service.py for the full cascade contract.
import { orgBrandingAPI } from './orgBranding';

export {
  api as default,
  // Legacy (unchanged)
  authAPI,
  analyticsAPI,
  analyticsSnapshotAPI,
  datasetsAPI,
  modulesAPI,
  insightsAPI,
  organizationsAPI,
  purchasesAPI,
  fixedCostsAPI,
  salesAPI,
  expensesAPI,
  // Phase-3
  customersAPI,
  suppliersAPI,
  productsAPI,
  purchaseRecordsAPI,
  columnMappingsAPI,
  // Phase-4
  validationRulesAPI,
  // Preferences
  // AI Chat
  aiAPI,
  // AI Digest
  digestsAPI,
  // Export
  exportAPI,
  // Customers Light
  customersLightAPI,
  // Product Catalog
  productCatalogAPI,
  // Billing (v5.0)
  billingAPI,
  // System Admin (v3.0)
  adminAPI,
  // Sales Core: Orders
  ordersAPI,
  // Store Settings
  storeSettingsAPI,
  // Multi-Store
  storesAPI,
  // Availability
  availabilityAPI,
  // Coupons
  couponsAPI,
  // Org-level branding (olistic settings)
  orgBrandingAPI,
};
